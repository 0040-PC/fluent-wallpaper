import ctypes
import logging
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, QTimer, Signal

logger = logging.getLogger("engine.desktop")

u32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

u32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
u32.FindWindowW.restype = wintypes.HWND
u32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
u32.FindWindowExW.restype = wintypes.HWND
u32.SendMessageTimeoutW.argtypes = [
    wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM,
    ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(wintypes.DWORD),
]
u32.SendMessageTimeoutW.restype = ctypes.c_ssize_t
u32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
u32.EnumWindows.restype = wintypes.BOOL
u32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
u32.SetParent.restype = wintypes.HWND
u32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LPARAM]
u32.SetWindowLongPtrW.restype = wintypes.LPARAM
u32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
u32.GetWindowLongPtrW.restype = wintypes.LPARAM
u32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, ctypes.c_uint,
]
u32.SetWindowPos.restype = wintypes.BOOL
u32.GetSystemMetrics.argtypes = [ctypes.c_int]
u32.GetSystemMetrics.restype = ctypes.c_int
u32.GetWindow.argtypes = [wintypes.HWND, ctypes.c_uint]
u32.GetWindow.restype = wintypes.HWND
u32.GetParent.argtypes = [wintypes.HWND]
u32.GetParent.restype = wintypes.HWND
u32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
u32.RegisterWindowMessageW.restype = wintypes.UINT
u32.IsWindow.argtypes = [wintypes.HWND]
u32.IsWindow.restype = wintypes.BOOL


class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


dwmapi.DwmExtendFrameIntoClientArea.argtypes = [wintypes.HWND, ctypes.POINTER(MARGINS)]
dwmapi.DwmExtendFrameIntoClientArea.restype = ctypes.c_long


WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _find_shell_view():
    shell_view = None
    container = None

    def enum_proc(hwnd, _lparam):
        nonlocal shell_view, container
        shell = u32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
        if shell:
            shell_view = shell
            container = hwnd
            return False
        return True

    u32.EnumWindows(WNDENUMPROC(enum_proc), 0)

    if not shell_view:
        progman = u32.FindWindowW("Progman", "Program Manager")
        if progman:
            shell = u32.FindWindowExW(progman, None, "SHELLDLL_DefView", None)
            if shell:
                shell_view = shell
                container = progman

    return shell_view, container


def find_desktop_anchor():
    progman = u32.FindWindowW("Progman", "Program Manager")
    if not progman:
        return None

    shell_view, container = _find_shell_view()

    workerw = u32.FindWindowExW(progman, None, "WorkerW", None)
    if not workerw:
        u32.SendMessageTimeoutW(
            progman,
            0x052C,  # 未记录消息，触发生成 WorkerW 窗口（桌面嵌入社区已知技巧）
            0, 0, 0x0002, 1000, ctypes.byref(wintypes.DWORD()),
        )
        shell_view, container = _find_shell_view()

    if not shell_view:
        return None

    return {"progman": progman, "shell_view": shell_view, "container": container}


def _is_ignorable_window(hwnd):
    ex_style = u32.GetWindowLongPtrW(hwnd, -20)
    return bool(ex_style & 0x00000080) or bool(ex_style & 0x00000020)


def check_intervening_windows(engine_hwnd, shell_view, container):
    intervening_count = 0
    found_shell = False
    found_engine = False

    curr = u32.GetWindow(container, 5)
    while curr:
        if curr == shell_view:
            found_shell = True
        elif curr == engine_hwnd:
            found_engine = True
            break
        elif found_shell:
            style = u32.GetWindowLongPtrW(curr, -16)
            if style & 0x10000000 and not _is_ignorable_window(curr):
                intervening_count += 1
        curr = u32.GetWindow(curr, 2)

    is_at_back = found_engine and not u32.GetWindow(engine_hwnd, 2)

    return {
        "has_intervening": intervening_count > 0,
        "intervening_count": intervening_count,
        "is_at_back": is_at_back,
    }


class WinEventFilter(QAbstractNativeEventFilter):
    def __init__(self, hwnd, on_taskbar_created=None):
        super().__init__()
        self._hwnd = hwnd
        self._on_taskbar_created = on_taskbar_created
        self._taskbar_created_msg = u32.RegisterWindowMessageW("TaskbarCreated")

    def cleanup(self):
        self._on_taskbar_created = None

    def nativeEventFilter(self, event_type, message):
        if event_type != b"windows_generic_MSG":
            return False, 0
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == self._taskbar_created_msg:
            if self._on_taskbar_created:
                self._on_taskbar_created()
            return False, 0
        if msg.message == 0x0083 and msg.hWnd == self._hwnd:
            return True, 0
        return False, 0


