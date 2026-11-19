"""Finding moments by what a recording sounds like, for games with no kill feed.

Marvel Rivals and Battlefield announce a kill on screen, so the detector can read it. An open-world
game does not: GTA's HUD shows *state* (a wanted level, a mission banner), never an event. What it
does have is sound. Gunfire, an explosion, a crash and a siren are AudioSet classes, so a sound
tagger (panns.py) listening to every second says where the action is, over the whole recording,
without decoding a single video frame.

The scoring is relative, which is the part that makes it work. Raw tagger probabilities on game
audio are small: in a 7-minute GTA recording gunfire never exceeded 0.27 and explosions 0.11, so an
absolute threshold finds nothing. Instead each sound is measured against its own usual level in
this recording, so the loudest gunfire in a quiet session still scores near 1. A floor (MIN_REF)
stops a recording with no real action from promoting its loudest footstep.
"""
import logging
import subprocess

import numpy as np

from . import panns

log = logging.getLogger("killclip.sound")

CHUNK_SECONDS = 60      # decoded at a time, so a three-hour recording never sits in memory
BASELINE = 90           # seconds either side that set a sound's usual level here
MIN_PROB = 0.10         # below this the tagger is not really hearing it
MIN_REF = 0.20          # "as loud as it gets here" is never taken lower than this
MERGE_SECONDS = 10      # a crash and the scramble after it are one moment
EXTEND_SECONDS = 45     # how long an aftermath sound may keep an incident open

# Sounds that begin an incident, and sounds that only mean one is still going. Gunfire starts a
# fight; a siren on its own is just traffic, but a siren after gunfire is the chase you caused, and
# that chase is the rest of the clip even though nothing is firing during it.
STARTS = ("gunfire", "explosion", "crash", "scream")
EXTENDS = ("siren", "engine")

# AudioSet classes worth listening for, grouped. Names must match panns.labels() exactly.
GROUPS = {
    "gunfire":   {"label": "gunfire", "classes": ["Gunshot, gunfire", "Machine gun", "Fusillade",
                                                  "Artillery fire", "Cap gun"]},
    "explosion": {"label": "an explosion", "classes": ["Explosion", "Boom", "Eruption"]},
    "crash":     {"label": "a crash", "classes": ["Smash, crash", "Shatter", "Breaking",
                                                  "Skidding", "Tire squeal", "Crushing"]},
    "siren":     {"label": "sirens", "classes": ["Siren", "Police car (siren)", "Emergency vehicle",
                                                 "Ambulance (siren)", "Civil defense siren"]},
    "engine":    {"label": "an engine", "classes": ["Accelerating, revving, vroom", "Race car, auto racing",
                                                    "Motorcycle", "Engine starting"]},
    "scream":    {"label": "a scream", "classes": ["Screaming", "Shout", "Yell", "Battle cry"]},
}


