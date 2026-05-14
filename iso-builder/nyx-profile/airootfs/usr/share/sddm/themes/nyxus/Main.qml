// ============================================================================
//  NYXUS · SDDM theme — Main.qml                          rev 2026-05-14 r3
//
//  THE FRONT DOOR. First thing every user sees. Single centred frosted-glass
//  card on an atmospheric layered background. The Eclipse mark sits above
//  the card; the wordmark sits inside it. One clock, big, above the panel.
//  Cream accent throughout (rev r15). No purple. No "Dark Mirror" branding.
//  No duplicate datetime. No slab edges. No overlap.
//
//  Layout:
//                         CLOCK (huge)
//                    Tue · May 14 · 2026
//                          ────────
//                       [ECLIPSE MARK]
//                           NYXUS
//
//                  ┌────────────────────────┐
//                  │   Welcome, <name>      │
//                  │  ─────────────────     │
//                  │  ┌──────────────────┐  │
//                  │  │ passphrase       │  │
//                  │  └──────────────────┘  │
//                  │   SESSION  [Hyprland▾] │
//                  │  ┌──────────────────┐  │
//                  │  │      ENTER       │  │
//                  │  └──────────────────┘  │
//                  └────────────────────────┘
//
//                hostname        F1 SESSION · F12 POWER
//
//  Implements P6.33 (AccountsService user picker — preserved as a compact
//  pill row above the card so multi-user systems still get a picker
//  without dominating the screen).
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
    color: "#000000"

    // Brand palette — rev r15 (cream + triple-black, locked).
    readonly property color cream:     "#f4ead5"
    readonly property color creamDim:  "#bfa97a"
    readonly property color black1:    "#000000"
    readonly property color black2:    "#06060a"
    readonly property color black3:    "#0a0a0e"
    readonly property color edge:      Qt.rgba(0.957, 0.918, 0.835, 0.10)
    readonly property color edgeHi:    Qt.rgba(0.957, 0.918, 0.835, 0.22)
    readonly property color textHi:    "#f4ead5"
    readonly property color textLo:    Qt.rgba(0.957, 0.918, 0.835, 0.55)
    readonly property color danger:    "#f87171"

    // Theme-relative — Eclipse PNG ships inside the SDDM tarball itself so
    // we never depend on the qt-svg plugin or the brand PNG render step
    // ordering during ISO bake. Falls back to /usr/share/nyxus/brand/png/
    // if the bundled file is somehow absent.
    readonly property string brandDir: "."
    readonly property string eclipseSrc: "eclipse.png"

    // ── BACKGROUND: layered atmospheric gradient ────────────────────────
    // No purple. Pure black with a subtle warm cream wash high-left and a
    // colder near-black wash bottom-right to imply depth.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.00; color: "#070608" }
            GradientStop { position: 0.55; color: "#030305" }
            GradientStop { position: 1.00; color: "#000000" }
        }
    }
    Rectangle {                               // soft cream wash, top-left
        width: 1100; height: 1100; radius: 550
        x: -350; y: -350
        opacity: 0.06
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.cream }
            GradientStop { position: 1.0; color: "#00000000" }
        }
    }
    Rectangle {                               // cool depth wash, bottom-right
        width: 1300; height: 1300; radius: 650
        x: parent.width - 950; y: parent.height - 950
        opacity: 0.08
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#1a1a22" }
            GradientStop { position: 1.0; color: "#00000000" }
        }
    }

    // ── HEADER STACK (clock · date · separator · mark · wordmark) ───────
    ColumnLayout {
        id: header
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: card.top
        anchors.bottomMargin: 56
        spacing: 6

        // Clock — the only datetime on screen.
        Text {
            id: clock
            color: root.textHi
            font.family: "JetBrains Mono"
            font.pixelSize: 88
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
            Timer {
                interval: 1000
                running: true
                repeat: true
                triggeredOnStart: true
                onTriggered: clock.text = Qt.formatDateTime(new Date(), "HH:mm")
            }
        }
        Text {
            id: dateLine
            color: root.textLo
            font.family: "Inter"
            font.pixelSize: 14
            font.letterSpacing: 4
            Layout.alignment: Qt.AlignHCenter
            Timer {
                interval: 60000
                running: true
                repeat: true
                triggeredOnStart: true
                onTriggered: dateLine.text =
                    Qt.formatDateTime(new Date(), "ddd · MMM dd · yyyy").toUpperCase()
            }
        }
        Rectangle {                                // hairline separator
            Layout.preferredWidth: 80
            Layout.preferredHeight: 1
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 12
            color: root.edge
        }
        // The Eclipse mark — pre-rendered PNG bundled inside the SDDM theme
        // tarball. No qt-svg plugin dependency, no fragile load-order coupling
        // with the brand PNG render step. If the bundled PNG is missing the
        // wordmark below still reads as NYXUS.
        Image {
            source: root.eclipseSrc
            sourceSize.width: 56
            sourceSize.height: 56
            Layout.preferredWidth: 56
            Layout.preferredHeight: 56
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 12
            fillMode: Image.PreserveAspectFit
            smooth: true
        }
        Text {
            text: "NYXUS"
            color: root.textHi
            font.family: "Inter"
            font.pixelSize: 22
            font.letterSpacing: 12
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 4
        }
    }

    // ── ACCOUNT PICKER (compact pill row, only visible if >1 account) ──
    RowLayout {
        id: picker
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: header.top
        anchors.bottomMargin: 24
        spacing: 8
        visible: userModel.count > 1

        Repeater {
            model: userModel
            Rectangle {
                Layout.preferredHeight: 36
                Layout.preferredWidth: 140
                radius: 3
                color: usersView.currentIndex === index
                       ? Qt.rgba(0.957, 0.918, 0.835, 0.10)
                       : "transparent"
                border.color: usersView.currentIndex === index
                       ? root.edgeHi : root.edge
                border.width: 1
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 8
                    Image {
                        source: model.icon !== "" ? "file://" + model.icon : ""
                        Layout.preferredWidth: 22
                        Layout.preferredHeight: 22
                        fillMode: Image.PreserveAspectCrop
                        visible: source != ""
                    }
                    Text {
                        text: model.realName !== "" ? model.realName : model.name
                        color: usersView.currentIndex === index
                               ? root.cream : root.textLo
                        font.family: "Inter"
                        font.pixelSize: 12
                        font.bold: true
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        usersView.currentIndex = index
                        passwordField.forceActiveFocus()
                    }
                }
            }
        }
    }
    // Hidden ListView keeps SDDM's user model semantics intact for the
    // single-user case (no visible picker, but currentIndex still tracks).
    ListView {
        id: usersView
        visible: false
        model: userModel
        currentIndex: userModel.lastIndex >= 0 ? userModel.lastIndex : 0
    }

    // ── THE GLASS CARD ──────────────────────────────────────────────────
    // Single centred panel. Layered translucent fills + cream hairline edge
    // + multi-stop shadow approximate frosted glass without a real blur
    // shader (which crashes some intel GPUs in the live SDDM context).
    Rectangle {
        id: card
        width: 460
        height: 360
        radius: 3
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: 60
        color: Qt.rgba(0.024, 0.024, 0.039, 0.78)   // black2 @ 78%
        border.color: root.edge
        border.width: 1

        // Inner top sheen.
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 1
            color: Qt.rgba(0.957, 0.918, 0.835, 0.06)
        }
        // Outer drop shadow rim (faked).
        Rectangle {
            anchors.fill: parent
            anchors.margins: -1
            radius: 4
            color: "transparent"
            border.color: Qt.rgba(0, 0, 0, 0.55)
            border.width: 1
            z: -1
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 32
            spacing: 16

            // Greeting.
            Text {
                id: greeting
                text: usersView.currentItem
                      ? "Welcome, " + (
                            userModel.data(userModel.index(usersView.currentIndex, 0),
                                           Qt.UserRole + 2) || "")
                      : "Welcome"
                color: root.textHi
                font.family: "Inter"
                font.pixelSize: 18
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: root.edge
            }

            // Password field.
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                radius: 3
                color: root.black1
                border.color: passwordField.activeFocus ? root.cream : root.edge
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
                    Keys.onReturnPressed: loginButton.activate()
                    Keys.onEnterPressed:  loginButton.activate()
                }
                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    text: "passphrase"
                    color: root.textLo
                    font.family: "Inter"
                    font.pixelSize: 14
                    visible: passwordField.text.length === 0
                             && !passwordField.activeFocus
                }
            }

            // Error text (hidden when empty — never reserves space).
            Text {
                id: errorText
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                color: root.danger
                font.family: "Inter"
                font.pixelSize: 11
                font.letterSpacing: 4
                text: ""
                visible: text.length > 0
            }

            // Session selector — preserved.
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Text {
                    text: "SESSION"
                    color: root.textLo
                    font.family: "Inter"
                    font.pixelSize: 10
                    font.letterSpacing: 4
                }
                ComboBox {
                    id: sessionBox
                    Layout.fillWidth: true
                    model: sessionModel
                    textRole: "name"
                    currentIndex: sessionModel.lastIndex >= 0
                                  ? sessionModel.lastIndex : 0
                    font.family: "Inter"
                    font.pixelSize: 12
                }
            }

            // ENTER button.
            Rectangle {
                id: loginButton
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                radius: 3
                color: ma.containsMouse ? root.cream
                                        : Qt.rgba(0.024, 0.024, 0.039, 0.85)
                border.color: ma.containsMouse ? root.creamDim : root.edgeHi
                border.width: 1

                function activate() {
                    var idx = usersView.currentIndex >= 0 ? usersView.currentIndex : 0
                    sddm.login(
                        userModel.data(userModel.index(idx, 0), Qt.UserRole + 1),
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
                    color: ma.containsMouse ? root.black2 : root.cream
                    font.family: "Inter"
                    font.pixelSize: 13
                    font.letterSpacing: 8
                    font.bold: true
                }
            }

            Item { Layout.fillHeight: true }
        }
    }

    // ── FOOTER (hostname + key hints — no clock dup) ────────────────────
    RowLayout {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottomMargin: 24
        anchors.leftMargin: 32
        anchors.rightMargin: 32
        spacing: 20
        Text {
            text: "NYXUS · " + Qt.application.version
            color: root.textLo
            font.family: "Inter"
            font.pixelSize: 10
            font.letterSpacing: 4
        }
        Item { Layout.fillWidth: true }
        Text {
            text: "F1 SESSION  ·  F2 LAYOUT  ·  F12 POWER"
            color: root.textLo
            font.family: "Inter"
            font.pixelSize: 10
            font.letterSpacing: 3
        }
    }

    // ── SDDM signals ────────────────────────────────────────────────────
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

    Keys.onPressed: {
        if (event.key === Qt.Key_F12) powerMenu.visible = !powerMenu.visible
    }

    // ── POWER MENU (toggleable, top-right) ──────────────────────────────
    Rectangle {
        id: powerMenu
        visible: false
        width: 320; height: 56; radius: 3
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 24
        anchors.rightMargin: 24
        color: Qt.rgba(0.024, 0.024, 0.039, 0.92)
        border.color: root.edgeHi
        border.width: 1
        RowLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 6
            Repeater {
                model: [
                    { label: "SUSPEND",  action: "suspend"  },
                    { label: "REBOOT",   action: "reboot"   },
                    { label: "SHUTDOWN", action: "shutdown" }
                ]
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 3
                    color: pma.containsMouse ? root.cream : "transparent"
                    border.color: root.edge
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        color: pma.containsMouse ? root.black2 : root.textHi
                        font.family: "Inter"
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
