# killclip

**Find your kills in raw console gameplay and turn them into clips, editor timelines and beat-synced montages. Locally, for free.**

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue) ![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey) ![License: MIT](https://img.shields.io/badge/license-MIT-green)

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

- macOS or Linux. Encoding uses libx264 by default; `--encoder h264_videotoolbox` or
  `$KILLCLIP_ENCODER` picks another, and `killclip doctor` reports what this machine has
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
| `captions` | read the game's own on-screen subtitles into an SRT |
| `short` | compose a finished 9:16 short with a title and captions |
| `doctor` | check this machine has everything the tool needs, in one pasteable block |
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

## Games with no kill feed (GTA)

Marvel Rivals and Battlefield print the event on screen. GTA never does: its HUD shows *state* (a
wanted level, a mission banner), not events. So `--game gta` listens instead. An AudioSet sound
tagger scores every second for gunfire, explosions, crashes, sirens and screams, and the peaks
become the moments. Audio only, so no video is decoded: a 7-minute recording is read in 4 seconds,
an hour in well under a minute.

```sh
killclip --game gta detect session.webm --out events.json   # moments from the audio
killclip --game gta cut --events events.json --out clips    # one clip per moment
```

Scoring is **relative**, which is what makes it work. Raw tagger probabilities on game audio are
small (in one GTA recording gunfire never passed 0.27), so an absolute threshold finds nothing.
Each sound is measured against its own usual level in that recording, with a floor so a quiet
session cannot promote its loudest footstep. `sound_threshold` (default 0.3) is how strong a sound
must be to start a moment, and `sound_weights` says how much each kind means.

Needs PyTorch, which the core does not: `pip install 'killclip[sound]'`. The tagger is PANNs
MobileNetV1 (Kong et al., MIT); its weights (23 MB, Zenodo record 3987831, CC BY 4.0) and the
AudioSet label list download on first use.

## Finished vertical shorts

```sh
killclip --game gta captions clip.mp4                       # the game's own subtitles -> SRT
killclip --game gta short clip.mp4 --title "He said he could drive" \
    --panel-aspect 1.33 --out short.mp4                     # 1080x1920, ready to post
```

`short` composes the clip for Reels, TikTok or Shorts: the gameplay blurred and darkened as a
background, the clip itself centred, the title at the top and captions underneath, all placed clear
of the platform's own buttons (`--platform`). `--panel-aspect 1.33` crops the gameplay sides so it
fills more of the tall frame; leave it off to keep the whole 16:9 scene.

Captions come from the **game's own on-screen subtitles**, read with OCR, not from transcribing the
audio. Game dialogue sits under engine noise and music, and on a GTA clip Whisper produced "It's
been a lot gabbing on the shelf with no rusty" where the game's caption read "It's been a lot,
yeah, we got to chill, no Rusty". Set `caption_region` in the game's config to the strip it prints
dialogue in. Pass `--srt` to use your own file, or `--no-captions` for none.

## Encoding and decoding

Both run in software, and that is the fast path rather than a fallback. Measured on an M5 Pro, per 5
seconds of 4K for encoding and 30 seconds at the detector's own 5 fps for decoding:

| operation | hardware | software |
|---|---|---|
| encode 4K | `h264_videotoolbox` 40M, 4.30 s | `libx264 veryfast crf 20`, **2.32 s** |
| decode 4K VP9 | `-hwaccel videotoolbox`, 9.93 s | **3.68 s** |
| decode 1080p H.264 | `-hwaccel videotoolbox`, 6.01 s | **0.96 s** |

The chip has no VP9 decoder, and for H.264 moving frames out of the media engine into system memory
costs more than decoding them across every core. So `--encoder` / `$KILLCLIP_ENCODER` and
`$KILLCLIP_HWACCEL` exist for anyone who wants the hardware path back, and neither is the default.
Run `killclip doctor` to see what was chosen and why.

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
- Menu-driven command line with a URL as input
- Model-assisted verification and victim names (a local Qwen3-VL bake-off lives in `tools/`)

## License

MIT for the code. See `LICENSE`.

Bundled third-party assets, each under its own licence and shipped unmodified:

- **Anton** (titles) and **Liberation Sans** (captions), SIL Open Font License 1.1, licences in
  `killclip/assets/fonts/`.
- **AudioSet** class list, CC BY 4.0, Google.
- **PANNs** MobileNetV1 sound tagger: code adapted from Kong et al. (MIT), weights downloaded on first
  use from Zenodo record 3987831 under CC BY 4.0.
