from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QAbstractAnimation


def play_open_animation(window, scale=0.92, duration=200):
    if not window:
        return

    target_x = window.x()
    target_y = window.y()
    target_w = window.width()
    target_h = window.height()

    center_x = target_x + target_w // 2
    center_y = target_y + target_h // 2

    start_w = int(target_w * scale)
    start_h = int(target_h * scale)
    start_x = center_x - start_w // 2
    start_y = center_y - start_h // 2

    window.setX(start_x)
    window.setY(start_y)
    window.setWidth(start_w)
    window.setHeight(start_h)
    window.setOpacity(0.0)

    curve = QEasingCurve.OutCubic

    group = QParallelAnimationGroup(window)
    group.addAnimation(_make_anim(window, b"x", start_x, target_x, duration, curve))
    group.addAnimation(_make_anim(window, b"y", start_y, target_y, duration, curve))
    group.addAnimation(_make_anim(window, b"width", start_w, target_w, duration, curve))
    group.addAnimation(_make_anim(window, b"height", start_h, target_h, duration, curve))
    group.addAnimation(_make_anim(window, b"opacity", 0.0, 1.0, duration, curve))

    group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
    return group


def _make_anim(target, prop, start_val, end_val, duration, curve):
    anim = QPropertyAnimation(target, prop)
    anim.setDuration(duration)
    anim.setStartValue(start_val)
    anim.setEndValue(end_val)
    anim.setEasingCurve(curve)
    return anim