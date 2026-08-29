from .models import BulletTask


def default_tasks() -> list:
    return [
        BulletTask(name="5.56x45mm M855", tier=3, buy_price=600, low_tier=750, high_tier=900, buy_times=10),
        BulletTask(name="7.62x39mm PS", tier=3, buy_price=500, low_tier=650, high_tier=800, buy_times=10),
        BulletTask(name="7.62x51mm BPZ", tier=3, buy_price=500, low_tier=650, high_tier=800, buy_times=10),
        BulletTask(name="5.45x39mm PP", tier=3, buy_price=600, low_tier=750, high_tier=900, buy_times=10),
        BulletTask(name="9x39mm SP5", tier=3, buy_price=600, low_tier=750, high_tier=900, buy_times=10),
        BulletTask(name="9x19mm PSO", tier=3, buy_price=30, low_tier=45, high_tier=60, buy_times=10),
        BulletTask(name="5.56x45mm M855A1", tier=4, buy_price=2000, low_tier=2300, high_tier=2600, buy_times=10),
        BulletTask(name="7.62x39mm BP", tier=4, buy_price=1800, low_tier=2100, high_tier=2400, buy_times=10),
        BulletTask(name="7.62x51mm M80", tier=4, buy_price=1800, low_tier=2100, high_tier=2400, buy_times=10),
        BulletTask(name="5.45x39mm BS", tier=4, buy_price=1800, low_tier=2100, high_tier=2400, buy_times=10),
        BulletTask(name="9x39mm SP6", tier=4, buy_price=1800, low_tier=2100, high_tier=2400, buy_times=10),
        BulletTask(name="7.62x54R LPS", tier=4, buy_price=1800, low_tier=2100, high_tier=2400, buy_times=10),
        BulletTask(name="5.8x42mm DBP10", tier=4, buy_price=2000, low_tier=2300, high_tier=2600, buy_times=10),
        BulletTask(name="9x19mm AP6.3", tier=4, buy_price=1500, low_tier=1750, high_tier=2000, buy_times=10),
    ]
