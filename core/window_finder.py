"""游戏窗口查找与 16:9 检测（Worker 与 UI 共用）。"""

import ctypes
from ctypes import wintypes

import pyautogui

TARGET_ASPECT = 16 / 9
ASPECT_TOLERANCE = 0.05


def find_game_window(keyword: str = "三角洲行动"):
    """返回 (left, top, width, height) 或 None。"""
    candidates = [keyword] if keyword else []
    for fallback in ("三角洲行动", "delta force", "deltaforce"):
        if fallback.lower() not in [c.lower() for c in candidates]:
            candidates.append(fallback)
    try:
        windows = pyautogui.getAllWindows()
    except Exception:
        return None
    for window in windows:
        title = window.title or ""
        if any(key.lower() in title.lower() for key in candidates):
            hwnd = getattr(window, "_hWnd", None) or getattr(window, "hwnd", None)
            if hwnd:
                rect = client_rect(hwnd)
                if rect:
                    return rect
            left = getattr(window, "left", None)
            top = getattr(window, "top", None)
            width = getattr(window, "width", 0)
            height = getattr(window, "height", 0)
            if left is not None and top is not None and width > 100 and height > 100:
                return (left, top, width, height)
    return None


def game_window_ok(keyword: str = "三角洲行动") -> bool:
    """窗口存在且接近 16:9。"""
    rect = find_game_window(keyword)
    if rect is None:
        return False
    width, height = rect[2], rect[3]
    return abs(width / height - TARGET_ASPECT) / TARGET_ASPECT <= ASPECT_TOLERANCE


def client_rect(hwnd):
    try:
        rect = wintypes.RECT()
        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect))
        point = wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point))
        width = rect.right
        height = rect.bottom
        if width > 100 and height > 100:
            return (point.x, point.y, width, height)
    except Exception:
        pass
    return None
