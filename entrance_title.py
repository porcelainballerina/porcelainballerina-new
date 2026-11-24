#!/usr/bin/env python3
"""Entrance book-title inscription. Swap the two strings here when the wording changes later.

The title is gold-tooled onto the grimoire cover (not floated on the floor).
Keep warn-gate.js a11y copy in sync with these strings.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageChops

# --- wording (easy to swap in a later step) ---
TITLE_LINE_1 = "The door is sealed"
TITLE_LINE_2 = "Atramentum Custodit"

# Cover geometry on the 1920x1080 sicker chamber (fractions of full frame).
# Book is roughly x 0.367–0.600, y 0.146–0.791. Main seal top ~0.345.
# Default: a title plate in the band above the main seal, centered on the cover.
TITLE_CX = 0.483
TITLE_CY = 0.248
TITLE_WIDTH = 0.200  # of full image width; stays inside the cover

FONT_TITLE = Path("/usr/share/fonts/truetype/sand-box/google/Cinzel/Cinzel-VariableFont_wght.ttf")
FONT_LATIN = Path("/usr/share/fonts/truetype/sand-box/google/IM Fell French Canon/IMFellFrenchCanon-Italic.ttf")
FONT_TITLE_SC = Path("/usr/share/fonts/truetype/sand-box/google/Cormorant SC/CormorantSC-Regular.ttf")


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def _text_size(font, text):
    b = font.getbbox(text)
    return b[2] - b[0], b[3] - b[1]


def stamp_title(
    im: Image.Image,
    line1: str = TITLE_LINE_1,
    line2: str = TITLE_LINE_2,
    cx: float = TITLE_CX,
    cy: float = TITLE_CY,
    width: float = TITLE_WIDTH,
    variant: str = "upper",
) -> Image.Image:
    """Gold-tool line1/line2 onto the grimoire cover. Words are arguments so they stay swappable."""
    im = im.convert("RGB")
    w, h = im.size
    if variant == "lower":
        cx, cy, width = 0.483, 0.735, 0.200

    box_w = int(width * w)
    # two lines + rules + padding
    box_h = int(box_w * 0.38)
    x0 = int(cx * w - box_w / 2)
    y0 = int(cy * h - box_h / 2)
    x1, y1 = x0 + box_w, y0 + box_h

    # sample leather in the plate area for texture and colour
    pad = 4
    leather = im.crop((max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)))

    plate = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(plate)

    # recessed leather panel: slightly darker rounded rect
    recess = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rd = ImageDraw.Draw(recess)
    rad = max(4, box_h // 10)
    rd.rounded_rectangle((x0, y0, x1, y1), radius=rad, fill=(10, 4, 3, 200))
    # inner drop to look impressed into the board
    rd.rounded_rectangle((x0 + 3, y0 + 3, x1 - 3, y1 - 3), radius=max(3, rad - 2), fill=(8, 3, 2, 120))
    recess = recess.filter(ImageFilter.GaussianBlur(1.4))
    plate = Image.alpha_composite(plate, recess)

    # worn gold double-rule border
    gold = (201, 164, 90, 200)
    gold_dim = (140, 100, 50, 140)
    border = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(border)
    bd.rounded_rectangle((x0 + 5, y0 + 5, x1 - 5, y1 - 5), radius=max(3, rad - 3), outline=gold, width=2)
    bd.rounded_rectangle((x0 + 9, y0 + 9, x1 - 9, y1 - 9), radius=max(2, rad - 4), outline=gold_dim, width=1)
    border = border.filter(ImageFilter.GaussianBlur(0.4))
    plate = Image.alpha_composite(plate, border)

    # typography
    # scale fonts to the plate
    # tooled titles read as caps; keep the source string natural for later wording swaps
    line1_draw = line1.upper()
    size1 = max(16, int(box_h * 0.30))
    size2 = max(14, int(box_h * 0.22))
    f1 = _font(FONT_TITLE, size1)
    f2 = _font(FONT_LATIN, size2)
    # shrink line 1 if it overflows the inner width
    inner_w = box_w - 28
    tw, th = _text_size(f1, line1_draw)
    if tw > inner_w:
        size1 = max(14, int(size1 * inner_w / tw))
        f1 = _font(FONT_TITLE, size1)
        tw, th = _text_size(f1, line1_draw)
    tw2, th2 = _text_size(f2, line2)
    if tw2 > inner_w:
        size2 = max(12, int(size2 * inner_w / tw2))
        f2 = _font(FONT_LATIN, size2)
        tw2, th2 = _text_size(f2, line2)

    gap = max(3, int(box_h * 0.06))
    total_h = th + gap + th2
    ty = y0 + (box_h - total_h) // 2 - int(box_h * 0.02)
    cx_px = (x0 + x1) // 2

    def render_line(text, font, cy_line, fill, shadow, highlight):
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        # getanchor-less: compute left from width
        tw, th = _text_size(font, text)
        # account for bbox left bearing
        bb = font.getbbox(text)
        tx = cx_px - tw // 2 - bb[0]
        ty_ = cy_line - bb[1]
        # engraved shadow (into the board, down-right)
        d.text((tx + 1, ty_ + 1), text, font=font, fill=shadow)
        d.text((tx + 2, ty_ + 2), text, font=font, fill=(0, 0, 0, 80))
        # gilt fill
        d.text((tx, ty_), text, font=font, fill=fill)
        # tooled highlight (upper-left)
        hi = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        hd = ImageDraw.Draw(hi)
        hd.text((tx - 1, ty_ - 1), text, font=font, fill=highlight)
        layer = Image.alpha_composite(layer, hi)
        return layer

    gilt = (232, 206, 128, 242)
    gilt_shadow = (40, 22, 8, 200)
    gilt_hi = (255, 236, 190, 160)
    latin_fill = (226, 196, 128, 230)

    line1_y = ty
    line2_y = ty + th + gap
    plate = Image.alpha_composite(plate, render_line(line1_draw, f1, line1_y, gilt, gilt_shadow, gilt_hi))
    plate = Image.alpha_composite(plate, render_line(line2, f2, line2_y, latin_fill, gilt_shadow, (255, 230, 180, 130)))

    # wear: break the gilt with leather texture and fine noise so it sits in the board
    # local wear on the plate alpha using the actual leather grain
    pa = np.array(plate).astype(np.float32)
    # noise
    rng = np.random.RandomState(777)
    noise = rng.normal(0, 1, pa.shape[:2]).astype(np.float32)
    noise = Image.fromarray(((noise - noise.min()) / (np.ptp(noise) + 1e-6) * 255).astype(np.uint8), "L")
    noise = noise.filter(ImageFilter.GaussianBlur(0.6))
    n = np.array(noise).astype(np.float32) / 255.0
    # leather luminance in the box only
    wear = np.ones((h, w), np.float32)
    leather_l = np.array(im.convert("L")).astype(np.float32) / 255.0
    # show leather grain in the gilt (darker leather eats gilt a little)
    grain = 0.78 + 0.32 * leather_l
    wear *= grain
    wear *= 0.82 + 0.28 * n
    # slightly stronger wear at plate edges
    yy, xx = np.ogrid[:h, :w]
    mx = np.clip((xx - x0) / max(box_w, 1), 0, 1)
    my = np.clip((yy - y0) / max(box_h, 1), 0, 1)
    edge = np.minimum(np.minimum(mx, 1 - mx), np.minimum(my, 1 - my))
    edge = np.clip(edge / 0.12, 0, 1)
    # only apply edge falloff inside the plate bbox
    inside = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    edge_mask = np.where(inside, edge, 1.0)
    wear *= 0.55 + 0.45 * edge_mask
    pa[..., 3] *= np.clip(wear, 0.35, 1.0)
    # mix a little leather colour into the gilt so it looks worn in
    leather_rgb = np.array(im).astype(np.float32)
    a = pa[..., 3:4] / 255.0
    pa[..., :3] = pa[..., :3] * 0.82 + leather_rgb * 0.18
    plate = Image.fromarray(pa.clip(0, 255).astype(np.uint8), "RGBA")

    out = Image.alpha_composite(im.convert("RGBA"), plate).convert("RGB")
    return out


if __name__ == "__main__":
    src = Path("/workspace/pb-entrance-work/v-new/chamber-sicker.jpg")
    im = Image.open(src).convert("RGB")
    dest = Path("/workspace/pb-entrance-work/step1b")
    for name in ("upper", "lower"):
        stamped = stamp_title(im.copy(), variant=name)
        stamped.save(dest / f"chamber-titled-{name}.jpg", quality=93, subsampling=0)
        # close crops
        if name == "upper":
            stamped.crop((720, 160, 1160, 420)).save(dest / f"title-crop-{name}.jpg", quality=94)
        else:
            stamped.crop((700, 680, 1180, 900)).save(dest / f"title-crop-{name}.jpg", quality=94)
        print("wrote", name)
