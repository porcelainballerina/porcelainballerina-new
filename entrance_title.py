#!/usr/bin/env python3
"""Entrance book-title inscription. Swap the two strings here when the wording changes later.

Step 1e: large Trajan/Cinzel roman capitals tooled into a reserved leather field
on the cover (no plate, no box, no blackletter). Keep warn-gate.js a11y copy
in sync with these strings (case on the cover is full capitals).
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

TITLE_LINE_1 = "The door is sealed"
TITLE_LINE_2 = "Atramentum Custodit"

# Reserved title field on the front board, upper third, above the main wax.
# Fractions of the 1920x1080 chamber. Lettering itself is sized to ~75% of
# the cover width (~704–1150).
FIELD = dict(cx=0.474, cy=0.244, w=0.205, h=0.176)

FONT_CINZEL = Path("/workspace/pb-entrance-work/step1e/fonts/Cinzel-700.ttf")


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
    boxes = []
    for ch, cw, cb in zip(text, widths, bearings):
        px, py = x - cb[0], ty - cb[1]
        draw.text((px, py), ch, font=font, fill=fill)
        boxes.append((px + cb[0], py + cb[1], px + cb[2], py + cb[3]))
        x += cw + spacing
    return boxes, total


def _diamond(draw, cx, cy, rx, ry, fill):
    draw.polygon([(cx, cy - ry), (cx + rx, cy), (cx, cy + ry), (cx - rx, cy)], fill=fill)


def _build_design(work_w: int, work_h: int, line1: str, line2: str, scale: int):
    """Frontal high-res stamp: two lines of roman caps and a mid rule. No frame."""
    mask = Image.new("L", (work_w, work_h), 0)
    d = ImageDraw.Draw(mask)
    line1_d = line1.upper()
    line2_d = line2.upper()

    # leave a generous leather margin so the field can be larger than the type
    inner_w = int(work_w * 0.80)
    size1 = int(work_h * 0.38)
    size2 = int(work_h * 0.225)
    f1 = _font(FONT_CINZEL, size1)
    f2 = _font(FONT_CINZEL, size2)

    # letter-spacing typical of tooled monumental caps
    spacing1 = max(1, int(0.06 * size1))
    spacing2 = max(1, int(0.055 * size2))

    def fitted(text, font, size, spacing, max_w, path):
        tw, th, _ = _bbox(font, text)
        tw += spacing * max(0, len(text) - 1)
        if tw > max_w:
            size = int(size * max_w / tw)
            font = _font(path, size)
            spacing = max(1, int((0.06 if text == line1_d else 0.055) * size))
            tw, th, _ = _bbox(font, text)
            tw += spacing * max(0, len(text) - 1)
        return font, size, spacing, tw, th

    f1, size1, spacing1, tw1, th1 = fitted(line1_d, f1, size1, spacing1, inner_w, FONT_CINZEL)
    f2, size2, spacing2, tw2, th2 = fitted(line2_d, f2, size2, spacing2, int(inner_w * 0.96), FONT_CINZEL)

    gap = int(10 * scale)
    orn_h = int(8 * scale)
    total = th1 + gap + orn_h + gap + th2
    ty = (work_h - total) // 2
    cx = work_w // 2

    _draw_tracked(d, line1_d, f1, cx, ty, 255, spacing=spacing1)
    mid_y = ty + th1 + gap + orn_h // 2
    rule_w = max(2, int(2.2 * scale))
    hair = max(1, int(1.1 * scale))
    # double tooled rule with a lozenge stop — classic binder ornament, not a star
    arm = int(42 * scale)
    gap_d = int(10 * scale)
    for y_off, wdt in ((-int(1.6 * scale), rule_w), (int(1.6 * scale), hair)):
        d.line([(cx - arm, mid_y + y_off), (cx - gap_d, mid_y + y_off)], fill=255, width=wdt)
        d.line([(cx + gap_d, mid_y + y_off), (cx + arm, mid_y + y_off)], fill=255, width=wdt)
    _diamond(d, cx, mid_y, int(5.5 * scale), int(3.6 * scale), 255)
    _draw_tracked(d, line2_d, f2, cx, ty + th1 + gap + orn_h + gap, 255, spacing=spacing2)

    # slight tool softening — a stamp, not a vector
    mask = mask.filter(ImageFilter.GaussianBlur(0.22 * scale))
    stamp = np.array(mask).astype(np.float32) / 255.0

    # reserved leather: a wide stadium / shallow cartouche, no drawn border.
    # Deep rounding so the field is not a postage-stamp rectangle.
    field_img = Image.new("L", (work_w, work_h), 0)
    df = ImageDraw.Draw(field_img)
    m = int(6 * scale)
    rad = int(min(work_h * 0.42, work_w * 0.18))
    df.rounded_rectangle((m, m, work_w - 1 - m, work_h - 1 - m), radius=rad, fill=255)
    field = np.array(field_img).astype(np.float32) / 255.0
    # slight irregularity so the reserve isn't laser-cut
    rng = np.random.RandomState(777)
    jitter = rng.normal(0, 1, field.shape).astype(np.float32)
    jitter = cv2.GaussianBlur(jitter, (0, 0), 4.0 * scale)
    jitter = jitter / (jitter.std() + 1e-6)
    field = np.clip(field + 0.04 * jitter * (field > 0.05), 0, 1)
    field = cv2.GaussianBlur(field, (0, 0), 3.6 * scale)
    return stamp, field


def _dst_quad(w, h, panel):
    cx, cy = panel["cx"] * w, panel["cy"] * h
    pw, ph = panel["w"] * w, panel["h"] * h
    x0, y0 = cx - pw / 2, cy - ph / 2
    x1, y1 = cx + pw / 2, cy + ph / 2
    # slight keystone so the field follows the standing cover
    tl = (x0 + 2, y0 + 1)
    tr = (x1 - 5, y0 + 5)
    br = (x1 - 2, y1 + 3)
    bl = (x0 + 1, y1 - 1)
    return np.float32([tl, tr, br, bl]), (x0, y0, x1, y1)


def _warp(src, dsize, quad):
    h, w = src.shape[:2]
    src_quad = np.float32([(0, 0), (w - 1, 0), (w - 1, h - 1), (0, h - 1)])
    M = cv2.getPerspectiveTransform(src_quad, quad)
    return cv2.warpPerspective(
        src, M, dsize, flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=0,
    )


def _synth_leather(cover, leather_l, field):
    """Build a clean worn-leather fill for the reserved title field.

    All bright sigils and white scratches are removed inside the field.
    Grain and colour stay in the same family as the surrounding cover.
    """
    h, w, _ = cover.shape
    # suppress bright ticks on a working copy so they cannot tint the estimate
    work = cover.copy()
    bright = leather_l > 0.16
    if bright.any():
        # fill bright pixels with a local dark neighbourhood
        dark = cover.copy()
        dark[bright] = 0
        wt = (~bright).astype(np.float32)
        k = 21
        kern = np.ones((k, k), np.float32)
        num = cv2.filter2D(dark, -1, kern)
        den = cv2.filter2D(wt, -1, kern)[..., None] + 1e-3
        local = num / den
        work[bright] = local[bright]

    low = cv2.GaussianBlur(work, (0, 0), 7.0)
    mid = cv2.GaussianBlur(work, (0, 0), 2.2) - cv2.GaussianBlur(work, (0, 0), 8.0)

    rng = np.random.RandomState(777)
    noise = rng.normal(0, 1, (h, w)).astype(np.float32)
    pores = cv2.GaussianBlur(noise, (0, 0), 0.9)
    pores = pores - cv2.GaussianBlur(pores, (0, 0), 3.5)
    # scale pores to a subtle leather variation
    pores = pores / (pores.std() + 1e-6)
    grain = mid + (pores * 5.0)[..., None] * np.array([1.0, 0.72, 0.62], np.float32)

    fill = low + grain
    # keep the field in the dark-leather range, slightly evened, not a black plate
    # lift from near-zero blacks so it still reads as leather
    fill = np.clip(fill, 0, 255)
    # a whisper of warmth, matching worn hide
    fill[..., 0] = np.clip(fill[..., 0] * 1.02 + 1.5, 0, 255)
    fill[..., 1] = np.clip(fill[..., 1] * 0.98 + 0.4, 0, 255)
    fill[..., 2] = np.clip(fill[..., 2] * 0.90, 0, 255)
    return fill


def _clean_field(cover, field, leather_l):
    """Replace the reserved field with clean leather. Soft edge, no plate border."""
    fill = _synth_leather(cover, leather_l, field)
    # core is fully replaced; the falloff lets surrounding sigils fade rather than hard-clip
    alpha = np.clip(field, 0, 1)[..., None]
    out = cover * (1.0 - alpha) + fill * alpha
    # very shallow sunken-panel dish, rim only — no tinted box
    dist = cv2.distanceTransform((field > 0.55).astype(np.uint8), cv2.DIST_L2, 3).astype(np.float32)
    rim = np.exp(-dist / 10.0) * field
    out = out * (1.0 - 0.10 * rim[..., None])
    return out.clip(0, 255)


def _tool_into_cover(cover, stamp, field):
    h, w, _ = cover.shape
    leather_l = cover.mean(axis=2) / 255.0
    cover = _clean_field(cover, field, leather_l)
    leather_l = cover.mean(axis=2) / 255.0

    blur = cv2.GaussianBlur(leather_l, (0, 0), 2.4)
    grain = leather_l - blur
    yy, xx = np.indices((h, w))
    # press the letters into the leather (small follow of grain, no tearing)
    dx = (0.55 * stamp + 0.6 * grain * stamp).astype(np.float32)
    dy = (1.45 * stamp + 0.6 * grain * stamp).astype(np.float32)
    displaced = cv2.remap(
        cover, (xx + dx).astype(np.float32), (yy + dy).astype(np.float32),
        interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT,
    )
    rec = cover * (1.0 - stamp[..., None]) + displaced * stamp[..., None]
    rec = rec * (1.0 - 0.28 * stamp[..., None])

    # bevel: candlelight from lower left
    gx = cv2.Sobel(stamp, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(stamp, cv2.CV_32F, 0, 1, ksize=3)
    gn = np.sqrt(gx * gx + gy * gy) + 1e-6
    lx, ly = -0.45, 0.82
    shade = -(gx * lx + gy * ly) / gn
    shade *= np.clip(gn * 2.4, 0, 1)
    shad = np.clip(-shade, 0, 1)
    high = np.clip(shade, 0, 1)
    rec = rec * (1.0 - 0.55 * shad[..., None])
    rec[..., 0] = np.clip(rec[..., 0] + 26 * high, 0, 255)
    rec[..., 1] = np.clip(rec[..., 1] + 16 * high, 0, 255)
    rec[..., 2] = np.clip(rec[..., 2] + 6 * high, 0, 255)
    erode = cv2.erode((stamp * 255).astype(np.uint8), np.ones((3, 3), np.uint8), 1)
    edge = np.clip(stamp - erode.astype(np.float32) / 255.0, 0, 1)
    rec = rec * (1.0 - 0.38 * edge[..., None])

    # gold leaf in the impressions — solid enough to read, worn on high spots
    inner = cv2.erode((stamp * 255).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1)
    inner = cv2.GaussianBlur(inner, (0, 0), 0.35).astype(np.float32) / 255.0
    rng = np.random.RandomState(777)
    coarse = rng.normal(0, 1, stamp.shape).astype(np.float32)
    coarse = cv2.GaussianBlur(coarse, (0, 0), 2.4)
    coarse = (coarse - coarse.min()) / (np.ptp(coarse) + 1e-6)
    fine = rng.normal(0, 1, stamp.shape).astype(np.float32)
    fine = cv2.GaussianBlur(fine, (0, 0), 0.55)
    fine = (fine - fine.min()) / (np.ptp(fine) + 1e-6)
    # wear: rubbed thinner on raised grain, but never thin enough to break a letter
    wear = 0.90 + 0.12 * (1.0 - np.clip(grain * 8, -0.2, 0.55))
    wear *= 0.86 + 0.16 * coarse
    wear *= 0.95 + 0.08 * fine
    wear = np.clip(wear, 0.72, 1.0)

    gilt_a = np.clip(inner * 0.99 + stamp * 0.22, 0, 1) * wear
    base = np.array([214.0, 172.0, 78.0])
    bright = np.array([248.0, 222.0, 138.0])
    spec = np.array([255.0, 244.0, 200.0])
    gilt = base * (0.90 + 0.12 * leather_l)[..., None]
    catch = np.clip(high, 0, 1) ** 1.3
    gilt = gilt * (1.0 - 0.70 * catch[..., None]) + bright * (0.70 * catch[..., None])
    spec_amt = np.clip(high - 0.48, 0, 1) ** 2 * 0.90
    gilt = gilt * (1.0 - spec_amt[..., None]) + spec * spec_amt[..., None]

    out = rec * (1.0 - gilt_a[..., None]) + gilt * gilt_a[..., None]
    return out.clip(0, 255)


def stamp_title(
    im: Image.Image,
    line1: str = TITLE_LINE_1,
    line2: str = TITLE_LINE_2,
    style: str = "roman",
    panel: dict | None = None,
) -> Image.Image:
    """Stamp line1/line2 into a reserved leather field on the grimoire cover."""
    im = im.convert("RGB")
    w, h = im.size
    panel = dict(FIELD if panel is None else panel)
    scale = 4
    work_w = int(panel["w"] * w * scale)
    work_h = int(panel["h"] * h * scale)
    stamp_f, field_f = _build_design(work_w, work_h, line1, line2, scale)
    quad, _ = _dst_quad(w, h, panel)
    stamp = np.clip(_warp(stamp_f, (w, h), quad), 0, 1)
    field = np.clip(_warp(field_f, (w, h), quad), 0, 1)
    cover = np.array(im).astype(np.float32)
    out = _tool_into_cover(cover, stamp, field)
    return Image.fromarray(out.astype(np.uint8), "RGB")


def title_bbox(w=1920, h=1080, panel: dict | None = None, pad=12):
    panel = dict(FIELD if panel is None else panel)
    cx, cy, pw, ph = panel["cx"] * w, panel["cy"] * h, panel["w"] * w, panel["h"] * h
    return (
        max(0, int(cx - pw / 2) - pad),
        max(0, int(cy - ph / 2) - pad),
        min(w, int(cx + pw / 2) + pad),
        min(h, int(cy + ph / 2) + pad),
    )


def _ocr_image(path: Path) -> str:
    r = subprocess.run(
        ["tesseract", str(path), "stdout", "--psm", "6", "-l", "eng"],
        capture_output=True, text=True, timeout=30,
    )
    return (r.stdout or "").strip()


def _norm_letters(s: str) -> str:
    return re.sub(r"[^A-Z]", "", s.upper())


def qa_title(im: Image.Image, dest: Path, line1: str = TITLE_LINE_1, line2: str = TITLE_LINE_2) -> dict:
    """Write 100%/200% crops and run tesseract. Returns a report dict."""
    dest.mkdir(parents=True, exist_ok=True)
    box = title_bbox(*im.size)
    crop = im.crop(box)
    crop.save(dest / "crop-100.jpg", quality=95, subsampling=0)
    crop2 = crop.resize((crop.size[0] * 2, crop.size[1] * 2), Image.Resampling.NEAREST)
    crop2.save(dest / "crop-200.jpg", quality=95, subsampling=0)
    # high-contrast gold-boosted copy to help OCR
    arr = np.array(crop).astype(np.float32)
    # emphasise yellowish gilt against dark leather
    gold = (arr[..., 0] * 0.50 + arr[..., 1] * 0.40 - arr[..., 2] * 0.10)
    gold = gold - gold.min()
    gold = gold / (gold.max() + 1e-6)
    hi = Image.fromarray((np.clip(gold, 0, 1) * 255).astype(np.uint8), "L")
    hi = hi.resize((hi.size[0] * 2, hi.size[1] * 2), Image.Resampling.LANCZOS)
    hi = hi.point(lambda p: 255 if p > 70 else 0)
    hi_path = dest / "crop-ocr.png"
    hi.save(hi_path)

    # tighter type-only crop (no surrounding sigil remnants) and per-line crops
    inset = crop.crop((int(crop.width*0.08), int(crop.height*0.22),
                       int(crop.width*0.92), int(crop.height*0.82)))
    inset_path = dest / "crop-inset.jpg"
    inset.save(inset_path, quality=95, subsampling=0)
    mid = inset.height // 2
    line1_im = inset.crop((0, 0, inset.width, mid))
    line2_im = inset.crop((0, mid, inset.width, inset.height))
    p1 = dest / "crop-line1.jpg"
    p2 = dest / "crop-line2.jpg"
    line1_im.save(p1, quality=95, subsampling=0)
    line2_im.save(p2, quality=95, subsampling=0)

    expect1 = _norm_letters(line1)
    expect2 = _norm_letters(line2)
    texts = {}
    for tag, path in (
        ("raw100", dest / "crop-100.jpg"),
        ("raw200", dest / "crop-200.jpg"),
        ("inset", inset_path),
        ("line1", p1),
        ("line2", p2),
        ("bin", hi_path),
    ):
        texts[tag] = _ocr_image(path)
    # also try psm 4 and 7 on the binary
    for psm in ("4", "7", "11"):
        r = subprocess.run(
            ["tesseract", str(hi_path), "stdout", f"--psm", psm, "-l", "eng"],
            capture_output=True, text=True, timeout=30,
        )
        texts[f"bin-psm{psm}"] = (r.stdout or "").strip()

    combined = " ".join(texts.values())
    letters = _norm_letters(combined)
    ok1 = expect1 in letters
    ok2 = expect2 in letters
    # per-source pass if a single read got both
    both = False
    for v in texts.values():
        n = _norm_letters(v)
        if expect1 in n and expect2 in n:
            both = True
            break
    report = {
        "ok_line1": ok1,
        "ok_line2": ok2,
        "ok_both_one_pass": both,
        "ok": ok1 and ok2,
        "expect": (line1.upper(), line2.upper()),
        "texts": texts,
        "box": box,
    }
    (dest / "ocr.txt").write_text(
        "OK" if report["ok"] else "FAIL" + "\n" +
        f"line1={ok1} line2={ok2} both_in_one={both}\n" +
        "\n".join(f"--- {k} ---\n{v}\n" for k, v in texts.items())
    )
    return report


if __name__ == "__main__":
    src = Path("/workspace/pb-entrance-work/step1c/chamber-quiet.jpg")
    dest = Path("/workspace/pb-entrance-work/step1e")
    dest.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    stamped = stamp_title(im)
    stamped.save(dest / "chamber-roman.jpg", quality=93, subsampling=0)
    stamped.resize((960, 540), Image.Resampling.LANCZOS).save(dest / "half-roman.jpg", quality=92)
    report = qa_title(stamped, dest)
    print("QA", {k: report[k] for k in ("ok", "ok_line1", "ok_line2", "ok_both_one_pass", "box")})
    for k, v in report["texts"].items():
        print(f"  [{k}] {v!r}")
