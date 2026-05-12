// ═══════════════════════════════════════════════════════════════════════════
//  NYXUS · SDDM greeter · DARK MIRROR void login (rev 2026-05-11 r6)
//  © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
//
//  WHAT'S NEW IN r6
//  ───────────────────────────────────────────────────────────────────────
//   · New void-vortex background (matches desktop wallpaper).
//   · Tightened glass card geometry; centred clock/date stack above it.
//   · Biometric status row beneath the password field — fingerprint and
//     face are tried automatically by the PAM stack (/etc/pam.d/sddm),
//     these icons just give the user feedback that the silent retry is
//     happening.
//   · SECRET BACKDOOR PANEL — hidden behind the key combo:
//         Ctrl + Backspace + F + U  (held simultaneously, in any order)
//     The greeter flips (180° Y-axis) into a separate panel demanding
//     password + YubiKey touch.  The auth chain is /etc/pam.d/sddm-backdoor
//     and is reached by prepending the magic prefix "\u0001NYXBD\u0001"
//     to the password sent through sddm.login() — pam_exec at the top of
//     /etc/pam.d/sddm detects the prefix, strips it, and routes the
//     authtok through nyxus-ghost-auth + pam_u2f.  Without the prefix
//     (i.e., normal front-door logins), routing is a no-op.
//
//  PALETTE (locked — matches hyprlock, waybar, app chrome)
//    void          #000000
//    glass         rgba(8, 12, 20, 0.55)
//    glass deep    rgba(15, 20, 32, 0.72)
//    hairline      rgba(255, 255, 255, 0.10)
//    text          #e8edf5    text dim  #c8ccd6   text hint  #6a6e78
//    accent danger #b22424     (used only in backdoor border, never main)
// ═══════════════════════════════════════════════════════════════════════════

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: "#000000"
    focus: true   // captures key events for the backdoor combo

    // ── DARK MIRROR palette ──────────────────────────────────────────────
    readonly property color clrBgVoid:       "#000000"
    readonly property color clrGlass:        Qt.rgba(8/255, 12/255, 20/255, 0.55)
    readonly property color clrGlassDeep:    Qt.rgba(15/255, 20/255, 32/255, 0.72)
    readonly property color clrGlassDeepest: Qt.rgba(5/255, 7/255, 12/255, 0.92)
    readonly property color clrHairline:     Qt.rgba(1.0, 1.0, 1.0, 0.10)
    // Accent comes from theme.conf.user (written by Settings → Appearance).
    // Falls back to the locked Mirror White if no accent has been set.
    readonly property color clrAccent:       config.Accent || "#e8edf5"
    readonly property color clrFocus:        Qt.rgba(0.90, 0.94, 1.0, 0.55)
    readonly property color clrText:         "#e8edf5"
    readonly property color clrTextDim:      "#c8ccd6"
    readonly property color clrTextHint:     "#6a6e78"
    readonly property color clrWhite:        "#ffffff"
    readonly property color clrBackdoor:     Qt.rgba(178/255, 36/255, 36/255, 0.85)

    // ── Backdoor magic prefix + field separator ───────────────────────────
    // MUST match the constants in /usr/local/bin/nyxus-bd-router:
    //     PREFIX = \x01 NYXBD \x01
    //     SEP    = \x02
    // Authtok layout when in backdoor mode:
    //     PREFIX + ghostPassword + SEP + yubikeyPin + SEP + totpCode
    readonly property string backdoorPrefix:    "\u0001NYXBD\u0001"
    readonly property string backdoorSeparator: "\u0002"

    // ── Backdoor key-combo state machine ─────────────────────────────────
    // Combo: Ctrl + Backspace + F + U  (must all be pressed; order doesn't
    // matter; combo resets on any key release).
    property bool kCtrl:      false
    property bool kBackspace: false
    property bool kF:         false
    property bool kU:         false
    property bool inBackdoor: false   // true when the panel is flipped open

    function checkCombo() {
        if (kCtrl && kBackspace && kF && kU && !inBackdoor) {
            inBackdoor = true
            // Reset the latches so leaving and re-entering works cleanly
            kCtrl = false; kBackspace = false; kF = false; kU = false
            backdoorUserField.forceActiveFocus()
            // Wipe any stray letters typed during the combo into the
            // visible password field.  The combo keys (f / u) and the
            // Backspace edits will have left the front-door password in
            // an unpredictable state; clear it so the user doesn't ship
            // garbage if they ever flip back.
            passwordField.text = ""
        }
    }

    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Control)   kCtrl = true
        if (event.key === Qt.Key_Backspace) kBackspace = true
        if (event.key === Qt.Key_F)         kF = true
        if (event.key === Qt.Key_U)         kU = true
        checkCombo()
    }
    Keys.onReleased: function(event) {
        if (event.key === Qt.Key_Control)   kCtrl = false
        if (event.key === Qt.Key_Backspace) kBackspace = false
        if (event.key === Qt.Key_F)         kF = false
        if (event.key === Qt.Key_U)         kU = false
    }

    // ═════════════════════════════════════════════════════════════════════
    //  BACKGROUND  (full-bleed vortex artwork + heavy void wash)
    // ═════════════════════════════════════════════════════════════════════
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
        color: Qt.rgba(0, 0, 0, 0.74)
    }

    // ═════════════════════════════════════════════════════════════════════
    //  TOP-RIGHT POWER CONTROLS
    // ═════════════════════════════════════════════════════════════════════
    Row {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 28
        spacing: 8
        z: 10

        Repeater {
            model: [
                { label: "REBOOT", action: "reboot", enabled: sddm.canReboot   },
                { label: "POWER",  action: "off",    enabled: sddm.canPowerOff }
            ]
            delegate: Button {
                text: modelData.label
                enabled: modelData.enabled
                font.family: "Inter"
                font.pixelSize: 10
                font.letterSpacing: 2.0
                padding: 11
                background: Rectangle {
                    color: parent.hovered ? clrGlassDeep : clrGlass
                    border.color: clrHairline
                    border.width: 1
                    radius: 14
                }
                contentItem: Text {
                    text: parent.text
                    color: parent.hovered ? clrWhite : clrTextDim
                    font: parent.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: {
                    if (modelData.action === "reboot") sddm.reboot()
                    else                                sddm.powerOff()
                }
            }
        }
    }

    // ═════════════════════════════════════════════════════════════════════
    //  CENTER STACK  (clock + date + login card + session combo)
    //  Wrapped in a flippable Item so the backdoor can rotate it out.
    // ═════════════════════════════════════════════════════════════════════
    Item {
        id: cardFlipper
        anchors.centerIn: parent
        width: 460
        height: 560

        // 3D Y-axis flip when entering the backdoor
        transform: Rotation {
            id: flipRot
            origin.x: cardFlipper.width / 2
            origin.y: cardFlipper.height / 2
            axis { x: 0; y: 1; z: 0 }
            angle: inBackdoor ? 180 : 0
            Behavior on angle {
                NumberAnimation { duration: 650; easing.type: Easing.InOutQuad }
            }
        }

        // ── FRONT FACE: standard login ────────────────────────────────────
        ColumnLayout {
            id: frontFace
            anchors.fill: parent
            spacing: 30
            // Hide the front when fully flipped (>90°) so back doesn't bleed through
            visible: flipRot.angle <= 90

            Text {
                id: clock
                Layout.alignment: Qt.AlignHCenter
                text: Qt.formatDateTime(new Date(), "HH:mm")
                color: clrText
                font.family: "Inter"
                font.pixelSize: 104
                font.weight: Font.Light
                font.letterSpacing: 5
            }
            Text {
                id: dateLabel
                Layout.alignment: Qt.AlignHCenter
                text: Qt.formatDateTime(new Date(), "dddd · d MMMM yyyy").toUpperCase()
                color: clrTextDim
                font.family: "Inter"
                font.pixelSize: 12
                font.letterSpacing: 3.5
            }
            Timer {
                interval: 1000; running: true; repeat: true
                onTriggered: {
                    clock.text     = Qt.formatDateTime(new Date(), "HH:mm")
                    dateLabel.text = Qt.formatDateTime(new Date(), "dddd · d MMMM yyyy").toUpperCase()
                }
            }

            // ── Login card ────────────────────────────────────────────────
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 400
                Layout.preferredHeight: 280
                color: clrGlass
                border.color: clrHairline
                border.width: 1
                radius: 16

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 26
                    spacing: 14

                    Text {
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        text: "WELCOME TO THE DARKSIDE"
                        color: clrTextHint
                        font.family: "Inter"
                        font.pixelSize: 10
                        font.letterSpacing: 3
                    }

                    TextField {
                        id: userField
                        Layout.fillWidth: true
                        placeholderText: "username"
                        placeholderTextColor: clrTextHint
                        color: clrText
                        font.family: "Inter"
                        font.pixelSize: 14
                        text: userModel.lastUser || (userModel.count > 0
                              ? userModel.data(userModel.index(0, 0), Qt.UserRole + 1)
                              : "nyx")
                        selectByMouse: true
                        leftPadding: 14; rightPadding: 14
                        background: Rectangle {
                            color: clrGlassDeep
                            border.color: userField.activeFocus ? clrFocus : clrHairline
                            border.width: 1
                            radius: 10
                        }
                        KeyNavigation.tab: passwordField
                        // Forward every key event to root so the secret combo
                        // detector still sees F / U / Backspace even while
                        // this field has focus.
                        Keys.forwardTo: [root]
                    }

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
                        leftPadding: 14; rightPadding: 14
                        background: Rectangle {
                            color: clrGlassDeep
                            border.color: passwordField.activeFocus ? clrFocus : clrHairline
                            border.width: 1
                            radius: 10
                        }
                        Keys.onReturnPressed: signInBtn.clicked()
                        Keys.onEnterPressed:  signInBtn.clicked()
                        // Same forward — TextField normally swallows letter
                        // keys and Backspace; without this the 4-key combo
                        // would never reach root's Keys.onPressed handler.
                        Keys.forwardTo: [root]
                    }

                    Button {
                        id: signInBtn
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        text: config.LoginButtonText || "SIGN IN"
                        font.family: "Inter"
                        font.pixelSize: 12
                        font.letterSpacing: 3.5
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
                        onClicked: sddm.login(userField.text,
                                              passwordField.text,
                                              sessionCombo.currentIndex)
                    }

                    // Biometric status row — visual cue that fprintd + howdy
                    // are running silently in the PAM stack.  No buttons: the
                    // whole point is that biometrics happen automatically;
                    // touching the sensor / facing the camera Just Works.
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 22
                        Text {
                            text: "◐  FINGERPRINT"
                            color: clrTextHint
                            font.family: "Inter"; font.pixelSize: 9; font.letterSpacing: 1.8
                        }
                        Text {
                            text: "◑  FACE"
                            color: clrTextHint
                            font.family: "Inter"; font.pixelSize: 9; font.letterSpacing: 1.8
                        }
                        Text {
                            text: "◒  PASSPHRASE"
                            color: clrTextHint
                            font.family: "Inter"; font.pixelSize: 9; font.letterSpacing: 1.8
                        }
                    }

                    Text {
                        id: errorLine
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        color: clrTextDim
                        font.family: "Inter"; font.pixelSize: 10; font.letterSpacing: 1.5
                        text: ""
                    }
                }
            }

            ComboBox {
                id: sessionCombo
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 240
                model: sessionModel
                textRole: "name"
                currentIndex: sessionModel.lastIndex >= 0 ? sessionModel.lastIndex : 0
                font.family: "Inter"; font.pixelSize: 11
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

        // ── BACK FACE: SECRET BACKDOOR PANEL ──────────────────────────────
        // Visible only when the combo flips the card.  Counter-rotated so
        // the text reads correctly when the parent is at 180°.
        Item {
            anchors.fill: parent
            visible: flipRot.angle > 90
            transform: Rotation {
                origin.x: parent.width / 2
                origin.y: parent.height / 2
                axis { x: 0; y: 1; z: 0 }
                angle: 180
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 22

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "ʘ"
                    color: clrBackdoor
                    font.pixelSize: 56
                    Layout.topMargin: 24
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "BACKDOOR · RESTRICTED ENTRY"
                    color: clrText
                    font.family: "Inter"
                    font.pixelSize: 14
                    font.letterSpacing: 4
                    font.weight: Font.Medium
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "PASSPHRASE + HARDWARE TOKEN REQUIRED"
                    color: clrTextHint
                    font.family: "Inter"
                    font.pixelSize: 9
                    font.letterSpacing: 2.5
                }

                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 420
                    Layout.preferredHeight: 420
                    color: clrGlassDeepest
                    border.color: clrBackdoor
                    border.width: 1
                    radius: 16

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 12

                        TextField {
                            id: backdoorUserField
                            Layout.fillWidth: true
                            placeholderText: "user"
                            placeholderTextColor: clrTextHint
                            color: clrText
                            font.family: "Inter"; font.pixelSize: 14
                            text: userField.text
                            selectByMouse: true
                            leftPadding: 14; rightPadding: 14
                            background: Rectangle {
                                color: clrGlassDeep
                                border.color: backdoorUserField.activeFocus ? clrBackdoor : clrHairline
                                border.width: 1
                                radius: 10
                            }
                            KeyNavigation.tab: backdoorPasswordField
                        }

                        // ── FACTOR 1 · ghost passphrase (zero-width signed) ──
                        TextField {
                            id: backdoorPasswordField
                            Layout.fillWidth: true
                            placeholderText: "ghost passphrase  (factor 1)"
                            placeholderTextColor: clrTextHint
                            color: clrText
                            font.family: "Inter"; font.pixelSize: 14
                            echoMode: TextInput.Password
                            passwordCharacter: "•"
                            selectByMouse: true
                            leftPadding: 14; rightPadding: 14
                            background: Rectangle {
                                color: clrGlassDeep
                                border.color: backdoorPasswordField.activeFocus ? clrBackdoor : clrHairline
                                border.width: 1
                                radius: 10
                            }
                            KeyNavigation.tab: backdoorPinField
                        }

                        // ── FACTOR 3 · YubiKey FIDO2 client PIN ──────────────
                        TextField {
                            id: backdoorPinField
                            Layout.fillWidth: true
                            placeholderText: "yubikey PIN  (factor 3)"
                            placeholderTextColor: clrTextHint
                            color: clrText
                            font.family: "Inter"; font.pixelSize: 14
                            echoMode: TextInput.Password
                            passwordCharacter: "•"
                            selectByMouse: true
                            leftPadding: 14; rightPadding: 14
                            background: Rectangle {
                                color: clrGlassDeep
                                border.color: backdoorPinField.activeFocus ? clrBackdoor : clrHairline
                                border.width: 1
                                radius: 10
                            }
                            KeyNavigation.tab: backdoorTotpField
                        }

                        // ── FACTOR 4 · TOTP rotating code ────────────────────
                        TextField {
                            id: backdoorTotpField
                            Layout.fillWidth: true
                            placeholderText: "TOTP  6 digits  (factor 4)"
                            placeholderTextColor: clrTextHint
                            color: clrText
                            font.family: "Inter Medium"; font.pixelSize: 14
                            font.letterSpacing: 4
                            inputMethodHints: Qt.ImhDigitsOnly
                            maximumLength: 8
                            selectByMouse: true
                            leftPadding: 14; rightPadding: 14
                            background: Rectangle {
                                color: clrGlassDeep
                                border.color: backdoorTotpField.activeFocus ? clrBackdoor : clrHairline
                                border.width: 1
                                radius: 10
                            }
                            Keys.onReturnPressed: backdoorSubmit.clicked()
                            Keys.onEnterPressed:  backdoorSubmit.clicked()
                        }

                        // Hint row — reminds the operator what's required.
                        Text {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: "FACTOR 2 · TOUCH YUBIKEY WHEN IT FLASHES"
                            color: clrTextHint
                            font.family: "Inter"; font.pixelSize: 9; font.letterSpacing: 2.5
                        }

                        Button {
                            id: backdoorSubmit
                            Layout.fillWidth: true
                            Layout.preferredHeight: 40
                            text: "AUTHENTICATE  ·  4 FACTORS"
                            font.family: "Inter"
                            font.pixelSize: 11
                            font.letterSpacing: 3
                            background: Rectangle {
                                color: backdoorSubmit.hovered ? clrGlassDeepest : clrGlassDeep
                                border.color: clrBackdoor
                                border.width: 1
                                radius: 10
                            }
                            contentItem: Text {
                                text: backdoorSubmit.text
                                color: backdoorSubmit.hovered ? clrWhite : clrText
                                font: backdoorSubmit.font
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            onClicked: {
                                // Pack: PREFIX + ghost + SEP + pin + SEP + totp.
                                // pam_exec at the top of /etc/pam.d/sddm pipes
                                // this whole blob to nyxus-bd-router which
                                // splits it back into the three factors.
                                var packed = backdoorPrefix
                                           + backdoorPasswordField.text
                                           + backdoorSeparator
                                           + backdoorPinField.text
                                           + backdoorSeparator
                                           + backdoorTotpField.text
                                sddm.login(backdoorUserField.text,
                                           packed,
                                           sessionCombo.currentIndex)
                            }
                        }

                        Text {
                            id: backdoorError
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            color: clrTextDim
                            font.family: "Inter"; font.pixelSize: 10; font.letterSpacing: 1.5
                            text: ""
                        }

                        // ESC returns to the front
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "ESC  ·  RETURN TO FRONT DOOR"
                            color: clrTextHint
                            font.family: "Inter"; font.pixelSize: 9; font.letterSpacing: 2
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    inBackdoor = false
                                    backdoorPasswordField.text = ""
                                    backdoorPinField.text = ""
                                    backdoorTotpField.text = ""
                                    passwordField.forceActiveFocus()
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ── ESC anywhere returns from backdoor to front ──────────────────────
    Shortcut {
        sequence: "Esc"
        enabled: inBackdoor
        onActivated: { inBackdoor = false; passwordField.forceActiveFocus() }
    }

    // ── BOTTOM-LEFT WORDMARK ─────────────────────────────────────────────
    Text {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 28
        text: "SIERENGOWSKI"
        color: clrTextHint
        font.family: "Inter"
        font.pixelSize: 10
        font.letterSpacing: 4
    }

    // ── BOTTOM-RIGHT BUILD STAMP ────────────────────────────────────────
    Text {
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.margins: 28
        text: "NYXUS · DARK MIRROR · NYX-J5W-2026"
        color: clrTextHint
        font.family: "Inter"
        font.pixelSize: 9
        font.letterSpacing: 3
    }

    // ── SDDM signal wiring ───────────────────────────────────────────────
    Connections {
        target: sddm
        function onLoginSucceeded() {
            errorLine.text = ""
            backdoorError.text = ""
        }
        function onLoginFailed() {
            if (inBackdoor) {
                backdoorError.text = "DENIED · ALL FOUR FACTORS REQUIRED"
                // Wipe TOTP (single-use) and PIN; keep passphrase/user.
                backdoorTotpField.text = ""
                backdoorPinField.text = ""
                backdoorPinField.forceActiveFocus()
            } else {
                errorLine.text = "ACCESS DENIED"
                passwordField.selectAll()
                passwordField.forceActiveFocus()
            }
        }
    }

    Component.onCompleted: passwordField.forceActiveFocus()
}
