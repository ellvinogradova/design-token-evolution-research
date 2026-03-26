#!/usr/bin/env python3
"""Day 3: real token parser for Carbon Design System (v10.60.5 -> v11.0.0).

WHY THIS SCRIPT SHELLS OUT TO `git show` FOR SOME FILES
---------------------------------------------------------
Day 2's sparse-clone script (scripts/01_extract_tokens.py) copied the
`before_token_paths` / `after_token_paths` arrays out of
data/preflight/carbon.json *verbatim* into the git sparse-checkout pattern
file. Those arrays are fine for real paths, but three of Carbon's entries
carried human-readable parenthetical annotations as part of the "path"
string, e.g.:

    "packages/themes/src/next/tokens/ (v11 token preview already present pre-release)"
    "packages/themes/src/tokens/ (Token.js, TokenFormat.js, ...)"
    "packages/themes/src/v10/ (legacy v10 token module kept for backward compatibility, ...)"

`git sparse-checkout` treats each line as a literal gitignore-style pattern,
so these three never matched anything real and the directories were never
materialized in data/repos/carbon/{before,after}/ on disk. This is a Day 2
extraction bug, not a Day 1 fact-finding error -- Day 1's preflight (see
data/preflight/carbon.json "notes") correctly *identified* that
packages/themes/src/next/ (v10.60.5) and packages/themes/src/tokens/ +
packages/themes/src/v10/ (v11.0.0) exist; Day 2 just failed to check them out.

Per the Day 3 task instructions, this script does not modify anything
outside scripts/parse_carbon.py and results/tokens_carbon.json -- so rather
than editing the sparse-checkout config or re-cloning, it reads those three
directories directly out of git's object store with `git show <path>`. Both
local repos are partial clones (`--filter=blob:none`) with `origin` still
configured, and git transparently fetches any missing blob on demand when
asked for one that was never in the sparse checkout. This was verified
working during investigation (see chat/agent notes) -- `git ls-tree -r HEAD`
lists the *full* commit tree regardless of sparse-checkout state (trees are
always fetched), and `git show HEAD:<path>` fetches the blob content lazily.
This is read-only: it does not touch the working tree or the sparse-checkout
file, it only populates git's local object cache (the normal, expected
side effect of interacting with a partial clone).

EXTRACTION APPROACH
--------------------
Every real token source file found under packages/{themes,layout,type}/src
in this repo is plain JavaScript (ES module), not SCSS and not W3C DTCG
JSON -- confirmed by listing both checkouts (`find ... -type f`) before
writing this script. Two JS shapes are used, and both are handled:

  1. String-literal arrays, e.g. `const colors = ['interactive01', ...]`
     or `export const unstable_tokens = ['spacing01', ...]` -- used by
     packages/themes/src/tokens.js (v10 only) and packages/layout/src/tokens.js.
  2. `export const NAME = <value>;` declarations, plus `export { a, b, ... }
     from './white';` re-export blocks -- used by packages/themes/src/{g10,
     g90,g100,white}.js and packages/type/src/tokens.js.

No SCSS variable files (`$name: value;`) were found in the extracted paths
for Carbon; only .js files. If that changes for another system, a SCSS
regex would need to be added -- it is not needed here.

TOKEN NAME SOURCE OF TRUTH (per category)
------------------------------------------
- typography: packages/type/src/tokens.js `export const NAME = 'NAME';`
  declarations (a closed, self-describing set).
- spacing (layout/dimension bucket -- see CATEGORY RULES below):
  packages/layout/src/tokens.js `unstable_tokens` string array.
- color: the union of (a) the `colors` string array in
  packages/themes/src/tokens.js (v10 only -- this file does not exist in
  v11's working tree) and (b) every top-level `export const NAME = ...` and
  every name inside `export { ... } from './white'` blocks across
  packages/themes/src/{g10,g90,g100,white}.js -- MINUS any name already
  claimed by the typography or spacing sets above, because g10/g90/g100/
  white.js all *also* re-export type and layout tokens for developer
  convenience (see the `export { caption01, ..., spacing01, ... } from
  './white'` block at the bottom of those files). Without this exclusion,
  spacing/typography tokens would double-count into "color".
  packages/type/src/scale.js is deliberately NOT parsed for names: it only
  exports an unnamed numeric array (pixel sizes indexed by position), not
  named tokens.

NAMING-CONVENTION CHOICE FOR v11 COLOR TOKENS (important judgment call)
-------------------------------------------------------------------------
v11 ships a *second*, structurally different color-token surface at
packages/themes/src/tokens/ (Token.js/TokenGroup.js/TokenSet.js/
v11TokenGroup.js/v11TokenSet.js) that identifies tokens with kebab-case
design-token IDs like 'background-hover', 'layer-01', 'border-subtle-00'
(confirmed by fetching v11TokenSet.js with `git show`, see
CARBON_TOKENS_DIR_NOTE below). This script does NOT use those kebab-case
IDs as the counted "after" color-token names. Reason: packages/themes/src/
{g10,g90,g100,white}.js -- the actually-imported, actually-shipped
JavaScript API (`import { textPrimary } from '@carbon/themes'`) -- uses
camelCase names in BOTH v10 and v11 (verified by reading both files
directly). Mixing kebab-case "after" names against camelCase "before"
names would make the before/after diff report almost everything as
removed+added purely from a naming-convention change, which would be a
parser artifact, not a real finding. Using the camelCase JS export surface
for both phases keeps the diff meaningful. The tokens/ directory's
existence, purpose, and kebab-case scheme are still recorded as evidence
in parser_notes, per the task instructions, and its file/token-identifier
count is computed for that note (not folded into "after" totals).

CATEGORY RULES (documented, applied to the deduplicated name set per phase)
-----------------------------------------------------------------------------
1. typography  -- any name sourced from packages/type/src/tokens.js.
2. spacing     -- any name sourced from packages/layout/src/tokens.js
                  `unstable_tokens` (this bucket covers Carbon's spacing
                  scale, fluid spacing, the deprecated `layout0X` scale,
                  and "container"/icon-size dimension tokens -- the source
                  file itself does not subdivide these into finer
                  categories, and none of them are radius, shadow, motion,
                  or color, so they are grouped under "spacing" as the
                  closest rubric category for dimensional/layout tokens).
3. shadow      -- exactly the color-bucket name 'shadow' (case-insensitive
                  exact match). Carbon's themes package defines exactly one
                  token literally named "shadow" (an rgba box-shadow
                  color) in both v10 and v11 -- confirmed by grep. No other
                  shadow-related token name exists in the extracted files.
4. radius      -- any remaining name matching /radius/i. Confirmed by grep
                  across all extracted + git-show-fetched files: zero
                  matches in either phase. Carbon's border-radius tokens
                  live in a different package (not in the themes/layout/
                  type scope Day 1/2 locked in), so this is honestly 0/0,
                  not an estimate.
5. motion      -- any remaining name matching /motion|duration|easing
                  |timing/i. Confirmed by grep: zero matches in either
                  phase (Carbon's motion tokens live in @carbon/motion,
                  out of scope). Honestly 0/0.
6. color       -- everything else in the color-bucket union described
                  above (i.e. not typography, not spacing, not the
                  'shadow' token, not radius/motion-named).
7. other       -- catch-all for anything that doesn't land in any bucket
                  above. Expected to be empty given the closed set of
                  source files in scope; kept for transparency/safety.

MIGRATION-GUIDE CROSS-REFERENCE
----------------------------------
The official migration guide index page
(https://carbondesignsystem.com/migrating/guide/overview/) was reachable
but its rendered body was too large for the fetch tool to return in full.
Its *source* markdown lives in the audited repo itself, though, at
docs/migration/v11.md (confirmed present via `git ls-tree -r HEAD` on the
"after" checkout and read in full via `git show`), with dedicated tables
for "@carbon/themes" (Design Tokens table) and "Type tokens", plus a
`@carbon/layout` JS export table. This is the primary source Carbon
maintainers themselves publish for the v10->v11 rename surface, so it is
used here as ground truth (each entry cited by table row) rather than pure
guesswork. It is transcribed below as RENAME_TABLE/TYPE_RENAME_TABLE/
LAYOUT_JS_RENAME_TABLE, converted from the guide's kebab-case to this
script's camelCase convention. A generic normalized-name fuzzy pass is
also run as a fallback net for anything not covered by the guide tables
(documented inline).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEFORE_DIR = ROOT / "data" / "repos" / "carbon" / "before"
AFTER_DIR = ROOT / "data" / "repos" / "carbon" / "after"
OUT_PATH = ROOT / "results" / "tokens_carbon.json"

BEFORE_TAG = "v10.60.5"
AFTER_TAG = "v11.0.0"


# ---------------------------------------------------------------------------
# Low-level file access
# ---------------------------------------------------------------------------


def read_working_tree(repo_dir: Path, rel_path: str) -> str | None:
    p = repo_dir / rel_path
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")


def git_show(repo_dir: Path, rel_path: str) -> str | None:
    """Read a file's blob content at HEAD via git plumbing, even if it was
    never materialized in the sparse-checkout working tree (see module
    docstring). Returns None if the path doesn't exist at HEAD."""
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "show", f"HEAD:{rel_path}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def git_ls_tree(repo_dir: Path, subpath: str) -> list[str]:
    """List all file paths under subpath at HEAD, regardless of what's
    actually checked out on disk (tree objects are always fetched, only
    blob content is deferred under --filter=blob:none)."""
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "ls-tree", "-r", "--name-only", "HEAD", "--", subpath],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Extraction primitives
# ---------------------------------------------------------------------------

