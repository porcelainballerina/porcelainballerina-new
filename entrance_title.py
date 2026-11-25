#!/usr/bin/env python3
"""Entrance book-title inscription. Swap the two strings here when the wording changes later.

Two professional binding styles, stamped into the cover (no CSS, no sticker plate):
  - panel: gilt-tooled small-cap serif in a filleted cartouche with corner tools
  - blackletter: deeply blind-stamped blackletter with worn gold, austere rules

Keep warn-gate.js a11y copy in sync with these strings.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

TITLE_LINE_1 = "The door is sealed"
TITLE_LINE_2 = "Atramentum Custodit"

# Front-board panel, above the main wax, slightly overlapping the lower rims
# of the upper seals. Fractions of the 1920x1080 chamber.
PANEL = dict(cx=0.484, cy=0.262, w=0.200, h=0.128)

FONT_FELL_SC = Path("/usr/share/fonts/truetype/sand-box/google/IM Fell English SC/IMFellEnglishSC-Regular.ttf")
FONT_FELL_IT = Path("/usr/share/fonts/truetype/sand-box/google/IM Fell French Canon/IMFellFrenchCanon-Italic.ttf")
FONT_BLACK = Path("/usr/share/fonts/truetype/sand-box/google/UnifrakturMaguntia/UnifrakturMaguntia-Regular.ttf")


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def _bbox(font, text):
    b = font.getbbox(text)
    return b[2] - b[0], b[3] - b[1], b


def _draw_tracked(draw, text, font, cx, ty, fill, spacing=0):
    widths, bearings = [], []
    for ch in text:
        cb = font.getbbox(ch)
        widths.append(cb[2] - cb[0])
        bearings.append(cb)
    total = sum(widths) + spacing * max(0, len(text) - 1)
    x = cx - total / 2
    for ch, cw, cb in zip(text, widths, bearings):
        draw.text((x - cb[0], ty - cb[1]), ch, font=font, fill=fill)
        x += cw + spacing


def _rosette(draw, cx, cy, r, fill):
    """Four-petal binder's flower (not a star). Petals on the cardinals, dotted centre."""
    r = float(r)
    # petals
    for ang in (0, 90, 180, 270):
        rad = np.radians(ang)
        px = cx + np.cos(rad) * r * 0.55
        py = cy + np.sin(rad) * r * 0.55
        pr = r * 0.48
        draw.ellipse((px - pr, py - pr, px + pr, py + pr), fill=fill)
    # ring
    draw.ellipse((cx - r * 0.38, cy - r * 0.38, cx + r * 0.38, cy + r * 0.38), fill=fill)
    # centre hole left as leather: punch a darker core later via a slightly smaller unpainted? 
    # keep solid gold bud — the recess will hollow it naturally
    draw.ellipse((cx - r * 0.16, cy - r * 0.16, cx + r * 0.16, cy + r * 0.16), fill=fill)


def _diamond(draw, cx, cy, rx, ry, fill):
    draw.polygon([(cx, cy - ry), (cx + rx, cy), (cx, cy + ry), (cx - rx, cy)], fill=fill)


def _rule_points(x0, y, x1, n, amp, rng):
    pts = []
    for i in range(n):
        t = i / (n - 1)
        x = x0 + (x1 - x0) * t
        jitter = amp * (0.7 * np.sin(t * 6.1 + 0.4) + 0.5 * np.sin(t * 17.0) + 0.35 * rng.normal())
        pts.append((x, y + jitter))
    return pts


