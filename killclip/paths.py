"""Where configs, templates, logs and scratch space live.

From a source checkout, the checkout itself. Installed as a package, $KILLCLIP_HOME if set, else
~/.killclip, which holds configs/, calib/, models/ and logs/.

`home()` is the function; `HOME` is kept as a module attribute because most of the package reads it
that way. It is a function so a long-lived process (the web UI) can resolve it after import rather
than being stuck with whatever the environment said when the first module was loaded.
"""
import contextlib
import functools
import logging
import os
import shutil
import tempfile

log = logging.getLogger("killclip.paths")

_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@functools.cache
def home():
    env = os.environ.get("KILLCLIP_HOME")
    if env:
        return env
    if os.path.isdir(os.path.join(_SRC, "configs")):
        return _SRC
    return os.path.expanduser("~/.killclip")


HOME = home()


@contextlib.contextmanager
def workdir(name):
    """Scratch space for one render, removed afterwards.

    beatsync writes one MP4 per kill here plus a full concatenated copy, so a montage that leaks its
    temp directory leaves roughly twice the finished size behind every single run. On failure the
    directory is kept and its path logged, because those slot files are the only way to see what went
    wrong. $KILLCLIP_TMP chooses the parent; $KILLCLIP_KEEP_TEMP=1 always keeps it.
    """
    path = tempfile.mkdtemp(prefix=f"killclip-{name}-", dir=os.environ.get("KILLCLIP_TMP") or None)
    keep = os.environ.get("KILLCLIP_KEEP_TEMP") == "1"
    try:
        yield path
    except BaseException:
        log.error("%s failed; its working files are kept at %s", name, path)
        keep = True
        raise
    finally:
        if keep:
            log.info("keeping %s", path)
        else:
            shutil.rmtree(path, ignore_errors=True)
