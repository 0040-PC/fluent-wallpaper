import os
from pathlib import Path

from PySide6.QtGui import QSurfaceFormat, QColor, QGuiApplication
from PySide6.QtCore import QObject, Slot, Signal, Property, QEvent, Qt, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from .native.event_filter import 原生事件过滤器
from .native.window_ops import (
    设置无边框窗口, 恢复边框窗口,
    最小化, 最大化, 还原, 关闭,
    启用缩放, 禁用缩放,
)
from .native.dwm_ops import 应用背景材质, 应用深色模式, 应用圆角偏好
from .native.open_animation import play_open_animation

def _init_rendering():                                        # 模块级：import 时执行，早于 QApplication
    # 仅提供默认值，宿主已设置时一律尊重
    os.environ.setdefault("QSG_RHI_BACKEND", "opengl")
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    os.environ.setdefault("QML_DISABLE_DISK_CACHE", "0")

    fmt = QSurfaceFormat.defaultFormat()
    if fmt.samples() < 0:                                     # 宿主未指定采样数时默认 4x MSAA
        fmt.setSamples(4)
        QSurfaceFormat.setDefaultFormat(fmt)                  # 必须在 QApplication() 之前调用

_init_rendering()

def _get_qml_dir():
    base = Path(__file__).parent
    return base / "qml"

_QML_DIR = _get_qml_dir()
_gripper_component_cache = {}


