from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.device import AdbBackendError, list_devices


CALIBRATION_STEPS = {
    "price_tl": "校准①：价格识别区 左上角",
    "price_br": "校准②：价格识别区 右下角",
    "qty_min": "校准③：数量滑条 最左端（1 发）",
    "qty_max": "校准④：数量滑条 最右端（最大）",
    "buy_button": "校准⑤：购买按钮",
}

from core.device import AdbBackendError, list_devices


class SettingsPage(QWidget):
    calibration_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("pageRoot")
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(16)

        title = QLabel("设置")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        hint = QLabel(
            "运行平台可选电脑（模拟键鼠）或手机（ADB 控制，需要开启 USB 调试并安装 platform-tools）。"
            "浮层需要窗口关键字来定位游戏窗口。"
        )
        hint.setObjectName("pageHint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.platform_combo = QComboBox()
        self.platform_combo.addItem("电脑（本机游戏窗口）", "pc")
        self.platform_combo.addItem("手机（ADB 连接）", "mobile")

        self.loop_gap_spin = QSpinBox()
        self.loop_gap_spin.setRange(50, 5000)
        self.loop_gap_spin.setSingleStep(10)
        self.loop_gap_spin.setValue(120)
        self.loop_gap_spin.setSuffix(" ms")

        self.refresh_delay_spin = QSpinBox()
        self.refresh_delay_spin.setRange(50, 2000)
        self.refresh_delay_spin.setSingleStep(10)
        self.refresh_delay_spin.setValue(150)
        self.refresh_delay_spin.setSuffix(" ms")

        self.convertible_check = QCheckBox("物品默认可兑换")
        self.convertible_check.setChecked(True)
        self.half_coin_check = QCheckBox("使用哈夫币余额计算价格（仅电脑）")
        self.half_coin_check.setChecked(False)

        self.overlay_check = QCheckBox("显示日志浮层（电脑模式嵌在游戏窗口内，手机模式悬浮于屏幕右上角）")
        self.overlay_check.setChecked(True)

        self.window_keyword_edit = QLineEdit("三角洲行动")
        self.game_path_edit = QLineEdit()
        self.game_path_edit.setPlaceholderText("选择 DeltaForce.exe 或快捷方式")
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self._browse_game)

        self.adb_path_edit = QLineEdit()
        self.adb_path_edit.setPlaceholderText("adb.exe 路径，留空自动探测")
        adb_browse_button = QPushButton("浏览...")
        adb_browse_button.clicked.connect(self._browse_adb)

        self.adb_serial_combo = QComboBox()
        self.adb_refresh_button = QPushButton("刷新设备")
        self.adb_refresh_button.clicked.connect(self._refresh_devices)

        self.save_button = QPushButton("保存配置")
        self.save_button.setObjectName("primaryButton")

        rows = [
            ("运行平台", self.platform_combo, None),
            ("OCR 监听频率（每轮间隔）", self.loop_gap_spin, None),
            ("免费刷新等待（ESC 后停顿）", self.refresh_delay_spin, None),
            ("默认选项", self.convertible_check, None),
            ("价格模式", self.half_coin_check, None),
            ("日志浮层", self.overlay_check, None),
            ("窗口关键字", self.window_keyword_edit, None),
            ("游戏启动路径", self.game_path_edit, browse_button),
            ("ADB 路径", self.adb_path_edit, adb_browse_button),
            ("手机设备", self.adb_serial_combo, self.adb_refresh_button),
        ]
        for text, widget, extra in rows:
            row = QHBoxLayout()
            label = QLabel(text)
            label.setObjectName("settingsLabel")
            label.setMinimumWidth(220)
            row.addWidget(label)
            row.addWidget(widget, 1)
            if extra is not None:
                row.addWidget(extra)
            root.addLayout(row)

        # ---- 手机校准 ----
        calib_card = QFrame()
        calib_card.setObjectName("card")
        calib_layout = QVBoxLayout(calib_card)
        calib_layout.setContentsMargins(14, 10, 14, 10)
        calib_layout.setSpacing(8)
        calib_title = QLabel("手机坐标校准（手机模式必做）")
        calib_title.setObjectName("cardTitle")
        calib_layout.addWidget(calib_title)
        calib_hint = QLabel(
            "手机上打开交易行任一商品详情页（可兑换状态），点下面每个按钮并按提示在手机截图上取点。"
            "未校准时程序用的是电脑版坐标，手机上会点错位置、识别错价格。"
        )
        calib_hint.setObjectName("pageHint")
        calib_hint.setWordWrap(True)
        calib_layout.addWidget(calib_hint)

        calib_row1 = QHBoxLayout()
        calib_row2 = QHBoxLayout()
        self.calib_buttons = {}
        for index, key in enumerate(CALIBRATION_STEPS):
            button = QPushButton(CALIBRATION_STEPS[key])
            button.clicked.connect(lambda _=False, k=key: self.calibration_requested.emit(k))
            if index < 3:
                calib_row1.addWidget(button)
            else:
                calib_row2.addWidget(button)
        calib_row1.addStretch(1)
        calib_row2.addStretch(1)
        calib_layout.addLayout(calib_row1)
        calib_layout.addLayout(calib_row2)
        self.calib_status = QLabel("")
        self.calib_status.setObjectName("pageHint")
        calib_layout.addWidget(self.calib_status)
        root.addWidget(calib_card)

        root.addWidget(self.save_button)
        root.addStretch(1)

        self.platform_combo.currentIndexChanged.connect(self._on_platform_changed)
        self._apply_platform_visibility()

    def _on_platform_changed(self) -> None:
        self._apply_platform_visibility()

    def _apply_platform_visibility(self) -> None:
        mobile = self.platform_mode() == "mobile"
        self.adb_path_edit.setEnabled(mobile)
        self.adb_serial_combo.setEnabled(mobile)
        self.adb_refresh_button.setEnabled(mobile)

    def platform_mode(self) -> str:
        return self.platform_combo.currentData() or "pc"

    def _browse_game(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择三角洲行动程序",
            "",
            "程序 (*.exe);;快捷方式 (*.lnk);;所有文件 (*)",
        )
        if path:
            self.game_path_edit.setText(path)

    def _browse_adb(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 adb.exe", "", "程序 (*.exe);;所有文件 (*)"
        )
        if path:
            self.adb_path_edit.setText(path)
            self._refresh_devices()

    def _refresh_devices(self) -> None:
        self.adb_serial_combo.clear()
        try:
            devices = list_devices(self.adb_path_edit.text().strip() or None)
        except AdbBackendError as exc:
            QMessageBox.warning(self, "刷新设备", str(exc))
            return
        if not devices:
            QMessageBox.information(self, "刷新设备", "没有检测到已连接的安卓设备")
            return
        self.adb_serial_combo.addItems(devices)

    def set_calibration(self, calibration: dict) -> None:
        done = [key for key in CALIBRATION_STEPS if calibration.get(key)]
        total = len(CALIBRATION_STEPS)
        if done:
            self.calib_status.setText(
                "已标定 %d/%d：%s" % (len(done), total, "、".join(CALIBRATION_STEPS[k][-6:] for k in done))
            )
        else:
            self.calib_status.setText("尚未标定（手机模式无法正确识别价格与点击购买）")

    def set_config(self, config: dict) -> None:
        index = 0 if config.get("platform_mode", "pc") == "pc" else 1
        self.platform_combo.setCurrentIndex(index)
        self.loop_gap_spin.setValue(int(config.get("loop_gap", 120)))
        self.refresh_delay_spin.setValue(int(config.get("refresh_delay", 150)))
        self.convertible_check.setChecked(bool(config.get("default_convertible", True)))
        self.half_coin_check.setChecked(bool(config.get("half_coin_mode", False)))
        self.overlay_check.setChecked(bool(config.get("overlay_enabled", True)))
        self.window_keyword_edit.setText(str(config.get("window_keyword", "三角洲行动")))
        self.game_path_edit.setText(str(config.get("game_path", "")))
        self.adb_path_edit.setText(str(config.get("adb_path", "")))
        serial = str(config.get("adb_serial", ""))
        if serial:
            self.adb_serial_combo.addItem(serial)
            self.adb_serial_combo.setCurrentText(serial)
        self._apply_platform_visibility()

    def to_config(self) -> dict:
        return {
            "platform_mode": self.platform_mode(),
            "loop_gap": self.loop_gap_spin.value(),
            "refresh_delay": self.refresh_delay_spin.value(),
            "default_convertible": self.convertible_check.isChecked(),
            "half_coin_mode": self.half_coin_check.isChecked(),
            "overlay_enabled": self.overlay_check.isChecked(),
            "window_keyword": self.window_keyword_edit.text().strip(),
            "game_path": self.game_path_edit.text().strip(),
            "adb_path": self.adb_path_edit.text().strip(),
            "adb_serial": self.adb_serial_combo.currentText().strip(),
        }
