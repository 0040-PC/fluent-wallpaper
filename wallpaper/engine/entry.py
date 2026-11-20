import ctypes
import logging
import os
import sys
from ctypes import wintypes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)

os.environ["QSG_INFO"] = "0"
os.environ["QSG_RENDER_LOOP"] = "threaded"
os.environ["QT_LOGGING_RULES"] = "qt.scenegraph.*=false;qt.rhi.*=false;qt.vulkan=false"
os.environ["QML_DISABLE_DISK_CACHE"] = "1"
os.environ["QSG_RHI_HDR"] = "scrgb"
os.environ["QSG_RHI_BACKEND"] = "d3d11"

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine.core import WallpaperEngine

_INSTANCE_MUTEX = "Local\\WallpaperEngineInstance"
_ERROR_ALREADY_EXISTS = 183

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL


class MainApp:
    def __init__(self):
        self.engine = None
        self._mutex = None

    def run(self):
        handle = _kernel32.CreateMutexW(None, False, _INSTANCE_MUTEX)
        error = ctypes.get_last_error()
        if not handle:
            print(f"[引擎] 创建实例互斥量失败: {error}")
            return 1
        if error == _ERROR_ALREADY_EXISTS:
            _kernel32.CloseHandle(handle)
            logging.warning(
                "已有引擎实例在运行，本次启动退出；若桌面没有壁纸，请先结束旧的 python 引擎进程"
            )
            return 0
        self._mutex = handle

        try:
            self.engine = WallpaperEngine()
        except RuntimeError as e:
            print(f"[引擎] 启动失败: {e}")
            return 1

        default_plugin = os.path.join(PROJECT_ROOT, "plugins", "DebugOverlay.qml")
        self.engine.load_plugin(default_plugin)
        return self.engine.run()


def main():
    sys.exit(MainApp().run())


if __name__ == "__main__":
    main()
