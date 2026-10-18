"""Exact unweighted directed Brandes centrality; parity-tested against NetworkX."""

import networkx as nx
import rustworkx as rx


def exact_betweenness(graph: nx.DiGraph) -> dict[str, float]:
    nodes = sorted(graph.nodes)
    if not all(isinstance(node, str) for node in nodes):
        raise TypeError("Graph identities must be qualified strings")
    if len(nodes) < 3:
        return {node: 0.0 for node in nodes}
    native = rx.PyDiGraph(multigraph=False)
    native.add_nodes_from(nodes)
    indices = {node: index for index, node in enumerate(nodes)}
    native.add_edges_from_no_data(
        [(indices[source], indices[target]) for source, target in sorted(graph.edges)]
    )
    # Sequential accumulation keeps the exact calculation deterministic across runs.
    values = rx.digraph_betweenness_centrality(
        native, normalized=True, endpoints=False, parallel_threshold=len(nodes) + 1
    )
    return {node: float(values[index]) for index, node in enumerate(nodes)}
