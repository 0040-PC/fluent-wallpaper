import QtQuick

Item {
    id: worleyRoot
    anchors.fill: parent

    Component.onCompleted: {
        console.log("[插件] Worley 噪波：加载成功")
    }
    
    Component.onDestruction: {
        console.log("[插件] Worley 噪波：正在卸载")
    }

    readonly property bool isPaused: (typeof engineStatus !== "undefined" && engineStatus !== null) ? engineStatus.isPaused : false

    ShaderEffect {
        id: wallpaperShader
        anchors.fill: parent
        
        visible: true 

        property real time: 0
        property vector2d resolution: Qt.vector2d(width, height)

        vertexShader: "lava.vert.qsb"
        fragmentShader: "worley.frag.qsb"

        Timer {
            interval: 25 
            running: !isPaused
            repeat: true
            onTriggered: {
                wallpaperShader.time += 0.025 
            }
        }
    }
}
