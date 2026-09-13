"""Logging: INFO progress on the console, everything to logs/killclip-<timestamp>.log."""
import logging
import os
import time

from .paths import HOME as ROOT


def setup(verbose=False, log_dir=None):
    log_dir = log_dir or os.path.join(ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, time.strftime("killclip-%Y%m%d-%H%M%S.log"))
    root = logging.getLogger("killclip")
    root.setLevel(logging.DEBUG)
    fh = logging.FileHandler(path)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s %(name)s: %(message)s"))
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG if verbose else logging.INFO)
    sh.setFormatter(logging.Formatter("%(levelname)-5s %(message)s"))
    root.addHandler(fh)
    root.addHandler(sh)
    return path
