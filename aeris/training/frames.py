"""Compose the 1920x1080 frames: screenshot, focus on highlighted elements, caption bar, chapter tag."""
import os
import textwrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
SCALE = 1.5                      # screenshots are 1280x720 CSS px at device scale 1.5
MAROON = (145, 25, 54)
GOLD = (188, 160, 83)
GREEN = (35, 115, 72)
FONT_DIR = r"C:\Windows\Fonts"


def font(size, bold=False):
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def compose(shot_path, caption, chapter, boxes, out_path):
    base = Image.open(shot_path).convert("RGB").resize((W, H), Image.LANCZOS)
    frame = base.copy()
    if boxes:
        # dim and soften everything, then paste the highlighted areas back sharp
        dim = Image.blend(base.filter(ImageFilter.GaussianBlur(1.2)), Image.new("RGB", (W, H), (20, 20, 28)), 0.45)
        frame = dim
        draw = ImageDraw.Draw(frame)
        for x, y, w, h in boxes:
            pad = 10
            l, t = max(0, int(x * SCALE) - pad), max(0, int(y * SCALE) - pad)
            r, b = min(W, int((x + w) * SCALE) + pad), min(H, int((y + h) * SCALE) + pad)
            frame.paste(base.crop((l, t, r, b)), (l, t))
            draw.rounded_rectangle((l - 3, t - 3, r + 3, b + 3), radius=12, outline=GOLD, width=6)
    draw = ImageDraw.Draw(frame, "RGBA")

    # caption bar, with the chapter name in gold above the caption
    f = font(44, bold=True)
    fc = font(28, bold=True)
    lines = textwrap.wrap(caption, width=70)[:2]
    bar_h = 30 + 40 + 58 * len(lines)
    draw.rectangle((0, H - bar_h, W, H), fill=(30, 12, 18, 228))
    draw.rectangle((0, H - bar_h, W, H - bar_h + 6), fill=GOLD + (255,))
    if chapter:
        draw.text((36, H - bar_h + 16), chapter.upper(), font=fc, fill=GOLD + (255,))
    y = H - bar_h + 58
    for line in lines:
        tw = draw.textlength(line, font=f)
        draw.text(((W - tw) / 2, y), line, font=f, fill="white")
        y += 58
    frame.save(out_path, quality=95)


def title_card(title, subtitle, out_path, logo_path=None, footer=None):
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, 14), fill=MAROON)
    draw.rectangle((0, 14, W, 20), fill=GOLD)
    draw.rectangle((0, H - 20, W, H - 14), fill=GOLD)
    draw.rectangle((0, H - 14, W, H), fill=GREEN)
    y = 170
    if logo_path:
        logo = Image.open(logo_path).convert("RGBA")
        lw = 640
        logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
        img.paste(logo, ((W - lw) // 2, y), logo)
        y += logo.height + 70
    for text, size, bold, color in ((title, 84, True, MAROON), (subtitle, 46, False, (60, 60, 60))):
        f = font(size, bold)
        for line in textwrap.wrap(text, width=40):
            tw = draw.textlength(line, font=f)
            draw.text(((W - tw) / 2, y), line, font=f, fill=color)
            y += size + 22
        y += 20
    if footer:
        f = font(32)
        tw = draw.textlength(footer, font=f)
        draw.text(((W - tw) / 2, H - 110), footer, font=f, fill=(110, 110, 110))
    img.save(out_path, quality=95)


def chapter_card(number, title, points, out_path):
    img = Image.new("RGB", (W, H), MAROON)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, H - 16, W, H), fill=GOLD)
    draw.text((140, 250), f"{number}", font=font(220, True), fill=GOLD)
    draw.text((420, 300), title, font=font(86, True), fill="white")
    y = 460
    for p in points:
        draw.text((430, y), "•  " + p, font=font(44), fill=(245, 235, 238))
        y += 72
    img.save(out_path, quality=95)
