"""Harvest hero portraits from the Marvel Rivals kill feed over a time range, group identical ones,
and write a contact sheet for labelling.

Usage: .venv/bin/python tools/harvest_portraits.py <video> --start 1059 --end 1420 --out DIR [--step 1.5]
Each feed row is "[killer portrait] killer  icon  >  victim  [victim portrait]"; rows are right-aligned,
so the victim slot is at a fixed x and the killer slot sits at the row's left edge, found per row.
"""
import argparse, json, os, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from killclip import detect, feed, grade, media

ROW_Y, ROW_H, ROW_STEP, TILE_W = 17, 34, 40, 42      # feed geometry at calib_height, measured from frames
VICTIM_X = 372

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("--game", default="marvel-rivals")
ap.add_argument("--start", type=float, default=0); ap.add_argument("--end", type=float)
ap.add_argument("--step", type=float, default=1.5); ap.add_argument("--out", required=True)
ap.add_argument("--same", type=float, default=0.80, help="tiles matching this well are the same portrait")
a = ap.parse_args()

cfg = detect.load_config(os.path.join(detect.ROOT, "configs", a.game + ".json"))
info = media.probe(a.video)
W, H, sc = media.scaled(info["width"], info["height"], cfg["calib_height"])
x0, y0, x1, y1 = media.region_px(cfg["feed_region"], W, H)
vf = grade.filters(info, "natural") + f"fps={1/a.step},{sc}crop={x1-x0}:{y1-y0}:{x0}:{y0}"
end = min(a.end or info["duration"], info["duration"])
cmd = ["ffmpeg", "-v", "error", "-ss", f"{a.start:.3f}", "-i", str(a.video), "-t", f"{end - a.start:.3f}",
       "-vf", vf, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
w, h = x1 - x0, y1 - y0
name_t = feed.load_templates(cfg["name_template"])

def row_left(gray, y):
    """x of the row panel's left edge, or None when this band holds no row. A row carries names and
    icons, so its middle is full of vertical edges; sky, sand and walls are not."""
    band = gray[y + 4: y + ROW_H - 8]
    if band.shape[0] < 8:
        return None
    if np.abs(cv2.Sobel(band[:, 120: 360], cv2.CV_32F, 1, 0, ksize=3)).mean() < 60:
        return None                                    # background, not a row
    col = cv2.blur(band.astype(float).mean(0).reshape(1, -1), (5, 1))[0]
    bright = col > (col.max() + col.min()) / 2
    idx = np.where(bright)[0]
    if len(idx) < 60:
        return None
    x = int(idx.min())
    return x if 20 <= x <= VICTIM_X - TILE_W else None

tiles, n = [], 0
while True:
    buf = proc.stdout.read(w * h * 3)
    if len(buf) < w * h * 3:
        break
    t = a.start + n * a.step; n += 1
    col = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    gray = cv2.cvtColor(col, cv2.COLOR_BGR2GRAY)
    mine = {r["y"]: r for r in feed.feed_rows(gray, name_t, cfg["name_threshold"], cfg["attacker_min_right"])}
    for k in range(4):
        y = ROW_Y + ROW_STEP * k
        if y + ROW_H > h:
            break
        x = row_left(gray, y)
        if x is None:
            continue
        for slot, sx in (("killer", x), ("victim", VICTIM_X)):
            tile = col[y - 4: y + ROW_H - 4, sx: sx + TILE_W]
            if tile.shape[:2] != (ROW_H, TILE_W) or cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY).std() < 18:
                continue                                # flat: no portrait there
            tiles.append({"t": round(t, 2), "row": k, "slot": slot, "img": tile,
                          "mine": any(abs(ry - y) <= 6 for ry in mine)})
proc.wait()
print(f"{n} frames sampled, {len(tiles)} portrait tiles")

def score(a_img, b_img):
    inner = cv2.cvtColor(a_img, cv2.COLOR_BGR2GRAY)[3:31, 7:37]
    return float(cv2.matchTemplate(cv2.cvtColor(b_img, cv2.COLOR_BGR2GRAY), inner, cv2.TM_CCOEFF_NORMED).max())

groups = []                                             # each: {"members": [tile], "reps": [img]}
for tl in tiles:
    hit = None
    for g in groups:
        if max(score(tl["img"], r) for r in g["reps"]) >= a.same:
            hit = g; break
    if hit is None:
        groups.append({"members": [tl], "reps": [tl["img"]]})
    else:
        hit["members"].append(tl)
        if len(hit["reps"]) < 6:                        # keep a few backgrounds as references
            hit["reps"].append(tl["img"])
groups.sort(key=lambda g: -len(g["members"]))
print(f"{len(groups)} distinct portraits ({sum(1 for g in groups if len(g['members']) >= 3)} seen 3+ times)")

os.makedirs(a.out, exist_ok=True)
sheet, meta = [], []
for i, g in enumerate(groups):
    best = max(g["members"], key=lambda m: cv2.cvtColor(m["img"], cv2.COLOR_BGR2GRAY).std())
    cv2.imwrite(os.path.join(a.out, f"p{i:02d}.png"), best["img"])
    meta.append({"id": f"p{i:02d}", "count": len(g["members"]), "first_t": min(m["t"] for m in g["members"]),
                 "slots": sorted({m["slot"] for m in g["members"]}), "mine": any(m["mine"] and m["slot"] == "killer" for m in g["members"])})
    big = cv2.resize(best["img"], (TILE_W * 5, (ROW_H) * 5), interpolation=cv2.INTER_LANCZOS4)
    big = cv2.copyMakeBorder(big, 40, 6, 6, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cv2.putText(big, f"p{i:02d}  x{len(g['members'])}", (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(big, f"{meta[-1]['first_t']:.0f}s {'MINE' if meta[-1]['mine'] else '/'.join(meta[-1]['slots'])}", (8, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (90, 90, 90), 1)
    sheet.append(big)
json.dump(meta, open(os.path.join(a.out, "groups.json"), "w"), indent=1)
per = 6
while len(sheet) % per:
    sheet.append(np.full_like(sheet[0], 255))
cv2.imwrite(os.path.join(a.out, "sheet.png"), np.vstack([np.hstack(sheet[i:i + per]) for i in range(0, len(sheet), per)]))
print("sheet ->", os.path.join(a.out, "sheet.png"))
