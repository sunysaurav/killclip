"""The browser UI's server end to end on the synthetic fixture: real HTTP on a free port, real jobs in
real worker processes, real event stream. Run: .venv/bin/python tests/test_web.py"""
import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = tempfile.mkdtemp(prefix="killclip-web-test-")
os.environ["KILLCLIP_WORK"] = os.path.join(TMP, "work")       # projects go here, not in the checkout
os.environ["KILLCLIP_VIDEOS"] = os.path.join(ROOT, "tests")
sys.path.insert(0, ROOT)
from PIL import Image  # noqa: E402

from killclip import media  # noqa: E402
from killclip.web import server, store  # noqa: E402
from killclip.web.api import api  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixture.mp4")
PORT = None


def call(method, path, body=None, headers=None, raw=False):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=300)
    h = dict(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    c.request(method, path, data, h)
    r = c.getresponse()
    out = r.read()
    c.close()
    if raw:
        return r.status, out, dict(r.getheaders())
    return r.status, (json.loads(out) if out and r.getheader("Content-Type", "").startswith("application/json") else out)


class Events(threading.Thread):
    """Reads the server's event stream for the whole test, keeping every event."""

    def __init__(self):
        super().__init__(daemon=True)
        self.seen = []

    def run(self):
        c = http.client.HTTPConnection("127.0.0.1", PORT)
        c.request("GET", "/api/events")
        r = c.getresponse()
        kind = None
        for line in iter(r.fp.readline, b""):
            line = line.decode().rstrip("\n")
            if line.startswith("event: "):
                kind = line[7:]
            elif line.startswith("data: ") and kind:
                self.seen.append((kind, json.loads(line[6:])))

    def of(self, kind, jid):
        return [p for k, p in self.seen if k == kind and p.get("id") == jid]


def run_job(kind, project, args, timeout=300):
    status, job = call("POST", "/api/jobs", {"kind": kind, "project": project, "args": args})
    assert status == 200, (status, job)
    t0 = time.time()
    while time.time() - t0 < timeout:
        _, d = call("GET", f"/api/jobs/{job['id']}")
        if d["job"]["state"] in ("done", "failed", "cancelled"):
            assert d["job"]["state"] == "done", (kind, d["job"].get("error"), d["log"][-10:])
            return d["job"]
        time.sleep(0.5)
    raise AssertionError(f"{kind} job did not finish in {timeout}s")


def click_track(path, bpm=120, seconds=40):
    period = 60 / bpm
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"aevalsrc='0.8*sin(2*PI*880*t)*lt(mod(t\\,{period})\\,0.04)':s=44100:d={seconds}",
                    path], check=True)
    return path


