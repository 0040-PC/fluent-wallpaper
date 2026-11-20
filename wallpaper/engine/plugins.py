import gc
import importlib.util
import logging
import os
from pathlib import Path

import shiboken6
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtQml import QQmlComponent

logger = logging.getLogger("engine.plugins")


class PluginManager(QObject):
    pluginLoaded = Signal(str)

    def __init__(self, qml_engine, base_dir, parent=None):
        super().__init__(parent)
        self._qml_engine = qml_engine
        self._base_dir = Path(base_dir)
        self._items = {}
        self._backends = {}
        self._loading = False

    @property
    def active_plugins(self):
        return dict(self._items)

    def load_plugin(self, qml_path, content_item):
        if self._loading:
            return False

        self._loading = True
        try:
            qml_path = self._resolve(qml_path)
            name = os.path.basename(qml_path)

            self._stop_backend(qml_path)
            self._start_backend(qml_path)

            component = QQmlComponent(self._qml_engine, QUrl.fromLocalFile(qml_path))
            if component.isError():
                logger.error("加载失败 (%s): %s", name, component.errors())
                self._stop_backend(qml_path)
                return False

            item = component.create()
            if not item:
                logger.error("创建失败: %s", name)
                self._stop_backend(qml_path)
                return False

            item.setObjectName(name)
            coexist = bool(item.property("coexist"))

            if coexist:
                self._destroy_item(self._items.pop(qml_path, None))
                self._qml_engine.trimComponentCache()
                gc.collect()
            else:
                self._unload_all_except(qml_path, content_item, item)

            if content_item:
                item.setParentItem(content_item)
            self._items[qml_path] = item
            self._sync_backend_property()
            logger.info("加载成功: %s", name)
            self.pluginLoaded.emit(qml_path)
            return True

        except (OSError, RuntimeError, TypeError) as e:
            logger.error("加载插件时发生异常: %s", e)
            return False
        finally:
            self._loading = False

    def unload_all(self, content_item=None):
        for path in list(self._backends):
            self._stop_backend(path)
        for item in list(self._items.values()):
            self._destroy_item(item)
        self._items.clear()

        if content_item:
            for child in list(content_item.childItems()):
                self._destroy_item(child)

        self._qml_engine.clearSingletons()
        self._qml_engine.clearComponentCache()
        self._sync_backend_property()

    def _unload_all_except(self, keep_path, content_item, keep_item):
        for path in list(self._backends):
            if path != keep_path:
                self._stop_backend(path)
        for item in list(self._items.values()):
            self._destroy_item(item)
        self._items.clear()

        if content_item:
            for child in list(content_item.childItems()):
                if child is not keep_item:
                    self._destroy_item(child)

        self._qml_engine.clearSingletons()
        self._qml_engine.clearComponentCache()

    def _resolve(self, qml_path):
        path = Path(qml_path)
        if not path.is_absolute():
            path = self._base_dir / path
        return str(path.resolve())

    @staticmethod
    def _destroy_item(item):
        if item and shiboken6.isValid(item):
            item.setParentItem(None)
            item.deleteLater()

    def _find_backend_file(self, qml_path):
        plugin_dir = Path(qml_path).parent
        candidates = [plugin_dir / "backend.py", *sorted(plugin_dir.glob("*_backend.py"))]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return None

    @staticmethod
    def _find_backend_class(module):
        for name in ("Backend", "MonitorBackend"):
            obj = getattr(module, name, None)
            if isinstance(obj, type):
                return obj
        for name, obj in vars(module).items():
            if (
                isinstance(obj, type)
                and name.endswith("Backend")
                and obj.__module__ == module.__name__
            ):
                return obj
        return None

    def _start_backend(self, qml_path):
        backend_file = self._find_backend_file(qml_path)
        if not backend_file:
            return None

        try:
            module_name = f"wallpaper_plugin_backend_{abs(hash(backend_file))}"
            spec = importlib.util.spec_from_file_location(module_name, backend_file)
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            cls = self._find_backend_class(module)
            if not cls:
                logger.warning("%s 中未找到后端类", backend_file)
                return None

            backend = cls()
            self._backends[qml_path] = backend
            self._sync_backend_property()
            logger.info("后端已激活: %s", os.path.basename(backend_file))
            return backend

        except Exception as e:
            logger.error("加载后端失败: %s", e)
            return None

    def _stop_backend(self, qml_path):
        backend = self._backends.pop(qml_path, None)
        if backend is None:
            return
        try:
            backend.stop()
        except Exception as e:
            logger.error("停止后端失败: %s", e)
        self._sync_backend_property()

    def _sync_backend_property(self):
        backends = list(self._backends.values())
        self._qml_engine.rootContext().setContextProperty(
            "backend", backends[-1] if backends else None
        )
