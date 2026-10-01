from __future__ import annotations

import pandas as pd


def build_relationship_table(
    pair_frequency: pd.DataFrame,
    jaccard: pd.DataFrame,
    pmi: pd.DataFrame,
) -> pd.DataFrame:

    if pair_frequency.empty:
        return pd.DataFrame(
            columns=[
                "skill_a",
                "skill_b",
                "pair_count",
                "jaccard",
                "pmi",
                "relationship_strength",
            ]
        )

    result = pair_frequency.merge(
        jaccard[
            [
                "skill_a",
                "skill_b",
                "jaccard",
            ]
        ],
        on=[
            "skill_a",
            "skill_b",
        ],
        how="left",
    )

    result = result.merge(
        pmi[
            [
                "skill_a",
                "skill_b",
                "pmi",
            ]
        ],
        on=[
            "skill_a",
            "skill_b",
        ],
        how="left",
    )

    result["jaccard"] = result["jaccard"].fillna(0.0)
    result["pmi"] = result["pmi"].fillna(0.0)

    result["relationship_strength"] = (
        result["jaccard"] * result["pmi"].clip(lower=0)
    )

    result["relationship_strength"] = (
        result["relationship_strength"].round(6)
    )

    return (
        result.sort_values(
            [
                "relationship_strength",
                "pair_count",
            ],
            ascending=[False, False],
        )
        .reset_index(drop=True)
    )


def calculate_network_metrics(
    edges_df: pd.DataFrame,
    min_weight: float = 1.0,
) -> tuple[pd.DataFrame, dict]:
    """
    Constructs a NetworkX graph from relationship edges and calculates:
    - Node degree, degree centrality, betweenness centrality, closeness centrality
    - Community clusters (modularity-based)
    - Global network properties (density, components, average degree)

    Returns:
        nodes_df: DataFrame with skill centrality and community assignments.
        topology: Summary dictionary of graph-level properties.
    """
    import networkx as nx
    from src.extraction.normalization import get_skill_category

    base_node_cols = [
        "skill", "degree", "degree_centrality", "betweenness_centrality",
        "closeness_centrality", "community_id", "category"
    ]

    empty_topology = {
        "num_nodes": 0,
        "num_edges": 0,
        "density": 0.0,
        "connected_components": 0,
        "avg_degree": 0.0,
    }

    if edges_df.empty:
        return pd.DataFrame(columns=base_node_cols), empty_topology

    # Filter edges by weight if provided
    active_edges = edges_df[edges_df["weight"] >= min_weight] if "weight" in edges_df.columns else edges_df
    if active_edges.empty:
        active_edges = edges_df

    G = nx.Graph()

    for _, row in active_edges.iterrows():
        u = str(row.get("source_skill", "")).strip()
        v = str(row.get("target_skill", "")).strip()
        if not u or not v:
            continue
        w = float(row.get("weight", 1.0))
        jaccard_val = float(row.get("jaccard", 0.0))
        strength = float(row.get("relationship_strength", 0.0))
        G.add_edge(u, v, weight=w, jaccard=jaccard_val, strength=strength)

    if G.number_of_nodes() == 0:
        return pd.DataFrame(columns=base_node_cols), empty_topology

    # Graph-level properties
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    density = round(float(nx.density(G)), 4)
    components = nx.number_connected_components(G)
    avg_degree = round(float(sum(dict(G.degree()).values()) / num_nodes), 2) if num_nodes > 0 else 0.0

    topology = {
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "density": density,
        "connected_components": components,
        "avg_degree": avg_degree,
    }

    # Centrality measures
    deg_dict = dict(G.degree())
    deg_cent = nx.degree_centrality(G)
    try:
        betw_cent = nx.betweenness_centrality(G, weight="weight")
    except Exception:
        betw_cent = {n: 0.0 for n in G.nodes()}

    try:
        close_cent = nx.closeness_centrality(G)
    except Exception:
        close_cent = {n: 0.0 for n in G.nodes()}

    # Community detection
    community_map: dict[str, int] = {}
    try:
        comms = list(nx.community.greedy_modularity_communities(G))
        for cid, comm in enumerate(comms):
            for node in comm:
                community_map[node] = cid + 1
    except Exception:
        # Fallback to connected components
        for cid, comp in enumerate(nx.connected_components(G)):
            for node in comp:
                community_map[node] = cid + 1

    node_rows = []
    for node in sorted(G.nodes()):
        node_rows.append({
            "skill": node,
            "degree": deg_dict.get(node, 0),
            "degree_centrality": round(deg_cent.get(node, 0.0), 4),
            "betweenness_centrality": round(betw_cent.get(node, 0.0), 4),
            "closeness_centrality": round(close_cent.get(node, 0.0), 4),
            "community_id": community_map.get(node, 1),
            "category": get_skill_category(node),
        })

    nodes_df = pd.DataFrame(node_rows).sort_values(
        ["betweenness_centrality", "degree"],
        ascending=[False, False]
    ).reset_index(drop=True)

    return nodes_df, topology