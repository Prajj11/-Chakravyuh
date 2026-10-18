import networkx as nx
import pytest

from app.graph_engine.centrality import exact_betweenness


@pytest.mark.parametrize("size", [0, 1, 2, 10, 30])
@pytest.mark.parametrize("seed", [7, 41, 93])
def test_exact_native_centrality_matches_networkx(size: int, seed: int) -> None:
    graph = nx.gnp_random_graph(size, 0.16, seed=seed, directed=True)
    graph = nx.relabel_nodes(graph, {node: f"simulator:{node:03d}" for node in graph.nodes})
    reference = nx.betweenness_centrality(graph, normalized=True, weight=None)
    actual = exact_betweenness(graph)
    assert actual == pytest.approx(reference, abs=1e-12)
    assert exact_betweenness(graph) == actual
