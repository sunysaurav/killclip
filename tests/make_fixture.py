"""Build a synthetic gameplay clip: fake kill feed rows, a KO banner, a fake kill sound.

Kills by PLAYER at 12.0, 27.5, 28.3 (double: the banner reads "2X" like the game's
"DOUBLE!"), 45.0. A death row at 35.0 and a teammate kill at 50.0 must not count.
A different sound plays at 20, 35, 50.
Writes fixture.json next to the video with the template boxes and regions.
"""
import json
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np
from scipy.io import wavfile

W, H, FPS, DUR, SR = 1280, 720, 30, 60, 48000
PLAYER = "PLAYER"
KILLS = [(12.0, "IronMan"), (27.5, "Hulk"), (28.3, "Venom"), (45.0, "Magik")]
OTHER_ROWS = [(35.0, "Loki", PLAYER), (50.0, "Buddy", "Thor")]
DISTRACTORS = [20.0, 35.0, 50.0]
ROW_LIFE = 5.0
FEED_X, FEED_Y, ROW_H = int(0.72 * W), int(0.06 * H), 34
KO_LIFE = 2.0
KO_X0, KO_Y0 = W - 260, 400
NAME_W = cv2.getTextSize(PLAYER, cv2.FONT_HERSHEY_DUPLEX, 0.7, 1)[0][0]
META = {
    "name_box": [W - 24 - cv2.getTextSize(f"{PLAYER}  [#]  >  IronMan", cv2.FONT_HERSHEY_DUPLEX, 0.7, 1)[0][0] - 3,
                 FEED_Y - 21,
                 W - 24 - cv2.getTextSize(f"{PLAYER}  [#]  >  IronMan", cv2.FONT_HERSHEY_DUPLEX, 0.7, 1)[0][0] + NAME_W + 3,
                 FEED_Y + 6],
    "emblem_box": [KO_X0 + 4, KO_Y0 + 6, KO_X0 + 56, KO_Y0 + 58],
    "ko_box": [W - 150, KO_Y0 + 10, W - 55, KO_Y0 + 55],
    "double_box": [W - 150, KO_Y0 + 10, W - 55, KO_Y0 + 55],
    "double_at": 28.6,
    "feed_region": [0.70, 0.01, 0.995, 0.35],
    "ko_region": [0.75, 0.50, 1.0, 0.70],
}


def banner(t):
    """'KO' for a kill, '2X' for a kill within 3 s of the previous one (the game's 'DOUBLE!'), or None."""
    live = [(i, tk) for i, (tk, _) in enumerate(KILLS) if tk <= t < tk + KO_LIFE]
    if not live:
        return None
    i, tk = live[-1]
    return "2X" if i and tk - KILLS[i - 1][0] <= 3.0 else "KO"


def sting():
    t = np.arange(int(0.35 * SR)) / SR
    return (0.6 * np.exp(-t * 9) * (np.sin(2 * np.pi * 1200 * t) + 0.6 * np.sin(2 * np.pi * 1800 * t))).astype(np.float32)


def distractor():
    t = np.arange(int(0.4 * SR)) / SR
    return (0.6 * np.exp(-t * 6) * np.sin(2 * np.pi * 700 * t)).astype(np.float32)


def make_audio():
    rng = np.random.default_rng(0)
    y = rng.normal(0, 0.03, DUR * SR).astype(np.float32)
    t = np.arange(len(y)) / SR
    y += 0.1 * np.sin(2 * np.pi * 110 * t) * np.sin(2 * np.pi * 0.5 * t)
    for tk, _ in KILLS:
        i = int(tk * SR); s = sting(); y[i:i + len(s)] += s
    for td in DISTRACTORS:
        i = int(td * SR); d = distractor(); y[i:i + len(d)] += d
    return np.clip(y, -1, 1)


def rows_at(t):
    rows = [(tk, PLAYER, v) for tk, v in KILLS] + list(OTHER_ROWS)
    return sorted([r for r in rows if r[0] <= t < r[0] + ROW_LIFE], key=lambda r: -r[0])


def make_video(path):
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    rng = np.random.default_rng(1)
    for n in range(DUR * FPS):
        t = n / FPS
        frame = np.full((H, W, 3), 40, np.uint8)
        cv2.circle(frame, (int(W / 2 + 300 * np.sin(t)), int(H / 2 + 150 * np.cos(1.3 * t))), 60, (30, 90, 200), -1)
        x = int(200 + 100 * np.sin(2 * t))
        cv2.rectangle(frame, (x, 500), (x + 200, 650), (60, 160, 60), -1)
        frame = cv2.add(frame, np.repeat(rng.integers(0, 25, (H, W, 1), dtype=np.uint8), 3, axis=2))
        label = banner(t)
        if label:
            cv2.rectangle(frame, (KO_X0, KO_Y0), (W - 40, KO_Y0 + 64), (40, 200, 230), -1)
            cv2.circle(frame, (KO_X0 + 30, KO_Y0 + 32), 22, (20, 20, 20), 3)   # the constant emblem
            cv2.line(frame, (KO_X0 + 16, KO_Y0 + 18), (KO_X0 + 44, KO_Y0 + 46), (20, 20, 20), 3)
            cv2.putText(frame, label, (W - 145, KO_Y0 + 50), cv2.FONT_HERSHEY_DUPLEX, 1.5, (20, 20, 20), 3, cv2.LINE_AA)
        for i, (_, att, vic) in enumerate(rows_at(t)):  # rows are right-aligned like the real HUD
            y = FEED_Y + i * ROW_H
            text = f"{att}  [#]  >  {vic}"   # [#] stands in for the weapon icon the real feed shows
            x = W - 24 - cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 0.7, 1)[0][0]
            cv2.rectangle(frame, (x - 10, y - 24), (W - 10, y + 8), (20, 20, 20), -1)
            cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_DUPLEX, 0.7, (240, 240, 240), 1, cv2.LINE_AA)
        vw.write(frame)
    vw.release()


def main(out):
    tmp = tempfile.mkdtemp()
    v, a = os.path.join(tmp, "v.mp4"), os.path.join(tmp, "a.wav")
    make_video(v)
    wavfile.write(a, SR, make_audio())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", v, "-i", a, "-c:v", "libx264", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out], check=True)
    with open(os.path.splitext(out)[0] + ".json", "w") as f:
        json.dump(META, f)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tests/fixture.mp4")
