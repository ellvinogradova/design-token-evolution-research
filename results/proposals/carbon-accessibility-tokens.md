# Carbon Design System v11 Accessibility Token Augmentation Proposal

**Status: independent research proposal. Not an official IBM Carbon Design System contribution, not endorsed by the Carbon team, and not merged into `carbon-design-system/carbon`.** This document and its accompanying token file (`carbon-accessibility-tokens.tokens.json`) are the §4.5 token-augmentation deliverable of the solo research study *"Design Token Evolution and Accessibility Drift Across Major Open-Source Design Systems"* (Olena Vynohradova). See the study's plan, §8 (Ethical & Legal Considerations), for the same disclaimer in context.

## 1. Why Carbon was selected for augmentation

Per the study's Day 3/4 accessibility-coverage scoring (`results/objective_subscores.json`), Carbon's post-migration (v11.0.0, "after") state scores **1 out of 4** on the study's objective sub-score — tied with Ant Design v5 as the lowest of the five audited systems:

| Category | Carbon v11 (after) |
|---|---|
| DTCG-format compliance | 0 |
| Contrast-safe color pairs | 0 |
| Focus-ring tokens | 1 (`focus`, `focusInset`, `focusInverse` exist, `packages/themes/src/white.js:182-184`) |
| Target-size tokens | 0 |
| **Objective sub-score** | **1 / 4** |

Carbon v11 ships a mature, well-organized global theme token set (Background / Layer / Field / Border / Text / Link / Icon / Support / Focus / Skeleton categories in `white.js`, `g10.js`, `g90.js`, `g100.js`) and already has dedicated focus-ring tokens — but it never ships (a) a token that asserts a verified contrast ratio for a specific text/surface pairing, or (b) a token expressing a minimum interactive target size. Both gaps are addressed here.

## 2. Source-of-truth note (read this before the token list)

The study's sparse checkout of Carbon at `data/repos/carbon/after` includes only `packages/themes`, `packages/layout`, and `packages/type` — it does **not** vendor `@carbon/colors`, the package `white.js`/`g10.js`/`g100.js` import their concrete hex values from (they only hold symbolic references like `textPrimary = gray100`). To avoid guessing at color values, the actual `@carbon/colors` and `@carbon/layout` packages were fetched directly from the public npm registry at **the exact versions `@carbon/themes@11.0.0` itself depends on** (`@carbon/colors@^11.0.0`, `@carbon/layout@^11.0.0`; confirmed via `npm view @carbon/themes@11.0.0 dependencies`), both published 2022-03-31, the same day as the `v11.0.0` theme tag:

- `@carbon/colors@11.0.0` (`lib/index.js`) — resolves `gray10`…`gray100`, `white`, `blue60`, `blue70`, etc. to real hex.
- `@carbon/layout@11.0.0` (`lib/index.js`) — resolves `spacing01`…`spacing13`, `container01`…`container05`, `sizeXSmall`…`size2XLarge`, `iconSize01`/`02` to real `rem()`-computed values.

These were cross-checked against the immediately-prior `10.31.0`/`10.34.0` releases (also fetched) and found identical — Carbon's core gray/blue palette and spacing/size scale did not change in the v11 transition, only the semantic theme-token layer on top of them did. Resolved values used below:

| Symbolic name (in `white.js`) | Real value (`@carbon/colors@11.0.0` / `@carbon/layout@11.0.0`) |
|---|---|
| `white` | `#ffffff` |
| `gray10` | `#f4f4f4` |
| `gray40` | `#a8a8a8` |
| `gray50` | `#8d8d8d` |
| `gray70` | `#525252` |
| `gray100` | `#161616` |
| `blue60` | `#0f62fe` |
| `blue70` | `#0043ce` |
| `sizeXSmall` | `rem(24)` = `1.5rem` = `24px` |
| `container01` | `miniUnits(3)` = `rem(24)` = `24px` |
| `spacing06` | `miniUnits(3)` = `rem(24)` = `24px` |
| `iconSize01` | `1rem` = `16px` |

## 3. What was added

Two new token groups, written in W3C DTCG format, using Carbon's real camelCase naming convention throughout (`textPrimary`, `backgroundBrand`, `layer01`, `sizeXSmall`) so each token reads as a natural extension of `packages/themes/src/white.js` and `packages/layout`.

### 3.1 `contrast` — six contrast-safe pairs

All anchored to Carbon's `white` theme (`packages/themes/src/white.js`, tag `v11.0.0`).

