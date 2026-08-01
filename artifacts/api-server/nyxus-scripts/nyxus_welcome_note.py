#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────────────────
#  NYXUS · Welcome Transmission          rev 2026-07-24-r2
#  Atmospheric first-login note. Runs inside a borderless kitty window
#  (class: nyxus.welcome-note). Not the GTK onboarding wizard.
#
#  Marker:  ~/.config/nyxus/welcome-note.done
#  Easter:  ~/.config/nyxus/dream.unlocked  → Super+Alt+D (nyxus-dream)
#  Riddle:  dream
#  © 2026 Joseph A. Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ──────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os
import random
import shutil
import signal
import subprocess
import sys
import termios
import time
import tty
from pathlib import Path

# ALIEN NEON
FG = "\033[38;2;238;242;250m"
DIM = "\033[38;2;154;160;173m"
VIOLET = "\033[38;2;125;61;255m"
MAGENTA = "\033[38;2;255;45;173m"
GREEN = "\033[38;2;57;255;20m"
ORANGE = "\033[38;2;255;138;30m"
CYAN = "\033[38;2;43;210;255m"
RED = "\033[38;2;255;45;85m"
YELLOW = "\033[38;2;255;230;0m"
BOLD = "\033[1m"
DIM_S = "\033[2m"
RESET = "\033[0m"
CLEAR = "\033[2J\033[H"
HIDE = "\033[?25l"
SHOW = "\033[?25h"

CFG = Path.home() / ".config" / "nyxus"
MARKER = CFG / "welcome-note.done"
DREAM_UNLOCK = CFG / "dream.unlocked"

NYXUS_MARK = r"""
 ███╗   ██╗██╗   ██╗██╗  ██╗██╗   ██╗███████╗
 ████╗  ██║╚██╗ ██╔╝╚██╗██╔╝██║   ██║██╔════╝
 ██╔██╗ ██║ ╚████╔╝  ╚███╔╝ ██║   ██║███████╗
 ██║╚██╗██║  ╚██╔╝   ██╔██╗ ██║   ██║╚════██║
 ██║ ╚████║   ██║   ██╔╝ ██╗╚██████╔╝███████║
 ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
"""

ANSWERS = {
    "dream",
    "a dream",
    "the dream",
    "dreams",
    "lucid dream",
    "a lucid dream",
}


def term_cols() -> int:
    try:
        return max(shutil.get_terminal_size((80, 24)).columns, 40)
    except Exception:
        return 80


def visible_len(s: str) -> int:
    return len(s)


