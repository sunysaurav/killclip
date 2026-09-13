"""Command line: probe, frames, template, test, detect, cut, montage, audio-ref, audio-scan."""
import argparse
import glob
import json
import logging
import os
import sys

import cv2
import numpy as np

from . import audio, beatsync, cut, detect, games, log as logmod, media

log = logging.getLogger("killclip.cli")


def cmd_probe(a, cfg):
    print(json.dumps(media.probe(a.video), indent=2))


def cmd_frames(a, cfg):
    """Dump frames around a time with the game's regions drawn (first red, then green, blue, yellow)."""
    info = media.probe(a.video)
    colors = ["red", "green", "blue", "yellow"]
    W, H, scale = media.scaled(info["width"], info["height"], cfg["calib_height"])
    boxes = [(*media.region_px(r, W, H), colors[i % 4])
             for i, r in enumerate(games.load(cfg["detector"]).regions(cfg).values())]
    os.makedirs(a.out, exist_ok=True)
    t = a.at - a.span / 2
    while t <= a.at + a.span / 2 + 1e-9:
        if t >= 0:
            out = os.path.join(a.out, f"frame_{t:08.2f}.png")
            media.save_frame(a.video, t, out, boxes, scale)
            print(out)
        t += a.step


def cmd_template(a, cfg):
    """Cut a grayscale template from the frame at --at; --box is x0 y0 x1 y1 in full-frame pixels."""
    info = media.probe(a.video)
    W, H, _ = media.scaled(info["width"], info["height"], cfg["calib_height"])   # --box is in these pixels
    x0, y0, x1, y1 = a.box
    img = media.grab_crop(a.video, a.at, [x0 / W, y0 / H, x1 / W, y1 / H], info["width"], info["height"], cfg["calib_height"])
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    cv2.imwrite(a.out, img)
    preview = os.path.splitext(a.out)[0] + "_x6.png"
    cv2.imwrite(preview, cv2.resize(img, None, fx=6, fy=6, interpolation=cv2.INTER_NEAREST))
    print(f"wrote {a.out}: {img.shape[1]}x{img.shape[0]} px (preview {preview})")


def cmd_test(a, cfg):
    """The game detector's report at one moment; saves its annotated image if it makes one."""
    lines, vis = detect.inspect(a.video, cfg, media.probe(a.video), a.at)
    print("\n".join(lines))
    if vis is not None:
        os.makedirs(a.out, exist_ok=True)
        out = os.path.join(a.out, f"test_{a.at:08.2f}.png")
        cv2.imwrite(out, vis)
        print(out)


def cmd_detect(a, cfg):
    info = media.probe(a.video)
    log.info("detect %s: %dx%d %.2f fps %.1fs, player %r", a.video, info["width"], info["height"],
             info["fps"], info["duration"], cfg["player_name"])
    events = detect.scan(a.video, cfg, info, ocr=not a.no_ocr)
    detect.audio_check(a.video, cfg, events)
    ms = detect.moments(events, cfg, info["duration"])
    detect.write(a.out, a.video, cfg, ms)
    print(f"{len(ms)} moments, {sum(m['kills'] for m in ms)} kills -> {a.out}")
    for m in ms:
        flag = "" if m["sources"] == ["ko"] else f"  [{', '.join(m['sources'])}]"
        print(f"  #{m['id']:02d} {m['start']:8.2f}s  kills={m['kills']}  {', '.join(m['victims'])}{flag}")


def cmd_cut(a, cfg):
    ev = detect.read(a.events)
    video = a.video or ev["video"]
    info = media.probe(video)
    os.makedirs(a.out, exist_ok=True)
    for m in ev["moments"]:
        if a.only and m["id"] not in a.only:
            continue
        if a.pre is not None:
            m["clip_start"] = max(0.0, m["start"] - a.pre)
        if a.post is not None:
            m["clip_end"] = min(info["duration"], m["end"] + a.post)
        name = f"kill_{m['id']:02d}_{int(m['start']):05d}s_x{m['kills']}{'_v' if a.vertical else ''}.mp4"
        out = os.path.join(a.out, name)
        cut.cut_clip(video, m["clip_start"], m["clip_end"], out, info, a.vertical, a.grade)
        print(out)
    if a.edl:
        edl = os.path.join(a.out, "kills.edl")
        cut.write_edl(edl, ev["moments"], info["fps"], os.path.basename(video))
        print(edl)


