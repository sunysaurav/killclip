"""One way to call tesseract, and one place that notices when it is not going to work.

Both OCR call sites used to invoke tesseract with different arguments and neither checked the return
code. That matters because of how tesseract fails: a missing language pack exits 1 with empty output,
so a systematic configuration error reads exactly like "no kills in this match" or "nobody spoke in
this clip". A twelve-minute scan would finish and report nothing, with no indication why.

So failures raise here, and `require()` checks up front, which turns three minutes of decoding into a
one-second error with the install command in it.
"""
import logging
import shutil
import subprocess

log = logging.getLogger("killclip.ocr")

_checked = set()


class OcrError(RuntimeError):
    """tesseract is missing, misconfigured, or failed on an image."""


def require(lang="eng"):
    """Raise unless tesseract is installed and has the language data. Cached after the first call."""
    if lang in _checked:
        return
    if not shutil.which("tesseract"):
        raise OcrError("tesseract is not on the PATH. brew install tesseract, or "
                       "apt-get install tesseract-ocr tesseract-ocr-eng. Run detect with --no-ocr to skip it.")
    r = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True)
    langs = {l.strip() for l in r.stdout.splitlines()[1:] if l.strip()}
    if langs and lang not in langs:
        raise OcrError(f"tesseract has no '{lang}' language data (it has: {', '.join(sorted(langs)) or 'none'}). "
                       f"apt-get install tesseract-ocr-{lang}, or brew reinstall tesseract.")
    _checked.add(lang)


def tsv(png_bytes, psm=7, lang="eng"):
    """Raw TSV rows from tesseract, as lists of columns. Raises if tesseract itself failed."""
    require(lang)
    r = subprocess.run(["tesseract", "stdin", "stdout", "--psm", str(psm), "-l", lang, "tsv"],
                       input=png_bytes, capture_output=True)
    if r.returncode != 0:
        raise OcrError(f"tesseract exited {r.returncode}: {r.stderr.decode(errors='replace').strip()[:200]}")
    return [line.split("\t") for line in r.stdout.decode("utf-8", "replace").splitlines()[1:]]
