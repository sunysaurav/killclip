"""Cut clips, reframe to 9:16, write an EDL or an FCPXML timeline, and join clips with crossfades."""
import logging
import math
import os
import subprocess
import time
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

from . import encode, grade as grading
from .media import probe

log = logging.getLogger("killclip.cut")

bitrate_for = encode.bitrate_for      # kept here: tools/ and older callers import it from cut


def _encode_args(height):
    """Video, audio and container flags for one output."""
    return [*encode.video_args(height), *encode.audio_args(), *encode.container_args()]


def cut_clip(video, start, end, out, info, vertical=False, grade="none"):
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-i", str(video), "-t", f"{end - start:.3f}"]
    vf = grading.filters(info, grade)                                # tone map HDR to SDR, then the grade
    if vertical:  # centre crop to 9:16, then 1080x1920
        vf += "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920,"
    cmd += ["-vf", vf + grading.stamp(info, grade)]                 # the frames carry the colour tags the encoder writes
    cmd += [*_encode_args(info["height"]), *grading.tags(info, grade), str(out)]
    run(cmd, f"clip {start:.2f}-{end:.2f}s -> {out}")


def run(cmd, what):
    log.debug("ffmpeg: %s", " ".join(cmd))
    t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log.error("%s failed: %s", what, r.stderr.strip())
        raise subprocess.CalledProcessError(r.returncode, cmd, r.stdout, r.stderr)
    log.info("%s (%.1fs)", what, time.perf_counter() - t0)


def timecode(sec, fps):
    fps_i = int(round(fps))
    frames = int(round(sec * fps_i))
    s, ff = divmod(frames, fps_i)
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{ff:02d}"


def write_edl(path, ms, fps, clip_name):
    """CMX3600 EDL: one event per moment, source timecodes from the original file."""
    lines = ["TITLE: killclip", "FCM: NON-DROP FRAME", ""]
    rec = 0.0
    for m in ms:
        dur = m["clip_end"] - m["clip_start"]
        lines.append(f"{m['id']:03d}  AX       V     C        "
                     f"{timecode(m['clip_start'], fps)} {timecode(m['clip_end'], fps)} "
                     f"{timecode(rec, fps)} {timecode(rec + dur, fps)}")
        lines.append(f"* FROM CLIP NAME: {clip_name}")
        lines.append("")
        rec += dur
    with open(path, "w") as f:
        f.write("\n".join(lines))
    log.info("EDL with %d events -> %s", len(ms), path)


def _rational(v):
    """A Fraction of a second as FCPXML writes time: '1001/60000s', '7s'."""
    return f"{v.numerator}s" if v.denominator == 1 else f"{v.numerator}/{v.denominator}s"


# Editors work in these rates. The console's recordings report odd ones (a 59.94 fps WebM reads as
# 19001/317 because its timestamps are whole milliseconds), so a timeline snaps to the nearest of these.
STANDARD_RATES = [Fraction(24000, 1001), Fraction(24), Fraction(25), Fraction(30000, 1001), Fraction(30),
                  Fraction(48), Fraction(50), Fraction(60000, 1001), Fraction(60), Fraction(120)]


def _standard_rate(fps):
    best = min(STANDARD_RATES, key=lambda r: abs(float(r) - fps))
    return best if abs(float(best) - fps) / fps < 0.005 else Fraction(fps).limit_denominator(1001)


def _marker_name(e):
    """The banner (Marvel Rivals) or the sound (GTA). Victim names are OCR of player names, too noisy."""
    return e.get("banner") or e.get("label") or "kill"


