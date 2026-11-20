import QtQuick
import QtQuick.Controls

Item {
    id: root
    anchors.fill: parent

    // Background: Removed to prevent Overdraw (Layer Superposition Optimization)
    // Rectangle { anchors.fill: parent; color: "#000510" }

    ShaderEffect {
        id: shadereffect
        anchors.fill: parent

        layer.enabled: true
        layer.smooth: true
        // Optimization: Reduce Resolution to 0.5 (4x Performance Boost)
        // This "inhibits" 75% of the pixel shader calculations.
        property real renderScale: 0.5 
        layer.textureSize: Qt.size(Math.max(1, Math.floor(width * renderScale)), Math.max(1, Math.floor(height * renderScale)))

        property real iTime: 0
        property vector2d resolution: Qt.vector2d(layer.textureSize.width, layer.textureSize.height)
        
        // Fluid Parameters
        property color waterColor: "#001133"    // Deep Ocean
        property color particleColor: "#00FFFF" // Bio-luminescent Cyan
        property real flowSpeed: 0.5            // Speed of the liquid distortion
        property real turbulence: 0.3           // How much the water twists
        property real density: 1.0              // Particle count multiplier

        vertexShader: "burn.vert.qsb"
        fragmentShader: "burn.frag.qsb"

        readonly property bool isPaused: (typeof engineStatus !== "undefined" && engineStatus !== null) ? engineStatus.isPaused : false

        Timer {
            interval: 33
            running: !shadereffect.isPaused
            repeat: true
            onTriggered: {
                shadereffect.iTime += 0.033
            }
        }
    }
}
