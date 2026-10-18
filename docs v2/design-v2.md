# UI/UX and Visualization Design: Chakravyuh

**Contract version:** 2.1.0  
**Updated:** October 18, 2026  
**Theme:** Dark investigation workbench with visible evidence and uncertainty.

This file fully replaces the v1 design. Use backend enum values and nested assessments from [backendschema-v2.md](backendschema-v2.md). Screenshots, example values and narrative names are illustrative, never expected computed outputs.

## 1. Assessment hierarchy

The campaign header shows three distinct assessments:
- **Coordination:** measured campaign sync and coverage, with a separate **CTI prioritization** badge. CTI includes media, geography and harm as well as coordination; do not describe CTI as a pure coordination metric.
- **Media indicators:** measured ELA/model result, computation method and status; NO MEDIA differs from PENDING, UNSUPPORTED and FAILED.
- **Claim verification:** UNVERIFIED, CONTRADICTED_BY_SOURCE, CORROBORATED or CONTEXT_MISSING, reference link/snapshot and review attribution.

Show data origin (especially SYNTHETIC REPLAY), collection window, model/fallback mode, missing evidence and alert suppression beside relevant scores. Null is displayed as "Insufficient data" with reasons, never 0%. Bot/ELA scales use "/100 indicator", not probability or confidence percentages. Synchronization may use a ratio.

Display score tiers from unrounded CTI: LOW [0,40), MEDIUM [40,60), HIGH [60,75), CRITICAL [75,100]. A provisional critical-tier score can be alert-suppressed; badge and banner must explain that distinction.

## 2. Layout and cross-filtering

```text
Header: Chakravyuh | origin + stream state | scenarios | inject | export
---------------------------------------------------------------------
Campaign feed | Tabs: Graph / Geography / Media / Claims | Account drawer
              |                                        | scores, reasons
              | Selected campaign workbench             | source evidence
              |                                        | observation limits
              |----------------------------------------|
              | Propagation timeline and event-time cursor
```

Campaign selection loads one snapshot revision for every panel. Node/edge selection filters its posts and highlights linked timeline evidence. Geographic selection filters the same campaign/window; clearing filters restores the complete snapshot. Controls must never silently change the underlying analytical score.

Desktop uses three columns; narrow layouts collapse the feed and drawer into accessible panels and render one workbench tab at a time. Maintain keyboard focus and escape-to-close behavior for dialogs. Do not rely on color alone for roles or alerts.

## 3. Palette and typography

| Token / role | Color | Meaning |
|---|---|---|
| canvas | #070B14 | app background |
| panel | #0F172A | primary surfaces |
| elevated | #1E293B | drawer/modal |
| border | #334155 | separators |
| primary | #38BDF8 | active controls |
| EARLIEST_OBSERVED_SEED | #EF4444 | earliest observed, not a guilt label |
| BOT_AMPLIFIER | #F59E0B | bot/coordination indicators pass gates |
| BRIDGE_INFLUENCER | #A855F7 | qualifying bridge pattern |
| ORGANIC_USER | #10B981 | low observed indicators |
| UNCLASSIFIED | #94A3B8 | insufficient/intermediate evidence |
| CRITICAL | #F43F5E | CTI >=75; alert eligibility shown separately |
| HIGH | #FB923C | CTI >=60 and <75 |

Use Inter/Plus Jakarta Sans with a bundled Devanagari-capable fallback for narratives, and JetBrains Mono/Fira Code with tabular numerals for hashes, times, indices and scores. Include units and UTC labels. Present full hashes in copyable expanded views; shortening is only visual.

## 4. Coordination graph and dossier

Canvas force layout is mandatory above 200 nodes. Use deterministic initial positions, cleanup on unmount and debounced filters. Provide a searchable accessible node list alongside the canvas.

Controls: sync threshold slider 0.20-0.95, reset 0.65, role toggles including UNCLASSIFIED, full discourse / candidate coordinated groups / observed cascade lenses, and time range. Sync slider filters synchronization edges only; interaction edges remain distinguishable and can be toggled separately. Louvain community hulls indicate topology, not proven bot ownership.

