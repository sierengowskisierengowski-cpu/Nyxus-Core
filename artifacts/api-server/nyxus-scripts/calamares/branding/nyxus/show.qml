/*
 * NYXUS · Calamares branding slideshow              rev 2026-05-14 r4
 *
 * Premium 6-slide installer slideshow (Sprint F). Frosted-glass cards on
 * triple-black radial background. CREAM #f4ead5 accent only — NO cyan
 * (rev r15 forbids cyan). Eclipse mark (◐) in brand row, Inter for prose
 * + JBM Nerd for taglines + Caveat for the closing flourish. Real
 * cross-fade between slides + animated pagination dots + breathing glow
 * on the Eclipse mark.
 *
 * Falls back gracefully if Inter/JBM/Caveat are missing — Qt picks the
 * sans-serif/monospace/cursive default in that order.
 *
 *  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
 */
import QtQuick 2.15

Item {
    id: root
    width: 800
    height: 460

    // Rev r15 palette — CREAM only. No purple, no cyan, no red.
    readonly property color accent:    "#f4ead5"
    readonly property color accentDim: "#a89e8a"
    readonly property color textHi:    "#f4ead5"
    readonly property color textBody:  "#cfc6b3"
    readonly property color textLo:    "#6c6452"
    readonly property color glassBg:   "#0c0c10"
    readonly property color glassEdge: "#221f1a"
    readonly property color hairline:  "#1a1916"

    // ── Background: triple-black radial ───────────────────────────────
    Rectangle {
        anchors.fill: parent
        color: "#000000"
    }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#10100c" }
            GradientStop { position: 0.6; color: "#050504" }
            GradientStop { position: 1.0; color: "#000000" }
        }
        opacity: 0.95
    }

    property int currentSlide: 0
    readonly property var slides: [
        {
            tagline: "WELCOME · 2026.05",
            title:   "Welcome to NYXUS",
            body:    "A premium take on Arch Linux: every NYXUS app is\nfirst-party, every config auditable, every default the\none we'd ship to ourselves. You won't believe it's Linux."
        },
        {
            tagline: "FIFTY APPS · ZERO COMPROMISE",
            title:   "One Operating System.",
            body:    "NYXUS Files, Notes, Stickies, Notepad, Doctor,\nUpdater, Backup, Security, Spotlight, and more —\nshipped, themed, and wired together out of the box."
        },
        {
            tagline: "NO TELEMETRY · NO ACCOUNTS",
            title:   "Your Computer. Yours.",
            body:    "Crash reporting and account sync are explicit opt-in.\nNothing leaves the machine unless you said so. Logs\nlive at ~/.cache/nyxus/<app>.log — readable, rotatable."
        },
        {
            tagline: "TIMESHIFT · BTRFS · SNAP-PAC",
            title:   "Snapshots. Always.",
            body:    "Every system update auto-snapshots before it runs.\nIf an update breaks something, restore the previous\nstate from NYXUS Backup or `nyxus-doctor --rollback`."
        },
        {
            tagline: "FIREWALLD · APPARMOR · USBGUARD",
            title:   "Hardened Defaults.",
            body:    "firewalld is on. AppArmor confines browsers. USBGuard\nlocks unrecognised USB on first plug. Auth lockout is\nOFF by design — turn it on after first login."
        },
        {
            tagline: "OPEN SETTINGS · BEGIN",
            title:   "Make it Yours.",
            body:    "Tap Super to launch Spotlight. Open Settings to set\nyour accent, default apps, hot corners, and language.\nWelcome to the Darkside."
        }
    ]

    Timer {
        interval: 8000
        running: true
        repeat: true
        onTriggered: slideContent.opacity = 0.0
    }

    // ── Brand row (top-left) — Eclipse + wordmark ─────────────────────
    Row {
        x: 40; y: 36
        spacing: 14
        Text {
            id: eclipseMark
            text: "◐"
            color: root.accent
            font.family: "Inter"
            font.pixelSize: 34
            font.bold: true
            // Breathing glow on the Eclipse mark — subtle, not loud.
            SequentialAnimation on opacity {
                loops: Animation.Infinite
                NumberAnimation { from: 0.78; to: 1.0; duration: 2200; easing.type: Easing.InOutSine }
                NumberAnimation { from: 1.0; to: 0.78; duration: 2200; easing.type: Easing.InOutSine }
            }
        }
        Column {
            spacing: 2
            Text {
                text: "NYXUS"
                color: root.accent
                font.family: "Inter"
                font.pixelSize: 18
                font.letterSpacing: 8
                font.weight: Font.Bold
            }
            Text {
                text: "Welcome to the Darkside"
                color: root.textLo
                font.family: "Caveat"
                font.pixelSize: 13
                font.italic: true
            }
        }
    }

    // ── Cream corner accent — top right (rev r15 cream, no cyan) ─────
    Rectangle {
        width: 60; height: 1
        color: root.accent
        opacity: 0.55
        x: parent.width - 100; y: 50
    }
    Rectangle {
        width: 1; height: 22
        color: root.accent
        opacity: 0.55
        x: parent.width - 41; y: 38
    }

    // ── Slide content — frosted glass card with cross-fade ────────────
    Rectangle {
        id: cardBg
        anchors.centerIn: parent
        width: 680
        height: 280
        radius: 3
        color: root.glassBg
        opacity: 0.78
        border.width: 1
        border.color: root.glassEdge
    }
    // Cream accent stripe along card top edge
    Rectangle {
        anchors.top: cardBg.top
        anchors.left: cardBg.left
        width: 86; height: 2
        color: root.accent
        opacity: 0.85
    }

    Column {
        id: slideContent
        anchors.centerIn: parent
        spacing: 18
        width: 600
        opacity: 1.0

        Text {
            text: root.slides[root.currentSlide].tagline
            color: root.accent
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 11
            font.letterSpacing: 6
            font.weight: Font.Bold
            anchors.horizontalCenter: parent.horizontalCenter
        }
        Text {
            text: root.slides[root.currentSlide].title
            color: root.textHi
            font.family: "Inter"
            font.pixelSize: 30
            font.weight: Font.Bold
            font.letterSpacing: 0.5
            anchors.horizontalCenter: parent.horizontalCenter
        }
        Rectangle {
            width: 60; height: 1
            color: root.accent
            opacity: 0.45
            anchors.horizontalCenter: parent.horizontalCenter
        }
        Text {
            text: root.slides[root.currentSlide].body
            color: root.textBody
            opacity: 0.9
            font.family: "Inter"
            font.pixelSize: 14
            lineHeight: 1.55
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            width: parent.width
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Behavior on opacity {
            SequentialAnimation {
                NumberAnimation { duration: 420; easing.type: Easing.OutCubic }
                ScriptAction {
                    script: {
                        if (slideContent.opacity < 0.05) {
                            root.currentSlide =
                                (root.currentSlide + 1) % root.slides.length
                            slideContent.opacity = 1.0
                        }
                    }
                }
            }
        }
    }

    // ── Pagination dots — animated width on selection ─────────────────
    Row {
        spacing: 10
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 36
        anchors.horizontalCenter: parent.horizontalCenter
        Repeater {
            model: root.slides.length
            Rectangle {
                width: index === root.currentSlide ? 32 : 8
                height: 3
                radius: 1
                color: index === root.currentSlide ? root.accent : root.hairline
                Behavior on width {
                    NumberAnimation { duration: 320; easing.type: Easing.OutCubic }
                }
                Behavior on color {
                    ColorAnimation { duration: 320 }
                }
            }
        }
    }

    // ── Footer hairline ───────────────────────────────────────────────
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: root.hairline
    }
}
