import os
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.overlay import GameLogOverlay
from app.pages.ammo_page import AmmoPage
from app.pages.monitor_page import MonitorPage
from app.pages.settings_page import SettingsPage
from app.theme import build_qss
from core.buy_bot import BuyBot
from core.config_manager import (
    config_from_tasks,
    load_config,
    merged_tasks_with_ammo,
    save_config,
)
from core.device import AdbBackend, AdbBackendError, PcBackend
from core.ocr import WindowsOcr
from core import window_finder
from core.worker import (
    STATE_OFF,
    STATE_RUNNING,
    STATE_WAITING,
    OcrTestThread,
    Worker,
)

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "img"


class _PickView(QGraphicsView):
    """截图取点视图：点击处画绿圈标记并回报相对坐标，反馈可见。"""

    picked = pyqtSignal(float, float)
    clicked = pyqtSignal()  # 调试：任何点击都上报，用于确认事件可达

    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self._pix_w = pixmap.width()
        self._pix_h = pixmap.height()
        scene = QGraphicsScene(self)
        scene.addPixmap(pixmap)
        self.setScene(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setCursor(Qt.CrossCursor)
        self._marker = None
        # 视口贴齐图片实际大小
        self.setFixedSize(pixmap.size())
        self.setSceneRect(0, 0, self._pix_w, self._pix_h)
        self.fitInView(0, 0, self._pix_w, self._pix_h, Qt.KeepAspectRatio)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        scene_pos = self.mapToScene(event.pos())
        x = min(1.0, max(0.0, scene_pos.x() / max(1, self._pix_w)))
        y = min(1.0, max(0.0, scene_pos.y() / max(1, self._pix_h)))
        self._draw_marker(scene_pos)
        self.picked.emit(x, y)

    def _draw_marker(self, scene_pos) -> None:
        scene = self.scene()
        if self._marker is not None:
            scene.removeItem(self._marker)
        radius = max(14, self._pix_w // 50)
        self._marker = scene.addEllipse(
            scene_pos.x() - radius,
            scene_pos.y() - radius,
            radius * 2,
            radius * 2,
            QPen(QColor("#17e97e"), max(3, radius // 5)),
        )


class PositionPickDialog(QDialog):
    """显示手机截图，点击图片选点 -> 确定，记录该位置的相对坐标。"""

    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.setWindowTitle("手机截图取点")
        self.setModal(True)
        self.fraction = None

        import io

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue())

        screen = self.screen().availableGeometry() if self.screen() else None
        # 顶部预留提示+按钮的高度，图片区域不超过剩余空间
        max_w = int(screen.width() * 0.7) if screen else 900
        max_h = int(screen.height() * 0.75) - 150 if screen else 500
        max_h = max(300, max_h)
        scaled = pixmap.scaled(
            max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        layout = QVBoxLayout(self)
        # 提示与按钮放顶部：竖屏截图很高，放底部会被顶出屏幕外
        self._hint = QLabel("① 点击图片上的子弹位置（可重复点选）→ ② 点右下“确定保存”")
        self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setWordWrap(True)
        layout.addWidget(self._hint)

        buttons = QHBoxLayout()
        self._ok_button = QPushButton("确定保存")
        self._ok_button.setObjectName("primaryButton")
        center_button = QPushButton("使用图片中心")
        center_button.clicked.connect(self._use_center)
        cancel_button = QPushButton("取消")
        self._ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(center_button)
        buttons.addStretch(1)
        buttons.addWidget(cancel_button)
        buttons.addWidget(self._ok_button)
        layout.addLayout(buttons)

        self._view = _PickView(scaled)
        layout.addWidget(self._view, 1)

        self._view.picked.connect(self._on_picked)
        self._view.clicked.connect(self._on_click_seen)

    def _on_click_seen(self) -> None:
        self._hint.setText("收到点击，绿圈即所选位置（可重复点选微调）")

    def _use_center(self) -> None:
        self.fraction = [0.5, 0.5]
        self._hint.setText("已选位置：50%, 50%（图片中心）→ 点“确定保存”")

    def _on_picked(self, x: float, y: float) -> None:
        self.fraction = [x, y]
        self._hint.setText("已选位置：%.0f%%, %.0f%%（绿圈处，可重新点选微调）→ 点“确定保存”" % (x * 100, y * 100))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("捣蛋助手 - 三角洲交易行")
        self.resize(660, 520)
        self.setMinimumSize(540, 420)
        icon_path = ASSETS_DIR / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.config = load_config()
        tasks = merged_tasks_with_ammo(self.config)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self._build_sidebar())
        self.splitter.addWidget(self._build_main_area(tasks))
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setChildrenCollapsible(False)
        sidebar_width = max(120, int(self.config.get("sidebar_width", 140)))
        sidebar_width = min(sidebar_width, max(120, self.width() // 3))
        self.splitter.setSizes([sidebar_width, self.width() - sidebar_width])
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        root_layout.addWidget(self.splitter)

        # ---------- 运行时 ----------
        self.ocr = WindowsOcr()
        self.buybot = None
        self.worker = None
        self._runtime_key = None
        self._rebuild_runtime()

        self.ocr_test_thread = None

        # ---------- 日志浮层 ----------
        self.overlay = GameLogOverlay()
        self._ratio_ok = None
        self._game_hwnd = None
        self.overlay_timer = QTimer(self)
        self.overlay_timer.timeout.connect(self.update_overlay)
        self.overlay_timer.start(500)

        # ---------- 信号 ----------
        self.ammo_page.test_ocr_requested.connect(self.test_ocr)
        self.ammo_page.capture_requested.connect(self.capture_position)
        self.ammo_page.tasks_changed.connect(self.on_tasks_changed)
        self.ammo_page.message.connect(self._on_message)
        self.ammo_page.auto_check_btn.toggled.connect(self._on_auto_toggled)
        self.monitor_page.clear_button.clicked.connect(lambda: None)  # 页内已接
        self.monitor_page.launch_game_button.clicked.connect(self.launch_game)
        self.settings_page.save_button.clicked.connect(self.save_settings)
        self.settings_page.calibration_requested.connect(self.capture_calibration)
        self.settings_page.platform_combo.currentIndexChanged.connect(
            lambda _=None: self._sync_platform_label()
        )

        # 首次进入：自动同步任务到 Worker，恢复自动监测开关
        self.worker.set_tasks([t for t in tasks if t.enabled])
        self.worker.set_auto(self.ammo_page.auto_check_btn.isChecked())
        self.worker.set_loop(self.config.get("loop_gap", 400), self.config.get("half_coin_mode", False))

        self._sync_platform_label()
        self._on_state(STATE_OFF)
        self.apply_theme_scale()
        from datetime import datetime
        self._on_log("success", "捣蛋助手已启动 %s（build %s）" % (datetime.now().strftime("%H:%M:%S"), "20260829"))

    # ---------- 界面构建 ----------

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(118)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)

        logo_path = ASSETS_DIR / "df_logo_cn.png"
        if logo_path.exists():
            logo_label = QLabel()
            pixmap = QPixmap(str(logo_path)).scaled(
                56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignLeft)
            layout.addWidget(logo_label)

        title = QLabel("捣蛋助手")
        title.setObjectName("appTitle")
        subtitle = QLabel("DELTA FORCE")
        subtitle.setObjectName("appSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(18)

        self.nav = QListWidget()
        self.nav.addItems(["目标子弹", "OCR 监测", "设置"])
        self.nav.setCurrentRow(0)
        layout.addWidget(self.nav, 1)
        return sidebar

    def _build_main_area(self, tasks: list) -> QWidget:
        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 10, 18, 10)
        header_layout.addWidget(QLabel("三角洲交易行 · 全自动监测买入"))
        header_layout.addStretch(1)
        self.status_pill = QLabel("监测未启动")
        self.status_pill.setObjectName("statusPill")
        header_layout.addWidget(self.status_pill)
        main_layout.addWidget(header)

        self.stack = QStackedWidget()
        self.ammo_page = AmmoPage(tasks)
        self.monitor_page = MonitorPage()
        self.settings_page = SettingsPage()
        self.settings_page.set_config(self.config)
        self.settings_page.set_calibration(self.config.get("mobile_calibration", {}))
        self.stack.addWidget(self._wrap_scroll(self.ammo_page))
        self.stack.addWidget(self._wrap_scroll(self.monitor_page))
        self.stack.addWidget(self._wrap_scroll(self.settings_page))
        main_layout.addWidget(self.stack, 1)

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        return main

    def _wrap_scroll(self, page: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        scroll.setFrameShape(QFrame.NoFrame)
        return scroll

    # ---------- 运行时 ----------

    def _rebuild_runtime(self, force: bool = False) -> None:
        settings = self.settings_page.to_config() if self.settings_page else {
            "platform_mode": self.config.get("platform_mode", "pc"),
            "adb_path": self.config.get("adb_path", ""),
            "adb_serial": self.config.get("adb_serial", ""),
            "refresh_delay": self.config.get("refresh_delay", 150),
        }
        key = (
            settings["platform_mode"],
            settings["adb_path"],
            settings["adb_serial"],
            int(settings["refresh_delay"]),
        )
        if key == self._runtime_key and self.worker is not None and not force:
            return
        # 平台/设备变化时必须重建（哪怕是运行中），否则手机模式永远切不过去
        if self.worker is not None:
            self.worker.shutdown()
            self.worker.wait(2000)
        if settings["platform_mode"] == "mobile":
            backend = AdbBackend(
                adb_path=settings["adb_path"] or None,
                serial=settings["adb_serial"],
                refresh_delay_ms=settings["refresh_delay"],
            )
        else:
            backend = PcBackend(refresh_delay_ms=settings["refresh_delay"])
        self.buybot = BuyBot(backend, self.ocr, calibration=self.config.get("mobile_calibration", {}))
        self.worker = Worker(self.buybot)
        self.worker.log_signal.connect(self._on_log)
        self.worker.state_signal.connect(self._on_state)
        self.worker.price_signal.connect(self._on_price)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.start()
        self._runtime_key = key
        self.on_tasks_changed()
        self.worker.set_auto(self.ammo_page.auto_check_btn.isChecked())

    def _sync_platform_label(self) -> None:
        pass

    # ---------- 自动监测 ----------

    def _on_auto_toggled(self, checked: bool) -> None:
        self.ammo_page.auto_check_btn.setText("自动监测：开" if checked else "自动监测：关")
        self.worker.set_auto(checked)
        self._on_message("自动监测已%s" % ("开启" if checked else "关闭"))

    def on_tasks_changed(self) -> None:
        enabled = [t for t in self.ammo_page.tasks if t.enabled]
        self.worker.set_tasks(enabled)
        self.worker.set_loop(
            self.settings_page.loop_gap_spin.value(),
            self.settings_page.half_coin_check.isChecked(),
        )

    # ---------- 位置标定 ----------

    def capture_position(self, task_name: str) -> None:
        if self.settings_page.platform_mode() == "mobile":
            self._capture_position_mobile(task_name)
        else:
            self._capture_position_pc(task_name)

    def _capture_position_pc(self, task_name: str) -> None:
        self._on_message("3 秒后记录鼠标位置，请现在把鼠标移到目标子弹上")
        QTimer.singleShot(3000, lambda: self._do_capture_pc(task_name))

    def _do_capture_pc(self, task_name: str) -> None:
        backend = PcBackend()
        position = backend.pointer_fraction()
        self.ammo_page.set_position(task_name, position)

    def _capture_position_mobile(self, task_name: str) -> None:
        try:
            self._rebuild_runtime()
            self.buybot.backend.check()
            self._on_message("正在截取手机画面...")
            QApplication.processEvents()
            image = self.buybot.backend.screenshot()
        except Exception as exc:
            QMessageBox.warning(self, "截图失败", str(exc))
            return
        dialog = PositionPickDialog(image, self)
        result = dialog.exec_()
        if result and dialog.fraction:
            self._on_message(
                "截图取点确认：%s -> %.0f%%, %.0f%%" % (task_name, dialog.fraction[0] * 100, dialog.fraction[1] * 100)
            )
            self.ammo_page.set_position(task_name, dialog.fraction)
            # 不依赖信号链，直接同步给监测线程，确保手机能收到点击
            self.on_tasks_changed()
            self._on_log("success", "位置已生效，监测循环将点击手机该位置")
        elif not result:
            self._on_message("已取消位置标定")

    # ---------- OCR 测试 ----------

    def test_ocr(self, row: int) -> None:
        if self.ocr_test_thread and self.ocr_test_thread.isRunning():
            return
        self._rebuild_runtime()
        if self.settings_page.platform_mode() == "mobile":
            try:
                self.buybot.backend.check()
            except AdbBackendError as exc:
                self._on_log("error", "手机未连接：%s" % exc)
                return
        else:
            if not window_finder.game_window_ok():
                self._on_log("warn", "未检测到 16:9 游戏窗口，OCR 测试结果可能不准")
        task = self.ammo_page._task_at_row(row)
        if task is None:
            return
        self._on_log("info", "开始测试 OCR：%s" % task.name)
        self.ocr_test_thread = OcrTestThread(self.buybot, task.convertible)
        self.ocr_test_thread.result.connect(self._on_test_result)
        self.ocr_test_thread.start()

    def _on_test_result(self, price: int, error: str) -> None:
        if price > 0:
            self._on_log("success", "OCR 识别成功：%s" % price)
        else:
            self._on_log("error", "OCR 识别失败：%s" % error)

    # ---------- 启动游戏 / 配置 ----------

    def capture_calibration(self, key: str) -> None:
        """手机校准：截手机屏 -> 取点 -> 保存 -> 重建运行时。"""
        self._rebuild_runtime()
        try:
            self.buybot.backend.check()
            self._on_message("校准 %s：正在截取手机画面..." % key)
            QApplication.processEvents()
            image = self.buybot.backend.screenshot()
        except Exception as exc:
            QMessageBox.warning(self, "校准失败", str(exc))
            return
        dialog = PositionPickDialog(image, self)
        result = dialog.exec_()
        if not (result and dialog.fraction):
            self._on_message("校准已取消")
            return
        calib = self.config.setdefault("mobile_calibration", {})
        calib[key] = dialog.fraction
        save_config(self.config)
        self.settings_page.set_calibration(calib)
        self._on_message("校准 %s 已保存：%0.0f%%, %.0f%%" % (key, dialog.fraction[0] * 100, dialog.fraction[1] * 100))
        self._rebuild_runtime(force=True)

    def launch_game(self) -> None:
        path = self.settings_page.game_path_edit.text().strip()
        if not path:
            self._on_log("error", "请先在设置页选择三角洲行动的启动程序或快捷方式")
            return
        if not os.path.exists(path):
            self._on_log("error", "游戏路径不存在：%s" % path)
            return
        try:
            os.startfile(path)
            self._on_log("info", "正在启动三角洲行动：%s" % path)
        except Exception as exc:
            self._on_log("error", "启动游戏失败：%s" % exc)

    def save_settings(self) -> None:
        self.config.update(self.settings_page.to_config())
        self.config = config_from_tasks(self.config, self.ammo_page.tasks)
        save_config(self.config)
        self._on_log("success", "配置已保存")
        self.on_tasks_changed()

    # ---------- 日志与状态 ----------

    def _on_message(self, text: str) -> None:
        self._on_log("info", text)

    def _on_log(self, level: str, text: str) -> None:
        self.monitor_page.append_log(level, text)
        self.overlay.add_line(level, text)

    def _on_state(self, state: str) -> None:
        self.monitor_page.set_state(state)
        text, color = {
            STATE_RUNNING: ("监测中", True),
            STATE_WAITING: ("等待游戏窗口", False),
            STATE_OFF: ("监测未启动", False),
        }.get(state, ("监测未启动", False))
        self.status_pill.setText(text)
        self.status_pill.setProperty("active", "true" if color else "false")
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)

    def _on_price(self, price: int, name: str) -> None:
        # 最近价格显示在监测日志里，浮层由 _on_log 覆盖
        pass

    def _on_progress(self, name: str, current: int, total: int) -> None:
        self.statusBar().showMessage("%s：%s / %s 次" % (name, current, total))

    def apply_theme_scale(self) -> None:
        scale = min(self.width() / 760.0, self.height() / 580.0)
        scale = max(0.8, min(1.3, scale))
        self.setStyleSheet(build_qss(scale))

    def resizeEvent(self, event) -> None:
        self.apply_theme_scale()
        super().resizeEvent(event)

    def update_overlay(self) -> None:
        if not self.settings_page.overlay_check.isChecked():
            self._ratio_ok = None
            self.overlay.hide()
            return
        if self.settings_page.platform_mode() == "mobile":
            if not self.overlay.isVisible():
                self.overlay.place_floating()
            return
        keyword = self.settings_page.window_keyword_edit.text().strip() or "三角洲行动"
        rect = window_finder.find_game_window(keyword)
        if rect is None:
            self._game_hwnd = None
            self._ratio_ok = None
            self.overlay.hide()
            return
        ratio_ok = (
            abs(rect[2] / rect[3] - window_finder.TARGET_ASPECT) / window_finder.TARGET_ASPECT
            <= window_finder.ASPECT_TOLERANCE
        )
        if not ratio_ok:
            if self._ratio_ok is not False:
                self._on_log("warn", "游戏窗口不是 16:9，日志浮层已暂停")
            self._ratio_ok = False
            self.overlay.hide()
            return
        if self._ratio_ok is not True:
            self._on_log("success", "已检测到 16:9 游戏窗口，日志浮层开启")
        self._ratio_ok = True
        self.overlay.place_on(rect)

    def _on_splitter_moved(self, position: int, index: int) -> None:
        self.config["sidebar_width"] = position

    def closeEvent(self, event) -> None:
        self.overlay_timer.stop()
        self.overlay.hide()
        if self.worker is not None:
            self.worker.shutdown()
            self.worker.wait(2000)
        # 直接落盘，不走 save_settings（避免退出时重建 worker 线程）
        self.config.update(self.settings_page.to_config())
        self.config = config_from_tasks(self.config, self.ammo_page.tasks)
        save_config(self.config)
        self.ocr.close()
        super().closeEvent(event)