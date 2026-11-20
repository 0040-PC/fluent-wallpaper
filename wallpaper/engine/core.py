import logging
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QDataStream, QObject, Property, Qt, Signal
from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from PySide6.QtNetwork import QLocalServer
from PySide6.QtQml import QQmlEngine
from PySide6.QtQuick import QQuickWindow

from .desktop import DesktopEmbedder, WinEventFilter, ZOrderMonitor
from .plugins import PluginManager

logger = logging.getLogger("engine")


class EngineStatus(QObject):
    pausedChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paused = False

    @Property(bool, notify=pausedChanged)
    def isPaused(self):
        return self._paused

    def set_paused(self, paused):
        if self._paused != paused:
            self._paused = paused
            self.pausedChanged.emit(paused)


class IPCServer(QObject):
    loadPluginReceived = Signal(str)
    resumeReceived = Signal()
    pauseReceived = Signal()
    stopReceived = Signal()

    SERVER_NAME = "WallpaperEngineControl"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server = None

    def start(self):
        self._server = QLocalServer(self)
        QLocalServer.removeServer(self.SERVER_NAME)

        for attempt in range(3):
            if self._server.listen(self.SERVER_NAME):
                self._server.newConnection.connect(self._handle_connection)
                logger.info("正在监听控制指令: %s", self.SERVER_NAME)
                return True
            logger.warning(
                "IPC 启动失败 (%d/3): %s", attempt + 1, self._server.errorString()
            )
            QLocalServer.removeServer(self.SERVER_NAME)
            time.sleep(0.3)

        logger.error("IPC 服务最终启动失败，外部指令不可用")
        return False

    def _handle_connection(self):
        socket = self._server.nextPendingConnection()
        if not socket:
            return
        socket.readyRead.connect(self._on_ready_read)
        socket.disconnected.connect(socket.deleteLater)

    def _on_ready_read(self):
        socket = self.sender()
        if socket:
            self._read_command(socket)

    def _read_command(self, socket):
        if socket.bytesAvailable() <= 0:
            socket.disconnectFromServer()
            return

        stream = QDataStream(socket)
        stream.startTransaction()
        command = stream.readString()
        qml_path = None
        if command == "LOAD_PLUGIN":
            qml_path = stream.readString()
        if not stream.commitTransaction():
            return

        if command == "LOAD_PLUGIN" and qml_path:
            self.loadPluginReceived.emit(qml_path)
        elif command == "RESUME_RENDER":
            self.resumeReceived.emit()
        elif command == "PAUSE_RENDER":
            self.pauseReceived.emit()
        elif command == "STOP":
            self.stopReceived.emit()
        elif command and command != "PING":
            logger.warning("未知指令: %s", command)

        socket.disconnectFromServer()


class WallpaperEngine(QObject):
    def __init__(self):
        super().__init__()
        self._setup_format()

        self.app = QGuiApplication.instance() or QGuiApplication([])
        self.window = self._create_window()
        self.qml_engine = QQmlEngine(self)

        self.status = EngineStatus(self)
        self.qml_engine.rootContext().setContextProperty("engineStatus", self.status)

        self.plugins = PluginManager(
            self.qml_engine, Path(__file__).resolve().parent.parent, self
        )
        self.desktop = DesktopEmbedder(self)
        self.z_order = ZOrderMonitor(self.desktop, self)
        self.ipc = IPCServer(self)

        self._manual_paused = False
        self._occluded = False
        self._recreating = False

        self.hwnd = self._show_and_embed(self.window)
        self.win_filter = WinEventFilter(self.hwnd, self.z_order.schedule_reembed)
        self.app.installNativeEventFilter(self.win_filter)
        self.z_order.start(self.hwnd)
        self._connect_signals()

        if not self.ipc.start():
            raise RuntimeError("无法启动控制服务器 WallpaperEngineControl")

    def _setup_format(self):
        fmt = QSurfaceFormat()
        fmt.setSamples(2)
        fmt.setAlphaBufferSize(8)
        fmt.setSwapInterval(1)
        QSurfaceFormat.setDefaultFormat(fmt)

    def _create_window(self):
        window = QQuickWindow()
        window.setTitle("Veil Wallpaper Engine")
        window.setFlags(
            Qt.Window | Qt.FramelessWindowHint | Qt.WindowTransparentForInput
        )
        window.setColor(Qt.transparent)
        return window

    def _show_and_embed(self, window):
        window.show()
        hwnd = int(window.winId())
        self.desktop.apply_win32_settings(hwnd)
        self.desktop.embed(hwnd)
        return hwnd

    def _connect_signals(self):
        self.ipc.loadPluginReceived.connect(self._on_load_plugin)
        self.ipc.resumeReceived.connect(self._on_resume)
        self.ipc.pauseReceived.connect(self._on_pause)
        self.ipc.stopReceived.connect(self._on_stop)
        self.plugins.pluginLoaded.connect(self._on_plugin_loaded)
        self.z_order.renderPauseChanged.connect(self._on_occlusion_changed)
        self.z_order.windowRecreationNeeded.connect(self._recreate_window)

    def _on_load_plugin(self, path):
        logger.info("收到加载指令: %s", path)
        if not self.plugins.load_plugin(path, self.window.contentItem()):
            logger.error("加载指令执行失败: %s", path)

    def _on_resume(self):
        self._set_manual_paused(False)
        self.z_order.set_monitoring_enabled(True)

    def _on_pause(self):
        self._set_manual_paused(True)
        self.z_order.set_monitoring_enabled(False)

    def _set_manual_paused(self, paused):
        self._manual_paused = paused
        self.status.set_paused(paused or self._occluded)

    def _on_occlusion_changed(self, occluded):
        if occluded == self._occluded:
            return
        self._occluded = occluded
        logger.info("遮挡状态变化: %s（仅暂停插件动画，不隐藏窗口）", occluded)
        self.status.set_paused(self._manual_paused or occluded)
        if not occluded:
            self.window.update()

    def _on_plugin_loaded(self, _path):
        self.z_order.set_monitoring_enabled(True)
        self.z_order.check()

    def _on_stop(self):
        logger.info("收到停止指令，正在退出")
        self.plugins.unload_all(self.window.contentItem())
        self.win_filter.cleanup()
        self.app.removeNativeEventFilter(self.win_filter)
        self.app.quit()

    def _recreate_window(self):
        if self._recreating:
            return
        logger.warning("开始重建引擎窗口")
        self._recreating = True
        try:
            plugin_paths = list(self.plugins.active_plugins)
            self.plugins.unload_all(self.window.contentItem())

            self.window.hide()
            self.window.deleteLater()
            QCoreApplication.processEvents()

            self.window = self._create_window()
            self.hwnd = self._show_and_embed(self.window)
            self.z_order.update_hwnd(self.hwnd)

            self.app.removeNativeEventFilter(self.win_filter)
            self.win_filter.cleanup()
            self.win_filter = WinEventFilter(self.hwnd, self.z_order.schedule_reembed)
            self.app.installNativeEventFilter(self.win_filter)

            self.window.setVisible(not self._occluded)
            self.status.set_paused(self._manual_paused or self._occluded)

            for path in plugin_paths:
                self.plugins.load_plugin(path, self.window.contentItem())
        finally:
            self._recreating = False

    def load_plugin(self, qml_path):
        self.plugins.load_plugin(qml_path, self.window.contentItem())

    def run(self):
        return self.app.exec()
