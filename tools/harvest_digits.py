"""Harvest the digit glyphs of a HUD counter so killclip.games.battlefield_6 can read it.

Usage:
  .venv/bin/python tools/harvest_digits.py VIDEO --game battlefield-6 --start 540 --dur 1230 --out /tmp/glyphs
    -> writes glyph_classes.png (class exemplars in first-seen order) and glyph_bin.npy
  .venv/bin/python tools/harvest_digits.py --label /tmp/glyphs --labels 0,3,3,4,x,6 --out calib/battlefield-6/digits
    -> writes <digit>_<n>.png exemplars; 'x' skips a garbage class

Read glyph_classes.png left to right and type the digit each tile shows. Counts only go up,
so the tiles appear roughly in the order 0, 1, 2, ... with variants of the same digit next
to each other.
"""
import argparse
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from killclip import detect, feed, media  # noqa: E402
from killclip.games.battlefield_6 import glyphs, iou  # noqa: E402


def harvest(a):
    cfg = detect.load_config(detect.config_path(a.game), a.game)
    info = media.probe(a.video)
    W, H = info["width"], info["height"]
    skull = feed.load_templates(cfg["skull_template"])
    sh, sw = skull[0].shape
    x0, y0, x1, y1 = media.region_px(cfg["hud_region"], W, H)
    w, h = x1 - x0, y1 - y0
    cmd = ["ffmpeg", "-v", "error", "-hwaccel", "videotoolbox", "-skip_frame", "nokey", "-ss", str(a.start), "-i", a.video,
           "-t", str(a.dur), "-vf", f"crop={w}:{h}:{x0}:{y0}", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    classes, n = [], 0
    while True:
        buf = proc.stdout.read(w * h)
        if len(buf) < w * h:
            break
        n += 1
        hud = np.frombuffer(buf, np.uint8).reshape(h, w)
        s, x, y = feed.match_max(hud, skull)
        if s < cfg["skull_threshold"]:
            continue
        for g in glyphs(hud[max(0, y - 4): y + sh + 4, x + sw + 2: x + sw + 72]):
            score, i = max(((iou(g, k["g"]), i) for i, k in enumerate(classes)), default=(0, -1))
            if score >= 0.75:
                classes[i]["n"] += 1
                classes[i]["acc"] += g
            else:
                classes.append({"g": g, "acc": g.astype(np.float32), "first": n, "n": 1})
    proc.wait()
    keep = [k for k in sorted(classes, key=lambda k: k["first"]) if k["n"] >= a.min_members]
    os.makedirs(a.out, exist_ok=True)
    means = np.array([k["acc"] / k["n"] for k in keep])
    np.save(os.path.join(a.out, "glyph_bin.npy"), means)
    tiles = [cv2.resize(cv2.copyMakeBorder((m * 255).astype(np.uint8), 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=100),
                        None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST) for m in means]
    cv2.imwrite(os.path.join(a.out, "glyph_classes.png"), np.hstack(tiles))
    print(f"{n} keyframes, {len(classes)} classes, {len(keep)} kept -> {a.out}/glyph_classes.png")


def label(a):
    means = np.load(os.path.join(a.label, "glyph_bin.npy"))
    labels = a.labels.split(",")
    if len(labels) != len(means):
        sys.exit(f"{len(means)} classes but {len(labels)} labels")
    os.makedirs(a.out, exist_ok=True)
    count = {}
    for m, d in zip(means, labels):
        if not d.isdigit():
            continue
        count[d] = count.get(d, 0) + 1
        cv2.imwrite(os.path.join(a.out, f"{d}_{count[d]}.png"), (m >= 0.5).astype(np.uint8) * 255)
    print("exemplars per digit:", dict(sorted(count.items())), "missing:", sorted(set("0123456789") - set(count)))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", nargs="?")
    p.add_argument("--game", default="battlefield-6")
    p.add_argument("--start", type=float, default=0)
    p.add_argument("--dur", type=float, default=3600)
    p.add_argument("--min-members", type=int, default=3)
    p.add_argument("--out", required=True)
    p.add_argument("--label", help="folder from a previous harvest to label")
    p.add_argument("--labels", help="comma-separated digit per class, x to skip")
    a = p.parse_args()
    label(a) if a.label else harvest(a)
