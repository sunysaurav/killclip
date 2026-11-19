"""Optional progress reporting.

The pipeline only ever reported progress by logging, which is fine to read in a terminal and useless
to draw a progress bar from. This is the thin seam that lets a caller receive it as data: install a
sink, and the four long loops in the package call it as they go.

With no sink installed every call is a no-op, so the CLI behaves exactly as before. The sink is a
context variable rather than a keyword argument because the GTA detector's progress happens inside
`sound.listen`, reached through `games.gta.candidates(video, cfg, info)`, and that three-argument
shape is the documented game-module contract.
"""
import contextvars

_sink = contextvars.ContextVar("killclip_progress_sink", default=None)


def to(fn):
    """Install a sink `fn(stage, done, total, extra)`. Returns a token for `contextvars.reset`."""
    return _sink.set(fn)


def step(stage, done, total=None, **extra):
    fn = _sink.get()
    if fn is None:
        return
    try:
        fn(stage, float(done), None if total is None else float(total), extra)
    except Exception:
        pass          # reporting progress must never be the thing that breaks a render
