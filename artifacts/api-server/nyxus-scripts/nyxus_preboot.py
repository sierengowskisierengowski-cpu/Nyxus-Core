#!/usr/bin/env python3
"""
NYXUS — Pre-Boot Flicker Effect
The moment before something powerful turns on.
Silent. Dark. Then it wakes up.
© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""

import sys
import time
import random
import shutil
import os

RESET = "\033[0m"
DIM   = "\033[2m"

def fg256(n):
    return f"\033[38;5;{n}m"

# Purple / white shades — dim only, no color chaos
PURPLE_FAINT  = fg256(54)   # darkest purple
PURPLE_DIM    = fg256(93)   # dim purple
PURPLE_MED    = fg256(135)  # medium purple
WHITE_FAINT   = fg256(236)  # barely visible white
WHITE_DIM     = fg256(242)  # dim white

BG_BLACK = "\033[40m"

def get_size():
    s = shutil.get_terminal_size((120, 40))
    return s.columns, s.lines

def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def hide_cursor():
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

def show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()

# Fragments that bleed through — just pieces, never fully legible
FRAGMENTS = [
    "NYXUS",    "NYX",      "_NYX_",    "YXU",      "NX",
    "n y x",    "nyxus",    "N·Y·X",    "XUS",      "NYX_",
    "INIT",     "BOOT",     "KERNEL",   "NYX::INIT","_CORE",
    "SILENT",   "DARK",     "0x4E5958", "NYX-J5W",  "2026",
    "PURELY",   "▓NYX▓",    "[ NYX ]",  "::NYX::",  "SIERENGOWSKI",
    "LOADING",  "STANDBY",  "ARMED",    "ENGAGE",   "nyx_boot",
    "\\x4e\\x59","4E 59 58", "NYX_LOCK", "CORE OK",  "STAGE_0",
]

NOISE_CHARS = list("|-+/\\:.*")


def render_black(cols: int, rows: int):
    """Pure black — nothing visible."""
    out = "\033[H\033[40m"
    blank = " " * cols
    for _ in range(rows - 1):
        out += blank + "\r\n"
    sys.stdout.write(out + RESET)
    sys.stdout.flush()


def render_flash(cols: int, rows: int, intensity: float):
    """
    Brief flash frame: dim NYXUS fragments scattered on black.
    intensity 0.0 to 1.0 controls brightness, density, fragment count.
    Colors stay in purple/dim-white only — never bright, never rainbow.
    """
    screen_ch    = [[" "]  * cols for _ in range(rows - 1)]
    screen_color = [[None] * cols for _ in range(rows - 1)]

    def pick_color():
        if intensity < 0.25:
            return PURPLE_FAINT
        elif intensity < 0.55:
            return random.choice([PURPLE_FAINT, PURPLE_DIM])
        elif intensity < 0.80:
            return random.choice([PURPLE_DIM, PURPLE_MED, WHITE_FAINT])
        else:
            return random.choice([PURPLE_DIM, PURPLE_MED, WHITE_FAINT, WHITE_DIM])

    # Scatter text fragments — broken signal, not readable
    n_fragments = max(1, int(intensity * 9) + random.randint(0, 2))
    for _ in range(n_fragments):
        frag = random.choice(FRAGMENTS)

        # At low intensity, only show a slice of the fragment
        if intensity < 0.4:
            start = random.randint(0, max(0, len(frag) - 2))
            end   = start + random.randint(1, max(1, len(frag) // 2))
            frag  = frag[start:end]

        r   = random.randint(0, rows - 3)
        c   = random.randint(0, max(0, cols - len(frag) - 1))
        col = pick_color()

        for j, ch in enumerate(frag):
            tc = c + j
            if tc >= cols:
                break
            # Random character drop — harder to read at low intensity
            drop_chance = 0.45 - intensity * 0.35
            if random.random() > drop_chance and ch.isprintable():
                screen_ch[r][tc]    = ch
                screen_color[r][tc] = col

    # Sparse noise dots
    n_noise = int(intensity * cols * 0.025 * random.random())
    for _ in range(n_noise):
        r = random.randint(0, rows - 3)
        c = random.randint(0, cols - 1)
        screen_ch[r][c]    = random.choice(NOISE_CHARS)
        screen_color[r][c] = PURPLE_FAINT

    # Render
    out = "\033[H\033[40m"
    for r in range(rows - 1):
        line      = "\033[40m"
        prev_col  = None
        for c in range(cols):
            ch  = screen_ch[r][c]
            col = screen_color[r][c]
            if col and ch != " ":
                if col != prev_col:
                    line    += col
                    prev_col = col
                line += ch
            else:
                if prev_col is not None:
                    line    += "\033[40m"
                    prev_col = None
                line += " "
        line += RESET
        out += line + "\r\n"

    sys.stdout.write(out)
    sys.stdout.flush()


def render_preboot(next_command=None):
    """
    Flicker animation:
      0.0 – 3.0s  : flickers, slow start → accelerating → peak
      3.0 – 3.45s : total black silence
      3.45 – 4.3s : 'initializing...' types in dim purple, cursor blinks
      4.3s+       : snap to black, exec next command
    """
    hide_cursor()
    cols, rows = get_size()
    clear()

    FLICKER_END   = 3.0
    SILENCE_END   = 3.45
    INIT_CHAR_DUR = 0.048   # seconds per character typed
    INIT_HOLD     = 0.55

    start       = time.time()
    state       = "black"
    state_start = start

    try:
        # ── Phase 1: Flicker ────────────────────────────────────────────────
        while True:
            now     = time.time()
            elapsed = now - start

            if elapsed >= FLICKER_END:
                break

            pct = elapsed / FLICKER_END  # 0.0 → 1.0

            # Timing curves:
            #   black_dur: 0.35s → 0.018s  (exponential decay — gaps shrink fast)
            #   flash_dur: 0.030s → 0.075s (flash grows slightly — more revealed)
            #   intensity: quick power ramp
            black_dur = 0.35 * ((1.0 - pct) ** 1.6) + 0.018
            flash_dur = 0.030 + 0.055 * (pct ** 0.6)
            intensity = pct ** 0.65

            state_elapsed = now - state_start

            if state == "black":
                render_black(cols, rows)
                if state_elapsed >= black_dur:
                    state       = "flash"
                    state_start = now
                else:
                    time.sleep(min(0.010, black_dur - state_elapsed))
            else:
                render_flash(cols, rows, intensity)
                if state_elapsed >= flash_dur:
                    state       = "black"
                    state_start = now
                else:
                    time.sleep(min(0.008, flash_dur - state_elapsed))

        # ── Phase 2: Pure black silence ─────────────────────────────────────
        render_black(cols, rows)
        silence_remaining = SILENCE_END - (time.time() - start)
        if silence_remaining > 0:
            time.sleep(silence_remaining)

        # ── Phase 3: "initializing..." types in dim purple ──────────────────
        init_text  = "initializing..."
        center_row = rows // 2
        pad        = max(0, (cols - len(init_text)) // 2)

        for i in range(len(init_text) + 1):
            sys.stdout.write(
                f"\033[{center_row};{pad + 1}H"
                f"{PURPLE_DIM}{init_text[:i]}{RESET}"
            )
            sys.stdout.flush()
            if i < len(init_text):
                time.sleep(INIT_CHAR_DUR)

        # Blinking block cursor after text
        for blink in range(4):
            cursor = "█" if blink % 2 == 0 else " "
            sys.stdout.write(
                f"\033[{center_row};{pad + len(init_text) + 1}H"
                f"{PURPLE_FAINT}{cursor}{RESET}"
            )
            sys.stdout.flush()
            time.sleep(0.14)

        time.sleep(INIT_HOLD)

        # ── Phase 4: Snap to black, launch next stage ────────────────────────
        clear()
        show_cursor()

        if next_command:
            os.execvp(next_command[0], next_command)

    except KeyboardInterrupt:
        clear()
        show_cursor()
        sys.exit(130)


# ── CLI entrypoint ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    import shlex

    parser = argparse.ArgumentParser(description="NYXUS Pre-Boot Flicker Effect")
    parser.add_argument(
        "--next", type=str, default=None,
        help="Command to exec after animation (e.g. 'python3 nyxus_splash.py')"
    )
    args = parser.parse_args()

    next_cmd = shlex.split(args.next) if args.next else None
    render_preboot(next_command=next_cmd)
