"""One job, in its own process. `python -m killclip.web.worker <job dir>`

Reads `job.json`, does the work by calling the library directly, and reports on stdout as JSON Lines:

    {"t":"stage","stage":"scan"}
    {"t":"progress","stage":"scan","done":412.0,"total":2757.0,"kills":12}
    {"t":"artifact","kind":"clip","path":"/abs/..."}
    {"t":"result","data":{...}}
    {"t":"error","message":"..."}

Logging goes to stderr, which the server forwards to the browser's log pane, and to this job's own
file under logs/ exactly as a CLI run would write one.

The handlers deliberately mirror the bodies of `cli.cmd_*` rather than calling them: those print to
stdout, which is this protocol's channel, and they fall back to current-directory defaults. Here
every path is absolute and inside the project.
"""
import json
import os
import sys
import time

from .. import beatsync, captions, cut, detect, games, grade, log as logmod, media, progress, short


def say(**msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _sink(stage, done, total, extra):
    say(t="progress", stage=stage, done=done, total=total, **extra)


def _cfg(project):
    path = detect.config_path(project["game"])
    cfg = detect.load_config(path, project["game"])
    if project.get("player"):
        cfg["player_name"] = project["player"]
    return cfg


def do_detect(job, project, cfg, args):
    video = project["video"]
    info = media.probe(video)
    say(t="stage", stage="scan", total=info["duration"])
    events = detect.scan(video, cfg, info, ocr=not args.get("no_ocr"))
    ms = detect.moments(events, cfg, info["duration"])
    out = os.path.join(os.getcwd(), "events.json")
    detect.write(out, video, cfg, ms)
    say(t="stage", stage="thumbs", total=len(ms))
    thumbs = os.path.join(os.getcwd(), "thumbs")
    os.makedirs(thumbs, exist_ok=True)
    vf = grade.filters(info, "natural") + "scale=480:-2"
    for i, m in enumerate(ms, 1):
        dst = os.path.join(thumbs, f"m{m['id']:02d}.jpg")
        try:
            media.save_frame(video, m["start"] + 0.2, dst, scale=vf)
        except Exception as e:                       # a thumbnail is never worth failing a detect for
            say(t="progress", stage="thumbs", done=i, total=len(ms), detail=str(e)[:80])
            continue
        say(t="progress", stage="thumbs", done=i, total=len(ms))
    return {"events": out, "moments": len(ms), "kills": sum(m["kills"] for m in ms)}


def do_cut(job, project, cfg, args):
    video = project["video"]
    info = media.probe(video)
    out_dir = args.get("out_dir") or os.path.join(os.getcwd(), "clips")
    os.makedirs(out_dir, exist_ok=True)
    ms = [m for m in args["moments"]]
    say(t="stage", stage="cut", total=len(ms))
    written = []
    for i, m in enumerate(ms, 1):
        name = f"kill_{m['id']:02d}_{int(m['start']):05d}s_x{m.get('kills', 1)}" \
               f"{'_v' if args.get('vertical') else ''}.mp4"
        dst = os.path.join(out_dir, name)
        cut.cut_clip(video, m["clip_start"], m["clip_end"], dst, info,
                     args.get("vertical", False), args.get("grade", "none"))
        written.append(dst)
        say(t="artifact", kind="clip", path=dst, moment=m["id"])
        say(t="progress", stage="cut", done=i, total=len(ms))
    if args.get("fcpxml") and written:
        timeline = os.path.join(out_dir, "kills.fcpxml")
        # the page sends moments without their kill events; the markers come from events.json
        found = {m["id"]: m.get("events", []) for m in detect.read(os.path.join(os.getcwd(), "events.json"))["moments"]}
        full = [dict(m, events=m.get("events") or found.get(m["id"], [])) for m in ms]
        cut.write_fcpxml(timeline, list(zip(written, full)), os.path.splitext(os.path.basename(video))[0])
        say(t="artifact", kind="timeline", path=timeline)
    if args.get("edl"):
        edl = os.path.join(out_dir, "kills.edl")
        cut.write_edl(edl, ms, info["fps"], os.path.basename(video))
        say(t="artifact", kind="edl", path=edl)
    return {"clips": written, "timeline": timeline if args.get("fcpxml") and written else None}


def do_captions(job, project, cfg, args):
    region = cfg.get("caption_region")
    if not region:
        raise SystemExit(f"{project['game']} has no caption_region in its config")
    clip = args["clip"]
    say(t="stage", stage="captions")
    cues = captions.from_video(clip, region, None, cfg.get("caption_step", 0.5), cfg["calib_height"])
    return {"cues": [[a, b, t] for a, b, t in cues]}


def do_short(job, project, cfg, args):
    out_dir = os.path.join(os.getcwd(), "shorts")
    os.makedirs(out_dir, exist_ok=True)
    dst = args.get("out") or os.path.join(out_dir, "short.mp4")
    cues = [tuple(c) for c in args.get("cues", [])]
    say(t="stage", stage="encode")
    short.build(args["clip"], args.get("title", ""), cues, dst, args.get("platform", "reels"),
                dim=args.get("dim", 0.2), panel_aspect=args.get("panel_aspect"))
    say(t="artifact", kind="short", path=dst)
    return {"short": dst}


def do_beatsync(job, project, cfg, args):
    out_dir = os.path.join(os.getcwd(), "montage")
    os.makedirs(out_dir, exist_ok=True)
    dst = args.get("out") or os.path.join(out_dir, time.strftime("beat-montage-%Y%m%d-%H%M%S.mp4"))
    files = list(args.get("events") or [])
    # From the UI: one filtered events file per project, holding only the moments the user kept, so
    # pool() still deduplicates overlapping recordings and the project's own events.json is untouched.
    from . import store
    for pid in args.get("projects") or []:
        pd = store.project_dir(pid)
        ev = store.read_json(os.path.join(pd, "events.json"), {})
        keep = {str(m["id"]) for m in store.moments(pid) if m["keep"]}
        kept = [m for m in ev.get("moments", []) if str(m.get("id")) in keep]
        path = os.path.join(out_dir, f".events-{pid}.json")
        store.write_json(path, dict(ev, moments=kept))
        files.append(path)
        if not cfg:
            cfg = _cfg(store.read_json(os.path.join(pd, "project.json")))
    events = beatsync.pool(files)
    mod = games.load(cfg["detector"])
    refine = mod.make_refiner(cfg) if hasattr(mod, "make_refiner") else None
    say(t="stage", stage="render")
    slots, tempo = beatsync.build(args.get("video"), events, args["music"], dst,
                                  args.get("beats_per_kill", 4), args.get("kill_at"), None,
                                  start_beat=args.get("start_beat", 0), refine=refine,
                                  bpm=args.get("bpm"), streak_gap=args.get("streak_gap", 6.0),
                                  style=args.get("style", "slowmo"),
                                  effect=args.get("effect", "preset"),
                                  grade=args.get("grade", "none"),
                                  music_start=args.get("music_start"))
    say(t="artifact", kind="montage", path=dst)
    return {"montage": dst, "tempo": tempo, "slots": len(slots),
            "kills": sum(len(s["kills"]) for s in slots)}


HANDLERS = {"detect": do_detect, "cut": do_cut, "captions": do_captions,
            "short": do_short, "beatsync": do_beatsync}


def main(job_dir):
    with open(os.path.join(job_dir, "job.json")) as f:
        job = json.load(f)
    logfile = logmod.setup(False)
    say(t="start", kind=job["kind"], log=logfile)
    progress.to(_sink)
    from . import store
    project = store.read_json(os.path.join(store.project_dir(job["project"]), "project.json")) \
        if job.get("project") else {}
    cfg = _cfg(project) if project else {}
    if not cfg and job.get("args", {}).get("projects"):
        first = job["args"]["projects"][0]
        cfg = _cfg(store.read_json(os.path.join(store.project_dir(first), "project.json")))
    fn = HANDLERS.get(job["kind"])
    if not fn:
        say(t="error", message=f"no handler for {job['kind']}")
        return 2
    try:
        say(t="result", data=fn(job, project, cfg, job.get("args") or {}))
        return 0
    except BaseException as e:                 # SystemExit is a normal failure mode in this package
        import traceback
        say(t="error", message=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-2000:])
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