def _stroke_polyline(draw, pts, fill, width):
    if len(pts) < 2:
        return
    draw.line(pts, fill=fill, width=width, joint="curve")
    r = max(1, int(round(width / 2)))
    for x, y in (pts[0], pts[-1]):
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def _build_design(style: str, work_w: int, work_h: int, line1: str, line2: str, scale: int):
    mask = Image.new("L", (work_w, work_h), 0)
    field = Image.new("L", (work_w, work_h), 0)
    d = ImageDraw.Draw(mask)
    df = ImageDraw.Draw(field)
    rng = np.random.RandomState(777)

    margin = int(16 * scale)
    x0, y0 = margin, margin
    x1, y1 = work_w - margin, work_h - margin
    # prepared field: soft rounded panel, used only to inpaint sigils + shallow dish
    df.rounded_rectangle((x0 - int(2 * scale), y0 - int(2 * scale),
                          x1 + int(2 * scale), y1 + int(2 * scale)),
                         radius=int(6 * scale), fill=255)

    if style == "panel":
        line1_draw = line1.upper()
        inner_x0, inner_y0 = x0 + int(24 * scale), y0 + int(18 * scale)
        inner_x1, inner_y1 = x1 - int(24 * scale), y1 - int(18 * scale)
        inner_w = inner_x1 - inner_x0

        size1 = int(work_h * 0.27)
        size2 = int(work_h * 0.215)
        f1 = _font(FONT_FELL_SC, size1)
        f2 = _font(FONT_FELL_IT, size2)
        tw, th, _ = _bbox(f1, line1_draw)
        if tw > inner_w * 0.96:
            size1 = int(size1 * inner_w * 0.96 / tw)
            f1 = _font(FONT_FELL_SC, size1)
            tw, th, _ = _bbox(f1, line1_draw)
        tw2, th2, _ = _bbox(f2, line2)
        if tw2 > inner_w * 0.94:
            size2 = int(size2 * inner_w * 0.94 / tw2)
            f2 = _font(FONT_FELL_IT, size2)
            tw2, th2, _ = _bbox(f2, line2)

        gap = int(7 * scale)
        ornament_h = int(7 * scale)
        total = th + gap + ornament_h + gap + th2
        ty = (work_h - total) // 2
        cx = work_w // 2
        spacing1 = max(1, int(0.06 * size1))
        _draw_tracked(d, line1_draw, f1, cx, ty, 255, spacing=spacing1)
        mid_y = ty + th + gap + ornament_h // 2
        _diamond(d, cx, mid_y, int(5 * scale), int(3.2 * scale), 255)
        _stroke_polyline(d, [(cx - int(38 * scale), mid_y), (cx - int(9 * scale), mid_y)], 255, max(1, int(1.3 * scale)))
        _stroke_polyline(d, [(cx + int(9 * scale), mid_y), (cx + int(38 * scale), mid_y)], 255, max(1, int(1.3 * scale)))
        _draw_tracked(d, line2, f2, cx, ty + th + gap + ornament_h + gap, 255, spacing=0)

        w_out = max(2, int(3.0 * scale))
        w_in = max(1, int(1.4 * scale))
        inset = int(8 * scale)

        def rect_rules(ix0, iy0, ix1, iy1, width):
            n, amp = 48, 0.35 * scale
            _stroke_polyline(d, _rule_points(ix0, iy0, ix1, n, amp, rng), 255, width)
            _stroke_polyline(d, _rule_points(ix0, iy1, ix1, n, amp, rng), 255, width)
            pts_l, pts_r = [], []
            for i in range(n):
                t = i / (n - 1)
                y = iy0 + (iy1 - iy0) * t
                j = amp * (0.5 * np.sin(t * 9.0) + 0.3 * rng.normal())
                pts_l.append((ix0 + j, y))
                pts_r.append((ix1 + j, y))
            _stroke_polyline(d, pts_l, 255, width)
            _stroke_polyline(d, pts_r, 255, width)

        rect_rules(x0, y0, x1, y1, w_out)
        rect_rules(x0 + inset, y0 + inset, x1 - inset, y1 - inset, w_in)

        # corner flower tools sit on the fillet corners, clearly visible
        r_ros = int(9.5 * scale)
        _rosette(d, x0, y0, r_ros, 255)
        _rosette(d, x1, y0, r_ros, 255)
        _rosette(d, x1, y1, r_ros, 255)
        _rosette(d, x0, y1, r_ros, 255)
        # mid-side dots
        dot = int(2.4 * scale)
        for px, py in (
            ((x0 + x1) / 2, y0),
            ((x0 + x1) / 2, y1),
            (x0, (y0 + y1) / 2),
            (x1, (y0 + y1) / 2),
        ):
            d.ellipse((px - dot, py - dot, px + dot, py + dot), fill=255)

    elif style == "blackletter":
        line1_draw = line1  # title case, never all-caps blackletter
        inner_w = work_w - int(40 * scale)
        size1 = int(work_h * 0.38)
        size2 = int(work_h * 0.235)
        f1 = _font(FONT_BLACK, size1)
        f2 = _font(FONT_FELL_IT, size2)
        tw, th, _ = _bbox(f1, line1_draw)
        if tw > inner_w * 0.98:
            size1 = int(size1 * inner_w * 0.98 / tw)
            f1 = _font(FONT_BLACK, size1)
            tw, th, _ = _bbox(f1, line1_draw)
        tw2, th2, _ = _bbox(f2, line2)
        if tw2 > inner_w * 0.92:
            size2 = int(size2 * inner_w * 0.92 / tw2)
            f2 = _font(FONT_FELL_IT, size2)
            tw2, th2, _ = _bbox(f2, line2)

        gap = int(11 * scale)
        total = th + gap + th2
        ty = (work_h - total) // 2 + int(4 * scale)
        cx = work_w // 2
        _draw_tracked(d, line1_draw, f1, cx, ty, 255, spacing=0)
        _draw_tracked(d, line2, f2, cx, ty + th + gap, 255, spacing=0)

        w_rule = max(2, int(2.4 * scale))
        w_hair = max(1, int(1.15 * scale))
        pad_x = int(20 * scale)
        y_top = y0 + int(5 * scale)
        y_bot = y1 - int(5 * scale)
        for y, wdt in ((y_top, w_rule), (y_top + int(4.6 * scale), w_hair),
                       (y_bot - int(4.6 * scale), w_hair), (y_bot, w_rule)):
            _stroke_polyline(
                d,
                _rule_points(x0 + pad_x, y, x1 - pad_x, 40, 0.28 * scale, rng),
                255,
                wdt,
            )
        for y in (y_top, y_bot):
            _diamond(d, (x0 + x1) / 2, y, int(6.0 * scale), int(3.6 * scale), 255)
            _diamond(d, x0 + pad_x, y, int(3.4 * scale), int(2.3 * scale), 255)
            _diamond(d, x1 - pad_x, y, int(3.4 * scale), int(2.3 * scale), 255)
    else:
        raise ValueError(style)

    # slight softening: a binder's tool, not a vector
    mask = mask.filter(ImageFilter.GaussianBlur(0.28 * scale))
    field = field.filter(ImageFilter.GaussianBlur(1.6 * scale))
    return np.array(mask).astype(np.float32) / 255.0, np.array(field).astype(np.float32) / 255.0


