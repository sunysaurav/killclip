"""Name the hero in small kill-feed portrait crops with Claude, using a labelled roster sheet as reference.

Usage: .venv/bin/python tools/claude_hero.py <roster-sheet.png> <tile.png> [tile.png ...]
Credentials: ANTHROPIC_API_KEY, or the key alone on the first line of ~/.anthropic_key (chmod 600).
"""
import base64, json, os, sys
import anthropic

def b64(path):
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode()

key = os.environ.get("ANTHROPIC_API_KEY")
keyfile = os.path.expanduser("~/.anthropic_key")
if not key and os.path.exists(keyfile):
    key = open(keyfile).read().strip().splitlines()[0]
client = anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()

roster, tiles = sys.argv[1], sys.argv[2:]
PROMPT = ("The first image is a reference sheet: every Marvel Rivals hero portrait with its name written under it. "
          "The second image is a small, blurry portrait cropped from the in-game kill feed. Identify which hero on the "
          "sheet the second image shows. Note the feed uses different art from the sheet, so match on hair colour and "
          "style, skin, mask or helmet, and colours, not on the exact drawing. Reply with JSON only: "
          '{"hero": "<name exactly as written on the sheet>", "confidence": <0-100>, "why": "<one short sentence>"}')
for t in tiles:
    resp = client.messages.create(
        model="claude-opus-5", max_tokens=2000,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64(roster)}},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64(t)}},
            {"type": "text", "text": PROMPT}]}])
    text = next((b.text for b in resp.content if b.type == "text"), "")
    print(json.dumps({"file": os.path.basename(t), "answer": text.strip(), "in": resp.usage.input_tokens, "out": resp.usage.output_tokens}), flush=True)
