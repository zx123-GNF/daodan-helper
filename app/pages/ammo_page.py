"""目标子弹页：全部官方可交易弹种 + 三档价格 + 最大买入数量。"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.ammo_db import all_ammo, tier_color, tier_label
from core.models import BulletTask


def tasks_from_ammo(price_overrides: dict = None) -> list:
    """由弹药库生成任务列表，price_overrides 保留用户改过的价格（按名称）。"""
    price_overrides = price_overrides or {}
    tasks = []
    for item in all_ammo():
        saved = price_overrides.get(item["name"], {})
        buy_price = int(saved.get("buy_price", 0) or 0) or item["ref_price"]
        high = int(saved.get("high_tier", 0) or 0) or round(buy_price * 1.5)
        low = int(saved.get("low_tier", 0) or 0) or (buy_price + high) // 2
        tasks.append(
            BulletTask(
                name=item["name"],
                caliber=item["caliber"],
                tier=item["tier"],
                buy_price=buy_price,
                low_tier=low,
                high_tier=high,
                buy_times=int(saved.get("buy_times", 10)),
                max_quantity=int(saved.get("max_quantity", 200)),
                position=list(saved.get("position", [])),
                enabled=bool(saved.get("enabled", False)),
                convertible=bool(saved.get("convertible", True)),
            )
        )
    return tasks


class AmmoPage(QWidget):
    test_ocr_requested = pyqtSignal(int)
    capture_requested = pyqtSignal(str)
    tasks_changed = pyqtSignal()
    message = pyqtSignal(str)

    COLUMNS = [
        "启用",
        "子弹名称",
        "等级",
        "买价",
        "低档",
        "高档",
        "上限",
        "次数",
        "位置",
    ]

    COL_NAME = 1
    COL_TIER = 2

    def __init__(self, tasks: list):
        super().__init__()
        self.setObjectName("pageRoot")
        self.tasks = tasks
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        # ---- 顶部横幅 ----
        banner = QWidget()
        banner.setObjectName("heroBanner")
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(14, 10, 14, 10)
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        hero_title = QLabel("目标子弹库")
        hero_title.setObjectName("heroTitle")
        hero_sub = QLabel(
            "勾选要蹲的子弹并设好三档价格 → 记录位置 → 打开游戏窗口即自动监测买入"
        )
        hero_sub.setObjectName("heroSub")
        text_col.addWidget(hero_title)
        text_col.addWidget(hero_sub)
        banner_layout.addLayout(text_col)
        banner_layout.addStretch(1)

        self.auto_check_btn = QPushButton("自动监测：开")
        self.auto_check_btn.setObjectName("primaryButton")
        self.auto_check_btn.setCheckable(True)
        self.auto_check_btn.setChecked(True)
        self.auto_check_btn.setFixedHeight(40)
        banner_layout.addWidget(self.auto_check_btn)
        root.addWidget(banner)

        # ---- 过滤与操作条 ----
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("筛选："))
        self.tier_filter = QComboBox()
        self.tier_filter.addItems(["全部等级", "T3/T4", "T1", "T2", "T3", "T4", "T5", "T0肉伤"])
        self.caliber_filter = QComboBox()
        self.caliber_filter.addItems(["全部口径"] + sorted({t.caliber for t in self.tasks}))
        filter_row.addWidget(self.tier_filter)
        filter_row.addWidget(self.caliber_filter)
        filter_row.addStretch(1)

        self.capture_button = QPushButton("记录选中子弹位置")
        self.test_button = QPushButton("测试 OCR 识别")
        self.common_button = QPushButton("只看 T3/T4 常用")
        filter_row.addWidget(self.common_button)
        filter_row.addWidget(self.capture_button)
        filter_row.addWidget(self.test_button)
        root.addLayout(filter_row)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("pageHint")
        root.addWidget(self.summary_label)

        # ---- 弹种表格 ----
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
        )
        self.table.verticalHeader().setDefaultSectionSize(28)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_NAME, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 64)
        for col in range(2, len(self.COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        root.addWidget(self.table, 1)

        self.tier_filter.currentIndexChanged.connect(lambda _=None: self.refresh_table())
        self.caliber_filter.currentIndexChanged.connect(lambda _=None: self.refresh_table())
        self.common_button.clicked.connect(self._filter_common)
        self.capture_button.clicked.connect(self.capture_position)
        self.test_button.clicked.connect(self.test_ocr)
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.cellClicked.connect(self._on_cell_clicked)

        self.refresh_table()

    # ---------- 表格 ----------

    def _visible_tasks(self) -> list:
        tier_text = self.tier_filter.currentText()
        caliber = self.caliber_filter.currentText()
        result = []
        for task in self.tasks:
            if tier_text == "T0肉伤":
                if task.tier != 0:
                    continue
            elif tier_text == "T3/T4":
                if task.tier not in (3, 4):
                    continue
            elif tier_text not in ("全部等级", "T%d" % task.tier):
                continue
            if caliber != "全部口径" and task.caliber != caliber:
                continue
            result.append(task)
        return result

    def refresh_table(self) -> None:
        self._loading = True
        # 保留当前选中（表格重建会清空 currentRow，导致后续操作找不到行）
        current_task = self._task_at_row(self.table.currentRow())
        visible = self._visible_tasks()
        self.table.setRowCount(0)
        self.table.setRowCount(len(visible))
        enabled_count = sum(1 for t in self.tasks if t.enabled)
        self.summary_label.setText(
            "弹种库共 %d 种（全部可交易）｜已启用 %d 种｜等级色：绿=T1/2 蓝=T3 紫=T4 橙=T5"
            % (len(self.tasks), enabled_count)
        )
        for row, task in enumerate(visible):
            enabled = QTableWidgetItem()
            enabled.setCheckState(Qt.Checked if task.enabled else Qt.Unchecked)
            # 禁用原生勾选交互，切换统一由 _on_cell_clicked 的整格点击处理
            enabled.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            enabled.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, enabled)

            name_item = QTableWidgetItem(task.name)
            if task.enabled:
                name_item.setForeground(QBrush(QColor("#17e97e")))
            self.table.setItem(row, self.COL_NAME, name_item)

            tier_item = QTableWidgetItem(tier_label(task.tier))
            tier_item.setForeground(QBrush(QColor(tier_color(task.tier))))
            font = QFont()
            font.setBold(True)
            tier_item.setFont(font)
            tier_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, self.COL_TIER, tier_item)

            self.table.setItem(row, 3, QTableWidgetItem(str(task.buy_price)))
            self.table.setItem(row, 4, QTableWidgetItem(str(task.low_tier)))
            self.table.setItem(row, 5, QTableWidgetItem(str(task.high_tier)))
            self.table.setItem(row, 6, QTableWidgetItem(str(task.max_quantity)))
            self.table.setItem(row, 7, QTableWidgetItem(str(task.buy_times)))

            if task.position:
                position = "%.0f%%, %.0f%%" % (task.position[0] * 100, task.position[1] * 100)
            else:
                position = "未记录"
            pos_item = QTableWidgetItem(position)
            if not task.position:
                pos_item.setForeground(QBrush(QColor("#6b7d6f")))
            self.table.setItem(row, 8, pos_item)
        # 恢复刷新前的选中行
        if current_task is not None:
            for row, task in enumerate(visible):
                if task is current_task or task.name == current_task.name:
                    self.table.selectRow(row)
                    break
        self._loading = False

    def _on_cell_changed(self, row: int, column: int) -> None:
        if self._loading:
            return
        task = self._task_at_row(row)
        item = self.table.item(row, column)
        if task is None or item is None:
            return

        def as_int(value, default):
            try:
                return int(str(value).replace(",", "").strip())
            except ValueError:
                return default

        if column == 0:
            # 勾选由 _on_cell_clicked 统一处理，这里只同步（防止 cellChanged 提前触发翻回）
            return
        if column == 3:
            task.buy_price = as_int(item.text(), task.buy_price)
        elif column == 4:
            task.low_tier = as_int(item.text(), task.low_tier)
        elif column == 5:
            task.high_tier = as_int(item.text(), task.high_tier)
        elif column == 6:
            task.max_quantity = max(1, min(200, as_int(item.text(), task.max_quantity)))
        elif column == 7:
            task.buy_times = as_int(item.text(), task.buy_times)
        if column == self.COL_NAME:
            self.refresh_table()
        self.tasks_changed.emit()

    def _task_at_row(self, row: int):
        if row < 0:
            return None
        visible = self._visible_tasks()
        if row >= len(visible):
            return None
        return visible[row]

    def selected_row(self) -> int:
        return self.table.currentRow()

    def _on_cell_clicked(self, row: int, column: int) -> None:
        self.table.selectRow(row)
        self.table.setCurrentCell(row, column)
        # 点击"启用"列任意位置都切换勾选，不用瞄准小复选框
        if column == 0 and not self._loading:
            task = self._task_at_row(row)
            if task is not None:
                task.enabled = not task.enabled
                self.message.emit("%s 已%s" % (task.name, "启用" if task.enabled else "停用"))
                self.refresh_table()
                self.tasks_changed.emit()

    def _filter_common(self) -> None:
        index = self.tier_filter.findText("T3/T4")
        if index >= 0:
            self.tier_filter.setCurrentIndex(index)

    def set_position(self, task_name: str, position: list) -> None:
        task = next((t for t in self.tasks if t.name == task_name), None)
        if task is None:
            self.message.emit("错误：未找到任务 %s，位置未保存" % task_name)
            return
        task.position = position
        try:
            self.refresh_table()
        except Exception as exc:
            self.message.emit("错误：位置已保存但界面刷新失败：%s" % exc)
        else:
            self.message.emit(
                "已记录 %s 位置：%.0f%%, %.0f%%" % (task.name, position[0] * 100, position[1] * 100)
            )
        self.tasks_changed.emit()

    def capture_position(self) -> None:
        task = self._task_at_row(self.selected_row())
        if task is None:
            self.message.emit("请先在表格中点选一颗子弹（点它的名字），再记录位置")
            return
        self.capture_requested.emit(task.name)

    def test_ocr(self) -> None:
        task = self._task_at_row(self.selected_row())
        if task is None:
            self.message.emit("请先在表格中点选一颗子弹，再测试 OCR")
            return
        self.test_ocr_requested.emit(self._visible_tasks().index(task))
