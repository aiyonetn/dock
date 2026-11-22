import QtQuick

// Lumabar "System" seti. Olcek: referans 154 px -> 320 px (x2.077).
// CPU/RAM 320x320 kare; Ag / Top CPU / Top RAM 977x320 genis.
// Kart secimi dock panelindeki 5 kucuk ikondan yapilir; bu dosya tek kare cizer.
Item {
    id: kart
    width: sekme >= 2 ? 977 : 320
    height: 320

    property int sekme: 0
    property var veri: sistemModel.veri

    readonly property color ana: "#F7F7F8"
    readonly property color ikincil: "#9A9AA0"
    readonly property color ucuncul: "#74747A"
    readonly property color ray: "#424242"
    readonly property color mavi: "#4CC2FF"
    readonly property color mor: "#A78BFA"

    function konumBildir() {
        kopru.sistem_konumu(Math.round(x), Math.round(y), Math.round(width), Math.round(height))
    }
    onXChanged: konumBildir()
    onYChanged: konumBildir()
    onWidthChanged: konumBildir()
    onHeightChanged: konumBildir()
    Component.onCompleted: konumBildir()

    function oran(deger) {
        return (deger === null || deger === undefined) ? "—" : Math.round(deger)
    }
    function hiz(bayt) {
        if (bayt === null || bayt === undefined) return "—"
        if (bayt < 1024) return Math.round(bayt) + " B/s"
        if (bayt < 1048576) return (bayt / 1024).toFixed(1) + " KB/s"
        return (bayt / 1048576).toFixed(1) + " MB/s"
    }
    function ramMiktar(mb) {
        if (mb === null || mb === undefined) return "—"
        if (mb >= 1024) return (mb / 1024).toFixed(1) + " GB"
        return Math.round(mb) + " MB"
    }
    function topCpuKayit(i) {
        var l = kart.veri ? kart.veri.topCpu : null
        return (l && l.length > i) ? l[i] : null
    }
    function topRamKayit(i) {
        var l = kart.veri ? kart.veri.topRam : null
        return (l && l.length > i) ? l[i] : null
    }
    readonly property bool topCpuVar: kart.veri && kart.veri.topCpu
        && kart.veri.topCpu.length > 0
    readonly property bool topRamVar: kart.veri && kart.veri.topRam
        && kart.veri.topRam.length > 0

    component Halka: Item {
        id: halka
        property real yuzde: 0
        property string ikonKaynak: ""
        property color yayRengi: kart.mavi
        property int ikonEn: 44
        property int ikonBoy: 44
        Canvas {
            anchors.fill: parent
            property real yuzde: halka.yuzde
            onYuzdeChanged: requestPaint()
            onPaint: {
                var c = getContext("2d"); c.reset()
                var m = width / 2
                var iz = 19
                var yay = 19
                var r = m - iz / 2 - 1
                c.lineCap = "round"
                c.lineWidth = iz
                c.strokeStyle = kart.ray
                c.beginPath(); c.arc(m, m, r, 0, Math.PI * 2); c.stroke()
                var oran = Math.max(0, Math.min(100, halka.yuzde)) / 100
                if (oran > 0) {
                    c.lineWidth = yay
                    c.strokeStyle = halka.yayRengi
                    c.beginPath()
                    c.arc(m, m, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * oran)
                    c.stroke()
                }
            }
        }
        // Ikon halkanin ic boslugunda, merkezin 41 px ustunde.
        Image {
            anchors.horizontalCenter: parent.horizontalCenter
            y: parent.height / 2 - 41 - height / 2
            width: halka.ikonEn; height: halka.ikonBoy
            source: halka.ikonKaynak
            fillMode: Image.PreserveAspectFit
            smooth: true
        }
    }

    // Opak kare; cam/blur, golge ve kenar isigi yok.
    Rectangle {
        anchors.fill: parent
        radius: 69
        color: "#1C1C1C"
        border.width: 3
        border.color: "#3A3A3A"
    }

    MouseArea { anchors.fill: parent }

    Text {
        visible: !sistemModel.veriVar
        anchors.centerIn: parent
        text: "veri yok"
        color: kart.ikincil
        font.pixelSize: 27
    }

    // --- CPU (320x320) -------------------------------------------------------
    Item {
        visible: sistemModel.veriVar && kart.sekme === 0
        anchors.fill: parent
        Halka {
            x: 39; y: 39; width: 242; height: 242
            yuzde: (kart.veri && kart.veri.cpu !== undefined) ? Math.round(kart.veri.cpu) : 0
            ikonKaynak: "../assets/cip.svg"
            ikonEn: 56; ikonBoy: 56
            yayRengi: "#4EC7EE"
        }
        // Sayi halkanin ic boslugunda, merkezin 41 px altinda.
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            y: 158
            text: kart.oran(kart.veri ? kart.veri.cpu : null)
            color: "#FFFFFF"
            font.pixelSize: 66
            font.bold: true
            font.family: "Geist Mono"
        }
    }

    // --- RAM (320x320) -------------------------------------------------------
    Item {
        visible: sistemModel.veriVar && kart.sekme === 1
        anchors.fill: parent
        Halka {
            x: 39; y: 39; width: 242; height: 242
            yuzde: (kart.veri && kart.veri.ramYuzde !== undefined) ? Math.round(kart.veri.ramYuzde) : 0
            ikonKaynak: "../assets/bellek.svg"
            ikonEn: 80; ikonBoy: 53
            yayRengi: "#3281FF"
        }
        // Sayi halkanin ic boslugunda, merkezin 41 px altinda.
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            y: 158
            text: kart.oran(kart.veri ? kart.veri.ramYuzde : null)
            color: "#FFFFFF"
            font.pixelSize: 66
            font.bold: true
            font.family: "Geist Mono"
        }
    }

    // --- Ag (977x320) --------------------------------------------------------
    Item {
        visible: sistemModel.veriVar && kart.sekme === 2
        anchors.fill: parent
        Text {
            x: 50; y: 26
            text: "indirme"
            color: kart.ikincil
            font.pixelSize: 22
        }
        Text {
            x: 50; y: 52; width: 420
            text: kart.hiz(kart.veri ? kart.veri.indirme : null)
            color: kart.ana
            font.pixelSize: 48
            font.family: "Geist Mono"
            elide: Text.ElideRight
        }
        Text {
            x: 500; y: 26
            text: "yükleme"
            color: kart.ikincil
            font.pixelSize: 22
        }
        Text {
            x: 500; y: 52; width: 427
            text: kart.hiz(kart.veri ? kart.veri.yukleme : null)
            color: kart.ana
            font.pixelSize: 48
            font.family: "Geist Mono"
            elide: Text.ElideRight
        }
        Canvas {
            id: grafik
            x: 50; y: 166
            width: 877; height: 144
            property var gecmis: kart.veri ? kart.veri.gecmis : []
            onGecmisChanged: if (visible) requestPaint()
            onPaint: {
                var c = getContext("2d"); c.reset()
                var w = width, h = height
                c.strokeStyle = "#1E1E22"; c.lineWidth = 1
                for (var g = 1; g <= 3; g++) {
                    var gy = h * g / 4
                    c.beginPath(); c.moveTo(0, gy); c.lineTo(w, gy); c.stroke()
                }
                var n = gecmis ? gecmis.length : 0
                if (n === 0) return
                var enBuyuk = 1024
                for (var i = 0; i < n; i++)
                    enBuyuk = Math.max(enBuyuk, gecmis[i][0], gecmis[i][1])
                enBuyuk *= 1.15
                function nx(i) { return n <= 1 ? w : i / (n - 1) * w }
                function ny(v) { return h - Math.min(1, v / enBuyuk) * (h - 4) }
                c.lineWidth = 4; c.lineJoin = "round"; c.lineCap = "round"
                c.strokeStyle = kart.mor
                c.beginPath()
                for (i = 0; i < n; i++) {
                    if (i === 0) c.moveTo(nx(i), ny(gecmis[i][1]))
                    else c.lineTo(nx(i), ny(gecmis[i][1]))
                }
                c.stroke()
                c.strokeStyle = kart.mavi
                c.beginPath()
                for (i = 0; i < n; i++) {
                    if (i === 0) c.moveTo(nx(i), ny(gecmis[i][0]))
                    else c.lineTo(nx(i), ny(gecmis[i][0]))
                }
                c.stroke()
            }
        }
    }

    // --- Top CPU (977x320) ---------------------------------------------------
    Item {
        visible: sistemModel.veriVar && kart.sekme === 3
        anchors.fill: parent
        Text {
            visible: !kart.topCpuVar
            anchors.centerIn: parent
            text: "veri yok"
            color: kart.ikincil
            font.pixelSize: 27
        }
        Column {
            visible: kart.topCpuVar
            x: 0; y: 13
            Repeater {
                model: 3
                delegate: Item {
                    width: kart.width; height: 98
                    property var kayit: kart.topCpuKayit(index)
                    Rectangle {
                        x: 50; y: 28; width: 42; height: 42; radius: 12
                        color: index === 2 ? "#30D158" : "#0A84FF"
                    }
                    Text {
                        x: 112; y: 33; width: 640
                        text: kayit ? kayit.ad : ""
                        color: kart.ana
                        font.pixelSize: 27
                        elide: Text.ElideRight
                    }
                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: 50
                        y: 33
                        text: kayit ? kayit.yuzde.toFixed(1) + "%" : ""
                        color: kart.ikincil
                        font.pixelSize: 27
                        font.family: "Geist Mono"
                    }
                }
            }
        }
    }

    // --- Top RAM (977x320) ---------------------------------------------------
    Item {
        visible: sistemModel.veriVar && kart.sekme === 4
        anchors.fill: parent
        Text {
            visible: !kart.topRamVar
            anchors.centerIn: parent
            text: "veri yok"
            color: kart.ikincil
            font.pixelSize: 27
        }
        Column {
            visible: kart.topRamVar
            x: 0; y: 13
            Repeater {
                model: 3
                delegate: Item {
                    width: kart.width; height: 98
                    property var kayit: kart.topRamKayit(index)
                    Rectangle {
                        x: 50; y: 28; width: 42; height: 42; radius: 12
                        color: index === 2 ? "#30D158" : "#0A84FF"
                    }
                    Text {
                        x: 112; y: 33; width: 620
                        text: kayit ? kayit.ad : ""
                        color: kart.ana
                        font.pixelSize: 27
                        elide: Text.ElideRight
                    }
                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: 50
                        y: 33
                        text: kayit ? kart.ramMiktar(kayit.mb) : ""
                        color: kart.ikincil
                        font.pixelSize: 27
                        font.family: "Geist Mono"
                    }
                }
            }
        }
    }
}