def cmd_montage(a, cfg):
    clips = a.clips or sorted(c for c in glob.glob(os.path.join(a.clips_dir, "kill_*.mp4")))
    if not clips:
        sys.exit("no clips found")
    cut.montage(clips, a.out, a.fade)
    print(a.out)


def cmd_beatsync(a, cfg):
    """Montage with every kill on a beat of the music; --style picks the speed pattern and effect."""
    events = beatsync.pool(a.events)                                 # kills from every recording given
    if a.video:
        events = [dict(e, video=a.video) for e in events]
    pattern = [tuple(float(v) for v in p.split(":")) for p in a.pattern.split(",")] if a.pattern else None
    mod = games.load(cfg["detector"])
    refine = mod.make_refiner(cfg) if hasattr(mod, "make_refiner") else None
    slots, tempo = beatsync.build(a.video, events, a.music, a.out, a.beats_per_kill, a.kill_at, pattern,
                                  start_beat=a.start_beat, refine=refine, bpm=a.bpm, streak_gap=a.streak_gap,
                                  style=a.style, effect=None if a.effect == "none" else a.effect, grade=a.grade,
                                  music_start=a.music_start)
    kills = sum(len(s["kills"]) for s in slots)
    print(f"{kills} kills in {len(slots)} slots on beats at {tempo:.0f} BPM, style {a.style} -> {a.out}")


def cmd_audio_ref(a, cfg):
    out = a.out or cfg["audio_ref"]
    if not out:
        sys.exit("give --out or set audio_ref in the config")
    ref = audio.cut_ref(media.read_audio(a.video), a.start, a.dur)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    audio.save_wav(out, ref)
    print(f"wrote {out}: {len(ref) / media.SR:.2f}s, peak {np.abs(ref).max():.3f}")


def cmd_audio_scan(a, cfg):
    """Print the strongest matches of the reference sting so you can judge if audio helps."""
    if not cfg["audio_ref"]:
        sys.exit("audio_ref is not set in the config")
    y = media.read_audio(a.video)
    sc = audio.scores(y, audio.load_wav(cfg["audio_ref"]), *cfg["audio_band"])
    pk = sorted(audio.peaks(sc, 0.0, cfg["audio_min_gap"]), key=lambda p: -p[1])[: a.top]
    print(f"top {a.top} matches (time, score); threshold {cfg['audio_threshold']}")
    for t, s in sorted(pk):
        print(f"  {t:8.2f}s  {s:.3f}  {'*' if s >= cfg['audio_threshold'] else ''}")
    if a.around is not None:
        lo, hi = int((a.around - 3) * media.SR / audio.HOP), int((a.around + 3) * media.SR / audio.HOP)
        seg = sc[max(0, lo):hi]
        print(f"max score within 3s of {a.around}s: {seg.max():.3f} at {(max(0, lo) + seg.argmax()) * audio.HOP / media.SR:.2f}s")


