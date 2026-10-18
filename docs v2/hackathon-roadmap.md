# Hackathon differentiation roadmap

**Prepared:** October 19, 2026

**Status:** Proposals for prioritization, not new release requirements or implemented analytical capabilities. The ten versioned v2 documents remain the active contract.

## Positioning

Pitch Chakravyuh as an evidence-led investigation workspace: observe a campaign forming, explain why it was flagged, inspect the original evidence and produce a reproducible dossier. Coordination does not establish falsity. A credible demonstration of that distinction is a product strength.

Graphs, narrative tracking and community analysis are established capabilities; [Graphika's platform](https://www.graphika.com/platform) describes these workflows. The recommendations below are project-specific judging advantages, not claims of industry-first invention. [Bellingcat's toolkit](https://bellingcat.gitbook.io/toolkit) illustrates the breadth of verification, mapping and archiving tasks investigators already use.

The current release already has graph and geographic views, computed image indicators, independent claim review, replay, warning gates, integrity-verified exports and an offline evaluation. The October 19 UI revision adds a deterministic evidence-linked brief, search and triage filters. The proposals below extend that foundation; none is automatically implemented by the UI refresh.

## Highest-value additions

| Priority | Feature | Concrete demo moment | Scope and evidence requirements |
|---|---|---|---|
| 1 | **Narrative evolution tree** | Show an English claim reworded in Hindi/Hinglish, then reused as a meme caption; select each version to read its source posts. | Extract claim variants and OCR text, cluster within a campaign and display language, first observed UTC and linked event IDs. Edges describe observed similarity and temporal order, not proven influence. Preserve original text alongside translations, mark model/fallback method, and show ambiguous matches. |
| 2 | **Campaign time machine** | Rewind to before the first warning, then watch eligible links and CTI emerge as observations arrive. | Add immutable historical analytical snapshots or deterministic as-of replay. Display event time, collection time, snapshot revision, parameters and missing evidence. Recompute from only observations available at that cutoff; avoid future-data leakage. The existing timeline is a visual filter of the current snapshot and must not be relabeled as this feature. |
| 3 | **False-positive and resilience lab** | Put coordinated manipulation beside genuine emergency mobilisation; explain why coordination alone should not trigger the same conclusion. | Reuse actual engines and add held-out benign campaigns, paraphrases, jittered timestamps, duplicate posts, multilingual variants and missing-location conditions. Report precision/recall, false alerts, abstentions, coverage and alert delay by scenario/language. Keep challenge labels out of runtime features; display the synthetic/real split and sample sizes. |
| 4 | **Media context lineage** | Find the same older photograph reused under a new date or location, then compare the captions and retained references. | Connect exact/perceptual hashes, OCR, collection history and source references. Add authorized public reference lookup or curated source snapshots. Distinguish a related image from proof of its original capture date/location. ELA remains an indicator, not a deepfake verdict. |
| 5 | **Ask the case, with citations** | Ask “What supports this warning?” and open the exact event IDs behind each answer. | Build on the shipped deterministic brief. Retrieve only authorized retained case evidence; enforce citations, abstain on unsupported questions and treat post text as data rather than instructions. Redact before any external model call; retain a local template fallback. Validate citation correctness and unsupported-claim rate on a fixed question set. |
| 6 | **Cross-campaign recurrence and caseboard** | Discover a repeated URL/media fingerprint in two retained campaigns and pin the evidence to a case. | Expose retained archive search through a scoped API/UI, then link by platform-qualified IDs, hashes and explicit shared evidence. Add notes, saved evidence cards and revision history. Shared content is not proof of common ownership; no inferred cross-platform identity matching. |
| 7 | **Bridge-removal simulation** | Hide one observed bridge in a copy of the graph and compare connected components and observed reachability. | Use explicit graph assumptions and show before/after connectivity, not predicted real-world impact. Label every result hypothetical; distinguish measured interactions from similarity edges. Keep it an analytical simulation with no external account action. |

If time permits only two major additions, build **narrative evolution** and the **time machine**. Add one well-designed benign-coordination challenge to the demo even before a full lab exists. A generic chatbot or a larger collection of unsupported detector badges is lower priority than these evidence workflows.

## Foundation before a public-data claim

Implement one permitted, allowlisted public connector end to end, including capture provenance, rate limits, resumable cursors, deletion/retention handling and visible collection gaps. Choose the platform only after verifying access and terms. Keep an explicit offline replay fallback for the presentation. Real-world performance requires a representative reviewed evaluation set; the current synthetic metrics cannot establish that performance.

For reference retrieval, [Google Fact Check Tools API](https://developers.google.com/fact-check/tools/api/reference/rest/) offers claim-search endpoints. A retrieved ClaimReview is candidate evidence: compare wording, date, location, language and provenance before human review. Do not inherit a search result's verdict as automatic ground truth. Keys, quotas and permitted use need verification during integration.

## A four-minute demonstration

1. **0:00–0:30 — Observe:** open a clearly labeled replay; state the investigation question and collection limits.
2. **0:30–1:20 — Detect:** show the first warning, coverage and the exact co-post evidence. With the proposed time machine, rewind to the last snapshot before the warning.
3. **1:20–2:10 — Explain:** inspect the earliest observed account and multilingual variants. With the proposed evolution tree, follow two variants to their original posts.
4. **2:10–3:00 — Challenge:** switch to a benign coordination control and explain suppression/uncertainty. Do not conflate high synchrony with false claims.
5. **3:00–4:00 — Verify:** inspect media/context, record a human claim review, export the tamper-evident dossier and verify its hashes.

Until the proposed features exist, demonstrate the existing timeline honestly as a view filter and use linked observations to compare wording manually. Judges should see a complete, working evidence path rather than screenshots of unimplemented capabilities.

## Current constraints to show honestly

- Image ELA/pHash are implemented; C2PA and audio/video model inference are not.
- Geography depends on available declared locations and coverage; it does not geolocate individuals from IP addresses.
- Local warning dispatch is gated; no automatic external countermeasures exist.
- The recorded Windows 1,000-node graph benchmark still misses the 800 ms target.
- Synthetic held-out evaluation and local browser checks do not establish deployment readiness or real-world accuracy.
