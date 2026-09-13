"""End-to-end check on the synthetic fixture. Run: .venv/bin/python tests/test_pipeline.py"""
import json
import os
import subprocess
import sys
import tempfile

import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from killclip import cut, detect, media  # noqa: E402
import difflib  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixture.mp4")
EXPECTED = [(12.0, 1, ["IronMan"]), (27.5, 2, ["Hulk", "Venom"]), (45.0, 1, ["Magik"])]


def sim(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def cut_template(video, t, box, info, out):
    W, H = info["width"], info["height"]
    x0, y0, x1, y1 = box
    cv2.imwrite(out, media.grab_crop(video, t, [x0 / W, y0 / H, x1 / W, y1 / H], W, H))


def main():
    if not os.path.exists(FIX):
        subprocess.run([sys.executable, os.path.join(ROOT, "tests", "make_fixture.py"), FIX], check=True)
    meta = json.load(open(os.path.splitext(FIX)[0] + ".json"))
    tmp = tempfile.mkdtemp()
    info = media.probe(FIX)

    # calibrate exactly as a user would: cut both templates from frames where they are visible
    emblem_png, ko_png, double_png, name_png = (os.path.join(tmp, n) for n in ("emblem.png", "ko.png", "double.png", "name.png"))
    cut_template(FIX, 12.5, meta["emblem_box"], info, emblem_png)
    cut_template(FIX, 12.5, meta["ko_box"], info, ko_png)
    cut_template(FIX, meta["double_at"], meta["double_box"], info, double_png)
    cut_template(FIX, 13.0, meta["name_box"], info, name_png)
    cfg = detect.load_config(None)
    cfg.update({"player_name": "PLAYER", "feed_region": meta["feed_region"], "ko_region": meta["ko_region"],
                "ko_template": emblem_png, "banner_texts": {"KO": ko_png, "2X": double_png},
                "name_template": name_png, "attacker_min_right": 90})

    events = detect.scan(FIX, cfg, info)
    print("events:", [(round(e["t"], 2), e["banner"], e["victims"]) for e in events])
    assert [e["banner"] for e in events] == ["KO", "KO", "2X", "KO"], events
    ms = detect.moments(events, cfg, info["duration"])
    assert len(ms) == 3, ms
    for m, (t, k, victims) in zip(ms, EXPECTED):
        assert abs(m["start"] - t) < 0.3 and m["kills"] == k, (m, t, k)
        for v in victims:
            assert any(sim(v, got) >= 0.6 for got in m["victims"]), (v, m["victims"])
    assert not any(abs(m["start"] - bad) < 2.0 for m in ms for bad in (35.0, 50.0)), ms

    ev_path = os.path.join(tmp, "events.json")
    detect.write(ev_path, FIX, cfg, ms)
    assert os.path.exists(os.path.join(tmp, "events.csv"))

    c1 = os.path.join(tmp, "k1.mp4")
    cut.cut_clip(FIX, ms[0]["clip_start"], ms[0]["clip_end"], c1, info)
    d = media.probe(c1)["duration"]
    assert abs(d - (ms[0]["clip_end"] - ms[0]["clip_start"])) < 0.3, d

    cv = os.path.join(tmp, "k1v.mp4")
    cut.cut_clip(FIX, ms[0]["clip_start"], ms[0]["clip_end"], cv, info, vertical=True)
    pv = media.probe(cv)
    assert (pv["width"], pv["height"]) == (1080, 1920), pv

    c2 = os.path.join(tmp, "k2.mp4")
    cut.cut_clip(FIX, ms[1]["clip_start"], ms[1]["clip_end"], c2, info)
    mont = os.path.join(tmp, "montage.mp4")
    cut.montage([c1, c2], mont, fade=0.5)
    dm = media.probe(mont)["duration"]
    expect = media.probe(c1)["duration"] + media.probe(c2)["duration"] - 0.5
    assert abs(dm - expect) < 0.4, (dm, expect)

    edl = os.path.join(tmp, "kills.edl")
    cut.write_edl(edl, ms, info["fps"], "fixture.mp4")
    text = open(edl).read()
    assert text.count("FROM CLIP NAME") == 3 and "00:00:04:00 00:00:17:00" in text, text

    print("OK: all checks passed;", tmp)


if __name__ == "__main__":
    main()
