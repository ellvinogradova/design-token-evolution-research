# Ant Design v5 Accessibility Token Augmentation Proposal

**Status: independent research proposal. Not an official Ant Design contribution, not endorsed by the Ant Design team, and not merged into `ant-design/ant-design`.** This document and its accompanying token file (`ant-design-accessibility-tokens.tokens.json`) are the §4.5 token-augmentation deliverable of the solo research study *"Design Token Evolution and Accessibility Drift Across Major Open-Source Design Systems"* (Olena Vynohradova). See the study's plan, §8 (Ethical & Legal Considerations), for the same disclaimer in context.

## 1. Why Ant Design was selected for augmentation

Per the study's Day 3/4 accessibility-coverage scoring (`results/objective_subscores.json`), Ant Design's post-migration (v5.0.0, "after") state scores **1 out of 4** on the study's objective sub-score:

| Category | Ant Design v5 (after) |
|---|---|
| DTCG-format compliance | 0 |
| Contrast-safe color pairs | 0 |
| Focus-ring tokens | 1 (`controlOutlineWidth`, `controlOutline`, `controlTmpOutline` exist) |
| Target-size tokens | 0 |
| **Objective sub-score** | **1 / 4** |

Ant Design formalized a real, well-documented three-layer Seed → Map → Alias token architecture at v5 and already ships focus-indicator tokens — but it never shipped (a) any token that documents a verified contrast ratio for a text/surface pairing, or (b) any token expressing a minimum interactive target size. Both gaps are addressed here.

## 2. What was added

Two new token groups, written in W3C DTCG format, using Ant's real camelCase `AliasToken` naming convention throughout so each token reads as a natural extension of `components/theme/interface.ts` rather than a foreign scheme.

### 2.1 `contrast` — five contrast-safe pairs

| Token | Value | Paired against | Ratio | WCAG 2.2 SC |
|---|---|---|---|---|
| `colorTextOnBgContainer` | `#1F1F1F` | `colorBgContainer` `#FFFFFF` | **16.48:1** | 1.4.3 (4.5:1, normal text) |
| `colorTextSecondaryOnBgContainer` | `#595959` | `colorBgContainer` `#FFFFFF` | **7.01:1** | 1.4.3 (4.5:1, normal text) |
| `colorTextOnBgLayout` | `#1F1F1F` | `colorBgLayout` `#F5F5F5` | **15.12:1** | 1.4.3 (4.5:1, normal text) |
| `colorPrimaryOnBgContainer` | `#1677FF` | `colorBgContainer` `#FFFFFF` | **4.10:1** | 1.4.11 (3:1, non-text) |
| `colorErrorOnBgContainer` | `#F5222D` | `colorBgContainer` `#FFFFFF` | **4.08:1** | 1.4.11 (3:1, non-text **only**) |

None of the five values are invented. Each is the real value (or the real composited solid equivalent of an existing `rgba()` token) already present in Ant Design v5's own token source at tag `5.0.0`:

- `colorText` is documented in `interface.ts` as an alpha color; its concrete default is set in `themes/default/colors.ts`: `colorText: getAlphaColor(colorTextBase, 0.88)` where `colorTextBase` defaults to `'#000'` (see `themes/default/colors.ts:29,35`).
- `colorTextSecondary` is the same base at alpha `0.65` (`colors.ts:36`).
- `colorBgContainer` is `getSolidColor(colorBgBase, 0)` where `colorBgBase` defaults to `'#fff'` (`colors.ts:28,46`), i.e. plain white.
- `colorBgLayout` is `getSolidColor(colorBgBase, 4)`, i.e. `TinyColor('#fff').darken(4)` (`colors.ts:45`, `colorAlgorithm.ts:6-9`).
- `colorPrimary` and `colorError` are unmodified Seed tokens straight from `themes/seed.ts:24,27` (`#1677ff`, `#f5222d`).

### 2.2 `target-size` — two minimum-target tokens

