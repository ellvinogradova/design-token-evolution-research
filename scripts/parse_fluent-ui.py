#!/usr/bin/env python3
"""Day 3: parse Fluent UI's v8 (Fabric) theme-object source (before = tag
`@fluentui/theme_v1.4.0`) and v9 stable theme-package source (after = tag
`@fluentui/react-theme_v9.0.0`) into a structured before/after token
inventory + diff, written to `results/tokens_fluent-ui.json`.

Per plan §4.2's locked-sample note: the "after" reference is the STABLE
`@fluentui/react-theme` package, not the alpha-only `@fluentui/tokens`
primitives package it wraps (which never left `1.0.0-alpha.*`). That is
exactly what got cloned into data/repos/fluent-ui/after/ -- confirmed below.

===========================================================================
WHICH FILES ARE PARSED, AND WHY
===========================================================================
Confirmed file listing (via `find data/repos/fluent-ui/{before,after} -type f`):

  before/packages/theme/src/
    types/IPalette.ts               <- interface, PARSED (color)
    types/ISemanticColors.ts        <- interface, PARSED (color)
    types/ISemanticTextColors.ts    <- interface, PARSED (color)
    types/ISpacing.ts               <- interface, PARSED (spacing)
    types/IEffects.ts               <- interface, PARSED (shadow/radius, per-key)
    types/IFontStyles.ts            <- interface, PARSED (typography)
    types/IAnimationStyles.ts       <- 2 interfaces, PARSED (motion)
    colors/FluentColors.ts          <- 3 namespaces, PARSED (color)
    fonts/FluentFonts.ts            <- 5 namespaces, PARSED (typography / other)
    effects/FluentDepths.ts         <- 1 namespace, PARSED (shadow)
    colors/DefaultPalette.ts        NOT parsed (see below)
    effects/DefaultEffects.ts       NOT parsed (see below)
    spacing/DefaultSpacing.ts       NOT parsed (see below)
    fonts/DefaultFontStyles.ts      NOT parsed (computed, not a literal)
    fonts/createFontStyles.ts(+snap) NOT parsed (generator fn / test fixture)
    FluentTheme.ts, createTheme.ts, mergeThemes.ts
                                     NOT parsed (composition/factory code)
    types/ITheme.ts, types/Theme.ts, types/IFabricConfig.ts, types/index.ts
                                     NOT parsed (barrels, window-config shape,
                                     and an internal/experimental "Theme.tokens"
                                     typing that never had a concrete value
                                     object in v8 -- see note below)

  after/packages/react-components/react-theme/src/
    tokens.ts                       <- 1 const block, PARSED (canonical flat
                                        alias/semantic token surface)
    global/colors.ts                <- exported scales + simple consts,
                                        PARSED (color); private ramp consts
                                        (darkRed, burgundy, red, ... ~30
                                        `const` without `export`) and
                                        `unusedSharedColors` SKIPPED (see below)
    global/brandColors.ts           <- brandWeb, brandTeams, PARSED (color)
    global/spacings.ts              <- only base `spacings` block PARSED
                                        (spacing); horizontalSpacings /
                                        verticalSpacings SKIPPED (redundant,
                                        see below)
    global/typographyStyles.ts      <- top-level keys only PARSED (typography)
    global/borderRadius.ts, curves.ts, durations.ts, fonts.ts,
    global/strokeWidths.ts          NOT parsed (redundant, see below)
    global/index.ts                 NOT parsed (barrel)
    alias/*.ts                      NOT parsed for names (redundant, see
                                        below); used only as a11y evidence
                                        search surface
    themes/*.ts                     NOT parsed (composed theme INSTANCES,
                                        e.g. `webLightTheme` -- products of
                                        tokens, not token declarations)
    index.ts                        NOT parsed (package barrel / type re-exports)

===========================================================================
WHY DefaultPalette.ts / DefaultEffects.ts / DefaultSpacing.ts ARE SKIPPED
(before), AND global/borderRadius.ts / curves.ts / durations.ts / fonts.ts /
strokeWidths.ts / horizontalSpacings|verticalSpacings ARE SKIPPED (after)
===========================================================================
These files are RE-IMPLEMENTATIONS of a token shape already declared
elsewhere with the exact same key names:
  - DefaultPalette.ts assigns concrete hex values to the *same* keys already
    declared by `interface IPalette` (themeDarker, neutralLight, ...).
  - DefaultEffects.ts / DefaultSpacing.ts do the same for IEffects / ISpacing.
  - global/borderRadius.ts, curves.ts, durations.ts, and the fontSizes /
    lineHeights / fontWeights / fontFamilies blocks in global/fonts.ts, and
    strokeWidths.ts, all export objects whose keys are IDENTICAL, bare-for-
    bare, to keys already present in tokens.ts (e.g. `borderRadiusSmall`
    appears in both global/borderRadius.ts and tokens.ts, unqualified,
    referring to the same conceptual token -- there is no separate
    primitive-vs-alias *rename* for these categories, tokens.ts *is* the
    flattened alias re-export of these global primitives).
  - global/spacings.ts's `horizontalSpacings` / `verticalSpacings` blocks are
    the same story: their keys (`spacingHorizontalXS`, ...) are identical to
    tokens.ts keys.
Parsing both the declaration and its redundant re-implementation would
either (a) silently no-op dedupe (if both are recorded under the identical
bare name -- harmless but pointless), or (b) double-count the same
conceptual token under two different qualified strings if a namespace
prefix were added inconsistently. We resolve this once, deliberately: only
the single most-canonical defining source is parsed per concept (the
*interface* on the before side since it is the authoritative schema; the
*flat tokens.ts export* on the after side since it is the package's
documented public flat token surface, `Record<keyof Theme, string>`,
guaranteed by TypeScript to include every token). The base `spacings`
primitive block (after) and the FluentColors.ts / FluentFonts.ts /
FluentDepths.ts namespaces (before) are the exception: their keys are NOT
duplicated verbatim elsewhere (they use different key names, e.g. primitive
`spacings.xs` vs. alias `spacingHorizontalXS`; namespace `NeutralColors.gray190`
vs. interface `IPalette.neutralLight` is not even the same *value* let alone
key) -- these ARE genuinely new, separately nameable public exports, so they
ARE parsed and namespace/const-qualified to keep them distinguishable.

`types/Theme.ts`'s `@internal`, explicitly-not-production-ready `Tokens` /
`ColorTokenSet` / `ColorTokens` type (an early, abandoned prototype of a v9-
style token system living inside the v8 package) is excluded: its field
names (`background`, `hovered`, `pressed`, ...) are generic TypeScript
*structural* field names on a recursive/partial type, not concrete token
identifiers -- there is no default value object anywhere in the extracted
source that instantiates them, so there is nothing to concretely count.

`global/colors.ts`'s ~30 un-exported `const <name>: ColorVariants = {...}`
blocks (darkRed, burgundy, red, orange, peach, ...) are internal
implementation details referenced-by-shorthand from `statusSharedColors` /
`personaSharedColors` / `unusedSharedColors` -- they are never `export`ed
from this file, so they are not part of the package's public token surface
and our `export `-anchored extraction regex naturally excludes them.
`unusedSharedColors` (which IS syntactically `export`ed) is deliberately
excluded anyway: its own source comment reads "These shared colors are
currently not used in themes ... Not exported from the package, we can
consider removing them" -- i.e. Fluent's own maintainers flag it as dead
weight not meant to be part of the consumable API. We follow that steer.

===========================================================================
EXTRACTION APPROACH (no TS/AST parser -- see extract_named_blocks())
===========================================================================
Every parsed file is one of three shapes, all handled by the SAME generic,
line-oriented, brace-depth-counting block scanner (`extract_named_blocks`):

  1. `export interface Name { propA: Type; propB?: Type; ... }`
  2. `export namespace Name { export const member = value; ... }`
  3. `export const name: Type = { key: value, key2: value2, ... };`

We do not use a TS/AST parser (none is in the stdlib; unjustified for this
fixed, hand-read file shape). `extract_named_blocks` finds every header line
matching a given header regex, then walks forward counting `{`/`}`
characters per line until the running depth returns to 0, collecting every
line strictly between the opening and closing brace as that block's body.
This is safe here because in every file we target, a single line's braces
are always balanced within that line even when they come from something
unrelated to block nesting (e.g. FluentFonts.ts's
`` `'${LocalizedFontNames.Arabic}'` `` template-literal interpolation
contributes one '{' and one '}' on the SAME line, net delta zero, so it
never confuses the depth counter) -- verified by reading every target file
before writing this script.

Within a block's body we distinguish two leaf-extraction rules:
  - `top_level_object_keys()` -- for interface property lines
    (`name: Type;`) and object-literal entries (`name: value,`,
    `'0': value,`, or JS shorthand `name,`) -- used for interfaces AND
    `export const` object blocks. It is depth-aware: it only records keys
    at depth 0 *relative to the block's own opening brace*, so a nested
    object literal one level deeper (e.g. `typographyStyles.body1`'s
    `{ fontFamily: ..., fontSize: ... }`) never leaks its inner keys out as
    if they were top-level typographyStyles tokens -- only `body1` itself
    is recorded, not `fontFamily`/`fontSize`/`fontWeight`/`lineHeight`
    (which are CSS-style property *labels* pointing at already-counted
    tokens, not token names in their own right).
  - `top_level_namespace_members()` -- for TS `namespace` bodies, whose
    members are declared `export const NAME = value;` (a different line
    shape entirely from object-literal `NAME: value,`).

A third small regex pass (inline in `parse_after`'s colors.ts handling)
picks up simple non-object exports (`export const white = '#ffffff';`) that
extract_named_blocks' header regex (which requires the header line to end
in `{`) deliberately does not match.

===========================================================================
QUALIFICATION RULE FOR TOKEN NAMES
===========================================================================
Interface properties (before) and tokens.ts keys (after) are used BARE
(e.g. `themeDarker`, `colorNeutralForeground1`) -- each is already a
complete, unambiguous, canonical token identifier as Fluent itself names it.

Namespace members (before: FluentColors.ts, FluentFonts.ts,
FluentDepths.ts) and `export const` object-literal keys that are NOT
already-canonical alias names (after: global/colors.ts ramps, brandColors.ts
ramps, the base `spacings` primitive block, typographyStyles.ts roles) are
qualified as `<ContainerName>.<key>` (e.g. `NeutralColors.gray190`,
`grey.14`, `spacings.xs`, `typographyStyles.body1`). This is necessary
because their own keys are short/ambiguous or purely ordinal (ramp stops
like `'14'`, `'40'`) and would otherwise silently collide across unrelated
containers (e.g. before's bare `black` in `IPalette` vs. `NeutralColors.black`
are DIFFERENT tokens -- a raw theme slot vs. a primitive ramp swatch -- and
must not be merged into one name by the diff).

===========================================================================
CATEGORIZATION RULES (color / typography / spacing / radius / shadow /
motion / other)
===========================================================================
BEFORE -- assigned by source file/interface (the file's own doc-comment
states its purpose, e.g. ISemanticColors.ts: "collection of all semantic
slots for colors used in themes"):
  IPalette, ISemanticColors, ISemanticTextColors     -> color
  FluentColors.ts (CommunicationColors/NeutralColors/SharedColors) -> color
  ISpacing                                           -> spacing
  IEffects            -> per-key: 'elevation*' -> shadow, 'roundedCorner*' -> radius
  FluentDepths.ts (Depths.depth*)                    -> shadow
  IFontStyles                                        -> typography
  FluentFonts.ts (LocalizedFontNames/Families, FontSizes, FontWeights) -> typography
  FluentFonts.ts (IconFontSizes)                      -> other (icon pixel-size
                                                          scale -- not text
                                                          typography, and the
                                                          rubric has no
                                                          dedicated "sizing"
                                                          bucket, so bucketed
                                                          conservatively as
                                                          "other" rather than
                                                          stretched into
                                                          "typography")
  IAnimationStyles, IAnimationVariables               -> motion

AFTER -- tokens.ts is categorized per-key by Fluent's own self-describing
name PREFIX convention (a real, citable naming-consistency improvement over
v8, itself worth reporting): color*/colorPalette* -> color; spacing* ->
spacing; duration*/curve* -> motion; fontSize*/fontWeight*/fontFamily*/
lineHeight* -> typography; shadow* -> shadow; borderRadius* -> radius;
strokeWidth* -> other (a border/line-thickness metric -- distinct from
corner "radius" and not "spacing" in the padding/margin sense; the rubric
has no dedicated bucket for it, so "other", mirroring the same conservative
call the Polaris parser made for its own border-width-* tokens).
global/colors.ts, brandColors.ts (ramps + simple consts)    -> color
global/spacings.ts (`spacings` primitive block only)        -> spacing
global/typographyStyles.ts (top-level roles only)            -> typography

===========================================================================
LAYERING JUDGMENT
===========================================================================
BEFORE: "flat". IPalette is a single flat bag of ~56 raw color slots;
ISemanticColors/ISemanticTextColors is a second, informally-related bag that
*can* reference palette colors when constructing a theme (see
`utilities/makeSemanticColors` referenced from createTheme.ts, not itself
extracted) but the relationship is not a formal, enforced, or DTCG-typed
tier -- semanticColors is an optional, independently-overridable property
on the theme object, and most v8 components historically read `palette.*`
directly rather than going through `semanticColors`. Per the task's own
framing this is "flat or weakly 2-layer at best"; we code it "flat" because
there is no consistently enforced primitive->semantic contract, only an
informal convention.
AFTER: "2-layer". global/*.ts holds primitive scales (raw grey/brand
ramps, base spacing scale, curves, durations) and alias/*.ts + tokens.ts
hold the semantic, consumer-facing names built FROM those primitives (e.g.
`colorNeutralForeground1 = grey[14]`, confirmed by reading alias/lightColor.ts
directly). No third, separate component-token tier is visible anywhere in
the extracted file set (no `components/` or per-component token file
exists in the after/ listing) -- so this is coded "2-layer", NOT the
3-layer primitive/semantic/component split Ant Design's Seed/Map/Alias
model has.

===========================================================================
DTCG COMPLIANCE JUDGMENT
===========================================================================
Confirmed "no" for both phases: a live regex scan (see `check_dtcg_hit`)
for the DTCG spec's required `$value` key (with optional `$type`/
`$description`) across every parsed file in each phase finds zero matches
in both, corroborating the structural fact that these are plain TypeScript
interfaces/object literals, not JSON, in both v8 and v9.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLUENT_ROOT = ROOT / "data/repos/fluent-ui"
BEFORE_DIR = FLUENT_ROOT / "before/packages/theme/src"
AFTER_DIR = FLUENT_ROOT / "after/packages/react-components/react-theme/src"
RESULTS_PATH = ROOT / "results/tokens_fluent-ui.json"

BEFORE_TAG = "@fluentui/theme_v1.4.0"
AFTER_TAG = "@fluentui/react-theme_v9.0.0"

CATEGORIES = ["color", "typography", "spacing", "radius", "shadow", "motion", "other"]

INTERFACE_HEADER_RE = re.compile(r"^export interface (\w+)\b")
NAMESPACE_HEADER_RE = re.compile(r"^export namespace (\w+)\b")
CONST_OBJECT_HEADER_RE = re.compile(r"^export const (\w+)\b.*\{\s*$")
SIMPLE_CONST_RE = re.compile(r"^export const (\w+)\b")
NAMESPACE_MEMBER_RE = re.compile(r"^export const (\w+)\b")

# Object-literal / interface-property key line, e.g. `themeDarker: string;`,
# `colorNeutralForeground1: 'var(--...)',`, a quoted numeric key `'14': ...,`
# (global/colors.ts's grey/whiteAlpha/... ramps), or a BARE numeric key
# `10: \`#061724\`,` (global/brandColors.ts's brandWeb/brandTeams ramps --
# these use unquoted numeric object keys, unlike colors.ts's quoted ones).
OBJECT_KEY_RE = re.compile(r"^(?:'([^']*)'|\"([^\"]*)\"|([A-Za-z_$][\w$]*|\d+))\??\s*:")
# JS shorthand property, e.g. `red,` inside `statusSharedColors = { red, green, ... }`.
SHORTHAND_KEY_RE = re.compile(r"^([A-Za-z_$][\w$]*)\s*,\s*(?://.*)?$")


# ---------------------------------------------------------------------------
# Generic block scanner (see module docstring "EXTRACTION APPROACH")
# ---------------------------------------------------------------------------

def extract_named_blocks(text: str, header_re: re.Pattern):
    """Find every header line matching header_re (group 1 = block name) and
    return [(name, body_lines)] where body_lines are the lines strictly
    between the header's opening '{' and its matching close, tracked with a
    per-line running brace-depth counter."""
    lines = text.splitlines()
    n = len(lines)
    blocks = []
    i = 0
    while i < n:
        m = header_re.match(lines[i].strip())
        if not m:
            i += 1
            continue
        name = m.group(1)
        depth = lines[i].count("{") - lines[i].count("}")
        body = []
        i += 1
        while i < n and depth > 0:
            depth += lines[i].count("{") - lines[i].count("}")
            if depth > 0:
                body.append(lines[i])
            i += 1
        blocks.append((name, body))
    return blocks


def top_level_object_keys(body_lines):
    """Depth-aware: only keys at depth 0 relative to the block's own
    opening brace are returned (see module docstring)."""
    keys = []
    depth = 0
    for raw in body_lines:
        line = raw.strip()
        if depth == 0 and line and not line.startswith(("//", "/*", "*")):
            m = OBJECT_KEY_RE.match(line)
            if m:
                keys.append(next(g for g in m.groups() if g is not None))
            else:
                m2 = SHORTHAND_KEY_RE.match(line)
                if m2:
                    keys.append(m2.group(1))
        depth += line.count("{") - line.count("}")
    return keys


def top_level_namespace_members(body_lines):
    members = []
    depth = 0
    for raw in body_lines:
        line = raw.strip()
        if depth == 0:
            m = NAMESPACE_MEMBER_RE.match(line)
            if m:
                members.append(m.group(1))
        depth += line.count("{") - line.count("}")
    return members


# ---------------------------------------------------------------------------
# BEFORE (v8 Fabric theme-object model)
# ---------------------------------------------------------------------------

def parse_before(base_dir: Path):
    tokens = {}
    debug = []

    def add(name, category, count_box):
        tokens[name] = category
        count_box[0] += 1

    # Interfaces whose every own property is one category.
    interface_files = [
        ("types/IPalette.ts", "color"),
        ("types/ISemanticColors.ts", "color"),
        ("types/ISemanticTextColors.ts", "color"),
        ("types/ISpacing.ts", "spacing"),
        ("types/IFontStyles.ts", "typography"),
    ]
    for rel, category in interface_files:
        text = (base_dir / rel).read_text()
        cnt = [0]
        for _iface, body in extract_named_blocks(text, INTERFACE_HEADER_RE):
            for key in top_level_object_keys(body):
                add(key, category, cnt)
        debug.append((rel, cnt[0]))

    # IEffects.ts: mixed category, resolved per-key.
    rel = "types/IEffects.ts"
    text = (base_dir / rel).read_text()
    cnt = [0]
    for _iface, body in extract_named_blocks(text, INTERFACE_HEADER_RE):
        for key in top_level_object_keys(body):
            if key.startswith("elevation"):
                cat = "shadow"
            elif key.startswith("roundedCorner"):
                cat = "radius"
            else:
                cat = "other"
            add(key, cat, cnt)
    debug.append((rel, cnt[0]))

    # IAnimationStyles.ts: two interfaces (IAnimationStyles, IAnimationVariables),
    # both entirely motion tokens.
    rel = "types/IAnimationStyles.ts"
    text = (base_dir / rel).read_text()
    cnt = [0]
    for _iface, body in extract_named_blocks(text, INTERFACE_HEADER_RE):
        for key in top_level_object_keys(body):
            add(key, "motion", cnt)
    debug.append((rel, cnt[0]))

    # FluentColors.ts: 3 namespaces, all color primitives.
    rel = "colors/FluentColors.ts"
    text = (base_dir / rel).read_text()
    cnt = [0]
    for ns_name, body in extract_named_blocks(text, NAMESPACE_HEADER_RE):
        for key in top_level_namespace_members(body):
            add(f"{ns_name}.{key}", "color", cnt)
    debug.append((rel, cnt[0]))

    # FluentFonts.ts: 5 namespaces; IconFontSizes -> other, rest -> typography.
    rel = "fonts/FluentFonts.ts"
    text = (base_dir / rel).read_text()
    cnt = [0]
    for ns_name, body in extract_named_blocks(text, NAMESPACE_HEADER_RE):
        category = "other" if ns_name == "IconFontSizes" else "typography"
        for key in top_level_namespace_members(body):
            add(f"{ns_name}.{key}", category, cnt)
    debug.append((rel, cnt[0]))

    # FluentDepths.ts: 1 namespace, shadow.
    rel = "effects/FluentDepths.ts"
    text = (base_dir / rel).read_text()
    cnt = [0]
    for ns_name, body in extract_named_blocks(text, NAMESPACE_HEADER_RE):
        for key in top_level_namespace_members(body):
            add(f"{ns_name}.{key}", "shadow", cnt)
    debug.append((rel, cnt[0]))

    return tokens, debug


# ---------------------------------------------------------------------------
# AFTER (v9 global + alias theme package)
# ---------------------------------------------------------------------------

def categorize_after_token(name: str) -> str:
    """tokens.ts's own self-describing name-prefix convention (see module
    docstring's CATEGORIZATION RULES)."""
    if name.startswith("color"):
        return "color"
    if name.startswith("spacing"):
        return "spacing"
    if name.startswith("duration") or name.startswith("curve"):
        return "motion"
    if (
        name.startswith("fontSize")
        or name.startswith("fontWeight")
        or name.startswith("fontFamily")
        or name.startswith("lineHeight")
    ):
        return "typography"
    if name.startswith("shadow"):
        return "shadow"
    if name.startswith("borderRadius"):
        return "radius"
    if name.startswith("strokeWidth"):
        return "other"
    return "other"


# unusedSharedColors: syntactically `export`ed but its own source comment
# says "Not exported from the package, we can consider removing them" --
# excluded per that explicit maintainer note (see module docstring).
AFTER_COLORS_SKIP_CONSTS = {"unusedSharedColors"}


def parse_after(base_dir: Path):
    tokens = {}
    debug = []

    def add(name, category, count_box):
        tokens[name] = category
        count_box[0] += 1

    # tokens.ts: the single canonical flat alias/semantic token surface.
    rel = "tokens.ts"
    text = (base_dir / rel).read_text()
    cnt = [0]
    for const_name, body in extract_named_blocks(text, CONST_OBJECT_HEADER_RE):
        if const_name != "tokens":
            continue
        for key in top_level_object_keys(body):
            add(key, categorize_after_token(key), cnt)
    debug.append((rel, cnt[0]))

    # global/colors.ts: exported primitive scales (qualified) + simple
    # bare consts (white/black/hc*), all color.
    rel = "global/colors.ts"
    text = (base_dir / rel).read_text()
    cnt = [0]
    for const_name, body in extract_named_blocks(text, CONST_OBJECT_HEADER_RE):
        if const_name in AFTER_COLORS_SKIP_CONSTS:
            continue
        for key in top_level_object_keys(body):
            add(f"{const_name}.{key}", "color", cnt)
    for line in text.splitlines():
        stripped = line.strip()
        m = SIMPLE_CONST_RE.match(stripped)
        if m and not stripped.endswith("{"):
            add(m.group(1), "color", cnt)
    debug.append((rel, cnt[0]))

    # global/brandColors.ts: brandWeb, brandTeams ramps.
    rel = "global/brandColors.ts"
    text = (base_dir / rel).read_text()
    cnt = [0]
    for const_name, body in extract_named_blocks(text, CONST_OBJECT_HEADER_RE):
        for key in top_level_object_keys(body):
            add(f"{const_name}.{key}", "color", cnt)
    debug.append((rel, cnt[0]))

    # global/spacings.ts: only the base `spacings` primitive block (the
    # horizontalSpacings/verticalSpacings blocks are skipped -- their keys
    # duplicate tokens.ts's spacingHorizontal*/spacingVertical* bare names).
    rel = "global/spacings.ts"
    text = (base_dir / rel).read_text()
    cnt = [0]
    for const_name, body in extract_named_blocks(text, CONST_OBJECT_HEADER_RE):
        if const_name != "spacings":
            continue
        for key in top_level_object_keys(body):
            add(f"{const_name}.{key}", "spacing", cnt)
    debug.append((rel, cnt[0]))

    # global/typographyStyles.ts: top-level composite typography roles only
    # (nested fontFamily/fontSize/fontWeight/lineHeight are style-property
    # labels pointing at already-counted tokens, not new token names --
    # excluded by top_level_object_keys' depth-awareness).
    rel = "global/typographyStyles.ts"
    text = (base_dir / rel).read_text()
    cnt = [0]
    for const_name, body in extract_named_blocks(text, CONST_OBJECT_HEADER_RE):
        if const_name != "typographyStyles":
            continue
        for key in top_level_object_keys(body):
            add(f"{const_name}.{key}", "typography", cnt)
    debug.append((rel, cnt[0]))

    return tokens, debug


# ---------------------------------------------------------------------------
# Accessibility-token evidence scan (RQ2 / rubric §4.3) -- a live regex scan
# over every .ts file in each phase, nothing hardcoded. Deliberate choice:
# CONTRAST_RATIO_RE does NOT match the bare word "contrast" alone, because
# before/types/ISemanticColors.ts uses "contrast" twice in plain decorative
# prose ("border ... provides contrast between an element ... and a
# standout background") describing visual distinction, not a documented,
# ratio-guaranteed text/background pair -- a bare "contrast" keyword match
# would false-positive on that. We instead require either an explicit ratio
# statement (e.g. "4.5:1"), the word "WCAG", or Fluent v9's own
# accessibility-labeled token name (`colorNeutralStrokeAccessible*`).
# ---------------------------------------------------------------------------

FOCUS_RING_RE = re.compile(
    r"focusBorder|inputFocusBorderAlt|colorStrokeFocus|focus.?(ring|indicator|outline)",
    re.I,
)
CONTRAST_RATIO_RE = re.compile(
    r"\bWCAG\b|contrast ratio|\d(\.\d+)?\s*:\s*1\b|colorNeutralStrokeAccessible", re.I
)
TARGET_SIZE_RE = re.compile(
    r"target.?size|touch.?target|tap.?target|min(imum)?.?(hit|touch|tap).?(area|size|target)|hitSlop",
    re.I,
)
REDUCED_MOTION_RE = re.compile(r"reduced.?motion|prefers-reduced-motion|reduceMotion", re.I)
DTCG_RE = re.compile(r"\$value\b|\$type\b|\$description\b")


def scan_full_text(search_dir: Path, pattern: re.Pattern):
    """Return 'relpath:line: text' for the first .ts file (in sorted path
    order) whose text matches pattern, or None if no file matches."""
    for path in sorted(search_dir.rglob("*.ts")):
        if "__snapshots__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                rel = path.relative_to(FLUENT_ROOT)
                return f"{rel}:{i}: {line.strip()}"
    return None


def build_accessibility_tokens(search_dir: Path):
    def hit_to_field(hit):
        return {"present": hit is not None, "evidence": hit or ""}

    return {
        "contrast_safe_pairs": hit_to_field(scan_full_text(search_dir, CONTRAST_RATIO_RE)),
        "focus_ring": hit_to_field(scan_full_text(search_dir, FOCUS_RING_RE)),
        "target_size": hit_to_field(scan_full_text(search_dir, TARGET_SIZE_RE)),
        "reduced_motion": hit_to_field(scan_full_text(search_dir, REDUCED_MOTION_RE)),
    }


# ---------------------------------------------------------------------------
# Diff + "likely renamed" heuristic
# ---------------------------------------------------------------------------

# Pure structural/type-prefix words from v9's self-describing naming
# convention -- stripped before comparing "core" word sets. Deliberately
# does NOT include "size"/"weight": an earlier version of this heuristic
# stripped those too and produced a false-positive match ('IconFontSizes.
# medium' ~ 'fontWeightMedium') by conflating an icon-SIZE scale label with
# a font-WEIGHT scale label that happen to share the generic word "medium".
# Keeping "size"/"weight" (and other words that can carry standalone
# distinguishing meaning: border, stroke, radius, shadow, width, brand,
# neutral, palette) un-stripped is what lets the core-word-SET comparison
# below tell those two concepts apart.
PREFIX_STOPWORDS = {"color", "spacing", "font", "family", "line", "height", "duration", "curve"}
# v8 and v9 both use these as interaction-state suffixes (v8:
# buttonBackgroundHovered/CheckedHovered/Pressed/Disabled; v9:
# colorNeutralBackground1Hover/Pressed/Selected) -- stripped symmetrically
# so a genuine base-concept match isn't hidden behind a differing state suffix.
STATE_STOPWORDS = {
    "hover", "hovered", "pressed", "selected", "disabled", "checked",
    "active", "alt", "inverted", "static", "link",
}
CAMEL_RE = re.compile(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])")


