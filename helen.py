# -*- coding: utf-8 -*-
"""
Created on Thu May 16 12:07:14 2024

@author: helen

Algo by Odile, implemented by Helen
"""

import networkx as nx
from collections import deque
import polars as pl
from utils import gv_defaults, filter_main_df_from_tx_hash, make_base_graph

def check_node_type(G, node):
    """
    Checks if the node is a source or a sink in the graph.

    Args:
    G (networkx.DiGraph): Directed graph.
    node (str): Node to check.

    Returns:
    str: "source" if the node is a source, "sink" if the node is a sink,
         "neither" if the node is neither.
    """
    if G.in_degree(node) == 0:
        return "source"
    elif G.out_degree(node) == 0:
        return "sink"
    else:
        return "neither"

def add_dummy_node_if_needed(G, initiator):
    """
    Adds a dummy node D to the graph if the initiator node is neither a source nor a sink.
    Replaces all incoming edges to the initiator node with edges to the dummy node.

    Args:
    G (networkx.DiGraph): Directed graph.
    initiator (str): Initiator node.

    Returns:
    None
    """
    if G.in_degree(initiator) > 0 and G.out_degree(initiator) > 0:
        dummy_node = 'Dummy'
        
        # Add dummy node to the graph
        G.add_node(dummy_node)

        # Get all incoming edges to the initiator
        incoming_edges = list(G.in_edges(initiator, data=True))

        # Redirect incoming edges to the dummy node
        for u, _, data in incoming_edges:
            G.add_edge(u, dummy_node, **data)
            G.remove_edge(u, initiator)

def find_arc_cut(G, start):
    """
    Applies Algorithm A to find an arc cut consisting of WETH arcs that separates sources from sinks.
    
    Args:
    G (networkx.DiGraph): Directed graph.
    start (str): The starting node (source).
    
    Returns:
    str: 'traceable' if there is no path from source to sink without WETH arcs,
         'not traceable' if there is such a path.
    set: Set S of marked nodes if the graph is traceable, otherwise None.
    set: Set T which is the complement of S containing nodes not marked, otherwise None.
    """
    # Initialize the queue and the set of marked nodes
    Q = deque()
    marked = {start}
    
    #add each source w to Q and mark w
    for node in G.nodes:
        if G.in_degree(node) == 0:  # Nodes with no incoming edges
            Q.append(node)
            marked.add(node)
    
    while Q:
        u = Q.popleft()
        for v in G.successors(u):
            if G[u][v]['symbol'] != 'WETH' and v not in marked:
                Q.append(v)
                marked.add(v)
    
    # Check if there is any sink marked
    for node in G.nodes:
        if G.out_degree(node) == 0 and node in marked:  # Sink node
            return 'not traceable', None, None
    
    # Create the set T as the complement of marked nodes
    Set_T = set(G.nodes) - marked
    
    return 'traceable', marked, Set_T

def sum_weth_arcs(G, marked_nodes, unmarked_nodes):
    """
    Sums the values of all WETH arcs from the marked nodes to the unmarked nodes.
    
    Args:
    G (networkx.DiGraph): Directed graph.
    marked_nodes (set): Set of marked nodes.
    unmarked_nodes (set): Set of unmarked nodes.
    
    Returns:
    int: Sum of the values of WETH arcs.
    """
    total_value = 0
    
    for u in marked_nodes:
        for v in G.successors(u):
            if v in unmarked_nodes and G[u][v]['symbol'] == 'WETH':
                total_value += G[u][v]['value']
    
    return total_value

def main(G, src):
    add_dummy_node_if_needed(G, src)
    status, marked_nodes, unmarked_nodes = find_arc_cut(G, src)

    total_weth_value = None
    if marked_nodes is not None and unmarked_nodes is not None:
        total_weth_value = sum_weth_arcs(G, marked_nodes, unmarked_nodes)
        return total_weth_value