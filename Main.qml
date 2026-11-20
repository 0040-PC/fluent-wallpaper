import QtQuick
import QtQuick.Window
import Veil
import FluentUI

Window {
    id: win
    width: 960
    height: 640
    title: "fluent wallpaper"
    visible: true
    color: "transparent"

    property var veilCtx: null
    onVeilCtxChanged: if (veilCtx) veilCtx.setBackdrop("ACRYLIC")

    readonly property bool dark: veilCtx ? veilCtx.isDark : true
    property string currentBackdrop: "ACRYLIC"

    // ==========================================
    // Main Layout (Will be captured for blurring)
    // ==========================================
    Item {
        id: mainLayout
        anchors.fill: parent

        // 1. Sidebar (Invades Title Bar Area)
        Rectangle {
            id: sidebar
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            width: 80
            color: dark ? Qt.rgba(0.08, 0.08, 0.08, 0.4) : Qt.rgba(0.96, 0.96, 0.96, 0.5)
            border.color: dark ? Qt.rgba(1, 1, 1, 0.05) : Qt.rgba(0, 0, 0, 0.05)
            border.width: 1

            FluentNavigation {
                id: nav
                anchors.fill: parent
                dark: win.dark
                accent: "#4CC2FF"
                currentTab: -1
                items: {
                    var list = engineBackend ? engineBackend.entries : []
                    var result = []
                    for (var i = 0; i < list.length; i++) {
                        result.push({ icon: list[i].icon, text: list[i].name })
                    }
                    return result
                }
                onCurrentTabChanged: {
                    var list = engineBackend ? engineBackend.entries : []
                    if (nav.currentTab >= 0 && nav.currentTab < list.length) {
                        engineBackend.loadWallpaper(list[nav.currentTab].path)
                    }
                }
            }
        }

        // 2. Client Area / Content Area (Invades Title Bar Area)
        Item {
            id: contentArea
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.left: sidebar.right
            anchors.right: parent.right

            Column {
                anchors.centerIn: parent
                spacing: 10

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: engineBackend ? engineBackend.statusText : ""
                    font.pixelSize: 16
                    color: win.dark ? "#DDDDDD" : "#333333"
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "从左侧导航选择壁纸"
                    font.pixelSize: 12
                    color: win.dark ? "#777777" : "#999999"
                }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 8

                    Repeater {
                        model: [
                            { label: "Mica", token: "MICA" },
                            { label: "Mica Alt", token: "MICA_ALT" },
                            { label: "Acrylic", token: "ACRYLIC" },
                            { label: "None", token: "NONE" }
                        ]

                        FluentButton {
                            text: modelData.label
                            dark: win.dark
                            isHighlighted: win.currentBackdrop === modelData.token
                            onClicked: {
                                win.currentBackdrop = modelData.token
                                if (win.veilCtx)
                                    win.veilCtx.setBackdrop(modelData.token)
                            }
                        }
                    }
                }
            }
        }

        // 3. Title bar starts right of the sidebar, keeping the nav column outside the caption area
        TitleBar {
            id: titleBar
            veilCtx: win.veilCtx
            titleBarHeight: 36
            anchors.top: parent.top
            anchors.left: sidebar.right
            anchors.right: parent.right
        }
    }

    // ==========================================
    // 4. Native Frame overlays (Layered on Top)
    // ==========================================
    SystemButtons {
        id: sysBtns
        veilCtx: win.veilCtx
    }

    ResizeGripper {
        id: gripper
        veilCtx: win.veilCtx
    }
}
