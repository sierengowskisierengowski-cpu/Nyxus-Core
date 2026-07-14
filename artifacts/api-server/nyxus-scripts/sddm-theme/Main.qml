// ============================================================
//  NYXUS — SDDM greeter · "Void Sign-In" (rev 2026-07-14 · from-scratch rebuild)
//
//  Design goals for this rebuild:
//   - RELIABLE RENDER FIRST. Pure QtQuick only — no QtQuick.Controls,
//     no SddmComponents. This avoids the qt5/qt6 quickcontrols2 split
//     (qt6-quickcontrols2 is not always present) and the QQC1 `Button`
//     shadowing bug that broke earlier themes. Nothing here needs a
//     control that isn't in base QtQuick.
//   - The blank-screen-on-boot failure was NOT this theme — it was the
//     greeter crashing in hardware GL on hybrid Intel+NVIDIA. The
//     deploy script sets QT_QUICK_BACKEND=software so the scene renders
//     via llvmpipe. This theme is written to also be cheap to render in
//     software (no blur, no shaders, no heavy effects).
//   - Nyxus palette (deep void black + purple #7949F2 + magenta #FF2667).
//     Rough palette match only — full theme polish is Phase 5.
//
//  Both Hyprland and COSMIC (and any other /usr/share/wayland-sessions
//  entry) are listed as selectable session pills, sourced from SDDM's
//  sessionModel.
//
//  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
// ============================================================
import QtQuick 2.15
import QtQuick.Window 2.15

