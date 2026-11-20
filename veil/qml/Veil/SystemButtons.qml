import QtQuick
import QtQuick.Window

Item {
    id: root
    z: 9999
    visible: veilCtx && veilCtx.veilApplied

    property var veilCtx: null
    property int buttonWidth: 46
    property int buttonHeight: 32

    anchors.right: parent.right
    anchors.top: parent.top
    width: buttonWidth * 3
    height: buttonHeight

    property var buttonIds: ["min", "max", "close"]

    function _iconForButton(btnId) {
        if (!veilCtx) return ""
        if (btnId === "min") return "\uE921"
        if (btnId === "max") return veilCtx.isMax ? "\uE923" : "\uE922"
        if (btnId === "close") return "\uE8BB"
        return ""
    }

    function reportButtonRect(btnId, btnItem) {
        if (!veilCtx) return;
        
        var pos = btnItem.mapToItem(null, 0, 0)
        var dpr = Screen.devicePixelRatio
        
        veilCtx.setButtonRect(
            btnId,
            Math.round(pos.x * dpr),
            Math.round(pos.y * dpr),
            Math.round(btnItem.width * dpr),
            Math.round(btnItem.height * dpr)
        )
    }

    function reportAllButtonRects() {
        for (var i = 0; i < repeater.count; i++) {
            var item = repeater.itemAt(i)
            if (item) reportButtonRect(item.btnId, item)
        }
    }

    onVeilCtxChanged: { if (veilCtx && veilCtx.ready) Qt.callLater(reportAllButtonRects) }

    Connections {
        target: veilCtx
        function onReadyChanged() {
            if (veilCtx.ready) Qt.callLater(reportAllButtonRects)
        }
    }

    onXChanged: reportAllButtonRects()
    onYChanged: reportAllButtonRects()
    onWidthChanged: reportAllButtonRects()
    onHeightChanged: reportAllButtonRects()

    Row {
        anchors.fill: parent
        spacing: 0

        Repeater {
            id: repeater
            model: root.buttonIds

            Rectangle {
                id: btnRect
                property string btnId: modelData
                width: root.buttonWidth
                height: root.buttonHeight
                color: "transparent" // 容器保持透明
                clip: true // 关键：裁剪内部的“气室填充”

                // 映射状态：0-正常, 1-悬停, 2-按下
                property int btnState: {
                    if (!veilCtx) return 0
                    if (btnId === "min") return veilCtx.minBtnState
                    else if (btnId === "max") return veilCtx.maxBtnState
                    else if (btnId === "close") return veilCtx.closeBtnState
                    return 0
                }

                // 气室填充层（火苗/气室）
                Rectangle {
                    id: fillLayer
                    anchors.fill: parent
                    // 完全动态计算状态颜色，避免 State 的 PropertyChanges 覆盖
                    color: {
                        if (btnId === "close") {
                            return btnState === 2 ? "#C50F1F" : "#E81123"
                        }
                        if (veilCtx && veilCtx.isDark) {
                            return btnState === 2 ? "#0DFFFFFF" : "#14FFFFFF"
                        } else {
                            // 浅色模式下：按下更深，悬停较浅
                            return btnState === 2 ? "#1A000000" : "#0A000000"
                        }
                    }
                    opacity: 0
                    scale: 0.92
                }

                state: btnState === 2 ? "pressed" : (btnState === 1 ? "hover" : "normal")

                states:[
                    State {
                        name: "normal"
                        PropertyChanges { target: fillLayer; opacity: 0; scale: 0.96 }
                    },
                    State {
                        name: "hover"
                        PropertyChanges { target: fillLayer; opacity: 1; scale: 1.0 }
                    },
                    State {
                        name: "pressed"
                        PropertyChanges { target: fillLayer; opacity: 1; scale: 1.0 }
                    }
                ]

                transitions:[
                    Transition {
                        from: "normal"; to: "hover"
                        ParallelAnimation {
                            NumberAnimation { target: fillLayer; property: "opacity"; duration: 167; easing.type: Easing.OutCubic }
                            NumberAnimation { target: fillLayer; property: "scale"; duration: 167; easing.type: Easing.OutCubic }
                        }
                    },
                    Transition {
                        from: "hover"; to: "normal"
                        ParallelAnimation {
                            NumberAnimation { target: fillLayer; property: "opacity"; duration: 180; easing.type: Easing.OutCubic }
                            NumberAnimation { target: fillLayer; property: "scale"; duration: 180; easing.type: Easing.OutCubic }
                        }
                    },
                    Transition {
                        from: "*"; to: "pressed"
                        PropertyAction { target: fillLayer; properties: "opacity,scale" }
                    }
                ]

                Text {
                    anchors.centerIn: parent
                    text: root._iconForButton(btnId)
                    font.family: "Segoe Fluent Icons"
                    font.pixelSize: 10
                    // 极致简化：只看 isDark。关闭按钮特殊处理放在这里
                    color: {
                        if (btnId === "close" && btnState !== 0) return "#FFFFFF";
                        // 强制使用 root 传入的 veilCtx 属性，确保绑定链条清晰
                        if (root.veilCtx) {
                            return root.veilCtx.isDark ? "#FFFFFF" : "#000000"
                        }
                        return "#FFFFFF"
                    }
                }

                // 【核心修改 3】：彻底删除了这里的 Connections！
                // 内部按钮不再需要关心 Window 的绝对坐标变化！
            }
        }
    }

    Connections {
        target: Screen
        function onDevicePixelRatioChanged() { if (veilCtx) Qt.callLater(reportAllButtonRects) }
    }
}