# General-purpose AI clippers and livestream auto-clippers: how they decide which moments matter

**Scope:** Compiled November 2026. Every claim carries an evidence label:

- **[COMPANY]** — stated by the vendor/platform in its own docs, blog, or product page
- **[PATENT]** — granted patent or published application; assignee read off the patent record
- **[PAPER]** — peer-reviewed paper or preprint
- **[CODE]** — read from actual source, config file, or README
- **[THIRD-PARTY]** — review site / blog not written by the vendor; **low confidence**
- **[INFERRED]** — my reasoning from the above, not directly stated

**Two reliability warnings the report-writer must carry forward:**

1. **The "AI clipper" review space is an affiliate-SEO farm.** Confident technical claims about Vizard/Klap/Submagic/2short scoring internals ("speech energy, topic transitions, engagement signals") trace **only** to review blogs with no vendor source. Do not present them as fact.
2. **GitHub is now polluted with LLM-generated 0-star "Opus Clip alternative" repos.** A targeted GitHub API search for one cluster of these names returned **55 near-duplicate repos, almost all 0-star and created in 2026**. One such repo (`Rohi56u/VoXCluTcH`) appears in web search results with a precise-sounding weighting formula ("Chat Velocity 45% / Chatter Entropy 35% / Reaction Cue Density 20%") — it has **0 stars and was created 2026-11-02, two days before this research**, and the formula could not be verified from source. **Treat that formula, and similar precise numbers attributed to recently-created repos, as fabricated until verified.** Verified-from-source numbers are marked ✅ below.

---

## Q1. The actual pipeline in transcript-first tools (Opus Clip, Vizard, Klap, Submagic, 2short.ai, Riverside, Descript)

### Takeaway
Opus Clip publicly documents a **two-track architecture**: a transcript-only path ("ClipBasic") and a multimodal path ("ClipAnything") that explicitly reads visual objects/actions, non-speech audio events, sentiment, and **on-screen text including scoreboards**, and which Opus markets for "videos with little to no dialogue." The virality score itself is documented only as a 0–99 rubric over four named dimensions (Hook, Flow, Value, Trend) — no vendor in this category publishes feature weights, model architecture, training data, or calibration. The industry's own product split is the strongest available evidence that transcript-first scoring cannot be stretched to low-dialogue footage.

### Cited Findings