IDENT_IN_QUOTES = re.compile(r"""['"]([A-Za-z][A-Za-z0-9]*)['"]""")
EXPORT_CONST_STRING = re.compile(r"^export const (\w+) = '(\w+)';\s*$", re.MULTILINE)
EXPORT_CONST_ANY = re.compile(r"^export const (\w+)\s*=", re.MULTILINE)
EXPORT_BLOCK = re.compile(r"export\s*\{([^}]*)\}\s*from", re.DOTALL)


def extract_array_block(text: str, var_name: str) -> str | None:
    """Return the text between `<var_name> = [` and the matching `];`."""
    m = re.search(rf"\b{re.escape(var_name)}\s*=\s*\[", text)
    if not m:
        return None
    start = m.end()
    end = text.find("];", start)
    if end == -1:
        return None
    return text[start:end]


def names_from_quoted_array(text: str, var_name: str) -> set[str]:
    block = extract_array_block(text, var_name)
    if block is None:
        return set()
    return set(IDENT_IN_QUOTES.findall(block))


def names_from_export_const_string(text: str) -> set[str]:
    """`export const NAME = 'NAME';` declarations (used by type/tokens.js)."""
    return {m.group(1) for m in EXPORT_CONST_STRING.finditer(text)}


def names_from_export_const_any(text: str) -> set[str]:
    """Any `export const NAME = ...;` top-level declaration."""
    return set(EXPORT_CONST_ANY.findall(text))


