# fluent-wallpaper

Windows 上的 Qt Quick 无边框窗口框架（Veil）与壁纸引擎示例。

## 截图

Monadology、SilkCocoon、GoldClassic，窗口材质均为 Acrylic。

<p align="center">
  <img src="https://37kt4leu5rtbrkuoguc.traesite.cn/assets/monadology.png" alt="Monadology 壁纸，Acrylic 材质" width="100%">
</p>

<p align="center">
  <img src="https://37kt4leu5rtbrkuoguc.traesite.cn/assets/silkcocoon.png" alt="SilkCocoon 壁纸，Acrylic 材质" width="49%">
  <img src="https://37kt4leu5rtbrkuoguc.traesite.cn/assets/goldclassic.png" alt="GoldClassic 壁纸，Acrylic 材质" width="49%">
</p>

## 组成

- `veil/`：无边框窗口核心。DWM 背景材质、非客户区命中测试、系统按钮、缩放握把、窗口动画
- `FluentUI/`：QML 组件库，包含 `FluentButton`、`FluentNavigation`、`FluentNavButton`
- `wallpaper/engine/`：壁纸引擎。独立进程，负责桌面嵌入、插件加载、本地 IPC、Z 序监控
- `wallpaper/plugins/`：壁纸插件。当前有 DebugOverlay、GoldClassic、GoldFlow、Monadology、PaperBurn、SilkCocoon、WaterFlow、Worley
- `main.py`、`Main.qml`：壁纸浏览器。导航列出壁纸，点击后按需启动引擎并加载

## 环境

- Windows 10/11 x64
- Python 3.12+
- PySide6 >= 6.6

## 运行

```bash
python -m pip install -r requirements.txt
python main.py       # 带控制台，便于看日志
pythonw main.pyw     # 无控制台启动
```

`main.pyw` 也可直接双击运行，前提是系统已关联 `.pyw` 到 `pythonw.exe`。

- 左侧导航由 `wallpaper/plugins` 扫描生成：根目录的 `.qml` 和子目录的 `*Plugin.qml` 各算一项
- 首次点击壁纸时才启动 `wallpaper/engine/entry.py`，之后通过命名管道发送加载指令
- 客户区按钮切换窗口材质：Mica、Mica Alt、Acrylic、None
- 关闭 main 会结束引擎，壁纸随之停止

## 架构

- 控制端 `main.py` 通过 `QLocalSocket` 连接命名管道 `WallpaperEngineControl`
- 引擎创建无边框透明窗口，嵌入桌面 `WorkerW` / `Progman` 容器，位于图标层下方
- 每 2 秒检查桌面锚点与 Z 序：被遮挡时冻结插件动画；锚点失效时重新嵌入；多次失败后重建窗口
- 插件为独立 QML 组件，可选配套 Python 后端

## 插件约定

- QML 根为 `Item`，通常 `anchors.fill: parent`
- 可选 `coexist: true`：为 false（默认）时加载新插件会卸载旧插件
- 可选后端：插件目录下的 `backend.py` 或 `*_backend.py`，类名可为 `Backend`、`MonitorBackend` 或任意 `*Backend`；实例会被注册为 QML 上下文属性 `backend`
- 可选暂停支持：绑定 `engineStatus.isPaused`，在遮挡/手动暂停时停止 `FrameAnimation` 等动画
- 着色器以 `.qsb` 形式与 QML 放在同一目录；本仓库只包含编译产物，不包含 `.frag` / `.vert` 源码

## 引擎控制

命名管道支持以下指令：

- `LOAD_PLUGIN` + 绝对路径
- `RESUME_RENDER`
- `PAUSE_RENDER`
- `STOP`
- `PING`

手动停止引擎：

```python
from PySide6.QtCore import QDataStream
from PySide6.QtNetwork import QLocalSocket

socket = QLocalSocket()
socket.connectToServer("WallpaperEngineControl")
if socket.waitForConnected(500):
    stream = QDataStream(socket)
    stream.writeString("STOP")
    socket.flush()
    socket.waitForBytesWritten(500)
```

IPC 没有鉴权，指令是单向的，没有回执；只应在本机可信环境使用。

## Veil 用法

```python
from veil import Veil

Veil.attach(engine, app)
```

QML 窗口声明 `veilCtx`，框架会注入实例：

```qml
Window {
    property var veilCtx: null
    onVeilCtxChanged: if (veilCtx) veilCtx.setBackdrop("ACRYLIC")

    TitleBar { veilCtx: win.veilCtx }
    SystemButtons { veilCtx: win.veilCtx }
    ResizeGripper { veilCtx: win.veilCtx }
}
```

常用接口：

- `setBackdrop("NONE" | "TRANSPARENT" | "MICA" | "ACRYLIC" | "MICA_ALT")`
- `setDark(bool)`
- `setCornerPreference(0 | 1 | 2 | 3)`
- `setResizable(bool)`
- `remove()`

`TitleBar` 只上报标题栏矩形，拖拽、双击最大化完全由 Win32 的 `HTCAPTION` 处理；命中测试只处理非客户区，QML 控件若与标题栏矩形重叠，点击归属由使用者自行调整布局解决。

## 渲染默认值

`import veil` 只提供默认值，不强制覆盖宿主设置：

- 未设置时使用 `QSG_RHI_BACKEND=opengl`
- 未设置时使用 `QT_QUICK_CONTROLS_STYLE=Basic`（`FluentButton` 依赖该风格的自定义背景）
- 未设置时使用 `QML_DISABLE_DISK_CACHE=0`
- 仅当宿主未指定采样数时请求 4x MSAA

这些默认值需要在创建 `QGuiApplication` / `QApplication` 之前生效。

## 已知限制

- 仅支持 Windows，其他平台会在 `ctypes.windll` 处失败
- DWM 背景材质需要 Windows 11 Build 22621（22H2）及以上；Windows 10 上没有回退效果
- 引擎只覆盖主显示器，暂不支持每屏独立壁纸
- 字体依赖 `Segoe UI Variable` 与 `Segoe Fluent Icons`；Windows 10 需自行替换
- 着色器只有 `.qsb` 二进制，没有 GLSL 源码；Qt 版本或渲染后端变化时需要重新编译
- 插件会被当作可执行代码：引擎会执行插件目录下的 Python 后端，并可由 IPC 指定任意本地 QML 路径

## License

- 代码（`veil/`、`FluentUI/`、`wallpaper/engine/`、`main.py`、`Main.qml`、插件 QML 外壳）：Apache-2.0，见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)
- 着色器与贴图（`wallpaper/plugins/` 下的 `.qsb`、着色器源码、贴图）：不是开源内容，允许随本项目整体分发，不得单独复用，见 [LICENSE-ASSETS](LICENSE-ASSETS)
