"""Generic pipeline: one decode pass feeding the game's detector, then moments and output files."""
import csv
import json
import logging
import os
import time

from . import audio, games, media

log = logging.getLogger("killclip.detect")
from .paths import HOME as ROOT

DEFAULTS = {
    "player_name": "PLAYER",
    "detector": None,            # killclip/games/<detector>.py; defaults to the game name
    "scan_fps": 5,
    "calib_height": None,        # height of the recording the templates were cut from; other sizes are scaled to it
    "ocr_upscale": 3,
    "audio_ref": None,           # optional reference sting; logged only
    "audio_band": [300, 6000],
    "audio_threshold": 0.5,
    "audio_min_gap": 0.4,
    "merge_gap": 4.0,            # kills closer than this become one clip
    "clip_pre": 8.0,
    "clip_post": 5.0,
}


def config_path(game):
    return os.path.join(ROOT, "configs", f"{game}.json")


def load_config(path, game="marvel-rivals"):
    """Generic DEFAULTS + the game module's DEFAULTS, updated by the JSON file, then by KILLCLIP_PLAYER.
    Relative template and audio paths are under the repo root."""
    user = {}
    if path and os.path.exists(path):
        with open(path) as f:
            user = json.load(f)
    detector = user.get("detector") or game.replace("-", "_")
    mod = games.load(detector)
    cfg = {**DEFAULTS, **mod.DEFAULTS, **user, "detector": detector}
    if os.environ.get("KILLCLIP_PLAYER"):
        cfg["player_name"] = os.environ["KILLCLIP_PLAYER"]
    def resolve(v):
        return [p if os.path.isabs(p) else os.path.join(ROOT, p) for p in ([v] if isinstance(v, str) else v)]
    for key in mod.TEMPLATE_KEYS:
        if isinstance(cfg[key], dict):
            cfg[key] = {name: resolve(v) for name, v in cfg[key].items()}
        elif cfg[key]:
            cfg[key] = resolve(cfg[key])
    if cfg["audio_ref"] and not os.path.isabs(cfg["audio_ref"]):
        cfg["audio_ref"] = os.path.join(ROOT, cfg["audio_ref"])
    log.debug("config %s: %s", path, cfg)
    return cfg


def union(regs):
    return [min(r[0] for r in regs), min(r[1] for r in regs), max(r[2] for r in regs), max(r[3] for r in regs)]


def crop_regions(crop, regs, origin, W, H):
    """Slice each named region out of the union crop."""
    ux0, uy0 = origin
    out = {}
    for name, r in regs.items():
        x0, y0, x1, y1 = media.region_px(r, W, H)
        out[name] = crop[y0 - uy0:y1 - uy0, x0 - ux0:x1 - ux0]
    return out


def scan(video, cfg, info, ocr=True):
    """Return kill events [{t, kills, victims, source, score}] from one decode of the video."""
    mod = games.load(cfg["detector"])
    det = mod.Detector(cfg, ocr)
    regs = mod.regions(cfg)
    W, H, _ = media.scaled(info["width"], info["height"], cfg["calib_height"])
    region = union(list(regs.values()))
    origin = media.region_px(region, W, H)[:2]
    t0 = time.perf_counter()
    for n, (t, crop) in enumerate(media.iter_crops(video, region, cfg["scan_fps"], info["width"], info["height"],
                                                   calib_height=cfg["calib_height"])):
        if n and n % (cfg["scan_fps"] * 120) == 0:
            log.info("  scanned %6.0fs / %.0fs (%.0fs elapsed, %d kills so far)",
                     t, info["duration"], time.perf_counter() - t0, len(det.events))
        det.frame(t, crop_regions(crop, regs, origin, W, H))
    det.flush()
    log.info("scan: %d events, %d kills in %.0fs", len(det.events), sum(e["kills"] for e in det.events),
             time.perf_counter() - t0)
    return det.events


def inspect(video, cfg, info, t):
    """The game detector's report for one moment: (lines, annotated image or None)."""
    mod = games.load(cfg["detector"])
    crops = {name: media.grab_crop(video, t, r, info["width"], info["height"], cfg["calib_height"])
             for name, r in mod.regions(cfg).items()}
    return mod.Detector(cfg).inspect(crops)


def audio_check(video, cfg, events):
    """Optional diagnostic: how the reference sting scores at each event and elsewhere."""
    if not cfg["audio_ref"] or not os.path.exists(cfg["audio_ref"]):
        return
    y = media.read_audio(video)
    sc = audio.scores(y, audio.load_wav(cfg["audio_ref"]), *cfg["audio_band"])
    for e in events:
        lo, hi = int((e["t"] - 1) * media.SR / audio.HOP), int((e["t"] + 1) * media.SR / audio.HOP)
        log.info("audio near %.2fs: best sting score %.2f", e["t"], sc[max(0, lo):hi].max() if hi > lo else 0)
    pk = audio.peaks(sc, cfg["audio_threshold"], cfg["audio_min_gap"])
    log.info("audio: %d sting matches >= %.2f overall", len(pk), cfg["audio_threshold"])


def moments(events, cfg, duration):
    out = []
    for e in sorted(events, key=lambda e: e["t"]):
        if out and e["t"] - out[-1]["end"] <= cfg["merge_gap"]:
            out[-1]["end"] = e["t"]
            out[-1]["events"].append(e)
        else:
            out.append({"start": e["t"], "end": e["t"], "events": [e]})
    for i, m in enumerate(out, 1):
        m["id"] = i
        m["kills"] = sum(e["kills"] for e in m["events"])
        m["victims"] = [v for e in m["events"] for v in e["victims"] if v]
        m["sources"] = sorted({e["source"] for e in m["events"]})
        m["clip_start"] = max(0.0, m["start"] - cfg["clip_pre"])
        m["clip_end"] = min(duration, m["end"] + cfg["clip_post"])
        log.info("moment #%02d %8.2fs kills=%d %s clip %.2f-%.2f", i, m["start"], m["kills"],
                 m["victims"], m["clip_start"], m["clip_end"])
    return out


def write(path, video, cfg, ms):
    with open(path, "w") as f:
        json.dump({"video": str(video), "config": cfg, "moments": ms}, f, indent=2)
    with open(os.path.splitext(path)[0] + ".csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "start", "end", "kills", "victims", "sources", "clip_start", "clip_end"])
        for m in ms:
            w.writerow([m["id"], f"{m['start']:.2f}", f"{m['end']:.2f}", m["kills"], "; ".join(m["victims"]),
                        "; ".join(m["sources"]), f"{m['clip_start']:.2f}", f"{m['clip_end']:.2f}"])


def read(path):
    with open(path) as f:
        return json.load(f)
