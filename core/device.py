"""设备后端抽象：电脑（SendInput + 屏幕截图）与手机（ADB tap + screencap）。

所有坐标一律使用"相对比例"（0~1 的浮点），由后端各自换算成
屏幕像素 / 手机像素，这样同一份任务配置可以同时在两个平台使用。
"""

import io
import os
import subprocess

from PIL import Image, ImageGrab

from . import input_fast


def _frac_to_pixel(value: float, limit: int) -> int:
    if value < 1:
        return int(limit * value)
    return int(value)


class PcBackend:
    name = "pc"

    def __init__(self, refresh_delay_ms: int = 150):
        self.refresh_delay = max(0, int(refresh_delay_ms)) / 1000.0

    def screen_size(self) -> tuple:
        return input_fast.screen_size()

    def click(self, position, hold: float = 0.008) -> None:
        if not position:
            return
        width, height = self.screen_size()
        input_fast.click(
            _frac_to_pixel(position[0], width),
            _frac_to_pixel(position[1], height),
            hold=hold,
        )

    def move(self, position) -> None:
        if not position:
            return
        width, height = self.screen_size()
        input_fast.move_to(
            _frac_to_pixel(position[0], width),
            _frac_to_pixel(position[1], height),
        )

    def press_escape(self) -> None:
        input_fast.press_escape()

    def capture(self, region) -> Image.Image:
        width, height = self.screen_size()
        left = _frac_to_pixel(region[0], width)
        top = _frac_to_pixel(region[1], height)
        right = _frac_to_pixel(region[2], width)
        bottom = _frac_to_pixel(region[3], height)
        if right <= left or bottom <= top:
            raise ValueError("截图区域无效")
        return ImageGrab.grab(bbox=(left, top, right, bottom))

    def screenshot(self) -> Image.Image:
        return ImageGrab.grab()

    def pointer_fraction(self) -> list:
        width, height = self.screen_size()
        x, y = input_fast.pointer_position()
        return [x / width, y / height]


class AdbBackendError(RuntimeError):
    pass


def find_adb() -> str:
    """按常见安装位置探测 adb.exe，找不到返回 'adb' 交给 PATH。"""
    candidates = []
    local = os.environ.get("LOCALAPPDATA", "")
    for root in ("", "D:\\", "E:\\", "C:\\"):
        candidates.append(os.path.join(root, "platform-tools", "adb.exe"))
        candidates.append(os.path.join(root, "adb", "adb.exe"))
    candidates += [
        os.path.join(local, "Android", "Sdk", "platform-tools", "adb.exe"),
        r"C:\Android\platform-tools\adb.exe",
        r"C:\Users\Public\platform-tools\adb.exe",
        r"D:\Program Files\platform-tools\adb.exe",
        r"E:\platform-tools\adb.exe",
    ]
    # 桌面/下载目录也扫一下（用户可能直接解压在桌面）
    for folder in (
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
    ):
        if folder and os.path.isdir(folder):
            for name in os.listdir(folder):
                sub = os.path.join(folder, name)
                if os.path.isdir(sub):
                    candidate = os.path.join(sub, "platform-tools", "adb.exe")
                    if os.path.isfile(candidate):
                        return candidate
                if name.lower() == "adb.exe" or "platform-tools" in name.lower():
                    candidate = os.path.join(sub, "adb.exe") if os.path.isdir(sub) else sub
                    if os.path.isfile(candidate):
                        return candidate
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return "adb"


ADB_MISSING_HINT = (
    "没有找到 adb.exe。请按以下步骤操作：\n\n"
    "1. 打开网址 developer.android.com/tools/releases/platform-tools\n"
    "2. 下载 \"SDK Platform Tools for Windows\"（zip）\n"
    "3. 解压到任意目录，比如 D:\\platform-tools\n"
    "4. 回到设置页，点 ADB 路径右侧的\"浏览...\"选中解压出来的 adb.exe"
)


def list_devices(adb_path: str = None) -> list:
    """返回 [serial]，adb 不可用时抛 AdbBackendError。"""
    adb_path = adb_path or find_adb()
    try:
        out = subprocess.run(
            [adb_path, "devices"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        ).stdout
    except FileNotFoundError:
        raise AdbBackendError(ADB_MISSING_HINT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AdbBackendError("adb 无法执行：%s" % exc)
    devices = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


class AdbBackend:
    name = "mobile"

    def __init__(self, adb_path: str = None, serial: str = "", refresh_delay_ms: int = 200):
        self.adb_path = adb_path or find_adb()
        self.serial = serial.strip()
        self.refresh_delay = max(0, int(refresh_delay_ms)) / 1000.0
        self._screen = None

    def _adb(self, *args, binary: bool = False, timeout: int = 15):
        command = [self.adb_path]
        if self.serial:
            command += ["-s", self.serial]
        command += list(args)
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AdbBackendError("adb 执行失败：%s" % exc)
        if result.returncode != 0:
            message = result.stderr.decode("utf-8", "ignore").strip()
            raise AdbBackendError("adb 命令失败：%s" % (message or " ".join(args)))
        return result.stdout if binary else result.stdout.decode("utf-8", "ignore")

    def check(self) -> str:
        devices = list_devices(self.adb_path)
        if not devices:
            raise AdbBackendError("没有检测到已连接的安卓设备，请确认 USB 调试已开启")
        if self.serial and self.serial not in devices:
            raise AdbBackendError("设备 %s 不在线，当前在线：%s" % (self.serial, ", ".join(devices)))
        if not self.serial:
            self.serial = devices[0]
        return self.serial

    def screen_size(self) -> tuple:
        if self._screen is None:
            self.screenshot()
        return self._screen

    def click(self, position, hold: float = 0.0) -> None:
        if not position:
            return
        width, height = self.screen_size()
        x = _frac_to_pixel(position[0], width)
        y = _frac_to_pixel(position[1], height)
        self._adb("shell", "input", "tap", str(x), str(y))

    def move(self, position) -> None:
        # 触屏没有 hover 概念，移动即为点击
        pass

    def press_escape(self) -> None:
        self._adb("shell", "input", "keyevent", "4")

    def screenshot(self) -> Image.Image:
        data = self._adb("exec-out", "screencap", "-p", binary=True, timeout=20)
        try:
            image = Image.open(io.BytesIO(data))
            image.load()
        except Exception as exc:
            raise AdbBackendError("手机截图解析失败：%s" % exc)
        self._screen = image.size
        return image

    def capture(self, region) -> Image.Image:
        image = self.screenshot()
        width, height = image.size
        left = _frac_to_pixel(region[0], width)
        top = _frac_to_pixel(region[1], height)
        right = _frac_to_pixel(region[2], width)
        bottom = _frac_to_pixel(region[3], height)
        if right <= left or bottom <= top:
            raise ValueError("截图区域无效")
        return image.crop((left, top, right, bottom))

    def pointer_fraction(self) -> list:
        raise AdbBackendError("手机平台不支持读取指针位置，请用截图取点")
