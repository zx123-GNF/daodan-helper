from dataclasses import dataclass, field
from typing import List


@dataclass
class BulletTask:
    """三档价格模型：

    - buy_price     买入价格：价格不高于它立即买入 max_quantity 发
    - low_tier      最低档位：买入价~最低档之间用小额购买刷新
    - high_tier     最高档位：最低档~最高档之间免费刷新等待，超过最高档同样只刷新
    - max_quantity  单次买入上限（滑条比例按 200 发满额换算）
    """

    name: str = ""
    caliber: str = ""
    tier: int = 4
    buy_price: int = 0
    low_tier: int = 0
    high_tier: int = 0
    buy_times: int = 10
    max_quantity: int = 200
    position: List[float] = field(default_factory=list)
    enabled: bool = True
    convertible: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "caliber": self.caliber,
            "tier": self.tier,
            "buy_price": self.buy_price,
            "low_tier": self.low_tier,
            "high_tier": self.high_tier,
            "buy_times": self.buy_times,
            "max_quantity": self.max_quantity,
            "position": [float(x) for x in self.position],
            "enabled": self.enabled,
            "convertible": self.convertible,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BulletTask":
        # 兼容旧配置：ideal_price -> buy_price, max_price -> high_tier
        buy_price = int(data.get("buy_price", data.get("ideal_price", 0)) or 0)
        high_tier = int(data.get("high_tier", data.get("max_price", 0)) or 0)
        low_tier = int(data.get("low_tier", 0) or 0)
        if low_tier <= 0 and buy_price > 0 and high_tier > buy_price:
            low_tier = (buy_price + high_tier) // 2
        return cls(
            name=str(data.get("name", "")),
            caliber=str(data.get("caliber", "")),
            tier=int(data.get("tier", 4)),
            buy_price=buy_price,
            low_tier=low_tier,
            high_tier=high_tier,
            buy_times=int(data.get("buy_times", 10)),
            max_quantity=int(data.get("max_quantity", 200) or 200),
            position=[float(x) for x in data.get("position", [])],
            enabled=bool(data.get("enabled", True)),
            convertible=bool(data.get("convertible", True)),
        )


def tasks_to_dicts(tasks: List[BulletTask]) -> List[dict]:
    return [t.to_dict() for t in tasks]


def tasks_from_dicts(data: List[dict]) -> List[BulletTask]:
    return [BulletTask.from_dict(item) for item in data]