def main(argv=None):
    p = argparse.ArgumentParser(prog="killclip", description=__doc__)
    p.add_argument("--game", default=os.environ.get("KILLCLIP_GAME", "marvel-rivals"),
                   help="loads configs/<game>.json (env KILLCLIP_GAME); KILLCLIP_PLAYER overrides player_name")
    p.add_argument("--config", help="explicit config file instead of --game")
    p.add_argument("--grade", default="none", choices=["none", "natural", "vivid"],
                   help="colour of cut clips and montages: none (as recorded, HDR tags kept), "
                        "natural (HDR tone-mapped to SDR), vivid (tone map plus a little saturation)")
    p.add_argument("-v", "--verbose", action="store_true", help="debug detail on the console too")
    p.add_argument("--log-dir", help="where run logs go (default: logs/ in the repo)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("probe", help="print resolution, fps, duration")
    s.add_argument("video")

    s = sub.add_parser("frames", help="dump frames around a time with the feed and KO regions drawn")
    s.add_argument("video"); s.add_argument("--at", type=float, required=True)
    s.add_argument("--span", type=float, default=3.0); s.add_argument("--step", type=float, default=0.5)
    s.add_argument("--out", default="calib/frames")

    s = sub.add_parser("template", help="cut a template png from a frame (KO letters, or your name in the feed)")
    s.add_argument("video"); s.add_argument("--at", type=float, required=True)
    s.add_argument("--box", type=int, nargs=4, metavar=("X0", "Y0", "X1", "Y1"), required=True)
    s.add_argument("--out", required=True)

    s = sub.add_parser("test", help="show KO score, feed rows and victim OCR at one moment")
    s.add_argument("video"); s.add_argument("--at", type=float, required=True)
    s.add_argument("--out", default="calib/test")

    s = sub.add_parser("detect", help="find kills; writes events.json and events.csv")
    s.add_argument("video"); s.add_argument("--out", default="events.json")
    s.add_argument("--no-ocr", action="store_true", help="skip victim OCR")

    s = sub.add_parser("cut", help="cut one clip per moment from events.json")
    s.add_argument("--video"); s.add_argument("--events", default="events.json")
    s.add_argument("--out", default="clips"); s.add_argument("--vertical", action="store_true")
    s.add_argument("--edl", action="store_true", help="also write kills.edl for DaVinci/Premiere")
    s.add_argument("--only", type=int, nargs="*", help="moment ids to cut")
    s.add_argument("--pre", type=float, help="seconds before the first kill (overrides the config's clip_pre)")
    s.add_argument("--post", type=float, help="seconds after the last kill (overrides the config's clip_post)")

    s = sub.add_parser("montage", help="join clips with crossfades")
    s.add_argument("--clips-dir", default="clips"); s.add_argument("--clips", nargs="*")
    s.add_argument("--out", default="clips/montage.mp4"); s.add_argument("--fade", type=float, default=0.5)

    s = sub.add_parser("beatsync", help="montage with each kill landing on a beat of a music track")
    s.add_argument("--music", required=True, help="mp3/wav/m4a; constant tempo works best")
    s.add_argument("--events", nargs="+", default=["events.json"], help="one or more events files (their recordings are pooled)")
    s.add_argument("--video", help="override the recording path stored in the events file")
    s.add_argument("--out", default="clips/beat-montage.mp4")
    s.add_argument("--style", default="slowmo", choices=list(beatsync.STYLES),
                   help="slowmo: slow into the kill, fast out; clean: hard cuts at 1x; punch: clean + zoom punch on "
                        "the kill; freeze: rush in at 2x, white flash and hold the kill frame for a beat")
    s.add_argument("--effect", default="preset", choices=["preset", "none", "punch", "flash"],
                   help="override the style's on-beat effect")
    s.add_argument("--beats-per-kill", type=int, default=4, help="beats per kill slot (4 = one bar)")
    s.add_argument("--kill-at", type=float, help="where in the slot the kill lands (0-1); default from the style")
    s.add_argument("--pattern", help="lead:fast speed factors per slot, cycling, e.g. 0.5:1.5,0.75:1.25; default from the style")
    s.add_argument("--start-beat", type=int, default=0, help="skip this many beats at the start of the track")
    s.add_argument("--music-start", type=float, help="start the montage this many seconds into the track (instead of --start-beat)")
    s.add_argument("--bpm", type=float, help="force the tempo if the tracker picks a half or double tempo")
    s.add_argument("--streak-gap", type=float, default=6.0,
                   help="kills this close (s) form a streak that plays on through, one beat per kill; 0 = every kill solo")

    s = sub.add_parser("audio-ref", help="save a sound starting at --start as the reference sting")
    s.add_argument("video"); s.add_argument("--start", type=float, required=True)
    s.add_argument("--dur", type=float, default=0.5); s.add_argument("--out")

    s = sub.add_parser("audio-scan", help="list the strongest sting matches")
    s.add_argument("video"); s.add_argument("--top", type=int, default=25)
    s.add_argument("--around", type=float)

    a = p.parse_args(argv)
    logfile = logmod.setup(a.verbose, a.log_dir)
    path = a.config or detect.config_path(a.game)
    if not os.path.exists(path):
        sys.exit(f"no config at {path}; copy configs/marvel-rivals.json there and edit it (KILLCLIP_HOME sets the folder)")
    cfg = detect.load_config(path, a.game)
    log.info("%s | game %s | player %r | log %s", a.cmd, a.game, cfg["player_name"], os.path.relpath(logfile))
    globals()["cmd_" + a.cmd.replace("-", "_")](a, cfg)
