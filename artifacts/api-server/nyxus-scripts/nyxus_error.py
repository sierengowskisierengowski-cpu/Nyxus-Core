#!/usr/bin/env python3
"""
NYXUS — Full-Screen Error Takeover
Red binary matrix cascade with glowing ERROR text.
© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""


__nyxid__ = "4e59582d4a35572d323032362d53494552454e474f57534b492d4c4f434b4544"

def _nyx_integrity():
    try:
        _s = open(__file__, encoding="utf-8").read()
        assert "SIERENGOWSKI" in _s, "NYXUS: tamper detected"
    except (OSError, AssertionError) as _e:
        import sys as _sys; print(f"NYXUS SECURITY: {_e}", file=_sys.stderr)
_nyx_integrity()


import os
import sys
import time
import random
import threading
import signal

# ANSI color codes
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

# Red shades (using 256-color escape for depth)
def red256(n):
    """Return 256-color red shade. n: 0 (dark) → 5 (bright)"""
    codes = [
        "\033[38;5;52m",   # very dark red
        "\033[38;5;88m",   # dark red
        "\033[38;5;124m",  # medium dark red
        "\033[38;5;160m",  # medium red
        "\033[38;5;196m",  # bright red
        "\033[38;5;197m",  # hot red/pink
    ]
    return codes[min(n, len(codes) - 1)]

RED_DARK   = "\033[38;5;52m"
RED_MED    = "\033[38;5;124m"
RED_BRIGHT = "\033[38;5;196m"
RED_GLOW   = "\033[38;5;197m"
BG_BLACK   = "\033[40m"
BG_RED_DIM = "\033[48;5;52m"

def get_size():
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 120, 40

def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def hide_cursor():
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

def show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()

def move(row, col):
    sys.stdout.write(f"\033[{row};{col}H")
    sys.stdout.flush()

ERROR_ART = [
    r" ███████╗██████╗ ██████╗  ██████╗ ██████╗  ",
    r" ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗ ",
    r" █████╗  ██████╔╝██████╔╝██║   ██║██████╔╝ ",
    r" ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗ ",
    r" ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║ ",
    r" ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝",
]

# ── Matrix rain state ──────────────────────────────────────────────────────────
class MatrixColumn:
    def __init__(self, col, height):
        self.col = col
        self.height = height
        self.head = random.randint(0, height)
        self.length = random.randint(6, 20)
        self.speed = random.uniform(0.5, 2.0)
        self.last_update = time.time()
        self.chars = [random.choice("01") for _ in range(height)]
        self.color_idx = random.randint(0, 5)

    def tick(self, now):
        if now - self.last_update >= 1.0 / self.speed:
            self.head = (self.head + 1) % self.height
            self.chars[self.head] = random.choice("01 01 01  ")
            self.last_update = now

    def char_at(self, row):
        dist = (row - self.head) % self.height
        if dist == 0:
            return self.chars[row], 5  # head - brightest
        elif dist <= self.length:
            brightness = max(0, 5 - int(dist * 5 / self.length))
            return self.chars[row], brightness
        else:
            return " ", -1  # invisible


def render_error(
    command="<unknown>",
    exit_code=1,
    location="<unknown>",
    message="A critical failure has occurred. The system cannot continue.",
    retry_callback=None,
    shell_callback=None,
):
    """
    Full-screen red binary matrix error takeover.

    Args:
        command: The command that failed
        exit_code: Non-zero exit code
        location: File/module/line where it failed
        message: Human-readable error description
        retry_callback: Optional callable for [R] Retry
        shell_callback: Optional callable for [S] Shell
    """
    hide_cursor()
    cols, rows = get_size()
    clear()

    columns = [MatrixColumn(c, rows) for c in range(cols)]

    logo_row_start = max(3, (rows // 2) - 6)
    logo_col_start = max(0, (cols - len(ERROR_ART[0])) // 2)
    detail_row     = logo_row_start + len(ERROR_ART) + 2
    menu_row       = rows - 4

    copyright = "© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED"
    cp_col    = max(0, (cols - len(copyright)) // 2)

    start_time = time.time()
    phase = 0  # 0 = rain only, 1 = rain + logo, 2 = static with menu

    frame_delay = 0.05
    frame = 0

    # Pre-build screen buffer (rows × cols chars)
    screen = [[" "] * cols for _ in range(rows)]
    screen_color = [[-1] * cols for _ in range(rows)]

    def write_screen():
        buf = "\033[H"  # move to top-left without clearing
        for r in range(rows - 1):
            line = ""
            for c in range(cols):
                ch = screen[r][c]
                ci = screen_color[r][c]
                if ci < 0:
                    line += f"{BG_BLACK} "
                else:
                    line += f"{BG_BLACK}{red256(ci)}{ch}"
            line += RESET
            buf += line + "\r\n"
        sys.stdout.write(buf)
        sys.stdout.flush()

    def draw_rain(now):
        for col in columns:
            col.tick(now)
            for r in range(rows - 1):
                ch, brightness = col.char_at(r)
                screen[r][col.col] = ch
                screen_color[r][col.col] = brightness

    def draw_logo_overlay():
        for i, line in enumerate(ERROR_ART):
            r = logo_row_start + i
            if r >= rows - 1:
                break
            for j, ch in enumerate(line):
                c = logo_col_start + j
                if c >= cols:
                    break
                if ch != " ":
                    screen[r][c] = ch
                    screen_color[r][c] = 5  # max brightness for logo

    def draw_glow_halo():
        # One row above/below logo in medium red
        for i in range(-1, len(ERROR_ART) + 1):
            r = logo_row_start + i
            if 0 <= r < rows - 1:
                for c in range(max(0, logo_col_start - 2), min(cols, logo_col_start + len(ERROR_ART[0]) + 2)):
                    if screen_color[r][c] < 3:
                        screen[r][c] = "░" if random.random() < 0.3 else " "
                        screen_color[r][c] = 3

    def draw_details():
        lines = [
            f"  CMD  : {command}",
            f"  EXIT : {exit_code}",
            f"  LOC  : {location}",
            f"  MSG  : {message[:cols - 12]}",
        ]
        for i, text in enumerate(lines):
            r = detail_row + i
            if r >= rows - 1:
                break
            for j, ch in enumerate(text[:cols]):
                screen[r][j] = ch
                screen_color[r][j] = 4

    def draw_menu():
        menu_text = "  [R] RETRY    [S] DROP TO SHELL    [Q] QUIT NYXUS  "
        mr = menu_row
        if mr < rows - 1:
            for j, ch in enumerate(menu_text[:cols]):
                screen[mr][j] = ch
                screen_color[mr][j] = 5

        bar = "─" * cols
        br = menu_row - 1
        if br >= 0:
            for j, ch in enumerate(bar[:cols]):
                screen[br][j] = ch
                screen_color[br][j] = 2

    def draw_copyright():
        r = rows - 2
        if r < rows:
            for j, ch in enumerate(copyright[:cols]):
                c = cp_col + j
                if c < cols:
                    screen[r][c] = ch
                    screen_color[r][c] = 1

    running = True

    try:
        while running:
            now = time.time()
            elapsed = now - start_time
            frame += 1

            draw_rain(now)

            if elapsed > 0.8:
                draw_glow_halo()
                draw_logo_overlay()

            if elapsed > 1.5:
                draw_details()
                draw_copyright()

            if elapsed > 2.2:
                draw_menu()

            write_screen()
            time.sleep(frame_delay)

            # After logo is shown and menu is drawn, stop animating rain
            if elapsed > 3.5:
                # Static final frame — just redraw and wait for input
                break

        # Final static render
        draw_rain(time.time())
        draw_glow_halo()
        draw_logo_overlay()
        draw_details()
        draw_copyright()
        draw_menu()
        write_screen()

        # Move cursor to bottom for input
        move(rows, 1)
        sys.stdout.write(f"\n{RED_BRIGHT}{BOLD}NYXUS ERROR > {RESET}")
        sys.stdout.flush()
        show_cursor()

        choice = input().strip().upper()

        if choice == "R" and retry_callback:
            retry_callback()
        elif choice == "S" and shell_callback:
            shell_callback()
        elif choice == "Q":
            clear()
            sys.exit(exit_code)
        else:
            clear()
            sys.exit(exit_code)

    except KeyboardInterrupt:
        clear()
        show_cursor()
        sys.exit(130)


# ── CLI entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NYXUS Error Screen")
    parser.add_argument("--command",   default="<unknown>", help="Failed command")
    parser.add_argument("--exit-code", default=1, type=int,  help="Exit code")
    parser.add_argument("--location",  default="<unknown>", help="Error location")
    parser.add_argument("--message",   default="A critical failure has occurred.",
                        help="Error message")
    args = parser.parse_args()

    render_error(
        command=args.command,
        exit_code=args.exit_code,
        location=args.location,
        message=args.message,
    )
