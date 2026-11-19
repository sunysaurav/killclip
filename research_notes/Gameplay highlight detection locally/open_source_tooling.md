# Open-Source Tooling and Models for a Local Gameplay Highlight-Detection Pipeline

**Method note for the report writer.** All star counts, licence IDs, last-push timestamps and archive flags below were read directly from the GitHub REST API on **2026-11-04**, and package versions/release dates from the PyPI JSON API on the same date. Where a figure comes from a blog post, README claim or search snippet instead, it is labelled as such. `pushed_at` is used as the last-activity proxy; it includes pushes to non-default branches, so it is an optimistic measure of "maintained". Licence IDs shown as `NOASSERTION` mean GitHub could not match the repo's LICENSE file to a standard SPDX identifier — treat every one of those as "must read the licence before shipping".

**Target machine for all hardware judgements:** Apple M5 Pro, 48 GB unified memory, macOS (Darwin 25.6), `ffmpeg 9.0.1` from Homebrew. Verified locally: the only hardware-acceleration method `ffmpeg` exposes on this box is `videotoolbox` (`ffmpeg -hwaccels`). There is no CUDA path on this machine, so anything CUDA-only is unusable, not merely slower.

---

## What open-source gameplay highlight/clipping projects exist? What signal do they use, do they work, are they maintained?

### Takeaway

The gameplay-specific highlight-detection niche is genuinely thin: GitHub searches across ten phrasings surface almost nothing with real traction, and the handful of projects with >100 stars are either Windows-only recorders, generic "long video → TikTok" shorts generators, or AGPL desktop apps. The projects that actually *work* reliably do not use computer vision at all — they read game telemetry (CS2 `.dem` demo files, War Thunder's local API, Segra's per-game kill/death hooks). Every CV/OCR-based gameplay clipper found is a sub-20-star hobby repo.

### Cited Findings

**Projects with meaningful traction (all metadata from GitHub API, 2026-11-04):**

