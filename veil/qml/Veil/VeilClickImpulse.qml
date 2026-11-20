import QtQuick

Item {
    id: root

    property color flashColor: "#0078D4"
    property real flashAlpha: 0.20

    function trigger(x, y) {
        impulseLayer.burstX = x
        impulseLayer.burstY = y
        impulseAnim.restart()
    }

    Item {
        id: impulseLayer
        anchors.fill: parent
        opacity: impulseAnim.running ? 1.0 : 0.0

        property real burstX: 0
        property real burstY: 0
        property real burstRadius: 0

        Canvas {
            id: rippleCanvas
            anchors.fill: parent

            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)

                var r = impulseLayer.burstRadius
                if (r <= 0) return

                var maxR = Math.sqrt(width * width + height * height) * 1.2
                var ratio = Math.min(r / maxR, 1.0)
                var alpha = root.flashAlpha * (1.0 - ratio)

                var gradient = ctx.createRadialGradient(
                    impulseLayer.burstX, impulseLayer.burstY, 0,
                    impulseLayer.burstX, impulseLayer.burstY, r
                )
                gradient.addColorStop(0, Qt.rgba(root.flashColor.r, root.flashColor.g, root.flashColor.b, alpha))
                gradient.addColorStop(0.8, Qt.rgba(root.flashColor.r, root.flashColor.g, root.flashColor.b, alpha * 0.4))
                gradient.addColorStop(1, "transparent")

                ctx.fillStyle = gradient
                ctx.fillRect(0, 0, width, height)
            }
        }

        ParallelAnimation {
            id: impulseAnim

            NumberAnimation {
                target: impulseLayer
                property: "burstRadius"
                from: 0
                to: Math.sqrt(Math.pow(impulseLayer.width, 2) + Math.pow(impulseLayer.height, 2)) * 1.2
                duration: 350
                easing.type: Easing.OutCubic
            }

            SequentialAnimation {
                NumberAnimation {
                    target: impulseLayer
                    property: "opacity"
                    from: 1.0
                    to: 0.0
                    duration: 350
                    easing.type: Easing.OutQuad
                }
                PropertyAction { target: impulseLayer; property: "opacity"; value: 0.0 }
            }
        }

        Connections {
            target: impulseLayer
            function onBurstRadiusChanged() {
                rippleCanvas.requestPaint()
            }
        }
    }
}