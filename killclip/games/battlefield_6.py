"""Battlefield 6.

Two HUDs. Battle Royale: a kill shows a score panel left of the crosshair with a grey "KILL"
box; that box is the event. Multiplayer (Conquest and the like): there is no box, but the kill
feed at the top right lists "> you  weapon  victim" for a kill and "killer  weapon  > you" for a
death; when the config gives `feed_region` and `name_template` the feed is the detector (the
`feed` mode below) and the KILL box is not used. In feed mode a kill is a new row with the name on
the left: rows are counted, and the count going up (seen twice, rows fade in) is the event.
Rows with the name on the right (the kill-cam) are ignored. "KILL CONFIRMED" boxes (a downed enemy bled out) share the letters, so every candidate
is scored against both a standalone-KILL template and the head of a KILL-CONFIRMED box, and
only wins by a margin count. The personal kill counter next to the skull icon (top right) is
read as the tally; it ticks for both, so it validates the total against the end-of-round
summary rather than timing the action.
"""
import glob
import logging
import os
from collections import deque

import cv2
import numpy as np

from .. import feed, media

log = logging.getLogger("killclip.games.battlefield_6")

DEFAULTS = {
    "panel_region": [0.20, 0.62, 0.50, 0.76],   # score panel, below-left of the crosshair
    "kill_template": None,                       # png of the grey "KILL" box (or a list of variants)
    "kill_confirmed_template": None,             # png of the head of a "KILL CONFIRMED" box, same size
    "kill_threshold": 0.8,                       # candidate boxes must match the KILL template this well ...
    "kill_margin": 0.10,                         # ... and beat the KILL CONFIRMED head by this much
    "kill_release": 0.65,                        # box must drop below this before a new kill counts
    "kill_refractory": 1.5,                      # the box animates in; one event per this many seconds
    "hud_region": [0.85, 0.05, 1.0, 0.095],      # top-right counters strip
    "skull_template": None,                      # png of the skull icon next to the kill counter
    "skull_threshold": 0.75,
    "digits_dir": None,                          # folder of <digit>_<n>.png glyph masks (tools/harvest_digits.py)
    "feed_region": None,                         # multiplayer HUD: kill feed box, top right; enables feed mode
    "name_template": None,                       # png(s) of the player's name as it appears in the feed
    "name_threshold": 0.75,
    "attacker_min_right": 120,                   # a row with this many px right of the name = the name is on the left = a kill
    "feed_settle": 2,                            # a new row must be seen in this many scans
    "feed_grace": 1.5,                           # a row not seen for this long (s) is gone; shorter gaps are flicker
}
TEMPLATE_KEYS = ("kill_template", "kill_confirmed_template", "skull_template", "name_template")
CW, CH = 20, 24  # glyph canvas


def regions(cfg):
    if cfg.get("feed_region"):
        return {"feed": cfg["feed_region"]}
    return {"panel": cfg["panel_region"], "hud": cfg["hud_region"]}


def kill_rows(crop, cfg, name_t):
    return [r for r in feed.feed_rows(crop, name_t, cfg["name_threshold"], cfg["attacker_min_right"]) if r["role"] == "kill"]


def make_refiner(cfg):
    """Returns refine(video, t, info, event) -> the first frame (at the recording's rate) where the kill
    shows, searching from 0.6 s before the scan-time event; used to land kills exactly on a beat.
    Battle Royale: the KILL box appears. Multiplayer feed mode: a kill row appears at the event's
    row position after that position was empty (an older row sitting there first moves up)."""
    feed_mode = bool(cfg.get("feed_region"))
    tmpl = feed.load_templates(cfg["name_template"] if feed_mode else cfg["kill_template"])
    region = cfg["feed_region"] if feed_mode else cfg["panel_region"]

    def refine(video, t, info, event=None):
        start = max(0.0, t - 0.6)
        seen_off = False
        rate = min(60, int(round(info.get("fps") or 60)))
        y_ev = (event or {}).get("y")
        for dt, crop in media.iter_crops(video, region, rate, info["width"], info["height"], start=start,
                                         dur=1.0, calib_height=cfg["calib_height"]):
            if feed_mode:
                rows = [r for r in feed.feed_rows(crop, tmpl, 0.55, cfg["attacker_min_right"])
                        if r["role"] == "kill" and (y_ev is None or abs(r["y"] - y_ev) <= 6)]
                on = any(r["score"] >= cfg["name_threshold"] for r in rows)
                off = not rows
            else:
                on = feed.match_max(crop, tmpl)[0] >= cfg["kill_threshold"]
                off = not on
            if on and seen_off:
                return start + dt
            seen_off |= off
        return t
    return refine


