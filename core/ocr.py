"""常驻式 Windows OCR 引擎。

旧实现每次识别都要新起一个 powershell.exe 进程（冷启动 1~3 秒），
根本谈不上"实时监测"。这里改成：进程只在第一次使用时启动一次，
之后每张图只走一趟 stdin/stdout 通信，单次识别降到几十毫秒，
足以支撑 100ms 级的轮询。
"""

import os
import re
import subprocess
import tempfile
import threading

from PIL import Image


def _windows_powershell() -> str:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    return os.path.join(windir, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")


def _script_path() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "assets", "ocr_server.ps1")


class WindowsOcr:
    """围绕 Windows.Media.Ocr 的常驻进程封装，线程安全。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._process = None
        self._counter = 0
        self._temp_dir = None

    def _next_path(self) -> str:
        if self._temp_dir is None:
            self._temp_dir = tempfile.mkdtemp(prefix="daodan_ocr_")
        self._counter += 1
        return os.path.join(self._temp_dir, "img_%d.png" % self._counter)

    def _ensure_process(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return

        process = subprocess.Popen(
            [
                _windows_powershell(),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                _script_path(),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        first = process.stdout.readline()
        if not first or not first.strip().startswith("READY"):
            process.kill()
            raise RuntimeError("OCR 引擎启动失败：%s" % first.strip() if first else "无输出")
        self._process = process

    def recognize(self, image) -> str:
        if not isinstance(image, Image.Image):
            raise TypeError("recognize 只接受 PIL Image")
        with self._lock:
            self._ensure_process()
            path = self._next_path()
            try:
                image.save(path, format="PNG")
                self._process.stdin.write(path + "\n")
                self._process.stdin.flush()
                line = self._process.stdout.readline()
            except (BrokenPipeError, OSError, ValueError):
                line = ""
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass
            if not line:
                # 进程挂了，下次调用时重启
                self._kill_process()
                raise RuntimeError("OCR 进程无响应")
            text = line.strip()
            if text == "ERROR":
                raise RuntimeError("OCR 识别失败")
            if text == "EMPTY":
                return ""
            return text

    def _kill_process(self) -> None:
        if self._process is not None:
            try:
                self._process.kill()
            except OSError:
                pass
                self._process = None

    def close(self) -> None:
        with self._lock:
            if self._process is not None:
                try:
                    self._process.stdin.write("EXIT\n")
                    self._process.stdin.flush()
                    self._process.wait(timeout=3)
                except (OSError, ValueError, subprocess.TimeoutExpired):
                    self._kill_process()
                self._process = None
            if self._temp_dir and os.path.isdir(self._temp_dir):
                try:
                    for name in os.listdir(self._temp_dir):
                        os.remove(os.path.join(self._temp_dir, name))
                    os.rmdir(self._temp_dir)
                except OSError:
                    pass
                self._temp_dir = None

    @staticmethod
    def parse_number(text: str):
        if not text:
            return None
        matches = re.findall(r"\d[\d\s,]*", text)
        if not matches:
            return None
        raw = matches[-1].replace(",", "").replace(" ", "").strip()
        try:
            return int(raw)
        except ValueError:
            return None
