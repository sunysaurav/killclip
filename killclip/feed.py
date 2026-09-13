"""Read the HUD: match the KO banner and the player's rendered name, OCR the victim."""
import logging
import re
import subprocess

import cv2
import numpy as np

log = logging.getLogger("killclip.feed")


def load_templates(paths):
    """One png path or a list of them (variants of the same element, e.g. "KO" and "DOUBLE!" banners)."""
    out = []
    for p in ([paths] if isinstance(paths, str) else paths):
        t = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if t is None:
            raise FileNotFoundError(f"template not found: {p}")
        out.append(t)
    return out


def _scores(img, tmpls):
    """Element-wise max of the match maps of all template variants (maps padded to a common size,
    top-left aligned), or None if img is too small for the first template."""
    if img.shape[0] < tmpls[0].shape[0] or img.shape[1] < tmpls[0].shape[1]:
        return None
    maps = [cv2.matchTemplate(img, t, cv2.TM_CCOEFF_NORMED) for t in tmpls
            if img.shape[0] >= t.shape[0] and img.shape[1] >= t.shape[1]]
    h, w = max(m.shape[0] for m in maps), max(m.shape[1] for m in maps)
    # pad (never trim): a smaller template has valid positions near the right and bottom edges
    return np.maximum.reduce([np.pad(m, ((0, h - m.shape[0]), (0, w - m.shape[1])), constant_values=-1.0) for m in maps])


def match_max(img, tmpls):
    """Best (score, x, y) of the template(s) in img."""
    r = _scores(img, tmpls)
    if r is None:
        return 0.0, 0, 0
    _, mx, _, (x, y) = cv2.minMaxLoc(r)
    return float(mx), x, y


def match_best(img, tmpls):
    """Best (score, x, y, template index) over the template variants."""
    best = (0.0, 0, 0, 0)
    for i, t in enumerate(tmpls):
        if img.shape[0] < t.shape[0] or img.shape[1] < t.shape[1]:
            continue
        _, mx, _, (x, y) = cv2.minMaxLoc(cv2.matchTemplate(img, t, cv2.TM_CCOEFF_NORMED))
        if mx > best[0]:
            best = (float(mx), x, y, i)
    return best


def match_all(img, tmpls, threshold):
    """All (score, x, y) >= threshold, best first, one per row (rows are template height apart)."""
    r = _scores(img, tmpls)
    if r is None:
        return []
    ys, xs = np.where(r >= threshold)
    kept, row_h = [], tmpls[0].shape[0] * 0.6
    for s, x, y in sorted(zip(r[ys, xs].tolist(), xs.tolist(), ys.tolist()), reverse=True):
        if all(abs(y - ky) >= row_h for _, _, ky in kept):
            kept.append((s, x, y))
    return kept


def feed_rows(feed, name_tmpl, threshold, attacker_min_right):
    """Feed rows showing the player's name, top to bottom.

    Rows are right-aligned. A victim's name is followed only by a hero icon before the edge;
    an attacker's name is followed by icons and the victim's name. So the player is the
    attacker (a kill) when at least attacker_min_right px of row remain right of the name.
    """
    rows = []
    for s, x, y in match_all(feed, name_tmpl, threshold):
        right = feed.shape[1] - (x + name_tmpl[0].shape[1])
        rows.append({"role": "kill" if right >= attacker_min_right else "death", "x": x, "y": y, "score": s})
    return sorted(rows, key=lambda r: r["y"])


def clean(text):
    return re.sub(r"^[^\w]+|[^\w]+$", "", text)


def victim_texts(feed, row, name_tmpl, upscale=3):
    """OCR the strip to the right of the name match with three preprocessings: [(text, confidence)].

    Adaptive threshold suits coloured names on a dark panel, plain inversion suits clean text,
    and a brightness threshold isolates white text over a busy background."""
    h, w = name_tmpl[0].shape
    strip = feed[max(0, row["y"] - 2): row["y"] + h + 2, row["x"] + w + 4:]
    if strip.size == 0 or strip.shape[1] < 10:
        return [("", 0.0)]
    big = cv2.resize(strip, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(big)
    bright = big > big.min() + 0.6 * (int(big.max()) - int(big.min()))
    variants = [cv2.adaptiveThreshold(clahe, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 15),
                255 - cv2.normalize(big, None, 0, 255, cv2.NORM_MINMAX),
                255 - bright.astype(np.uint8) * 255]
    return [ocr_words(v) for v in variants]


def victim_text(feed, row, name_tmpl, upscale=3):
    """Best (text, confidence) among the preprocessings."""
    return max(victim_texts(feed, row, name_tmpl, upscale), key=lambda r: r[1])


def ocr_words(img):
    """Single-line OCR: (joined words, lowest word confidence), keeping words of 3+ characters."""
    _, png = cv2.imencode(".png", img)
    tsv = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "7", "-l", "eng", "tsv"],
                         input=png.tobytes(), capture_output=True).stdout.decode("utf-8", "replace")
    words = []
    for line in tsv.splitlines()[1:]:
        c = line.split("\t")
        if len(c) >= 12 and c[0] == "5":
            text, conf = clean(c[11].strip()), float(c[10])
            if len(re.sub(r"[^\w]", "", text)) >= 3 and conf >= 40:
                words.append((text, conf))
    if not words:
        return "", 0.0
    return " ".join(t for t, _ in words), min(c for _, c in words)
