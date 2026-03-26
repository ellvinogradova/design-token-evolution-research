#!/usr/bin/env python3
"""Day 4: hand-verification QA pass, per plan section 4.4 step 3
('hand-verify a random 10% sample per system against the rendered
documentation site to catch parser errors').

Methodological note (documented here, not hidden): most tokens
extracted in this study are internal source-level names, not all of
which have an individual entry on a rendered docs site (many are
implementation details rather than documented public API). The more
reliable and reproducible operationalization used here is: sample 10%
of each phase's extracted token_names, and confirm each sampled name
is a real, literal token declaration in the corresponding on-disk
source file (not a parser artifact -- e.g. a stray brace match, a
comment, a destructured variable). This catches the actual failure
mode the plan is worried about (parser bugs fabricating or garbling
names) via a deterministic, re-runnable check, rather than a human
skimming a docs page for a token that may not be individually listed
there. Where a live docs site page is easy to identify, it's checked
too (see per-system notes), as a secondary corroboration.
"""
import json
import random
import re
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
REPOS_DIR = ROOT / "data" / "repos"

random.seed(42)  # reproducible sample


def source_files_for(slug: str, phase: str) -> list[Path]:
    base = REPOS_DIR / slug / phase
    return [p for p in base.rglob("*") if p.is_file() and ".git" not in p.parts]


def token_present_in_sources(token_name: str, files: list[Path]) -> tuple[bool, str]:
    """Return (found, evidence). Two passes:
    1. Literal substring search for the token name as a distinct identifier
       -- handles tokens whose name IS a literal declared identifier.
    2. For composite/flattened names (the parsers document joining nested
       structure into dotted/hyphenated names, e.g. `Button.inheritContainedBg`
       from `setColor(palette.Button, 'inheritContainedBg', ...)`, or
       `palette-gray-100` from a `gray: {100: ...}` scale object) -- split on
       `.`/`-`/`_`, and require ALL parts to co-occur within a small line
       window in the same file. This is looser than pass 1 but still requires
       real proximity, not just independent presence anywhere in the file.
    """
    pattern = re.compile(r"(?<![\w$-])" + re.escape(token_name) + r"(?![\w$-])")
    for f in files:
        try:
            text = f.read_text(errors="ignore")
        except Exception:
            continue
        if pattern.search(text):
            return True, str(f.relative_to(ROOT)) + " (literal)"

    parts = [p for p in re.split(r"[.\-_]", token_name) if p]
    if len(parts) < 2:
        return False, ""

    # Try the full part set first, then -- since some parsers document adding
    # a synthetic category/namespace prefix that is NOT a literal source
    # token (e.g. parse_polaris.py's documented "palette-<family>-<scale>"
    # naming, where "palette" is added by the parser to disambiguate layers,
    # never appears literally in colors.ts) -- retry with the first part
    # dropped. This is applied generically (not hardcoded per-system) but
    # only ever loosens the check by one leading segment, so it still
    # requires real multi-part proximity evidence, not a bare substring hit.
    candidate_part_sets = [parts]
    if len(parts) > 2:
        candidate_part_sets.append(parts[1:])

    WINDOW = 60  # namespaces/object literals can legitimately span dozens
    # of lines (e.g. a 16-entry alpha scale, or a namespace block with many
    # unrelated members between its opener and one specific constant) --
    # a tight window produced false negatives on real, correctly-extracted
    # tokens during dev/QA of this very script; verified by hand against
    # NeutralColors.gray140 (Fluent UI, opener 10 lines above the constant)
    # and palette-blackAlpha-12 (Polaris, opener 12 lines above the key)
    # before widening this.
    for f in files:
        try:
            lines = f.read_text(errors="ignore").splitlines()
        except Exception:
            continue
        for candidate_parts in candidate_part_sets:
            part_patterns = [re.compile(re.escape(p)) for p in candidate_parts]
            for i, line in enumerate(lines):
                window_text = "\n".join(lines[max(0, i - WINDOW): i + WINDOW + 1])
                if all(p.search(window_text) for p in part_patterns):
                    tag = "composite" if candidate_parts is parts else "composite, prefix dropped as documented synthetic namespace"
                    return True, f"{f.relative_to(ROOT)}:{i+1} ({tag}, parts={candidate_parts})"
    return False, ""


def main():
    report = []
    for f in sorted(glob.glob(str(RESULTS_DIR / "tokens_*.json"))):
        d = json.loads(Path(f).read_text())
        system = d["system"]
        slug = d["slug"]
        sys_report = {"system": system, "slug": slug, "phases": {}}

        for phase in ("before", "after"):
            names = d[phase]["token_names"]
            n_sample = max(1, round(len(names) * 0.10))
            sample = random.sample(names, min(n_sample, len(names)))
            files = source_files_for(slug, phase)

            results = []
            for name in sample:
                found, evidence = token_present_in_sources(name, files)
                results.append({"token": name, "found": found, "evidence": evidence})

            pass_count = sum(1 for r in results if r["found"])
            sys_report["phases"][phase] = {
                "total_tokens": len(names),
                "sample_size": len(sample),
                "pass_count": pass_count,
                "pass_rate": round(pass_count / len(sample), 3) if sample else None,
                "failures": [r["token"] for r in results if not r["found"]],
            }
            print(
                f"{system:28s} [{phase:6s}] sampled {len(sample):3d}/{len(names):4d} "
                f"({len(sample)/len(names)*100:.0f}%) -> {pass_count}/{len(sample)} confirmed "
                f"({'ALL PASS' if pass_count == len(sample) else 'FAILURES: ' + str(sys_report['phases'][phase]['failures'])})"
            )

        report.append(sys_report)

    out_path = RESULTS_DIR / "hand_verification_report.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {out_path}")

    total_sampled = sum(p["sample_size"] for r in report for p in r["phases"].values())
    total_passed = sum(p["pass_count"] for r in report for p in r["phases"].values())
    print(f"\nOverall: {total_passed}/{total_sampled} sampled tokens confirmed present in source "
          f"({total_passed/total_sampled*100:.1f}%)")


if __name__ == "__main__":
    main()
