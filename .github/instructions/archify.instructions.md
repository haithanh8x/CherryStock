---
applyTo: "docs/architecture/diagrams/**/*.json,docs/architecture/generated/**/*.html,scripts/*archify*.py,scripts/*archify*.ps1"
---

# Archify Instructions

This file defines mandatory CherryStock rules for authoring, validating, delivering and navigating durable Archify architecture artifacts.

Canonical ownership and knowledge:
- `.github/agents/SolutionArchitect.agent.md` — architecture owner and Archify user.
- `docs/architecture/**` — engineering architecture Source of Truth.
- `docs/adr/**` — durable cross-module decisions when required.
- `docs/architecture/diagrams/**` — Archify typed visualization sources and navigation mapping.
- `docs/architecture/generated/**` — generated presentation artifacts only.

Archify is a visualization/validation tool of `SolutionArchitect`; it is not an architecture authority and generated HTML is never a Source of Truth.

## 1. Mandatory authoring workflow

For every durable CherryStock Archify architecture artifact:

```text
Repository evidence + architecture docs / ADR
        ↓
Archify typed source (*.architecture.json)
        ↓
CherryStock preflight
        ↓
Archify validate --quality showcase
        ↓
Archify deliver
        ↓
CherryStock presentation post-processing
        ↓
Generated HTML
```

Use repository wrappers instead of manually reproducing the pipeline when a wrapper exists.

Canonical high-level command:

```powershell
.\scripts\render_archify_cherrystock.ps1
```

The expected wrapper sequence is:

```text
[1] CherryStock preflight
[2] Archify validate (showcase)
[3] Archify deliver
[4] Typography / font picker
[5] Drill-down navigation
```

Do not mark an Archify-backed design complete unless the typed source and generated HTML are synchronized and the applicable Archify validation returns `"ok": true`.

## 2. Archify architecture schema guardrails

### Component IDs
- Every component `id` MUST be unique, stable and non-empty.
- Treat `id` as an integration contract for relationships and drill-down navigation.
- Rename `label` freely when wording changes; do not rename `id` solely for presentation cleanup.
- When an `id` changes intentionally, update every connection and navigation mapping referencing it in the same change.

### Component sources
- `component.sources` is repository evidence only.
- Architecture schema currently allows at most **3 source items per component**; keep every component at `sources.length <= 3`.
- Prefer the three strongest evidence files rather than enumerating all related files.
- Do NOT place generated HTML, drill-down targets, navigation metadata or presentation-only documents in `component.sources`.
- Do NOT use a source label such as `Drill-down architecture` to model navigation.
- Every declared source path MUST exist under the repository root when validation runs.

Correct:

```json
"sources": [
  {"path": "src/calcEngine/calcIndicators.py", "label": "Indicators"},
  {"path": "src/calcEngine/levelLadder.py", "label": "R/S Ladder"},
  {"path": "src/calcEngine/smartMoneyScore.py", "label": "SmartMoneyScore"}
]
```

Incorrect:

```json
"sources": [
  {"path": "...", "label": "..."},
  {"path": "...", "label": "..."},
  {"path": "...", "label": "..."},
  {"path": "docs/architecture/generated/Some_Detail.html", "label": "Drill-down"}
]
```

### Connections
- Every `from` and `to` MUST reference an existing component id.
- Prefer simple orthogonal/straight relationships.
- Keep relationship bends within Archify showcase limits; avoid decorative routing.
- Explicit `labelAt`, `fromSide`, `toSide`, `route` and `via` are preferred when automatic placement causes overlap or ambiguous corridors.

### Repository-backed diagrams
If the diagram declares `meta.repository` or component `sources`, validate/deliver with `--repo-root`.

Repository wrappers MUST resolve and pass the repository root explicitly.

## 3. Text/readability rules

Archify `showcase` validates desktop readability, not only schema and geometry.

### Labels
- Node labels MUST fit within the component width.
- If Archify reports `Label ... is wider than component`, either shorten the label or widen the component.
- When widening a node that already has aligned edges, preserve its center where practical so existing orthogonal routes remain stable.

Example:

