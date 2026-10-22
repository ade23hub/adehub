# pyright: reportMissingImports=false
import sys
from pathlib import Path

from PySide6.QtCore import (
    QDir,
    QEasingCurve,
    QFile,
    QPoint,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    Qt,
    QTimer,
)
from PySide6.QtGui import QFont
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QGraphicsOpacityEffect, QLabel, QProgressBar

import paths

ROOT = paths.resource_dir()
UI_FILE = ROOT / "GoPiliotsplashscreen.ui"

STAGES = [
    (30, "Loading"),
    (60, "Preparing workspace"),
    (90, "Starting GOPILOT"),
    (100, "Ready"),
]


class Splash:
    def __init__(self):
        loader = QUiLoader()
        loader.setWorkingDirectory(QDir(str(ROOT)))
        ui_file = QFile(str(UI_FILE))
        ui_file.open(QFile.OpenModeFlag.ReadOnly)
        self.widget = loader.load(ui_file)
        ui_file.close()
        self.widget.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)

        self.background = self.widget.findChild(QLabel, "label")
        self.logo = self.widget.findChild(QLabel, "LOGO")
        self.bar = self.widget.findChild(QProgressBar, "progressBar")
        self.status = self.widget.findChild(QLabel, "loadinglbl")

        self._animate_background()
        self._animate_logo()
        self.bar.setValue(0)
        self.progress = 0
        self.dots = 0
        self.stage_text = STAGES[0][1]

    def _animate_background(self):
        # The label is larger than the window, so it can drift without exposing edges.
        home = self.background.pos()
        drift = QPropertyAnimation(self.background, b"pos")
        drift.setDuration(6000)
        drift.setStartValue(home)
        drift.setEndValue(home + QPoint(40, 25))
        drift.setEasingCurve(QEasingCurve.Type.InOutSine)
        back = QPropertyAnimation(self.background, b"pos")
        back.setDuration(6000)
        back.setStartValue(home + QPoint(40, 25))
        back.setEndValue(home)
        back.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.bg_anim = QSequentialAnimationGroup()
        self.bg_anim.addAnimation(drift)
        self.bg_anim.addAnimation(back)
        self.bg_anim.setLoopCount(-1)
        self.bg_anim.start()

    def _animate_logo(self):
        effect = QGraphicsOpacityEffect(self.logo)
        self.logo.setGraphicsEffect(effect)
        fade_out = QPropertyAnimation(effect, b"opacity")
        fade_out.setDuration(1200)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.6)
        fade_in = QPropertyAnimation(effect, b"opacity")
        fade_in.setDuration(1200)
        fade_in.setStartValue(0.6)
        fade_in.setEndValue(1.0)
        self.logo_anim = QSequentialAnimationGroup()
        self.logo_anim.addAnimation(fade_out)
        self.logo_anim.addAnimation(fade_in)
        self.logo_anim.setLoopCount(-1)
        self.logo_anim.start()

    def _tick_dots(self):
        self.dots = (self.dots + 1) % 4
        self._set_status(self.stage_text + "." * self.dots)

    def _set_status(self, text):
        self.status.setText(
            '<p align="center"><span style="font-size:16pt; font-weight:600; '
            f'color:#8a5cff;">{text}</span></p>'
        )

    def run(self, on_finished, step_ms=30):
        self.widget.show()
        self.dot_timer = QTimer()
        self.dot_timer.timeout.connect(self._tick_dots)
        self.dot_timer.start(350)

        def step():
            self.progress += 1
            self.bar.setValue(self.progress)
            for limit, text in STAGES:
                if self.progress <= limit:
                    self.stage_text = text
                    break
            if self.progress >= 100:
                self.timer.stop()
                self.dot_timer.stop()
                self._set_status("Ready")
                QTimer.singleShot(250, lambda: self._finish(on_finished))

        self.timer = QTimer()
        self.timer.timeout.connect(step)
        self.timer.start(step_ms)

    def _finish(self, on_finished):
        self.bg_anim.stop()
        self.logo_anim.stop()
        on_finished()
        self.widget.close()


def main():
    from GOPILOT import APP_NAME, GoPilotWindow

    paths.set_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Segoe UI", 10))

    splash = Splash()
    holder = {}

    def launch():
        holder["window"] = GoPilotWindow()
        holder["window"].show()

    splash.run(launch)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
