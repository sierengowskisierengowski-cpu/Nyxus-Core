#!/usr/bin/env python3
"""
NYXUS — Message of the Day (MOTD)
Dense hacker aesthetic terminal banner.
© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""

import os
import sys
import time
import random
import shutil

# ANSI color codes
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

# Foreground colors
BLACK   = "\033[30m"
RED     = "\033[31m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
BLUE    = "\033[34m"
MAGENTA = "\033[35m"
CYAN    = "\033[36m"
WHITE   = "\033[37m"

# Bright foreground
BRED     = "\033[91m"
BGREEN   = "\033[92m"
BYELLOW  = "\033[93m"
BBLUE    = "\033[94m"
BMAGENTA = "\033[95m"
BCYAN    = "\033[96m"
BWHITE   = "\033[97m"

# Background
BG_BLACK = "\033[40m"
BG_RED   = "\033[41m"

def get_size():
    size = shutil.get_terminal_size((120, 40))
    return size.columns, size.lines

def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def move(row, col):
    sys.stdout.write(f"\033[{row};{col}H")

def hide_cursor():
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

def show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()

TOOL_NAMES = [
    ("nmap",        BGREEN,   BOLD,   5),
    ("metasploit",  BMAGENTA, BOLD,   8),
    ("hashcat",     BYELLOW,  "",     6),
    ("wireshark",   BCYAN,    BOLD,   9),
    ("hydra",       BRED,     BOLD,   5),
    ("sqlmap",      BGREEN,   "",     6),
    ("aircrack",    BYELLOW,  BOLD,   8),
    ("volatility",  BMAGENTA, "",     9),
    ("ghidra",      BCYAN,    BOLD,   6),
    ("john",        BRED,     "",     4),
    ("burpsuite",   BWHITE,   BOLD,   8),
    ("nikto",       BGREEN,   BOLD,   5),
    ("gobuster",    BYELLOW,  "",     8),
    ("bettercap",   BMAGENTA, BOLD,   9),
    ("radare2",     BCYAN,    "",     7),
    ("binwalk",     BRED,     BOLD,   7),
    ("foremost",    BGREEN,   "",     8),
    ("netcat",      BYELLOW,  BOLD,   7),
    ("tcpdump",     BMAGENTA, "",     7),
    ("mimikatz",    BWHITE,   BOLD,   8),
    ("exploitdb",   BGREEN,   "",     9),
    ("maltego",     BMAGENTA, BOLD,   7),
    ("recon-ng",    BCYAN,    "",     8),
    ("set",         BYELLOW,  BOLD,   3),
    ("beef",        BRED,     "",     4),
    ("w3af",        BGREEN,   BOLD,   4),
    ("shodan",      BCYAN,    BOLD,   6),
    ("wifite",      BYELLOW,  "",     6),
    ("msfvenom",    BMAGENTA, BOLD,   8),
    ("crunch",      BRED,     "",     6),
]

NYXUS_LOGO = [
    r"  _   _  __   __ __  __  _   _  _____  ",
    r" | \ | | \ \ / /|  \/  || | | ||  ___| ",
    r" |  \| |  \ V / | |\/| || | | || |___  ",
    r" | |\  |   | |  | |  | || |_| ||___ |  ",
    r" |_| \_|   |_|  |_|  |_| \___/ |___/   ",
]

SKULL_ART = [
    r"  ░░░░░░░░░░░░░░░░░░  ",
    r"  ▓▓▓▓▓▓░   ░▓▓▓▓▓▓  ",
    r"   ░▓▓▓▓▓▓ ▓▓▓▓▓▓░   ",
    r"     ░▓▓▓▓▓▓▓▓▓▓░    ",
    r"       ░▓▓▓▓▓▓░       ",
    r"     ░▓▓▓▓▓▓▓▓▓▓░    ",
    r"   ░▓▓▓▓▓▓ ▓▓▓▓▓▓░   ",
    r"  ▓▓▓▓▓▓░   ░▓▓▓▓▓▓  ",
    r"  ░░── N · Y · X ──░░ ",
    r"  ░░░░░░░░░░░░░░░░░░  ",
]

GLITCH_CHARS = list("!@#$%^&*()_+-=[]{}|;:,.<>?/\\~`")
BINARY_CHARS = list("01")

def glitch_line(text, intensity=0.15):
    result = []
    for ch in text:
        if random.random() < intensity:
            result.append(random.choice(GLITCH_CHARS))
        else:
            result.append(ch)
    return "".join(result)

def render_motd():
    hide_cursor()
    cols, rows = get_size()
    clear()
    sys.stdout.write(BG_BLACK)

    lines_out = []

    # ─── TOP BORDER ────────────────────────────────────────────────────────────
    border_char = "█"
    top_border = f"{BRED}{BOLD}" + border_char * cols + RESET
    lines_out.append(top_border)

    # ─── NYXUS LOGO (centered, neon effect) ────────────────────────────────────
    logo_colors = [BMAGENTA, BCYAN, BMAGENTA, BCYAN, BMAGENTA]
    for i, line in enumerate(NYXUS_LOGO):
        pad = max(0, (cols - len(line)) // 2)
        color = logo_colors[i % len(logo_colors)]
        lines_out.append(f"{BG_BLACK}{color}{BOLD}{' ' * pad}{line}{RESET}")

    # ─── TAGLINE ───────────────────────────────────────────────────────────────
    tag = "[ S I L E N T . D A R K . P U R E L Y   F U N C T I O N A L ]"
    pad = max(0, (cols - len(tag)) // 2)
    lines_out.append(f"{' ' * pad}{DIM}{GREEN}{tag}{RESET}")
    lines_out.append("")

    # ─── DIVIDER ───────────────────────────────────────────────────────────────
    div = f"{DIM}{BRED}{'─' * cols}{RESET}"
    lines_out.append(div)

    # ─── TOOL SCATTER ──────────────────────────────────────────────────────────
    # Build a grid of tool name rows, filling width
    tool_rows = []
    current_row_parts = []
    current_len = 0

    shuffled = TOOL_NAMES[:]
    random.shuffle(shuffled)

    for (name, color, style, size) in shuffled:
        # Random ASCII decoration
        prefixes = ["[", "{", ">>", "//", "##", "~~"]
        suffixes = ["]", "}", "<<", "//", "##", "~~"]
        px = random.choice(prefixes)
        sx = random.choice(suffixes)
        display = f"{px}{name}{sx}"
        chunk = f"{color}{style}{display}{RESET}"
        chunk_len = len(display) + random.randint(2, 6)  # spacing
        if current_len + chunk_len > cols - 2:
            tool_rows.append("  ".join(current_row_parts))
            current_row_parts = []
            current_len = 0
        current_row_parts.append(chunk)
        current_len += chunk_len + 2

    if current_row_parts:
        tool_rows.append("  ".join(current_row_parts))

    # Add some glitch/binary filler rows between tool rows
    filler_colors = [BGREEN, BYELLOW, BMAGENTA, BBLUE, BRED]
    for i, row in enumerate(tool_rows):
        lines_out.append(f" {row}")
        if i % 2 == 0 and i < len(tool_rows) - 1:
            # mini binary filler
            frow = ""
            fc = random.choice(filler_colors)
            for _ in range(cols):
                frow += f"{DIM}{fc}" + random.choice(BINARY_CHARS + ["·", "░", "▒"])
            lines_out.append(frow + RESET)

    # ─── DIVIDER ───────────────────────────────────────────────────────────────
    lines_out.append(f"{DIM}{BMAGENTA}{'═' * cols}{RESET}")

    # ─── SKULL + SIDE TEXT LAYOUT ──────────────────────────────────────────────
    # Left: warning block, Center: Skull, Right: stats
    skull_col = max(0, (cols // 2) - 12)

    warning_lines = [
        f"{BRED}{BOLD}!! WARNING !!{RESET}",
        f"{BYELLOW}UNAUTHORIZED ACCESS{RESET}",
        f"{BYELLOW}IS STRICTLY PROHIBITED{RESET}",
        f"{RED}ALL ACTIVITY MONITORED{RESET}",
        f"{RED}AND LOGGED IN REAL-TIME{RESET}",
        f"{DIM}{WHITE}violators will be{RESET}",
        f"{DIM}{WHITE}prosecuted to the{RESET}",
        f"{DIM}{WHITE}fullest extent of law{RESET}",
        f"{BMAGENTA}NYX-J5W-2026{RESET}",
        f"{BMAGENTA}SIERENGOWSKI-LOCKED{RESET}",
    ]

    stat_lines = [
        f"{DIM}{GREEN}KERNEL: 6.6.0-nyxus{RESET}",
        f"{DIM}{GREEN}ARCH:   x86_64{RESET}",
        f"{DIM}{CYAN}TOOLS:  {BWHITE}200+{RESET}",
        f"{DIM}{CYAN}PAYLD:  {BWHITE}LOADED{RESET}",
        f"{DIM}{YELLOW}NET:    {BWHITE}STEALTH{RESET}",
        f"{DIM}{YELLOW}PRIV:   {BWHITE}ROOT{RESET}",
        f"{DIM}{MAGENTA}SIG:    {BWHITE}MASKED{RESET}",
        f"{DIM}{MAGENTA}ENC:    {BWHITE}AES-256{RESET}",
        f"{DIM}{RED}STATUS: {BGREEN}OPERATIONAL{RESET}",
        f"{DIM}{RED}MODE:   {BRED}OFFENSIVE{RESET}",
    ]

    skull_colored = [f"{BWHITE}{DIM}{s}{RESET}" for s in SKULL_ART]

    max_block = max(len(warning_lines), len(skull_colored), len(stat_lines))
    third = cols // 3

    for i in range(max_block):
        left  = warning_lines[i] if i < len(warning_lines) else ""
        mid   = skull_colored[i] if i < len(skull_colored) else ""
        right = stat_lines[i]    if i < len(stat_lines)    else ""

        # Strip ANSI to measure visible length
        import re
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        left_vis  = len(ansi_escape.sub('', left))
        mid_vis   = len(ansi_escape.sub('', mid))
        right_vis = len(ansi_escape.sub('', right))

        left_pad  = third - left_vis
        mid_pad   = third - mid_vis
        right_pad = third - right_vis

        line = f" {left}{' ' * max(0, left_pad)}{mid}{' ' * max(0, mid_pad)}{right}"
        lines_out.append(line)

    # ─── DIVIDER ───────────────────────────────────────────────────────────────
    lines_out.append(f"{DIM}{BCYAN}{'─' * cols}{RESET}")

    # ─── EXTRA HACKER TEXT BLOCK ───────────────────────────────────────────────
    hacker_phrases = [
        (f"{BGREEN}{BOLD}EXPLOIT FRAMEWORK LOADED{RESET}",            f"{DIM}{GREEN}[OK]{RESET}"),
        (f"{BCYAN}NETWORK INTERFACES INITIALIZED{RESET}",             f"{DIM}{CYAN}[READY]{RESET}"),
        (f"{BYELLOW}ANONYMOUS ROUTING ENABLED{RESET}",                f"{DIM}{YELLOW}[TOR OK]{RESET}"),
        (f"{BMAGENTA}PAYLOAD GENERATOR STANDING BY{RESET}",           f"{DIM}{MAGENTA}[ARMED]{RESET}"),
        (f"{BRED}INTRUSION DETECTION BYPASS{RESET}",                  f"{DIM}{RED}[ACTIVE]{RESET}"),
        (f"{BWHITE}CRYPTOGRAPHIC ENGINE INITIALIZED{RESET}",          f"{DIM}{WHITE}[AES OK]{RESET}"),
        (f"{BGREEN}PASSWORD CRACKER READY{RESET}",                    f"{DIM}{GREEN}[LOADED]{RESET}"),
        (f"{BCYAN}PACKET SNIFFER PASSIVE MODE{RESET}",                f"{DIM}{CYAN}[SILENT]{RESET}"),
    ]

    col_mid = cols // 2
    for phrase, status in hacker_phrases:
        import re
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        phrase_vis = len(ansi_escape.sub('', phrase))
        status_vis = len(ansi_escape.sub('', status))
        gap = max(4, col_mid - phrase_vis - status_vis)
        lines_out.append(f"  {phrase}{' ' * gap}{status}")

    # ─── BOTTOM BORDER ─────────────────────────────────────────────────────────
    lines_out.append(f"{DIM}{BRED}{'─' * cols}{RESET}")

    # ─── COPYRIGHT ─────────────────────────────────────────────────────────────
    copyright_text = "© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED"
    cp_pad = max(0, (cols - len(copyright_text)) // 2)
    lines_out.append(f"{' ' * cp_pad}{DIM}{WHITE}{copyright_text}{RESET}")

    # ─── BOTTOM BORDER ─────────────────────────────────────────────────────────
    lines_out.append(f"{BRED}{BOLD}" + border_char * cols + RESET)

    # ─── RENDER ALL LINES ──────────────────────────────────────────────────────
    for line in lines_out:
        print(line)

    # Fill remaining rows if needed
    import re
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    rendered_rows = len(lines_out)
    remaining = rows - rendered_rows - 2
    for _ in range(max(0, remaining)):
        # Random glitch filler rows at bottom
        row_color = random.choice([DIM + GREEN, DIM + BMAGENTA, DIM + BCYAN, DIM + BYELLOW])
        frow = row_color
        for _ in range(cols):
            frow += random.choice(BINARY_CHARS + ["·", "░", " ", " ", " "])
        print(frow + RESET)

    # ─── PROMPT ────────────────────────────────────────────────────────────────
    sys.stdout.write(f"\n{BG_BLACK}{BWHITE}{BOLD}")
    sys.stdout.write("  ██ NYXUS OS ██  Press [ENTER] to continue into the void... ")
    sys.stdout.write(RESET)
    sys.stdout.flush()
    show_cursor()

    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass

    clear()

if __name__ == "__main__":
    render_motd()
