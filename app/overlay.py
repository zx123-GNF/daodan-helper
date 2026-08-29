"""BetterGI 风格的游戏内日志浮层。

参考 BetterGI 的做法：小字号等宽字体、按级别着色的日志行、半透明底、
完全点击穿透（鼠标事件直接穿到游戏里）。用 QPainter 自绘而不是
QPlainTextEdit，才能做到 10px 小字 + 每行独立颜色 + 极低渲染开销。
"""

import ctypes
import time

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter
from PyQt5.QtWidgets import QApplication, QWidget

LEVEL_COLORS = {
    "info": "#9fd6ff",
    "success": "#4ade80",
    "warn": "#fbbf24",
    "error": "#f87171",
    "buy": "#22d3ee",
}

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000


class GameLogOverlay(QWidget):
    MAX_LINES = 12
    PADDING = 8
    LINE_HEIGHT = 15
    FONT_SIZE = 9

    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._lines = []  # [(timestamp, level, text)]
        self._width = 420
        self.setWindowTitle("捣蛋助手浮层")

    def add_line(self, level: str, text: str) -> None:
        self._lines.append((time.strftime("%H:%M:%S"), level or "info", text))
        if len(self._lines) > self.MAX_LINES:
            self._lines = self._lines[-self.MAX_LINES :]
        self._resize_to_lines()
        if self.isVisible():
            self.update()
        else:
            self.show()
            self.raise_()

    def _resize_to_lines(self) -> None:
        count = max(1, len(self._lines))
        height = self.PADDING * 2 + count * self.LINE_HEIGHT
        geo = self.geometry()
        self.setGeometry(geo.x(), geo.y(), self._width, height)

    def clear_lines(self) -> None:
        self._lines = []
        self.hide()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(6, 10, 18, 160))
        painter.drawRoundedRect(self.rect(), 6, 6)
        painter.setPen(QColor(34, 211, 238, 200))
        painter.drawLine(3, 6, 3, self.height() - 6)

        font = QFont("Consolas", self.FONT_SIZE)
        font.setStyleStrategy(QFont.NoAntialias)
        painter.setFont(font)
        y = self.PADDING + self.LINE_HEIGHT - 3
        for stamp, level, text in self._lines:
            painter.setPen(QColor(90, 105, 125, 220))
            painter.drawText(self.PADDING + 6, y, stamp)
            painter.setPen(QColor(LEVEL_COLORS.get(level, LEVEL_COLORS["info"])))
            painter.drawText(self.PADDING + 62, y, text)
            y += self.LINE_HEIGHT
        painter.end()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        try:
            hwnd = int(self.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
            )
        except Exception:
            pass

    def place_on(self, rect) -> None:
        """贴在游戏窗口客户区左上角（PC 模式）。"""
        left, top, width, height = rect
        self._width = max(360, min(560, int(width * 0.34)))
        line_h = max(13, int(height * 0.011))
        self.LINE_HEIGHT = line_h
        count = max(1, len(self._lines))
        self.setGeometry(
            left + 14,
            top + 14,
            self._width,
            self.PADDING * 2 + count * line_h,
        )
        self.show()
        self.raise_()

    def place_floating(self) -> None:
        """悬浮在电脑屏幕右上角（手机模式，游戏画面在手机上）。"""
        screen = QApplication.primaryScreen().availableGeometry()
        self._width = 420
        self.LINE_HEIGHT = 15
        count = max(1, len(self._lines))
        self.setGeometry(
            screen.right() - self._width - 12,
            screen.top() + 12,
            self._width,
            self.PADDING * 2 + count * self.LINE_HEIGHT,
        )
        self.show()
        self.raise_()
