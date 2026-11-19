"""A small HTTP server for the browser UI, on the standard library.

The UI needs three things an ordinary static server does not give you: byte ranges, so a browser can
seek inside a video; server-sent events, so a running job can report progress; and a handful of JSON
endpoints. That is about sixty lines, which is cheaper than the dependency tree any web framework
brings, and it keeps `pip install killclip` exactly as light as it is today.

The price of hand-rolling it is that HTTP/1.1 keep-alive desynchronises if a response carries a wrong
Content-Length, so every reply goes out through `json`, `data` or `file`, and nothing writes to
`wfile` directly except the event stream, which deliberately has no length and is read until close.
"""
import json
import logging
import mimetypes
import os
import re
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, unquote, urlparse

log = logging.getLogger("killclip.web")

CHUNK = 256 * 1024


class Router:
    """Routes like '/api/projects/:pid/moments/:mid'. Handlers take (req, **params)."""

    def __init__(self):
        self.routes = []

    def add(self, method, pattern, fn):
        regex = re.sub(r":(\w+)", r"(?P<\1>[^/]+)", pattern)
        self.routes.append((method, re.compile(f"^{regex}$"), fn))

    def get(self, p):
        return lambda fn: (self.add("GET", p, fn), fn)[1]

    def post(self, p):
        return lambda fn: (self.add("POST", p, fn), fn)[1]

    def put(self, p):
        return lambda fn: (self.add("PUT", p, fn), fn)[1]

    def patch(self, p):
        return lambda fn: (self.add("PATCH", p, fn), fn)[1]

    def delete(self, p):
        return lambda fn: (self.add("DELETE", p, fn), fn)[1]

    def match(self, method, path):
        for m, rx, fn in self.routes:
            got = rx.match(path)
            if got and m == method:
                return fn, got.groupdict()
        return None, None


class Request:
    def __init__(self, handler, query):
        self.handler = handler
        self.query = {k: v[0] for k, v in query.items()}
        self._body = None

    @property
    def body(self):
        if self._body is None:
            n = int(self.handler.headers.get("Content-Length") or 0)
            raw = self.handler.rfile.read(n) if n else b"{}"
            try:
                self._body = json.loads(raw or b"{}")
            except ValueError:
                self._body = {}
        return self._body


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"        # required for Range and keep-alive
    router = None
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    server_version = "killclip"

    def log_message(self, fmt, *args):
        log.debug("%s %s", self.address_string(), fmt % args)

    # ---- replies ---------------------------------------------------------------------------
    def json(self, obj, status=200):
        self.data(json.dumps(obj).encode(), "application/json; charset=utf-8", status)

    def data(self, payload, ctype, status=200, headers=()):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def file(self, path, ctype=None):
        """Serve a file, honouring a Range request so <video> can seek."""
        if not os.path.isfile(path):
            raise HttpError(404, f"no such file: {path}")
        size = os.path.getsize(path)
        ctype = ctype or mimetypes.guess_type(path)[0] or "application/octet-stream"
        start, end = 0, size - 1
        rng = self.headers.get("Range")
        partial = False
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            if a:
                start = int(a)
                end = int(b) if b else end
            elif b:                                   # suffix range: last N bytes
                start = max(0, size - int(b))
            partial = True
            if start >= size:
                raise HttpError(416, "range beyond end of file")
            end = min(end, size - 1)
        length = end - start + 1
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(path, "rb") as f:
            f.seek(start)
            left = length
            while left > 0:
                buf = f.read(min(CHUNK, left))
                if not buf:
                    break
                self.wfile.write(buf)
                left -= len(buf)

    def sse(self, subscribe):
        """Hold the connection open and write events as they arrive. No Content-Length by design."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = subscribe()
        try:
            while True:
                try:
                    kind, payload = q.get(timeout=15)
                except Exception:
                    self.wfile.write(b": ping\n\n")      # keeps proxies and browsers from timing out
                    self.wfile.flush()
                    continue
                self.wfile.write(f"event: {kind}\ndata: {json.dumps(payload)}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.close_connection = True

    # ---- dispatch --------------------------------------------------------------------------
    def _serve(self):
        url = urlparse(self.path)
        path = unquote(url.path)
        try:
            self._guard(path)
            if path == "/" or path == "/index.html":
                return self.file(os.path.join(self.static_dir, "index.html"), "text/html; charset=utf-8")
            if path.startswith("/static/"):
                name = os.path.basename(path)
                return self.file(os.path.join(self.static_dir, name))
            fn, params = self.router.match(self.command, path)
            if not fn:
                raise HttpError(404, f"no route for {self.command} {path}")
            out = fn(Request(self, parse_qs(url.query)), **params)
            if out is None:
                return self.json({})
            if isinstance(out, tuple):
                return self.json(out[1], out[0])
            if out is not True:                          # True: the handler already replied
                return self.json(out)
        except HttpError as e:
            log.info("%s %s -> %s %s", self.command, path, e.status, e.message)
            self.json({"error": e.message}, e.status)
        except Exception as e:
            log.exception("%s %s failed", self.command, path)
            self.json({"error": f"{type(e).__name__}: {e}"}, 500)

    def _guard(self, path):
        """Refuse anything that is not this machine talking to itself."""
        host = (self.headers.get("Host") or "").split(":")[0]
        if host and host not in ("localhost", "127.0.0.1", "[::1]", "::1"):
            raise HttpError(403, f"refusing requests for host {host!r}")
        if self.command in ("POST", "PUT", "PATCH", "DELETE"):
            site = self.headers.get("Sec-Fetch-Site")
            if site and site not in ("same-origin", "none"):
                raise HttpError(403, "cross-site request refused")

    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = _serve


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve(router, host="127.0.0.1", port=8765, on_start=None):
    Handler.router = router
    httpd = Server((host, port), Handler)
    actual = httpd.server_address[1]
    if on_start:
        threading.Thread(target=on_start, args=(actual,), daemon=True).start()
    log.info("killclip ui on http://%s:%d", host, actual)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("stopping")
    finally:
        httpd.server_close()
    return actual