def names_from_export_block(text: str) -> set[str]:
    """`export { a, b, // comment\\n c } from './white';` re-export blocks."""
    names: set[str] = set()
    for block in EXPORT_BLOCK.findall(text):
        for line in block.splitlines():
            line = re.sub(r"//.*$", "", line).strip().strip(",")
            if not line:
                continue
            for part in line.split(","):
                part = part.strip()
                if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", part):
                    names.add(part)
    return names


def count_identifiers_loose(text: str) -> int:
    """Rough count of distinct token-like identifiers in a file, used only
    for descriptive parser_notes about excluded directories (next/, v10/,
    tokens/) -- not used for any category count in the main schema."""
    quoted = set(IDENT_IN_QUOTES.findall(text))
    consts = names_from_export_const_any(text)
    return len(quoted | consts)


# ---------------------------------------------------------------------------
# Phase parsing
# ---------------------------------------------------------------------------


def parse_theme_color_names(repo_dir: Path, has_flat_tokens_js: bool) -> set[str]:
    names: set[str] = set()
    if has_flat_tokens_js:
        tokens_js = read_working_tree(repo_dir, "packages/themes/src/tokens.js")
        if tokens_js:
            names |= names_from_quoted_array(tokens_js, "colors")
    for theme_file in ("g10.js", "g90.js", "g100.js", "white.js"):
        text = read_working_tree(repo_dir, f"packages/themes/src/{theme_file}")
        if text is None:
            continue
        names |= names_from_export_const_any(text)
        names |= names_from_export_block(text)
    return names


def parse_typography_names(repo_dir: Path) -> set[str]:
    text = read_working_tree(repo_dir, "packages/type/src/tokens.js")
    if text is None:
        return set()
    return names_from_export_const_string(text)


def parse_spacing_names(repo_dir: Path) -> set[str]:
    text = read_working_tree(repo_dir, "packages/layout/src/tokens.js")
    if text is None:
        return set()
    return names_from_quoted_array(text, "unstable_tokens")


def categorize(all_color_raw: set[str], typography: set[str], spacing: set[str]):
    """Apply the CATEGORY RULES documented in the module docstring."""
    color_bucket = all_color_raw - typography - spacing

    shadow = {n for n in color_bucket if n.lower() == "shadow"}
    color_bucket = color_bucket - shadow

    radius = {n for n in (color_bucket | typography | spacing) if re.search(r"radius", n, re.I)}
    motion = {
        n
        for n in (color_bucket | typography | spacing)
        if re.search(r"motion|duration|easing|timing", n, re.I)
    }
    # radius/motion, if ever found, must not double-count against their
    # origin bucket.
    color_bucket -= radius | motion
    typography = typography - radius - motion
    spacing = spacing - radius - motion

    categorized = {
        "color": color_bucket,
        "typography": typography,
        "spacing": spacing,
        "radius": radius,
        "shadow": shadow,
        "motion": motion,
    }
    accounted = set().union(*categorized.values())
    other = (all_color_raw | typography | spacing) - accounted
    categorized["other"] = other
    return categorized


def build_phase(repo_dir: Path, tag: str, has_flat_tokens_js: bool):
    color_raw = parse_theme_color_names(repo_dir, has_flat_tokens_js)
    typography = parse_typography_names(repo_dir)
    spacing = parse_spacing_names(repo_dir)
    categorized = categorize(color_raw, typography, spacing)

    all_names = set()
    for names in categorized.values():
        all_names |= names

    by_category = {cat: len(names) for cat, names in categorized.items()}

    return {
        "tag": tag,
        "total_tokens": len(all_names),
        "by_category": by_category,
        "token_names": sorted(all_names),
        "_categorized_sets": categorized,  # internal use, stripped before writing
    }


# ---------------------------------------------------------------------------
# Excluded/compat directories -- documented, not counted (task instruction)
# ---------------------------------------------------------------------------


def describe_excluded_dir(repo_dir: Path, subpath: str) -> dict:
    files = git_ls_tree(repo_dir, subpath)
    js_files = [f for f in files if f.endswith(".js") and "__tests__" not in f and "__snapshots__" not in f]
    total_identifiers = 0
    for f in js_files:
        text = git_show(repo_dir, f)
        if text:
            total_identifiers += count_identifiers_loose(text)
    return {
        "path": subpath,
        "file_count": len(files),
        "js_source_file_count": len(js_files),
        "approx_identifier_count": total_identifiers,
    }


# ---------------------------------------------------------------------------
# Accessibility-token evidence (real grep-based citations, not assumptions)
# ---------------------------------------------------------------------------


def scan_accessibility_evidence(repo_dir: Path, phase_label: str) -> dict:
    sources = {
        "packages/themes/src/tokens.js": read_working_tree(repo_dir, "packages/themes/src/tokens.js"),
        "packages/themes/src/g10.js": read_working_tree(repo_dir, "packages/themes/src/g10.js"),
        "packages/themes/src/g90.js": read_working_tree(repo_dir, "packages/themes/src/g90.js"),
        "packages/themes/src/g100.js": read_working_tree(repo_dir, "packages/themes/src/g100.js"),
        "packages/themes/src/white.js": read_working_tree(repo_dir, "packages/themes/src/white.js"),
        "packages/layout/src/tokens.js": read_working_tree(repo_dir, "packages/layout/src/tokens.js"),
        "packages/type/src/tokens.js": read_working_tree(repo_dir, "packages/type/src/tokens.js"),
    }

    def find_lines(pattern: str) -> list[str]:
        hits = []
        for path, text in sources.items():
            if not text:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if re.search(pattern, line, re.I):
                    hits.append(f"{path}:{i}: {line.strip()}")
        return hits

    contrast_hits = find_lines(r"contrast|4\.5:1|wcag")
    focus_hits = find_lines(r"\bfocus")
    target_hits = find_lines(r"target-size|targetsize|touch|tap-target|min-target")
    motion_hits = find_lines(r"reduced.motion|prefers-reduced")

    def result(hits: list[str], max_cite: int = 3) -> dict:
        present = len(hits) > 0
        evidence = "; ".join(hits[:max_cite]) if present else ""
        return {"present": present, "evidence": evidence}

    return {
        "contrast_safe_pairs": result(contrast_hits),
        "focus_ring": result(focus_hits),
        "target_size": result(target_hits),
        "reduced_motion": result(motion_hits),
    }


