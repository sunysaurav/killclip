"""Marvel Rivals.

Two signals, both generic:

1. The kill banner. Its emblem is the same for every kill, whatever the word next to it
   ("KO", "DOUBLE!", "TRIPLE!", ...), so the emblem is the trigger. The word only labels the
   banner and tells one banner from the next in a streak: a new word is a new kill.
2. The kill feed (top right). Around the banner, the newest row that carries the player's name
   decides: name on the left means the player is the attacker (a kill); name on the right means
   someone killed the player, which is what the kill-cam replay shows with the enemy's banner.
   The player's own rows pulse, hiding the victim half for a frame, so a few frames vote.
"""
import logging

import cv2

from .. import feed, media

log = logging.getLogger("killclip.games.marvel_rivals")

DEFAULTS = {
    "ko_region": [0.78, 0.41, 1.0, 0.57],      # x0, y0, x1, y1 as fractions of the frame
    "ko_template": None,                        # png(s) of the banner emblem
    "ko_threshold": 0.75,
    "banner_texts": {},                         # {label: png(s) of the word}
    "banner_text_threshold": 0.8,
    "same_word_gap": 8.0,                       # the same word again within this is the same banner (it animates)
    "feed_region": [0.76, 0.02, 0.985, 0.20],
    "name_template": None,                      # png(s) of the player's name as the feed renders it
    "name_threshold": 0.9,
    "attacker_min_right": 90,                   # px of row right of the name that make it the attacker side
    "confirm_lead": 0.6,                        # feed rows can precede the banner by this much ...
    "confirm_window": 1.5,                      # ... or follow it by this much
    "history": 3.0,                             # rows already up this long before the banner are not new
}
TEMPLATE_KEYS = ("ko_template", "name_template", "banner_texts")


def regions(cfg):
    return {"ko": cfg["ko_region"], "feed": cfg["feed_region"]}


def make_refiner(cfg):
    """Returns refine(video, t, info) -> the first frame (at the recording's rate) where the banner emblem appears,
    searching from 0.5 s before the scan-time onset; used to land kills exactly on a beat. The emblem
    must be absent first: inside a streak the previous banner is still up when the window opens and
    is swapped out (emblem gone for a few frames) just before the new one comes in."""
    ko_t = feed.load_templates(cfg["ko_template"])

    def refine(video, t, info):
        start = max(0.0, t - 0.5)
        seen_off = False
        rate = min(60, int(round(info.get("fps") or 60)))
        for dt, crop in media.iter_crops(video, cfg["ko_region"], rate, info["width"], info["height"], start=start, dur=0.9,
                                         calib_height=cfg["calib_height"]):
            on = feed.match_max(crop, ko_t)[0] >= cfg["ko_threshold"]
            if on and seen_off:
                return start + dt
            seen_off |= not on
        return t
    return refine


