import QtQuick
import QtQuick.Controls

Item {
    id: root
    anchors.fill: parent

    ShaderEffect {
        id: shadereffect
        anchors.fill: parent

        // Properties
        property real iTime: 0
        property vector2d resolution: Qt.vector2d(width, height)

        vertexShader: "silk.vert.qsb"
        fragmentShader: "silk.frag.qsb"

        // Time Driver (VSync Smooth Animation)
        NumberAnimation on iTime {
            from: 0
            to: 1000
            duration: 1600000 
            loops: Animation.Infinite
            running: true
        }
    }
}
