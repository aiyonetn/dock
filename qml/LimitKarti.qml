import QtQuick

Item {
    id: kart
    width: 320
    height: 228

    property var codex: limitModel.codex
    property var claude: limitModel.claude
    property bool codexVar: !!codex && codex.kaynak !== "yok"
    property bool claudeVar: !!claude && claude.kaynak !== "yok"
    property string kartKaynak: ""
    property int simdi: Math.floor(Date.now() / 1000)
    property double sonGuncelleme: Math.floor(Date.now() / 1000)

    readonly property color ana: "#F7F7F8"
    readonly property color ikincil: "#A1A1A6"
    readonly property color ucuncul: "#74747A"
    readonly property color cizgi: "#2A2A2C"
    readonly property color ayirici: "#262628"
    readonly property color ray: "#2C2C2E"

    function renk(p) {
        if (p < 50) return "#30D158"
        if (p < 80) return "#F5C542"
        if (p < 90) return "#F59E42"
        return "#F05B5B"
    }

    function kalan(epoch) {
        if (!epoch || epoch <= 0) return "—"
        var d = Math.floor(epoch - kart.simdi)
        if (d <= 0) return "şimdi"
        var gun = Math.floor(d / 86400)
        var sa = Math.floor((d % 86400) / 3600)
        var dk = Math.floor((d % 3600) / 60)
        if (gun > 0) return gun + " gün" + (sa > 0 ? " " + sa + " sa" : "")
        if (sa > 0) return sa + " sa" + (dk > 0 ? " " + dk + " dk" : "")
        return Math.max(1, dk) + " dk"
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
        interval: 5000
        repeat: true
        running: kart.visible
        triggeredOnStart: true
        onTriggered: kart.simdi = Math.floor(Date.now() / 1000)
    }

    function konumBildir() {
        kopru.kart_konumu(Math.round(x), Math.round(y), Math.round(width), Math.round(height))
    }
    onXChanged: konumBildir()
    onYChanged: konumBildir()
    Component.onCompleted: konumBildir()

    // Disari 10 px yumusak golge (Python'da bir kez uretilir).
    Image {
        source: "image://arkaplan/kartGolge"
        x: -10
        y: -8
        width: parent.width + 20
        height: parent.height + 20
        fillMode: Image.Stretch
        smooth: true
    }

    // Kompozit cam: kendi arkasindaki masaustu + blur + %55 ton.
    Image {
        anchors.fill: parent
        source: kart.kartKaynak
        fillMode: Image.Stretch
        cache: false
        smooth: true
    }

    Rectangle {
        anchors.fill: parent
        radius: 14
        color: "#00000000"
        border.width: 1
        border.color: "#14ffffff"
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
            GradientStop { position: 0.5; color: "#24ffffff" }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    Column {
        x: 18
        y: 18
        width: parent.width - 36
        spacing: 0

        Item {
            width: parent.width
            height: 18
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "AI Kullanımı"
                color: kart.ana
                font.pixelSize: 13
                font.weight: Font.DemiBold
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                text: "ChatGPT" + (kart.codex && kart.codex.plan ? " · " + kart.codex.plan : "")
                color: "#C9C9CE"
                font.pixelSize: 12
                font.weight: Font.Medium
            }
        }

        Item { width: parent.width; height: 8 }
        Rectangle { width: parent.width; height: 1; color: kart.ayirici }
        Item { width: parent.width; height: 8 }

        Item {
            visible: kart.codexVar
            width: parent.width
            height: 45
            Item {
                width: parent.width
                height: 16
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Session"
                    color: kart.ikincil
                    font.pixelSize: 11
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    text: (kart.codex.session.percent === null ? "—"
                        : Math.round(kart.codex.session.percent) + "%")
                    color: kart.codex.session.percent === null
                        ? kart.ikincil : kart.renk(kart.codex.session.percent)
                    font.pixelSize: 15
                    font.bold: true
                }
            }
            Rectangle {
                y: 22
                width: parent.width
                height: 8
                radius: 4
                color: kart.ray
                Rectangle {
                    width: kart.codex.session.percent > 0
                        ? Math.max(1, parent.width * kart.codex.session.percent / 100) : 0
                    height: parent.height
                    radius: 4
                    color: kart.codex.session.percent === null
                        ? kart.ray : kart.renk(kart.codex.session.percent)
                }
            }
            Text {
                y: 34
                width: parent.width
                horizontalAlignment: Text.AlignRight
                text: kart.codex.session.percent === null ? "—"
                    : kart.kalan(kart.codex.session.reset)
                color: kart.ucuncul
                font.pixelSize: 10
            }
        }

        Item { width: parent.width; height: 14; visible: kart.codexVar }

        Item {
            visible: kart.codexVar
            width: parent.width
            height: 45
            Item {
                width: parent.width
                height: 16
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Weekly"
                    color: kart.ikincil
                    font.pixelSize: 11
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    text: (kart.codex.weekly.percent === null ? "—"
                        : Math.round(kart.codex.weekly.percent) + "%")
                    color: kart.codex.weekly.percent === null
                        ? kart.ikincil : kart.renk(kart.codex.weekly.percent)
                    font.pixelSize: 15
                    font.bold: true
                }
            }
            Rectangle {
                y: 22
                width: parent.width
                height: 8
                radius: 4
                color: kart.ray
                Rectangle {
                    width: kart.codex.weekly.percent > 0
                        ? Math.max(1, parent.width * kart.codex.weekly.percent / 100) : 0
                    height: parent.height
                    radius: 4
                    color: kart.codex.weekly.percent === null
                        ? kart.ray : kart.renk(kart.codex.weekly.percent)
                }
            }
            Text {
                y: 34
                width: parent.width
                horizontalAlignment: Text.AlignRight
                text: kart.codex.weekly.percent === null ? "—"
                    : kart.kalan(kart.codex.weekly.reset)
                color: kart.ucuncul
                font.pixelSize: 10
            }
        }

        Text {
            visible: !kart.codexVar
            width: parent.width
            height: 41
            verticalAlignment: Text.AlignVCenter
            text: "yapılandırılmadı"
            color: kart.ikincil
            font.pixelSize: 11
        }

        Item { width: parent.width; height: 8 }
        Rectangle { width: parent.width; height: 1; color: kart.ayirici }
        Item { width: parent.width; height: 8 }

        Item {
            width: parent.width
            height: 18
            Text {
                id: claudeAd
                y: 0
                text: "Claude"
                color: "#C9C9CE"
                font.pixelSize: 12
            }
            Text {
                anchors.right: parent.right
                anchors.baseline: claudeAd.baseline
                text: kart.claudeVar
                    ? "Session " + Math.round(kart.claude.session.percent) + "% · Weekly "
                        + Math.round(kart.claude.weekly.percent) + "%"
                    : "yapılandırılmadı"
                color: kart.ucuncul
                font.pixelSize: 11
            }
        }

        Item { width: parent.width; height: 6 }

        Item {
            width: parent.width
            height: 12
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: kart.guncellemeMetni()
                color: kart.ucuncul
                font.pixelSize: 10
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                text: "v0.1"
                color: kart.ucuncul
                font.pixelSize: 10
            }
        }
    }

    MouseArea { anchors.fill: parent }
}
