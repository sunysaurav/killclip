"""What this ffmpeg can do, and how to ask it to encode.

Every output used to go through `h264_videotoolbox`, which is why the tool only ran on a Mac. It was
also the slower choice: on an M5 Pro, 5 seconds of 4K took 4.30 s through VideoToolbox at 40 Mbit/s and
2.32 s through libx264 at CRF 20, because the hardware encoder is one fixed-rate engine while libx264
spreads over every core. So software is the default everywhere now, and the hardware encoder is
available to anyone who asks for it by name.

The same measurement runs the other way for decoding, which is why `media.iter_crops` no longer asks
for hardware decode: see `hwaccel_args`.

Capabilities are probed once per process. ffmpeg honours only the first info option per invocation, so
this costs one spawn per question, about 60 ms in total.
"""
import logging
import os
import subprocess

log = logging.getLogger("killclip.encode")

# Codecs with a hardware decode path worth taking, when one is asked for. VP9 and AV1 are absent on
# purpose: this chip has no VP9 decoder, so the flag only adds a failed attempt and a retry.
HWACCEL_CODECS = {"h264", "hevc"}
PREFERRED = ("libx264", "h264_videotoolbox", "libopenh264")
_caps = None


class FfmpegError(RuntimeError):
    """ffmpeg cannot do something this tool needs, with the remedy in the message."""


def _names(kind):
    """The name column of `ffmpeg -<kind>`, as a set."""
    try:
        out = subprocess.run(["ffmpeg", "-hide_banner", f"-{kind}"], capture_output=True, text=True,
                             check=False).stdout
    except FileNotFoundError:
        raise FfmpegError("ffmpeg is not on the PATH: brew install ffmpeg / apt-get install ffmpeg")
    # Both listings print a legend, then a line of dashes, then one row per entry:
    #   " V....D libx264              libx264 H.264 / AVC ..."
    names, started = set(), False
    for line in out.splitlines():
        if not started:
            started = line.strip().startswith("---")
            continue
        parts = line.split()
        if len(parts) >= 2:
            names.add(parts[1])
    return names


def caps():
    """{'encoders', 'filters', 'hwaccels', 'version'}, probed once."""
    global _caps
    if _caps is None:
        ver = subprocess.run(["ffmpeg", "-hide_banner", "-version"], capture_output=True, text=True,
                             check=False).stdout.splitlines()
        hw = subprocess.run(["ffmpeg", "-hide_banner", "-hwaccels"], capture_output=True, text=True,
                            check=False).stdout.splitlines()[1:]
        _caps = {"encoders": _names("encoders"), "filters": _names("filters"),
                 "hwaccels": {h.strip() for h in hw if h.strip()},
                 "version": (ver[0].split()[2] if ver else "unknown")}
    return _caps


def require_filters(*names):
    """Raise unless this build has every filter named. Better than a silently different picture."""
    missing = [n for n in names if n not in caps()["filters"]]
    if missing:
        raise FfmpegError(
            f"this ffmpeg has no {', '.join(missing)} filter. It is probably built without --enable-gpl; "
            "install a full build (brew install ffmpeg, or a static gpl build) and try again.")


def encoder():
    """The video encoder to use: $KILLCLIP_ENCODER, else the best available."""
    want = os.environ.get("KILLCLIP_ENCODER")
    have = caps()["encoders"]
    if want:
        if want not in have:
            raise FfmpegError(f"KILLCLIP_ENCODER={want} is not in this ffmpeg. Available: "
                              + ", ".join(sorted(n for n in PREFERRED if n in have)))
        return want
    for name in PREFERRED:
        if name in have:
            return name
    raise FfmpegError("this ffmpeg has no H.264 encoder (looked for " + ", ".join(PREFERRED) + ")")


def bitrate_for(height):
    """The bitrate the tool has always used, kept exactly so hardware output is unchanged."""
    return "40M" if height >= 2000 else "16M"


def crf_for(height):
    """A quality target matching those bitrates. Lower at 1080p because 16M there is the richer of
    the two in bits per pixel, so the ladder stays monotonic."""
    return 20 if height >= 2000 else 19


def video_args(height, bitrate=None, crf=None):
    """Encoder plus rate control. Rate-controlled encoders keep the old bitrate; quality-controlled
    ones get a CRF with the old bitrate as a ceiling, so a file can never come out larger than before."""
    name = encoder()
    rate = bitrate or bitrate_for(height)
    if name.endswith("_videotoolbox") or name == "libopenh264":
        return ["-c:v", name, "-b:v", rate, "-pix_fmt", "yuv420p"]
    q = str(crf if crf is not None else crf_for(height))
    return ["-c:v", name, "-preset", "veryfast", "-crf", q,
            "-maxrate", rate, "-bufsize", f"{int(rate[:-1]) * 2}M", "-pix_fmt", "yuv420p"]


def audio_args():
    return ["-c:a", "aac", "-b:a", "192k"]


def container_args():
    return ["-movflags", "+faststart"]


def blur_filter(radius, power=2):
    """boxblur where available, else an equivalent gaussian. Two box passes of radius r approximate a
    gaussian of sigma 0.83r, so the look is kept on builds without the GPL filters."""
    if "boxblur" in caps()["filters"]:
        return f"boxblur={radius}:{power}"
    return f"gblur=sigma={0.83 * radius:.1f}"


def hwaccel_args(codec=None):
    """Decoder flags. Empty by default, and that is the fast path, not a fallback.

    Measured on an M5 Pro over 30 s at the detector's own 5 fps: 4K VP9 took 9.93 s with
    `-hwaccel videotoolbox` and 3.68 s without; 1080p H.264 took 6.01 s with and 0.96 s without. The
    chip has no VP9 decoder at all, and for H.264 moving frames out of the media engine into system
    memory costs more than decoding them across 15 cores. $KILLCLIP_HWACCEL asks for one anyway.
    """
    want = os.environ.get("KILLCLIP_HWACCEL", "none")
    if want in ("", "none", "0"):
        return []
    if want == "auto":
        want = "videotoolbox" if "videotoolbox" in caps()["hwaccels"] else "none"
    if want == "none" or want not in caps()["hwaccels"]:
        return []
    if codec and codec not in HWACCEL_CODECS:
        return []
    return ["-hwaccel", want]
