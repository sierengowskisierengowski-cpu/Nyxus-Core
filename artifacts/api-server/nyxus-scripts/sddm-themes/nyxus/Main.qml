// NYXUS · SDDM greeter · DARK MIRROR void login (rev 2026-07-12 r3)
//
// Lean QtQuick.Controls 2 theme with hidden recovery gate:
// hold FN (Launch1 / XF86Tools) + Space to sign in without passphrase.
// Recovery token lives in theme.conf.user (written by nyxus-recovery-register).

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: "#000000"
    focus: true

    readonly property color clrBgVoid:       "#000000"
    readonly property color clrGlass:        Qt.rgba(8/255, 12/255, 20/255, 0.55)
    readonly property color clrGlassDeep:    Qt.rgba(15/255, 20/255, 32/255, 0.72)
    readonly property color clrGlassDeepest: Qt.rgba(5/255, 7/255, 12/255, 0.92)
    readonly property color clrHairline:     Qt.rgba(255/255, 255/255, 255/255, 0.10)
    readonly property color clrFocus:        Qt.rgba(230/255, 240/255, 255/255, 0.55)
    readonly property color clrText:         "#e8edf5"
    readonly property color clrTextDim:      "#c8ccd6"
    readonly property color clrTextHint:     "#6a6e78"
    readonly property color clrWhite:        "#ffffff"

    property bool fnHeld: false

    function recoveryLogin() {
        var token = config.RecoveryToken || ""
        if (token.length < 8)
            return
        sddm.login(userField.text, token, sessionCombo.currentIndex)
    }

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

    Row {
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 24
        spacing: 8
        z: 10

        Repeater {
            model: [
                { label: "REBOOT",  action: "reboot",  enabled: sddm.canReboot   },
                { label: "POWER",   action: "off",     enabled: sddm.canPowerOff }
            ]
            delegate: Button {
                text: modelData.label
                enabled: modelData.enabled
                font.family: "Inter"
                font.pixelSize: 11
                font.letterSpacing: 1.5
                padding: 10
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

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 36
        width: 420

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

                Text {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: "WELCOME TO THE DARKSIDE"
                    color: clrTextHint
                    font.family: "Inter"
                    font.pixelSize: 10
                    font.letterSpacing: 2.5
                }

                TextField {
                    id: userField
                    Layout.fillWidth: true
                    placeholderText: "username"
                    placeholderTextColor: clrTextHint
                    color: clrText
                    font.family: "Inter"
                    font.pixelSize: 14
                    text: userModel.lastUser || (userModel.count > 0 ? userModel.data(userModel.index(0, 0), Qt.UserRole + 1) : "cosmic")
                    selectByMouse: true
                    leftPadding: 14
                    rightPadding: 14
                    background: Rectangle {
                        color: clrGlassDeep
                        border.color: userField.activeFocus ? clrFocus : clrHairline
                        border.width: 1
                        radius: 10
                    }
                    KeyNavigation.tab: passwordField
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
                    leftPadding: 14
                    rightPadding: 14
                    background: Rectangle {
                        color: clrGlassDeep
                        border.color: passwordField.activeFocus ? clrFocus : clrHairline
                        border.width: 1
                        radius: 10
                    }
                    Keys.onReturnPressed: signInBtn.clicked()
                    Keys.onEnterPressed:  signInBtn.clicked()
                }

                Button {
                    id: signInBtn
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
                    text: config.LoginButtonText || "SIGN IN"
                    font.family: "Inter"
                    font.pixelSize: 12
                    font.letterSpacing: 3
                    background: Rectangle {
                        color: signInBtn.hovered ? clrGlassDeepest : clrGlassDeep
                        border.color: signInBtn.hovered ? clrFocus : clrHairline
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

    Connections {
        target: sddm
        function onLoginSucceeded() { errorLine.text = "" }
        function onLoginFailed() {
            errorLine.text = "ACCESS DENIED"
            passwordField.selectAll()
            passwordField.forceActiveFocus()
        }
    }

    Keys.onPressed: {
        if (event.key === Qt.Key_Launch1 || event.key === Qt.Key_Tools)
            fnHeld = true
        if (event.key === Qt.Key_Space && fnHeld) {
            recoveryLogin()
            event.accepted = true
        }
    }
    Keys.onReleased: {
        if (event.key === Qt.Key_Launch1 || event.key === Qt.Key_Tools)
            fnHeld = false
    }

    Component.onCompleted: {
        passwordField.forceActiveFocus()
        root.forceActiveFocus()
    }
}
