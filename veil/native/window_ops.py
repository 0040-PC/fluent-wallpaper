from ..platform.win32 import (
    user32,
)


def 设置无边框窗口(hwnd):
    style = user32.GetWindowLongPtrW(hwnd, -16)

    style |= (
        0x00040000
        | 0x00C00000
        | 0x00080000
        | 0x00010000
        | 0x00020000
    )

    user32.SetWindowLongPtrW(hwnd, -16, style)

    user32.SetWindowPos(
        hwnd, 0, 0, 0, 0, 0,
        0x0020
        | 0x0002
        | 0x0001
        | 0x0004
        | 0x0010
    )


def 最小化(hwnd):
    user32.PostMessageW(hwnd, 0x0112, 0xF020, 0)


def 最大化(hwnd):
    user32.PostMessageW(hwnd, 0x0112, 0xF030, 0)


def 还原(hwnd):
    user32.PostMessageW(hwnd, 0x0112, 0xF120, 0)


def 关闭(hwnd):
    user32.PostMessageW(hwnd, 0x0112, 0xF060, 0)


def 恢复边框窗口(hwnd):
    style = user32.GetWindowLongPtrW(hwnd, -16)

    style |= (
        0x00C00000
        | 0x00040000
        | 0x00080000
        | 0x00010000
        | 0x00020000
    )

    user32.SetWindowLongPtrW(hwnd, -16, style)

    user32.SetWindowPos(
        hwnd, 0, 0, 0, 0, 0,
        0x0020
        | 0x0002
        | 0x0001
        | 0x0004
        | 0x0010
    )


def 启用缩放(hwnd):
    style = user32.GetWindowLongPtrW(hwnd, -16)
    style |= 0x00040000
    user32.SetWindowLongPtrW(hwnd, -16, style)
    user32.SetWindowPos(
        hwnd, 0, 0, 0, 0, 0,
        0x0020 | 0x0002 | 0x0001 | 0x0004 | 0x0010
    )


def 禁用缩放(hwnd):
    style = user32.GetWindowLongPtrW(hwnd, -16)
    style &= ~0x00040000
    user32.SetWindowLongPtrW(hwnd, -16, style)
    user32.SetWindowPos(
        hwnd, 0, 0, 0, 0, 0,
        0x0020 | 0x0002 | 0x0001 | 0x0004 | 0x0010
    )


def 显示系统菜单(hwnd, screen_x, screen_y, resizable=True):
    """
    在指定屏幕坐标处显示原生系统菜单。
    使用 GetSystemMenu + TrackPopupMenu，完全绕过 DefWindowProc 的命中测试，
    适用于消除了非客户区的自定义边框窗口（Chrome、VS Code 等均使用此方案）。
    """
    hmenu = user32.GetSystemMenu(hwnd, False)
    if not hmenu:
        return

    is_max = bool(user32.IsZoomed(hwnd))

    def _enable(cmd, enabled):
        user32.EnableMenuItem(hmenu, cmd, 0x0000 | (0x0000 if enabled else 0x0001))

    _enable(0xF120,  is_max)
    _enable(0xF010,     not is_max)
    _enable(0xF000,     not is_max and resizable)
    _enable(0xF020, True)
    _enable(0xF030, not is_max)
    _enable(0xF060,    True)

    user32.SetForegroundWindow(hwnd)

    flags = 0x0000 | 0x0000 | 0x0002 | 0x0100
    cmd = user32.TrackPopupMenu(hmenu, flags, screen_x, screen_y, 0, hwnd, None)

    if cmd:
        user32.PostMessageW(hwnd, 0x0112, cmd, 0)