def write_fcpxml(path, items, name="killclip"):
    """An FCPXML 1.8 timeline of cut clips laid end to end, with a marker on every kill.

    DaVinci Resolve (free included) imports it with File > Import > Timeline; Final Cut opens it too.
    It points at the cut MP4s rather than the recording, because Resolve cannot read the console's
    WebM. items: [(clip path, moment)], the moment's event times in the recording and its clip_start
    where the clip began in it. Every time is snapped to a frame of its clip.
    """
    root = ET.Element("fcpxml", version="1.8")         # 1.8: the version most importers read
    res = ET.SubElement(root, "resources")
    formats, clips = {}, []
    for n, (clip, m) in enumerate(items, 1):
        info = probe(clip)
        fps = _standard_rate(info["fps"])
        key = (info["width"], info["height"], fps)
        if key not in formats:
            formats[key] = f"f{len(formats) + 1}"
            ET.SubElement(res, "format", id=formats[key], frameDuration=_rational(1 / fps),
                          width=str(info["width"]), height=str(info["height"]))
        frames = math.floor(info["duration"] * fps)                  # never past the file's last frame
        window = m["clip_end"] - m["clip_start"]
        if abs(info["duration"] - window) > 0.5:
            log.warning("%s is %.1fs but its moment's window is %.1fs: cut with other --pre/--post? its markers "
                        "may be off", os.path.basename(clip), info["duration"], window)
        asset = ET.SubElement(res, "asset", id=f"a{n}", name=Path(clip).stem, start="0s",
                              duration=_rational(frames / fps), hasVideo="1", format=formats[key],
                              src=Path(os.path.abspath(clip)).as_uri())
        if info["has_audio"]:
            asset.attrib.update(hasAudio="1", audioSources="1", audioChannels="2", audioRate="48000")
        clips.append((f"a{n}", Path(clip).stem, formats[key], fps, frames, m))

    seq_fps = clips[0][3]
    event = ET.SubElement(ET.SubElement(root, "library"), "event", name=name)
    seq = ET.SubElement(ET.SubElement(event, "project", name=name), "sequence", format=clips[0][2],
                        tcStart="0s", tcFormat="NDF", audioLayout="stereo", audioRate="48k")
    spine = ET.SubElement(seq, "spine")
    at, markers = Fraction(0), 0
    for aid, stem, fid, fps, frames, m in clips:
        dur = Fraction(frames) / fps
        ac = ET.SubElement(spine, "asset-clip", ref=aid, name=stem, offset=_rational(at), start="0s",
                           duration=_rational(dur), format=fid, tcFormat="NDF")
        for e in sorted(m.get("events", []), key=lambda e: e["t"]):
            f = round((Fraction(e["t"]) - Fraction(m["clip_start"])) * fps)
            if 0 <= f < frames:
                ET.SubElement(ac, "marker", start=_rational(f / fps), duration=_rational(1 / fps),
                              value=_marker_name(e))
                markers += 1
        at += Fraction(round(dur * seq_fps)) / seq_fps
    seq.set("duration", _rational(at))
    ET.indent(root)
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n')
        f.write(ET.tostring(root, encoding="unicode") + "\n")
    log.info("FCPXML timeline: %d clips, %d kill markers -> %s", len(clips), markers, path)
    return path


def montage(clips, out, fade=0.5):
    """Concatenate clips with video and audio crossfades."""
    infos = [probe(c) for c in clips]
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for c in clips:
        cmd += ["-i", str(c)]
    parts, off, v_prev, a_prev = [], 0.0, "[0:v]", "[0:a]"
    for i in range(1, len(clips)):
        off += infos[i - 1]["duration"] - fade
        parts.append(f"{v_prev}[{i}:v]xfade=transition=fade:duration={fade}:offset={off:.3f}[v{i}]")
        parts.append(f"{a_prev}[{i}:a]acrossfade=d={fade}[a{i}]")
        v_prev, a_prev = f"[v{i}]", f"[a{i}]"
    if parts:
        cmd += ["-filter_complex", ";".join(parts), "-map", v_prev, "-map", a_prev]
    cmd += [*_encode_args(infos[0]["height"]), *grading.tags(infos[0]), str(out)]   # clips are already graded
    run(cmd, f"montage of {len(clips)} clips -> {out}")
