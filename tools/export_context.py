"""Export this project's context for another assistant: the repo's own documents, the source of the
pipeline, and optionally the conversation transcripts as plain text.

Usage: .venv/bin/python tools/export_context.py --out handover.md [--transcripts DIR]
"""
import argparse, glob, json, os, sys

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="handover.md")
ap.add_argument("--transcripts", help="folder of Claude Code .jsonl sessions to flatten alongside")
ap.add_argument("--max-chars", type=int, default=2_000_000)
a = ap.parse_args()
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

parts = ["# killclip - project handover\n",
         "Everything below is the current state of the project: documents, configuration and source.\n"]
for pat in ("README.md", "docs/*.md", "configs/*.json", "killclip/*.py", "killclip/games/*.py", "tools/*.py"):
    for f in sorted(glob.glob(os.path.join(root, pat))):
        rel = os.path.relpath(f, root)
        lang = "python" if f.endswith(".py") else ("json" if f.endswith(".json") else "markdown")
        parts.append(f"\n## {rel}\n\n```{lang}\n{open(f).read().rstrip()}\n```\n")
out = "".join(parts)
open(a.out, "w").write(out)
print(f"{a.out}: {len(out):,} chars, ~{len(out)//4:,} tokens")

if a.transcripts:
    lines = []
    for f in sorted(glob.glob(os.path.join(a.transcripts, "*.jsonl")), key=os.path.getmtime):
        for raw in open(f):
            try:
                d = json.loads(raw)
            except Exception:
                continue
            m = d.get("message") or {}
            role = m.get("role") or d.get("type")
            if role not in ("user", "assistant"):
                continue
            c = m.get("content")
            if isinstance(c, str):
                text = c
            else:
                text = "\n".join(b.get("text", "") for b in (c or []) if isinstance(b, dict) and b.get("type") == "text")
            text = text.strip()
            if text and not text.startswith("<") :
                lines.append(f"### {role}\n{text}\n")
    conv = "\n".join(lines)[: a.max_chars]
    fn = os.path.splitext(a.out)[0] + "-conversation.md"
    open(fn, "w").write("# killclip - conversation history (text only, tool calls removed)\n\n" + conv)
    print(f"{fn}: {len(conv):,} chars, ~{len(conv)//4:,} tokens")
