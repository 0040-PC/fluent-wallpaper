import QtQuick
import QtQuick.Layouts
import Veil

Item {
    id: control
    
    property string icon: ""
    property string text: ""
    property bool isSelected: false
    property bool dark: true 
    
    property color accentColor: "#008080"
    property color normalColor: dark ? "white" : "black"
    
    property color hoverColor: dark ? Qt.rgba(1, 1, 1, 0.06) : Qt.rgba(0, 0, 0, 0.04)
    property color pressedColor: dark ? Qt.rgba(1, 1, 1, 0.09) : Qt.rgba(0, 0, 0, 0.08)
    property color selectedBgColor: dark ? Qt.rgba(1, 1, 1, 0.08) : Qt.rgba(0, 0, 0, 0.06)
    
    property real iconSize: 22 
    property real radius: 4

    signal clicked()

    implicitWidth: 80 
    implicitHeight: 70

    Rectangle {
        id: background
        anchors.fill: parent
        anchors.margins: 2 
        radius: control.radius
        
        // 终极绑定：直接根据交互状态输出颜色，没有任何状态机开销
        color: {
            if (control.isSelected) return control.selectedBgColor
            if (mouseArea.pressed) return control.pressedColor
            if (mouseArea.containsMouse) return control.hoverColor
            return "transparent"
        }

        VeilClickImpulse {
            id: impulseEffect
            anchors.fill: parent
            flashColor: control.dark ? Qt.rgba(1,1,1,0.12) : Qt.rgba(0,0,0,0.06)
            z: 1
        }
    }

    RowLayout {
        anchors.centerIn: parent
        spacing: 8
        
        Text {
            id: iconText
            text: control.icon
            font.family: "Segoe Fluent Icons"
            font.pixelSize: control.iconSize
            // 图标颜色也同样处理
            color: control.isSelected ? control.accentColor : control.normalColor
        }
        
        Text {
            visible: control.text !== "" && control.width > 100
            text: control.text
            font.pixelSize: 14
            font.weight: control.isSelected ? Font.DemiBold : Font.Normal
            color: control.normalColor
            elide: Text.ElideRight
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true

        property point lastPos: Qt.point(width/2, height/2)
        onPressed: (mouse) => lastPos = Qt.point(mouse.x, mouse.y)

        onClicked: {
            impulseEffect.trigger(lastPos.x, lastPos.y)
            control.clicked()
        }
    }
}
