import QtQuick

Item {
    id: goldFlowRoot
    anchors.fill: parent

    Component.onCompleted: {
        console.log("[插件] 黄金流体：加载成功")
    }
    
    Component.onDestruction: {
        console.log("[插件] 黄金流体：正在卸载")
    }

    readonly property bool isPaused: (typeof engineStatus !== "undefined" && engineStatus !== null) ? engineStatus.isPaused : false

    ShaderEffect {
        id: wallpaperShader
        anchors.fill: parent
        
        visible: true 
        layer.enabled: true
        layer.smooth: true
        layer.textureSize: Qt.size(Math.max(1, Math.floor(width * renderScale)), Math.max(1, Math.floor(height * renderScale)))

        property real time: 0
        property vector2d resolution: Qt.vector2d(layer.textureSize.width, layer.textureSize.height)
        property real renderScale: 0.6

        vertexShader: "lava.vert.qsb"
        fragmentShader: "gold_flow.frag.qsb"

        Timer {
            interval: 50 
            running: !isPaused
            repeat: true
            onTriggered: {
                wallpaperShader.time += 0.05 
            }
        }
    }
}
