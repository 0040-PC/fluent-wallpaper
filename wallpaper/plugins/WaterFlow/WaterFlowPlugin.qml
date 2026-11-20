import QtQuick

Item {
    id: waterFlowRoot
    anchors.fill: parent

    Component.onCompleted: {
        console.log("[插件] 自然流水：加载成功")
    }

    Component.onDestruction: {
        console.log("[插件] 自然流水：正在卸载")
    }

    readonly property bool _engineValid: typeof engineStatus !== "undefined" && engineStatus !== null
    readonly property bool isPaused: _engineValid && engineStatus.isPaused

    ShaderEffect {
        id: waterShader
        anchors.fill: parent

        visible: true

        property real time: 0
        property real aspectRatio: width > 0 ? width / height : 1.0

        vertexShader: "lava.vert.qsb"
        fragmentShader: "water.frag.qsb"

        property real _startTime: Date.now() / 1000.0
        property real _pauseAccum: 0
        property real _pauseBegin: 0

        Component.onCompleted: {
            if (waterFlowRoot.isPaused) {
                waterShader._pauseBegin = Date.now() / 1000.0
            }
        }

        FrameAnimation {
            running: !waterFlowRoot.isPaused
            onTriggered: {
                waterShader.time = (Date.now() / 1000.0) - waterShader._startTime - waterShader._pauseAccum
            }
        }

        Connections {
            target: waterFlowRoot
            function onIsPausedChanged() {
                if (waterFlowRoot.isPaused) {
                    waterShader._pauseBegin = Date.now() / 1000.0
                } else {
                    waterShader._pauseAccum += (Date.now() / 1000.0) - waterShader._pauseBegin
                }
            }
        }
    }
}