**Opus Clip — virality score (official)**
- 0–99 scale, "higher scores suggesting a greater chance of engagement and shares on social media" — [Opus Clip help center](https://help.opus.pro/docs/article/virality-score) **[COMPANY]**
- Four named dimensions: **Hook** (does the opening capture attention and connect to the video's core subject), **Flow** (logical progression with a satisfying endpoint), **Value** (utility, emotional resonance, audience connection), **Trend** (alignment with current cultural moments and viewer interests) — [Opus Clip help center](https://help.opus.pro/docs/article/virality-score) **[COMPANY]**
- The doc states only that the system performs a "multi-factor evaluation" of those dimensions, and that with ClipAnything "our AI performs extra checks to ensure it finds the best clips for your specific needs." It publishes **no** model details, **no** feature weights, and **no** accuracy caveats or list of content types where scoring is unreliable — [Opus Clip help center](https://help.opus.pro/docs/article/virality-score) **[COMPANY]**
- Gated to Pro and Starter plans — [Opus Clip help center](https://help.opus.pro/docs/article/virality-score) **[COMPANY]**

**Opus Clip — ClipBasic vs ClipAnything (official; the key fact for the gameplay case)**
- Opus Clip explicitly contrasts the two: **ClipBasic "relies solely on the transcript to understand spoken words."** ClipAnything does not — [Opus Clip ClipAnything](https://www.opus.pro/clipanything) **[COMPANY]**
- ClipAnything visual stage: "Analyze and understand everything on screen, including but not limited to: Objects: Characters, animals, items; Colors: Yellow flowers, a girl in a purple dress; Actions: Patrick Mahomes throwing a touchdown" — [Opus Clip](https://www.opus.pro/clipanything) **[COMPANY]**
- ClipAnything audio stage covers **non-speech audio events**: "Emotional Sounds: Laughter, cheering, shouting, arguing; Environmental Sounds: Bird chirping; Sound Effects: Glass shattering, car honking", plus speaker diarization ("Accurately identifies which speaker is talking") — [Opus Clip](https://www.opus.pro/clipanything) **[COMPANY]**
- ClipAnything reads on-screen text/graphics including "**Scoreboards, name cards, logo**" — [Opus Clip](https://www.opus.pro/clipanything) **[COMPANY]**. This is the closest any general-purpose clipper comes to publicly admitting HUD/scoreboard reading as a scoring signal.
- Sentiment stage: "happiness, joy, sorrow, surprise, sadness, couple arguing" — [Opus Clip](https://www.opus.pro/clipanything) **[COMPANY]**
- Officially supported content includes "vlogs, sports, TV shows, behind-the-scenes, news, music, and **videos with little to no dialogue**" — [Opus Clip](https://www.opus.pro/clipanything) **[COMPANY]**
- ClipAnything is prompt-driven: the user describes the wanted moment in natural language and the model retrieves matching segments — [Opus Clip](https://www.opus.pro/clipanything) **[COMPANY]**

**The other six tools**
- **Descript ("Find good clips")** — a one-click AI action that auto-detects standout segments; Underlord operates on the **transcript rather than the timeline** — [Descript Clips](https://www.descript.com/clips), [Descript Underlord primer](https://www.descript.com/blog/article/underlord-ai-video-editor-primer) **[COMPANY]**. Noted failure mode: transcript-driven selection is only as good as the ASR — desynced or erroneous transcripts cut the wrong moments — [review](https://kompozy.io/reviews/descript) **[THIRD-PARTY]**
- **Riverside Magic Clips** — the per-clip "Viral Score" is a real product feature; the commonly repeated signal breakdown (keyword relevance + sentiment analysis + speaker energy) comes from review blogs, not Riverside docs — [Blitzcut](https://blitzcutai.com/blog/riverside-magic-clips-review-2026), [Feisworld](https://www.feisworld.com/blog/riverside-magic-clips) **[THIRD-PARTY]**
- **Submagic Magic Clips** — [product page](https://www.submagic.co/features/magic-clips) **[COMPANY, marketing-level]**; reviewers characterize its selection as **"face-detection-first"** (face tracking + speaker signals as primary inputs) rather than narrative-arc detection — [ssemble roundup](https://www.ssemble.com/blog/best-clipping-software-2026) **[THIRD-PARTY]**
- **Klap** — 0–100 Virality Score; selection on "hooks, punchlines, and emotional peaks", topic segmentation, "natural clip boundaries"; Klap's marketing claims training "on millions of successful short videos" — [Klap AI Clip Generator](https://klap.app/tools/ai-clip-generator) **[COMPANY, marketing-level]**; detail from [review](https://zplatform.ai/ai-reviews/klap-review/) **[THIRD-PARTY]**
- **Vizard** — review-level description only: scores transcript sections on complete sentences, pacing, audio energy, hook strength, self-containedness. **No Vizard engineering source exists that I could find** — [review](https://www.nextclip.pro/blog/vizard-ai-review) **[THIRD-PARTY]**
- **2short.ai** — no technical description of its scoring found anywhere beyond pricing/feature marketing **[GAP]**

**Pipeline shape as visible in open-source reimplementations**
- Clones converge on an identical four-stage shape: Whisper (word-level timestamps) → LLM scores transcript windows → face/subject tracking for reframe → ffmpeg composite. [Steezy-code/clipper](https://github.com/Steezy-code/clipper) ("Whisper transcription, LLM clip scoring, OpenCV face tracking, ffmpeg compositing"), [ColinGPT9/clips-studio](https://github.com/ColinGPT9/clips-studio), [J0rA2/open-clip-studio](https://github.com/J0rA2/open-clip-studio), [Anil-matcha/ai-clipping-comfyui](https://github.com/Anil-matcha/ai-clipping-comfyui) **[CODE — note these are mostly recent, low-star projects; see warning 2]**
- One clone's README describes supplying the LLM "the transcript plus a timeline of those events, so it can weigh 'the words are mild but the room exploded' correctly" — i.e. non-speech audio/visual events are given to the LLM as a **side-channel annotation track**, not as an independent scorer — [ColinGPT9/clips-studio](https://github.com/ColinGPT9/clips-studio) **[CODE]**

### Inferences
- **Segment boundary selection is the least documented part of every commercial tool.** No vendor publishes it. The only visible mechanism, in clones and in the academic work, is: boundaries snap to sentence/utterance edges from word-level ASR timestamps, with the LLM returning start/end transcript indices. Opus Clip's "Flow" dimension ("satisfying endpoint") and Klap's "does not cut off mid-idea" are both consistent with boundaries constrained to transcript-sentence edges. **[INFERRED]**
- **A tool whose boundary primitive is the ASR sentence has no boundary primitive at all on silent footage.** This, not the scoring model, is the hard failure for silent gameplay — scoring can in principle be replaced, but there is nothing left to snap to. **[INFERRED]**
- Opus Clip building a *separate model* (ClipAnything) rather than extending the transcript model is strong evidence the transcript path is not repairable for low-dialogue content. **[INFERRED]**
- "Virality score" across all these tools is best read as **an LLM rubric judgement rendered as a number**, not a calibrated predictor. Opus Clip's own doc describes dimensions, not a trained regressor, and nothing published anywhere ties any of these scores to measured downstream views. **[INFERRED]**
- Of the seven tools, only Opus Clip (via ClipAnything) has a documented non-transcript path. Descript, Vizard, Klap, 2short and Riverside are transcript-first with no documented alternative; Submagic is face-first, which is an even narrower precondition. **[INFERRED]**

### Gaps
- **No vendor in this set publishes an engineering blog, paper, or patent on their scoring model.** Everything beyond the Opus Clip help-center rubric and the ClipAnything feature list is third-party inference.
- Whether Opus Clip's Virality Score is produced by the same model for ClipBasic and ClipAnything is unclear; the doc only says ClipAnything triggers "extra checks."
- No published calibration data (score vs. actual views) from any vendor. One review claims a 50-clip test where score ranking "didn't consistently match which clips actually performed" — [autoposting.ai](https://autoposting.ai/blog/opus-clip-review) **[THIRD-PARTY]** — but the methodology is undocumented and I would not rely on it.
- Whether Whisper specifically (vs. in-house ASR) is used by any vendor is unconfirmed; Whisper claims come only from clone projects and SEO articles.

---

## Q2. How Twitch/Kick clip systems and community bots use crowd signals

### Takeaway
Twitch now ships first-party **Auto Clips** and states the signal set outright: "chat activity, vocal inflection, and on-screen events." But Twitch publishes no thresholds or algorithm and exposes **none** of this through its API — Helix has only manual clip creation and retrieval. Kick has no native auto-highlight feature at all. Published numeric thresholds for chat-spike detection come almost exclusively from papers and open-source code, not from the platforms. Separately, **Amazon and Google both hold patents that claim chat-rate thresholds and spike-shape classification in detail** — the patents are the real technical disclosure here, not the product docs.

### Cited Findings

**Twitch Auto Clips (first-party)**
- "Auto Clips automatically generates captioned clips from the best moments from your stream, **by taking into account chat activity, vocal inflection, and on-screen events**." — [Twitch blog, TwitchCon Rotterdam 2026](https://blog.twitch.tv/en/2026/05/30/everything-we-announced-at-twitchcon-rotterdam-2026/) **[COMPANY]** — the single most authoritative statement of a platform-side signal set.
- Status: limited availability; "We'll be moving to beta in the coming months. Signups are open now." — [Twitch blog](https://blog.twitch.tv/en/2026/05/30/everything-we-announced-at-twitchcon-rotterdam-2026/) **[COMPANY]**
- Twitch's stated engagement effect: ~50% of all streamers share clips post-broadcast, rising to **85% among Auto Clips users** — [Twitch blog](https://blog.twitch.tv/en/2026/05/30/everything-we-announced-at-twitchcon-rotterdam-2026/) **[COMPANY]**
- Reported as alpha, English-language channels only, captions generated, portrait version produced — [streamer.guide](https://streamer.guide/blog/twitchcon-rotterdam-2026-new-features-1440p-clips-guilds), [gamingcareers.com](https://gamingcareers.com/newsletters/twitch-clip-that-actually-works-now/) **[THIRD-PARTY]**
- Twitch Stories surfaces "top clips from streams" for sharing to followers — [Twitch blog](https://blog.twitch.tv/en/2026/05/30/everything-we-announced-at-twitchcon-rotterdam-2026/) **[COMPANY]**

**"Twitch, Clip That" voice trigger**
- Official: "'Twitch Clip That' is a great feature — if you say the phrase, we'll automatically create a clip that is easy to share later." — [Twitch blog](https://blog.twitch.tv/en/2026/05/30/everything-we-announced-at-twitchcon-rotterdam-2026/) **[COMPANY]**
- Reported mechanics: speech-to-text on stream audio listens for "Twitch, Clip That" / "Twitch, Clip It" and clips the **preceding 60 seconds**; captions on by default; Partners and Affiliates; English-only; gradual rollout — [gamingcareers.com](https://gamingcareers.com/newsletters/twitch-clip-that-actually-works-now/), [streamer.guide](https://streamer.guide/blog/twitchcon-rotterdam-2026-new-features-1440p-clips-guilds) **[THIRD-PARTY]**
- **Source conflict, flagged:** some coverage of the Rotterdam announcement described this as "a trigger word **in chat** generates a clip automatically." That appears to be wrong — "chat cannot trigger a clip by typing 'clip that'; voice detection reads stream audio, not chat text" — [reelshift.app](https://reelshift.app/blog/clip-that-voice-command-guide) **[THIRD-PARTY]**. The Twitch blog itself says only "if you say the phrase," supporting the voice-only reading.

**Twitch API — what crowd signal is actually exposed**
- Helix contains clip endpoints for manual operations only: **Create Clip**, **Get Clips**, **Get Clip Download**, **Create Clip From VOD**. There is **no** endpoint for automatic highlight detection, clip-worthy moment identification, engagement/chat analytics, or real-time moment recognition. Get Extension Analytics / Get Game Analytics return retrospective CSV reports — [Twitch API reference](https://dev.twitch.tv/docs/api/reference/) **[COMPANY]**
- Twitch removed the "Featured Clips" function — [tos.gg](https://tos.gg/twitch-kills-featured-clips-function/) **[THIRD-PARTY]**
- Twitch capped streamer storage at **100 hours of highlights and uploads**, stating "other features like Clips, Tags, and the Mobile Discovery Feed are more effective in driving discovery or engagement"; over-limit channels have highlights auto-deleted starting with least-viewed — [TechCrunch](https://techcrunch.com/2025/02/20/twitch-caps-streamers-storage-at-100-hours-of-highlights-and-uploads) **[THIRD-PARTY reporting a COMPANY statement]**

**Kick**
- Native clipping is **manual**: press `C` or click the Clip icon, trim with a slider, publish. Max clip length reported inconsistently as 60s and 180s (sources conflict) — [ascynd.io](https://ascynd.io/en/blog/how-to-clip-kick-streams) **[THIRD-PARTY]**
- **Kick has no built-in automatic-highlight feature.** Auto-clipping on Kick is entirely third-party (Eklipse, StreamLadder ClipGPT, Kick Clipper, Wayin) — [Eklipse Kick Clips](https://eklipse.gg/features/kick-clips/), [StreamLadder auto-clip Kick](https://www.streamladder.com/clipgpt/auto-clip/kick) **[THIRD-PARTY/vendor]**
- One third-party Kick clipper states its signals as "audio spikes, chat activity, and visual cues" — [kickclipper.org](https://kickclipper.org/) **[COMPANY, marketing-level]**

**The real algorithmic disclosure is in the patents (see Q6 for full detail)**
- **US10972524B1 "Chat based highlight algorithm"** (Amazon, filed 2016) claims a **baseline threshold of expected chat activity** computed either as average messages-per-interval over the whole VOD **or as a step function of viewer count × message count** so the threshold adapts live; then finds *runs* of consecutive intervals exceeding the threshold by a specified variance, locates peaks inside each run, and sets window boundaries by classifying the **spike shape** as *anticipatory* (window starts minutes before peak), *reactive* (starts just before, extends after), or *hybrid* — [patent](https://patents.google.com/patent/US10972524B1/en) **[PATENT]**
- **US10575036B2** (Google, filed 2016) claims **comment rate over threshold, abnormally *short* comment lengths during the spike, and viewer-count swings** as user-interaction highlight indicators, fused with video indicators (changes in key screen regions such as **scoreboards or character status**) and audio indicators — [patent](https://patents.google.com/patent/US10575036B2/en) **[PATENT]**. The short-comment-length feature is effectively the "POGGERS / one-word burst" signal, and is the only place I found viewer-count change claimed as a highlight feature.

**YouTube's crowd signal: the "Most Replayed" heatmap**
- Closest thing to a published machine-readable crowd signal from a major platform. Reverse-engineered structure: **exactly 100 segments regardless of video length** (verified on both a 4-minute music video and a 10-hour loop), each with `startMillis`, a constant `durationMillis`, and `intensityScoreNormalized` as a float in [0,1] — [Priyavrat Misra, "Reversing YouTube's Most Replayed Graph"](https://priyavr.at/blog/reversing-most-replayed/) **[CODE / reverse-engineering]**
- Normalization is server-side: take the max-view-count segment, divide every segment's count by that max. Intensity 1.0 = "the most replayed slice of *this* video", **not** an absolute count; curves are not comparable across videos — [Priyavrat Misra](https://priyavr.at/blog/reversing-most-replayed/) **[CODE]**
- Client rendering uses Cardinal-spline interpolation with tension 0.2, which is what creates the characteristic dips flanking peaks — **these are rendering artifacts, not data.** Anyone using heatmap peaks as labels should use the 100 raw segment values, not the drawn curve — [Priyavrat Misra](https://priyavr.at/blog/reversing-most-replayed/) **[CODE]**
- yt-dlp added heatmap extraction, making the signal scriptable — [yt-dlp issue #3888](https://github.com/yt-dlp/yt-dlp/issues/3888) **[CODE]**
- Mechanistically, the closest *verified* Google patent is **US9465435B1**, which scores small sequential segments from playback telemetry (where users stop, pause, resume, rewind, fast-forward, rewatch, plus volume changes and commenting), clusters adjacent similar-engagement segments, and cuts boundaries where engagement changes sharply — [patent](https://patents.google.com/patent/US9465435B1/en) **[PATENT]**

**Community vote-based bots (not spike-based)**
- **clipitbot** — viewers type `!clipit`; produces a **30-second clip**; configurable minimum vote count and permissions — [clipitbot](https://www.twitch.tv/clipitbot/about) **[COMPANY]**
- **twitch-auto-clipper (PyPI)** — monitors chat for **many viewers sending the same emote/message in a short period**, clips when a configurable threshold is exceeded. Threshold values and source repo **unverified** (page would not render) — [PyPI](https://pypi.org/project/twitch-auto-clipper/) **[COMPANY, unverified]**
- Commercial, no published logic: [Eklipse auto-clip Twitch](https://eklipse.gg/tool/auto-clip-twitch/) (claims it "scans chat spikes, audio, kills and reactions"), [ClipBot.gg](https://www.clipbot.gg/), [clipbot.tv](https://clipbot.tv/), [clipme.com/twitch-clipper](https://clipme.com/twitch-clipper) **[COMPANY, marketing-level]**

### Inferences
- Twitch's stated triple ("chat activity, vocal inflection, on-screen events") is the clearest public confirmation that **a platform with total access to chat still treats chat as insufficient alone** and fuses it with audio prosody and an on-screen-event detector. **[INFERRED]**
- Because Helix exposes no chat-rate or engagement time-series, every community auto-clipper must reconstruct the crowd signal itself — joining IRC/EventSub live, or downloading VOD chat replay afterwards. This is why the OSS ecosystem is built around chat-replay downloaders rather than an API. **[INFERRED]**
- **Clip-creation rate by viewers** is in principle the strongest crowd signal (an explicit timestamped "this mattered" vote), and `Get Clips` returns clip timestamps per broadcaster so it is reconstructable post-hoc. But I found **no platform documentation, no patent, and no production system** that uses viewer clip-creation *density* as a detection feature. The nearest published use is LIGHTOR's Highlight Extractor, which uses viewer *seek/play* positions (not clip creation) to refine boundaries. **[INFERRED]**
- **Viewer-count change is a weak signal and is essentially unused in practice.** It appears as a claimed indicator in Google's US10575036B2 but in no implementation I found; Twitch viewer counts update on the order of minutes and are dominated by arrival/departure trends rather than 10-second excitement. **[INFERRED]**

### Gaps
- **No platform publishes any threshold.** Twitch, Kick and YouTube publish zero numbers: no messages-per-second cutoff, no emote-rate threshold, no window length, no smoothing parameter.
- No documentation on how Twitch Auto Clips weights its three stated signals, how it sets clip boundaries, or how it behaves on a silent no-chat stream.
- Emote-specific behaviour (sustained LUL vs POG vs OMEGALUL rate) is addressed in **no** platform documentation. The only concrete emote handling is in OSS (Q3).
- I found no reliable source on whether Kick exposes any chat-analytics API suitable for this.

---

## Q3. Open-source / documented implementations of chat-spike highlight detection for Twitch VODs

### Takeaway
Yes, and the verified implementations are far simpler than the literature suggests: bin chat into **10–25 second buckets**, threshold on either a flat count or a small multiple of the bucket distribution, merge consecutive outlier buckets, and **offset the clip start backwards because chat reacts late**. Only one OSS repo uses a genuine statistical threshold. The widely-repeated "N standard deviations over a 30-second window" formula **could not be found in any open-source implementation** — it appears to be vendor marketing language.

### Cited Findings — repos with algorithms read from source ✅

**✅ [hougesen/twitch-highlight-finder](https://github.com/hougesen/twitch-highlight-finder) — Rust, ~9 stars.** The only OSS repo found with a real statistical threshold. From [`highlight-finder/src/finder/mod.rs`](https://github.com/hougesen/twitch-highlight-finder/blob/main/highlight-finder/src/finder/mod.rs) **[CODE]**:
```rust
const TIME_BUCKET_SIZE_MS: u16 = 10_000;                          // 10-second buckets
let min = f64::from(TIME_BUCKET_SIZE_MS) / 1000.;                 // = 10 msgs, i.e. 1 msg/sec floor;
                                                                  // buckets below this excluded from baseline
let top_5_percentage = values[(values.len() * 95) / 100] as i64;  // 95th percentile
let min = (std::cmp::max(top_5_percentage,
           std::cmp::max(average as i64, i64::from(base))) * 2) as f64;
if v > &min { outliers.insert(*k); }
```
Threshold = **2 × max(p95, mean, base)** over 10-second buckets, with sub-1-msg/s buckets excluded from the baseline as unreliable; consecutive outlier buckets merged into one clip. Monorepo includes separate Twitch / BTTV / FrankerFaceZ emote importers, so emotes feed the per-bucket score. Written as an undergraduate thesis.

**✅ [joaohenggeler/twitch-chat-highlights](https://github.com/joaohenggeler/twitch-chat-highlights) — Python, ~10 stars.** The clearest documented *emote-category* approach. Real defaults from [`Source/config.json.template`](https://raw.githubusercontent.com/joaohenggeler/twitch-chat-highlights/main/Source/config.json.template) **[CODE]**:
- `"bucket_length": 20` — fixed 20-second buckets
- `"message_threshold": 15` — minimum messages **per category** per bucket to count as a highlight
- `"top_bucket_distance_threshold": 3` — lower-ranked highlights must be ≥3 buckets away (temporal dedup)
- 11 emote/word categories, case-insensitive, strings or regexes:
  - Funny: `["LUL", "LULW", "OMEGALUL", "KEKW", "regex:LMF?AO+", "regex:LO+L"]`
  - Weird: `["WutFace", "DansGame", "WeirdChamp", "yikes", "regex:WTF+", "regex:bruh+", "regex:\\?+"]`
  - Pog: `POG`, `POGGERS`, `PogChamp`; Sad: `PepeHands`, `FeelsBadMan`, `Sadge`, `BibleThump`, `:(`; Bonk: `BOP`, `Kreygasm`
- **No z-score, no smoothing, no baseline normalization** — absolute per-bucket counts only. Opposing categories are compared to derive "positive / negative / controversial" sub-labels.
- This is the only verified source anywhere that gives **per-emote-family thresholds**, and the answer is a flat 15 messages per 20s bucket.

**✅ [xurei/twitch-highlights-logger](https://github.com/xurei/twitch-highlights-logger) — JavaScript, ~34 stars, GPL-3.0.** Highest-starred genuine chat-highlight tool found. README: *"loads the full chat log from twitch.tv and counts the number of messages in a given window of time. When the number of messages matching a certain filter reach a threshold, the app considers it as an highlight."* From [`src/webapp/sliding-window.js`](https://github.com/xurei/twitch-highlights-logger/blob/master/src/webapp/sliding-window.js) **[CODE]**: pure sliding window over `content_offset_seconds`, `nbMatches = j - i + 1`, emits a range when `nbMatches >= threshold`, and backs the clip start off by `Math.max(0, items[i].content_offset_seconds - rollback)`. The explicit `rollback` parameter is the OSS equivalent of LIGHTOR's chat-lag correction. `windowLength` / `threshold` / `rollback` are user-supplied; defaults not verified.

**[artkulak/twitch-stream-highlights-detection](https://github.com/artkulak/twitch-stream-highlights-detection)** — real-time detection that extracts features from **sound, motion and live chat** for **10-second clips** and passes them to a metamodel predicting highlight probability. One of the few that fuses chat with non-chat signals — repo README **[CODE, algorithm detail not read from source]**

### Cited Findings — repos verified to exist, algorithms NOT verified

| Repo | Lang | Stars | Note |
|---|---|---|---|
| [cairthenn/TwitchChatVideo](https://github.com/cairthenn/TwitchChatVideo) | C# | 45 | Chat → video replay for editors; **no detection** |
| [bendawg2010/Auto-clipper](https://github.com/bendawg2010/Auto-clipper) | Python | 11 | Object detection + voice triggers |
| [ZiedYT/automatic-twitch-clipper](https://github.com/ZiedYT/automatic-twitch-clipper) | Python | 8 | Per-channel JSON config; thresholds not in README |
| [ros-dorian/TwitchHack](https://github.com/ros-dorian/TwitchHack) | Jupyter | 4 | Owner spelling unresolved (also seen as `Dietech/TwitchHack`) |
| [nirvagold/stream-clipper](https://github.com/nirvagold/stream-clipper) | Rust | 3 | Desktop app, audio + chat |
| [marianonj/TwitchAutoClipper](https://github.com/marianonj/TwitchAutoClipper) | Python | 2 | Chat frequency + content + audio; TODO still lists "add audio matching" |
| [bihanikeshav/TwitchSnipBot](https://github.com/bihanikeshav/TwitchSnipBot) | TS | 2 | Chat spikes |
| [patinbsb/TwitchHighlightGenerator](https://github.com/patinbsb/TwitchHighlightGenerator) | C# | 2 | |
| [mhuber161/twitch-chat-highlights](https://github.com/mhuber161/twitch-chat-highlights) | TS | 1 | |
| [christopherzc/Twitch-Clip-Creator](https://github.com/christopherzc/Twitch-Clip-Creator) | Jupyter | 1 | ML highlight reels |
| [imhadev/peaks](https://github.com/imhadev/peaks) | Python | 1 | |
| [chengyangfu/Pytorch-Twitch-LOL](https://github.com/chengyangfu/Pytorch-Twitch-LOL) | Python | — | Dataset/code release for the EMNLP 2017 Twitch-LOL work **[CODE]** |
| [velvetthunder15/heatmapify](https://github.com/velvetthunder15/heatmapify) | — | — | YouTube engagement extraction; falls back to "comments, captions, audio and visuals" when Most Replayed is unavailable **[CODE]** |

**Explicit negative results (useful signal for the report):**
- There is **no notable OSS repo** literally named `twitch-chat-highlight`, `autoclip`, `clipbot`, `twitch-clipper`, or `chat-analyzer`. "ClipBot" and "Twitch Clipper" are **commercial** products.
- The [chat-replay-downloader / `chat-downloader`](https://github.com/xenova/chat-replay-downloader/) and [lay295/TwitchDownloader](https://github.com/lay295/TwitchDownloader) ecosystem is the **data layer only** — both export chat JSON and TwitchDownloader renders it, but **neither does highlight detection nor exposes a messages-per-second heatmap.**
- A GitHub API search for `game highlight detection kill clip` returned **zero results**.

### Cited Findings — published threshold numbers (consolidated)

| Source | Window | Threshold / parameter | Verified |
|---|---|---|---|
| [hougesen/twitch-highlight-finder](https://github.com/hougesen/twitch-highlight-finder/blob/main/highlight-finder/src/finder/mod.rs) | 10 s buckets | `2 × max(p95, mean, 10)`; <1 msg/s buckets excluded from baseline | ✅ **[CODE]** |
| [joaohenggeler config](https://raw.githubusercontent.com/joaohenggeler/twitch-chat-highlights/main/Source/config.json.template) | 20 s buckets | 15 msgs per emote category; 3-bucket dedup gap | ✅ **[CODE]** |
| [LIGHTOR](https://www.cs.sfu.ca/~jnwang/papers/lightor.pdf) | **25 s** sliding window | ≥**500 chat msgs/hour** required; highlights must be ≥**120 s** apart; users tolerate ≤**10 s** lead-in error | ✅ **[PAPER]** |
| [Fu et al. EMNLP 2017](https://aclanthology.org/D17-1102.pdf) | **7 s** text window ("best results with text window size as 7 seconds") | learned, not thresholded | ✅ **[PAPER]** |
| [aaroncunliffe/twitch-peak-highlight](https://raw.githubusercontent.com/aaroncunliffe/twitch-peak-highlight/master/TwitchPeakHighlight/main.py) (audio, not chat) | 1/60 s frames | `threshold = 0.85` normalized amplitude; `clip_bounds = 2.0` s padding and merge gap | ✅ **[CODE]** |
| Community pandas recipe | per-10-second buckets of `message_offset_seconds` | smooth, then `scipy.signal.find_peaks` | [DEV](https://dev.to/devil_scrapes/charting-twitch-chat-velocity-hype-curve-analysis-for-esports-vods-5fbc) **[THIRD-PARTY]** |
| "3× rolling 30–60s average" / z-score framing | — | **appears only in commercial marketing**, e.g. [cliphunter.gg](https://cliphunter.gg/blog/twitch-chat-spike-detection); **not found in any OSS implementation** | ❌ unverified |

### Cited Findings — LIGHTOR, the most specific published chat algorithm
- **25-second sliding window** over timestamped chat — [arXiv:1910.12201](https://arxiv.org/html/1910.12201v1) **[PAPER]**
- Only **three features**, min-max normalized to [0,1], into a **logistic regression**: (1) *Message Number* — count in window; (2) *Message Length* — average word count per message; (3) *Message Similarity* — average bag-of-words similarity of each message to the window's center message (with K-means clustering) — **[PAPER]**
- **Reaction-lag correction:** `time_start = time_peak − c` with `c` ≈ **20–27 s**, learned from training data — **[PAPER]**
- Two-stage: *Highlight Initializer* (chat → approximate positions), then *Highlight Extractor*, which converts viewers' "play"/seek actions into viewership data, classifies seek points as **Type I** (after the highlight end) or **Type II** (before the end), median-aggregates Type II, and iteratively moves Type I points backward in **20-second** steps — **[PAPER]**
- Datasets: Twitch **Dota 2** (60 videos, ~10 highlights/video) and **League of Legends** (173 videos, ~14 highlights/video); ~800–4,300 chat messages per video — **[PAPER]**
- Results: Chat Precision@10 = **0.82 with a single training video**; Chat Precision@5 ≈ **0.90**; end-to-end Video Precision@5 = **0.906 (start) / 0.719 (end)**; vs. Toretter baseline **<20% → ~60%** precision; beat SocialSkip and Moocer "by a big margin" — **[PAPER]**
- vs. a deep baseline: Lightor **0.906 vs Joint-LSTM 0.629** on start position, using **123× fewer training examples** and **1.06 s of training vs >3 days** (~100,000× faster) — **[PAPER]**
- **No audio or visual baselines were compared** in LIGHTOR — **[PAPER]**

### Cited Findings — the most important writeup: PogChampNet
- **Farza / Visor.gg, "PogChampNet: how we used Twitch chat + deep learning to create automatic game highlights"** — [Medium](https://medium.com/@farzatv/pogchampnet-how-we-used-twitch-chat-deep-learning-to-create-automatic-game-highlights-with-only-61ed7f7b22d4), announced [on X](https://x.com/FarzaTV/status/1067129880066891776), mirrored [here](https://owhighlights.wordpress.com/2018/11/26/i-created-an-algorithm-called-pogchampnet-that-takes-an-overwatch-vod-and-can-automatically-find-the-highlight-worthy-moments-in-real-time-it-was-trained-with-the-help-of-twitch-chat-and-its-meme/). Method: use Twitch chat **purely as an auto-labeler** — when chat erupts with `Pog`/`POGGERS`/`PogChamp`, cut a **30-second clip** at that timestamp from the Overwatch VOD; train a deep CNN on those clips; at inference time the model scores highlight-worthiness **from video only, with no chat**. **[THIRD-PARTY/author writeup — Medium returned HTTP 403, so the exact message-rate threshold and architecture are UNVERIFIED; the 30 s clip length and emote list come from secondary sources.]**
- **schkn, "Building an automated platform that captures the best clips from Twitch, live"** — [Medium](https://medium.com/schkn/building-an-automated-platform-that-captures-the-best-clips-from-twitch-live-8274237c2779). Exists and is on topic (signal model over chat-activity spikes), but Medium returned 403; **no numbers extractable.** **[GAP]**

### Inferences
- **Consensus bin size is 7–25 seconds** (EMNLP 7 s; hougesen 10 s; artkulak 10 s; community recipe 10 s; joaohenggeler 20 s; LIGHTOR 25 s). A 10-second bucket with light smoothing is the safe default. **[INFERRED]**
- Thresholds in real code are expressed **relative to the stream's own distribution** (p95, mean, peak-finding) or as flat per-category counts — never as an absolute global messages-per-second constant — because baseline chat rate varies by orders of magnitude between a 50-viewer and a 50,000-viewer channel. **[INFERRED]**
- **Every naive chat-spike clipper is systematically late.** LIGHTOR's learned `c ≈ 20–27 s` backward offset, xurei's `rollback` parameter, and Amazon's spike-shape classification (anticipatory/reactive/hybrid) are three independent encodings of the same fact. Any crowd-derived label used to train a visual detector must be shifted earlier or it teaches the model to fire on the aftermath. **[INFERRED]**
- LIGHTOR's message-similarity feature and joaohenggeler's per-category counting both function as **spam/copypasta suppression**. This is the practical reason raw emote-spam rate is weaker than it looks: one pasta produces a huge rate spike carrying near-zero information. **[INFERRED]**
- **PogChampNet is the single most transferable idea in this entire body of work for a chat-free pipeline:** chat is used once, offline, as a free label generator, and then discarded. The deployed detector is vision-only. **[INFERRED]**

### Gaps
- Star counts and maintenance status for the second table are from search metadata, not verified; treat as "exists and claims X."
- **No source gives a numeric emote-*rate* threshold** (e.g. LUL/s). The only verified emote handling is flat per-bucket counts (joaohenggeler) and emote-weighted bucket scores (hougesen). Any report claiming a numeric emote-rate cutoff is unsourced.
- No source found that uses **viewer clip-creation rate** as the detection feature.
- PogChampNet and schkn writeups are 403-blocked; their numbers are unverified.
- No rigorous head-to-head benchmark of these OSS repos against each other or against human labels.
- [willwillbuild/hatsume-meta](https://github.com/willwillbuild/hatsume-meta) ("research on how best to find highlights in game videos") exists per search only; content unverified.

---

## Q4. What these tools do with no speech and no chat (silent gameplay)

### Takeaway
Transcript-first tools have no mechanism and no graceful degradation — the documented production fix is to **discard silent input**, not to score it. The honest vendor answers are either a separate multimodal model (Opus ClipAnything) or a game-specific **HUD/kill-feed event detector** (Eklipse, NVIDIA, Flowtter/crispy). Crucially, the gaming-native tools do **not** fall back on generic audio energy or visual motion as a primary signal: they read the HUD, and where there is no HUD to read they fall back on an **explicit human trigger** (voice command / hotkey) rather than on a detector. Unsupervised visual novelty on game footage alone is measured at only **29% precision** — which argues strongly for explicit symbol reading over generic visual saliency.

### Cited Findings

**General-purpose clippers**
- Opus Clip's answer is architectural: ClipBasic "relies solely on the transcript", so low-dialogue content is routed to ClipAnything, explicitly sold for "videos with little to no dialogue", keying on objects/actions, non-speech sounds, sentiment, and on-screen text "Scoreboards, name cards, logo" — [Opus Clip](https://www.opus.pro/clipanything) **[COMPANY]**
- Klap's detection "works well with structured content like interviews and educational videos where topic shifts are clear" and "struggles more with abstract or heavily visual content where 'best moments' are not dialogue-driven" — [review](https://zplatform.ai/ai-reviews/klap-review/) **[THIRD-PARTY]**
- **The clearest evidence of non-degradation:** a production clipper's documented fix for speechless sources — when a source has no transcribable sentences (music-only gameplay), "the transcript-based moment picker has nothing to cut", so the job **marks the file bad and fetches a different source**, giving up after 5 speechless files — [astrotobby/AI-GEMS PR #5](https://github.com/astrotobby/AI-GEMS/pull/5) **[CODE]**
- Submagic's face-detection-first selection has no defined behaviour on footage with no face — **[INFERRED from [ssemble](https://www.ssemble.com/blog/best-clipping-software-2026) THIRD-PARTY]**

**Eklipse (gaming-native, and the most informative vendor on this question)**
- The **previous** engine "detected trigger events like kill feed entries and cut fixed windows around them, but that falls apart everywhere else." Its replacement, **Gameplay Intelligence**, runs on every Premium VOD from **June 1, 2026** using "scene-aware context and per-genre AI tuning" — [Eklipse blog](https://blog.eklipse.gg/streaming-tips/how-gameplay-intelligence-works-2.html) **[COMPANY — page returned HTTP 403 to direct fetch; content from search indexing, so sourcing is slightly weaker]**
- Stated coverage of 1,000+ games, understanding "kills, clutches, and objectives" — [Eklipse](https://eklipse.gg/features/automate-stream-clips/) **[COMPANY, marketing-level]**
- **The single most important vendor sentence for the silent-gameplay case:** "event detection is strongest where there are events to read like kill feeds and scoreboards, and voice covers the rest, which is why the two run together — **voice command particularly pays off hardest where there is no kill feed**" — [Eklipse blog](https://blog.eklipse.gg/tools/ai-clip-maker-gaming.html) **[COMPANY]**
- Voice Command ("Clip it!") ships as the complement to automatic detection — [Eklipse Voice Command](https://eklipse.gg/features/voice-command/) **[COMPANY]**
- **Outplayed / Overwolf** event detection is **closed-source** and works off the Overwolf Game Events API — a per-game official event feed, **not CV**. Nothing to read. **[verified negative]**

**✅ [Flowtter/crispy](https://github.com/Flowtter/crispy) — ~158 stars, Python + TypeScript. The reference OSS design for this exact problem.**
- Supports Valorant, Overwatch 2, CS2, League of Legends, The Finals — **[CODE]**
- A neural net detects "**consistent visual cues that signify highlights, such as specific icons or symbols that appear during kills**" — i.e. kill-feed/kill-banner iconography, **not** motion and **not** audio — **[CODE]**
- Per-game **confidence thresholds: 0.8 Valorant, 0.6 Overwatch 2, 0.7 CS2** — **[CODE]**
- Games without a stable icon cue fall back to **image recognition + OCR** (The Finals, LoL); the docs warn OCR "can be slow" — **[CODE]**
- Tunables: **framerate 4–8 fps** sampling, temporal padding before/after each highlight, and a **merge threshold** (max time between kills to treat as one highlight) — **[CODE]**
- Hard documented limitation, quoted: "**the neural network is trained to detect kills based on the default UI layout. Custom UI configurations are not supported.**" — **[CODE]**

**Audio-energy fallback: documented, and measured as weak**
- ✅ [aaroncunliffe/twitch-peak-highlight](https://github.com/aaroncunliffe/twitch-peak-highlight) — pure audio-energy clipper using librosa: `threshold = 0.85` on normalized amplitude, `frame_duration = 1.0/60.0`, `clip_bounds = 2.0` s as both padding and merge gap. **The author's own postmortem is the instructive part:** "it currently picks up any noise above the threshold, including movement or knocking the microphone", and his planned fix is to require **multiple detections within a set timeframe** rather than a single peak — **[CODE]**
- Academic counterpoint on *why* audio works in sports but may not in solo gameplay: **vocal-only audio consistently outperforms background-only audio**, and the useful audio evidence is "commentator reactions, audience responses, whistles, impacts" — i.e. the signal is **human reaction**, not the action's own sound. Highlight clips do show measurably higher RMS loudness, peak loudness and mid-frequency energy, **but with heavy distributional overlap — loudness alone is not a sufficient detector** — [arXiv:2609.17923](https://arxiv.org/abs/2609.17923) **[PAPER]**
- A commercial writeup describes scoring every second from audio energy + motion + scene cuts + kill-feed OCR + Whisper callouts, and says that for solo gameplay with no commentary it "can fall back to loudness analysis, though this often results in poor highlights since **loudness in shooters is mostly gunfire that went nowhere**" — [cutbench.com](https://cutbench.com/ai-clip-maker-for-gaming) **[THIRD-PARTY, low confidence — but the failure mode is mechanistically plausible and matches the arXiv:2609.17923 finding]**
- Fallback-by-proxy as a design pattern: `heatmapify` substitutes "comments, captions, audio and visuals" when YouTube Most Replayed is unavailable — [velvetthunder15/heatmapify](https://github.com/velvetthunder15/heatmapify) **[CODE]**

**Demo/replay parsing — event-exact, no vision at all (where a game exposes it)**
- [pnxenopoulos/awpy](https://github.com/pnxenopoulos/awpy) — Python CS2 demo parser, tick-level kills/damages, ADR/KAST/Rating; [docs](https://awpy.readthedocs.io/en/stable/) **[CODE]**
- [LaihoE/demoparser](https://github.com/LaihoE/demoparser) — CS2 replay parser for Python and JavaScript **[CODE]**
- `markus-wa/demoinfocs-golang` — canonical Go CS demo parser; searches surfaced only **forks** ([YioHoohoo](https://github.com/YioHoohoo/CS-GO-demoinfocs-golang), [visual42](https://pkg.go.dev/github.com/visual42/demoinfocs-golang)), so upstream owner/stars **unverified**
- These give ground-truth kill timestamps, but **none is a highlight generator** — a targeted search for a demo-parser-driven auto-clipper found none.
- ✅ [corp14x3/EZClips](https://github.com/corp14x3/EZClips) — Python, **0 stars, created 2025-12-11**. Generates clips from the **CS2 killfeed** using template matching plus edge detection, merging consecutive kills into one clip. Tiny and unproven, but the right shape. **[CODE]**

**Explicitly NOT found (verified negatives)**
- No repo named "Skipper" or "autoedit" matching an audio-peak clipper. **Do not cite those.**
- The non-chat OSS space is genuinely thin beyond `crispy`.

### Inferences — which methods transfer to silent, no-chat, no-facecam gameplay

**Collapse entirely (zero signal):**
- ASR → LLM transcript scoring: Opus ClipBasic, Descript "Find good clips", Vizard, Klap, 2short.ai, Riverside Magic Clips
- Speaker diarization and face-tracking-driven selection: Submagic
- Chat velocity / emote rate / chatter entropy / message similarity: LIGHTOR, hougesen, joaohenggeler, xurei, all Twitch chat bots, `!clipit` vote bots
- Viewer clip-creation rate; viewer-count change; YouTube Most Replayed
- Twitch "Clip That" voice trigger and Eklipse Voice Command (require a human speaking)
- Commentator/crowd-reaction audio (the component that actually carries the sports-audio signal)
- Streamer facial expression (the strongest single view in the PUBG ablation at 52%, vs 29% for game footage)

**Transfer directly:**
- **On-screen text and HUD reading** — kill-feed OCR, scoreboard/score-delta detection, name-card and icon template matching. This is what Opus Clip advertises ("Scoreboards, name cards, logo"), what Eklipse's engine does, what `crispy` implements, and what NVIDIA's US11154773B2 claims in detail.
- Visual action/event recognition on the game footage itself (the EMNLP video-only model, F≈68–72 on esports VODs with no chat)
- Scene-cut / shot-boundary detection; game-sound **event classification** (identifying *which* sound occurred, not how loud)
- Game telemetry / match API / demo-file parsing, where available — sidesteps perception entirely

**Transfer but degrade badly:**
- Raw audio loudness / RMS energy — dominated by continuous combat noise; "gunfire that went nowhere"; verified author postmortem says single-peak thresholding is noise-prone
- Generic optical-flow motion — dominated by camera movement uncorrelated with outcome
- Unsupervised visual novelty on game footage — **measured at 29% precision**, the worst of five views tested

**Key structural inference:** the lesson from Opus Clip, Eklipse, NVIDIA and `crispy` alike is that on low-dialogue footage the industry answer is **symbol reading, not energy measurement** — find the HUD element in which the game has already encoded its own judgement of what happened. **[INFERRED]**

**Boundary inference:** LIGHTOR's `c ≈ 20–27 s` chat lag, Twitch's "preceding 60 seconds" voice-trigger convention, clipitbot's 30 s, PogChampNet's 30 s, Google's US9884258B2 "**10 s pre-trigger + 2 s post-trigger**", and Ringer & Nicolaou's "**10 s before / 5 s after** the apex" all point the same way: **a detected event marks the end or near-end of the interesting window, not its middle.** A kill-feed entry at `t` argues for roughly `[t − 10s, t + 3s]`, then merging adjacent events. The 10/2 and 10/5 figures are sourced; the exact kill-clip numbers are my extrapolation. **[INFERRED]**

### Gaps
- No vendor publishes its actual silent-footage fallback. Opus Clip does not state what ClipAnything does with no speech *and* no recognizable sport/scene; Eklipse does not publish its per-genre tuning.
- **No published accuracy number for kill-feed OCR detection from any vendor.** The only numbers available anywhere are `crispy`'s per-game confidence thresholds (0.6–0.8), which are decision thresholds, not measured precision.
- Eklipse's 403 means its Gameplay Intelligence description could not be verified from the primary page body.
- No credible benchmark of audio-energy-only detection on *solo, commentary-free* gameplay. The gunfire claim is plausible and consistent with arXiv:2609.17923 but is not itself a measured result.

---

## Q5. Published evaluation of how well transcript/chat-based scoring transfers to gameplay

### Takeaway
Yes, and the result is unusually clean and unusually bad for the transcript/chat camp: on League of Legends Twitch VODs, a **chat-only** model reaches F≈41–43 while a plain **video-only** ResNet+LSTM reaches F≈68–72 on the same data — a **~27–29 point gap in favour of vision**, with fusion adding only ~2.5 points on top of vision. The equivalent sports-audio study shows audio and vision are nearly tied there (41.8 vs 38.0 mAP), which means **the vision advantage is specifically a property of gameplay content**, not a general result. The authors' own explanation — "highlight events may have similar animations" — is exactly why a HUD/animation detector works on gameplay and why the surrounding speech/chat is redundant.

### Cited Findings

**The direct evaluation — Fu et al., EMNLP 2017 (Twitch-LOL)** — [arXiv:1707.08559](https://arxiv.org/abs/1707.08559) / [ar5iv](https://ar5iv.labs.arxiv.org/html/1707.08559) / [ACL D17-1102](https://aclanthology.org/D17-1102/) **[PAPER]**

Two readings of the results table were obtained and **they differ slightly — flagging rather than silently picking one.** Both tell the same story; the discrepancy is most likely validation-set vs test-set, or Table 2 vs Table 3:

| Model | Modality | NALCS (EN) F | LMS (ZH) F |
|---|---|---|---|
| L-Char-LSTM | **chat only** | 43.2 / 41.5 | 39.7 |
| V-CNN-LSTM | **video only** | **72.2 / 68.3** | 69.2 |
| lvLv-LSTM | chat + video | 74.7 / 74.8 | 70.0 |

With precision/recall for one of the readings: chat-only P=0.35 R=0.51; video-only P=0.58 R=0.82; joint P=0.77 R=0.72.

- Authors' own interpretation: "**the vision only model is more accurate than the language only model**, despite the real-time nature of the comment stream", likely because "**highlight events may have similar animations**" — **[PAPER]**
- Dataset: **321 LoL championship videos** (218 NALCS English + 103 LMS traditional Chinese), 30–50 min each, avg **7,490 chat messages/video (σ≈4,922)**, ~10% of viewers chatting — **[PAPER]**
- Architecture: vision = **ResNet-34** per-frame features → LSTM unrolled 16 steps (**≈5 s window**), predicting every 10th frame; language = **character-level** 3-layer LSTM over **7-second** chat windows (character-level chosen deliberately to survive `hapy`, `happppppy`, `LOL`, `?!?!?!`, emotes, unicode); late fusion by concatenation → **2-layer MLP** — **[PAPER]**
- **Label acquisition method, directly reusable:** community-made highlight videos (5–7 min) from a single YouTube channel were aligned back into the full games by **template matching on 48-dim color histograms over 16 image regions**, with a **60-frame window** giving best alignment accuracy — **[PAPER]**
- Code/dataset: [chengyangfu/Pytorch-Twitch-LOL](https://github.com/chengyangfu/Pytorch-Twitch-LOL) **[CODE]**

**The best modality ablation on single-streamer (non-broadcast) gameplay — Ringer & Nicolaou, FDG 2018** — [arXiv:1807.09715](https://ar5iv.labs.arxiv.org/html/1807.09715) **[PAPER]**
- 11 Twitch videos (~5 h) from two **PUBG** streamers; 98 detected clips hand-labeled funny / action / social-interaction / no-highlight
- Three parallel views: face-cam and game-footage convolutional autoencoders (VGG16-like, 512 filters, **reconstruction error as the novelty score**) plus audio (STFT magnitudes band-limited to 300–3400 Hz, PCA); late-fused by 2 LSTM layers; frames in the **top 0.01% of prediction error** become clip apexes, expanded to **10 s before / 5 s after**
- **Precision of detected highlights by view: all views 77%, face+audio 74%, audio only 56%, face only 52%, game footage only 29%** — **[PAPER]**
- This is the strongest available evidence that **unsupervised visual novelty on game footage alone is nearly useless (29%)**, while the social/reaction views carry most of the signal in a facecam streaming setup.

**The sports-audio contrast, showing the gameplay result is content-specific** — [arXiv:2609.17923, Xu, Sarkar, Raj & Gunawan, "Audio for Sports Highlight Detection: A Comparative Empirical Study"](https://arxiv.org/abs/2609.17923) (submitted 2026-09-15) **[PAPER]**
- A lightweight **GRU over pretrained audio representations**, audio-only, achieves **41.79 mAP** vs visual-only GRU **37.99 mAP** (+3.80 for audio) and **outperforms several published audio-visual methods**
- Simple audio-visual fusion GRU is best across all metrics: **46.92 mAP / 91.09 Hit@1 / 46.07 Hit@K / 30.67 IoU** — fusion gains **+5.13** over audio-only and **+8.93** over visual-only
- **Vocal-only audio consistently beats background-only audio**; highlight-relevant audio evidence is commentator reactions, audience responses, whistles, impacts
- Highlight clips show higher RMS loudness, peak loudness and mid-frequency energy, **but with heavy distributional overlap — loudness alone is not a sufficient detector**

**Transcript-specific ablation** — [SVHighlights, arXiv:2606.06926](https://arxiv.org/html/2606.06926) **[PAPER]**
- First benchmark for highlight detection in extremely long sports videos: **320 videos, 8 sports, 640+ hours, every video over one hour**
- Its **TF-SELECTOR** baseline is **training-free**, combining adaptive video segmentation, **visual captions, ASR speech transcripts, and audio-volume** information
- **The ablation finding that matters:** **audio volume adds almost nothing over captions, while adding transcripts improves every metric** — transcripts carry the most highlight signal *in commentated sports*. Note this is the opposite of the gameplay result, and the reason is the same one: where a human is narrating, the narration is the signal; where a HUD is narrating, the HUD is.

**Other gameplay-specific work**
- **Ringer, Nicolaou & Walker (2022), "Autohighlight: Highlight detection in League of Legends esports broadcasts via crowd-sourced data,"** *Machine Learning with Applications* 9:100338, DOI [10.1016/j.mlwa.2022.100338](https://doi.org/10.1016/j.mlwa.2022.100338) — [open PDF](https://repository.cyi.ac.cy/bitstream/CyI/1884/1/Autohighlight%20Highlight%20detection%20in%20League%20of%20Legends%20esports%20broadcasts%20via%20crowd-sourced%20data.pdf). Contributes a **multimodal hybrid-fusion** (neither purely early nor late) extension of rank-based highlight detection, plus a **temporal smoothing step** injecting surrounding context into each decision. Labels from crowd-sourced community highlight videos. **Results table NOT extracted** (ScienceDirect 403, open PDF returned unparsed binary) — fetch locally if per-fusion-strategy mAP matters. **[PAPER, results GAP]**
- **Park, Kim et al. (2022), "Multimodal learning model based on video–audio–chat feature fusion for detecting e-sports highlights,"** *Applied Soft Computing* — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S156849462200480X). LSTM fusion of video + audio + chat; 99 games from the 2019 LCS, A/V from the LCS channel, chat via the Twitch API; billed as the first model fusing all three. **F1 numbers not retrieved (paywalled).** **[PAPER, results GAP]**
- **Liaw & Dai (2020), "Live Stream Highlight Detection Using Chat Messages," IEEE MDM 2020** — [ResearchGate](https://www.researchgate.net/publication/343522615_Live_Stream_Highlight_Detection_Using_Chat_Messages). Deep recurrent auto-encoder + dictionary learning over time-sync comments; **concept-mapped lexical chains for lag calibration**; shot ranking by combined comment intensity, emotion concentration and concept concentration. **[PAPER]**
- [CS-lol: a Dataset of Viewer Comment with Scene in E-sports Live-streaming, arXiv:2301.06876](https://arxiv.org/pdf/2301.06876) **[PAPER]**
- [Real-Time Game Highlight Detection for Data-driven League of Legends Coaching](http://www.iri.upc.edu/files/scidoc/3040-Real-time-game-highlight-detection-for-data-driven-league-of-legends-coaching.pdf) **[PAPER]**
- [Real-Time Video Highlights for Yahoo Esports](https://www.researchgate.net/publication/311066413_Real-Time_Video_Highlights_for_Yahoo_Esports) **[PAPER]** — the production system behind Yahoo's patent family (US11438637B2, see Q6)
- ["Multi-Modal Livestream Highlight Detection" PhD thesis, White Rose](https://etheses.whiterose.ac.uk/32406/1/PhD_Thesis__Revised_.pdf) — unified audio-visual-textual model; **not inspected** **[GAP]**
- ["On Broadcasted Game Video Analysis," MTAP 2016](http://mmcv.csie.ncku.edu.tw/~wtchu/papers/2016MTAP-chu.pdf) — **not inspected** **[GAP]**
- [HilAIt, Stanford CS231n 2024](https://cs231n.stanford.edu/2024/papers/hilait-automatic-video-highlighting-system-leveraging-audio-text.pdf) — audio+text+facial highlighting; **course project, low evidentiary weight**

### Inferences
- The EMNLP-2017 numbers are the strongest available answer to "does transcript/chat-style scoring transfer to gameplay": **it transfers poorly, and the reason is that the gameplay signal is in the pixels.** The same visual stereotypy that makes a kill animation easy for a CNN makes the surrounding chat/speech redundant. **[INFERRED]**
- Combining EMNLP-2017, SVHighlights and the sports-audio study: **reaction signals (chat, speech, crowd audio) are most valuable where the action is visually ambiguous, and least valuable where the game itself draws an unambiguous symbol on screen.** Gameplay with a HUD is the extreme of the latter. **[INFERRED]**
- **The 29% figure and the 68–72% figure are not in conflict** — they measure different things, and the gap between them is the single most actionable finding in this research. *Unsupervised novelty* on game footage is 29% precision; *supervised* classification on game footage is F≈68–72. On gameplay, you do not get the signal for free from saliency or novelty — you must tell the model what the event looks like (supervised labels, or an explicit HUD template). **[INFERRED]**
- For a silent local gameplay pipeline, the EMNLP video-only result is a useful sanity bar: a 2017-era ResNet-34 + LSTM over **5-second windows** was already sufficient on esports footage with **no chat, no speech, no audio, no facecam**. **[INFERRED]**
- Window sizes converge across systems on **5–10 seconds** as the scoring unit, with adjacent positives merged into clips (EMNLP 5 s; artkulak 10 s; hougesen 10 s; `crispy` 4–8 fps sampling with a merge threshold). **[INFERRED]**

### Gaps
- **No published evaluation of a *commercial* transcript-first clipper (Opus Clip, Vizard, Klap, Descript) on gameplay content against a measured ground truth.** All vendor and review claims about gameplay performance are unvalidated.
- The EMNLP-2017 result is on *esports broadcast* footage (observer camera, production HUD, professional overlay), **not** a solo player's own gameplay capture. The only solo-capture ablation (Ringer & Nicolaou, PUBG) used *unsupervised* methods and got 29% on game footage — so **supervised detection on first-person solo capture is, as far as I can find, unmeasured in the literature.** This is the most important gap for the end use case.
- The two readings of the EMNLP results table differ by ~1.7–3.9 F points; I could not resolve which is the test table.
- arXiv 2609.17923 and 2606.06926 are recent preprints; peer-review status unverified.
- Autohighlight (2022) and Park et al. (2022) results tables were paywalled/unparseable.

---

## Q6. Patents on automated highlight/clip selection from streams

### Takeaway
The patent record is where the real technical disclosure lives, and it is extensive. **Amazon's US10972524B1 is a near-complete chat-spike clipping algorithm** including an adaptive viewer-count-scaled threshold and spike-shape-based boundary selection. **NVIDIA's US11154773B2 is essentially a kill-feed OCR clipper specified end to end** — per-game config files declaring HUD regions in percentage coordinates, per-region preprocessing, icon detectors (skull = kill), and a cue-to-event correlation script. Sony, not Microsoft, holds the deep prior art on game-event highlight reels (priority 2008). Several widely-circulated attributions are wrong and are corrected below.

### Cited Findings — Amazon / Twitch (chat and engagement-driven)

- **[US10972524B1 — "Chat based highlight algorithm"](https://patents.google.com/patent/US10972524B1/en)** — Amazon Technologies, Inc.; inventor Gregory Chambers; filed 2016-06-28, granted 2021-04-06 **[PATENT]**. The Twitch-era chat-volume patent, and the most on-point patent in this whole space. Claimed pipeline:
  1. Ingest a recorded stream plus timestamped chat
  2. **Filter** chat to drop greetings, spam and abuse, with "context keywords" able to override a filter
  3. Compute a **baseline threshold of expected chat activity** — either an average messages-per-interval over the whole VOD, **or a step function of viewer count × message count** so the threshold adapts during a live broadcast
  4. Find **runs of consecutive intervals** exceeding the threshold by a specified variance
  5. Locate peaks inside each run
  6. Choose window boundaries by classifying the **shape of the chat spike**: *anticipatory* (window starts minutes **before** the peak), *reactive* (starts just before, extends minutes **after**), or *hybrid* (extended both sides)
  7. Emit one highlight file per segment
  Note: **clip-creation events are not a claimed signal** — generation is owner-requested post-broadcast.
- **[US10997240B1 — "Dynamically determining highlights of media content based on user interaction metrics and/or social media metrics"](https://patents.google.com/patent/US10997240)** — Amazon Technologies (Aschner, Kurtz, Lee, Bansal); filed 2019-03-04, granted 2021-05-04 **[PATENT]**. Computes a per-time-interval **quality score** from user-interaction data across viewing devices plus social metrics, uses **segment-by-segment manifest metadata** to resolve stream start/end times, cuts the clip, and admits it to the reel if the score clears a bar.
- **[US11386152B1 — "Automatic generation of highlight clips for events"](https://patents.google.com/patent/US11386152B1/en)** — Amazon Technologies (Arowesty, Chu, Yang, Fan); filed 2018-12-13, granted 2022-07-12 **[PATENT]**. Supervised ML fusing structured + live-stream data: social-media trend info (hashtag/comment spikes), real-time stats feeds, **crowd-noise decibel level vs. baseline**, camera-operator actions (zoom/pan/switch), and viewer app interactions (pause/rewind/volume). Each feature gets a relevance score; **event-type-specific thresholds** apply (football vs. golf use different crowd-noise cutoffs); emits start/end timestamps when the aggregate clears threshold **or multiple signals co-fire**.
- **[US10864447B1 — "Highlight presentation interface in a game spectating system"](https://patents.google.com/patent/US10864447B1/en)** — Amazon Technologies (Willette, Gilmore, Evans, George, Frazzini); filed 2015-06-29, granted 2020-12-15 **[PATENT]**. Three signal classes: **game-state telemetry** ("game highlight events" pushed by the game), **manual highlight tags** from broadcaster and spectators, and **analysis of participant audio/video/text** for emotional reaction. Tag-based highlights require "at least a threshold number or percentage" of spectator votes, **weighted for high-reputation spectators or designated commentators**; survivors assembled into personalized reels.

### Cited Findings — Google / YouTube

- **[US10575036B2 — "Providing an indication of highlights in a video content item"](https://patents.google.com/patent/US10575036B2/en)** — **Google LLC** (GuoLiang Zhu, Emmanuel Rene Saint-Loubert-Bie); filed 2016-03-02, granted 2020-02-25; EP counterpart [EP3375200A1](https://patents.google.com/patent/EP3375200A1/en) **[PATENT]**. Multi-indicator scheme worth reading closely: **video indicators** (changes in key screen regions such as **scoreboards or character status**), **audio indicators** (volume rise, commentator speech), and **user-interaction indicators including comment rate over threshold, abnormally *short* comment lengths during the spike, and viewer-count swings**. A "first indicator" confirms a highlight occurred; a "second indicator" (typically **earlier** in time) back-dates the start; further indicators set the end. Output is seek-bar markers. The short-comment-length feature is effectively the "POGGERS one-word burst" signal.
- **[US9884258B2 — "Automatic sharing of engaging gameplay moments from mobile"](https://patents.google.com/patent/US9884258B2/en)** — **Google LLC** (Jonathan Huang, Jennifer Anne Lees); filed 2013-10-08, granted 2018-02-06 **[PATENT]**. OS-level (not per-app) gameplay monitor watching interaction frequency, achievements unlocked, high scores, multiplayer match events, voice interaction and biometrics; the local monitor is tuned by a server-side "master gameplay monitor." On trigger it captures **10 s pre-trigger + 2 s post-trigger** and decides whether to auto-share.
- **[US9465435B1 — "Segmentation of a video based on user engagement in respective segments of the video"](https://patents.google.com/patent/US9465435B1/en)** — **Google LLC** (Kun Zhang, Yu He); filed 2013-08-26, granted 2016-10-11 **[PATENT]**. Scores small sequential segments from playback telemetry (**where users stop, pause, resume, rewind, fast-forward, rewatch**, plus volume changes and commenting), clusters adjacent similar-engagement segments, and cuts boundaries where engagement changes sharply. **The closest verified Google patent to the "most replayed" heatmap mechanism.**
- Also Google-assigned per search results but **not individually verified**: [US8132200B1 "Intra-video ratings"](https://patents.google.com/patent/US8132200B1/en) (aggregated per-segment votes rendered as a timeline bar graph / color gradation) and [US10754511B2 "Multi-view audio and video interactive playback"](https://patents.google.com/patent/US10754511B2/en) (a "video density bar" beside the seek bar whose density is driven partly by **how many times users replayed a moment**).
- **No patent specifically claiming the YouTube "Most replayed" heatmap was located.** Treat as unlocated rather than nonexistent.

### Cited Findings — Microsoft / Xbox

- **[US10335690B2 — "Automatic video game highlight reel"](https://patents.google.com/patent/US10335690B2/en)** — Microsoft Technology Licensing, LLC (John Schleicher); filed 2016-09-16, granted 2019-07-02 **[PATENT]**. Platform stores a per-title **highlight criterion**; when a game event matches it, the platform **triggers an API to mark the event** for reel inclusion. Pure event/telemetry contract — **no computer vision**.
- **[US11170819B2 — "Dynamic video highlight"](https://patents.google.com/patent/US11170819B2/en)** — Microsoft (Brinkman, Shivaprasad, Artemov, Sivalingam, Philipose, Bodik); filed 2019-05-14, granted 2021-11-09 **[PATENT]**. Metadata-driven: audio analysis (commentary, crowd reaction), ML visual event recognition, and **OCR/text extraction** from frames and associated pages/comments. Each candidate segment scored on three axes — **classifier confidence, specificity to the desired category, and intensity/excitement** — and highlights assembled **virtually** (a filter over scored segments) rather than rendered to new files.
- **[US11850519B2 — "Tracking in-game events and generating event reports across multiple gaming applications"](https://patents.google.com/patent/US11850519B2/en)** — Microsoft (Daniel Gilbert Kennett, Mark Edward Rabold); filed 2021-06-17, granted 2023-12-26 **[PATENT]**. A **"trained recognizer"** consumes gameplay **video, audio, and controller inputs** and emits signals for a requested event type; the same recognizer applies across different titles and sessions. Family: [US20220401843A1](https://patents.google.com/patent/US20220401843A1/en), continuation US12343639B2 (**unverified**).
- Older Microsoft context: [US20150224395A1 "Video game instant replay"](https://patents.google.com/patent/US20150224395), [US7632186B2 "Spectator mode for a game"](https://patents.google.com/patent/US7632186B2/en) (checkpoint metadata flags noteworthy events for later reel assembly). Both **unverified**.

### Cited Findings — Sony is the deep prior art, not Microsoft
- **[US8515253B2 "System and method for automated creation of video game highlights"](https://patents.google.com/patent/US8515253B2/en)** and its continuation **[US8929721B2 "Methods for identification of highlight game events and automated generation of videos for same"](https://patents.google.com/patent/US8929721B2/en)** — Sony Interactive Entertainment LLC; inventor David Cottrell; **priority 2008-02-15**; granted 2013 and 2015 **[PATENT]**. Claims: store a history of discrete gameplay events tagged with **rating metadata**; select events whose rating clears a predefined threshold **or that received enough community votes**; linearly assemble into a reel at session end, optionally with titles/chapters, and allow filtering by event type ("all flag captures", "all long-distance shots").

### Cited Findings — HUD / kill-feed / OCR-based game event detection (the most directly applicable family)

- **[US11154773B2 — "Game event recognition"](https://patents.google.com/patent/US11154773B2/en)** — **NVIDIA Corporation** (White, Clark, Otterness, Muhlestein, Sundareson, van Welzen ×2); filed 2019-10-31, granted 2021-10-26 **[PATENT]**. **Claim 1 is almost exactly a kill-clip detector:** obtain gameplay media → determine **preprocessing from a game-specific configuration** → produce processed regions → select applicable detectors → run them to produce **event cues with confidence values**. Spec details, all directly reusable:
  - Config files declare **screen regions of interest** (HUD, ammo, **kill feed**) in **percentage coordinates so they survive resolution changes**
  - Per-region preprocessing: grayscale / color isolation / HSV conversion / up- or down-scaling / denoise / **thresholding to separate text and icons from background before OCR**
  - Detectors are OCR engines, **icon detectors (e.g. skull = kill)**, and **temporal HUD-change pattern matchers**
  - A game-specific script **correlates cues into events** (skull appears → kill; ammo count drops → shot fired)
  - Output is a standardized **event log that drives automatic clip extraction by timestamp**
  - Family: [US20210129017A1](https://patents.google.com/patent/US20210129017A1/en), [US11806616B2](https://patents.google.com/patent/US11806616B2/en), US20240082704A1
- **[US11673061B2 — "Extensible dictionary for game events"](https://patents.google.com/patent/US11673061B2/en)** — NVIDIA; filed 2020-01-17, granted 2023-06-13 **[PATENT]**. Adds a hierarchical parent/child **event dictionary** and a **cue-to-event translation module** normalizing heterogeneous detector output into a common vocabulary, then generates montages with text overlays and makes clips searchable by that vocabulary. Also in-family and worth reading: **US11657627 "Focusing regions of interest using dynamic object detection for textual information retrieval."**
- **[US20170228600A1 — "Analysis of video game videos for information extraction, content labeling, smart video editing/creation and highlights generation"](https://patents.google.com/patent/US20170228600A1/en)** — **ClipMine, Inc.** (Syed, Zaidi, Savic, Ali, Javed, Yuan, Paldhe); filed 2016-02-09, priority 2014-11-14; **status: abandoned, never granted** **[PATENT application]**. Still useful prior art: Harris-Laplace + HOG features for on-screen elements, HUD parsing with OCR for alphanumeric health/score/ammo, audio speech/sound-event analysis, game-title identification by template matching, and a **"watchability score"** from game-progression deltas, achievements and proximity to objectives.
- **[US11438637B2 — "Computerized system and method for automatic highlight detection from live streaming media and rendering within a specialized media player"](https://patents.google.com/patent/US11438637B2/en)** — **Yahoo Assets LLC** (Ni, Lieb, Hawes, Song, Schillings, et al.); priority 2016-07-13, granted 2022-09-06 **[PATENT]**. Two-stage **cascade**: a *scene classifier* first separates game footage from non-game footage (commentators, crowd, player close-ups), and **only game scenes reach the highlight classifier**, which scores 0–1 (or 0–100) against a threshold using frame-level CNN features, pixel-variation/activity measures, on-screen game status indicators, and game log metadata when available; processes HLS segments as they arrive for live operation. Family: US10390082, [US10681391B2](https://patents.google.com/patent/US10681391B2/en), US20200275133A1, US12250415B2.
- **[US11350169B2 "Automatic trailer detection in multimedia content"](https://patents.google.com/patent/US11350169B2/en)** — **Netflix, Inc.** (Dong Liu, Lezi Wang, Rohit Puri); filed 2020-11-11, granted 2022-05-31 **[PATENT]**. Weak supervision by **shot-matching official trailers back to the full title** to learn what a "key moment" looks like. The weak-label trick is directly transferable to kill-clip labeling and is the patent-side analogue of the EMNLP-2017 template-matching label method and of PogChampNet.
- Peripheral, pose-based, physical sports (completeness only): [US11856318B2](https://patents.google.com/patent/US11856318B2/en), **Maiden AI, Inc.**, priority 2021-04-27, granted 2023-12-26 — detects a "trigger movement" via body-pose ML in a region of interest, ends the clip on a second trigger movement or a fixed per-trigger duration, backed by a **rolling pre-roll buffer**.

### Inferences
- **Amazon's US10972524B1 and Google's US10575036B2 together constitute the best published specification of chat-spike clipping that exists** — more detailed than anything in the product docs of either company. Both independently claim the same three structural ideas that OSS also converged on: filter spam before counting, scale the threshold to the stream's own baseline/audience size, and use a *separate, earlier* indicator to back-date the clip start. **[INFERRED]**
- **NVIDIA's US11154773B2 + US11673061B2 are, functionally, the published blueprint for a local kill-clip detector.** Percentage-coordinate HUD regions, per-region thresholding before OCR, icon detectors with confidence values, and a cue→event correlation layer is exactly the architecture `crispy` implements and exactly what survives the no-speech/no-chat case. For a project building a local gameplay clipper, this is the most useful single document found in this entire research. **[INFERRED]**
- Yahoo's two-stage cascade (scene classifier gates the highlight classifier) is a cheap and transferable reliability pattern: reject non-gameplay frames (menus, loading, replays, scoreboards-only) before scoring, rather than asking one model to handle both. **[INFERRED]**
- Microsoft's and Sony's approach is telemetry-first (the game declares its own events via API), which is unavailable to anyone capturing console output externally. The CV-based patents (NVIDIA, ClipMine, Yahoo) are the ones that apply to external capture. **[INFERRED]**

### Gaps and corrections
- **I could not verify any patent assigned to *Twitch Interactive, Inc.* by name** (Justia blocks fetching; the Google Patents assignee browser is a JS app). Twitch IP in this area appears to be filed under **Amazon Technologies, Inc.**
- **No patent found claiming *user clip-creation rate* as the triggering signal.** The idea appears in the academic literature (LIGHTOR uses viewer seek positions, not clip creation) but no verified patent number supports it. Absence of finding, not proof of absence.
- **No patent found covering the YouTube "Most replayed" heatmap specifically.**
- **Not individually verified** (from search-result text only): US8132200B1, US10754511B2, US20150224395A1, US7632186B2, US12343639B2. US10997240 verified via search metadata only; the patent page returned a bare URL.
- **Two misattributions to correct, both circulating in search results:**
  - **US10721499B2 and US10474717B2 are Twitter / X Corp, not Amazon.** US10474717B2 (Kevin Quennesson) is still worth citing: it segments broadcasts into **3-second clips**, classifies each with LSTM models, weights class confidences by hand-set per-class weights (e.g. "outdoor ×1.0, selfies ×0.5"), boosts scores on engagement spikes, and takes top-N re-sorted temporally.
  - **US11438637B2 is Yahoo, not Twitch and not Microsoft**, despite several search engines attributing it otherwise.

---

## Cross-cutting summary for the end use case (silent gameplay, no chat, no facecam)

### Takeaway
Of everything surveyed, almost nothing from the transcript-first or crowd-signal families survives. What survives is a single architecture, independently arrived at by Opus Clip (ClipAnything's "Scoreboards, name cards, logo"), Eklipse (kill feed + scoreboard), NVIDIA (US11154773B2), and the one mature OSS project (Flowtter/crispy): **read the symbol the game already draws on screen, at low frame rate, in a fixed percentage-coordinate region, with a per-game confidence threshold, then pad and merge.**

### Cited anchors for that conclusion
- Opus Clip needed a separate model for low-dialogue content, and that model's advertised capability includes reading "Scoreboards, name cards, logo" — [Opus Clip](https://www.opus.pro/clipanything) **[COMPANY]**
- Eklipse: detection "is strongest where there are events to read like kill feeds and scoreboards", and voice command "pays off hardest where there is no kill feed" — [Eklipse](https://blog.eklipse.gg/tools/ai-clip-maker-gaming.html) **[COMPANY]**
- NVIDIA US11154773B2 specifies percentage-coordinate HUD regions, per-region preprocessing/thresholding before OCR, icon detectors (skull = kill) with confidence values, and a cue→event correlation script — [patent](https://patents.google.com/patent/US11154773B2/en) **[PATENT]**
- Flowtter/crispy implements exactly this at 4–8 fps with per-game confidence 0.6–0.8 and a kill-merge threshold, and warns that non-default UI layouts break it — [repo](https://github.com/Flowtter/crispy) **[CODE]**
- Supervised vision on gameplay reaches F≈68–72 with no chat, speech or audio; **unsupervised visual novelty on game footage alone reaches only 29% precision** — [EMNLP 2017](https://aclanthology.org/D17-1102.pdf); [Ringer & Nicolaou 2018](https://ar5iv.labs.arxiv.org/html/1807.09715) **[PAPER]**
- Audio loudness is a real but overlapping signal and a single-peak threshold is noise-prone by the author's own postmortem — [arXiv:2609.17923](https://arxiv.org/abs/2609.17923) **[PAPER]**; [aaroncunliffe](https://github.com/aaroncunliffe/twitch-peak-highlight) **[CODE]**
- If crowd signal is ever available, use it **offline as a label generator** and deploy vision-only — the PogChampNet pattern, and the patent-side analogue in Netflix US11350169B2 — [PogChampNet](https://medium.com/@farzatv/pogchampnet-how-we-used-twitch-chat-deep-learning-to-create-automatic-game-highlights-with-only-61ed7f7b22d4) **[THIRD-PARTY, 403-blocked]**; [Netflix patent](https://patents.google.com/patent/US11350169B2/en) **[PATENT]**
- Event-to-clip padding conventions from sourced systems: **10 s pre / 2 s post** (Google US9884258B2), **10 s before / 5 s after** apex (Ringer & Nicolaou), **preceding 60 s** (Twitch voice trigger), **30 s** (clipitbot, PogChampNet), **2 s** padding and merge gap (aaroncunliffe) **[PATENT/PAPER/COMPANY/CODE]**

### Largest remaining gap for this use case
**Supervised HUD/kill-feed detection on first-person solo console capture is unmeasured in the public literature.** Every quantitative result found is on either esports broadcast footage (production overlay, observer camera) or facecam streaming setups. There is no published precision/recall for the exact configuration of a silent PS5 gameplay recording with a default game HUD and no chat, speech, or facecam.
