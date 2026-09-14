# Handoff: Benchmark-Tavily Comparison Mockup

## Overview
UI mockup for Benchmark-Tavily, a tool that estimates LLM token cost/price for running Tavily search methods vs. alternatives, scaled to 1,000 searches. The core job of the page is to make the **lowest-cost, most token-efficient option obvious at a glance** within each comparison pair.

## About the Design Files
`Benchmark-Tavily.dc.html` is a **design reference built in HTML** (a Claude "Design Component") — a prototype of look and behavior, not production code to lift directly. Recreate it in the target codebase's real stack: the source app is a SvelteKit + Tailwind + shadcn-preset app (see `reference/`), so implement this as Svelte components using that existing setup, matching the structure, tokens, and interactions documented below.

## Fidelity
**High-fidelity.** Colors, type, spacing, and the winner-highlight treatment are final; component structure should be recreated pixel-close using shadcn primitives already in the app (Tabs, Card, Badge) restyled with the tokens below.

## Reference material included
- `reference/Tavily_Benchmark_sample.html` — the original app export the mockup is based on (structure, copy, tab pattern, `data-testid` hooks).
- `reference/0.CTd9UrJT.css` — the original compiled Tailwind/shadcn CSS (preset `b10ocktRFA`) for class-name/utility cross-reference.

## Screens / Views
### 1. Summary tab (primary view)
**Purpose:** Let a user scan two head-to-head comparisons and immediately see which method is cheaper/more efficient.

**Layout:**
- Page container, max-width 960px, centered, 56px top/bottom padding, 24px side padding (fluid below that width).
- Header row: flex, `justify-content: space-between`, wraps on narrow widths.
  - Left: H1 "Tavily Benchmark" (32px/700) + one paragraph subtitle (14px/400, muted) describing the ×1000 scaling methodology, with "1,000 searches" bolded inline.
  - Right: GitHub link — ghost pill button, 1px hairline border, icon + "GitHub" text, links to `https://github.com/newtob/Benchmark-Tavily`, opens in new tab.
- Tab bar: pill container (`background: surface-2`, 4px padding, 6px radius) containing two buttons, "Summary" (active by default) and "Searches". Active tab: white surface, 1px soft shadow, dark text. Inactive: transparent, muted text. Both 14px/600.
- Two comparison sections, each:
  - H2 section title (20px/700) e.g. "Tavily: Raw Tool Call vs MCP"
  - Caption directly under it (13px/400, muted) e.g. "Average across 3 searches, ×1000."
  - Two-column grid (`1fr 1fr`, 16px gap; stacks to 1 column under ~560px) of comparison cards — see Winner Highlight Pattern below.
- Methodology footnote: hairline top border, 20px top padding, 12px/300 muted text.

### 2. Searches tab (stub)
Placeholder panel: dashed 1px border, 4px radius, centered text, 56px vertical padding. Title "Per-search detail" (16px/700) + one muted line explaining it's not yet built. This is intentionally unbuilt — implement as a route/tab that can later host a per-search breakdown table.

## Winner Highlight Pattern (the core interaction of the app)
This is the most important pattern to replicate — it is the entire reason the app exists.

Each comparison group is two cards, A vs B. The card with the **lower cost** (tiebreaker: lower token count) gets:
1. A `4px` solid left border in Synechron Yellow (`#FBF321`) — this is the brand's "keyline accent" motif, used here as a winner marker. It is a border only, never a filled yellow area (brand rule: no large yellow fills).
2. A small pill badge, absolutely positioned at `top: -11px; left: 16px`, background Core Blue (`#002535`), white text, 11px/700, uppercase, letter-spacing .04em, reading "Most efficient".
3. A stronger shadow than the losing card (`0 4px 16px rgba(0,37,53,.12)` vs none/flat on the loser).
4. The value line rendered in Core Blue and a heavier weight (800) instead of black/700 on the losing card.
5. Optional delta line below the value, e.g. "43% cheaper · 43% fewer tokens", 12px/600, in the lighter brand blue (`#0a5a78`).

The losing card is a plain flat card: 1px hairline border (`#E6E7E8`), no shadow, black text.

