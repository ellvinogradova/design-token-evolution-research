#!/usr/bin/env python3
r"""Day 3: token parser for Ant Design (v4 -> v5), one of the N=5 systems in the
design-token-evolution-research study (see plans/design-token-evolution-research-plan.md
S4.3 for the coding rubric this implements).

BEFORE (v4, tag 4.24.16): Less variable files under
    data/repos/ant-design/before/components/style/themes/*.less
  (compact.less, dark.less, default.less, index.less, variable.less)

AFTER (v5, tag 5.0.0): TypeScript token interfaces + seed object literal under
    data/repos/ant-design/after/components/theme/interface.ts
    data/repos/ant-design/after/components/theme/themes/seed.ts

Output: results/tokens_ant-design.json (schema fixed by the task spec).

===========================================================================
PARSING APPROACH (documented per task instructions)
===========================================================================

BEFORE (Less):
  Every `*.less` file directly under components/style/themes/ is scanned with
  a single regex that matches a Less variable declaration:

      ^[ \t]*@([A-Za-z][\w-]*)\s*:\s*(.*?);

  - Anchored on optional leading whitespace then '@' then an identifier then
    ':' -- this deliberately also picks up variables declared *inside* a
    selector block (e.g. `@{html-selector} { @base-primary: @blue-6; ... }`
    in variable.less), which are still real Less variable declarations.
  - `.*?` + re.DOTALL lets the value span multiple physical lines (several
    tokens here -- @font-family, @shadow-2, @input-padding-vertical-base --
    wrap across lines) while stopping at the first top-level `;`.
  - CSS custom-property lines (`--ant-primary-color: ...;`) do NOT match
    (they start with `--`, not `@`), so they are correctly excluded.
  - `@import '...';` lines do NOT match: after "import" the next non-space
    character is a quote, not ':', so the regex never captures "import" as a
    variable name. No special-casing was needed for the "exclude pure
    @import lines" requirement -- it falls out of the regex shape.
  - Four files (compact.less, dark.less, default.less, variable.less)
    largely redeclare an overlapping vocabulary of the *same* token names
    for different theme variants (compact spacing scale, dark palette,
    default vs. CSS-variable-based `variable.less` entry point). Token
    *names* are unioned/deduplicated across all files to represent "the v4
    flat token vocabulary" as a whole; index.less contributes nothing (it is
    pure @import) but is scanned too for completeness/transparency.
  - No manual curation was applied beyond this: a handful of non-visual
    "meta" variables incidentally match the same syntax (@theme, @mode,
    @html-selector, @ant-prefix, @root-entry-name) and are included per a
    literal reading of "extract every @variable-name: value; declaration";
    they fall into the 'other' category and are immaterial to the totals.

AFTER (TypeScript):
  Two sources, matching the task's explicit pointers ("the actual
  interface.ts ... and the seed.ts object literal"):

  1. interface.ts -- the seven interfaces that make up the real, *literal*
     (non-mapped-type) global token surface are located by name and their
     bodies extracted via brace-depth matching:
         SeedToken, NeutralColorMapToken, ColorMapToken, SizeMapToken,
         HeightMapToken, CommonMapToken, AliasToken
     `MapToken` itself is skipped: its body is empty (`interface MapToken
     extends SeedToken, ColorPalettes, ColorMapToken, SizeMapToken,
     HeightMapToken, CommonMapToken {}`) -- it contributes no new property
     names of its own, only an aggregation of the others, which are already
     parsed directly.
     `ComponentTokenMap`, `OverrideToken`, `GlobalToken` are skipped: these
     describe per-*component* token overrides (Button, Table, ...), which
     are out of scope -- Day 2's extraction only pulled components/theme/,
     not each component's own style/ folder, so per-component tokens were
     never part of this system's extracted corpus in the first place.
     `PresetColorType` and `ColorPalettes` are skipped: both are TypeScript
     *mapped/template-literal* types (`Record<PresetColorKey, string>` and
     `{ [key in \`${...}-${1|2|...|10}\`]: string }`), not literal
     `key: type;` lists -- they cannot be enumerated by static regex without
     hardcoding the color-name x 1-10 cross product, which would be
     generating data rather than parsing it. This is a documented, honest
     under-count (ColorPalettes alone is ~130 runtime-generated keys,
     e.g. blue-1..blue-10, that never appear literally in source).
  2. themes/seed.ts -- the `defaultPresetColors` and `seedToken` object
     literals are located the same way (brace-depth matching from
     `const NAME ... = {`) and scanned for `key:` at the start of a
     (trimmed) line. This recovers the 13 concrete preset-color names
     (blue, purple, cyan, ...) that PresetColorType could not give us
     statically, and cross-checks the SeedToken interface against its
     actual literal implementation.
  Property/key extraction, for both interface bodies and object-literal
  bodies, uses one shared line-based rule: a (trimmed) line matching
  `^([A-Za-z_$][\w$]*)\??\s*:` is a declaration; the identifier before the
  ':' is the token name. Comment lines (//, /*, *) and spread lines (...x)
  are skipped. This does not attempt to parse the *value* -- only the key --
  which sidesteps values that legitimately span multiple lines (e.g.
  seed.ts's `fontFamily` template literal spans 3 lines; a full-value parser
  would need real tokenization, a key-only line scan does not).
  `alias.ts` (util/formatToken) was read as a manual cross-check: its
  returned object literal's key set matches the AliasToken interface 1:1,
  confirming the interface-based extraction is not missing anything real.

===========================================================================
CATEGORY RULES (documented per task instructions)
===========================================================================
Applied to a normalized form of the name: lowercased, with '-' and '_'
stripped (so kebab-case v4 and camelCase v5 names are compared on equal
footing, and multi-word Less names like "line-height-base" collapse to
"lineheightbase" so a "lineheight" check can fire). Checked in this fixed
priority order, first match wins:

  1. color      -- contains "color"
  2. typography -- contains "font", "text", or "lineheight"
  3. spacing    -- contains "margin", "padding", "size", or "gap"
  4. radius     -- contains "radius"
  5. shadow     -- contains "shadow" or "elevation"
  6. motion     -- contains "motion", "duration", "easing", or "ease"
  7. other      -- none of the above

Two deliberate deviations from the task's illustrative rule text, both
driven by tokens actually observed in this system's files:
  - Case-insensitive matching throughout, rather than requiring the exact
    casing shown in the task text (e.g. literal "Size"). The task's
    dual-case examples ("font"/"Font", "Size") read as illustrating the two
    naming conventions in play (kebab-case v4 vs. camelCase v5), not as a
    case-sensitivity requirement -- and case-sensitive "Size" would miss
    v5's own SizeMapToken family (sizeXXL, sizeSM, ...), which all start
    with a lowercase 's'.
  - "lineheight" added to the typography rule, and "ease" added to the
    motion rule. v5's lineHeight/lineHeightLG/... tokens are unambiguously
    typography but contain neither "font" nor "text"; v4's @ease-base-out,
    @ease-in, @ease-in-out-circ, etc. (14 tokens) are unambiguously motion
    easing curves but are spelled "ease-*", not "easing-*". Both additions
    were checked against the full extracted name list for false positives
    (e.g. "ease" colliding with a word like "release") before being kept --
    none were found in either corpus.
  - Priority order matters and is intentional: "colorText*"/"colorBg*"
    style names correctly land in `color` (checked first) even though they
    contain "text"/"bg"-adjacent substrings, because they are fundamentally
    color tokens; "fontSizeSM" lands in `typography` (font checked before
    size) rather than `spacing`, matching how the token is actually used.
  - A third, narrow color-rule extension (checked before the keyword list):
    141 before-names and 13 after-names follow a bare-hue or numbered-shade
    pattern for antd's 13 preset colors plus "primary" (e.g. "blue",
    "blue-1".."blue-10", "primary-1".."primary-10") -- literal hex/HSL
    color values that do not contain the substring "color" at all. Without
    this extension they would all misfile into `other`. See
    is_preset_color_family_name() / PRESET_COLOR_FAMILY_NAMES below.

Tokens that are purely dimensional but do not contain any listed keyword
(e.g. v4's @height-base, @btn-height-base -- "height"/"width" were not in
the task's given keyword list and were not added) fall into `other`. This
is a known, documented limitation of a literal-keyword rubric, not a bug.

===========================================================================
DIFF METHODOLOGY (documented per task instructions)
===========================================================================
1. Raw diff: exact string match between the before name set (already
   stored without the leading '@') and the after name set. Expected to
   show ~100% removed/added, per the task brief, because v4 used
   @kebab-case and v5 uses camelCase -- this is itself a finding (a
   discontinuous rename), not a parser bug.
2. Fuzzy secondary pass: every before name is converted kebab-case ->
   camelCase (e.g. "font-size-base" -> "fontSizeBase"), then compared
   case-insensitively against every after name. A case-insensitive
   comparison (rather than exact-case) is required because v5's own
   convention capitalizes size suffixes fully (paddingLG, controlHeightSM)
   where a naive kebab->camel conversion of "padding-lg"/"control-height-sm"
   would produce "paddingLg"/"controlHeightSm" -- same word, different
   casing. Matches found this way are reported as "likely renamed, not
   removed"; everything else in the removed set is reported as genuinely
   gone (no surviving equivalent name, even allowing for a casing change).
   This is a strict, name-only equivalence check -- it does not attempt
   semantic matching (e.g. "primary-color" -> "colorPrimary" is a real,
   documented rename but is *not* caught, because v5's naming convention
   reordered "noun-adjective" to "adjective-noun" rather than merely
   re-casing the same word order; catching that would require a hardcoded
   synonym table, which would be asserting domain knowledge, not parsing).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEFORE_DIR = ROOT / "data" / "repos" / "ant-design" / "before"
AFTER_DIR = ROOT / "data" / "repos" / "ant-design" / "after"
RESULTS_PATH = ROOT / "results" / "tokens_ant-design.json"

BEFORE_THEMES_DIR = BEFORE_DIR / "components" / "style" / "themes"
AFTER_INTERFACE_FILE = AFTER_DIR / "components" / "theme" / "interface.ts"
AFTER_SEED_FILE = AFTER_DIR / "components" / "theme" / "themes" / "seed.ts"

# Interfaces in interface.ts that form the literal (non-mapped-type) global
# token surface. See module docstring for why MapToken/ComponentTokenMap/
# OverrideToken/GlobalToken/PresetColorType/ColorPalettes are excluded.
AFTER_INTERFACE_NAMES = [
    "SeedToken",
    "NeutralColorMapToken",
    "ColorMapToken",
    "SizeMapToken",
    "HeightMapToken",
    "CommonMapToken",
    "AliasToken",
]

# Object literals in seed.ts to scan for concrete key names.
AFTER_SEED_OBJECT_NAMES = ["defaultPresetColors", "seedToken"]


# ---------------------------------------------------------------------------
# BEFORE (Less) parsing
# ---------------------------------------------------------------------------

LESS_DECL_RE = re.compile(r"^[ \t]*@([A-Za-z][\w-]*)\s*:\s*(.*?);", re.MULTILINE | re.DOTALL)


def parse_less_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [m.group(1) for m in LESS_DECL_RE.finditer(text)]


def parse_before() -> dict:
    names_by_file = {}
    all_names = []
    for less_file in sorted(BEFORE_THEMES_DIR.glob("*.less")):
        names = parse_less_file(less_file)
        names_by_file[less_file.name] = names
        all_names.extend(names)
    unique_names = sorted(set(all_names))
    return {"names": unique_names, "by_file": names_by_file}


# ---------------------------------------------------------------------------
# AFTER (TypeScript) parsing
# ---------------------------------------------------------------------------

KEY_LINE_RE = re.compile(r"^([A-Za-z_$][\w$]*)\??\s*:")


def extract_block(text: str, start_idx: int) -> str:
    """Given the index just after an opening '{', return the block body up
    to (not including) the matching closing '}', using simple brace-depth
    counting. Good enough here: none of the parsed blocks contain string
    literals with unbalanced braces."""
    depth = 1
    i = start_idx
    while i < len(text) and depth > 0:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return text[start_idx : i - 1]


def extract_keys_from_block(body: str) -> list[str]:
    names = []
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("//") or s.startswith("/*") or s.startswith("*") or s.startswith("..."):
            continue
        m = KEY_LINE_RE.match(s)
        if m:
            names.append(m.group(1))
    return names


def find_interface_body(text: str, iface_name: str) -> str | None:
    pattern = re.compile(r"interface\s+" + re.escape(iface_name) + r"\b[^{]*\{")
    m = pattern.search(text)
    if not m:
        return None
    return extract_block(text, m.end())


def find_const_object_body(text: str, const_name: str) -> str | None:
    pattern = re.compile(r"const\s+" + re.escape(const_name) + r"\b[^={]*=\s*\{")
    m = pattern.search(text)
    if not m:
        return None
    return extract_block(text, m.end())


def parse_after() -> dict:
    interface_text = AFTER_INTERFACE_FILE.read_text(encoding="utf-8")
    seed_text = AFTER_SEED_FILE.read_text(encoding="utf-8")

    names_by_source = {}
    all_names = []

    for iface_name in AFTER_INTERFACE_NAMES:
        body = find_interface_body(interface_text, iface_name)
        if body is None:
            raise RuntimeError(f"interface {iface_name} not found in {AFTER_INTERFACE_FILE}")
        keys = extract_keys_from_block(body)
        names_by_source[f"interface.ts:{iface_name}"] = keys
        all_names.extend(keys)

    for obj_name in AFTER_SEED_OBJECT_NAMES:
        body = find_const_object_body(seed_text, obj_name)
        if body is None:
            raise RuntimeError(f"const {obj_name} not found in {AFTER_SEED_FILE}")
        keys = extract_keys_from_block(body)
        names_by_source[f"seed.ts:{obj_name}"] = keys
        all_names.extend(keys)

    unique_names = sorted(set(all_names))
    return {"names": unique_names, "by_source": names_by_source}


# ---------------------------------------------------------------------------
# Categorization
# ---------------------------------------------------------------------------

CATEGORY_ORDER = ["color", "typography", "spacing", "radius", "shadow", "motion"]

CATEGORY_KEYWORDS = {
    "color": ["color"],
    "typography": ["font", "text", "lineheight"],
    "spacing": ["margin", "padding", "size", "gap"],
    "radius": ["radius"],
    "shadow": ["shadow", "elevation"],
    "motion": ["motion", "duration", "easing", "ease"],
}

# A third, narrowly-scoped color-rule extension, added after inspecting the
# actual before/after token lists: 141 before-tokens follow a
# "<name>-<1..10>" pattern (blue-1..blue-10, purple-1..purple-10, ...,
# primary-1..primary-10) -- a numbered tint/shade scale for antd's 13 preset
# hues plus the "primary" semantic color alias. after has the 13 bare hue
# names themselves (seed.ts's defaultPresetColors: blue, purple, cyan, ...).
# None of these contain the literal substring "color", so the generic rule
# above would misfile ~141 before-tokens and 13 after-tokens into 'other'
# despite them being unambiguous color tokens (literal hex/HSL color
# values). This extension matches only that specific, actually-observed
# pattern -- it does not attempt broader color-name inference.
PRESET_COLOR_FAMILY_NAMES = {
    "blue", "purple", "cyan", "green", "magenta", "pink", "red", "orange",
    "yellow", "volcano", "geekblue", "lime", "gold", "primary",
}
NUMBERED_COLOR_RE = re.compile(r"^([a-zA-Z]+)-([1-9]|10)$")


def normalize_for_category(name: str) -> str:
    return re.sub(r"[-_]", "", name).lower()


def is_preset_color_family_name(name: str) -> bool:
    if name in PRESET_COLOR_FAMILY_NAMES:
        return True
    m = NUMBERED_COLOR_RE.match(name)
    return bool(m and m.group(1) in PRESET_COLOR_FAMILY_NAMES)


def categorize(name: str) -> str:
    if is_preset_color_family_name(name):
        return "color"
    n = normalize_for_category(name)
    for category in CATEGORY_ORDER:
        for kw in CATEGORY_KEYWORDS[category]:
            if kw in n:
                return category
    return "other"


def by_category(names: list[str]) -> dict:
    counts = {c: 0 for c in CATEGORY_ORDER + ["other"]}
    for name in names:
        counts[categorize(name)] += 1
    return counts


# ---------------------------------------------------------------------------
# Diff (raw + fuzzy)
# ---------------------------------------------------------------------------


def kebab_to_camel(name: str) -> str:
    parts = re.split(r"[-_]", name)
    if not parts:
        return name
    out = parts[0]
    for p in parts[1:]:
        if not p:
            continue
        out += p[0].upper() + p[1:]
    return out


def compute_diff(before_names: list[str], after_names: list[str]) -> dict:
    before_set = set(before_names)
    after_set = set(after_names)

    removed = sorted(before_set - after_set)
    added = sorted(after_set - before_set)

    after_lower_set = {n.lower() for n in after_names}
    likely_renamed = []
    genuinely_gone = []
    for name in removed:
        camel = kebab_to_camel(name)
        if camel.lower() in after_lower_set:
            likely_renamed.append(name)
        else:
            genuinely_gone.append(name)

    return {
        "removed_count": len(removed),
        "added_count": len(added),
        "removed_names_sample": removed[:20],
        "added_names_sample": added[:20],
        "likely_renamed_count": len(likely_renamed),
        "likely_renamed_sample": likely_renamed[:20],
        "renamed_note": (
            f"Raw string diff (before names have '@' already stripped; after names are the "
            f"TS identifiers as written): {len(removed)}/{len(before_set)} before-names have no "
            f"exact-string match in after, and {len(added)}/{len(after_set)} after-names have no "
            f"exact-string match in before -- essentially total churn, as expected for a "
            f"kebab-case -> camelCase rewrite. Fuzzy pass: convert each removed before-name from "
            f"kebab-case to camelCase (e.g. font-size-base -> fontSizeBase) and compare "
            f"case-insensitively against every after-name (case-insensitive because v5 fully "
            f"capitalizes size suffixes, e.g. control-padding-horizontal-sm -> "
            f"controlPaddingHorizontalSm needs to match controlPaddingHorizontalSM). This finds "
            f"{len(likely_renamed)} likely-renamed-not-removed tokens ({', '.join(likely_renamed[:15])}"
            f"{', ...' if len(likely_renamed) > 15 else ''}), all in the padding/margin/font-family/"
            f"control-padding family where v4's per-scale suffix (-lg/-md/-sm/-xs) happens to "
            f"survive a literal casing conversion. The remaining "
            f"{len(genuinely_gone)} removed names do not match any after-name even after "
            f"normalization -- most are single-component variables (e.g. @btn-*, @table-*, "
            f"@picker-*) that v5 replaced with component-level ComponentToken overrides "
            f"(out of scope for this extraction, see interface.ts note) rather than global "
            f"aliases, or use a reordered semantic ('primary-color' -> 'colorPrimary' swaps "
            f"adjective-noun order, which a literal kebab->camel conversion cannot catch). This "
            f"confirms the study's expectation: v4->v5 is a discontinuous architecture rewrite, "
            f"not an incremental rename."
        ),
    }


# ---------------------------------------------------------------------------
# DTCG compliance check (data-driven, not assumed)
# ---------------------------------------------------------------------------


def check_dtcg_compliance(directory: Path) -> tuple[str, str]:
    """Scan every extracted file for literal W3C DTCG format markers
    ($value / $type as JSON-style keys). Returns (verdict, evidence)."""
    hits = []
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            # Skip git internals (e.g. .git/hooks/*.sample shell scripts use
            # "$value"-style shell variable syntax that has nothing to do
            # with DTCG token format -- a false positive, not a token file).
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for marker in ('"$value"', "'$value'", '"$type"', "'$type'"):
            if marker in text:
                hits.append(f"{path.relative_to(ROOT)}: found {marker}")
    if not hits:
        return "no", f"Scanned every file under {directory.relative_to(ROOT)} for literal \"$value\"/\"$type\" DTCG markers; none found."
    if len(hits) < 3:
        return "partial", "; ".join(hits)
    return "yes", "; ".join(hits[:5])


# ---------------------------------------------------------------------------
# Accessibility-token evidence (grep-based, cited)
# ---------------------------------------------------------------------------


def build_accessibility_tokens(phase: str) -> dict:
    if phase == "before":
        return {
            "contrast_safe_pairs": {
                "present": False,
                "evidence": "",
            },
            "focus_ring": {
                "present": True,
                "evidence": (
                    "components/style/themes/variable.less:209-210 declares "
                    "@link-focus-decoration: none; and @link-focus-outline: 0; (link focus-state "
                    "tokens -- note the value explicitly disables the native focus outline rather "
                    "than replacing it with a styled one, a real accessibility caveat, not an "
                    "enhancement). variable.less:235-239, under a '// Outline' section header, "
                    "declares @outline-blur-size: 0, @outline-width: 2px, @outline-color: "
                    "@primary-color (commented '// No use anymore'), and @outline-fade: 20% -- a "
                    "blur/width/color trio consistent with driving an interactive/focus glow via "
                    "box-shadow, though the component CSS that would consume them was not part of "
                    "this extraction (only components/style/themes/ was pulled, see "
                    "data/extraction-manifest.json), so consumption could not be directly confirmed."
                ),
            },
            "target_size": {
                "present": False,
                "evidence": "",
            },
            "reduced_motion": {
                "present": False,
                "evidence": "",
            },
        }
    return {
        "contrast_safe_pairs": {
            "present": False,
            "evidence": "",
        },
        "focus_ring": {
            "present": True,
            "evidence": (
                "components/theme/interface.ts:391-392 declares controlOutline: string and "
                "colorWarningOutline/colorErrorOutline: string on AliasToken; interface.ts:424 "
                "declares controlOutlineWidth: number; interface.ts:466 declares "
                "linkFocusDecoration: React.CSSProperties['textDecoration']; interface.ts:491-492 "
                "declares controlTmpOutline: string with the comment 'Used for DefaultButton, "
                "Switch which has default outline'. components/theme/util/alias.ts:96,104-105 "
                "compute controlOutlineWidth and controlOutline via getAlphaColor(...), and "
                "util/alias.ts:119 sets linkFocusDecoration: 'none' by default -- as in v4, the "
                "link focus decoration token exists but defaults to disabling visible focus "
                "styling rather than styling it, a recurring caveat across both versions."
            ),
        },
        "target_size": {
            "present": False,
            "evidence": "",
        },
        "reduced_motion": {
            "present": False,
            "evidence": "",
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    before_parsed = parse_before()
    after_parsed = parse_after()

    before_names = before_parsed["names"]
    after_names = after_parsed["names"]

    before_dtcg, before_dtcg_evidence = check_dtcg_compliance(BEFORE_DIR)
    after_dtcg, after_dtcg_evidence = check_dtcg_compliance(AFTER_DIR)

    diff = compute_diff(before_names, after_names)

    result = {
        "system": "Ant Design",
        "slug": "ant-design",
        "before": {
            "tag": "4.24.16",
            "total_tokens": len(before_names),
            "by_category": by_category(before_names),
            "token_names": before_names,
            "layering": "flat",
            "dtcg_compliant": before_dtcg,
            "accessibility_tokens": build_accessibility_tokens("before"),
        },
        "after": {
            "tag": "5.0.0",
            "total_tokens": len(after_names),
            "by_category": by_category(after_names),
            "token_names": after_names,
            "layering": "3-layer",
            "dtcg_compliant": after_dtcg,
            "accessibility_tokens": build_accessibility_tokens("after"),
        },
        "diff": {
            "removed_count": diff["removed_count"],
            "added_count": diff["added_count"],
            "removed_names_sample": diff["removed_names_sample"],
            "added_names_sample": diff["added_names_sample"],
            "likely_renamed_count": diff["likely_renamed_count"],
            "renamed_note": diff["renamed_note"],
        },
        "parser_notes": (
            "BEFORE: unioned unique @variable names across all *.less files directly under "
            "components/style/themes/ (compact.less, dark.less, default.less, index.less, "
            "variable.less) -- see module docstring for the full regex/approach and why "
            "compact/dark/default largely re-declare an overlapping vocabulary rather than "
            "adding disjoint names. Per-file raw counts: "
            + ", ".join(f"{k}={len(v)}" for k, v in before_parsed["by_file"].items())
            + f". Union across files = {len(before_names)} unique names.\n\n"
            "AFTER: unioned unique property/key names from interface.ts's SeedToken, "
            "NeutralColorMapToken, ColorMapToken, SizeMapToken, HeightMapToken, CommonMapToken, "
            "and AliasToken interfaces, plus seed.ts's defaultPresetColors and seedToken object "
            "literals. MapToken (empty body, pure aggregation via `extends`) and "
            "ComponentTokenMap/OverrideToken/GlobalToken (per-component overrides, out of the "
            "theme/-only extraction scope) were intentionally excluded, as were the "
            "PresetColorType/ColorPalettes *mapped types* (~130 runtime-generated palette keys "
            "like blue-1..blue-10 that have no literal `key: type;` form in source -- a "
            "documented, honest under-count, not a bug). Per-source raw counts: "
            + ", ".join(f"{k}={len(v)}" for k, v in after_parsed["by_source"].items())
            + f". Union across sources = {len(after_names)} unique names.\n\n"
            "LAYERING: before='flat' -- variable.less/default.less/etc. are single-level "
            "@name: value lists with no named layering scheme; before/docs/react/"
            "customize-theme.en-US.md and customize-theme-variable.en-US.md do not use "
            "'primitive'/'semantic'/'alias' language. after='3-layer' -- confirmed both "
            "structurally (interface.ts:151 `interface SeedToken`, :347 `interface MapToken "
            "extends SeedToken, ...`, :359 `interface AliasToken extends MapToken`) and in "
            "documentation (after/docs/react/customize-theme-v5.en-US.md:162, 'we provide a "
            "three-layer structure ... Seed Token, Map Token and Alias Token ... Map Tokens are "
            "derived from Seed Tokens, and Alias Tokens are derived from Map Tokens'). This is "
            "the textbook case the study's literature review cites (Ant Design 'Customize "
            "Theme' docs) and it held up under direct inspection of the actual source, not just "
            "the doc's own claim about itself.\n\n"
            f"DTCG COMPLIANCE: before={before_dtcg} ({before_dtcg_evidence}); "
            f"after={after_dtcg} ({after_dtcg_evidence}). Neither phase ships a literal "
            "W3C DTCG-format ($value/$type) JSON token file -- confirmed by scanning every "
            "extracted file, not assumed.\n\n"
            "ACCESSIBILITY TOKENS: see per-phase accessibility_tokens.*.evidence for cited "
            "findings. Neither version has a token or comment referencing a contrast ratio, an "
            "explicit minimum touch/tap target size, or prefers-reduced-motion/reduced-motion "
            "(confirmed via grep across before/, after/, and both docs/ trees -- zero hits for "
            "'contrast', 'reduced-motion', 'prefers-reduced', 'touch-target', 'tap-target', "
            "'target-size' in either phase). Both versions do carry outline/focus-related "
            "tokens (flagged focus_ring=true for both, with citations). One nuance intentionally "
            "NOT counted as target_size evidence: v4's @checkbox-size/@radio-size (16px) and v5's "
            "controlHeight/controlInteractiveSize (interface.ts:192,428; alias.ts:98, commented "
            "'Checkbox size and expand icon size') do control the physical size of small "
            "interactive controls, but neither is named or documented with any accessibility/"
            "target-size framing (no WCAG reference, no 'touch'/'tap'/'minimum' language) in "
            "the extracted source -- treating a generic dimension token as accessibility "
            "evidence without that framing would overclaim, per the task's 'do not mark "
            "present without a real citation' instruction. Worth a sentence in the write-up as "
            "a borderline case, not worth a 'present: true'.\n\n"
            "CATEGORY RULES: see module docstring CATEGORY RULES section for the full priority-"
            "ordered, case-insensitive keyword list and the three documented deviations from the "
            "task's illustrative (case-mixed) rule text.\n\n"
            "KNOWN 'other'-BUCKET LIMITATION (name-only categorization, stated rather than "
            "guessed): 148 of before's 283 'other' tokens (and a handful of after's 40, e.g. "
            "controlItemBgHover/controlItemBgActive*, which interface.ts itself annotates "
            "inline as '// Note. It also is a color') match a '-bg'/'-background'/'-border' "
            "name suffix. Some of these ARE color references (e.g. btn-default-bg resolves to "
            "@component-background, a color) and some are NOT (e.g. btn-border-width, "
            "border-width-base -- dimensions, not colors) -- the suffix alone does not "
            "disambiguate without resolving each token's actual Less/TS value, which the task "
            "scopes this categorizer to avoid (\"Categorizes each token name into one of... "
            "based on naming patterns\", not by resolving values). Rather than guess and risk "
            "false positives (e.g. mis-tagging border-width-base as color), these are left in "
            "'other' and flagged here as a known, name-only-categorization limitation -- unlike "
            "the preset-color-family extension above, where every matched name was unambiguously "
            "a literal color value with no false-positive risk.\n\n"
            "DIFF METHODOLOGY: see module docstring DIFF METHODOLOGY section and diff.renamed_note."
        ),
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Sanity-check summary printed to stdout.
    print(f"BEFORE total_tokens = {result['before']['total_tokens']}")
    print(f"  by_category = {result['before']['by_category']}")
    print(f"AFTER  total_tokens = {result['after']['total_tokens']}")
    print(f"  by_category = {result['after']['by_category']}")
    print(f"DIFF removed={diff['removed_count']} added={diff['added_count']} "
          f"likely_renamed={diff['likely_renamed_count']}")
    print(f"Wrote {RESULTS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
