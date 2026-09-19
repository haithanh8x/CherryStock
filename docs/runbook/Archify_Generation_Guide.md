# Archify Generation Guide — CherryStock

- Owner: .github/agents/SolutionArchitect.agent.md
- Mandatory instruction: .github/instructions/archify.instructions.md
- Preflight: scripts/validate_archify_source.py
- Shared renderer: scripts/render_archify_cherrystock.ps1

## 1. Mandatory rule

Every CherryStock task that creates, updates, validates or renders an Archify artifact MUST read this guide before editing the typed source.

Do not fix Archify by repeatedly patching only the latest validator error. First design semantic lanes and stable flows, then add the minimum routing metadata required.

The only completion condition is the current showcase run returning "ok": true. Preflight PASS, a visually plausible diagram, partial rendering, or PASS from an older revision is not enough.

## 2. Canonical generation flow

~~~text
Architecture Markdown / ADR / repository evidence
        ↓
Read this guide
        ↓
Plan scope + semantic lanes
        ↓
Edit *.architecture.json
        ↓
CherryStock preflight
        ↓
Archify validate --quality showcase
        ↓
Archify deliver
        ↓
Typography/navigation post-processing
        ↓
Visual review
        ↓
Commit typed source + generated HTML
~~~

Preferred wrappers:

~~~powershell
.\scripts\render_archify_cherrystock.ps1 -NoOpen
.\scripts\render_archify_analytics.ps1 -NoOpen
~~~

## 3. Design before routing

The recurring failure pattern is:

~~~text
insert node into an existing corridor
→ unrelated edge now crosses the node
→ patch fromSide/toSide/via/labelAt
→ another crossing or label issue appears
→ patch again
~~~

Avoid that loop. Use this order:

~~~text
1. identify semantic lanes
2. place nodes by lane
3. keep adjacent relationships local
4. move long cross-diagram dependencies out of overview when canonical docs/sources/drill-down can preserve them
5. stabilize positions
6. add explicit routing only where simple routing remains ambiguous
7. validate the complete diagram
~~~

Example from Analytics:

~~~text
Daily lane:
Indicator → SmartMoney → persistence → public → Consumers

Movement lane:
ZigZag → Movement persistence → Movement public → Price Movement Character → Consumers

Research lane:
Monthly orchestration → R/S evaluation → R/S research persistence
~~~

## 4. Known recurring failures

