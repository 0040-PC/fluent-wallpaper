import sys
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QDataStream,
    QObject,
    QProcess,
    QProcessEnvironment,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from veil import Veil

PROJECT_ROOT = Path(__file__).resolve().parent
WALLPAPER_DIR = PROJECT_ROOT / "wallpaper" / "plugins"
ENGINE_SCRIPT = PROJECT_ROOT / "wallpaper" / "engine" / "entry.py"
SERVER_NAME = "WallpaperEngineControl"


def scan_wallpapers():
    entries = []
    if not WALLPAPER_DIR.is_dir():
        return entries

    for path in sorted(WALLPAPER_DIR.glob("*.qml"), key=lambda p: p.name.lower()):
        entries.append({"name": path.stem, "path": str(path), "icon": "\uE8A5"})

    for folder in sorted(WALLPAPER_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not folder.is_dir():
            continue
        plugins = sorted(folder.glob("*Plugin.qml"))
        if plugins:
            entries.append(
                {"name": folder.name, "path": str(plugins[0]), "icon": "\uE8B7"}
            )
    return entries


class EngineBackend(QObject):
    statusTextChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = scan_wallpapers()
        self._status = "准备就绪"
        self._process = None
        self._pending = None
        QTimer.singleShot(0, self._check_startup)

    @Property("QVariantList", constant=True)
    def entries(self):
        return self._entries

    @Property(str, notify=statusTextChanged)
    def statusText(self):
        return self._status

    @Slot(str)
    def loadWallpaper(self, qml_path):
        if not qml_path:
            return
        if self._send(qml_path):
            self._set_status("已加载: " + Path(qml_path).stem)
            return
        self._pending = qml_path
        self._set_status("正在启动引擎...")
        self._ensure_engine()

    def _set_status(self, text):
        if text != self._status:
            self._status = text
            self.statusTextChanged.emit()

    def _check_startup(self):
        self._set_status("引擎在线" if self._ping() else "点击左侧壁纸加载")

    def _ping(self):
        socket = QLocalSocket()
        socket.connectToServer(SERVER_NAME)
        online = socket.waitForConnected(300)
        socket.disconnectFromServer()
        socket.deleteLater()
        return online

    def _ensure_engine(self):
        if self._ping():
            self._flush_pending()
            return
        if self._process and self._process.state() != QProcess.NotRunning:
            return

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ForwardedChannels)
        self._process.setWorkingDirectory(str(ENGINE_SCRIPT.parent))
        self._process.setProcessEnvironment(QProcessEnvironment.systemEnvironment())
        self._process.finished.connect(self._on_process_finished)
        self._process.start(sys.executable, [str(ENGINE_SCRIPT)])

        if not self._process.waitForStarted(2000):
            self._set_status("错误: 引擎启动失败")
            return
        self._wait_online(0)

    def _wait_online(self, attempt):
        if self._ping():
            self._set_status("引擎在线")
            self._flush_pending()
        elif attempt < 5:
            QTimer.singleShot(500, lambda: self._wait_online(attempt + 1))
        else:
            self._set_status("错误: 引擎未响应，请查看控制台")

    def _flush_pending(self):
        path, self._pending = self._pending, None
        if not path:
            return
        if self._send(path):
            self._set_status("已加载: " + Path(path).stem)
        else:
            self._pending = path
            self._set_status("引擎未响应")

    def _on_process_finished(self):
        if not self._ping():
            self._set_status("引擎已退出")

    def _send(self, qml_path):
        socket = QLocalSocket()
        socket.connectToServer(SERVER_NAME)
        if not socket.waitForConnected(500):
            socket.deleteLater()
            return False

        stream = QDataStream(socket)
        stream.writeString("LOAD_PLUGIN")
        stream.writeString(qml_path)
        socket.flush()
        written = socket.waitForBytesWritten(2000) or socket.bytesToWrite() == 0
        socket.disconnectFromServer()
        socket.deleteLater()
        return written


def main():
    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(PROJECT_ROOT))

    backend = EngineBackend()
    engine.rootContext().setContextProperty("engineBackend", backend)

    Veil.attach(engine, app)
    engine.load(QUrl.fromLocalFile(str(PROJECT_ROOT / "Main.qml")))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
