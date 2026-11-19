"""Transcribe a clip locally and write an SRT beside it (mlx-whisper, Apple Silicon).

Usage: .venv-vlm/bin/python tools/subtitles.py clip.mp4 [--model mlx-community/whisper-large-v3-turbo]
"""
import argparse, os, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
ap.add_argument("--out"); a = ap.parse_args()

import mlx_whisper

wav = os.path.splitext(a.video)[0] + ".wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
r = mlx_whisper.transcribe(wav, path_or_hf_repo=a.model, word_timestamps=False)
os.remove(wav)

def ts(s):
    h, rem = divmod(s, 3600); m, rem = divmod(rem, 60); sec, ms = divmod(rem, 1)
    return f"{int(h):02d}:{int(m):02d}:{int(sec):02d},{int(ms*1000):03d}"

out = a.out or os.path.splitext(a.video)[0] + ".srt"
with open(out, "w") as f:
    for i, seg in enumerate(r["segments"], 1):
        f.write(f"{i}\n{ts(seg['start'])} --> {ts(seg['end'])}\n{seg['text'].strip()}\n\n")
print(f"{out}: {len(r['segments'])} lines, language {r.get('language')}")
for seg in r["segments"][:12]:
    print(f"  {seg['start']:6.1f}s  {seg['text'].strip()}")


def burn(video, srt, out, height=None, font_frac=0.040, margin_frac=0.085):
    """Burn an SRT into a video without libass: each line is rendered to a transparent PNG and
    overlaid for its own time range. This ffmpeg build has no subtitles/ass/drawtext filter."""
    import re, subprocess, tempfile
    from PIL import Image, ImageDraw, ImageFont
    from killclip import media
    info = media.probe(video); W, H = info["width"], info["height"]

    def secs(ts):
        h, m, rest = ts.split(":"); s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    blocks = [b for b in re.split(r"\n\s*\n", open(srt).read().strip()) if b.strip()]
    cues = []
    for b in blocks:
        lines = b.strip().splitlines()
        a_, b_ = lines[1].split(" --> ")
        cues.append((secs(a_), secs(b_), " ".join(l.strip() for l in lines[2:])))

    size = max(16, int(H * font_frac))
    for path in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"):
        try:
            font = ImageFont.truetype(path, size); break
        except Exception:
            font = None
    font = font or ImageFont.load_default()
    tmp = tempfile.mkdtemp()
    pngs = []
    for i, (s, e, text) in enumerate(cues):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        x0, y0, x1, y1 = d.textbbox((0, 0), text, font=font)
        x = (W - (x1 - x0)) // 2; y = H - int(H * margin_frac) - (y1 - y0)
        d.text((x, y), text, font=font, fill=(255, 255, 255, 255),
               stroke_width=max(2, size // 12), stroke_fill=(0, 0, 0, 230))
        p = f"{tmp}/cue{i:03d}.png"; img.save(p); pngs.append((p, s, e))

    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(video)]
    for p, _, _ in pngs:
        cmd += ["-i", p]
    chain, prev = [], "[0:v]"
    for i, (_, s, e) in enumerate(pngs, 1):
        tag = f"[v{i}]"
        chain.append(f"{prev}[{i}:v]overlay=0:0:enable='between(t,{s:.3f},{e:.3f})'{tag}")
        prev = tag
    cmd += ["-filter_complex", ";".join(chain), "-map", prev, "-map", "0:a?",
            "-c:v", "h264_videotoolbox", "-b:v", "40M" if H >= 2000 else "16M", "-pix_fmt", "yuv420p",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-c:a", "copy", "-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:500])
    return out


if __name__ == "__main__" and "--burn" in sys.argv:
    v = sys.argv[1]; s = os.path.splitext(v)[0] + ".srt"
    o = os.path.splitext(v)[0] + "_subbed.mp4"
    print("burned ->", burn(v, s, o))
