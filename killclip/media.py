"""ffmpeg / ffprobe helpers."""
import json
import logging
import subprocess
import time

import numpy as np

log = logging.getLogger("killclip.media")
SR = 16000  # sample rate used for all audio analysis


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    num, den = v["r_frame_rate"].split("/")
    res = {
        "width": int(v["width"]),
        "height": int(v["height"]),
        "fps": float(num) / float(den),
        "duration": float(info["format"]["duration"]),
        "has_audio": any(s["codec_type"] == "audio" for s in info["streams"]),
        "hdr": v.get("color_transfer") in ("smpte2084", "arib-std-b67"),   # PQ or HLG recording
        "color": {k: v.get(k) for k in ("color_primaries", "color_transfer", "color_space", "color_range")},
    }
    log.debug("probe %s: %s", path, res)
    return res


def read_audio(path):
    """Whole audio track as float32 mono at SR."""
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    t0 = time.perf_counter()
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    y = np.frombuffer(raw, dtype=np.float32)
    log.debug("read_audio: %.1fs of audio at %d Hz in %.1fs", len(y) / SR, SR, time.perf_counter() - t0)
    return y


def region_px(region, width, height):
    """(x0, y0, x1, y1) fractions of the frame -> integer pixels."""
    x0, y0, x1, y1 = region
    even = lambda v: int(v) // 2 * 2  # 4:2:0 video needs even crop offsets and sizes
    return even(x0 * width), even(y0 * height), even(x1 * width), even(y1 * height)


def scaled(width, height, calib_height=None):
    """The frame size the templates were cut at: (width, height, ffmpeg scale step or ''). A 4K
    recording is scanned at the calibration height so the 1080p templates still fit."""
    if not calib_height or calib_height == height:
        return width, height, ""
    w = int(round(width * calib_height / height / 2)) * 2
    return w, calib_height, f"scale={w}:{calib_height},"


def iter_crops(path, region, fps, width, height, hwaccel=True, start=None, dur=None, calib_height=None):
    """Yield (t, gray uint8 array) of the region, sampled at `fps` frames per second.
    t is relative to `start` when a window is given."""
    width, height, sc = scaled(width, height, calib_height)
    x0, y0, x1, y1 = region_px(region, width, height)
    w, h = x1 - x0, y1 - y0
    cmd = ["ffmpeg", "-v", "error"]
    if hwaccel:
        cmd += ["-hwaccel", "videotoolbox"]
    if start is not None:
        cmd += ["-ss", f"{start:.4f}"]
    cmd += ["-i", str(path)]
    if dur is not None:
        cmd += ["-t", f"{dur:.4f}"]
    cmd += ["-vf", f"fps={fps},{sc}crop={w}:{h}:{x0}:{y0}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    log.debug("iter_crops: region %dx%d at (%d,%d), %s fps, hwaccel=%s", w, h, x0, y0, fps, hwaccel)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    n = 0
    while True:
        buf = proc.stdout.read(w * h)
        if len(buf) < w * h:
            break
        yield n / fps, np.frombuffer(buf, np.uint8).reshape(h, w)
        n += 1
    err = proc.stderr.read().decode()
    proc.wait()
    if n == 0 and hwaccel:  # decoder refused hardware decoding: retry in software
        log.info("hardware decoding produced no frames, retrying in software (%s)", err.strip())
        yield from iter_crops(path, region, fps, width, height, hwaccel=False, start=start, dur=dur)   # already scaled dims
    elif n == 0:
        log.error("ffmpeg produced no frames: %s", err.strip())
        raise RuntimeError(f"ffmpeg produced no frames: {err}")
    else:
        log.debug("iter_crops: %d frames", n)


def grab_crop(path, t, region, width, height, calib_height=None):
    """One gray crop of the region at time t."""
    width, height, sc = scaled(width, height, calib_height)
    x0, y0, x1, y1 = region_px(region, width, height)
    w, h = x1 - x0, y1 - y0
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
           "-vf", f"{sc}crop={w}:{h}:{x0}:{y0}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w)


def save_frame(path, t, out_png, boxes=(), scale=""):
    """Write the frame at t as PNG (after the optional scale step); boxes = [(x0, y0, x1, y1, color)]
    in pixels of that frame are drawn on it."""
    vf = [f for f in [scale.rstrip(","), ",".join(f"drawbox=x={x0}:y={y0}:w={x1 - x0}:h={y1 - y0}:color={c}:t=3"
                                                    for x0, y0, x1, y1, c in boxes)] if f]
    vf = ["-vf", ",".join(vf)] if vf else []
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(path),
                    "-frames:v", "1", *vf, str(out_png)], check=True)
