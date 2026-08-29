import ctypes
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path


_MUTEX_HANDLE = None


def _log(message: str) -> None:
    """启动追踪日志：pythonw 没有控制台，出了问题看 logs/boot.log。"""
    try:
        log_dir = Path(__file__).resolve().parent / "logs"
        log_dir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_dir / "boot.log", "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (stamp, message))
    except OSError:
        pass


def _configure_qt_plugin_path() -> None:
    if os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"):
        return
    python_dir = Path(sys.executable).resolve().parent
    plugin_dir = (
        python_dir.parent
        / "Lib"
        / "site-packages"
        / "PyQt5"
        / "Qt5"
        / "plugins"
    )
    if plugin_dir.exists():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugin_dir)


def _pythonw() -> str:
    candidate = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return candidate if os.path.exists(candidate) else sys.executable


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


if __name__ == "__main__":
    _log("启动：python=%s admin=%s" % (sys.executable, is_admin()))

    # 任何未捕获异常都落盘，避免 pythonw 静默死亡
    def _excepthook(exc_type, exc_value, exc_tb):
        _log("未捕获异常：\n%s" % "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))

    sys.excepthook = _excepthook

    if not is_admin():
        script = os.path.abspath(__file__)
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            _pythonw(),
            '"%s"' % script,
            None,
            1,
        )
        _log("请求管理员权限，ShellExecute 返回 %s（<=32 表示失败）" % result)
        sys.exit(0)

    kernel32 = ctypes.windll.kernel32
    _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, "Local\\DaoDanHelper")
    if kernel32.GetLastError() == 183:
        _log("已有实例在运行，退出")
        ctypes.windll.user32.MessageBoxW(0, "捣蛋助手已经在运行。", "捣蛋助手", 0x40)
        sys.exit(0)

    try:
        _configure_qt_plugin_path()

        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QApplication

        from app.main_window import MainWindow

        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        _log("主窗口已显示")
        app.exec_()
        # 监测线程可能卡在 adb 通信上，事件循环结束后强制结束进程，
        # 避免 pythonw 残留占用单实例锁导致下次无法启动
        _log("窗口已关闭，进程退出")
        os._exit(0)
    except Exception:
        error = traceback.format_exc()
        _log("启动失败：\n%s" % error)
        try:
            ctypes.windll.user32.MessageBoxW(
                0, error, "捣蛋助手启动失败", 0x10
            )
        except Exception:
            pass
        os._exit(1)
