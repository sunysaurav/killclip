# killclip

Finds your kills in raw gameplay footage (Marvel Rivals first) and cuts each one into a clip.
Runs entirely on this Mac: ffmpeg, tesseract, numpy, scipy, OpenCV. No cloud, no tokens.

How a kill is found, in one decode pass over the video:

- **Kill banner**: the game flashes a gold banner at a fixed spot when you eliminate someone.
  Its emblem is the same for every kill, so the emblem is the trigger; the word next to it
  ("KO", "DOUBLE!", "TRIPLE!", "QUAD!", "PENTA!", "HEXA!") only labels the banner and marks the
  next kill of a streak. One banner is one kill.
- **Kill feed**: your name, as the feed renders it, is matched in the top-right feed, and rows
  are right-aligned with the newest on top. Around the banner, the newest row with your name
  decides: a lot of row right of the name means you are the attacker (a kill); almost none
  means you are the victim, which is the kill-cam replay of your death and is rejected. Rows
  slide into place and your own rows pulse, so a row counts once seen twice at one position.
- **Audio** is optional and only logged. Marvel Rivals has no distinct kill sound.

## Install

From a checkout, the `bin/killclip` wrapper uses the local `.venv`. As a tool:

```sh
uv tool install .            # or: pipx install .
killclip --help
```

Installed that way, configs, templates and logs live in `~/.killclip/` (or the folder in
`KILLCLIP_HOME`); copy `configs/` and `calib/` there, or point `KILLCLIP_HOME` at this checkout.
Needs `ffmpeg` and `tesseract` on the PATH and, for encoding, macOS VideoToolbox.

## Adding a game

Everything that recognises a kill lives in one module per game, `killclip/games/<game>.py`
(see `marvel_rivals.py`). The shared code only decodes the video once, hands each game
module the screen regions it asked for, and turns its events into clips. A new game needs:

1. `configs/<game>.json` with `player_name`, `"detector": "<game>"` and the module's settings.
2. `killclip/games/<game>.py` defining `DEFAULTS`, `TEMPLATE_KEYS`, `regions(cfg)` and a
   `Detector` with `frame(t, crops)`, `flush()`, `events`, and `inspect(crops)`.
   The contract is documented in `killclip/games/__init__.py`.
3. The templates that module matches, cut from real frames with `killclip template`.

Nothing in the shared pipeline changes when a game is added.

## Config: one file per game

`configs/<game>.json` holds the in-game name, the detector module, its screen regions,
template paths and thresholds. `bin/killclip --game marvel-rivals ...` picks the file (default:
`marvel-rivals`, or set `KILLCLIP_GAME`). `KILLCLIP_PLAYER=Name` overrides the name for one
run. To add a game, copy `configs/marvel-rivals.json` and calibrate. Templates are tied to
the recording resolution (1080p for the PlayStation).

## One-time calibration (per game / resolution)

```sh
bin/killclip probe match.mp4                          # resolution, fps, duration
bin/killclip frames match.mp4 --at 123.4              # frames near a kill; feed box red, KO box green
#   -> adjust feed_region / ko_region in the config until the boxes cover the HUD elements
bin/killclip template match.mp4 --at 123.6 --box 1848 512 1900 556 --out calib/marvel-rivals/ko.png
bin/killclip template match.mp4 --at 124.0 --box 1645 35 1702 74   --out calib/marvel-rivals/name.png
#   boxes are full-frame pixels; check the *_x6.png previews
bin/killclip test match.mp4 --at 124.0                # KO score, feed rows, victim OCR at that moment
```

### Battlefield 6 (Battle Royale HUD)

`killclip/games/battlefield_6.py` watches the score panel that appears below-left of the
crosshair when you score: a grey "KILL" box there is a kill and becomes the event. A
"KILL CONFIRMED" box (a downed enemy bled out later) shares the letters, so each candidate
is scored against a standalone-KILL template and the head of a KILL-CONFIRMED box and must
win by a margin. The personal kill counter next to the skull icon in the top-right strip is
read as the tally; it ticks for both kinds, so it validates the total against the
end-of-round summary rather than timing the action.

Calibration: `template` for the "KILL" box, for the head of a "KILL CONFIRMED" box (same
pixel size), and for the skull icon; then harvest the counter's digit glyphs once per
resolution with `tools/harvest_digits.py` (it clusters every glyph the counter shows, you
label the tiles, it writes `calib/battlefield-6/digits/`).

## Every match after that

```sh
bin/killclip detect match.mp4                # -> events.json + events.csv
bin/killclip cut --edl                       # -> clips/kill_NN_*.mp4 + clips/kills.edl
bin/killclip cut --vertical --out shorts     # 9:16 centre-cropped versions
bin/killclip cut --pre 4 --post 2 --out tight   # tighter windows, e.g. for a montage
bin/killclip montage --clips-dir tight --fade 0.4 --out montage.mp4   # clips joined with crossfades
```

`events.csv` lists each moment: start, kills, victims. `kills.edl` imports into DaVinci
Resolve or Premiere and lays the cuts on a timeline against the original file.

