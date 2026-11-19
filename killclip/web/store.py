"""The UI's workspace: one folder per project, plain JSON inside.

A project is one recording plus everything made from it. The detector's own `events.json` is written
here untouched, and the user's decisions live beside it in `edits.json` rather than inside it, because
`detect.write` rewrites the whole events file and bakes the resolved config into it: merging the two
would mean a re-detect silently discarded every trim the user had made.

No database. The implementation plan reserves `killclip/index.py` for the kill index, and a UI that
invented its own schema first would be in the way when that lands.
"""
import json
import logging
import os
import re
import time

from .. import detect, media, paths

log = logging.getLogger("killclip.web.store")

VIDEO_SUFFIXES = (".mp4", ".webm", ".mkv", ".mov", ".m4v", ".avi")
AUDIO_SUFFIXES = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")


def work():
    return os.environ.get("KILLCLIP_WORK") or os.path.join(paths.home(), "work")


def projects_dir():
    return os.path.join(work(), "projects")


def project_dir(pid):
    return os.path.join(projects_dir(), pid)


def write_json(path, obj):
    """Atomic, so a crash halfway cannot lose the moment list the user just edited."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {} if default is None else default


def slug(text):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return s[:48] or "project"


def roots():
    """Folders the file picker may look in. Everything else is refused."""
    out = []
    for p in (os.environ.get("KILLCLIP_VIDEOS"), os.path.join(paths.home(), "videos"),
              os.path.expanduser("~/Movies"), os.path.expanduser("~/Downloads"), work()):
        if p and os.path.isdir(p) and p not in out:
            out.append(os.path.realpath(p))
    return out


def allowed(path):
    """True when `path` sits under a root, or inside the workspace. Keeps the picker and the media
    endpoints from serving anything on the disk."""
    real = os.path.realpath(path)
    return any(real == r or real.startswith(r + os.sep) for r in roots())


def browse(path=None):
    rs = roots()
    here = os.path.realpath(path or (rs[0] if rs else os.path.expanduser("~")))
    if not allowed(here):
        here = rs[0] if rs else os.path.expanduser("~")
    entries = []
    try:
        for name in sorted(os.listdir(here), key=str.lower):
            if name.startswith("."):
                continue
            full = os.path.join(here, name)
            is_dir = os.path.isdir(full)
            suffix = os.path.splitext(name)[1].lower()
            kind = "dir" if is_dir else ("video" if suffix in VIDEO_SUFFIXES else
                                         "audio" if suffix in AUDIO_SUFFIXES else "file")
            if kind == "file":
                continue
            entries.append({"name": name, "path": full, "kind": kind,
                            "size": 0 if is_dir else os.path.getsize(full)})
    except OSError as e:
        log.info("cannot list %s: %s", here, e)
    parent = os.path.dirname(here)
    return {"dir": here, "parent": parent if allowed(parent) else None,
            "roots": [{"name": os.path.basename(r) or r, "path": r} for r in rs], "entries": entries}


def poster(video):
    """The console writes a .jpg beside each recording; free project art."""
    cand = os.path.splitext(video)[0] + ".jpg"
    return cand if os.path.exists(cand) else None


def summary(pid):
    p = read_json(os.path.join(project_dir(pid), "project.json"))
    if not p:
        return None
    ev = os.path.join(project_dir(pid), "events.json")
    p["id"] = pid
    p["has_events"] = os.path.exists(ev)
    p["moments"] = len(read_json(ev, {}).get("moments", [])) if p["has_events"] else 0
    return p


def all_projects():
    d = projects_dir()
    if not os.path.isdir(d):
        return []
    out = [summary(pid) for pid in sorted(os.listdir(d))]
    return sorted([p for p in out if p], key=lambda p: p.get("created", 0), reverse=True)


def create(video, game, player="", name=None):
    if not os.path.isfile(video):
        raise FileNotFoundError(video)
    info = media.probe(video)
    base = name or os.path.splitext(os.path.basename(video))[0]
    pid = slug(base)
    n, pid0 = 2, pid
    while os.path.exists(project_dir(pid)):
        pid = f"{pid0}-{n}"
        n += 1
    rec = {"id": pid, "video": os.path.realpath(video), "game": game, "player": player,
           "name": base, "created": time.time(), "poster": poster(video), "info": info}
    write_json(os.path.join(project_dir(pid), "project.json"), rec)
    log.info("project %s: %s (%s)", pid, video, game)
    return rec


def moments(pid):
    """The detector's moments with the user's edits laid over them."""
    d = project_dir(pid)
    ev = read_json(os.path.join(d, "events.json"), {})
    edits = read_json(os.path.join(d, "edits.json"), {})
    out = []
    for m in ev.get("moments", []):
        mid = str(m.get("id"))
        e = edits.get(mid, {})
        out.append({
            "id": m.get("id"), "start": m.get("start"), "end": m.get("end"),
            "kills": m.get("kills", 0), "victims": m.get("victims", []),
            "labels": m.get("labels", []), "sources": m.get("sources", []),
            "score": m.get("score"),
            "clip_start": e.get("clip_start", m.get("clip_start")),
            "clip_end": e.get("clip_end", m.get("clip_end")),
            "keep": e.get("keep", True), "title": e.get("title", ""),
            "kill_times": [ev_.get("t") for ev_ in m.get("events", [])],
        })
    return out


def edit(pid, mid, patch):
    path = os.path.join(project_dir(pid), "edits.json")
    edits = read_json(path, {})
    cur = edits.get(str(mid), {})
    cur.update({k: v for k, v in patch.items()
                if k in ("clip_start", "clip_end", "keep", "title") and v is not None})
    edits[str(mid)] = cur
    write_json(path, edits)
    return cur


def artifacts(pid):
    d = project_dir(pid)
    out = {}
    for kind in ("clips", "shorts", "montage"):
        folder = os.path.join(d, kind)
        files = sorted(os.listdir(folder)) if os.path.isdir(folder) else []
        out[kind] = [{"name": f, "path": os.path.join(folder, f),
                      "size": os.path.getsize(os.path.join(folder, f))}
                     for f in files if f.endswith(".mp4") or f.endswith(".edl")]
    return out
