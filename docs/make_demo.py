"""
Generate docs/demo.gif: an animated SIMULATION of what TECHNEXUS reports.

This is an illustration, not real model output. It shows the kind of
detections the pipeline produces (driver actions, passenger seats, vehicle
info) and how they end up in results.json.

Run from the repository root:
    python docs/make_demo.py
"""
import math
from PIL import Image, ImageDraw, ImageFont

W, H = 960, 540
VIEW_W = 600          # camera view width; the JSON panel fills the rest
FPS = 10
DURATION = 11.0       # seconds
OUT = "docs/demo.gif"

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
f_title = ImageFont.truetype(FONT_DIR + "DejaVuSans-Bold.ttf", 18)
f_small = ImageFont.truetype(FONT_DIR + "DejaVuSans.ttf", 13)
f_tag = ImageFont.truetype(FONT_DIR + "DejaVuSans-Bold.ttf", 13)
f_mono = ImageFont.truetype(FONT_DIR + "DejaVuSansMono.ttf", 12)
f_mono_b = ImageFont.truetype(FONT_DIR + "DejaVuSansMono-Bold.ttf", 12)

BG = (18, 20, 26)
PANEL = (12, 14, 18)
CABIN = (38, 41, 50)
SEAT = (58, 62, 74)
SKIN = (196, 160, 132)
SHIRT_D = (52, 92, 140)
SHIRT_P = (120, 72, 96)
SHIRT_R = (84, 120, 84)
WHITE = (235, 238, 245)
MUTED = (140, 146, 160)

COL_DRIVER = (255, 92, 92)
COL_PAX = (80, 200, 255)
COL_OBJ = (255, 196, 60)

# Timed events: (time, label, category, confidence, colour, target)
EVENTS = [
    (1.0, "on_koltuk", "yolcular", 0.91, COL_PAX, "pax_front"),
    (1.4, "arka_koltuk_1", "yolcular", 0.84, COL_PAX, "pax_rear"),
    (3.2, "esneme", "sofor_eylemi", 0.86, COL_DRIVER, "driver_face"),
    (5.6, "telefonla_konusma", "sofor_eylemi", 0.78, COL_DRIVER, "driver_phone"),
    (8.0, "etrafa_bakinma", "sofor_eylemi", 0.72, COL_DRIVER, "driver_face"),
]
BOX_HOLD = 1.8  # seconds a driver-action box stays visible


def person(d, cx, cy, scale, shirt, head_dx=0, mouth_open=0.0, phone=False, eye_dx=0):
    """Draw a simple seated person seen from the front camera."""
    s = scale
    # shoulders / body
    d.rounded_rectangle([cx - 46 * s, cy + 24 * s, cx + 46 * s, cy + 120 * s],
                        radius=int(26 * s), fill=shirt)
    # neck
    d.rectangle([cx - 9 * s, cy + 12 * s, cx + 9 * s, cy + 28 * s], fill=SKIN)
    # head
    hx = cx + head_dx * s
    d.ellipse([hx - 24 * s, cy - 30 * s, hx + 24 * s, cy + 22 * s], fill=SKIN)
    # hair
    d.chord([hx - 25 * s, cy - 32 * s, hx + 25 * s, cy + 6 * s], 180, 360, fill=(54, 40, 32))
    # eyes
    for ex in (-9, 9):
        d.ellipse([hx + (ex - 3 + eye_dx) * s, cy - 6 * s, hx + (ex + 3 + eye_dx) * s, cy], fill=(30, 30, 30))
    # mouth
    if mouth_open > 0.05:
        mh = 4 + 10 * mouth_open
        d.ellipse([hx - 6 * s, cy + 6 * s, hx + 6 * s, cy + (6 + mh) * s], fill=(90, 30, 30))
    else:
        d.line([hx - 6 * s, cy + 10 * s, hx + 6 * s, cy + 10 * s], fill=(110, 60, 50), width=max(1, int(2 * s)))
    if phone:
        # hand and phone at the right ear (image right)
        d.ellipse([hx + 20 * s, cy - 2 * s, hx + 38 * s, cy + 18 * s], fill=SKIN)
        d.rounded_rectangle([hx + 24 * s, cy - 20 * s, hx + 36 * s, cy + 6 * s], radius=3, fill=(20, 20, 24),
                            outline=(90, 90, 100))


def seat(d, cx, cy, scale):
    s = scale
    d.rounded_rectangle([cx - 56 * s, cy - 50 * s, cx + 56 * s, cy + 130 * s], radius=int(22 * s), fill=SEAT)


def box(d, rect, label, conf, colour):
    x1, y1, x2, y2 = rect
    d.rectangle(rect, outline=colour, width=3)
    tag = f"{label} {conf:.2f}"
    tw = d.textlength(tag, font=f_tag)
    d.rectangle([x1, y1 - 20, x1 + tw + 10, y1], fill=colour)
    d.text((x1 + 5, y1 - 18), tag, font=f_tag, fill=(10, 10, 10))


