import QtQuick

Item {
    id: kart
    width: 320
    height: 210

    property string kartKaynak: ""
    readonly property color ana: "#F7F7F8"
    readonly property color ikincil: "#9A9AA0"
    readonly property color ucuncul: "#8E8E93"
    readonly property color ayirici: "#262628"
    readonly property color ray: "#2C2C2E"

    function konumBildir() {
        kopru.muzik_konumu(Math.round(x), Math.round(y), Math.round(width), Math.round(height))
    }
    onXChanged: konumBildir()
    onYChanged: konumBildir()
    Component.onCompleted: konumBildir()

    function sure(ms) {
        var s = Math.max(0, Math.floor(ms / 1000))
        return Math.floor(s / 60) + ":" + (s % 60 < 10 ? "0" : "") + (s % 60)
    }

    Image {
        source: "image://arkaplan/muzikGolge"
        x: -10; y: -10
        width: parent.width + 20; height: parent.height + 20
        fillMode: Image.Stretch; smooth: true
    }
    Image {
        anchors.fill: parent
        source: kart.kartKaynak
        fillMode: Image.Stretch
        cache: true
        smooth: true
    }
    Rectangle {
        anchors.fill: parent
        radius: 14
        color: "#00000000"
        border.width: 1
        border.color: "#30ffffff"
    }
    Rectangle {
        anchors.top: parent.top
        anchors.topMargin: 1
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width - 28
        height: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.5; color: "#3dffffff" }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    MouseArea { anchors.fill: parent }

    Image {
        x: 18; y: 16
        width: 88; height: 88
        source: muzikModel.kapak !== "" ? "file://" + muzikModel.kapak : ""
        fillMode: Image.PreserveAspectCrop
        smooth: true
        asynchronous: true
    }

    GolgeText {
        x: 118; y: 16; width: 184
        text: muzikModel.baslik
        color: kart.ana
        font.pixelSize: 13
        font.weight: Font.Medium
        elide: Text.ElideRight
    }
    Text {
        x: 118; y: 38; width: 184
        text: muzikModel.sanatci + (muzikModel.album ? " · " + muzikModel.album : "")
        color: kart.ikincil
        font.pixelSize: 11
        elide: Text.ElideRight
    }

    Rectangle { x: 18; y: 112; width: parent.width - 36; height: 1; color: kart.ayirici }

    Item {
        id: cubukAlan
        x: 18; y: 118
        width: parent.width - 36
        height: 12
        Rectangle {
            id: ray
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            height: cubukFare.containsMouse ? 6 : 4
            radius: height / 2
            color: kart.ray
            Behavior on height { NumberAnimation { duration: 120 } }
            Rectangle {
                width: muzikModel.sureMs > 0
                    ? parent.width * Math.min(1, muzikModel.konumMs / muzikModel.sureMs) : 0
                height: parent.height
                radius: parent.radius
                color: kart.ana
                Behavior on width { NumberAnimation { duration: 700; easing.type: Easing.OutQuad } }
            }
        }
        MouseArea {
            id: cubukFare
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: function(mouse) { muzikModel.ara(mouse.x / width) }
        }
    }

    Text {
        x: 18; y: 132
        text: kart.sure(muzikModel.konumMs)
        color: kart.ikincil
        font.pixelSize: 11
        font.family: "Geist Mono"
    }
    Text {
        anchors.right: parent.right
        anchors.rightMargin: 18
        y: 132
        text: kart.sure(muzikModel.sureMs)
        color: kart.ikincil
        font.pixelSize: 11
        font.family: "Geist Mono"
    }

    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 150
        spacing: 24

        Item {
            width: 32; height: 32
            Rectangle { anchors.fill: parent; radius: 16; color: geriFare.containsMouse ? "#1C1C1E" : "transparent" }
            Canvas {
                anchors.fill: parent
                onPaint: {
                    var c = getContext("2d"); c.reset(); c.fillStyle = "#F7F7F8"
                    c.beginPath(); c.moveTo(7,16); c.lineTo(17,7); c.lineTo(17,25); c.fill()
                    c.beginPath(); c.moveTo(17,16); c.lineTo(27,7); c.lineTo(27,25); c.fill()
                }
            }
            MouseArea {
                id: geriFare; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: muzikModel.geri()
            }
        }

        Item {
            width: 36; height: 36
            Rectangle {
                anchors.fill: parent; radius: 18
                color: oynatFare.containsMouse ? "#E4E4E8" : kart.ana
            }
            Canvas {
                id: oynatCanvas
                anchors.fill: parent
                property bool caliyor: muzikModel.caliyor
                onCaliyorChanged: requestPaint()
                onPaint: {
                    var c = getContext("2d"); c.reset(); c.fillStyle = "#0A0A0A"
                    if (oynatCanvas.caliyor) {
                        c.fillRect(12, 10, 5, 16)
                        c.fillRect(20, 10, 5, 16)
                    } else {
                        c.beginPath(); c.moveTo(12, 9); c.lineTo(25, 18); c.lineTo(12, 27); c.fill()
                    }
                }
            }
            MouseArea {
                id: oynatFare; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: muzikModel.oynatDuraklat()
            }
        }

        Item {
            width: 32; height: 32
            Rectangle { anchors.fill: parent; radius: 16; color: ileriFare.containsMouse ? "#1C1C1E" : "transparent" }
            Canvas {
                anchors.fill: parent
                onPaint: {
                    var c = getContext("2d"); c.reset(); c.fillStyle = "#F7F7F8"
                    c.beginPath(); c.moveTo(27,16); c.lineTo(17,7); c.lineTo(17,25); c.fill()
                    c.beginPath(); c.moveTo(17,16); c.lineTo(7,7); c.lineTo(7,25); c.fill()
                }
            }
            MouseArea {
                id: ileriFare; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: muzikModel.ileri()
            }
        }
    }

    Text {
        x: 18; y: 192
        text: muzikModel.demo ? "demo · oynatıcı yok" : "MPRIS"
        color: kart.ucuncul
        font.pixelSize: 11
    }
}
