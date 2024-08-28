import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import string

import networkx as nx
import pandas as pd
import polars as pl
import numpy as np
import gravis as gv
import string

import re

gv_defaults = dict(
    show_edge_label=True,
    edge_label_data_source="attr",
    edge_curvature=0.3,
    
    use_links_force=True,
    links_force_distance=30,
    links_force_strength=0.05,
    
    use_collision_force=True,
    collision_force_radius=50,
    collision_force_strength=.7,
    
    use_y_positioning_force=True,
    y_positioning_force_strength=0.1
)

SPECIAL_HASHES = [
    "0x4200000000000000000000000000000000000006", 
    "0x0000000000000000000000000000000000000000"
]
    
    
def filter_main_df_from_tx_hash(load_df: pl.DataFrame, tx_hash):
    """
    read from polars, convert to pandas since networkx can read edgelists from it
    """
    
    # hash of the tx INSTIGATOR
    SOURCE_HASH = (
        load_df
        .filter(
            pl.col("hash") == tx_hash,
            pl.col("source") == "main"
        )[0, "from"]
    )
    df = (
        load_df
        .filter(
            pl.col("hash") == tx_hash,
            pl.col("value") != 0
        )
    )
    
    df = (
        safe_remove_special_edges(df)
        .to_pandas()
        .reset_index() # keep index for later (after groupby)
    )
    # --------------
    # Hash Renaming
    # --------------
    
    hashes = df[["from", "to"]].values.flatten()
    _, idx = np.unique(hashes, return_index=True)

    
    
    renaming_dict_consts = dict(zip(
         SPECIAL_HASHES, ["WRAP", "MINT"]
    ))
    # map hashes to letters
    renaming_dict_var = dict(
        zip(
            hashes[idx], 
            list(string.ascii_letters)
        )
    )
    
    # merging dictionaries
    # order matters here as the last seen key:val takes precedence, and we want to hard code known hashes
    renaming_dict = renaming_dict_var | renaming_dict_consts
    
    SOURCE = renaming_dict[SOURCE_HASH]
    
    df["from"] = df["from"].map(renaming_dict)
    df["to"] = df["to"].map(renaming_dict)

    # handle SIMPLE duplicate transactions. assumes same underlying symbol
    df = (
        df
        .groupby(
            ["symbol", "from", "to"]
        )
        .agg({
            "value": "sum", 
            "index": "first"
        })
        .reset_index()
        .set_index("index")
        .sort_index()
    )
    
    # --------------
    # Create edge label column
    # --------------
    
    df["value_str"] = df["value"].apply('{:20,.4f}'.format).astype(str)
    df["attr"] = df["symbol"].astype(str) + "-" + df["value_str"]
    
    return df, SOURCE
    
def make_base_graph(df: pd.DataFrame, source_node, create_using):
    G = nx.from_pandas_edgelist(
        df, 
        source="from", target="to", 
        edge_attr=["symbol", "value", "attr"], 
        create_using=create_using
    )

    G.nodes[source_node]["color"] = "red"
    
    # gv_defaults reads attr, so mask it
    for edge_id in G.edges:
        if G.edges[edge_id]["symbol"] == "WETH":
            G.edges[edge_id]["color"] = "red"

    return G, gv.d3(
        G, **gv_defaults
    )


def contraction_1(df, source_node):
    """
    does NOT produce a lossless graph, do not use if possible.
    robustness to be added wrt nodes movement
    """
    EDGE_LABEL = "attr"
    EDGE_WEIGHT = "value"

    FAILED_FLAG = False
    Gs = {}
    for symbol in df.symbol.unique():
        # print(symbol)
        temp = df[df.symbol == symbol]
        G = nx.from_pandas_edgelist(temp, source="from", target="to", edge_attr=[EDGE_LABEL, EDGE_WEIGHT, "symbol"], create_using=nx.MultiDiGraph)

        ins = G.in_degree(weight=EDGE_WEIGHT)
        outs = G.out_degree(weight=EDGE_WEIGHT)
        nodes = {}
        for node in G.nodes():
            nodes[node] = outs[node] - ins[node]

        minor_G = G
        for node, flow in nodes.items():
            if flow == 0:
                if len(minor_G.out_edges(node)) > 1: continue
                to_remove = []
                to_remove.extend(list(minor_G.in_edges(node)))
                # to_remove.extend(list(minor_G.out_edges(node)))
                # print(symbol, len(to_remove), to_remove)
                for _ in to_remove:
                    u,v = _
                    if u == source_node:
                        _ = [u, v]
                    elif v == source_node:
                        _ = [v, u]
                    
                    
                    try:
                        minor_G = nx.contracted_nodes(
                            minor_G, *_, self_loops=False
                        )
                    except: 
                        FAILED_FLAG = True
                        break
        Gs[symbol] = (minor_G.copy())


    composed = nx.compose_all(Gs.values())

    return composed, FAILED_FLAG

def estimate_value(G, src):
    visited = set()
    queue = set()
    queue.add(src)
    edges_kept = []
    ambiguous = False

    while queue:
        u = queue.pop()
        last_visited = u
        if u not in visited:
            visited.add(u)

            staging_edges = list(G.out_edges(u))
            if len(staging_edges) == 0:
                ambiguous = True
            for (u,v) in staging_edges:
                edge = G.edges[u,v]
                if edge["symbol"] == "WETH":
                    edges_kept.append((u,v))
                else:
                    queue.add(v)
    
    # compute value
    return sum([G.edges[_edge]["value"] for _edge in edges_kept]), ambiguous#, edges_kept


def safe_remove_special_edges(df):
    """
    Some edges -> 0x42... and 0x000
    These tend to work in pair, but it can also be forked, so we cannot simply eliminate by count
    
    We tag the edges that involve these special hashes, give them a direction 
        (sign attribution does not matter as long as they exist)
        
    This gives us a (signed) flow, which we can sum up per target (i.e. node that triggers an ETH->WETH xfer)
    If that sum is 0, then we confirm it's lossless and we can then safely remove these edges from the original graph.
    
    
    """
    df = (
        df
        # add sign to flow
        .with_columns(
            pl
            .when(pl.col("from").is_in(SPECIAL_HASHES))
            .then(pl.lit("1").cast(int))

            .when(pl.col("to").is_in(SPECIAL_HASHES))
            .then(pl.lit("-1").cast(int))

            .otherwise(0)
            .alias("has_special"),
            
            # select the right node to act as target
            pl # explicitly model both cases so we dont have to filter then join
            .when(pl.col("from").is_in(SPECIAL_HASHES))
            .then(pl.col("to"))

            .when( pl.col("to").is_in(SPECIAL_HASHES))
            .then(pl.col("from"))

            .alias("target")
        )
    )

    removable_targets = (
        df
        # remove nodes that aren't involved
        .filter(~pl.col("target").is_null())
        # compute flow
        .with_columns(
            (pl.col("has_special") * pl.col('value')).alias("flow")
        )
        .group_by(
            "target",
        )
        .agg(
            pl.sum("flow").alias("resid_flow")
        )
        .with_columns(
            pl
            .when(
                pl.col("resid_flow").abs() < 1e-6
            )
            .then(
                pl.lit(0.)
            )
            .otherwise(pl.col("resid_flow"))
            .name.keep()
        )
        .filter(
            pl.col("resid_flow") == 0
        )
        .select("target")
    )

    df = df.join(removable_targets, on="target", how="anti")
    return df