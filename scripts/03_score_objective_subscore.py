#!/usr/bin/env python3
"""Day 4: compute the 0-4 objective sub-score per system per phase, per
plan section 4.3. One point each for: DTCG-format compliance,
contrast-safe color pairs present, focus-ring tokens present, target-size
tokens present. reduced_motion is tracked (see accessibility_tokens in
each results/tokens_*.json) but deliberately NOT scored -- it has no
WCAG 2.2 SC citation in this study's chosen criteria set (1.4.3, 1.4.11,
2.5.8), so per plan section 4.3 it stays a descriptive-only finding.
Layering formalization and naming consistency are also descriptive-only
and reported separately, not folded into this score.
"""
import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"

SCORED_CATEGORIES = ["contrast_safe_pairs", "focus_ring", "target_size"]


def score_phase(phase: dict) -> dict:
    dtcg_point = 1 if phase["dtcg_compliant"] == "yes" else 0
    access_points = {
        cat: (1 if phase["accessibility_tokens"][cat]["present"] else 0)
        for cat in SCORED_CATEGORIES
    }
    total = dtcg_point + sum(access_points.values())
    return {
        "dtcg_point": dtcg_point,
        "accessibility_points": access_points,
        "objective_subscore": total,
        "reduced_motion_present_not_scored": phase["accessibility_tokens"]["reduced_motion"]["present"],
        "layering_not_scored": phase["layering"],
    }


def main():
    summary = []
    for f in sorted(glob.glob(str(RESULTS_DIR / "tokens_*.json"))):
        d = json.loads(Path(f).read_text())
        before_score = score_phase(d["before"])
        after_score = score_phase(d["after"])
        entry = {
            "system": d["system"],
            "slug": d["slug"],
            "before_tag": d["before"]["tag"],
            "after_tag": d["after"]["tag"],
            "before": before_score,
            "after": after_score,
            "delta": after_score["objective_subscore"] - before_score["objective_subscore"],
        }
        summary.append(entry)
        print(
            f"{d['system']:30s} "
            f"before={before_score['objective_subscore']}/4  "
            f"after={after_score['objective_subscore']}/4  "
            f"delta={entry['delta']:+d}  "
            f"(layering {before_score['layering_not_scored']}->{after_score['layering_not_scored']})"
        )

    out_path = RESULTS_DIR / "objective_subscores.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
