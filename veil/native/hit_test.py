import ctypes
from ctypes import wintypes

from ..platform.win32 import (
    user32,
)

BUTTON_HT_MAP = (("min", 8), ("max", 9), ("close", 20))


class 区域注册表:
    def __init__(self):
        self._button_rects = {}
        self._caption_rect = None
        self._gripper_rect = None

    def 注册按钮(self, btn_id, x, y, w, h):
        self._button_rects[btn_id] = (x, y, x + w, y + h)

    def 注册标题栏(self, x, y, w, h):
        self._caption_rect = (x, y, x + w, y + h)

    def 注册缩放手柄(self, x, y, w, h):
        self._gripper_rect = (x, y, x + w, y + h)

    def 清除缩放手柄(self):
        self._gripper_rect = None

    def 获取按钮矩形(self, btn_id):
        return self._button_rects.get(btn_id)

    def 命中测试(self, client_x, client_y):
        for btn_id, ht_value in BUTTON_HT_MAP:
            rect = self._button_rects.get(btn_id)
            if rect:
                l, t, r, b = rect
                if l <= client_x < r and t <= client_y < b:
                    return ht_value
        if self._gripper_rect:
            l, t, r, b = self._gripper_rect
            if l <= client_x < r and t <= client_y < b:
                return 17
        if self._caption_rect:
            l, t, r, b = self._caption_rect
            if l <= client_x < r and t <= client_y < b:
                return 2
        return None


class 边框命中测试:
    def __init__(self, corner_size=12, edge_size=4):
        self._corner_size = corner_size
        self._edge_size = edge_size

    def 测试(self, hwnd, screen_x, screen_y):
        window_rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(window_rect))

        cs = self._corner_size
        es = self._edge_size

        if (screen_x < window_rect.left + cs
                and screen_y < window_rect.top + cs):
            return 13
        if (screen_x > window_rect.right - cs
                and screen_y < window_rect.top + cs):
            return 14
        if (screen_x < window_rect.left + cs
                and screen_y > window_rect.bottom - cs):
            return 16
        if (screen_x > window_rect.right - cs
                and screen_y > window_rect.bottom - cs):
            return 17

        if screen_x < window_rect.left + es:
            return 10
        if screen_x > window_rect.right - es:
            return 11
        if screen_y < window_rect.top + es:
            return 12
        if screen_y > window_rect.bottom - es:
            return 15

        return None


def 提取屏幕坐标(lParam):
    screen_x = lParam & 0xFFFF
    screen_y = (lParam >> 16) & 0xFFFF
    if screen_x > 32767:
        screen_x -= 65536
    if screen_y > 32767:
        screen_y -= 65536
    return screen_x, screen_y


def 屏幕到窗口坐标(hwnd, screen_x, screen_y):
    pt = wintypes.POINT(screen_x, screen_y)
    user32.ScreenToClient(hwnd, ctypes.byref(pt))
    return pt.x, pt.y