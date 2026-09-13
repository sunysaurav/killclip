"""Read kill-feed crops with a local vision-language model (Qwen3-VL via mlx-vlm).
Usage: .venv-vlm/bin/python tools/vlm_feed.py --model mlx-community/Qwen3-VL-8B-Instruct-4bit img1.png img2.png ...
Prints one JSON line per image: {"file", "text", "seconds"}."""
import argparse, json, sys, time
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config

PROMPT = ("This is the kill feed from a Battlefield 6 multiplayer match. Each row reads: killer name, weapon icon, "
          "victim name. List every row as a JSON array of objects with keys \"killer\" and \"victim\", top row first. "
          "Copy names exactly, character by character. Output only the JSON.")

ap = argparse.ArgumentParser(); ap.add_argument("--model", default="mlx-community/Qwen3-VL-8B-Instruct-4bit")
ap.add_argument("--max-tokens", type=int, default=200); ap.add_argument("images", nargs="+")
a = ap.parse_args()
t0 = time.time()
model, processor = load(a.model); config = load_config(a.model)
print(json.dumps({"loaded": a.model, "seconds": round(time.time() - t0, 1)}), flush=True)
for f in a.images:
    t0 = time.time()
    prompt = apply_chat_template(processor, config, PROMPT, num_images=1)
    out = generate(model, processor, prompt, image=[f], max_tokens=a.max_tokens, temperature=0.0, verbose=False)
    text = out.text if hasattr(out, "text") else str(out)
    print(json.dumps({"file": f, "text": text.strip(), "seconds": round(time.time() - t0, 2)}), flush=True)
