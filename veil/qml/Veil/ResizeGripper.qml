import QtQuick
import QtQuick.Window

Item {
    id: root
    z: 9999
    visible: veilCtx && veilCtx.veilApplied && veilCtx.resizable && !veilCtx.isMax && veilCtx.showGripper

    property var veilCtx: null
    property int gripSize: 16

    anchors.right: parent.right
    anchors.bottom: parent.bottom
    width: gripSize
    height: gripSize

    function reportGripperRect() {
        if (!veilCtx || !visible) return
        var pos = root.mapToItem(null, 0, 0)
        var dpr = Screen.devicePixelRatio
        veilCtx.setGripperRect(
            Math.round(pos.x * dpr),
            Math.round(pos.y * dpr),
            Math.round(root.width * dpr),
            Math.round(root.height * dpr)
        )
    }

    onVeilCtxChanged: { if (veilCtx) Qt.callLater(reportGripperRect) }
    onVisibleChanged: {
        if (visible) Qt.callLater(reportGripperRect)
        else if (veilCtx) veilCtx.clearGripperRect()
    }
    onXChanged: { Qt.callLater(reportGripperRect) }
    onYChanged: { Qt.callLater(reportGripperRect) }
    onWidthChanged: { Qt.callLater(reportGripperRect) }
    onHeightChanged: { Qt.callLater(reportGripperRect) }

    property bool _hovered: veilCtx && veilCtx.gripperHover

    Canvas {
        id: gripCanvas
        anchors.fill: parent
        opacity: root._hovered ? 1.0 : 0.4

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)

            var isDark = root.veilCtx ? root.veilCtx.isDark : true
            ctx.fillStyle = isDark ? "#AAFFFFFF" : "#88000000"

            var dotSize = 2
            var gap = 4
            var margin = 2

            var rows = 3
            for (var row = 0; row < rows; row++) {
                for (var col = 0; col < rows - row; col++) {
                    var x = width - margin - (rows - row) * gap + col * gap
                    var y = height - margin - (row + 1) * gap
                    ctx.beginPath()
                    ctx.arc(x, y, dotSize * 0.5, 0, Math.PI * 2)
                    ctx.fill()
                }
            }
        }

        Connections {
            target: root.veilCtx
            function onIsDarkChanged() { gripCanvas.requestPaint() }
        }
    }

    Connections {
        target: Screen
        function onDevicePixelRatioChanged() { if (veilCtx) Qt.callLater(reportGripperRect) }
    }
}
