"""Beat-synced montage: every kill lands on a beat, with a slow lead-in and a fast follow-through.

Beat tracking is a small constant-tempo tracker: spectral-flux onsets, autocorrelation tempo, then
the exact tempo and phase whose rigid beat grid sits on the strongest onsets. That suits the electronic and hip-hop tracks montages usually use. A lone kill gets a slot of
`beats_per_kill` beats: the kill sits at `kill_at` of the way through, the part before plays at the
slow factor and the part after at the fast factor. Kills closer together than `streak_gap` (a
double, triple, ... kill) share one slot: the footage runs on through the streak, re-timed so each
kill lands on its own beat. Slots are cut with no crossfade; the music is laid under.

STYLES are the presets: how fast the footage runs into and out of each kill, whether the kill
frame is held (a freeze), and which on-beat effect hits on the kill frame (a zoom punch or a
white flash).
"""
import logging
import os
import subprocess
import tempfile

import numpy as np
from scipy.signal import correlate, stft

from . import grade as grading, media
from .cut import bitrate_for, ENCODE

log = logging.getLogger("killclip.beatsync")
SR = 22050
HOP = 256
FPS = 60

# lead/fast: speed into the kill and through a streak (cycling per slot); tail: speed after the
# last kill (None = fast); hold: beats to freeze the kill frame; effect: on the kill frame;
# kill_at: where in the slot the kill lands (0.5 = the cut before it is on a beat too)
STYLES = {
    "slowmo": {"pattern": [(0.5, 1.5)], "tail": None, "hold": 0, "effect": None, "kill_at": 0.6},
    "clean": {"pattern": [(1.0, 1.0)], "tail": None, "hold": 0, "effect": None, "kill_at": 0.5},
    "punch": {"pattern": [(1.0, 1.0)], "tail": None, "hold": 0, "effect": "punch", "kill_at": 0.5},
    "freeze": {"pattern": [(2.0, 2.0)], "tail": 1.0, "hold": 1, "effect": "flash", "kill_at": 0.6},
}
EFFECTS = (None, "punch", "flash")


