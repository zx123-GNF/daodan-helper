import time

from .ocr import WindowsOcr


# 手机端校准键：价格识别区两点 + 数量滑条两端 + 购买按钮 + 确认按钮
CALIBRATION_KEYS = ("price_tl", "price_br", "qty_min", "qty_max", "buy_button", "buy_confirm")


class OCRFailure(Exception):
    pass


class BuyBot:
    """交易行买入执行器，通过 backend 抽象同时支持电脑与手机。

    电脑端坐标是 2560x1440 下标定的比例常量；手机端 UI 布局不同，
    必须使用用户通过"手机校准"标定的坐标（calibration 字典）。
    """

    def __init__(self, backend, ocr: WindowsOcr = None, calibration: dict = None):
        self.backend = backend
        self.ocr = ocr or WindowsOcr()
        self.calibration = dict(calibration or {})
        self.confirm_delay = 0.35  # 点购买后等确认弹窗出现
        self.buy_settle_delay = 0.8  # 买入后等交易处理，避免被后续点击打断
        self.range_isconvertible_lowest_price = [2179 / 2560, 1078 / 1440, 2308 / 2560, 1102 / 1440]
        self.range_notconvertible_lowest_price = [2179 / 2560, 1156 / 1440, 2308 / 2560, 1178 / 1440]
        self.postion_max_shopping_number = [2324 / 2560, 1112 / 1440]
        self.postion_min_shopping_number = [2028 / 2560, 1112 / 1440]
        self.postion_buy_button = [2186 / 2560, 1225 / 1440]
        self.offset_isconvertible = (1038 - 1112) / 1440
        self.postion_balance = [2200 / 2560, 70 / 1440]
        self.postion_balance_half_coin = [1930 / 2560, 363 / 1440, 2324 / 2560, 387 / 1440]
        self.balance_half_coin = None

    @property
    def is_mobile(self) -> bool:
        return self.backend.name == "mobile"

    def _mobile_calibrated(self) -> bool:
        calib = self.calibration
        return all(calib.get(key) for key in ("price_tl", "price_br", "qty_min", "qty_max", "buy_button"))

    def detect_price(self, is_convertible: bool = True, debug_mode: bool = False) -> int:
        calib = self.calibration
        if self.is_mobile and calib.get("price_tl") and calib.get("price_br"):
            tl, br = calib["price_tl"], calib["price_br"]
            region = [tl[0], tl[1], br[0], br[1]]
        else:
            region = (
                self.range_isconvertible_lowest_price
                if is_convertible
                else self.range_notconvertible_lowest_price
            )
        image = self.backend.capture(region)
        text = self.ocr.recognize(image)
        self.last_raw_text = text
        self.last_region = region
        if debug_mode:
            print(text)
        price = self.ocr.parse_number(text)
        if price is None:
            raise OCRFailure("价格识别失败，请检查物品是否可兑换")
        return price

    def detect_balance_half_coin(self, debug_mode: bool = False):
        self.backend.move(self.postion_balance)
        image = self.backend.capture(self.postion_balance_half_coin)
        text = self.ocr.recognize(image)
        if debug_mode:
            print(text)
        self.balance_half_coin = self.ocr.parse_number(text)
        return self.balance_half_coin

    def _quantity_position(self, target_buy_number: int, is_convertible: bool) -> list:
        calib = self.calibration
        if self.is_mobile and calib.get("qty_min") and calib.get("qty_max"):
            qmin, qmax = calib["qty_min"], calib["qty_max"]
            t = (target_buy_number - 1) / 199.0
            return [qmin[0] + (qmax[0] - qmin[0]) * t, qmin[1] + (qmax[1] - qmin[1]) * t]
        pos = [
            (target_buy_number - 1) / 200 * (self.postion_max_shopping_number[0] - self.postion_min_shopping_number[0])
            + self.postion_min_shopping_number[0],
            self.postion_min_shopping_number[1],
        ]
        if is_convertible:
            pos[1] = pos[1] + self.offset_isconvertible
        return pos

    def buy_new(self, is_convertible: bool, target_buy_number: int) -> None:
        """抢单关键路径：数量滑条 + 确认按钮两连击，中间零人为延迟。"""
        self.backend.click(self._quantity_position(target_buy_number, is_convertible))
        calib = self.calibration
        if self.is_mobile and calib.get("buy_button"):
            pos = list(calib["buy_button"])
        else:
            pos = list(self.postion_buy_button)
            if is_convertible:
                pos[1] = pos[1] + self.offset_isconvertible
        self.backend.click(pos)
        if self.is_mobile:
            # 点完购买后等交易处理，防止下一轮点击（点子弹/ESC）打断成交
            time.sleep(self.buy_settle_delay)
            self._capture_buy_receipt()

    def _capture_buy_receipt(self) -> None:
        """买入后截一张手机图存到 logs/buy_after.png，用于核对成交情况。"""
        try:
            from pathlib import Path

            log_dir = Path(__file__).resolve().parents[1] / "logs"
            log_dir.mkdir(exist_ok=True)
            self.backend.screenshot().save(str(log_dir / "buy_after.png"))
            self.last_buy_receipt = True
        except Exception:
            self.last_buy_receipt = False

    def buy(self, is_convertible: bool) -> None:
        self.buy_new(is_convertible, 200)

    def refresh(self, is_convertible: bool) -> None:
        self.buy_new(is_convertible, 31)

    def freerefresh(self, good_position: list) -> None:
        """ESC 关闭商品页后重新点开该商品，完成一次免费刷新。"""
        self.backend.press_escape()
        time.sleep(self.backend.refresh_delay)
        self.backend.click(good_position)

    def mobile_calibrated(self) -> bool:
        return self.is_mobile and self._mobile_calibrated()
