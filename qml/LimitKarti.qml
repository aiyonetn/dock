import QtQuick

Item {
    id: kart
    width: 300
    height: 150

    property int simdi: Math.floor(Date.now() / 1000)
    readonly property color soluk: "#9aa0ad"
    readonly property color cizgi: "#26ffffff"

    function renk(p) {
        if (p < 50) return "#8BE34D"
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
        if (gun > 0) return gun + "g " + sa + "s sonra"
        if (sa > 0) return sa + "s " + dk + "dk sonra"
        return Math.max(1, dk) + "dk sonra"
    }

    Timer {
        interval: 1000
        repeat: true
        running: kart.visible
        triggeredOnStart: true
        onTriggered: kart.simdi = Math.floor(Date.now() / 1000)
    }

    Rectangle {
        anchors.fill: parent
        radius: 20
        color: "#d20e0e12"
        border.width: 1
        border.color: "#22ffffff"
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
            GradientStop { position: 0.5; color: "#30ffffff" }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    component Cubuk: Item {
        id: cubuk
        property string etiket: ""
        property real yuzde: -1
        property real reset: 0
        width: parent.width
        height: 16

        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: 44
            text: cubuk.etiket
            color: "#c9ceda"
            font.pixelSize: 10
        }
        Rectangle {
            id: ray
            anchors.verticalCenter: parent.verticalCenter
            x: 48
            width: 116
            height: 6
            radius: 3
            color: "#26ffffff"
            Rectangle {
                width: cubuk.yuzde > 0 ? Math.max(2, ray.width * cubuk.yuzde / 100) : 0
                height: parent.height
                radius: parent.radius
                color: kart.renk(cubuk.yuzde)
            }
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            x: 170
            width: 32
            horizontalAlignment: Text.AlignRight
            text: cubuk.yuzde < 0 ? "—" : Math.round(cubuk.yuzde) + "%"
            color: "#f2f4f8"
            font.pixelSize: 10
            font.bold: true
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            x: 206
            width: 70
            horizontalAlignment: Text.AlignRight
            text: cubuk.yuzde < 0 ? "—" : kart.kalan(cubuk.reset)
            color: kart.soluk
            font.pixelSize: 9
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 4

        Text {
            text: "AI Limit"
            color: "#eef1f7"
            font.pixelSize: 12
            font.bold: true
        }

        Repeater {
            model: limitModel
            delegate: Column {
                width: parent.width
                spacing: 1
                property bool yok: model.kaynak === "yok"

                Item {
                    width: parent.width
                    height: 14
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: model.ad + (model.plan ? " · " + model.plan : "")
                        color: "#e6eaf2"
                        font.pixelSize: 10
                        font.bold: true
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.right: parent.right
                        text: parent.parent.yok ? "yapılandırılmadı"
                            : model.kaynak === "elle" ? "elle" : "canlı"
                        color: parent.parent.yok ? "#F5C542" : kart.soluk
                        font.pixelSize: 9
                    }
                }

                Text {
                    visible: parent.yok
                    width: parent.width
                    height: 22
                    verticalAlignment: Text.AlignVCenter
                    text: "yapılandırılmadı"
                    color: kart.soluk
                    font.pixelSize: 10
                }

                Cubuk {
                    visible: !parent.yok
                    etiket: "Session"
                    yuzde: model.sessionYuzde
                    reset: model.sessionReset
                }
                Cubuk {
                    visible: !parent.yok
                    etiket: "Weekly"
                    yuzde: model.weeklyYuzde
                    reset: model.weeklyReset
                }
            }
        }
    }

    MouseArea { anchors.fill: parent }
}
