"""Find kills with the local vision-language model instead of templates: sample the kill feed every
few seconds, let Qwen3-VL read the rows, and turn rows with the player's name on the left into kills.
Writes the same events file as `killclip detect`, so `cut` and `beatsync` work on it.

Usage: .venv/bin/python tools/vlm_detect.py <video> --game battlefield-6-mp --out events.json [--every 3]
"""
import argparse, json, os, re, subprocess, sys, tempfile, time
import cv2, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from killclip import detect, media

def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("--game", default="battlefield-6-mp"); ap.add_argument("--out", required=True)
ap.add_argument("--every", type=float, default=3.0, help="seconds between sampled frames (feed rows last ~9 s)")
ap.add_argument("--row-life", type=float, default=12.0, help="the same victim within this many seconds is the same row")
ap.add_argument("--min-seen", type=int, default=2, help="a row must be read in this many samples (drops model hallucinations)")
ap.add_argument("--workdir", default=tempfile.mkdtemp(prefix="vlm-"))
a = ap.parse_args()
cfg = detect.load_config(os.path.join(ROOT, "configs", a.game + ".json"))
info = media.probe(a.video); player = cfg["player_name"].lower()
os.makedirs(a.workdir, exist_ok=True)
times = np.arange(a.every / 2, info["duration"], a.every)
t0 = time.time(); paths = []
for i, t in enumerate(times):
    crop = media.grab_crop(a.video, float(t), cfg["feed_region"], info["width"], info["height"], cfg["calib_height"])
    p = os.path.join(a.workdir, f"t{t:07.1f}.png")
    cv2.imwrite(p, cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)); paths.append(p)
    if i % 50 == 0: print(f"crops {i}/{len(times)}", flush=True)
print(f"crops {len(times)}/{len(times)} in {time.time() - t0:.0f}s", flush=True)

t0 = time.time()
proc = subprocess.Popen([os.path.join(ROOT, ".venv-vlm", "bin", "python"), os.path.join(ROOT, "tools", "vlm_feed.py"), *paths],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
active, events, singles, n = [], [], 0, 0
for line in proc.stdout:
    if not line.startswith('{"file"'):
        continue
    r = json.loads(line); n += 1
    t = float(os.path.basename(r["file"])[1:-4])
    m = re.search(r"\[.*\]", r["text"], re.S)
    try:
        rows = json.loads(m.group(0)) if m else []
    except Exception:
        rows = []
    seen = []
    for row in rows:
        if not isinstance(row, dict) or lev(str(row.get("killer", "")).lower(), player) > 2:
            continue
        v = str(row.get("victim", "")).strip()
        if any(lev(v.lower(), s.lower()) <= 2 for s in seen):
            continue                                                 # the model repeated a row
        seen.append(v)
        hit = next((x for x in active if lev(x["victim"].lower(), v.lower()) <= 2 and t - x["last"] <= a.row_life), None)
        if hit:
            hit["last"], hit["seen"] = t, hit["seen"] + 1
        else:
            hit = {"victim": v, "first": t, "last": t, "seen": 1, "fired": False}
            active.append(hit)
        if hit["seen"] >= a.min_seen and not hit["fired"]:
            hit["fired"] = True
            kill_t = round(max(0.0, hit["first"] - a.every / 2), 2)  # the row appeared some time in the previous interval
            events.append({"t": kill_t, "kills": 1, "victims": [v], "source": "vlm", "score": 1.0})
            print(f"kill {kill_t:8.2f}s  victim {v!r}", flush=True)
    if n % 25 == 0: print(f"read {n}/{len(paths)}", flush=True)
proc.wait()
singles = sum(1 for x in active if not x["fired"])
print(f"read {n}/{len(paths)} in {time.time() - t0:.0f}s; {len(events)} kills; {singles} rows seen only once were ignored", flush=True)
ms = detect.moments(events, cfg, info["duration"])
detect.write(a.out, a.video, cfg, ms)
print(f"{len(ms)} moments, {len(events)} kills -> {a.out}", flush=True)
