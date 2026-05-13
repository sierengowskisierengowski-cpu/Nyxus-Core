/*
 * NYXUS · Calamares branding slideshow              rev 2026-05-13 r2
 *
 * 6-slide installer slideshow. Auto-advances every 8 s while Calamares
 * runs the install steps in the background. Sharp slab edges, DARK
 * MIRROR palette, no blur.
 *
 *  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
 */
import QtQuick 2.15

Item {
    id: root
    width: 800
    height: 460

    readonly property color accent:  "#C084FC"
    readonly property color textHi:  "#E9E5F2"
    readonly property color textLo:  "#7B7390"
    readonly property color hairline:"#1A1722"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0A0712" }
            GradientStop { position: 1.0; color: "#000000" }
        }
    }

    property int currentSlide: 0
    readonly property var slides: [
        {
            title: "Welcome to NYXUS",
            tagline: "DARK MIRROR · 2026.05",
            body:  "A fresh take on Arch Linux: every NYXUS app is\nfirst-party, every config is auditable, every default\nis the one we'd ship to ourselves."
        },
        {
            title: "One Operating System.",
            tagline: "FIFTY APPS. ZERO COMPROMISE.",
            body:  "NYXUS Files, Notes, Stickies, Notepad, Doctor,\nUpdater, Backup, Security, Spotlight, and more —\nshipped, themed, and wired together out of the box."
        },
        {
            title: "Your Computer. Yours.",
            tagline: "NO TELEMETRY · NO ACCOUNTS",
            body:  "Crash reporting and account sync are explicit opt-in.\nNothing leaves the machine unless you said so. Logs\nlive at ~/.cache/nyxus/<app>.log — readable, rotatable."
        },
        {
            title: "Snapshots. Always.",
            tagline: "TIMESHIFT · BTRFS · SNAP-PAC",
            body:  "Every system update auto-snapshots before it runs.\nIf an update breaks something, restore the previous\nstate from NYXUS Backup or `nyxus-doctor --rollback`."
        },
        {
            title: "Hardened Defaults.",
            tagline: "FIREWALLD · APPARMOR · USBGUARD",
            body:  "firewalld is on. AppArmor confines browsers. USBGuard\nlocks unrecognised USB devices on first plug. Auth\nlockout is OFF by design until you turn it on."
        },
        {
            title: "Make it Yours.",
            tagline: "OPEN SETTINGS → BEGIN",
            body:  "Tap Super to launch Spotlight. Open Settings to set\nyour accent, default apps, hot corners, and language.\nWelcome to NYXUS."
        }
    ]

    Timer {
        interval: 8000
        running: true
        repeat: true
        onTriggered: root.currentSlide = (root.currentSlide + 1) % root.slides.length
    }

    // ── Brand mark (top-left) ─────────────────────────────────────────
    Row {
        x: 40; y: 36
        spacing: 14
        Text {
            text: "◤ X ◥"
            color: root.accent
            font.family: "JetBrains Mono"
            font.pixelSize: 32
            font.bold: true
        }
        Column {
            spacing: 0
            Text {
                text: "NYXUS"
                color: root.accent
                font.family: "JetBrains Mono"
                font.pixelSize: 18
                font.letterSpacing: 6
                font.bold: true
            }
            Text {
                text: "DARK MIRROR"
                color: root.textLo
                font.family: "JetBrains Mono"
                font.pixelSize: 9
                font.letterSpacing: 4
            }
        }
    }

    // ── Slide content (centre) ────────────────────────────────────────
    Column {
        anchors.centerIn: parent
        spacing: 16
        width: 640

        Text {
            text: root.slides[root.currentSlide].tagline
            color: root.textLo
            font.family: "JetBrains Mono"
            font.pixelSize: 11
            font.letterSpacing: 6
            anchors.horizontalCenter: parent.horizontalCenter
        }
        Text {
            text: root.slides[root.currentSlide].title
            color: root.textHi
            font.family: "JetBrains Mono"
            font.pixelSize: 32
            font.bold: true
            anchors.horizontalCenter: parent.horizontalCenter
        }
        Rectangle {
            width: 80; height: 1
            color: root.accent
            opacity: 0.6
            anchors.horizontalCenter: parent.horizontalCenter
        }
        Text {
            text: root.slides[root.currentSlide].body
            color: root.textHi
            opacity: 0.85
            font.family: "JetBrains Mono"
            font.pixelSize: 14
            lineHeight: 1.5
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            width: parent.width
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Behavior on opacity { NumberAnimation { duration: 350 } }
    }

    // ── Pagination dots (bottom) ──────────────────────────────────────
    Row {
        spacing: 10
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 36
        anchors.horizontalCenter: parent.horizontalCenter
        Repeater {
            model: root.slides.length
            Rectangle {
                width: index === root.currentSlide ? 28 : 8
                height: 4
                color: index === root.currentSlide ? root.accent : root.hairline
                Behavior on width { NumberAnimation { duration: 300 } }
            }
        }
    }

    // ── Footer rule ───────────────────────────────────────────────────
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: root.hairline
    }
}