Node hover shows role, first observed UTC, bot indicator, sync, and coverage. Clicking opens a drawer with nested bot_assessment and sync_assessment, separate computation methods, effective feature weights, observed span/post count, evidence reasons and linked posts. Show "Earliest observed in collected data" for the seed; reach/centrality are separate fields.

Edges distinguish repost/reply direction from symmetric co-posting. Edge details show exact matched event IDs, time deltas, repeated minute buckets and normalized weight. No matching edges shows a reset control, not an empty unexplained canvas.

## 5. Geographic workbench

Draw H3 resolution-5 cells and source-to-target arcs with optional independently computed resolution-7 display. Offline mode uses bundled geography/coordinate grid; remote tiles are optional.

Each cell shows current volume, historical scope, valid bucket count, Z or missing-baseline reason, GMR or unknown-source reason, source coverage, known-source posts/authors and GPS-vs-declared composition. Name the baseline topic-family and collector scope. Declared source locations are labelled as declarations.

Separate "Regional spike" from "Astroturfing indicator." Show all failed sample/coverage/coordination gates in the tooltip. Low-coverage arcs can be inspected but never imply known physical origin. Unresolved source coordinates produce no invented arc.

## 6. Timeline, media and claim review

Timeline uses one-minute event-time bins with coordinated-volume, low-observed-indicator-volume and unclassified-volume series whose sum equals observed volume. Display actual burst_index when sufficient; show Hawkes as unsupported in MVP. Mark alerts and collection gaps; speed control affects replay, not measured event intervals.

Media panel compares original and computed ELA overlay using an accessible split slider and toggles. Show pHash candidate matches, exact-byte SHA-256, EXIF presence, C2PA status and adapter/model revision. Missing EXIF never reads "stripped" without evidence. Unsupported video/audio has a clear status and no fabricated heatmap, face boxes or lip-sync measurement.

Claims tab displays candidate references, source/snapshot, date, region, similarity and context notes. A human reviewer selects a permitted status and submits a note; client cannot assign reviewer identity. Synthetic references carry an unavoidable label and cannot be used on public/injected campaigns.

## 7. Jobs, replay and export

Scenario controls choose electoral coordination, geographic mismatch, organic baseline or all, with seed and speed. Show queued/running jobs and the active event-time cursor. Scenario reset confirms state replacement in the UI; retained evidence persists. No automatic arbitrary scenario CTI is promised.

Injection accepts text, optional actor ID/time/location and uploaded media IDs. Default location is unknown; no automatic "External Proxy" coordinates. Upload validates status before submission and never accepts fabricated public-source origin.

Export dialog defaults to redaction of ORGANIC_USER and UNCLASSIFIED participants; offers bundle/PDF/HTML/STIX. Explain that downloads are investigative packages with limitations. Queue export, show integrity failures and download only completed verified artifacts. A local download has no external dispatch step.

## 8. Loading, error and accessibility states

| State | Behavior |
|---|---|
| Initial load / scenario job | skeletons plus job state; avoid presenting old data as new |
| Stream connected | live connection status independent of data origin |
| Reconnecting | 1/2/4/8-second backoff, cap 30s; REST/job polling every 3s |
| Expired stream sequence | REST resync all selected campaign panels |
| Missing evidence | null score, coverage meter, reason and available raw observations |
| Empty graph/filter | empty-state explanation and reset controls |
| Worker/media error | scoped retry and error code; other views stay usable |
| Integrity mismatch | blocked export with affected artifact and safe diagnostic |
| Offline map/model | explicit fallback mode; investigation remains usable |

Honor reduced-motion settings; offer static arcs and disable flashing. Use text/icon alerts, sufficient contrast, labelled controls, accessible tooltips and keyboard alternatives. Verify long multilingual narratives, narrow screens, null values and large graph selections visually before release.