## Battlefield 6 multiplayer (kill feed mode)

Battle Royale and multiplayer have different HUDs, so each has its own config: `--game battlefield-6`
(the KILL box in the score panel) and `--game battlefield-6-mp` (the kill feed at the top right, where a
kill is a row "> you  weapon  victim" and a death "killer  weapon  > you"). In feed mode a row with the
name on the left is tracked by its position: rows enter at the bottom and only move up, so a kill row no
tracked row can account for is a new kill; short dropouts are tolerated because the feed is translucent
and the template score flickers with the background. Recordings at a different size from the templates
(the 4K multiplayer recording vs the 1080p templates) are scanned at `calib_height`; `--box` for
`template` and the frames from `frames` are in those pixels.

## Colour (HDR recordings)

The PS5 records in HDR (10-bit PQ, BT.2020). By default (`--grade none`) every output keeps the
pixels as recorded and carries the recording's colour tags over, so players and sites that show HDR
(macOS, iOS, YouTube) display the clips the way the game looked. A filter that drops those tags would
make the file look washed out, so the tags are always set explicitly on the encoder. For players that
cannot show HDR there is `--grade natural` (tone map to SDR through a generated 3D LUT,
`calib/pq2sdr.cube`, see `killclip/grade.py`) and `--grade vivid` (the same plus some saturation). The
option is global, so it applies to `cut`, `montage` and `beatsync` alike.

## Beat-synced montage

```sh
bin/killclip beatsync --events videos/work/events-mr-*.json --music track.mp3 --style punch --out clips/beat.mp4
```

Every kill lands on a beat of the track and the music runs underneath. `--events` takes one or
more events files: their recordings are pooled, and two recordings of the same play (the console
saved overlapping clips) are found by the constant offset between their kill times and deduplicated.
When the music holds fewer kills than given, streaks are kept first, then lone kills in order.

`--style` picks the look:

| style | into the kill | on the kill frame | after |
|---|---|---|---|
| `slowmo` (default) | slow motion (0.5x) | nothing | fast (1.5x) |
| `clean` | 1x, the cut before it is on a beat too | nothing | 1x |
| `punch` | 1x | 8% zoom punch, back out over 6 frames | 1x |
| `freeze` | rush in at 2x | white flash, kill frame held for one beat | 1x |

A streak (kills within `--streak-gap 6` seconds of each other: double, triple, ... kills) shares one
slot: the footage runs on through the streak, re-timed so every kill of it lands on its own beat;
a lone kill gets the solo slot. Other options: `--effect none|punch|flash` (override the style's
effect, e.g. slowmo with a punch), `--beats-per-kill 4` (one bar per kill; 2 for a faster cut),
`--kill-at 0.6` (where in the slot the kill lands), `--pattern 0.5:1.5,0.75:1.25` (lead:fast speed
factors, cycling per slot), `--start-beat N` or `--music-start SECONDS` (begin the montage that far into the track, e.g. at the build-up before the drop), `--bpm N` (force the tempo if the
tracker lands on a half or double tempo), `--streak-gap 0` (every kill solo), `--video` (override
the recording path stored in a single events file).
The beat tracker assumes a constant tempo, which suits most montage music: it takes the tempo from
the autocorrelation of the onset curve, then the exact tempo and phase whose rigid beat grid sits on
the strongest onsets. It deliberately does not snap beats to individual onsets (that jittered by up
to 0.1 s on a compressed track). To check the grid by ear, mix a click on every beat:

```sh
.venv/bin/python -c "
import sys, subprocess, numpy as np; sys.path.insert(0, '.')
from killclip import beatsync
m = 'track.mp3'; sr = beatsync.SR
y = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', m, '-vn', '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'], capture_output=True).stdout, np.float32)
t, bpm = beatsync.beats(m); c = np.zeros_like(y); n = int(0.03 * sr); tt = np.arange(n) / sr
for b in t: k = int(b * sr); c[k:k + n] += 0.9 * np.exp(-tt * 120) * np.sin(2 * np.pi * 1800 * tt) if k + n < len(c) else 0
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(sr), '-ac', '1', '-i', '-', 'clicks.mp3'], input=np.clip(0.6 * y + c, -1, 1).tobytes())
print(bpm)"
```

Kill instants are re-read from the source at its own frame rate so the banner's first frame is
what sits on the beat (inside a streak, the frame where the previous banner has been swapped out
and the new one appears).

## Logs

Every run prints progress on the console and writes a full debug log to
`logs/killclip-<timestamp>.log` (every KO onset, feed row counts, ffmpeg commands).
A warning is logged whenever the feed shows a new kill row with no KO banner, which
is how to spot kills the banner missed. Add `-v` for the debug detail on the console.

## Test

```sh
.venv/bin/python tests/test_pipeline.py    # builds a synthetic clip and checks detection + cutting
.venv/bin/python tools/check_cases.py      # short real cuts in videos/work/cases with known kill counts (~20 s)
```

Validate a full recording against the game's own numbers: the end-of-match scoreboard's
Final Hits column for your row should equal the kills detected in that match's time range.
