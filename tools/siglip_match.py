"""Name kill-feed portrait tiles with SigLIP 2: image-to-image against the hero avatars, and
image-to-text against hero names / descriptions.
Usage: .venv-vlm/bin/python tools/siglip_match.py [--mode image|text|both] tile.png [...]"""
import argparse, glob, json, os
import numpy as np, torch
from PIL import Image
from transformers import AutoModel, AutoProcessor

ap = argparse.ArgumentParser(); ap.add_argument("--model", default="google/siglip2-base-patch16-224")
ap.add_argument("--mode", default="both"); ap.add_argument("--assets", default="calib/marvel-rivals/heroes-assets")
ap.add_argument("tiles", nargs="+"); a = ap.parse_args()
dev = "mps" if torch.backends.mps.is_available() else "cpu"
proc = AutoProcessor.from_pretrained(a.model); model = AutoModel.from_pretrained(a.model).to(dev).eval()

def img_emb(imgs):
    with torch.no_grad():
        v = model.get_image_features(**proc(images=imgs, return_tensors="pt").to(dev))
        v = v.pooler_output if hasattr(v, "pooler_output") else v
    return torch.nn.functional.normalize(v, dim=1).cpu().numpy()

def txt_emb(texts):
    with torch.no_grad():
        v = model.get_text_features(**proc(text=texts, padding="max_length", max_length=64, truncation=True, return_tensors="pt").to(dev))
        v = v.pooler_output if hasattr(v, "pooler_output") else v
    return torch.nn.functional.normalize(v, dim=1).cpu().numpy()

names, refs = [], []
for f in sorted(glob.glob(os.path.join(a.assets, "*_avatar.png"))):
    if "squarehead" in f: continue
    im = Image.open(f).convert("RGBA"); im = Image.alpha_composite(Image.new("RGBA", im.size, (150, 150, 150, 255)), im).convert("RGB")
    w, h = im.size
    for v in (im, im.crop((int(w * .15), int(h * .05), int(w * .85), int(h * .75)))):
        refs.append(v); names.append(os.path.basename(f)[:-11])
R = img_emb(refs) if a.mode in ("image", "both") else None
uniq = sorted(set(names))
T = txt_emb([f"a portrait of the Marvel hero {n.replace('-', ' ')}" for n in uniq]) if a.mode in ("text", "both") else None

for t in a.tiles:
    im = Image.open(t).convert("RGB"); e = img_emb([im])[0]
    line = f"{os.path.basename(t)[:28]:28s}"
    if R is not None:
        best = {}
        for s, n in zip(R @ e, names): best[n] = max(best.get(n, -9), float(s))
        line += "  img: " + ", ".join(f"{n} {s:.2f}" for n, s in sorted(best.items(), key=lambda kv: -kv[1])[:3])
    if T is not None:
        st = sorted(zip(T @ e, uniq), reverse=True)[:3]
        line += "  | txt: " + ", ".join(f"{n} {s:.2f}" for s, n in st)
    print(line, flush=True)