def _dst_quad(w, h, panel):
    cx, cy, pw, ph = panel["cx"] * w, panel["cy"] * h, panel["w"] * w, panel["h"] * h
    x0, y0 = cx - pw / 2, cy - ph / 2
    x1, y1 = cx + pw / 2, cy + ph / 2
    # slight keystone: the cover recedes a hair to the right, top a touch narrower
    tl = (x0 + 2, y0 + 1)
    tr = (x1 - 4, y0 + 4)
    br = (x1 - 1, y1 + 3)
    bl = (x0 + 1, y1 - 1)
    return np.float32([tl, tr, br, bl])


def _warp(src, dsize, quad):
    h, w = src.shape[:2]
    src_quad = np.float32([(0, 0), (w - 1, 0), (w - 1, h - 1), (0, h - 1)])
    M = cv2.getPerspectiveTransform(src_quad, quad)
    return cv2.warpPerspective(
        src, M, dsize, flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0,
    )


def _follow_leather(arr, leather_l, amount=0.4):
    """Slight wobble so the tooling follows the leather, without tearing the gilt."""
    h, w = leather_l.shape
    # mid-frequency only — ignore sharp scratches so they cannot rip the stamp
    mid = cv2.GaussianBlur(leather_l, (0, 0), 7.0) - cv2.GaussianBlur(leather_l, (0, 0), 16.0)
    yy, xx = np.indices((h, w))
    dx = (amount * 6 * mid).astype(np.float32)
    dy = (amount * 5 * mid).astype(np.float32)
    return cv2.remap(
        arr, (xx + dx).astype(np.float32), (yy + dy).astype(np.float32),
        interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
    )


def _inpaint_marks(cover, leather_l, region):
    """Remove sharp bright sigil ticks inside region, leave the leather itself.

    Only high-frequency bright marks are touched, so TELEA cannot smear mid-tone
    leather into a muddy cloud.
    """
    blur = cv2.GaussianBlur(leather_l, (0, 0), 1.6)
    highs = (leather_l - blur) > 0.045
    bright_lines = (leather_l > 0.28) & (np.abs(leather_l - blur) > 0.03)
    marks = (highs | bright_lines) & (region > 0.08)
    mask = (marks.astype(np.uint8) * 255)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
    if mask.max() == 0:
        return cover.copy()
    bgr = cv2.cvtColor(cover.astype(np.uint8), cv2.COLOR_RGB2BGR)
    filled = cv2.inpaint(bgr, mask, 3, cv2.INPAINT_TELEA)
    filled_l = filled.mean(axis=2).astype(np.float32) / 255.0
    fblur = cv2.GaussianBlur(filled_l, (0, 0), 1.6)
    leftover = (((filled_l - fblur) > 0.05) & (filled_l > 0.26) & (region > 0.12)).astype(np.uint8) * 255
    leftover = cv2.dilate(leftover, np.ones((3, 3), np.uint8), iterations=1)
    if leftover.max() > 0:
        filled = cv2.inpaint(filled, leftover, 3, cv2.INPAINT_TELEA)
    return cv2.cvtColor(filled, cv2.COLOR_BGR2RGB).astype(np.float32)


