# Commercial Gaming Highlight-Clipping Products: Detection Mechanisms

**Research date: 2026-11-04.** Evidence labels used throughout:

- **[STATED]** — the company says this in its own docs, help centre, feature page, or engineering blog.
- **[PATENT]** — appears in a granted patent assigned to the company (or an adjacent company).
- **[PRESS]** — journalism or a technical interview, i.e. a company claim filtered through a reporter.
- **[3P-LOW]** — third-party SEO / affiliate / competitor-comparison content. Treat as weak; these pages are written to rank, often by direct competitors, and frequently carry unsourced numbers.
- **[INFER]** — my inference from the above, flagged as such.

**Important methodological caveat:** every `eklipse.gg` and `blog.eklipse.gg` URL returned HTTP 403 to direct fetch. All Eklipse claims below come from search-engine summaries of those pages, not from reading them. I have cited the canonical Eklipse URLs, but the quoting is second-hand and should be re-verified before being treated as a hard company statement.

---

## Which detection signals does each product use?

### Takeaway

The industry splits cleanly into two families: **event-API consumers** (Medal, Overwolf/Outplayed, Nvidia Highlights) that take a structured "kill happened" signal from the game, hook, or platform and simply cut video around a timestamp with essentially zero perception cost; and **pixel/audio analysers** (Eklipse, Powder, Sizzle, FragCut, the defunct Athenascope) that read the rendered frame — HUD OCR, icon template matching — plus audio energy, laughter/shout detection, speech transcription and chat-rate spikes, and fuse them into a score. Nobody in the second family publishes an architecture; the most concrete published mechanism for pixel-based detection anywhere is Nvidia's own patent, not a clipper's blog.

### Cited Findings