```text
old: pos.x=40, width=180 → center=130
new: pos.x=30, width=200 → center=130
```

### Sublabel/context text
- Keep context text short: normally **2–4 compact semantic chunks**.
- Prefer conceptual names over long physical object names when the title/source evidence already preserves exact implementation detail.
- Do not encode a mini-document inside a node.
- Put detailed contracts in architecture Markdown, cards, source evidence or a drill-down diagram.

Prefer:

```text
values · config SSOT
feature · state · score
baseline/ablation · effect
```

Avoid:

```text
vw_Ticker_indicators · vw_Indicator_config
baseline/ablation · effectiveness · promotion
raw_* · ticker/FA · vw_Ticker_OHLC_D · indicator config
```

### Desktop readability budget
At a 1440px desktop viewport, Archify may provide about 930px to the diagram. Approximate rendered text scale as:

```text
projectedFontPx ≈ sourceFontPx × availableDiagramWidth / viewBoxWidth
```

For the observed showcase desktop check:

```text
availableDiagramWidth ≈ 930px
minimum projected context text = 6px
```

Therefore:
- avoid unnecessarily wide viewBoxes;
- prefer a focused diagram over a horizontally sprawling diagram;
- for detail diagrams, target a compact viewBox when possible (roughly 1050–1150px wide is often easier to keep readable than ~1300px+);
- if multiple contexts are near the readability floor, compact the whole diagram or split scope instead of repeatedly shortening one reported label at a time.

When Archify reports one `composition/desktop-readability` issue, assume it may be exposing only the current worst offender. Audit and shorten all unusually long node contexts in the same pass.

## 4. Geometry and relationship-label rules

- Prefer aligned rows/columns and predictable spacing.
- Preserve node centers when resizing whenever this avoids unnecessary edge churn.
- Do not let relationship labels overlap source/target components.
- If Archify provides a suggested `labelAt`, use it as the first correction unless it creates another clear conflict.
- Relationship labels between horizontally adjacent nodes often need placement above or below the corridor rather than centered inside the gap.
- Do not change topology merely to satisfy presentation; repair geometry/presentation first.

A showcase-ready diagram should normally have:
- no proper relationship crossings;
- no ambiguous corridors;
- no label-route clearance errors;
- no container-border runs;
- bounded bend/stretch metrics;
- zero desktop-readability errors.

## 5. High-level vs drill-down scope

`CherryStock_High_Level.html` is the root/main architecture map.

High-level rules:
- keep only major system components (normally around 8–12 primary nodes);
- do not embed internal engine stages, detailed tables or research subflows when a domain drill-down can own them;
- keep high-level labels/context concise.

Use drill-down pages for detailed domains, for example:

```text
CherryStock_High_Level.html
    ↓ Analytics & Calculation Engines
CherryStock_Analytics_Calculation_Engines.html
```

A drill-down is presentation navigation, not an Archify `source` relationship.

## 6. Drill-down navigation rules

Navigation is configured outside the Archify typed architecture source:

```text
docs/architecture/diagrams/cherrystock-archify-navigation.json
```

Use stable component ids as navigation keys.

Example:

```json
{
  "pages": {
    "CherryStock_High_Level.html": {
      "nodes": {
        "analytics": {
          "target": "CherryStock_Analytics_Calculation_Engines.html",
          "interaction": "double-click"
        }
      }
    }
  }
}
```

Rules:
- targets should normally be relative paths between generated files in the same directory;
- use double-click for drill-down by default so normal Archify click/inspect behavior remains available;
- detail pages SHOULD expose a back link to the parent/root page;
- navigation MUST be injected by `scripts/customize_archify_navigation.py` or the repository wrapper, never maintained manually in generated HTML;
- navigation node ids MUST exist in the typed source for the page being rendered.

## 7. PowerShell wrapper rules

Do NOT name PowerShell parameters `$Input` or `$Output`.

PowerShell has the automatic variable `$input` and variable names are case-insensitive, so `$Input` can lose the intended path value.

Use:

```powershell
[string]$InputPath
[string]$OutputPath
```

and resolve both before invoking Archify.

