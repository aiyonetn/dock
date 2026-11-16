import QtQuick
import QtQuick.Effects

Item {
    id: kart
    width: 320
    height: 194

    property string kartKaynak: ""
    readonly property color ana: "#F7F7F8"
    readonly property color ikincil: "#A1A1A6"
    readonly property color ucuncul: "#74747A"
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
        x: -10
        y: -10
        width: parent.width + 20
        height: parent.height + 20
        fillMode: Image.Stretch
        smooth: true
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

    // Bos alan tiklamalarini yut (dugmeler ustte kalir).
    MouseArea { anchors.fill: parent }

    // --- Kapak -------------------------------------------------------------
    Item {
        id: kapakKutu
        x: 18
        y: 18
        width: 56
        height: 56
    }

    Rectangle {
        visible: muzikModel.kapak === ""
        anchors.fill: kapakKutu
        radius: 8
        color: "#1C1C1E"
    }

    Canvas {
        visible: muzikModel.kapak === ""
        anchors.fill: kapakKutu
        onPaint: {
            var c = getContext("2d")
            c.reset()
            c.strokeStyle = "#A1A1A6"
            c.fillStyle = "#A1A1A6"
            c.lineWidth = 2.5
            c.beginPath()
            c.ellipse(18, 35, 6, 5, 0, 0, Math.PI * 2)
            c.fill()
            c.beginPath()
            c.moveTo(23.5, 37)
            c.lineTo(23.5, 17)
            c.quadraticCurveTo(35, 18, 37, 27)
            c.lineTo(37, 23)
            c.stroke()
        }
    }

    Image {
        id: kapakResim
        visible: false
        source: muzikModel.kapak
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        sourceSize.width: 112
        sourceSize.height: 112
    }

    Rectangle {
        id: kapakMaske
        anchors.fill: kapakKutu
        radius: 8
        color: "black"
        layer.enabled: true
        visible: false
    }

    MultiEffect {
        anchors.fill: kapakKutu
        visible: muzikModel.kapak !== ""
        source: kapakResim
        maskEnabled: true
        maskSource: kapakMaske
    }

    // --- Baslik ------------------------------------------------------------
    GolgeText {
        x: 86
        y: 18
        width: 216
        text: muzikModel.baslik
        color: kart.ana
        font.pixelSize: 13
        font.weight: Font.DemiBold
        elide: Text.ElideRight
    }
    GolgeText {
        x: 86
        y: 36
        width: 216
        text: muzikModel.sanatci + (muzikModel.album ? " · " + muzikModel.album : "")
        color: "#9A9AA0"
        font.pixelSize: 11
        elide: Text.ElideRight
    }

    Rectangle {
        x: 18
        y: 82
        width: parent.width - 36
        height: 1
        color: kart.ayirici
    }

    // --- Ilerleme ----------------------------------------------------------
    Rectangle {
        x: 18
        y: 91
        width: parent.width - 36
        height: 4
        radius: 2
        color: kart.ray
        Rectangle {
            width: muzikModel.sureMs > 0
                ? parent.width * Math.min(1, muzikModel.konumMs / muzikModel.sureMs) : 0
            height: parent.height
            Behavior on width { NumberAnimation { duration: 700; easing.type: Easing.OutQuad } }
            radius: 2
            color: kart.ana
        }
    }

    GolgeText {
        x: 18
        y: 99
        text: kart.sure(muzikModel.konumMs)
        color: "#9A9AA0"
        font.pixelSize: 10
    }
    GolgeText {
        anchors.right: parent.right
        anchors.rightMargin: 18
        y: 99
        text: kart.sure(muzikModel.sureMs)
        color: "#9A9AA0"
        font.pixelSize: 10
    }

    // --- Dugmeler ----------------------------------------------------------
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 123
        spacing: 24

        Item {
            width: 28
            height: 28
            Rectangle {
                anchors.fill: parent
                radius: 14
                color: geriFare.containsMouse ? "#1C1C1E" : "transparent"
            }
            Canvas {
                anchors.fill: parent
                onPaint: {
                    var c = getContext("2d")
                    c.reset()
                    c.fillStyle = "#F7F7F8"
                    c.beginPath(); c.moveTo(6, 14); c.lineTo(14, 6); c.lineTo(14, 22); c.fill()
                    c.beginPath(); c.moveTo(14, 14); c.lineTo(22, 6); c.lineTo(22, 22); c.fill()
                }
            }
            MouseArea {
                id: geriFare
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: muzikModel.geri()
            }
        }

        Item {
            width: 28
            height: 28
            Rectangle {
                anchors.fill: parent
                radius: 14
                color: oynatFare.containsMouse ? "#E4E4E8" : kart.ana
            }
            Canvas {
                id: oynatCanvas
                anchors.fill: parent
                property bool caliyor: muzikModel.caliyor
                onCaliyorChanged: requestPaint()
                onPaint: {
                    var c = getContext("2d")
                    c.reset()
                    c.fillStyle = "#0A0A0A"
                    if (oynatCanvas.caliyor) {
                        c.fillRect(9, 7, 4, 14)
                        c.fillRect(15, 7, 4, 14)
                    } else {
                        c.beginPath(); c.moveTo(8, 6); c.lineTo(19, 14); c.lineTo(8, 22); c.fill()
                    }
                }
            }
            MouseArea {
                id: oynatFare
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: muzikModel.oynatDuraklat()
            }
        }

        Item {
            width: 28
            height: 28
            Rectangle {
                anchors.fill: parent
                radius: 14
                color: ileriFare.containsMouse ? "#1C1C1E" : "transparent"
            }
            Canvas {
                anchors.fill: parent
                onPaint: {
                    var c = getContext("2d")
                    c.reset()
                    c.fillStyle = "#F7F7F8"
                    c.beginPath(); c.moveTo(22, 14); c.lineTo(14, 6); c.lineTo(14, 22); c.fill()
                    c.beginPath(); c.moveTo(14, 14); c.lineTo(6, 6); c.lineTo(6, 22); c.fill()
                }
            }
            MouseArea {
                id: ileriFare
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: muzikModel.ileri()
            }
        }
    }

    GolgeText {
        x: 18
        y: 163
        text: muzikModel.demo ? "demo · oynatıcı yok" : "MPRIS"
        color: "#8E8E93"
        font.pixelSize: 11
    }

}
