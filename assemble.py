#!/usr/bin/env python3
"""Assemble the porcelainballerina-new test site from the pinned v4 seed + overlay.

Never writes a CNAME or sealed-room.html. Rewrites test-site URLs to this space.
"""
from __future__ import annotations
import argparse, shutil, sys
from pathlib import Path

OLD_BASE = "https://porcelainballerina.github.io/porcelainballerina-test"
NEW_BASE = "https://porcelainballerina.github.io/porcelainballerina-new"
NEW_V = "1795640000"
OLD_VS = ("1795547111", "1795594000", "1795602000", "1795612000", "1795624000", "1795632000")
TEXT_SUF = {".html", ".js", ".css", ".json", ".txt", ".xml", ".webmanifest", ".svg", ".md"}
SKIP_DIRS = {".git", ".github", ".staging-payload", ".src"}
SKIP_FILES = {"CNAME", "sealed-room.html"}
LIVE_GOAT = "https://porcelainballerina.goatcounter.com/count"


def copy_seed(seed: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for src in seed.iterdir():
        if src.name in SKIP_DIRS or src.name in SKIP_FILES:
            continue
        target = dest / src.name
        if src.is_dir():
            shutil.copytree(src, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*SKIP_FILES, ".git"))
        else:
            shutil.copy2(src, target)
    # belt and braces
    for bad in SKIP_FILES:
        p = dest / bad
        if p.exists():
            p.unlink()
            print("removed", bad)



def decode_plates(overlay: Path, dest: Path) -> None:
    import base64
    plate_dir = overlay / "plates"
    if not plate_dir.is_dir():
        return
    out_dir = dest / "images" / "gate-library"
    out_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(plate_dir.glob("*.webp.b64")):
        raw = "".join(src.read_text().split())
        if len(raw) % 4 != 0:
            raise SystemExit(f"bad b64 length for {src.name}: {len(raw)}")
        data = base64.b64decode(raw)
        name = src.name[:-4] if src.name.endswith(".b64") else src.name
        (out_dir / name).write_bytes(data)
        print("decoded", name, len(data))


def overlay_copy(overlay_site: Path, dest: Path) -> None:
    if not overlay_site.is_dir():
        raise SystemExit(f"missing overlay site: {overlay_site}")
    for src in overlay_site.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(overlay_site)
        if rel.name in SKIP_FILES or "sealed-room" in rel.name:
            raise SystemExit(f"refusing to overlay {rel}")
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        print("overlay", rel)


def rewrite_tree(dest: Path) -> None:
    n_url = n_ver = 0
    for p in dest.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXT_SUF:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        orig = text
        if OLD_BASE in text:
            text = text.replace(OLD_BASE, NEW_BASE)
            n_url += 1
        for ov in OLD_VS:
            if f"?v={ov}" in text:
                text = text.replace(f"?v={ov}", f"?v={NEW_V}")
                n_ver += 1
        if text != orig:
            p.write_text(text, encoding="utf-8")
    print(f"rewrote urls in {n_url} files, versions in {n_ver} files")


def assert_safe(dest: Path) -> None:
    if (dest / "CNAME").exists():
        raise SystemExit("CNAME present — abort")
    if (dest / "sealed-room.html").exists():
        raise SystemExit("sealed-room.html present — abort")
    robots = (dest / "robots.txt").read_text(encoding="utf-8")
    if "Disallow: /" not in robots:
        raise SystemExit("robots.txt missing Disallow")
    index = (dest / "index.html").read_text(encoding="utf-8")
    if "noindex" not in index:
        raise SystemExit("index.html missing noindex")
    if OLD_BASE in index:
        raise SystemExit("index.html still points at porcelainballerina-test")
    if NEW_BASE not in index:
        raise SystemExit("index.html missing new base URL")
    if LIVE_GOAT in index:
        raise SystemExit("live GoatCounter endpoint found — abort")
    # staging sink or none is fine
    print("safety checks ok: no CNAME, no sealed-room, noindex, no live GoatCounter")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=Path, required=True)
    ap.add_argument("--overlay", type=Path, required=True)
    ap.add_argument("--dest", type=Path, required=True)
    args = ap.parse_args()
    if args.dest.exists():
        shutil.rmtree(args.dest)
    print("copy seed", args.seed)
    copy_seed(args.seed, args.dest)
    overlay_site = args.overlay / "site" if (args.overlay / "site").is_dir() else args.overlay
    print("overlay", overlay_site)
    overlay_copy(overlay_site, args.dest)
    decode_plates(args.overlay, args.dest)
    rewrite_tree(args.dest)
    assert_safe(args.dest)
    print("assembled", args.dest)


if __name__ == "__main__":
    main()
