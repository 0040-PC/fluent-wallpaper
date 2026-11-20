import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

from ..platform.win32 import (
    user32, MONITORINFO,
)
from .hit_test import (
    区域注册表, 边框命中测试, 提取屏幕坐标, 屏幕到窗口坐标,
)
from .button_state_machine import 按钮状态机
from .window_ops import 显示系统菜单


class 原生事件过滤器(QAbstractNativeEventFilter, QObject):

    isMaxChanged = Signal()

    def __init__(self, hwnd, parent=None):
        QAbstractNativeEventFilter.__init__(self)
        QObject.__init__(self, parent)
        self._hwnd = hwnd
        self._is_max = bool(user32.IsZoomed(hwnd))

        self._区域注册表 = 区域注册表()
        self._边框命中测试 = 边框命中测试()
        self._按钮状态机 = 按钮状态机(hwnd, self._区域注册表, parent=self)

    @property
    def 区域注册表(self):
        return self._区域注册表

    @property
    def 按钮状态机(self):
        return self._按钮状态机

    @property
    def is_max(self):
        return self._is_max

    def nativeEventFilter(self, et, m_ptr):
        if et != b"windows_generic_MSG":
            return False, 0

        msg = wintypes.MSG.from_address(int(m_ptr))
        if msg.hWnd != self._hwnd:
            return False, 0

        if msg.message == 0x0083 and msg.wParam:
            return self._处理非客户区计算尺寸(msg)

        if msg.message == 0x0084:
            return self._处理命中测试(msg)

        if msg.message == 0x00A0:
            return self._处理非客户区鼠标移动(msg)

        if msg.message == 0x02A2:
            if self._按钮状态机._capture_active:
                return False, 0
            return self._处理非客户区鼠标离开(msg)

        if msg.message == 0x00A1 and msg.wParam in (8, 9, 20):
            return self._处理非客户区按钮按下(msg)

        if msg.message == 0x00A2 and msg.wParam in (8, 9, 20):
            return self._处理非客户区按钮释放(msg)
            
        if msg.message == 0x00A5:
            return self._处理非客户区右键释放(msg)

        if msg.message == 0x0202:
            return self._处理左键释放(msg)

        if msg.message == 0x0205:
            return self._处理右键释放(msg)

        if msg.message == 0x0200:
            return self._处理鼠标移动(msg)

        if msg.message == 0x0005:
            return self._处理尺寸变化(msg)

        return False, 0

    def _处理非客户区计算尺寸(self, msg):
        if not msg.lParam:
            return False, 0

        rect = wintypes.RECT.from_address(msg.lParam)

        original_top = rect.top
        user32.DefWindowProcW(self._hwnd, 0x0083, msg.wParam, msg.lParam)
        rect.top = original_top

        if user32.IsZoomed(self._hwnd):
            monitor_info = MONITORINFO()
            monitor_info.cbSize = ctypes.sizeof(MONITORINFO)
            user32.GetMonitorInfoW(
                user32.MonitorFromWindow(self._hwnd, 2),
                ctypes.byref(monitor_info)
            )
            work = monitor_info.rcWork
            rect.left = work.left
            rect.top = work.top
            rect.right = work.right
            rect.bottom = work.bottom

        return True, 0

    def _处理命中测试(self, msg):
        screen_x, screen_y = 提取屏幕坐标(msg.lParam)
        client_x, client_y = 屏幕到窗口坐标(self._hwnd, screen_x, screen_y)

        if user32.IsZoomed(self._hwnd):
            ht = self._区域注册表.命中测试(client_x, client_y)
            self._按钮状态机.更新悬停(ht if ht is not None else 0)
            if ht is not None:
                return True, ht
            return False, 0

        ht = self._边框命中测试.测试(self._hwnd, screen_x, screen_y)
        if ht is not None:
            return True, ht

        ht = self._区域注册表.命中测试(client_x, client_y)
        self._按钮状态机.更新悬停(ht if ht is not None else 0)
        if ht is not None:
            return True, ht

        return False, 0

    def _处理非客户区鼠标移动(self, msg):
        self._按钮状态机.更新悬停(msg.wParam)
        return False, 0

    def _处理非客户区鼠标离开(self, _msg):
        self._按钮状态机.处理离开()
        return False, 0

    def _处理非客户区按钮按下(self, msg):
        self._按钮状态机.处理按下(msg.wParam)
        return True, 0

    def _处理非客户区按钮释放(self, msg):
        handled = self._按钮状态机.处理释放(msg.wParam)
        return handled, 0

    def _处理非客户区右键释放(self, msg):
        """处理非客户区右键释放 (WM_NCRBUTTONUP)"""
        if msg.wParam == 2:
            screen_x, screen_y = 提取屏幕坐标(msg.lParam)
            显示系统菜单(self._hwnd, screen_x, screen_y)
            return True, 0
        return False, 0

    def _处理左键释放(self, _msg):
        if self._按钮状态机.pressing_btn_id == "max":
            pt = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            client_pt = wintypes.POINT(pt.x, pt.y)
            user32.ScreenToClient(self._hwnd, ctypes.byref(client_pt))
            ht = self._区域注册表.命中测试(client_pt.x, client_pt.y)
            self._按钮状态机.处理最大化释放(ht)
            return True, 0
        return False, 0

    def _处理右键释放(self, _msg):
        """处理客户区右键释放 (WM_RBUTTONUP)"""
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        client_pt = wintypes.POINT(pt.x, pt.y)
        user32.ScreenToClient(self._hwnd, ctypes.byref(client_pt))
        
        ht = self._区域注册表.命中测试(client_pt.x, client_pt.y)
        if ht == 2:
            显示系统菜单(self._hwnd, pt.x, pt.y)
            return True, 0
        return False, 0

    def _处理鼠标移动(self, _msg):
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        client_pt = wintypes.POINT(pt.x, pt.y)
        user32.ScreenToClient(self._hwnd, ctypes.byref(client_pt))
        ht = self._区域注册表.命中测试(client_pt.x, client_pt.y)
        self._按钮状态机.更新悬停(ht if ht is not None else 0)
        return False, 0

    def _处理尺寸变化(self, msg):
        new_is_max = (msg.wParam == 2)
        if self._is_max != new_is_max:
            self._is_max = new_is_max
            self.isMaxChanged.emit()
        return False, 0
