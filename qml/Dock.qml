import QtQuick
import QtQuick.Effects

Item {
    id: kok

    // Python tarafindan doldurulur: ayar, ikonModel, kopru, ikonSayisi
    property string arkaplanTam: ""
    property string arkaplanPanel: ""
    property string vurgu: "#8fb4ff"

    // Referans olculeri: ikon 56, panel 76, yan 12, ara 8, alt bosluk 10.
    readonly property real ikonBoyut: 56
    readonly property real buyutmeCarpan: ayar ? ayar.buyutme : 1.9
    readonly property real bosluk: 8
    readonly property real yanBosluk: 12
    readonly property real icBosluk: 10
    readonly property real panelYukseklik: 76
    readonly property real altPay: 10
    readonly property real hucreYuksekligi: Math.round(ikonBoyut * buyutmeCarpan)
    readonly property real tabanGenislik: ikonSayisi > 0
        ? ikonSayisi * ikonBoyut + (ikonSayisi - 1) * bosluk : 0
    readonly property real panelGenislik: tabanGenislik + 2 * yanBosluk
    readonly property real sigma: 0.85

    property real fareX: -1
    property int ipucu: -1

    function hedefOlcek(i) {
        if (fareX < 0 || ikonSayisi === 0)
            return 1.0
        var sol = (width - tabanGenislik) / 2
        var merkez = sol + i * (ikonBoyut + bosluk) + ikonBoyut / 2
        var d = (fareX - merkez) / (ikonBoyut + bosluk)
        return 1.0 + (buyutmeCarpan - 1.0) * Math.exp(-(d * d) / (2 * sigma * sigma))
    }

    HoverHandler {
        id: fare
        onPointChanged: kok.fareX = fare.point.position.x
        onHoveredChanged: {
            if (!fare.hovered) {
                kok.fareX = -1
                kok.ipucu = -1
            }
        }
    }

    // Masaustu goruntusu: opak pencere, dikissiz birlesir.
    Image {
        anchors.fill: parent
        source: kok.arkaplanTam
        fillMode: Image.Stretch
        cache: false
        smooth: true
    }

    // Panel ustundeki yumusak golge (8 px asagi).
    Rectangle {
        x: panelKutu.x + 6
        y: panelKutu.y + 8
        width: panelKutu.width - 12
        height: panelKutu.height
        radius: 20
        color: "#66000000"
        layer.enabled: true
        layer.effect: MultiEffect {
            blurEnabled: true
            blur: 1.0
            blurMax: 18
        }
    }

    Item {
        id: panelKutu
        width: kok.panelGenislik
        height: kok.panelYukseklik
        x: Math.round((kok.width - width) / 2)
        y: kok.height - kok.altPay - height

        // Arkasi bulanik masaustu (Python'da 12 kat kucult/buyut).
        Image {
            id: arkaPlan
            anchors.fill: parent
            source: kok.arkaplanPanel
            fillMode: Image.Stretch
            cache: false
            visible: false
        }

        MultiEffect {
            anchors.fill: parent
            source: arkaPlan
            blurEnabled: false
            maskEnabled: true
            maskSource: panelMaske
        }

        Rectangle {
            id: panelMaske
            anchors.fill: parent
            radius: 20
            color: "black"
            layer.enabled: true
            visible: false
        }

        // %80 opak koyu katman + ust isik gradyani.
        Rectangle {
            anchors.fill: parent
            radius: 20
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#cd12141a" }
                GradientStop { position: 0.45; color: "#cd0e0e12" }
                GradientStop { position: 1.0; color: "#d10b0b0f" }
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: 20
            color: "#00000000"
            border.width: 1
            border.color: "#22ffffff"
        }

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 1
            width: parent.width - 28
            height: 1
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.5; color: "#30ffffff" }
                GradientStop { position: 1.0; color: "transparent" }
            }
        }
    }

    // --- Ikonlar -----------------------------------------------------------
    Row {
        id: satir
        anchors.horizontalCenter: parent.horizontalCenter
        y: panelKutu.y + panelKutu.height - kok.icBosluk - kok.hucreYuksekligi
        spacing: kok.bosluk
        height: kok.hucreYuksekligi

        Repeater {
            model: ikonModel
            delegate: Item {
                id: hucre
                width: kok.ikonBoyut
                height: kok.hucreYuksekligi
                z: 1 + Math.round(olcekDeger * 10)

                property real olcekDeger: kok.hedefOlcek(index)
                property int parlamaSurum: model.parlama
                property real parParlama: 0
                Behavior on olcekDeger {
                    NumberAnimation { duration: 140; easing.type: Easing.OutQuad }
                }

                Rectangle {
                    id: kutu
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    width: kok.ikonBoyut * hucre.olcekDeger
                    height: width
                    radius: width * 0.24
                    color: "#1affffff"
                }

                Image {
                    anchors.centerIn: kutu
                    width: kutu.width * 0.9
                    height: width
                    source: model.ikon && model.ikon.length > 0
                        ? "file://" + model.ikon : ""
                    sourceSize.width: 64
                    sourceSize.height: 64
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    mipmap: true
                    asynchronous: true
                }

                Rectangle {
                    anchors.fill: kutu
                    radius: kutu.radius
                    color: kok.vurgu
                    opacity: hucre.parParlama * 0.55
                }

                // Acik uygulama: ikonun altinda 4 px daire.
                Rectangle {
                    visible: model.calisti
                    width: 4
                    height: 4
                    radius: 2
                    color: "#aaffffff"
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: kutu.bottom
                    anchors.topMargin: 3
                }

                Rectangle {
                    id: ipucuKutu
                    visible: kok.ipucu === index
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: Math.max(2, kutu.y - height - 6)
                    width: ipucuMetin.implicitWidth + 16
                    height: ipucuMetin.implicitHeight + 10
                    radius: 7
                    color: "#e6141820"
                    border.width: 1
                    border.color: "#40ffffff"

                    Text {
                        id: ipucuMetin
                        anchors.centerIn: parent
                        text: model.hata && model.hata.length > 0
                            ? model.ad + " — " + model.hata : model.ad
                        color: model.hata && model.hata.length > 0 ? "#ffb3b3" : "#f2f4f8"
                        font.pixelSize: 12
                    }
                }

                Timer {
                    id: ipucuZaman
                    interval: 350
                    onTriggered: kok.ipucu = index
                }

                MouseArea {
                    anchors.fill: kutu
                    cursorShape: Qt.PointingHandCursor
                    hoverEnabled: true
                    onEntered: ipucuZaman.start()
                    onExited: {
                        ipucuZaman.stop()
                        if (kok.ipucu === index)
                            kok.ipucu = -1
                    }
                    onClicked: kopru.tikla(index)
                }

                SequentialAnimation {
                    id: parlamaAnim
                    NumberAnimation { target: hucre; property: "parParlama"; to: 1; duration: 90 }
                    NumberAnimation { target: hucre; property: "parParlama"; to: 0; duration: 310 }
                }

                onParlamaSurumChanged: {
                    if (parlamaSurum > 0)
                        parlamaAnim.restart()
                }
            }
        }
    }
}