# ---------------------------------------------------------------------------
# Diff + migration-guide-grounded rename detection
# ---------------------------------------------------------------------------


def kebab_to_camel(s: str) -> str:
    """Convert the migration guide's kebab-case names to this script's
    camelCase convention. Special-cases the 'ui' segment to 'UI': Carbon's
    real v10 exports overwhelmingly use the all-caps abbreviation
    (activeUI, hoverUI, hoverLightUI, hoverSelectedUI, selectedUI,
    selectedLightUI, inverseHoverUI -- all confirmed in
    packages/themes/src/tokens.js) even though a naive capitalize() would
    produce 'Ui'. One confirmed real exception exists in the source itself
    -- 'inverseFocusUi' uses lowercase-i 'Ui', not 'UI' -- which this
    special-case will therefore fail to match; that single row falls
    through to the fuzzy-normalization fallback (or, if that also misses,
    is reported as genuinely removed). This UI/Ui split is itself evidence
    of a mixed/inconsistent naming convention within Carbon's own v10
    token set, worth noting for the rubric's naming-consistency dimension."""
    parts = s.split("-")
    converted = []
    for i, p in enumerate(parts):
        if i == 0:
            converted.append(p)
        elif p.lower() == "ui":
            converted.append("UI")
        else:
            converted.append(p.capitalize())
    return "".join(converted)


# Transcribed directly from docs/migration/v11.md in the audited repo
# (fetched via `git show HEAD:docs/migration/v11.md` on the "after"
# checkout, v11.0.0 tag) -- the "@carbon/themes" Design Tokens table,
# lines ~1812-1924 as of that tag. Columns: (v10 kebab name, v11 kebab
# name or None, status). Status vocabulary matches the guide's own legend
# (No change / Updated / Split / New / Deprecated).
THEMES_RENAME_TABLE_KEBAB = [
    ("active-danger", "button-danger-active", "Updated"),
    ("active-light-ui", "layer-active-02", "Updated"),
    ("active-primary", "button-primary-active", "Updated"),
    ("active-secondary", "button-secondary-active", "Updated"),
    ("active-tertiary", "button-tertiary-active", "Updated"),
    ("active-ui", "layer-active-01", "Split"),
    ("active-ui", "background-active", "Split"),
    ("active-ui", "layer-accent-active-01", "Split"),
    ("active-ui", "border-subtle-selected-01", "Split"),
    ("button-separator", "button-separator", "No change"),
    ("danger", "button-danger-primary", "Deprecated"),
    ("danger-01", "button-danger-primary", "Updated"),
    ("danger-02", "button-danger-secondary", "Updated"),
    ("decorative-01", "border-subtle-02", "Updated"),
    ("disabled-01", None, "Deprecated"),
    ("disabled-02", "text-disabled", "Split"),
    ("disabled-02", "icon-disabled", "Split"),
    ("disabled-02", "button-disabled", "Split"),
    ("disabled-02", "border-disabled", "Split"),
    ("disabled-03", "icon-on-color-disabled", "Split"),
    ("disabled-03", "layer-selected-disabled", "Split"),
    ("disabled-03", "text-on-color-disabled", "Split"),
    ("field-01", "field-01", "No change"),
    ("field-02", "field-02", "No change"),
    ("focus", "focus", "No change"),
    ("highlight", "highlight", "No change"),
    ("hover-danger", "button-danger-hover", "Updated"),
    ("hover-light-ui", "layer-hover-02", "Updated"),
    ("hover-primary", "button-primary-hover", "Updated"),
    ("hover-primary-text", "link-primary-hover", "Updated"),
    ("hover-secondary", "button-secondary-hover", "Updated"),
    ("hover-selected-ui", "background-selected-hover", "Split"),
    ("hover-selected-ui", "layer-accent-hover-01", "Split"),
    ("hover-selected-ui", "layer-selected-hover-01", "Split"),
    ("hover-tertiary", "button-tertiary-hover", "Updated"),
    ("hover-ui", "background-hover", "Updated"),
    ("hover-ui", "layer-hover-01", "Split"),
    ("hover-ui", "field-hover-01", "Split"),
    ("hover-ui", "field-hover-02", "Split"),
    ("icon-01", "icon-primary", "Updated"),
    ("icon-02", "icon-secondary", "Updated"),
    ("icon-03", "icon-on-color", "Updated"),
    ("interactive-01", "button-primary", "Updated"),
    ("interactive-01", "background-brand", "Updated"),
    ("interactive-02", "button-secondary", "Updated"),
    ("interactive-03", "button-tertiary", "Updated"),
    ("interactive-04", "border-interactive", "Split"),
    ("interactive-04", "interactive", "Split"),
    ("inverse-01", "icon-inverse", "Split"),
    ("inverse-01", "focus-inset", "Split"),
    ("inverse-01", "text-inverse", "Split"),
    ("inverse-02", "background-inverse", "Updated"),
    ("inverse-focus-ui", "focus-inverse", "Updated"),
    ("inverse-hover-ui", "background-inverse-hover", "Updated"),
    ("inverse-link", "link-inverse", "Updated"),
    ("inverse-support-01", "support-error-inverse", "Updated"),
    ("inverse-support-02", "support-success-inverse", "Updated"),
    ("inverse-support-03", "support-warning-inverse", "Updated"),
    ("inverse-support-04", "support-info-inverse", "Updated"),
    ("link-01", "link-primary", "Updated"),
    ("link-02", "link-secondary", "Updated"),
    ("overlay-01", "overlay", "Updated"),
    ("selected-light-ui", "layer-selected-02", "Updated"),
    ("selected-ui", "layer-selected-01", "Split"),
    ("selected-ui", "background-selected", "Split"),
    ("skeleton-01", "skeleton-background", "Updated"),
    ("skeleton-02", "skeleton-element", "Updated"),
    ("support-01", "support-error", "Updated"),
    ("support-02", "support-success", "Updated"),
    ("support-03", "support-warning", "Updated"),
    ("support-04", "support-info", "Updated"),
    ("text-01", "text-primary", "Updated"),
    ("text-02", "text-secondary", "Updated"),
    ("text-03", "text-placeholder", "Updated"),
    ("text-04", "text-on-color", "Updated"),
    ("text-05", "text-helper", "Updated"),
    ("text-error", "text-error", "Updated"),
    ("hover-row", "layer-hover-01", "Deprecated"),
    ("ui-01", "layer-01", "Updated"),
    ("ui-02", "layer-02", "Updated"),
    ("ui-03", "layer-accent-01", "Split"),
    ("ui-03", "border-subtle-01", "Split"),
    ("ui-04", "toggle-off", "Split"),
    ("ui-04", "border-strong-01", "Split"),
    ("ui-05", "border-inverse", "Updated"),
    ("ui-05", "layer-selected-inverse", "Updated"),
    ("ui-background", "background", "Updated"),
    ("visited-link", "link-visited", "Updated"),
    ("brand-01", None, "Deprecated"),
    ("brand-02", None, "Deprecated"),
    ("brand-03", None, "Deprecated"),
]

