// ─────────────────────────────────────────────────────────────────────────────
//  NYXUS SDDM Greeter · COSMIC INK SWIRL · DARK GLASS LOGIN
//  Visual System: locked rev 2026-05-06v
//  © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
// ─────────────────────────────────────────────────────────────────────────────
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SddmComponents 2.0

Item {
    id: root
    width:  Screen.width
    height: Screen.height

    // ── Locked NYXUS palette (DARK GLASS WAYBAR rules) ──────────────────────
    readonly property color clrInk:      "#080c14"   // shell base
    readonly property color clrPebble:   "#0f1420"   // raised pebble
    readonly property color clrText:     "#e8edf5"   // primary
    readonly property color clrTextDim:  "#a8b0bd"   // secondary
    readonly property color clrTextFaint:"#6b7383"   // tertiary
    readonly property color clrStarlight:"#e6f0ff"   // hover halo
    readonly property color clrGold:     "#d4a73a"   // jewelry-only
    readonly property color clrShadow:   "#000000"

    readonly property string fontHand: "Architects Daughter, Caveat, sans-serif"
    readonly property string fontUI:   "Inter, sans-serif"
    readonly property string fontMono: "JetBrains Mono, Fira Code, monospace"

    // ── State ────────────────────────────────────────────────────────────────
    property bool   authBusy:   false
    property bool   authFailed: false
    property string authMsg:    ""

    Connections {
        target: sddm
        function onLoginSucceeded() {
            authBusy   = false
            authFailed = false
            authMsg    = "WELCOME"
        }
        function onLoginFailed() {
            authBusy   = false
            authFailed = true
            authMsg    = "AUTHENTICATION FAILED — RETRY"
            shakeAnim.restart()
        }
    }

    // ── Wallpaper: cosmic ink swirl, full bleed ──────────────────────────────
    Image {
        id: wallpaper
        anchors.fill: parent
        source:       "background.png"
        fillMode:     Image.PreserveAspectCrop
        smooth:       true
        cache:        true
        asynchronous: false
    }

    // Subtle vignette so the login plate reads against any wallpaper region
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0, 0, 0, 0.25) }
            GradientStop { position: 0.5; color: Qt.rgba(0, 0, 0, 0.05) }
            GradientStop { position: 1.0; color: Qt.rgba(0, 0, 0, 0.45) }
        }
    }

    // ── NYXUS wordmark · top center ──────────────────────────────────────────
    Column {
        anchors.top: parent.top
        anchors.topMargin: 64
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 6

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "NYXUS"
            color: clrGold
            font.family: fontHand
            font.pixelSize: 72
            font.weight: Font.Bold
            // engraved + warm gold glow
            style: Text.Raised
            styleColor: Qt.rgba(0, 0, 0, 0.85)
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "SIERENGOWSKI · 2026"
            color: clrTextDim
            font.family: fontMono
            font.pixelSize: 13
            font.letterSpacing: 6
        }
    }

    // ── Date / time · top-left dark glass pebble ─────────────────────────────
    Rectangle {
        id: clockPlate
        anchors.left: parent.left
        anchors.top:  parent.top
        anchors.leftMargin: 40
        anchors.topMargin:  40
        width:  220
        height: 76
        radius: 14
        color:  Qt.rgba(8/255, 12/255, 20/255, 0.58)
        border.color: Qt.rgba(255, 255, 255, 0.08)
        border.width: 1

        Column {
            anchors.centerIn: parent
            spacing: 2

            Text {
                id: clockTime
                anchors.horizontalCenter: parent.horizontalCenter
                color: clrText
                font.family: fontMono
                font.pixelSize: 28
                font.weight: Font.Bold
                text: Qt.formatTime(new Date(), "HH:mm")
            }
            Text {
                id: clockDate
                anchors.horizontalCenter: parent.horizontalCenter
                color: clrTextDim
                font.family: fontUI
                font.pixelSize: 11
                font.letterSpacing: 3
                text: Qt.formatDate(new Date(), "ddd · MMM d yyyy").toUpperCase()
            }
        }

        Timer {
            interval: 1000; running: true; repeat: true
            onTriggered: {
                clockTime.text = Qt.formatTime(new Date(), "HH:mm")
                clockDate.text = Qt.formatDate(new Date(), "ddd · MMM d yyyy").toUpperCase()
            }
        }
    }

    // ── Hostname pebble · top-right ──────────────────────────────────────────
    Rectangle {
        anchors.right: parent.right
        anchors.top:   parent.top
        anchors.rightMargin: 40
        anchors.topMargin:   40
        width:  220
        height: 76
        radius: 14
        color:  Qt.rgba(8/255, 12/255, 20/255, 0.58)
        border.color: Qt.rgba(255, 255, 255, 0.08)
        border.width: 1

        Column {
            anchors.centerIn: parent
            spacing: 2
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                color: clrText
                font.family: fontMono; font.pixelSize: 16; font.weight: Font.Bold
                text: "NYXUS · ARCH"
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                color: clrTextDim
                font.family: fontMono; font.pixelSize: 11; font.letterSpacing: 3
                text: "HYPRLAND · WAYLAND"
            }
        }
    }

    // ── Login plate · centered dark glass ────────────────────────────────────
    Rectangle {
        id: loginPlate
        anchors.centerIn: parent
        width:  420
        height: 360
        radius: 18
        color:  Qt.rgba(8/255, 12/255, 20/255, 0.66)
        border.color: Qt.rgba(255, 255, 255, 0.10)
        border.width: 1

        // shake on auth fail
        SequentialAnimation {
            id: shakeAnim
            NumberAnimation { target: loginPlate; property: "x"; to: loginPlate.x - 10; duration: 50 }
            NumberAnimation { target: loginPlate; property: "x"; to: loginPlate.x + 10; duration: 50 }
            NumberAnimation { target: loginPlate; property: "x"; to: loginPlate.x - 6;  duration: 50 }
            NumberAnimation { target: loginPlate; property: "x"; to: loginPlate.x + 6;  duration: 50 }
            NumberAnimation { target: loginPlate; property: "x"; to: loginPlate.x;      duration: 50 }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 32
            spacing: 18

            // Title
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "SIGN IN"
                color: clrText
                font.family: fontUI
                font.pixelSize: 18
                font.weight: Font.Bold
                font.letterSpacing: 6
            }

            // ── Username row ────────────────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Text {
                    text: "USER"
                    color: clrTextFaint
                    font.family: fontMono
                    font.pixelSize: 10
                    font.letterSpacing: 3
                }

                ComboBox {
                    id: userBox
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    model: userModel
                    textRole: "name"
                    currentIndex: userModel.lastIndex
                    font.family: fontUI
                    font.pixelSize: 14

                    background: Rectangle {
                        color: Qt.rgba(15/255, 20/255, 32/255, 0.85)
                        radius: 10
                        border.color: userBox.activeFocus
                            ? Qt.rgba(230/255, 240/255, 255/255, 0.55)
                            : Qt.rgba(255, 255, 255, 0.10)
                        border.width: 1
                    }
                    contentItem: Text {
                        text: userBox.displayText
                        color: clrText
                        font: userBox.font
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: 14
                    }
                }
            }

            // ── Password row ────────────────────────────────────────────────
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Text {
                    text: "PASSWORD"
                    color: clrTextFaint
                    font.family: fontMono
                    font.pixelSize: 10
                    font.letterSpacing: 3
                }

                TextField {
                    id: passwordField
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    echoMode: TextInput.Password
                    passwordCharacter: "•"
                    color: clrText
                    selectionColor: Qt.rgba(212/255, 167/255, 58/255, 0.55)
                    font.family: fontUI
                    font.pixelSize: 14
                    leftPadding: 14
                    rightPadding: 14
                    placeholderText: "enter passphrase"
                    placeholderTextColor: clrTextFaint

                    background: Rectangle {
                        color: Qt.rgba(15/255, 20/255, 32/255, 0.85)
                        radius: 10
                        border.color: passwordField.activeFocus
                            ? Qt.rgba(230/255, 240/255, 255/255, 0.55)
                            : Qt.rgba(255, 255, 255, 0.10)
                        border.width: 1
                    }

                    Keys.onReturnPressed: doLogin()
                    Keys.onEnterPressed:  doLogin()
                    Component.onCompleted: forceActiveFocus()
                }
            }

            // ── Status line ─────────────────────────────────────────────────
            Text {
                Layout.alignment: Qt.AlignHCenter
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: authBusy ? "AUTHENTICATING…" : authMsg
                color: authFailed ? Qt.rgba(212/255, 167/255, 58/255, 1.0) : clrTextDim
                font.family: fontMono
                font.pixelSize: 11
                font.letterSpacing: 3
                wrapMode: Text.WordWrap
                elide: Text.ElideRight
                visible: authBusy || authMsg.length > 0
            }

            // ── Sign-in button ──────────────────────────────────────────────
            Button {
                id: signInBtn
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                text: authBusy ? "•••" : "SIGN IN"
                font.family: fontUI
                font.pixelSize: 13
                font.weight: Font.Bold
                font.letterSpacing: 4

                background: Rectangle {
                    radius: 10
                    color: signInBtn.down
                        ? Qt.rgba(230/255, 240/255, 255/255, 0.18)
                        : signInBtn.hovered
                            ? Qt.rgba(230/255, 240/255, 255/255, 0.10)
                            : Qt.rgba(15/255, 20/255, 32/255, 0.85)
                    border.color: Qt.rgba(230/255, 240/255, 255/255, 0.35)
                    border.width: 1
                }
                contentItem: Text {
                    text: signInBtn.text
                    color: clrText
                    font: signInBtn.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: doLogin()
            }

            // ── Session selector (compact, bottom row) ──────────────────────
            RowLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter
                spacing: 12

                Text {
                    text: "SESSION"
                    color: clrTextFaint
                    font.family: fontMono
                    font.pixelSize: 10
                    font.letterSpacing: 3
                }

                ComboBox {
                    id: sessionBox
                    Layout.preferredWidth: 200
                    Layout.preferredHeight: 28
                    model: sessionModel
                    textRole: "name"
                    currentIndex: sessionModel.lastIndex
                    font.family: fontUI
                    font.pixelSize: 11

                    background: Rectangle {
                        color: Qt.rgba(15/255, 20/255, 32/255, 0.85)
                        radius: 8
                        border.color: Qt.rgba(255, 255, 255, 0.10)
                        border.width: 1
                    }
                    contentItem: Text {
                        text: sessionBox.displayText
                        color: clrTextDim
                        font: sessionBox.font
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: 10
                    }
                }
            }
        }
    }

    // ── Power controls · bottom-right pebbles ────────────────────────────────
    Row {
        anchors.right:  parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin:  40
        anchors.bottomMargin: 40
        spacing: 10

        // Reboot
        Rectangle {
            width: 110; height: 38; radius: 12
            color: Qt.rgba(15/255, 20/255, 32/255, 0.72)
            border.color: Qt.rgba(255, 255, 255, 0.10); border.width: 1
            Text {
                anchors.centerIn: parent
                text: "REBOOT"
                color: clrText
                font.family: fontMono; font.pixelSize: 11; font.letterSpacing: 3; font.weight: Font.Bold
            }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: sddm.reboot() }
        }
        // Shut down
        Rectangle {
            width: 130; height: 38; radius: 12
            color: Qt.rgba(15/255, 20/255, 32/255, 0.72)
            border.color: Qt.rgba(255, 255, 255, 0.10); border.width: 1
            Text {
                anchors.centerIn: parent
                text: "SHUT DOWN"
                color: clrText
                font.family: fontMono; font.pixelSize: 11; font.letterSpacing: 3; font.weight: Font.Bold
            }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: sddm.powerOff() }
        }
    }

    // ── Bottom-left signature ────────────────────────────────────────────────
    Text {
        anchors.left:   parent.left
        anchors.bottom: parent.bottom
        anchors.leftMargin:   40
        anchors.bottomMargin: 44
        text: "NYX-J5W-2026 · BUILT BY HAND"
        color: clrTextFaint
        font.family: fontMono
        font.pixelSize: 10
        font.letterSpacing: 3
    }

    // ── Login action ─────────────────────────────────────────────────────────
    function doLogin() {
        if (passwordField.text.length === 0) {
            authFailed = true
            authMsg = "PASSWORD REQUIRED"
            shakeAnim.restart()
            return
        }
        authBusy   = true
        authFailed = false
        authMsg    = ""
        sddm.login(userBox.currentText, passwordField.text, sessionBox.currentIndex)
    }
}
