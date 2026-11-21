import QtQuick
import Qt5Compat.GraphicalEffects

Item {
    id: kok

    // Python tarafindan doldurulur: ayar, ikonModel, kopru, ikonSayisi
    property string arkaplanTam: ""
    property string arkaplanPanel: ""
    property string vurgu: "#8fb4ff"

    // Referans olculeri: ikon 56, panel 76, yan 12, ara 8, alt bosluk 10.
    readonly property real ikonBoyut: ayar ? ayar.iconSize : 64
    readonly property real buyutmeCarpan: ayar ? ayar.buyutme : 1.9
    readonly property real bosluk: 12
    readonly property real yanBosluk: 16
    readonly property real icBosluk: Math.round((panelYukseklik - ikonBoyut) / 2)
    readonly property real panelYukseklik: 108
    readonly property real altPay: 12
    readonly property real hucreYuksekligi: Math.round(ikonBoyut * buyutmeCarpan)
    readonly property real tabanGenislik: ikonSayisi > 0
        ? ikonSayisi * ikonBoyut + (ikonSayisi - 1) * bosluk : 0
    // Buyuyen ikonlar komsularini iter; panel icerik kadar genisler.
    readonly property real icerikGenislik: {
        var toplam = 0
        for (var i = 0; i < ikonSayisi; i++)
            toplam += ikonBoyut * hedefOlcek(i)
        return toplam + Math.max(0, ikonSayisi - 1) * bosluk
    }
    readonly property real panelGenislik: icerikGenislik + 2 * yanBosluk

    property real fareX: -1
    property int ipucu: -1
    property bool kartAcik: false
    property bool muzikAcik: false
    property string kartKaynak: ""
    property string muzikKaynak: ""
    property real aiMerkezX: 0
    property Item muzikHucre: null
    property real pencereSol: _pencereSol
    property real ekranGenislik: _ekranGenislik

    // Imlece en yakin ikon; yalnizca o buyur (komsu gaussian yok).
    readonly property int yakinIkon: {
        if (fareX < 0 || ikonSayisi === 0)
            return -1
        var sol = (width - tabanGenislik) / 2
        var indeks = Math.round(
            (fareX - sol - ikonBoyut / 2) / (ikonBoyut + bosluk))
        return Math.max(0, Math.min(ikonSayisi - 1, indeks))
    }

    function hedefOlcek(i) {
        var n = yakinIkon
        if (n < 0)
            return 1.0
        if (i === n)
            return buyutmeCarpan
        return 1.0
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
        cache: true
        smooth: true
    }

    // Panel golgesi: Python tarafinda bir kez uretilir. Onceden burada
    // layer + MultiEffect vardi; yazilim render'da her karede ek gecis
    // maliyeti cikariyordu. Artik tek dokulu dikdortgen.
    Image {
        source: golgeUrl
        x: panelKutu.x - 20
        y: panelKutu.y - 20
        width: panelKutu.width + 40
        height: panelKutu.height + 40
        fillMode: Image.Stretch
        smooth: true
    }

    Item {
        id: panelKutu
        width: kok.panelGenislik
        height: kok.panelYukseklik
        x: Math.round((kok.width - width) / 2)
        y: kok.height - kok.altPay - height
        Behavior on width { NumberAnimation { duration: 140; easing.type: Easing.OutQuad } }
        Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutQuad } }
        onWidthChanged: panelYenile.restart()

        Timer {
            id: panelYenile
            interval: 170
            onTriggered: kopru.panel_genislik(Math.round(panelKutu.width), Math.round(panelKutu.x))
        }

        // Arkasi bulanik masaustu (Python'da 12 kat kucult/buyut).
        Image {
            id: arkaPlan
            anchors.fill: parent
            source: kok.arkaplanPanel
            fillMode: Image.Stretch
            cache: true
        }

        Rectangle {
            anchors.fill: parent
            radius: yaricaplar.panel
            color: "#00000000"
            border.width: 1
            border.color: "#14ffffff"
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
                GradientStop { position: 0.5; color: "#24ffffff" }
                GradientStop { position: 1.0; color: "transparent" }
            }
        }
    }

    // --- Ikonlar -----------------------------------------------------------
    Item {
        id: satir
        width: kok.icerikGenislik
        x: (kok.width - width) / 2
        y: panelKutu.y + panelKutu.height - kok.icBosluk - kok.hucreYuksekligi
        height: kok.hucreYuksekligi

        Behavior on width { NumberAnimation { duration: 140; easing.type: Easing.OutQuad } }
        Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutQuad } }

        Repeater {
            model: ikonModel
            delegate: Item {
                id: hucre
                // Konumlar birikimli genislikten: buyuyen ikon komsusunu iter.
                x: {
                    var konum = 0
                    for (var j = 0; j < index; j++)
                        konum += kok.ikonBoyut * kok.hedefOlcek(j) + kok.bosluk
                    return konum
                }
                width: kok.ikonBoyut * hucre.olcekDeger
                height: kok.hucreYuksekligi
                z: 1 + Math.round(olcekDeger * 10)

                Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutQuad } }
                function aiBildir() {
                    if (model.kimlik === "ai-limit.desktop")
                        kok.aiMerkezX = satir.x + hucre.x + hucre.width / 2
                }
                onXChanged: aiBildir()
                onWidthChanged: aiBildir()
                Component.onCompleted: {
                    aiBildir()
                    if (model.kimlik === "muzik.desktop")
                        kok.muzikHucre = hucre
                }
                property real olcekDeger: kok.hedefOlcek(index)
                property int parlamaSurum: model.parlama
                property real parParlama: 0
                Behavior on olcekDeger {
                    NumberAnimation { duration: 140; easing.type: Easing.OutQuad }
                }

                Rectangle {
                    visible: model.kimlik === "muzik.desktop"
                    width: 1
                    height: 44
                    color: "#30ffffff"
                    anchors.verticalCenter: parent.verticalCenter
                    x: -7
                }

                Item {
                    id: kutu
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    width: kok.ikonBoyut * hucre.olcekDeger
                    height: width
                }

                // Ikon + gomulu yumusak golge (1 px asagi, 6 px blur).
                Image {
                    id: simge
                    visible: model.kimlik !== "muzik.desktop"
                    anchors.centerIn: kutu
                    width: kutu.width
                    height: width
                    source: model.ikon && model.ikon.length > 0
                        ? "file://" + model.ikon : ""
                    sourceSize.width: 160
                    sourceSize.height: 160
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    mipmap: false
                    asynchronous: true
                }

                Item {
                    id: muzikKapakKutu
                    visible: model.kimlik === "muzik.desktop" && muzikModel.kapak !== ""
                    anchors.centerIn: kutu
                    width: kutu.width * 0.8
                    height: width

                    Image {
                        id: muzikKapakKaynak
                        anchors.fill: parent
                        source: muzikModel.kapak !== "" ? "file://" + muzikModel.kapak : ""
                        fillMode: Image.PreserveAspectCrop
                        smooth: true
                        asynchronous: true
                        visible: false
                    }
                    Rectangle {
                        id: muzikKapakMaske
                        anchors.fill: parent
                        radius: yaricaplar.ikonKapak
                        color: "white"
                        layer.enabled: true
                        visible: false
                    }
                    OpacityMask {
                        anchors.fill: parent
                        source: muzikKapakKaynak
                        maskSource: muzikKapakMaske
                    }
                }

                Item {
                    visible: model.kimlik === "muzik.desktop"
                    anchors.horizontalCenter: kutu.horizontalCenter
                    anchors.bottom: kutu.bottom
                    anchors.bottomMargin: 6
                    width: 10
                    height: 12
                    property real faz: 0
                    Timer {
                        interval: 250
                        repeat: true
                        running: muzikModel.caliyor && model.kimlik === "muzik.desktop"
                            && kok.fareX >= 0
                        onTriggered: parent.faz += 0.9
                    }
                    Rectangle {
                        x: 0; width: 2; radius: 1; color: "#F7F7F8"
                        height: muzikModel.caliyor ? 6 + 6 * Math.abs(Math.sin(parent.faz)) : 3
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Rectangle {
                        x: 4; width: 2; radius: 1; color: "#F7F7F8"
                        height: muzikModel.caliyor ? 6 + 6 * Math.abs(Math.sin(parent.faz + 2.1)) : 3
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Rectangle {
                        x: 8; width: 2; radius: 1; color: "#F7F7F8"
                        height: muzikModel.caliyor ? 6 + 6 * Math.abs(Math.sin(parent.faz + 4.2)) : 3
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                Rectangle {
                    anchors.centerIn: kutu
                    width: kutu.width * 0.78
                    height: width
                    radius: 12 * hucre.olcekDeger
                    color: kok.vurgu
                    opacity: hucre.parParlama * 0.55
                }

                // Acik uygulama: ikonun altinda 4 px daire.
                Rectangle {
                    visible: model.calisti
                    width: 6
                    height: 6
                    radius: 3
                    color: "#ffffffff"
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

    // Kart acikken panel ustune tiklamak kapatir; ikonlar etkilenmez.
    MouseArea {
        visible: kok.kartAcik || kok.muzikAcik
        z: 30
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: panelKutu.top
        onClicked: {
            kok.kartAcik = false
            kok.muzikAcik = false
            kopru.kartKapat()
        }
    }

    LimitKarti {
        id: kart
        z: 31
        readonly property real aiGenislik: kok.ikonBoyut * kok.hedefOlcek(kok.ikonSayisi - 1)
        readonly property real hedefY: panelKutu.y - height - 16
        kartKaynak: kok.kartKaynak
        visible: kok.kartAcik || opacity > 0
        opacity: kok.kartAcik ? 1 : 0
        x: Math.round(Math.max(12 - kok.pencereSol,
            Math.min(kok.ekranGenislik - 12 - width - kok.pencereSol,
                satir.x + satir.width - aiGenislik / 2 - width / 2)))
        y: Math.round(hedefY + (kok.kartAcik ? 0 : 6))
        Behavior on opacity {
            NumberAnimation { duration: 120; easing.type: Easing.OutQuad }
        }
        Behavior on y {
            NumberAnimation { duration: 120; easing.type: Easing.OutQuad }
        }
    }

    MusicKarti {
        id: muzikKart
        z: 31
        kartKaynak: kok.muzikKaynak
        readonly property real aiGenislik: kok.ikonBoyut * kok.hedefOlcek(kok.ikonSayisi - 1)
        readonly property real kendiGenislik: kok.ikonBoyut * kok.hedefOlcek(kok.ikonSayisi - 2)
        readonly property real merkezX: kok.muzikHucre
            ? satir.x + kok.muzikHucre.x + kok.muzikHucre.width / 2
            : satir.x + satir.width - aiGenislik - kok.bosluk - kendiGenislik / 2
        readonly property real hedefY: panelKutu.y - height - 16
        visible: kok.muzikAcik || opacity > 0
        opacity: kok.muzikAcik ? 1 : 0
        x: Math.round(Math.max(12 - kok.pencereSol,
            Math.min(kok.ekranGenislik - 12 - width - kok.pencereSol,
                merkezX - width / 2)))
        y: Math.round(hedefY + (kok.muzikAcik ? 0 : 6))
        Behavior on opacity {
            NumberAnimation { duration: 120; easing.type: Easing.OutQuad }
        }
        Behavior on y {
            NumberAnimation { duration: 120; easing.type: Easing.OutQuad }
        }
    }
}