Wrappers MUST:
- fail when the typed source is missing;
- use resolved absolute input/output paths where practical;
- preserve non-zero child-process exit codes as failures;
- run preflight before Archify;
- run presentation post-processors only after successful `deliver`.

## 8. CherryStock preflight

Before Archify validation, run:

```powershell
python scripts/validate_archify_source.py <input> `
  --repo-root . `
  --output <output> `
  --navigation-config docs/architecture/diagrams/cherrystock-archify-navigation.json
```

The preflight MUST fail fast for repository-owned invariants including:
- more than 3 component sources;
- duplicate component ids;
- connection endpoints referencing unknown components;
- missing source paths;
- presentation/navigation material placed in `component.sources`;
- navigation mappings referencing unknown node ids;
- malformed navigation targets/backlinks.

Archify remains authoritative for its complete schema, rendering, geometry and showcase composition checks. Do not attempt to duplicate the whole Archify validator in CherryStock preflight.

## 9. Error triage

Classify failures by stage before changing the diagram.

### `stage: arguments`
CLI invocation/wrapper problem. Typical causes:
- missing `<input.json>` argument;
- PowerShell `$Input` collision;
- invalid command/option ordering.

Fix the wrapper/command first. Do not change diagram geometry for an arguments-stage failure.

### `stage: render`
Schema or initial layout constraint problem. Typical causes:
- `sources` exceeds max items;
- label wider than component;
- relationship label overlaps component;
- invalid/missing schema field.

Fix the exact schema/layout diagnostic, then rerun.

### `stage: check`
Final showcase/composition problem. Typical causes:
- desktop readability;
- route/corridor/crossing quality;
- label clearance.

For readability failures, audit all long contexts in one pass. Do not repeatedly patch only the single text string currently reported if several nodes use similarly long context.

## 10. Validation and completion gate

A diagram is not validated because it looks correct or because earlier checks passed.

Only claim Archify validation success when the current local run returns:

```json
"ok": true
```

For `quality_profile=showcase`, completion requires the showcase profile to pass.

After successful rendering, synchronize the generated HTML with the typed source in Git. If local generation cannot be executed from the connected environment, state `PENDING_LOCAL_ARCHIFY_VALIDATION/RENDER` rather than claiming completion.

## 11. Artifact synchronization

Every approved design change affecting an Archify-backed scope MUST keep these aligned:

```text
architecture Markdown / ADR when required
        ↕
Archify typed source
        ↕
generated HTML
```

Generated HTML:
- is derived output;
- MUST be regenerated after typed-source changes;
- MUST NOT be manually edited as architecture meaning;
- MAY receive repository-owned presentation-only post-processing such as typography and navigation after Archify delivery.

If only documentation navigation changes and architecture semantics do not change, do not churn an unrelated Archify geometry source unnecessarily.

## 12. Anti-patterns

Do not:
- add a fourth source to a component;
- put drill-down HTML/navigation into `component.sources`;
- use generated HTML as architecture Source of Truth;
- use `$Input`/`$Output` PowerShell parameters;
- expand the viewBox to solve every local overlap without checking readability impact;
- fix repeated readability failures one label at a time without auditing the diagram;
- manually patch generated HTML for durable navigation;
- rename stable component ids for cosmetic reasons;
- invent repository evidence or topology to make the diagram prettier;
- claim validation before the current `showcase` run returns `ok: true`.

## 13. Review checklist

Before handoff, verify:

```text
[ ] Correct SolutionArchitect-owned architecture scope
[ ] Durable architecture meaning exists in docs/ADR as required
[ ] Unique/stable component ids
[ ] <= 3 repository evidence sources per component
[ ] No navigation/presentation entries in component.sources
[ ] All source paths exist
[ ] All connection endpoints resolve
[ ] Labels fit nodes
[ ] Context text is compact and desktop-readable
[ ] Relationship labels clear nodes/routes
[ ] High-level vs drill-down scope is appropriate
[ ] Navigation config references valid node ids and relative targets
[ ] CherryStock preflight PASS
[ ] Archify showcase validation returns ok: true
[ ] Deliver succeeds
[ ] Typography/navigation post-processing succeeds
[ ] Typed source + generated HTML synchronized in Git
```
