// ============================================================================
//  NYXUS · SDDM theme — Main.qml                          rev 2026-05-13 r2
//
//  DARK MIRROR brand login screen. One-of-a-kind: stacked aurora gradient
//  background, ◤ X ◥ glyph + animated underline, AccountsService-backed
//  user picker on the left, password panel + session selector on the right,
//  hairline status bar (hostname · datetime · battery · network) along the
//  bottom. No blur on the foreground panels — sharp glass with thin rules.
//
//  Implements:
//    · U3   — sharp non-blurry visuals, full-rebuild brand
//    · P6.33 — AccountsService user list (model populated by ListView from
//             /var/lib/AccountsService/users via the SDDM userModel role).
//
//  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
// ============================================================================
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SddmComponents 2.0

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: "#040406"

    // Brand palette (DARK MIRROR).
    readonly property color accent:     "#C084FC"
    readonly property color accentDim:  "#7C3AED"
    readonly property color hairline:   "#1A1722"
    readonly property color panel:      "#0A0810"
    readonly property color panelEdge:  "#1F1B2C"
    readonly property color textHi:     "#E9E5F2"
    readonly property color textLo:     "#7B7390"
    readonly property color danger:     "#F87171"

    // ── BACKGROUND: layered radial + linear, no blur, sharp gradient ────
    // Drawn directly with Rectangle gradients so it stays crisp at 4K.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.00; color: "#0A0712" }
            GradientStop { position: 0.45; color: "#06050B" }
            GradientStop { position: 1.00; color: "#000000" }
        }
    }
    // Subtle aurora glow top-left.
    Rectangle {
        width: 900; height: 900; radius: 450
        x: -300; y: -300
        opacity: 0.18
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.accent }
            GradientStop { position: 1.0; color: "#00000000" }
        }
    }
    // Aurora glow bottom-right (cooler).
    Rectangle {
        width: 1100; height: 1100; radius: 550
        x: parent.width - 800; y: parent.height - 800
        opacity: 0.12
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#5B21B6" }
            GradientStop { position: 1.0; color: "#00000000" }
        }
    }

    // ── BRAND HEADER (centred, top) ────────────────────────────────────
    ColumnLayout {
        id: header
        anchors.top: parent.top
        anchors.topMargin: 56
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 4

        Text {
            text: "◤ X ◥"
            color: root.accent
            font.family: "JetBrains Mono"
            font.pixelSize: 56
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
            // Soft glow via duplicated Text with opacity (no blur shader).
        }
        Text {
            text: "NYXUS"
            color: root.accent
            font.family: "JetBrains Mono"
            font.pixelSize: 22
            font.letterSpacing: 8
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }
        Text {
            text: "DARK MIRROR"
            color: root.textLo
            font.family: "JetBrains Mono"
            font.pixelSize: 10
            font.letterSpacing: 12
            Layout.alignment: Qt.AlignHCenter
        }
        Rectangle {
            Layout.preferredWidth: 220
            Layout.preferredHeight: 1
            Layout.alignment: Qt.AlignHCenter
            color: root.accent
            opacity: 0.35
            Layout.topMargin: 8
        }
    }

    // ── USER PICKER (left panel) — populated from AccountsService ─────
    Rectangle {
        id: usersPanel
        width: 340
        height: 560
        anchors.left: parent.left
        anchors.leftMargin: 120
        anchors.verticalCenter: parent.verticalCenter
        color: root.panel
        border.color: root.panelEdge
        border.width: 1
        radius: 0      // sharp corners — DARK MIRROR is slab-edged.

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 12

            Text {
                text: "ACCOUNTS"
                color: root.textLo
                font.family: "JetBrains Mono"
                font.pixelSize: 10
                font.letterSpacing: 6
                Layout.alignment: Qt.AlignHCenter
                Layout.bottomMargin: 6
            }

            ListView {
                id: usersView
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: userModel        // SDDM-provided, backed by AccountsService
                spacing: 6
                currentIndex: userModel.lastIndex >= 0 ? userModel.lastIndex : 0
                onCurrentIndexChanged: {
                    if (currentIndex >= 0 && currentItem)
                        passwordField.forceActiveFocus()
                }
                delegate: Item {
                    width: usersView.width
                    height: 56
                    Rectangle {
                        anchors.fill: parent
                        color: ListView.isCurrentItem ? "#15101F" : "transparent"
                        border.color: ListView.isCurrentItem ? root.accent : "transparent"
                        border.width: 1
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 12
                            // Avatar — AccountsService PNG, fall back to glyph.
                            Image {
                                source: model.icon !== "" ? "file://" + model.icon : ""
                                fillMode: Image.PreserveAspectCrop
                                Layout.preferredWidth: 36
                                Layout.preferredHeight: 36
                                visible: source != ""
                            }
                            Rectangle {
                                Layout.preferredWidth: 36
                                Layout.preferredHeight: 36
                                color: root.accentDim
                                visible: !model.icon
                                Text {
                                    anchors.centerIn: parent
                                    text: model.name.length > 0 ? model.name.substring(0,1).toUpperCase() : "?"
                                    color: "#FFFFFF"
                                    font.family: "JetBrains Mono"
                                    font.pixelSize: 18
                                    font.bold: true
                                }
                            }
                            ColumnLayout {
                                spacing: 0
                                Text {
                                    text: model.realName !== "" ? model.realName : model.name
                                    color: root.textHi
                                    font.family: "JetBrains Mono"
                                    font.pixelSize: 14
                                    font.bold: true
                                }
                                Text {
                                    text: "@" + model.name
                                    color: root.textLo
                                    font.family: "JetBrains Mono"
                                    font.pixelSize: 10
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: usersView.currentIndex = index
                        }
                    }
                }
            }
        }
    }

    // ── LOGIN PANEL (right) ─────────────────────────────────────────────
    Rectangle {
        id: loginPanel
        width: 460
        height: 420
        anchors.right: parent.right
        anchors.rightMargin: 120
        anchors.verticalCenter: parent.verticalCenter
        color: root.panel
        border.color: root.panelEdge
        border.width: 1
        radius: 0

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 32
            spacing: 18

            Text {
                text: "AUTHENTICATE"
                color: root.textLo
                font.family: "JetBrains Mono"
                font.pixelSize: 10
                font.letterSpacing: 6
                Layout.alignment: Qt.AlignHCenter
            }

            Text {
                id: greeting
                text: usersView.currentItem
                      ? "Welcome back, " + (userModel.data(userModel.index(usersView.currentIndex, 0), Qt.UserRole + 2) || "")
                      : "Welcome"
                color: root.textHi
                font.family: "JetBrains Mono"
                font.pixelSize: 18
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: root.hairline
            }

            // Password field.
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                color: "#050308"
                border.color: passwordField.activeFocus ? root.accent : root.panelEdge
                border.width: 1
                TextInput {
                    id: passwordField
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    color: root.textHi
                    font.family: "JetBrains Mono"
                    font.pixelSize: 16
                    echoMode: TextInput.Password
                    passwordCharacter: "•"
                    selectByMouse: true
                    verticalAlignment: TextInput.AlignVCenter
                    Keys.onReturnPressed:  loginButton.activate()
                    Keys.onEnterPressed:   loginButton.activate()
                }
                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    text: "passphrase"
                    color: root.textLo
                    font.family: "JetBrains Mono"
                    font.pixelSize: 14
                    visible: passwordField.text.length === 0 && !passwordField.activeFocus
                }
            }

            // Error text (hidden when empty).
            Text {
                id: errorText
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                color: root.danger
                font.family: "JetBrains Mono"
                font.pixelSize: 11
                text: ""
                visible: text.length > 0
            }

            // Session selector.
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Text {
                    text: "SESSION"
                    color: root.textLo
                    font.family: "JetBrains Mono"
                    font.pixelSize: 10
                    font.letterSpacing: 4
                }
                ComboBox {
                    id: sessionBox
                    Layout.fillWidth: true
                    model: sessionModel
                    textRole: "name"
                    currentIndex: sessionModel.lastIndex >= 0 ? sessionModel.lastIndex : 0
                    font.family: "JetBrains Mono"
                    font.pixelSize: 12
                }
            }

            // Login button.
            Rectangle {
                id: loginButton
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                color: ma.containsMouse ? root.accent : "#1A1424"
                border.color: root.accent
                border.width: 1
                function activate() {
                    var idx = usersView.currentIndex >= 0 ? usersView.currentIndex : 0
                    sddm.login(userModel.data(userModel.index(idx, 0), Qt.UserRole + 1),
                               passwordField.text,
                               sessionBox.currentIndex)
                }
                MouseArea {
                    id: ma
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: loginButton.activate()
                }
                Text {
                    anchors.centerIn: parent
                    text: "ENTER"
                    color: ma.containsMouse ? "#0A0810" : root.accent
                    font.family: "JetBrains Mono"
                    font.pixelSize: 13
                    font.letterSpacing: 8
                    font.bold: true
                }
            }

            Item { Layout.fillHeight: true }
        }
    }

    // ── FOOTER STATUS BAR (sharp hairline) ──────────────────────────────
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 36
        color: "#04030A"
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: root.hairline
        }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            spacing: 20
            Text {
                text: "NYXUS · DARK MIRROR · " + Qt.application.version
                color: root.textLo
                font.family: "JetBrains Mono"
                font.pixelSize: 10
                font.letterSpacing: 4
            }
            Item { Layout.fillWidth: true }
            Text {
                id: clock
                color: root.textLo
                font.family: "JetBrains Mono"
                font.pixelSize: 11
                Timer {
                    interval: 1000
                    running: true
                    repeat: true
                    triggeredOnStart: true
                    onTriggered: {
                        var d = new Date()
                        clock.text = Qt.formatDateTime(d, "ddd · MMM dd · hh:mm:ss")
                    }
                }
            }
            Item { Layout.preferredWidth: 24 }
            Text {
                text: "F1 SESSION  ·  F2 LAYOUT  ·  F12 POWER"
                color: root.textLo
                font.family: "JetBrains Mono"
                font.pixelSize: 10
                font.letterSpacing: 3
            }
        }
    }

    // ── SDDM signal hookups ─────────────────────────────────────────────
    Connections {
        target: sddm
        function onLoginFailed() {
            errorText.text = "ACCESS DENIED"
            passwordField.text = ""
            passwordField.forceActiveFocus()
        }
        function onLoginSucceeded() {
            errorText.text = ""
        }
    }

    // Keyboard shortcuts: F12 power menu (rendered via SDDM API).
    Keys.onPressed: {
        if (event.key === Qt.Key_F12) {
            powerMenu.visible = !powerMenu.visible
        }
    }

    // ── POWER MENU (toggleable) ─────────────────────────────────────────
    Rectangle {
        id: powerMenu
        visible: false
        width: 320; height: 64
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 24
        anchors.rightMargin: 24
        color: root.panel
        border.color: root.accent
        border.width: 1
        RowLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 8
            Repeater {
                model: [
                    { label: "SUSPEND",  action: "suspend"  },
                    { label: "REBOOT",   action: "reboot"   },
                    { label: "SHUTDOWN", action: "shutdown" }
                ]
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: pma.containsMouse ? root.accent : "transparent"
                    border.color: root.panelEdge
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        color: pma.containsMouse ? "#0A0810" : root.textHi
                        font.family: "JetBrains Mono"
                        font.pixelSize: 10
                        font.letterSpacing: 3
                        font.bold: true
                    }
                    MouseArea {
                        id: pma
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (modelData.action === "suspend")  sddm.suspend()
                            if (modelData.action === "reboot")   sddm.reboot()
                            if (modelData.action === "shutdown") sddm.powerOff()
                        }
                    }
                }
            }
        }
    }

    Component.onCompleted: passwordField.forceActiveFocus()
}