def json_lines(t):
    lines = [
        ("{", WHITE, False),
        ('  "video_id": "demo",', MUTED, False),
        ('  "arac_bilgisi": {', MUTED, False),
        ('    "tip": "sedan",', MUTED, False),
        ('    "renk": "beyaz",', MUTED, False),
        ('    "plaka": "06 TNX 26"', MUTED, False),
        ("  },", MUTED, False),
        ('  "tespitler": [', MUTED, False),
    ]
    shown = [e for e in EVENTS if t >= e[0]]
    for i, (et, lbl, kat, cf, col, _) in enumerate(shown):
        fresh = t - et < 0.8
        comma = "," if i < len(shown) - 1 else ""
        lines.append((f'    {{"zaman_saniye": {et:.1f},', col if fresh else WHITE, fresh))
        lines.append((f'     "kategori": "{kat}",', col if fresh else MUTED, False))
        lines.append((f'     "etiket": "{lbl}",', col if fresh else WHITE, fresh))
        lines.append((f'     "confidence_score": {cf:.2f}}}{comma}', col if fresh else MUTED, False))
    lines.append(("  ]", MUTED, False))
    lines.append(("}", WHITE, False))
    return lines


def frame(t):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # header
    d.rectangle([0, 0, W, 40], fill=(26, 29, 38))
    d.text((16, 10), "TECHNEXUS · Road Safety AI", font=f_title, fill=WHITE)
    sim = "SIMULATION · not real model output"
    d.rounded_rectangle([W - 16 - d.textlength(sim, font=f_tag) - 16, 9, W - 16, 31], radius=6, fill=(120, 40, 40))
    d.text((W - 16 - d.textlength(sim, font=f_tag) - 8, 12), sim, font=f_tag, fill=WHITE)

    # camera view
    vx0, vy0, vx1, vy1 = 12, 52, VIEW_W - 6, H - 46
    d.rounded_rectangle([vx0, vy0, vx1, vy1], radius=10, fill=CABIN)
    # rear window light
    d.rounded_rectangle([vx0 + 110, vy0 + 18, vx1 - 110, vy0 + 90], radius=18, fill=(70, 78, 96))

    # rear passenger (image left, behind)
    seat(d, 200, 175, 0.62)
    person(d, 200, 160, 0.62, SHIRT_R, head_dx=2 * math.sin(t * 1.3))
    # front passenger (image left)
    seat(d, 170, 300, 1.0)
    person(d, 170, 280, 1.0, SHIRT_P, head_dx=3 * math.sin(t * 0.9))

    # driver (image right: left-hand-drive car seen from the front camera)
    yawn = max(0.0, 1 - abs(t - 3.6) / 0.7) if 2.9 <= t <= 4.3 else 0.0
    on_phone = 5.4 <= t <= 7.2
    look = 0.0
    if 7.8 <= t <= 9.4:
        look = -16 * min(1.0, (t - 7.8) / 0.3, (9.4 - t) / 0.3)
    seat(d, 430, 300, 1.0)
    person(d, 430, 280, 1.0, SHIRT_D, head_dx=look + 1.5 * math.sin(t * 1.1),
           mouth_open=yawn, phone=on_phone, eye_dx=look / 4)
    # seat belt
    d.line([400, 300, 470, 395], fill=(30, 30, 30), width=7)
    # steering wheel
    d.arc([360, 380, 500, 470], 200, 340, fill=(20, 20, 24), width=10)

    # detection boxes
    for et, lbl, kat, cf, col, target in EVENTS:
        if t < et:
            continue
        if target == "pax_front":
            box(d, (110, 252, 230, 410), lbl, cf, col)
        elif target == "pax_rear":
            box(d, (164, 128, 236, 214), lbl, cf, col)
        elif t - et <= BOX_HOLD:
            if target == "driver_face":
                box(d, (396 + int(look), 242, 466 + int(look), 312), lbl, cf, col)
            elif target == "driver_phone":
                box(d, (396, 236, 482, 312), lbl, cf, col)

    # view caption
    d.text((vx0 + 10, vy1 - 22), "in-cabin camera", font=f_small, fill=MUTED)

    # JSON panel
    px0 = VIEW_W + 6
    d.rounded_rectangle([px0, 52, W - 12, H - 46], radius=10, fill=PANEL)
    d.text((px0 + 12, 60), "results.json", font=f_tag, fill=MUTED)
    lines = json_lines(t)
    max_lines = 26
    lines = lines[:8] + lines[8:][-(max_lines - 8):] if len(lines) > max_lines else lines
    y = 84
    for txt, col, bold in lines:
        d.text((px0 + 12, y), txt, font=f_mono_b if bold else f_mono, fill=col)
        y += 15

    # timeline
    d.rectangle([12, H - 30, W - 12, H - 24], fill=(44, 48, 58))
    d.rectangle([12, H - 30, 12 + (W - 24) * t / DURATION, H - 24], fill=(90, 160, 255))
    for et, *_rest, col, _tg in [(e[0], e[1], e[2], e[3], e[4], e[5]) for e in EVENTS]:
        x = 12 + (W - 24) * et / DURATION
        d.ellipse([x - 4, H - 31, x + 4, H - 23], fill=col)
    d.text((W - 80, H - 20), f"{t:4.1f} s", font=f_small, fill=MUTED)
    return img


def main():
    frames = [frame(i / FPS) for i in range(int(DURATION * FPS))]
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=96) for f in frames]
    pal[0].save(OUT, save_all=True, append_images=pal[1:], duration=int(1000 / FPS), loop=0, optimize=True)
    print("saved", OUT)


if __name__ == "__main__":
    main()