| Token | Value | Derivation | WCAG 2.2 SC |
|---|---|---|---|
| `controlMinTargetSize` | `24px` | equals existing `controlHeightSM` (`controlHeight * 0.75` = `32 * 0.75` = `24`, `genControlHeight.ts:7`) | 2.5.8 (24×24 CSS px minimum, Level AA) |
| `controlMinTargetInset` | `4px` | `(controlMinTargetSize − controlHeightXS) / 2` = `(24 − 16) / 2` = `4`, which equals existing `sizeXXS` (`genSizeMapToken.ts`) | 2.5.8 |

Named to sit naturally alongside Ant's existing `control*` family (`controlHeight`, `controlHeightSM`, `controlHeightLG`, `controlOutlineWidth`, `controlInteractiveSize`).

## 3. The contrast math (worked, not asserted)

WCAG contrast ratio uses relative luminance:

```
for channel c in {R, G, B}, c_srgb = c / 255
  c_lin = c_srgb / 12.92                          if c_srgb <= 0.03928
        = ((c_srgb + 0.055) / 1.055) ^ 2.4         otherwise

L = 0.2126*R_lin + 0.7152*G_lin + 0.0722*B_lin

contrast(A, B) = (L_lighter + 0.05) / (L_darker + 0.05)
```

Example — `colorText` (`rgba(0,0,0,0.88)`) composited onto `colorBgContainer` (`#FFFFFF`):

1. **Composite the alpha color onto its background** (this is what a browser renders, and what actually needs to pass contrast — not the raw `rgba()` alpha value): for each channel, `result = alpha*fg + (1-alpha)*bg` → `0.88*0 + 0.12*255 = 30.6 → 31`. So `colorText` on white renders as solid `rgb(31,31,31)` = `#1F1F1F`.
2. **Relative luminance of `#1F1F1F`**: `31/255 = 0.1216` → linearized `((0.1216+0.055)/1.055)^2.4 = 0.01370`. Since R=G=B, `L = 0.01370`.
3. **Relative luminance of `#FFFFFF`**: `L = 1.0`.
4. **Ratio**: `(1.0 + 0.05) / (0.01370 + 0.05) = 1.05 / 0.0637 = 16.48`.

→ **16.48:1**, well past the 4.5:1 floor required by SC 1.4.3.

The other four pairs were computed the same way (see `results/proposals` computation; values cross-checked to 3 decimal places). Two results are worth flagging explicitly because they show why "pick a token, assume it's safe" is the wrong workflow:

- `colorPrimary` (`#1677FF`) on white computes to **4.10:1** — above the 3:1 non-text floor, so it is valid for icons/borders/focus indicators (SC 1.4.11), but it was *not* promoted to a normal-text pairing token even though 4.10 looks close to 4.5, because it is in fact below the 4.5:1 text floor.
- `colorError` (`#F5222D`) on white computes to **4.08:1** — this clears SC 1.4.11 (non-text, 3:1) but *fails* SC 1.4.3 (normal text, 4.5:1). This is the reason `colorErrorOnBgContainer` in the token file is explicitly scoped to non-text usage (icons, invalid-field borders) with a `usageWarning` extension, rather than offered as a general-purpose error-text color. It also explains, independently, why Ant's own shipped component styles route error *text* through the darker `colorErrorText` (a generated-palette shade) rather than the raw `colorError` seed value — this proposal did not attempt to reproduce `colorErrorText`'s exact hex because it depends on the `@ant-design/colors` palette-generation algorithm rather than a simple seed value, and reverse-deriving it risked introducing a value Ant itself doesn't actually ship.
- For completeness (not included as proposed pairs because they fail even the lower bar): raw `colorSuccess` (`#52C41A`) on white computes to only **2.27:1**, and raw `colorWarning` (`#FAAD14`) to **1.90:1** — both fail SC 1.4.11's 3:1 floor outright. This is a genuine, if out-of-scope-for-this-proposal, finding: several of Ant's seed status colors are not safe to use directly as icon/border colors on a white surface at any text or non-text size, which is exactly the kind of gap a documented contrast-pair layer is meant to catch before a consuming team discovers it in production.

## 4. Where these tokens belong in Ant's Seed → Map → Alias flow

Ant Design's real architecture (`components/theme/interface.ts`) is three layers:

