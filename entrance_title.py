#!/usr/bin/env python3
"""Entrance book-title inscription. Swap the two strings here when the wording changes later.

The title is deeply tooled / engraved into the grimoire cover itself — no plate, no sticker.
Keep warn-gate.js a11y copy in sync with these strings.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --- wording (easy to swap in a later step) ---
TITLE_LINE_1 = "The door is sealed"
TITLE_LINE_2 = "Atramentum Custodit"

# Cover geometry on the 1920x1080 chamber (fractions of full frame).
# Book is roughly x 0.367–0.600, y 0.146–0.791. Main seal top ~0.345.
TITLE_CX = 0.483
TITLE_CY = 0.252
TITLE_WIDTH = 0.200

FONT_TITLE = Path("/usr/share/fonts/truetype/sand-box/google/Cinzel/Cinzel-VariableFont_wght.ttf")
FONT_LATIN = Path("/usr/share/fonts/truetype/sand-box/google/IM Fell French Canon/IMFellFrenchCanon-Italic.ttf")


def _font(path: Path, size: int, weight=None) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(path), size=size)
    if weight is not None and hasattr(font, "set_variation_axes"):
        try:
            font.set_variation_axes({"wght": weight})
        except Exception:
            pass
    return font


def _text_size(font, text):
    b = font.getbbox(text)
    return b[2] - b[0], b[3] - b[1]


def _render_text_mask(size, lines, fonts, cx, cy, gap, letter_space=0):
    """Return a float32 mask in [0,1] of the two title lines, plus their pixel box."""
    w, h = size
    # render at 2x for cleaner stems, then downsample
    sc = 2
    canvas = Image.new("L", (w * sc, h * sc), 0)
    draw = ImageDraw.Draw(canvas)
    sizes = []
    fonts_hi = []
    for text, font in zip(lines, fonts):
        # rebuild at 2x
        # font.size is not always reliable on variable fonts; use bbox ratio
        bb = font.getbbox(text)
        px = max(8, (bb[3] - bb[1]) * sc)
        # approximate by using the same file
        path = font.path if hasattr(font, "path") else None
        sizes.append((text, font, px))

    # easier: render each line on its own 2x image via the original font by drawing
    # at 2x coordinates with a font opened at 2x size — we pass already-sized fonts
    # and just scale positions.
    # We'll instead accept pre-sized fonts and draw at 1x then upsample-smooth.
    # (cleaner: open 2x fonts)
    return None


def stamp_title(
    im: Image.Image,
    line1: str = TITLE_LINE_1,
    line2: str = TITLE_LINE_2,
    cx: float = TITLE_CX,
    cy: float = TITLE_CY,
    width: float = TITLE_WIDTH,
    variant: str = "upper",
) -> Image.Image:
    """Engrave line1/line2 into the grimoire cover as worn gold tooling. No plate."""
    im = im.convert("RGB")
    w, h = im.size
    if variant == "lower":
        cx, cy, width = 0.483, 0.735, 0.200

    box_w = int(width * w)
    # typographic measure only — no visible plate
    box_h = int(box_w * 0.34)
    x0 = int(cx * w - box_w / 2)
    y0 = int(cy * h - box_h / 2)
    x1, y1 = x0 + box_w, y0 + box_h

    line1_draw = line1.upper()
    size1 = max(20, int(box_h * 0.46))
    size2 = max(16, int(box_h * 0.32))
    f1 = _font(FONT_TITLE, size1, weight=650)
    f2 = _font(FONT_LATIN, size2)
    inner_w = box_w - 8
    tw, th = _text_size(f1, line1_draw)
    if tw > inner_w:
        size1 = max(14, int(size1 * inner_w / tw))
        f1 = _font(FONT_TITLE, size1, weight=650)
        tw, th = _text_size(f1, line1_draw)
    tw2, th2 = _text_size(f2, line2)
    if tw2 > inner_w:
        size2 = max(12, int(size2 * inner_w / tw2))
        f2 = _font(FONT_LATIN, size2)
        tw2, th2 = _text_size(f2, line2)

    gap = max(6, int(box_h * 0.10))
    total_h = th + gap + th2
    ty = y0 + (box_h - total_h) // 2
    cx_px = (x0 + x1) // 2

    # --- 2x mask for clean stems ---
    sc = 2
    mask_hi = Image.new("L", (w * sc, h * sc), 0)
    dhi = ImageDraw.Draw(mask_hi)
    f1h = _font(FONT_TITLE, size1 * sc, weight=650)
    f2h = _font(FONT_LATIN, size2 * sc)
    # slight letter-spacing for tooled caps
    def draw_spaced(draw, text, font, cx_, ty_, spacing=0):
        bb = font.getbbox(text)
        tw_ = bb[2] - bb[0]
        if spacing <= 0:
            draw.text((cx_ - tw_ // 2 - bb[0], ty_ - bb[1]), text, font=font, fill=255)
            return
        # per-glyph
        x = cx_ - tw_ // 2 - bb[0]
        # fallback: draw as a whole with a tracking hack
        # measure each char
        cursor = 0
        widths = []
        for ch in text:
            cb = font.getbbox(ch)
            widths.append(cb[2] - cb[0])
        total = sum(widths) + spacing * (len(text) - 1)
        x = cx_ - total // 2
        for ch, cw in zip(text, widths):
            cb = font.getbbox(ch)
            draw.text((x - cb[0], ty_ - cb[1]), ch, font=font, fill=255)
            x += cw + spacing

    line1_y = ty * sc
    line2_y = (ty + th + gap) * sc
    draw_spaced(dhi, line1_draw, f1h, cx_px * sc, line1_y, spacing=max(0, int(0.06 * size1 * sc)))
    draw_spaced(dhi, line2, f2h, cx_px * sc, line2_y, spacing=0)
    # slight optical softening so it doesn't look like sharp digital type on leather
    mask_hi = mask_hi.filter(ImageFilter.GaussianBlur(0.6))
    mask = mask_hi.resize((w, h), Image.Resampling.LANCZOS)
    m = np.array(mask).astype(np.float32) / 255.0
    if m.max() < 0.05:
        return im

    original = np.array(im).astype(np.float32)
    # compact the leather around the letters (follows the glyphs, not a rectangle)
    halo = cv2.GaussianBlur(m, (0, 0), 3.5)
    src = original * (1.0 - 0.22 * halo[..., None])
    leather_l = src.mean(axis=2) / 255.0
    original_l = original.mean(axis=2) / 255.0

    # local leather grain / cracks (high frequency of the cover)
    blur = cv2.GaussianBlur(leather_l, (0, 0), 2.2)
    grain = leather_l - blur  # signed
    # existing bright sigil scratches from the untouched cover
    scratches = np.clip((original_l - 0.22) / 0.35, 0, 1)

    # --- 1. physically recess the cover in the letter shapes ---
    # displace a copy of the cover slightly down-right into the trough
    yy, xx = np.indices((h, w))
    # 1.4 px into the board
    dx = (0.9 * m).astype(np.float32)
    dy = (1.3 * m).astype(np.float32)
    map_x = (xx + dx).astype(np.float32)
    map_y = (yy + dy).astype(np.float32)
    displaced = cv2.remap(
        src, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT
    )
    # mix recess only where letters are
    rec = src * (1.0 - m[..., None]) + displaced * m[..., None]
    # darken the trough (the cut into the board)
    rec = rec * (1.0 - 0.50 * m[..., None])
    # the cut goes through the painted sigils: crush their white inside the letters
    rec = rec * (1.0 - 0.78 * (scratches * m)[..., None])

    # --- 2. bevel: deboss lit by candlelight from lower left ---
    # image y increases downward; light from lower-left: (-x, +y)
    gx = cv2.Sobel(m, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(m, cv2.CV_32F, 0, 1, ksize=3)
    gn = np.sqrt(gx * gx + gy * gy) + 1e-6
    lx, ly = -0.55, 0.75
    # for a depression, invert the usual bump shading
    shade = -(gx * lx + gy * ly) / gn
    shade *= np.clip(gn * 1.8, 0, 1)  # only on edges
    # shadow (upper-right inner wall) and highlight (lower-left inner wall)
    shad = np.clip(-shade, 0, 1)
    high = np.clip(shade, 0, 1)
    rec = rec * (1.0 - 0.55 * shad[..., None])
    rec[..., 0] = np.clip(rec[..., 0] + 38 * high, 0, 255)
    rec[..., 1] = np.clip(rec[..., 1] + 26 * high, 0, 255)
    rec[..., 2] = np.clip(rec[..., 2] + 12 * high, 0, 255)

    # a thin dark cut-line around each stroke
    erode = cv2.erode((m * 255).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1)
    edge = np.clip(m - erode.astype(np.float32) / 255.0, 0, 1)
    rec = rec * (1.0 - 0.50 * edge[..., None])

    # --- 3. worn gilt sitting in the recesses ---
    # gold lives mainly in the trough, stronger in the deeper inner stroke,
    # worn off on high grain and on existing bright scratches
    inner = cv2.erode((m * 255).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1)
    inner = cv2.GaussianBlur(inner, (0, 0), 0.5).astype(np.float32) / 255.0
    rng = np.random.RandomState(777)
    noise = rng.normal(0, 1, m.shape).astype(np.float32)
    noise = cv2.GaussianBlur(noise, (0, 0), 0.8)
    noise = (noise - noise.min()) / (np.ptp(noise) + 1e-6)

    wear = 0.62 + 0.50 * leather_l - 0.55 * np.clip(grain * 8, 0, 1)
    wear *= 0.78 + 0.40 * noise
    # scratches and bright sigils eat the leaf
    wear *= 1.0 - 0.28 * scratches * m
    wear = np.clip(wear, 0.12, 1.0)

    gilt_a = np.clip(inner * 0.88 + m * 0.40, 0, 1) * wear
    # aged gilt — darker, less lemon than a sticker
    gilt = np.zeros_like(src)
    gilt[..., 0] = 214
    gilt[..., 1] = 176
    gilt[..., 2] = 96
    # pick up leather colour so the leaf belongs to the board
    gilt = gilt * 0.78 + src * 0.22
    # slightly brighter gold where the candle would catch the trough
    catch = np.clip(high * 0.45 + inner * 0.2, 0, 1)
    gilt = gilt + np.dstack((
        42 * catch,
        28 * catch,
        8 * catch,
    ))

    out = rec * (1.0 - gilt_a[..., None]) + gilt * gilt_a[..., None]
    # a last whisper of cover texture into the gold
    out = out * (1.0 - 0.06 * m[..., None]) + src * (0.06 * m[..., None])

    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGB")


if __name__ == "__main__":
    src = Path("/workspace/pb-entrance-work/v-new/chamber-sicker.jpg")
    im = Image.open(src).convert("RGB")
    dest = Path("/workspace/pb-entrance-work/step1c")
    dest.mkdir(parents=True, exist_ok=True)
    stamped = stamp_title(im.copy())
    stamped.save(dest / "title-only-test.jpg", quality=93, subsampling=0)
    stamped.crop((720, 160, 1160, 430)).save(dest / "title-crop.jpg", quality=95)
    stamped.resize((960, 540), Image.Resampling.LANCZOS).save(dest / "title-half.jpg", quality=92)
    print("title test written")
