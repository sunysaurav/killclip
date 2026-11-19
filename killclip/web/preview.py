"""Things the browser can actually display, made from recordings it cannot.

The recordings are 10-bit VP9 with PQ colour in Matroska. Safari cannot decode that at all and no
browser tone-maps it consistently, so the page never points at a source file. Everything it shows is
generated here, tone-mapped through the same LUT the renders use:

  still      one frame as a JPEG, for the short composer's layout preview
  filmstrip  one decode of a moment's window into a single horizontal sprite of small frames, so the
             trim handles scrub against a CSS background with no <video> element and no seeking
"""
import logging
import os
import subprocess
import threading

from .. import grade, media

log = logging.getLogger("killclip.web.preview")
_gate = threading.Semaphore(2)          # at most two ffmpeg decodes from page loads at once

STRIP_FPS = 2
STRIP_W = 160


def _run(cmd):
    with _gate:
        r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[-300:])


def still(video, t, out, width=720):
    """One tone-mapped frame at `t`, cached by path."""
    if os.path.exists(out):
        return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    info = media.probe(video)
    vf = grade.filters(info, "natural") + f"scale={width}:-2"
    _run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(video), "-frames:v", "1",
          "-vf", vf, "-q:v", "3", out])
    return out


def filmstrip(video, t0, t1, out):
    """Frames of [t0, t1] at STRIP_FPS, side by side in one JPEG. Returns (path, frame count)."""
    t0 = max(0.0, t0)
    n = max(1, int(round((t1 - t0) * STRIP_FPS)))
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        info = media.probe(video)
        vf = grade.filters(info, "natural") + f"fps={STRIP_FPS},scale={STRIP_W}:-2,tile={n}x1"
        _run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-i", str(video), "-t", f"{t1 - t0:.3f}",
              "-vf", vf, "-frames:v", "1", "-q:v", "4", out])
    return out, n