| Token | Value | Paired against | Ratio | WCAG 2.2 SC |
|---|---|---|---|---|
| `textPrimaryOnBackground` | `#161616` (textPrimary) | `background` `#ffffff` | **18.10:1** | 1.4.3 (4.5:1, normal text) |
| `textSecondaryOnBackground` | `#525252` (textSecondary) | `background` `#ffffff` | **7.81:1** | 1.4.3 (4.5:1, normal text) |
| `textPrimaryOnLayer01` | `#161616` (textPrimary) | `layer01` `#f4f4f4` | **16.45:1** | 1.4.3 (4.5:1, normal text) |
| `textOnColorOnBackgroundBrand` | `#ffffff` (textOnColor) | `backgroundBrand` `#0f62fe` | **5.00:1** | 1.4.3 (4.5:1, normal text — tight) |
| `focusOnBackground` | `#0f62fe` (focus) | `background` `#ffffff` | **5.00:1** | 1.4.11 (3:1, non-text) |
| `borderStrongOnBackground` | `#8d8d8d` (borderStrong01) | `background` `#ffffff` | **3.32:1** | 1.4.11 (3:1, non-text **only**) |

None of the six values are invented — each is the real, unmodified hex Carbon's own `white.js` already references symbolically (line numbers cited in the token file's `$description` fields).

`textPrimaryOnLayer01` exists as a separate entry (not folded into `textPrimaryOnBackground`) specifically because Carbon's layered-surface model (`layer01`/`02`/`03`, each with hover/active/selected/accent variants) is a real, distinguishing architectural feature of this system versus the flatter background models of Ant Design or MUI — a pairing verified against `background` is not automatically verified against `layer01`, and nothing in Carbon's shipped source asserts it is.

### 3.2 `target-size` — two minimum-target tokens

| Token | Value | Derivation | WCAG 2.2 SC |
|---|---|---|---|
| `sizeMinTarget` | `24px` | equals existing `sizeXSmall`, `container01`, and `spacing06` (all `miniUnits(3)` = `rem(24)`) | 2.5.8 (24×24 CSS px minimum, Level AA) |
| `sizeMinTargetSpacing` | `24px` | minimum center-to-center spacing between adjacent undersized targets (two 24px-diameter, 12px-radius circles must be ≥24px apart to not intersect) | 2.5.8 (spacing exception) |

Named to sit naturally alongside Carbon's existing `size*`/`container*`/`spacing*` scale family in `packages/layout` (`sizeXSmall … size2XLarge`, `spacing01 … spacing13`, `container01 … container05` — see `before/packages/layout/src/tokens.js`).

## 4. The contrast math (worked, not asserted)

WCAG contrast ratio uses relative luminance:

```
for channel c in {R, G, B}, c_srgb = c / 255
  c_lin = c_srgb / 12.92                          if c_srgb <= 0.03928
        = ((c_srgb + 0.055) / 1.055) ^ 2.4         otherwise

L = 0.2126*R_lin + 0.7152*G_lin + 0.0722*B_lin

contrast(A, B) = (L_lighter + 0.05) / (L_darker + 0.05)
```

Example — `textPrimary` (`gray100`, `#161616`) on `background` (`white`, `#ffffff`):

1. **`#161616`** → `R=G=B=0x16=22`; `c_srgb = 22/255 = 0.08627`. Since `0.08627 > 0.03928`, linearize: `c_lin = ((0.08627+0.055)/1.055)^2.4 = (0.13391)^2.4 = 0.00802`. Since `R=G=B`, `L = 0.2126*0.00802 + 0.7152*0.00802 + 0.0722*0.00802 = 0.00802`.
2. **`#ffffff`** → `c_srgb = 1.0`, `c_lin = 1.0`, `L = 1.0`.
3. **Ratio** = `(L_lighter + 0.05) / (L_darker + 0.05) = (1.0 + 0.05) / (0.00802 + 0.05) = 1.05 / 0.05802 = 18.10`.

→ **18.10:1**, matching the token file, well past the 4.5:1 floor required by SC 1.4.3.

The other five pairs were computed the same way with a script, to 4 decimal places before rounding for display (script and method in `results/proposals`, reproducible from the hex table in §2). Three results are worth flagging explicitly, because "the token exists" is not the same claim as "the token is contrast-safe":

- **`textOnColorOnBackgroundBrand` computes to 5.00:1** — `textOnColor` (white) is Carbon's own token for text placed on colored surfaces, and `backgroundBrand` (blue60) is Carbon's own brand-surface token, so this is exactly the pairing a primary-button-style component would use. 5.00:1 clears SC 1.4.3's 4.5:1 floor, but with under half a point of margin — a genuinely tight, realistic result, not a comfortable one. This is precisely the kind of number a documented contrast-pair token is supposed to surface before a future palette tweak (e.g. a slightly lighter `blue60`) quietly pushes it under 4.5:1.
- **`focusOnBackground` and `textOnColorOnBackgroundBrand` share the identical underlying color pair** (`blue60` / `white`) and therefore the identical numeric ratio (5.00:1) — contrast ratio is symmetric and doesn't care about semantic role. They are documented as two separate tokens anyway because they satisfy two different success criteria for two different reasons: one is normal text legibility (SC 1.4.3), the other is non-text focus-indicator visibility against the page (SC 1.4.11). Collapsing them into one token would have obscured which SC is actually being satisfied for which use case.
- **`borderStrongOnBackground` computes to 3.32:1** — clears the 3:1 non-text floor (SC 1.4.11) but is explicitly scoped to non-text usage only, since 3.32:1 is well short of the 4.5:1 text floor. For comparison, the next step down Carbon's gray scale, `gray40` (`#a8a8a8`), computes to only **2.38:1** against white and would fail SC 1.4.11 outright — meaning `borderStrong01` (`gray50`) is close to the last usable rung of Carbon's own gray scale for a 3:1-conforming non-text border on a white surface, which is worth knowing before substituting a "slightly lighter" gray in a redesign.

