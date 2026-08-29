import json
import os
from pathlib import Path

from .device import find_adb
from .models import tasks_from_dicts, tasks_to_dicts
from .presets import default_tasks


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_config() -> dict:
    return {
        "platform_mode": "pc",
        "loop_gap": 120,
        "default_convertible": True,
        "half_coin_mode": False,
        "refresh_delay": 150,
        "overlay_enabled": True,
        "window_keyword": "三角洲行动",
        "game_path": "",
        "adb_path": "",
        "adb_serial": "",
        "mobile_calibration": {},
        "sidebar_width": 140,
        "tasks": tasks_to_dicts(default_tasks()),
    }


def load_config(path: str = None) -> dict:
    path = path or os.path.join(project_root(), "config.json")
    config = default_config()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for key in config:
                    if key in data:
                        config[key] = data[key]
                if isinstance(data.get("tasks"), list):
                    config["tasks"] = data["tasks"]
        except (json.JSONDecodeError, OSError):
            pass
    # 旧配置迁移 + adb 路径自动探测
    config["tasks"] = [t.to_dict() for t in tasks_from_dicts(config["tasks"])]
    if not config.get("adb_path"):
        config["adb_path"] = find_adb()
    if config.get("platform_mode") not in ("pc", "mobile"):
        config["platform_mode"] = "pc"
    return config


def save_config(config: dict, path: str = None) -> None:
    path = path or os.path.join(project_root(), "config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def config_to_tasks(config: dict) -> list:
    return tasks_from_dicts(config.get("tasks", []))


def merged_tasks_with_ammo(config: dict) -> list:
    """以弹药库 53 种弹为基础生成任务列表，继承旧配置里同名任务的设置。"""
    from .models import BulletTask

    saved = {t["name"]: t for t in config.get("tasks", []) if isinstance(t, dict)}
    from .ammo_db import all_ammo

    tasks = []
    for item in all_ammo():
        old = saved.get(item["name"], {})
        buy_price = int(old.get("buy_price", old.get("ideal_price", 0)) or 0) or item["ref_price"]
        high_tier = int(old.get("high_tier", old.get("max_price", 0)) or 0) or round(buy_price * 1.5)
        low_tier = int(old.get("low_tier", 0) or 0) or (buy_price + high_tier) // 2
        tasks.append(
            BulletTask(
                name=item["name"],
                caliber=item["caliber"],
                tier=item["tier"],
                buy_price=buy_price,
                low_tier=low_tier,
                high_tier=high_tier,
                buy_times=int(old.get("buy_times", 10)),
                max_quantity=int(old.get("max_quantity", 200) or 200),
                position=[float(x) for x in old.get("position", [])],
                enabled=bool(old.get("enabled", False)),
                convertible=bool(old.get("convertible", True)),
            )
        )
    return tasks


def config_from_tasks(config: dict, tasks: list) -> dict:
    config["tasks"] = tasks_to_dicts(tasks)
    return config
