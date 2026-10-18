"""Content-linked repeated co-post observations and explicitly scaled bot heuristics."""

import math
import re
import statistics
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import timedelta
from itertools import combinations

from app.config import Parameters
from app.nlp_engine.engine import normalize_url
from app.schemas.models import (
    AccountSyncAssessment,
    AnalysisStatus,
    BotAssessment,
    ComputationMode,
    CoordinationAssessment,
    InteractionType,
    UnifiedSocialEvent,
)

Similarity = Callable[[UnifiedSocialEvent, UnifiedSocialEvent], float]


@dataclass(frozen=True)
class PairMatch:
    event_a: str
    event_b: str
    delta: float
    bucket: int


@dataclass(frozen=True)
class SyncEdge:
    source: str
    target: str
    weight: float
    matches: tuple[PairMatch, ...]


@dataclass(frozen=True)
class CoordinationResult:
    assessment: CoordinationAssessment
    accounts: dict[str, AccountSyncAssessment]
    bots: dict[str, BotAssessment]
    edges: list[SyncEdge]
    coordinated_authors: frozenset[str]


def span(events: Sequence[UnifiedSocialEvent]) -> float:
    return (
        (
            max(event.timestamp_utc for event in events)
            - min(event.timestamp_utc for event in events)
        ).total_seconds()
        if events
        else 0
    )


