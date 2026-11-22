import QtQuick
import Qt5Compat.GraphicalEffects

// Lumbara "Now Playing" duzeni: opak #1C1C1C hap kartlar.
// Alfa < 255 zemin yok; yalnizca dis golge karta tasar.
Item {
    id: kart
    readonly property int secili: muzikModel.gorunum
    readonly property int kose: secili === 2 ? 20 : (secili === 1 || secili === 3 ? 16 : 18)
    readonly property int dugmeBoy: secili === 2 || secili === 3 ? 12
        : (secili >= 4 ? 14 : 16)
    readonly property int seciciAra: secili === 0 ? 3 : 2
    readonly property int seciciY: secili === 3 ? 2 : (secili === 1 ? 3 : (secili === 2 ? 4 : 5))

    width: {
        switch (secili) {
        case 0: return 360
        case 1: return 300
        case 2: return 120
        case 3: return 380
        default: return 320
        }
    }
    height: {
        switch (secili) {
        case 0: return 84
        case 1: return 68
        case 2: return 120
        case 3: return 56
        default: return 110
        }
    }

    readonly property color ana: "#F7F7F8"
    readonly property color ikincil: "#9A9AA0"
    readonly property color ucuncul: "#74747A"
    readonly property color zemin: "#1C1C1C"
    readonly property color yuzey: "#2A2A2C"
    readonly property color yuzeyFare: "#333336"
    readonly property color kenar: "#3A3A3A"
    readonly property color ray: "#2A2A2C"
    readonly property color mavi: "#4CC2FF"
    readonly property color uyari: "#FF9F0A"

    function konumBildir() {
        kopru.muzik_konumu(Math.round(x), Math.round(y), Math.round(width), Math.round(height))
    }
    onXChanged: konumBildir()
    onYChanged: konumBildir()
    onWidthChanged: konumBildir()
    onHeightChanged: konumBildir()
    Component.onCompleted: konumBildir()

    function sure(ms) {
        var s = Math.max(0, Math.floor(ms / 1000))
        return Math.floor(s / 60) + ":" + (s % 60 < 10 ? "0" : "") + (s % 60)
    }
    function kalanSure() {
        return sure(Math.max(0, muzikModel.sureMs - muzikModel.konumMs))
    }

    Timer {
        interval: 1200
        repeat: true
        running: kart.visible && kart.secili >= 4
        onTriggered: sesModel.yenile()
    }
    onSeciliChanged: {
        if (secili >= 4)
            sesModel.yenile()
        konumBildir()
    }

    // Dis golge (kart icinde degil, kartin arkasinda).
    Image {
        source: "image://arkaplan/muzikGolge"
        x: -10; y: -10
        width: parent.width + 20; height: parent.height + 20
        fillMode: Image.Stretch; smooth: true
    }

    // Opak zemin: duz #1C1C1C, 1 px ic kenar.
    Rectangle {
        anchors.fill: parent
        radius: kart.kose
        color: kart.zemin
        border.width: 1
        border.color: kart.kenar
    }

    MouseArea { anchors.fill: parent }

    // --- 6'li secici -------------------------------------------------------
    component SeciciDugme: Item {
        id: dugme
        property int tur: 0
        property int indeks: 0
        property bool aktif: false
        width: kart.dugmeBoy
        height: kart.dugmeBoy
        Rectangle {
            anchors.fill: parent
            radius: 5
            color: dugme.aktif ? kart.yuzey
                : (secFare.containsMouse ? kart.yuzeyFare : kart.zemin)
        }
        Canvas {
            id: secCizim
            anchors.fill: parent
            property int tip: dugme.tur
            property color cizgi: dugme.aktif ? kart.mavi : kart.ikincil
            onTipChanged: requestPaint()
            onCizgiChanged: requestPaint()
            onPaint: {
                var c = getContext("2d")
                c.reset()
                c.save()
                c.scale(width / 22, height / 22)
                c.strokeStyle = secCizim.cizgi
                c.fillStyle = secCizim.cizgi
                c.lineWidth = 1.5
                c.lineCap = "round"
                var m = 11, n = 11
                switch (tip) {
                case 0: // tam
                    c.strokeRect(m - 7, n - 5, 14, 10)
                    c.fillRect(m - 5, n - 3, 4, 6)
                    break
                case 1: // kompakt
                    c.strokeRect(m - 7, n - 4, 14, 8)
                    c.beginPath(); c.moveTo(m - 3, n); c.lineTo(m + 4, n); c.stroke()
                    break
                case 2: // mini
                    c.strokeRect(m - 4, n - 4, 8, 8)
                    c.beginPath(); c.arc(m, n, 8, 0.3, 1.8); c.stroke()
                    break
                case 3: // bar
                    c.strokeRect(m - 8, n - 2, 16, 4)
                    break
                case 4: // ses cikisi
                    c.beginPath()
                    c.moveTo(m - 7, n - 2); c.lineTo(m - 4, n - 2); c.lineTo(m, n - 6)
                    c.lineTo(m, n + 6); c.lineTo(m - 4, n + 2); c.lineTo(m - 7, n + 2)
                    c.closePath(); c.fill()
                    c.beginPath(); c.arc(m + 1, n, 5, -0.8, 0.8); c.stroke()
                    break
                case 5: // mikrofon
                    c.beginPath()
                    c.moveTo(m - 2.5, n - 6); c.lineTo(m + 2.5, n - 6)
                    c.lineTo(m + 2.5, n - 1); c.arc(m, n - 1, 2.5, 0, Math.PI)
                    c.closePath(); c.fill()
                    c.beginPath()
                    c.arc(m, n + 1, 5, 0.15, Math.PI - 0.15)
                    c.moveTo(m, n + 6); c.lineTo(m, n + 8)
                    c.moveTo(m - 3, n + 8); c.lineTo(m + 3, n + 8)
                    c.stroke()
                    break
                }
                c.restore()
            }
        }
        MouseArea {
            id: secFare
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: muzikModel.gorunumSec(dugme.indeks)
        }
    }

    Row {
        spacing: kart.seciciAra
        anchors.horizontalCenter: parent.horizontalCenter
        y: kart.seciciY
        Repeater {
            model: 6
            delegate: SeciciDugme {
                tur: index
                indeks: index
                aktif: kart.secili === index
            }
        }
    }

    // --- ortak parcalar ----------------------------------------------------
    component Kapak: Item {
        id: kapak
        property int boy: 44
        property int kose: 10
        width: boy; height: boy
        Image {
            id: kapakKaynak
            anchors.fill: parent
            source: muzikModel.kapak !== "" ? "file://" + muzikModel.kapak : ""
            fillMode: Image.PreserveAspectCrop
            smooth: true
            asynchronous: true
            visible: false
        }
        Rectangle {
            id: kapakMaske
            anchors.fill: parent
            radius: kapak.kose
            color: "white"
            layer.enabled: true
            visible: false
        }
        OpacityMask {
            anchors.fill: parent
            source: kapakKaynak
            maskSource: kapakMaske
        }
    }

    component DaireDugme: Item {
        id: daire
        property int boy: 32
        property string tur: "oynat"
        property bool caliyor: false
        property bool susturulmus: false
        signal tiklandi()
        width: boy; height: boy
        Rectangle {
            anchors.fill: parent
            radius: boy / 2
            color: daireFare.containsMouse ? kart.yuzeyFare : kart.yuzey
        }
        Canvas {
            id: ikon
            anchors.fill: parent
            property string tur: daire.tur
            property bool caliyor: daire.caliyor
            property bool susturulmus: daire.susturulmus
            onTurChanged: requestPaint()
            onCaliyorChanged: requestPaint()
            onSusturulmusChanged: requestPaint()
            onPaint: {
                var c = getContext("2d")
                c.reset()
                c.save()
                c.scale(width / 48, height / 48)
                c.fillStyle = "#F7F7F8"
                c.strokeStyle = "#F7F7F8"
                c.lineWidth = 2.4
                c.lineCap = "round"
                c.lineJoin = "round"
                var m = 24
                if (tur === "oynat") {
                    if (caliyor) {
                        c.fillRect(m - 7, m - 9, 5, 18)
                        c.fillRect(m + 2, m - 9, 5, 18)
                    } else {
                        c.beginPath()
                        c.moveTo(m - 5, m - 9); c.lineTo(m + 10, m); c.lineTo(m - 5, m + 9)
                        c.closePath(); c.fill()
                    }
                } else if (tur === "geri") {
                    c.beginPath(); c.moveTo(m - 2, m); c.lineTo(m - 12, m - 9); c.lineTo(m - 12, m + 9); c.fill()
                    c.beginPath(); c.moveTo(m + 10, m); c.lineTo(m, m - 9); c.lineTo(m, m + 9); c.fill()
                } else if (tur === "ileri") {
                    c.beginPath(); c.moveTo(m + 2, m); c.lineTo(m + 12, m - 9); c.lineTo(m + 12, m + 9); c.fill()
                    c.beginPath(); c.moveTo(m - 10, m); c.lineTo(m, m - 9); c.lineTo(m, m + 9); c.fill()
                } else if (tur === "hoparlor") {
                    c.beginPath()
                    c.moveTo(m - 12, m - 4); c.lineTo(m - 7, m - 4); c.lineTo(m - 1, m - 11)
                    c.lineTo(m - 1, m + 11); c.lineTo(m - 7, m + 4); c.lineTo(m - 12, m + 4)
                    c.closePath(); c.fill()
                    c.beginPath(); c.arc(m, m, 9, -0.9, 0.9); c.stroke()
                } else if (tur === "mikrofon") {
                    c.beginPath()
                    c.moveTo(m - 4, m - 13); c.lineTo(m + 4, m - 13)
                    c.lineTo(m + 4, m - 4); c.arc(m, m - 4, 4, 0, Math.PI)
                    c.closePath(); c.fill()
                    c.beginPath()
                    c.arc(m, m, 9, 0.15, Math.PI - 0.15)
                    c.moveTo(m, m + 9); c.lineTo(m, m + 13)
                    c.moveTo(m - 6, m + 13); c.lineTo(m + 6, m + 13)
                    c.stroke()
                }
                if (susturulmus) {
                    c.strokeStyle = "#FF9F0A"
                    c.lineWidth = 3
                    c.beginPath()
                    c.moveTo(m - 11, m - 11); c.lineTo(m + 11, m + 11)
                    c.stroke()
                }
                c.restore()
            }
        }
        MouseArea {
            id: daireFare
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: daire.tiklandi()
        }
    }

    component Ilerleme: Item {
        id: cubuk
        property int kalinlik: 3
        property bool etkin: true
        readonly property real oran: muzikModel.sureMs > 0
            ? Math.max(0, Math.min(1, muzikModel.konumMs / muzikModel.sureMs)) : 0
        height: Math.max(12, kalinlik)
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            height: cubuk.kalinlik
            radius: cubuk.kalinlik / 2
            color: kart.ray
            Rectangle {
                width: parent.width * cubuk.oran
                height: parent.height
                radius: parent.radius
                color: kart.mavi
                Behavior on width { NumberAnimation { duration: 600; easing.type: Easing.OutQuad } }
            }
        }
        MouseArea {
            anchors.fill: parent
            enabled: cubuk.etkin
            cursorShape: Qt.PointingHandCursor
            onClicked: function(m) { muzikModel.ara(Math.max(0, Math.min(1, m.x / width))) }
        }
    }

    // --- 0: tam ------------------------------------------------------------
    Item {
        anchors.fill: parent
        visible: kart.secili === 0
        Kapak { x: 14; y: 30; boy: 44; kose: 10 }
        Text {
            x: 68; y: 28; width: 238
            text: muzikModel.baslik
            color: kart.ana
            font.pixelSize: 14
            font.weight: Font.Bold
            elide: Text.ElideRight
        }
        Text {
            x: 68; y: 46; width: 238
            text: muzikModel.sanatci
            color: kart.ikincil
            font.pixelSize: 11
            elide: Text.ElideRight
        }
        Ilerleme { x: 68; y: 58; width: 228; kalinlik: 3 }
        Text {
            x: 68; y: 68
            text: kart.sure(muzikModel.konumMs)
            color: kart.ikincil
            font.pixelSize: 10
            font.family: "Geist Mono"
        }
        Text {
            x: 252; y: 68; width: 44
            horizontalAlignment: Text.AlignRight
            text: kart.sure(muzikModel.sureMs)
            color: kart.ikincil
            font.pixelSize: 10
            font.family: "Geist Mono"
        }
        Text {
            visible: muzikModel.demo
            x: 112; y: 68; width: 136
            horizontalAlignment: Text.AlignHCenter
            text: "demo · oynatıcı yok"
            color: kart.ucuncul
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        DaireDugme {
            x: 316; y: 36; boy: 32; tur: "oynat"; caliyor: muzikModel.caliyor
            onTiklandi: muzikModel.oynatDuraklat()
        }
    }

    // --- 1: kompakt --------------------------------------------------------
    Item {
        anchors.fill: parent
        visible: kart.secili === 1
        Kapak { x: 12; y: 24; boy: 36; kose: 9 }
        Text {
            x: 56; y: 21; width: 196
            text: muzikModel.baslik
            color: kart.ana
            font.pixelSize: 13
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }
        Text {
            x: 56; y: 38; width: 196
            text: muzikModel.sanatci
            color: kart.ikincil
            font.pixelSize: 10
            elide: Text.ElideRight
        }
        Ilerleme { x: 56; y: 48; width: 184; kalinlik: 2 }
        DaireDugme {
            x: 260; y: 26; boy: 28; tur: "oynat"; caliyor: muzikModel.caliyor
            onTiklandi: muzikModel.oynatDuraklat()
        }
    }

    // --- 2: mini -----------------------------------------------------------
    Item {
        anchors.fill: parent
        visible: kart.secili === 2
        Item {
            x: 14; y: 22; width: 92; height: 92
            Canvas {
                anchors.fill: parent
                property real oran: muzikModel.sureMs > 0
                    ? Math.max(0, Math.min(1, muzikModel.konumMs / muzikModel.sureMs)) : 0
                onOranChanged: requestPaint()
                onPaint: {
                    var c = getContext("2d")
                    c.reset()
                    var m = width / 2
                    var r = m - 2
                    c.lineWidth = 3
                    c.lineCap = "round"
                    c.strokeStyle = kart.ray
                    c.beginPath(); c.arc(m, m, r, 0, Math.PI * 2); c.stroke()
                    if (oran > 0) {
                        c.strokeStyle = kart.mavi
                        c.beginPath()
                        c.arc(m, m, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * oran)
                        c.stroke()
                    }
                }
            }
        }
        DaireDugme {
            x: 36; y: 44; boy: 48; tur: "oynat"; caliyor: muzikModel.caliyor
            onTiklandi: muzikModel.oynatDuraklat()
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            y: 101
            text: kart.kalanSure()
            color: kart.ikincil
            font.pixelSize: 10
            font.family: "Geist Mono"
        }
    }

    // --- 3: bar ------------------------------------------------------------
    Item {
        anchors.fill: parent
        visible: kart.secili === 3
        Kapak { x: 10; y: 18; boy: 32; kose: 8 }
        Text {
            x: 50; y: 16; width: 240
            text: muzikModel.baslik + (muzikModel.sanatci ? " — " + muzikModel.sanatci : "")
            color: kart.ana
            font.pixelSize: 12
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }
        Ilerleme { x: 50; y: 34; width: 180; kalinlik: 2 }
        Text {
            x: 234; y: 32; width: 66
            elide: Text.ElideRight
            text: kart.sure(muzikModel.konumMs) + " / " + kart.sure(muzikModel.sureMs)
            color: kart.ikincil
            font.pixelSize: 9
            font.family: "Geist Mono"
        }
        DaireDugme {
            x: 310; y: 23; boy: 26; tur: "oynat"; caliyor: muzikModel.caliyor
            onTiklandi: muzikModel.oynatDuraklat()
        }
        DaireDugme {
            x: 342; y: 25; boy: 22; tur: "ileri"
            onTiklandi: muzikModel.ileri()
        }
    }

    // --- 4: ses cikisi -----------------------------------------------------
    Item {
        anchors.fill: parent
        visible: kart.secili === 4
        Text {
            x: 14; y: 22
            text: "Hoparlör"
            color: kart.ana
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }
        Text {
            x: 14; y: 40; width: 200
            text: sesModel.cikisVar ? sesModel.cikisAd : "çıkış aygıtı yok"
            color: kart.ikincil
            font.pixelSize: 11
            elide: Text.ElideRight
        }
        Text {
            x: 200; y: 20; width: 106
            horizontalAlignment: Text.AlignRight
            text: sesModel.cikisYuzde + "%"
            color: kart.ana
            font.pixelSize: 20
            font.weight: Font.Bold
            font.family: "Geist Mono"
        }
        Item {
            id: sesCubuk
            x: 14; y: 70; width: 258; height: 16
            property real onizleme: -1
            readonly property real oran: Math.max(0, Math.min(1, sesModel.cikisYuzde / 100.0))
            readonly property real goster: onizleme >= 0 ? onizleme : oran
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width; height: 8; radius: 4; color: kart.ray
                Rectangle {
                    width: parent.width * sesCubuk.goster
                    height: parent.height; radius: parent.radius; color: kart.mavi
                }
            }
            MouseArea {
                anchors.fill: parent
                enabled: sesModel.cikisVar
                cursorShape: Qt.PointingHandCursor
                preventStealing: true
                onPressed: function(m) { sesCubuk.onizleme = Math.max(0, Math.min(1, m.x / sesCubuk.width)) }
                onPositionChanged: function(m) {
                    if (pressed)
                        sesCubuk.onizleme = Math.max(0, Math.min(1, m.x / sesCubuk.width))
                }
                onReleased: function(m) {
                    if (sesCubuk.onizleme >= 0)
                        sesModel.cikisAyarla(Math.round(sesCubuk.onizleme * 100))
                    sesCubuk.onizleme = -1
                }
                onCanceled: sesCubuk.onizleme = -1
            }
        }
        DaireDugme {
            x: 280; y: 62; boy: 32; tur: "hoparlor"; susturulmus: sesModel.cikisMute
            onTiklandi: sesModel.cikisMuteDegistir()
        }
    }

    // --- 5: mikrofon -------------------------------------------------------
    Item {
        anchors.fill: parent
        visible: kart.secili === 5
        Text {
            x: 14; y: 15
            text: "Mikrofon"
            color: kart.ana
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }
        Text {
            x: 14; y: 30; width: 292
            text: sesModel.kaynakVar ? sesModel.kaynakAd : "kaynak yok"
            color: kart.ikincil
            font.pixelSize: 11
            elide: Text.ElideRight
        }
        DaireDugme {
            x: 104; y: 44; boy: 48; tur: "mikrofon"; susturulmus: sesModel.kaynakMute
            onTiklandi: sesModel.kaynakMuteDegistir()
        }
        DaireDugme {
            x: 168; y: 44; boy: 48; tur: "hoparlor"; susturulmus: sesModel.cikisMute
            onTiklandi: sesModel.cikisMuteDegistir()
        }
        Text {
            visible: !sesModel.mikrofonVar
            anchors.horizontalCenter: parent.horizontalCenter
            y: 96
            text: "mikrofon yok"
            color: kart.uyari
            font.pixelSize: 10
            font.weight: Font.DemiBold
        }
    }
}
