"""The UI's endpoints. One function per route, each returning something JSON-serialisable."""
import glob
import logging
import os

from .. import beatsync, detect, encode, fonts, grade, media, ocr, panns, paths, short
from . import jobs, store
from .server import HttpError, Router

log = logging.getLogger("killclip.web.api")
api = Router()


def _project(pid):
    rec = store.read_json(os.path.join(store.project_dir(pid), "project.json"))
    if not rec:
        raise HttpError(404, f"no project {pid}")
    rec["id"] = pid
    return rec


def _checked(path):
    if not path or not store.allowed(path):
        raise HttpError(403, f"path outside the allowed folders: {path}")
    return path


@api.get("/api/state")
def state(req):
    """Everything the page needs to render its chrome: what this machine can do, which games exist,
    the constants the layout preview must agree with, and the current projects and jobs."""
    caps, encoder_name, trouble = {}, None, []
    try:
        caps = encode.caps()
        encoder_name = encode.encoder()
    except encode.FfmpegError as e:
        trouble.append(str(e))
    try:
        ocr.require()
        has_ocr = True
    except ocr.OcrError as e:
        has_ocr = False
        trouble.append(str(e))
    games = []
    cfg_dir = os.path.join(paths.home(), "configs")
    for f in sorted(glob.glob(os.path.join(cfg_dir, "*.json"))):
        name = os.path.splitext(os.path.basename(f))[0]
        try:
            cfg = detect.load_config(f, name)
        except Exception:
            continue
        games.append({"game": name, "detector": cfg.get("detector"), "player": cfg.get("player_name", ""),
                      "captions": bool(cfg.get("caption_region")),
                      "needs_sound": cfg.get("detector") == "gta"})
    return {
        "home": paths.home(), "work": store.work(),
        "caps": {"encoder": encoder_name, "ffmpeg": caps.get("version"), "ocr": has_ocr,
                 "sound": panns.available(), "trouble": trouble},
        "games": games,
        "styles": list(beatsync.STYLES), "effects": ["preset", "none", "punch", "flash"],
        "grades": list(grade.GRADES), "short": {"w": short.W, "h": short.H, "safe": short.SAFE},
        "projects": store.all_projects(), "jobs": jobs.registry.list(),
    }


@api.get("/api/browse")
def browse(req):
    return store.browse(req.query.get("path"))


@api.get("/api/probe")
def probe(req):
    path = _checked(req.query.get("path"))
    try:
        info = media.probe(path)
    except Exception as e:
        raise HttpError(400, f"cannot read {os.path.basename(path)}: {e}")
    info["poster"] = store.poster(path)
    info["name"] = os.path.basename(path)
    info["size"] = os.path.getsize(path)
    return info


@api.post("/api/projects")
def create_project(req):
    b = req.body
    video = _checked(b.get("video"))
    game = b.get("game") or "marvel-rivals"
    return store.create(video, game, b.get("player", ""), b.get("name"))


@api.get("/api/projects/:pid")
def get_project(req, pid):
    return {"project": _project(pid), "moments": store.moments(pid),
            "artifacts": store.artifacts(pid)}


@api.delete("/api/projects/:pid")
def delete_project(req, pid):
    import shutil
    _project(pid)
    shutil.rmtree(store.project_dir(pid), ignore_errors=True)   # the recording itself is never touched
    return {"deleted": pid}


@api.put("/api/projects/:pid/moments/:mid")
def edit_moment(req, pid, mid):
    _project(pid)
    return store.edit(pid, mid, req.body)


@api.post("/api/jobs")
def submit(req):
    b = req.body
    kind = b.get("kind")
    if kind not in jobs.KINDS:
        raise HttpError(400, f"unknown job kind {kind!r}; expected one of {', '.join(jobs.KINDS)}")
    return jobs.registry.submit(kind, b.get("project"), b.get("args") or {})


@api.get("/api/jobs")
def list_jobs(req):
    return jobs.registry.list()


@api.get("/api/jobs/:jid")
def get_job(req, jid):
    job = jobs.registry.get(jid)
    if not job:
        raise HttpError(404, f"no job {jid}")
    return {"job": job, "log": jobs.registry.tail(jid)}


@api.delete("/api/jobs/:jid")
def cancel_job(req, jid):
    if not jobs.registry.cancel(jid):
        raise HttpError(404, f"no running job {jid}")
    return {"cancelled": jid}


@api.get("/api/events")
def events(req):
    req.handler.sse(jobs.registry.subscribe)
    return True


