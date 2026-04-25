#!/usr/bin/env python3
"""
NYXUS — Boot Splash Screen
Red-glow scrolling code/hex matrix. The Matrix but red.
Sets a serious dark tone from the first second.
© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""

import os
import sys
import time
import random
import shutil
import math

# ── ANSI helpers ───────────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"

def fg256(n):
    return f"\033[38;5;{n}m"

def bg256(n):
    return f"\033[48;5;{n}m"

BG_BLACK = "\033[40m"

# ── Red palette (deep dark → bright glow) ─────────────────────────────────────
# 256-color red ramp: 52 (darkest) → 88 → 124 → 160 → 196 (brightest) → 197
RED_RAMP = [52, 88, 124, 160, 196, 197, 198, 203]

def red_shade(brightness_0_1: float) -> str:
    idx = int(brightness_0_1 * (len(RED_RAMP) - 1))
    return fg256(RED_RAMP[min(idx, len(RED_RAMP) - 1)])

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

# ── Code line templates ────────────────────────────────────────────────────────
# Realistic-looking C/assembly/hex mixed code
CODE_TEMPLATES = [
    "0x{:08X}: {:02X} {:02X} {:02X} {:02X}  {:02X} {:02X} {:02X} {:02X}   {:<20s}",
    "  push   rbp",
    "  mov    rbp, rsp",
    "  sub    rsp, 0x{:02X}",
    "  lea    rax, [rbp-0x{:02X}]",
    "  call   0x{:016X}",
    "  test   eax, eax",
    "  jne    0x{:08x}",
    "  xor    eax, eax",
    "  ret",
    "  mov    QWORD PTR [rbp-0x{:02X}], rdi",
    "  movabs rax, 0x{:016X}",
    "  mov    edi, 0x{:08X}",
    "  syscall",
    "  int3",
    "  nop",
    "  endbr64",
    "[0x{:08x}] <_nyxus_init+{}>:",
    "  cmp    DWORD PTR [rip+0x{:X}], 0x0",
    "  je     0x{:08X}",
    "  add    rsp, 0x{:02X}",
    "  pop    rbp",
    "if (!nyxus_check_integrity(ctx)) {{",
    "  return NYX_ERR_TAMPER;",
    "}}",
    "memcpy(dst + offset, payload, len & 0x{:04X});",
    "nyxus_aes256_cbc_encrypt(key, iv, buf, sz);",
    "for (i = 0; i < 0x{:04X}; i++) {{",
    "  buf[i] ^= key_sched[i & 0x{:02X}];",
    "}}",
    "nyx_socket_t *sock = nyx_connect(\"{}\", {});",
    "if (recv(fd, &hdr, sizeof(hdr), 0) < 0) {{",
    "  NYX_LOG(\"recv failed: %s\", strerror(errno));",
    "}}",
    "static const uint8_t shellcode[] = {{",
    "  0x{:02X}, 0x{:02X}, 0x{:02X}, 0x{:02X},",
    "  0x{:02X}, 0x{:02X}, 0x{:02X}, 0x{:02X},",
    "}};",
    "// NYX-J5W-2026 :: SIERENGOWSKI-LOCKED",
    "// kernel: 6.6.0-nyxus  arch: x86_64",
    "// init sequence: STAGE_{} OK",
    "// checksum: {:08X} [VERIFIED]",
    "// entropy pool: {} bits",
    "#define NYX_VERSION  \"2.0.{}\"",
    "#define NYX_KEY_LEN  256",
    "#define NYX_MAGIC    0x{:08X}ULL",
    "typedef struct __attribute__((packed)) {{",
    "  uint32_t magic;",
    "  uint16_t version;",
    "  uint8_t  flags;",
    "  uint8_t  reserved[5];",
    "}} nyx_header_t;",
]

IP_POOL = [
    "10.0.0.1", "192.168.1.254", "172.16.0.1",
    "8.8.8.8", "1.1.1.1", "104.21.0.1",
]

def gen_code_line():
    tpl = random.choice(CODE_TEMPLATES)
    try:
        count = tpl.count("{")
        args  = []
        for _ in range(count):
            args.append(random.randint(0, 0xFFFFFFFF))
        # handle string slots
        filled = tpl
        while "{:<20s}" in filled:
            mnemonics = ["nyxus_init", "nyx_exec", "exploit", "shellcode", "payload_run", "stealth_hook", "aes_xform", "nyx_exit"]
            filled = filled.replace("{:<20s}", f"{random.choice(mnemonics):<20s}", 1)
        while '"{}"' in filled:
            filled = filled.replace('"{}"', f'"{random.choice(IP_POOL)}"', 1)
        # fill integer slots
        import re
        def fill_int(m):
            spec = m.group(1)
            val  = random.randint(0, 0xFFFF if "04X" in spec else 0xFF if "02X" in spec else 0xFFFFFFFF)
            try:
                return format(val, spec.strip(":").strip("{").strip("}"))
            except Exception:
                return str(val)
        filled = re.sub(r"\{(:[^}]+)\}", fill_int, filled)
        filled = re.sub(r"\{(\d+)\}", lambda m: str(random.randint(0, 0xFFFF)), filled)
        filled = re.sub(r"\{\}", lambda m: str(random.randint(0, 255)), filled)
        return filled
    except Exception:
        return f"0x{random.randint(0, 0xFFFFFFFFFF):010X}  nop"

# ── Matrix rain column ─────────────────────────────────────────────────────────
class CodeColumn:
    """A single falling column of code characters."""
    def __init__(self, col, rows):
        self.col    = col
        self.rows   = rows
        self.head   = random.randint(-rows, 0)
        self.length = random.randint(rows // 3, rows)
        self.speed  = random.uniform(0.3, 1.8)
        self.last_t = time.time()
        self.chars  = [self._rand_char() for _ in range(rows)]
        # Refresh random chars
        self.refresh_timer = time.time()
        self.refresh_rate  = random.uniform(0.05, 0.3)

    def _rand_char(self):
        pool = list("0123456789ABCDEFabcdef") + list("_{}()[];:,.<>+=-/\\*&^%#@!|~`'\"")
        return random.choice(pool)

    def tick(self, now):
        if now - self.last_t >= 1.0 / self.speed:
            self.head += 1
            self.last_t = now
        if now - self.refresh_timer >= self.refresh_rate:
            idx = random.randint(0, self.rows - 1)
            self.chars[idx] = self._rand_char()
            self.refresh_timer = now

    def brightness_at(self, row):
        """Returns brightness 0.0–1.0 or -1.0 (invisible)."""
        dist = row - self.head
        if dist < 0:
            return -1.0
        if dist == 0:
            return 1.0  # head
        if dist <= self.length:
            return max(0.05, 1.0 - dist / self.length)
        return -1.0

    def char_at(self, row):
        return self.chars[row % self.rows]

# ── NYXUS logo (big block letters) ────────────────────────────────────────────
NYXUS_LOGO = [
    "███╗   ██╗██╗   ██╗██╗  ██╗██╗   ██╗███████╗",
    "████╗  ██║╚██╗ ██╔╝╚██╗██╔╝██║   ██║██╔════╝",
    "██╔██╗ ██║ ╚████╔╝  ╚███╔╝ ██║   ██║███████╗",
    "██║╚██╗██║  ╚██╔╝   ██╔██╗ ██║   ██║╚════██║",
    "██║ ╚████║   ██║   ██╔╝ ██╗╚██████╔╝███████║",
    "╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝",
]

TAGLINE = "S I L E N T . D A R K . P U R E L Y   F U N C T I O N A L"
COPYRIGHT = "© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED"

# ── Glow distance function (radial gradient) ──────────────────────────────────
def glow_brightness(row, col, center_row, center_col, radius):
    """Return 0.0–1.0 based on distance from center."""
    dist = math.sqrt((row - center_row) ** 2 + ((col - center_col) * 0.5) ** 2)
    return max(0.0, 1.0 - dist / radius)

# ── Main render ────────────────────────────────────────────────────────────────
def render_splash(next_command=None):
    """
    Splash animation:
      0.0 – 3.0s  : red scrolling code rain (dark to bright center glow)
      3.0 – 4.0s  : logo fades in over rain
      4.0 – 5.0s  : tagline fades in, rain dims
      5.0+        : static display, then exit
    """
    hide_cursor()
    cols, rows = get_size()
    clear()

    columns = [CodeColumn(c, rows) for c in range(cols)]

    logo_row     = max(2, (rows - len(NYXUS_LOGO)) // 2 - 2)
    logo_col     = max(0, (cols - len(NYXUS_LOGO[0])) // 2)
    tagline_row  = logo_row + len(NYXUS_LOGO) + 2
    cp_row       = rows - 2
    cp_col       = max(0, (cols - len(COPYRIGHT)) // 2)

    center_row   = logo_row + len(NYXUS_LOGO) // 2
    center_col   = cols // 2
    glow_radius  = max(cols, rows) * 0.7

    start_time = time.time()
    TARGET_FPS = 30
    frame_time = 1.0 / TARGET_FPS

    # ── Screen buffer ──────────────────────────────────────────────────────────
    # Each cell: (char, red_brightness_0_1)
    screen_ch = [[" "] * cols for _ in range(rows)]
    screen_br = [[0.0]       * cols for _ in range(rows)]

    def update(now, elapsed):
        for col_obj in columns:
            col_obj.tick(now)

        for r in range(rows):
            for c in range(cols):
                col_obj = columns[c]
                rain_br  = col_obj.brightness_at(r)

                if rain_br < 0:
                    screen_ch[r][c] = " "
                    screen_br[r][c] = 0.0
                    continue

                # Glow map: brightest near center
                center_bonus = glow_brightness(r, c, center_row, center_col, glow_radius)

                # Combined brightness
                brightness = rain_br * (0.4 + center_bonus * 0.6)
                screen_ch[r][c] = col_obj.char_at(r)
                screen_br[r][c] = brightness

    def overlay_logo(elapsed):
        if elapsed < 3.0:
            return

        alpha = min(1.0, (elapsed - 3.0) / 0.8)

        for i, line in enumerate(NYXUS_LOGO):
            r = logo_row + i
            if r >= rows:
                break
            for j, ch in enumerate(line):
                c = logo_col + j
                if c >= cols or ch == " ":
                    continue
                if random.random() < alpha:
                    screen_ch[r][c] = ch
                    screen_br[r][c] = 0.85 + 0.15 * alpha  # near max brightness

    def overlay_tagline(elapsed):
        if elapsed < 4.2:
            return
        alpha = min(1.0, (elapsed - 4.2) / 0.6)
        if tagline_row < rows:
            pad = max(0, (cols - len(TAGLINE)) // 2)
            for j, ch in enumerate(TAGLINE):
                c = pad + j
                if c >= cols or ch == " ":
                    continue
                if random.random() < alpha:
                    screen_ch[tagline_row][c] = ch
                    screen_br[tagline_row][c] = 0.6

    def overlay_copyright(elapsed):
        if elapsed < 4.5:
            return
        alpha = min(1.0, (elapsed - 4.5) / 0.5)
        if cp_row < rows:
            for j, ch in enumerate(COPYRIGHT):
                c = cp_col + j
                if c >= cols or ch == " ":
                    continue
                if random.random() < alpha:
                    screen_ch[cp_row][c] = ch
                    screen_br[cp_row][c] = 0.25

    def render():
        output = "\033[H"
        for r in range(rows - 1):
            line = BG_BLACK
            prev_shade = -1
            for c in range(cols):
                br = screen_br[r][c]
                ch = screen_ch[r][c]
                shade_idx = int(br * (len(RED_RAMP) - 1))
                shade_idx = max(0, min(shade_idx, len(RED_RAMP) - 1))
                if br < 0.01:
                    if prev_shade != -99:
                        line += BG_BLACK + " "
                        prev_shade = -99
                    else:
                        line += " "
                else:
                    color_code = fg256(RED_RAMP[shade_idx])
                    if shade_idx != prev_shade:
                        line += color_code
                        prev_shade = shade_idx
                    line += ch
            output += line + RESET + "\r\n"
        sys.stdout.write(output)
        sys.stdout.flush()

    # ── Boot status messages (shown during animation) ──────────────────────────
    STATUS_MSGS = [
        (0.4, "BIOS........[ OK ]"),
        (0.7, "MBR.........[ OK ]"),
        (0.9, "KERNEL......[ LOADING ]"),
        (1.2, "INITRD......[ OK ]"),
        (1.5, "ROOTFS......[ MOUNTED ]"),
        (1.8, "NETWORK.....[ STEALTH ]"),
        (2.0, "CRYPTO......[ ARMED ]"),
        (2.3, "TOOLS.......[ LOADED ]"),
        (2.6, "EXPLOIT-FW..[ READY ]"),
        (2.9, "NYXUS OS....[ ██████████ ] BOOT OK"),
    ]
    shown_msgs = set()

    def draw_status_msg(elapsed):
        for t, msg in STATUS_MSGS:
            if elapsed >= t and t not in shown_msgs:
                shown_msgs.add(t)
                r = rows - 3
                pad = 2
                full = f"  >> {msg}"
                for j, ch in enumerate(full[:cols]):
                    screen_ch[r][j] = ch
                    screen_br[r][j] = 0.55

    # ── Main loop ──────────────────────────────────────────────────────────────
    TOTAL_DURATION = 5.5

    try:
        while True:
            loop_start = time.time()
            elapsed    = loop_start - start_time

            if elapsed >= TOTAL_DURATION:
                break

            update(loop_start, elapsed)
            overlay_logo(elapsed)
            overlay_tagline(elapsed)
            overlay_copyright(elapsed)
            draw_status_msg(elapsed)
            render()

            sleep_t = frame_time - (time.time() - loop_start)
            if sleep_t > 0:
                time.sleep(sleep_t)

    except KeyboardInterrupt:
        pass

    # ── Final hold frame ───────────────────────────────────────────────────────
    update(time.time(), TOTAL_DURATION)
    overlay_logo(TOTAL_DURATION)
    overlay_tagline(TOTAL_DURATION)
    overlay_copyright(TOTAL_DURATION)
    render()
    time.sleep(0.6)

    # ── Fade to black ──────────────────────────────────────────────────────────
    steps = 8
    for step in range(steps):
        factor = 1.0 - (step + 1) / steps
        for r in range(rows):
            for c in range(cols):
                screen_br[r][c] *= factor
        render()
        time.sleep(0.04)

    clear()
    show_cursor()

    # ── Launch next stage ──────────────────────────────────────────────────────
    if next_command:
        os.execvp(next_command[0], next_command)


# ── CLI entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse, shlex

    parser = argparse.ArgumentParser(description="NYXUS Boot Splash Screen")
    parser.add_argument("--next", type=str, default=None,
                        help="Command to exec after animation finishes")
    args = parser.parse_args()

    next_cmd = shlex.split(args.next) if args.next else None
    render_splash(next_command=next_cmd)
