# killclip: implementation plan

Where the project stands after the proof-of-concept work, what is left to build, and in what order.
Dates assume part-time evenings from **2026-09-17**; each phase ends with something usable.

## Status

| capability | state |
|---|---|
| Kill detection, Marvel Rivals (banner + feed ownership) | shipped; 90 of 93 kills across four matches |
| Kill detection, Battlefield 6 Battle Royale (KILL box) | shipped |
| Kill detection, Battlefield 6 multiplayer (feed rows) | shipped; 49 of 50 in one match |
| Clip cutting, 9:16, EDL, crossfade montage | shipped |
| Beat-synced montage (styles, streaks, pooling, HDR colour) | shipped |
| Packaging, public repo, `killclip` console script | shipped |
| 4K recordings scanned at the templates' size | shipped |
| Hero recognition in the kill feed | proven feasible, not built |
| Kill index and queries | designed, not built |
| Hero-specific montages from a query | designed, not built |
| Works for someone else's name and machine | not built |

## What the POCs settled

- Feed rows carry both heroes as portraits: the killer's at the row's left edge, the victim's at a fixed
  right-hand slot. Tiles are 42x34 px at 1088p.
- A row is present when the middle of its band is full of vertical edges; that test removed the
  background tiles that a brightness test let through (36 junk tiles down to 0 in a one-minute probe).
- Official avatars (rivalskins.com) are **different art** from what the feed draws: a known Black Widow
  tile scores 0.36 against her avatar. They do match the large bottom-left HUD portrait (0.78 vs 0.53
  runner-up), so they name *your own* hero but not the victim's.
- Naming a 30-pixel portrait is beyond every local model tried: Qwen3-VL 8B 1 of 4, Gemma 3 27B 0 of 4,
  SigLIP 2 3 of 8, DINOv2 about 5 of 19. A frontier model reading the tile against a labelled roster
  sheet got 3 of 4, with the miss correct as second choice. Naming is therefore a one-time human or
  frontier-model step, never a per-kill step.
- Matching tile against tile is the per-kill mechanism, and DINOv3 does it best so far: same-hero pairs
  never below 0.549, different heroes up to 0.612, an overlap of 0.06. Plain pixel correlation overlaps
  by 0.51 and drops one true pair to 0.00. DINOv3 grouped Doctor Strange, The Thing and Groot unaided.
- The remaining overlap is a background effect, and the fix is fine-tuning on row tracks: one row over
  nine seconds gives the same portrait on many backgrounds (positives), and two rows in one frame give
  the same background on different portraits (hard negatives).

## Phase 1 - Hero recognition (17 Sep - 1 Oct)

| # | step | done when |
|---|---|---|
| 1.1 | Row tracker for Marvel Rivals: follow a row by its name-text strip, not its portrait | a nine-second row yields one track with 20+ tiles |
| 1.2 | Harden the harvester: reject flat and low-edge tiles, record track ids | a full match yields zero background tiles |
| 1.3 | Harvest all recordings into the tile corpus | tile count and distinct-portrait count reported |
| 1.4 | Label the portrait dictionary once (frontier model proposes, you confirm on a sheet) | every portrait seen 3+ times has a hero name |
| 1.5 | Fine-tune DINOv3 on row tracks; evaluate on a held-out match | lowest same-hero score above highest different-hero score |
| 1.6 | Matcher in the Marvel Rivals module: `my_hero`, `victim_hero` on every kill, `unknown` when unsure | the 24-tile and match sheets score 95%+ |

Milestone: `killclip detect` writes hero names into `events.json`.

## Phase 2 - The index (1 Oct - 8 Oct)

| # | step | done when |
|---|---|---|
| 2.1 | `killclip/index.py`: SQLite schema for recordings, kills, streaks, tiles, tracks, clusters, corrections | schema created and documented |
| 2.2 | `killclip index` command, plus `detect --index`; recorded-at parsed from the console file name | six existing recordings indexed |
| 2.3 | Streaks derived from banner words, with the gap rule as fallback | the known penta and hexa appear with the right size |
| 2.4 | Overlapping recordings marked, not duplicated | the two overlapping matches show 22 duplicate kills |

Milestone: every kill ever recorded is one row in a small database that outlives the footage.

## Phase 3 - Ask and build (8 Oct - 15 Oct)

| # | step | done when |
|---|---|---|
| 3.1 | `killclip query` with `--hero`, `--victim`, `--label`, `--streak`, `--since`, `--csv` | the three example questions each run as one command |
| 3.2 | The same filters on `cut`, `montage` and `beatsync`, replacing `--events` | a Spider-Man montage builds from one command |
| 3.3 | Streak queries cut the whole run as one clip | a hexa clip runs first kill to last |
| 3.4 | `killclip stats`: kills per hero played, victims per hero, streak counts | printed table matches hand counts |