@api.get("/media/file")
def media_file(req):
    req.handler.file(_checked(req.query.get("path")))
    return True


@api.get("/media/thumb/:pid/:name")
def media_thumb(req, pid, name):
    path = os.path.join(store.project_dir(pid), "thumbs", name)
    if not os.path.exists(path):
        raise HttpError(404, "not generated yet")
    req.handler.file(path, "image/jpeg")
    return True


# ---- trim, short and montage support --------------------------------------------------------
import hashlib  # noqa: E402

from . import preview  # noqa: E402

STRIP_PAD = 15.0          # the strip reaches this far past the clip, so a handle can be dragged outward


@api.get("/api/projects/:pid/moments/:mid/strip")
def moment_strip(req, pid, mid):
    """The filmstrip window for one moment: where it starts and ends, and how many frames it holds."""
    p = _project(pid)
    m = next((m for m in store.moments(pid) if str(m["id"]) == str(mid)), None)
    if not m:
        raise HttpError(404, f"no moment {mid}")
    dur = p.get("info", {}).get("duration") or media.probe(p["video"])["duration"]
    t0 = max(0.0, (m["clip_start"] or m["start"]) - STRIP_PAD)
    t1 = min(dur, (m["clip_end"] or m["end"]) + STRIP_PAD)
    out = os.path.join(store.project_dir(pid), "strips", f"m{int(mid):02d}-{t0:.1f}-{t1:.1f}.jpg")
    path, n = preview.filmstrip(p["video"], t0, t1, out)
    return {"url": f"/media/file?path={path}", "t0": t0, "t1": t1, "frames": n,
            "frame_w": preview.STRIP_W, "moment": m}


@api.get("/api/still")
def still(req):
    """A tone-mapped frame from any allowed video, for the layout preview."""
    path = _checked(req.query.get("path"))
    t = float(req.query.get("t") or 1.0)
    out = os.path.join(store.work(), "stills", f"{hashlib.sha1(path.encode()).hexdigest()[:12]}-{t:.2f}.jpg")
    preview.still(path, t, out)
    req.handler.file(out, "image/jpeg")
    return True


@api.get("/api/clips")
def all_clips(req):
    """Every cut clip across projects, for the short composer's source picker."""
    out = []
    for p in store.all_projects():
        for c in store.artifacts(p["id"]).get("clips", []):
            if c["name"].endswith(".mp4"):
                out.append(dict(c, project=p["id"], game=p["game"]))
    return out


def _kept_events(pid):
    """The kill events of a project's kept moments, each tagged with its recording."""
    p = _project(pid)
    ev = store.read_json(os.path.join(store.project_dir(pid), "events.json"), {})
    keep = {str(m["id"]) for m in store.moments(pid) if m["keep"]}
    return [dict(e, video=p["video"]) for m in ev.get("moments", []) if str(m.get("id")) in keep
            for e in m.get("events", [])]


@api.post("/api/plan")
def plan_montage(req):
    """A beat-synced montage's plan without rendering any of it: the tempo, which kill lands on which
    beat, and what did not fit. Seconds, where the render is minutes."""
    b = req.body
    music = _checked(b.get("music"))
    events = [e for pid in b.get("projects", []) for e in _kept_events(pid)]
    if not events:
        raise HttpError(400, "no kept moments in the selected projects")
    style = b.get("style", "slowmo")
    st = dict(beatsync.STYLES[style])
    if b.get("effect") not in (None, "preset"):
        st["effect"] = b["effect"]
    kill_at = b.get("kill_at") or st["kill_at"]
    times, tempo = beatsync.beats(music, bpm=b.get("bpm"))
    start_beat = int(b.get("start_beat") or 0)
    if b.get("music_start") is not None:
        import numpy as np
        start_beat = int(np.searchsorted(times, float(b["music_start"])))
    slots = beatsync.plan(events, times, int(b.get("beats_per_kill", 4)), kill_at, st, start_beat,
                          float(b.get("streak_gap", 6.0)))
    used = sum(len(s["kills"]) for s in slots)
    length = (slots[-1]["end"] - slots[0]["start"]) if slots else 0
    return {"tempo": round(tempo, 2), "beats": len(times), "kills": len(events), "used": used,
            "unused": len(events) - used, "length": round(length, 1),
            "slots": [{"start": round(s["start"], 2), "end": round(s["end"], 2),
                       "kills": [round(k, 2) for k, _ in s["kills"]],
                       "video": os.path.basename(s["video"] or "")} for s in slots]}