## 5. Where these tokens belong in Carbon's theme-token structure

Carbon v11's global theme files (`white.js`, `g10.js`, `g90.js`, `g100.js`) are organized as flat, comment-delimited category blocks — `// Background`, `// Layer`, `// Field`, `// Border`, `// Text`, `// Link`, `// Icon`, `// Support`, `// Focus`, `// Skeleton`, `// Misc` — each exporting `const` bindings built from `@carbon/colors` primitives (occasionally through `adjustAlpha()`). This is a real, if informally-named, two-layer model: `@carbon/colors` / `@carbon/layout` act as the primitive layer, and the theme files (`white.js` etc.) act as the semantic layer — the plan's rubric records this as "2-layer" under the descriptive-only layering finding, not the scored sub-score.

**Both new groups belong in that same semantic theme layer, added as new category blocks**, for the same reason `// Focus` already lives there rather than in `@carbon/colors`: every token here is a *contextual composition* of existing primitive values for a specific consumption purpose (a verified pairing, a minimum operable size), not a new primitive color or scale step. Concretely, in `packages/themes/src/white.js`:

- The `contrast` tokens would be added as a new `// Contrast` block directly after the existing `// Focus` block (after line 184), each exported the same way existing tokens are — e.g. `export const textPrimaryOnBackground = textPrimary;` (a same-value alias; the point of these tokens is the asserted, documented ratio in their description/spec entry, not a new color). Because Carbon's theme files are per-theme (`white.js`, `g10.js`, `g90.js`, `g100.js`), each theme would need its own resolved set — this proposal covers `white` only, as a representative, fully-worked example; `g10`/`g90`/`g100` would need the same pairs recomputed against their own literal values before being considered complete (they are not included here, to avoid asserting ratios that were not actually computed).
- The `target-size` tokens would be added not to the theme files (which are color-only) but to `packages/layout`, as new exports alongside the existing `sizeXSmall … size2XLarge` family in `packages/layout/src/index.js`/`tokens.js` — e.g. `export const sizeMinTarget = rem(24);`, deliberately expressed with the same `rem()` helper Carbon's own scale uses rather than a raw px literal, so it participates in the same base-font-size-relative system as every other Carbon dimension token.

They do not belong in `@carbon/colors` or `@carbon/layout` themselves (those are primitive/scale packages with no consumption context) — they belong exactly where Carbon already puts its other purpose-bound semantic tokens: the theme layer for color, the layout package for size.

## 6. Score delta

Per the study's objective sub-score rubric (plan §4.3): one point each for DTCG-format compliance, contrast-safe pairs, focus-ring tokens, and target-size tokens.

| | DTCG | Contrast pairs | Focus ring | Target size | **Score** |
|---|---|---|---|---|---|
| Carbon v11 "after" (shipped, `data/repos/carbon/after`) | 0 | 0 | 1 | 0 | **1 / 4** |
| + this proposal, augmented | 0 | **1** | 1 | **1** | **3 / 4** |

**Delta: +2 (1/4 → 3/4).**

The DTCG point is deliberately **not** awarded, for the same reason it wasn't awarded in this study's parallel Ant Design augmentation proposal: this file is itself written in DTCG format, but the rubric's DTCG point measures whether *the system's actual shipped token source* is DTCG-compliant, and Carbon v11 still ships its real global tokens as plain JavaScript `const` exports (`packages/themes/src/*.js`), not as DTCG JSON — there is no `.tokens.json` anywhere in Carbon's actual v11.0.0 source tree. A standalone proposal document adopting DTCG format for portability does not retroactively convert the shipped source, so inflating this point would overstate the delta beyond what's honestly supportable. The two points that *are* awarded reflect a real, checkable property of this file: it introduces at least one documented contrast-safe pair (six, in fact) and at least one target-size token (two), which is exactly what those two rubric categories test for.

## 7. Disclaimer

This proposal is an independent research output produced for a solo computational/structural audit (Zenodo preprint, no external participants). It is **not** a Carbon Design System RFC, GitHub issue, or pull request, has not been reviewed or accepted by the Carbon maintainers at IBM, and should not be represented as an official or in-progress Carbon feature. Anyone wishing to actually propose these tokens to the `carbon-design-system/carbon` project should open a discussion or RFC through the project's own contribution process (Carbon publishes its own accessibility guidance separately at carbondesignsystem.com; this proposal is independent of and does not speak for that documentation). This document exists solely to demonstrate, in a reproducible and externally-scored way, what closing Carbon's accessibility-token gap could look like.
