import QtQuick

Item {
    id: goldClassicRoot
    anchors.fill: parent

    Component.onCompleted: {
        console.log("[插件] 黄金经典：加载成功")
    }
    
    Component.onDestruction: {
        console.log("[插件] 黄金经典：正在卸载")
    }

    readonly property bool _engineValid: typeof engineStatus !== "undefined" && engineStatus !== null
    readonly property bool isPaused: _engineValid && engineStatus.isPaused

    ShaderEffect {
        id: wallpaperShader
        anchors.fill: parent
        
        // 恢复显示：暂停时依然保持可见，实现“冻结”效果
        visible: true 

        property real time: 0
        property vector2d resolution: Qt.vector2d(width, height)

        vertexShader: "lava.vert.qsb"
        fragmentShader: "gold.frag.qsb"

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
