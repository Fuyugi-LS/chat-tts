"""Pure GUI layer — no business logic, no config I/O, no worker knowledge.

Wire behavior from outside:
    win = Base(initial_values)
    win.on_start = callable
    win.on_stop  = callable
    win.on_save  = callable(video_id, delay, max_delay)
"""

import os
import sys
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QProcess, Qt, Signal
from PySide6.QtGui import QAction, QFont, QIcon, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QStyle,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

_FROZEN = getattr(sys, "frozen", False)

if _FROZEN:
    _ICON      = str(Path(sys.executable).parent / "icon.ico")
    _POPUP_CMD = [str(Path(sys.executable).parent / "notif_popup.exe")]
else:
    _ICON      = str(Path(__file__).parent.parent / "assets" / "icon.ico")
    _POPUP_CMD = [sys.executable, str(Path(__file__).parent / "notif_popup.py")]

_LEVELS = ("flag", "warn", "fatal")

# Exit codes that notif_popup.py returns
_EXIT_OK       = 0
_EXIT_STOP     = 1
_EXIT_CONTINUE = 2

_active: set["Notification"] = set()


class Notification:
    """
    Launches notif_popup.py as a child process and maps its exit code
    back to on_kill / on_continue / on_restart callbacks.

    Levels : "flag"  → info        (OK)
             "warn"  → warning      (Kill / Continue / Restart)
             "fatal" → critical     (OK)

    Hooks  : .on_kill      default → QApplication.quit
             .on_continue  default → dismiss
             .on_restart   default → dismiss

    Example:
        n = Notification("warn")
        n.errmsg = "Live not found"
        n.on_restart = worker.restart
        n.pop()
    """

    def __init__(self, level: str) -> None:
        if level not in _LEVELS:
            raise ValueError(f"level must be one of {_LEVELS}")
        self.level = level
        self.errmsg: str = ""
        self.on_stop: Optional[Callable] = None
        self.on_continue: Optional[Callable] = None
        self._proc: Optional[QProcess] = None

    def pop(self) -> None:
        self.destroy()
        _active.add(self)
        self._proc = QProcess()
        self._proc.finished.connect(self._on_finished)
        self._proc.start(_POPUP_CMD[0], _POPUP_CMD[1:] + [self.level, self.errmsg])

    def destroy(self) -> None:
        _active.discard(self)
        if self._proc is not None:
            if self._proc.state() != QProcess.ProcessState.NotRunning:
                self._proc.kill()
                self._proc.waitForFinished(500)
            self._proc = None

    def _on_finished(self, code: int, _status) -> None:
        _active.discard(self)
        self._proc = None
        if code == _EXIT_STOP:
            if self.on_stop:
                self.on_stop()
        elif code == _EXIT_CONTINUE:
            if self.on_continue:
                self.on_continue()


class Base(QMainWindow):
    """
    UI only.  Set hook properties before show():

        win.on_start = callable()
        win.on_stop  = callable()
        win.on_quit  = callable()
        win.on_save  = callable(video_id: str, delay: str, max_delay: str)
    """

    on_start: Optional[Callable[[], None]] = None
    on_stop:  Optional[Callable[[], None]] = None
    on_quit:  Optional[Callable[[], None]] = None
    on_save:  Optional[Callable[[str, str, str], None]] = None

    def __init__(
        self,
        video_id: str = "",
        delay_per_char: str = "0.03",
        max_delay: str = "2.0",
    ) -> None:
        super().__init__()
        self._build_tray()
        self._build_ui(video_id, delay_per_char, max_delay)

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(
            QIcon(_ICON) if os.path.exists(_ICON)
            else self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)
        )
        menu = QMenu()
        show_act = QAction("Show", self)
        show_act.triggered.connect(self._restore)
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(self._do_quit)
        menu.addAction(show_act)
        menu.addSeparator()
        menu.addAction(quit_act)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_click)
        self.tray.show()

    def _on_tray_click(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._restore()

    def _restore(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _build_ui(self, video_id: str, delay: str, max_delay: str) -> None:
        self.setWindowTitle("tdibam_t2s")
        self.setMinimumSize(600, 480)

        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        grp_cfg = QGroupBox("Config")
        gl = QVBoxLayout(grp_cfg)
        gl.addWidget(QLabel("YouTube Video ID / URL"))
        self.e_vid = QLineEdit(video_id)
        gl.addWidget(self.e_vid)
        hl = QHBoxLayout()
        hl.addWidget(QLabel("Delay per char (sec)"))
        self.e_delay = QLineEdit(delay)
        self.e_delay.setFixedWidth(72)
        hl.addWidget(self.e_delay)
        hl.addSpacing(20)
        hl.addWidget(QLabel("Max delay (sec)"))
        self.e_max = QLineEdit(max_delay)
        self.e_max.setFixedWidth(72)
        hl.addWidget(self.e_max)
        hl.addStretch()
        btn_save = QPushButton("Save")
        btn_save.setFixedWidth(80)
        btn_save.clicked.connect(self._clicked_save)
        hl.addWidget(btn_save)
        gl.addLayout(hl)
        lay.addWidget(grp_cfg)

        grp_ctrl = QGroupBox("Controls")
        cl = QHBoxLayout(grp_ctrl)
        self.btn_start = QPushButton("Start")
        self.btn_start.setFixedWidth(80)
        self.btn_start.clicked.connect(self._clicked_start)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setFixedWidth(80)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._clicked_stop)
        self.lbl_status = QLabel("Idle")
        cl.addWidget(self.btn_start)
        cl.addWidget(self.btn_stop)
        cl.addSpacing(16)
        cl.addWidget(QLabel("Status:"))
        cl.addWidget(self.lbl_status)
        cl.addStretch()
        lay.addWidget(grp_ctrl)

        grp_log = QGroupBox("Log")
        ll = QVBoxLayout(grp_log)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 9))
        self.log_view.setStyleSheet(
            "QTextEdit { background:#1e1e1e; color:#d4d4d4; border:none; }"
        )
        self.log_view.document().setMaximumBlockCount(500)
        ll.addWidget(self.log_view)
        lay.addWidget(grp_log, stretch=1)

    def _clicked_start(self) -> None:
        if self.on_start:
            self.on_start()

    def _clicked_stop(self) -> None:
        if self.on_stop:
            self.on_stop()

    def _clicked_save(self) -> None:
        if self.on_save:
            self.on_save(
                self.e_vid.text().strip(),
                self.e_delay.text().strip(),
                self.e_max.text().strip(),
            )

    def set_running(self, running: bool) -> None:
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    def set_status(self, text: str) -> None:
        self.lbl_status.setText(text)

    def append_log(self, line: str) -> None:
        self.log_view.append(line)
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    def notify_tray(self, title: str, body: str) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.showMessage(
                title, body, QSystemTrayIcon.MessageIcon.Information, 3000
            )

    def _do_quit(self) -> None:
        if self.on_quit:
            self.on_quit()
        else:
            QApplication.instance().quit()

    def closeEvent(self, event) -> None:
        event.ignore()
        self._do_quit()

    @property
    def current_video_id(self) -> str:
        return self.e_vid.text().strip()

    @property
    def current_delay(self) -> str:
        return self.e_delay.text().strip()

    @property
    def current_max_delay(self) -> str:
        return self.e_max.text().strip()