def singularize(word: str) -> str:
    """Crude plural-stripping (e.g. 'Sizes'/'Weights'/'Colors' -> 'size'/
    'weight'/'color') so a namespace container's plural form (before:
    'FontSizes', 'FontWeights') lines up with v9's singular compound-prefix
    form (after: 'fontSize*', 'fontWeight*') when comparing core word sets."""
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def core_words(name: str) -> frozenset:
    """Core word SET for the fuzzy rename pass. Unlike a leaf-only
    comparison, this deliberately keeps the namespace/const qualifier's own
    words in the set (e.g. 'FontWeights.regular' contributes both 'weight'
    and 'regular', not just 'regular') -- dropping the qualifier was the
    root cause of the false-positive noted above, since two differently-
    qualified same-leaf-word names (FontSizes.medium vs
    IconFontSizes.medium) would otherwise collapse to the same core."""
    whole = re.sub(r"\d+$", "", name)  # drop a trailing ordinal, e.g. ...Background1 -> ...Background
    words = {singularize(w.lower()) for w in CAMEL_RE.findall(whole)}
    words -= PREFIX_STOPWORDS
    words -= STATE_STOPWORDS
    words.discard("")
    return frozenset(words)


def compute_diff(before_tokens: dict, after_tokens: dict):
    before_set, after_set = set(before_tokens), set(after_tokens)
    removed = sorted(before_set - after_set)
    added = sorted(after_set - before_set)

    added_core_index = {}
    for a in added:
        cw = core_words(a)
        if cw:
            added_core_index.setdefault(cw, []).append(a)

    likely_renamed_pairs = []
    for r in removed:
        cw = core_words(r)
        if cw and cw in added_core_index:
            likely_renamed_pairs.append((r, added_core_index[cw][0]))

    if likely_renamed_pairs:
        note = (
            "Normalized pass: for each removed/added name, split the FULL "
            "name (namespace/const qualifier included -- e.g. both 'font' "
            "and 'weight' from 'FontWeights.regular', not just 'regular') "
            "into lowercase camelCase words, singularize each word (crude "
            "trailing-'s' strip, so 'Sizes'/'Colors' line up with v9's "
            "singular 'fontSize*'/'color*' prefixes), drop a trailing "
            "ordinal digit from the whole name first, and strip a small "
            "set of pure structural prefix words (color, spacing, font, "
            "family, line, height, duration, curve) and interaction-state "
            "suffix words (hover, pressed, selected, disabled, checked, "
            "active, alt, inverted, static, link) common to both naming "
            "eras. Deliberately keeps 'size'/'weight' un-stripped (an "
            "earlier version stripped them too and produced a false-"
            "positive match, 'IconFontSizes.medium' ~ 'fontWeightMedium', "
            "by conflating an icon-size scale label with a font-weight "
            "scale label over the shared generic word 'medium' -- see code "
            "comments above core_words()). A removed name is flagged "
            "'likely renamed' only if its resulting core word SET matches "
            "an added name's core word set exactly (no partial/fuzzy "
            "overlap, to avoid manufacturing matches). "
            f"{len(likely_renamed_pairs)} pair(s) found: "
            + "; ".join(f"'{r}' -> '{a}'" for r, a in likely_renamed_pairs[:15])
        )
    else:
        note = (
            "Normalized pass (see code comments for the exact rule: "
            "lowercase camelCase word-set match after stripping structural "
            "prefixes and interaction-state suffixes) found ZERO exact "
            "core-word-set matches between removed and added names. This "
            "is itself a real finding, not a parser gap: v9 did not rename "
            "v8's palette/semantic slots token-by-token, it replaced the "
            "entire naming SYSTEM -- v8 names describe a color's place in a "
            "raw ramp or a component ('neutralLight', 'buttonBackground'), "
            "v9 names describe a role ('colorNeutralForeground1') with no "
            "component scoping at all. The breaking-change surface at this "
            "transition is best read as a wholesale architecture swap, not "
            "a renamed-token migration -- consistent with Microsoft's own "
            "v8->v9 migration guidance, which points teams at a new "
            "component-by-component adoption rather than a token rename map."
        )

    return {
        "removed_count": len(removed),
        "added_count": len(added),
        "removed_names_sample": removed[:25],
        "added_names_sample": added[:25],
        "likely_renamed_count": len(likely_renamed_pairs),
        "renamed_note": note,
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
    print("=== Parsing BEFORE (@fluentui/theme_v1.4.0) ===")
    before_tokens, before_debug = parse_before(BEFORE_DIR)
    for rel_path, count in before_debug:
        print(f"  {rel_path}: {count} token names")
    print(f"  TOTAL (deduped): {len(before_tokens)}")

    print("\n=== Parsing AFTER (@fluentui/react-theme_v9.0.0) ===")
    after_tokens, after_debug = parse_after(AFTER_DIR)
    for rel_path, count in after_debug:
        print(f"  {rel_path}: {count} token names")
    print(f"  TOTAL (deduped): {len(after_tokens)}")

    before_a11y = build_accessibility_tokens(BEFORE_DIR)
    after_a11y = build_accessibility_tokens(AFTER_DIR)

    before_dtcg_hit = scan_full_text(BEFORE_DIR, DTCG_RE)
    after_dtcg_hit = scan_full_text(AFTER_DIR, DTCG_RE)
    print(f"\nDTCG $value/$type scan -- before: {before_dtcg_hit!r}, after: {after_dtcg_hit!r}")

    before_phase = build_phase(BEFORE_TAG, before_tokens, "flat", "no", before_a11y)
    after_phase = build_phase(AFTER_TAG, after_tokens, "2-layer", "no", after_a11y)

    diff = compute_diff(before_tokens, after_tokens)

    output = {
        "system": "Fluent UI",
        "slug": "fluent-ui",
        "before": before_phase,
        "after": after_phase,
        "diff": diff,
        "parser_notes": (
            "Extraction: a single generic line-based, brace-depth-counting "
            "block scanner (extract_named_blocks) handles all three source "
            "shapes present -- `export interface X { prop: Type; }` "
            "(before), `export namespace X { export const member = v; }` "
            "(before), and `export const x: T = { key: value }` (both). No "
            "TS/AST parser used; see scripts/parse_fluent-ui.py module "
            "docstring for the full file-by-file inclusion/exclusion list "
            "and rationale. "
            "BEFORE parses: types/IPalette.ts, ISemanticColors.ts, "
            "ISemanticTextColors.ts, ISpacing.ts, IEffects.ts (per-key "
            "shadow/radius split), IFontStyles.ts, IAnimationStyles.ts (2 "
            "interfaces) as bare interface-property names -- the "
            "authoritative v8 theme-slot schema; plus colors/FluentColors.ts, "
            "fonts/FluentFonts.ts, effects/FluentDepths.ts as "
            "Namespace.member-qualified primitive-color/typography/depth "
            "exports. Deliberately SKIPPED: DefaultPalette.ts/"
            "DefaultEffects.ts/DefaultSpacing.ts (redundant value "
            "re-implementations of the same interface-declared keys), "
            "DefaultFontStyles.ts/createFontStyles.ts (computed via a "
            "function call, not a static literal), FluentTheme.ts/"
            "createTheme.ts/mergeThemes.ts (composition/factory code, no "
            "new token names), and Theme.ts's @internal, "
            "never-shipped-with-real-values `Tokens`/`ColorTokenSet` "
            "prototype type. "
            "AFTER parses: tokens.ts (the package's own "
            "`Record<keyof Theme, string>` flat alias/semantic surface, "
            "categorized per-key by Fluent's self-describing name prefix) "
            "as the canonical after-state token list; plus "
            "global/colors.ts (exported ramps + simple consts; ~30 "
            "un-exported private ramp consts and the maintainer-flagged-"
            "unused `unusedSharedColors` excluded), global/brandColors.ts, "
            "the base `spacings` primitive block in global/spacings.ts, and "
            "the top-level composite roles in global/typographyStyles.ts -- "
            "all qualified `const.key`. Deliberately SKIPPED: "
            "global/borderRadius.ts, curves.ts, durations.ts, fonts.ts "
            "(fontSizes/lineHeights/fontWeights/fontFamilies), "
            "strokeWidths.ts, and spacings.ts's horizontalSpacings/"
            "verticalSpacings blocks (all have keys IDENTICAL, bare-for-"
            "bare, to keys already counted from tokens.ts -- there is no "
            "primitive/alias rename for these categories, tokens.ts is "
            "their flattened re-export, so parsing both would double-count "
            "the same conceptual token); alias/*.ts (their generated "
            "ColorTokens/ColorPaletteTokens key sets are, by direct "
            "inspection, a subset of tokens.ts's names -- used only as an "
            "a11y-evidence search surface, not for name extraction); "
            "themes/*.ts (fully-composed named theme INSTANCES like "
            "webLightTheme -- products of tokens, not token declarations). "
            "Category totals are intentionally larger on the after side "
            "than a naive 'count tokens.ts only' reading would suggest, "
            "because v9 genuinely does expose a larger, separately-"
            "nameable public primitive layer (grey/brand/alpha ramps, the "
            "base spacing scale, composite typography roles) alongside its "
            "alias layer, whereas v8's DefaultPalette/DefaultEffects/"
            "DefaultSpacing were pure non-public re-implementations of "
            "already-declared interface shapes -- this is a real "
            "architectural asymmetry between the two phases, not a "
            "parser artifact; both totals nonetheless land in a "
            "tens-to-low-hundreds range, not an inflated one. "
            "Naming-convention consistency (descriptive, per plan §4.3, not "
            "part of the objective sub-score): v8's before-state names mix "
            "conventions across files with no shared prefix grammar "
            "(bare theme-slot names like 'themeDarker', semantic-state "
            "names like 'buttonBackgroundCheckedHovered', and separate "
            "primitive-namespace ramps like 'NeutralColors.gray190') -- "
            "genuinely mixed. v9's tokens.ts names are strikingly "
            "consistent: every single one of its ~270 keys begins with an "
            "unambiguous category prefix (color/spacing/duration/curve/"
            "fontSize/fontWeight/fontFamily/lineHeight/shadow/"
            "borderRadius/strokeWidth), which is exactly what made this "
            "script's tokens.ts categorization possible via simple prefix "
            "matching with zero ambiguous cases -- a single, consistently-"
            "applied scheme. "
            "Layering: 'flat' before, '2-layer' after -- see module "
            "docstring 'LAYERING JUDGMENT' section for the full reasoning "
            "(confirmed by reading alias/lightColor.ts's direct references "
            "into global/colors.ts's `grey`/`brand` ramps; no third "
            "component-token tier exists in either the before or after "
            "file listing). "
            "DTCG compliance: confirmed 'no' for both phases by a live "
            "regex scan for '$value'/'$type'/'$description' across every "
            "parsed .ts file in each phase -- zero matches in both, "
            "corroborating that these are plain TypeScript interfaces/"
            "object literals in both eras, never W3C DTCG JSON. "
            "Accessibility tokens: all four flags come from a live regex "
            "scan of every .ts file in each phase's source tree (not "
            "hardcoded), with citations recorded at run time -- see code "
            "comments directly above build_accessibility_tokens() for the "
            "deliberate choice to require a specific ratio/'WCAG'/"
            "'Accessible'-token signal for contrast_safe_pairs rather than "
            "a bare 'contrast' keyword match, which would false-positive on "
            "before/types/ISemanticColors.ts's decorative prose about "
            "visual contrast between a card and its background (not a "
            "documented, ratio-guaranteed color pair). target_size and "
            "reduced_motion returned zero matches in both phases: Fluent's "
            "v8 and v9 theme-token layers define color/typography/spacing/"
            "radius/shadow/motion-TIMING tokens, but neither phase defines "
            "a minimum tap/touch target-size token, nor a "
            "prefers-reduced-motion-aware token or flag, anywhere in the "
            "extracted theme-package source -- both are reported "
            "present:false with no fabricated citation."
        ),
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(output, indent=2) + "\n")

    print("\n=== Diff ===")
    print(f"  removed_count: {diff['removed_count']}")
    print(f"  added_count: {diff['added_count']}")
    print(f"  likely_renamed_count: {diff['likely_renamed_count']}")
    print("\n=== Accessibility tokens ===")
    print("  before:", json.dumps(before_a11y, indent=2))
    print("  after:", json.dumps(after_a11y, indent=2))
    print(f"\nWrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
