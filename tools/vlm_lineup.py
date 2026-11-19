"""Line-up test for a local vision-language model: which hero on a labelled roster sheet is this feed tile?
Usage: .venv-vlm/bin/python tools/vlm_lineup.py --model mlx-community/gemma-3-27b-it-4bit roster.png tile.png [...]"""
import argparse, json, os, time
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config

ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); ap.add_argument("roster"); ap.add_argument("tiles", nargs="+"); a = ap.parse_args()
t0 = time.time(); model, processor = load(a.model); config = load_config(a.model)
print(json.dumps({"loaded": a.model, "seconds": round(time.time() - t0, 1)}), flush=True)
PROMPT = ("The first image is a reference sheet of Marvel Rivals hero portraits with the hero's name written under each. "
          "The second image is a small, blurry portrait cropped from the in-game kill feed; the feed uses different art, so "
          "match on hair colour and style, skin, mask or helmet and colours rather than the exact drawing. Which hero on the "
          "sheet is the second image? Answer with the hero's name exactly as written on the sheet, then your second choice.")
labels = json.load(open("calib/marvel-rivals/feed-portraits/labels.json"))
for t in a.tiles:
    t0 = time.time(); prompt = apply_chat_template(processor, config, PROMPT, num_images=2)
    out = generate(model, processor, prompt, image=[a.roster, t], max_tokens=40, temperature=0.0, verbose=False)
    text = (out.text if hasattr(out, "text") else str(out)).strip().replace("\n", " ")
    truth = labels.get(os.path.basename(t).replace("tm-", "").replace("big-", ""), "?")
    print(json.dumps({"file": os.path.basename(t), "truth": truth, "answer": text, "seconds": round(time.time() - t0, 1)}), flush=True)