def _prepare_field(cover, field, leather_l, style: str, stamp=None):
    """Prepare leather under the tooling without laying down a dark plate."""
    region = field
    if stamp is not None:
        kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        bed = cv2.dilate((stamp > 0.22).astype(np.uint8), kern).astype(np.float32)
        bed = cv2.GaussianBlur(bed, (0, 0), 1.6)
        region = np.clip(np.maximum(field, bed), 0, 1)
    filled = _inpaint_marks(cover, leather_l, region)
    # safe mid-frequency grain (no sharp white ticks)
    low = cv2.GaussianBlur(leather_l, (0, 0), 3.5)
    mid = low - cv2.GaussianBlur(low, (0, 0), 10.0)
    filled = filled + (mid * 22 * field)[..., None] * np.array([1.0, 0.92, 0.80])
    out = cover * (1.0 - field[..., None]) + filled * field[..., None]
    if style == "panel":
        # shallow sunken-panel rim only — no overall tinted box
        dist = cv2.distanceTransform((field > 0.45).astype(np.uint8), cv2.DIST_L2, 3).astype(np.float32)
        rim = np.exp(-dist / 8.0) * field
        out = out * (1.0 - 0.14 * rim[..., None])
    else:
        # blackletter: almost no tone change, just a whisper of settle under the letters
        out = out * (1.0 - 0.04 * field[..., None])
    return out.clip(0, 255)


