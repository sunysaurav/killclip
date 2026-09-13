"""Colour of every output. The PS5 records in HDR (10-bit PQ, BT.2020). `none` (the default) keeps the
pixels as recorded and carries the HDR colour tags over to the output, so players that understand them
(macOS, iOS, YouTube) show the montage the way the game looked; a filter that drops those tags (zoompan)
made the punch montage look washed out, so the tags are always set explicitly. `natural` tone-maps to SDR
for players and sites that cannot show HDR; `vivid` adds saturation on top of that.

The tone map is a 3D LUT generated here once (calib/pq2sdr.cube): PQ EOTF -> linear light with 120 nits
as SDR white (brighter mid-tones than the broadcast 203) -> BT.2020 to BT.709 -> a soft knee above 0.6
so highlights roll off instead of clipping -> BT.709 OETF.
"""
import os

import numpy as np

from .paths import HOME

LUT = os.path.join(HOME, "calib", "pq2sdr.cube")
WHITE_NITS, KNEE = 120.0, 0.6
GRADES = ("none", "natural", "vivid")
SDR_TAGS = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]


def tags(info, grade="none"):
    """Encoder flags that label the output's colour: the recording's own tags for `none`, BT.709 after a tone map."""
    if grade != "none" and info.get("hdr"):
        return list(SDR_TAGS)
    c = info.get("color") or {}
    out = []
    for flag, key in (("-color_primaries", "color_primaries"), ("-color_trc", "color_transfer"), ("-colorspace", "color_space")):
        if c.get(key) and c[key] != "unknown":
            out += [flag, c[key]]
    return out


def stamp(info, grade="none"):
    """A `setparams` filter that stamps the colour tags onto the frames themselves, for the end of a graph:
    h264_videotoolbox writes the frames' tags, not the encoder flags, and zoompan drops them."""
    t = tags(info, grade)
    names = {"-color_primaries": "color_primaries", "-color_trc": "color_trc", "-colorspace": "colorspace", "-color_range": "range"}
    kv = [f"{names[t[i]]}={t[i + 1]}" for i in range(0, len(t), 2)]
    return "setparams=" + ":".join(kv) if kv else "null"


def ensure_lut():
    if os.path.exists(LUT):
        return LUT
    n = 65
    g = np.linspace(0, 1, n)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")                 # .cube order: red varies fastest
    rgb = np.stack([r, gg, b], -1).reshape(-1, 3)
    m1, m2 = 2610 / 16384, 2523 / 4096 * 128
    c1, c2, c3 = 3424 / 4096, 2413 / 4096 * 32, 2392 / 4096 * 32
    p = rgb ** (1 / m2)
    nits = 10000 * (np.maximum(p - c1, 0) / (c2 - c3 * p)) ** (1 / m1)          # PQ EOTF
    to709 = np.array([[1.6605, -0.5876, -0.0728], [-0.1246, 1.1329, -0.0083], [-0.0182, -0.1006, 1.1187]])
    lin = np.clip((nits / WHITE_NITS) @ to709.T, 0, None)
    tm = np.where(lin <= KNEE, lin, KNEE + (1 - KNEE) * (1 - np.exp(-(lin - KNEE) / (1 - KNEE))))
    tm = np.clip(tm, 0, 1)
    oetf = np.where(tm < 0.018, 4.5 * tm, 1.099 * tm ** 0.45 - 0.099)         # BT.709 OETF
    os.makedirs(os.path.dirname(LUT), exist_ok=True)
    with open(LUT, "w") as f:
        f.write(f'TITLE "PQ BT.2020 to BT.709 SDR, {WHITE_NITS:.0f} nit white, knee {KNEE}"\nLUT_3D_SIZE {n}\n')
        f.writelines(f"{x:.6f} {y:.6f} {z:.6f}\n" for x, y, z in oetf)
    return LUT


def filters(info, grade="none"):
    """Filter-chain prefix (ends with a comma, or empty) for a source described by media.probe()."""
    if grade == "none":
        return ""
    if grade not in GRADES:
        raise ValueError(f"unknown grade {grade!r}; use one of {GRADES}")
    chain = []
    if info.get("hdr"):
        chain += ["scale=in_color_matrix=bt2020:in_range=tv:out_range=pc", "format=gbrp10le",
                  f"lut3d=file={ensure_lut()}:interp=tetrahedral",
                  "scale=out_color_matrix=bt709:out_range=tv", "format=yuv420p"]
    if grade == "vivid":
        chain.append("eq=saturation=1.15" if info.get("hdr") else "eq=contrast=1.05:saturation=1.15")
    return ",".join(chain) + ("," if chain else "")
