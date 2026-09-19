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


## 9. Required CherryStock preflight

Run through the wrapper, or explicitly as one command:

~~~powershell
python scripts\validate_archify_source.py docs\architecture\diagrams\<diagram>.architecture.json --repo-root . --output docs\architecture\generated\<artifact>.html --navigation-config docs\architecture\diagrams\cherrystock-archify-navigation.json
~~~

Current preflight protects at least:

~~~text
diagram type
component ids
max component sources
source path existence
navigation misuse in sources
connection endpoint existence
navigation node validity
minimum explicit direct connection clearance
showcase desktop readability budget
~~~

Preflight PASS is necessary but not sufficient. Archify remains authoritative for complete geometry and showcase composition.

## 10. Error triage by Archify stage

### stage: arguments

This is usually wrapper/CLI behavior. Check input path, argument ordering, PowerShell variable collision, Archify installation/version, and repo-root.

Do not touch diagram geometry until invocation is correct.

### stage: render

This is usually schema or a hard initial layout constraint. Common examples:

~~~text
label too wide
invalid field
too many sources
connection too short
hard geometry constraint
~~~

Fix the direct cause, then rerun from preflight.

### stage: check

The SVG was produced, but final showcase composition failed. Common examples:

~~~text
desktop-readability
proper crossings
ambiguous corridors
label-route clearance
container border runs
route rhythm
stretch/bend quality
~~~

Treat these as whole-diagram composition problems, not automatically as isolated edge problems.

## 11. Mandatory checker review

When Archify returns checker metrics, inspect all of them even if only one issue is fatal.

Desired steady state:

~~~text
single_svg                  PASS
finite_svg                  PASS
orthogonal_arrows           PASS
label_route_clearance       PASS
relationship_crossings      PASS
relationship_corridors      PASS
container_border_runs       PASS
route_rhythm                PASS
legend_clearance            PASS

properCrossings             0
ambiguousCorridors          0
labelRouteClearanceIssues   0
desktopReadabilityIssues    0
routesOverSuggestedBends    0
routesOverSuggestedStretch  0
microSegmentCount           0
~~~

A passing diagram sitting exactly on a threshold is fragile. Prefer margin where possible.

## 12. Generated artifact rules

Typed source:

~~~text
docs/architecture/diagrams/**
~~~

Generated presentation:

~~~text
docs/architecture/generated/**
~~~

Rules:

~~~text
- canonical Markdown / ADR owns architecture meaning
- typed source owns diagram structure
- generated HTML is derived presentation output
- never hand-edit generated HTML for durable meaning
- rerender after typed-source changes
- typography/navigation changes must come from deterministic scripts
- commit typed source + generated artifact together after successful validation when practical
~~~

## 13. CI and version consistency

Where a GitHub workflow exists, use:

~~~text
pinned Archify version
→ CherryStock preflight
→ showcase validation
→ deliver HTML
→ deterministic post-processing
→ synchronize artifact only after PASS
~~~

Current workflows:

~~~text
.github/workflows/render-archify-analytics.yml
.github/workflows/render-archify-agent-harness.yml
~~~

Do not assume local and CI Archify versions behave identically.

## 14. Safe editing procedure

Before changing any Archify typed source:

~~~text
A. Read this guide.
B. Read canonical architecture Markdown / ADR.
C. Inspect all node positions/sizes and all connections.
D. Identify semantic lanes and affected corridors.
E. Check component bounds against viewBox.
F. Check readability budget before widening viewBox.
G. Keep direct connection gaps >= 24px, preferably >= 30px.
H. Make the smallest coherent layout change.
I. Run CherryStock preflight.
J. Run Archify showcase validation.
K. Classify any failure by stage and fix root cause.
L. Deliver/post-process only after validate PASS.
M. Visually inspect final HTML.
N. Commit typed source + generated artifact.
~~~

## 15. Anti-patterns

~~~text
DO NOT:
- patch generated HTML to hide validation defects
- widen viewBox horizontally without checking font scale
- insert a node into an existing corridor without checking unrelated edges
- add many via points to compensate for bad placement
- assume automatic routing repairs congested topology
- assume explicit routing remains valid after neighboring nodes move
- put every dependency on the overview page
- add more than 3 evidence sources to one component
- put drill-down navigation in component.sources
- rename stable component ids for cosmetics
- claim PASS because preflight passed
- claim PASS from an earlier revision
~~~

## 16. Completion checklist

Before declaring an Archify-backed architecture synchronized:

~~~text
[ ] This guide was read
[ ] Canonical architecture / ADR is correct
[ ] Diagram scope fits high-level vs drill-down
[ ] Semantic lanes are explicit
[ ] Component ids are stable and unique
[ ] <= 3 evidence sources per component
[ ] Every source path exists
[ ] All connection endpoints resolve
[ ] Existing corridors were rechecked after node moves/inserts
[ ] Explicit direct connections have >= 24px clearance
[ ] viewBox satisfies readability budget
[ ] Labels and sublabels are concise
[ ] CherryStock preflight PASS
[ ] Archify showcase returns "ok": true
[ ] Checker reports zero composition errors
[ ] Deliver succeeds
[ ] Typography/navigation post-processing succeeds
[ ] Generated HTML visually reviewed
[ ] Typed source and generated HTML synchronized in Git
~~~

## 17. Maintenance rule

Whenever a new recurring Archify failure is discovered:

~~~text
1. record symptom + root cause + durable fix in this guide
2. add a generic deterministic preflight check when safe
3. update Archify Instructions if mandatory behavior changes
4. do not encode one diagram's node ids into shared validation logic
~~~

## 18. Core principle

Archify failures should improve the repository guardrails.

~~~text
new failure
→ identify root cause
→ repair architecture presentation correctly
→ document the pattern here
→ add preflight guardrail when deterministic
→ prevent recurrence across every diagram
~~~

This file is the durable CherryStock knowledge base for avoiding Archify generation regressions.
