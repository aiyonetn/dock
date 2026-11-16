import QtQuick

Item {
    id: kart
    width: 320
    height: claudeVar ? 306 : 236

    property var codex: limitModel.codex
    property var claude: limitModel.claude
    property bool codexVar: !!codex && codex.kaynak !== "yok" && codex.kaynak !== "hata"
    property bool claudeVar: !!claude && claude.kaynak !== "yok" && claude.kaynak !== "suresi_doldu"
    property int simdi: Math.floor(Date.now() / 1000)
    property double sonGuncelleme: Math.floor(Date.now() / 1000)
    property string kartKaynak: ""

    readonly property color ana: "#F7F7F8"
    readonly property color ikincil: "#A1A1A6"
    readonly property color ucuncul: "#74747A"
    readonly property color ayirici: "#262628"

    component Halka: Item {
        id: halka
        width: 92
        height: 114
        property real yuzde: -1
        property string etiket: ""
        property real reset: 0

        function renk(p) {
            if (p < 50) return "#F7F7F8"
            if (p < 80) return "#F5C542"
            return "#F05B5B"
        }
        function kalanParcalar(epoch) {
            if (!epoch || epoch <= 0) return [{metin: "—", mono: false}]
            var d = Math.floor(epoch - kart.simdi)
            if (d <= 0) return [{metin: "şimdi", mono: false}]
            var gun = Math.floor(d / 86400)
            var sa = Math.floor((d % 86400) / 3600)
            var dk = Math.floor((d % 3600) / 60)
            var p = []
            if (gun > 0) {
                p.push({metin: gun, mono: true}, {metin: " gün", mono: false})
                if (sa > 0) p.push({metin: " " + sa, mono: true}, {metin: " sa", mono: false})
            } else if (sa > 0) {
                p.push({metin: sa, mono: true}, {metin: " sa", mono: false})
                if (dk > 0) p.push({metin: " " + dk, mono: true}, {metin: " dk", mono: false})
            } else {
                p.push({metin: Math.max(1, dk), mono: true}, {metin: " dk", mono: false})
            }
            return p
        }

        Canvas {
            id: halkaTuval
            width: 84; height: 84
            property real yuzde: halka.yuzde
            onYuzdeChanged: requestPaint()
            Connections {
                target: limitModel
                function onVeriDegisti() { halkaTuval.requestPaint() }
            }
            onPaint: {
                var c = getContext("2d"); c.reset()
                var m = 42, r = 39
                c.lineWidth = 6
                c.strokeStyle = "#2C2C2E"
                c.beginPath(); c.arc(m, m, r, 0, Math.PI * 2); c.stroke()
                if (halka.yuzde >= 0) {
                    c.strokeStyle = halka.renk(halka.yuzde)
                    c.beginPath()
                    c.arc(m, m, r, -Math.PI / 2,
                        -Math.PI / 2 + Math.PI * 2 * Math.min(1, halka.yuzde / 100))
                    c.stroke()
                }
            }
        }
        GolgeText {
            anchors.centerIn: halkaTuval
            text: halka.yuzde < 0 ? "—" : Math.round(halka.yuzde) + "%"
            color: halka.yuzde < 0 ? kart.ikincil : halka.renk(halka.yuzde)
            font.pixelSize: 15
            font.bold: true
            font.family: "Geist Mono"
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            y: 86
            text: halka.etiket
            color: kart.ikincil
            font.pixelSize: 11
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            y: 98
            height: 12
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 0
                Repeater {
                    model: halka.kalanParcalar(halka.reset)
                    Text {
                        text: modelData.metin
                        color: kart.ucuncul
                        font.pixelSize: 10
                        font.family: modelData.mono ? "Geist Mono" : "Geist"
                    }
                }
            }
        }
    }

    function codexDeger(tur) {
        var d = tur === "session" ? kart.codex.session : kart.codex.weekly
        return (!d || d.percent === null || d.percent === undefined) ? -1 : d.percent
    }
    function claudeDeger(tur) {
        if (!kart.claude) return -1
        var d = tur === "session" ? kart.claude.session : kart.claude.weekly
        return (!d || d.percent === null || d.percent === undefined) ? -1 : d.percent
    }
    function codexReset(tur) {
        var d = tur === "session" ? kart.codex.session : kart.codex.weekly
        return (!d || !d.reset) ? 0 : d.reset
    }

    Image {
        source: "image://arkaplan/kartGolge"
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
        radius: yaricaplar.kart
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

    Item {
        x: 16; y: 16; width: parent.width - 32; height: 18
        GolgeText {
            anchors.verticalCenter: parent.verticalCenter
            text: "AI Kullanımı"
            color: kart.ana
            font.pixelSize: 13
            font.weight: Font.Medium
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            text: "ChatGPT" + (kart.codex && kart.codex.plan ? " · " + kart.codex.plan : "")
            color: "#C9C9CE"
            font.pixelSize: 12
        }
    }

    Rectangle { x: 16; y: 42; width: parent.width - 32; height: 1; color: kart.ayirici }

    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 50
        spacing: 24
        Halka { etiket: "Oturum"; yuzde: kart.codexDeger("session"); reset: kart.codexReset("session") }
        Halka { etiket: "Hafta"; yuzde: kart.codexDeger("weekly"); reset: kart.codexReset("weekly") }
    }

    Text {
        visible: !kart.claudeVar
        anchors.horizontalCenter: parent.horizontalCenter
        y: 152
        text: "Claude · " + (kart.claude && kart.claude.kaynak === "suresi_doldu"
            ? "oturum süresi doldu" : "yapılandırılmadı")
        color: kart.ikincil
        font.pixelSize: 11
    }

    Row {
        visible: kart.claudeVar
        anchors.horizontalCenter: parent.horizontalCenter
        y: 170
        spacing: 24
        Halka {
            etiket: "Claude Oturum"
            yuzde: kart.claudeDeger("session")
            reset: 0
        }
        Halka {
            etiket: "Claude Hafta"
            yuzde: kart.claudeDeger("weekly")
            reset: 0
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: kart.claudeVar ? 270 : 200
        text: !limitModel.veriVar ? "veri bekleniyor"
            : (limitModel.bayat ? "veri gelmedi" : kart.guncellemeMetni())
        color: kart.ucuncul
        font.pixelSize: 11
    }

    function guncellemeMetni() {
        var yas = Math.max(0, Math.round(kart.simdi - kart.sonGuncelleme))
        if (yas <= 1) return "güncellendi az önce"
        if (yas < 60) return "güncellendi " + yas + " sn önce"
        return "güncellendi " + Math.floor(yas / 60) + " dk önce"
    }

    Connections {
        target: limitModel
        function onVeriDegisti() { kart.sonGuncelleme = Date.now() / 1000 }
    }
    Timer {
        interval: 5000; repeat: true; running: kart.visible
        triggeredOnStart: true
        onTriggered: kart.simdi = Math.floor(Date.now() / 1000)
    }
}