**Winner logic:** cost is the primary metric; token count is the tiebreaker. This should be computed, not hardcoded — if a future comparison's cost ties, fall back to lower tokens.

**Title-weight rule (applies everywhere):** any heading/label is always heavier weight than the text beneath it — H1 (700) over its subtitle (400), H2 (700) over its caption (400), card label (600) over nothing lighter below it except the value which is intentionally bolder as the focal number.

## Interactions & Behavior
- Tab switch (Summary ⇄ Searches): simple client-side state toggle, no animation beyond the standard brand ease (150–250ms, `cubic-bezier(.4,0,.2,1)`) if a transition is added.
- GitHub link: standard `<a target="_blank" rel="noopener">`, opens in a new tab.
- Ghost button hover: background tints to `surface-2` on hover (per brand hover rules — subtle, no color shift beyond that).
- No loading or error states needed for this static mockup; if wired to live data, show a skeleton in place of the value line (muted grey block, same dimensions) while fetching.

## State Management
- `activeTab`: `'summary' | 'searches'`, default `'summary'`.
- Comparison data should be modeled as an array of groups, each with two named entries (`{ label, tokens, cost }`), so the winner-highlight logic (`lowest cost, tokens as tiebreaker`) can run generically instead of being hardcoded per pair. This also lets more comparison groups be added later without new layout code.

## Design Tokens
All from the bound Synechron design system (`colors_and_type.css`) — do not introduce new colors.

**Color**
- Background: `--bg` (`#FAFAFA` light / `#002535` dark)
- Surface (cards): `--surface` (`#FFFFFF` light / `#06303F` dark)
- Surface-2 (tab pill bg): `--surface-2` (`#F4F4F4` light / `#0A3D50` dark)
- Primary text: `--fg1` (`#000000` light / `#FFFFFF` dark)
- Secondary/accent text (winner values, section subheads): `--fg2` (`#002535` light / `#BFE3EF` dark)
- Muted/caption text: `--fg3` (`#808285` light / `#8FB3C0` dark)
- Border/hairline: `--border` (`#E6E7E8` light / `rgba(255,255,255,.12)` dark)
- Winner keyline: Synechron Yellow `#FBF321` (border only, never a fill)
- Winner badge background: Core Blue `#002535`
- Delta text: Blue-light `#0a5a78`

**Typography** — Aptos family throughout (self-hosted; see `fonts/` in the design system bundle)
- H1: 32px / 700
- H2 (section title): 20px / 700
- Card label: 13px / 600
- Card value: 22px / 700 (loser) or 800 (winner)
- Caption/subtitle/footnote: 13–14px / 400, muted; footnote is 12px / 300
- Tab label: 14px / 600
- Badge: 11px / 700, uppercase, letter-spacing .04em

**Spacing / radius**
- Card padding: 20px (22px top on the winner card to clear the badge)
- Card radius: 4px (brand default is near-square, 0–4px)
- Grid gap: 16px
- Section spacing: 36–40px between comparison groups

**Shadows**
- Flat card: none
- Winner card: `0 4px 16px rgba(0,37,53,.12)`
- Active tab: `0 1px 3px rgba(0,37,53,.1)`

## Assets
- GitHub icon: inline SVG mark (16×16, `currentColor`), included directly in the mockup — no external asset needed.
- No photography/illustration used, per brand guidance (solid surfaces + hairlines only).

## Sample data used (placeholder — replace with real benchmark output)
| Group | Option | Tokens | Cost | Winner |
|---|---|---|---|---|
| Raw Tool Call vs MCP | Raw tool call | 128,000 | $0.26 | |
| | MCP | 72,667 | $0.15 | ✅ |
| Claude Web Search vs Tavily Extract | Claude Web Search | 95,400 | $0.19 | |
| | Tavily Extract | 41,200 | $0.08 | ✅ |

## Files
- `Benchmark-Tavily.dc.html` — the mockup (open directly in a browser; view source for exact markup/inline styles).
- `reference/Tavily_Benchmark_sample.html` + `reference/0.CTd9UrJT.css` — original app export this was based on.
