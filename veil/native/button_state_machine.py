import ctypes
from ctypes import wintypes

from PySide6.QtCore import QObject, Signal, QTimer

from ..platform.win32 import (
    user32,
)
from .hit_test import BUTTON_HT_MAP


class 按钮状态机(QObject):
    minBtnStateChanged = Signal()
    maxBtnStateChanged = Signal()
    closeBtnStateChanged = Signal()
    gripperHoverChanged = Signal()
    minimizeButtonClicked = Signal()
    maximizeButtonClicked = Signal()
    closeButtonClicked = Signal()

    def __init__(self, hwnd, 区域注册表, parent=None):
        super().__init__(parent)
        self._hwnd = hwnd
        self._区域注册表 = 区域注册表
        self._min_btn_state = 0
        self._max_btn_state = 0
        self._close_btn_state = 0
        self._gripper_hover = False
        self._pressing_btn_id = None
        self._capture_active = False
        self._last_ht = None

        self._guard_timer = QTimer(self)
        self._guard_timer.setInterval(16)
        self._guard_timer.timeout.connect(self._轮询守卫)

    @property
    def min_btn_state(self):
        return self._min_btn_state

    @property
    def max_btn_state(self):
        return self._max_btn_state

    @property
    def close_btn_state(self):
        return self._close_btn_state

    @property
    def gripper_hover(self):
        return self._gripper_hover

    @property
    def pressing_btn_id(self):
        return self._pressing_btn_id

    def 更新悬停(self, ht_value):
        if ht_value != self._last_ht:
            self._last_ht = ht_value
            self._应用悬停(ht_value)

    def 处理按下(self, ht_value):
        if ht_value == 9:
            user32.SetCapture(self._hwnd)
            self._capture_active = True
            self._pressing_btn_id = "max"
            self._更新按钮状态("max", 2)
            return

        for btn_id, ht_val in BUTTON_HT_MAP:
            if ht_value == ht_val:
                self._pressing_btn_id = btn_id
                self._更新按钮状态(btn_id, 2)

    def 处理释放(self, ht_value):
        last_pressing_id = self._pressing_btn_id
        if last_pressing_id == "max":
            return False

        self._pressing_btn_id = None
        self._刷新守卫定时器()

        sig_map = {"min": "minimize", "close": "close"}
        for btn_id, ht_val in BUTTON_HT_MAP:
            if last_pressing_id == btn_id and ht_value == ht_val:
                sig_prefix = sig_map.get(btn_id)
                if sig_prefix:
                    getattr(self, f"{sig_prefix}ButtonClicked").emit()
            self._更新按钮状态(btn_id, 0)

        self._应用悬停(ht_value)
        return True

    def 处理最大化释放(self, ht):
        self._capture_active = False
        user32.ReleaseCapture()

        if ht == 9:
            self.maximizeButtonClicked.emit()

        self._更新按钮状态("max", 0)
        self._pressing_btn_id = None
        self._刷新守卫定时器()

        if ht:
            self._应用悬停(ht)
        return True

    def 处理离开(self):
        self._last_ht = None
        for btn_id, _ in BUTTON_HT_MAP:
            self._更新按钮状态(btn_id, 0)
        if self._gripper_hover:
            self._gripper_hover = False
            self.gripperHoverChanged.emit()

    def _应用悬停(self, ht):
        gripper_hover = (ht == 17 and self._区域注册表._gripper_rect is not None)
        if gripper_hover != self._gripper_hover:
            self._gripper_hover = gripper_hover
            self.gripperHoverChanged.emit()

        if self._pressing_btn_id:
            for btn_id, ht_val in BUTTON_HT_MAP:
                if btn_id == self._pressing_btn_id:
                    self._更新按钮状态(btn_id, 2 if ht_val == ht else 0)
                else:
                    self._更新按钮状态(btn_id, 0)
        else:
            for btn_id, ht_val in BUTTON_HT_MAP:
                if ht_val == ht:
                    self._更新按钮状态(btn_id, 1)
                else:
                    self._更新按钮状态(btn_id, 0)

    def _更新按钮状态(self, btn_id, v):
        attr_name = f"_{btn_id}_btn_state"
        if getattr(self, attr_name) != v:
            setattr(self, attr_name, v)
            getattr(self, f"{btn_id}BtnStateChanged").emit()
            self._刷新守卫定时器()

    def _刷新守卫定时器(self):
        active = self._capture_active or (self._pressing_btn_id is not None) or any(
            getattr(self, f"_{btn_id}_btn_state") != 0
            for btn_id, _ in BUTTON_HT_MAP
        )
        if active and not self._guard_timer.isActive():
            self._guard_timer.start()
        elif not active and self._guard_timer.isActive():
            self._guard_timer.stop()

    def _轮询守卫(self):
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        is_lbutton_down = (user32.GetAsyncKeyState(0x01) & 0x8000) != 0

        if self._pressing_btn_id and not is_lbutton_down:
            if self._capture_active:
                self._capture_active = False
                user32.ReleaseCapture()
            self._pressing_btn_id = None
            self._刷新守卫定时器()

        client_pt = wintypes.POINT(pt.x, pt.y)
        user32.ScreenToClient(self._hwnd, ctypes.byref(client_pt))
        cx, cy = client_pt.x, client_pt.y

        for btn_id, _ in BUTTON_HT_MAP:
            current_state = getattr(self, f"_{btn_id}_btn_state")
            rect = self._区域注册表.获取按钮矩形(btn_id)
            if not rect:
                continue
            l, t, r, b = rect
            inside = l <= cx < r and t <= cy < b

            if self._pressing_btn_id == btn_id:
                if inside:
                    self._更新按钮状态(btn_id, 2 if is_lbutton_down else 1)
                else:
                    self._更新按钮状态(btn_id, 0)
            else:
                if not inside and current_state != 0:
                    self._更新按钮状态(btn_id, 0)
                elif inside and current_state == 2 and not is_lbutton_down:
                    self._更新按钮状态(btn_id, 1)