class Detector:
    def __init__(self, cfg, ocr=True):
        for key in ("ko_template", "name_template"):
            if not cfg[key]:
                raise SystemExit(f"{key} is not set; run `killclip template` to create it (see README)")
        self.cfg, self.ocr = cfg, ocr
        self.ko_t = feed.load_templates(cfg["ko_template"])
        self.name_t = feed.load_templates(cfg["name_template"])
        self.texts = {label: feed.load_templates(paths) for label, paths in cfg["banner_texts"].items()}
        self.events, self.pending = [], None
        self.recent = []                        # (t, feed crop, newest row with the name or None) for the lead
        self.last_ko, self.cur_label = -99.0, None

    def frame(self, t, crops):
        cfg = self.cfg
        rows = feed.feed_rows(crops["feed"], self.name_t, cfg["name_threshold"], cfg["attacker_min_right"])
        newest = min(rows, key=lambda r: r["y"]) if rows else None   # the feed puts the newest row on top
        if newest:
            newest["right"] = crops["feed"].shape[1] - (newest["x"] + self.name_t[0].shape[1])
            if newest["role"] == "kill" and any(r["role"] == "death" for r in rows):
                newest["below_death"] = True   # a kill row above a death row: newer than the death
        self.recent = [r for r in self.recent if t - r[0] <= cfg["history"]] + [(t, crops["feed"], newest)]

        ko_score, _, _ = feed.match_max(crops["ko"], self.ko_t)
        on = ko_score >= cfg["ko_threshold"]
        label = self.read_label(crops["ko"]) if on else None
        new_word = on and label is not None and self.cur_label is not None and label != self.cur_label
        if on and (new_word or t - self.last_ko >= cfg["same_word_gap"]):
            self._finish()
            lead = [r for r in self.recent if t - r[0] <= cfg["confirm_lead"]]
            older = [r[2] for r in self.recent if t - r[0] > cfg["confirm_lead"] and r[2]]
            self.pending = {"t": t, "score": ko_score, "banner": label, "frames": lead, "older": older}
            self.last_ko, self.cur_label = t, label
            log.debug("banner at %.2fs emblem %.3f word %s", t, ko_score, label)
        elif on and label is not None and self.cur_label is None:
            self.cur_label = label              # the word became readable after the emblem
            if self.pending:
                self.pending["banner"] = self.pending["banner"] or label
        elif not on and t - self.last_ko >= cfg["same_word_gap"]:
            self.cur_label = None               # banner long gone: the next one is a new kill whatever its word
        if self.pending and self.pending["frames"][-1][0] < t:
            self.pending["frames"].append((t, crops["feed"], newest))
        if self.pending and t - self.pending["t"] >= cfg["confirm_window"]:
            self._finish()

    def read_label(self, ko_crop):
        """Word on the banner, or None when no known word matches."""
        best = max(((feed.match_max(ko_crop, tm)[0], label) for label, tm in self.texts.items()), default=(0, None))
        return best[1] if best[0] >= self.cfg["banner_text_threshold"] else None

    def flush(self):
        self._finish()

    def _finish(self):
        """Judge the pending banner by the newest feed row carrying the name around it."""
        p, self.pending = self.pending, None
        if not p:
            return
        # A row counts once seen at the same position (role, width right of the name) in two frames of
        # the window: rows slide into place and the feed can flicker. A row that was already up in
        # the seconds before the banner is not new. A new kill row of yours confirms the kill (even if
        # your death row lands on top a moment later, a trade). No new row, with your death row the
        # newest, is the kill-cam replay of your death.
        rows = [(fd, r) for _, fd, r in p["frames"] if r]
        same = lambda a, b: a["role"] == b["role"] and abs(a["right"] - b["right"]) <= 8
        settled = [(fd, r) for fd, r in rows if sum(1 for _, o in rows if same(o, r)) >= 2]
        new = [(fd, r) for fd, r in settled if not any(same(o, r) for o in p["older"])]
        kills = [(fd, r) for fd, r in new if r["role"] == "kill"]
        newest_is_death = bool(settled) and settled[-1][1]["role"] == "death"
        banner = p["banner"] or "?"
        if kills:
            victims = []
            if self.ocr:
                # the latest frames show the settled feed, with this kill's row on top
                text, conf = max((feed.victim_text(fd, r, self.name_t, self.cfg["ocr_upscale"]) for fd, r in kills[-2:]),
                                 key=lambda tc: tc[1], default=("", 0.0))
                victims = [text] if text and conf >= 60 else []
            self.events.append({"t": p["t"], "kills": 1, "victims": victims, "source": "ko", "score": p["score"],
                                "banner": banner})
            log.info("kill at %8.2fs %-7s %s (emblem %.2f, new kill row seen in %d frames)",
                     p["t"], banner, victims, p["score"], len(kills))
        elif newest_is_death:
            log.info("banner at %8.2fs rejected: the newest feed row is a death (kill-cam replay)", p["t"])
        else:
            log.warning("banner at %8.2fs dropped: no feed row with the name around it", p["t"])

    def inspect(self, crops):
        cfg = self.cfg
        s, _, _ = feed.match_max(crops["ko"], self.ko_t)
        lines = [f"banner emblem {s:.3f} (threshold {cfg['ko_threshold']}) word {self.read_label(crops['ko'])}"
                 f"{'  <- KILL' if s >= cfg['ko_threshold'] else ''}"]
        fd = crops["feed"]
        rows = feed.feed_rows(fd, self.name_t, cfg["name_threshold"], cfg["attacker_min_right"])
        bs, _, _ = feed.match_max(fd, self.name_t)
        lines.append(f"feed rows with {cfg['player_name']!r}: {len(rows)} "
                     f"(best name match anywhere {bs:.3f}, threshold {cfg['name_threshold']}); newest row first")
        vis = cv2.cvtColor(fd, cv2.COLOR_GRAY2BGR)
        h, w = self.name_t[0].shape
        for r in rows:
            txt, conf = feed.victim_text(fd, r, self.name_t, cfg["ocr_upscale"]) if r["role"] == "kill" else ("", 0.0)
            lines.append(f"  {r['role']:5s} score {r['score']:.3f}  right {fd.shape[1] - (r['x'] + w):3d}px"
                         f"  y {r['y']:3d}  victim {txt!r} (conf {conf:.0f})")
            cv2.rectangle(vis, (r["x"], r["y"]), (r["x"] + w, r["y"] + h),
                          (0, 0, 255) if r["role"] == "kill" else (255, 0, 0), 1)
        return lines, vis
