"""The browser UI: `killclip ui`."""
import logging
import os
import threading
import webbrowser

log = logging.getLogger("killclip.web")


def serve(host="127.0.0.1", port=8765, open_browser=True):
    from .api import api
    from .server import serve as run
    from . import store

    os.makedirs(store.work(), exist_ok=True)

    def opened(actual):
        url = f"http://{host}:{actual}/"
        log.info("open %s", url)
        if open_browser:
            threading.Timer(0.4, webbrowser.open, args=(url,)).start()

    run(api, host, port, on_start=opened)