def beats(music, bpm_range=(60, 200), bpm=None):
    """Beat times (s) and tempo (BPM) of a music file: a rigid grid at a constant tempo. Pass bpm to
    force the tempo (only the phase is then estimated), e.g. when the tracker picks a half or double
    tempo."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", music, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    y = np.frombuffer(raw, np.float32)
    f, _, Z = stft(y, fs=SR, nperseg=1024, noverlap=1024 - HOP, boundary=None, padded=False)
    S = np.log1p(1000 * np.abs(Z))
    d = np.maximum(np.diff(S, axis=1), 0)                          # spectral flux = onset strength
    z = lambda v: (v - v.mean()) / (v.std() + 1e-9)
    flux = z(d[f < 400].sum(axis=0)) + 0.5 * z(d.sum(axis=0))      # kicks and bass lead; hi-hats only support
    fps = SR / HOP
    pos = np.clip(flux, 0, None)

    def grid_score(bpm, phases=16):
        """Mean onset strength on a rigid grid at this tempo (best phase), relative to the average."""
        period = fps * 60 / bpm
        best = (0.0, 0.0)
        for ph in np.linspace(0, period, phases, endpoint=False):
            idx = np.round(np.arange(ph, len(pos) - 1, period)).astype(int)
            best = max(best, (pos[idx].mean() / (pos.mean() + 1e-9), ph))
        return best

    if bpm is None:
        # coarse tempo from the autocorrelation of the onset curve, then the exact tempo (within 3%)
        # whose rigid grid sits on the strongest onsets
        ac = correlate(flux, flux, mode="full", method="fft")[len(flux) - 1:]
        lo, hi = int(fps * 60 / bpm_range[1]), int(fps * 60 / bpm_range[0])
        coarse = fps * 60 / (lo + int(np.argmax(ac[lo:hi + 1])))
        bpm = max(np.arange(coarse * 0.97, coarse * 1.03, 0.05), key=lambda b: grid_score(b)[0])
    tempo = float(bpm)
    period = fps * 60 / tempo
    _, phase = grid_score(tempo, phases=64)
    times = np.arange(phase, len(pos), period) * HOP / SR              # rigid grid: no per-beat snapping
    log.info("beats: tempo %.2f BPM, %d beats over %.1fs", tempo, len(times), len(y) / SR)
    return times, tempo


def pool(paths):
    """Kills from several events files (one per recording), each tagged with its video. Two recordings
    that overlap (the console saved two clips of the same play) show up as a constant offset between
    their kill times; the duplicates in the later file are dropped."""
    from . import detect
    recs = []
    for p in paths:
        ev = detect.read(p)
        recs.append([dict(e, video=ev["video"]) for m in ev["moments"] for e in m["events"]])
    for a in range(len(recs)):
        for b in range(a + 1, len(recs)):
            ta, tb = (np.array([e["t"] for e in r]) for r in (recs[a], recs[b]))
            if len(ta) < 3 or len(tb) < 3:
                continue
            vals, counts = np.unique(np.round((ta[:, None] - tb[None, :]) * 2) / 2, return_counts=True)
            if counts.max() < 6:                                     # fewer coincide by chance across an hour of play
                continue
            off = vals[counts.argmax()]
            keep = [e for e in recs[b] if np.abs(ta - (e["t"] + off)).min() > 0.45]
            log.info("%s overlaps %s (offset %.1fs): %d duplicate kills dropped", os.path.basename(paths[b]),
                     os.path.basename(paths[a]), off, len(recs[b]) - len(keep))
            recs[b] = keep
    return [e for r in recs for e in r]


def plan(events, beat_times, beats_per_kill, kill_at, style, start_beat=0, streak_gap=6.0):
    """Assign kills to beat slots. Each slot is a dict: video, src_start (s in the recording), parts
    [(source seconds, output seconds)] played back to back (source 0 = hold the frame at that
    point), kills [(kill_t, beat_t)], and start/end on the music timeline. Kills within streak_gap
    of the previous one join its slot and land on later beats; the footage between two kills of a
    streak takes the number of beats that keeps its speed near the fast factor. When more kills
    than the music can hold are given, streaks are kept first, then lone kills in order."""
    beat = beat_times[1] - beat_times[0]
    lead_out, tail_out = kill_at * beats_per_kill * beat, (1 - kill_at) * beats_per_kill * beat
    hold = min(style["hold"] * beat, tail_out - 0.25 * beat)        # a freeze never eats the whole tail
    hold_beats = round(hold / beat)
    groups = []
    for e in sorted(events, key=lambda e: (e.get("video") or "", e["t"])):
        if groups and groups[-1][-1].get("video") == e.get("video") and e["t"] - groups[-1][-1]["t"] <= streak_gap:
            groups[-1].append(e)
        else:
            groups.append([e])

    def layout(g, slot_index):
        """parts, beat offset of each kill from the first, and the beats the slot uses."""
        lead, fast = style["pattern"][slot_index % len(style["pattern"])]
        tail = fast if style["tail"] is None else style["tail"]
        parts, at = [(lead_out * lead, lead_out)], [0]
        for a, b in zip(g, g[1:]):
            gap = b["t"] - a["t"]
            k = min(beats_per_kill, max(1, round((gap / fast - hold) / beat)))
            if hold:
                parts.append((0.0, hold))
            parts.append((gap, k * beat))
            at.append(at[-1] + k + hold_beats)
        if hold:
            parts.append((0.0, hold))
        parts.append(((tail_out - hold) * tail, tail_out - hold))
        return parts, at, at[-1] + beats_per_kill

    i = start_beat
    while i < len(beat_times) and beat_times[i] < lead_out:
        i += 1                                                       # the first slot must not start before the music does
    budget, used, chosen = len(beat_times) - i - 1, 0, []
    for j in sorted(range(len(groups)), key=lambda j: (-len(groups[j]), j)):   # streaks first, then in order
        cost = layout(groups[j], len(chosen))[2]
        if used + cost <= budget:
            chosen.append(j)
            used += cost
    if len(chosen) < len(groups):
        left = sum(len(groups[j]) for j in range(len(groups)) if j not in chosen)
        log.warning("music holds %d of %d kills: streaks kept first, %d lone kills left out", len(events) - left, len(events), left)
    slots = []
    last = {}                                                        # video -> source end of its last slot
    for j in sorted(chosen):
        g = groups[j]
        parts, at, cost = layout(g, len(slots))
        if i + cost > len(beat_times) - 1:
            log.warning("music ended: %d kills did not get a slot", len(g))
            break
        src_start = g[0]["t"] - parts[0][0]
        video = g[0].get("video")
        if src_start < last.get(video, -1e9):                        # inside the previous slot's footage
            log.info("kill at %.2fs skipped: already covered by the previous slot", g[0]["t"])
            continue
        slots.append({"video": video, "src_start": src_start, "parts": parts,
                      "kills": [(e["t"], beat_times[i + a]) for e, a in zip(g, at)],
                      "start": beat_times[i] - lead_out, "end": beat_times[i + at[-1]] + tail_out})
        last[video] = g[-1]["t"] + parts[-1][0]
        i += cost
    return slots


def effect_filters(effect, hits, width, height):
    """ffmpeg filters that fire on output frames `hits` (0-based, after fps=FPS)."""
    if not effect or not hits:
        return ""
    if effect == "punch":                                            # 8% push-in on the beat, back out over 6 frames
        z = "+".join(f"gte(on,{k})*lt(on,{k + 6})*(1-(on-{k})/6)" for k in hits)
        return (f"zoompan=z='1+0.08*({z})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d=1:s={width}x{height}:fps={FPS},")
    if effect == "flash":                                            # white flash on the beat, gone in 4 frames
        strong = "+".join(f"eq(n,{k})+eq(n,{k + 1})" for k in hits)
        weak = "+".join(f"eq(n,{k + 2})+eq(n,{k + 3})" for k in hits)
        return (f"drawbox=c=white@0.75:t=fill:enable='{strong}',"
                f"drawbox=c=white@0.35:t=fill:enable='{weak}',")
    raise ValueError(f"unknown effect {effect!r}; use one of {EFFECTS}")


def render_slot(video, width, height, src_start, parts, out, frames, effect=None, hits=(), pre="", tags=(), stamp="null"):
    """One slot: the parts [(source seconds, output seconds)] back to back, exactly `frames`
    frames, with the on-beat effect on the output frames `hits`; `pre` is the colour chain applied first."""
    n = len(parts)
    graph = f"[0:v]{pre}split={n}" + "".join(f"[s{j}]" for j in range(n)) + ";"
    t = 0.0
    for j, (src, dur) in enumerate(parts):
        if src > 0:
            graph += f"[s{j}]trim={t:.4f}:{t + src:.4f},setpts=(PTS-STARTPTS)*{dur / src:.5f}[p{j}];"
        else:                                                        # hold the frame at t for dur seconds
            graph += (f"[s{j}]trim={t - 0.5 / FPS:.4f}:{t + 0.5 / FPS:.4f},setpts=PTS-STARTPTS,"
                      f"tpad=stop_mode=clone:stop_duration={dur - 1 / FPS:.4f}[p{j}];")
        t += src
    graph += ("".join(f"[p{j}]" for j in range(n)) +
              f"concat=n={n}:v=1:a=0,fps={FPS}," + effect_filters(effect, hits, width, height) +
              f"{stamp},tpad=stop_mode=clone:stop_duration=0.5,setpts=PTS-STARTPTS[v]")
    # seek half a source frame early: the first decoded frame is the first one at or after the seek point,
    # so this lands it within half a frame of src_start instead of up to a frame late
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, src_start - 1 / 120):.4f}", "-i", str(video), "-t", f"{t + 0.5:.4f}",
           "-filter_complex", graph, "-map", "[v]", "-an", "-frames:v", str(frames), "-b:v", bitrate_for(height), *ENCODE, *tags, str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())


def build(video, events, music, out, beats_per_kill=4, kill_at=None, pattern=None, start_beat=0,
          refine=None, bpm=None, streak_gap=6.0, style="slowmo", effect="preset", grade="none", music_start=None):
    st = dict(STYLES[style])
    if pattern:
        st["pattern"] = list(pattern)
    if effect != "preset":
        st["effect"] = effect
    if kill_at is None:
        kill_at = st["kill_at"]
    events = [dict(e, video=e.get("video") or video) for e in events]
    infos = {v: media.probe(v) for v in dict.fromkeys(e["video"] for e in events)}
    if refine:  # the game module can re-read each kill instant at a finer rate than the scan
        import inspect
        with_event = len(inspect.signature(refine).parameters) >= 4
        events = [dict(e, t=refine(e["video"], e["t"], infos[e["video"]], e) if with_event else refine(e["video"], e["t"], infos[e["video"]]))
                  for e in events]
    times, tempo = beats(music, bpm=bpm)
    if music_start is not None:                                       # seconds into the track -> first usable beat
        start_beat = int(np.searchsorted(times, music_start))
    slots = plan(events, times, beats_per_kill, kill_at, st, start_beat, streak_gap)
    if not slots:
        raise SystemExit("no kills fit the music")
    tmp = tempfile.mkdtemp()
    parts = []
    music_start = slots[0]["start"]                                   # output 0 = first slot start on the music timeline
    done = 0                                                          # frames rendered so far
    log.info("style %s: lead/fast %s, tail %s, hold %s beat(s), effect %s, kill at %.2f of the slot",
             style, st["pattern"], st["tail"], st["hold"], st["effect"], kill_at)
    for n, s in enumerate(slots):
        p = os.path.join(tmp, f"slot{n:03d}.mp4")
        frames = int(round((s["end"] - music_start) * FPS)) - done    # exact count: no drift against the music
        hits = [int(round((b - s["start"]) * FPS)) for _, b in s["kills"]]
        info = infos[s["video"]]
        render_slot(s["video"], info["width"], info["height"], s["src_start"], s["parts"], p, frames, st["effect"], hits,
                    grading.filters(info, grade), grading.tags(info, grade), grading.stamp(info, grade))
        done += frames
        parts.append(p)
        log.info("slot %2d: %d kill%s at %s on beats %s; parts %s  [%s]", n, len(s["kills"]), "s" if len(s["kills"]) > 1 else "",
                 " ".join(f"{k:.2f}s" for k, _ in s["kills"]), " ".join(f"{b:.2f}s" for _, b in s["kills"]),
                 " ".join(f"hold {d:.2f}s" if src == 0 else f"{src:.2f}s@{src / d:.2f}x" for src, d in s["parts"]),
                 os.path.basename(s["video"]))
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    video_only = os.path.join(tmp, "video.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video_only], check=True)
    total = done / FPS
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", video_only, "-ss", f"{music_start:.4f}", "-i", music, "-t", f"{total:.4f}",
           "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    kills = sum(len(s["kills"]) for s in slots)
    log.info("beat montage: %d kills in %d slots on beats at %.0f BPM, %.1fs -> %s", kills, len(slots), tempo, total, out)
    return slots, tempo
