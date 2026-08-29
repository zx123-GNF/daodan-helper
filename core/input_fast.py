"""零延迟键鼠注入，直接走 Win32 SendInput。

pyautogui 每个动作之间默认有 PAUSE=0.1s 停顿，一次"移动+点击"要浪费
200ms 以上，抢单场景下不可接受。这里用 ctypes 直接构造 SendInput 结构，
移动、按下、抬起之间没有任何人为停顿（仅保留可配置的按下保持时间，
部分游戏需要非零的按下时长才能注册点击）。
"""

import ctypes
import ctypes.wintypes as wintypes
import time

_user32 = ctypes.windll.user32

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000

KEYEVENTF_KEYUP = 0x0002

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

VK_ESCAPE = 0x1B


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ULONG_PTR)),
    )


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ULONG_PTR)),
    )


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = ("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT)

    _anonymous_ = ("u",)
    _fields_ = ("type", wintypes.DWORD), ("u", _U)


def screen_size() -> tuple:
    return _user32.GetSystemMetrics(0), _user32.GetSystemMetrics(1)


def _send(*inputs: _INPUT) -> None:
    count = len(inputs)
    array = (_INPUT * count)(*inputs)
    _user32.SendInput(count, array, ctypes.sizeof(_INPUT))


def _abs_coords(x: int, y: int) -> tuple:
    width, height = screen_size()
    abs_x = int(round(max(0, min(width - 1, x)) * 65535 / max(1, width - 1)))
    abs_y = int(round(max(0, min(height - 1, y)) * 65535 / max(1, height - 1)))
    return abs_x, abs_y


def _mouse(flags: int, abs_x: int = 0, abs_y: int = 0) -> _INPUT:
    item = _INPUT(type=INPUT_MOUSE)
    item.mi = _MOUSEINPUT(
        dx=abs_x,
        dy=abs_y,
        mouseData=0,
        dwFlags=flags,
        time=0,
        dwExtraInfo=ctypes.cast(0, ctypes.POINTER(ULONG_PTR)),
    )
    return item


def _key(vk: int, flags: int) -> _INPUT:
    item = _INPUT(type=INPUT_KEYBOARD)
    item.ki = _KEYBDINPUT(
        wVk=vk,
        wScan=0,
        dwFlags=flags,
        time=0,
        dwExtraInfo=ctypes.cast(0, ctypes.POINTER(ULONG_PTR)),
    )
    return item


def move_to(x: int, y: int) -> None:
    abs_x, abs_y = _abs_coords(int(x), int(y))
    _send(_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, abs_x, abs_y))


def mouse_down() -> None:
    _send(_mouse(MOUSEEVENTF_LEFTDOWN))


def mouse_up() -> None:
    _send(_mouse(MOUSEEVENTF_LEFTUP))


def click(x: int, y: int, hold: float = 0.008) -> None:
    """移动到目标并点击。hold 是按下保持时长，过小部分游戏会丢点击。"""
    move_to(x, y)
    mouse_down()
    if hold > 0:
        time.sleep(hold)
    mouse_up()


def press_escape(hold: float = 0.005) -> None:
    _send(_key(VK_ESCAPE, 0))
    if hold > 0:
        time.sleep(hold)
    _send(_key(VK_ESCAPE, KEYEVENTF_KEYUP))


def pointer_position() -> tuple:
    point = wintypes.POINT()
    _user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y