1. **`SeedToken`** — the small set of designer-controlled root values (`colorPrimary`, `colorError`, `controlHeight`, `sizeUnit`, `sizeStep`, ...). Explicitly commented `DO NOT MODIFY THIS. PLEASE CONTACT DESIGNER.`
2. **`MapToken`** — seed values expanded into a derived palette/scale via `@ant-design/colors` and the `gen*` functions (`ColorMapToken`, `SizeMapToken`, `HeightMapToken`, `CommonMapToken`). Also designer-owned.
3. **`AliasToken`** — developer-facing, semantic/contextual tokens built by composing Map tokens for specific UI purposes (e.g. `colorTextHeading: mergedToken.colorText`, `colorLinkHover: mergedToken.colorInfoHover`, `controlOutlineWidth: mergedToken.lineWidth * 2`), assembled in `util/alias.ts`'s `formatToken()`.

**Both new groups belong in the Alias layer, not Seed or Map**, for the same reason the rest of `AliasToken` lives there: every token here is a *contextual composition* of existing Seed/Map values for a specific consumption purpose (a verified pairing, a minimum operable size), not a new primitive color or scale step. Concretely:

- The `contrast` tokens would be added as new keys on the `AliasToken` interface (alongside `colorTextHeading`, `colorTextLabel`, etc. in `interface.ts` lines ~370-390) and produced inside `formatToken()` in `util/alias.ts`, e.g. `colorTextOnBgContainer: mergedToken.colorText` (no new math needed at runtime — the composited hex values in this proposal exist purely to let the ratio be asserted and documented in isolation, outside the alpha-blended `rgba()` representation Ant currently ships).
- The `target-size` tokens would be added as new `AliasToken` keys near the existing `control*` alias tokens (`controlOutlineWidth`, `controlInteractiveSize`, `controlPaddingHorizontal` at `interface.ts` lines ~424-469), and derived the same way `controlInteractiveSize: mergedToken.controlHeight / 2` is today — i.e. `controlMinTargetSize: mergedToken.controlHeightSM` and `controlMinTargetInset: (controlMinTargetSize - mergedToken.controlHeightXS) / 2`.

They do not belong in `SeedToken` (they're not independent designer inputs — they're derived from/verified against existing seeds) or in `MapToken` (they're not palette/scale expansions — they're purpose-bound, single-use compositions, which is exactly `AliasToken`'s job per Ant's own documentation).

## 5. Score delta

Per the study's objective sub-score rubric (plan §4.3): one point each for DTCG-format compliance, contrast-safe pairs, focus-ring tokens, and target-size tokens.

| | DTCG | Contrast pairs | Focus ring | Target size | **Score** |
|---|---|---|---|---|---|
| Ant Design v5 "after" (shipped, `data/repos/ant-design/after`) | 0 | 0 | 1 | 0 | **1 / 4** |
| + this proposal, augmented | 0 | **1** | 1 | **1** | **3 / 4** |

**Delta: +2 (1/4 → 3/4).**

The DTCG point is deliberately **not** awarded. This proposal file is itself written in DTCG format, but the rubric's DTCG point measures whether *the system's actual shipped token source* is DTCG-compliant — and Ant Design v5 still ships its real tokens as TypeScript interfaces (`interface.ts`) and Less variables, not as DTCG JSON. A standalone proposal document adopting DTCG format for portability does not retroactively convert the shipped source, so inflating this point would overstate the delta beyond what's honestly supportable. The two points that *are* awarded reflect a real, checkable property of this file: it introduces at least one documented contrast-safe pair and at least one target-size token, which is exactly what those two rubric categories test for.

## 6. Disclaimer

This proposal is an independent research output produced for a solo computational/structural audit (Zenodo preprint, no external participants). It is **not** an Ant Design RFC, issue, or pull request, has not been reviewed or accepted by the Ant Design maintainers, and should not be represented as an official or in-progress Ant Design feature. Anyone wishing to actually propose these tokens to the `ant-design/ant-design` project should open a discussion/RFC through the project's own contribution process; this document exists solely to demonstrate, in a reproducible and externally-scored way, what closing Ant Design's accessibility-token gap could look like.