| Symptom / diagnostic | Root cause seen in CherryStock | Prevention / durable fix |
|---|---|---|
| sources has more than 3 items | Too much evidence/navigation stored in component.sources | Keep sources.length <= 3; use strongest evidence only. |
| Missing source path | Source points to moved/nonexistent file | Validate with --repo-root; never invent repository evidence. |
| Duplicate component id | Copy/paste or cosmetic rename drift | IDs are stable integration keys; keep unique/stable. |
| Unknown connection endpoint | Node id renamed without updating edges | Update connections/navigation in the same change. |
| Unknown navigation node | Navigation config drift | Keep navigation external and validate in preflight. |
| stage: arguments / missing input | Wrapper or PowerShell parameter problem | Never use $Input/$Output parameter names; use $InputPath/$OutputPath. |
| Repository-backed validation fails | --repo-root omitted | Always pass resolved repository root. |
| Label wider than component | Copy too long for node width | Shorten label or widen node while preserving center where practical. |
| Context/sublabel unreadable | Too much detail inside node | Keep 2–4 compact semantic chunks; move detail to docs/cards/sources. |
| composition/desktop-readability | ViewBox too wide | Check readability formula before widening canvas. |
| Only one readability offender shown | Validator exposes current worst offender | Audit all long sublabels in one pass. |
| Connection too short | Adjacent nodes too close | Explicit direct cardinal gap >= 24px; prefer 30px+. |
| Edge runs through node | New node inserted in existing corridor | Re-layout semantic lanes; do not only switch routing mode. |
| Proper relationship crossing | Long edges share same area | Separate flows into dedicated lanes/corridors. |
| Ambiguous corridor | Edges overlap/share indistinguishable paths | Use separate bands or target sides. |
| Label-route clearance | labelAt is in dense route area | Fix spacing/lane first, then label placement. |
| Container border run | Route hugs node/container border | Move corridor away instead of adding micro-bends. |
| Too many bends / poor route rhythm | Excess via/forced routing | Re-layout nodes; target <= 2 bends per relation. |
| Micro/short segments | Waypoints too close | Remove unnecessary via points. |
| Automatic routing still crosses nodes | Topology is congested | Move/re-lane nodes first; auto-routing is not topology repair. |
| Explicit routing later breaks | Hard-coded corridor became occupied after layout change | Add explicit routing only after positions stabilize; recheck neighboring edges after every move/insert. |
| Wider viewBox fixes overlap but breaks readability | Local spacing solved by widening entire canvas | Prefer vertical space, lane rearrangement, shorter copy, or drill-down. |
| Generated HTML stale | Typed source changed without deliver | Treat source + generated HTML as artifact pair. |
| Generated HTML manually edited | Presentation became accidental Source of Truth | Never hand-edit HTML for durable architecture meaning. |
| meta.repository.revision stale | Diagram changed while evidence revision stayed old | Update mapping when intentionally moving to new evidence revision. |
| Local and CI differ | Different Archify versions | Prefer repository-pinned version where CI exists. |
| Wrapper continues after failure | Child exit code not propagated | Stop after failed preflight/validate/deliver/post-processing. |
| Diagram overcrowded | Too much detail on one page | Split high-level and drill-down. |

## 5. Readability budget

Current showcase assumptions observed in CherryStock:

~~~text
viewport width               1440px
available diagram width       930px
minimum projected text          6px
typical context source font      9px
~~~

Approximation:

~~~text
projectedFontPx = sourceFontPx × availableDiagramWidth / viewBoxWidth
~~~

For 9px context text:

~~~text
max safe viewBox width ≈ 9 × 930 / 6 ≈ 1395px
~~~

Real failure:

~~~text
viewBoxWidth = 1400
9px context → 5.9786px
composition/desktop-readability = FAIL
~~~

Fix:

~~~text
viewBoxWidth = 1390
9px context → ~6.022px
readability budget restored
~~~

The exact threshold is a compatibility assumption for current Archify behavior. Revisit preflight constants when renderer/font behavior changes.

## 6. Direct connection clearance

Real failure:

~~~text
Connection "movement profile" is too short
20px; minimum 24px
~~~

For explicit straight cardinal relationships:

~~~text
right → left:
gap = target.x - (source.x + source.width)

bottom → top:
gap = target.y - (source.y + source.height)
~~~

CherryStock minimum is 24px. Prefer 30px+ margin. Shared preflight checks this before Archify.

## 7. Routing rules that proved stable

Prefer local straight relationships in the same semantic lane:

~~~text
Engine
  ↓
Persistence
  ↓
Public contract
  ↓
Downstream
~~~

Prefer adjacent peer relationships over long cross-diagram edges.

If a dependency is important but makes the overview unstable, preserve it in component.sources, component.sublabel, canonical architecture Markdown, ADR, or a drill-down diagram.

Automatic routing is useful when the layout already has clean corridors. Explicit routing is useful only after positions stabilize and a source/target side or label corridor must be deterministic.

Never respond to an edge-through-node failure by blindly deleting all routing fields. Ask first whether the layout itself is congested.

## 8. Change-impact rule

Whenever a component is inserted, removed, resized or moved, inspect every relationship whose corridor passes through the same row/column — not only relationships attached to that node.

Real CherryStock example: Indicator Engine → SmartMoney Engine became invalid after a ZigZag component was inserted between them. Endpoints remained valid, but the straight relationship passed through the new node.

The durable fix was semantic re-laning, not adding random bends.
