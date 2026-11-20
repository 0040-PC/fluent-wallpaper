import ctypes

from ..platform.win32 import (
    dwmapi,
    _SetPreferredAppMode, _FlushMenuThemes,
)

BACKDROP_VALUES = {"NONE": 1, "MICA": 2, "ACRYLIC": 3, "MICA_ALT": 4, "TRANSPARENT": 1}


def 应用背景材质(hwnd, token):
    value = BACKDROP_VALUES.get(token, 1)
    t = ctypes.c_int(value)
    hr = dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(t), 4)
    return hr == 0


def 应用深色模式(hwnd, dark):
    t = ctypes.c_int(1 if dark else 0)
    hr = dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(t), 4)
    if _SetPreferredAppMode and _FlushMenuThemes:
        _SetPreferredAppMode(2 if dark else 3)
        _FlushMenuThemes()
    return hr == 0


def 应用圆角偏好(hwnd, mode):
    """
    mode: 0=DEFAULT, 1=DONOTROUND, 2=ROUND, 3=ROUNDSMALL
    """
    t = ctypes.c_int(mode)
    hr = dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(t), 4)
    return hr == 0