"""OCR 监测与日志页：顶部状态灯 + 按事件级别着色的日志流。"""

import time

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.worker import STATE_OFF, STATE_RUNNING, STATE_WAITING

LEVEL_COLORS = {
    "info": "#9fd6ff",
    "success": "#4ade80",
    "warn": "#fbbf24",
    "error": "#f87171",
    "buy": "#17e97e",
}
LEVEL_TAGS = {
    "info": "监测",
    "success": "完成",
    "warn": "注意",
    "error": "异常",
    "buy": "买入",
}

# 状态灯：文字、颜色
STATE_DISPLAY = {
    STATE_RUNNING: ("OCR 监测中", "#17e97e"),
    STATE_WAITING: ("等待游戏窗口", "#fbbf24"),
    STATE_OFF: ("监测未启动", "#f87171"),
}


class StatusLight(QLabel):
    def __init__(self):
        super().__init__("●  监测未启动")
        self.setObjectName("statusLight")
        font = QFont("Microsoft YaHei UI", 12)
        font.setBold(True)
        self.setFont(font)
        self.setAlignment(Qt.AlignCenter)
        self.set_state(STATE_OFF)

    def set_state(self, state: str) -> None:
        text, color = STATE_DISPLAY.get(state, STATE_DISPLAY[STATE_OFF])
        self.setText("●  " + text)
        self.setStyleSheet(
            """
            QLabel {
                color: %s;
                background: #0b120e;
                border: 2px solid %s;
                border-radius: 10px;
                padding: 8px 20px;
            }
            """
            % (color, color)
        )


class MonitorPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("pageRoot")
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        title = QLabel("OCR 监测")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        hint = QLabel("游戏窗口打开即自动开始监测；以下日志实时记录每一次比价与买入动作。")
        hint.setObjectName("pageHint")
        root.addWidget(hint)

        status_row = QHBoxLayout()
        self.status_light = StatusLight()
        status_row.addWidget(self.status_light)
        status_row.addStretch(1)
        self.launch_game_button = QPushButton("一键启动三角洲行动")
        self.launch_game_button.setObjectName("orangeButton")
        status_row.addWidget(self.launch_game_button)
        self.clear_button = QPushButton("清空日志")
        status_row.addWidget(self.clear_button)
        root.addLayout(status_row)

        self.log_list = QListWidget()
        self.log_list.setObjectName("logList")
        self.log_list.setSelectionMode(QListWidget.NoSelection)
        self.log_list.setAlternatingRowColors(False)
        font = QFont("Consolas", 10)
        self.log_list.setFont(font)
        root.addWidget(self.log_list, 1)

        self.count_label = QLabel("共 0 条")
        self.count_label.setObjectName("pageHint")
        root.addWidget(self.count_label)

        self.clear_button.clicked.connect(self.clear_logs)

    def set_state(self, state: str) -> None:
        self.status_light.set_state(state)

    def append_log(self, level: str, text: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        color = LEVEL_COLORS.get(level, LEVEL_COLORS["info"])
        tag = LEVEL_TAGS.get(level, "监测")
        item = QListWidgetItem("[%s] %s｜%s" % (stamp, tag, text))
        item.setForeground(QColor(color))
        self.log_list.addItem(item)
        # 只保留最近 200 条
        if self.log_list.count() > 200:
            self.log_list.takeItem(0)
        self.log_list.scrollToBottom()
        self.count_label.setText("共 %d 条" % self.log_list.count())

    def clear_logs(self) -> None:
        self.log_list.clear()
        self.count_label.setText("共 0 条")
