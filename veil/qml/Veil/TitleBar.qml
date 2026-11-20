import QtQuick
import QtQuick.Window

Item {
    id: root

    property var veilCtx: null
    property int titleBarHeight: 48
    property int leftInset: 0
    property string title: ""
    property bool devMode: false

    height: titleBarHeight

    Rectangle {
        anchors.fill: parent
        visible: root.devMode
        color: "transparent"
        border.color: "#FF4444"
        border.width: 1
        z: 9999
    }

    Text {
        id: titleText
        anchors.left: parent.left
        anchors.leftMargin: leftInset + 12
        anchors.verticalCenter: parent.verticalCenter
        // Dynamic binding: Use custom title if set, otherwise bind to the parent Window's title
        text: root.title !== "" ? root.title : (Window.window ? Window.window.title : "Veil Window")
        font.family: "Segoe UI Variable"
        font.pixelSize: 14 // Make it look elegant and standard (not overly huge 20px)
        font.weight: Font.DemiBold
        color: veilCtx ? (veilCtx.isDark ? "#FFFFFF" : "#000000") : "#FFFFFF"
    }

    function reportCaptionRect() {
        if (!veilCtx) return;
        
        var pos = root.mapToItem(null, 0, 0)
        var dpr = Screen.devicePixelRatio
        
        veilCtx.setCaptionRect(
            Math.round(pos.x * dpr),
            Math.round(pos.y * dpr),
            Math.round(root.width * dpr),
            Math.round(root.height * dpr)
        )
    }

    onVeilCtxChanged: { if (veilCtx && veilCtx.ready) Qt.callLater(reportCaptionRect) }

    Connections {
        target: veilCtx
        function onReadyChanged() {
            if (veilCtx.ready) Qt.callLater(reportCaptionRect)
        }
    }

    onWidthChanged: reportCaptionRect()
    onHeightChanged: reportCaptionRect()

    Connections {
        target: Screen
        function onDevicePixelRatioChanged() { Qt.callLater(reportCaptionRect) }
    }
}