def main():
    global PORT
    if not os.path.exists(FIX):
        subprocess.run([sys.executable, os.path.join(ROOT, "tests", "make_fixture.py"), FIX], check=True)
    os.makedirs(store.work(), exist_ok=True)
    up = threading.Event()

    def started(port):
        global PORT
        PORT = port
        up.set()

    threading.Thread(target=server.serve, args=(api, "127.0.0.1", 0, started), daemon=True).start()
    assert up.wait(10), "server did not start"
    events = Events()
    events.start()

    # the page and the state it boots from
    status, page = call("GET", "/")
    assert status == 200 and b"/static/app.js" in page
    status, st = call("GET", "/api/state")
    assert status == 200 and st["caps"]["encoder"] and "slowmo" in st["styles"], st["caps"]

    # the picker sees the fixture; the guard refuses other hosts, cross-site writes and other folders
    _, b = call("GET", f"/api/browse?path={os.path.join(ROOT, 'tests')}")
    assert "fixture.mp4" in [e["name"] for e in b["entries"]], b
    assert call("GET", "/api/state", headers={"Host": "evil.example"})[0] == 403
    assert call("POST", "/api/projects", {"video": FIX}, headers={"Sec-Fetch-Site": "cross-site"})[0] == 403
    assert call("GET", "/media/file?path=/etc/hosts")[0] == 403

    # a project and a real detect job, with its progress arriving over the event stream
    status, p = call("POST", "/api/projects", {"video": FIX, "game": "marvel-rivals"})
    assert status == 200, p
    pid = p["id"]
    job = run_job("detect", pid, {})
    assert "moments" in job["result"], job["result"]
    time.sleep(0.3)
    assert events.of("progress", job["id"]), "no progress events for the detect job"
    assert any(j["state"] == "done" for j in events.of("job", job["id"])), "no done event for the detect job"

    # known moments laid down by hand, so the rest does not depend on the game's templates
    pd = store.project_dir(pid)
    ms = [{"id": 1, "start": 12.0, "end": 12.0, "kills": 1, "clip_start": 7.0, "clip_end": 16.0,
           "events": [{"t": 12.0}]},
          {"id": 2, "start": 27.5, "end": 28.4, "kills": 2, "clip_start": 22.0, "clip_end": 32.0,
           "events": [{"t": 27.5}, {"t": 28.4}]},
          {"id": 3, "start": 45.0, "end": 45.0, "kills": 1, "clip_start": 40.0, "clip_end": 49.0,
           "events": [{"t": 45.0}]}]
    store.write_json(os.path.join(pd, "events.json"), {"video": FIX, "config": {}, "moments": ms})

    # edits sit beside the detector's output and never change it
    assert call("PUT", f"/api/projects/{pid}/moments/2", {"keep": False})[0] == 200
    assert call("PUT", f"/api/projects/{pid}/moments/1", {"clip_start": 8.0, "clip_end": 15.0})[0] == 200
    got = {m["id"]: m for m in store.moments(pid)}
    assert not got[2]["keep"] and (got[1]["clip_start"], got[1]["clip_end"]) == (8.0, 15.0), got
    assert json.load(open(os.path.join(pd, "events.json")))["moments"][0]["clip_start"] == 7.0

    # filmstrip: one frame per half second, side by side
    _, s = call("GET", f"/api/projects/{pid}/moments/1/strip")
    assert s["frames"] == round((s["t1"] - s["t0"]) * 2), s
    w, _ = Image.open(s["url"].split("path=", 1)[1]).size
    assert w == s["frames"] * s["frame_w"], (w, s)
    status, jpg, _ = call("GET", f"/api/still?path={FIX}&t=12", raw=True)
    assert status == 200 and jpg[:2] == b"\xff\xd8", status

    # montage dry run: the dropped moment's two kills are left out
    music = click_track(os.path.join(TMP, "work", "click.wav"))
    status, plan = call("POST", "/api/plan", {"projects": [pid], "music": music, "style": "clean",
                                              "beats_per_kill": 4})
    assert status == 200, plan
    assert abs(plan["tempo"] - 120) < 1.5 and plan["kills"] == 2 and plan["used"] == 2, plan

    # cut the trimmed moment, list it, and serve part of it the way a <video> element asks
    job = run_job("cut", pid, {"moments": [got[1]], "grade": "none"})
    clip = job["result"]["clips"][0]
    assert abs(media.probe(clip)["duration"] - 7.0) < 0.3, media.probe(clip)["duration"]
    _, clips = call("GET", "/api/clips")
    assert os.path.realpath(clip) in [os.path.realpath(c["path"]) for c in clips], clips
    status, part, hdr = call("GET", f"/media/file?path={clip}", headers={"Range": "bytes=0-99"}, raw=True)
    assert status == 206 and len(part) == 100 and hdr["Content-Range"].startswith("bytes 0-99/"), (status, hdr)

    # the montage render matches the plan it was shown
    job = run_job("beatsync", None, {"projects": [pid], "music": music, "style": "clean", "beats_per_kill": 4})
    r = job["result"]
    assert r["kills"] == plan["used"] and r["slots"] == len(plan["slots"]), (r, plan)
    d = media.probe(r["montage"])["duration"]
    assert abs(d - plan["length"]) < 0.3, (d, plan["length"])

    # a queued job can be cancelled before it starts
    status, a = call("POST", "/api/jobs", {"kind": "detect", "project": pid, "args": {}})
    status, b = call("POST", "/api/jobs", {"kind": "detect", "project": pid, "args": {}})
    assert call("DELETE", f"/api/jobs/{b['id']}")[0] == 200
    assert call("DELETE", f"/api/jobs/{a['id']}")[0] == 200
    time.sleep(1)
    assert call("GET", f"/api/jobs/{b['id']}")[1]["job"]["state"] == "cancelled"

    print("OK: web checks passed;", TMP)


if __name__ == "__main__":
    main()