def read_audio(video, chunk_seconds=CHUNK_SECONDS):
    """Mono 32 kHz float32 audio from a video, a chunk at a time."""
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1",
         "-ar", str(panns.SAMPLE_RATE), "-f", "f32le", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    size = chunk_seconds * panns.SAMPLE_RATE * 4
    try:
        while True:
            buf = proc.stdout.read(size)
            if not buf:
                break
            yield np.frombuffer(buf[: len(buf) // 4 * 4], np.float32)
    finally:
        proc.stdout.close()
        proc.wait()


def listen(video, groups=None):
    """{group: probability per second} over the whole recording. Each second is judged on the
    two seconds around it, so a short bang is not missed by landing on a boundary."""
    groups = groups or GROUPS
    names = {n: i for i, n in enumerate(panns.labels())}
    index = {}
    for g, spec in groups.items():
        ix = [names[c] for c in spec.get("classes", []) if c in names]
        missing = [c for c in spec.get("classes", []) if c not in names]
        if missing:
            log.debug("group %s: unknown AudioSet classes %s", g, missing)
        if ix:
            index[g] = ix
    if not index:
        return None

    sr = panns.SAMPLE_RATE
    half, width = sr // 2, 2 * sr
    out = {g: [] for g in index}
    buf = np.zeros(half, np.float32)         # half a second of silence stands in before the start
    start, total, s = -half, 0, 0

    def run(windows):
        if windows:
            probs = panns.tag(np.stack(windows))
            for g, ix in index.items():
                out[g].append(probs[:, ix].max(axis=1))

    for chunk in read_audio(video):
        total += chunk.size
        buf = np.concatenate([buf, chunk])
        windows = []
        while (s + 1) * sr + half <= start + buf.size:
            windows.append(buf[s * sr - half - start: s * sr - half - start + width])
            s += 1
        run(windows)
        keep = s * sr - half - start
        buf, start = buf[keep:], start + keep
    seconds = total // sr
    if seconds < 1:
        return None
    buf = np.concatenate([buf, np.zeros(width, np.float32)])
    windows = []
    while s < seconds:
        windows.append(buf[s * sr - half - start: s * sr - half - start + width])
        s += 1
    run(windows)
    return {g: np.concatenate(v)[:seconds].astype(np.float32) for g, v in out.items() if v}


def _usual_level(x, half=BASELINE):
    """The median of the `half` seconds either side of each second."""
    from numpy.lib.stride_tricks import sliding_window_view
    padded = np.pad(x, half, mode="edge")
    return np.median(sliding_window_view(padded, 2 * half + 1), axis=1).astype(np.float32)


def strengths(heard, groups=None, weights=None):
    """{group: 0..1 per second}, each sound scored against its own usual level in this recording."""
    groups = groups or GROUPS
    out = {}
    for g, p in heard.items():
        p = np.asarray(p, np.float32)
        level = _usual_level(p)
        ref = max(float(np.percentile(p, 99.5)), MIN_REF)
        usual = float(np.median(p))
        s = np.clip((p - level) / max(ref - usual, 0.05), 0.0, 1.0) * (p >= MIN_PROB)
        out[g] = (s * float((weights or {}).get(g, 1.0))).astype(np.float32)
    return out


def moments(heard, groups=None, weights=None, threshold=0.3, merge=MERGE_SECONDS, limit=None,
            starts=STARTS, extends=EXTENDS, extend_gap=EXTEND_SECONDS):
    """Ranked [{t, end, score, label, groups}] from what listen() heard.

    `threshold` is how strong a sound must be, relative to this recording, to count. Only `starts`
    sounds open a moment; `extends` sounds (sirens, engines) keep an open one running, so a
    gunfight and the police chase it causes come out as one clip instead of two with the quiet
    getaway dropped in between."""
    groups = groups or GROUPS
    st = strengths(heard, groups, weights)
    runs = []
    for g, s in st.items():
        i = 0
        while i < s.size:
            if s[i] < threshold:
                i += 1
                continue
            end = i
            while end + 1 < s.size and (s[end + 1] >= threshold or s[end + 2:end + 4].max(initial=0) >= threshold):
                end += 1
            runs.append((i, end, g, float(s[i:end + 1].max())))
            i = end + 1
    merged = []
    for lo, hi, g, peak in sorted(runs):
        gap = lo - merged[-1]["end"] if merged else None
        # an aftermath sound gets a longer reach back, but only onto a moment something started
        reach = merge if g in starts else (extend_gap if merged and merged[-1]["started"] else merge)
        if merged and gap <= reach:
            m = merged[-1]
            m["end"] = max(m["end"], hi)
            m["groups"][g] = max(m["groups"].get(g, 0.0), peak)
            if g in starts:
                m["score"] = max(m["score"], peak)
                m["started"] = True
        elif g in starts:
            merged.append({"t": float(lo), "end": float(hi), "score": peak, "groups": {g: peak},
                           "started": True})
        else:
            # a siren with no incident behind it is traffic; keep it, but it ranks on its own
            merged.append({"t": float(lo), "end": float(hi), "score": peak * 0.6, "groups": {g: peak},
                           "started": False})
    for m in merged:
        m.pop("started", None)
        order = sorted(m["groups"], key=lambda g: -m["groups"][g])
        m["label"] = " + ".join(groups[g].get("label", g) for g in order)
    merged.sort(key=lambda m: -m["score"])
    return merged[:limit] if limit else merged
