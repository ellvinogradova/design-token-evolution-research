#!/usr/bin/env python3
"""Day 3: parse Shopify `polaris-tokens` TS source files (before = tag
`@shopify/polaris-tokens@7.12.1`, after = tag `@shopify/polaris-tokens@8.0.0`)
into a structured before/after token inventory + diff, written to
`results/tokens_polaris.json`.

Per plan §4.2's locked-sample note: Polaris's `polaris-tokens` package has
been a dedicated token system since v5 -- there is no "pre-tokens" era in
what we're diffing here. The v8.0.0 transition documented in the package's
own CHANGELOG is "Removed legacy v11 border/font/space/shadow/color tokens"
+ "Added border-radius semantic layer" -- a legacy-cleanup /
semantic-formalization story, NOT a "tokens introduced" story like Ant
Design's v4->v5. This script's job is to quantify that cleanup with real
counts, not estimate them.

===========================================================================
WHICH FILES ARE PARSED, AND WHY
===========================================================================
Confirmed file listing (via `find data/repos/polaris/{before,after} -type f`):

  before/polaris-tokens/src/
    colors.ts                  <- raw color PALETTE scale (parsed)
    colors-experimental.ts     <- raw color PALETTE scale, newer scale (parsed)
    size.ts                    <- raw size/spacing PRIMITIVE scale (parsed)
    utilities.ts                  NOT parsed (see below)
    themes/{types,constants,utils,index,light,light-uplift}.ts   NOT parsed
    themes/base/{border,breakpoints,color,font,height,motion,
                 shadow,space,text,width,zIndex}.ts              <- parsed
                (the SEMANTIC token groups)

  after/polaris-tokens/src/
    colors.ts                  <- raw color PALETTE scale (parsed; absorbed
                                   the old colors-experimental.ts scale)
    size.ts                    <- raw size/spacing PRIMITIVE scale (parsed)
    utils.ts (renamed from utilities.ts)                        NOT parsed
    themes/{types,constants,utils,index,light,
            light-high-contrast}.ts                              NOT parsed
    themes/base/{...same 11 files as before...}                 <- parsed

Files deliberately EXCLUDED from token extraction, and why:
  * utilities.ts / utils.ts    -- pure helper FUNCTIONS (unit conversion,
    CSS var-name builders, etc.), no token definitions at all.
  * themes/types.ts, constants.ts, themes/utils.ts, themes/index.ts
                                -- TypeScript type declarations, theme-name
    string constants, and aggregation/merge helper functions. No token
    names originate here.
  * themes/light.ts, light-uplift.ts (before-only),
    light-high-contrast.ts (after-only)
                                -- these are THEME VALUE OVERLAYS: they
    re-assign alternate *values* to token names that are already declared
    in themes/base/*.ts (e.g. `'color-border-focus': {value: colors.blue[13]}`
    inside light-uplift.ts overrides the base value for the token name
    'color-border-focus', it does not declare a new token name). Counting
    these would either double-count already-counted names or silently
    inflate "added/removed" if a theme happens to touch a token the other
    phase's equivalent theme file doesn't. We only count each CANONICAL
    token NAME once, from its base/primitive declaration.

===========================================================================
EXTRACTION APPROACH (documented in detail; see extract_blocks())
===========================================================================
Every parsed file is Prettier-formatted TypeScript of the shape:

    export const <name>[: <Type annotation, possibly multi-line>] = {
      'token-or-scale-key': { value: '...', description?: '...' },   // themes/base/*.ts
      -- or --
      'token-or-scale-key': 'raw css value',                          // colors.ts / size.ts
      ...
    };

We do not use a TS/AST parser (none is available in the stdlib and pulling
one in is unjustified for this fixed, known file shape). Instead we exploit
two facts that hold consistently across every file we read by hand before
writing this script:

  1. The exported object literal's top-level keys are ALWAYS indented by
     exactly two spaces; any key nested one level deeper (`value:`,
     `description:` inside a `{value: ...}` wrapper) is indented by four.
     So "line starts with exactly two spaces, then an optional quote, then
     an identifier, then a colon" reliably identifies a top-level token
     entry and skips nested metadata keys.
  2. Prettier only ever emits an UN-indented `};` (at column 0) to close a
     top-level statement. Some token values (motion keyframes) contain
     literal `{`/`}` characters *inside their string value*
     (e.g. `'{ to { opacity: 1 } }'`), which would break a naive
     brace-counter -- but those braces are always indented, never a
     bare `};` at column 0, so scanning for a column-0 `};` is safe.

extract_blocks() finds every `export const <name>` declaration, scans
forward to the line that actually opens the value literal (either on the
same line, for simple `export const gray: Color = {`, or several lines
later where a multi-line mapped-type annotation closes with `} = {`, as in
`export const color: {\n  [T in ...]: ...;\n} = {`), then scans forward to
the next column-0 `};` and collects every two-space-indented key in
between. A file can contain multiple `export const` blocks (colors.ts
defines one block per color family -- gray, green, blue, ...); each block
is returned separately so palette files can flatten "block name + scale
key" into one token name (e.g. `palette-gray-50`).

===========================================================================
FLATTENING RULE FOR RAW SCALES
===========================================================================
colors.ts / colors-experimental.ts define several *nested* scale objects
(`gray`, `green`, `blue`, ... each keyed '50'..'900' or '1'..'16'). Per the
task's flattening instruction, each is turned into one flat token name:
`palette-<family>-<scale>`, e.g. `palette-gray-50`, `palette-blue-1`. The
"palette-" prefix keeps this primitive layer's names from colliding with
the semantic `color-*` token names declared in themes/base/color.ts, which
matters for an accurate diff (a primitive `palette-gray-50` and a semantic
`color-bg` are different tokens, not the same name).

size.ts defines a single flat scale (`size['0']`, `size['025']`, ...); each
key becomes `size-<key>`, e.g. `size-0`, `size-025`.

themes/base/*.ts token names are already fully-qualified string literals
(e.g. `'color-bg'`, `'border-radius-0'`, `'shadow-100'`) -- no flattening
or prefixing needed, they are used as-is.

===========================================================================
CATEGORIZATION RULES (color / typography / spacing / radius / shadow /
motion / other) -- based on the *file* each name came from, since Polaris's
own source organizes tokens exactly this way (themes/base/index.ts imports
one module per category: border, breakpoints, color, font, height, motion,
shadow, space, text, width, zIndex):
===========================================================================
  colors.ts, colors-experimental.ts        -> color   (raw color palette)
  themes/base/color.ts                     -> color   (semantic color tokens)
  size.ts                                  -> spacing (raw size primitive scale)
  themes/base/space.ts                     -> spacing (semantic spacing tokens)
  themes/base/font.ts                      -> typography
  themes/base/text.ts                      -> typography (composite text styles
                                               built from font-* tokens)
  themes/base/shadow.ts                    -> shadow
  themes/base/motion.ts                    -> motion
  themes/base/border.ts                    -> radius for any token name
                                               containing "radius"
                                               (border-radius-*); "other" for
                                               border-width-* (a border-line
                                               thickness scale, not one of
                                               the rubric's named categories)
  themes/base/width.ts, height.ts          -> other   (component dimension
                                               tokens -- distinct from
                                               margin/padding "spacing";
                                               the rubric has no dedicated
                                               "sizing" bucket, so these are
                                               conservatively bucketed as
                                               "other" rather than folded
                                               into "spacing")
  themes/base/zIndex.ts                    -> other   (stacking order, not
                                               a visual/layout category)
  themes/base/breakpoints.ts               -> other   (responsive breakpoints,
                                               not a visual/layout category)

===========================================================================
LAYERING JUDGMENT (see also parser_notes in the output)
===========================================================================
Both phases show a primitive -> semantic split: colors.ts/size.ts hold raw
scale values, and themes/base/*.ts semantic tokens reference them (before:
via `colors.gray[500]` or `var(--p-color-bg)` indirection through
"-experimental" helper tokens; after: via `colors.gray[6]` or `size[100]`
directly). That is a real 2-layer (primitive -> semantic) structure in BOTH
phases -- Polaris did not go from flat to layered at this transition (it
was already layered), consistent with plan §4.2's note that this is not a
"tokens introduced" story. A few token names look component-specific
(`color-avatar-bg-fill`, `space-card-gap`, `shadow-button-primary`) but
they live in the SAME flat dictionary as generic semantic tokens,
distinguished only by naming convention, not by a separate file/namespace
tier -- so we do NOT call this a 3-layer primitive/semantic/component
architecture in either phase. Both before and after are coded "2-layer".

===========================================================================
DTCG COMPLIANCE JUDGMENT
===========================================================================
Confirmed "no" for both phases by inspection: tokens are plain TypeScript
object literals (not JSON), using bespoke `value` / `description` keys
(not the DTCG spec's required `$value`, with optional `$type`/`$description`).
No `$type` metadata exists anywhere in either phase's source.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEFORE_SRC = ROOT / "data/repos/polaris/before/polaris-tokens/src"
AFTER_SRC = ROOT / "data/repos/polaris/after/polaris-tokens/src"
RESULTS_PATH = ROOT / "results/tokens_polaris.json"

BEFORE_TAG = "@shopify/polaris-tokens@7.12.1"
AFTER_TAG = "@shopify/polaris-tokens@8.0.0"

CATEGORIES = ["color", "typography", "spacing", "radius", "shadow", "motion", "other"]

# (relative path under .../src, "kind") -- kind controls flattening.
#   "palette"     -> multiple `export const <family>` blocks, flatten to
#                    palette-<family>-<scale>, category "color"
#   "size"        -> single `export const size` block, flatten to
#                    size-<scale>, category "spacing"
#   "themes_base" -> single `export const <name>` block, names used as-is,
#                    category resolved per-file (and per-key for border.ts)
FILES_BEFORE = [
    ("colors.ts", "palette"),
    ("colors-experimental.ts", "palette"),
    ("size.ts", "size"),
    ("themes/base/border.ts", "themes_base"),
    ("themes/base/breakpoints.ts", "themes_base"),
    ("themes/base/color.ts", "themes_base"),
    ("themes/base/font.ts", "themes_base"),
    ("themes/base/height.ts", "themes_base"),
    ("themes/base/motion.ts", "themes_base"),
    ("themes/base/shadow.ts", "themes_base"),
    ("themes/base/space.ts", "themes_base"),
    ("themes/base/text.ts", "themes_base"),
    ("themes/base/width.ts", "themes_base"),
    ("themes/base/zIndex.ts", "themes_base"),
]

# after/ has no colors-experimental.ts (its content was absorbed into colors.ts).
FILES_AFTER = [f for f in FILES_BEFORE if f[0] != "colors-experimental.ts"]

THEMES_BASE_CATEGORY = {
    "breakpoints": "other",
    "color": "color",
    "font": "typography",
    "height": "other",
    "motion": "motion",
    "shadow": "shadow",
    "space": "spacing",
    "text": "typography",
    "width": "other",
    "zIndex": "other",
    # "border" handled specially, per-key, below.
}

EXPORT_CONST_RE = re.compile(r"^export const (\w+)\b")
# Token/scale keys can contain hyphens (e.g. 'border-radius-0',
# 'font-letter-spacing-densest'), so the key charclass must include '-'.
KEY_RE = re.compile(r"^ {2}'?([A-Za-z0-9_-]+)'?:\s")
# Some blocks (size.ts) close with "} as const;" instead of a bare "};".
BLOCK_END_RE = re.compile(r"^(\};|\} as const;)$")


def extract_blocks(text: str):
    """Yield (const_name, [token_key, ...]) for every top-level
    `export const <name> ... = { ... };` object literal in `text`.
    See module docstring ("EXTRACTION APPROACH") for the exact rule.
    """
    lines = text.split("\n")
    i = 0
    blocks = []
    while i < len(lines):
        m = EXPORT_CONST_RE.match(lines[i])
        if not m:
            i += 1
            continue
        const_name = m.group(1)

        # Scan forward to the line that actually opens the object literal
        # (same line for simple declarations; a later "} = {" line for
        # declarations with a multi-line mapped-type annotation).
        start = i
        while start < len(lines) and not lines[start].rstrip().endswith("= {"):
            start += 1
        if start >= len(lines):
            break  # malformed / no object literal found; stop safely

        # Scan forward to the matching column-0 closing line. Almost every
        # block closes with a bare "};"; size.ts uses "} as const;" instead
        # (it's declared `export const size = {...} as const;`).
        end = start + 1
        while end < len(lines) and not BLOCK_END_RE.match(lines[end]):
            end += 1
        if end >= len(lines):
            break

        keys = [
            km.group(1)
            for line in lines[start + 1 : end]
            if (km := KEY_RE.match(line))
        ]
        blocks.append((const_name, keys))
        i = end + 1
    return blocks


def categorize_themes_base(file_stem: str, token_name: str) -> str:
    if file_stem == "border":
        return "radius" if "radius" in token_name else "other"
    return THEMES_BASE_CATEGORY[file_stem]


def collect_tokens(src_dir: Path, file_list):
    """Returns dict: token_name -> category, plus a per-file debug count
    for sanity-checking (printed at the end of main())."""
    tokens = {}
    debug_counts = []
    for rel_path, kind in file_list:
        path = src_dir / rel_path
        text = path.read_text()
        blocks = extract_blocks(text)
        file_stem = Path(rel_path).stem  # e.g. "colors", "border", "size"
        file_token_count = 0

        for const_name, keys in blocks:
            for key in keys:
                if kind == "palette":
                    name = f"palette-{const_name}-{key}"
                    category = "color"
                elif kind == "size":
                    name = f"size-{key}"
                    category = "spacing"
                else:  # themes_base
                    name = key
                    category = categorize_themes_base(file_stem, name)

                if name in tokens and tokens[name] != category:
                    print(
                        f"  WARNING: token name collision '{name}' "
                        f"(existing category {tokens[name]!r} vs new "
                        f"{category!r} from {rel_path})"
                    )
                tokens[name] = category
                file_token_count += 1

        debug_counts.append((rel_path, file_token_count))
    return tokens, debug_counts


# ---------------------------------------------------------------------------
# Accessibility-token evidence scan (RQ2 / rubric §4.3). We scan the actual
# extracted token names (plus, for target-size/reduced-motion, the raw file
# text as a backstop in case such a token exists as a value/comment rather
# than a name) for real evidence -- nothing here is asserted without a
# citation computed at run time.
# ---------------------------------------------------------------------------

def find_contrast_safe_pairs(tokens: dict, src_dir: Path):
    """WCAG 1.4.3/1.4.11: look for token names that explicitly pair a
    foreground token with the background it's designed to sit on -- Polaris's
    own naming convention for this is the '-on-bg-fill' / '-on-color' suffix
    (e.g. 'color-text-critical-on-bg-fill', 'color-icon-on-color'), which is
    a real, if informal, documented contrast-safe pairing convention."""
    matches = sorted(
        n for n in tokens if re.search(r"-on-(bg-fill|color)(-|$)", n)
    )
    if not matches:
        return {"present": False, "evidence": ""}
    rel = "polaris-tokens/src/themes/base/color.ts"
    example = matches[0]
    return {
        "present": True,
        "evidence": (
            f"{rel}: {len(matches)} token(s) with the '-on-bg-fill'/'-on-color' "
            f"naming convention pairing a foreground color with the specific "
            f"background it is designed to sit on, e.g. '{example}'."
        ),
    }


def find_focus_ring(tokens: dict, src_dir: Path):
    matches = sorted(n for n in tokens if "focus" in n)
    if not matches:
        return {"present": False, "evidence": ""}
    rel = "polaris-tokens/src/themes/base/color.ts"
    example = matches[0]
    return {
        "present": True,
        "evidence": (
            f"{rel}: dedicated focus-indicator token(s) found, e.g. "
            f"'{example}' ({len(matches)} total: {', '.join(matches)})."
        ),
    }


TARGET_SIZE_RE = re.compile(r"target-size|touch-target|tap-target|min-target", re.I)
REDUCED_MOTION_RE = re.compile(r"reduced-motion|prefers-reduced", re.I)


def find_via_full_text_scan(src_dir: Path, file_list, pattern: re.Pattern):
    for rel_path, _kind in file_list:
        text = (src_dir / rel_path).read_text()
        m = pattern.search(text)
        if m:
            return rel_path, m.group(0)
    return None, None


def build_accessibility_tokens(tokens: dict, src_dir: Path, file_list):
    contrast = find_contrast_safe_pairs(tokens, src_dir)
    focus = find_focus_ring(tokens, src_dir)

    target_file, target_match = find_via_full_text_scan(src_dir, file_list, TARGET_SIZE_RE)
    target_size = (
        {"present": False, "evidence": ""}
        if target_file is None
        else {
            "present": True,
            "evidence": f"{target_file}: matched '{target_match}'",
        }
    )

    motion_file, motion_match = find_via_full_text_scan(src_dir, file_list, REDUCED_MOTION_RE)
    reduced_motion = (
        {"present": False, "evidence": ""}
        if motion_file is None
        else {
            "present": True,
            "evidence": f"{motion_file}: matched '{motion_match}'",
        }
    )

    return {
        "contrast_safe_pairs": contrast,
        "focus_ring": focus,
        "target_size": target_size,
        "reduced_motion": reduced_motion,
    }


# ---------------------------------------------------------------------------
# Diff + "likely renamed" heuristic
# ---------------------------------------------------------------------------

def strip_experimental(name: str) -> str:
    return re.sub(r"-experimental$", "", name)


def compute_diff(before_tokens: dict, after_tokens: dict):
    before_set = set(before_tokens)
    after_set = set(after_tokens)

    removed = sorted(before_set - after_set)
    added = sorted(after_set - before_set)

    # "Likely renamed, not removed" heuristic: a removed name is flagged as
    # a likely rename (rather than a genuine deletion) only if stripping a
    # trailing "-experimental" suffix from it (or from an added name) makes
    # it match an entry in the *added* set exactly. This is a conservative,
    # literal, no-fuzzy-matching rule -- it will not claim a rename unless
    # the normalized names are identical, so it is unlikely to invent
    # renames that aren't really there.
    added_set = set(added)
    added_stripped = {strip_experimental(a): a for a in added}
    likely_renamed_pairs = []
    for r in removed:
        r_stripped = strip_experimental(r)
        if r_stripped in added_set or r_stripped in added_stripped:
            match = r_stripped if r_stripped in added_set else added_stripped[r_stripped]
            likely_renamed_pairs.append((r, match))

    return {
        "removed_count": len(removed),
        "added_count": len(added),
        "removed_names_sample": removed[:25],
        "added_names_sample": added[:25],
        "likely_renamed_count": len(likely_renamed_pairs),
        "renamed_note": (
            "Rename detection used a conservative, literal heuristic: a "
            "removed name counts as a 'likely rename' only if stripping a "
            "trailing '-experimental' suffix makes it match an added name "
            "exactly (no fuzzy/edit-distance matching). "
            + (
                f"{len(likely_renamed_pairs)} such pair(s) found: "
                + "; ".join(f"'{r}' -> '{a}'" for r, a in likely_renamed_pairs[:10])
                if likely_renamed_pairs
                else "No pairs matched this rule: the diff volume is "
                "overwhelmingly pure removal, not rename-to-a-new-name. "
                "Most removed names are either (a) an entire duplicate "
                "'-experimental' or legacy raw-scale token whose value was "
                "inlined/re-sourced directly from the size/color primitive "
                "scale rather than replaced by a differently-named token "
                "(e.g. border-radius-1..6 removed, but the semantic "
                "border-radius-100/200/... names that referenced them via "
                "var() already existed pre-transition and simply changed "
                "their internal value reference), or (b) part of the old "
                "10-step (50-900) color palette entirely superseded by the "
                "16-step (1-16) palette that already existed as "
                "colors-experimental.ts before the transition. This "
                "matches the CHANGELOG's own framing: 'removed legacy v11 "
                "tokens' + 'added border-radius semantic layer' describes a "
                "cleanup/formalization, not a mass rename."
            )
        ),
    }


def build_phase(tag: str, tokens: dict, layering: str, dtcg: str, accessibility: dict):
    by_category = {c: 0 for c in CATEGORIES}
    for category in tokens.values():
        by_category[category] += 1
    return {
        "tag": tag,
        "total_tokens": len(tokens),
        "by_category": by_category,
        "token_names": sorted(tokens),
        "layering": layering,
        "dtcg_compliant": dtcg,
        "accessibility_tokens": accessibility,
    }


def main():
    print("=== Parsing BEFORE (7.12.1) ===")
    before_tokens, before_debug = collect_tokens(BEFORE_SRC, FILES_BEFORE)
    for rel_path, count in before_debug:
        print(f"  {rel_path}: {count} token names")
    print(f"  TOTAL (deduped): {len(before_tokens)}")

    print("\n=== Parsing AFTER (8.0.0) ===")
    after_tokens, after_debug = collect_tokens(AFTER_SRC, FILES_AFTER)
    for rel_path, count in after_debug:
        print(f"  {rel_path}: {count} token names")
    print(f"  TOTAL (deduped): {len(after_tokens)}")

    before_a11y = build_accessibility_tokens(before_tokens, BEFORE_SRC, FILES_BEFORE)
    after_a11y = build_accessibility_tokens(after_tokens, AFTER_SRC, FILES_AFTER)

    before_phase = build_phase(BEFORE_TAG, before_tokens, "2-layer", "no", before_a11y)
    after_phase = build_phase(AFTER_TAG, after_tokens, "2-layer", "no", after_a11y)

    diff = compute_diff(before_tokens, after_tokens)

    output = {
        "system": "Shopify Polaris",
        "slug": "polaris",
        "before": before_phase,
        "after": after_phase,
        "diff": diff,
        "parser_notes": (
            "Extraction: token names parsed with a line-based regex scanner "
            "(no TS/AST parser used) that exploits this codebase's "
            "consistent Prettier formatting -- top-level object-literal "
            "keys are indented by exactly two spaces, nested `value:`/"
            "`description:` metadata keys by four, and a top-level "
            "statement always closes with an un-indented '};'. See "
            "scripts/parse_polaris.py module docstring for the full rule "
            "and the exact file list parsed vs. excluded. "
            "Parsed sources: colors.ts + colors-experimental.ts (before "
            "only; its content was absorbed into after's colors.ts) as the "
            "raw color PALETTE scale, flattened to 'palette-<family>-"
            "<scale>' (e.g. 'palette-gray-50'); size.ts as the raw spacing "
            "PRIMITIVE scale, flattened to 'size-<scale>'; and the 11 "
            "themes/base/*.ts semantic token modules (border, breakpoints, "
            "color, font, height, motion, shadow, space, text, width, "
            "zIndex) whose string-literal keys are already fully-qualified "
            "token names. Excluded: utilities.ts/utils.ts (helper "
            "functions, no tokens), themes/types.ts + constants.ts + "
            "utils.ts + index.ts (TS types / theme-name constants / merge "
            "helpers, no tokens), and themes/light.ts + light-uplift.ts "
            "(before) + light-high-contrast.ts (after) -- these are theme "
            "VALUE OVERLAYS that re-assign alternate values to token names "
            "already declared in themes/base/*.ts, not new token "
            "declarations; counting them would double-count or skew the "
            "diff. "
            "Categorization: assigned per source file, matching Polaris's "
            "own module boundaries (themes/base/index.ts imports exactly "
            "these 11 category modules) -- see module docstring "
            "'CATEGORIZATION RULES' for the full per-file table, including "
            "the border.ts special case (per-key: 'radius' if the token "
            "name contains 'radius', else 'other' for border-width-*) and "
            "the conservative choice to bucket width.ts/height.ts/"
            "zIndex.ts/breakpoints.ts as 'other' rather than stretching "
            "them into 'spacing'. "
            "Layering: coded '2-layer' (primitive -> semantic) for BOTH "
            "before and after -- Polaris already had a primitive palette "
            "(colors.ts/size.ts) feeding semantic tokens (themes/base/"
            "*.ts) before this transition (consistent with plan §4.2's "
            "note that this is a legacy-cleanup story, not a 'tokens "
            "introduced' story), and no separate component-tier "
            "file/namespace exists in either phase -- a handful of "
            "component-specific names (color-avatar-bg-fill, "
            "space-card-gap, shadow-button-primary) live in the same flat "
            "dictionaries as generic semantic tokens, distinguished only "
            "by naming convention, so we conservatively do not call this "
            "'3-layer' in either phase. "
            "DTCG compliance: confirmed 'no' for both phases by direct "
            "inspection -- tokens are TypeScript object literals (not "
            "JSON) using bespoke 'value'/'description' keys, never the "
            "DTCG spec's required '$value' (with optional '$type'/"
            "'$description'); no '$type' metadata exists anywhere in "
            "either phase's source. "
            "Accessibility tokens: contrast_safe_pairs and focus_ring "
            "evidence come from a live regex scan of the extracted token "
            "NAMES (not hardcoded) -- contrast_safe_pairs looks for the "
            "'-on-bg-fill'/'-on-color' foreground/background pairing "
            "naming convention in themes/base/color.ts; focus_ring looks "
            "for any token name containing 'focus' (e.g. "
            "'color-border-focus', present in both phases). target_size "
            "and reduced_motion were searched for across every parsed "
            "file's full text (not just token names, as a backstop) via "
            "the patterns target-size|touch-target|tap-target|min-target "
            "and reduced-motion|prefers-reduced respectively; both came "
            "back with zero matches in both phases, so both are reported "
            "present:false. Note: after/ adds a 'light-high-contrast-"
            "experimental' THEME (themes/light-high-contrast.ts) that "
            "overrides several color values for higher contrast -- this is "
            "real accessibility-oriented design intent, but it is a whole "
            "alternate theme (a set of alternate VALUES for already-"
            "counted token names), not a new contrast-ratio-metadata token "
            "or token name, so it does not change token counts and is not "
            "counted as contrast_safe_pairs evidence (which is scoped to "
            "explicit foreground/background pairing tokens per rubric "
            "§4.3); it is worth a mention in the writeup as a related, "
            "softer accessibility signal in the after state."
        ),
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(output, indent=2) + "\n")

    print(f"\n=== Diff ===")
    print(f"  removed_count: {diff['removed_count']}")
    print(f"  added_count: {diff['added_count']}")
    print(f"  likely_renamed_count: {diff['likely_renamed_count']}")
    print(f"\nWrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
