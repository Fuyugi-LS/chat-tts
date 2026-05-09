import datetime
import logging
import os
import signal
import sys
import time
import typing
from pathlib import Path
from typing import Optional

try:
    from PySide6.QtCore import QObject, QTimer, QtMsgType, Signal, qInstallMessageHandler
    from PySide6.QtWidgets import QApplication
except ImportError:
    sys.exit("Missing dependency: PySide6\nRun: pip install PySide6>=6.11.0")

try:
    import src.tt2s_gui as tt2s_gui
except ImportError as e:
    sys.exit(f"Missing GUI module: {e}\nEnsure tt2s_gui.py is in the same directory as tt2s.py")

import src.config as config

try:
    from src.worker import TTSWorker
except ImportError as e:
    sys.exit(f"Missing worker dependency: {e}\nRun: pip install -r requirements.txt")


# ---------------------------------------------------------------------------
_qt_log = logging.getLogger("qt")


def _qt_msg_handler(mode: QtMsgType, context, message: str) -> None:
    if mode == QtMsgType.QtDebugMsg:
        _qt_log.debug(message)
    elif mode == QtMsgType.QtInfoMsg:
        _qt_log.info(message)
    elif mode == QtMsgType.QtWarningMsg:
        _qt_log.warning(message)
    elif mode in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        _qt_log.error(message)


class _QtLogSignal(QObject):
    message = Signal(str)


class _QtLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self._obj = _QtLogSignal()
        self.message = self._obj.message

    def emit(self, record: logging.LogRecord) -> None:
        self._obj.message.emit(self.format(record))


# ---------------------------------------------------------------------------
def _rotate_logs(envp: dict, keep_days: int = 30) -> None:
    logs = Path(envp["TT2S_LOGS"])
    cutoff = time.time() - keep_days * 86400
    try:
        for p in logs.iterdir():
            if p.name.startswith("tt2s_") and p.suffix == ".log":
                try:
                    if p.stat().st_mtime < cutoff:
                        p.unlink()
                except OSError:
                    pass
    except OSError:
        pass


def init_app(av: list[str]) -> QApplication:
    qInstallMessageHandler(_qt_msg_handler)
    app = QApplication(av)
    app.setQuitOnLastWindowClosed(False)
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    app._heartbeat = QTimer()
    app._heartbeat.start(200)
    app._heartbeat.timeout.connect(lambda: None)
    return app


def init_logging(program: tt2s_gui.Base, envp: dict) -> None:
    _rotate_logs(envp)
    session  = f"tt2s_{os.getpid()}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log_path = Path(envp["TT2S_LOGS"]) / f"{session}.log"

    file_fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    gui_fmt = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S")

    fh = logging.FileHandler(log_path, encoding="utf-8", delay=False)
    fh.setFormatter(file_fmt)

    qt_h = _QtLogHandler()
    qt_h.setFormatter(gui_fmt)
    qt_h.message.connect(program.append_log)

    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    root.addHandler(fh)

    worker_log = logging.getLogger("worker")
    worker_log.setLevel(logging.INFO)
    worker_log.propagate = True
    worker_log.addHandler(qt_h)


def init_gui(cfg: config.configparser.ConfigParser) -> tt2s_gui.Base:
    s = cfg["settings"]
    return tt2s_gui.Base(
        video_id=s.get("youtube_video_id", ""),
        delay_per_char=s.get("delay_per_char", "0.03"),
        max_delay=s.get("max_delay", "2.0"),
    )


def init_hooks(
    program: tt2s_gui.Base,
    cfg: config.configparser.ConfigParser,
    envp: dict,
    on_quit: typing.Callable[[], None],
) -> None:
    _w: list[Optional[TTSWorker]] = [None]

    def start() -> None:
        try:
            delay = float(cfg["settings"].get("delay_per_char", "0.03"))
            max_d = float(cfg["settings"].get("max_delay", "2.0"))
        except ValueError as e:
            n = tt2s_gui.Notification("flag")
            n.errmsg = f"Invalid config: {e}"
            n.pop()
            return
        _w[0] = TTSWorker(
            config.extract_video_id(cfg["settings"].get("youtube_video_id", "")),
            delay,
            max_d,
        )
        _w[0].tray_notify.connect(program.notify_tray)
        _w[0].status_changed.connect(program.set_status)
        _w[0].warn_error.connect(on_warn)
        _w[0].fatal_error.connect(on_fatal)
        _w[0].start()
        program.set_running(True)

    def stop() -> None:
        if _w[0]:
            _w[0].stop()
            _w[0].wait(5000)
            _w[0] = None
        program.set_running(False)
        program.set_status("Stopped")

    def quit() -> None:
        stop()
        on_quit()

    def user_stop() -> None:
        stop()
        n = tt2s_gui.Notification("flag")
        n.errmsg = "Session stopped."
        n.pop()

    def save(video_id: str, delay: str, max_delay: str) -> None:
        cfg["settings"]["youtube_video_id"] = video_id
        cfg["settings"]["delay_per_char"] = delay
        cfg["settings"]["max_delay"] = max_delay
        n = tt2s_gui.Notification("flag")
        n.errmsg = "Settings applied for this session."
        n.pop()

    def on_warn(msg: str) -> None:
        n = tt2s_gui.Notification("warn")
        n.errmsg = msg
        n.on_stop = stop
        n.pop()

    def on_fatal(msg: str) -> None:
        stop()
        n = tt2s_gui.Notification("fatal")
        n.errmsg = msg
        n.pop()

    program.on_start = start
    program.on_stop  = user_stop
    program.on_quit  = quit
    program.on_save  = save


# ---------------------------------------------------------------------------
def main(
    ac: int | None = None,
    av: typing.List[str] | None = None,
    envp: typing.Dict[str, str] | None = None,
) -> int:
    av   = sys.argv         if av   is None else av
    envp = dict(os.environ) if envp is None else envp
    ac   = len(av)          if ac   is None else ac

    root = Path(av[0]).resolve().parent
    envp["TT2S_ROOT"] = str(root)
    envp["TT2S_LOGS"] = str(root / "logs")

    logging.getLogger().addHandler(logging.NullHandler())

    app     = init_app(av)
    cfg     = config.load(envp)
    program = init_gui(cfg)
    init_logging(program, envp)
    init_hooks(program, cfg, envp, on_quit=app.quit)

    program.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
