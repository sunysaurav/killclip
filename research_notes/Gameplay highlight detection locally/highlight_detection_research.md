# Automatic Highlight Detection in Gameplay, Esports and General Video — Literature Notes (current as of Nov 2026)

Scope note for the report writer: the target application is **1–2 hour single-player open-world (GTA) sessions with no kill feed, no scoreboard, no caster commentary and no chat**. Throughout, I flag which findings survive that setting and which depend on structured HUD, broadcast production or crowd signals.

---

## Q1. What architectures dominate video highlight detection now?

### Takeaway
The field has converged on **DETR-style temporal transformers over frozen CLIP(+SlowFast) or InternVideo2 features** as the workhorse (QD-DETR → CG-DETR → FlashVTG lineage, 2023–2024), with the 2026 frontier being **MLLM-based grounding with learned visual-token selection** (GroundVTS on InternVL3.5-8B, Apr 2026, HIT@1 88.4 / mAP 52.5 on QVHighlights val) and **training-free LLM-over-segment-captions pipelines** for very long video (TF-SELECTOR, Jun 2026). Pure zero-shot video-LLMs are near-useless at this task; the gains come entirely from task-specific adaptation on top of them.

### Cited Findings

**QVHighlights (val) highlight-detection leaderboard, dated, HIT@1 / mAP** — [SOTA2 leaderboard](https://www.sota2.com/research/sota/highlight-detection-on-qvhighlights-val):
- GroundVTS-I (InternVL3.5-8B), 2026.04 — **88.4 / 52.5** (rank 1)
- FlashVTG (InternVideo2), 2024.12 — 72.9 / 44.15
- HL-CLIP (HL-CLIP-2, saliency pooling), 2024.04 — 72.4 / 42.37
- InternVideo2-6B (S2-6B features), 2024.03 — 72.0 / 42.9
- NumPro, 2026.04 — 70.7 / 40.5
- InternVideo2-1B, 2024.03 — 69.74 / 42.36
- FlashVTG (SlowFast+CLIP), 2024.12 — 67.61 / 41.39
- CG-DETR (SlowFast+CLIP), 2023.11 — 66.7 / 40.8
- LLMEPET (SF+C), 2024.12 — 65.03 / 40.52
- UMT (SlowFast+CLIP, audio modality on), 2023.11 — 64.2 / 39.9
- R2-Tuning (CLIP only), 2024.12 — 64.13 / 39.45
- TaskWeave, 2024.04 — 63.68 / 39.28
- QD-DETR (SlowFast+CLIP), 2023.11 — 63.0 / 39.1
- UniVTG (SlowFast+CLIP), 2023.11 — 61.8 / 38.8
- GroundVTS-Q (Qwen2.5VL-7B), 2026.04 — 58.8 / 35.7
- EaTR (SlowFast+CLIP), 2023.11 — 58.7 / 37.2
- Moment-DETR / M-DETR (SlowFast+CLIP), 2021 paper, leaderboard 2023.11 — 55.6 / 35.7
- Qwen2.5VL-7B + grounding fine-tune, 2026.04 — 44.5 / 34.4
- InternVL3.5-8B + grounding fine-tune, 2026.04 — 39.8 / 31.9
- VTG-LLM, 2026.04 — 33.5 / 16.5
- TimeChat, 2026.04 — 23.9 / 14.5
- **Qwen2.5VL-7B zero-shot, 2026.04 — 0.6 / 24.9**
- **InternVL3.5-8B zero-shot, 2026.04 — 0.32 / 24.8**

- **GroundVTS** (arXiv 2604.02093, Apr 2026) adds "a query-guided visual token sampling module to enable efficient and fine-grained temporal grounding in multimodal large language models"; on InternVL3.5-8B it gains +0.9 R1@0.3, +1.3 R1@0.5, +1.1 mIoU over the plain InternVL grounding fine-tune — [arXiv](https://arxiv.org/html/2604.02093)
- **HL-CLIP** — "Unleash the Potential of CLIP for Video Highlight Detection", Han et al., CVPR 2024 ELVM workshop: uses a novel **saliency pooling** technique over CLIP features and reported SOTA on the QVHighlights highlight-detection task at the time — [CVPRW 2024 PDF](https://openaccess.thecvf.com/content/CVPR2024W/ELVM/papers/Han_Unleash_the_Potential_of_CLIP_for_Video_Highlight_Detection_CVPRW_2024_paper.pdf)
- **VideoLights** (arXiv 2412.01558, Dec 2024) — "Feature Refinement and Cross-Task Alignment Transformer for Joint Video Highlight Detection and Moment Retrieval"; reports SOTA across most QVHighlights metrics for both tasks at publication — [arXiv](https://arxiv.org/pdf/2412.01558)
- **DiffusionVMR** (arXiv 2308.15109, Aug 2023) — diffusion model that denoises random spans into moment/highlight predictions, i.e. a generative alternative to DETR decoding — [arXiv](https://arxiv.org/pdf/2308.15109)
- **FlashVTG** (arXiv 2412.13441, Dec 2024) — "Feature Layering and Adaptive Score Handling Network for Video Temporal Grounding"; the strongest non-MLLM entry on the leaderboard above — [arXiv](https://arxiv.org/pdf/2412.13441)
- **Multi-modal Fusion and Query Refinement Network** (arXiv 2501.10692, Jan 2025) — joint MR+HD with explicit audio fusion — [arXiv](https://arxiv.org/pdf/2501.10692)
- **SRF — "See, Rank, and Filter"** (arXiv 2511.22906, submitted 28 Nov 2025; YuEun Lee, Jung Uk Kim): MLLM-based scene understanding plus a Feature Enhancement Module that identifies important query words and a Ranking-based Filtering Module that iteratively refines clips. Reported to show "superior performance across all metrics when using only video, and with the concatenated video and audio setting, it still outperforms other methods on most metrics." Code at `github.com/VisualAIKHU/SRF` — [arXiv abs](https://arxiv.org/abs/2511.22906); [PDF](https://arxiv.org/pdf/2511.22906)
- **MLLM Frame Segmentation** (arXiv 2512.12246v1, 13 Dec 2025; Jiwanta & Purwarianti, ITB): reframes HD/MR as **binary mask generation** — BLIP-3 Large (4.36B: SigLIP vision encoder + Perceiver Resampler + Phi-3) emits "0"/"1" text tokens per frame over 25 sampled frames. Loss = causal LM + binary cross-entropy + Tversky + generalized Dice with scheduled weights. QVHighlights: **HIT@1 56.74, HL mAP 34.48; MR R1@0.5 60.77, R1@0.7 37.42, avg mAP 35.28**. Beats Moment-DETR on HD; trails SFT/RL methods on MR while using only 25 frames vs competitors' 60+. Training ≈4 h 40 min on 2×H100. Code: `github.com/bagasjiwanta/llm-frame-segmentation`, **CC BY-SA 4.0** — [arXiv HTML](https://arxiv.org/html/2512.12246v1)
- **TF-SELECTOR / SVHighlights** (arXiv 2606.06926, v1 5 Jun 2026, v2 17 Jun 2026; Donggyu Lee, Youngbin Ki, Jeonghun Kang, Taehwan Kim): a **training-free, segment-based** method that groups adjacent shots with shared semantic content and scores each segment with an LLM over **visual captions + transcripts + audio volume**, deliberately avoiding frame-level scoring. Gains over Video Temporal Grounding baselines: **+2.50 HIT@1, +4.04 HIT@K, +2.95 IoU** — [arXiv abs](https://arxiv.org/abs/2606.06926); [HTML](https://arxiv.org/html/2606.06926)
- **AHA — "Predicting What Matters Next: Online Highlight Detection Without Looking Ahead"** (arXiv 2509.16421, 19 Sep 2025, accepted NeurIPS 2025; Aiden Chang, Celso De Melo, Stephanie M. Lukin): autoregressive multimodal VLM + "lightweight, decoupled heads"; a **Dynamic SinkCache mechanism maintains constant memory usage across infinite-length streams** without performance degradation. Reports **+5.9% mAP on TVSum and +8.3% mAP on Mr.HiSum** over prior offline methods, in a strictly causal/streaming setting (no future frames) — [arXiv abs](https://arxiv.org/abs/2509.16421); [PDF](https://arxiv.org/pdf/2509.16421)
- **TVHighlights** (CVPR 2026, Qiu et al.) — "LLM-Guided Human-Free Collaborative Training for Video Highlight Detection"; exists and is peer-reviewed at CVPR 2026, but the PDF was not retrievable (403) so I have no numbers — [CVF open access link](https://openaccess.thecvf.com/content/CVPR2026/papers/Qiu_TVHighlights_LLM-Guided_Human-Free_Collaborative_Training_for_Video_Highlight_Detection_in_CVPR_2026_paper.pdf)
- Other 2026 entries seen in search but not fetched: **SGWIB** (Sliced Gromov-Wasserstein Information Bottleneck for Video Highlight Detection, arXiv 2609.13966); **TimeLens** (CVPR 2026 poster, "Rethinking Video Temporal Grounding with Multimodal LLMs", thinking-free RLVR training); **GIRL-DETR** (Gradient-Isolated RL for Video Moment Retrieval, arXiv 2606.00775); **VideoITG** (NVlabs, CVPR 2026 Highlight, instructed temporal grounding) — [TimeLens](https://cvpr.thecvf.com/virtual/2026/poster/39512); [GIRL-DETR](https://arxiv.org/pdf/2606.00775); [VideoITG repo](https://github.com/NVlabs/VideoITG)
- RL-based grounding is now a recognised recipe: "combining supervised initialization with reinforcement learning is a potent strategy for Video Temporal Grounding, with the RL phase producing the most significant performance jumps" — [Datasets and Recipes for Video Temporal Grounding via RL, EMNLP 2025 Industry](https://aclanthology.org/2025.emnlp-industry.66.pdf)

### Inferences
- The dominant *shape* of a system is: frozen visual backbone (CLIP / SlowFast / InternVideo2) → short clip-level feature sequence → transformer that emits per-clip saliency + span proposals. This decouples cheaply from the backbone, which matters for a 1–2 h GTA recording: you can extract features once at ~1–2 fps and then run a very cheap temporal head.
- Every leaderboard-topping method is **query-conditioned** (QVHighlights is a natural-language moment-retrieval benchmark). For GTA with no query, the directly relevant sub-family is the *query-free* saliency branch (UMT/HL-CLIP-style saliency heads, LOGA's query-free formulation, AHA's online head), not the MR branch.
- TF-SELECTOR and AHA are the two architectures whose *design premise* matches hour-long unstructured footage: segment-level LLM scoring over captions+audio, and constant-memory causal streaming respectively. Both avoid the O(T²) attention blowup that kills DETR-style heads on 1–2 h inputs.

### Gaps
- TVHighlights (CVPR 2026) numbers, architecture and code status — PDF behind a 403.
- SRF's actual numeric table (the abs page did not expose it); I can only report its qualitative SOTA claim.
- Licences for most QVHighlights-lineage repos (Moment-DETR, QD-DETR, CG-DETR, FlashVTG) were not confirmed in sources I fetched. Moment-DETR's repo is widely cited as permissively licensed but I did not verify it here.

---

## Q2. Weakly-supervised and self-supervised highlight detection (no frame-level labels)

### Takeaway
There is a mature line of work that replaces frame labels with **free proxy signals**: video *duration* (short uploads ≈ curated), *event/category label only* (multiple-instance ranking), *the existence of an official/crowd highlight reel* for the same raw video, and *aggregate viewer replay statistics*. Unsupervised audio-visual methods now essentially match or beat older supervised ones on YouTube Highlights (≈0.65 mAP unsupervised vs 0.46–0.54 for classic supervised baselines), which is the single most encouraging result for a label-free GTA pipeline.

### Cited Findings

**Proxy-label families**
- **Duration as weak supervision** — "Less is More: Learning Highlight Detection from Video Duration" (Xiong et al., CVPR 2019): "user-generated videos carry a latent supervision signal relevant for highlight detection: their duration," on the hypothesis that "shorter user-uploaded videos tend to have a key focal point as the user is more selective about the content, whereas longer ones may not have every second be as crisp or engaging." Their domain-specific variant outperformed all baselines including supervised ranking-based methods — [arXiv](https://arxiv.org/pdf/1903.00859); [CVPR 2019 PDF](https://openaccess.thecvf.com/content_CVPR_2019/papers/Xiong_Less_Is_More_Learning_Highlight_Detection_From_Video_Duration_CVPR_2019_paper.pdf)
- **Multiple-instance ranking from category labels only** — MINI-Net (ECCV 2020): "cast weakly supervised highlight detection as a multiple instance learning problem and proposed a Multiple Instance Ranking Network (MINI-Net)," learning "segments that are more attractive in training videos given their video event label but without expensive supervision of manually annotating highlight segments." Reports audio and no-audio variants — [arXiv](https://arxiv.org/pdf/2007.09833)
- **"This segment was clipped" as the weak label** — Autohighlight (Journal of Machine Learning with Applications, 2022) "tackled highlight detection in a weakly supervised manner, utilizing datasets of 'crowd-sourced' highlight videos and unedited broadcasts" for League of Legends esports — [ScienceDirect (403 on fetch)](https://www.sciencedirect.com/science/article/pii/S2666827022000469); [York Research Database record](https://pure.york.ac.uk/portal/en/publications/autohighlight-highlight-detection-in-league-of-legends-esports-br/)
- The same official-reel-vs-full-video pairing is how **SVHighlights** was built: "Using official highlight videos paired with full-length content, the authors developed a scalable annotation pipeline" — [arXiv abs](https://arxiv.org/abs/2606.06926)
- **Implicit crowdsourcing** — "Towards Extracting Highlights From Recorded Live Videos: An Implicit Crowdsourcing Approach" (arXiv 1910.12201) uses viewer behaviour on recorded live video as the signal — [arXiv](https://arxiv.org/pdf/1910.12201)
- **Aggregate replay counts as labels** — Mr. HiSum (NeurIPS 2023 Datasets & Benchmarks) contains **31,892 videos** with "reliable frame importance score labels aggregated from 50,000+ users per video," derived from YouTube's "Most replayed" statistics "normalized to a score of 0 to 1." Provided baselines: PGL-SUM, VASNet, SL-module. Data/code at `github.com/MRHiSum/MR.HiSum` — [NeurIPS PDF](https://proceedings.neurips.cc/paper_files/paper/2023/file/7f880e3a325b06e3601af1384a653038-Paper-Datasets_and_Benchmarks.pdf); [repo](https://github.com/MRHiSum/MR.HiSum)
- On Mr.HiSum test, a 2025 method reports **64.19 mAP@50 and 32.66 mAP@15**, "+8.3 mAP@50 over PGL-SUM" (this is AHA) — [AHA PDF](https://arxiv.org/pdf/2509.16421)
- **Chat reactions as the weak label** — "Video Highlight Prediction Using Audience Chat Reactions" (EMNLP 2017): automatic Twitch highlight prediction from "joint visual features and textual analysis of audience discourse," on League of Legends championship streams from North American and Taiwanese Twitch channels, using a **multimodal character-level CNN-RNN** — [ACL Anthology](https://aclanthology.org/D17-1102.pdf)

**Fully unsupervised**
- **RASL — "Unsupervised Modality-Transferable Video Highlight Detection with Representation Activation Sequence Learning"** (Tingtian Li, Zixun Sun, Xinyu Xiao; **Tencent**; arXiv 2403.09401, Mar 2024). Features: **Swin Transformer** (visual) + **Mockingjay** (audio), feature-vector sequences; a representation-activation-sequence module trained with **k-point contrastive learning**; key property — trained on paired audio-visual data but **visual-only at inference**. YouTube Highlights mAP by domain: dog 0.642, gymnastics 0.758, parkour 0.709, skating 0.456, skiing 0.665, surfing 0.667, **average 0.651**. TVSum Top-5 mAP average **0.783**. Full comparison from that paper (avg): LSVM 0.464, Video2GIF 0.54, RARE 0.38, LM 0.564, MINI-Net 0.584, LR 0.630, CHD 0.654, RASL 0.651 — [ar5iv HTML](https://ar5iv.labs.arxiv.org/html/2403.09401); [PDF](https://arxiv.org/pdf/2403.09401)
- Same paper's TVSum Top-5 mAP averages: KVS 0.398, DPP 0.447, sLSTM 0.451, SM 0.461, MINI-Net 0.702, LR 0.768, CHD 0.528, RASL 0.783 — [ar5iv HTML](https://ar5iv.labs.arxiv.org/html/2403.09401)
- **"Unsupervised Video Highlight Detection by Learning from Audio and Visual Recurrence"** (Zahidul Islam, Sujoy Paul, Mrigank Rochan; University of Saskatchewan + **Google Research**; WACV 2025; arXiv 2407.13933). Method: cluster videos into "pseudo-categories," then compute **audio pseudo-highlight scores** and **visual pseudo-highlight scores** from within-category recurrence, and train on the resulting pseudo-labels — the "recurrence = typical = boring" prior — [arXiv abs](https://arxiv.org/abs/2407.13933); [WACV 2025 PDF](https://openaccess.thecvf.com/content/WACV2025/papers/Islam_Unsupervised_Video_Highlight_Detection_by_Learning_from_Audio_and_Visual_Recurrence_WACV_2025_paper.pdf)
- **Robust recurrent auto-encoders** — "Unsupervised Extraction of Video Highlights Via Robust Recurrent Auto-encoders" (arXiv 1510.01442, 2015): the original reconstruction-error-as-highlight formulation — [arXiv](https://arxiv.org/pdf/1510.01442)
- **Cross-category / set-based** — "Cross-category Video Highlight Detection via Set-based Learning" (arXiv 2108.11770) targets generalisation to unseen categories — [arXiv](https://arxiv.org/html/2108.11770)

### Inferences
- For GTA there is a clean, available weak label with no annotation cost: **the user's own existing clips / Share-button saves / the official-reel-vs-raw pairing used by Autohighlight and SVHighlights**. If the user has any history of manually clipping their own sessions, that is exactly the "this segment was clipped" supervision these papers exploit, and it requires no frame labels.
- The RASL result (unsupervised 0.651 avg mAP, beating classic supervised 0.46–0.54 and MINI-Net's 0.584 on the same benchmark) suggests a **label-free audio-visual recurrence/novelty approach is not a big accuracy sacrifice** — but note those numbers are on 1–6 min curated sports clips, not 2 h of driving around Los Santos, and the recurrence prior is far weaker when 95% of the footage is visually similar urban traversal.
- RASL's modality-transferable design (audio at train, visual-only at inference) is the wrong direction for GTA; here audio is the *more* reliable modality at inference (gunfire, sirens, crashes, explosions) and should be kept at test time.
- Mr.HiSum's "most replayed" labels are the closest public analogue of "viewers found this exciting" and it's the only highlight dataset at a scale (31,892 videos) where pretraining a temporal head is plausible.

### Gaps
- The WACV 2025 audio-visual-recurrence paper's actual mAP tables — the PDF 403'd on CVF and the PDF text layer did not extract from arXiv; I have the method but no numbers for it.
- Autohighlight's dataset size, feature set and accuracy — ScienceDirect 403.
- Licences for RASL (no code link given in the paper) and for the WACV 2025 method.

---

## Q3. Esports / gameplay-specific highlight detection

### Takeaway
Gameplay-specific work splits sharply into (a) **broadcast esports**, where the most predictive signals are production and crowd artefacts — caster pitch/volume, chat rate, kill feed, scoreboard, canned visual effects — and (b) **raw gameplay**, where the only published strong result is AMD's 2025 X-CLIP fine-tune at 94.3% event accuracy on FPS titles, which explicitly relies on game UI and drops to 69% on kill detection for an unseen game. The one 2026 benchmark on *long-form* game video (LOGA) finds **audio-visual fusion beats vision-only on every subset**.

### Cited Findings

**Raw first-person gameplay**
- **"Gameplay Highlights Generation"** (Vignesh Edithal, Le Zhang, Ilia Blank, Imran Junejo — **AMD**; arXiv 2505.07721, 12 May 2025):
  - Model: **X-CLIP**, ViT-B/16 backbone, 32 RGB frames at 224×224 per **1-second clip**; text encoder frozen, video encoder fine-tuned; prompt template "Game Name. Event Name. Description" boosted performance.
  - Data: **110 GB of video**; CS:GO, PUBG, Valorant, Overwatch 2, Fortnite; 7 event classes (kill, death, grenade throw, reload, bomb planted, knocked down, power use) + background; **4,408 manually annotated events**, **7,153 clips** total (4,408 event + 2,745 background), 80/20 split.
  - Training: AdamW, wd 8e-5, cosine LR 1e-3 → 8e-7, batch 4, 10 epochs = 13 h 20 min on an AMD Radeon Pro W7900.
  - Accuracy: **94.3% overall** (CS:GO 95.0, Valorant 95.0, PUBG 90.9, Fortnite 87.6, OW2 89.7); INT8-quantised 92.9% overall (OW2 collapses to 76.9); **avg F-score 0.93, AUC 0.99**.
  - **Unseen game (Apex Legends), generic prompts**: kill 69%, death 100%, background 96.7%, **89.2% average with sliding window**.
  - Cost: 768 MB FP32 → **192 MB INT8** (4×); **~0.15 s inference per 1-second clip**; 1,500 MB VRAM, 800 MB RAM; **13 FPS drop** when run alongside Fortnite averaging 80 FPS (DirectML backend, Windows).
  - **Audio not used**: "we did not use the audio modality of gameplay videos," flagged as important future work; they note CS:GO "plays a unique sound whenever a kill event occurs" that would reduce confusion.
  - HUD dependence: they claim the approach avoids the "per game engineering" that OCR needs, but concede that successful death detection correlates with "clear transition scene or display of huge and easy to detect text."
  - **No code or weights release stated** (described only as "Python notebooks").
  — [arXiv HTML](https://arxiv.org/html/2505.07721v1)
- **LOGA** — "A multimodal benchmark and audio-visual fusion baseline for long-form mobile game highlight localization" (Expert Systems with Applications / ScienceDirect S1566-2535-26-00713-X, 2026). Formulates highlight localization in long-form mobile gameplay as **query-free, multi-instance temporal localization**. Core finding: "**audio-visual fusion outperforms vision-only input on all four LOGA subsets**," with ablations showing "consistent gains over vision-only input across the four within-game evaluation settings, indicating that audio offers complementary evidence for highlight localization in long-form gaming video" — [ScienceDirect abstract (403 on fetch; details from search snippets)](https://www.sciencedirect.com/science/article/abs/pii/S156625352600713X)
- **Deep Unsupervised Multi-View Detection of Video Game Stream Highlights** (Charles Ringer, Mihalis A. Nicolaou, Goldsmiths; **FDG 2018**): PUBG streams from two streamers, **11 videos, >5 hours**, each 19:30–30:40. Architecture: convolutional autoencoders (stacked VGG16-like) separately on **face cam** and **game footage**, audio via STFT with PCA restricted to **300–3400 Hz** (human speech band), late temporal fusion with LSTM + FC. Objective: next-frame prediction / reconstruction error as novelty-based highlight proxy. Result: 98 candidate clips generated; manual categorisation found **77% true highlights when all modalities were combined**; no formal precision/recall reported. No code — [ar5iv HTML](https://ar5iv.labs.arxiv.org/html/1807.09715)

**Broadcast esports**
- **Non-local attention network for LoL** — "Discriminative and efficient non-local attention network for league of legends highlight detection" (Complex & Intelligent Systems, 2022, doi 10.1007/s40747-022-00762-1): "an end-to-end framework for learning both spatial and temporal dependencies in a non-local attention network for LoL video highlight detection, while significantly reducing computation cost" — [Springer](https://link.springer.com/article/10.1007/s40747-022-00762-1); [full text PDF](https://d-nb.info/1264743114/34)
- **Visual-effect CNNs** — "Most video games use pronounced visual effects to emphasize highlight moments; CNNs have been used to learn convolution filters of those visual effects for detecting highlights" — [Springer, same paper](https://link.springer.com/article/10.1007/s40747-022-00762-1)
- **Yahoo Esports** — "Real-Time Video Highlights for Yahoo Esports" (2016), an industrial real-time pipeline — [ResearchGate record](https://www.researchgate.net/publication/311066413_Real-Time_Video_Highlights_for_Yahoo_Esports)
- **LoL coaching** — "Real-Time Game Highlight Detection for Data-driven League of Legends Coaching" (IRI-UPC): identifies impactful moments by fusing visual and audio cues, extracting visual indicators via **optical flow and colour intensity**, and audio excitement from **caster commentary pitch and volume** — [PDF](http://www.iri.upc.edu/files/scidoc/3040-Real-time-game-highlight-detection-for-data-driven-league-of-legends-coaching.pdf)
- **Twitch chat** — multimodal char-level CNN-RNN over chat + video on LoL championship streams (EMNLP 2017) — [ACL Anthology](https://aclanthology.org/D17-1102.pdf)
- Industry practice for games without structured HUD: systems "score audio and chat signals higher since there is no kill feed to read"; for "horror and survival where events don't show up on scoreboards, detection leans on player reaction and audio spikes instead" — [transcriptr.ai commercial writeup](https://transcriptr.ai/blog/ai-gaming-clip-generator); commercial product in this space: [Eklipse](https://eklipse.gg/features/ai-highlights/)

### Inferences
- **Every high-accuracy esports result in the literature leans on structured production signals that GTA single-player does not have**: kill feed, scoreboard, canned kill visual effects, caster audio, chat. The AMD X-CLIP result is the closest to GTA (raw gameplay, no caster, no chat) but its event vocabulary *is* the FPS HUD vocabulary, and its one honest generalisation test (unseen game, generic prompts) lost 25 points on kills.
- Open-world GTA has no analogue of "kill" as a crisp, visually-announced, 1-second event. The transferable part of the AMD recipe is the *shape* — CLIP-family video encoder, 1-second clips, prompt-conditioned classification, INT8 quantisation, ~0.15 s/clip — not its label set. A GTA label set would have to be built around things that are visually/acoustically evident without HUD: vehicle crash, explosion, police chase/siren onset, fall from height, gunfight, near-miss, large physics event.
- Ringer & Nicolaou's 77%-usable-clips from pure audio-visual novelty on PUBG, with no labels at all, is arguably the most honest baseline for what a zero-label GTA pipeline should expect. Note that their face-cam branch and speech-band audio filter are both inapplicable to a bare GTA capture with no webcam and no mic.
- LOGA is the single most load-bearing citation for the GTA design decision: on **long-form, query-free** game video, audio is not optional.

### Gaps
- LOGA's actual size (hours, video count, game titles), annotation protocol, baseline architecture and numeric results — ScienceDirect 403. I can only report its qualitative audio-visual-beats-vision conclusion, which was consistently stated across multiple search snippets.
- No published highlight-detection work found for **GTA specifically**, or for any open-world/sandbox title. Searches for open-world/no-kill-feed highlight detection returned only commercial tool copy, not peer-reviewed work. This is a genuine hole in the literature.
- No CS:GO/CS2-specific academic paper surfaced (CS:GO appears only as one of five games in the AMD dataset). No Dota or Valorant-specific paper surfaced either. No Riot, Tencent-games, or Microsoft esports-extraction paper surfaced beyond Tencent's general-video RASL and the 2016 Yahoo work.

---

## Q4. Generic video-understanding models vs task-specific HUD reading

### Takeaway
The cleanest head-to-head available is the QVHighlights leaderboard, and it is brutal: **zero-shot video-LLMs score HIT@1 ≈ 0.3–0.6 where a fine-tuned version of the same backbone scores 88.4**. Off-the-shelf "find the exciting part" from a VLM does not work; the same backbone adapted with a grounding head or a token-sampling module does. Meanwhile task-specific HUD-reading achieves 94% on FPS events but is non-transferable, and long-video performance collapses for everyone.

### Cited Findings
- **Zero-shot vs adapted, same backbone, same benchmark** (QVHighlights val, HIT@1 / mAP) — [SOTA2](https://www.sota2.com/research/sota/highlight-detection-on-qvhighlights-val):
  - Qwen2.5VL-7B zero-shot **0.6 / 24.9** → grounding fine-tuned 44.5 / 34.4 → GroundVTS-Q 58.8 / 35.7
  - InternVL3.5-8B zero-shot **0.32 / 24.8** → grounding fine-tuned 39.8 / 31.9 → GroundVTS-I **88.4 / 52.5**
  - Purpose-built video-LLM grounding models also underperform the DETR line: TimeChat 23.9 / 14.5, VTG-LLM 33.5 / 16.5 vs CG-DETR 66.7 / 40.8
- **Frozen CLIP features + a small temporal head are extremely competitive**: R2-Tuning with CLIP-only features reaches 64.13 / 39.45, essentially matching UMT with SlowFast+CLIP+audio (64.2 / 39.9) — [SOTA2](https://www.sota2.com/research/sota/highlight-detection-on-qvhighlights-val)
- **Long-video collapse**: TF-SELECTOR, the best method on SVHighlights (2 h sports videos), reaches **mAP 12.81 and HIT@1 26.56** — against HIT@1 ~88 for the best method on 150-second QVHighlights clips. SVHighlights exists precisely because "prior benchmark studies have primarily focused on short-form videos, with these datasets containing videos under 5 minutes in duration on average" — [alphaXiv SVHighlights](https://www.alphaxiv.org/abs/2606.06926); [arXiv HTML](https://arxiv.org/html/2606.06926)
- **Fine-tuning a generic video-language model on gameplay works very well in-domain**: AMD "finetuned a multimodal general purpose video understanding model (X-CLIP) using a custom dataset, achieving more than 90% accuracy for detecting interesting events in first-person shooting games from unseen gameplay footage" — [arXiv HTML](https://arxiv.org/html/2505.07721v1)
- **…but degrades out-of-domain**: on unseen Apex Legends, kill detection fell to 69% while death detection held at 100% — and death is the event with "clear transition scene or display of huge and easy to detect text," i.e. the strongest HUD cue — [arXiv HTML](https://arxiv.org/html/2505.07721v1)
- **Audio-visual fusion beats vision-only on long-form game video on all four LOGA subsets** — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S156625352600713X)
- **LLM-over-captions, training-free, is the current best recipe for >1 h video**: TF-SELECTOR scores segments from "visual captions, transcripts, audio volume" with an LLM, explicitly "without frame-level scoring" — [arXiv abs](https://arxiv.org/abs/2606.06926)
- Zero-shot LLM-guided summarisation is an active alternative framing: "Prompts to Summaries: Zero-Shot Language-Guided Video Summarization with Large Language and Video Models" (arXiv 2506.10807) — [arXiv](https://arxiv.org/html/2506.10807v2)

### Inferences
- For GTA, the useful reading of these numbers is: **do not expect a video-LLM prompted with "find the exciting parts" to work**. The two credible routes are (a) frozen CLIP/SigLIP features + a small learned or heuristic saliency head (the R2-Tuning/HL-CLIP shape, cheap and the backbone is reusable), or (b) the TF-SELECTOR shape — caption/transcribe/measure-audio per segment, then let an LLM rank segments. (b) is the only one in the literature actually demonstrated at the 2-hour scale, and it needs no training.
- The HUD-reading advantage is real but is exactly what GTA removes. Expect the AMD-style approach to lose most of its margin: its best-detected class (death) is a HUD/transition artefact, and its worst (kill, 69% unseen) is the one requiring genuine visual understanding.
- The SVHighlights number (HIT@1 26.56) should be read as the realistic ceiling for an off-the-shelf method on hour-scale footage, and sports broadcast is *easier* than open-world sandbox play — it has a bounded event vocabulary, a scoreboard, and commentary.

### Gaps
- No head-to-head anywhere of "generic video-LM vs HUD/OCR pipeline" **on the same gameplay footage**. The comparison above is assembled across benchmarks and is therefore indicative, not a controlled result. Flag this to the writer.

---

## Q5. Audio-only event detection models

### Takeaway
BEATs is the accuracy leader on AudioSet-527 (48.6% mAP), PaSST is the efficient-transformer option (0.471), PANNs CNN14 (0.431, ~81M params, open code, **frame-level** outputs enabling onset/offset) is the practical workhorse, YAMNet is the cheap edge baseline (521 classes at 0.96 s resolution), and CLAP is the one that matters most for GTA because it is **open-vocabulary zero-shot** — you can prompt for "car crash", "explosion", "police siren", "machine gun fire" without retraining. All of them cover gunshot / explosion / siren / screaming / music within the AudioSet ontology.

### Cited Findings

**AudioSet mAP (527 classes)** — note a source conflict, flagged below:
- BEATs iter3+ **48.6%** mAP on full AudioSet (AS-2M); AST 45.9%; PANNs 43.1%; CLAP 46.9% — [canlab scoping review](https://github.com/canlab/narrative_feature_annotations/blob/main/docs/scoping_review/03_audio.md)
- AST paper itself reports **0.485 mAP** on AudioSet, and that figure is the **Ensemble-M** result, not a single model — [AST, Interspeech 2021](https://sls.csail.mit.edu/publications/2021/YuanGong_Interspeech-2021.pdf); [ar5iv](https://ar5iv.labs.arxiv.org/html/2104.01778)
- PaSST-S: **0.471 mAP**, 87.0M params — [PaSST, Interspeech 2022](https://www.isca-archive.org/interspeech_2022/koutini22_interspeech.pdf)
- PANNs CNN14: **0.431 mAP and 0.973 AUC** on the AudioSet eval set — [PANNs](https://arxiv.org/pdf/1912.10211); [surrey postprint](https://personalpages.surrey.ac.uk/w.wang/papers/KongCIWWP_TASLP_2020_postprint.pdf)

**Architecture / output / cost**
- **BEATs** (Microsoft, 2022–2023): self-supervised acoustic-tokenizer ViT encoder fine-tuned on AudioSet-2M; output "527-dim AudioSet class probability vector per analysis window"; rated best-in-class — [scoping review](https://github.com/canlab/narrative_feature_annotations/blob/main/docs/scoping_review/03_audio.md)
- **PaSST** (2022): DeiT-style spectrogram transformer with **patchout** regularisation, "designed to train/infer efficiently on a single GPU" — [scoping review](https://github.com/canlab/narrative_feature_annotations/blob/main/docs/scoping_review/03_audio.md); [PaSST paper](https://www.isca-archive.org/interspeech_2022/koutini22_interspeech.pdf)
- **AST** (MIT, 2021): pure ViT over log-mel spectrograms, "527-dim AudioSet class probabilities per ~10 s window"; **88.0M params**; "largely superseded by BEATs/PaSST on AudioSet mAP". Code: `github.com/YuanGongND/ast` — [scoping review](https://github.com/canlab/narrative_feature_annotations/blob/main/docs/scoping_review/03_audio.md); [AST repo](https://github.com/YuanGongND/ast)
- AST throughput reported as **88.7 samples/s at inference, batch of 64 × 10 s clips on a single V100-32GB** — [search summary of AST/PaSST comparison](https://www.isca-archive.org/interspeech_2022/koutini22_interspeech.pdf) — **treat as uncertain**, see conflict note below
- **PANNs CNN14**: "~81M parameters and requires more than 50G MACs for inference corresponding to a 10s audio clip"; exposes "527-dim AudioSet clipwise probabilities; CNN14 also exposes **framewise (segment-level) predictions**," which "enables onset/offset localization." Code: `github.com/qiuqiangkong/audioset_tagging_cnn` — [PANNs](https://arxiv.org/pdf/1912.10211); [scoping review](https://github.com/canlab/narrative_feature_annotations/blob/main/docs/scoping_review/03_audio.md); [repo](https://github.com/qiuqiangkong/audioset_tagging_cnn)
- **PANNs MobileNet variants**: MobileNetV1 ~4M params, 3.6×10⁹ multi-adds, ≈0.389 mAP; MobileNetV2 ~3M params, 2.8×10⁹ multi-adds, ≈0.379 mAP — vs CNN14's 42.2×10⁹ multi-adds — [PANNs](https://arxiv.org/pdf/1912.10211); [Emergent Mind summary](https://www.emergentmind.com/topics/pretrained-audio-neural-networks-panns)
- **E-PANNs**: efficient PANNs with **24M parameters and 13G MACs per 10 s** of audio. Code: `github.com/Arshdeep-Singh-Boparai/E-PANNs` — [E-PANNs](https://openresearch.surrey.ac.uk/view/pdfCoverPage?instCode=44SUR_INST&filePid=13186519080002346&download=true); [repo](https://github.com/Arshdeep-Singh-Boparai/E-PANNs)
- **YAMNet** (Google): a **521-class subset** of AudioSet, "521-dim AudioSet-class scores per **0.96 s frame**"; positioned as the "lightweight…fast/edge baseline", rated "alternative only" — [scoping review](https://github.com/canlab/narrative_feature_annotations/blob/main/docs/scoping_review/03_audio.md)
- **CLAP** (2022–2023): "contrastive language-audio embedding enabling **OPEN-VOCABULARY zero-shot audio classification**"; "512-dim joint audio and text embeddings"; works "beyond the fixed AudioSet ontology"; rated best-in-class, recommended "for custom prompts" — [scoping review](https://github.com/canlab/narrative_feature_annotations/blob/main/docs/scoping_review/03_audio.md)
- Zero-shot CLAP "reaches 82–91% top-1 accuracy on ESC-50 depending on prompts and checkpoints" — [search synthesis over CLAP zero-shot literature](https://arxiv.org/pdf/2410.15062); prompt-formulation sensitivity is itself a studied effect — [PAT: Parameter-Free Audio-Text Aligner](https://arxiv.org/pdf/2410.15062)
- ESC-50 reference: "2,000 environmental audio recordings, every 5 seconds in length, organized into 50 semantically distinct classes with 40 examples per class" — [ESC-50 via benchmark paper](https://arxiv.org/pdf/2412.03771)
- Heavier CNNs are materially slower: "ConvNeXt, Res1dNet51, Wavegram_Logmel, and ResNet54 exhibit higher inference times, generally **between 2 and 3 seconds**" on resource-constrained devices — [Comprehensive Evaluation of CNN-Based Audio Tagging Models on Resource-Constrained Devices, arXiv 2509.14049](https://arxiv.org/pdf/2509.14049)
- **Relevant classes**: the AudioSet ontology used by all of these includes "speech, music, laughter, dog, vehicle, **gunshot**, applause, rain" — [scoping review](https://github.com/canlab/narrative_feature_annotations/blob/main/docs/scoping_review/03_audio.md). Emergency-sound work targets "explosion, fire, gunshot, screaming, shouting and other emergency sounds" with CLAP and related methods; the Gunshot Triangulation dataset uses 4 classes — "Casual (not a threat), Gunshot, Explosion, and Siren" — [DCASE 2024 workshop paper](https://dcase.community/documents/workshop2024/proceedings/DCASE2024Workshop_Lin_14.pdf)
- Practical advice from the scoping review, worth quoting to the writer: "Choose **ONE** primary AudioSet tagger (BEATs or PaSST) rather than running AST+PANNs+YAMNet+BEATs together, since their 527-class outputs are highly correlated" — [scoping review](https://github.com/canlab/narrative_feature_annotations/blob/main/docs/scoping_review/03_audio.md)
- Transductive/zero-shot audio-language classification is an active 2026 topic — [Transductive Zero-Shot Audio Classification with Audio–Language Models, arXiv 2606.17160](https://arxiv.org/html/2606.17160v1)

### Inferences
- For GTA specifically, the audio ontology is unusually well matched: gunshot, machine gun, explosion, siren/emergency vehicle, screaming, vehicle/skidding/crash, and music (radio) are all AudioSet classes, and GTA's audio design makes them loud and unambiguous. This is the single strongest HUD-free signal available, and it is the modality the AMD paper left on the table.
- **PANNs CNN14 is likely the best first choice for this project despite being third on mAP**, because it is the one model in the list that exposes framewise predictions for onset/offset localisation — which is what you need to cut a clip, not just tag a 10-second window — and it has permissive open code. BEATs/PaSST give per-window tags only unless you window them yourself.
- **CLAP should be used alongside it**, not instead: GTA-specific concepts ("police siren approaching", "car explosion", "helicopter") are prompt-expressible and need no training data.
- Cost is a non-issue at this scale: CNN14 at >50 G MACs per 10 s means a 2-hour session is ~720 windows; even at 2–3 s/window worst case (the slow ConvNeXt-class figure) that is under an hour on CPU, and far less with CNN14 or a MobileNet variant. Audio is cheap enough to run densely over the whole session and use as the *first-stage retrieval*, with visual models applied only to surviving candidates.

### Gaps
- **Source conflict on AudioSet mAP**: the scoping review lists "AST 45.9 / PANNs 43.1 / CLAP 46.9 / BEATs 48.6" while the AST paper's own headline is 0.485 (ensemble) and the PANNs paper's own figure is 0.431. The ≈0.459 figure is AST's single-model result. The "CLAP 46.9" figure is unsourced in the review and I would not report it without verification — CLAP is normally evaluated zero-shot, not as a supervised AudioSet tagger, so that number is suspect.
- The "88.7 samples/s" throughput figure appeared attached to **both** AST (inference throughput) and PaSST-S (training speed) in search summaries. That coincidence is almost certainly a conflation by the search summariser; I did not get a clean read of the original table. **Do not quote a throughput number for either model without checking the PaSST paper's Table 1 directly.**
- No per-class (gunshot/explosion/siren) AP numbers found for any of these models; the scoping review explicitly "provides no specific mAP scores, parameter counts, or inference speeds for individual models or specific event classes like gunshots, explosions, or screaming."
- Licences: only repo URLs confirmed, not licence text. PANNs (`audioset_tagging_cnn`) and AST are commonly MIT/Apache but unverified here; YAMNet ships under TF-Hub's Apache-2.0 terms in general but unverified here; CLAP checkpoints vary by provider (LAION-CLAP vs Microsoft CLAP have different terms).

---

## Q6. Standard benchmarks, current numbers, and resemblance to gameplay footage

### Takeaway
The canonical benchmarks are **tiny, short, and nothing like gameplay**: TVSum is 50 videos, SumMe is 25, YouTube Highlights is ~700 across six sports/pet domains, and QVHighlights clips average ~150 s of vlog/news. Only **Mr.HiSum** (31,892 videos) is large, and only **SVHighlights** (320 videos, 640 h, avg 2.00 h each) is long — and the best SVHighlights score is HIT@1 26.56 vs ~88 on QVHighlights. For a 2-hour GTA session, SVHighlights is the only benchmark whose *shape* resembles the problem, and even it is professionally-produced sports.

### Cited Findings

**Dataset specs**
- **YouTube Highlights**: six domain-specific categories — surfing, skating, skiing, gymnastics, parkour, dog — "approximately 100 videos per domain totaling around 1430 minutes"; elsewhere described as "only 712 videos from only 6 specific categories" — [SVHighlights](https://arxiv.org/html/2606.06926); [Mr.HiSum NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/file/7f880e3a325b06e3601af1384a653038-Paper-Datasets_and_Benchmarks.pdf)
- **TVSum**: 50 YouTube videos, 10 categories × 5 videos, shot-segmented with manually annotated importance scores — [TVSum](https://www.researchgate.net/publication/308861592_TVSum_Summarizing_web_videos_using_titles)
- **SumMe**: 25 raw user-generated videos of everyday activities, ~1–6 min each, multiple human ground-truth summaries — [Mr.HiSum NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/file/7f880e3a325b06e3601af1384a653038-Paper-Datasets_and_Benchmarks.pdf)
- Explicit limitation statement: "SumMe and TVSum suffer from two critical limitations: extremely small scale (25 and 50 videos, respectively) and **unimodal annotation based solely on visual cues**" — [Mr.HiSum NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/file/7f880e3a325b06e3601af1384a653038-Paper-Datasets_and_Benchmarks.pdf)
- **QVHighlights** (Lei, Berg & Bansal, NeurIPS 2021): 7,218 train / 1,550 val / 1,542 test query-video samples (10,310 total); "on average 1.8 moments per query in a video, while all the [other] moment retrieval datasets can only have a single moment"; natural-language queries over vlog and news video — [NeurIPS 2021 PDF](https://papers.neurips.cc/paper/2021/file/62e0973455fd26eb03e91d5741a4a3bb-Paper.pdf); [arXiv](https://arxiv.org/pdf/2107.09609)
- **Mr.HiSum** (NeurIPS 2023 D&B): 31,892 videos, labels aggregated from 50,000+ users per video via YouTube "Most replayed", normalised 0–1; baselines PGL-SUM, VASNet, SL-module — [NeurIPS PDF](https://proceedings.neurips.cc/paper_files/paper/2023/file/7f880e3a325b06e3601af1384a653038-Paper-Datasets_and_Benchmarks.pdf); [repo](https://github.com/MRHiSum/MR.HiSum)
- **SVHighlights** (Jun 2026): "the first benchmark for highlight detection in sports videos exceeding one hour each" — **320 videos, average duration 2.00 hours, 640.18 total hours** — [arXiv abs](https://arxiv.org/abs/2606.06926)
- **SoccerHigh** (arXiv 2509.01439, Sep 2025) — a soccer-specific summarisation benchmark — [arXiv](https://arxiv.org/html/2509.01439)

**Current numbers**
- QVHighlights val HD: top = GroundVTS-I 88.4 HIT@1 / 52.5 mAP (2026.04); strong non-LLM = FlashVTG 72.9 / 44.15 (2024.12); Moment-DETR floor = 55.6 / 35.7 — [SOTA2](https://www.sota2.com/research/sota/highlight-detection-on-qvhighlights-val)
- YouTube Highlights avg mAP: LSVM 0.464, Video2GIF 0.54, RARE 0.38, LM 0.564, MINI-Net 0.584, LR 0.630, CHD 0.654, RASL (unsupervised) 0.651 — [RASL, ar5iv](https://ar5iv.labs.arxiv.org/html/2403.09401)
- TVSum Top-5 mAP avg: KVS 0.398, DPP 0.447, sLSTM 0.451, SM 0.461, CHD 0.528, MINI-Net 0.702, LR 0.768, RASL 0.783 — [RASL, ar5iv](https://ar5iv.labs.arxiv.org/html/2403.09401); AHA adds +5.9% mAP on TVSum over prior offline methods in an online setting — [AHA](https://arxiv.org/abs/2509.16421)
- Mr.HiSum: 64.19 mAP@50 / 32.66 mAP@15, "+8.3 mAP@50 over PGL-SUM" (AHA) — [AHA PDF](https://arxiv.org/pdf/2509.16421)
- SVHighlights: TF-SELECTOR mAP **12.81**, HIT@1 **26.56** — [SOTA2 search synthesis citing SVHighlights](https://arxiv.org/html/2606.06926)

**Resemblance to gameplay**
- None of TVSum, SumMe, YouTube Highlights or QVHighlights contains gameplay as a category: YouTube Highlights is six sports/pet domains; TVSum is 10 web-video categories; SumMe is "everyday activities"; QVHighlights is vlog + news — [Mr.HiSum](https://proceedings.neurips.cc/paper_files/paper/2023/file/7f880e3a325b06e3601af1384a653038-Paper-Datasets_and_Benchmarks.pdf); [QVHighlights](https://arxiv.org/pdf/2107.09609)
- Gameplay-specific benchmarks exist only recently and are not in the general leaderboards: **LOGA** (long-form mobile game, query-free multi-instance, 2026) and AMD's unreleased 7,153-clip FPS set (2025) — [LOGA](https://www.sciencedirect.com/science/article/abs/pii/S156625352600713X); [AMD](https://arxiv.org/html/2505.07721v1)

### Inferences
- **Benchmark numbers from TVSum/SumMe/YouTube Highlights should not be used to predict GTA performance at all.** Beyond the domain gap, they are 1–6 minute curated clips where roughly 10–20% of the video is highlight; a 2-hour GTA session has a highlight *rate* of maybe 1–2%, which changes the problem from ranking to extreme-imbalance detection. The literature's standard metrics (Top-5 mAP on a 3-minute video) are not even well-defined for that regime.
- The honest expectation-setting number for the report is the SVHighlights one: on hour-scale video with a bounded event vocabulary and commentary, the best published method gets **HIT@1 26.56**. GTA is harder on every axis except that the user only needs a handful of good clips, not complete recall — which is why precision@k, not mAP, is the right metric for this project.
- Mr.HiSum is the only benchmark whose labels ("what did 50,000 viewers re-watch") match the actual product objective, and at 31,892 videos it is the only one large enough to pretrain a general-purpose saliency head that could then be adapted with a handful of GTA sessions.

### Gaps
- Mr.HiSum's exact baseline mAP table (PGL-SUM / VASNet / SL-module absolute numbers) — the NeurIPS PDF host refused the connection; I only have AHA's relative "+8.3 mAP@50 over PGL-SUM" and its own 64.19/32.66.
- Mr.HiSum licence not confirmed (the repo distributes extracted features rather than video, which usually implies a research-only arrangement, but I did not verify).
- Whether the SVHighlights dataset and TF-SELECTOR code are actually released: the paper "mentions a project page but the content does not explicitly confirm code or dataset availability."

---

## Cross-cutting notes for the GTA application (methods that degrade without a structured HUD)

### Degrade badly / do not transfer
- Anything that reads a **kill feed, scoreboard, or canned kill effect**: the LoL visual-effect CNNs, the non-local attention LoL network, Autohighlight, the Yahoo Esports pipeline. All assume broadcast production — [Springer LoL](https://link.springer.com/article/10.1007/s40747-022-00762-1); [IRI-UPC](http://www.iri.upc.edu/files/scidoc/3040-Real-time-game-highlight-detection-for-data-driven-league-of-legends-coaching.pdf)
- Anything keyed on **caster commentary pitch/volume** or **chat rate**: IRI-UPC LoL coaching, EMNLP 2017 chat model. Single-player GTA with no mic has neither — [ACL](https://aclanthology.org/D17-1102.pdf)
- The **AMD X-CLIP event vocabulary** (kill/death/reload/bomb-planted): these are FPS-HUD events. Its own unseen-game test shows the HUD-light event (kill) dropping to 69% while the HUD-heavy one (death) stayed at 100% — [AMD](https://arxiv.org/html/2505.07721v1)
- **Query-conditioned MR models** (Moment-DETR → CG-DETR → FlashVTG) need a text query; without one you are only using their saliency head, which is the weaker half of those systems.
- **Face-cam branches** (Ringer & Nicolaou) and speech-band audio filtering: no webcam, no mic — [ar5iv](https://ar5iv.labs.arxiv.org/html/1807.09715)
- **Short-video assumptions**: every method validated only on <5 min clips. The SVHighlights paper exists because of this — [arXiv](https://arxiv.org/html/2606.06926)

### Likely to transfer
- **Audio event detection** (PANNs CNN14 framewise for onset/offset + CLAP for open-vocabulary GTA-specific prompts). GTA's gunfire, sirens, explosions and crashes are exactly AudioSet classes, and LOGA's finding that audio-visual fusion beats vision-only on *all four* long-form game subsets is the directly on-point result — [PANNs](https://arxiv.org/pdf/1912.10211); [LOGA](https://www.sciencedirect.com/science/article/abs/pii/S156625352600713X); [scoping review](https://github.com/canlab/narrative_feature_annotations/blob/main/docs/scoping_review/03_audio.md)
- **TF-SELECTOR's training-free segment+LLM recipe** — shot-group segmentation, caption each segment, add audio volume, let an LLM score. No labels, no training, demonstrated at 2-hour scale — [arXiv](https://arxiv.org/abs/2606.06926)
- **AHA's constant-memory streaming head** (Dynamic SinkCache) if the pipeline ever needs to run live over a long session — [arXiv](https://arxiv.org/abs/2509.16421)
- **Unsupervised recurrence/novelty scoring** (RASL, WACV 2025 audio-visual recurrence, the 2015 recurrent autoencoder line) — no labels needed, and "what is unusual for this session" is a defensible prior for open-world footage where 95% of frames are routine traversal — [RASL ar5iv](https://ar5iv.labs.arxiv.org/html/2403.09401); [WACV 2025](https://openaccess.thecvf.com/content/WACV2025/papers/Islam_Unsupervised_Video_Highlight_Detection_by_Learning_from_Audio_and_Visual_Recurrence_WACV_2025_paper.pdf)
- **"This segment was clipped" weak supervision** from the user's own saved clips — the Autohighlight / SVHighlights construction, applicable with zero annotation effort if any clip history exists — [SVHighlights](https://arxiv.org/abs/2606.06926)
- **Frozen CLIP features + a tiny temporal head**: R2-Tuning with CLIP-only features reaches 64.13 HIT@1, within 0.1 of UMT with SlowFast+CLIP+audio, i.e. the expensive backbones buy almost nothing — [SOTA2](https://www.sota2.com/research/sota/highlight-detection-on-qvhighlights-val)
- **INT8 quantisation of the video encoder**: AMD's 4× size reduction (768 → 192 MB) cost only 1.4 points of overall accuracy, though it was much worse for under-represented games — [AMD](https://arxiv.org/html/2505.07721v1)

### Code / licence status of the most relevant artefacts
- MLLM Frame Segmentation — `github.com/bagasjiwanta/llm-frame-segmentation`, **CC BY-SA 4.0** (note: a share-alike licence, relevant if the project ships anything derived) — [arXiv](https://arxiv.org/html/2512.12246v1)
- SRF — `github.com/VisualAIKHU/SRF`, licence unknown — [arXiv](https://arxiv.org/abs/2511.22906)
- PANNs — `github.com/qiuqiangkong/audioset_tagging_cnn`, licence not verified here — [repo](https://github.com/qiuqiangkong/audioset_tagging_cnn)
- E-PANNs — `github.com/Arshdeep-Singh-Boparai/E-PANNs`, licence not verified — [repo](https://github.com/Arshdeep-Singh-Boparai/E-PANNs)
- AST — `github.com/YuanGongND/ast`, licence not verified — [repo](https://github.com/YuanGongND/ast)
- Mr.HiSum data/code — `github.com/MRHiSum/MR.HiSum`, licence not verified — [repo](https://github.com/MRHiSum/MR.HiSum)
- VideoITG (NVIDIA, CVPR 2026 Highlight) — `github.com/NVlabs/VideoITG`, licence not verified (NVlabs repos are typically research-only non-commercial) — [repo](https://github.com/NVlabs/VideoITG)
- AMD Gameplay Highlights Generation — **no code or weights released**; the most directly relevant gameplay result is not reproducible — [arXiv](https://arxiv.org/html/2505.07721v1)
- RASL (Tencent) — no code link in the paper — [ar5iv](https://ar5iv.labs.arxiv.org/html/2403.09401)
- TF-SELECTOR / SVHighlights — project page mentioned, release not confirmed — [arXiv](https://arxiv.org/abs/2606.06926)
