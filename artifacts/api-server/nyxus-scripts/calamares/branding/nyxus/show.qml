/*
 * Calamares slideshow for NYXUS — DARK MIRROR aesthetic.
 *
 * SlideshowAPI: 2 (Calamares ≥ 3.2). Slides advance every 12s and the
 * Slideshow's onActivate / onDeactivate hooks start/stop the timer so
 * we don't keep firing while the install pages aren't visible.
 *
 * The "Dark Mirror" gold is #d4b87a. Background is the same near-black
 * (#0b0b0f) used by the rest of the OS.
 *
 * © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
 */
import QtQuick 2.15
import calamares.slideshow 1.0

Presentation {
    id: presentation
    width:  900
    height: 480

    Rectangle { anchors.fill: parent; color: "#0b0b0f" }

    function nextSlide() { presentation.goToNextSlide(); }
    Timer {
        id: advanceTimer
        interval: 12000
        repeat:   true
        onTriggered: presentation.nextSlide()
    }

    Slide {
        Text {
            anchors.centerIn: parent
            text: "Welcome to NYXUS"
            font.pixelSize: 38
            font.bold: true
            color: "#d4b87a"
        }
        Text {
            anchors.top: parent.verticalCenter
            anchors.topMargin: 40
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Arch-based · Hyprland · designed for clarity"
            font.pixelSize: 16
            color: "#e8e8ee"
        }
    }

    Slide {
        Text {
            anchors.centerIn: parent
            text: "First-class privacy"
            font.pixelSize: 32
            font.bold: true
            color: "#d4b87a"
        }
        Text {
            anchors.top: parent.verticalCenter
            anchors.topMargin: 36
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - 80
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            text: "Built-in proxy + DoH controls, encrypted backups via " +
                  "Timeshift, and Parental Controls that nudge — never " +
                  "lock you out of your own machine."
            font.pixelSize: 15
            color: "#e8e8ee"
        }
    }

    Slide {
        Text {
            anchors.centerIn: parent
            text: "A complete suite, out of the box"
            font.pixelSize: 30
            font.bold: true
            color: "#d4b87a"
        }
        Text {
            anchors.top: parent.verticalCenter
            anchors.topMargin: 36
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - 80
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            text: "Notepad · Stickies · Files · Spotlight · Mission " +
                  "Control · Control Center · Notification Center · " +
                  "Sysmon · Backup · Account sync · Screen recorder."
            font.pixelSize: 15
            color: "#e8e8ee"
        }
    }

    Slide {
        Text {
            anchors.centerIn: parent
            text: "You bought it from Best Buy"
            font.pixelSize: 30
            font.bold: true
            color: "#d4b87a"
        }
        Text {
            anchors.top: parent.verticalCenter
            anchors.topMargin: 36
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width - 80
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            text: "Every menu opens a real panel. Every setting persists. " +
                  "No mockups, no dead ends — that's the NYXUS bar."
            font.pixelSize: 15
            color: "#e8e8ee"
        }
    }

    function onActivate()   { advanceTimer.start(); }
    function onLeave()      { advanceTimer.stop();  }
}
