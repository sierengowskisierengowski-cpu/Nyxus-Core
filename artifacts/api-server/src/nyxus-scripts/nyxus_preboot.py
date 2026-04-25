#!/usr/bin/env python3
"""
NYXUS — Pre-Boot Glitch / Static Animation
TV static signal corruption — pure chaos before order.
THIS IS A TOP TIER BUILD. Unforgettable first impression.
© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""

import os
import sys
import time
import random
import shutil
import math

# ── ANSI helpers ───────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

# 256-color foreground
def fg256(n):
    return f"\033[38;5;{n}m"

# 256-color background
def bg256(n):
    return f"\033[48;5;{n}m"

# ── Terminal ────────────────────────────────────────────────────────────────────
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

# ── Glitch character palette ───────────────────────────────────────────────────
# Heavy blocks / half-blocks / box-drawing / braille / special symbols
BLOCK_CHARS = list("█▓▒░▀▄▌▐■□▪▫▬▲▶▼◀●○◆◇★☆")
BOX_CHARS   = list("─│┌┐└┘├┤┬┴┼╔╗╚╝╠╣╦╩╬═║")
BRAILLE     = list("⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟")
SYMBOLS     = list("@#$%^&*!?~<>{}[]|\\;:,./`'\"")
BINARY      = list("01")
HEX_CHARS   = list("0123456789ABCDEF")
GLITCH_ALL  = BLOCK_CHARS + BOX_CHARS + SYMBOLS + BINARY * 4 + HEX_CHARS + [" "] * 8

# ── Color palettes for TV static effect ───────────────────────────────────────
# True TV static mixes: white, gray, black + saturated color spikes
WHITE_GRAY_IDX  = [231, 255, 254, 253, 252, 251, 250, 249, 248, 247, 246, 245, 244, 243, 242, 241, 240, 239, 238, 237, 236, 235, 234, 233, 232]
CYAN_IDX        = [51, 45, 39, 33, 27, 21, 159, 123, 87]
MAGENTA_IDX     = [201, 207, 213, 219, 225, 165, 171, 177, 183]
GREEN_IDX       = [46, 82, 118, 154, 190, 40, 34, 28, 22, 76]
RED_IDX         = [196, 197, 198, 199, 160, 124, 88, 52, 203]
YELLOW_IDX      = [226, 220, 214, 208, 202, 227, 228, 229, 230]
BLUE_IDX        = [21, 27, 33, 39, 45, 57, 63, 69, 75, 81]

ALL_STATIC_COLORS = (
    WHITE_GRAY_IDX * 6 +   # white/gray dominant like real TV static
    CYAN_IDX * 2 +
    MAGENTA_IDX * 2 +
    GREEN_IDX * 2 +
    RED_IDX +
    YELLOW_IDX +
    BLUE_IDX
)

def random_static_color():
    return random.choice(ALL_STATIC_COLORS)

# ── Horizontal scanline glitch effect ─────────────────────────────────────────
class ScanlineGlitch:
    """Simulates horizontal tearing/shifting artifacts."""
    def __init__(self, row, cols):
        self.row   = row
        self.shift = random.randint(-cols // 4, cols // 4)
        self.width = random.randint(cols // 8, cols // 2)
        self.ttl   = random.randint(1, 6)
        self.color = random.choice(ALL_STATIC_COLORS)

# ── Main render engine ─────────────────────────────────────────────────────────
def render_preboot(duration=2.8, next_command=None):
    """
    Play the TV-static glitch animation for `duration` seconds,
    then snap to black and optionally exec `next_command`.
    """
    hide_cursor()
    cols, rows = get_size()
    clear()

    start_time  = time.time()
    frame_count = 0

    # Screen buffer: 2D array of (char, fg_color_idx, bg_color_idx)
    buf = [[(random.choice(GLITCH_ALL), random_static_color(), random.choice([232, 233, 234, 235, 16])) for _ in range(cols)] for _ in range(rows)]

    # Active scanline glitches
    glitches = []

    # ── Phase config ───────────────────────────────────────────────────────────
    # Phase 0 (0.0 – 0.5s): instant full chaos
    # Phase 1 (0.5 – 1.5s): wild pulsing, color explosions, horizontal tears
    # Phase 2 (1.5 – 2.3s): rapid flicker, losing signal feel, blackouts
    # Phase 3 (2.3 – 2.8s): signal collapses, static clears row by row
    # Phase 4: snap to black

    def update_buffer(now, elapsed):
        nonlocal glitches

        phase = (
            0 if elapsed < 0.5 else
            1 if elapsed < 1.5 else
            2 if elapsed < 2.3 else
            3
        )

        # ── Spawn scanline glitches ────────────────────────────────────────────
        if phase in (1, 2) and random.random() < 0.4:
            for _ in range(random.randint(1, 5)):
                glitches.append(ScanlineGlitch(random.randint(0, rows - 1), cols))
        glitches = [g for g in glitches if g.ttl > 0]
        for g in glitches:
            g.ttl -= 1

        # ── Update each cell ──────────────────────────────────────────────────
        chaos_factor = {0: 0.95, 1: 0.8, 2: 0.5, 3: 0.2}[phase]

        # Determine blackout rows in phase 3
        collapse_rows = set()
        if phase == 3:
            pct = (elapsed - 2.3) / 0.5   # 0 → 1
            n_collapse = int(pct * rows * 1.2)
            # Rows collapse from bottom up (and random in middle)
            for r in range(rows - 1, max(-1, rows - 1 - n_collapse), -1):
                collapse_rows.add(r)
            # Random additional collapses
            for _ in range(int(pct * rows * 0.5)):
                collapse_rows.add(random.randint(0, rows - 1))

        for r in range(rows):
            if r in collapse_rows:
                buf[r] = [(" ", 232, 16) for _ in range(cols)]
                continue

            for c in range(cols):
                if random.random() > chaos_factor:
                    continue  # cell stays frozen this frame

                ch    = random.choice(GLITCH_ALL)
                fg    = random_static_color()
                bg_ch = random.choice([232, 233, 234, 235, 16, 16, 16, 16])  # mostly black BG

                # Phase-specific overrides
                if phase == 1:
                    # Color spikes: occasional rows turn solid neon
                    spike_chance = 0.05
                    if random.random() < spike_chance:
                        neon = random.choice(CYAN_IDX + MAGENTA_IDX + GREEN_IDX + RED_IDX + YELLOW_IDX)
                        fg   = neon
                        ch   = random.choice(BLOCK_CHARS + ["█"])

                elif phase == 2:
                    # More blackouts interspersed
                    if random.random() < 0.15:
                        ch = " "
                        fg = 16
                        bg_ch = 16

                buf[r][c] = (ch, fg, bg_ch)

        # ── Apply scanline glitch horizontal shifts ────────────────────────────
        for g in glitches:
            r = g.row
            if 0 <= r < rows:
                shifted = []
                for c in range(cols):
                    src_c = (c - g.shift) % cols
                    orig  = buf[r][src_c]
                    shifted.append((orig[0], g.color, orig[2]))
                buf[r] = shifted

    def render_buffer():
        """Write the entire buffer to stdout in one shot."""
        output = "\033[H"  # cursor to top-left, no clear (avoids flicker)
        for r in range(rows - 1):
            line = ""
            prev_fg = -1
            prev_bg = -1
            for c in range(cols):
                ch, fg, bg = buf[r][c]
                seg = ""
                if fg != prev_fg:
                    seg += fg256(fg)
                    prev_fg = fg
                if bg != prev_bg:
                    seg += bg256(bg)
                    prev_bg = bg
                seg += ch
                line += seg
            output += line + "\033[0m\r\n"
        sys.stdout.write(output)
        sys.stdout.flush()

    # ── Main animation loop ─────────────────────────────────────────────────────
    TARGET_FPS = 24
    frame_time = 1.0 / TARGET_FPS

    try:
        while True:
            loop_start = time.time()
            elapsed = loop_start - start_time

            if elapsed >= duration:
                break

            update_buffer(loop_start, elapsed)
            render_buffer()
            frame_count += 1

            sleep_time = frame_time - (time.time() - loop_start)
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        pass

    # ── SNAP TO BLACK ──────────────────────────────────────────────────────────
    # Three rapid white flashes then darkness — like a TV losing power
    for flash_col in [231, 255, 16]:
        output = "\033[H"
        for r in range(rows - 1):
            line = f"\033[38;5;{flash_col}m\033[48;5;{flash_col}m" + "█" * cols + RESET
            output += line + "\r\n"
        sys.stdout.write(output)
        sys.stdout.flush()
        time.sleep(0.04)

    clear()
    show_cursor()

    # ── LAUNCH NEXT COMMAND ────────────────────────────────────────────────────
    if next_command:
        os.execvp(next_command[0], next_command)


# ── CLI entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse, shlex

    parser = argparse.ArgumentParser(description="NYXUS Pre-Boot Glitch Screen")
    parser.add_argument("--duration", type=float, default=2.8,
                        help="Duration of glitch animation in seconds (default: 2.8)")
    parser.add_argument("--next",     type=str,   default=None,
                        help="Command to exec after animation (e.g. 'python3 nyxus_splash.py')")
    args = parser.parse_args()

    next_cmd = shlex.split(args.next) if args.next else None
    render_preboot(duration=args.duration, next_command=next_cmd)
