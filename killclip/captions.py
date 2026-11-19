"""Subtitles for a clip, read from the game's own on-screen captions.

Transcribing the audio is the obvious approach and it is the worse one here. Game dialogue sits
under engine noise, music and gunfire, and on a GTA clip Whisper produced "It's been a lot gabbing
on the shelf with no rusty" where the game's own caption read "It's been a lot, yeah, we got to
chill, no Rusty". The game already did the hard part, so this reads that strip with OCR instead,
at 96% confidence on the same line.

Captions are white with a soft shadow over whatever the scene happens to be, so each sample is
tried at a few brightness thresholds and the reading with the best word confidence wins. Blobs too
large or too small to be letters are dropped first, which is what stops headlights and HUD icons
from becoming words.
"""
import logging
import os
import subprocess

import cv2
import numpy as np

from . import media, ocr, progress

log = logging.getLogger("killclip.captions")

THRESHOLDS = (180, 200, 215)
MIN_WORD_CONF = 55
MIN_LINE_CONF = 60
SAME = 0.6          # two readings this similar are the same caption
MIN_LETTERS = 0.70  # share of a reading that must be letters or spaces for it to be words


def _ocr(img, threshold):
    up = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, b = cv2.threshold(up, threshold, 255, cv2.THRESH_BINARY)
    n, lab, st, _ = cv2.connectedComponentsWithStats(b, 8)
    keep = np.zeros_like(b)
    for i in range(1, n):
        _, _, w, h, area = st[i]
        if 10 <= h <= 80 and 2 <= w <= 250 and area >= 25:      # letter-sized blobs only
            keep[lab == i] = 255
    words, confs = [], []
    for p in ocr.tsv(cv2.imencode(".png", 255 - keep)[1].tobytes(), psm=7):
        if len(p) >= 12 and p[11].strip():
            try:
                conf = float(p[10])
            except ValueError:
                continue
            if conf > MIN_WORD_CONF:
                words.append(p[11].strip())
                confs.append(conf)
    return " ".join(words), (float(np.mean(confs)) if confs else 0.0)


def _clean(text):
    """Drop tokens that carry no letters or digits: OCR turns highlights into '|', '~', '(TM)'."""
    return " ".join(w for w in text.split() if any(c.isalnum() for c in w)).strip()


def _plausible(text, conf=0.0):
    """OCR on a moving scene turns highlights and HUD icons into things like '| \\ (TM)'. Real dialogue
    is mostly letters and has at least a couple of words."""
    if len(text) < 5:
        return False
    letters = sum(c.isalpha() or c.isspace() or c in ".,'!?-" for c in text)
    if letters / len(text) < MIN_LETTERS:
        return False
    words = [w for w in text.split() if sum(c.isalpha() for c in w) >= 2]
    if len(words) >= 2:
        return True
    # a one-word line ("Alright.") is real only when the reading is a confident, wholly alphabetic word
    return bool(words) and conf >= 85 and sum(c.isalpha() for c in words[0]) >= 4


def _similar(a, b):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()


def read(video, region, step=0.5, calib_height=None):
    """[(t, text, confidence)] sampled across the whole clip."""
    info = media.probe(video)
    out = []
    # stop short of the final frame: seeking past it returns nothing to decode
    for t in np.arange(0.0, max(0.0, info["duration"] - 1.0 / max(info["fps"], 1)), step):
        progress.step("captions", float(t), info["duration"])
        try:
            img = media.grab_crop(video, float(t), region, info["width"], info["height"], calib_height)
        except Exception as e:
            log.debug("no frame at %.2fs: %s", t, e)
            continue
        best = max(((_clean(t), c) for t, c in (_ocr(img, thr) for thr in THRESHOLDS)),
                   key=lambda r: (len(r[0]) > 3, r[1]))
        if best[0] and best[1] >= MIN_LINE_CONF and _plausible(best[0], best[1]):
            out.append((float(t), best[0], best[1]))
    return out


def cues(samples, step=0.5, hold=0.6):
    """Readings of the same caption merged into [(start, end, text)], keeping the most confident
    wording. `hold` is how long a caption is assumed to stay up after the last sample that saw it."""
    out = []
    for t, text, conf in samples:
        if out and _similar(out[-1]["text"], text) >= SAME and t - out[-1]["end"] <= step * 3:
            c = out[-1]
            c["end"] = t
            # Prefer the reading that caught the most words. Confidence is averaged per word, so a
            # partial read ("It's been a lot, to chill") can outscore the full line it was cut from.
            if (len(text.split()), conf) > (len(c["text"].split()), c["conf"]):
                c["text"], c["conf"] = text, conf
        else:
            out.append({"start": t, "end": t, "text": text, "conf": conf})
    cues_ = [(c["start"], c["end"] + hold, c["text"]) for c in out]
    # never let one caption run over the next one's start
    return [(a, min(b, cues_[i + 1][0]) if i + 1 < len(cues_) else b, t)
            for i, (a, b, t) in enumerate(cues_)]


def write_srt(cues_, path):
    def ts(s):
        h, rem = divmod(s, 3600)
        m, rem = divmod(rem, 60)
        sec, ms = divmod(rem, 1)
        return f"{int(h):02d}:{int(m):02d}:{int(sec):02d},{int(ms * 1000):03d}"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        for i, (a, b, text) in enumerate(cues_, 1):
            f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{text}\n\n")
    return path


def from_video(video, region, out=None, step=0.5, calib_height=None):
    ocr.require()
    c = cues(read(video, region, step, calib_height), step)
    log.info("captions: %d lines from the game's own subtitles", len(c))
    for a, b, text in c:
        log.debug("  %6.1f-%5.1fs  %s", a, b, text)
    return (write_srt(c, out) if out else c)
