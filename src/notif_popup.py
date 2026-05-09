"""
Standalone notification popup — launched as a child process by the main app.

Usage:
    python notif_popup.py <level> <message>

    level   : "flag" | "warn" | "fatal"
    message : error text (may be empty string)

Exit codes:
    0  OK / dismiss
    1  Kill
    2  Continue
    3  Restart
"""
import sys

_TITLES = {"flag": "Notice", "warn": "Warning", "fatal": "Fatal Error"}

OK       = 0
STOP     = 1
CONTINUE = 2

_STYLE = """
QWidget {
    background: #ffffff;
    color: #000000;
    border: 1px solid #cccccc;
    border-radius: 8px;
}
QLabel { border: none; }
QPushButton {
    border: 1px solid #aaaaaa;
    border-radius: 4px;
    padding: 5px 16px;
    font-size: 11px;
    font-weight: bold;
    background: #f0f0f0;
    color: #000000;
}
QPushButton:hover { background: #e0e0e0; }
QPushButton#kill  { background: #ffd6d6; color: #cc0000; border-color: #cc0000; }
QPushButton#kill:hover  { background: #ffbbbb; }
QPushButton#restart { background: #d6e8ff; color: #004acc; border-color: #004acc; }
QPushButton#restart:hover { background: #bbccff; }
"""

try:
    from PySide6.QtCore import (
        QEasingCurve,
        QParallelAnimationGroup,
        QPoint,
        QPropertyAnimation,
        Qt,
    )
    from PySide6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    sys.exit(OK)


def _add_btn(layout, obj_name: str, label: str, code: int, app: QApplication) -> None:
    b = QPushButton(label)
    b.setObjectName(obj_name)
    b.clicked.connect(lambda: app.exit(code))
    layout.addWidget(b)


def main() -> int:
    if len(sys.argv) < 3:
        return OK

    level   = sys.argv[1]
    message = sys.argv[2]

    if level not in _TITLES:
        return OK

    app = QApplication(sys.argv)

    win = QWidget()
    win.setWindowFlags(
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool
    )
    win.setStyleSheet(_STYLE)
    win.setMinimumWidth(320)

    lay = QVBoxLayout(win)
    lay.setContentsMargins(16, 12, 16, 12)
    lay.setSpacing(8)

    prog = QLabel("tdibam_t2s")
    prog.setStyleSheet("font-size:9px; color:#888888; letter-spacing:1px; border:none;")
    lay.addWidget(prog)

    hdr = QLabel(f"<b>{_TITLES[level]}</b>")
    hdr.setStyleSheet("font-size:14px; color:#000000; border:none;")
    lay.addWidget(hdr)

    if message:
        body = QLabel(message)
        body.setWordWrap(True)
        body.setStyleSheet("font-size:11px; color:#000000; border:none;")
        lay.addWidget(body)

    btns = QHBoxLayout()
    btns.setSpacing(6)
    if level == "warn":
        _add_btn(btns, "stop", "Stop",     STOP,     app)
        _add_btn(btns, "cont", "Continue", CONTINUE, app)
    else:
        _add_btn(btns, "ok", "OK", OK, app)
    lay.addLayout(btns)

    win.adjustSize()
    screen = app.primaryScreen().availableGeometry()
    x = screen.center().x() - win.width() // 2
    y = screen.center().y() - win.height() // 2

    offset = 36
    win.setWindowOpacity(0.0)
    win.move(x, y + offset)
    win.show()
    win.raise_()
    win.activateWindow()

    pos_anim = QPropertyAnimation(win, b"pos")
    pos_anim.setDuration(260)
    pos_anim.setStartValue(QPoint(x, y + offset))
    pos_anim.setEndValue(QPoint(x, y))
    pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    fade = QPropertyAnimation(win, b"windowOpacity")
    fade.setDuration(200)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.Type.OutQuad)

    grp = QParallelAnimationGroup(win)
    grp.addAnimation(pos_anim)
    grp.addAnimation(fade)
    grp.start()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
