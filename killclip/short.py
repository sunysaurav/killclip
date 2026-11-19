"""Turn a landscape gameplay clip into a finished 9:16 short: blurred background, the gameplay
centred, a title bar at the top and big captions underneath.

Text is rasterised to transparent PNGs with Pillow and composited with the overlay filter, rather
than drawn by ffmpeg. That started as a workaround, because the author's ffmpeg build carries no
subtitles, ass or drawtext filter, and it stayed because it gives exact control of the styling and
works on any build.
"""
import json, os, re, subprocess, tempfile

from PIL import Image, ImageDraw

from . import encode, fonts, media, paths

W, H = 1080, 1920                      # the canvas every vertical platform wants
# Space the platform's own buttons sit over, so nothing important goes there.
SAFE = {"reels": (245, 400), "tiktok": (180, 420), "shorts": (250, 350), "all": (250, 420), "none": (0, 0)}


def wrap(draw, text, fnt, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=fnt) <= width or not cur:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def text_png(path, text, fnt, centre_y, fill=(255, 255, 255, 255), stroke=(0, 0, 0, 235),
             max_width=None, line_gap=1.18, box=None):
    """One transparent 1080x1920 frame with `text` centred horizontally at `centre_y`."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lines = wrap(d, text, fnt, max_width or int(W * 0.88))
    asc, desc = fnt.getmetrics()
    lh = int((asc + desc) * line_gap)
    total = lh * len(lines)
    y = int(centre_y - total / 2)
    if box:
        pad_x, pad_y, colour, radius = box
        widest = max(d.textlength(l, font=fnt) for l in lines)
        d.rounded_rectangle([(W - widest) / 2 - pad_x, y - pad_y, (W + widest) / 2 + pad_x, y + total + pad_y],
                            radius=radius, fill=colour)
    sw = max(3, fnt.size // 9)
    for line in lines:
        x = (W - d.textlength(line, font=fnt)) / 2
        d.text((x, y), line, font=fnt, fill=fill, stroke_width=sw, stroke_fill=stroke)
        y += lh
    img.save(path)
    return path


def cues_from_srt(srt):
    def secs(ts):
        h, m, rest = ts.split(":"); s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    out = []
    for block in re.split(r"\n\s*\n", open(srt).read().strip()):
        lines = [l for l in block.strip().splitlines() if l.strip()]
        if len(lines) < 3:
            continue
        a, b = lines[1].split(" --> ")
        out.append((secs(a), secs(b), " ".join(l.strip() for l in lines[2:])))
    return out


def build(video, title, cues, out, platform="reels", blur=28, dim=0.2, title_font="display",
          caption_font="body", panel_aspect=None):
    info = media.probe(video)
    top, bottom = SAFE.get(platform, SAFE["reels"])
    # The gameplay fills the canvas width. panel_aspect crops the sides first, so the panel is
    # taller and the frame feels fuller; None keeps the whole 16:9 scene.
    src_aspect = info["width"] / info["height"]
    aspect = panel_aspect or src_aspect
    panel_h = int(round(W / aspect / 2) * 2)
    panel_y = (H - panel_h) // 2
    with paths.workdir("short") as tmp:
        overlays = []
        if title:
            # Just below the platform's top furniture, above the gameplay panel.
            cy = top + (panel_y - top) // 2
            overlays.append((text_png(f"{tmp}/title.png", title.upper(), fonts.resolve(title_font, 96), cy,
                                      max_width=int(W * 0.86)), None, None))
        cap_font = fonts.resolve(caption_font, 64)
        cap_cy = panel_y + panel_h + (H - bottom - (panel_y + panel_h)) // 2
        for i, (s, e, text) in enumerate(cues):
            overlays.append((text_png(f"{tmp}/cue{i:03d}.png", text, cap_font, cap_cy,
                                      max_width=int(W * 0.84)), s, e))

        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(video)]
        for p, _, _ in overlays:
            cmd += ["-i", p]
        chain = [
            f"[0:v]split=2[bg][fg]",
            f"[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"{encode.blur_filter(blur)},eq=brightness=-{dim}:saturation=0.8[bgb]",
            (f"[fg]scale={W}:{panel_h}[fgs]" if aspect >= src_aspect - 1e-6 else
             f"[fg]crop=ih*{aspect:.5f}:ih:(iw-ih*{aspect:.5f})/2:0,scale={W}:{panel_h}[fgs]"),
            f"[bgb][fgs]overlay=0:{panel_y}[base]",
        ]
        prev = "[base]"
        for i, (_, s, e) in enumerate(overlays, 1):
            tag = f"[v{i}]"
            en = f":enable='between(t,{s:.3f},{e:.3f})'" if s is not None else ""
            chain.append(f"{prev}[{i}:v]overlay=0:0{en}{tag}")
            prev = tag
        cmd += ["-filter_complex", ";".join(chain), "-map", prev, "-map", "0:a?",
                *encode.video_args(H, bitrate="12M", crf=21),
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                *encode.audio_args(), *encode.container_args(), str(out)]
        # inside the scratch directory: ffmpeg reads the overlay PNGs from it
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr.strip()[:600])
    return out