Rectangle {
    id: root
    width: Screen.width
    height: Screen.height
    color: "#04030a"

    // ── palette ──────────────────────────────────────────────
    readonly property color cVoid:     "#04030a"
    readonly property color cCard:     Qt.rgba(10/255, 8/255, 18/255, 0.72)
    readonly property color cCardEdge: Qt.rgba(121/255, 73/255, 242/255, 0.55)
    readonly property color cInput:    Qt.rgba(4/255, 3/255, 10/255, 0.92)
    readonly property color cAccent:   "#7949f2"
    readonly property color cAccent2:  "#ff2667"
    readonly property color cText:     "#e8edf5"
    readonly property color cTextDim:  "#a6abba"
    readonly property color cTextFaint:"#6a6e78"

    property int selectedSession: sessionModel.lastIndex
    property string errorText: ""

    // ── background artwork + void wash ───────────────────────
    Image {
        anchors.fill: parent
        source: config.background || "background.png"
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        onStatusChanged: if (status === Image.Error) visible = false
    }
    Rectangle {  // heavy wash so the login stays legible on any wall
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.62)
    }
    Rectangle {  // subtle purple floor glow (cheap linear gradient)
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(121/255, 73/255, 242/255, 0.00) }
            GradientStop { position: 1.0; color: Qt.rgba(121/255, 73/255, 242/255, 0.14) }
        }
    }

    // ── live clock ───────────────────────────────────────────
    Timer { id: clockTimer; interval: 1000; running: true; repeat: true
        onTriggered: { timeLabel.text = Qt.formatDateTime(new Date(), "HH:mm");
                       dateLabel.text = Qt.formatDateTime(new Date(), "dddd · MMMM d").toUpperCase() } }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: root.height * 0.10
        spacing: 4
        Text { id: timeLabel; anchors.horizontalCenter: parent.horizontalCenter
            text: Qt.formatDateTime(new Date(), "HH:mm")
            color: cText; font.pixelSize: 76; font.family: "Orbitron"; font.letterSpacing: 2 }
        Text { id: dateLabel; anchors.horizontalCenter: parent.horizontalCenter
            text: Qt.formatDateTime(new Date(), "dddd · MMMM d").toUpperCase()
            color: cTextDim; font.pixelSize: 14; font.family: "JetBrainsMono Nerd Font"; font.letterSpacing: 3 }
    }

    // ── login card ───────────────────────────────────────────
    Rectangle {
        id: card
        width: 420
        height: cardCol.height + 56
        radius: 16
        color: cCard
        border.width: 1
        border.color: cCardEdge
        anchors.centerIn: parent

        Rectangle {  // 2px accent top rule
            anchors { top: parent.top; left: parent.left; right: parent.right; topMargin: 0 }
            height: 2; radius: 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: cAccent }
                GradientStop { position: 1.0; color: cAccent2 }
            }
        }

        Column {
            id: cardCol
            anchors.centerIn: parent
            width: parent.width - 56
            spacing: 18

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "NYXUS"
                color: cText; font.pixelSize: 34; font.family: "Permanent Marker"; font.letterSpacing: 2
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "welcome back, operator"
                color: cTextFaint; font.pixelSize: 13; font.family: "Caveat"
            }

            // username
            Rectangle {
                width: parent.width; height: 48; radius: 10
                color: cInput; border.width: 1
                border.color: nameInput.activeFocus ? cAccent : Qt.rgba(1,1,1,0.10)
                TextInput {
                    id: nameInput
                    anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16
                    verticalAlignment: TextInput.AlignVCenter
                    color: cText; font.pixelSize: 15; font.family: "JetBrainsMono Nerd Font"
                    clip: true
                    text: userModel.lastUser
                    onAccepted: passwordInput.forceActiveFocus()
                    Text { anchors.verticalCenter: parent.verticalCenter
                        visible: !nameInput.text && !nameInput.activeFocus
                        text: "username"; color: cTextFaint; font: nameInput.font }
                }
            }

            // password
            Rectangle {
                width: parent.width; height: 48; radius: 10
                color: cInput; border.width: 1
                border.color: passwordInput.activeFocus ? cAccent : Qt.rgba(1,1,1,0.10)
                TextInput {
                    id: passwordInput
                    anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16
                    verticalAlignment: TextInput.AlignVCenter
                    color: cText; font.pixelSize: 15; font.family: "JetBrainsMono Nerd Font"
                    echoMode: TextInput.Password; passwordCharacter: "•"; clip: true
                    onAccepted: root.doLogin()
                    onTextChanged: root.errorText = ""
                    Text { anchors.verticalCenter: parent.verticalCenter
                        visible: !passwordInput.text
                        text: config.PasswordFieldPlaceholderText || "passphrase"
                        color: cTextFaint; font: passwordInput.font }
                }
            }

            // session pills (all wayland/x sessions SDDM found)
            Flow {
                width: parent.width; spacing: 8
                Repeater {
                    model: sessionModel
                    delegate: Rectangle {
                        radius: 8; height: 30
                        width: pillText.width + 24
                        color: index === root.selectedSession ? Qt.rgba(121/255,73/255,242/255,0.28)
                                                              : Qt.rgba(1,1,1,0.05)
                        border.width: 1
                        border.color: index === root.selectedSession ? cAccent : Qt.rgba(1,1,1,0.10)
                        Text { id: pillText; anchors.centerIn: parent
                            text: model.name; color: index === root.selectedSession ? cText : cTextDim
                            font.pixelSize: 12; font.family: "JetBrainsMono Nerd Font" }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.selectedSession = index }
                    }
                }
            }

            // sign-in button
            Rectangle {
                width: parent.width; height: 50; radius: 10
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: signInArea.pressed ? Qt.darker(cAccent,1.2) : cAccent }
                    GradientStop { position: 1.0; color: signInArea.pressed ? Qt.darker(cAccent2,1.2) : cAccent2 }
                }
                Text { anchors.centerIn: parent
                    text: config.LoginButtonText || "SIGN IN"
                    color: "#ffffff"; font.pixelSize: 15; font.bold: true
                    font.family: "JetBrainsMono Nerd Font"; font.letterSpacing: 2 }
                MouseArea { id: signInArea; anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor; onClicked: root.doLogin() }
            }

            // error / caps-lock line
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                height: 14
                text: root.errorText !== "" ? root.errorText
                      : (keyboard.capsLock ? "⇪ CAPS LOCK ON" : "")
                color: root.errorText !== "" ? cAccent2 : cTextFaint
                font.pixelSize: 11; font.family: "JetBrainsMono Nerd Font"; font.letterSpacing: 1
            }
        }
    }

    // ── power controls (top-right) ───────────────────────────
    Row {
        anchors.top: parent.top; anchors.right: parent.right
        anchors.topMargin: 28; anchors.rightMargin: 32; spacing: 22
        Text { text: "⏻ shutdown"; color: cTextDim; font.pixelSize: 13; font.family: "JetBrainsMono Nerd Font"
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                onClicked: sddm.powerOff() } }
        Text { text: "⟳ reboot"; color: cTextDim; font.pixelSize: 13; font.family: "JetBrainsMono Nerd Font"
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                onClicked: sddm.reboot() } }
    }

    Text {  // copyright chrome
        anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 18
        text: "© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED"
        color: cTextFaint; font.pixelSize: 9; font.family: "JetBrainsMono Nerd Font"
    }

    function doLogin() {
        errorText = "";
        sddm.login(nameInput.text, passwordInput.text, selectedSession);
    }

    Connections {
        target: sddm
        function onLoginFailed() { root.errorText = "ACCESS DENIED"; passwordInput.text = ""; passwordInput.forceActiveFocus(); }
        function onLoginSucceeded() { root.errorText = ""; }
    }

    Component.onCompleted: {
        if (nameInput.text === "") nameInput.forceActiveFocus();
        else passwordInput.forceActiveFocus();
    }
}
