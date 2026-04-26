import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.15
import SddmComponents 2.0

Item {
    id: root
    width: Screen.width
    height: Screen.height

    // ── Palette ─────────────────────────────────────────────────────────────
    readonly property color clrPurple:  "#c084fc"
    readonly property color clrRed:     "#f87171"
    readonly property color clrGreen:   "#34d399"
    readonly property color clrOrange:  "#fb923c"
    readonly property color clrBlack:   "#000000"
    readonly property color clrGlass:   Qt.rgba(0, 0, 0, 0.72)
    readonly property color clrBorder:  Qt.rgba(192, 132, 252, 0.55)
    readonly property color clrBorderHi:Qt.rgba(192, 132, 252, 1.0)
    readonly property string monoFont:  "JetBrains Mono, Fira Code, Cascadia Code, Monospace"

    // ── State ────────────────────────────────────────────────────────────────
    property bool authBusy:    false
    property bool authFailed:  false
    property string authMsg:   ""
    property real  revealProgress: 0.0

    // ── Connections ──────────────────────────────────────────────────────────
    Connections {
        target: sddm
        function onLoginSucceeded() {
            authBusy   = false
            authFailed = false
            authMsg    = "// ACCESS GRANTED"
            glowPulse.stop()
        }
        function onLoginFailed() {
            authBusy   = false
            authFailed = true
            authMsg    = "// AUTHENTICATION FAILED — RETRY"
            shakeAnim.restart()
            glowPulse.stop()
            failFlash.restart()
        }
    }

    // ── Boot reveal animation ─────────────────────────────────────────────────
    SequentialAnimation {
        id: bootReveal
        running: true
        NumberAnimation { target: root; property: "revealProgress"; from: 0; to: 1; duration: 1400; easing.type: Easing.OutCubic }
    }

    // ── Background: wallpaper ────────────────────────────────────────────────
    Image {
        id: wallpaper
        anchors.fill: parent
        source:       "background.png"
        fillMode:     Image.PreserveAspectCrop
        smooth:       true
        asynchronous: true
    }

    // Desaturate overlay so the glass panel pops
    FastBlur {
        anchors.fill: wallpaper
        source:       wallpaper
        radius:       2
        opacity:      0.15
    }

    // Dark gradient overlay
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: Qt.rgba(0,0,0,0.55) }
            GradientStop { position: 0.5; color: Qt.rgba(0,0,0,0.30) }
            GradientStop { position: 1.0; color: Qt.rgba(0,0,0,0.70) }
        }
    }

    // ── Hex-grid canvas overlay ──────────────────────────────────────────────
    Canvas {
        id: hexCanvas
        anchors.fill: parent
        opacity: 0.07

        property real pulse: 0.0
        NumberAnimation on pulse {
            from: 0; to: Math.PI * 2
            duration: 6000
            loops: Animation.Infinite
            running: true
        }
        onPulseChanged: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            var size = 38
            var h    = size * Math.sqrt(3)
            var cols = Math.ceil(width  / (size * 1.5)) + 2
            var rows = Math.ceil(height / h) + 2
            ctx.strokeStyle = "#c084fc"
            ctx.lineWidth   = 0.8
            for (var col = -1; col < cols; col++) {
                for (var row = -1; row < rows; row++) {
                    var x = col * size * 1.5
                    var y = row * h + (col % 2 === 0 ? 0 : h / 2)
                    var dist = Math.sqrt(Math.pow((x - width/2)/width, 2) + Math.pow((y - height/2)/height, 2))
                    var alpha = 0.3 + 0.7 * Math.max(0, Math.sin(pulse - dist * 4))
                    ctx.globalAlpha = alpha
                    ctx.beginPath()
                    for (var i = 0; i < 6; i++) {
                        var angle = Math.PI / 180 * (60 * i - 30)
                        var px = x + size * Math.cos(angle)
                        var py = y + size * Math.sin(angle)
                        if (i === 0) ctx.moveTo(px, py)
                        else         ctx.lineTo(px, py)
                    }
                    ctx.closePath()
                    ctx.stroke()
                }
            }
            ctx.globalAlpha = 1.0
        }
    }

    // ── Scanline overlay ─────────────────────────────────────────────────────
    Canvas {
        anchors.fill: parent
        opacity: 0.06
        onPaint: {
            var ctx = getContext("2d")
            ctx.fillStyle = "#000000"
            for (var y = 0; y < height; y += 4) {
                ctx.fillRect(0, y, width, 2)
            }
        }
    }

    // ── Clock (top-right) ────────────────────────────────────────────────────
    Item {
        id: clockBlock
        anchors { top: parent.top; right: parent.right; margins: 36 }
        width:  260
        height: 72
        opacity: root.revealProgress

        property var now: new Date()
        Timer {
            interval: 1000; running: true; repeat: true
            onTriggered: clockBlock.now = new Date()
        }

        Column {
            anchors.right: parent.right
            spacing: 4

            Text {
                anchors.right: parent.right
                text: Qt.formatDateTime(clockBlock.now, "HH:mm:ss")
                font { family: root.monoFont; pixelSize: 28; weight: Font.Light }
                color: root.clrPurple
                style: Text.Outline; styleColor: Qt.rgba(192,132,252,0.18)
            }
            Text {
                anchors.right: parent.right
                text: Qt.formatDateTime(clockBlock.now, "ddd  yyyy-MM-dd")
                font { family: root.monoFont; pixelSize: 12 }
                color: Qt.rgba(192,132,252,0.65)
                letterSpacing: 2
            }
        }
    }

    // ── NYXUS wordmark (top-left) ────────────────────────────────────────────
    Item {
        anchors { top: parent.top; left: parent.left; margins: 36 }
        opacity: root.revealProgress
        width: 320; height: 72

        Column {
            spacing: 4
            Text {
                text: "NYX<font color='#f87171'>US</font>"
                font { family: root.monoFont; pixelSize: 32; weight: Font.Bold }
                color: root.clrPurple
                textFormat: Text.RichText
            }
            Text {
                text: "SILENT  ·  DARK  ·  PURELY FUNCTIONAL"
                font { family: root.monoFont; pixelSize: 10 }
                color: Qt.rgba(192,132,252,0.5)
                letterSpacing: 3
            }
        }
    }

    // ── Hostname / kernel (bottom-left) ──────────────────────────────────────
    Item {
        anchors { bottom: parent.bottom; left: parent.left; margins: 28 }
        opacity: root.revealProgress * 0.7

        Column {
            spacing: 3
            Text {
                text: "KERNEL " + sddm.hostName.toUpperCase()
                font { family: root.monoFont; pixelSize: 11 }
                color: Qt.rgba(52,211,153,0.7)
                letterSpacing: 2
            }
            Text {
                text: "NYX-J5W-2026-SIERENGOWSKI-LOCKED"
                font { family: root.monoFont; pixelSize: 10 }
                color: Qt.rgba(192,132,252,0.4)
                letterSpacing: 1
            }
        }
    }

    // ── Copyright (bottom-right) ─────────────────────────────────────────────
    Text {
        anchors { bottom: parent.bottom; right: parent.right; margins: 28 }
        text: "© 2026 JOSEPH SIERENGOWSKI"
        font { family: root.monoFont; pixelSize: 10 }
        color: Qt.rgba(192,132,252,0.38)
        letterSpacing: 2
        opacity: root.revealProgress
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // ── MAIN LOGIN PANEL ──────────────────────────────────────────────────────
    // ═══════════════════════════════════════════════════════════════════════════
    Item {
        id: loginPanel
        anchors.centerIn: parent
        width:  420
        height: panelCol.implicitHeight + 56
        opacity: root.revealProgress

        // Shake animation on failed auth
        SequentialAnimation {
            id: shakeAnim
            NumberAnimation { target: loginPanel; property: "x"; to: loginPanel.x - 12; duration: 50 }
            NumberAnimation { target: loginPanel; property: "x"; to: loginPanel.x + 12; duration: 50 }
            NumberAnimation { target: loginPanel; property: "x"; to: loginPanel.x - 8;  duration: 45 }
            NumberAnimation { target: loginPanel; property: "x"; to: loginPanel.x + 8;  duration: 45 }
            NumberAnimation { target: loginPanel; property: "x"; to: loginPanel.x;       duration: 40 }
        }

        // Glass background
        Rectangle {
            anchors.fill: parent
            color:  root.clrGlass
            radius: 2

            // Backdrop blur via layer
            layer.enabled: true
            layer.effect: FastBlur { radius: 32 }
        }

        // Border — purple neon, animated glow
        Rectangle {
            id: panelBorder
            anchors.fill: parent
            color:        "transparent"
            radius:       2
            border.width: 1
            border.color: root.clrBorder

            // Glow pulse on idle
            SequentialAnimation {
                id: glowPulse
                running: !root.authBusy && !root.authFailed
                loops: Animation.Infinite
                NumberAnimation { target: panelBorder; property: "border.width"; to: 1.5; duration: 1800; easing.type: Easing.InOutSine }
                NumberAnimation { target: panelBorder; property: "border.width"; to: 0.8; duration: 1800; easing.type: Easing.InOutSine }
            }

            // Red flash on fail
            SequentialAnimation {
                id: failFlash
                NumberAnimation { target: panelBorder; property: "border.color"; to: root.clrRed;    duration: 80  }
                NumberAnimation { target: panelBorder; property: "border.color"; to: "transparent";  duration: 80  }
                NumberAnimation { target: panelBorder; property: "border.color"; to: root.clrRed;    duration: 80  }
                NumberAnimation { target: panelBorder; property: "border.color"; to: root.clrBorder; duration: 500 }
            }
        }

        // Neon top-edge accent line
        Rectangle {
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0;  color: "transparent"       }
                GradientStop { position: 0.25; color: root.clrPurple      }
                GradientStop { position: 0.75; color: root.clrPurple      }
                GradientStop { position: 1.0;  color: "transparent"       }
            }
            opacity: 0.85
        }

        // Drawing border animation (traces the top-left corner on load)
        Canvas {
            id: drawBorder
            anchors.fill: parent
            property real progress: 0.0
            NumberAnimation on progress { from: 0; to: 1; duration: 900; easing.type: Easing.OutCubic; running: true }
            onProgressChanged: requestPaint()
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                var p = progress
                var w = width; var h = height
                var perimeter = 2 * (w + h)
                var traveled  = p * perimeter
                ctx.strokeStyle = "#c084fc"
                ctx.lineWidth   = 2
                ctx.shadowBlur  = 12
                ctx.shadowColor = "#c084fc"
                ctx.beginPath()
                // Trace: top → right → bottom → left
                if (traveled <= w) {
                    ctx.moveTo(0, 0); ctx.lineTo(traveled, 0)
                } else if (traveled <= w + h) {
                    ctx.moveTo(0, 0); ctx.lineTo(w, 0); ctx.lineTo(w, traveled - w)
                } else if (traveled <= 2*w + h) {
                    ctx.moveTo(0, 0); ctx.lineTo(w, 0); ctx.lineTo(w, h); ctx.lineTo(w - (traveled - w - h), h)
                } else {
                    ctx.moveTo(0, 0); ctx.lineTo(w, 0); ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.lineTo(0, h - (traveled - 2*w - h))
                }
                ctx.stroke()
            }
        }

        // Panel title bar
        Rectangle {
            id: titleBar
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height:  38
            color:   Qt.rgba(192, 132, 252, 0.08)

            Row {
                anchors { left: parent.left; verticalCenter: parent.verticalCenter; leftMargin: 16 }
                spacing: 8
                // Traffic-light style dots
                Repeater {
                    model: [root.clrRed, root.clrOrange, root.clrGreen]
                    Rectangle {
                        width: 8; height: 8; radius: 4
                        color: modelData
                        opacity: 0.7
                    }
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "  NYXUS · SECURE SESSION INIT"
                    font { family: root.monoFont; pixelSize: 11 }
                    color: Qt.rgba(192,132,252,0.7)
                    letterSpacing: 2
                }
            }
        }

        // ── Form content ───────────────────────────────────────────────────
        Column {
            id: panelCol
            anchors { top: titleBar.bottom; left: parent.left; right: parent.right }
            anchors.topMargin: 24
            anchors.leftMargin: 28
            anchors.rightMargin: 28
            spacing: 0

            // Boot log lines (decorative terminal output)
            Column {
                width: parent.width
                spacing: 2
                bottomPadding: 18

                Repeater {
                    model: [
                        { t: "[  0.001]", msg: "Initializing NYXUS security kernel...",   c: "#34d399" },
                        { t: "[  0.043]", msg: "Loading encrypted session modules...",     c: "#34d399" },
                        { t: "[  0.112]", msg: "Establishing secure handshake...",         c: "#c084fc" },
                        { t: "[  0.198]", msg: "Awaiting operator credentials.",           c: "#fb923c" },
                    ]
                    delegate: Row {
                        spacing: 8
                        opacity: root.revealProgress > (index * 0.25) ? 1 : 0
                        Behavior on opacity { NumberAnimation { duration: 300 } }
                        Text {
                            text: modelData.t
                            font { family: root.monoFont; pixelSize: 10 }
                            color: Qt.rgba(192,132,252,0.38)
                        }
                        Text {
                            text: modelData.msg
                            font { family: root.monoFont; pixelSize: 10 }
                            color: modelData.c
                            opacity: 0.75
                        }
                    }
                }
            }

            // Divider
            Rectangle {
                width: parent.width; height: 1
                color: Qt.rgba(192,132,252,0.15)
                bottomPadding: 0
            }
            Item { width: 1; height: 20 }

            // ── User select ──────────────────────────────────────────────
            Text {
                text: "OPERATOR ID"
                font { family: root.monoFont; pixelSize: 10 }
                color: Qt.rgba(192,132,252,0.55)
                letterSpacing: 3
                bottomPadding: 6
            }
            Item { width: 1; height: 6 }

            Rectangle {
                id: userBox
                width:  parent.width
                height: 40
                color:  Qt.rgba(192,132,252,0.06)
                border.color: userCombo.focus ? root.clrPurple : Qt.rgba(192,132,252,0.28)
                border.width: 1
                radius: 1

                ComboBox {
                    id: userCombo
                    anchors.fill: parent
                    anchors.margins: 1
                    model: userModel
                    textRole: "name"
                    currentIndex: userModel.lastIndex

                    background: Rectangle { color: "transparent" }

                    contentItem: Text {
                        leftPadding: 12
                        text: userCombo.displayText
                        font { family: root.monoFont; pixelSize: 13 }
                        color: root.clrPurple
                        verticalAlignment: Text.AlignVCenter
                    }

                    delegate: ItemDelegate {
                        width:  userCombo.width
                        background: Rectangle {
                            color: highlighted ? Qt.rgba(192,132,252,0.18) : Qt.rgba(0,0,0,0.85)
                        }
                        contentItem: Text {
                            text: model.name
                            font { family: root.monoFont; pixelSize: 12 }
                            color: root.clrPurple
                            leftPadding: 12
                        }
                    }

                    indicator: Text {
                        anchors { right: parent.right; verticalCenter: parent.verticalCenter; rightMargin: 12 }
                        text: "▾"
                        font.pixelSize: 14
                        color: Qt.rgba(192,132,252,0.55)
                    }

                    popup: Popup {
                        y: userCombo.height
                        width: userCombo.width
                        padding: 0
                        background: Rectangle { color: Qt.rgba(0,0,0,0.92); border.color: root.clrBorder; border.width: 1 }
                        contentItem: ListView {
                            implicitHeight: contentHeight
                            model: userCombo.delegateModel
                            clip: true
                        }
                    }
                }
            }

            Item { width: 1; height: 20 }

            // ── Password field ───────────────────────────────────────────
            Text {
                text: "PASSPHRASE"
                font { family: root.monoFont; pixelSize: 10 }
                color: Qt.rgba(192,132,252,0.55)
                letterSpacing: 3
            }
            Item { width: 1; height: 6 }

            Rectangle {
                id: pwBox
                width:  parent.width
                height: 40
                color:  pwField.activeFocus ? Qt.rgba(192,132,252,0.09) : Qt.rgba(192,132,252,0.04)
                radius: 1
                border.width: pwField.activeFocus ? 1 : 1
                border.color: {
                    if (root.authFailed)           return root.clrRed
                    if (pwField.activeFocus)       return root.clrPurple
                    return Qt.rgba(192,132,252,0.28)
                }

                Behavior on border.color { ColorAnimation { duration: 180 } }
                Behavior on color        { ColorAnimation { duration: 180 } }

                // Neon left-edge bar when focused
                Rectangle {
                    anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                    width:  2
                    radius: 1
                    color:  pwField.activeFocus ? root.clrPurple : "transparent"
                    Behavior on color { ColorAnimation { duration: 200 } }
                }

                // Glow effect when focused
                layer.enabled: pwField.activeFocus
                layer.effect: Glow {
                    radius:    8
                    samples:   12
                    color:     "#c084fc"
                    spread:    0.1
                    cached:    true
                }

                TextInput {
                    id: pwField
                    anchors { fill: parent; leftMargin: 12; rightMargin: 12 }
                    verticalAlignment: TextInput.AlignVCenter
                    echoMode: TextInput.Password
                    passwordCharacter: "█"
                    font { family: root.monoFont; pixelSize: 15; letterSpacing: 4 }
                    color: root.clrPurple
                    selectionColor: Qt.rgba(192,132,252,0.35)
                    focus: true
                    enabled: !root.authBusy

                    Keys.onReturnPressed: doLogin()
                    Keys.onEnterPressed:  doLogin()

                    Text {
                        anchors { fill: parent; leftMargin: 0 }
                        verticalAlignment: Text.AlignVCenter
                        text: "enter passphrase..."
                        font { family: root.monoFont; pixelSize: 13; italic: true }
                        color: Qt.rgba(192,132,252,0.3)
                        visible: pwField.text.length === 0 && !pwField.activeFocus
                    }
                }
            }

            Item { width: 1; height: 8 }

            // Caps lock warning
            Text {
                width: parent.width
                text: "⚠  CAPS LOCK ACTIVE"
                font { family: root.monoFont; pixelSize: 10 }
                color: root.clrOrange
                visible: keyboard.capsLock
                horizontalAlignment: Text.AlignHCenter
                topPadding: 4
            }

            // Auth status message
            Text {
                id: statusMsg
                width: parent.width
                text: root.authFailed ? root.authMsg : (root.authBusy ? "// AUTHENTICATING..." : "")
                font { family: root.monoFont; pixelSize: 10 }
                color: root.authFailed ? root.clrRed : root.clrGreen
                horizontalAlignment: Text.AlignHCenter
                topPadding: 6
                visible: text.length > 0
                Behavior on color { ColorAnimation { duration: 200 } }
            }

            Item { width: 1; height: 18 }

            // ── Primary action button ────────────────────────────────────
            Rectangle {
                id: loginBtn
                width:  parent.width
                height: 42
                radius: 1
                color: loginMouse.containsMouse
                       ? Qt.rgba(192,132,252,0.22)
                       : Qt.rgba(192,132,252,0.10)
                border.color: loginMouse.containsMouse ? root.clrPurple : root.clrBorder
                border.width: 1
                enabled: !root.authBusy

                Behavior on color        { ColorAnimation { duration: 120 } }
                Behavior on border.color { ColorAnimation { duration: 120 } }

                // Horizontal sweep highlight on hover
                Rectangle {
                    anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                    width: parent.width * (loginMouse.containsMouse ? 1 : 0)
                    color: Qt.rgba(192,132,252,0.07)
                    Behavior on width { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }
                }

                Text {
                    anchors.centerIn: parent
                    text: root.authBusy ? "AUTHENTICATING  ···" : "AUTHENTICATE  →"
                    font { family: root.monoFont; pixelSize: 12; weight: Font.Medium }
                    color: root.clrPurple
                    letterSpacing: 3

                    SequentialAnimation on opacity {
                        running: root.authBusy
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.3; duration: 500 }
                        NumberAnimation { to: 1.0; duration: 500 }
                    }
                }

                MouseArea {
                    id: loginMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: doLogin()
                }
            }

            Item { width: 1; height: 16 }

            // ── Session + power row ───────────────────────────────────────
            Row {
                width: parent.width
                spacing: 8

                // Session selector (compact)
                Rectangle {
                    width:  (parent.width - 16) * 0.6
                    height: 32
                    color:  Qt.rgba(192,132,252,0.05)
                    border.color: Qt.rgba(192,132,252,0.22)
                    border.width: 1
                    radius: 1

                    ComboBox {
                        id: sessionCombo
                        anchors.fill: parent
                        anchors.margins: 1
                        model: sessionModel
                        textRole: "name"

                        background: Rectangle { color: "transparent" }
                        contentItem: Text {
                            leftPadding: 10
                            text: sessionCombo.displayText
                            font { family: root.monoFont; pixelSize: 10 }
                            color: Qt.rgba(192,132,252,0.7)
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        indicator: Text {
                            anchors { right: parent.right; verticalCenter: parent.verticalCenter; rightMargin: 8 }
                            text: "▾"; font.pixelSize: 10
                            color: Qt.rgba(192,132,252,0.45)
                        }
                        delegate: ItemDelegate {
                            width: sessionCombo.width
                            background: Rectangle { color: highlighted ? Qt.rgba(192,132,252,0.18) : Qt.rgba(0,0,0,0.92) }
                            contentItem: Text {
                                text: model.name
                                font { family: root.monoFont; pixelSize: 10 }
                                color: Qt.rgba(192,132,252,0.8)
                                leftPadding: 10
                            }
                        }
                        popup: Popup {
                            y: sessionCombo.height; width: sessionCombo.width; padding: 0
                            background: Rectangle { color: Qt.rgba(0,0,0,0.92); border.color: root.clrBorder; border.width: 1 }
                            contentItem: ListView { implicitHeight: contentHeight; model: sessionCombo.delegateModel; clip: true }
                        }
                    }
                }

                // Reboot button
                Rectangle {
                    width:  (parent.width - 16) * 0.2
                    height: 32
                    color:  rebootMouse.containsMouse ? Qt.rgba(251,146,60,0.18) : Qt.rgba(251,146,60,0.07)
                    border.color: rebootMouse.containsMouse ? root.clrOrange : Qt.rgba(251,146,60,0.3)
                    border.width: 1; radius: 1
                    Behavior on color        { ColorAnimation { duration: 120 } }
                    Behavior on border.color { ColorAnimation { duration: 120 } }
                    Text {
                        anchors.centerIn: parent
                        text: "↻"
                        font.pixelSize: 16
                        color: Qt.rgba(251,146,60,0.85)
                    }
                    MouseArea {
                        id: rebootMouse; anchors.fill: parent
                        hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: sddm.reboot()
                    }
                }

                // Shutdown button
                Rectangle {
                    width:  (parent.width - 16) * 0.2
                    height: 32
                    color:  shutMouse.containsMouse ? Qt.rgba(248,113,113,0.18) : Qt.rgba(248,113,113,0.07)
                    border.color: shutMouse.containsMouse ? root.clrRed : Qt.rgba(248,113,113,0.3)
                    border.width: 1; radius: 1
                    Behavior on color        { ColorAnimation { duration: 120 } }
                    Behavior on border.color { ColorAnimation { duration: 120 } }
                    Text {
                        anchors.centerIn: parent
                        text: "⏻"
                        font.pixelSize: 15
                        color: Qt.rgba(248,113,113,0.85)
                    }
                    MouseArea {
                        id: shutMouse; anchors.fill: parent
                        hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: sddm.powerOff()
                    }
                }
            }

            Item { width: 1; height: 28 }
        } // Column
    } // loginPanel

    // ── Login function ───────────────────────────────────────────────────────
    function doLogin() {
        if (root.authBusy) return
        root.authBusy   = true
        root.authFailed = false
        root.authMsg    = ""
        glowPulse.stop()
        sddm.login(userCombo.currentText, pwField.text, sessionCombo.currentIndex)
    }

} // root