Milestone: "make me a video of every kill on Spider-Man" is one line.

## Phase 4 - For other people (15 Oct onward)

| # | step | done when |
|---|---|---|
| 4.1 | Automatic name-template calibration from a first recording | a new user runs one command, no manual crop |
| 4.2 | Software encoder fallback for Linux and Windows | the test suite passes without VideoToolbox |
| 4.3 | Menu-driven CLI with a banner, and a URL as input | `killclip` with no arguments opens the menu |
| 4.4 | Ship the portrait dictionary with the package | a fresh install names heroes with no training |

## Decisions still open

- Whether the labelling step uses the Anthropic API (needs a key, cents per match) or stays interactive.
- Whether Battlefield gets weapon recognition from the row icon, the same mechanism as heroes.
- Whether the tile corpus is ever published; it is game art, so probably not.

## Risks

| risk | mitigation |
|---|---|
| Fine-tuning learns the maps in three recordings rather than heroes | in-frame hard negatives; evaluate on an unseen match |
| New skins produce portraits the dictionary does not know | `unknown` outcome plus a labelling pass on the unknown bucket |
| Hero recognition inherits kill-detection misses | index stores detection source and score; scoreboard totals stay the check |
| Recordings deleted after indexing cannot be re-harvested | back up the database, not the footage |

---

# Future scope: from facts to understanding

Everything above reads the HUD and is exact. This section covers what it would take to say *how* a
match was played, not just what happened in it. It is written as three tiers, because they differ in
how much they can be trusted, and the rule across all of them is the same: **a model may interpret a
signal, never invent one.** Anything a detector could have measured must come from the detector.

## Tier 1 - More of the HUD (exact, deterministic)

Most of what sounds tactical is already drawn on screen. Each of these is the same kind of work as the
kill feed: a fixed region, a template or a number, read at the moments that matter.

| signal | where | gives |
|---|---|---|
| Deaths | feed rows with the name on the right, already detected and currently discarded | kills and deaths, who kills you most, revenge kills |
| Health | bar under the hero portrait, bottom left | how close a fight was, clutch survivals |
| Ultimate charge | percentage bottom right | whether a streak followed an ultimate, and how long charge sat unused |
| Ability cooldowns | icon row, bottom right | which abilities were used into a kill |
| Objective progress | bar and timer, top centre | contest state at the moment of a kill |
| Minimap | bottom left | where on the map kills and deaths happen, and whether you were with the team |
| Scoreboard at match end | already detected | final hits, assists, damage, result |
| Hero switch | the HUD portrait changing | which hero you played in each part of a match |

The minimap is the one with real work in it: reading your marker, teammate markers and the objective
means template matching per map, and it yields coordinates rather than a label.

## Tier 2 - Analytics on those signals (exact, statistical)

Once tier 1 lands, questions that sound like judgement become arithmetic over the index.

- Kills per minute with the ultimate available versus not.
- How often a death follows within ten seconds of your own ultimate.
- Which hero matchups you win and lose, as a matrix of your hero against the victim's.
- Where on the map your kills and deaths cluster, per map.
- Whether streaks start from full health or from a fight already in progress.
- Which time in a match you are most and least effective.

This is the layer worth building, because it answers "how am I playing" without any model guessing, and
it feeds both the summaries and the montage selection: a highlight is a clip that scores well on
measured things such as multi-kill, low health, long streak, or a contested objective.

## Tier 3 - Narration and judgement (probabilistic, always labelled)

Only here does a model watch the footage. It is given the clip, the tier 1 signals for that moment, and
the tier 2 context, and asked to describe or assess. Two uses:

- **Narration for a video**: a sentence per clip for on-screen text or voice-over.
- **Coaching notes**: patterns across many clips, such as repeatedly dying after pushing past the point.

Rules that keep it honest:

1. Every number in the output comes from the index, never from the model.
2. The model's own claims are marked as interpretation in the output, not merged with the facts.
3. A claim it cannot ground in a supplied signal is dropped rather than shown.
4. Cost is per clip, not per frame, so it stays cents per match.

## Sequencing

| stage | depends on | rough effort |
|---|---|---|
| Deaths stored | nothing; the detector already sees them | an afternoon |
| Health, ultimate, cooldowns, objective | one calibration each | a day each |
| Scoreboard read | the header detector that already exists | two days |
| Minimap positions | per-map templates | a week, per game |
| Analytics and highlight scoring | the signals above plus the index | a week |
| Narration and coaching notes | everything above, plus a frontier model | days, mostly prompt and evaluation work |

## What stays genuinely out of reach

Intent. Why a team grouped, whether a call was right, what an opponent was about to do. Those are not
on the screen, so no amount of reading gets there, and a model asked for them will produce confident
fiction. The honest ceiling is: exact facts, measured patterns, and clearly labelled interpretation.