class DesktopEmbedder(QObject):
    def apply_win32_settings(self, hwnd):
        margins = MARGINS(-1, -1, -1, -1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

    def embed(self, hwnd):
        for attempt in range(3):
            anchor = find_desktop_anchor()
            if not anchor:
                logger.warning("桌面锚点定位失败")
                continue

            shell_view = anchor["shell_view"]
            container = anchor["container"]
            progman = anchor["progman"]

            if container and not u32.IsWindow(container):
                container = None
            if progman and not u32.IsWindow(progman):
                progman = None

            chosen_parent = container or progman
            if not chosen_parent:
                logger.warning("桌面锚点无效: shell_view=%s", shell_view)
                continue

            logger.info("嵌入桌面层: 容器=%s 图标层=%s", chosen_parent, shell_view)

            u32.SetWindowLongPtrW(hwnd, -16, 0x40000000 | 0x04000000)
            u32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                0x0020 | 0x0002 | 0x0001 | 0x0004 | 0x0010,
            )
            u32.SetWindowLongPtrW(
                hwnd, -20,
                0x00080000 | 0x00000080 | 0x08000000 | 0x00000020,
            )
            u32.SetParent(hwnd, 0)
            u32.SetParent(hwnd, chosen_parent)

            if u32.GetParent(hwnd) != chosen_parent and progman and chosen_parent != progman:
                u32.SetParent(hwnd, progman)

            u32.SetWindowPos(
                hwnd, shell_view, 0, 0,
                u32.GetSystemMetrics(0), u32.GetSystemMetrics(1),
                0x0020 | 0x0040 | 0x0010,
            )

            if u32.GetParent(hwnd) == chosen_parent:
                logger.info("嵌入完成: hwnd=%d 父窗口=%s", int(hwnd), chosen_parent)
                return True
            logger.warning("第%d次嵌入未生效", attempt + 1)

        logger.error("3 次嵌入重试全部失败")
        return False


class ZOrderMonitor(QObject):
    renderPauseChanged = Signal(bool)
    windowRecreationNeeded = Signal()

    def __init__(self, desktop_embedder, parent=None):
        super().__init__(parent)
        self._desktop_embedder = desktop_embedder
        self._hwnd = None
        self._monitoring_enabled = True
        self._last_anchor = None
        self._reembed_active = False
        self._last_paused = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.check)

    def start(self, hwnd):
        self._hwnd = hwnd
        self._timer.start(2000)

    def update_hwnd(self, hwnd):
        self._hwnd = hwnd

    def set_monitoring_enabled(self, enabled):
        self._monitoring_enabled = enabled

    def schedule_reembed(self):
        if self._reembed_active:
            return
        self._reembed_active = True
        self._reembed_step(0)

    def _reembed_step(self, index):
        if not self._reembed_active:
            return
        if self._do_reembed():
            self._reembed_active = False
            logger.info("重嵌入成功")
            return
        delays = [200, 500, 1000, 1500, 2500]
        if index < len(delays):
            QTimer.singleShot(delays[index], lambda: self._reembed_step(index + 1))
        else:
            self._reembed_active = False
            logger.warning("重嵌入全部失败，触发窗口重建")
            self.windowRecreationNeeded.emit()

    def _do_reembed(self):
        self._last_anchor = None
        if not self._hwnd:
            return False
        result = self._desktop_embedder.embed(self._hwnd)
        self.check()
        return result

    def _emit_paused(self, paused):
        if self._last_paused != paused:
            self._last_paused = paused
            logger.info("渲染暂停状态: %s", paused)
            self.renderPauseChanged.emit(paused)

    def check(self):
        if not self._monitoring_enabled or not self._hwnd:
            return

        anchor = find_desktop_anchor()
        if not anchor:
            return

        shell_view = anchor["shell_view"]
        container = anchor["container"]
        if not shell_view or not container:
            return

        key = (container, shell_view)
        anchor_changed = key != self._last_anchor
        if anchor_changed or u32.GetParent(self._hwnd) != container:
            if not self._desktop_embedder.embed(self._hwnd):
                self.windowRecreationNeeded.emit()
                return
            self._last_anchor = key

        check = check_intervening_windows(self._hwnd, shell_view, container)
        if check["is_at_back"]:
            u32.SetWindowPos(
                self._hwnd, shell_view, 0, 0, 0, 0,
                0x0001 | 0x0002 | 0x0010 | 0x0040,
            )
            self._emit_paused(False)
        elif check["has_intervening"]:
            self._emit_paused(True)
        else:
            self._emit_paused(False)
            if u32.GetWindow(self._hwnd, 3) != shell_view:
                u32.SetWindowPos(
                    self._hwnd, shell_view, 0, 0, 0, 0,
                    0x0001 | 0x0002 | 0x0010 | 0x0040,
                )
