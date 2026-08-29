"""全自动监测 Worker。

不再依赖 F8/F9 热键：自动模式开启时，检测到 16:9 游戏窗口就开始逐个
监测启用的子弹任务；窗口消失则自动挂起等待。手机模式没有窗口概念，
由界面的自动开关直接控制。
"""

from PyQt5.QtCore import QMutex, QThread, pyqtSignal

from . import window_finder
from .device import AdbBackend


class OcrTestThread(QThread):
    result = pyqtSignal(int, str)

    def __init__(self, buybot, is_convertible: bool):
        super().__init__()
        self.buybot = buybot
        self.is_convertible = is_convertible

    def run(self):
        try:
            price = self.buybot.detect_price(is_convertible=self.is_convertible)
            self.result.emit(price, "")
        except Exception as exc:
            self.result.emit(-1, str(exc))


# 状态常量：监测页状态灯与状态文字
STATE_OFF = "off"          # 自动开关关闭
STATE_WAITING = "waiting"  # 等待游戏窗口
STATE_RUNNING = "running"  # 监测中


class Worker(QThread):
    log_signal = pyqtSignal(str, str)          # (level, text)
    state_signal = pyqtSignal(str)             # STATE_*
    price_signal = pyqtSignal(int, str)        # (price, task_name)
    progress_signal = pyqtSignal(str, int, int)  # (task_name, current, total)

    def __init__(self, buybot):
        super().__init__()
        self.buybot = buybot
        self._lock = QMutex()
        self._stop = False
        self._auto = False
        self._mobile = isinstance(buybot.backend, AdbBackend)
        self._tasks = []
        self._loop_gap = 400
        self._half_coin_mode = False
        self._buy_counts = {}  # 按任务名计数，避免多任务轮询时混计

    # ---------- 线程安全配置 ----------

    def set_tasks(self, tasks: list) -> None:
        self._lock.lock()
        self._tasks = list(tasks)
        self._lock.unlock()

    def set_auto(self, auto: bool) -> None:
        self._lock.lock()
        self._auto = bool(auto)
        self._lock.unlock()

    def set_loop(self, loop_gap: int, half_coin_mode: bool) -> None:
        self._lock.lock()
        self._loop_gap = max(100, int(loop_gap))
        self._half_coin_mode = bool(half_coin_mode) and not self._mobile
        self._lock.unlock()

    def shutdown(self) -> None:
        self._lock.lock()
        self._stop = True
        self._auto = False
        self._lock.unlock()

    # ---------- 主循环 ----------

    def run(self):
        warned_no_position = set()
        while True:
            self._lock.lock()
            stop = self._stop
            auto = self._auto
            tasks = list(self._tasks)
            loop_gap = self._loop_gap
            half_coin_mode = self._half_coin_mode
            self._lock.unlock()

            if stop:
                break
            if not auto or not tasks:
                self.state_signal.emit(STATE_OFF)
                self.msleep(200)
                continue

            # PC 模式：游戏窗口没开就挂起等待（手机模式跳过窗口检测）
            if not self._mobile and not window_finder.game_window_ok():
                self.state_signal.emit(STATE_WAITING)
                self.msleep(1000)
                continue

            self.state_signal.emit(STATE_RUNNING)

            # 一轮：依次监测所有启用且已标定位置的任务
            for task in tasks:
                self._lock.lock()
                auto = self._auto
                self._lock.unlock()
                if not auto:
                    break
                if not task.enabled:
                    continue
                if not task.position:
                    if task.name not in warned_no_position:
                        warned_no_position.add(task.name)
                        self.log_signal.emit(
                            "warn", "%s 未标定位置，已跳过；请在目标子弹页点击其位置格" % task.name
                        )
                    continue
                self.monitor_one(task, half_coin_mode)
                self.msleep(120)  # 任务间留出页面切换时间

            self.msleep(loop_gap)

    def monitor_one(self, task, half_coin_mode: bool) -> None:
        try:
            self.buybot.backend.click(task.position)
            price = self.buybot.detect_price(is_convertible=task.convertible)
            raw = getattr(self.buybot, "last_raw_text", "") or ""
            self.price_signal.emit(price, task.name)

            tiers = "三档[买%d/低%d/高%d]" % (task.buy_price, task.low_tier, task.high_tier)
            if price <= task.buy_price:
                quantity = max(1, min(200, int(task.max_quantity or 200)))
                self.buybot.buy_new(is_convertible=task.convertible, target_buy_number=quantity)
                self._buy_counts[task.name] = self._buy_counts.get(task.name, 0) + 1
                count = self._buy_counts[task.name]
                receipt = "已存 logs/buy_after.png" if getattr(self.buybot, "last_buy_receipt", False) else "截图失败"
                self.log_signal.emit(
                    "buy",
                    "%s 价格 %s ≤ 买入价 %s，买入 %d 发，等待成交（%s；OCR:%s）"
                    % (task.name, price, task.buy_price, quantity, receipt, raw),
                )
                self.progress_signal.emit(task.name, count, task.buy_times)
                if task.buy_times and count >= task.buy_times:
                    task.enabled = False
                    self._buy_counts[task.name] = 0
                    self.log_signal.emit("success", "%s 已买满 %s 次，自动停用" % (task.name, task.buy_times))
            elif price <= task.low_tier:
                self.buybot.refresh(is_convertible=task.convertible)
                self.log_signal.emit(
                    "warn", "%s %s 价格 %s 略高于买入价，小额刷新（OCR:%s）" % (task.name, tiers, price, raw)
                )
            else:
                self.buybot.freerefresh(task.position)
                if price > task.high_tier:
                    self.log_signal.emit(
                        "error",
                        "%s %s 价格 %s 超最高档，刷新盯守（OCR:%s）" % (task.name, tiers, price, raw),
                    )
                else:
                    self.log_signal.emit(
                        "info", "%s %s 价格 %s 在档位区间，免费刷新（OCR:%s）" % (task.name, tiers, price, raw)
                    )
        except Exception as exc:
            message = str(exc)
            if "识别" in message:
                self.log_signal.emit("warn", "%s 识别失败，刷新商品页：%s" % (task.name, message))
                try:
                    self.buybot.freerefresh(task.position)
                except Exception:
                    pass
            else:
                self.log_signal.emit("error", "%s 操作失败：%s" % (task.name, message))
