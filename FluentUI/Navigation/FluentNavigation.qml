import QtQuick
import QtQuick.Layouts
import FluentUI

Rectangle {
    id: navRoot
    Layout.fillHeight: true
    Layout.preferredWidth: 84
    color: "transparent"

    property int currentTab: 0
    property int lastTab: 0
    property bool dark: true
    property color accent: "#0078D4"
    
    property var items: []

    property Item currentIndicatorItem: null

    function switchTab(index, item) {
        if (navRoot.currentTab === index) return
        navRoot.lastTab = navRoot.currentTab
        navRoot.currentTab = index 
        navRoot.currentIndicatorItem = item
    }

    Rectangle {
        id: globalIndicator
        z: 99
        x: 3
        width: 4
        radius: 2
        color: navRoot.accent

        property real indicatorTop: 0
        property real indicatorBottom: 0

        y: Math.min(indicatorTop, indicatorBottom)
        height: Math.abs(indicatorBottom - indicatorTop)

        Component.onCompleted: {
            Qt.callLater(function() {
                updateIndicator(false)
            })
        }

        function updateIndicator(animate) {
            if (!navRoot.currentIndicatorItem) return

            var targetPos = navRoot.currentIndicatorItem.mapToItem(globalIndicator.parent, 0, 0)
            
            var indicatorH = 20
            var destTop = targetPos.y + (navRoot.currentIndicatorItem.height - indicatorH) / 2
            var destBottom = destTop + indicatorH
            
            if (!animate) {
                indicatorTop = destTop
                indicatorBottom = destBottom
                return
            }

            var isMovingDown = destTop > indicatorTop
            var diff = Math.abs(navRoot.currentTab - navRoot.lastTab)

            animFluency.stop()
            animShuttle.stop()

            if (diff <= 1) {
                animFluency.toTop = destTop
                animFluency.toBottom = destBottom

                if (isMovingDown) {
                    animFluency.easingTop = Easing.InOutQuad
                    animFluency.easingBottom = Easing.OutBack
                } else {
                    animFluency.easingTop = Easing.OutBack
                    animFluency.easingBottom = Easing.InOutQuad
                }
                
                animFluency.restart()
            } else {
                const offset = 14

                animShuttle.divePoint = isMovingDown ? indicatorBottom + offset : indicatorTop - offset
                animShuttle.emergePoint = isMovingDown ? destTop - offset : destBottom + offset
                animShuttle.destTop = destTop
                animShuttle.destBottom = destBottom
                
                animShuttle.restart()
            }
        }

        Connections {
            target: navRoot
            function onCurrentIndicatorItemChanged() {
                globalIndicator.updateIndicator(true)
            }
        }
        
        ParallelAnimation {
            id: animFluency
            property real toTop
            property real toBottom
            property var easingTop: Easing.OutQuad
            property var easingBottom: Easing.OutQuad

            NumberAnimation { target: globalIndicator; property: "indicatorTop"; to: animFluency.toTop; duration: 400; easing.type: animFluency.easingTop; easing.overshoot: 1.15 }
            NumberAnimation { target: globalIndicator; property: "indicatorBottom"; to: animFluency.toBottom; duration: 400; easing.type: animFluency.easingBottom; easing.overshoot: 1.15 }
        }

        SequentialAnimation {
            id: animShuttle
            
            property real divePoint
            property real emergePoint
            property real destTop
            property real destBottom
            
            ParallelAnimation {
                NumberAnimation { target: globalIndicator; property: "indicatorTop"; to: animShuttle.divePoint; duration: 150; easing.type: Easing.InQuad }
                NumberAnimation { target: globalIndicator; property: "indicatorBottom"; to: animShuttle.divePoint; duration: 150; easing.type: Easing.InQuad }
            }
            
            ScriptAction {
                script: {
                    globalIndicator.indicatorTop = animShuttle.emergePoint
                    globalIndicator.indicatorBottom = animShuttle.emergePoint
                }
            }
            
            ParallelAnimation {
                NumberAnimation { target: globalIndicator; property: "indicatorTop"; to: animShuttle.destTop; duration: 250; easing.type: Easing.OutBack; easing.overshoot: 1.2 }
                NumberAnimation { target: globalIndicator; property: "indicatorBottom"; to: animShuttle.destBottom; duration: 250; easing.type: Easing.OutBack; easing.overshoot: 1.2 }
            }
        }
    }

    ColumnLayout {
        id: navColumn
        anchors.fill: parent
        anchors.margins: 2
        spacing: 0

        Repeater {
            model: navRoot.items
            delegate: Loader {
                active: !modelData.isBottom
                Layout.fillWidth: true
                Layout.preferredHeight: active ? 70 : 0
                visible: active
                
                sourceComponent: FluentNavButton {
                    icon: modelData.icon
                    text: modelData.text
                    isSelected: navRoot.currentTab === index
                    accentColor: navRoot.accent
                    onClicked: navRoot.switchTab(index, this)
                    Layout.fillWidth: true
                    Layout.preferredHeight: 70
                    dark: navRoot.dark
                    
                    Component.onCompleted: {
                        if (isSelected) {
                            navRoot.currentIndicatorItem = this
                        }
                    }
                }
            }
        }

        Item { Layout.fillHeight: true }

        Repeater {
            model: navRoot.items
            delegate: Loader {
                active: modelData.isBottom === true
                Layout.fillWidth: true
                Layout.preferredHeight: active ? 70 : 0
                visible: active
                
                sourceComponent: FluentNavButton {
                    icon: modelData.icon
                    text: modelData.text
                    isSelected: navRoot.currentTab === index
                    accentColor: navRoot.accent
                    onClicked: navRoot.switchTab(index, this)
                    Layout.fillWidth: true
                    Layout.preferredHeight: 70
                    dark: navRoot.dark
                    
                    Component.onCompleted: {
                        if (isSelected) {
                            navRoot.currentIndicatorItem = this
                        }
                    }
                }
            }
        }
    }
}
