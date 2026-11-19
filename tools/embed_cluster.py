"""Test an image embedding as a PORTRAIT MATCHER: does it pull tiles of the same hero together and
push different heroes apart? Uses the known same-hero groups from one match as truth.
Usage: .venv-vlm/bin/python tools/embed_cluster.py --model <hf id> --dir <harvest dir>"""
import argparse, glob, itertools, json, os
import numpy as np, torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

ap = argparse.ArgumentParser(); ap.add_argument("--model", default="facebook/dinov3-vitb16-pretrain-lvd1689m")
ap.add_argument("--dir", required=True); a = ap.parse_args()
dev = "mps" if torch.backends.mps.is_available() else "cpu"
proc = AutoImageProcessor.from_pretrained(a.model); model = AutoModel.from_pretrained(a.model).to(dev).eval()

def embed(paths):
    ims = [Image.open(p).convert("RGB") for p in paths]
    with torch.no_grad():
        out = model(**proc(images=ims, return_tensors="pt").to(dev))
    h = out.last_hidden_state
    v = torch.cat([h[:, 0], h[:, 1:].mean(1)], 1)
    return torch.nn.functional.normalize(v, dim=1).cpu().numpy()

files = sorted(glob.glob(os.path.join(a.dir, "p*.png")))
ids = [os.path.basename(f)[:-4] for f in files]
E = embed(files); S = E @ E.T
# known same-hero pairs from the labelled sheet, and known-different pairs
same = [("p09", "p11"), ("p10", "p23"), ("p18", "p31"), ("p06", "p12"), ("p02", "p14"), ("p02", "p15"), ("p04", "p13")]
diff = [("p00", "p01"), ("p00", "p09"), ("p01", "p10"), ("p09", "p17"), ("p18", "p00"), ("p25", "p10"), ("p17", "p18")]
idx = {i: k for k, i in enumerate(ids)}
sv = [S[idx[a_], idx[b]] for a_, b in same if a_ in idx and b in idx]
dv = [S[idx[a_], idx[b]] for a_, b in diff if a_ in idx and b in idx]
print(f"model {a.model}")
print("same hero  : " + ", ".join(f"{a_}-{b} {S[idx[a_], idx[b]]:.3f}" for a_, b in same if a_ in idx and b in idx))
print("diff heroes: " + ", ".join(f"{a_}-{b} {S[idx[a_], idx[b]]:.3f}" for a_, b in diff if a_ in idx and b in idx))
print(f"same min {min(sv):.3f}  diff max {max(dv):.3f}  -> {'SEPARABLE' if min(sv) > max(dv) else 'OVERLAP'}")
# nearest neighbour of each known tile
print("nearest neighbour of each labelled tile:")
for k in ["p00", "p01", "p09", "p10", "p17", "p18", "p25", "p06"]:
    if k not in idx: continue
    order = np.argsort(-S[idx[k]])
    nn = [ids[j] for j in order if ids[j] != k][:3]
    print(f"  {k} -> " + ", ".join(f"{n} {S[idx[k], idx[n]]:.3f}" for n in nn))