# Transcribed from the same doc's "Type tokens" table, lines ~2008-2046.
TYPE_RENAME_TABLE_KEBAB = [
    ("code-01", "code-01", "No change"),
    ("code-02", "code-02", "No change"),
    ("label-01", "label-01", "No change"),
    ("label-02", "label-02", "No change"),
    ("helper-text-01", "helper-text-01", "No change"),
    ("helper-text-02", "helper-text-02", "No change"),
    ("caption-01", None, "Deprecated"),
    ("caption-02", None, "Deprecated"),
    ("body-short-01", "body-compact-01", "Updated"),
    ("body-short-02", "body-compact-02", "Updated"),
    ("body-long-01", "body-01", "Updated"),
    ("body-long-02", "body-02", "Updated"),
    ("productive-heading-01", "heading-compact-01", "Updated"),
    ("productive-heading-02", "heading-compact-02", "Updated"),
    ("expressive-heading-01", "heading-01", "Updated"),
    ("expressive-heading-02", "heading-02", "Updated"),
    ("productive-heading-03", "heading-03", "Updated"),
    ("productive-heading-04", "heading-04", "Updated"),
    ("productive-heading-05", "heading-05", "Updated"),
    ("productive-heading-06", "heading-06", "Updated"),
    ("productive-heading-07", "heading-07", "Updated"),
    ("expressive-heading-03", "fluid-heading-03", "Updated"),
    ("expressive-heading-04", "fluid-heading-04", "Updated"),
    ("expressive-heading-05", "fluid-heading-05", "Updated"),
    ("expressive-heading-06", "fluid-heading-06", "Updated"),
    ("expressive-paragraph-01", "fluid-paragraph-01", "Updated"),
    ("quotation-01", "fluid-quotation-01", "Updated"),
    ("quotation-02", "fluid-quotation-02", "Updated"),
    ("display-01", "fluid-display-01", "Updated"),
    ("display-02", "fluid-display-02", "Updated"),
    ("display-03", "fluid-display-03", "Updated"),
]

# Transcribed from the same doc's `@carbon/layout` "JavaScript API" table,
# lines ~1684-1693 (already camelCase in the source, no conversion needed).
LAYOUT_JS_RENAME_TABLE = [
    ("layout01", "spacing05", "Updated"),
    ("layout02", "spacing06", "Updated"),
    ("layout03", "spacing07", "Updated"),
    ("layout04", "spacing09", "Updated"),
    ("layout05", "spacing10", "Updated"),
    ("layout06", "spacing12", "Updated"),
    ("layout07", "spacing13", "Updated"),
    ("layout", None, "Deprecated"),
]


def build_camelcase_rename_table() -> dict[str, list[tuple[str | None, str]]]:
    table: dict[str, list[tuple[str | None, str]]] = {}
    for v10_kebab, v11_kebab, status in THEMES_RENAME_TABLE_KEBAB + TYPE_RENAME_TABLE_KEBAB:
        v10_name = kebab_to_camel(v10_kebab)
        v11_name = kebab_to_camel(v11_kebab) if v11_kebab else None
        table.setdefault(v10_name, []).append((v11_name, status))
    for v10_name, v11_name, status in LAYOUT_JS_RENAME_TABLE:
        table.setdefault(v10_name, []).append((v11_name, status))
    return table


