"""Rank kill-feed portrait tiles against the official hero avatars with a DINO image embedding.
Usage: .venv-vlm/bin/python tools/embed_match.py [--model facebook/dinov2-base] tile.png [tile.png ...]"""
import argparse, glob, json, os, sys
import numpy as np, torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

ap = argparse.ArgumentParser(); ap.add_argument("--model", default="facebook/dinov2-base")
ap.add_argument("--assets", default="calib/marvel-rivals/heroes-assets"); ap.add_argument("tiles", nargs="+"); a = ap.parse_args()
dev = "mps" if torch.backends.mps.is_available() else "cpu"
proc = AutoImageProcessor.from_pretrained(a.model); model = AutoModel.from_pretrained(a.model).to(dev).eval()

def embed(imgs):
    with torch.no_grad():
        out = model(**proc(images=imgs, return_tensors="pt").to(dev))
    cls = out.last_hidden_state[:, 0]; patch = out.last_hidden_state[:, 1:].mean(1)
    v = torch.cat([cls, patch], 1); return torch.nn.functional.normalize(v, dim=1).cpu().numpy()

def variants(img):
    """the avatar as is, plus tighter crops around the face (the feed shows roughly the upper-middle)"""
    w, h = img.size
    return [img, img.crop((int(w * .15), int(h * .05), int(w * .85), int(h * .75))), img.crop((int(w * .25), int(h * .1), int(w * .75), int(h * .6)))]

refs, names = [], []
for f in sorted(glob.glob(os.path.join(a.assets, "*_avatar.png"))):
    if "squarehead" in f: continue
    im = Image.open(f).convert("RGBA"); bg = Image.new("RGBA", im.size, (150, 150, 150, 255)); im = Image.alpha_composite(bg, im).convert("RGB")
    for v in variants(im): refs.append(v); names.append(os.path.basename(f)[:-11])
R = embed(refs)
labels = json.load(open("calib/marvel-rivals/feed-portraits/labels.json")) if os.path.exists("calib/marvel-rivals/feed-portraits/labels.json") else {}
for t in a.tiles:
    im = Image.open(t).convert("RGB")
    sims = R @ embed([im])[0]
    best = {}
    for s, n in zip(sims, names): best[n] = max(best.get(n, -1), float(s))
    rank = sorted(best.items(), key=lambda kv: -kv[1])
    truth = labels.get(os.path.basename(t).replace("tm-", "").replace("big-", ""), "?")
    print(f"{os.path.basename(t):40s} truth {truth:16s} -> " + ", ".join(f"{n} {s:.2f}" for n, s in rank[:5]))
