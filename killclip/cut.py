"""Cut clips, reframe to 9:16, write an EDL, and join clips with crossfades."""
import logging
import subprocess
import time

from . import grade as grading
from .media import probe

log = logging.getLogger("killclip.cut")

ENCODE = ["-c:v", "h264_videotoolbox", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]


def bitrate_for(height):
    return "40M" if height >= 2000 else "16M"


def cut_clip(video, start, end, out, info, vertical=False, grade="none"):
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-i", str(video), "-t", f"{end - start:.3f}"]
    vf = grading.filters(info, grade)                                # tone map HDR to SDR, then the grade
    if vertical:  # centre crop to 9:16, then 1080x1920
        vf += "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920,"
    cmd += ["-vf", vf + grading.stamp(info, grade)]                 # the frames carry the colour tags the encoder writes
    cmd += ["-b:v", bitrate_for(info["height"]), *ENCODE, *grading.tags(info, grade), str(out)]
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
    cmd += ["-b:v", bitrate_for(infos[0]["height"]), *ENCODE, *grading.tags(infos[0]), str(out)]   # clips are already graded
    run(cmd, f"montage of {len(clips)} clips -> {out}")
