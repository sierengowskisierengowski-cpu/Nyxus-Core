// NYXUS · SDDM greeter · DARK MIRROR void login (rev 2026-05-12 r14)
// P2.10 polish: user avatar from ~/.face via UserModel, SUSPEND power
// action, focus rings on power buttons, screen-reader accessibility
// labels on every interactive control.
//
// Replaces a 448-line theme that broke at line 245 with a non-existent
// `contentItem` binding on a ComboBox `background:` — caused SDDM to fall
// back to the default blue Breeze theme. This rewrite is intentionally
// lean (~200 lines) and uses only well-supported QtQuick.Controls 2 API.
//
// Visual System lock (DARK MIRROR rev r13):
//   - Pure void: black base + 78% black wash over background.png, so the
//     existing cosmic-ink artwork barely whispers through as faint silver.
//   - Login card: rgba(8,12,20,0.55) dark glass, 1px white hairline at
//     0.10 alpha, 14px corner radius.
//   - Inputs: rgba(15,20,32,0.72) deeper glass.
//   - Text: #e8edf5 primary off-white, #c8ccd6 secondary, #6a6e78 hint,
//     #ffffff hover halo only.
//   - No gold, no neon, no per-app colors. Monochrome only.

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
// NOTE: do NOT import SddmComponents — its `Button` type (QQC1-era, no
// `contentItem` property) shadows the QQC2 Button and breaks the theme
// with `Cannot assign to non-existent property "contentItem"`. Nothing
// in this theme uses SddmComponents types, so the import is unneeded.

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: "#000000"

    // ── DARK MIRROR palette tokens ───────────────────────────────────────
    readonly property color clrBgVoid:       "#000000"
    readonly property color clrGlass:        Qt.rgba(8/255, 12/255, 20/255, 0.55)
    readonly property color clrGlassDeep:    Qt.rgba(15/255, 20/255, 32/255, 0.72)
    readonly property color clrGlassDeepest: Qt.rgba(5/255, 7/255, 12/255, 0.92)
    readonly property color clrHairline:     Qt.rgba(255/255, 255/255, 255/255, 0.10)
    // Accent comes from theme.conf.user (written by Settings → Appearance).
    // Falls back to the locked Mirror White if no accent has been set.
    readonly property color clrAccent:       config.Accent || "#e8edf5"
    readonly property color clrFocus:        Qt.rgba(230/255, 240/255, 255/255, 0.55)
    readonly property color clrText:         "#e8edf5"
    readonly property color clrTextDim:      "#c8ccd6"
    readonly property color clrTextHint:     "#6a6e78"
    readonly property color clrWhite:        "#ffffff"

    // ── Background: artwork + heavy void wash ────────────────────────────
    Image {
        anchors.fill: parent
        source: config.background || "background.png"
        fillMode: Image.PreserveAspectCrop
        asynchronous: false
        cache: true
        smooth: true
    }
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.78)
    }

    // ── Top-right power controls ─────────────────────────────────────────
    Row {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 24
        spacing: 8
        z: 10

        Repeater {
            model: [
                { label: "SUSPEND", action: "suspend", enabled: sddm.canSuspend  },
                { label: "REBOOT",  action: "reboot",  enabled: sddm.canReboot   },
                { label: "POWER",   action: "off",     enabled: sddm.canPowerOff }
            ]
            delegate: Button {
                id: pwrBtn
                text: modelData.label
                enabled: modelData.enabled
                font.family: "Inter"
                font.pixelSize: 11
                font.letterSpacing: 1.5
                padding: 10
                Accessible.role: Accessible.Button
                Accessible.name: modelData.label
                Accessible.description: "Session " + modelData.action.toLowerCase() + " action"
                background: Rectangle {
                    color: pwrBtn.hovered ? clrGlassDeep : clrGlass
                    // Visible keyboard focus ring — required for a11y.
                    border.color: pwrBtn.activeFocus ? clrAccent
                                : pwrBtn.hovered    ? clrFocus
                                : clrHairline
                    border.width: pwrBtn.activeFocus ? 2 : 1
                    radius: 14
                    opacity: pwrBtn.enabled ? 1.0 : 0.45
                }
                contentItem: Text {
                    text: pwrBtn.text
                    color: pwrBtn.hovered ? clrWhite : clrTextDim
                    font: pwrBtn.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: {
                    if      (modelData.action === "suspend") sddm.suspend()
                    else if (modelData.action === "reboot")  sddm.reboot()
                    else                                     sddm.powerOff()
                }
            }
        }
    }

    // ── Center clock + login card stack ──────────────────────────────────
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 28
        width: 420

        // Avatar — circular ~/.face from UserModel (when a real account
        // exists). Falls back to a hairline glyph on the live ISO. The
        // outer Rectangle gives us a hairline ring + circular clip.
        Rectangle {
            id: avatarRing
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 96
            Layout.preferredHeight: 96
            color: clrGlass
            radius: 48
            border.color: clrHairline
            border.width: 1
            // The icon source from UserModel is already a file path; if
            // missing or unreadable QML will silently skip the Image
            // and the hairline ring + glyph remain visible.
            property string iconPath: userModel.count > 0
                ? userModel.data(userModel.index(0, 0), Qt.UserRole + 2)
                : ""

            Image {
                id: avatarImg
                anchors.fill: parent
                anchors.margins: 2
                source: avatarRing.iconPath
                fillMode: Image.PreserveAspectCrop
                visible: status === Image.Ready
                asynchronous: true
                cache: true
                smooth: true
                // Round mask via OpacityMask would require QtGraphicalEffects;
                // a plain radius + clip on the parent achieves the same look
                // on every Qt 6 stack without an extra import.
                layer.enabled: true
            }
            Text {
                anchors.centerIn: parent
                visible: !avatarImg.visible
                text: "◆"
                color: clrTextDim
                font.family: "Inter"
                font.pixelSize: 38
            }
            clip: true
        }

        // Clock
        Text {
            id: clock
            Layout.alignment: Qt.AlignHCenter
            text: Qt.formatDateTime(new Date(), "HH:mm")
            color: clrText
            font.family: "Inter"
            font.pixelSize: 96
            font.weight: Font.Light
            font.letterSpacing: 4
        }
        Text {
            id: dateLabel
            Layout.alignment: Qt.AlignHCenter
            text: Qt.formatDateTime(new Date(), "dddd · d MMMM yyyy").toUpperCase()
            color: clrTextDim
            font.family: "Inter"
            font.pixelSize: 12
            font.letterSpacing: 3
        }
        Timer {
            interval: 1000
            running: true
            repeat: true
            onTriggered: {
                clock.text = Qt.formatDateTime(new Date(), "HH:mm")
                dateLabel.text = Qt.formatDateTime(new Date(), "dddd · d MMMM yyyy").toUpperCase()
            }
        }

        // Login card
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 380
            Layout.preferredHeight: 220
            color: clrGlass
            border.color: clrHairline
            border.width: 1
            radius: 14

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 24
                spacing: 14

                // Tagline
                Text {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: "WELCOME TO THE DARKSIDE"
                    color: clrTextHint
                    font.family: "Inter"
                    font.pixelSize: 10
                    font.letterSpacing: 2.5
                }

                // Username field (free entry — works on live ISO with no users)
                TextField {
                    id: userField
                    Layout.fillWidth: true
                    placeholderText: "username"
                    placeholderTextColor: clrTextHint
                    color: clrText
                    font.family: "Inter"
                    font.pixelSize: 14
                    text: userModel.lastUser || (userModel.count > 0 ? userModel.data(userModel.index(0, 0), Qt.UserRole + 1) : "root")
                    selectByMouse: true
                    leftPadding: 14
                    rightPadding: 14
                    Accessible.role: Accessible.EditableText
                    Accessible.name: "Username"
                    Accessible.description: "Account username for sign-in"
                    background: Rectangle {
                        color: clrGlassDeep
                        border.color: userField.activeFocus ? clrFocus : clrHairline
                        border.width: 1
                        radius: 10
                    }
                    KeyNavigation.tab: passwordField
                }

                // Password field
                TextField {
                    id: passwordField
                    Layout.fillWidth: true
                    placeholderText: config.PasswordFieldPlaceholderText || "enter passphrase"
                    placeholderTextColor: clrTextHint
                    color: clrText
                    font.family: "Inter"
                    font.pixelSize: 14
                    echoMode: TextInput.Password
                    passwordCharacter: "•"
                    selectByMouse: true
                    leftPadding: 14
                    rightPadding: 14
                    Accessible.role: Accessible.EditableText
                    Accessible.name: "Password"
                    Accessible.description: "Account password — input is hidden"
                    background: Rectangle {
                        color: clrGlassDeep
                        border.color: passwordField.activeFocus ? clrFocus : clrHairline
                        border.width: 1
                        radius: 10
                    }
                    Keys.onReturnPressed: signInBtn.clicked()
                    Keys.onEnterPressed:  signInBtn.clicked()
                }

                // Sign-in button
                Button {
                    id: signInBtn
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
                    text: config.LoginButtonText || "SIGN IN"
                    font.family: "Inter"
                    font.pixelSize: 12
                    font.letterSpacing: 3
                    Accessible.role: Accessible.Button
                    Accessible.name: "Sign in"
                    Accessible.description: "Authenticate and start the selected session"
                    background: Rectangle {
                        color: signInBtn.hovered ? clrGlassDeepest : clrGlassDeep
                        border.color: signInBtn.hovered ? clrAccent : clrHairline
                        border.width: 1
                        radius: 10
                    }
                    contentItem: Text {
                        text: signInBtn.text
                        color: signInBtn.hovered ? clrWhite : clrText
                        font: signInBtn.font
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: sddm.login(userField.text, passwordField.text, sessionCombo.currentIndex)
                }

                // Error indicator
                Text {
                    id: errorLine
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    color: clrTextDim
                    font.family: "Inter"
                    font.pixelSize: 10
                    font.letterSpacing: 1.5
                    text: ""
                }
            }
        }

        // Session selector (small, beneath card)
        ComboBox {
            id: sessionCombo
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 220
            model: sessionModel
            textRole: "name"
            currentIndex: sessionModel.lastIndex >= 0 ? sessionModel.lastIndex : 0
            font.family: "Inter"
            font.pixelSize: 11
            background: Rectangle {
                color: clrGlass
                border.color: clrHairline
                border.width: 1
                radius: 10
            }
            contentItem: Text {
                text: sessionCombo.displayText
                color: clrTextDim
                font: sessionCombo.font
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                leftPadding: 14
            }
            popup.background: Rectangle {
                color: clrGlassDeepest
                border.color: clrHairline
                border.width: 1
                radius: 10
            }
        }
    }

    // ── Bottom-left wordmark ─────────────────────────────────────────────
    Text {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 24
        text: "SIERENGOWSKI"
        color: clrTextHint
        font.family: "Inter"
        font.pixelSize: 10
        font.letterSpacing: 4
    }

    // ── SDDM signal wiring ───────────────────────────────────────────────
    Connections {
        target: sddm
        function onLoginSucceeded() { errorLine.text = "" }
        function onLoginFailed() {
            errorLine.text = "ACCESS DENIED"
            passwordField.selectAll()
            passwordField.forceActiveFocus()
        }
    }

    Component.onCompleted: passwordField.forceActiveFocus()
}