- `Segergren/Segra` — 256 stars, **GPL-2.0**, last push **2026-11-01**. Open-source game recorder built on OBS (libobs). README: "Auto highlights from kill/death tracking in CS2, League, Dota 2, PUBG, Rocket League, Rust, Minecraft, RuneScape: Dragonwilds, War Thunder and GTA"; replay buffer, hotkey clipping, clip editor with waveform. Install instructions cover **Windows only**, plus "Linux support is in early alpha. It might not start at all… Please do not open GitHub issues for Linux problems yet." **No macOS build.** — [Segra README](https://github.com/Segergren/Segra)
- `divyaprakash0426/autoshorts` — 206 stars, **Apache-2.0**, last push **2026-11-01**. README: "Gaming/esports use action heuristics plus AI ranking; other types use AI-first selection"; "Flexible analysis: Gemini, including full-video deep analysis; OpenAI vision; or local heuristic selection without API analysis"; Whisper transcription, PyCaps captions, "GPU rendering". Showcase clips are gameplay footage. — [autoshorts README](https://github.com/divyaprakash0426/autoshorts)
- `Aseiel/VideoHighlighter` — 368 stars, **AGPL-3.0**, last push **2026-10-30**. Local desktop app (Electron-style, Windows/macOS/Linux builds in Releases). README: "it scores strong moments from scene, motion, audio, objects, actions and the transcript, shows you *why* each one scored on a signal timeline and in a report, then exports a highlight reel and the individual clips. Nothing is uploaded for analysis, and the basic pipeline needs no API key." Explicit use case: "A 4-hour Twitch or YouTube VOD → a few minutes of highlights. Crowd noise, your own reactions and scene changes all score." Has a "composition rules" engine for user-defined combination events, and local Whisper for transcripts. macOS install requires `xattr -dr com.apple.quarantine /Applications/VideoHighlighter.app` (not notarised). — [VideoHighlighter README](https://github.com/Aseiel/VideoHighlighter)
- `Anil-matcha/AI-Youtube-Shorts-Generator` — 5,754 stars, **MIT**, last push **2026-11-03**. Self-described "Open-source alternative to Opus Clip, Vidyo.ai, Klap & SubMagic" — generic long-form→shorts, not gameplay-aware. — [GitHub API](https://github.com/Anil-matcha/AI-Youtube-Shorts-Generator)
- `jipraks/yt-short-clipper` — 1,068 stars, **MIT**, last push **2026-09-20**. Described as a "**Windows desktop app**" for 9:16 clipping. — [GitHub API](https://github.com/jipraks/yt-short-clipper)
- `6v17/VideoSeek` — 106 stars, **AGPL-3.0**, last push **2026-11-01**. Local video-library search by "text or screenshot, with hard-subtitle OCR"; stack is "ONNX · Lance · FFmpeg"; exports MP4 / Jianying / NLE timelines. Badge and README state **Windows 10/11 only**. — [VideoSeek README](https://github.com/6v17/VideoSeek)

**Telemetry-based (not CV) gameplay clippers — the ones that demonstrably work:**

- `hkslover/cs2-highlight-tool` — 59 stars, **no licence file**, last push 2026-10-26. Go; CS2 demo import, segment selection, recording, concatenation (README is Chinese). — [GitHub API](https://github.com/hkslover/cs2-highlight-tool)
- `zek/replay-master` — 30 stars, **GPL-3.0**, last push **2024-04-14** (abandoned). Node.js, auto-records CS2 demos. — [GitHub API](https://github.com/zek/replay-master)
- `Arad119/Fragfinder-GUI` — 16 stars, **GPL-3.0**, last push 2026-03-24. "Generate highlight timestamps and filter out specific player highlights" from demos. — [GitHub API](https://github.com/Arad119/Fragfinder-GUI)
- `Keanoski/CS2-Highlight-Automator-for-OBS` — 8 stars, **MIT**, last push 2025-09-19. C#, "Automated CS2 Demo Highlights with OBS CLI". — [GitHub API](https://github.com/Keanoski/CS2-Highlight-Automator-for-OBS)
- `dawsoncarsoulle-lab/wt-clipper` — 4 stars, **MIT**, last push 2026-08-31. Rust; "uses War Thunder's local [localhost API]" — i.e. game telemetry, Linux-native. — [GitHub API](https://github.com/dawsoncarsoulle-lab/wt-clipper)
- `Rovniy/cs2-highlights-maker` — 6 stars, no licence, last push 2026-06-12. "feed it a match `.dem` file, get a `*-highlights`". — [GitHub API](https://github.com/Rovniy/cs2-highlights-maker)

**CV/OCR-based gameplay clippers — all tiny, mostly unlicensed:**

- `bendawg2010/Auto-clipper` — 11 stars, **MIT**, last push 2026-04-19. "Auto-find highlights in your Twitch/YouTube VODs — YOLO object detection, pixel analysis". The largest CV-based one found. — [GitHub API](https://github.com/bendawg2010/Auto-clipper)
- `Vladshmalii/highlight-detector` — **0 stars**, no licence, last push 2025-10-14. "Automated highlight detection for CS2 and Dota 2 gameplay videos using computer vision, OCR". — [GitHub API](https://github.com/Vladshmalii/highlight-detector)
- `DavoDC/RivalsVidMaker` — **0 stars**, **MIT**, last push 2026-09-29. "Stream copy muxing for **Marvel Rivals** YouTube compilations. OCR multi-kill detection, automated…" — the only Marvel Rivals OCR repo surfaced by any query. — [GitHub API](https://github.com/DavoDC/RivalsVidMaker)
- `reuke1111/local-shorts-ai` — 3 stars, no licence, last push 2026-07-09. "Fully offline AI pipeline that auto-detects highlight clips from gameplay footage". — [GitHub API](https://github.com/reuke1111/local-shorts-ai)
- `mahdi-alkak-1/HighlightIQ` — 4 stars, **MIT**, last push 2026-01-31. "Automated gameplay highlight detection and clipping with review and YouTube publishing" (TypeScript). — [GitHub API](https://github.com/mahdi-alkak-1/HighlightIQ)
- `1Mochiyuki/VOD-Insights` — **0 stars**, no licence, last push 2026-02-24. "killfeed detection, keyword search, event analysis" — description only, no code of substance. — [GitHub API](https://github.com/1Mochiyuki/VOD-Insights)
- `Manav-S2/cs2-highlight-studio` and `Manav-S2/cs2-highlight-automation` — **0 stars** each, `NOASSERTION`, last push 2026-09-02. "Computer-vision and LLM application that turns live CS2 esports broadcasts into edited vertical…" — [GitHub API](https://github.com/Manav-S2/cs2-highlight-studio)
- `SWTube/LoL-eSports-Highlight-Extractor` — 17 stars, **GPL-3.0**, last push **2023-09-02** (abandoned). — [GitHub API](https://github.com/SWTube/LoL-eSports-Highlight-Extractor)
- Searching the exact phrase **"valorant clip detector" returned zero repositories**. — (GitHub search API, `search/repositories`, 2026-11-04)

**Twitch VOD–specific:**

- `xurei/twitch-highlights-logger` — 34 stars, **GPL-3.0**, last push **2025-05-13**. "Find interesting moments on a Twitch VOD" — chat-velocity signal. — [GitHub API](https://github.com/xurei/twitch-highlights-logger)
- `LuisSotelo/vod-to-viral` — 12 stars, **no licence**, last push 2026-06-15. — [GitHub API](https://github.com/LuisSotelo/vod-to-viral)
- `ros-dorian/TwitchHack` — 4 stars, no licence, last push **2019-11-17**. "Highlight clip detector for twitch vods" — dead. — [GitHub API](https://github.com/ros-dorian/TwitchHack)

**OCR engines (relevant because "kill detection OCR" is the obvious killfeed signal):**

| Repo | Stars | Licence | Last push | Apple Silicon notes |
|---|---|---|---|---|
| `tesseract-ocr/tesseract` | 77,329 | Apache-2.0 | 2026-11-02 | CPU, `brew install tesseract`, well-proven |
| `PaddlePaddle/PaddleOCR` | 92,236 | Apache-2.0 | 2026-09-16 | PaddlePaddle runtime on macOS ARM is historically awkward; CPU |
| `RapidAI/RapidOCR` | 8,436 | Apache-2.0 | **2026-11-04** | ONNX Runtime — the cleanest cross-platform CPU path for PaddleOCR-family models |
| `JaidedAI/EasyOCR` | 30,123 | Apache-2.0 | 2025-12-05 | PyTorch; MPS or CPU |
| `straussmaximilian/ocrmac` | 552 | MIT | 2026-01-08 | **Python wrapper around Apple's native Vision framework** — macOS-only by design, uses the OS OCR engine, no model download |
| `mindee/doctr` | 6,412 | Apache-2.0 | 2026-11-03 | PyTorch/TF |

— all rows from the [GitHub REST API](https://docs.github.com/rest), 2026-11-04.

- `mlx-community/PaddleOCR-VL-1.5-4bit` exists on Hugging Face with 2,176 downloads in the last 30 days (also `PaddleOCR-VL-1.6-4bit`, 1,450; `PaddleOCR-VL-1.5-bf16`, 918) — i.e. there is a native MLX OCR-VLM option. — [HF models API, author=mlx-community](https://huggingface.co/mlx-community)

### Inferences

- There is **no maintained, macOS-native, open-source gameplay highlight detector** to adopt wholesale. The realistic build options are: (a) assemble from the generic components in the sections below, or (b) fork `Aseiel/VideoHighlighter`, which is the closest architectural match (multi-signal scoring + explainable timeline + local Whisper + macOS build) — but it is **AGPL-3.0**, which means any derivative distributed to users must also be AGPL.
- The strong correlation between "uses game telemetry" and "actually ships working clips" is the single most useful design signal in this space. Marvel Rivals has no public demo-file format, so a vision/OCR approach is forced — which is precisely why nothing good exists for it (the one Marvel Rivals OCR repo has 0 stars).
- For a killfeed/banner OCR on macOS, `ocrmac` (Apple Vision) is the lowest-friction and probably fastest option — no model weights, no Python ML runtime, hardware-accelerated by the OS — at the cost of macOS lock-in. `RapidOCR` is the portable fallback.

### Gaps

- I could not verify whether `Segra`'s kill/death tracking is log-parsing, memory-reading, or game-API based, nor whether any of it is portable off Windows; the README does not say and I did not read the C# source.
- No independent accuracy evaluation exists for *any* of these gameplay clippers. None of them publishes precision/recall against a ground-truth scoreboard. "Does it work?" is therefore answerable only from stars/activity/issue volume, not measurement.
- `DavoDC/RivalsVidMaker` (Marvel Rivals, MIT) is worth a direct code read by the implementer — I did not fetch its source, only its description, so I cannot say what its OCR approach or accuracy is.

---

## What open-source tools detect audio events (gunshots, explosions, sirens, crashes) in long audio files?

### Takeaway

The pretrained-weights situation is good and the inference-tooling situation is poor: AudioSet-trained taggers covering gunshot/explosion/siren classes are available under permissive licences and run fine on CPU/MPS, but almost every "ready-made CLI" is either a research repo frozen in 2024 or needs 30–80 lines of glue to turn frame-level logits into timestamped events. The best-maintained path is **AST or CLAP via `huggingface/transformers`** (pushed 2026-11-04), not the original authors' repos.

### Cited Findings

**AudioSet taggers — pretrained, 527/521-class ontology (includes Gunshot/gunfire, Explosion, Siren, Machine gun, Artillery fire):**

- **AST (Audio Spectrogram Transformer).** Original repo `YuanGongND/ast` — 1,485 stars, **BSD-3-Clause**, last push **2023-05-21** (effectively frozen). The usable artifact is the checkpoint: `MIT/ast-finetuned-audioset-10-10-0.4593` with **1,729,183 downloads in the last 30 days**, `pipeline_tag: audio-classification` — by far the most-downloaded audio event model on the Hub. Variants: `MIT/ast-finetuned-audioset-14-14-0.443` (34,892), `-16-16-0.442` (936), `-12-12-0.447` (759). ONNX ports exist: `Xenova/ast-finetuned-audioset-10-10-0.4593` (25,829) and `onnx-community/ast-finetuned-audioset-10-10-0.4593-ONNX` (2,088). — [GitHub API](https://github.com/YuanGongND/ast); [HF models API](https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593)
- **PANNs.** `qiuqiangkong/audioset_tagging_cnn` — 1,791 stars, **MIT**, last push **2024-07-25**, **61 open issues**. The inference wrapper `qiuqiangkong/panns_inference` — 275 stars, **MIT**, last push **2024-03-05**, 17 open issues; PyPI `panns-inference` is at **v0.1.1 released 2023-03-26** and declares **no licence metadata**. Both are stale but functional; PANNs is the canonical "sound event detection + tagging" baseline and the wrapper's API returns both clipwise tags and framewise segment-level output. — [GitHub API](https://github.com/qiuqiangkong/panns_inference); [PyPI](https://pypi.org/project/panns-inference/)
- **EfficientAT — the best-value modern option.** `fschmid56/EfficientAT` — 374 stars, **MIT**, last push **2024-11-20**. README: knowledge-distilled MobileNetV3/DyMN CNNs trained on AudioSet that "achieve **competitive audio tagging performance on resource constrained platforms**" and "extract high-quality general purpose audio representations"; the stated goal is a codebase with "similar capabilities as the PANNs codebase" but with "Pre-trained models of **lower computational and parameter complexity**" and "**Higher performance** due to Knowledge Distillation from Transformers". Pre-trained models ship via GitHub Releases and auto-download. Caveat in the README: "make sure you have **FFmpeg <v4.4** installed" — the local machine has ffmpeg 9.0.1, so this constraint needs checking. Stated unfinished milestones include "Wrap this repository in an installable python package" — i.e. **not pip-installable**. — [EfficientAT README](https://github.com/fschmid56/EfficientAT)
- **YAMNet.** Lives in `tensorflow/models/research/audioset/yamnet`. README: "YAMNet is a pretrained deep net that predicts **521 audio event classes** based on the AudioSet-YouTube corpus, and employing the Mobilenet_v1 depthwise-separable convolution architecture." Critical warning in the README: "**YAMNet currently relies on Keras 2 and is incompatible with Keras 3** (the default as of TF 2.16)." Weights are a direct download (`https://storage.googleapis.com/audioset/yamnet.h5`), and `inference.py` "will report the top-5 highest-scoring classes averaged over all the frames", with `PATCH_HOP_SECONDS` in `params.py` as the knob for temporal resolution. — [YAMNet README](https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/README.md)
- Third-party YAMNet ports on the Hub are all low-traffic: `thelou1s/yamnet` (982 downloads/30d), `qualcomm/YamNet` (294), `niobures/YAMNet` (271), `sami-hatna66/yamnet` (PyTorch reimplementation, 5 GitHub stars). — [HF models API](https://huggingface.co/models?search=yamnet)
- **BEATs.** Lives inside `microsoft/unilm` — 22,237 stars, **MIT**, last push **2026-09-21**, but **690 open issues** across the whole monorepo. There is **no official BEATs checkpoint on the Hugging Face Hub**: a search for "BEATs" returns only community artifacts, the most relevant being `espnet/BEATs-AS20K` with **13 downloads in 30 days** and `slseanwu/beats-conformer-bart-audio-captioner` (66). — [GitHub API](https://github.com/microsoft/unilm); [HF models API](https://huggingface.co/models?search=BEATs)
- **PaSST.** `kkoutini/PaSST` — 392 stars, **Apache-2.0**, last push **2024-01-12**. — [GitHub API](https://github.com/kkoutini/PaSST)
- **ATST-SED** — `Audio-WestlakeU/ATST-SED`, 174 stars, **MIT**, last push **2026-06-08**. Fine-tunes a pretrained ATST for *sound event detection* specifically (frame-level onsets/offsets, not clip tagging) — the most recently maintained true SED repo found. — [GitHub API](https://github.com/Audio-WestlakeU/ATST-SED)

**CLAP — text-queried audio retrieval ("find explosions"):**

- `LAION-AI/CLAP` — 2,324 stars, **CC0-1.0**, last push **2025-05-15**, 68 open issues. PyPI `laion-clap` **v1.1.7 released 2025-05-04**, licence CC0-1.0. — [GitHub API](https://github.com/LAION-AI/CLAP); [PyPI](https://pypi.org/project/laion-clap/)
- Hub checkpoints: `laion/clap-htsat-fused` with **6,138,039 downloads in 30 days** (`pipeline_tag: audio-classification`) and `laion/clap-htsat-unfused` with **867,745** (`feature-extraction`). An ONNX port exists (`Xenova/clap-htsat-unfused`, 8,479) and an ExecuTorch build (`mlboydaisuke/CLAP-HTSAT-fused-ExecuTorch`, 136, `zero-shot-classification`). — [HF models API](https://huggingface.co/laion/clap-htsat-fused)
- Microsoft's CLAP: PyPI `msclap` **v1.3.4 released 2025-05-23, MIT**. — [PyPI](https://pypi.org/project/msclap/)
- CLAP is exposed through `transformers` as `ClapModel`/`ClapProcessor`, and `huggingface/transformers` itself is 168,521 stars, **Apache-2.0**, last push **2026-11-04** — i.e. the maintained delivery vehicle, unlike the research repos. — [GitHub API](https://github.com/huggingface/transformers)

**General audio toolkits / CLIs:**

- `amsehili/auditok` — 862 stars, **MIT**, last push **2026-07-28**, **2 open issues**. A genuine CLI for *audio activity detection* (energy-based region splitting). Not event classification, but the right tool for cheaply segmenting an hour of audio into candidate regions before running a classifier. — [GitHub API](https://github.com/amsehili/auditok)
- `tyiannak/pyAudioAnalysis` — 6,272 stars, **Apache-2.0**, last push 2026-10-09, but **204 open issues**. Classic feature extraction + classification + segmentation library. — [GitHub API](https://github.com/tyiannak/pyAudioAnalysis)
- `MTG/essentia` — 3,793 stars, **AGPL-3.0**, last push 2026-10-22, 447 open issues. Powerful C++/Python audio analysis, and it bundles some AudioSet classifier models — but **AGPL-3.0 is a shipping hazard**. — [GitHub API](https://github.com/MTG/essentia)
- `libAudioFlux/audioFlux` — 3,382 stars, **MIT**, last push 2026-03-06. Feature extraction only (spectral/mel/CQT), no event models. — [GitHub API](https://github.com/libAudioFlux/audioFlux)
- `ffmpeg` on this machine provides `silencedetect`, `astats` and `ebur128` filters (verified via `ffmpeg -filters`) — zero-dependency loudness/silence gating for a first-pass over an hour of audio. — (local `ffmpeg 9.0.1` verification)

**Gunshot-specific repos — all unusable:**
`gabemagee/gunshot_detection` (65 stars, **no licence**, last push 2024-07-30), `hasnainnaeem/Gunshot-Detection-in-Audio` (23, no licence, **2020-02-16**), `mariamkhmahran/gunshot-detection-system` (15, no licence, 2023-07-18), `pcprince/audiomoth-gunshot-detection` (3, MIT, 2021-05-04 — AudioMoth firmware, not a library). — [GitHub search API](https://github.com/search?q=gunshot+detection+audio&type=repositories)

### Inferences

- For "find the explosions/gunfire in this hour of game audio", the two sane 2026 paths are: **(1)** `transformers` + `MIT/ast-finetuned-audioset-10-10-0.4593` sliding a 10s window and thresholding the Gunshot/Explosion logits, or **(2)** `transformers` + `laion/clap-htsat-fused` with text queries, which lets the user type the event they want rather than being limited to the 527 AudioSet labels. Option 2 is the better fit for an open-ended "highlight" notion; option 1 is more accurate on the specific classes it knows.
- EfficientAT is the right choice if throughput matters (MobileNetV3-class compute on an hour of audio is trivial on an M5 Pro), but the lack of a pip package and the `FFmpeg <v4.4` note mean vendoring the repo and handling audio decode yourself.
- All of these are PyTorch or TF models of ≤100M parameters; **none of them has any memory or hardware concern on 48 GB**, and all run acceptably on CPU alone. There is no CUDA-only blocker anywhere in this category. The constraint is engineering glue, not hardware.
- Game audio is adversarial for AudioSet models in a way nobody has measured: music beds, voice chat, and stylised weapon sound design are all out of distribution relative to YouTube clips. Expect to calibrate thresholds on actual footage rather than trusting published mAP.

### Gaps

- **No published accuracy figures for any AudioSet tagger on video-game audio specifically.** I found no benchmark, paper or issue thread evaluating gunshot/explosion detection on gameplay (as opposed to real-world) recordings. This is a real unknown for the pipeline.
- No ready-made CLI exists that goes from `input.wav` to a list of timestamped, labelled sound events using a modern model. `auditok` does segmentation without labels; PANNs/AST do labels without a CLI. The report should state plainly that this glue must be written.
- I did not find official Microsoft BEATs weights on Hugging Face. Whether the `unilm` repo's download links still resolve, and under what terms, is unverified.

---

## What local speech-to-text options are strongest on Apple Silicon?

### Takeaway

On Apple Silicon the ranking is not the same as on NVIDIA: **`faster-whisper` loses badly on a Mac** because CTranslate2 has no Metal backend and falls back to CPU, while **`mlx-whisper` and `whisper.cpp` (Metal + Core ML/ANE)** are the two real contenders, with one careful independent benchmark putting `mlx-whisper` at **2.03× faster than `whisper.cpp`** on the same long file with `large-v3-turbo`. The main maintenance worry is that `mlx-whisper` itself is drifting: last PyPI release **2025-08-29**.

### Cited Findings

**Repo/package health (GitHub + PyPI APIs, 2026-11-04):**

| Tool | Stars | Licence | Last push | PyPI version / date |
|---|---|---|---|---|
| `ggml-org/whisper.cpp` | **54,905** | **MIT** | **2026-11-03** | n/a (C++; 362 open issues) |
| `SYSTRAN/faster-whisper` | 26,465 | **MIT** | **2026-11-02** | `faster-whisper` 1.2.1, **2025-10-31** (only 19 open issues) |
| `m-bain/whisperX` | 25,082 | **BSD-2-Clause** | 2026-10-22 | `whisperx` 3.8.6, **2026-05-25** (**217 open issues**) |
| `openai/whisper` | 111,914 | **MIT** | 2026-08-31 | `openai-whisper` 20250625, 2025-06-26 |
| `ml-explore/mlx-examples` (hosts `mlx-whisper`) | 9,050 | **MIT** | **2026-04-06** | `mlx-whisper` 0.4.3, **2025-08-29**, MIT (**185 open issues**) |
| `ml-explore/mlx` (the framework) | 29,051 | **MIT** | **2026-11-03** | — |
| `argmaxinc/argmax-oss-swift` (WhisperKit; repo renamed from `argmaxinc/WhisperKit`) | 6,443 | **MIT** | 2026-10-27 | Swift package (144 open issues) |
| `FluidInference/FluidAudio` | 3,257 | **Apache-2.0** | 2026-11-02 | Swift/CoreML |
| `sbryngelson/ANEForge` | 68 | **MIT** | **2026-11-02** | "Python runtime for the Apple Neural Engine" |
| `jianfch/stable-ts` | 2,280 | MIT | 2026-05-30 | **ARCHIVED — read-only, do not build on it** |
| `mustafaaljadery/lightning-whisper-mlx` | 958 | **NO LICENCE FILE** | **2024-05-08** | unmaintained; unshippable as-is |
| `pyannote/pyannote-audio` (diarization) | 10,757 | **MIT** | **2026-11-03** | — |

— [GitHub REST API](https://docs.github.com/rest); [PyPI JSON API](https://pypi.org/)

**Measured speeds:**

- **The one clean head-to-head on a long file.** Bill Mill's January 2026 rerun, using `hyperfine` over 10 runs on `mlk_ihaveadream_long.wav` with matched turbo models (`mlx-community/whisper-large-v3-turbo` vs `ggml-large-v3-turbo.bin`): `whisper.cpp` **26.704 s ± 0.625 s**, `mlx_whisper` **13.135 s ± 0.280 s**, reported as "**2.03 ± 0.06 times faster**". **The article does not state which Mac or chip was used**, which limits how far this generalises. — [llimllib notes, Jan 2026](https://notes.billmill.org/dev_blog/2026/01/updated_my_mlx_whisper_vs._whisper.cpp_benchmark.html)
- An earlier run by the same author measured mlx-whisper at **1.78× faster** than whisper.cpp, so the gap has widened with turbo models. — [llimllib notes](https://notes.billmill.org/link_blog/2024/08/mlx-whisper.html)
- **`anvanvan/mac-whisper-speedtest`** (49 stars, **MIT**, last push 2025-08-04) publishes a ranked table from a **MacBook Pro M4, 24 GB**, `large`-class models. ⚠️ **These are single-short-utterance latencies** (the test phrase is "Which is the fastest transcription on my Mac?"), **not throughput on an hour of audio** — do not present them as hourly figures. Ordering: `fluidaudio-coreml` (Parakeet TDT 0.6B v2 CoreML) **0.1935 s**; `parakeet-mlx` **0.4995 s**; `mlx-whisper` (large-v3-turbo, no quant) **1.0230 s**; `insanely-fast-whisper` (mps, batch 12, 4-bit) **1.1324 s**; `whisper.cpp` (large-v3-turbo-q5_0, **coreml=True**, 4 threads) **1.2293 s**; `lightning-whisper-mlx` **1.8160 s**; `whisperkit` (large-v3) **2.2190 s**; `whisper-mps` **5.3722 s**; and **`faster-whisper` last at 6.9613 s** with parameters recorded as "`model=large-v3-turbo`, **`device=cpu`**, `compute_type=int8`, beam_size=1, cpu_threads=12". — [mac-whisper-speedtest README](https://github.com/anvanvan/mac-whisper-speedtest)
- The same README claims FluidAudio's CoreML Parakeet achieves "**real-time streaming ASR with ~110× RTF on M4 Pro**" — a secondhand claim about a third-party project, not a measurement in that repo's table. — [mac-whisper-speedtest README](https://github.com/anvanvan/mac-whisper-speedtest)
- **whisper.cpp's own Apple Silicon claims**, from its README: "Apple Silicon first-class citizen - optimized via ARM NEON, Accelerate framework, Metal and Core ML"; "On Apple Silicon, the inference runs fully on the GPU via Metal"; and for Core ML, "the Encoder inference can be executed on the Apple Neural Engine (ANE) via Core ML. This can result in significant speed-up - **more than x3 faster compared with CPU-only execution**". Enabled with `cmake -B build -DWHISPER_COREML=1` after `./models/generate-coreml-model.sh <model>`. Warning in the README: "The first run on a device is slow, since the ANE service compiles the Core ML model to some device-specific format." — [whisper.cpp README](https://github.com/ggml-org/whisper.cpp)
- **New in whisper.cpp: ANEForge.** README: "On Apple Silicon, the Encoder can also run on the Apple Neural Engine via ANEForge, which dispatches to the ANE directly instead of through Core ML. It is about **2× faster than the Core ML encoder from `tiny` to `medium`**." Used via `export ANEFORGE_ENCODER=/tmp/whisper-base-encoder` after exporting a bundle, and the bundle is "tied to the machine and OS build that produced it". — [whisper.cpp README](https://github.com/ggml-org/whisper.cpp); [ANEForge](https://github.com/sbryngelson/ANEForge)
- **Long-audio scaling concern, with a caveat.** whisper.cpp issue #3682 ("Performance Question: whisper.cpp vs faster-whisper scaling on longer audio", opened 2026-02-26, now **closed**) reports that on 31 s of audio, `faster-whisper (base)` took **5.07 s** while `whisper.cpp (base)` took **49.15 s** — "9.7× SLOWER" — whereas on 10.6 s they were within 2% of each other. ⚠️ **This was measured on an Intel N97, 4 cores, no GPU, Ubuntu 24.04** — it is *not* an Apple Silicon result and the issue was closed, strongly suggesting a configuration cause. Flagged only because it is the kind of nonlinearity to watch for when moving from 30-second test clips to hour-long VODs. — [whisper.cpp issue #3682](https://github.com/ggml-org/whisper.cpp/issues/3682)
- MLX Whisper weights are well-stocked on the Hub: `mlx-community/whisper-large-v3-turbo` **299,486 downloads/30d**, `whisper-small-mlx` 134,808, `whisper-large-v3-mlx` 86,411, `whisper-large-v3-turbo-q4` 16,776. — [HF models API, author=mlx-community](https://huggingface.co/mlx-community)
- **WhisperX capability set** (what you'd use it for rather than raw speed): forced alignment to word level plus speaker diarization via `pyannote-audio`. Licence **BSD-2-Clause**, last push 2026-10-22, but **217 open issues** against 25,082 stars. — [GitHub API](https://github.com/m-bain/whisperX)

### Inferences

- **`faster-whisper` is the wrong default on this machine.** CTranslate2 exposes no Metal/MPS backend, so the recorded `device=cpu, compute_type=int8` in the Mac benchmark is not a misconfiguration — it is the only option. That makes it roughly **7× slower than mlx-whisper** on the same hardware. This matters because `faster-whisper` is the most-recommended Whisper backend in general-purpose tutorials, and **WhisperX sits on top of it**, inheriting the CPU-only limitation on Mac.
- Therefore: if you want word-level alignment + diarization (WhisperX), budget CPU-bound transcription time, or decouple the stages — transcribe with `mlx-whisper`/`whisper.cpp` and run alignment/diarization separately with `pyannote-audio` (MIT, pushed 2026-11-03, runs on MPS/CPU).
- Scaling the one clean long-file benchmark: 2.03× in mlx-whisper's favour with `large-v3-turbo` is the best-supported number available. I will not convert it to "minutes per hour of audio" because the source does not state the audio duration or the chip — any such figure would be fabricated.
- For a highlight pipeline, **Parakeet TDT via FluidAudio (CoreML, Apache-2.0) or `parakeet-mlx` deserves a serious look**: it is 2–5× faster than even mlx-whisper in the Mac latency table, and for the narrow task of "did the player say something excited" you do not need Whisper-large quality. The trade-off is English-only and a different (non-Whisper) ecosystem.
- `whisper.cpp` remains the better choice if you want a single static binary, quantised models (q5_0 etc.), no Python, and the ANE path; `mlx-whisper` is better if you are already in Python and want peak speed. The deciding factor is probably **maintenance direction**: whisper.cpp pushed 2026-11-03 vs `mlx-examples` pushed 2026-04-06 and `mlx-whisper` unreleased since 2025-08-29.

### Gaps

- **No published, chip-identified, hour-of-audio throughput number for any Whisper implementation on an M-series Mac was found.** The two candidate sources are an SEO-styled site (`promptquorum.com`) whose own summary described its M4 Max figures — "60× real-time for Tiny, 44× for Base, 34× for Small, 16× for Medium via whisper.cpp with Metal" — as "historical reference points"; I could not trace those numbers to a primary benchmark and **recommend the report not cite them**. The honest answer is: benchmark locally on the M5 Pro with `hyperfine`, which takes minutes.
- No M5-generation Whisper benchmarks exist publicly at all (the M5 Pro is newer than every benchmark found). The ANE and GPU both changed generation, so M4 numbers are a floor, not a prediction.
- Whether `mlx-whisper` is still actively maintained is genuinely ambiguous: the parent `mlx` framework is extremely active (pushed 2026-11-03) but `mlx-examples`, where `whisper` lives, has been quiet since 2026-04-06 with 185 open issues. I found no deprecation notice or migration announcement.

---

## What local video-language models can describe or temporally ground events in video, and which have Apple Silicon / MLX builds?

### Takeaway

This is the weakest link in the whole pipeline on Apple Silicon. Video-capable VLMs with MLX support exist, but **`mlx-vlm` lists video chat for Qwen2-VL and Qwen2.5-VL — not Qwen3-VL**, so the strongest open video model (Qwen3-VL, with explicit timestamp-grounding training) has MLX *image* builds on the Hub but no documented MLX *video* path. Dedicated temporal-grounding models (QVHighlights lineage) are all 2024-era research code, and the only maintained wrapper around them is LINE's `lighthouse`.

### Cited Findings

**Video LLM repos (GitHub API, 2026-11-04):**

| Repo | Stars | Licence | Last push | Status |
|---|---|---|---|---|
| `QwenLM/Qwen3-VL` | 20,164 | **Apache-2.0** | **2026-01-30** | 441 open issues; repo quiet for ~9 months |
| `QwenLM/Qwen3-VL-Embedding` | 1,424 | **Apache-2.0** | 2026-06-23 | retrieval embeddings |
| `OpenGVLab/InternVL` | 10,174 | **MIT** | **2025-09-22** | 319 open issues; stale >1 yr |
| `LLaVA-VL/LLaVA-NeXT` | 4,735 | **Apache-2.0** | 2026-06-15 | **355 open issues** |
| `PKU-YuanGroup/Video-LLaVA` | 3,510 | Apache-2.0 | **2024-12-03** | abandoned |
| `DAMO-NLP-SG/Video-LLaMA` | 3,139 | BSD-3-Clause | **2024-06-04** | **abandoned — do not start here** |
| `DAMO-NLP-SG/VideoLLaMA3` | 1,190 | Apache-2.0 | **2025-08-14** | successor, also going quiet |

- **Qwen3-VL capabilities** (from the repo README): sizes **2B, 4B, 8B, 32B, 30B-A3B (MoE), 235B-A22B (MoE)**, each in Instruct and Thinking editions; "native **256K context, expandable to 1M**"; handles "hours-long video"; the architecture includes "**Text–Timestamp Alignment**" for "**precise, timestamp-grounded event localization** for stronger video temporal modeling"; default video frame sampling is `fps=2`. Deployment guidance covers "Hugging Face Transformers, vLLM, SGLang, and Docker" and contains **no mention of MLX, Apple Silicon, llama.cpp, or GGUF**. — [Qwen3-VL README](https://github.com/QwenLM/Qwen3-VL)
- **`mlx-vlm` is the Apple Silicon host for video VLMs.** Note the repo moved: `Blaizzy/mlx-vlm` now redirects to **`Neywa-Labs/mlx-vlm`** — 5,798 stars, **MIT**, last push **2026-11-03**, **254 open issues**. PyPI `mlx-vlm` **v0.7.11 released 2026-10-28, MIT** — actively released. Tagline: "Run and fine-tune multimodal models on Apple Silicon. Text, images, video, and audio in — any out. Built on MLX." — [GitHub API](https://github.com/Neywa-Labs/mlx-vlm); [PyPI](https://pypi.org/project/mlx-vlm/)
- **The critical limitation, quoted verbatim from the `mlx-vlm` README:** "The following models support video chat: 1. Qwen2-VL 2. Qwen2.5-VL 3. Idefics3 4. LLaVA 5. MiniMax M3 / M3.1 Flash 6. LLaVA-OneVision 7. Mage-VL 8. Muse Spark Open" followed by "With more coming soon." **Qwen3-VL and InternVL are absent from that list.** Working CLI invocation: `mlx_vlm.generate --model mlx-community/Qwen2-VL-2B-Instruct-4bit --max-tokens 100 --prompt "Describe this video" --video path/to/video.mp4 --fps 1.0`; in Python, pass `video=` to `apply_chat_template` and the same path to `generate`. — [mlx-vlm README](https://github.com/Neywa-Labs/mlx-vlm)
- **MLX weights that exist on the Hub** (downloads = last 30 days): `mlx-community/Qwen2.5-VL-7B-Instruct-4bit` **23,775**; `Qwen2-VL-2B-Instruct-4bit` **23,632**; `Qwen3-VL-4B-Instruct-4bit` **18,338**; `Qwen3-VL-2B-Instruct-4bit` 7,189; `Qwen3-VL-8B-Instruct-4bit` 6,080; `Qwen2.5-VL-3B-Instruct-4bit` 5,166; `Qwen2.5-VL-7B-Instruct-8bit` 2,501; `Qwen2.5-VL-72B-Instruct-4bit` 1,760; `Qwen3-VL-30B-A3B-Instruct-4bit` 1,538; `Qwen3-VL-32B-Instruct-4bit` 681; `Qwen3-VL-8B-Instruct-8bit` 746; `Qwen3-VL-Embedding-2B-8bit` 974; `Kimi-VL-A3B-Thinking-4bit` 858; plus the LFM2/LFM2.5-VL small models (1.6B-4bit at 5,622). **No `mlx-community` InternVL build appeared in the top 25 by downloads.** — [HF models API, author=mlx-community, search=VL](https://huggingface.co/mlx-community)
- **`mlx-vlm` performance features** that matter for hour-long video: the README documents "Vision Feature Caching", "TurboQuant KV Cache", speculative decoding with drafter models, "Distributed Inference", and fine-tuning. — [mlx-vlm README](https://github.com/Neywa-Labs/mlx-vlm)

**Temporal grounding / moment retrieval (the QVHighlights lineage):**

- **`line/lighthouse` — the one to actually use.** 272 stars, **Apache-2.0**, last push **2026-11-01**, from LINE. README: "a user-friendly library for reproducible video moment retrieval and highlight detection (MR-HD). It supports **seven models, four features (video and audio features), and six datasets**… we prepare an inference API and Gradio demo". **Crucially: "Inference API (Available for both CPU/GPU mode)"** and "Note that the inference API is available for CPU environments." Published at EMNLP 2024 (demo track), with ICASSP 2025 and ICASSP 2026 follow-ups; v1.2 released 2025-11-20. It also covers **audio moment retrieval** — find moments in an audio track from a text query. The API returns exactly the shape a highlight pipeline wants: `pred_relevant_windows: [[start, end, score], ...]` and `pred_saliency_scores: [score, ...]`. Example output shows windows like `[117.1296, 149.4698, 0.9993]`. Install: `pip install 'git+https://github.com/line/lighthouse.git'`. ⚠️ The README's torch install line is CUDA-specific (`--index-url .../cu118`, "We tested the codes on Python 3.9 and CUDA 11.8") and `clip_slowfast` features need an external `SLOWFAST_8x8_R50.pkl`. — [lighthouse README](https://github.com/line/lighthouse)
- Underlying research repos, all stale: `jayleicn/moment_detr` (357 stars, MIT, pushed 2026-03-09, **46 open issues** — the original QVHighlights/Moment-DETR); `wjun0830/QD-DETR` (254, **NOASSERTION**, 2025-08-12); `showlab/UniVTG` (382, MIT, **2024-05-08**); `wjun0830/CGDETR` (157, **NOASSERTION**, **2024-08-21**); `yeliudev/R2-Tuning` (92, BSD-3-Clause, **2024-07-02**); `TencentARC/UMT` (239, **NOASSERTION**, **2024-04-15**); `snailma0229/MS-DETR` (204, **no licence**, 2025-09-26, ACM MM'25). — [GitHub REST API](https://docs.github.com/rest)
- Live demos exist on HF Spaces: `awkrail/lighthouse_demo` (video MR) and `lighthouse-emnlp2024/AudioMomentRetrieval`. — [lighthouse README](https://github.com/line/lighthouse)
- `Tangkfan/Awesome-Temporal-Video-Grounding` (46 stars, no licence, last push 2026-07-30) is the only *currently updated* survey list for this area; the older lists (`ZhenZHAO/awesome-video-moment-retrieval`, `SCZwangxiao/...`, `Huntersxsx/TSGV-Learning-List`) all died in 2022–23. — [GitHub API](https://github.com/Tangkfan/Awesome-Temporal-Video-Grounding)

### Inferences

- **The practical MLX video-description path today is `mlx-vlm` + `mlx-community/Qwen2.5-VL-7B-Instruct-4bit`** (23,775 downloads/30d, video chat explicitly supported, ~5–6 GB at 4-bit — trivial on 48 GB). Qwen3-VL's timestamp-grounding advantage is real on paper but unreachable through `mlx-vlm`'s documented video path, so using it for video on this machine means `transformers` on MPS, which is a far slower and less-tested road.
- On 48 GB you could comfortably load `mlx-community/Qwen3-VL-32B-Instruct-4bit` (roughly 18–20 GB) or the `30B-A3B` MoE for *image*/keyframe captioning. The sane architecture given the video-mode gap is therefore: **detect candidate moments cheaply (audio/OCR/motion), extract keyframes, and caption/verify those keyframes with a 4-bit Qwen3-VL** — rather than feeding an hour of video to any VLM.
- `vLLM` and `SGLang`, the two deployment backends Qwen3-VL's README recommends, are **CUDA-only in practice** and should be struck from consideration on this machine. Plain `transformers` on MPS is the only non-MLX local option, and MPS coverage for video preprocessing ops is patchy.
- Feeding "hours-long video" at `fps=2` into a 256K-context model is a token-budget problem before it is a memory problem: 2 fps × 3,600 s = 7,200 frames. That is not a realistic local workload on a laptop regardless of claims, which reinforces the keyframe-triage architecture above.
- `lighthouse` is the single best-value find in this whole research pass for a highlight pipeline: it is MIT/Apache-licensed, maintained as of 2026-11-01, explicitly CPU-capable, and emits scored `[start, end]` windows plus per-frame saliency from a text query — exactly the output format a clipper consumes. The `SLOWFAST` feature dependency is the thing to probe, since SlowFast extraction is where CUDA assumptions usually hide.

### Gaps

- **I could not confirm whether `lighthouse` runs on Apple Silicon.** "CPU mode" is documented, but MPS is not mentioned, and I did not find any issue or report of someone running it on a Mac. The `clip_slowfast` feature extractor (SlowFast R50) is the specific risk — whether `pytorchvideo`/SlowFast weights load and run without CUDA on macOS is untested here. This should be the implementer's first experiment.
- No benchmark exists for `mlx-vlm` video throughput on any M-series chip (frames/second, or minutes to caption an N-minute clip). None was published in the repo or found in search.
- `QwenLM/Qwen3-VL`'s 2026-01-30 last push against 441 open issues is hard to interpret — the Qwen team may simply have moved development to the model cards and a newer repo, and the `mlx-vlm` README does reference `Qwen3.5` and `Qwen3.8` checkpoints, implying newer Qwen VL generations exist that I did not characterise. **The report should flag Qwen3-VL's repo staleness as a question, not assert abandonment.**
- Qwen3-VL's licence is Apache-2.0 at the repo level per the GitHub API, but the README itself does not state a licence and individual checkpoint licences on the Hub were not verified. Confirm per-checkpoint before shipping.

---

## What scene-detection and shot-boundary tools are worth using, and what motion/optical-flow tooling is practical for an hour of 4K?

### Takeaway

**PySceneDetect is the clear and unambiguous answer** for cut detection — BSD-3-Clause, 5,352 stars, pushed two days before this writing, with five detectors and built-in downscale/frame-skip knobs. For motion rather than cuts, **DVR-Scan** (same author) is a real CLI. The neural shot-boundary models are better on paper but the field's two best-known ones are frozen in 2023; `OmniShotCut` (2026-11-01, MIT) is the live alternative. For an hour of 4K, the bottleneck is decode, and the only hardware path on this machine is `videotoolbox`.

### Cited Findings

| Tool | Stars | Licence | Last push | Notes |
|---|---|---|---|---|
| `Breakthrough/PySceneDetect` | **5,352** | **BSD-3-Clause** | **2026-11-02** | 64 open issues; PyPI `scenedetect` **0.7.2, 2026-10-12** |
| `Breakthrough/DVR-Scan` | 531 | **NOASSERTION** (verify) | **2026-11-02** | motion-event extraction CLI; v1.8.2.1, May 9 2026 |
| `UVA-Computer-Vision-Lab/OmniShotCut` | 344 | **MIT** | **2026-11-01** | "sensitive and more informative SoTA on Shot Boundary Detection" |
| `wentaozhu/AutoShot` | 266 | **MIT** | **2023-04-18** | CVPR-NAS workshop; abandoned |
| `soCzech/TransNetV2` | 1,075 | **MIT** | **2023-12-04** | the long-standing SBD baseline; **frozen 3 years**; PyPI `transnetv2-pytorch` 1.0.5, 2025-06-01 (no licence metadata) |
| `Tangshitao/ClipShots` | 129 | MIT | 2021-11-09 | dataset only |
| `yasinyildirim/ShotDetection` | 49 | **LGPL-2.1** | 2018-07-12 | dead |

— [GitHub REST API](https://docs.github.com/rest); [PyPI](https://pypi.org/project/scenedetect/)

- **PySceneDetect 0.7's five detectors**, from the official CLI docs: `detect-adaptive` — "Find fast cuts using diffs in HSL colorspace (rolling average)", a two-pass algorithm with rolling averages "to mitigate false detections from camera movement"; `detect-content` — "Find fast cuts using differences in HSL (filtered)", combining `delta_hue`, `delta_sat`, `delta_lum`, `delta_edges` as a weighted sum against a threshold; `detect-hash` — perceptual hashing with Hamming distance; `detect-hist` — "Find fast cuts by differencing YUV histograms"; `detect-threshold` — "Find fade in/out using averaging". — [PySceneDetect CLI docs](https://www.scenedetect.com/docs/latest/cli.html)
- **PySceneDetect's performance knobs**, quoted from the same docs: downscaling — "If unset, value is selected based on resolution. Set `-d 1` to disable downscaling" (i.e. **downscaling is on by default and resolution-aware**, which is why 4K is tractable); frame skip — "`-fs 1` skips every other frame processing 50% of the video, `-fs 2` processes 33%". The docs contain **no benchmark figures, no hardware-acceleration options, and no 4K-specific guidance**. — [PySceneDetect CLI docs](https://www.scenedetect.com/docs/latest/cli.html)
- **DVR-Scan** README: "a command-line application that **automatically detects motion events in video files** (e.g. security camera footage). DVR-Scan looks for areas in footage containing motion, and saves each event to a separate video clip… works on Windows, Linux, and **Mac**." Install: `pip install dvr-scan --upgrade`. It has both a GUI (`dvr-scan-app`) and a CLI (`dvr-scan -i video.mp4`), and — directly useful for a fixed-HUD game overlay — **region masking**: `dvr-scan -i video.mp4 -r` for the interactive region editor, or `dvr-scan -i video.mp4 -a 50 50 100 50 100 100 100 50` to pass a polygon on the command line. Latest release v1.8.2.1, **May 9 2026**. — [DVR-Scan README](https://github.com/Breakthrough/DVR-Scan)
- **`ffmpeg` capabilities verified locally** on `ffmpeg version 9.0.1` (Homebrew, built with Apple clang 21.0.0):
  - `ffmpeg -hwaccels` → **`videotoolbox`** is the only method available. No CUDA, no QSV, no VAAPI.
  - `scdet` filter: "Detect video scene change", options `threshold`/`t` (0–100, **default 10**) and `sc_pass`/`s` ("Set the flag to pass scene change frames", default false).
  - `freezedetect` filter: "Detects frozen video input", options `noise`/`n` (0–1, default 0.001) and `duration`/`d` (default 2 s).
  - Also present: **`mestimate` ("Generate motion vectors")**, `select` ("Select video frames to pass in output" — supports the `scene` expression), `signalstats` ("Generate statistics from video analysis"), `blackdetect`, `thumbnail` ("Select the most representative frame in a given sequence of consecutive frames"), `framestep`, plus audio-side `silencedetect`, `astats`, `ebur128`.
  — (verified via `ffmpeg -hwaccels`, `ffmpeg -h filter=scdet`, `ffmpeg -h filter=freezedetect`, `ffmpeg -filters` on the target machine, 2026-11-04)
- **OpenCV is not installed on the target machine** — `import cv2` raises `ModuleNotFoundError`. (verified locally). Note that OpenCV's GPU-accelerated optical-flow implementations live in the `cv2.cuda` / `cv2.cuda_OpticalFlowDual_TVL1` namespace and are **CUDA-only**; on macOS only the CPU implementations (`calcOpticalFlowFarneback`, `DISOpticalFlow`, `calcOpticalFlowPyrLK`) are available.

### Inferences

- **Use `ffmpeg`'s own filters for the first pass over an hour of 4K, not Python.** `scdet` and `select='gt(scene,T)'` run inside the decode pipeline with no frame marshalling into Python, and `-hwaccel videotoolbox` puts H.264/HEVC decode on the media engine. A reasonable recipe shape: `ffmpeg -hwaccel videotoolbox -i in.mp4 -vf "scale=640:-2,scdet=t=10" -f null -` to get cut timestamps, then only decode full-resolution frames around the candidates.
- **PySceneDetect is the right tool but downscaling is doing the heavy lifting at 4K.** Its default resolution-aware downscale plus `-fs 1/2` is the documented way to keep an hour of 4K tractable; the absence of any published benchmark means the implementer must measure it. Because detection happens on a downscaled frame, a small fixed-position HUD element (a killfeed line) may be **below the detection scale** — if PySceneDetect is used to find killfeed changes rather than real cuts, `-d 1` (downscale off) will likely be required, and the cost of that is exactly what needs measuring.
- **Game footage has almost no true shot boundaries**, so neural SBD models (TransNetV2, AutoShot, OmniShotCut) are a poor fit for first-person gameplay; they will mostly fire on respawns, scoreboard transitions and killcam cuts. That is arguably *useful* (round boundaries), but it is not highlight detection. Prefer PySceneDetect's `detect-adaptive`, which is explicitly designed to suppress camera-movement false positives — the dominant failure mode for a mouse-look camera.
- **DVR-Scan's region masking is the sleeper feature here.** Restricting motion detection to a polygon is exactly what a fixed-HUD signal needs: mask to the killfeed region, and "motion" inside that box *is* the killfeed updating — no OCR required for a first-pass candidate generator. This dovetails with the project's "banner + left-name feed only" simplicity constraint.
- Optical flow at 4K for an hour is not practical in OpenCV on CPU and there is no GPU path on this machine. If a motion magnitude signal is wanted, derive it cheaply from `ffmpeg`'s `mestimate` motion vectors, or from frame-difference energy on a heavily downscaled stream (e.g. 320×180), rather than from dense flow.

### Gaps

- **No published throughput benchmark for PySceneDetect on 4K video at any resolution or on Apple Silicon.** The official docs state the knobs but publish no numbers. This is a measurement the implementer must take.
- I did not verify DVR-Scan's actual licence text — the GitHub API reports `NOASSERTION`, meaning its LICENSE file does not match a standard SPDX ID. Must be read before shipping.
- Whether `videotoolbox` hardware decode actually helps a filter-graph-bound `scdet` workload (as opposed to a transcode) is unverified; hwaccel sometimes costs more in GPU→CPU frame readback than it saves.
- `OmniShotCut`'s claim of "SoTA on Shot Boundary Detection" is self-reported in its own repo description; I did not verify it against a benchmark leaderboard, nor check whether it has Apple Silicon support.

---

## Are there open-source CLIP/SigLIP-based video retrieval implementations for searching one's own footage by text?

### Takeaway

Yes in components, no in finished products. **`open_clip` plus a vector index is the maintained, well-trodden path**, and SigLIP 2 checkpoints are enormously popular on the Hub, but every turnkey "search my own video library by text" application found is either Windows-only, AGPL, or abandoned in 2022. MLX CLIP weights exist but are nearly unused (tens of downloads a month), so the realistic local stack is PyTorch-on-MPS rather than MLX.

### Cited Findings

**Encoders:**

- `mlfoundations/open_clip` — **14,243 stars**, licence reported as **`NOASSERTION`** (non-standard LICENSE file — must be read before shipping), last push **2026-10-29**, only **28 open issues** against 14k stars (a strong health signal). — [GitHub API](https://github.com/mlfoundations/open_clip)
- **SigLIP/SigLIP 2 are the current default image-text encoders by usage.** Hub downloads in the last 30 days: `google/siglip2-giant-opt-patch16-384` **1,959,626**; `google/siglip2-base-patch16-224` **1,501,099**; `google/siglip2-base-patch16-naflex` **1,223,737**; `google/siglip-base-patch16-224` 846,457; `google/siglip-so400m-patch14-384` 699,709; `google/siglip2-so400m-patch14-384` 642,743; `google/siglip2-so400m-patch16-256` 527,776; `google/siglip2-base-patch16-256` 454,474. All carry `pipeline_tag: zero-shot-image-classification`. — [HF models API, search=siglip](https://huggingface.co/models?search=siglip)
- **MLX-native CLIP weights are essentially unused**: `mlx-community/clip-vit-base-patch32` **83 downloads/30d**, `clip-vit-large-patch14` **50**, `clip-vit-base-patch16` **46**. **No `mlx-community` SigLIP build appeared** in a downloads-sorted search of that org. — [HF models API, author=mlx-community, search=clip](https://huggingface.co/mlx-community)

**Indexing / retrieval infrastructure:**

- `rom1504/clip-retrieval` — 2,799 stars, **MIT**, last push **2026-03-28**, **94 open issues**. The standard "embed a corpus with CLIP and serve a kNN index" toolkit. — [GitHub API](https://github.com/rom1504/clip-retrieval)
- `QwenLM/Qwen3-VL-Embedding` — 1,424 stars, **Apache-2.0**, last push 2026-06-23 — a VLM-based embedding model, and `mlx-community/Qwen3-VL-Embedding-2B-8bit` exists on the Hub with **974 downloads/30d**, making it the one MLX-native multimodal retrieval embedder with real usage. — [GitHub API](https://github.com/QwenLM/Qwen3-VL-Embedding); [HF models API](https://huggingface.co/mlx-community)

**Turnkey video-search applications — every one has a disqualifying caveat:**

- `6v17/VideoSeek` — 106 stars, **AGPL-3.0**, last push 2026-11-01. Closest to the ask: "Search a local video library by **text or screenshot**, with **hard-subtitle OCR**; preview hits and export MP4, Jianying, or NLE timelines… indexing stays on your machine (**ONNX · Lance · FFmpeg**) and media is not uploaded." ⚠️ Badge states **"platform: Windows 10/11"**; README offers only a Windows download. Also offers an opt-in cloud embedding mode. — [VideoSeek README](https://github.com/6v17/VideoSeek)
- `GhostPeony/clip-finder` — 57 stars, **MIT**, last push 2026-07-02. "AI-powered YouTube search. Index any channel, playlist, or video and search through…" — YouTube-oriented, not local files. — [GitHub API](https://github.com/GhostPeony/clip-finder)
- `johanmodin/clifs` — 483 stars, **Apache-2.0**, last push **2022-03-15**. "CLIP-based Low-level Image/Frame Search" over video — the original demo of this exact idea, **abandoned 4.5 years**. — [GitHub API](https://github.com/johanmodin/clifs)
- `haltakov/natural-language-image-search` — 1,044 stars, **MIT**, last push **2022-10-13**. Abandoned. — [GitHub API](https://github.com/haltakov/natural-language-image-search)
- `Davegdd/Semantic-video-search` — 4 stars, MIT, last push **2023-02-13**. "Search a scene in a video using natural language with X-CLIP". — [GitHub API](https://github.com/Davegdd/Semantic-video-search)
- `MaGinMP/localphotos` — 3 stars, **Apache-2.0**, last push 2026-07-30. "Your own Google Photos, **running entirely on your Mac**. Local-first photo & video libra[ry]" — tiny but the only explicitly Mac-first one found. — [GitHub API](https://github.com/MaGinMP/localphotos)
- `dolphin-creator/VideoContext-Engine` — 39 stars, **no licence**, last push **2025-12-04**. "Local Video RAG Engine. A FastAPI microservice for video understanding: Scene Detecti[on]…" — architecturally the closest match to a full pipeline, but unlicensed and quiet. — [GitHub API](https://github.com/dolphin-creator/VideoContext-Engine)
- `Aseiel/VideoHighlighter` (see Q1) advertises "Visual search" alongside automatic highlighting, AGPL-3.0, pushed 2026-10-30, with a macOS build. — [VideoHighlighter README](https://github.com/Aseiel/VideoHighlighter)
- `line/lighthouse` (see Q4) is arguably the better fit than CLIP retrieval for *temporal* text search, since it returns `[start, end, score]` windows rather than per-frame similarity. — [lighthouse README](https://github.com/line/lighthouse)

### Inferences

- **Build, don't adopt.** The component stack is mature and permissively licensed — `open_clip` or `transformers` + a SigLIP 2 checkpoint, frames sampled at 1–2 fps by `ffmpeg`, embeddings in FAISS/LanceDB/sqlite-vec, cosine search against an encoded text query. That is a few hundred lines. Every finished application in this category fails on licence (AGPL), platform (Windows), or abandonment (2022), so there is nothing to fork cleanly.
- **Run the encoder on MPS via PyTorch, not MLX.** The MLX CLIP ports' download counts (46–83/month) indicate they are essentially untested in the wild and there is no MLX SigLIP at all; `mlx-community/Qwen3-VL-Embedding-2B-8bit` (974/month) is the only MLX retrieval option with visible adoption. SigLIP 2 base/so400m on MPS is a solved, well-trodden configuration by comparison.
- Sizing for this machine: 1 fps over an hour of footage is 3,600 frames; a SigLIP-base forward pass on that is minutes on an M5 Pro GPU, and the resulting index is well under 10 MB. **Frame embedding is not the bottleneck — 4K decode is.** Decode at low resolution via `-hwaccel videotoolbox` and feed the encoder's native 224/256 px input.
- A known and important weakness for this project specifically: **CLIP/SigLIP are weak at reading small on-screen text**. They will match "explosion" or "police chase" in gameplay reasonably well, but will not reliably retrieve "the frame where the killfeed says X". Text search over a *killfeed OCR* index and embedding search over *visual scenes* are two separate indexes solving two separate problems, and the report should not conflate them. VideoSeek's design — ONNX embeddings **plus** a separate hard-subtitle OCR index — independently arrives at the same two-index conclusion.

### Gaps

- `open_clip`'s licence is reported as `NOASSERTION` by the GitHub API; I did not read the LICENSE file, so I cannot state its terms. Must be checked before shipping.
- No benchmark found for SigLIP/CLIP frame-embedding throughput (frames/sec) on any Apple Silicon chip via MPS or MLX. All sizing statements above are inferences from model scale, not measurements.
- No published evaluation of CLIP/SigLIP zero-shot retrieval accuracy on *video-game* footage. Game art styles are a distribution shift from the web images these models were trained on, and the magnitude of the degradation is unmeasured.
- `MaGinMP/localphotos` (3 stars) and `dolphin-creator/VideoContext-Engine` (39 stars, unlicensed) are the two architecturally closest projects to the user's goal; I did not read either codebase, so I cannot assess quality. Both are small enough that a code read is cheap and may be worthwhile.