**Medal.tv — event APIs only, no perception**
- [STATED] "The instant the game reports a kill, ace, goal, or win, Medal saves the seconds around that moment as a clip." Medal auto-clips "any PC game that reports its events, through the game's replay system or through events its developer sets up with Medal" — [Medal Auto Clipping](https://medal.tv/auto-clipping)
- [STATED] Three event sources: native game replay systems; developer integrations configured via the Medal developer portal; and custom per-server events for GTA V (FiveM) and Minecraft, where "each server sets its own events." Rocket League and R.E.P.O. require a Medal plugin — [Medal Auto Clipping](https://medal.tv/auto-clipping)
- [STATED] The developer integration is explicitly a webhook, not an in-process SDK: "Auto clipping happens in the Medal app on the player's PC, not inside your game" — the game sends "one small web request" and Medal cuts from the buffer it is already recording. Developers define event name, icon, and pre/post buffer length in the portal and get an API key — [Medal Auto-Clipping API for Developers](https://medal.tv/developer/auto-clipping)
- [STATED] No pixel detection, OCR, or audio analysis is described anywhere in Medal's auto-clipping documentation. Auto clipping "runs on the same recorder as instant replay. The difference is that in a supported game, the game event saves the clip instead of your hotkey." Windows only; not available on iOS/Android — [Medal Support: Automatic Event Detection](https://support.medal.tv/support/solutions/articles/48001167701-what-is-automatic-event-detection-auto-clipping-); [Medal Auto Clipping](https://medal.tv/auto-clipping)
- [PATENT] Medal *does* use HUD-region computer vision, but for a different purpose: matching players who were in the same match. US11872495B1 (assignee Medal BV) captures a frame, extracts "at least one pre-determined section of the image in the screen grab" chosen as a "common display area visible to all players" (health bars, timers, player indicators — explicitly static HUD rather than player-specific viewpoint), hashes that region via a "computer vision processing routine," optionally salted with a synchronised timestamp, at intervals of e.g. 1, 5 or 60 seconds, and compares hashes server-side to identify co-players — [US11872495B1](https://patents.google.com/patent/US11872495B1/en)

**Overwolf / Outplayed — GEP event stream**
- [STATED] Overwolf's Game Events Provider exposes four feature categories for CS2 (`gep_internal`, `live_data`, `match_info`, `chat`) and fires discrete events: `match_start`, `match_end`, `kill`, `death`, `assist`, `round_start`, `round_end`, `kill_feed` (with attacker, victim, weapon, and metadata such as headshot), plus in-game and lobby `chat` messages — [Overwolf GEP: Counter-Strike 2](https://dev.overwolf.com/ow-native/live-game-data-gep/supported-games/counter-strike-2/)
- [STATED] For Marvel Rivals, GEP exposes events `match_start`/`match_end`, `round_start`/`round_end`, `kill` (returns kill count), `death`, `assist`, and `kill_feed` with "character IDs/names, and whether each is a teammate"; plus info-updates `roster_xx` (names, character IDs, K/D/A, ultimate charge, team), `player_stats` (damage dealt, damage blocked, accuracy, healing), `match_outcome`, `objective_progress`, `ability_cooldown_X`, `scene` (Lobby/Ingame). A compliance note records that NetEase policy "prevents giving users confidential information like damage and healing statistics" — [Overwolf GEP: Marvel Rivals](https://dev.overwolf.com/ow-native/live-game-data-gep/supported-games/marvel-rivals)
- [STATED] Event payloads are often minimal. For PUBG, Rainbow Six Siege and Deadlock the `kill` event "has null event data" and simply fires when the local player kills an enemy; for CS2 and Apex Legends it carries a running total — [Overwolf GEP: PUBG](https://dev.overwolf.com/ow-native/live-game-data-gep/supported-games/playerunknowns-battlegrounds); [Overwolf GEP: Rainbow Six Siege](https://dev.overwolf.com/ow-native/live-game-data-gep/supported-games/rainbow-six-siege/); [Overwolf GEP: Deadlock](https://dev.overwolf.com/ow-native/live-game-data-gep/supported-games/deadlock/)
- [STATED] Outplayed's Highlights mode "will automatically detect game events and create highlight clips for those events," and the Highlights/Full Match capture modes "depend on game events" — i.e. automatic detection exists only where Overwolf has integrated event support. Users set pre-roll and post-roll length per event — [Overwolf Support: How to use Outplayed](https://support.overwolf.com/support/solutions/articles/9000284659-how-to-use-outplayed)
- [STATED] The *developer-facing* Game Events SDK is a cooperative integration: the game calls `owgame_events_trigger_event` for transient occurrences and `owgame_events_set_info_key` for persistent state (health, player name), batched in transactions, shipped as C/C++ headers, a C# P/Invoke wrapper and `libowgameevents.dll`. The SDK documentation makes **no mention** of memory reading, log parsing, or reverse engineering — [overwolf/game-events-sdk](https://github.com/overwolf/game-events-sdk)
- [3P-LOW] A third-party technical article asserts the non-cooperative path is memory inspection: Overwolf "pioneered" directly inspecting a game's running memory to get "the internal representation of in-game notifications and events in their purest form," which is "faster and more reliable than computer vision" with "no expensive image analysis," but is "the same method used by most cheat programs like FPS aimbots, a violation of games' terms of service." It cites Call of Duty's June 2021 update blocking Overwolf entirely for "over a month" — [Hypetrigger: Three methodologies for automated video game highlight detection](https://hypetrigger.io/article/)
- [STATED] Anti-cheat demonstrably gates GEP: when FACEIT anti-cheat is active it "may block Overwolf from accessing game events" in titles such as CS2, disabling event-driven features — [Overwolf Support: Using Overwolf and FACEIT](https://support.overwolf.com/support/solutions/articles/9000233364-using-overwolf-and-faceit)
- [3P-LOW] Overwolf renders overlays by injecting a Chromium layer into the game process, in user mode with no kernel driver — [Vera Field Guide: Overwolf](https://www.veraproject.xyz/field-guide/processes/overwolf)

**Nvidia Highlights / ShadowPlay — game-declared events, now legacy**
- [STATED] The SDK is asynchronous and polled: "Every command is asynchronous while the game runs and issues calls against the Highlights SDK. A Poll function must be called periodically to get these callbacks from the GFE SDK." Events "include things such as kills, deaths, victories, or specific in-game milestones **defined by the game developer**" — [Nvidia: Implementing NVIDIA Highlights in UE4](https://developer.nvidia.com/blog/implementing-nvidia-highlights-plugin-unreal-engine-4)
- [STATED] Nvidia's own Highlights landing page describes capture ("key moments, clutch kills, and match-winning plays", 15-second GIF export) but gives **no detection mechanism at all** — because there is none on Nvidia's side; the game decides. The page now carries the notice: "This is a legacy SDK. Developers may download and continue to use, but it is no longer supported." Requires Maxwell (GTX 9xx) or later plus GeForce Experience — [NVIDIA Highlights](https://developer.nvidia.com/highlights)
- [3P-LOW] Coverage of the structural limits: requires per-game developer adoption; AMD users are excluded because "AMD's replay recording software does not have any support for automatic highlight recording"; Xbox and PlayStation players cannot use it; "computer vision approaches are universal" by contrast — [Hypetrigger](https://hypetrigger.io/article/)

**Eklipse — pixel + audio + chat fusion (cloud)**
- [STATED, second-hand via search summary; page 403s] Eklipse describes "Object Detection and Optical Character Recognition (OCR)" over the stream to extract kills, boss fights and similar moments — [Eklipse Help: How does Eklipse work?](https://eklipse.gg/help/how-does-eklipse-work/)
- [STATED, second-hand] Three signal families: visuals ("spotting key in-game actions and on-screen events"), audio ("catching hype moments like shouts, laughs, and fast commentary"), and game data ("reading kills, wins, and other key stats from supported titles") — [Eklipse Help: How does the AI actually detect a highlight?](https://eklipse.gg/help/how-does-the-ai-actually-detect-a-highlight-in-my-stream/)
- [STATED, second-hand] Chat is a fourth signal: the engine "analyzes gameplay video, audio, and chat simultaneously, rating kills, clutches, comebacks, and chat surges with a 'virality score'" — [Eklipse: AI Highlights](https://eklipse.gg/features/ai-highlights/)
- [STATED, second-hand] "Gameplay Intelligence," rolled out to Eklipse Premium on every VOD from 1 June 2026, replaces single-trigger cutting: "Advanced Moment Detection scores candidate moments instead of cutting around a single trigger," with "per-genre tuning" running "different detection logic for FPS, BR, MOBA, tactical, and strategy games." The June 2026 rebuild also extended detection to just-chatting, IRL and podcast content — [Eklipse blog: How Gameplay Intelligence Works](https://blog.eklipse.gg/streaming-tips/how-gameplay-intelligence-works-2.html)
- [STATED, second-hand] The same release claims it reduces false positives "by separating voice from in-game audio and weighting action density on screen" — [Eklipse blog: What Gameplay Intelligence Actually Changes](https://blog.eklipse.gg/streaming-tips/gameplay-intelligence.html)
- [STATED, second-hand] A non-automatic signal also exists: a voice command feature where a streamer says "Clip it!" to mark the stream in place — [Eklipse: Voice Command](https://eklipse.gg/features/voice-command/)
- [STATED, second-hand] Eklipse's own failure taxonomy: missed moments occur when "the stream may have been processed with an older AI model or important gameplay signals were hidden by overlays"; spurious clips mean "the AI locked onto less important visual or audio cues." This is a direct admission that detection is pixel-region-dependent and overlay-fragile — [Eklipse Help: Why is the AI not capturing my kills?](https://eklipse.gg/help/why-is-the-ai-not-capturing-my-kills-wins-or-other-key-moments/)

**Powder.gg — multimodal, ~40 per-game models, on-device (now defunct)**
- [PRESS] "Over 40 proprietary game-specific AI models," covering Fortnite, Valorant, Apex Legends, Call of Duty, Rocket League, Fall Guys, Elden Ring, Among Us, CS2. Signals: in-game performance spikes (kills, assists, victories); **laughter recognition**; **voice fluctuation / shouting detection** (shipping mid-December 2023); **chat activity spikes** via a "Community Hype" feature; and speech-to-text transcription with keyword search (shipping ~December 2023) — [TechCrunch, 20 Nov 2023](https://techcrunch.com/2023/11/20/powder-an-ai-clipping-tool-for-gaming-can-detect-when-a-creator-yells-during-a-stream/)
- [STATED, company blog] "Powder created a state-of-the-art AI detection technology that identifies gaming highlights based on peak moments in the game (a goal in FIFA or a kill in Fortnite) as well as emotional reactions of the streamers (screams, laughs, cries, etc.)". The same post states: "As a deep tech company, Powder invests in **self-supervised machine learning** techniques for highlight detection, surpassing state-of-the-art" — [Powder: Building the Camera of the Metaverse, 7 Oct 2021](https://blog.powder.gg/2021/10/07/powder-building-the-camera-of-the-metaverse/) (Medium mirror: [powderapp.medium.com](https://powderapp.medium.com/powder-building-the-camera-of-the-metaverse-168da8ca26fa), which 403s)
- [STATED] Powder's EU CORDIS project description: "the only app offering a complete turnkey solution to automatically detect the best gaming moments, earn rewards from quests and challenges, and compete with other gamers" — [CORDIS project 190156232](https://cordis.europa.eu/project/id/190156232)
- [3P-LOW] A tool-directory profile describes the fallback hierarchy: "audio emotion, chat spikes, transcription and keyword search **when game-specific detection was unavailable**" — i.e. per-game visual models first, generic multimodal second — [The Rundown: Powder](https://www.therundown.ai/tools/powder)
- [PRESS] Founder framing of why multimodal: Barthélémy Kiss said "the best moments when gaming is highly subjective and need to be reflected with several different perspectives that extend beyond the gameplay itself" — [TechCrunch, 20 Nov 2023](https://techcrunch.com/2023/11/20/powder-an-ai-clipping-tool-for-gaming-can-detect-when-a-creator-yells-during-a-stream/)

**Sizzle — server-side video + audio + chat, no client software**
- [STATED] "AI analyzes the video, audio, and chat of your livestreams to automatically determine the best moments." Sizzle says it identifies when big plays occur, when commentators are excited, when audiences are excited, and funny moments, and breaks moments down per individual player — [Sizzle: Esports Leagues](https://www.sizzle.gg/esports-leagues)
- [STATED] Explicit architectural commitment: "We do NOT have any software in any player's PC" — detection is entirely from the public Twitch/YouTube stream — [Sizzle: Esports Leagues](https://www.sizzle.gg/esports-leagues)
- [STATED/PRESS] Sizzle "automatically creates gaming and esports highlights in real time, directly from Twitch and YouTube streams," with no installation on the player's side — [MarkTechPost, 25 May 2022](https://www.marktechpost.com/2022/05/25/meet-sizzle-a-california-based-startup-that-leverages-ai-to-automatically-create-gaming-highlights-from-twitch-and-youtube-videos/)
- [STATED] Claimed personalisation mechanism is pointer-based rather than render-based: "patented technology to personalize highlights to millions or billions of fans, all without creating any new video," using "pointers and timestamps back to the source video" — [Sizzle info page](https://www.sizzle.gg/info/index.html); [Sizzle: Esports Leagues](https://www.sizzle.gg/esports-leagues)
- [PRESS] $5M seed led by White Star Capital, May 2022; customers include PUBG Esports Americas, Free Fire LatinoAmerica League, and Twitch — [Sizzle blog](https://www.origin.sizzle.gg/blog/?p=124); [Esports Trade Association, 14 Jan 2025](https://esportsta.org/2025/01/14/ai-highlights/)

**FragCut — cloud, computer vision, viral scoring**
- [STATED] "Computer vision to identify kills, clutches, team wipes, and funny moments" with "Viral Potential Scoring"; burned-in subtitles via speech-to-text; "AI analyzes gameplay visuals, audio cues, and game-specific actions (headshots, multi-kills)". Browser-based, no install; accepts Twitch, OBS or local recordings as "universal video input" — [FragCut: Valorant](https://fragcut.io/games/valorant); [FragCut: CS2](https://fragcut.io/games/counter-strike-2)
- [STATED] Per-game detection targets are listed per title, including non-kill-feed games: for GTA V it claims auto-detection of "heists, police chases, stunt sequences, and GTA RP highlights" — [FragCut: GTA V](https://fragcut.io/games/grand-theft-auto-v)

**Athenascope — HUD computer vision, cloud (defunct)**
- [3P-LOW/PRESS] "The tool captures the gamer's screen and recognizes indicators in the game's user interface that communicate important events happening in-game: kills and deaths, goals and saves, wins and losses," via "computer vision deep learning" — [Hypetrigger](https://hypetrigger.io/article/); [TechCrunch, 8 Feb 2019](https://techcrunch.com/2019/02/08/athenascope-nabs-2-5m-seed-led-by-first-round-to-bring-gamers-ai-edited-highlight-reels/)
- [3P-LOW] Why HUDs specifically: game UIs are ideal CV targets because the information is "high-contrast, clear and unobscured" at "predictable, fixed locations on the screen" — [Hypetrigger](https://hypetrigger.io/article/)
- [PRESS] $2.5M seed led by First Round, Feb 2019; team of Silicon Valley big-tech alumni; roadmap included multi-perspective replay by syncing footage from other Athenascope users in the same match, and a "computer vision coach" product — [TechCrunch, 8 Feb 2019](https://techcrunch.com/2019/02/08/athenascope-nabs-2-5m-seed-led-by-first-round-to-bring-gamers-ai-edited-highlight-reels/)

**Adjacent / other**
- [STATED] Streamlabs Replay (formerly Highlighter) "includes automated clipping powered by Logitech G HUB technology" — a hardware-vendor event path analogous to Nvidia's — [Streamlabs Highlighter](https://streamlabs.com/highlighter)
- [3P-LOW] AMD: ReLive provides hotkey save and rolling instant replay inside Radeon Software, but I found **no official AMD automatic-highlight event API**; automatic capture for AMD users is community-built (e.g. ClipRing for CS2) — [ClipRing](https://github.com/michpese/ClipRing); [AnandTech ReLive coverage](https://at-web1.www.anandtech.com/show/11664/amd-radeon-software-crimson-relive-edition-1772/3)
- [3P-LOW] A marketing page (vendor unidentified in the snippet, surfaced alongside Powder material) claims models that "flag kills, clutch plays, boss kills, wipes, reactions, and chat spikes — the moments your audience actually clips, not just loud audio peaks," explicitly positioning against naive audio-energy peak-picking — [Wayin AI Gaming Clip Generator](https://wayin.ai/tools/ai-gaming-clip-generator/)

### Inferences

- [INFER] The *only* signals in the brief's list that I found no commercial product using are **facecam emotion detection** (vision-based) and **controller/input activity as a clipper's own signal**. Powder, Eklipse and Sizzle all do emotion via **audio** (laughter, shouting, vocal energy) rather than webcam facial analysis. Controller input appears only as a claimed detection signal in a Microsoft patent (below), not in any shipping clipper's materials.
- [INFER] Medal and Outplayed are architecturally *not* highlight detectors at all — they are event-triggered ring-buffer dumpers. Neither scores or ranks moments; the game's definition of "event" is the entire notion of "highlight." This is why their quality failure mode is binary (clip or no clip) while Eklipse/Powder's is ranking quality (wrong moment, bad boundaries).
- [INFER] Medal's patented HUD-region hashing (US11872495B1) is a technically convenient building block for highlight detection too — a cheap, local, per-N-second frame signature over a fixed HUD rect — but Medal's public materials do not claim to use it that way.

### Gaps

- **"Clipster"**: I could not identify any gaming highlight-clipping product by this name. Searches for "Clipster" surface only Eklipse/Streamlabs/Insights.gg and the unrelated broadcast product Clipster by Rohde & Schwarz. Either the name in the brief is wrong, the product is too small to index, or it is a renamed product. No findings.
- **"Allie" / "Ally" AI clippers**: searches returned nothing matching. Only generic AI clip generators (FlexClip, Vmaker, Wayin, Revid, LumiClip, Short.ai) appeared. Cannot confirm such a product exists under that name.
- **Steam as an event source**: no product documents using Steam APIs (Steam Rich Presence, achievements, or Game State Integration) as a highlight trigger. CS2's native Game State Integration is the obvious candidate and Medal's "game's replay system" language is consistent with it, but no source states this explicitly.
- **Riot/Valorant APIs**: no product states it uses Riot's official APIs for live highlight triggers. Riot provides no public live in-match event API for Valorant, which is why Overwolf's Valorant GEP support and Medal's Valorant auto-clipping are notable but unexplained. Mechanism unconfirmed.
- Whether Overwolf's non-cooperative GEP titles use memory reading, log tailing, or network inspection is **not stated by Overwolf anywhere I could find**. The only assertion is the third-party Hypetrigger article. The FACEIT-blocks-CS2 evidence is consistent with in-process access but does not prove memory reads.

---

## Local (on-PC) vs cloud detection, and compute-cost implications

### Takeaway

Event-API products (Medal, Outplayed, Nvidia) run entirely locally and have near-zero detection compute because they do no perception. Pixel-analysing products split: Powder ran its models **on-device on Windows**, while Eklipse, Sizzle, FragCut and the defunct Athenascope all run **cloud-side after upload** — and Eklipse's own queue design is the clearest public evidence that cloud video analysis is GPU-expensive enough to require rationing.

### Cited Findings

- [STATED] Medal: detection and capture are local; "Auto clipping happens in the Medal app on the player's PC, not inside your game"; clips are "saved on device" in the Medal library; instant replay runs continuously alongside auto clipping on Windows with NVIDIA, AMD or Intel GPUs — [Medal Developer](https://medal.tv/developer/auto-clipping); [Medal Auto Clipping](https://medal.tv/auto-clipping)
- [STATED] Outplayed: detection is local, via the Overwolf client consuming GEP in real time; capture modes are configured with local pre/post buffers — [Overwolf Support: How to use Outplayed](https://support.overwolf.com/support/solutions/articles/9000284659-how-to-use-outplayed)
- [STATED] Nvidia Highlights: capture happens in the GPU/driver path via GeForce Experience, with no upload in the detection loop — [Nvidia UE4 Highlights plugin](https://developer.nvidia.com/blog/implementing-nvidia-highlights-plugin-unreal-engine-4). [3P-LOW] This yields "lightning fast and high quality video capture" without internet upload delays — [Hypetrigger](https://hypetrigger.io/article/)
- [STATED, second-hand] Eklipse is fully cloud: it "runs entirely in the cloud after your stream ends. The only resource it uses is your VOD upload bandwidth after the session is over" — [Eklipse blog review compilation](https://blog.eklipse.gg/featured/eklipse-gg-review.html)
- [STATED, second-hand] Eklipse's explicit cost statement and rationing design: "Processing video requires heavy GPU power." Free users "share a massive pool of GPU resources" in a Standard Queue; Premium members "bypass the standard line and get access to dedicated high-speed GPU servers." On the free plan during peak evenings/weekends "your VOD may sit in a processing queue for several hours" — [Eklipse Help: Why is my stream processing stuck?](https://eklipse.gg/help/why-is-my-stream-processing-stuck-or-taking-longer-than-usual/)
- [STATED] Sizzle is cloud by design and by claim: "We do NOT have any software in any player's PC" — [Sizzle: Esports Leagues](https://www.sizzle.gg/esports-leagues)
- [STATED] FragCut is cloud and browser-based with no install, taking Twitch/OBS/local uploads — [FragCut: Valorant](https://fragcut.io/games/valorant)
- [3P-LOW] Powder ran locally: "a Windows app that used **local AI** to find highlights in gameplay recordings and completed Twitch, YouTube or Kick streams"; "a free, on-device Windows app for about 40 games" — [The Rundown: Powder](https://www.therundown.ai/tools/powder)
- [3P-LOW] Athenascope was cloud: "Raw video is uploaded to Athenascope's server cluster — affectionately named 'Athena' — and after processing, the highlights are delivered to the user's inbox for downloading" — [TechMikeWi, 11 Apr 2020](https://techmikewi.com/2020/04/11/machine-learning-based-video-scrubbing-for-highlight-moments-with-athenascope/)
- [3P-LOW] The published cost framing of the two approaches: local CV is "computation-heavy" to run while gaming; cloud CV requires uploads that introduce "round trip processing time and quality loss," and "infrastructure maintenance represents significant ongoing costs." Memory-based event reading has "no expensive image analysis" — [Hypetrigger](https://hypetrigger.io/article/)
- [PATENT] Nvidia's patent is explicit that the same detector can be deployed either way: "event detection can be performed on a player device, on the game server or a related device, by a third party service or resource provider from a provider environment" — [US12288404B2](https://patents.google.com/patent/US12288404B2/en)

### Inferences

- [INFER] Eklipse's tiered-GPU-queue design is the single best public datapoint on commercial per-VOD cost for cloud highlight detection: a business sufficiently GPU-bound that it uses queue position as the primary paywall. A detector cheap enough to run on commodity CPU would not be monetised this way.
- [INFER] Powder's on-device choice plus ~40 per-game models implies small, cheap, specialised models (per-game HUD region classifiers / template matchers) rather than one large general video model — a large VLM could not have run on-device alongside a game on 2023 consumer hardware. This is inference; Powder never published architecture.
- [INFER] Powder failing to find a sustainable business model while running *locally* (i.e. with near-zero marginal inference cost) suggests the binding constraint for this product category is per-game model maintenance and distribution/retention, not GPU cost.

### Gaps

- No product publishes concrete compute figures: no GPU-seconds per VOD-hour, no realtime-factor (e.g. "analyses 1 h of 1080p60 in X minutes on a T4"), no VRAM or model-size numbers. None.
- Eklipse's "20–60 minutes after a stream ends" is wall-clock including queueing, not compute time, so it cannot be converted into a cost estimate.

---

## ML architectures named in company materials

### Takeaway

Essentially none. Across all the clippers, the only named ML technique is Powder's "self-supervised machine learning" (a training paradigm, not an architecture) and Athenascope's "computer vision deep learning." No clipper names a CNN backbone, an audio event detection model, a transformer, CLIP-style embeddings, or an LLM/VLM anywhere. The named architectures in this space all come from **patents by hardware/platform companies**, not from the clipping startups.

### Cited Findings

- [STATED] Powder: "self-supervised machine learning techniques for highlight detection, surpassing state-of-the-art" — the most specific ML claim any clipper makes, and it names no architecture — [Powder blog, 2021](https://blog.powder.gg/2021/10/07/powder-building-the-camera-of-the-metaverse/)
- [PRESS] Powder: "over 40 proprietary game-specific AI models, including audio analysis and laughter detection, as well as standalone models for popular titles" — model *inventory*, no architecture — [TechCrunch, 20 Nov 2023](https://techcrunch.com/2023/11/20/powder-an-ai-clipping-tool-for-gaming-can-detect-when-a-creator-yells-during-a-stream/)
- [STATED, second-hand] Eklipse names only techniques, not architectures: "Object Detection and Optical Character Recognition (OCR)" — [Eklipse Help](https://eklipse.gg/help/how-does-eklipse-work/). "Gameplay Intelligence," "Advanced Moment Detection," "virality score" and "per-genre tuning" are product names, not architectures — [Eklipse blog](https://blog.eklipse.gg/streaming-tips/how-gameplay-intelligence-works-2.html)
- [STATED] Sizzle says only "deep AI systems that analyze video, audio, and chat" — [Esports Trade Association, 14 Jan 2025](https://esportsta.org/2025/01/14/ai-highlights/); [Sizzle: Esports Leagues](https://www.sizzle.gg/esports-leagues)
- [STATED] FragCut says only "computer vision," "AI," and "speech-to-text" — [FragCut: Valorant](https://fragcut.io/games/valorant)
- [STATED] Medal names no ML at all for auto-clipping; its patent names only "computer vision processing routine[s]" producing hash values — not a learned model — [US11872495B1](https://patents.google.com/patent/US11872495B1/en)
- [PATENT] **Nvidia US12288404B2** is the richest named-mechanism source in the whole space: "Various motion, optical flow, audio, and other such detectors, machine learning models, or trained neural networks can be used to analyze a media stream." Concretely it specifies HUD region identification → **4× bicubic-interpolation upscaling of the selected region** → thresholding/binarization and background removal → OCR character decode plus icon/template matching (skull counts, health bars, score indicators), with optical flow for avatar/environment motion and audio pattern recognition (e.g. hit-impact sounds) as additional detectors. Upscaling is applied *before* binarization because 10–15 px HUD text has anti-aliasing-degraded edges, and is region-limited to bound compute versus full-frame upscaling — [US12288404B2](https://patents.google.com/patent/US12288404B2/en)
- [PATENT] **Microsoft US11850519B2** names ML event recognisers trained on "consumable gaming content" — video frames as primary signal, audio as confirmation, **controller inputs as supplementary signal**, with an "area of interest" parameter specifying the screen region where an event occurs. It explicitly contrasts this with back-end data or source code access — [US11850519B2](https://patents.google.com/patent/US11850519B2/en)
- [PATENT] **EA US10346942B2** names a non-ML, GPU-resident mechanism: a cost-ordered cascade that picks "the least resource-consuming or least intrusive method" per frame among simple pattern matching, per-pixel pattern matching, API/draw-call sequence identification, and GPU-based detection; the GPU path uses a **modified geometry shader** that compares rendering parameters to pre-recorded configuration data and emits a "dummy primitive" on match, then issues a primitive-count query — detection "entirely on the GPU and on-the-fly without buffer inspection," avoiding CPU↔GPU transfers (the patent cites cloud gaming as the motivating constraint) — [US10346942B2](https://patents.google.com/patent/US10346942B2/en)
- [PATENT] **Google US10867212B2** (sports, not games) names a full classical pipeline: 500 ms chunking, unsupervised clustering into 30–100 clusters, embedded **Hidden Markov Models** trained with Viterbi (alternatively **Gaussian Mixture Models**), **PCA** to 50 dimensions, and a **linear SVM** final highlight/non-highlight classifier, over features comprising colour histograms, oriented gradients, SIFT, motion rigidity and audio spectrograms. The patent explicitly targets "sports videos" and never mentions gaming — [US10867212B2](https://patents.google.com/patent/US10867212B2/en)

### Inferences

- [INFER] No commercial gaming clipper has publicly disclosed LLM or VLM usage for highlight *detection* as of Nov 2026. Where LLM-ish capability shows up it is downstream of detection — Eklipse/FragCut captioning and subtitling, Powder's keyword search over transcripts. Treat any claim that these products "use a VLM to watch gameplay" as unsupported.
- [INFER] Eklipse's stated 1 June 2026 shift from "cutting around a single trigger" to "scoring candidate moments" with per-genre logic is, architecturally, a move from a detector to a two-stage proposal-then-ranker. That is the normal shape of a learned highlight-scoring model, but Eklipse does not say it is learned, so "learned highlight-scoring model" remains unconfirmed for Eklipse.
- [INFER] The Nvidia patent's 4× region upscale-before-binarize trick is the most directly reusable published engineering detail for anyone building local HUD OCR, and it is a strong hint that naive OCR on native-resolution HUD text is the main accuracy failure mode.

### Gaps

- Zero disclosed architectures for any clipper's audio emotion models (Powder's laughter/shout detectors, Eklipse's hype detection). No model names, no training data description, no evaluation.
- No clipper discloses whether kill-feed reading uses OCR, learned text spotting, or icon template matching specifically — Eklipse says both "Object Detection" and "OCR" without saying which signal each serves.
- Sizzle's "patented technology" is never tied to a patent number by Sizzle. I could not locate a patent assigned to Sizzle; the auto-curation patents that surface on those queries (e.g. US10595101B2, US10433030B2) are **not** Sizzle's.

---

## Games with no structured HUD events (GTA) vs competitive shooters with a kill feed

### Takeaway

The event-API products simply do not work in unstructured games — their coverage lists are a list of games with kill feeds — and Medal's answer for GTA V and Minecraft is to outsource event definition to the **server operator** rather than detect anything. The pixel-analysing products fall back to generic "action density," audio/emotion, chat spikes, transcript keywords, or an explicit manual trigger; both Eklipse and FragCut market GTA detection in terms of chases/stunts/crashes rather than scored events.

### Cited Findings

- [STATED] Medal's unstructured-game answer is delegation, not perception: for GTA V (FiveM) and Minecraft, "each server sets its own events" — [Medal Auto Clipping](https://medal.tv/auto-clipping)
- [STATED] Outplayed's automatic highlight capture simply does not exist outside integrated titles: "The Highlights/Full Match capture mode depend on game events" — [Overwolf Support](https://support.overwolf.com/support/solutions/articles/9000284659-how-to-use-outplayed)
- [STATED, second-hand] Eklipse's GTA framing is generic action, not events: it "detects high-action moments broadly — stunts, wrecks, chases, combat — not just combat kills, so open-world chaos gets caught the same way ranked plays do" — [Eklipse: GTA](https://eklipse.gg/use-case/gta/); [Eklipse: GTA V Highlights](https://eklipse.gg/use-case/grand-theft-auto-v-highlights/)
- [STATED, second-hand] For GTA RP specifically Eklipse concedes the problem is narrative, not mechanical: "GTA RP highlights aren't always about action," and it offers the voice-command manual escape hatch — say "Clip it!" to mark the stream — [Eklipse: GTA RP Clips](https://eklipse.gg/use-case/gta-rp-clips/); [Eklipse: Voice Command](https://eklipse.gg/features/voice-command/)
- [STATED] FragCut claims detection of "heists, police chases, stunt sequences, and GTA RP highlights" for GTA V, and also lists Minecraft among supported titles — i.e. visual-only detection targets — [FragCut: GTA V](https://fragcut.io/games/grand-theft-auto-v); [FragCut: Minecraft](https://fragcut.io/games/minecraft)
- [3P-LOW] The constraint stated plainly in comparison content: "AI Highlights is strongest where there are events to read: kill feeds, scoreboards, squad wipes," and "games with no kill feed have little for detection to score," naming GTA V as the example — surfaced from [Medal: Best Clipping Software 2026](https://medal.tv/learn/best-clipping-software) and [gameclipperadvanced.com](https://gameclipperadvanced.com/blog/eklipse-alternatives/) (both competitor-authored; low reliability but consistent with the companies' own coverage lists)
- [3P-LOW] Powder's documented fallback ordering is the cleanest expression of the pattern: audio emotion, chat spikes, transcription and keyword search were used "when game-specific detection was unavailable" — [The Rundown: Powder](https://www.therundown.ai/tools/powder)
- [STATED, second-hand] Eklipse's June 2026 rebuild extended detection to content with no game signal at all — "just chatting, IRL streams, and podcasts" — which necessarily means audio/transcript/chat-only scoring — [Eklipse blog: How Gameplay Intelligence Works](https://blog.eklipse.gg/streaming-tips/how-gameplay-intelligence-works-2.html)
- [STATED, second-hand] Eklipse claims coverage of "more than 3,000 games, with highlight detection tuned for each game category" — note: *category*, not per-game — [Eklipse](https://eklipse.gg/)

### Inferences

- [INFER] "3,000 games" vs Powder's "40 game-specific models" is the whole story of this trade-off: Eklipse achieves breadth by scoring genre-generic signals (motion/action density, audio energy, chat rate), accepting worse precision; Powder achieved per-game precision by shipping a model per title, accepting a maintenance treadmill. There is no public evidence of anyone solving both.
- [INFER] Since the event-API vendors' coverage lists *are* their capability statements, "which games does Medal/Outplayed support" is a direct proxy for "which games expose structured kill events" — useful as a ready-made list of games where a kill-feed-reading detector has a reliable ground-truth source to validate against.
- [INFER] For GTA-class games no vendor claims semantic event detection; the honest state of the art commercially is unsupervised salience (action density + audio arousal) plus a manual marker. Any project targeting open-world games should expect to be in genuinely unsolved territory, not reimplementing something commercial products already do well.

### Gaps

- No vendor publishes a comparison of detection quality in kill-feed games vs open-world games. The qualitative claim ("strongest where there are events to read") only appears in competitor-authored content.
- Nothing found on how any product handles minimap, scoreboard, or killcam screens as confounders (e.g. a kill feed visible during a spectated death cam producing a false positive). User-report threads on this were not findable.

---

## Published accuracy, precision/recall, or latency figures

### Takeaway

There are effectively **no credible published accuracy figures** from any company in this space. I found exactly one numeric accuracy claim anywhere, and it appears in affiliate-style review content with no stated methodology. Latency figures exist only for Eklipse (wall-clock, queue-inclusive) and Medal (an unrelated config-propagation delay).

### Cited Findings

- [3P-LOW, attribution uncertain] A single accuracy figure surfaced: "In testing with Valorant, Eklipse correctly identified 83% of highlight-worthy moments, with the other 17% being either missed kills in chaotic teamfights or false positives on routine plays." This appeared in a search summary spanning several affiliate/review pages for Eklipse, most likely [agent-finder.co/reviews/eklipse](https://agent-finder.co/reviews/eklipse) and/or [clipwick.com/articles/outplayed-review](https://clipwick.com/articles/outplayed-review). **I could not fetch the page to confirm attribution, sample size, labelling protocol, or who "correctly" was judged by.** Do not present this as an industry accuracy figure; it is one unverified reviewer's impression stated as a percentage.
- [STATED, second-hand] Eklipse latency: "Most processing finishes 20–60 minutes after a stream ends," with free-tier queueing potentially adding "several hours" — [Eklipse Help: processing stuck](https://eklipse.gg/help/why-is-my-stream-processing-stuck-or-taking-longer-than-usual/)
- [STATED] Medal's only published timing number is unrelated to detection latency: after saving a new developer event, "allow about 3 minutes" for it to go live — [Medal Developer](https://medal.tv/developer/auto-clipping)
- [STATED] Medal's architectural latency answer is retroactive buffering rather than a figure: "Medal uses retroactive recording, so your captured clip includes the play and what happened just before it, instead of recording after the play happened" — [Medal Auto Clipping](https://medal.tv/auto-clipping)
- [STATED/PRESS] Sizzle claims "real time" highlight creation directly from Twitch/YouTube streams but gives no latency number — [MarkTechPost, 25 May 2022](https://www.marktechpost.com/2022/05/25/meet-sizzle-a-california-based-startup-that-leverages-ai-to-automatically-create-gaming-highlights-from-twitch-and-youtube-videos/). Sizzle's own esports page does not specify whether processing is real-time or batch, nor any latency — [Sizzle: Esports Leagues](https://www.sizzle.gg/esports-leagues)
- [PRESS] Powder published only a time-saving claim, not an accuracy claim: a survey of 3,200+ streamers found creators spend 630 hours a year on clip editing, and Powder claimed to save ~520 hours annually per user — [TechCrunch, 20 Nov 2023](https://techcrunch.com/2023/11/20/powder-an-ai-clipping-tool-for-gaming-can-detect-when-a-creator-yells-during-a-stream/)
- [3P-LOW] Qualitative failure reports rather than numbers: user reviews mention "a processing queue, clips that arrive mistimed and need manual re-editing," and Eklipse's June 2026 release is positioned as producing "more keepable clips per VOD and fewer false positives" — a relative claim with no baseline — [Eklipse blog: review compilation](https://blog.eklipse.gg/featured/eklipse-gg-review.html); [Eklipse blog: Gameplay Intelligence](https://blog.eklipse.gg/streaming-tips/gameplay-intelligence.html)
- [STATED] Overwolf's own developer forum carries event-correctness bug reports, e.g. a thread titled "R6 wrong event detection," confirming GEP event errors are a real class of problem — [Overwolf Developers Q&A](https://discuss.overwolf.com/t/r6-wrong-event-detection/1063)

### Inferences

- [INFER] The complete absence of precision/recall from every vendor, across eight years and multiple funded startups, is itself the finding: there is no shared benchmark or evaluation protocol for gameplay highlight detection in industry, so vendors compete on coverage and turnaround time instead. Any internal accuracy target set for a local project should therefore be validated against a self-built ground truth (e.g. a scoreboard or kill-count check), because no external number exists to compare against.
- [INFER] Eklipse's stated failure causes — older model version, and "important gameplay signals were hidden by overlays" — imply HUD-region-dependent detection with no overlay-occlusion robustness. For a local detector this predicts that stream overlays, webcam boxes and alert popups over the kill-feed region are a primary recall killer.

### Gaps

- No precision, recall, F1, mAP, or per-game accuracy from Eklipse, Medal, Overwolf, Powder, Sizzle, FragCut, or Athenascope. None published, ever, as far as I can find.
- No latency figures for Powder (local), FragCut (cloud), or Sizzle (claimed real-time).
- **Reddit/Discord/forum user-report threads were not retrievable through this search tool.** Queries aimed at r/medal, r/Valorant and similar returned only vendor pages and Wikipedia. The one Overwolf developer-forum thread above is the sole genuine first-hand defect report I obtained. The brief's suggestion to infer method from false-positive reports could not be executed; this is a real gap and would need direct forum browsing.

---

## Patents covering highlight detection

### Takeaway

The clipping startups hold little or nothing on highlight detection itself — Medal's granted patents cover co-player identification by HUD hashing, and I found no Overwolf-assigned event-detection patent. The substantive patents are held by **Nvidia** (HUD-region OCR with pre-binarization upscaling), **Microsoft** (ML event recognisers over video/audio/controller input across games), and **EA** (GPU geometry-shader draw-call event detection), with **Google** holding a classical sports-highlight pipeline that explicitly excludes games.

### Cited Findings

**Nvidia — US12288404B2, "Resolution upscaling for event detection"**
- Assignee Nvidia Corp; inventors Nathan Otterness, Jonathan White, Dave Clark, Jim van Welzen. Priority 20 Jan 2020, filed 15 Sep 2021, granted 29 Apr 2025 — [US12288404B2](https://patents.google.com/patent/US12288404B2/en)
- Claim shape: identify regions within gameplay frames (typically HUD elements) → apply resolution upscaling to those regions → perform character/icon detection on the enhanced content → translate detected cues into structured event data — [US12288404B2](https://patents.google.com/patent/US12288404B2/en)
- Mechanism detail: HUD text is typically 10–15 px with anti-aliasing-degraded edges; selected regions are upscaled 4× by bicubic interpolation, and "upscaling is performed before steps such as binarization and background removal… which can provide input to the decoder that is both separated from the background and which retains visual fidelity." Region-limited upscaling bounds compute versus full-frame. Additional detectors: OCR of status/overlay text, icon/template matching (skull counts, health bars, score indicators), optical-flow motion detection, and audio pattern recognition (hit-impact sounds). Deployment is explicitly flexible: player device, game server, or third-party/provider cloud, at the preprocessing stage "as media is received, enabling near real-time event logging." Downstream uses named include highlight video generation, player analysis, and matchmaking — [US12288404B2](https://patents.google.com/patent/US12288404B2/en)

**Medal — US11872495B1 (+ family US12285695B1, US20250135355A1), "Method and system for detecting common videogame gameplay"**
- Assignee Medal BV; inventors Wilhelmus Wilfried Alexander de Witte, Zaid Deric Osama Elnasser; filed 27 Oct 2023, granted 16 Jan 2024 — [US11872495B1](https://patents.google.com/patent/US11872495B1/en)
- Claim 1: process frame → extract a pre-determined shared HUD portion → generate a hash → compare against a repository → identify co-players. Local executables do capture and hashing; a central server stores and matches hash streams. Hashing interval examples: every 1, 5 or 60 seconds; hashes may embed synchronised timestamps. Port-scanning and IP-address correlation are described as supplementary techniques. Integration named with Medal.tv for notifying users they shared a session — [US11872495B1](https://patents.google.com/patent/US11872495B1/en)
- **This is not a highlight-detection patent.** It covers "Clips You're In"-style co-player matching — [Medal: Clips You're In](https://medal.tv/features/clips-you-are-in)
- [PRESS/3P-LOW] Portfolio size: Medal is reported to have filed ~10 patents / 8 patent documents with 7 granted, with the Oct 2023 "common videogame gameplay" family being the recent activity — [CB Insights: Medal](https://www.cbinsights.com/company/medaltv)

**Microsoft — US11850519B2, "Tracking in-game events and generating event reports across multiple gaming applications"**
- Assignee Microsoft Technology Licensing LLC; inventors Daniel Gilbert Kennett, Mark Edward Rabold; filed 17 Jun 2021, granted 26 Dec 2023, expiry 22 Dec 2041 — [US11850519B2](https://patents.google.com/patent/US11850519B2/en)
- Claims: receive requests to track event instances across multiple gaming applications → train event recognisers using ML to detect in-game signals → apply recognisers to gaming content without interrupting the user experience → generate event reports across users and applications — [US11850519B2](https://patents.google.com/patent/US11850519B2/en)
- Mechanism: analyses "consumable gaming content" rather than application code — "event recognizers are trained to recognize events based on an evaluation of consumable gaming content" — using video frames as the primary signal, audio as confirmation, controller inputs as a supplementary signal, and an "area of interest" parameter specifying the screen region. **Does not claim highlight or clip generation**; outputs are event reports and metadata — [US11850519B2](https://patents.google.com/patent/US11850519B2/en)

**Electronic Arts — US10346942B2, "Method for event detection in real-time graphic applications"**
- Assignee Electronic Arts Inc; inventor Yuval Sarna; filed/priority 2 Feb 2015, granted 9 Jul 2019 — [US10346942B2](https://patents.google.com/patent/US10346942B2/en)
- Four independent claims: (1) a cost-ordered cascade selecting "the least resource-consuming or least intrusive method" per frame among simple pattern matching, per-pixel pattern matching, API sequence identification, and GPU-based detection; (2) GPU detection via a modified geometry shader that checks rendering parameters against pre-recorded configuration data, emits a "dummy primitive" on match, then queries primitive counts; (3) per-pixel pattern matching in which individual pixels receive **distinct variance thresholds reflecting their significance** to element identification; (4) a computer program product. Configuration data is extracted in a debug preparation phase. Detection runs "entirely on the GPU and on-the-fly without buffer inspection," avoiding CPU↔GPU copies — motivated by resource-constrained cloud gaming — [US10346942B2](https://patents.google.com/patent/US10346942B2/en)

**Google — US10867212B2 (and continuation US11556743B2), "Learning highlights using event detection"**
- Assignee Google LLC; inventors Vivek Kwatra, Ullas Gargi, Mehmet Emre Sargin, Henry Hao Tang; filed 21 Jul 2017, granted 15 Dec 2020 — [US10867212B2](https://patents.google.com/patent/US10867212B2/en)
- Claims: extract low-level frame features → generate vectors indicating transition frequencies between detected occurrences → match vectors against previously identified events using highlight classifiers → designate highlight-containing portions → update video metadata. Pipeline: 500 ms chunks, unsupervised clustering into 30–100 clusters for initial event designation, embedded HMM + Viterbi (or GMM), PCA to 50 dims, linear SVM highlight classifier; features are colour histograms, oriented gradients, SIFT, motion rigidity, audio spectrograms — [US10867212B2](https://patents.google.com/patent/US10867212B2/en)
- Scope limit: explicitly "sports videos," with no mention of gaming or interactive content; adjacent applications named are traffic and security cameras — [US10867212B2](https://patents.google.com/patent/US10867212B2/en)

### Inferences

- [INFER] Freedom-to-operate for a local HUD-OCR kill detector looks workable but not trivially clear. Nvidia's US12288404B2 claims region-upscale-then-decode specifically, so a pipeline that OCRs HUD regions *without* the pre-binarization upscaling step reads outside its core claim; EA's US10346942B2 is confined to graphics-pipeline/draw-call interception and per-pixel variance-threshold matching, neither of which a post-hoc video analyser performs. This is a lay reading, not legal advice.
- [INFER] That Nvidia — the company whose own Highlights product needs no perception because games declare events — holds the best HUD-OCR detection patent, filed in 2020–2021 after Highlights adoption stalled, suggests Nvidia concluded developer-integrated events would never achieve coverage and invested in universal pixel-side detection instead. Consistent with Highlights now being marked a legacy SDK.
- [INFER] The absence of any clipper-assigned highlight-detection patent (Eklipse, Powder, FragCut, Athenascope all appear to hold none I could find) implies their detection is engineering-and-data work on known techniques rather than novel method, reinforcing that "AI" in their marketing is mostly per-game HUD templates plus audio heuristics.

### Gaps

- **No Overwolf-assigned patent found.** Searches for Overwolf as assignee on in-game event detection returned EA's and Microsoft's patents instead. Either Overwolf holds none in this area or it is not indexed under queries I tried.
- **No Sizzle patent located**, despite Sizzle repeatedly claiming "patented technology." Unresolved.
- **No Eklipse, FragCut, Powder, or Athenascope patents located.**
- **Discord**: no highlight-detection patent found (Discord acquired no clipper and its Clips feature is manual as far as I found). Not investigated deeply.
- **AMD**: no highlight-detection patent or automatic-highlight API found.
- Two further patents surfaced but were **not verified** and should be checked by the report writer if patent coverage matters: US12273604 "Method and system to highlight video segments in a video stream" (assignee unverified) and the pair US11438637 / US12250415 "Computerized system and method for automatic highlight detection from live streaming media and rendering within a specialized media player" (assignee unverified, plausibly Yahoo/Verizon Media). I did not fetch these.

---

## Status and dating of defunct / changed products

### Takeaway

Athenascope is long defunct. **Powder's shutdown date is genuinely contested** and the brief's "shut down 2024" does not match what I found. Nvidia Highlights is now officially a legacy SDK. Eklipse's current engine dates from 1 June 2026.

### Cited Findings

- [CONFLICT — Powder shutdown date] Multiple competitor/directory pages state **July 2026**: "Powder shut down in July 2026, and the team says the app will no longer be updated or maintained and that active subscriptions are being canceled," with the team's statement framed as "after 7 incredible years, their journey with Powder has reached its end… unable to secure a sustainable business model" — [FragCut: Powder.gg Shut Down](https://fragcut.io/alternatives/powder-gg); [gameclipperadvanced.com: Powder alternatives](https://gameclipperadvanced.com/blog/powder-gg-alternatives/); [autostreampro.com](https://www.autostreampro.com/blog/autostreampro-vs-powder). A separate source in the same search described a **late-2024** announcement — [eklipse blog: Powder.gg alternatives](https://blog.eklipse.gg/tools/powder-gg-alternatives.html). **These contradict each other and all are competitor-authored SEO pages.** Supporting the later date: Powder was actively shipping features and publicising a roadmap in Nov 2023 with $22M raised — [TechCrunch, 20 Nov 2023](https://techcrunch.com/2023/11/20/powder-an-ai-clipping-tool-for-gaming-can-detect-when-a-creator-yells-during-a-stream/) — and "7 years" from a 2018 founding lands on 2025–2026, not 2024. **Recommendation: treat July 2026 as the more likely date, flag it as unverified, and do not assert 2024.** The primary source would be Powder's own announcement on [@Powder_video](https://x.com/powder_video?lang=en), which I could not fetch.
- [PRESS] Powder founding and funding: founded 2018 in France by Barthélémy Kiss (CEO), Yannis Mangematin, Stanislas Coppin, Christian Navelot; $22M raised as of Nov 2023 — [TechCrunch, 20 Nov 2023](https://techcrunch.com/2023/11/20/powder-an-ai-clipping-tool-for-gaming-can-detect-when-a-creator-yells-during-a-stream/)
- [PRESS] Athenascope: $2.5M seed led by First Round announced 8 Feb 2019; the product was still being written about in Apr 2020; it is no longer operating — [TechCrunch, 8 Feb 2019](https://techcrunch.com/2019/02/08/athenascope-nabs-2-5m-seed-led-by-first-round-to-bring-gamers-ai-edited-highlight-reels/); [TechMikeWi, 11 Apr 2020](https://techmikewi.com/2020/04/11/machine-learning-based-video-scrubbing-for-highlight-moments-with-athenascope/); [CB Insights: Athenascope](https://www.cbinsights.com/company/athenascope)
- [STATED] Nvidia Highlights carries, as of this research, the notice "This is a legacy SDK. Developers may download and continue to use, but it is no longer supported" — [NVIDIA Highlights](https://developer.nvidia.com/highlights)
- [STATED, second-hand] Eklipse "Gameplay Intelligence" runs on every Premium VOD **from 1 June 2026**; the engine was "rebuilt around video analysis in June 2026" — so any Eklipse behaviour described before mid-2026 is stale — [Eklipse blog](https://blog.eklipse.gg/streaming-tips/how-gameplay-intelligence-works-2.html)
- [3P-LOW] Powder's distinguishing feature was console ingest: "its unique ability to connect directly to consoles like Xbox, although this feature was sometimes unreliable" — [eklipse blog: Powder.gg alternatives](https://blog.eklipse.gg/tools/powder-gg-alternatives.html) (competitor-authored; treat the reliability jab as marketing). Note this contradicts [The Rundown's](https://www.therundown.ai/tools/powder) Windows/Twitch/YouTube/Kick-only description, which does not mention console support.

### Inferences

- [INFER] Powder was the only product in this set that combined local on-device inference with multimodal detection, and the only one claiming console ingest. Its death removes the closest commercial analogue to a local-first clipping pipeline, which means there is currently **no shipping commercial product doing on-device multimodal highlight detection** — the gap a local project would be filling.

### Gaps

- Could not reach Powder's own shutdown announcement (x.com and medium/blog.powder.gg both unfetchable), so the date remains unconfirmed from a primary source.
- Athenascope's exact shutdown date was not found.