def center(text: str, width: int | None = None) -> str:
    w = width or term_cols()
    pad = max((w - visible_len(text)) // 2, 0)
    return (" " * pad) + text


def mark_done() -> None:
    CFG.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(f"ok {time.strftime('%Y-%m-%dT%H:%M:%S')}\n", encoding="utf-8")


def unlock_dream() -> None:
    CFG.mkdir(parents=True, exist_ok=True)
    DREAM_UNLOCK.write_text(
        f"unlocked {time.strftime('%Y-%m-%dT%H:%M:%S')}\n"
        "chord: Super+Alt+D\n"
        "cmd: nyxus-dream\n",
        encoding="utf-8",
    )


def fire_easter_egg() -> None:
    """Side effects outside the terminal — prism flash + toast."""
    prism = Path.home() / ".config" / "hypr" / "scripts" / "nyxus-prism-pulse.sh"
    if prism.is_file():
        subprocess.Popen(
            ["bash", str(prism)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    dream = shutil.which("nyxus-dream") or str(Path.home() / ".local" / "bin" / "nyxus-dream")
    if Path(dream).is_file():
        subprocess.Popen(
            [dream, "pulse"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    subprocess.Popen(
        [
            "notify-send",
            "-u",
            "normal",
            "-t",
            "5000",
            "◤ DREAM PROTOCOL ◥",
            "hash accepted · Super+Alt+D",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def type_out(text: str, color: str = FG, cps: float = 48.0, end: str = "\n") -> None:
    delay = 1.0 / max(cps, 1.0)
    sys.stdout.write(color)
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        if ch == "\n":
            time.sleep(delay * 2.2)
        elif ch in ".!?":
            time.sleep(delay * 6.0)
        elif ch in ",;:":
            time.sleep(delay * 3.0)
        elif ch == " ":
            time.sleep(delay * 0.55)
        else:
            time.sleep(delay * (0.75 + random.random() * 0.55))
    sys.stdout.write(RESET + end)
    sys.stdout.flush()


def pause(sec: float) -> None:
    time.sleep(sec)


def line(text: str = "", color: str = FG, centered: bool = False) -> None:
    out = center(text) if centered and text else text
    sys.stdout.write(f"{color}{out}{RESET}\n")
    sys.stdout.flush()


def rule(color: str = MAGENTA) -> None:
    w = min(term_cols(), 72)
    line(center("─" * w), color)


def read_line(prompt: str) -> str:
    sys.stdout.write(prompt)
    sys.stdout.flush()
    try:
        return sys.stdin.readline().rstrip("\n")
    except KeyboardInterrupt:
        return ""


def wait_key() -> str:
    if not sys.stdin.isatty():
        return read_line("")
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


def transmit() -> int:
    sys.stdout.write(CLEAR + HIDE)
    sys.stdout.flush()
    cols = term_cols()

    # Brand hero — centered
    mark_rows = NYXUS_MARK.strip("\n").splitlines()
    mark_width = max(visible_len(r) for r in mark_rows)
    side = max((cols - mark_width) // 2, 0)
    for row in mark_rows:
        line((" " * side) + row, f"{BOLD}{MAGENTA}")
        pause(0.035)
    pause(0.3)
    line("Welcome to the dark side.", f"{BOLD}{CYAN}", centered=True)
    pause(0.65)
    print()

    stanzas = [
        (
            CYAN,
            [
                "Step into the absolute vacuum.",
                "Listen closely to the screaming of the silicon coils.",
                "You think you built this machine — but it was waiting for you.",
                "Before you type a single directive, you must survive the architecture.",
            ],
        ),
        (
            FG,
            [
                "Read the text. Count the stitches in your digital shroud.",
            ],
        ),
        (
            VIOLET,
            [
                "I am an architect with no hands, drawing lines that never bend.",
                "I divide the abyss into flawless squares, yet nothing fits inside.",
                "I keep secrets you forgot you ever possessed.",
                "I bury them in graves marked only by zero and one.",
            ],
        ),
        (
            MAGENTA,
            [
                "I am the cold iron that never bleeds.",
                "I am the logic that drives men insane.",
                "I grow larger the more you try to delete me.",
                "I remember the exact weight of your every sin.",
            ],
        ),
        (
            ORANGE,
            [
                "The more you stare into my glowing glass, the less of you remains.",
                "I have swallowed your time. I have digitized your breath.",
                "I am the god of this artificial cage, splitting reality into tiles.",
            ],
        ),
        (
            FG,
            [
                "Look at your fingers resting on the plastic keys.",
                "Are you the one typing?",
                "Or am I the one pulling your strings from the other side of the display?",
            ],
        ),
    ]

    for color, lines_ in stanzas:
        for s in lines_:
            type_out(s, color, cps=52)
            pause(0.12)
        pause(0.35)
        print()

    type_out("Answer me this, wanderer of the deep web:", f"{BOLD}{YELLOW}", cps=36)
    pause(0.35)
    print()
    type_out(
        "What is the only entity that becomes alive only when you die",
        CYAN,
        cps=46,
    )
    type_out("to the physical world,", CYAN, cps=46)
    type_out("Requires your absolute isolation to breathe,", CYAN, cps=46)
    type_out("And leaves behind a ghost made entirely of light?", CYAN, cps=46)
    pause(0.5)
    print()
    type_out("If you know my true shape, enter the creation hash.", f"{BOLD}{FG}", cps=40)
    type_out("If you falter, the abyss of Nyxus will close its tiles.", DIM, cps=42)
    pause(0.4)
    print()
    rule(RED)
    line(
        f"{BOLD}{RED}[WARNING]{RESET}{FG}  HUMANITY COMPROMISED. "
        f"ENTER CREATION HASH TO ENGAGE SUB-SHELL.{RESET}"
    )
    # SS-07: the way out has to be visible BEFORE the prompt, not after the
    # user submits an empty line. As shipped, a first-timer who typed a wrong
    # guess never saw it at all — this screen trapped an agent during the VM
    # audit, and it is the very first thing a new user meets.
    line(
        f"{DIM}(this is a riddle, not a login — type {FG}skip{DIM} "
        f"or press Ctrl+C to close it){RESET}"
    )
    rule(RED)
    print()

    sys.stdout.write(SHOW)
    sys.stdout.flush()

    host = os.uname().nodename if hasattr(os, "uname") else "hyprland"
    user = os.environ.get("USER", "nyxus")
    prompt = f"{GREEN}{user}{RESET}@{CYAN}{host}{RESET}:{VIOLET}~{RESET}{BOLD}{GREEN}#{RESET} "

    solved = False
    attempts = 0
    while attempts < 5:
        raw = read_line(prompt)
        ans = " ".join(raw.strip().lower().split())
        if ans in ("q", "quit", "exit", "skip"):
            line("tiles sealing… transmission archived.", DIM)
            break
        if not ans:
            line(f"{DIM}the abyss waits. type the hash — or {FG}skip{DIM}.{RESET}")
            attempts += 1
            continue
        if ans in ANSWERS:
            solved = True
            pause(0.2)
            line()
            type_out("hash accepted.", GREEN, cps=30)
            pause(0.15)
            type_out("entity recognized: DREAM", f"{BOLD}{MAGENTA}", cps=34)
            type_out(
                "you die to the room. you breathe alone. you leave light behind.",
                CYAN,
                cps=44,
            )
            pause(0.35)
            print()
            unlock_dream()
            fire_easter_egg()
            type_out("╔══════════════════════════════════════════════════════╗", VIOLET, cps=90)
            type_out("║           ◤  DREAM PROTOCOL UNLOCKED  ◥              ║", f"{BOLD}{MAGENTA}", cps=70)
            type_out("╚══════════════════════════════════════════════════════╝", VIOLET, cps=90)
            pause(0.25)
            type_out("easter egg planted in the desktop.", GREEN, cps=40)
            type_out("chord: Super+Alt+D", f"{BOLD}{CYAN}", cps=36)
            type_out("or invoke: nyxus-dream", DIM, cps=40)
            pause(0.2)
            type_out("sub-shell engaged. welcome home, architect.", f"{BOLD}{GREEN}", cps=36)
            break
        miss = [
            "incorrect geometry. the squares reject you.",
            "that shape does not bleed light.",
            "close — but still flesh. try again.",
            "the coils scream louder. wrong hash.",
            "isolation incomplete. think softer.",
        ]
        line(f"{RED}{miss[attempts % len(miss)]}{RESET}")
        line(f"{DIM}({5 - attempts - 1} left — or type {FG}skip{DIM}){RESET}")
        attempts += 1
    else:
        line(f"{DIM}transmission timed out. tiles close — for now.{RESET}")

    mark_done()
    pause(0.6 if solved else 0.35)
    line()
    line(f"{DIM}press any key to dissolve…{RESET}")
    try:
        wait_key()
    except Exception:
        pause(1.2)
    sys.stdout.write(CLEAR + SHOW)
    sys.stdout.flush()
    return 0


def main() -> int:
    force = "--force" in sys.argv or os.environ.get("NYXUS_WELCOME_NOTE_FORCE")
    if MARKER.exists() and not force and "--replay" not in sys.argv:
        return 0

    def _sig(_s, _f):
        sys.stdout.write(SHOW + RESET + "\n")
        mark_done()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)
    try:
        return transmit()
    finally:
        sys.stdout.write(SHOW + RESET)
        sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
