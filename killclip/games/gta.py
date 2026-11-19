"""Grand Theft Auto: finding moments without a kill feed.

Marvel Rivals and Battlefield print the event on screen, so those modules read it. GTA never does:
its HUD carries *state* (a wanted level, a mission banner, a health bar), not events. So this module
listens instead. A sound tagger scores every second of the recording for gunfire, explosions,
crashes, sirens and screams, each judged against its own usual level in that recording, and the
peaks become the moments. Audio alone, so an hour is read in well under a minute with no video
decoding at all.

It therefore has no Detector and no per-frame scan: it exposes `candidates()`, which detect.scan()
uses in place of the frame loop. The events it returns carry a `label` ("gunfire + sirens") and an
`end`, and go through the same moments, cut, EDL and montage path as any other game.

`sound_weights` says how much each sound means here: an explosion or gunfire is almost always worth
a clip, an engine revving on its own rarely is.
"""
import logging

from .. import sound

log = logging.getLogger("killclip.games.gta")

DEFAULTS = {
    "sound_threshold": 0.3,      # how strong a sound must be, relative to this recording, to count
    "sound_merge": 10.0,         # sounds this close are one moment
    "sound_extend_gap": 45.0,    # how long sirens may keep an incident open after the shooting stops
    "sound_limit": None,         # keep only the N strongest moments (None: all above threshold)
    "sound_weights": {"gunfire": 1.0, "explosion": 1.0, "crash": 0.9,
                      "siren": 0.8, "engine": 0.4, "scream": 0.8},
    "caption_region": [0.18, 0.845, 0.82, 0.935],   # the strip GTA prints dialogue in
    "caption_step": 0.5,
    "clip_pre": 6.0,
    "clip_post": 4.0,
    "merge_gap": 8.0,
}
TEMPLATE_KEYS = ()


def regions(cfg):
    """No frame scanning: everything comes from the audio."""
    return {}


def candidates(video, cfg, info):
    """Moments as events, strongest first in `score`, in time order."""
    heard = sound.listen(video)
    if not heard:
        log.warning("no audio in %s: nothing to detect", video)
        return []
    found = sound.moments(heard, weights=cfg["sound_weights"], threshold=cfg["sound_threshold"],
                          merge=cfg["sound_merge"], limit=cfg["sound_limit"],
                          extend_gap=cfg["sound_extend_gap"])
    events = []
    for m in sorted(found, key=lambda m: m["t"]):
        events.append({"t": round(m["t"], 2), "end": round(m["end"], 2), "kills": 1, "victims": [],
                       "source": "sound", "score": round(m["score"], 3), "label": m["label"]})
        log.info("moment %8.2fs-%.2fs  %.2f  %s", m["t"], m["end"], m["score"], m["label"])
    log.info("sound: %d moments", len(events))
    return events
