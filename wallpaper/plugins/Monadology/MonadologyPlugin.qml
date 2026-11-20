import QtQuick
import QtQuick.Controls

Item {
    id: root
    anchors.fill: parent

    ShaderEffect {
        id: shadereffect
        anchors.fill: parent

        // 传递属性
        property real iTime: 0
        property vector2d iResolution: Qt.vector2d(width, height)
        property var source: Image { 
            source: "textures/organic_cyber.png"
            visible: false // 不需要显示，只需要数据
        }

        vertexShader: "monad.vert.qsb"
        fragmentShader: "monad.frag.qsb"
    }

    // 时间驱动
    Timer {
        interval: 16
        running: true
        repeat: true
        onTriggered: {
            shadereffect.iTime += 0.016
        }
    }
}