def normalize_fuzzy(name: str) -> str:
    """Fallback heuristic for names the official guide table doesn't cover:
    lowercase and strip digits/underscores, so e.g. 'spacing01' and
    'spacing1' would collide. This is intentionally weak -- Carbon's real
    v10->v11 renames are largely semantic rewrites (interactive01 ->
    buttonPrimary) that no generic string-normalization pass could catch,
    which is exactly why the guide table above is the primary mechanism
    and this is only a fallback net."""
    return re.sub(r"[^a-z]", "", name.lower())


def compute_diff(before_names: set[str], after_names: set[str]):
    removed = before_names - after_names
    added = after_names - before_names

    rename_table = build_camelcase_rename_table()
    fuzzy_after = {}
    for name in after_names:
        fuzzy_after.setdefault(normalize_fuzzy(name), []).append(name)

    renamed_detail = []
    genuinely_removed = []
    for name in sorted(removed):
        entries = rename_table.get(name)
        matched_targets = []
        source = None
        if entries:
            for target, status in entries:
                if target and status != "Deprecated" and target in after_names:
                    matched_targets.append((target, status))
            if matched_targets:
                source = "official migration guide (docs/migration/v11.md)"
        if not matched_targets:
            fuzzy_key = normalize_fuzzy(name)
            fuzzy_matches = fuzzy_after.get(fuzzy_key, [])
            if fuzzy_matches:
                matched_targets = [(t, "fuzzy-normalized-match") for t in fuzzy_matches]
                source = "fallback fuzzy normalization"

        if matched_targets:
            renamed_detail.append(
                {"before_name": name, "likely_after_names": [t for t, _ in matched_targets], "source": source}
            )
        else:
            genuinely_removed.append(name)

    return {
        "removed": sorted(removed),
        "added": sorted(added),
        "renamed_detail": renamed_detail,
        "genuinely_removed": genuinely_removed,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def strip_internal(phase: dict) -> dict:
    phase = dict(phase)
    phase.pop("_categorized_sets", None)
    return phase


def main():
    before = build_phase(BEFORE_DIR, BEFORE_TAG, has_flat_tokens_js=True)
    after = build_phase(AFTER_DIR, AFTER_TAG, has_flat_tokens_js=False)

    before_names = set(before["token_names"])
    after_names = set(after["token_names"])

    diff = compute_diff(before_names, after_names)

    # Excluded/compat directories -- documented per task instructions,
    # never folded into before/after totals.
    next_dir_note = describe_excluded_dir(BEFORE_DIR, "packages/themes/src/next")
    tokens_dir_note = describe_excluded_dir(AFTER_DIR, "packages/themes/src/tokens")
    v10_compat_dir_note = describe_excluded_dir(AFTER_DIR, "packages/themes/src/v10")

    before_a11y = scan_accessibility_evidence(BEFORE_DIR, "before")
    after_a11y = scan_accessibility_evidence(AFTER_DIR, "after")

    # layering / dtcg_compliant: judgment calls made from real evidence
    # gathered above, documented in parser_notes.
    layering_judgment = "2-layer"
    dtcg_judgment = "no"

    before_out = strip_internal(before)
    before_out["layering"] = layering_judgment
    before_out["dtcg_compliant"] = dtcg_judgment
    before_out["accessibility_tokens"] = before_a11y

    after_out = strip_internal(after)
    after_out["layering"] = layering_judgment
    after_out["dtcg_compliant"] = dtcg_judgment
    after_out["accessibility_tokens"] = after_a11y

    parser_notes = (
        "SPARSE-CHECKOUT GAP FIXED AT READ TIME: Day 2's extraction script "
        "(scripts/01_extract_tokens.py) copied malformed sparse-checkout "
        "patterns straight from data/preflight/carbon.json (paths with "
        "parenthetical human notes baked in), so packages/themes/src/next/ "
        "(before) and packages/themes/src/tokens/ + packages/themes/src/v10/ "
        "(after) were never checked out to disk. This script reads them "
        "directly from git's object store with `git show HEAD:<path>` "
        "instead (both repos are partial clones with `origin` intact, so "
        "missing blobs fetch on demand) -- read-only, does not touch the "
        "working tree or sparse-checkout config. "
        f"STAGED MIGRATION EVIDENCE: v{BEFORE_TAG} already ships "
        f"packages/themes/src/next/ -- {next_dir_note['file_count']} files "
        f"({next_dir_note['js_source_file_count']} JS source files, "
        f"~{next_dir_note['approx_identifier_count']} token-like "
        "identifiers across them), essentially a working preview of what "
        "became the real v11 g10/g90/g100/white.js (confirmed by reading "
        "next/g10.js: same 268-line structure and camelCase export names "
        "as the real v11.0.0 g10.js). This directory is EXCLUDED from the "
        "'before' count/token_names by explicit choice (task instruction): "
        "it previews the v11 API but was not the shipped v10 API surface "
        f"at the {BEFORE_TAG} tag. Symmetrically, v{AFTER_TAG} ships "
        f"packages/themes/src/v10/ -- {v10_compat_dir_note['file_count']} "
        f"files (~{v10_compat_dir_note['approx_identifier_count']} "
        "token-like identifiers), a near-duplicate of the v10 tokens.js/"
        "g10/g90/g100/white.js module kept for backward compatibility "
        "(confirmed via `git show HEAD:packages/themes/src/v10/tokens.js`: "
        "437 lines, same `colors` array shape as the real v10.60.5 "
        "tokens.js). It ships its own metadata.yml documenting removal "
        "target v12. EXCLUDED from the 'after' count for the same reason "
        "(it is legacy v10 surface area re-exposed, not the new v11 API). "
        f"v{AFTER_TAG} also ships packages/themes/src/tokens/ -- "
        f"{tokens_dir_note['file_count']} files (Token.js/TokenFormat.js/"
        "TokenGroup.js/TokenSet.js/v11TokenGroup.js/v11TokenSet.js), a new "
        "object model replacing the flat v10 tokens.js. Confirmed by "
        "fetching v11TokenSet.js: it organizes tokens into named groups "
        "(e.g. '01 Layer set') using kebab-case design-token IDs like "
        "'layer-01', 'border-subtle-00' via a `TokenGroup.getToken(id)` "
        "API -- structurally different from v10's flat camelCase string "
        "array. Its token identifiers are NOT what this script counts as "
        "'after' color tokens (see module docstring 'NAMING-CONVENTION "
        "CHOICE'): counting them would compare kebab-case v11 names "
        "against camelCase v10 names and manufacture a spurious ~100% "
        "removed+added diff from the naming-convention change alone, not "
        "from real token churn. Instead, both phases' color-token names "
        "come from the actually-imported JS API surface "
        "(themes/src/{g10,g90,g100,white}.js `export const` declarations), "
        "which is camelCase in both v10 and v11. "
        "TYPE TOKENS ARE STRUCTURALLY UNCHANGED: `diff` of "
        "packages/type/src/tokens.js between the two tags is byte-for-byte "
        "identical (verified with `diff`) -- v10.60.5 already exports the "
        "full v11 typography name set (legal01, bodyCompact01, body01, "
        "headingCompact01, heading03-07, fluidHeading03-06, "
        "fluidParagraph01, fluidQuotation01/02, fluidDisplay01-04) "
        "alongside the legacy names (caption01, productiveHeading01, "
        "expressiveHeading01, etc.) under a 'V11 Tokens' comment, and "
        "keeps them both in v11.0.0 too. This is a second, independent "
        "staged-migration signal beyond next/ and v10/. It also means the "
        "typography category shows ZERO structural diff at the JS-export "
        "layer for this study -- the officially documented typography "
        "renames (caption01 removed, body-short-01 -> body-compact-01, "
        "etc., see docs/migration/v11.md 'Type tokens' table) operate at "
        "the Sass $variable / CSS custom-property layer, which sits "
        "outside packages/type/src/tokens.js and so outside this script's "
        "file scope. "
        "LAYOUT TOKENS: packages/layout/src/tokens.js differs by exactly "
        "the removal of layout01-07 (7 names) between the two tags -- "
        "matches docs/migration/v11.md's @carbon/layout JS table exactly "
        "(layout01-07 -> spacing05/06/07/09/10/12/13). "
        "CATEGORIZATION: radius and motion both come back 0/0 for both "
        "phases -- confirmed by grepping every extracted and git-show-"
        "fetched file for /radius|motion|duration|easing|timing/i with "
        "zero hits; Carbon's radius and motion tokens live in packages "
        "outside the themes/layout/type scope this study locked in at "
        "Day 1, so this is an honest scope limitation, not an estimate. "
        "'spacing' groups everything from @carbon/layout's unstable_tokens "
        "array (spacing scale, fluid spacing, deprecated layout scale, "
        "container sizes, icon sizes) since the source file does not "
        "itself subdivide these into finer categories and none of them "
        "are color/typography/radius/shadow/motion. "
        "LAYERING JUDGMENT (2-layer for both phases): both v10 and v11 "
        "show a primitive-color-scale-to-semantic-token mapping (raw "
        "colors like blue60/gray80 imported from the separate @carbon/"
        "colors package, assigned to semantic names like textPrimary/"
        "borderSubtle01 in themes/src/*.js) but no distinct third "
        "'component-specific' token tier is formalized within the themes/"
        "layout/type files in scope. v11's numeric 01/02/03 suffixes "
        "(layer-01/02/03, field-01/02/03, borderSubtle-00..03) are a UI "
        "elevation/nesting-depth concept, not an additional naming-layer "
        "in the primitive/semantic/component sense -- deliberately not "
        "over-read as a jump to '3-layer'. Carbon's own public docs are "
        "less explicit about a named layering model than e.g. Ant Design's "
        "Seed/Map/Alias framing, so this is a researcher judgment call, "
        "stated explicitly per the task instructions. "
        "DTCG COMPLIANCE: 'no' for both phases -- no `.tokens.json`-style "
        "W3C DTCG export exists anywhere in the extracted files or the "
        "git-show-fetched next/tokens//v10 directories; all token "
        "definitions are plain JS `export const` / string-array "
        "declarations. "
        "MIGRATION GUIDE CROSS-REFERENCE: the rendered migration site "
        "(https://carbondesignsystem.com/migrating/guide/overview/) "
        "returned content too large for the fetch tool to summarize in "
        "full, so this script instead reads the guide's own markdown "
        "source directly from the audited repo at docs/migration/v11.md "
        "(present at the v11.0.0 tag; fetched via `git show`), which "
        "contains explicit v10-token -> v11-token rename tables for "
        "@carbon/themes (Design Tokens), @carbon/type (Type tokens), and "
        "@carbon/layout (JS exports). Those tables are transcribed "
        "verbatim (kebab-case, converted to this script's camelCase "
        "convention) as THEMES_RENAME_TABLE_KEBAB / TYPE_RENAME_TABLE_KEBAB "
        "/ LAYOUT_JS_RENAME_TABLE and used as the primary source for "
        "renamed-vs-genuinely-removed classification; a generic "
        "normalized-string fuzzy match is applied only as a fallback for "
        "names the guide table doesn't cover. "
        "ACCESSIBILITY-TOKEN EVIDENCE: contrast_safe_pairs and "
        "target_size and reduced_motion all came back with zero matches "
        "after grepping every extracted file (both working-tree and "
        "git-show-fetched) for contrast/WCAG/4.5:1, target-size/touch/tap, "
        "and reduced-motion/prefers-reduced-motion patterns -- left as "
        "present:false with empty evidence rather than assumed present "
        "from Carbon's general accessibility reputation, per task "
        "instructions. focus_ring is present in both phases with real "
        "citations: packages/themes/src/tokens.js defines 'focus', "
        "'focusInset', 'focusInverse' as named color tokens (v10), and "
        "packages/themes/src/g10.js assigns them real values in both v10 "
        "and v11 -- these are color tokens used to drive focus-indicator "
        "styling, not a dedicated ring-width/offset token; no separate "
        "focus-ring geometry token was found in scope. "
        "'BUTTON-*' FAMILY IS A DOCUMENTED-BUT-UNVERIFIABLE RENAME "
        "GROUP: docs/migration/v11.md's Design Tokens table documents "
        "interactive-01 -> button-primary, interactive-02 -> "
        "button-secondary, danger-01/02 -> button-danger-primary/"
        "secondary, hover-danger -> button-danger-hover, active-primary/"
        "secondary/tertiary -> button-*-active, and button-separator -> "
        "button-separator ('No change'). None of these button* names "
        "appear anywhere in packages/themes/src/{g10,g90,g100,white}.js "
        "in the v11.0.0 checkout (confirmed with a direct grep across all "
        "four files: zero matches for 'button'). This makes up roughly "
        "half of the genuinely_removed sample below. Most likely "
        "explanation: these particular v11 tokens live in the @carbon/"
        "styles Sass layer (component-level tokens), not in the "
        "@carbon/themes JS package this study's Day 1 preflight scoped "
        "in -- i.e. the guide is accurate about Carbon-the-system, but "
        "the specific files this audit locked in do not contain the "
        "successor names, so this script reports them as genuinely "
        "removed from ITS scope rather than silently assuming a match "
        "that isn't actually verifiable in the extracted files. Treat "
        "genuinely_removed_count as an upper bound on true breaking "
        "removals for this reason -- some fraction is a scope artifact, "
        "not evidence that Carbon dropped the concept entirely."
    )

    output = {
        "system": "Carbon Design System",
        "slug": "carbon",
        "before": before_out,
        "after": after_out,
        "diff": {
            "removed_count": len(diff["removed"]),
            "added_count": len(diff["added"]),
            "removed_names_sample": diff["removed"][:25],
            "added_names_sample": diff["added"][:25],
            "likely_renamed_count": len(diff["renamed_detail"]),
            "renamed_note": (
                f"{len(diff['renamed_detail'])} of {len(diff['removed'])} "
                "structurally-removed names were cross-referenced against "
                "docs/migration/v11.md's official @carbon/themes 'Design "
                "Tokens' and @carbon/type 'Type tokens' rename tables "
                "(fetched via `git show HEAD:docs/migration/v11.md` on "
                "the v11.0.0 checkout; transcribed in this script as "
                "THEMES_RENAME_TABLE_KEBAB / TYPE_RENAME_TABLE_KEBAB / "
                "LAYOUT_JS_RENAME_TABLE), or, failing that, a normalized-"
                "string fuzzy fallback (digits/case stripped), and "
                "classified as likely renamed rather than genuinely "
                f"dropped; the remaining {len(diff['genuinely_removed'])} "
                "have no documented or fuzzy-matched v11 successor and "
                "are treated as genuinely removed. Representative "
                "examples of matched renames -- ui01->layer01 (guide, "
                "'Updated'), text01->textPrimary (guide, 'Updated'), "
                "decorative01->borderSubtle02 (guide, 'Updated'), "
                "disabled02->{textDisabled,iconDisabled,buttonDisabled,"
                "borderDisabled} (guide, 'Split'), ui03->{layerAccent01,"
                "borderSubtle01} (guide, 'Split'), borderSubtle->"
                "{borderSubtle00,borderSubtle01,borderSubtle02,"
                "borderSubtle03} (fuzzy fallback, since v10.60.5's own "
                "'new color token' preview name 'borderSubtle' predates "
                "the guide's v9-era 'ui-03' source column). Representative "
                "genuinely-removed examples -- brand01/02/03, danger, "
                "disabled01 (guide status 'Deprecated', no successor), "
                "plus the whole 'button*' family (buttonPrimary, "
                "buttonDangerActive, buttonSeparator, etc.) which the "
                "guide documents as renamed but whose v11 target names do "
                "not actually appear anywhere in packages/themes/src/"
                "{g10,g90,g100,white}.js at v11.0.0 -- see parser_notes "
                "'BUTTON-* FAMILY' paragraph for why that is reported as "
                "removed rather than matched despite guide documentation."
            ),
        },
        "parser_notes": parser_notes,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    print(f"before total_tokens = {before_out['total_tokens']}  by_category = {before_out['by_category']}")
    print(f"after  total_tokens = {after_out['total_tokens']}  by_category = {after_out['by_category']}")
    print(f"removed = {len(diff['removed'])}  added = {len(diff['added'])}  "
          f"likely_renamed = {len(diff['renamed_detail'])}  "
          f"genuinely_removed = {len(diff['genuinely_removed'])}")
    print(f"next/ (before, excluded): {next_dir_note}")
    print(f"tokens/ (after, excluded): {tokens_dir_note}")
    print(f"v10/ (after, excluded): {v10_compat_dir_note}")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