def glyphs(strip):
    """Binarized digit-sized blobs in a counter strip, left to right, on a fixed canvas."""
    lo, hi = int(strip.min()), int(strip.max())
    if strip.size == 0 or hi - lo < 60:
        return []
    b = (strip > lo + 0.55 * (hi - lo)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(b, 8)
    out = []
    for i in range(1, n):
        x, y, bw, bh, _ = st[i]
        if 15 <= bh <= 20 and 3 <= bw <= 15:
            canvas = np.zeros((CH, CW), np.uint8)
            ox, oy = (CW - bw) // 2, (CH - bh) // 2
            canvas[oy:oy + bh, ox:ox + bw] = (lab[y:y + bh, x:x + bw] == i)
            out.append((x, canvas))
    return [g for _, g in sorted(out, key=lambda p: p[0])]


def iou(a, b):
    union = np.logical_or(a, b).sum()
    return np.logical_and(a, b).sum() / union if union else 0.0


def ncc_at(img, tmpl, x, y):
    """Normalised correlation of tmpl with img at exactly (x, y)."""
    reg = img[y:y + tmpl.shape[0], x:x + tmpl.shape[1]]
    return float(cv2.matchTemplate(reg, tmpl, cv2.TM_CCOEFF_NORMED)[0, 0]) if reg.shape == tmpl.shape else 0.0


class Digits:
    """Reads the counter by snapping each glyph to the nearest labelled exemplar."""

    def __init__(self, folder):
        self.ex = [(int(os.path.basename(p).split("_")[0]), cv2.imread(p, 0) > 127)
                   for p in sorted(glob.glob(os.path.join(folder, "*_*.png")))]
        if not self.ex:
            raise FileNotFoundError(f"no digit exemplars in {folder}")

    def read(self, strip):
        """Counter value (trailing two digits; leading ghost zeros are ignored) or None."""
        digits = []
        for g in glyphs(strip):
            score, d = max((iou(g, e), d) for d, e in self.ex)
            if score < 0.6:
                return None
            digits.append(str(d))
        return int("".join(digits[-2:])) if digits else None


class Detector:
    def __init__(self, cfg, ocr=True):
        self.feed_mode = bool(cfg.get("feed_region"))
        if self.feed_mode:
            self.cfg, self.events = cfg, []
            self.name_t = feed.load_templates(cfg["name_template"])
            self.rows = []                                            # tracked kill rows: {y, first, last, hits, fired}
            return
        for key in TEMPLATE_KEYS + ("digits_dir",):
            if not cfg[key]:
                raise SystemExit(f"{key} is not set; see README for Battlefield 6 calibration")
        self.cfg = cfg
        self.kill = feed.load_templates(cfg["kill_template"])
        self.confirmed = feed.load_templates(cfg["kill_confirmed_template"])
        if self.confirmed[0].shape != self.kill[0].shape:
            raise SystemExit("kill_confirmed_template must be the same size as kill_template")  # scored at one spot
        self.skull = feed.load_templates(cfg["skull_template"])
        from ..paths import HOME as ROOT
        d = cfg["digits_dir"]
        self.digits = Digits(d if os.path.isabs(d) else os.path.join(ROOT, d))
        self.events = []
        self.box_on, self.last_kill = False, -99.0
        self.readings = deque(maxlen=15)   # (t, value) over the last 3 s at 5 fps
        self.count, self.credited = None, 0

    def standalone(self, panel):
        """(score, margin) of the best standalone KILL box, or None."""
        best = None
        for sk, x, y in feed.match_all(panel, self.kill, self.cfg["kill_threshold"]):
            margin = sk - max(ncc_at(panel, c, x, y) for c in self.confirmed)
            if margin >= self.cfg["kill_margin"] and (best is None or sk > best[0]):
                best = (sk, margin)
        return best

    def frame(self, t, crops):
        if self.feed_mode:
            return self.feed_frame(t, crops["feed"])
        return self.panel_frame(t, crops)

    def feed_frame(self, t, crop):
        """Rows enter at the bottom of the feed and only ever move up (pushed by newer rows), so a kill row
        that no tracked row can account for is a new kill. A row is tracked across short dropouts (the feed
        is translucent and the template score flickers with the background) and must be seen feed_settle
        times before it counts."""
        cfg = self.cfg
        self.rows = [r for r in self.rows if t - r["last"] <= cfg["feed_grace"]]
        for d in sorted(kill_rows(crop, cfg, self.name_t), key=lambda r: r["y"]):
            cands = [r for r in self.rows if r["y"] >= d["y"] - 6 and not r.get("taken")]
            if cands:
                r = min(cands, key=lambda r: r["y"] - d["y"])       # the nearest row above or at this position
                r.update(y=d["y"], last=t, hits=r["hits"] + 1, taken=True)
            else:
                r = {"y": d["y"], "first": t, "last": t, "hits": 1, "fired": False, "taken": True}
                self.rows.append(r)
            if r["hits"] >= cfg["feed_settle"] and not r["fired"]:
                r["fired"] = True
                self.events.append({"t": round(r["first"], 3), "kills": 1, "victims": [], "source": "feed", "score": 1.0, "y": r["y"]})
                log.info("kill %8.2fs: new feed row with the name on the left (y=%d)", r["first"], r["y"])
        for r in self.rows:
            r["taken"] = False

    def panel_frame(self, t, crops):
        hit = self.standalone(crops["panel"])
        if hit and not self.box_on and t - self.last_kill >= self.cfg["kill_refractory"]:
            self.box_on, self.last_kill = True, t
            self.events.append({"t": t, "kills": 1, "victims": [], "source": "kill-box", "score": hit[0]})
            log.info("KILL box at %8.2fs (match %.2f, margin over KILL CONFIRMED %.2f)", t, hit[0], hit[1])
        elif feed.match_max(crops["panel"], self.kill)[0] < self.cfg["kill_release"]:
            self.box_on = False
        self._counter(t, crops["hud"])

    def _counter(self, t, hud):
        s, x, y = feed.match_max(hud, self.skull)
        if s < self.cfg["skull_threshold"]:
            return
        h, w = self.skull[0].shape
        self.readings.append((t, self.digits.read(hud[max(0, y - 4): y + h + 4, x + w + 2: x + w + 72])))
        recent = [v for _, v in list(self.readings)[-5:] if v is not None]
        if len(recent) < 3:
            return
        stable = max(set(recent), key=recent.count)
        if recent.count(stable) < 3:
            return
        if self.count is None:
            self.count = stable
            log.info("kill counter starts at %d (%.2fs)", stable, t)
        elif 1 <= stable - self.count <= 3:
            self.credited += stable - self.count
            log.info("kill counter %d -> %d at %8.2fs", self.count, stable, t)
            self.count = stable
        elif stable < self.count:
            older = [v for _, v in self.readings if v is not None]
            if older and older.count(stable) >= 0.8 * len(older):
                log.info("kill counter reset %d -> %d at %.2fs (new round?)", self.count, stable, t)
                self.count = stable

    def flush(self):
        if self.feed_mode:
            log.info("feed: %d kills", len(self.events))
            return
        log.info("counter: %d kills credited during the scan, final value %s; %d KILL boxes",
                 self.credited, self.count, len(self.events))

    def inspect(self, crops):
        if self.feed_mode:
            rows = feed.feed_rows(crops["feed"], self.name_t, self.cfg["name_threshold"], self.cfg["attacker_min_right"])
            lines = [f"feed: name score {feed.match_max(crops['feed'], self.name_t)[0]:.3f} (threshold {self.cfg['name_threshold']}); rows: "
                     + (", ".join(f"{r['role']} at x={r['x']} y={r['y']} ({r['score']:.2f})" for r in rows) or "none")]
            vis = cv2.cvtColor(crops["feed"], cv2.COLOR_GRAY2BGR)
            h, w = self.name_t[0].shape
            for r in rows:
                cv2.rectangle(vis, (r["x"], r["y"]), (r["x"] + w, r["y"] + h), (0, 0, 255) if r["role"] == "kill" else (0, 200, 255), 1)
            return lines, vis
        score, x, y = feed.match_max(crops["panel"], self.kill)
        hit = self.standalone(crops["panel"])
        lines = [f"KILL box score {score:.3f} (threshold {self.cfg['kill_threshold']}), "
                 f"margin over KILL CONFIRMED {score - max(ncc_at(crops['panel'], c, x, y) for c in self.confirmed):+.2f}"
                 f"{'  <- KILL' if hit else ''}"]
        s, sx, sy = feed.match_max(crops["hud"], self.skull)
        h, w = self.skull[0].shape
        strip = crops["hud"][max(0, sy - 4): sy + h + 4, sx + w + 2: sx + w + 72] if s >= self.cfg["skull_threshold"] else np.zeros((1, 1), np.uint8)
        lines.append(f"skull icon score {s:.3f}; counter reads {self.digits.read(strip)} ({len(glyphs(strip))} glyphs)")
        vis = cv2.cvtColor(crops["panel"], cv2.COLOR_GRAY2BGR)
        kh, kw = self.kill[0].shape
        cv2.rectangle(vis, (x, y), (x + kw, y + kh), (0, 0, 255) if score >= self.cfg["kill_threshold"] else (0, 200, 255), 1)
        return lines, vis
