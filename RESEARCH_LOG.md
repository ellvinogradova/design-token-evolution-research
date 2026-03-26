# Research Log

*Reconstructed from the project's commit history after the local repository was
accidentally deleted and restored. Entries reflect the work completed each day,
March 20–25, 2026.*

## Day 1 — March 20, 2026: Lock research plan and pre-flight-verified sample (5 systems)

- Verified all 5 systems' repos, tags, and token file paths against live GitHub/npm/Bitbucket
  data before committing to extraction.
- Ant Design (4.24.16 -> 5.0.0), Carbon (v10.60.5 -> v11.0.0) confirmed as originally planned.
- Fluent UI after-reference switched from the never-stabilized `@fluentui/tokens` alpha
  package to the stable `@fluentui/react-theme` v9.0.0, which wraps it.
- MUI after-reference confirmed (v5.16.7 -> v6.0.0) but CSS-variable theming is a gradual
  graduation from experimental (v5.6.0) to stable, not a v6 introduction.
- Atlassian Design System failed verification: its only public mirror (Bitbucket) has zero
  git tags and bot-squashed history, so the pre-registered fallback (Shopify Polaris,
  polaris-tokens 7.12.1 -> 8.0.0) was invoked instead.
- Plan document updated in place with the locked sample table and reasoning for every
  deviation from the original draft.

## Day 2 — March 21, 2026: Extract token source files for all 5 systems (before/after)

- `scripts/01_extract_tokens.py`: reproducible shallow + sparse-checkout clone driver,
  reading repo/tag/path data directly from Day 1's `data/preflight/*.json` files.
- Uses git partial clone (`--filter=blob:none`) + sparse-checkout so each of the 10 clones
  (5 systems x before/after) pulls only the confirmed token source paths, not the full
  monorepos — 25M total vs. what would otherwise be several GB across fluentui/mui/carbon.
- `data/repos/` is gitignored (re-derivable third-party source, not vendored);
  `data/extraction-manifest.json` is tracked as the reproducibility record of exactly what
  was pulled.
- Spot-checked real token content on both ends (Ant Design `seed.ts`, Polaris `colors.ts`)
  to confirm the checkouts aren't empty/broken.

## Day 3 — March 22, 2026: Parse token files, compute counts and diffs for all 5 systems

- Format-aware parsers (Less, TS object literals, SCSS/JS, JS objects) written per system,
  since each system's real token declaration syntax differs.
- Results (before -> after tokens, removed/added):
  - Ant Design: 915 -> 231 (wholesale kebab-Less -> camelCase-TS rewrite, ~34 tokens
    fuzzy-matched as likely-renamed rather than genuinely gone)
  - Carbon: 242 -> 184 (101 removed / 43 added, 67 removals cross-referenced as renames
    against the official migration guide — a staged, not abrupt, migration)
  - Fluent UI: 354 -> 576 (wholesale naming-system replacement, global+alias split
    confirmed 2-layer)
  - MUI: 110 -> 121 (near-zero churn, confirms the "gradual graduation" framing;
    `createPalette.js` is byte-identical between v5.16.7 and v6.0.0)
  - Shopify Polaris: 969 -> 674 (295 removed / 0 added — real, moderate legacy-token
    cleanup matching the CHANGELOG's own wording)
- DTCG compliance is "no" for both before and after on every system — none of the 5 ship
  native W3C DTCG-format token files.
- Fixed two Day 2 data-quality bugs found while parsing: Carbon's preflight paths had
  human notes baked into the path strings (broke sparse-checkout for 3 directories); MUI's
  "after" path list omitted `createPalette.js`, understating the after-side token count.

## Day 4 (partial) — March 23, 2026: Objective sub-score + hand-verification QA pass

- `scripts/03_score_objective_subscore.py`: computes the plan's 0–4 objective sub-score
  (DTCG + 3 WCAG-cited accessibility categories) from Day 3's data. Result: 4 of 5 systems
  show zero movement in accessibility-token coverage despite real architectural rewrites —
  only Fluent UI improved (+1, gained contrast-safe pairs).
- `scripts/04_hand_verify_sample.py`: independently re-verifies a random 10% sample of
  every system's extracted token names against the actual on-disk source, as a check on
  Day 3's parsers. Caught and fixed two real bugs in the verification script itself
  (window too small for tokens spanning >3 lines; no handling for MUI's Channel-suffix
  convention). Final result: 437/437 (100%) after manual review — no real parser errors
  from Day 3 were found.
- Reliability re-code intentionally not done in this session — it requires a genuine
  24+ hour gap from Day 3's initial coding pass to be a valid same-rater consistency check.

## Day 4 (complete) + Day 5 — March 24, 2026: Reliability check and augmentation proposals

**Reliability check (revised methodology):** a pure time gap doesn't blind an LLM within
the same conversation, so the original "wait 24h" design was replaced with genuine
blindness — fresh, context-isolated subagent instances with zero access to this
conversation or to `results/tokens_*.json`, given only the rubric and raw source. Sampled
8/40 (20%) accessibility-token binary judgments across all 5 systems' before/after states,
seeded and reproducible (`data/reliability_sample.json`). Result: 8/8 (100%) agreement
between the original coding pass and the blind re-code — framed precisely as "consistency
under genuine blindness to the original answer," not inter-rater reliability, since both
passes share the same underlying model.

**Accessibility token augmentation proposals:** Ant Design and Carbon were tied for the
lowest objective sub-score (1/4, missing contrast-safe pairs and target-size tokens — the
only 2 systems missing contrast pairs, and notably all 5 systems are missing target-size
tokens). Built real DTCG-format token proposals for both, matching each system's actual
naming conventions, with every contrast ratio computed via the real WCAG relative-luminance
formula against each system's actual shipped color values. Score deltas: both systems go
from 1/4 to 3/4. Both proposals carry an explicit "independent research proposal, not an
endorsed or merged contribution" disclaimer.

## Day 6 — March 25, 2026: Finalize paper, figures, and results

- Wrote up the full paper (`paper/draft.md`, `paper/latex/paper.tex`, compiled
  `paper/latex/paper.pdf`).
- Generated final figures (`scripts/05_generate_figures.py`): token counts, objective
  sub-score, migration cost.
- Compiled the consolidated `results/dataset.csv` and added `LICENSE` / `.gitignore` for
  publication.
