#!/usr/bin/env python3
"""
NYXUS — Message of the Day (MOTD)
Fully responsive. Adapts to any terminal size. Never overflows. Never truncates.
© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""


__nyxid__ = "4e59582d4a35572d323032362d53494552454e474f57534b492d4c4f434b4544"

def _nyx_integrity():
    try:
        _s = open(__file__, encoding="utf-8").read()
        assert "SIERENGOWSKI" in _s, "NYXUS: tamper detected"
    except (OSError, AssertionError) as _e:
        import sys as _sys; print(f"NYXUS SECURITY: {_e}", file=_sys.stderr)

# ── NYXUS palette (single source of truth · rev r13) ────────────────
try:
    from nyxus_palette import (
        WHITE_PURE, WHITE_OFF, GREY_LIGHT, GREY_MID, GREY_TERTIARY,
        INK_FADED, INK_BLACK,
        GLASS_DARK, GLASS_DEEPER, GLASS_DEEPEST,
        HAIRLINE_WHITE, HAIRLINE_INK,
        SHADOW_INK_ACTIVE, SHADOW_INK_INACTIVE,
        RADIUS_CARD, RADIUS_PILL, RADIUS_INPUT,
        FONT_UI, FONT_MONO, FONT_DISPLAY,
        format_css, assert_no_forbidden,
    )
except Exception:
    # palette module is shipped alongside every NYXUS app via
    # nyxus_install.sh; if it's missing, fall back to literals so
    # the app still launches.
    WHITE_PURE='#ffffff'; WHITE_OFF='#e8edf5'; GREY_LIGHT='#c8ccd6'
    GREY_MID='#9aa0ad'; GREY_TERTIARY='#6a6e78'
    INK_FADED='#0a0a0a'; INK_BLACK='#000000'
    GLASS_DARK='rgba(8, 12, 20, 0.55)'
    GLASS_DEEPER='rgba(15, 20, 32, 0.72)'
    GLASS_DEEPEST='rgba(5, 7, 12, 0.92)'
    HAIRLINE_WHITE='rgba(255, 255, 255, 0.10)'
    HAIRLINE_INK='rgba(0, 0, 0, 0.45)'
    SHADOW_INK_ACTIVE='rgba(0, 0, 0, 0.65)'
    SHADOW_INK_INACTIVE='rgba(0, 0, 0, 0.20)'
    RADIUS_CARD=14; RADIUS_PILL=12; RADIUS_INPUT=10
    FONT_UI='Inter'; FONT_MONO='JetBrains Mono'; FONT_DISPLAY='Inter Display'
    def format_css(t):
        _d = {
            'WHITE_PURE': WHITE_PURE, 'WHITE_OFF': WHITE_OFF,
            'GREY_LIGHT': GREY_LIGHT, 'GREY_MID': GREY_MID,
            'GREY_TERTIARY': GREY_TERTIARY,
            'INK_FADED': INK_FADED, 'INK_BLACK': INK_BLACK,
            'GLASS_DARK': GLASS_DARK, 'GLASS_DEEPER': GLASS_DEEPER,
            'GLASS_DEEPEST': GLASS_DEEPEST,
            'HAIRLINE_WHITE': HAIRLINE_WHITE, 'HAIRLINE_INK': HAIRLINE_INK,
            'SHADOW_INK_ACTIVE': SHADOW_INK_ACTIVE,
            'SHADOW_INK_INACTIVE': SHADOW_INK_INACTIVE,
            'RADIUS_CARD': RADIUS_CARD, 'RADIUS_PILL': RADIUS_PILL,
            'RADIUS_INPUT': RADIUS_INPUT,
            'FONT_UI': FONT_UI, 'FONT_MONO': FONT_MONO,
            'FONT_DISPLAY': FONT_DISPLAY,
        }
        return t.format_map(_d)
    def assert_no_forbidden(*a, **k): pass
# ─────────────────────────────────────────────────────────────────────

_nyx_integrity()


import os
import re
import sys
import random

# ── ANSI helpers ──────────────────────────────────────────────────────────────
_ansi = re.compile(r'\x1b\[[0-9;]*m')

def _vis_len(s):
    return len(_ansi.sub('', s))

def _vis_truncate(s, max_len):
    """Truncate string to max_len visible chars, preserving ANSI codes."""
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

def _pad_to(s, width):
    """Return s padded/truncated so its visible length == width."""
    vl = _vis_len(s)
    if vl >= width:
        return _vis_truncate(s, width)
    return s + ' ' * (width - vl)

# ── Colors ────────────────────────────────────────────────────────────────────
RESET    = "\033[0m"
BOLD     = "\033[1m"
DIM      = "\033[2m"
BRED     = "\033[91m"
BGREEN   = "\033[92m"
BWHITE   = "\033[97m"
GREEN    = "\033[32m"
WHITE    = "\033[37m"

def c256(n): return f"\033[38;5;{n}m"

_DPURPLE = c256(54)
_HPURPLE = c256(93)
_EPURPLE = c256(135)
_NPINK   = c256(213)
_GOLD    = c256(220)
_AMBER   = c256(214)
_DRED    = c256(88)
_MRED    = c256(160)
_BRTRED  = c256(196)
_TEAL    = c256(51)
_LIME    = c256(118)

BG_BLACK = "\033[40m"

# ── Terminal ──────────────────────────────────────────────────────────────────
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

# ── Block letter definitions (7 wide × 5 tall each) ──────────────────────────
_N = ["██   ██","███  ██","██ █ ██","██  ███","██   ██"]
_Y = ["██  ██ "," █████ ","  ███  ","  ███  ","  ███  "]
_X = ["██   ██"," ██ ██ ","  ███  "," ██ ██ ","██   ██"]
_U = ["██   ██","██   ██","██   ██","██   ██"," █████ "]
_S = [" █████ ","██     "," █████ ","     ██"," █████ "]
NYXUS_BLOCK = ["  ".join([_N[i],_Y[i],_X[i],_U[i],_S[i]]) for i in range(5)]
_BLOCK_W    = len(NYXUS_BLOCK[0])   # 43
_LOGO_COLORS = [_HPURPLE, _EPURPLE, _NPINK, _EPURPLE, _HPURPLE]

# ── Dynamic X logo generator ──────────────────────────────────────────────────
def _make_x(w, h):
    """
    Generate an X art of exactly w chars wide, h rows tall.
    Last row is always the N·Y·X label.
    Returns a list of plain strings (no ANSI) — caller applies color.
    """
    w = max(4, w)
    h = max(2, h)
    rows_out = []

    body_h   = h - 1           # rows of actual X shape
    arm      = max(1, min(3, w // 7))   # arm thickness in chars

    for r in range(body_h):
        t = r / max(1, body_h - 1)   # 0.0 → 1.0
        ltr = int(t * (w - arm))     # left-to-right diagonal position
        rtl = w - arm - ltr          # right-to-left diagonal position

        row = [' '] * w
        for i in range(arm):
            # left-to-right arm: leading edge '░', body '▓', trailing '█'
            lp = ltr + i
            if 0 <= lp < w:
                row[lp] = '░' if i == 0 else ('▓' if i < arm - 1 else '█')
            # right-to-left arm: leading '█', body '▓', trailing '░'
            rp = rtl + i
            if 0 <= rp < w:
                row[rp] = '█' if i == 0 else ('▓' if i < arm - 1 else '░')

        rows_out.append(''.join(row))

    # Label row
    raw_label = "── N · Y · X ──"
    label     = raw_label[:w]
    lp        = max(0, (w - len(label)) // 2)
    rows_out.append((' ' * lp + label)[:w])

    return rows_out

def _color_x_row(line, r, total_rows):
    """Apply gradient color to an X row. Center = gold, edges = deep purple."""
    if total_rows <= 1:
        return f"{_GOLD}{BOLD}{line}{RESET}"
    mid  = (total_rows - 1) / 2.0
    dist = abs(r - mid) / max(1, mid)   # 0 = center, 1 = outer

    if r == total_rows - 1:             # label row
        col = f"{_AMBER}{DIM}"
    elif dist < 0.12:
        col = f"{_GOLD}{BOLD}"
    elif dist < 0.28:
        col = f"{_NPINK}{BOLD}"
    elif dist < 0.50:
        col = f"{_EPURPLE}{BOLD}"
    elif dist < 0.75:
        col = f"{_HPURPLE}"
    else:
        col = f"{_DPURPLE}{DIM}"

    return f"{col}{line}{RESET}"

# ── Binary / hex row generators ───────────────────────────────────────────────
_BIN_CHARS = list("01") * 6 + list("·░▒▓") + list("0123456789ABCDEF")

def _binary_row(cols, hi_color, lo_color, hi_prob=0.18):
    out = ""
    for _ in range(cols):
        ch = random.choice(_BIN_CHARS)
        out += f"{hi_color}{BOLD}{ch}" if random.random() < hi_prob else f"{lo_color}{DIM}{ch}"
    return out + RESET

def _hex_row(cols, color):
    chars = "0123456789ABCDEFabcdef :;.-><[]{}|"
    out   = ""
    for _ in range(cols):
        out += f"{color}{'BOLD' if random.random()<0.2 else DIM}{random.choice(chars)}"
    return out + RESET

def _hex_row_clean(cols, color):
    chars = "0123456789ABCDEFabcdef :;.-><[]{}|"
    out   = ""
    for _ in range(cols):
        shade = BOLD if random.random() < 0.2 else DIM
        out  += f"{color}{shade}{random.choice(chars)}"
    return out + RESET

# ── Tool cascade ──────────────────────────────────────────────────────────────
TOOLS = [
    ("nmap",        BGREEN,    BOLD),  ("metasploit", _NPINK, BOLD),
    ("hashcat",     _AMBER,    BOLD),  ("wireshark",  _TEAL,  BOLD),
    ("hydra",       BRED,      BOLD),  ("sqlmap",     BGREEN, ""),
    ("aircrack",    _AMBER,    BOLD),  ("volatility", _NPINK, ""),
    ("ghidra",      _TEAL,     BOLD),  ("john",       BRED,   ""),
    ("burpsuite",   BWHITE,    BOLD),  ("nikto",      BGREEN, BOLD),
    ("gobuster",    _AMBER,    ""),    ("bettercap",  _NPINK, BOLD),
    ("radare2",     _TEAL,     ""),    ("binwalk",    BRED,   BOLD),
    ("foremost",    BGREEN,    ""),    ("netcat",     _AMBER, BOLD),
    ("tcpdump",     _NPINK,    ""),    ("mimikatz",   BWHITE, BOLD),
    ("exploitdb",   BGREEN,    ""),    ("maltego",    _NPINK, BOLD),
    ("recon-ng",    _TEAL,     ""),    ("SET",        _AMBER, BOLD),
    ("beef-xss",    BRED,      ""),    ("shodan",     _TEAL,  BOLD),
    ("wifite",      _AMBER,    ""),    ("msfvenom",   _NPINK, BOLD),
    ("crunch",      BRED,      ""),    ("responder",  BGREEN, BOLD),
    ("impacket",    _TEAL,     BOLD),  ("bloodhound", BWHITE, ""),
    ("powersploit", _NPINK,    ""),    ("cobalt",     _AMBER, BOLD),
    ("empire",      BRED,      BOLD),  ("yersinia",   BGREEN, ""),
    ("scapy",       _TEAL,     BOLD),  ("frida",      _NPINK, ""),
    ("angr",        _AMBER,    BOLD),  ("pwndbg",     BRED,   ""),
]

_GLITCH = list("!@#$%^&*()_+-=[]{}|;:,.<>?/\\~`")
_PREFIXES  = ["//",">>","~~","##","{{","[[","--","++","::",">>"]
_SUFFIXES  = ["//","<<","~~","##","}}","]]","--","++","::","<<"]
_SEPS      = ["  ","   ","····","  |  ","  ·  "]
_ROW_TINTS = [_BRTRED, BGREEN, _AMBER, _NPINK, _EPURPLE]
_ROW_DIMS  = [_DRED, DIM+GREEN, DIM+"\033[33m", _DPURPLE, _HPURPLE]

def _tool_cascade(cols, n_rows=5):
    shuffled = TOOLS[:]
    random.shuffle(shuffled)
    bucket   = [[] for _ in range(n_rows)]
    for i, t in enumerate(shuffled):
        bucket[i % n_rows].append(t)

    lines = []
    for ri, row_tools in enumerate(bucket):
        parts = []
        cur   = 0
        for name, color, style in row_tools:
            px      = random.choice(_PREFIXES)
            sx      = random.choice(_SUFFIXES)
            sep     = random.choice(_SEPS)
            display = f"{px}{name}{sx}"
            if random.random() < 0.15:
                display = "".join(
                    random.choice(_GLITCH) if random.random() < 0.08 else c
                    for c in display
                )
            dv  = len(display)
            sv  = len(sep)
            if cur + dv + sv > cols - 2:
                break
            parts.append(f"{color}{style}{display}{RESET}")
            parts.append(f"{_ROW_DIMS[ri % len(_ROW_DIMS)]}{sep}{RESET}")
            cur += dv + sv

        # Pad remaining width with dim noise
        line_vis  = sum(_vis_len(p) for p in parts)
        remaining = cols - 2 - line_vis
        if remaining > 0:
            nc   = _ROW_TINTS[ri % len(_ROW_TINTS)]
            noise = ""
            for _ in range(remaining):
                noise += f"{nc}{DIM}{random.choice(_GLITCH)}{RESET}" if random.random() < 0.06 else " "
            parts.append(noise)

        lines.append(" " + "".join(parts))
    return lines

# ── Section divider helper ────────────────────────────────────────────────────
def _div(cols, text, color):
    dashes = max(0, cols - len(text))
    left   = "─" * (dashes // 2)
    right  = "─" * (dashes - dashes // 2)
    return f"{color}{left}{text}{right}{RESET}"

# ── Static data ───────────────────────────────────────────────────────────────
_WARNING_FULL = [
    f"{_BRTRED}{BOLD}!! WARNING !!!!{RESET}",
    f"{_BRTRED}{BOLD}!! WARNING !!!!{RESET}",
    f"{_MRED}{BOLD}UNAUTHORIZED ACCESS{RESET}",
    f"{_MRED}{BOLD}IS PROHIBITED{RESET}",
    f"{_AMBER}{BOLD}ALL ACTIVITY IS{RESET}",
    f"{_AMBER}{BOLD}MONITORED 24/7{RESET}",
    f"{BRED}{BOLD}LOGGED REAL-TIME{RESET}",
    f"{BRED}VIOLATIONS PROSECUTED{RESET}",
    f"{_DRED}{DIM}─────────────────{RESET}",
    f"{_NPINK}{DIM}NYX-J5W-2026{RESET}",
    f"{_NPINK}{DIM}SIERENGOWSKI{RESET}",
    f"{_DPURPLE}{DIM}LOCKED·LOCKED{RESET}",
    f"{_HPURPLE}{DIM}LOCKED·LOCKED{RESET}",
    f"{_EPURPLE}{DIM}· · · · · · ·{RESET}",
    f"{_NPINK}◆ SYSTEM ARMED ◆{RESET}",
    f"{_AMBER}{DIM}BREACH LOGGED{RESET}",
    f"{BRED}{DIM}YOU ARE WATCHED{RESET}",
    f"{_DRED}{DIM}─────────────────{RESET}",
]

_STATS_FULL = [
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

_BOOT_LEFT = [
    (f"{BGREEN}{BOLD}EXPLOIT FRAMEWORK{RESET}",    f"{DIM}{BGREEN}[OK]{RESET}"),
    (f"{_TEAL}NETWORK INTERFACES{RESET}",           f"{DIM}{_TEAL}[READY]{RESET}"),
    (f"{_AMBER}ANONYMOUS ROUTING{RESET}",            f"{DIM}{_AMBER}[TOR]{RESET}"),
    (f"{_NPINK}PAYLOAD GENERATOR{RESET}",            f"{DIM}{_NPINK}[ARMED]{RESET}"),
    (f"{BRED}IDS BYPASS MODULE{RESET}",              f"{DIM}{BRED}[ACTIVE]{RESET}"),
    (f"{BWHITE}CRYPTO ENGINE AES-256{RESET}",        f"{DIM}{BWHITE}[OK]{RESET}"),
    (f"{BGREEN}HASHCRACK ENGINE{RESET}",              f"{DIM}{BGREEN}[LOADED]{RESET}"),
    (f"{_TEAL}PACKET SNIFFER{RESET}",                f"{DIM}{_TEAL}[SILENT]{RESET}"),
    (f"{_AMBER}VPN TUNNEL LAYER{RESET}",              f"{DIM}{_AMBER}[UP]{RESET}"),
    (f"{_NPINK}ROOTKIT STEALTH LAYER{RESET}",         f"{DIM}{_NPINK}[MASKED]{RESET}"),
    (f"{BGREEN}POST-EXPLOIT FRAMEWORK{RESET}",        f"{DIM}{BGREEN}[PRIMED]{RESET}"),
    (f"{_TEAL}LATERAL MOVEMENT ENG{RESET}",           f"{DIM}{_TEAL}[READY]{RESET}"),
]

_QUICK_REF = [
    f"{_EPURPLE}{BOLD}── QUICK WEAPONS REFERENCE ──────{RESET}",
    f"{BGREEN}nmap -sV -sC -O -p-{RESET} {DIM}{WHITE}<ip>{RESET}",
    f"{BGREEN}hydra -l root -P wl{RESET} {DIM}{WHITE}<ip>{RESET}",
    f"{BGREEN}sqlmap -u{RESET} {DIM}{WHITE}<url>{RESET} {BGREEN}--dbs --dump{RESET}",
    f"{BGREEN}msfconsole -q -r{RESET} {DIM}{WHITE}<rc>{RESET}",
    f"{BGREEN}airmon-ng start wlan0{RESET}",
    f"{BGREEN}hashcat -m 0 -a 0 h wl{RESET}",
    f"{BGREEN}gobuster dir -u{RESET} {DIM}{WHITE}<url>{RESET} {BGREEN}-w wl{RESET}",
    f"{BGREEN}bloodhound-python -d{RESET} {DIM}{WHITE}<dom>{RESET}",
    f"{BGREEN}volatility -f mem imageinfo{RESET}",
    f"{BGREEN}frida-ps -Ua{RESET}",
    f"{_EPURPLE}{BOLD}── NYX-J5W-2026 · SIERENGOWSKI{RESET}",
]

COPYRIGHT = "© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED"

# ── Main render — fully responsive ───────────────────────────────────────────
def render_motd():
    hide_cursor()
    cols, rows = get_size()
    clear()
    sys.stdout.write(BG_BLACK)
    out = []

    # ── Layout breakpoints ─────────────────────────────────────────────────────
    # WIDE:   cols >= 78  → 3-col (warning | X | stats) + 2-col commands
    # MED:    cols >= 50  → 2-col (warning+stats no X) + 2-col commands
    # NARROW: cols < 50   → single column, compact
    if cols >= 78:
        mode = "wide"
    elif cols >= 50:
        mode = "med"
    else:
        mode = "narrow"

    # ── Row budget ─────────────────────────────────────────────────────────────
    # Figure out how many rows each section can use so everything fits.
    # Header overhead (borders + NYXUS logo + tagline + dividers)
    logo_rows_h  = 7 if cols >= 45 else 1   # full block or single text line
    header_rows  = 2 + logo_rows_h + 1 + 1  # top_border + logo + tagline + divider
    footer_rows  = 4                          # bottom binary + divider + copyright + border

    # Scale secondary sections based on available rows
    tc_rows  = min(5, max(1, (rows - header_rows - footer_rows) // 6))
    bin_top  = min(3, max(1, (rows - header_rows - footer_rows) // 8))
    bin_mid  = min(2, max(0, (rows - header_rows - footer_rows) // 10))
    cmd_rows = min(12, max(2, (rows - header_rows - footer_rows) // 4))

    # Remaining rows go to the center panel (X + warning + stats)
    center_h = rows - header_rows - footer_rows - tc_rows - bin_top - bin_mid - cmd_rows - 3
    center_h = max(3, center_h)

    # ── X logo sizing ──────────────────────────────────────────────────────────
    # x_h is always clamped to center_h so the X never overflows vertically
    if mode == "wide":
        x_col_budget = cols // 3 - 2
        x_w = max(4, min(26, x_col_budget))
        x_h = max(2, min(center_h, 18))
    elif mode == "narrow":
        x_w = max(4, min(cols - 4, 16))
        x_h = max(2, min(max(2, center_h // 2), center_h, 10))
    else:
        x_w = x_h = 0   # no X in MED mode

    # Clip WARNING and STATS to center_h
    warning = _WARNING_FULL[:center_h]
    stats   = _STATS_FULL[:center_h]

    # ── TOP BORDERS ────────────────────────────────────────────────────────────
    out.append(f"{_BRTRED}{BOLD}{'█' * cols}{RESET}")
    out.append(f"{_DRED}{'▓' * cols}{RESET}")

    # ── NYXUS LOGO ─────────────────────────────────────────────────────────────
    if cols >= 45:
        # Full 5-row block logo
        avail_w  = cols - max(0, (cols - _BLOCK_W) // 2)
        pad_str  = " " * max(0, (cols - _BLOCK_W) // 2)
        halo     = NYXUS_BLOCK[0].replace("█", "░")[:avail_w]
        out.append(f"{pad_str}{_DPURPLE}{DIM}{halo}{RESET}")
        for line, col_code in zip(NYXUS_BLOCK, _LOGO_COLORS):
            out.append(f"{pad_str}{col_code}{BOLD}{line[:avail_w]}{RESET}")
        out.append(f"{pad_str}{_DPURPLE}{DIM}{halo}{RESET}")
    else:
        # Compact single-line "NYXUS"
        word = f"{_NPINK}{BOLD}NYXUS{RESET}"
        wp   = max(0, (cols - 5) // 2)
        out.append(f"{' ' * wp}{word}")

    # ── TAGLINE ────────────────────────────────────────────────────────────────
    tag  = "[ S I L E N T  ·  D A R K  ·  P U R E L Y   F U N C T I O N A L ]"
    tag  = tag[:cols]
    out.append(f"{' ' * max(0,(cols-len(tag))//2)}{DIM}{BGREEN}{tag}{RESET}")

    # ── DIVIDER ────────────────────────────────────────────────────────────────
    out.append(f"{_DRED}{DIM}{'═' * cols}{RESET}")

    # ── TOOL CASCADE ───────────────────────────────────────────────────────────
    for line in _tool_cascade(cols, tc_rows):
        out.append(line)

    # ── BINARY STREAMS (top) ───────────────────────────────────────────────────
    for _ in range(bin_top):
        palette = [
            (_BRTRED, _DRED,    0.22),
            (BGREEN,  DIM+GREEN, 0.18),
            (_AMBER,  DIM+"\033[33m", 0.15),
        ]
        hi, lo, prob = palette[_ % len(palette)]
        out.append(_binary_row(cols, hi, lo, prob))

    # ── CENTER SECTION DIVIDER ─────────────────────────────────────────────────
    msg = "[ SYSTEM ARMED · PAYLOAD LIVE · STEALTH MODE ACTIVE ]"
    out.append(_div(cols, msg, _NPINK + BOLD))

    # ── CENTER PANEL ───────────────────────────────────────────────────────────
    if mode == "wide":
        # 3-column: warning | X logo | stats
        third  = cols // 3
        x_col  = min(x_w + 2, third)
        left_w = third
        rgt_w  = cols - left_w - x_col - 1

        x_art   = _make_x(x_w, x_h)
        n_rows3 = center_h  # all inputs already clamped to center_h

        for i in range(n_rows3):
            # Left column: warning
            lraw  = warning[i] if i < len(warning) else ""
            lraw  = _vis_truncate(lraw, left_w - 1)
            l_pad = max(0, left_w - _vis_len(lraw))

            # Center column: X logo
            if i < x_h:
                x_line   = x_art[i]
                x_colored = _color_x_row(x_line, i, x_h)
                m_pad    = max(0, x_col - x_w)
            else:
                x_colored = ""
                m_pad     = x_col

            # Right column: stats
            rraw = stats[i] if i < len(stats) else ""
            rraw = _vis_truncate(rraw, rgt_w - 1)

            out.append(f" {lraw}{' ' * l_pad}{x_colored}{' ' * m_pad}{rraw}")

    elif mode == "med":
        # 2-column: warning | stats (no X)
        half   = cols // 2
        rgt_w  = cols - half - 1
        n_rows2 = min(max(len(warning), len(stats)), center_h)

        for i in range(n_rows2):
            lraw = warning[i] if i < len(warning) else ""
            lraw = _vis_truncate(lraw, half - 1)
            l_pad = max(0, half - _vis_len(lraw))
            rraw = stats[i] if i < len(stats) else ""
            rraw = _vis_truncate(rraw, rgt_w - 1)
            out.append(f" {lraw}{' ' * l_pad}{rraw}")

    else:
        # NARROW: stack warning compact, then mini X, then stats compact
        # Show fewer rows
        compact_rows = center_h

        # Show mini X centered
        x_art  = _make_x(x_w, x_h)
        x_xpad = max(0, (cols - x_w) // 2)
        for i, xrow in enumerate(x_art):
            xc = _color_x_row(xrow, i, x_h)
            out.append(f"{' ' * x_xpad}{xc}")

        # Warning (compact)
        w_rows = min(4, compact_rows - x_h)
        for i in range(w_rows):
            row = warning[i] if i < len(warning) else ""
            row = _vis_truncate(row, cols - 2)
            out.append(f" {row}")

        # Stats (compact, prioritize first few)
        s_rows = min(8, compact_rows - x_h - w_rows)
        for i in range(s_rows):
            row = stats[i] if i < len(stats) else ""
            row = _vis_truncate(row, cols - 2)
            out.append(f" {row}")

    # ── BINARY STREAMS (mid) ───────────────────────────────────────────────────
    for _ in range(bin_mid):
        palette = [(_NPINK, _DPURPLE, 0.20), (_TEAL, DIM+"\033[36m", 0.12)]
        hi, lo, prob = palette[_ % len(palette)]
        out.append(_binary_row(cols, hi, lo, prob))

    # ── COMMAND SECTION ────────────────────────────────────────────────────────
    msg2 = "[ EXPLOIT FRAMEWORK · TOOLS LOADED · WEAPONS HOT ]"
    out.append(_div(cols, msg2, _AMBER + BOLD))

    if mode in ("wide", "med") and cols >= 50:
        # 2-column: boot status | quick ref
        half       = cols // 2
        rgt_avail  = cols - half - 1
        STATUS_MAX = 9
        PHRASE_MAX = half - 2 - STATUS_MAX - 1

        n_cmd = min(cmd_rows, max(len(_BOOT_LEFT), len(_QUICK_REF)))
        for i in range(n_cmd):
            if i < len(_BOOT_LEFT):
                phrase, status = _BOOT_LEFT[i]
                phrase    = _vis_truncate(phrase, max(1, PHRASE_MAX))
                pv        = _vis_len(phrase)
                sv        = _vis_len(status)
                gap       = max(1, half - 2 - pv - sv)
                lcell     = f"  {phrase}{' ' * gap}{status}"
                lv        = _vis_len(lcell)
            else:
                lcell, lv = "", 0

            rcell = _vis_truncate(_QUICK_REF[i], max(0, rgt_avail)) if i < len(_QUICK_REF) else ""
            out.append(f"{lcell}{' ' * max(0, half - lv)} {rcell}")
    else:
        # Single column: key status + key commands interleaved
        n_cmd = min(cmd_rows, len(_BOOT_LEFT))
        for i in range(n_cmd):
            phrase, status = _BOOT_LEFT[i]
            phrase = _vis_truncate(phrase, cols - 12)
            pv     = _vis_len(phrase)
            sv     = _vis_len(status)
            gap    = max(1, cols - 2 - pv - sv)
            out.append(f"  {phrase}{' ' * gap}{status}")

    # ── FOOTER ─────────────────────────────────────────────────────────────────
    out.append(_binary_row(cols, _AMBER, _DRED, 0.10))
    out.append(f"{DIM}{_BRTRED}{'─' * cols}{RESET}")

    cp_pad = max(0, (cols - len(COPYRIGHT)) // 2)
    cp_txt = COPYRIGHT[:cols]
    out.append(f"{' ' * cp_pad}{DIM}{WHITE}{cp_txt}{RESET}")

    out.append(f"{_DRED}{'▓' * cols}{RESET}")
    out.append(f"{_BRTRED}{BOLD}{'█' * cols}{RESET}")

    # ── RENDER ─────────────────────────────────────────────────────────────────
    for line in out:
        print(line)

    # Fill remaining rows with hex noise so terminal background is pure black
    remaining = rows - len(out) - 2
    if remaining > 0:
        nc_pool = [DIM + _DRED, DIM + _DPURPLE, DIM + GREEN, DIM + "\033[33m"]
        for _ in range(remaining):
            nc  = random.choice(nc_pool)
            row = ""
            for _c in range(cols):
                row += nc + (random.choice(_BIN_CHARS) if random.random() < 0.35 else " ")
            print(row + RESET)

    # ── HOLD ───────────────────────────────────────────────────────────────────
    show_cursor()
    sys.stdout.write(f"\n{_NPINK}{BOLD}NYXUS > {RESET}")
    sys.stdout.flush()
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass
    clear()


if __name__ == "__main__":
    render_motd()
