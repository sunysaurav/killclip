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