def _tool_into_cover(cover, stamp, field, style: str):
    h, w, _ = cover.shape
    leather_l = cover.mean(axis=2) / 255.0
    cover = _prepare_field(cover, field, leather_l, style, stamp=stamp)
    leather_l = cover.mean(axis=2) / 255.0

    blur = cv2.GaussianBlur(leather_l, (0, 0), 2.4)
    grain = leather_l - blur
    yy, xx = np.indices((h, w))
    # press the stamp into the leather
    depth_px = 1.6 if style == "blackletter" else 1.3
    dx = (0.7 * stamp + 1.4 * grain * np.clip(stamp + 0.3 * field, 0, 1)).astype(np.float32)
    dy = (depth_px * stamp + 1.4 * grain * np.clip(stamp + 0.3 * field, 0, 1)).astype(np.float32)
    displaced = cv2.remap(
        cover, (xx + dx).astype(np.float32), (yy + dy).astype(np.float32),
        interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT,
    )
    rec = cover * (1.0 - stamp[..., None]) + displaced * stamp[..., None]
    depth = 0.36 if style == "blackletter" else 0.30
    rec = rec * (1.0 - depth * stamp[..., None])

    # bevel: candlelight from lower left
    gx = cv2.Sobel(stamp, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(stamp, cv2.CV_32F, 0, 1, ksize=3)
    gn = np.sqrt(gx * gx + gy * gy) + 1e-6
    lx, ly = -0.45, 0.80
    shade = -(gx * lx + gy * ly) / gn
    shade *= np.clip(gn * 2.2, 0, 1)
    shad = np.clip(-shade, 0, 1)
    high = np.clip(shade, 0, 1)
    rec = rec * (1.0 - 0.55 * shad[..., None])
    rec[..., 0] = np.clip(rec[..., 0] + 28 * high, 0, 255)
    rec[..., 1] = np.clip(rec[..., 1] + 17 * high, 0, 255)
    rec[..., 2] = np.clip(rec[..., 2] + 7 * high, 0, 255)
    erode = cv2.erode((stamp * 255).astype(np.uint8), np.ones((3, 3), np.uint8), 1)
    edge = np.clip(stamp - erode.astype(np.float32) / 255.0, 0, 1)
    rec = rec * (1.0 - 0.40 * edge[..., None])

    # --- gold leaf in the impressions: solid fill, worn, metallic catch ---
    inner = cv2.erode((stamp * 255).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1)
    inner = cv2.GaussianBlur(inner, (0, 0), 0.35).astype(np.float32) / 255.0
    rng = np.random.RandomState(777)
    noise = rng.normal(0, 1, stamp.shape).astype(np.float32)
    noise = cv2.GaussianBlur(noise, (0, 0), 0.55)
    # a coarser wear map so gilt rubs off in patches, not speckles
    coarse = rng.normal(0, 1, stamp.shape).astype(np.float32)
    coarse = cv2.GaussianBlur(coarse, (0, 0), 2.8)
    coarse = (coarse - coarse.min()) / (np.ptp(coarse) + 1e-6)
    fine = (noise - noise.min()) / (np.ptp(noise) + 1e-6)
    # high leather grain stands rub the leaf thinner
    wear = 0.86 + 0.18 * (1.0 - np.clip(grain * 8, -0.2, 0.6))
    wear *= 0.78 + 0.28 * coarse
    wear *= 0.92 + 0.12 * fine
    wear = np.clip(wear, 0.52, 1.0)

    if style == "blackletter":
        gilt_a = np.clip(inner * 0.98 + stamp * 0.28, 0, 1) * wear
        base = np.array([200.0, 156.0, 68.0])
        bright = np.array([244.0, 214.0, 124.0])
        spec = np.array([255.0, 240.0, 186.0])
    else:
        gilt_a = np.clip(inner * 0.99 + stamp * 0.26, 0, 1) * wear
        base = np.array([210.0, 166.0, 76.0])
        bright = np.array([246.0, 218.0, 132.0])
        spec = np.array([255.0, 244.0, 200.0])

    # leather stains the leaf a little
    gilt = base * (0.88 + 0.14 * leather_l)[..., None]
    catch = np.clip(high, 0, 1) ** 1.35
    gilt = gilt * (1.0 - 0.70 * catch[..., None]) + bright * (0.70 * catch[..., None])
    spec_amt = np.clip(high - 0.50, 0, 1) ** 2 * 0.90
    gilt = gilt * (1.0 - spec_amt[..., None]) + spec * spec_amt[..., None]

    out = rec * (1.0 - gilt_a[..., None]) + gilt * gilt_a[..., None]
    return out.clip(0, 255)


def stamp_title(
    im: Image.Image,
    line1: str = TITLE_LINE_1,
    line2: str = TITLE_LINE_2,
    style: str = "blackletter",
    panel: dict | None = None,
) -> Image.Image:
    """Stamp line1/line2 into the grimoire cover in a professional binding style."""
    im = im.convert("RGB")
    w, h = im.size
    panel = dict(PANEL if panel is None else panel)
    scale = 4
    work_w = int(panel["w"] * w * scale)
    work_h = int(panel["h"] * h * scale)
    stamp_f, field_f = _build_design(style, work_w, work_h, line1, line2, scale)
    quad = _dst_quad(w, h, panel)
    stamp = _warp(stamp_f, (w, h), quad)
    field = _warp(field_f, (w, h), quad)
    leather_l = np.array(im).astype(np.float32).mean(axis=2) / 255.0
    stamp = _follow_leather(stamp, leather_l, amount=0.45)
    field = _follow_leather(field, leather_l, amount=0.45)
    stamp = np.clip(stamp, 0, 1)
    if style == "blackletter":
        # no rectangular plate: only a tight halo around the tooled work
        kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        halo = cv2.dilate((stamp > 0.22).astype(np.uint8), kern)
        field = cv2.GaussianBlur(halo.astype(np.float32), (0, 0), 3.2)
        field = np.clip(field, 0, 1)
    else:
        field = np.clip(field, 0, 1)
    cover = np.array(im).astype(np.float32)
    out = _tool_into_cover(cover, stamp, field, style)
    return Image.fromarray(out.astype(np.uint8), "RGB")


if __name__ == "__main__":
    src = Path("/workspace/pb-entrance-work/step1c/chamber-quiet.jpg")
    im = Image.open(src).convert("RGB")
    dest = Path("/workspace/pb-entrance-work/step1d")
    dest.mkdir(parents=True, exist_ok=True)
    for style in ("panel", "blackletter"):
        stamped = stamp_title(im.copy(), style=style)
        stamped.save(dest / f"chamber-{style}.jpg", quality=93, subsampling=0)
        stamped.crop((700, 150, 1160, 430)).save(dest / f"crop-{style}.jpg", quality=95)
        stamped.resize((960, 540), Image.Resampling.LANCZOS).save(dest / f"half-{style}.jpg", quality=92)
        stamped.crop((760, 210, 1100, 340)).resize((680, 260), Image.Resampling.NEAREST).save(dest / f"zoom-{style}.jpg", quality=95)
        stamped.crop((720, 180, 860, 280)).resize((420, 300), Image.Resampling.NEAREST).save(dest / f"corner-{style}.jpg", quality=95)
        band = stamped.crop((700, 150, 1160, 430))
        band.resize((280, int(280 * band.size[1] / band.size[0])), Image.Resampling.LANCZOS).save(dest / f"phoneband-{style}.jpg", quality=95)
        print("wrote", style)
