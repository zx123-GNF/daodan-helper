"""三角洲行动弹药数据库。

数据来源：
- MAIN：官方口径图鉴（7 大主口径，等级与可交易性为官方口径）
- EXTRA：交易行在售的次级口径弹种（价格为近期行情参考值，可在界面修改）

字段：(名称, 口径, 穿透等级, 可交易, 参考买入价)
等级 0 = 无穿透高肉伤弹（修脚弹），T6 弹（M61 等）仅工作台生产不收录。
"""

DEFAULT_MAX_QUANTITY = 200


def _task(name, caliber, tier, tradable, ref_price):
    return {
        "name": name,
        "caliber": caliber,
        "tier": tier,
        "tradable": tradable,
        "ref_price": ref_price,
    }


AMMO_DB = [
    # ---- 5.56x45mm ----
    _task("5.56x45mm RRLP", "5.56x45mm", 1, True, 60),
    _task("5.56x45mm FMJ", "5.56x45mm", 2, True, 110),
    _task("5.56x45mm M855", "5.56x45mm", 3, True, 500),
    _task("5.56x45mm M855A1", "5.56x45mm", 4, True, 2000),
    _task("5.56x45mm M995", "5.56x45mm", 5, True, 3300),
    # ---- 5.45x39mm ----
    _task("5.45x39mm PRS", "5.45x39mm", 1, True, 50),
    _task("5.45x39mm T", "5.45x39mm", 2, True, 90),
    _task("5.45x39mm PS", "5.45x39mm", 3, True, 530),
    _task("5.45x39mm BT", "5.45x39mm", 4, True, 1900),
    _task("5.45x39mm BS", "5.45x39mm", 5, True, 3100),
    # ---- 5.8x42mm ----
    _task("5.8x42mm DBP191", "5.8x42mm", 3, True, 480),
    _task("5.8x42mm DBP10", "5.8x42mm", 4, True, 2000),
    _task("5.8x42mm DVC12", "5.8x42mm", 5, True, 3200),
    # ---- 7.62x39mm ----
    _task("7.62x39mm LP", "7.62x39mm", 1, True, 55),
    _task("7.62x39mm T45M", "7.62x39mm", 2, True, 100),
    _task("7.62x39mm PS", "7.62x39mm", 3, True, 490),
    _task("7.62x39mm BP", "7.62x39mm", 4, True, 1800),
    _task("7.62x39mm AP", "7.62x39mm", 5, True, 3000),
    # ---- 7.62x51mm ----
    _task("7.62x51mm BPZ", "7.62x51mm", 3, True, 500),
    _task("7.62x51mm M80", "7.62x51mm", 4, True, 1800),
    _task("7.62x51mm M62", "7.62x51mm", 5, True, 2900),
    # ---- 7.62x54R ----
    _task("7.62x54R T46M", "7.62x54R", 3, True, 520),
    _task("7.62x54R LPS", "7.62x54R", 4, True, 1800),
    _task("7.62x54R BT", "7.62x54R", 5, True, 3000),
    # ---- 9x39mm ----
    _task("9x39mm SP5", "9x39mm", 3, True, 600),
    _task("9x39mm SP6", "9x39mm", 4, True, 1800),
    _task("9x39mm BP", "9x39mm", 5, True, 3000),
    # ---- 9x19mm ----
    _task("9x19mm PSO", "9x19mm", 1, True, 30),
    _task("9x19mm Pst", "9x19mm", 2, True, 60),
    _task("9x19mm AP6.3", "9x19mm", 3, True, 400),
    _task("9x19mm PBP", "9x19mm", 4, True, 1500),
    _task("9x19mm RIP", "9x19mm", 0, True, 90),
    # ---- 4.6x30mm ----
    _task("4.6x30mm Subsonic SX", "4.6x30mm", 2, True, 500),
    _task("4.6x30mm FMJ", "4.6x30mm", 3, True, 900),
    _task("4.6x30mm AP", "4.6x30mm", 4, True, 2000),
    # ---- 5.7x28mm ----
    _task("5.7x28mm L191", "5.7x28mm", 3, True, 190),
    _task("5.7x28mm SS190", "5.7x28mm", 4, True, 900),
    # ---- 6.8x51mm ----
    _task("6.8x51mm FMJ", "6.8x51mm", 4, True, 2000),
    _task("6.8x51mm HYBRID", "6.8x51mm", 5, True, 3400),
    # ---- 12.7x55mm ----
    _task("12.7x55mm PS12", "12.7x55mm", 4, True, 2900),
    _task("12.7x55mm PD12", "12.7x55mm", 5, True, 3800),
    _task("12.7x55mm PS12B", "12.7x55mm", 5, True, 5200),
    # ---- 12 Gauge ----
    _task("12 Gauge 8.5毫米鹿弹", "12 Gauge", 2, True, 120),
    _task("12 Gauge 独头AP-20", "12 Gauge", 3, True, 450),
    _task("12 Gauge 箭形弹", "12 Gauge", 3, True, 560),
    _task("12 Gauge 独头APX", "12 Gauge", 4, True, 1300),
    # ---- .45 ACP ----
    _task(".45 ACP CT", ".45 ACP", 0, True, 80),
    _task(".45 ACP RIP", ".45 ACP", 0, True, 120),
    _task(".45 ACP HIP", ".45 ACP", 2, True, 160),
    _task(".45 ACP AP", ".45 ACP", 5, True, 1400),
    # ---- .300 BLK ----
    _task(".300 BLK 穿甲弹", ".300BLK", 3, True, 590),
    # ---- .50 AE ----
    _task(".50 AE AP", ".50 AE", 4, True, 800),
    # ---- .357 Magnum ----
    _task(".357 Magnum HP", ".357 Magnum", 2, True, 90),
]

TIER_COLORS = {
    0: "#9ca3af",
    1: "#9ca3af",
    2: "#4ade80",
    3: "#38bdf8",
    4: "#a78bfa",
    5: "#f59e0b",
    6: "#f87171",
}


def tier_color(tier: int) -> str:
    return TIER_COLORS.get(int(tier), "#9ca3af")


def tier_label(tier: int) -> str:
    return "T%d" % tier if tier > 0 else "T0肉伤"


def all_ammo() -> list:
    return list(AMMO_DB)
