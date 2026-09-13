"""Fast regression: run the detector on short case segments and compare kill counts.

  .venv/bin/python tools/check_cases.py            # all cases (~30 s)
  .venv/bin/python tools/check_cases.py penta      # cases whose name contains 'penta'
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from killclip import detect, media  # noqa: E402

CASES = {  # file: (game, expected kills, expected banner words or None)
    "mr-double-290.webm": ("marvel-rivals", 2, ["KO", "DOUBLE"]),
    "mr-killcam-735.webm": ("marvel-rivals", 0, []),
    "mr-killcam-385.webm": ("marvel-rivals", 0, []),
    "mr-triple-665.webm": ("marvel-rivals", 3, ["KO", "DOUBLE", "TRIPLE"]),
    "mr-penta-1135.webm": ("marvel-rivals", 5, ["KO", "DOUBLE", "TRIPLE", "QUAD", "PENTA"]),
    "mr-hexa-2728.webm": ("marvel-rivals", 6, ["KO", "DOUBLE", "TRIPLE", "QUAD", "PENTA", "HEXA"]),
    "mr-enemydouble-555.webm": ("marvel-rivals", 0, []),
    "mr-late-2683.webm": ("marvel-rivals", 3, ["KO", "DOUBLE", "TRIPLE"]),   # feed rows arrive late
    "mr-backfill-828.webm": ("marvel-rivals", 1, ["KO"]),
}


def main():
    logging.getLogger("killclip").setLevel(logging.ERROR)
    want = sys.argv[1] if len(sys.argv) > 1 else ""
    ok = True
    for name, (game, kills, words) in CASES.items():
        if want not in name:
            continue
        path = os.path.join("videos", "work", "cases", name)
        cfg = detect.load_config(detect.config_path(game), game)
        events = detect.scan(path, cfg, media.probe(path))
        got_words = [e.get("banner", "?") for e in events]
        passed = len(events) == kills and (words is None or got_words == words)
        ok &= passed
        print(f"{'PASS' if passed else 'FAIL'}  {name:26s} kills {len(events)} (want {kills})  {got_words}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
