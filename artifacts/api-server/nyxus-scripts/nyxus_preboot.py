#!/usr/bin/env python3
"""
NYXUS — Pre-Boot Flicker Sequence
Five phases. Cinematic. Unforgettable.
© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""

import os
import sys
import time
import random

# ── ANSI ─────────────────────────────────────────────────────────────────────────
RESET      = "\033[0m"
BOLD       = "\033[1m"
FG_WHITE   = "\033[97m"        # phase 1 flashes
PURPLE_EL  = "\033[38;5;135m"  # electric purple — fragment bleed
PINK_EL    = "\033[38;5;213m"  # neon pink      — overload mix
PURPLE_DIM = "\033[38;5;97m"   # dim purple     — awakening cursor

# ── TERMINAL ─────────────────────────────────────────────────────────────────────
def term_size():
    try:
        sz = os.get_terminal_size()
        return sz.columns, sz.lines
    except OSError:
        return 120, 40

def flush():
    sys.stdout.flush()

def clear():
    sys.stdout.write("\033[2J\033[H")
    flush()

def hide_cursor():
    sys.stdout.write("\033[?25l")
    flush()

def show_cursor():
    sys.stdout.write("\033[?25h")
    flush()


# ── FRAME RENDERERS ───────────────────────────────────────────────────────────────

def frame_black(cols, rows):
    """Absolute black — not a single photon."""
    out  = "\033[H\033[40m"
    line = " " * cols
    for _ in range(rows):
        out += line
    sys.stdout.write(out + RESET)
    flush()


def frame_white(cols, rows):
    """Blinding white flash — fills every cell."""
    # Bright white background + bright white block char = total white
    line = "\033[107m" + "█" * cols
    out  = "\033[H"
    for _ in range(rows):
        out += line
    sys.stdout.write(out + RESET)
    flush()


# Fragments that bleed through in Phase 2 — never full words, just pieces
FRAG_POOL = [
    "NYX", "◆", "★", "彡", "INIT", "SYS", "_",
    "N", "Y", "X", "U", "S", "◆★", "★彡", "NYX_",
    "BOOT", "CORE", ":::", ">>>", "---",
    "██", "▓▓", "░░", "■", "▪",
    "KERNEL", "STAGE", "ARM", "NYX::",
    "彡★", "◆★彡", "★◆",
]

# Noise chars to pad out the white base in Phase 2
_NOISE = "█░▓▒"

def frame_fragment(cols, rows, density):
    """
    Phase 2 frame: white base with electric purple fragments scattered across it.
    density 0.0 → 1.0 controls how many fragments appear and how boldly.
    """
    # Build cell buffers
    ch_buf    = [["█"] * cols for _ in range(rows)]
    color_buf = [["w"]  * cols for _ in range(rows)]  # 'w'=white, 'p'=purple

    # Scatter fragments — count and length grow with density
    n_frags = max(2, int(density * rows * 1.8) + random.randint(0, 3))
    for _ in range(n_frags):
        frag = random.choice(FRAG_POOL)
        # At low density, only show a slice of each fragment
        if density < 0.4:
            sl = random.randint(1, max(1, len(frag) // 2))
            frag = frag[:sl]

        r = random.randint(0, rows - 1)
        c = random.randint(0, max(0, cols - len(frag)))
        for j, ch in enumerate(frag):
            tc = c + j
            if tc < cols and ch.isprintable():
                # Random dropout — lower at higher density
                if random.random() > (0.35 - density * 0.30):
                    ch_buf[r][tc]    = ch
                    color_buf[r][tc] = "p"

    # Render — minimize escapes by tracking prev color
    out = "\033[H\033[40m"   # black background throughout
    for r in range(rows):
        line     = ""
        prev_col = None
        for c in range(cols):
            col = color_buf[r][c]
            ch  = ch_buf[r][c]
            if col != prev_col:
                if col == "p":
                    line += f"{PURPLE_EL}{BOLD}"
                else:
                    line += FG_WHITE
                prev_col = col
            line += ch
        out += line + RESET + "\n"

    sys.stdout.write(out)
    flush()


_OVERLOAD_CHARS = list(
    "NYXUSnyxus◆★彡█▓░▒│─┼╪╬╋╳×+*#@!$%^&|<>{}[]()_=~`"
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)

def frame_overload(cols, rows):
    """
    Phase 3: every single cell filled with random purple/pink char — total overload.
    """
    out = "\033[H\033[40m"
    for r in range(rows):
        line     = ""
        prev_col = None
        for c in range(cols):
            ch  = random.choice(_OVERLOAD_CHARS)
            col = random.choice(("p", "k"))   # purple or pink
            if col != prev_col:
                if col == "p":
                    line += f"{PURPLE_EL}{BOLD}"
                else:
                    line += f"{PINK_EL}{BOLD}"
                prev_col = col
            line += ch
        out += line + RESET + "\n"

    sys.stdout.write(out)
    flush()


# ── MAIN ──────────────────────────────────────────────────────────────────────────

def run(next_command=None):
    hide_cursor()
    cols, rows = term_size()
    clear()

    start = time.perf_counter()

    try:
        # ─────────────────────────────────────────────────────────────────────────
        # PHASE 1 — Power struggling (1.0 s)
        # Black / white only. No text. Gets faster.
        # ─────────────────────────────────────────────────────────────────────────
        P1_END = 1.0

        state       = "black"
        state_start = start

        while True:
            now     = time.perf_counter()
            elapsed = now - start
            if elapsed >= P1_END:
                break

            pct = elapsed / P1_END                          # 0 → 1
            # Black gap: wide (0.28s) → very tight (0.013s)
            black_dur = 0.28 * ((1.0 - pct) ** 1.9) + 0.013
            # White flash: stays relatively constant, slight shrink
            white_dur = 0.090 - 0.040 * pct

            se = now - state_start
            if state == "black":
                frame_black(cols, rows)
                if se >= black_dur:
                    state       = "white"
                    state_start = now
                else:
                    time.sleep(min(0.008, black_dur - se))
            else:
                frame_white(cols, rows)
                if se >= white_dur:
                    state       = "black"
                    state_start = now
                else:
                    time.sleep(min(0.008, white_dur - se))

        # ─────────────────────────────────────────────────────────────────────────
        # PHASE 2 — Something breaks through (1.5 s)
        # White flashes with electric purple fragments. Gets more chaotic.
        # ─────────────────────────────────────────────────────────────────────────
        P2_START = P1_END
        P2_END   = P1_END + 1.5

        state       = "black"
        state_start = time.perf_counter()

        while True:
            now     = time.perf_counter()
            elapsed = now - start
            if elapsed >= P2_END:
                break

            pct = (elapsed - P2_START) / 1.5               # 0 → 1

            # Black gap continues shrinking — nearly gone by end
            black_dur = 0.013 * (1.0 - pct * 0.75) + 0.005
            # Fragment flash grows — fragments linger longer and longer
            flash_dur = 0.038 + 0.140 * pct
            # Fragment density builds
            density   = 0.10 + 0.65 * (pct ** 0.7)

            se = now - state_start
            if state == "black":
                frame_black(cols, rows)
                if se >= black_dur:
                    state       = "flash"
                    state_start = now
                else:
                    time.sleep(min(0.005, black_dur - se))
            else:
                frame_fragment(cols, rows, density=density)
                if se >= flash_dur:
                    state       = "black"
                    state_start = now
                else:
                    time.sleep(min(0.008, flash_dur - se))

        # ─────────────────────────────────────────────────────────────────────────
        # PHASE 3 — Overload (0.5 s)
        # Every cell filled with purple + pink. Overwhelming. Then: nothing.
        # ─────────────────────────────────────────────────────────────────────────
        P3_END = P2_END + 0.5

        while time.perf_counter() - start < P3_END:
            frame_overload(cols, rows)
            time.sleep(0.030)   # rapid redraw ~ 33fps

        # Instant cut to black
        frame_black(cols, rows)

        # ─────────────────────────────────────────────────────────────────────────
        # PHASE 4 — Silence (0.8 s)
        # Pure black. Complete stillness. The calm after.
        # ─────────────────────────────────────────────────────────────────────────
        time.sleep(0.8)

        # ─────────────────────────────────────────────────────────────────────────
        # PHASE 5 — Awakening
        # Cursor blinks 3x in dim purple.
        # Then the awakening line types itself out.
        # ─────────────────────────────────────────────────────────────────────────
        center_row = rows // 2
        center_col = cols // 2

        # Cursor blink: 3 on/off cycles
        for blink in range(6):
            char = "█" if blink % 2 == 0 else " "
            sys.stdout.write(
                f"\033[{center_row};{center_col}H{PURPLE_DIM}{char}{RESET}"
            )
            flush()
            time.sleep(0.22)

        # Clear cursor position
        sys.stdout.write(f"\033[{center_row};{center_col}H {RESET}")
        flush()
        time.sleep(0.18)

        # Type the awakening text character by character
        awaken    = "◆★彡 NYXUS — INITIALIZING ★彡◆"
        awaken_c  = max(1, (cols - len(awaken)) // 2 + 1)

        sys.stdout.write(
            f"\033[{center_row};{awaken_c}H{PURPLE_EL}{BOLD}"
        )
        flush()

        for ch in awaken:
            sys.stdout.write(ch)
            flush()
            time.sleep(0.052)

        sys.stdout.write(RESET)
        flush()
        time.sleep(0.75)

        # Snap to black — done
        clear()
        show_cursor()

        if next_command:
            os.execvp(next_command[0], next_command)

    except KeyboardInterrupt:
        frame_black(cols, rows)
        show_cursor()
        sys.exit(130)


# ── ENTRY POINT ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    import shlex

    parser = argparse.ArgumentParser(description="NYXUS Pre-Boot Flicker Sequence")
    parser.add_argument(
        "--next", type=str, default=None,
        help="Command to exec after the animation completes"
    )
    args = parser.parse_args()
    nxt  = shlex.split(args.next) if args.next else None
    run(next_command=nxt)
