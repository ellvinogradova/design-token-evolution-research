# Design Token Evolution and Accessibility Drift Across Major Open-Source Design Systems

**Olena Vynohradova** — UI/UX & Product Designer, New York, NY
[hello@ellvinogradova.com](mailto:hello@ellvinogradova.com) · [ux.ellvinogradova.com](https://ux.ellvinogradova.com)

A structural audit of token-architecture evolution across five major open-source design
systems — Ant Design, Fluent UI, Carbon Design System, MUI, and Shopify Polaris — comparing
each system's token source immediately before and after its most significant documented
token-architecture transition, on a single externally-grounded rubric (W3C DTCG format
compliance + three WCAG 2.2-cited accessibility-token categories).

**Central finding:** token-architecture formalization and accessibility-token coverage are
largely decoupled. Four of five systems showed zero change in accessibility-token coverage
despite substantial architectural rewrites, and none of the five define a minimum
touch/click target-size token in either version studied, despite WCAG 2.2 SC 2.5.8 being a
Level AA requirement since October 2023.

Full writeup: [`paper/draft.md`](paper/draft.md) ([LaTeX](paper/latex/paper.tex) /
[PDF](paper/latex/paper.pdf)). Day-by-day process notes: [`RESEARCH_LOG.md`](RESEARCH_LOG.md).

## Repository structure

```
data/
  preflight/                 pre-flight verification of each system's repo/tag/paths
  extraction-manifest.json   reproducibility record of what was pulled and from where
  reliability_sample.json    the seeded 20% sample used for the blind reliability check
  reliability_blind_raw/     raw output of the context-isolated blind re-code
paper/
  draft.md                   full paper (markdown)
  latex/                     LaTeX source + compiled PDF
  figures/                   generated figures (token counts, sub-score, migration cost)
results/
  tokens_*.json               per-system extracted token sets, before/after
  objective_subscores.json    the 0-4 objective sub-score per system/phase
  hand_verification_report.json  10% hand-verification QA pass on extracted tokens
  reliability_check.json      blind re-code results (Table 2 in the paper)
  proposals/                   DTCG-format accessibility-token augmentation proposals
                                for the two lowest-scoring systems (Ant Design, Carbon)
  dataset.csv                  consolidated dataset backing the paper's figures/tables
scripts/
  01_extract_tokens.py         sparse-checkout extraction driver (reads data/preflight/*.json)
  parse_*.py                   per-system, format-aware token parsers
  03_score_objective_subscore.py   computes the 0-4 objective sub-score
  04_hand_verify_sample.py     hand-verification QA pass on extracted tokens
  05_generate_figures.py       generates paper/figures/*.png from results/
```

## Reproducing the pipeline

```
python scripts/01_extract_tokens.py        # sparse-checkout each system's before/after source
python scripts/parse_<system>.py           # per-system token extraction
python scripts/03_score_objective_subscore.py
python scripts/04_hand_verify_sample.py
python scripts/05_generate_figures.py
```

`data/repos/` (the sparse-checked-out third-party source) is gitignored and re-derivable
from `data/extraction-manifest.json` — it is not vendored into this repository.

## Scope note

This is a structural/computational audit of public repository history, not a usability
study. No external participants were recruited or tested; all data originates from public
repositories under permissive OSI licenses (MIT/Apache-2.0). See §7–8 of the paper for full
limitations and ethical/legal considerations.

## License

MIT — see [LICENSE](LICENSE).