class CoordinationEngine:
    def __init__(self, parameters: Parameters) -> None:
        self.p = parameters

    def linked(
        self,
        a: UnifiedSocialEvent,
        b: UnifiedSocialEvent,
        similarity: Similarity,
        phashes: dict[str, str],
        media_hashes: dict[str, tuple[str, ...]] | None = None,
    ) -> bool:
        if {normalize_url(url) for url in a.urls} & {normalize_url(url) for url in b.urls}:
            return True
        hashes_a = {media.sha256_hash for media in a.media_attachments if media.sha256_hash} | set(
            (media_hashes or {}).get(a.event_id, ())
        )
        hashes_b = {media.sha256_hash for media in b.media_attachments if media.sha256_hash} | set(
            (media_hashes or {}).get(b.event_id, ())
        )
        if hashes_a & hashes_b:
            return True
        for left in hashes_a:
            for right in hashes_b:
                if (
                    left in phashes
                    and right in phashes
                    and (int(phashes[left], 16) ^ int(phashes[right], 16)).bit_count()
                    <= self.p.PHASH_MAX_DISTANCE
                ):
                    return True
        return similarity(a, b) >= self.p.SEMANTIC_CLUSTER_SIMILARITY

    def analyze(
        self,
        events: Sequence[UnifiedSocialEvent],
        *,
        similarity: Similarity,
        phashes: dict[str, str] | None = None,
        media_hashes: dict[str, tuple[str, ...]] | None = None,
        account_hourly_baselines: dict[str, tuple[int, ...]] | None = None,
    ) -> CoordinationResult:
        p = self.p
        all_events = list({event.event_id: event for event in events}.values())
        if len({event.data_origin for event in all_events}) > 1:
            raise ValueError("Origins cannot share coordination state")
        if all_events:
            watermark = max(event.timestamp_utc for event in all_events)
            all_events = [
                event
                for event in all_events
                if event.timestamp_utc > watermark - timedelta(hours=p.NARRATIVE_WINDOW_HOURS)
            ]
        authors: dict[str, list[UnifiedSocialEvent]] = defaultdict(list)
        for event in all_events:
            authors[event.account.account_id].append(event)
        edges = []
        repeated_copies: set[str] = set()
        for left, right in combinations(sorted(authors), 2):
            candidates = []
            for a in authors[left]:
                for b in authors[right]:
                    delta = abs((a.timestamp_utc - b.timestamp_utc).total_seconds())
                    if delta <= p.TEMPORAL_CO_POST_WINDOW_SEC and self.linked(
                        a, b, similarity, phashes or {}, media_hashes
                    ):
                        candidates.append(
                            (delta, min(a.timestamp_utc, b.timestamp_utc), a.event_id, b.event_id)
                        )
                        repeated_copies.update((a.event_id, b.event_id))
            used: set[str] = set()
            matches = []
            for delta, earlier, a_id, b_id in sorted(candidates):
                if a_id not in used and b_id not in used:
                    used.update((a_id, b_id))
                    matches.append(
                        PairMatch(a_id, b_id, delta, int(earlier.timestamp() // p.SYNC_BUCKET_SEC))
                    )
            if len({match.bucket for match in matches}) >= p.SYNC_MIN_DISTINCT_BUCKETS:
                weight = 1 - math.exp(
                    -sum(math.exp(-match.delta / p.TEMPORAL_DECAY_TAU_SEC) for match in matches)
                )
                edges.append(SyncEdge(left, right, weight, tuple(matches)))
        account_reports = {}
        for author, observed in sorted(authors.items()):
            eligible = (
                len(observed) >= p.ANALYSIS_MIN_ACCOUNT_POSTS
                and span(observed) >= p.ANALYSIS_MIN_OBSERVATION_SEC
            )
            peers = sorted(
                [edge for edge in edges if author in (edge.source, edge.target)],
                key=lambda edge: (-edge.weight, edge.source, edge.target),
            )
            top = peers[: p.ACCOUNT_TOP_SYNC_PEERS]
            deltas = [match.delta for edge in peers for match in edge.matches]
            account_reports[author] = AccountSyncAssessment(
                computation_mode=ComputationMode.COMPUTED_PIPELINE,
                analysis_status=AnalysisStatus.AVAILABLE
                if eligible
                else AnalysisStatus.INSUFFICIENT_DATA,
                parameter_set_id=p.parameter_set_id,
                coverage_ratio=min(span(observed) / p.ANALYSIS_MIN_OBSERVATION_SEC, 1)
                if len(observed) >= p.ANALYSIS_MIN_ACCOUNT_POSTS
                else 0,
                missing_signals=[] if eligible else ["account_post_count_or_span"],
                evidence_reasons=[
                    "Mean of strongest repeated content-linked peers. "
                    "Synchrony does not prove automation."
                ],
                feature_contributions={
                    edge.target if edge.source == author else edge.source: edge.weight / len(top)
                    for edge in top
                }
                if eligible
                else {},
                sync_score=sum(edge.weight for edge in top) / len(top)
                if top and eligible
                else 0
                if eligible
                else None,
                matched_peer_count=len(peers),
                repeated_bucket_count=len(
                    {match.bucket for edge in peers for match in edge.matches}
                ),
                mean_matched_delta_sec=statistics.mean(deltas) if deltas else None,
            )
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)
        components = []
        visited: set[str] = set()
        for author in sorted(adjacency):
            if author in visited:
                continue
            pending = [author]
            component: set[str] = set()
            while pending:
                member = pending.pop()
                if member in component:
                    continue
                component.add(member)
                pending.extend(adjacency[member] - component)
            visited |= component
            if len(component) >= p.COORDINATION_MIN_AUTHORS:
                component_edges = [
                    edge for edge in edges if edge.source in component and edge.target in component
                ]
                mean = statistics.mean(edge.weight for edge in component_edges)
                components.append((mean, tuple(sorted(component)), component_edges))
        components.sort(key=lambda component: (-component[0], component[1]))
        selected = components[0][2] if components else []
        coordinated = frozenset(
            author
            for mean, group, _ in components
            if mean >= p.BOT_SYNC_SCORE_CUTOFF
            for author in group
        )
        sufficient = (
            len(all_events) >= p.COORDINATION_MIN_POSTS
            and len(authors) >= p.COORDINATION_MIN_AUTHORS
            and span(all_events) >= p.ANALYSIS_MIN_OBSERVATION_SEC
        )
        burst = self.burst(all_events)
        report = CoordinationAssessment(
            computation_mode=ComputationMode.COMPUTED_PIPELINE,
            analysis_status=AnalysisStatus.AVAILABLE
            if sufficient
            else AnalysisStatus.INSUFFICIENT_DATA,
            parameter_set_id=p.parameter_set_id,
            coverage_ratio=sum(report.sync_score is not None for report in account_reports.values())
            / len(authors)
            if authors
            else 0,
            missing_signals=[] if sufficient else ["campaign_post_author_count_or_span"],
            evidence_reasons=[
                "Maximum component mean across components with at least three observed authors.",
                "Hawkes estimator is unsupported; minute-bin dispersion is descriptive only.",
            ],
            feature_contributions={
                edge.source + "|" + edge.target: edge.weight / len(selected) for edge in selected
            }
            if sufficient
            else {},
            sync_score=components[0][0] if sufficient and components else 0 if sufficient else None,
            eligible_pair_count=len(edges),
            coordinated_account_count=len(coordinated),
            total_account_count=len(authors),
            burst_index=burst,
        )
        bots = {
            author: self.bot(
                observed,
                all_events,
                account_reports[author],
                repeated_copies,
                (account_hourly_baselines or {}).get(author, ()),
            )
            for author, observed in authors.items()
        }
        return CoordinationResult(report, account_reports, bots, edges, coordinated)

    def burst(self, events: Sequence[UnifiedSocialEvent]) -> float | None:
        if len(events) < self.p.BURST_MIN_EVENTS:
            return None
        first = int(
            min(event.timestamp_utc.timestamp() for event in events) // self.p.SYNC_BUCKET_SEC
        )
        last = int(
            max(event.timestamp_utc.timestamp() for event in events) // self.p.SYNC_BUCKET_SEC
        )
        if last - first < self.p.BURST_MIN_COMPLETE_BINS:
            return None
        counts = [0] * (last - first)
        for event in events:
            bucket = int(event.timestamp_utc.timestamp() // self.p.SYNC_BUCKET_SEC)
            if bucket < last:
                counts[bucket - first] += 1
        return statistics.variance(counts) / max(statistics.mean(counts), 1)

    def bot(
        self,
        events: Sequence[UnifiedSocialEvent],
        campaign_events: Sequence[UnifiedSocialEvent],
        sync: AccountSyncAssessment,
        repeated_copies: set[str],
        hourly_baseline: tuple[int, ...],
    ) -> BotAssessment:
        p = self.p
        profile = events[-1].account
        observed_span = span(events)
        features: dict[str, float] = {}
        if sync.sync_score is not None:
            features["sync_tightness"] = 100 * sync.sync_score
        others = {
            event.account.account_id: event.account
            for event in campaign_events
            if event.account.account_id != profile.account_id
            and event.account.created_at is not None
        }
        if profile.created_at is not None and len(others) >= p.CREATION_BATCH_MIN_KNOWN_PEERS:
            nearby = sum(
                abs((other.created_at - profile.created_at).total_seconds())
                <= p.CREATION_BATCH_WINDOW_HOURS * 3600
                for other in others.values()
                if other.created_at is not None
            )
            features["creation_batch_density"] = 100 * min(
                nearby / p.CREATION_BATCH_DENSITY_DENOMINATOR, 1
            )
        if len(events) >= p.ANALYSIS_MIN_ACCOUNT_POSTS:
            amplified = sum(
                event.interaction_type in {InteractionType.REPOST, InteractionType.QUOTE}
                or event.event_id in repeated_copies
                for event in events
            )
            features["amplification_ratio"] = 100 * amplified / len(events)
        if (
            len(hourly_baseline) >= p.GEO_BASELINE_MIN_HOURLY_BUCKETS
            and observed_span >= p.ANALYSIS_MIN_OBSERVATION_SEC
            and len(events) >= p.ANALYSIS_MIN_ACCOUNT_POSTS
        ):
            hourly_rate = len(events) * 3600 / observed_span
            features["posting_rate_burst"] = 100 * min(
                max(
                    (hourly_rate / max(statistics.mean(hourly_baseline), 1) - 1)
                    / p.POSTING_RATE_BURST_SCALE,
                    0,
                ),
                1,
            )
        if profile.handle.strip():
            digits = re.search(r"\d+$", profile.handle)
            features["handle_entropy"] = (
                100 * min(len(digits[0]) / p.HANDLE_TRAILING_DIGIT_CAP, 1) if digits else 0
            )
        available = {key: p.BOT_FEATURE_WEIGHTS[key] for key in features}
        coverage = sum(available.values())
        sufficient = (
            coverage >= p.BOT_MIN_FEATURE_COVERAGE
            and len(events) >= p.ANALYSIS_MIN_ACCOUNT_POSTS
            and observed_span >= p.ANALYSIS_MIN_OBSERVATION_SEC
        )
        contributions = (
            {key: features[key] * weight / coverage for key, weight in available.items()}
            if sufficient
            else {}
        )
        return BotAssessment(
            computation_mode=ComputationMode.HEURISTIC_INDICATOR,
            analysis_status=AnalysisStatus.AVAILABLE
            if sufficient
            else AnalysisStatus.INSUFFICIENT_DATA,
            parameter_set_id=p.parameter_set_id,
            coverage_ratio=coverage,
            missing_signals=sorted(set(p.BOT_FEATURE_WEIGHTS) - features.keys()),
            evidence_reasons=[
                "Available-feature weighted indicator; not a calibrated bot probability.",
                "Requires sufficient posts, span and feature coverage.",
            ],
            feature_contributions=contributions,
            bot_indicator_score=sum(contributions.values()) if sufficient else None,
            observed_posts=len(events),
            observation_seconds=observed_span,
            available_feature_weights=available,
        )
