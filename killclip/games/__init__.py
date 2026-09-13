"""One module per game. Each defines:

DEFAULTS       config keys the detector needs, with defaults
TEMPLATE_KEYS  config keys holding template png paths (resolved relative to the repo root)
regions(cfg)   {name: [x0, y0, x1, y1]} screen regions to crop, as fractions of the frame
Detector(cfg, ocr)
    .frame(t, crops)   crops = {region name: gray uint8 array}, called once per scanned frame
    .flush()           finish anything pending at the end of the video
    .events            [{t, kills, victims, source, score}] found so far
    .inspect(crops)    -> (lines of text, annotated BGR image or None) for `killclip test`
"""
import importlib


def load(name):
    return importlib.import_module(f"killclip.games.{name.replace('-', '_')}")
