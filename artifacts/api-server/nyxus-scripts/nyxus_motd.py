#!/usr/bin/env python3
"""
NYXUS — Message of the Day (MOTD)
Loaded weapons terminal. Dense. Aggressive. Unforgettable.
© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""

import os
import re
import sys
import time
import random

# ── ANSI helpers ──────────────────────────────────────────────────────────────
_ansi = re.compile(r'\x1b\[[0-9;]*m')

def _vis_len(s):
    return len(_ansi.sub('', s))

def _vis_truncate(s, max_len):
    if max_len <= 0:
        return ""
    visible = 0
    result  = []
    i = 0
    while i < len(s):
        if s[i] == '\033' and i + 1 < len(s) and s[i + 1] == '[':
            j = i + 2
            while j < len(s) and s[j] not in 'mABCDEFGHJKLMSTfn':
                j += 1
            result.append(s[i:j + 1])
            i = j + 1
        else:
            if visible >= max_len:
                break
            result.append(s[i])
            visible += 1
            i += 1
    return ''.join(result)

# ── Color constants ───────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

# Standard
RED     = "\033[31m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
CYAN    = "\033[36m"
WHITE   = "\033[37m"
MAGENTA = "\033[35m"

# Bright
BRED     = "\033[91m"
BGREEN   = "\033[92m"
BYELLOW  = "\033[93m"
BBLUE    = "\033[94m"
BMAGENTA = "\033[95m"
BCYAN    = "\033[96m"
BWHITE   = "\033[97m"

# 256-color palette
def c256(n):   return f"\033[38;5;{n}m"
def bg256(n):  return f"\033[48;5;{n}m"

BG_BLACK = "\033[40m"

# Named 256-color aliases
_DPURPLE = c256(54)    # deep purple — far halo
_HPURPLE = c256(93)    # hot purple
_EPURPLE = c256(135)   # electric purple
_NPINK   = c256(213)   # neon pink  — hottest core
_GOLD    = c256(220)   # gold
_AMBER   = c256(214)   # hot amber / orange
_LIME    = c256(118)   # toxic lime green
_DRED    = c256(88)    # deep red
_MRED    = c256(160)   # medium red
_BRTRED  = c256(196)   # bright red
_TEAL    = c256(51)    # electric teal

# ── Terminal size ─────────────────────────────────────────────────────────────
def get_size():
    try:
        s = os.get_terminal_size()
        return s.columns, s.lines
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

# ── NYXUS block logo — solid █ letters ───────────────────────────────────────
_N = ["██   ██", "███  ██", "██ █ ██", "██  ███", "██   ██"]
_Y = ["██  ██ ", " █████ ", "  ███  ", "  ███  ", "  ███  "]
_X = ["██   ██", " ██ ██ ", "  ███  ", " ██ ██ ", "██   ██"]
_U = ["██   ██", "██   ██", "██   ██", "██   ██", " █████ "]
_S = [" █████ ", "██     ", " █████ ", "     ██", " █████ "]
NYXUS_BLOCK = ["  ".join([_N[i],_Y[i],_X[i],_U[i],_S[i]]) for i in range(5)]

# Logo gradient: deep purple halo → hot → electric → neon pink core → back
_LOGO_COLORS = [_HPURPLE, _EPURPLE, _NPINK, _EPURPLE, _HPURPLE]

# ── Big X logo (center panel) — 26 wide × 18 rows ────────────────────────────
# Colored dynamically in render; these are the raw shapes
BIG_X_RAW = [
    "████▓░              ░▓████",
    " ████▓░            ░▓████ ",
    "  ████▓░          ░▓████  ",
    "   ████▓░        ░▓████   ",
    "    ████▓░      ░▓████    ",
    "     ████▓░    ░▓████     ",
    "      ████▓░  ░▓████      ",
    "       ████████████       ",
    "        ░░██████░░        ",   # center
    "       ████████████       ",
    "      ████▓░  ░▓████      ",
    "     ████▓░    ░▓████     ",
    "    ████▓░      ░▓████    ",
    "   ████▓░        ░▓████   ",
    "  ████▓░          ░▓████  ",
    " ████▓░            ░▓████ ",
    "████▓░              ░▓████",
    "────────  N · Y · X  ─────",
]

# Per-row colors for the X (outer→center→outer gradient)
_X_ROW_COLORS = [
    _DPURPLE, _DPURPLE, _HPURPLE, _HPURPLE,
    _EPURPLE, _EPURPLE, _NPINK,
    _GOLD + BOLD,        # crossover
    _GOLD + BOLD,        # center
    _GOLD + BOLD,        # crossover
    _NPINK, _EPURPLE,
    _EPURPLE, _HPURPLE, _HPURPLE,
    _DPURPLE, _DPURPLE,
    _AMBER + DIM,        # label row
]

# ── Tool names ────────────────────────────────────────────────────────────────
TOOLS = [
    ("nmap",        BGREEN,    BOLD),
    ("metasploit",  _NPINK,    BOLD),
    ("hashcat",     _AMBER,    BOLD),
    ("wireshark",   _TEAL,     BOLD),
    ("hydra",       BRED,      BOLD),
    ("sqlmap",      BGREEN,    ""),
    ("aircrack",    _AMBER,    BOLD),
    ("volatility",  _NPINK,    ""),
    ("ghidra",      _TEAL,     BOLD),
    ("john",        BRED,      ""),
    ("burpsuite",   BWHITE,    BOLD),
    ("nikto",       BGREEN,    BOLD),
    ("gobuster",    _AMBER,    ""),
    ("bettercap",   _NPINK,    BOLD),
    ("radare2",     _TEAL,     ""),
    ("binwalk",     BRED,      BOLD),
    ("foremost",    BGREEN,    ""),
    ("netcat",      _AMBER,    BOLD),
    ("tcpdump",     _NPINK,    ""),
    ("mimikatz",    BWHITE,    BOLD),
    ("exploitdb",   BGREEN,    ""),
    ("maltego",     _NPINK,    BOLD),
    ("recon-ng",    _TEAL,     ""),
    ("SET",         _AMBER,    BOLD),
    ("beef-xss",    BRED,      ""),
    ("shodan",      _TEAL,     BOLD),
    ("wifite",      _AMBER,    ""),
    ("msfvenom",    _NPINK,    BOLD),
    ("crunch",      BRED,      ""),
    ("responder",   BGREEN,    BOLD),
    ("impacket",    _TEAL,     BOLD),
    ("bloodhound",  BWHITE,    ""),
    ("powersploit", _NPINK,    ""),
    ("cobalt",      _AMBER,    BOLD),
    ("empire",      BRED,      BOLD),
    ("yersinia",    BGREEN,    ""),
    ("scapy",       _TEAL,     BOLD),
    ("frida",       _NPINK,    ""),
    ("angr",        _AMBER,    BOLD),
    ("pwndbg",      BRED,      ""),
]

GLITCH = list("!@#$%^&*()_+-=[]{}|;:,.<>?/\\~`")

def _glitch(text, intensity=0.12):
    return "".join(random.choice(GLITCH) if random.random() < intensity else c for c in text)

# ── Binary stream generator ───────────────────────────────────────────────────
_BIN_CHARS = list("01") * 6 + list("·░▒▓") + list("0123456789ABCDEF")

def _binary_row(cols, hi_color, lo_color, hi_prob=0.18):
    out = ""
    for _ in range(cols):
        ch = random.choice(_BIN_CHARS)
        if random.random() < hi_prob:
            out += f"{hi_color}{BOLD}{ch}"
        else:
            out += f"{lo_color}{DIM}{ch}"
    return out + RESET

def _hex_row(cols, color):
    chars = "0123456789ABCDEFabcdef :;.-><[]{}|"
    out = ""
    for _ in range(cols):
        ch = random.choice(chars)
        shade = BOLD if random.random() < 0.2 else DIM
        out += f"{color}{shade}{ch}"
    return out + RESET

# ── Build tool cascade (chaotic 5 rows) ──────────────────────────────────────
def _tool_cascade(cols):
    prefixes  = ["//", ">>", "~~", "##", "{{", "[[", "--", "++", "::"]
    suffixes  = ["//", "<<", "~~", "##", "}}", "]]", "--", "++", "::"]
    separators = ["  ", "   ", "····", "   //   ", "  ·  ", "  |  "]

    shuffled = TOOLS[:]
    random.shuffle(shuffled)

    # Distribute tools into 5 rows
    rows_content = [[] for _ in range(5)]
    for idx, tool_data in enumerate(shuffled):
        rows_content[idx % 5].append(tool_data)

    # Row-level color tints for variety
    row_tints = [_BRTRED, BGREEN, _AMBER, _NPINK, _EPURPLE]
    row_dim   = [_DRED,   DIM+GREEN, DIM+YELLOW, _DPURPLE, _HPURPLE]

    lines = []
    for row_idx, row_tools in enumerate(rows_content):
        if not row_tools:
            continue
        parts = []
        current_len = 0
        for (name, color, style) in row_tools:
            px  = random.choice(prefixes)
            sx  = random.choice(suffixes)
            sep = random.choice(separators)
            display = f"{px}{name}{sx}"

            # Glitch some names slightly
            if random.random() < 0.2:
                display = _glitch(display, 0.08)

            chunk_vis = len(display)
            if current_len + chunk_vis + len(_ansi.sub('', sep)) > cols - 2:
                break
            parts.append(f"{color}{style}{display}{RESET}")
            current_len += chunk_vis + len(_ansi.sub('', sep))
            parts.append(f"{row_dim[row_idx]}{sep}{RESET}")

        # Pad remaining width with dim noise
        line_vis  = sum(len(_ansi.sub('', p)) for p in parts)
        remaining = cols - 2 - line_vis
        if remaining > 0:
            noise = ""
            nc = row_tints[row_idx]
            for _ in range(remaining):
                if random.random() < 0.08:
                    noise += f"{nc}{DIM}{random.choice(GLITCH)}{RESET}"
                else:
                    noise += " "
            parts.append(noise)

        lines.append(" " + "".join(parts))

    return lines

# ── Main render ───────────────────────────────────────────────────────────────
def render_motd():
    hide_cursor()
    cols, rows = get_size()
    clear()
    sys.stdout.write(BG_BLACK)

    lines_out = []

    # ─── TOP BORDER ────────────────────────────────────────────────────────────
    lines_out.append(f"{_BRTRED}{BOLD}{'█' * cols}{RESET}")
    lines_out.append(f"{_DRED}{'▓' * cols}{RESET}")

    # ─── NYXUS BLOCK LOGO ─────────────────────────────────────────────────────
    logo_w   = len(NYXUS_BLOCK[0])
    logo_pad = max(0, (cols - logo_w) // 2)
    avail_w  = cols - logo_pad
    ps       = " " * logo_pad

    halo = NYXUS_BLOCK[0].replace("█", "░")[:avail_w]
    lines_out.append(f"{ps}{_DPURPLE}{DIM}{halo}{RESET}")
    for line, col_code in zip(NYXUS_BLOCK, _LOGO_COLORS):
        lines_out.append(f"{ps}{col_code}{BOLD}{line[:avail_w]}{RESET}")
    lines_out.append(f"{ps}{_DPURPLE}{DIM}{halo}{RESET}")

    # ─── TAGLINE ───────────────────────────────────────────────────────────────
    tag = "[ S I L E N T  ·  D A R K  ·  P U R E L Y   F U N C T I O N A L ]"
    tag = tag[:cols]
    tp  = max(0, (cols - len(tag)) // 2)
    lines_out.append(f"{' ' * tp}{DIM}{BGREEN}{tag}{RESET}")

    # ─── DIVIDER ───────────────────────────────────────────────────────────────
    lines_out.append(f"{_DRED}{DIM}{'═' * cols}{RESET}")

    # ─── TOOL CASCADE — 5 chaotic rows ────────────────────────────────────────
    for tc_line in _tool_cascade(cols):
        lines_out.append(tc_line)

    # ─── BINARY STREAMS — 3 rows ───────────────────────────────────────────────
    lines_out.append(_binary_row(cols, _BRTRED,  _DRED,    hi_prob=0.22))
    lines_out.append(_hex_row   (cols, BGREEN))
    lines_out.append(_binary_row(cols, _AMBER,   DIM+YELLOW, hi_prob=0.15))

    # ─── SECTION DIVIDER ──────────────────────────────────────────────────────
    div_body = f"{'─' * 10}[ SYSTEM ARMED · PAYLOAD LIVE · STEALTH MODE ACTIVE ]{'─' * 10}"
    div_body = div_body[:cols]
    div_pad  = max(0, (cols - len(div_body)) // 2)
    lines_out.append(f"{' ' * div_pad}{_NPINK}{BOLD}{div_body}{RESET}")

    # ─── 3-COLUMN: WARNING | BIG X | STATS ────────────────────────────────────
    x_w      = len(BIG_X_RAW[0])              # 26
    third    = max(1, cols // 3)
    x_col_w  = min(x_w + 2, third)            # center column budget

    WARNING = [
        f"{_BRTRED}{BOLD}!! WARNING !!!!{RESET}",
        f"{_BRTRED}{BOLD}!! WARNING !!!!{RESET}",
        f"{_MRED}{BOLD}UNAUTHORIZED ACCESS{RESET}",
        f"{_MRED}{BOLD}IS  PROHIBITED{RESET}",
        f"{_AMBER}{BOLD}ALL ACTIVITY IS{RESET}",
        f"{_AMBER}{BOLD}MONITORED 24/7{RESET}",
        f"{BRED}{BOLD}LOGGED REAL-TIME{RESET}",
        f"{BRED}VIOLATIONS WILL BE{RESET}",
        f"{BRED}PROSECUTED FULLY{RESET}",
        f"{_DRED}{DIM}─────────────────{RESET}",
        f"{_NPINK}{DIM}NYX-J5W-2026{RESET}",
        f"{_NPINK}{DIM}SIERENGOWSKI{RESET}",
        f"{_DPURPLE}{DIM}LOCKED·LOCKED{RESET}",
        f"{_HPURPLE}{DIM}LOCKED·LOCKED{RESET}",
        f"{_EPURPLE}{DIM}· · · · · · ·{RESET}",
        f"{_NPINK}◆ SYSTEM ARMED ◆{RESET}",
        f"{_AMBER}{DIM}BREACH LOGGED{RESET}",
        f"{BRED}{DIM}YOU ARE WATCHED{RESET}",
    ]

    STATS = [
        f"{_EPURPLE}KERNEL {_NPINK}{BOLD}6.6.0-nyxus{RESET}",
        f"{_EPURPLE}ARCH   {BWHITE}{BOLD}x86_64{RESET}",
        f"{_EPURPLE}TOOLS  {_AMBER}{BOLD}200+{RESET}",
        f"{_EPURPLE}PAYLD  {BGREEN}{BOLD}LOADED{RESET}",
        f"{_EPURPLE}NET    {BGREEN}{BOLD}STEALTH{RESET}",
        f"{_EPURPLE}PRIV   {BRED}{BOLD}ROOT{RESET}",
        f"{_EPURPLE}SIG    {_AMBER}{BOLD}MASKED{RESET}",
        f"{_EPURPLE}ENC    {BGREEN}{BOLD}AES-256{RESET}",
        f"{_EPURPLE}STATUS {BGREEN}{BOLD}OPERATIONAL{RESET}",
        f"{_EPURPLE}MODE   {BRED}{BOLD}OFFENSIVE{RESET}",
        f"{_EPURPLE}IDS    {_AMBER}{BOLD}BYPASSED{RESET}",
        f"{_EPURPLE}VPN    {BGREEN}{BOLD}ACTIVE{RESET}",
        f"{_EPURPLE}TOR    {BGREEN}{BOLD}ROUTING{RESET}",
        f"{_EPURPLE}CRYPT  {_NPINK}{BOLD}ARMED{RESET}",
        f"{_EPURPLE}EXPL   {_AMBER}{BOLD}READY{RESET}",
        f"{_EPURPLE}ANON   {BGREEN}{BOLD}MAXIMUM{RESET}",
        f"{_EPURPLE}HASH   {BGREEN}{BOLD}CRACKING{RESET}",
        f"{_EPURPLE}PKT    {_AMBER}{BOLD}SNIFFING{RESET}",
    ]

    max_rows_3col = max(len(WARNING), len(BIG_X_RAW), len(STATS))
    left_w  = third
    right_w = cols - left_w - x_col_w - 2

    for i in range(max_rows_3col):
        # Left: warning
        left = WARNING[i] if i < len(WARNING) else ""
        left = _vis_truncate(left, left_w - 1)
        lv   = _vis_len(left)
        l_pad = max(0, left_w - lv)

        # Center: X logo
        if i < len(BIG_X_RAW):
            x_raw = BIG_X_RAW[i][:x_col_w - 1]
            col_c = _X_ROW_COLORS[i] if i < len(_X_ROW_COLORS) else _HPURPLE
            mid   = f"{col_c}{BOLD}{x_raw}{RESET}"
        else:
            mid   = ""
        mv = _vis_len(mid)
        m_pad = max(0, x_col_w - mv)

        # Right: stats
        right = STATS[i] if i < len(STATS) else ""
        right = _vis_truncate(right, max(0, right_w - 1))

        lines_out.append(f" {left}{' ' * l_pad}{mid}{' ' * m_pad}{right}")

    # ─── BINARY STREAMS — 2 rows ───────────────────────────────────────────────
    lines_out.append(_binary_row(cols, _NPINK,  _DPURPLE, hi_prob=0.20))
    lines_out.append(_binary_row(cols, _TEAL,   DIM+CYAN, hi_prob=0.12))

    # ─── SECTION DIVIDER ──────────────────────────────────────────────────────
    div2 = f"{'─' * 8}[ EXPLOIT FRAMEWORK · TOOLS LOADED · WEAPONS HOT ]{'─' * 8}"
    div2 = div2[:cols]
    d2p  = max(0, (cols - len(div2)) // 2)
    lines_out.append(f"{' ' * d2p}{_AMBER}{BOLD}{div2}{RESET}")

    # ─── 2-COLUMN: BOOT STATUS | QUICK REFERENCE ──────────────────────────────
    half = cols // 2

    HC = _EPURPLE       # header color
    CC = DIM + WHITE    # comment
    VC = BGREEN         # value/command

    BOOT_STATUS = [
        (f"{BGREEN}{BOLD}EXPLOIT FRAMEWORK{RESET}",   f"{DIM}{BGREEN}[OK]{RESET}"),
        (f"{_TEAL}NETWORK INTERFACES{RESET}",          f"{DIM}{_TEAL}[READY]{RESET}"),
        (f"{_AMBER}ANONYMOUS ROUTING{RESET}",           f"{DIM}{_AMBER}[TOR]{RESET}"),
        (f"{_NPINK}PAYLOAD GENERATOR{RESET}",           f"{DIM}{_NPINK}[ARMED]{RESET}"),
        (f"{BRED}IDS BYPASS MODULE{RESET}",             f"{DIM}{BRED}[ACTIVE]{RESET}"),
        (f"{BWHITE}CRYPTO ENGINE AES-256{RESET}",       f"{DIM}{BWHITE}[OK]{RESET}"),
        (f"{BGREEN}HASHCRACK ENGINE{RESET}",             f"{DIM}{BGREEN}[LOADED]{RESET}"),
        (f"{_TEAL}PACKET SNIFFER{RESET}",               f"{DIM}{_TEAL}[SILENT]{RESET}"),
        (f"{_AMBER}VPN TUNNEL LAYER{RESET}",             f"{DIM}{_AMBER}[UP]{RESET}"),
        (f"{_NPINK}ROOTKIT STEALTH LAYER{RESET}",        f"{DIM}{_NPINK}[MASKED]{RESET}"),
        (f"{BGREEN}POST-EXPLOIT FRAMEWORK{RESET}",       f"{DIM}{BGREEN}[PRIMED]{RESET}"),
        (f"{_TEAL}LATERAL MOVEMENT ENG{RESET}",          f"{DIM}{_TEAL}[READY]{RESET}"),
    ]

    QUICK_REF = [
        f"{HC}{BOLD}── QUICK WEAPONS REFERENCE ──────{RESET}",
        f"{VC}nmap -sV -sC -O -p-{RESET} {CC}<ip>   # full scan{RESET}",
        f"{VC}hydra -l root -P wl{RESET}   {CC}<ip>   # brute ssh{RESET}",
        f"{VC}sqlmap -u{RESET} {CC}<url>{VC} --dbs --dump{RESET}  {CC}# sql{RESET}",
        f"{VC}msfconsole -q -r{RESET}      {CC}<rc>   # msf auto{RESET}",
        f"{VC}airmon-ng start wlan0{RESET}          {CC}# monitor{RESET}",
        f"{VC}hashcat -m 0 -a 0 h wl{RESET}         {CC}# crack{RESET}",
        f"{VC}gobuster dir -u{RESET} {CC}<url>{VC} -w wl{RESET}   {CC}# fuzz{RESET}",
        f"{VC}bloodhound-python -d{RESET}  {CC}<dom>  # ad map{RESET}",
        f"{VC}volatility -f mem imageinfo{RESET}     {CC}# mem{RESET}",
        f"{VC}frida-ps -Ua{RESET}                    {CC}# mobile{RESET}",
        f"{HC}{BOLD}── NYX-J5W-2026 · SIERENGOWSKI ──{RESET}",
    ]

    STATUS_MAX = 9
    PHRASE_MAX = half - 2 - STATUS_MAX - 1
    n_rows2    = max(len(BOOT_STATUS), len(QUICK_REF))

    for i in range(n_rows2):
        if i < len(BOOT_STATUS):
            phrase, status = BOOT_STATUS[i]
            phrase    = _vis_truncate(phrase, max(1, PHRASE_MAX))
            pv        = _vis_len(phrase)
            sv        = _vis_len(status)
            inner_gap = max(1, half - 2 - pv - sv)
            left_cell = f"  {phrase}{' ' * inner_gap}{status}"
            lv        = _vis_len(left_cell)
        else:
            left_cell = ""
            lv        = 0

        right_avail = cols - half - 1
        if i < len(QUICK_REF):
            right_cell = _vis_truncate(QUICK_REF[i], max(0, right_avail))
        else:
            right_cell = ""

        pad = max(0, half - lv)
        lines_out.append(f"{left_cell}{' ' * pad} {right_cell}")

    # ─── FINAL BINARY STREAM ──────────────────────────────────────────────────
    lines_out.append(_binary_row(cols, _AMBER, _DRED, hi_prob=0.10))

    # ─── BOTTOM DIVIDER ───────────────────────────────────────────────────────
    lines_out.append(f"{DIM}{_BRTRED}{'─' * cols}{RESET}")

    # ─── COPYRIGHT ────────────────────────────────────────────────────────────
    copyright_text = "© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED"
    cp_pad = max(0, (cols - len(copyright_text)) // 2)
    lines_out.append(f"{' ' * cp_pad}{DIM}{WHITE}{copyright_text}{RESET}")

    # ─── BOTTOM BORDER ────────────────────────────────────────────────────────
    lines_out.append(f"{_DRED}{'▓' * cols}{RESET}")
    lines_out.append(f"{_BRTRED}{BOLD}{'█' * cols}{RESET}")

    # ─── RENDER ───────────────────────────────────────────────────────────────
    for line in lines_out:
        print(line)

    # Fill any remaining terminal rows with scrolling hex noise
    rendered  = len(lines_out)
    remaining = rows - rendered - 2
    noise_colors = [DIM + _DRED, DIM + _DPURPLE, DIM + GREEN, DIM + YELLOW]
    for _ in range(max(0, remaining)):
        nc  = random.choice(noise_colors)
        row = ""
        for _c in range(cols):
            row += nc + (random.choice(_BIN_CHARS) if random.random() < 0.4 else " ")
        print(row + RESET)

    # ─── HOLD ─────────────────────────────────────────────────────────────────
    show_cursor()
    sys.stdout.write(f"\n{_NPINK}{BOLD}NYXUS > {RESET}")
    sys.stdout.flush()
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass
    clear()


# ── CLI entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    render_motd()
