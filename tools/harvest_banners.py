"""Find every variant of a HUD banner in a recording (e.g. Marvel Rivals "KO" / "DOUBLE!" / "TRIPLE!").

Detects onsets of a constant part of the banner (the emblem) and clusters the text area right
of it, so the variants can be labelled and cut as templates.

Usage:
  .venv/bin/python tools/harvest_banners.py VIDEO --game marvel-rivals --region ko_region \\
      --template calib/marvel-rivals/emblem.png --out /tmp/banners
  -> prints onsets with their cluster id and writes banner_clusters.png (one tile per cluster)
"""
import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from killclip import detect, feed, media  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video")
    p.add_argument("--game", default="marvel-rivals")
    p.add_argument("--region", default="ko_region", help="config key of the region to scan")
    p.add_argument("--template", required=True, help="png of the constant part of the banner")
    p.add_argument("--threshold", type=float, default=0.75)
    p.add_argument("--release", type=float, default=0.5)
    p.add_argument("--text-offset", type=int, default=96, help="px right of the template match where the text starts")
    p.add_argument("--text-width", type=int, default=120)
    p.add_argument("--fps", type=int, default=5)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    cfg = detect.load_config(detect.config_path(a.game), a.game)
    info = media.probe(a.video)
    W, H = info["width"], info["height"]
    tmpl = feed.load_templates(a.template)
    th, tw = tmpl[0].shape
    on, pending, onsets, clusters = False, None, [], []
    for t, crop in media.iter_crops(a.video, cfg[a.region], a.fps, W, H, calib_height=cfg["calib_height"]):
        s, x, y = feed.match_max(crop, tmpl)
        if s >= a.threshold and not on:
            on, pending = True, (t, s, 2)  # take the text two frames after the onset (animation settles)
        elif s < a.release:
            on = False
        if pending:
            t0, s0, wait = pending
            if wait > 0:
                pending = (t0, s0, wait - 1)
            else:
                pending = None
                text = crop[max(0, y - 6): y + th + 6, x + a.text_offset: x + a.text_offset + a.text_width]
                if text.shape[0] < th or text.shape[1] < 40:
                    continue
                text = cv2.resize(text, (a.text_width, th + 12))
                best = max(((float(cv2.matchTemplate(text, c["img"], cv2.TM_CCOEFF_NORMED)[0, 0]), i)
                            for i, c in enumerate(clusters)), default=(0, -1))
                if best[0] >= 0.8:
                    clusters[best[1]]["n"] += 1
                    cid = best[1]
                else:
                    clusters.append({"img": text, "n": 1, "first": t0})
                    cid = len(clusters) - 1
                onsets.append((t0, s0, cid))
    os.makedirs(a.out, exist_ok=True)
    print(f"{len(onsets)} banner onsets, {len(clusters)} text clusters")
    for i, c in enumerate(clusters):
        print(f"  cluster {i}: {c['n']} onsets, first at {c['first']:.1f}s")
    print("onsets (t: cluster):", " ".join(f"{t:.1f}:{c}" for t, _, c in onsets))
    tiles = [cv2.resize(cv2.copyMakeBorder(c["img"], 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255), None, fx=3, fy=3,
                        interpolation=cv2.INTER_CUBIC) for c in clusters]
    cv2.imwrite(os.path.join(a.out, "banner_clusters.png"), np.hstack(tiles) if tiles else np.zeros((10, 10), np.uint8))
    with open(os.path.join(a.out, "onsets.txt"), "w") as f:
        f.writelines(f"{t:.1f}\t{s:.3f}\t{c}\n" for t, s, c in onsets)


if __name__ == "__main__":
    main()
