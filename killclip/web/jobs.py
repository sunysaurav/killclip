"""Long jobs: one subprocess each, a queue of one, and progress pushed to the browser.

Detection on an hour of 4K takes minutes and a montage renders one encode per kill, so none of it can
run inside the request. It runs in a child process rather than a thread, for three specific reasons:

  * Cancel means `killpg`, which stops the ffmpeg underneath. A thread cannot interrupt a 60-second
    concat, and killing the Python side alone would orphan the decode.
  * `log.setup()` is called once per process, exactly as the CLI does it, so every job writes its own
    `logs/killclip-<timestamp>.log` and the handler-stacking in `log.py` is never reached.
  * `paths.home()` is resolved at import; passing KILLCLIP_HOME in the child's environment makes the
    child agree with the server without the library having to care.

The child speaks JSON Lines on stdout (progress, artifacts, the result) and logs on stderr, which is
already the INFO stream the author reads in a terminal, so it is forwarded to the browser verbatim.
"""
import json
import logging
import os
import queue
import signal
import subprocess
import sys
import threading
import time

from .. import paths
from . import store

log = logging.getLogger("killclip.web.jobs")

KINDS = ("detect", "thumbs", "cut", "captions", "short", "beatsync", "montage")
LOG_TAIL = 400


class Registry:
    def __init__(self, parallel=1):
        self.jobs = {}
        self.logs = {}
        self.lock = threading.Lock()
        self.queue = queue.Queue()
        self.subscribers = []
        self.running = {}
        for _ in range(parallel):
            threading.Thread(target=self._worker_loop, daemon=True).start()

    # ---- subscribers -----------------------------------------------------------------------
    def subscribe(self):
        q = queue.Queue(maxsize=500)
        with self.lock:
            self.subscribers = self.subscribers[-3:] + [q]   # a few tabs at most
        return q

    def _emit(self, kind, payload):
        with self.lock:
            subs = list(self.subscribers)
        for q in subs:
            try:
                q.put_nowait((kind, payload))
            except queue.Full:
                pass

    # ---- the public surface ----------------------------------------------------------------
    def submit(self, kind, pid, args):
        jid = time.strftime("%Y%m%d-%H%M%S-") + kind + "-" + os.urandom(2).hex()
        job = {"id": jid, "kind": kind, "project": pid, "state": "queued", "args": args,
               "created": time.time(), "started": None, "finished": None,
               "progress": {}, "result": None, "error": None}
        with self.lock:
            self.jobs[jid] = job
            self.logs[jid] = []
        self._save(job)
        self._emit("job", job)
        self.queue.put(jid)
        return job

    def list(self):
        with self.lock:
            return sorted(self.jobs.values(), key=lambda j: j["created"], reverse=True)[:50]

    def get(self, jid):
        return self.jobs.get(jid)

    def tail(self, jid, n=120):
        return self.logs.get(jid, [])[-n:]

    def cancel(self, jid):
        proc = self.running.get(jid)
        job = self.jobs.get(jid)
        if job and job["state"] == "queued":
            self._finish(job, "cancelled")
            return True
        if not proc:
            return False
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            return False
        threading.Timer(5.0, self._sigkill, args=(proc,)).start()
        return True

    @staticmethod
    def _sigkill(proc):
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass

    # ---- running ---------------------------------------------------------------------------
    def _job_dir(self, jid):
        return os.path.join(store.work(), "jobs", jid)

    def _save(self, job):
        store.write_json(os.path.join(self._job_dir(job["id"]), "job.json"), job)

    def _finish(self, job, state, error=None):
        job["state"] = state
        job["error"] = error
        job["finished"] = time.time()
        self._save(job)
        self._emit("job", job)

    def _worker_loop(self):
        while True:
            jid = self.queue.get()
            job = self.jobs.get(jid)
            if not job or job["state"] != "queued":
                continue
            try:
                self._run(job)
            except Exception as e:
                log.exception("job %s crashed", jid)
                self._finish(job, "failed", f"{type(e).__name__}: {e}")

    def _run(self, job):
        jid = job["id"]
        jd = self._job_dir(jid)
        os.makedirs(jd, exist_ok=True)
        self._save(job)
        cwd = store.project_dir(job["project"]) if job["project"] else store.work()
        os.makedirs(cwd, exist_ok=True)
        # The child runs in the project directory, so a source checkout is no longer on sys.path:
        # hand it the package's parent explicitly. An installed wheel does not need this and is
        # unaffected, since site-packages is already importable.
        pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        pypath = os.pathsep.join(x for x in (pkg_parent, os.environ.get("PYTHONPATH")) if x)
        env = dict(os.environ, KILLCLIP_HOME=paths.home(), PYTHONUNBUFFERED="1",
                   PYTHONPATH=pypath, KILLCLIP_TMP=os.path.join(store.work(), "tmp"))
        os.makedirs(env["KILLCLIP_TMP"], exist_ok=True)
        proc = subprocess.Popen([sys.executable, "-m", "killclip.web.worker", jd],
                                cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)       # its own group, so cancel takes ffmpeg too
        self.running[jid] = proc
        job.update(state="running", started=time.time(), pid=proc.pid)
        self._save(job)
        self._emit("job", job)

        err = threading.Thread(target=self._read_log, args=(jid, proc.stderr), daemon=True)
        err.start()
        for raw in proc.stdout:
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            t = msg.get("t")
            if t == "progress":
                job["progress"] = {k: v for k, v in msg.items() if k != "t"}
                self._emit("progress", dict(job["progress"], id=jid))
            elif t == "result":
                job["result"] = msg.get("data")
            elif t == "error":
                job["error"] = msg.get("message")
            elif t == "artifact":
                self._emit("artifact", dict(msg, id=jid))
        code = proc.wait()
        err.join(timeout=2)
        self.running.pop(jid, None)
        if job.get("error"):
            self._finish(job, "failed", job["error"])
        elif code == 0:
            self._finish(job, "done")
        elif code in (-signal.SIGTERM, -signal.SIGKILL):
            self._finish(job, "cancelled")
        else:
            self._finish(job, "failed", f"exited {code}; see the log")
        if job["project"]:
            self._emit("project", {"id": job["project"]})

    def _read_log(self, jid, pipe):
        for raw in pipe:
            line = raw.decode("utf-8", "replace").rstrip()
            if not line:
                continue
            buf = self.logs.setdefault(jid, [])
            buf.append(line)
            del buf[:-LOG_TAIL]
            self._emit("log", {"id": jid, "line": line})


registry = Registry()