class Veil(QObject):
    veilAppliedChanged = Signal()
    minBtnStateChanged = Signal()
    maxBtnStateChanged = Signal()
    closeBtnStateChanged = Signal()
    gripperHoverChanged = Signal()
    isMaxChanged = Signal()
    isDarkChanged = Signal()
    backdropChanged = Signal()
    resizableChanged = Signal()
    showGripperChanged = Signal()
    readyChanged = Signal()

    def __init__(self, hwnd, parent):
        super().__init__(parent)
        self.hwnd = hwnd
        self._app = QGuiApplication.instance()
        self._event_filter = 原生事件过滤器(hwnd, parent=self) if hwnd else None
        self._window = None
        self._engine = None # 仅管理对象持有
        self._context_name = "veilCtx"
        self._veil_applied = False
        self._backdrop = "MICA"
        
        # 初始值同步：通过 Qt 原生 API 读取系统主题
        self._is_dark = self._detect_system_dark()
        self._corner_preference = 0
        self._open_animation_played = False
        self._resizable = True
        self._show_gripper = True
        self._ready = False
        
        self._removal_pending = False
        self._caption_rect = None
        self._button_rects = {}
        self._gripper_rect = None

    def _detect_system_dark(self):
        try:
            hints = self._app.styleHints()
            return hints.colorScheme() == Qt.ColorScheme.Dark
        except Exception:
            return True

    def set_window(self, window: QQuickWindow):
        self._window = window

    @staticmethod
    def attach(engine, app, specific_window=None):
        """
        全自动接入入口：支持多次安全调用
        """
        # 1. 注册 QML 模块导入路径
        engine.addImportPath(str(_QML_DIR))

        # 2. 防御性检查：避免重复创建管理单例
        ctx = engine.rootContext()
        existing_manager = ctx.contextProperty("veilCtx")
        
        if isinstance(existing_manager, Veil):
            veil_manager = existing_manager
        else:
            veil_manager = Veil(None, app) # 创建新的管理对象
            veil_manager._engine = engine
            ctx.setContextProperty("veilCtx", veil_manager)

            # 【核心】订阅 Qt 原生系统主题变化信号（Qt 6.5+）
            # 这是全局唯一数据源，主线程安全，即时响应
            def _on_system_color_scheme_changed(scheme):
                new_dark = (scheme == Qt.ColorScheme.Dark)
                if new_dark != veil_manager._is_dark:
                    veil_manager.setDark(new_dark)
            
            hints = app.styleHints()
            hints.colorSchemeChanged.connect(_on_system_color_scheme_changed)
        
        # 3. 处理指定窗口或全局扫描
        if specific_window:
            veil_manager.attach_window(specific_window)
        else:
            # 扫描存量窗口并安装全局过滤器
            for win in app.allWindows():
                veil_manager.attach_window(win)

        # 3. 核心增强：全局事件监听（解决所有动态创建窗口的注入问题）
        # 有借有还流水线：installEventFilter（借）→ aboutToQuit → removeEventFilter（还）
        class WindowWatcher(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Show and isinstance(obj, QQuickWindow):
                    veil_manager.attach_window(obj)
                return False

        watcher = WindowWatcher(app)
        app.installEventFilter(watcher)
        app.aboutToQuit.connect(lambda: app.removeEventFilter(watcher))
        
        # 将管理器引用也挂在 app 上，方便某些场景溯源
        app.setProperty("_veil_manager", veil_manager)
        
        return veil_manager

    @Slot(QObject)
    def attach_window(self, obj):
        """将窗口附加到框架，并在窗口对象上注入 context"""
        if not isinstance(obj, QQuickWindow):
            return
        
        # 已经附加过则跳过
        if obj.property(self._context_name):
            return

        hwnd = int(obj.winId())
        
        # 直接使用 obj 作为 sub_veil 的 parent，实现生命周期同步
        sub_veil = Veil(hwnd, obj)
        sub_veil.set_window(obj)
        
        # 核心：监听销毁信号，确保在窗口消失前卸载原生事件过滤器
        # 闭包捕获 app/filter 引用，不依赖 Veil 子对象存活（Qt parent-child 析构顺序：子先毁 → destroyed 后发）
        app_ref = sub_veil._app
        filter_ref = sub_veil._event_filter
        def _cleanup():
            app_ref.removeNativeEventFilter(filter_ref)
        obj.destroyed.connect(_cleanup)
        
        # 精准注入：只设置窗口对象的动态属性
        obj.setProperty(self._context_name, sub_veil)

        # --- 核心改进：全自动 UI 注入 (ResizeGripper) ---
        # 如果 QML 里没有手动定义 ResizeGripper，则由框架自动注入一个隐藏的默认实例
        self._inject_default_ui(obj, sub_veil)

        sub_veil.apply()

    def _inject_default_ui(self, window, sub_veil):
        """利用 Python 驱动，自动向窗口注入基础 UI 组件"""
        if not self._engine:
            # 尝试从全局获取引擎 (如果是从 sub_veil 调用的，需要上溯)
            manager = self._app.property("_veil_manager")
            if manager:
                engine = manager._engine
            else:
                return
        else:
            engine = self._engine

        # 1. 注入缩放手柄 (ResizeGripper)
        # 检查是否已经存在手动定义的 Gripper (通过类名判断)
        for child in window.contentItem().childItems():
            if "ResizeGripper" in child.metaObject().className():
                return

        gripper_path = _QML_DIR / "Veil" / "ResizeGripper.qml"
        path_str = str(gripper_path)
        if path_str in _gripper_component_cache:
            component = _gripper_component_cache[path_str]
        else:
            component = QQmlComponent(engine, QUrl.fromLocalFile(path_str))
            _gripper_component_cache[path_str] = component

        if component.isError():
            print(f"[Veil] Error loading default gripper: {component.errors()}")
            return

        # 创建实例，parent 设置为 window.contentItem 确保它显示在最上层且随窗缩放
        context = QQmlEngine.contextForObject(window)
        gripper = component.beginCreate(context)
        if gripper:
            gripper.setParentItem(window.contentItem())
            gripper.setParent(window)
            gripper.setProperty("veilCtx", sub_veil)
            gripper.setProperty("z", 99999)
            component.completeCreate()

    @Slot()
    def apply(self):
        if self._veil_applied:
            return
        if self._removal_pending:
            self._removal_pending = False
            return

        if self._caption_rect:
            self._event_filter.区域注册表.注册标题栏(*self._caption_rect)
        for btn_id, rect in self._button_rects.items():
            self._event_filter.区域注册表.注册按钮(btn_id, *rect)
        if self._gripper_rect:
            self._event_filter.区域注册表.注册缩放手柄(*self._gripper_rect)

        if not self._resizable:
            禁用缩放(self.hwnd)

        self._app.installNativeEventFilter(self._event_filter)

        应用深色模式(self.hwnd, self._is_dark)
        应用圆角偏好(self.hwnd, self._corner_preference)

        设置无边框窗口(self.hwnd)

        sm = self._event_filter.按钮状态机
        sm.minBtnStateChanged.connect(self.minBtnStateChanged.emit)
        sm.maxBtnStateChanged.connect(self.maxBtnStateChanged.emit)
        sm.closeBtnStateChanged.connect(self.closeBtnStateChanged.emit)
        sm.gripperHoverChanged.connect(self.gripperHoverChanged.emit)
        self._event_filter.isMaxChanged.connect(self.isMaxChanged.emit)
        sm.minimizeButtonClicked.connect(self.minimize)
        sm.maximizeButtonClicked.connect(self.toggleMaximize)
        sm.closeButtonClicked.connect(self.close)

        self.isMaxChanged.emit()

        self.setBackdrop(self._backdrop)

        self._veil_applied = True
        self.veilAppliedChanged.emit()

        if not self._open_animation_played and self._window:
            self._open_animation_played = True
            anim_group = play_open_animation(self._window)
            # 使用 QueuedConnection 确保在下一帧事件循环再标记 Ready，给 UI 布局留出稳态时间
            anim_group.finished.connect(self._mark_ready, Qt.QueuedConnection)
        else:
            self._mark_ready()

    def _mark_ready(self):
        if not self._ready:
            self._ready = True
            self.readyChanged.emit()

    @Property(bool, notify=readyChanged)
    def ready(self):
        return self._ready

    @Slot()
    def remove(self):
        if not self._veil_applied:
            return

        self._veil_applied = False
        self._removal_pending = True
        self.veilAppliedChanged.emit()
        self.backdropChanged.emit()
        self._disconnect_event_filter_signals()

        _handled = False
        def on_frame_swapped():
            nonlocal _handled
            if _handled: return
            _handled = True
            self._removal_pending = False
            self._window.frameSwapped.disconnect(on_frame_swapped)
            self._app.removeNativeEventFilter(self._event_filter)
            恢复边框窗口(self.hwnd)

        self._window.frameSwapped.connect(on_frame_swapped, Qt.QueuedConnection)

    def _disconnect_event_filter_signals(self):
        ef = self._event_filter
        if not ef:
            return
        sm = ef.按钮状态机
        sm.minBtnStateChanged.disconnect(self.minBtnStateChanged.emit)
        sm.maxBtnStateChanged.disconnect(self.maxBtnStateChanged.emit)
        sm.closeBtnStateChanged.disconnect(self.closeBtnStateChanged.emit)
        sm.gripperHoverChanged.disconnect(self.gripperHoverChanged.emit)
        ef.isMaxChanged.disconnect(self.isMaxChanged.emit)
        sm.minimizeButtonClicked.disconnect(self.minimize)
        sm.maximizeButtonClicked.disconnect(self.toggleMaximize)
        sm.closeButtonClicked.disconnect(self.close)

    @Property(int, notify=minBtnStateChanged)
    def minBtnState(self):
        return self._event_filter.按钮状态机.min_btn_state

    @Property(int, notify=maxBtnStateChanged)
    def maxBtnState(self):
        return self._event_filter.按钮状态机.max_btn_state

    @Property(int, notify=closeBtnStateChanged)
    def closeBtnState(self):
        return self._event_filter.按钮状态机.close_btn_state

    @Property(bool, notify=gripperHoverChanged)
    def gripperHover(self):
        return self._event_filter.按钮状态机.gripper_hover

    @Property(bool, notify=isMaxChanged)
    def isMax(self):
        return self._event_filter.is_max

    @Property(bool, notify=veilAppliedChanged)
    def veilApplied(self):
        return self._veil_applied

    @Property(bool, notify=isDarkChanged)
    def isDark(self):
        return self._is_dark

    @Property(str, notify=backdropChanged)
    def backdrop(self):
        return self._backdrop

    @Slot(int, int, int, int)
    def setCaptionRect(self, x, y, w, h):
        self._caption_rect = (x, y, w, h)
        if self._event_filter:
            self._event_filter.区域注册表.注册标题栏(x, y, w, h)

    @Slot(str, int, int, int, int)
    def setButtonRect(self, btn_id, x, y, w, h):
        self._button_rects[btn_id] = (x, y, w, h)
        if self._event_filter:
            self._event_filter.区域注册表.注册按钮(btn_id, x, y, w, h)

    @Slot(int, int, int, int)
    def setGripperRect(self, x, y, w, h):
        self._gripper_rect = (x, y, w, h)
        if self._event_filter:
            self._event_filter.区域注册表.注册缩放手柄(x, y, w, h)

    @Slot()
    def clearGripperRect(self):
        self._gripper_rect = None
        if self._event_filter:
            self._event_filter.区域注册表.清除缩放手柄()

    @Slot()
    def minimize(self):
        最小化(self.hwnd)

    @Slot()
    def toggleMaximize(self):
        if self._event_filter and self._event_filter.is_max:
            还原(self.hwnd)
        else:
            最大化(self.hwnd)

    @Slot()
    def close(self):
        关闭(self.hwnd)

    @Slot(str)
    def setBackdrop(self, token):
        self._backdrop = token
        if token == "NONE":
            # 纯色不透明：仅覆盖颜色，不调用 DWM 切换，避免 1 帧的闪烁
            bg_color = "#121214" if self._is_dark else "#FFFFFF"
            self._window.setColor(QColor(bg_color))
        elif token == "TRANSPARENT":
            # 纯透明无材质
            self._window.setColor(QColor("transparent"))
            应用背景材质(self.hwnd, "TRANSPARENT")
        else:
            # 材质：MICA, ACRYLIC, MICA_ALT
            self._window.setColor(QColor("transparent"))
            应用背景材质(self.hwnd, token)
        self.backdropChanged.emit()

    @Slot(bool)
    def setDark(self, dark):
        # 如果是全局管理器，通知所有已注册的窗口
        if self.hwnd is None:
            self._is_dark = dark
            self.isDarkChanged.emit()
            for win in self._app.allWindows():
                sub_ctx = win.property(self._context_name)
                if sub_ctx and sub_ctx != self:
                    sub_ctx.setDark(dark)
            return

        # 子管理器：先更新原生窗口装饰
        应用深色模式(self.hwnd, dark)
        # 无论 DWM 调用是否成功，都必须更新属性并发射信号
        # 否则 QML 绑定永远收不到通知
        self._is_dark = dark
        if self._backdrop == "NONE":
            self.setBackdrop("NONE")
        self.isDarkChanged.emit()

    @Slot(int)
    def setCornerPreference(self, mode):
        self._corner_preference = mode
        应用圆角偏好(self.hwnd, mode)

    @Slot(bool)
    def setResizable(self, enabled):
        if self._resizable == enabled:
            return
        self._resizable = enabled
        if self._veil_applied:
            if enabled:
                启用缩放(self.hwnd)
            else:
                禁用缩放(self.hwnd)
        self.resizableChanged.emit()

    @Property(bool, notify=resizableChanged)
    def resizable(self):
        return self._resizable

    @Property(bool, notify=showGripperChanged)
    def showGripper(self):
        return self._show_gripper

    @Slot(bool)
    def setShowGripper(self, show):
        if self._show_gripper == show:
            return
        self._show_gripper = show
        self.showGripperChanged.emit()