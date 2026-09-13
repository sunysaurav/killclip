# killclip

**Find your kills in raw console gameplay and turn them into clips, editor timelines and beat-synced montages. Locally, for free.**

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue) ![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey) ![License: MIT](https://img.shields.io/badge/license-MIT-green)

Console recordings (PlayStation, Xbox) carry no game events, only pixels. killclip reads the HUD the way you do: it watches the kill banner and the kill feed, decides which rows are yours, and stamps each kill to the frame. From there it cuts clips, writes an EDL for your editor, and builds montages where every kill lands on a beat of your track.

No cloud, no account, no per-run cost. ffmpeg, OpenCV and a few kilobytes of templates.

## What it does

- **Detects kills** in Marvel Rivals and Battlefield 6 (Battle Royale and multiplayer HUDs), one decode pass per recording, about 3 minutes for a 12-minute 4K match.
- **Rejects the kill-cam**: rows with your name on the right are your deaths and are ignored.
- **Cuts clips** per kill moment, 9:16 versions for Shorts, and a CMX3600 EDL that lays the cuts on a timeline in DaVinci Resolve or Premiere.
- **Beat-synced montages**: kills on beats, streaks on consecutive beats, four looks (`slowmo`, `clean`, `punch`, `freeze`), kills pooled from several recordings with overlapping recordings deduplicated.
- **HDR-aware**: console recordings are 10-bit PQ; outputs keep the HDR look by default, or tone-map to SDR on request.
- **Per-game modules**: each game's recognition lives in one file; the shared pipeline never changes when a game is added.

## How a kill is found

| game | trigger | ownership |
|---|---|---|
| Marvel Rivals | the gold banner emblem, identical for KO, DOUBLE!, TRIPLE!, QUAD!, PENTA!, HEXA! | the newest kill-feed row with your name: name on the left is a kill, name on the right is your death (the kill-cam) |
| Battlefield 6, Battle Royale | the grey **KILL** box in the score panel, scored against a KILL CONFIRMED look-alike | the personal kill counter next to the skull icon, read as a tally |
| Battlefield 6, multiplayer | the kill feed itself | a row `> you  weapon  victim`, tracked by position: rows enter at the bottom and only move up, so a row no tracked row explains is a new kill |

Everything is template matching on small grayscale crops of the HUD, at 5 frames a second. Recordings larger than the templates (4K vs 1080p) are scanned at the calibration size. For beat sync each kill is then re-read at the recording's full frame rate so the beat lands on the banner's first frame.

Validated against the games' own numbers (end-of-match scoreboards): 90 of 93 kills across four Marvel Rivals matches with no false positives; 49 of 50 in a Battlefield multiplayer match.

## Requirements

- macOS with Apple silicon (encoding uses VideoToolbox; a software encoder for Linux and Windows is on the roadmap)
- `ffmpeg` and `tesseract` on the PATH (`brew install ffmpeg tesseract`)
- Python 3.11 or newer, or [`uv`](https://docs.astral.sh/uv/)

## Install

```sh
uv tool install git+https://github.com/sunysaurav/killclip     # or: pipx install git+https://github.com/sunysaurav/killclip
killclip --help
```

Configs, templates and logs live in `~/.killclip/` (or the folder named by `KILLCLIP_HOME`). Copy this repository's `configs/` and `calib/` there to start from the bundled games, then put your own in-game name in the config and cut your name template (see Calibration).

From a checkout, `bin/killclip` runs the same CLI from the local `.venv` and uses the checkout as its home.

## Quick start

```sh
killclip --game marvel-rivals detect match.webm               # -> events.json, events.csv
killclip cut --edl --out clips                                # one clip per moment + clips/kills.edl
killclip cut --vertical --out shorts                          # 9:16 centre-cropped versions
killclip beatsync --events events.json --music track.mp3 --style freeze --out montage.mp4
```

`--game` picks `configs/<game>.json` (`marvel-rivals`, `battlefield-6`, `battlefield-6-mp`); `KILLCLIP_GAME` and `KILLCLIP_PLAYER` set the game and name for a shell.

## Commands

| command | purpose |
|---|---|
| `probe` | resolution, frame rate, duration, HDR |
| `detect` | find kills, write `events.json` and `events.csv` |
| `cut` | one clip per moment; `--vertical`, `--edl`, `--pre`/`--post` windows, `--only` ids |
| `montage` | join clips with crossfades |
| `beatsync` | beat-synced montage from one or more events files |
| `frames`, `template`, `test` | calibration: dump frames with the regions drawn, cut a template, inspect one moment |

Global: `--grade none|natural|vivid` (colour, see below), `-v` for debug on the console. Every run writes a full log to `logs/`.

## Beat-synced montages

```sh
killclip beatsync --events events-a.json events-b.json --music track.mp3 --style punch --out montage.mp4
```

The tracker assumes a constant tempo, which suits montage music: tempo from the autocorrelation of the onset curve, then the exact tempo and phase whose rigid grid sits on the strongest onsets, with no per-beat snapping. Each kill gets a slot of `--beats-per-kill` beats and lands at `--kill-at` of the way through it.

| style | into the kill | on the kill frame | after |
|---|---|---|---|
| `slowmo` (default) | slow motion, 0.5x | | fast, 1.5x |
| `clean` | 1x, the cut before it on a beat too | | 1x |
| `punch` | 1x | 8% zoom punch, eased out over 6 frames | 1x |
| `freeze` | rush in at 2x | white flash, frame held one beat | 1x |

- **Streaks**: kills within `--streak-gap` seconds (default 6) share a slot and land on consecutive beats. `--streak-gap 0` makes every kill solo.
- **Several recordings**: pass all events files; recordings of the same play (a console saving overlapping clips) are found by the constant offset between their kill times and deduplicated. When the track is shorter than the kill list, streaks are kept first.
- **Placement**: `--music-start SECONDS` starts the montage at the build-up before a drop; `--bpm` forces the tempo if the tracker picks half or double; `--pattern 0.75:1.25` overrides a style's speeds; `--effect none|punch|flash` mixes looks.

## Colour

Console recordings are HDR (10-bit PQ, BT.2020). With the default `--grade none` every output keeps the pixels as recorded and carries the HDR tags, so macOS, iOS and YouTube show it the way the game looked. `--grade natural` tone-maps to SDR through a generated 3D LUT for players that cannot show HDR; `--grade vivid` adds saturation on top.

## Calibration and adding a game

Templates are cut from your own footage once per game and resolution.

```sh
killclip frames match.webm --at 123.4                  # frames around a kill, HUD regions drawn
killclip template match.webm --at 123.6 --box x0 y0 x1 y1 --out calib/<game>/name.png
killclip test match.webm --at 124.0                    # scores and rows at that moment
```

Boxes are in calibration-size pixels (1080p for the bundled games). The banner and KILL-box templates are universal; the name template is yours, so a new user cuts one.

A new game is one module, `killclip/games/<game>.py`, defining `DEFAULTS`, `TEMPLATE_KEYS`, `regions(cfg)` and a `Detector` with `frame(t, crops)`, `flush()`, `events` and `inspect(crops)`, plus `configs/<game>.json`. The contract is in `killclip/games/__init__.py`. An optional `make_refiner(cfg)` gives beat sync frame-exact kill instants.

## Project layout

```
killclip/          the pipeline: media, detect, feed, cut, beatsync, grade, cli
killclip/games/    one module per game
configs/           one JSON per game or HUD mode
calib/             templates cut from real frames
tools/             calibration harvesters, the case suite, OCR and VLM bake-off scripts
tests/             synthetic-clip pipeline test
```

## Tests

```sh
.venv/bin/python tests/test_pipeline.py    # synthetic clip: detection, cutting, montage, EDL
.venv/bin/python tools/check_cases.py      # short real cuts with known kill counts
```

To validate a whole match, compare the detected count with your row's Final Hits on the end-of-match scoreboard.

## Roadmap

- Automatic name-template calibration from a first recording
- Software encoder fallback for Linux and Windows
- Menu-driven command line with a URL as input
- Model-assisted verification and victim names (a local Qwen3-VL bake-off lives in `tools/`)

## License

MIT. See `LICENSE`.
