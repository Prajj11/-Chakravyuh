"""Directed observed interactions, separate sync edges and evidence-based role precedence."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

import networkx as nx
import numpy as np

from app.config import Parameters
from app.coordination.engine import CoordinationResult
from app.graph_engine.centrality import exact_betweenness
from app.schemas.models import (
    AccountRole,
    AnalysisStatus,
    ComputationMode,
    GraphEdge,
    GraphNode,
    InteractionType,
    TimelineBucket,
    UnifiedSocialEvent,
)


@dataclass(frozen=True)
class GraphResult:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    timeline: list[TimelineBucket]


class GraphEngine:
    def __init__(self, parameters: Parameters) -> None:
        self.p = parameters

    def build(
        self, events: Sequence[UnifiedSocialEvent], coordination: CoordinationResult
    ) -> GraphResult:
        if not events:
            return GraphResult([], [], [])
        p = self.p
        parameter_id = p.parameter_set_id
        by_id = {event.event_id: event for event in events}
        authors: dict[str, list[UnifiedSocialEvent]] = defaultdict(list)
        for event in by_id.values():
            authors[event.account.account_id].append(event)
        interaction = nx.DiGraph()
        projection = nx.Graph()
        interaction.add_nodes_from(sorted(authors))
        projection.add_nodes_from(sorted(authors))
        edges: list[GraphEdge] = []
        for event in sorted(
            by_id.values(), key=lambda event: (event.timestamp_utc, event.event_id)
        ):
            if event.interaction_type not in {
                InteractionType.REPOST,
                InteractionType.QUOTE,
                InteractionType.REPLY,
            }:
                continue
            parent = by_id.get(event.parent_event_id or "")
            if parent is None or parent.account.account_id == event.account.account_id:
                continue
            source, target = parent.account.account_id, event.account.account_id
            interaction.add_edge(
                source,
                target,
                weight=interaction.get_edge_data(source, target, {}).get("weight", 0) + 1,
            )
            projection.add_edge(
                source,
                target,
                weight=projection.get_edge_data(source, target, {}).get("weight", 0) + 1,
            )
            edges.append(
                GraphEdge(
                    computation_mode=ComputationMode.COMPUTED_PIPELINE,
                    analysis_status=AnalysisStatus.AVAILABLE,
                    parameter_set_id=parameter_id,
                    coverage_ratio=1,
                    evidence_reasons=[
                        "Observed source-to-amplifier interaction; unresolved parents are omitted."
                    ],
                    source=source,
                    target=target,
                    interaction_type="ORGANIC_REPLY"
                    if event.interaction_type == InteractionType.REPLY
                    else "REPOST_CASCADE",
                    matched_event_ids=[parent.event_id, event.event_id],
                    time_delta_sec=abs(
                        (event.timestamp_utc - parent.timestamp_utc).total_seconds()
                    ),
                )
            )
        for edge in coordination.edges:
            projection.add_edge(
                edge.source,
                edge.target,
                weight=projection.get_edge_data(edge.source, edge.target, {}).get("weight", 0)
                + edge.weight,
            )
            edges.append(
                GraphEdge(
                    computation_mode=ComputationMode.COMPUTED_PIPELINE,
                    analysis_status=AnalysisStatus.AVAILABLE,
                    parameter_set_id=parameter_id,
                    coverage_ratio=1,
                    evidence_reasons=[
                        "Disjoint repeated matches; deltas (seconds): "
                        f"{[match.delta for match in edge.matches]}"
                    ],
                    source=edge.source,
                    target=edge.target,
                    interaction_type="CO_POST_SYNC",
                    sync_weight=edge.weight,
                    matched_event_ids=[
                        event_id
                        for match in edge.matches
                        for event_id in (match.event_a, match.event_b)
                    ],
                    time_delta_sec=float(np.mean([match.delta for match in edge.matches])),
                )
            )
        communities = (
            nx.community.louvain_communities(
                projection, weight="weight", resolution=p.LOUVAIN_RESOLUTION, seed=p.RANDOM_SEED
            )
            if projection.number_of_edges()
            else [{author} for author in sorted(authors)]
        )
        communities = sorted(communities, key=lambda community: tuple(sorted(community)))
        membership = {
            author: index for index, community in enumerate(communities) for author in community
        }
        centrality = exact_betweenness(interaction)
        percentile = float(np.percentile(list(centrality.values()), p.BRIDGE_CENTRALITY_PERCENTILE))
        low = {author for author in authors if self.low_indicator(author, coordination)}
        low_communities = set()
        for index, community in enumerate(communities):
            scored = {
                author
                for author in community
                if coordination.bots[author].bot_indicator_score is not None
            }
            if scored and len(scored & low) > len(scored) / 2:
                low_communities.add(index)
        earliest = min(
            events, key=lambda event: (event.timestamp_utc, event.account.account_id)
        ).account.account_id
        nodes = []
        for author, observed in sorted(authors.items()):
            bot = coordination.bots[author]
            sync = coordination.accounts[author]
            neighbours = set(interaction.predecessors(author)) | set(interaction.successors(author))
            links_group = bool((neighbours | {author}) & coordination.coordinated_authors)
            links_low = any(membership[neighbour] in low_communities for neighbour in neighbours)
            bridge = (
                centrality[author] > 0
                and centrality[author] >= percentile
                and len(neighbours) >= p.BRIDGE_MIN_INTERACTION_EDGES
                and links_group
                and links_low
            )
            role = (
                AccountRole.EARLIEST_OBSERVED_SEED
                if author == earliest
                else AccountRole.BOT_AMPLIFIER
                if bot.bot_indicator_score is not None
                and bot.bot_indicator_score >= p.BOT_PROBABILITY_HIGH_CUTOFF
                and sync.sync_score is not None
                and sync.sync_score >= p.BOT_SYNC_SCORE_CUTOFF
                else AccountRole.BRIDGE_INFLUENCER
                if bridge
                else AccountRole.ORGANIC_USER
                if author in low
                else AccountRole.UNCLASSIFIED
            )
            profile = max(observed, key=lambda event: (event.timestamp_utc, event.event_id)).account
            nodes.append(
                GraphNode(
                    computation_mode=ComputationMode.COMPUTED_PIPELINE,
                    analysis_status=AnalysisStatus.AVAILABLE,
                    parameter_set_id=parameter_id,
                    coverage_ratio=bot.coverage_ratio,
                    missing_signals=bot.missing_signals,
                    evidence_reasons=[
                        f"Role precedence selected {role.value}.",
                        "Low indicators require sufficient evidence; "
                        "other uncertain/intermediate accounts remain unclassified.",
                        "Earliest seed is bounded by this observed collection.",
                    ],
                    id=author,
                    handle=profile.handle,
                    role=role,
                    bot_assessment=bot,
                    sync_assessment=sync,
                    posts_in_campaign=len(observed),
                    community_id=membership[author],
                    betweenness_centrality=centrality[author],
                    cascade_out_degree=interaction.out_degree(author),
                    region=profile.profile_location,
                    account_created_at=profile.created_at,
                    first_observed_utc=min(event.timestamp_utc for event in observed),
                )
            )
        node_map = {node.id: node for node in nodes}
        edges = [
            edge.model_copy(update={"interaction_type": "BRIDGE_TRANSFER"})
            if edge.interaction_type == "REPOST_CASCADE"
            and any(
                node_map[author].role == AccountRole.BRIDGE_INFLUENCER
                for author in (edge.source, edge.target)
            )
            else edge
            for edge in edges
        ]
        bins: dict[int, list[int]] = defaultdict(lambda: [0, 0, 0])
        dates = {}
        for event in by_id.values():
            bucket = int(event.timestamp_utc.timestamp() // p.SYNC_BUCKET_SEC)
            dates[bucket] = event.timestamp_utc.replace(second=0, microsecond=0)
            author = event.account.account_id
            index = 0 if author in coordination.coordinated_authors else 1 if author in low else 2
            bins[bucket][index] += 1
        timeline = [
            TimelineBucket(
                timestamp_utc=dates[bucket],
                coordinated_volume=counts[0],
                low_indicator_volume=counts[1],
                unclassified_volume=counts[2],
                burst_index=coordination.assessment.burst_index,
            )
            for bucket, counts in sorted(bins.items())
        ]
        return GraphResult(nodes, edges, timeline)

    def low_indicator(self, author: str, coordination: CoordinationResult) -> bool:
        bot, sync = coordination.bots[author], coordination.accounts[author]
        return (
            bot.bot_indicator_score is not None
            and bot.bot_indicator_score < self.p.ORGANIC_BOT_MAX_EXCLUSIVE
            and sync.sync_score is not None
            and sync.sync_score < self.p.ORGANIC_SYNC_MAX_EXCLUSIVE
            and bot.coverage_ratio >= self.p.ORGANIC_MIN_FEATURE_COVERAGE
            and bot.observed_posts >= self.p.ANALYSIS_MIN_ACCOUNT_POSTS
            and bot.observation_seconds >= self.p.ANALYSIS_MIN_OBSERVATION_SEC
        )
