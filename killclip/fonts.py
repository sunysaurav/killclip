"""The fonts titles and captions are drawn in, bundled rather than discovered.

`short.py` used to name two files under /System/Library/Fonts and catch every exception around
loading them. That fallback was worse than a crash: `ImageFont.load_default()` ignores the size it is
given, so on any machine without Apple's fonts a 96-pixel title rendered at 10 pixels and the MP4 came
out valid and illegible. Nothing in the tests would have noticed.

So the fonts ship with the package and loading them never falls back. Two roles:

    display  Anton Regular          titles. A condensed caps face, the usual stand-in for Impact.
    body     Liberation Sans Bold   captions. Metrically identical to Arial Bold, so lines wrap in
                                    exactly the same places they did before this change.

Both are SIL Open Font License 1.1 (licences alongside the files), which permits bundling inside a
larger work. They are shipped unmodified, as the licence requires. Impact and Arial are proprietary
and are never bundled; `$KILLCLIP_FONT_DISPLAY` and `$KILLCLIP_FONT_BODY` point at them for anyone who
wants the old look back.
"""
import logging
import os

from PIL import ImageFont

log = logging.getLogger("killclip.fonts")

ROLES = {"display": "Anton-Regular.ttf", "body": "LiberationSans-Bold.ttf"}
ENV = {"display": "KILLCLIP_FONT_DISPLAY", "body": "KILLCLIP_FONT_BODY"}
MIN_SIZE = 24       # the guard against a silent fallback to a 10-pixel default


class FontError(RuntimeError):
    """A font could not be loaded. Raised rather than substituting something illegible."""


def bundled(role):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts", ROLES[role])


def resolve(spec, size):
    """A font at `size`. `spec` is a role name ("display"/"body"), a path, or None for the body role.

    Never falls back: a missing or unreadable font raises, naming what to do about it."""
    role = spec if spec in ROLES else ("body" if spec is None else None)
    path = spec
    if role:
        path = os.environ.get(ENV[role]) or bundled(role)
    try:
        font = ImageFont.truetype(path, size)
    except Exception as e:
        hint = f" Set ${ENV[role]} to a .ttf file." if role else ""
        raise FontError(f"cannot load the {role or 'requested'} font at {path}: {e}.{hint}") from e
    if font.size < MIN_SIZE:
        raise FontError(f"{path} loaded at size {font.size}, not {size}: Pillow fell back to its "
                        "built-in bitmap font, which would render the text unreadably small.")
    return font
