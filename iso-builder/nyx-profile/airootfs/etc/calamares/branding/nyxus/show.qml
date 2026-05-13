// NYXUS · Calamares slideshow (DARK MIRROR)
// Cycles through 5 cards while the user installs. Uses only QtQuick 2.15
// to remain compatible with every Calamares 3.3.x build.

import QtQuick 2.15

Rectangle {
    id: root
    width:  900
    height: 380
    color:  "#080a10"

    readonly property color clrText:  "#e8edf5"
    readonly property color clrDim:   "#a8acb6"
    readonly property color clrAcc:   "#d4b87a"

    property int idx: 0
    property var slides: [
        {
            "title":  "WELCOME TO NYXUS",
            "lead":   "DARK MIRROR · Arch-based, Hyprland-native",
            "body":   "A grade-A desktop with a single visual contract: " +
                      "deep void, hairline white, restrained gold. No neon, " +
                      "no per-app colors."
        },
        {
            "title":  "THE SECURITY CENTER",
            "lead":   "Defender-class privacy and protection",
            "body":   "Live firewall · ClamAV · LUKS vaults · TPM/Secure " +
                      "Boot status · USBGuard · privacy indicators · " +
                      "Super+Ctrl+Alt+L panic lockdown."
        },
        {
            "title":  "THE FILE MANAGER",
            "lead":   "Finder/Explorer parity, NYXUS look",
            "body":   "Sidebar, breadcrumbs, list+grid, Tab, search, " +
                      "drag/drop, MIME-aware open, gio-backed trash. " +
                      "Spotlight finds anything with =calc, /files, ?web."
        },
        {
            "title":  "BACKUP, ACCOUNT, DROP",
            "lead":   "Built-in continuity",
            "body":   "Timeshift snapshots with restore, NYXUS Account " +
                      "wallpaper/theme sync, KDE Connect-rebrand NYXUS Drop " +
                      "for instant cross-device file send."
        },
        {
            "title":  "SHIP IT",
            "lead":   "Welcome wizard runs on first login",
            "body":   "We'll pick your accent, set your timezone, install " +
                      "extras from the Software Store, and you're done. " +
                      "Press F1 anywhere for the cheat sheet."
        }
    ]

    Column {
        anchors.fill: parent
        anchors.margins: 48
        spacing: 18

        Text {
            text: slides[idx].title
            color: clrAcc
            font.family: "Inter"
            font.pixelSize: 26
            font.weight: Font.DemiBold
            font.letterSpacing: 4
        }
        Rectangle {
            width: 60; height: 1; color: clrAcc; opacity: 0.6
        }
        Text {
            text: slides[idx].lead
            color: clrText
            font.family: "Inter"
            font.pixelSize: 18
            font.weight: Font.Light
        }
        Text {
            width: parent.width
            text: slides[idx].body
            color: clrDim
            wrapMode: Text.WordWrap
            font.family: "Inter"
            font.pixelSize: 13
            lineHeight: 1.5
        }

        Item { width: 1; height: 8 }

        Row {
            spacing: 6
            Repeater {
                model: slides.length
                Rectangle {
                    width: 28; height: 3
                    radius: 2
                    color: index === idx ? clrAcc : "#3a3d44"
                    opacity: index === idx ? 1.0 : 0.6
                }
            }
        }
    }

    Timer {
        interval: 9000
        running:  true
        repeat:   true
        onTriggered: idx = (idx + 1) % slides.length
    }

    function onActivate()   { idx = 0 }
    function onLeave()      { /* nothing — slideshow is purely visual */ }
}
