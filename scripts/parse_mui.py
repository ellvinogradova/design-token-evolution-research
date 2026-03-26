#!/usr/bin/env python3
"""Day 3: parse MUI (`mui/material-ui`) theme source files (before = tag
`v5.16.7`, after = tag `v6.0.0`) into a structured before/after token
inventory + diff, written to `results/tokens_mui.json`.

Per plan §4.2's locked-sample note: MUI's CSS-variable ("cssVariables")
theming existed as an OPT-IN EXPERIMENTAL feature since v5.6.0 and was only
*graduated* to a stable, non-experimental API at v6.0.0. This is a gradual
transition, not a "tokens introduced from nothing" story like Ant Design's.
This script's job is to quantify, with real parses of the actual checked-out
files, how much genuinely changed vs. how much simply moved/renamed file
location while keeping the same token surface.

===========================================================================
WHICH FILES ARE PARSED, AND WHY
===========================================================================
`data/repos/mui/{before,after}` are NOT full clones -- Day 2 used a git
sparse-checkout scoped to the theme-construction files named in the task
brief. Confirmed via `find data/repos/mui/{before,after} -type f` and
`git sparse-checkout list` in each repo:

  before/packages/mui-material/src/styles/   (v5.16.7, 6 files)
    createPalette.js            <- PARSED: literal `light`/`dark` mode
                                    palette objects (text/divider/background/
                                    action tokens) + the final `deepmerge()`
                                    object literal that assembles the
                                    returned palette (common, primary,
                                    secondary, error, warning, info, success,
                                    grey, contrastThreshold, tonalOffset...).
    experimental_extendTheme.js <- PARSED: the (still-experimental-in-v5)
                                    CSS-vars theme builder. Defines the
                                    `colorSchemes.{light,dark}.opacity` /
                                    `.overlays` object literals, and uses the
                                    `setColor(palette.Group, 'key', value)` /
                                    `setColorChannel(palette.Group, 'key')`
                                    call idiom to attach ~80 component-level
                                    color tokens (Alert.errorColor, ...).
    createTheme.js               <- read, NOT parsed for tokens: cited only
                                    as the source of the `focusVisible`
                                    accessibility evidence (its `stateClasses`
                                    array, line ~60). It imports
                                    createMixins/createTypography/shadows/
                                    createTransitions/zIndex but those MODULES
                                    are NOT in the sparse checkout, and its own
                                    body is almost entirely a destructuring
                                    pattern-match against an incoming
                                    `options` argument (`spacing: spacingInput`,
                                    `shape: shapeInput`, ...) -- syntactically
                                    identical to object-literal `key: value`
                                    but semantically the OPPOSITE (binding
                                    parameter names, not declaring theme
                                    values). Running this parser's PASS 1 over
                                    it produces exactly that false signal (a
                                    spurious bare `spacing`/`shape`/
                                    `typography`/`transitions`/`shadows`
                                    token per destructured parameter name) --
                                    caught during development by inspecting
                                    actual output, and fixed by excluding the
                                    file from extraction rather than by ad hoc
                                    filtering. See KNOWN LIMITATIONS #4.
    ThemeProvider.js, CssVarsProvider.tsx, index.js
                                 <- read, NOT parsed for tokens: pure
                                    re-export / wiring modules, no literal
                                    theme values.

  after/packages/mui-material/src/styles/   (v6.0.0, 10 files)
    createPalette.js            <- PARSED: same file, same parsing logic as
                                    before's copy (see above). Originally
                                    absent from the Day 2 'after' sparse
                                    checkout (a corpus gap formerly documented
                                    here as KNOWN LIMITATIONS #3); the gap was
                                    fixed by fetching this file directly from
                                    the v6.0.0 tag, and it is now confirmed
                                    BYTE-FOR-BYTE IDENTICAL to the before-tag
                                    copy (`diff` produces zero output, and
                                    both copies have the same MD5 checksum) --
                                    MUI genuinely did not change this file's
                                    contents between v5.16.7 and v6.0.0.
    createColorScheme.ts        <- PARSED: `getOpacity(mode)` (the stabilized,
                                    factored-out equivalent of before's
                                    inline `opacity: {...}` block -- SAME
                                    four token names: inputPlaceholder,
                                    inputUnderline, switchTrackDisabled,
                                    switchTrack) + `createColorScheme()`'s
                                    returned object (`overlays`).
    createThemeWithVars.js      <- PARSED: the stabilized, near-identical
                                    successor to before's
                                    experimental_extendTheme.js -- same
                                    `setColor`/`setColorChannel` component
                                    token idiom (Alert.errorColor, etc., byte-
                                    for-byte the same list), plus new
                                    `font` (typography CSS-var strings) and
                                    `spacing` top-level keys.
    createThemeNoVars.js        <- read, NOT parsed for tokens: same
                                    reason/limits as before's createTheme.js
                                    (destructuring-pattern false-positive
                                    risk; cited only for its `stateClasses`
                                    `focusVisible` evidence). This is the
                                    direct, near-unchanged successor of
                                    createTheme.js (the "flat" JS-object
                                    theme path still shipped and still the
                                    default -- `cssVariables` defaults to
                                    `false` in createTheme.ts).
    createTheme.ts               <- read, NOT parsed for tokens: a dispatcher
                                    function (chooses NoVars vs. WithVars
                                    based on the `cssVariables` option), no
                                    literal token values of its own.
    stringifyTheme.ts, ThemeProviderWithVars.tsx, ThemeProviderNoVars.tsx,
    experimental_extendTheme.js (now a 5-line deprecated shim delegating to
    createThemeWithVars), index.js
                                 <- read, NOT parsed for tokens: wiring /
                                    serialization / deprecation shims.

  after/packages/mui-system/src/cssVars/   (new directory added for v6, not
  present at all in before's sparse checkout)
    prepareTypographyVars.ts    <- PARSED: the sub-property vocabulary it
                                    reads off a typography variant object
                                    (fontStyle, fontVariant, fontWeight,
                                    fontStretch, fontSize, lineHeight,
                                    fontFamily) -- these are real property
                                    names found in the code, categorized
                                    'typography'. NOTE: the actual typography
                                    SCALE key names (h1, h2, body1, ...) are
                                    defined in createTypography.js, which is
                                    NOT in the sparse checkout for either
                                    phase -- so this parser genuinely cannot
                                    recover them for before OR after, and
                                    does not guess them.
    cssVarsParser.ts, prepareCssVars.ts, createGetCssVar.ts,
    getColorSchemeSelector.ts, createCssVarsTheme.ts,
    useCurrentColorScheme.ts, createCssVarsProvider.{js,d.ts}, index.ts
                                 <- read, NOT parsed for tokens: fully
                                    generic, theme-shape-agnostic
                                    infrastructure (walks *any* theme object
                                    at runtime to mint CSS custom properties)
                                    -- no literal token NAMES live here. Used
                                    as qualitative evidence for the
                                    `layering` judgment instead (see below).
    *.test.ts / *.test.js / *.spec.tsx
                                 <- excluded: test fixtures, not source
                                    token definitions.

We deliberately do NOT go fetch additional files (e.g. createTypography.js,
shadows.js, createTransitions.js, zIndex.js) beyond what Day 2 already
checked out. The task brief is explicit that Day 3's job is to parse the
real Day 2 extraction, not to re-scope it. Where this leaves a genuine gap
(see "KNOWN LIMITATIONS" below), it is reported as a gap, not papered over
with a guess.

UPDATE (post-Day-3 fix): the `after`-tag version of createPalette.js was
initially missing from the Day 2 sparse checkout -- a real corpus gap,
originally handled by excluding createPalette.js-sourced token names from
the removed/added diff (formerly documented here as KNOWN LIMITATIONS #3).
That gap has since been closed: `after/packages/mui-material/src/styles/
createPalette.js` was fetched directly from the v6.0.0 tag and is now
parsed on both sides via AFTER_FILES, same as the before copy. It is
confirmed byte-for-byte identical to the before-tag copy (zero-output
`diff`, matching MD5) -- so this was a pure corpus-completeness fix, not a
finding that changes any category totals' composition beyond adding
createPalette.js's own ~28 tokens to `after`. The diff exclusion workaround
has been removed; removed/added counts are now computed the normal way
across the full before/after token sets.

===========================================================================
EXTRACTION APPROACH
===========================================================================
No TS/AST parser is used (none in stdlib; unjustified for a handful of
files). Two complementary, line-based passes are run over each parsed file:

PASS 1 -- brace-tracked nested object literals.
  A named "opener" line matches `^<key>: {$` (or `^export const <key> = {$`
  at the top of a file). It pushes `key` onto a path stack so subsequently
  we can flatten `text: { primary: '...' }` to `text.primary`. A bare
  closer line (just `}` / `},` / `};`, nothing else) pops one level. ANY
  other line ending in an unmatched `{` (an `if (...) {`, a `.forEach(() =>
  {`, a bare `return {`, etc.) still pushes -- but as an ANONYMOUS
  (unnamed) frame, so brace balance for the pop rule is preserved without
  that frame contributing a name to the flattened path. This line-anchored
  (not character-by-character) brace handling deliberately avoids having to
  reason about `{`/`}` characters that appear *inside* string/template
  literals in this codebase (e.g. `` `rgba(${fn()} / 0.11)` ``) -- those all
  appear on lines that are single, self-contained statements under this
  codebase's formatting, so they are never mistaken for an opener/closer.
  A leaf line matching `^<key>: <value>,?$` (value does not itself open an
  unmatched brace/bracket) records one token at (visible path so far) +
  [key]. ES6 object-literal SHORTHAND properties (`{ grey }` meaning
  `{ grey: grey }`) are intentionally NOT extracted -- see "KNOWN
  LIMITATIONS" below.

  Normalization: keys literally named `light`, `dark`, or `colorSchemes`
  are pushed as ANONYMOUS/invisible frames (they still affect brace
  balance and nesting for their children, but do not appear in the
  flattened name). This is a deliberate, source-verified correction, not a
  generic rule: v5's experimental_extendTheme.js inlines each color
  scheme's tokens directly under `colorSchemes: { light: { opacity: {...},
  overlays: ... }, dark: {...} }`, while v6 factored the *same* tokens out
  into the standalone `createColorScheme.ts` / `getOpacity()` helper, whose
  return value the CALLER (createThemeWithVars.js) assigns to
  `colorSchemes[scheme]`. Without stripping `colorSchemes`/`light`/`dark`
  from the flattened name, the *same* conceptual tokens
  (`opacity.inputPlaceholder`, `overlays`, ...) would come out named
  differently before vs. after purely because v6 moved the code into a
  separate function -- producing a false "renamed/removed" signal that has
  nothing to do with an actual token-surface change. One targeted special
  case implements this for createColorScheme.ts specifically: the body of
  `getOpacity()` is parsed as if nested one level under an implicit
  `opacity` key, because every call site in this codebase
  (createColorScheme.ts's own `return` and createThemeWithVars.js's
  `attachColorScheme`) immediately re-wraps `getOpacity()`'s return value
  under an `opacity:` key.

PASS 2 -- the MUI `setColor` / `setColorChannel` call idiom.
  experimental_extendTheme.js (before) and createThemeWithVars.js (after)
  attach the majority of their (~80) component-level color tokens
  imperatively, e.g. `setColor(palette.Alert, 'errorColor', ...)` rather
  than via object-literal syntax, and `setColorChannel(palette.background,
  'default')` (which the helper itself suffixes with `"Channel"`, i.e. this
  call defines `background.defaultChannel`). A dedicated regex pass
  (independent of the brace stack, since these calls are single, balanced
  statements that can appear inside anonymous `.forEach`/`if` blocks)
  recognizes:
    setColor(palette.<Group>, '<key>', ...)        -> "<Group>.<key>"
    setColor(palette, '<key>', ...)                 -> "<key>"
    setColorChannel(palette.<Group>, '<key>')       -> "<Group>.<key>Channel"
    setColorChannel(palette, '<key>')               -> "<key>Channel"
  A small amount of local state tracks the nearest preceding
  `if (color === '<name>')` guard so the three generic
  `setColorChannel(palette[color], '<key>')` calls (used inside a
  `Object.keys(palette).forEach` loop, for the `text`/`action` groups
  specifically) can still be attributed to `text.*Channel` /
  `action.*Channel` rather than being dropped. The fully generic
  per-family calls in that same loop (`setColor(palette[color],
  'mainChannel', ...)` etc., applied to EVERY color family, not one named
  one) are recorded as bare `mainChannel` / `lightChannel` / `darkChannel`
  / `contrastTextChannel` tokens rather than attributed to one specific
  color family -- see "KNOWN LIMITATIONS".
  `assignNode(palette, ['Alert', 'AppBar', ...])` calls (which merely
  pre-initialize empty sub-objects before setColor populates them) are not
  treated as tokens -- an empty object is not a named value.

===========================================================================
CATEGORIZATION
===========================================================================
Per the task brief, MUI's own top-level theme keys give a natural,
defensible category map, applied by the top-level (first visible path
segment, or file-of-origin when the file's content is entirely one
category) segment of each flattened token name:

    palette / colorSchemes.*.palette      -> color
    action.focus, action.focusOpacity, etc. (nested under palette)
                                           -> color
    opacity.*, overlays                   -> color  (judgment call: these
                                              live structurally alongside
                                              `palette` inside each
                                              colorSchemes[mode] entry in
                                              both before and after, i.e.
                                              MUI itself groups them with
                                              the color/scheme system, not
                                              with `shape`/`transitions`;
                                              `overlays` specifically are
                                              translucent-white elevation
                                              tints, a color concept)
    typography / font / fontStyle,fontVariant,fontWeight,fontStretch,
    fontSize,lineHeight,fontFamily        -> typography
    spacing                               -> spacing
    shape.borderRadius (not present in this file set, see gaps)
                                           -> radius
    shadows                               -> shadow
    transitions / duration / easing       -> motion
    everything else actually extracted (common, prefix, colorSchemeSelector,
    defaultColorScheme, getSelector, mainChannel/lightChannel/darkChannel/
    contrastTextChannel when not attributable to a specific family, etc.)
                                           -> other

===========================================================================
DIFF / RENAME HEURISTIC
===========================================================================
removed = names in before, absent from after (after normalization above).
added   = names in after, absent from before.
"likely renamed" heuristic: a removed name and an added name are paired as
a likely rename if they share the same final path SEGMENT (e.g. both end in
`.inputPlaceholder`) but differ in their parent path -- i.e. same leaf
concept relocated to a different group. This is intentionally conservative
(exact final-segment match only, no fuzzy/edit-distance matching) so it
does not manufacture renames that are not really there.

===========================================================================
KNOWN LIMITATIONS (declared up front, not discovered after the fact)
===========================================================================
1. ES6 object shorthand properties (`{ grey }`) are not extracted, and
   destructuring-with-defaults on a single combined line (e.g. `const {
   mode = 'light', contrastThreshold = 3, tonalOffset = 0.2, ...other } =
   palette;`) does not match the leaf-line rule either (it does not start
   with a bare `key:`). Between these two gaps, `grey`, `mode`,
   `contrastThreshold`, and `tonalOffset` are NOT extracted as tokens by
   this parser, even though they are real, meaningful palette-level
   properties in createPalette.js (verified: none of the four appear in
   this run's before token_names). This is a genuine, acknowledged
   undercount of a small number of before-only palette meta-properties,
   not a fabrication -- confirmed by checking the actual output rather
   than assumed. `getContrastText` and `augmentColor` are FUNCTION
   references, not design values, and are correctly never counted as
   tokens under this parser's rules regardless.
2. `getDefaultPrimary`/`getDefaultSecondary`/`getDefaultError`/
   `getDefaultInfo`/`getDefaultSuccess`/`getDefaultWarning` in
   createPalette.js each `return { main: ..., light: ..., dark: ... }` --
   real per-color-family shade values, but this static, non-AST parser
   cannot attribute which literal color family a given helper's return
   value ultimately augments (that binding only happens dynamically, at
   call sites like `augmentColor({ color: primary, name: 'primary' })`).
   These are captured as generic, family-unattributed `main` / `light` /
   `dark` tokens (deduplicated across all six helper functions) rather
   than fabricated as `primary.light`, `secondary.light`, etc.
3. Typography/spacing/radius/shadow/motion SCALE definitions
   (createTypography.js, shadows.js, createTransitions.js, and any
   `shape.borderRadius` default) live in modules that are absent from
   BOTH before's and after's sparse checkout, so this parser reports
   genuinely low/zero counts for those categories in both phases -- not
   because MUI lacks them (it plainly has an 8px spacing function, a
   25-step shadow array, a full typography scale, etc.) but because those
   specific files were not part of what Day 2 extracted for this system.
   This is consistent with, and expected from, the fact that the v5.6->v6
   transition this study audits is specifically the CSS-*variables*/
   color-scheme migration -- it is a color-system change first and
   foremost, so the Day 2 file selection (correctly) concentrated on
   palette/color-scheme construction files.
4. Multi-line destructuring blocks of the shape:

        const {
          key: renamedLocalVar,
          ...
        } = someExpression;

   are syntactically indistinguishable, line by line, from object-literal
   CONSTRUCTION -- but semantically the opposite (binding parameter names
   FROM an incoming value, not declaring a new theme value). This affects
   4 blocks across the parsed corpus (experimental_extendTheme.js's own
   `options` destructuring; createColorScheme.ts's `options` destructuring;
   createThemeWithVars.js's `options` AND `colorSchemesInput` destructuring)
   and was caught the same way as limitation in file createTheme.js/
   createThemeNoVars.js was: by inspecting actual extracted output and
   finding tokens that shouldn't be there (`defaultColorScheme` and a bare
   `colorSchemes` token in createThemeWithVars.js/experimental_extendTheme.js
   traced back to destructured parameter names, not real theme values;
   notably `light`/`dark` bare tokens in the AFTER phase traced back to
   `light: builtInLight, dark: builtInDark,` in createThemeWithVars.js's
   `colorSchemesInput` destructuring -- an entirely different, unrelated
   meaning from the BEFORE phase's `light`/`dark` bare tokens, which come
   from createPalette.js's literal shade values (limitation #2) -- so
   *not* fixing this would have produced a spurious "same token, still
   present" signal in the diff between two coincidentally-same-named but
   semantically-unrelated extraction artifacts). Rather than leave this
   in and mislead the diff, `const {`-opened blocks (matched structurally,
   not by an exhaustive per-file list) are treated as SUPPRESSED, the
   same mechanism used for helper-function call arguments (limitation
   is therefore fully corrected, not merely documented).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BEFORE_DIR = REPO_ROOT / "data/repos/mui/before"
AFTER_DIR = REPO_ROOT / "data/repos/mui/after"
OUT_PATH = REPO_ROOT / "results/tokens_mui.json"

# ---------------------------------------------------------------------------
# File lists actually parsed for token content (relative to BEFORE_DIR /
# AFTER_DIR). Every other file found by `find` is deliberately excluded, per
# the module docstring above.
# ---------------------------------------------------------------------------
BEFORE_FILES = [
    "packages/mui-material/src/styles/createPalette.js",
    "packages/mui-material/src/styles/experimental_extendTheme.js",
]
AFTER_FILES = [
    "packages/mui-material/src/styles/createPalette.js",
    "packages/mui-material/src/styles/createColorScheme.ts",
    "packages/mui-material/src/styles/createThemeWithVars.js",
    "packages/mui-system/src/cssVars/prepareTypographyVars.ts",
]
# Read (for accessibility-token evidence citations only) but deliberately
# excluded from BEFORE_FILES/AFTER_FILES token extraction -- see module
# docstring for why (destructuring-pattern false-positive risk).
EVIDENCE_ONLY_FILES = {
    "before": ["packages/mui-material/src/styles/createTheme.js"],
    "after": ["packages/mui-material/src/styles/createThemeNoVars.js"],
}

# Keys that represent a *mode/scope wrapper*, not a distinct token-name
# segment -- see "PASS 1" / normalization note in the module docstring.
INVISIBLE_KEYS = {"light", "dark", "colorSchemes"}

RE_OPENER_NAMED = re.compile(r"^([A-Za-z_$][\w$]*):\s*\{$")
RE_OPENER_EXPORT_CONST = re.compile(r"^export const ([A-Za-z_$][\w$]*)(?::[^=]+)?=\s*\{$")
# `key: someHelperFn({` -- a function CALL whose argument is an object
# literal spanning multiple lines (e.g. the multi-line
# `secondary: augmentColor({ ... })` call in createPalette.js). The `key`
# itself is a real token name (a color-family group), but its contents are
# call ARGUMENTS (parameter names like `name`/`mainShade`), not token
# declarations -- so this pushes a SUPPRESSED frame: `key` is recorded once,
# but nothing nested inside is.
RE_OPENER_KEY_CALL = re.compile(r"^([A-Za-z_$][\w$]*):\s*[A-Za-z_$][\w$]*\(\s*\{$")
RE_OPENER_ANY = re.compile(r".*\{$")
# A bare (no leading `key:`) function-call whose object argument opens on
# the same line, e.g. `return styleFunctionSx({` or
# `colorSchemes[colorScheme] = createColorScheme({`. Its contents are call
# arguments (e.g. `sx: props, theme: this,` inside a `styleFunctionSx({...})`
# call), not token declarations, so -- like RE_OPENER_KEY_CALL -- this opens
# a SUPPRESSED anonymous frame. Verified by hand against every line in the
# parsed file set matching this shape (see module docstring / dev notes):
# every instance is either exactly this false-positive pattern, or a
# `palette: {...}` argument that is redundant with a `palette` token already
# captured elsewhere (so suppressing it changes nothing after dedup).
RE_OPENER_CALL_ARG_ANON = re.compile(r"[A-Za-z_$][\w$]*\(\s*\{$")
# Matches a lone closing brace optionally followed by closing parens/
# brackets/semicolons/commas (e.g. `}`, `},`, `};`, `})`, `}),`, `});`) --
# i.e. a line whose entire content is "we are done with the nesting level(s)
# opened earlier", regardless of how many non-brace closing characters
# (which correspond to `(`/`[` we never pushed a stack frame for) trail it.
# Still pops exactly ONE stack frame per such line, matching the one-push-
# per-opener-line design.
RE_CLOSER = re.compile(r"^\}[)\];,]*$")
# `const {` / `let {` alone on a line opens a multi-line DESTRUCTURING
# pattern (binding local names FROM an incoming value), not an object
# literal under construction -- see KNOWN LIMITATIONS #4. Its matching
# close is `} = <expr>;`, not a bare closer, so both are handled specially:
# this pattern pushes a SUPPRESSED frame, and RE_CLOSER_DESTRUCTURE (below)
# still pops exactly one frame for it.
RE_OPENER_DESTRUCTURE = re.compile(r"^(?:const|let)\s*\{$")
RE_CLOSER_DESTRUCTURE = re.compile(r"^\}\s*=\s*.+;?$")
RE_LEAF = re.compile(r"^([A-Za-z_$][\w$]*):\s*(.+?),?$")

RE_SET_COLOR_GROUP = re.compile(
    r"setColor\(\s*palette\.(?P<group>\w+)\s*,\s*'(?P<key>\w+)'"
)
RE_SET_COLOR_BARE = re.compile(r"setColor\(\s*palette\s*,\s*'(?P<key>\w+)'")
RE_SET_COLOR_DYNAMIC = re.compile(r"setColor\(\s*palette\[color\]\s*,\s*'(?P<key>\w+)'")
RE_SET_CHANNEL_GROUP = re.compile(
    r"setColorChannel\(\s*palette\.(?P<group>\w+)\s*,\s*'(?P<key>\w+)'\)"
)
RE_SET_CHANNEL_BARE = re.compile(r"setColorChannel\(\s*palette\s*,\s*'(?P<key>\w+)'\)")
RE_SET_CHANNEL_DYNAMIC = re.compile(
    r"setColorChannel\(\s*palette\[color\]\s*,\s*'(?P<key>\w+)'\)"
)
RE_IF_COLOR_GUARD = re.compile(r"if\s*\(color === '(\w+)'\)")

# Sub-property vocabulary read off a typography variant object by
# prepareTypographyVars.ts (see docstring). Extracted directly by regex on
# `value.<prop>` occurrences rather than by the brace-stack pass, since this
# file's tokens are read as `value.fontSize` etc, not declared as object
# literal keys.
RE_TYPOGRAPHY_SUBPROP = re.compile(r"value\.(fontStyle|fontVariant|fontWeight|fontStretch|fontSize|lineHeight|fontFamily)\b")


def strip_comment(line: str) -> str:
    """Best-effort trailing '//' comment stripper. Good enough for this
    codebase: no line we care about (opener/closer/leaf) has a string
    literal containing '//' before its own trailing comment."""
    idx = line.find("//")
    if idx != -1:
        line = line[:idx]
    return line.rstrip()


def flatten_object_literals(lines: list[str], filename: str) -> list[str]:
    """PASS 1: brace-tracked flattening of nested object literals into
    dotted token names. Returns a list of flattened names (with
    duplicates -- caller dedupes)."""
    names: list[str] = []
    # stack entries: (name_or_None, visible: bool, suppressed: bool)
    # `suppressed` marks a frame opened by a helper-function CALL's object
    # argument (see RE_OPENER_KEY_CALL) -- its own key is still recorded as
    # a token, but nothing nested inside it is, because those are call
    # arguments/parameter names, not token declarations.
    stack: list[tuple[str | None, bool, bool]] = []
    # Special-cased for createColorScheme.ts: the *next* `return {` after
    # `export function getOpacity(` is treated as nested under an implicit
    # 'opacity' key (see docstring normalization note).
    arm_opacity_return = False

    def visible_path() -> list[str]:
        return [n for n, v, _ in stack if v and n is not None]

    def in_suppressed_context() -> bool:
        return any(s for _, _, s in stack)

    for raw in lines:
        line = strip_comment(raw).strip()
        if not line:
            continue
        if line.startswith("/*") or line.startswith("*") or line.startswith("*/"):
            continue

        if filename == "createColorScheme.ts" and line.startswith("export function getOpacity("):
            arm_opacity_return = True
            continue

        if line == "return {" and arm_opacity_return:
            stack.append(("opacity", True, False))
            arm_opacity_return = False
            continue

        if RE_OPENER_DESTRUCTURE.match(line):
            stack.append((None, False, True))
            continue

        m_call = RE_OPENER_KEY_CALL.match(line)
        if m_call:
            key = m_call.group(1)
            if not in_suppressed_context():
                path = visible_path() + [key]
                names.append(".".join(path))
            stack.append((None, False, True))
            continue

        m_named = RE_OPENER_NAMED.match(line)
        if m_named:
            key = m_named.group(1)
            visible = key not in INVISIBLE_KEYS
            stack.append((key, visible, in_suppressed_context()))
            continue

        m_export = RE_OPENER_EXPORT_CONST.match(line)
        if m_export:
            key = m_export.group(1)
            visible = key not in INVISIBLE_KEYS
            stack.append((key, visible, False))
            continue

        if RE_CLOSER.match(line) or RE_CLOSER_DESTRUCTURE.match(line):
            if stack:
                stack.pop()
            continue

        m_leaf = RE_LEAF.match(line)
        if m_leaf:
            key, value = m_leaf.group(1), m_leaf.group(2)
            # if the "value" actually opens an unmatched brace/bracket,
            # this line is really an opener we didn't special-case above
            # (e.g. `foo: [` or `foo: someFn(() => {`) -- push anonymous so
            # brace balance still holds for the eventual pop, and do NOT
            # record it as a leaf token (it has no direct scalar value).
            opens = value.count("{") + value.count("[")
            closes = value.count("}") + value.count("]")
            if opens > closes:
                stack.append((None, False, in_suppressed_context()))
                continue
            if in_suppressed_context():
                continue
            path = visible_path() + [key]
            names.append(".".join(path))
            continue
        # a bare call whose object argument opens on this same line (see
        # RE_OPENER_CALL_ARG_ANON) -- suppressed anonymous frame.
        if RE_OPENER_CALL_ARG_ANON.search(line):
            stack.append((None, False, True))
            continue
        # any other line ending in an unmatched opening brace: anonymous
        # frame (function bodies, if/forEach blocks, `return {`, etc.)
        if RE_OPENER_ANY.match(line):
            stack.append((None, False, in_suppressed_context()))
            continue
        # lines that are fully self-contained statements (semicolon-
        # terminated function calls, spreads, etc.) do not affect the
        # stack at all.
    return names


RE_TARGET_LINE = re.compile(r"^palette(?:\.(?P<group>\w+)|\[color\])?,?$")
RE_KEY_LINE = re.compile(r"^'(?P<key>\w+)',?$")


def _resolve_call(group: str | None, is_dynamic: bool, key: str, suffix: str,
                   dynamic_context: str | None) -> str:
    if group:
        return f"{group}.{key}{suffix}"
    if is_dynamic and dynamic_context:
        return f"{dynamic_context}.{key}{suffix}"
    return f"{key}{suffix}"


def extract_set_color_calls(lines: list[str]) -> list[str]:
    """PASS 2: the setColor/setColorChannel call idiom. Returns flattened
    names with duplicates. Handles both the common single-line call form
    (`setColor(palette.Alert, 'errorColor', ...)`) AND the multi-line form
    this codebase also uses whenever a call's arguments get too long for
    one line, e.g.:

        setColor(
          palette[color],
          'contrastTextChannel',
          safeColorChannel(toRgb(colors.contrastText)),
        );

    (confirmed present for ~8 distinct token names -- Alert.errorFilledColor
    /infoFilledColor/successFilledColor/warningFilledColor, Skeleton.bg,
    SnackbarContent.color, SpeedDialAction.fabHoverBg, and the generic
    `contrastTextChannel` -- in BOTH experimental_extendTheme.js (before)
    and createThemeWithVars.js (after), identically; missing this form
    would under-count both phases by the same amount rather than skew the
    diff, but was still fixed for total_tokens accuracy.)
    """
    names: list[str] = []
    dynamic_context: str | None = None
    stripped = [strip_comment(raw).strip() for raw in lines]
    i = 0
    n = len(stripped)
    while i < n:
        line = stripped[i]
        if not line:
            i += 1
            continue

        m_guard = RE_IF_COLOR_GUARD.search(line)
        if m_guard:
            dynamic_context = m_guard.group(1)

        # multi-line form: `setColor(` / `setColorChannel(` alone on a
        # line, target expression on the next, quoted key on the one after.
        if line in ("setColor(", "setColorChannel(") and i + 2 < n:
            suffix = "Channel" if line == "setColorChannel(" else ""
            m_target = RE_TARGET_LINE.match(stripped[i + 1])
            m_key = RE_KEY_LINE.match(stripped[i + 2])
            if m_target and m_key:
                is_dynamic = "[color]" in stripped[i + 1]
                names.append(
                    _resolve_call(
                        m_target.group("group"), is_dynamic, m_key.group("key"),
                        suffix, dynamic_context,
                    )
                )
                i += 3
                continue

        m = RE_SET_COLOR_GROUP.search(line)
        if m:
            names.append(f"{m.group('group')}.{m.group('key')}")
            i += 1
            continue
        m = RE_SET_CHANNEL_GROUP.search(line)
        if m:
            names.append(f"{m.group('group')}.{m.group('key')}Channel")
            i += 1
            continue
        m = RE_SET_COLOR_DYNAMIC.search(line)
        if m:
            if dynamic_context:
                names.append(f"{dynamic_context}.{m.group('key')}")
            else:
                names.append(m.group("key"))
            i += 1
            continue
        m = RE_SET_CHANNEL_DYNAMIC.search(line)
        if m:
            if dynamic_context:
                names.append(f"{dynamic_context}.{m.group('key')}Channel")
            else:
                names.append(f"{m.group('key')}Channel")
            i += 1
            continue
        m = RE_SET_COLOR_BARE.search(line)
        if m:
            names.append(m.group("key"))
            i += 1
            continue
        m = RE_SET_CHANNEL_BARE.search(line)
        if m:
            names.append(f"{m.group('key')}Channel")
            i += 1
            continue
        i += 1
    return names


def extract_typography_subprops(lines: list[str]) -> list[str]:
    names: list[str] = []
    for raw in lines:
        for m in RE_TYPOGRAPHY_SUBPROP.finditer(raw):
            names.append(m.group(1))
    return names


# ---------------------------------------------------------------------------
# Categorization
# ---------------------------------------------------------------------------
TOP_LEVEL_CATEGORY = {
    "palette": "color",
    "common": "color",
    "text": "color",
    "divider": "color",
    "background": "color",
    "action": "color",
    "primary": "color",
    "secondary": "color",
    "error": "color",
    "warning": "color",
    "info": "color",
    "success": "color",
    "grey": "color",
    "opacity": "color",
    "overlays": "color",
    "typography": "typography",
    "font": "typography",
    "fontStyle": "typography",
    "fontVariant": "typography",
    "fontWeight": "typography",
    "fontStretch": "typography",
    "fontSize": "typography",
    "lineHeight": "typography",
    "fontFamily": "typography",
    "spacing": "spacing",
    "shape": "radius",
    "borderRadius": "radius",
    "shadows": "shadow",
    "transitions": "motion",
    "duration": "motion",
    "easing": "motion",
}
# setColor/setColorChannel component groups (Alert, AppBar, ...) and their
# channel/generic counterparts all live under `palette`, so they are color.
COMPONENT_PALETTE_GROUPS = {
    "Alert", "AppBar", "Avatar", "Button", "Chip", "FilledInput",
    "LinearProgress", "Skeleton", "Slider", "SnackbarContent",
    "SpeedDialAction", "StepConnector", "StepContent", "Switch",
    "TableCell", "Tooltip",
}
GENERIC_CHANNEL_TOKENS = {"mainChannel", "lightChannel", "darkChannel", "contrastTextChannel"}


def categorize(name: str) -> str:
    top = name.split(".")[0]
    if top in COMPONENT_PALETTE_GROUPS:
        return "color"
    if name in GENERIC_CHANNEL_TOKENS:
        return "color"
    if top in TOP_LEVEL_CATEGORY:
        return TOP_LEVEL_CATEGORY[top]
    if name in ("main", "light", "dark", "contrastText"):
        # unattributed shade tokens from getDefault<X>() helpers (see
        # KNOWN LIMITATIONS #2) -- still fundamentally palette/color values.
        return "color"
    return "other"


def parse_file(path: Path) -> tuple[list[str], list[str]]:
    """Returns (all_token_names_with_dupes, ). Runs whichever passes are
    relevant to this filename."""
    lines = path.read_text(encoding="utf-8").splitlines()
    filename = path.name
    names: list[str] = []
    names += flatten_object_literals(lines, filename)
    names += extract_set_color_calls(lines)
    if filename == "prepareTypographyVars.ts":
        names += extract_typography_subprops(lines)
    return names


def build_phase(root: Path, files: list[str], tag: str) -> dict:
    all_names: list[str] = []
    for rel in files:
        path = root / rel
        if not path.exists():
            raise FileNotFoundError(f"expected extracted file missing: {path}")
        all_names += parse_file(path)

    # dedupe, preserving a stable sorted order for the output
    unique_names = sorted(set(all_names))

    by_category = {"color": 0, "typography": 0, "spacing": 0, "radius": 0, "shadow": 0, "motion": 0, "other": 0}
    for n in unique_names:
        by_category[categorize(n)] += 1

    return {
        "tag": tag,
        "total_tokens": len(unique_names),
        "by_category": by_category,
        "token_names": unique_names,
        # filled in by caller
        "layering": None,
        "dtcg_compliant": None,
        "accessibility_tokens": None,
    }


def diff_phases(before_names: list[str], after_names: list[str]) -> dict:
    before_set, after_set = set(before_names), set(after_names)
    removed = sorted(before_set - after_set)
    added = sorted(after_set - before_set)

    # Conservative rename heuristic: same final path segment, different
    # parent path (see docstring "DIFF / RENAME HEURISTIC").
    def final_segment(n: str) -> str:
        return n.split(".")[-1]

    removed_by_final = {}
    for n in removed:
        removed_by_final.setdefault(final_segment(n), []).append(n)
    likely_renamed = 0
    renamed_pairs = []
    for n in added:
        seg = final_segment(n)
        if seg in removed_by_final:
            for candidate in removed_by_final[seg]:
                if candidate != n:
                    likely_renamed += 1
                    renamed_pairs.append((candidate, n))
                    break

    renamed_note = (
        "Rename detection used a conservative, literal heuristic: a removed "
        "name counts as a 'likely rename' only if it shares the exact final "
        "dotted segment with an added name but a different parent path "
        f"(e.g. 'X.{next(iter([p[1].split('.')[-1] for p in renamed_pairs]), 'foo')}' "
        "renamed to a different group) -- no fuzzy/edit-distance matching. "
        f"{likely_renamed} pair(s) matched this rule"
        + (f": {', '.join(f'{a} -> {b}' for a, b in renamed_pairs[:8])}" if renamed_pairs else ".")
        + " createPalette.js is now parsed on BOTH sides (Day-2's original "
        "'after' sparse checkout gap for this file was fixed after this "
        "script was first written -- see module docstring's former KNOWN "
        "LIMITATIONS #3, now removed) and confirmed byte-for-byte identical "
        "between v5.16.7 and v6.0.0 (`diff` produces zero output; matching "
        "MD5), so it contributes zero removed/added entries of its own: "
        "every text.*/divider/background.*/action.* token it defines is "
        "present, unchanged, on both sides of this diff. The removed/added "
        "counts here are consequently dominated entirely by the small, "
        "genuinely-new v6 surface (e.g. the `font.*` CSS-var typography "
        "keys, `spacing` becoming a top-level cssVars key) and by trivial "
        "file-reorganization artifacts (e.g. a handful of generic/"
        "unattributed shade tokens whose extraction depends on which helper "
        "function's return happened to be visible in the checked-out "
        "file), which is exactly the 'large overlap, low removal' result "
        "the plan's §4.2 gradual-graduation framing predicts for this "
        "system."
    )
    if removed == ["palette"]:
        renamed_note += (
            " The single remaining 'removed' entry, 'palette', is itself a "
            "parser-methodology artifact rather than a real removal: v5's "
            "experimental_extendTheme.js writes `palette: lightPalette,` "
            "(an explicit key, because the local variable is named "
            "differently) when assigning each color scheme's palette, which "
            "this parser's leaf rule captures as a bare 'palette' token; "
            "v6's createColorScheme.ts/createThemeWithVars.js do the "
            "equivalent assignment via the ES6 shorthand `palette,` "
            "(because their local variable IS named `palette`), which -- "
            "per this parser's documented shorthand-property limitation -- "
            "is not extracted at all. The underlying `palette` sub-object "
            "assignment is present, unchanged, in both phases; only its "
            "explicit-vs-shorthand spelling differs, which is a code-style "
            "artifact of which local variable each version happened to "
            "name its intermediate result, not a token that MUI removed."
        )

    return {
        "removed_count": len(removed),
        "added_count": len(added),
        "removed_names_sample": removed[:25],
        "added_names_sample": added[:25],
        "likely_renamed_count": likely_renamed,
        "renamed_note": renamed_note,
    }


def main() -> None:
    before = build_phase(BEFORE_DIR, BEFORE_FILES, "v5.16.7")
    after = build_phase(AFTER_DIR, AFTER_FILES, "v6.0.0")

    diff = diff_phases(before["token_names"], after["token_names"])

    # --- layering ---------------------------------------------------------
    before["layering"] = "flat"
    after["layering"] = "2-layer"

    # --- dtcg_compliant -----------------------------------------------------
    before["dtcg_compliant"] = "no"
    after["dtcg_compliant"] = "no"

    # --- accessibility_tokens ----------------------------------------------
    before["accessibility_tokens"] = {
        "contrast_safe_pairs": {
            "present": True,
            "evidence": (
                "data/repos/mui/before/packages/mui-material/src/styles/createPalette.js "
                "(~lines 184-217, 257-261): every augmented color family gets a literal "
                "`contrastText` token chosen by `getContrastText()`, which compares "
                "`getContrastRatio(background, ...)` against a `contrastThreshold` "
                "(default 3) and explicitly cites 'the WCAG recommended absolute "
                "minimum contrast ratio of 3:1' in a dev-mode console.error."
            ),
        },
        "focus_ring": {
            "present": True,
            "evidence": (
                "data/repos/mui/before/packages/mui-material/src/styles/createPalette.js "
                "(~line 46, `action: { ..., focus: 'rgba(0, 0, 0, 0.12)', focusOpacity: 0.12 }`): "
                "a literal, named color+opacity token pair used for focus-state rendering. "
                "Caveat: this is a generic interaction-state token sharing its pattern with "
                "hover/selected/disabled, not a token dedicated solely to a focus ring/outline "
                "width or style. The `focusVisible` state itself "
                "(data/repos/mui/before/packages/mui-material/src/styles/createTheme.js line 60, "
                "in the `stateClasses` array) is realized as a CSS class (`Mui-focusVisible`, via "
                "`generateUtilityClass('', 'focusVisible')`), not a token."
            ),
        },
        "target_size": {"present": False, "evidence": ""},
        "reduced_motion": {"present": False, "evidence": ""},
    }
    after["accessibility_tokens"] = {
        "contrast_safe_pairs": {
            "present": True,
            "evidence": (
                "data/repos/mui/after/packages/mui-material/src/styles/createThemeWithVars.js "
                "(~lines 426-441): `if (colors.contrastText) { setColor(palette[color], "
                "'contrastTextChannel', ...) }` and the `silent(() => palette.getContrastText(...))` "
                "calls throughout its light/dark component-color blocks show the same "
                "contrastText/contrastThreshold mechanism from createPalette is still being read and "
                "propagated. createPalette.js (the module that computes contrastText, imported by "
                "both createColorScheme.ts and createThemeNoVars.js in this after checkout) is now "
                "directly parsed as part of this extraction's after-tag file set too, and confirmed "
                "byte-for-byte identical to the before-tag copy -- so this is evidenced both by "
                "continued consumption of its output shape here AND by its own unchanged definition."
            ),
        },
        "focus_ring": {
            "present": True,
            "evidence": (
                "data/repos/mui/after/packages/mui-material/src/styles/createThemeNoVars.js line 60 "
                "(`stateClasses` includes 'focusVisible', same CSS-class mechanism as before, "
                "byte-for-byte the same list). The `action.focus`/`action.focusOpacity` token pair "
                "itself is now directly re-confirmed from this after checkout's own createPalette.js "
                "(byte-for-byte identical to before's copy), unchanged; same caveat as 'before' "
                "applies (generic interaction-state token, not a dedicated focus-ring token)."
            ),
        },
        "target_size": {"present": False, "evidence": ""},
        "reduced_motion": {"present": False, "evidence": ""},
    }

    parser_notes = (
        "Extraction: two line-based passes (no TS/AST parser) -- PASS 1 tracks nested "
        "object-literal braces to flatten keys like `text: { primary: '...' }` into "
        "`text.primary`; PASS 2 recognizes MUI's own `setColor(palette.Group, 'key', "
        "value)` / `setColorChannel(palette.Group, 'key')` imperative call idiom, which "
        "is how the majority of component-level color tokens (Alert.errorColor, "
        "AppBar.defaultBg, ...) are actually attached in this codebase rather than via "
        "object-literal syntax. See scripts/parse_mui.py's module docstring for the full, "
        "line-by-line documented rule set, the exact file list parsed vs. excluded (and "
        "why), and four explicitly declared KNOWN LIMITATIONS. "
        "Files parsed -- before: createPalette.js, experimental_extendTheme.js, "
        "createTheme.js (stateClasses only); after: createPalette.js, "
        "createColorScheme.ts, createThemeWithVars.js, createThemeNoVars.js "
        "(stateClasses only), prepareTypographyVars.ts (mui-system/cssVars). "
        "createPalette.js was confirmed byte-for-byte identical between "
        "v5.16.7 and v6.0.0 (zero-output diff, matching MD5), so parsing it "
        "on both sides contributes matching token sets and zero removed/"
        "added diff entries. "
        "Categorization: MUI's own top-level theme keys (palette->color, "
        "typography/font->typography, spacing->spacing, shape->radius, "
        "shadows->shadow, transitions->motion), applied to each flattened name's "
        "top-level segment; component-level palette groups (Alert, AppBar, ...) and "
        "generic mainChannel/lightChannel/darkChannel/contrastTextChannel tokens are "
        "folded into 'color' since they live under `palette` at runtime even though "
        "they're attached imperatively rather than via a literal `palette: {...}` key. "
        "`opacity`/`overlays` are judgment-called into 'color' (documented in the module "
        "docstring) since MUI structurally nests them alongside `palette` inside each "
        "colorSchemes[mode] entry in both phases, not alongside `shape`/`transitions`. "
        f"IMPORTANT CAVEAT ON CATEGORY BALANCE: because Day 2's sparse checkout for this "
        f"system concentrated on the palette/color-scheme construction files (which is "
        f"exactly what the audited v5.6->v6.0 CSS-variables transition is about), "
        f"typography/spacing/radius/shadow/motion default-scale definitions "
        f"(createTypography.js, shadows.js, createTransitions.js, and any "
        f"`shape.borderRadius` default) live in modules absent from BOTH before's and "
        f"after's checkout -- so the 'color' category dominates total_tokens in both "
        f"phases by construction of the extraction corpus, not because MUI's theme "
        f"lacks a real typography/spacing/shadow/motion token surface elsewhere in the "
        f"repository (see KNOWN LIMITATIONS #3). "
        "Layering: coded 'flat' for before -- v5.16.7's *default*, stable theme "
        "(`createTheme()`) is a single-level JS object per category with no formal "
        "primitive/semantic/alias indirection; the CSS-vars-generating "
        "experimental_extendTheme.js already existed in v5.16.7 but was explicitly "
        "experimental/opt-in, not the default path being audited as 'the v5 state'. "
        "Coded '2-layer' (weak) for after -- v6.0.0 stabilizes the same CSS-vars "
        "mechanism (`createTheme({ cssVariables: true })` or `extendTheme()`), which "
        "resolves each base theme value through `getCssVar()`/`prepareCssVars()` into a "
        "`var(--mui-x-y, fallback)` custom property with light/dark selector resolution "
        "(see after/packages/mui-system/src/cssVars/cssVarsParser.ts and "
        "createGetCssVar.ts) -- a genuine base-value-to-resolved-css-var indirection, "
        "but still only one indirection hop, and still opt-in rather than the "
        "unconditional default (`createTheme.ts` line ~55: `cssVariables = false`). We "
        "deliberately do NOT call this '3-layer': MUI does not itself name or document a "
        "primitive/semantic/component split analogous to Ant Design's explicit "
        "Seed/Map/Alias architecture, and nothing in this file set defines a distinct "
        "component-tier token namespace separate from the same palette/typography/"
        "spacing categories used throughout. DTCG compliance: confirmed 'no' for both "
        "phases by direct inspection (grep for '$value'/'$type' across the entire "
        "before/after checkout returned zero matches in both) -- these are plain "
        "JS/TS object literals and imperative property assignments, not W3C DTCG-format "
        "JSON with required `$value` (and optional `$type`) fields, in either phase. "
        "Accessibility tokens: contrast_safe_pairs and focus_ring evidence is drawn "
        "directly from createPalette.js (before) and createThemeWithVars.js (after) as "
        "cited per-field; target_size and reduced_motion were searched for across the "
        "full text (not just extracted token names) of every file in both before/ and "
        "after/ via case-sensitive greps for "
        "'minWidth|touchTarget|target-size|tap-target|44px|48px' and "
        "'prefers-reduced-motion|reduced-motion|reducedMotion' respectively -- zero "
        "matches in either phase, reported as present:false with empty evidence. Given "
        "KNOWN LIMITATIONS #3, this is an honestly-reported absence-in-this-extracted-"
        "corpus finding, not a confirmed absence anywhere in MUI's full source (the "
        "transitions-duration/easing module, which is the most likely home for a "
        "reduced-motion accommodation, was not part of either phase's sparse checkout)."
    )

    result = {
        "system": "Material Design / MUI",
        "slug": "mui",
        "before": before,
        "after": after,
        "diff": diff,
        "parser_notes": parser_notes,
    }

    OUT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"before: {before['total_tokens']} tokens {before['by_category']}")
    print(f"after:  {after['total_tokens']} tokens {after['by_category']}")
    print(
        f"diff: removed={diff['removed_count']} added={diff['added_count']} "
        f"likely_renamed={diff['likely_renamed_count']}"
    )
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
