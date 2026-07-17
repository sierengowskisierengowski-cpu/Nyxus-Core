#!/usr/bin/env python3
"""
NYXUS · bar mascot sprite generator (rev 2026-07-09)

Pre-renders the graffiti stick-figure mascot that lives on the bottom
bar: neon spray-stroke body + Noto Color Emoji head, transparent bg,
38px tall. Output: ~/.config/eww/assets/mascot/<pose>_<face>.png
consumed by scripts/mascot.py (deflisten state machine).

Poses:  idle0 idle1 walk0..3 dance0..3 wave0 wave1 fall0 fall1 moon0 moon1
Faces:  happy cool shock sleepy love angry wink party

Body color rides the live accent pair from ~/.config/nyxus/accent.json
(re-run after preset switches to re-tint the little guy).
"""
import json, math, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HOME = os.path.expanduser("~")
OUT = os.path.join(HOME, ".config/eww/assets/mascot")
os.makedirs(OUT, exist_ok=True)

W, H = 40, 44          # canvas
HEAD = 15              # emoji head size (px)
SS = 4                 # supersample factor for smooth strokes

def accent_pair():
    try:
        with open(os.path.join(HOME, ".config/nyxus/accent.json")) as f:
            data = json.load(f)
        p = data["presets"][data.get("active", "prism")]
        return p["primary"], p["secondary"]
    except Exception:
        return "#ff4994", "#26ff39"

def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

PRIMARY, SECONDARY = (rgb(c) for c in accent_pair())

FACES = {
    "happy":  "😄", "cool":   "😎", "shock":  "😱", "sleepy": "😴",
    "love":   "😍", "angry":  "😤", "wink":   "😉", "party":  "🥳",
}

# emoji head — Noto Color Emoji is a fixed-109px CBDT font
_emoji_font = ImageFont.truetype("/usr/share/fonts/noto/NotoColorEmoji.ttf", 109)
def emoji_img(ch, size):
    img = Image.new("RGBA", (137, 137), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((0, 0), ch, font=_emoji_font, embedded_color=True)
    box = img.getbbox()
    img = img.crop(box) if box else img
    return img.resize((size, size), Image.LANCZOS)

# ── pose skeletons ────────────────────────────────────────────────────
# Each pose: dict with neck/hip anchors and limb endpoints, in canvas
# coords (y grows down). Head is pasted centred above the neck.
def pose_lines(name):
    """returns list of ((x1,y1),(x2,y2)) body segments"""
    neck = (20, 17); hip = (20, 29)
    spine = [(neck, hip)]
    def limbs(la, ra, ll, rl, spine_pts=None):
        segs = list(spine_pts or spine)
        sh = (20, 19)  # shoulders
        segs += [(sh, la[0]), (la[0], la[1])] if isinstance(la[0], tuple) else [(sh, la)]
        segs += [(sh, ra[0]), (ra[0], ra[1])] if isinstance(ra[0], tuple) else [(sh, ra)]
        segs += [(hip, ll[0]), (ll[0], ll[1])] if isinstance(ll[0], tuple) else [(hip, ll)]
        segs += [(hip, rl[0]), (rl[0], rl[1])] if isinstance(rl[0], tuple) else [(hip, rl)]
        return segs
    P = {
      "idle0": limbs(((14,24),(13,28)), ((26,24),(27,28)), ((17,36),(16,42)), ((23,36),(24,42))),
      "idle1": limbs(((14,25),(14,29)), ((26,25),(26,29)), ((17,36),(16,42)), ((23,36),(24,42))),
      "walk0": limbs(((13,23),(10,27)), ((27,25),(29,30)), ((14,35),(11,42)), ((26,35),(29,42))),
      "walk1": limbs(((15,24),(13,29)), ((25,24),(27,29)), ((17,36),(15,42)), ((24,36),(26,42))),
      "walk2": limbs(((27,23),(30,27)), ((13,25),(11,30)), ((26,35),(29,42)), ((14,35),(11,42))),
      "walk3": limbs(((25,24),(27,29)), ((15,24),(13,29)), ((23,36),(25,42)), ((16,36),(14,42))),
      "dance0": limbs(((11,13),(8,9)),   ((29,13),(32,9)),  ((15,35),(12,41)), ((25,35),(28,41))),
      "dance1": limbs(((11,22),(7,19)),  ((29,13),(32,9)),  ((16,34),(12,38)), ((24,36),(25,42))),
      "dance2": limbs(((11,13),(8,9)),   ((29,22),(33,19)), ((16,36),(15,42)), ((24,34),(28,38))),
      "dance3": limbs(((12,16),(9,12)),  ((28,16),(31,12)), ((14,35),(10,40)), ((26,35),(30,40))),
      "wave0": limbs(((14,24),(13,28)), ((28,12),(31,8)),  ((17,36),(16,42)), ((23,36),(24,42))),
      "wave1": limbs(((14,24),(13,28)), ((26,11),(24,7)),  ((17,36),(16,42)), ((23,36),(24,42))),
      "fall0": [((22,20),(27,30)), ((27,30),(20,33)), ((22,20),(16,24)), ((22,20),(28,25)),
                ((27,30),(33,36)), ((27,30),(22,40))],
      "fall1": [((10,38),(30,38)), ((12,38),(8,33)),  ((28,38),(33,34)), ((14,38),(12,42)),
                ((26,38),(29,42))],
      "moon0": limbs(((13,25),(10,29)), ((27,22),(30,26)), ((13,36),(9,42)),  ((25,34),(28,40))),
      "moon1": limbs(((15,24),(12,28)), ((25,23),(28,27)), ((16,35),(12,41)), ((24,36),(27,42))),
    }
    return P[name]

# head anchor per pose (centre of head)
HEAD_AT = {
    "fall0": (20, 14), "fall1": (35, 37),
}
DEF_HEAD = (20, 9)

def render(pose, face_name, face_im):
    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    segs = pose_lines(pose)
    # glow pass (accent), then core pass (bright)
    for (a, b) in segs:
        d.line((a[0]*SS, a[1]*SS, b[0]*SS, b[1]*SS), fill=PRIMARY + (200,), width=4*SS)
    glow = img.filter(ImageFilter.GaussianBlur(2 * SS))
    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for (a, b) in segs:
        d.line((a[0]*SS, a[1]*SS, b[0]*SS, b[1]*SS), fill=(255, 255, 255, 235), width=int(1.8*SS))
        d.ellipse((b[0]*SS-3, b[1]*SS-3, b[0]*SS+3, b[1]*SS+3), fill=SECONDARY + (160,))
    out = Image.alpha_composite(glow, img).resize((W, H), Image.LANCZOS)
    hx, hy = HEAD_AT.get(pose, DEF_HEAD)
    out.alpha_composite(face_im, (hx - HEAD // 2, hy - HEAD // 2))
    out.save(os.path.join(OUT, f"{pose}_{face_name}.png"))

POSES = ["idle0","idle1","walk0","walk1","walk2","walk3",
         "dance0","dance1","dance2","dance3","wave0","wave1",
         "fall0","fall1","moon0","moon1"]

faces = {name: emoji_img(ch, HEAD) for name, ch in FACES.items()}
n = 0
for pose in POSES:
    for fname, fim in faces.items():
        render(pose, fname, fim)
        n += 1
print(f"wrote {n} sprites to {OUT}")
