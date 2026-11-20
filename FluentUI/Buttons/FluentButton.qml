import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import Veil

Button {
    id: control
    
    property bool dark: false
    property color highlightColor: "#0078D4"
    property bool isHighlighted: false

    implicitWidth: Math.max(120, contentItem.implicitWidth + 24)
    implicitHeight: 32

    contentItem: Text {
        text: control.text
        font: control.font
        color: {
            if (control.isHighlighted) return "white"
            return control.dark ? "white" : "black"
        }
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        id: bg
        radius: 4
        clip: true
        
        color: {
            if (control.isHighlighted) {
                if (control.down) return Qt.darker(control.highlightColor, 1.1)
                if (control.hovered) return Qt.lighter(control.highlightColor, 1.1)
                return control.highlightColor
            }
            
            if (control.dark) {
                if (control.down) return Qt.rgba(1, 1, 1, 0.06)
                if (control.hovered) return Qt.rgba(1, 1, 1, 0.09)
                return Qt.rgba(1, 1, 1, 0.06)
            } else {
                if (control.down) return Qt.rgba(0, 0, 0, 0.06)
                if (control.hovered) return Qt.rgba(0, 0, 0, 0.04)
                return Qt.rgba(1, 1, 1, 0.4)
            }
        }
        
        border.color: {
            if (control.isHighlighted) return "transparent"
            
            if (control.dark) {
                return Qt.rgba(0, 0, 0, 0.2)
            } else {
                return Qt.rgba(0, 0, 0, 0.06)
            }
        }
        border.width: control.isHighlighted ? 0 : 1
        
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 1
            height: 1
            radius: 4
            
            visible: !control.down && !control.isHighlighted
            
            color: control.dark ? Qt.rgba(1,1,1,0.08) : Qt.rgba(0,0,0,0.1)
        }

        Rectangle {
            id: revealLight
            anchors.fill: parent
            radius: 4
            color: "transparent"
            opacity: 0.0

            property point lightPos: Qt.point(width / 2, height / 2)

            Shape {
                anchors.fill: parent
                ShapePath {
                    strokeWidth: 0
                    strokeColor: "transparent"

                    startX: 4; startY: 0
                    PathLine { x: revealLight.width - 4; y: 0 }
                    PathArc { x: revealLight.width; y: 4; radiusX: 4; radiusY: 4 }
                    PathLine { x: revealLight.width; y: revealLight.height - 4 }
                    PathArc { x: revealLight.width - 4; y: revealLight.height; radiusX: 4; radiusY: 4 }
                    PathLine { x: 4; y: revealLight.height }
                    PathArc { x: 0; y: revealLight.height - 4; radiusX: 4; radiusY: 4 }
                    PathLine { x: 0; y: 4 }
                    PathArc { x: 4; y: 0; radiusX: 4; radiusY: 4 }

                    fillGradient: RadialGradient {
                        centerX: revealLight.lightPos.x
                        centerY: revealLight.lightPos.y
                        centerRadius: 200
                        focalX: revealLight.lightPos.x
                        focalY: revealLight.lightPos.y
                        GradientStop { position: 0.0; color: control.dark ? Qt.rgba(1,1,1,0.24) : Qt.rgba(1,1,1,0.40) }
                        GradientStop { position: 0.15; color: control.dark ? Qt.rgba(1,1,1,0.12) : Qt.rgba(1,1,1,0.18) }
                        GradientStop { position: 0.4; color: control.dark ? Qt.rgba(1,1,1,0.04) : Qt.rgba(1,1,1,0.06) }
                        GradientStop { position: 0.8; color: Qt.rgba(0,0,0,0) }
                        GradientStop { position: 1.0; color: "transparent" }
                    }
                }
            }
        }

        VeilClickImpulse {
            id: impulseEffect
            anchors.fill: parent
            flashColor: control.highlightColor
            z: 10
        }
    }

    Connections {
        target: control
        function onClicked() {
            impulseEffect.trigger(revealLight.lightPos.x, revealLight.lightPos.y)
        }
    }

    // 顶层代理 MouseArea，确保在按下状态下也能拿到坐标
    MouseArea {
        id: mouseTracker
        anchors.fill: parent
        hoverEnabled: true
        
        onPositionChanged: (mouse) => {
            revealLight.lightPos = Qt.point(mouse.x, mouse.y)
        }
        
        onPressed: (mouse) => {
            control.down = true 
            revealLight.lightPos = Qt.point(mouse.x, mouse.y)
        }
        
        onReleased: (mouse) => {
            control.down = false
            if (containsMouse) {
                control.clicked()
            }
        }
    }

    states: [
        State {
            name: "pressed"
            when: control.down && mouseTracker.containsMouse
            PropertyChanges { target: revealLight; opacity: 1.0 }
        },
        State {
            name: "hovered"
            when: mouseTracker.containsMouse && !control.down
            PropertyChanges { target: revealLight; opacity: 1.0 }
        }
    ]

    transitions: [
        Transition {
            from: "*"; to: "pressed"
            ParallelAnimation {
                ColorAnimation {
                    target: bg
                    property: "color"
                    duration: 80
                    easing.type: Easing.InQuad
                }
                NumberAnimation {
                    target: revealLight
                    property: "opacity"
                    duration: 80
                    easing.type: Easing.InQuad
                }
            }
        },
        Transition {
            from: "pressed"
            ParallelAnimation {
                ColorAnimation {
                    target: bg
                    property: "color"
                    duration: 200
                    easing.type: Easing.OutCubic
                }
                NumberAnimation {
                    target: revealLight
                    property: "opacity"
                    duration: 200
                    easing.type: Easing.OutCubic
                }
            }
        },
        Transition {
            to: "hovered"
            ParallelAnimation {
                ColorAnimation {
                    target: bg
                    property: "color"
                    duration: 120
                    easing.type: Easing.OutCubic
                }
                NumberAnimation {
                    target: revealLight
                    property: "opacity"
                    duration: 120
                    easing.type: Easing.OutCubic
                }
            }
        },
        Transition {
            from: "hovered"
            ParallelAnimation {
                ColorAnimation {
                    target: bg
                    property: "color"
                    duration: 180
                    easing.type: Easing.OutCubic
                }
                NumberAnimation {
                    target: revealLight
                    property: "opacity"
                    duration: 180
                    easing.type: Easing.OutCubic
                }
            }
        }
    ]
}
