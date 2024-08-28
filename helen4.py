# -*- coding: utf-8 -*-
"""
Created on Thu May 16 12:07:14 2024

@author: helen
"""

######################################################################
# List of functions:
    
#     create_graph(transactions) 
#     Creates a (multi) directed graph from transaction data (list of transactions).

#     check_node_type(G, node) 
#     Checks if the node is a source or a sink in the graph.

#     check_flow_conservation_node(G, node) 
#     Checks if the node is a flow conservation node.

#     split_flow_conservation_node(G, node)
#     Splits a flow conservation node into multiple nodes based on token types.

#     add_dummy_node_if_needed(G, initiator)
#     Add a dummy_node and re-direct appropriate arrows to make the initiator a source.

#     find_arc_cut(G, start) #Algorithm A, as denoted by Odile
#     Applies Algorithm A to find an arc cut consisting of WETH arcs that separates sources from sinks.

#     sum_weth_arcs(G, marked_nodes, unmarked_nodes)
#     Sums the values of all WETH arcs from the marked nodes to the unmarked nodes.

#     main(G, start)
#     4 Steps as follows:
#       1. Add a dummy node if the start node is a sink.
#       2. Split flow conservation nodes.
#       3. Find an arc cut in the graph.
#       4. Sum the values of WETH arcs between marked and unmarked nodes.

#    check_bifurcation_node(G, node)
#    Checks if the node is a bifurcation node.

#    check_uncategorized_node(G, node)
#    Checks if the node is an uncategorized node.

#    check_transaction_has_uncategorized_node(G)
#    Checks if the transaction contains an uncategorized node
#######################################################################

import networkx as nx
from collections import deque

def create_graph(transactions):
    """
    Creates a (multi) directed graph from transaction data.

    Args:
    transactions (list): List of transaction dictionaries.

    Returns:
    G (networkx.MultiDiGraph): Multi Directed graph with transactions as edges.
    """
    G = nx.MultiDiGraph()
    for transaction in transactions:
        u = transaction['from']
        v = transaction['to']
        token = transaction['symbol']
        value = transaction['For']
        G.add_edge(u, v, token=token, value=value)
    return G

def check_node_type(G, node):
    """
    Checks if the node is a source or a sink in the graph.

    Args:
    G (networkx.MultiDiGraph): Multi Directed graph.
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
    
def check_flow_conservation_node(G, node):
    """
    Checks if the node is a flow conservation node.

    Args:
    G (networkx.MultiDiGraph): Multi Directed graph.
    node (str): Node to check.

    Returns:
    bool: True if the node is a flow conservation node, False otherwise.
    """
    node_type = check_node_type(G, node)
    if node_type == "source" or node_type == "sink":
        return False
    
    incoming_edges = G.in_edges(node, data=True)
    outgoing_edges = G.out_edges(node, data=True)
    
    token_flow = {}

    for u, v, data in incoming_edges:
        token = data['symbol']
        value = data['value']
        if token not in token_flow:
            token_flow[token] = {'in': 0, 'out': 0}
        token_flow[token]['in'] += value

    for u, v, data in outgoing_edges:
        token = data['symbol']
        value = data['value']
        if token not in token_flow:
            token_flow[token] = {'in': 0, 'out': 0}
        token_flow[token]['out'] += value
    
#    print(token_flow.items())
    for token, flows in token_flow.items():  
        if (flows['in'] == 0) or (flows['out'] == 0):
            return False
        if abs(flows['in'] - flows['out']) > 0.001:
            return False

    return True

def split_flow_conservation_node(G, N):
    """
    Splits a flow conservation node into multiple nodes based on token types.

    Args:
    G (networkx.MultiDiGraph): Multi Directed graph.
    node (str): Node to split.

    Returns:
    None
    """ 
    
    incoming_edges = G.in_edges(N, data=True)
    outgoing_edges = G.out_edges(N, data=True)
    
    # Get the types of edges connected to N
    type_list = set()
    for u, v, data in incoming_edges:
        edge_type = data.get('symbol')
        type_list.add(edge_type)
    # Since this is a flow-conservation node, 
    # we don't need this extra step:
    for u, v, data in outgoing_edges:
        edge_type = data.get('symbol')  
        type_list.add(edge_type)
    #print(type_list)
    
    # Create new nodes based on the types of edges
    new_nodes = {edge_type: f"{N}_{edge_type}" for edge_type in type_list}
    for new_node in new_nodes.values():
        G.add_node(new_node)
    
    # Redirect edges to the new nodes
    edges_to_add = []
    edges_to_remove = []
    for u, v, data in list(G.edges(data=True)):
        edge_type = data.get('symbol')
        new_node = new_nodes.get(edge_type)
        if u == N:
            edges_to_add.append((new_node, v, data))
            edges_to_remove.append((u, v))
        elif v == N:
            edges_to_add.append((u, new_node, data))
            edges_to_remove.append((u, v))

    # Add new edges
    for edge in edges_to_add:
        G.add_edge(edge[0], edge[1], **edge[2])
        #edge[2] is a dict, the double star is so to unpack it.

    # Remove old edges
    for edge in edges_to_remove:
        G.remove_edge(edge[0], edge[1])

    # Remove the old node
    G.remove_node(N)
    
    return G

def add_dummy_node_if_needed(G, initiator):
    """
    Adds a dummy node D to the graph if the initiator node is neither a source nor a sink.
    Replaces all incoming edges to the initiator node with edges to the dummy node.

    Args:
    G (networkx.MultiDiGraph): Multi Directed graph.
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
    G (networkx.MultiDiGraph): Multi Directed graph.
    start (str): The starting node (source).
    
    Returns:
    str: 'traceable' if there is no path from source to sink without WETH arcs,
         'not traceable' if there is such a path.
    set: Set S of marked nodes if the graph is traceable, otherwise None.
    set: Set T which is the complement of S containing nodes not marked, otherwise None.
    """
    # Initialize the queue and the set of marked nodes
    Q = deque()
    marked = set()
    
    # Add each source w to Q and mark w
    for node in G.nodes:
        if G.in_degree(node) == 0:  # Nodes with no incoming edges
            Q.append(node)
            marked.add(node)
    
    while Q:
        u = Q.popleft()
        for v in G.successors(u):
            # Check all edges between u and v
            for key, data in G[u][v].items():
                if data['symbol'] != 'WETH' and v not in marked:
                    Q.append(v)
                    marked.add(v)
                    break  # No need to check other edges between u and v once v is marked
    
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
    G (networkx.MultiDiGraph): Multi Directed graph.
    marked_nodes (set): Set of marked nodes.
    unmarked_nodes (set): Set of unmarked nodes.
    
    Returns:
    int: Sum of the values of WETH arcs.
    """
    total_value = 0
    
    for u in marked_nodes:
        for v in G.successors(u):
            if v in unmarked_nodes:
                for key, data in G[u][v].items():
                    if data['symbol'] == 'WETH':
                        total_value += data['value']
    
    return total_value


def main(G, start):
    """
    Main function to process a graph from transaction data and perform various operations.

    Steps:
    1. Add a dummy node if the start node is a sink.
    2. Split flow conservation nodes into multiple nodes based on token types.
    3. Find an arc cut in the graph starting from the given node.
    4. Sum the values of WETH arcs between marked and unmarked nodes.

    Args:
    G (networkx.MultiDiGraph): Multi Directed graph.
    start (str): The starting node for the operations.

    Returns:
    None
    """
    
    # print("Original graph:")
    # print(G.edges(data=True))
    # num_nodes = G.number_of_nodes()
    # num_edges = G.number_of_edges()
    # print(f"Number of nodes: {num_nodes}")
    # print(f"Number of edges (arrows): {num_edges}")

    # Step 1: Add a dummy node if needed
    add_dummy_node_if_needed(G, start)
    
    # print("Graph with a dummy node:")
    # print(G.edges(data=True))
    # num_nodes = G.number_of_nodes()
    # num_edges = G.number_of_edges()
    # print(f"Number of nodes: {num_nodes}")
    # print(f"Number of edges (arrows): {num_edges}")

    # Step 2: Split flow conservation nodes
    nodes_to_check = list(G.nodes())
    for node in nodes_to_check:
        if check_flow_conservation_node(G, node):
            # print(node)
            # print(check_flow_conservation_node(G, node))
            split_flow_conservation_node(G, node)
            
    # print("Graph with flow_conservation_nodes splitted:")
    # print(G.edges(data=True))
    # num_nodes = G.number_of_nodes()
    # num_edges = G.number_of_edges()
    # print(f"Number of nodes: {num_nodes}")
    # print(f"Number of edges (arrows): {num_edges}")

    # Step 3: Find an arc cut
    status, marked_nodes, unmarked_nodes = find_arc_cut(G, start)
    
    # print(f"Status: {status}")
    # print(f"Marked Nodes (S): {marked_nodes}")
    # print(f"Complement: {unmarked_nodes}")
    
    # Step 4: Sum WETH arcs
    if marked_nodes is not None and unmarked_nodes is not None:
        # Apply the sum_weth_arcs function to sum the values of WETH arcs
        total_weth_value = sum_weth_arcs(G, marked_nodes, unmarked_nodes)
        # print(f"Total WETH value: {total_weth_value}")
        return total_weth_value

####################################################################
# Example usage: Jacky sent this by email on Jun 1, 2024
# The answer should be 'Total WETH value: 0.0014', 
# marked_nodes should be all nodes except 'c'
# transactions = [
#     {'from': 'b', 'to': 'd', 'symbol': 'Dog', 'For': 510},
#     {'from': 'd', 'to': 'c', 'symbol': 'wstWETH', 'For': 0.0012},
#     {'from': 'c', 'to': 'a', 'symbol': 'wstWETH', 'For': 0.0012},
#     {'from': 'a', 'to': 'c', 'symbol': 'WETH', 'For': 0.0014},
#     {'from': 'c', 'to': 'e', 'symbol': 'WETH', 'For': 0.0014},
#     {'from': 'e', 'to': 'b', 'symbol': 'Brett', 'For': 100.4170},
# ]
# start = 'b'  # Starting node
# ###################################################################
# # Example usage: split two nodes
# transactions = [
#     {'from': 'a', 'to': 'b', 'symbol': 'Dog', 'For': 510},
#     {'from': 'a', 'to': 'b', 'symbol': 'WETH', 'For': 25},
    
#     {'from': 'b', 'to': 'c', 'symbol': 'WETH', 'For': 20},
#     {'from': 'b', 'to': 'c', 'symbol': 'WETH', 'For': 5},
#     {'from': 'b', 'to': 'c', 'symbol': 'Dog', 'For': 510},
    
#     {'from': 'c', 'to': 'e', 'symbol': 'Dog', 'For': 510},
#     {'from': 'c', 'to': 'e', 'symbol': 'WETH', 'For': 25},
    
#     {'from': 'e', 'to': 'a', 'symbol': 'WETH', 'For': 99},
# ]
# start = 'a'  # Starting node
# ###################################################################
#Example of a bifurcation node 'b'
# transactions = [
#     {'from': 'a', 'to': 'b', 'symbol': 'Dog', 'For': 510},
#     {'from': 'b', 'to': 'c', 'symbol': 'WETH', 'For': 20},
# ]
# start = 'a'  # Starting node
# #####################################################################
#Exemple of uncategorized node 'b'
# transactions = [
#      {'from': 'a', 'to': 'b', 'symbol': 'Dog', 'For': 510},
#      {'from': 'b', 'to': 'c', 'symbol': 'WETH', 'For': 20},
#      {'from': 'b', 'to': 'c', 'symbol': 'Dog', 'For': 20},
#      {'from': 'c', 'to': 'd', 'symbol': 'WETH', 'For': 209},
# ]
# start = 'a'  # Starting node
#####################################################################

def check_bifurcation_node(G, node):
    """
    Checks if the node is a bifurcation node.

    Args:
    G (networkx.MultiDiGraph): Multi Directed graph.
    node (str): Node to check.

    Returns:
    bool: True if the node is a bifurcation node, False otherwise.
    """
    node_type = check_node_type(G, node)
    if node_type == "source" or node_type == "sink":
        return False
    
    if check_flow_conservation_node(G, node):
        return False
        
    incoming_edges = G.in_edges(node, data=True)
    outgoing_edges = G.out_edges(node, data=True)
    
    tokens_in = set()
    tokens_out = set()
    
    for _, _, data in incoming_edges:
        token = data['symbol']
        tokens_in.add(token)
            
    for _, _, data in outgoing_edges:
        token = data['symbol']
        tokens_out.add(token)
    
    if not tokens_in.intersection(tokens_out):
#        print('This is a bifurcation node: ', node)
        return True
    else:
#        print('This is NOT bifurcation node: ',node)
        return False

def check_uncategorized_node(G, node):
    """
    Checks if the node is an uncategorized node.

    Args:
    G (networkx.MultiDiGraph): Multi Directed graph.
    node (str): Node to check.

    Returns:
    bool: True if the node is an uncategorized node, False otherwise.
    """
    
    node_type = check_node_type(G, node)
    if node_type == "source" or node_type == "sink":
#        print('This is a source or a sink node: ',node)
        return False
    
    if check_flow_conservation_node(G, node):
#        print('This is a flow conservation node: ', node)
        return False
    
    if check_bifurcation_node(G, node):
#        print("This is a bifurcation node: ", node)
        return False
    
#    print("This is an uncategorized node: ", node)
    return True

def check_transaction_has_uncategorized_node(G):
    """
    Checks if the transaction contains an uncategorized node
    (an uncategorized node is one that is not of type source, sink, flow-conservation or bifurcation)

    Args:
    G (networkx.MultiDiGraph): Multi Directed graph.

    Returns:
    bool: True if there is a node that is uncategorized, False otherwise.
    """
    
    nodes_to_check = list(G.nodes())
    for node in nodes_to_check:
        if check_uncategorized_node(G, node):
            # print('This transaction has an uncategorized node')
            return True
    
    return False

#untraceable 4
transactions = [
    {'from': 'a', 'to': 'b' ,'symbol': 'USDbC', 'For': 605.941105, 'attr': 'USDbC-605.9411'},

# For testing pourposes,
# this next line adds an uncategorized node to this transaction
#    {'from': 'a', 'to': 'b' ,'symbol': 'TOSHI', 'For': 605.941105, 'attr': 'USDbC-605.9411'},

    {'from': 'a', 'to': 'd' ,'symbol': 'WETH', 'For': 0.165084, 'attr': 'WETH-0.1651', 'color': 'red'},
    {'from': 'a', 'to': 'c' ,'symbol': 'WETH', 'For': 0.991018, 'attr': 'WETH-0.9910', 'color': 'red'},
    {'from': 'a', 'to': 'g' ,'symbol': 'BRETT', 'For': 146333.837132, 'attr': 'BRETT-146,333.8371'},
    {'from': 'a', 'to': 'i' ,'symbol': 'BRETT', 'For': 13302.411768, 'attr': 'BRETT-13,302.4118'},
    {'from': 'a', 'to': 'h' ,'symbol': 'WETH', 'For': 0.825619, 'attr': 'WETH-0.8256', 'color': 'red'},
    {'from': 'b', 'to': 'f' ,'symbol': 'TOSHI', 'For': 957275.165478, 'attr': 'TOSHI-957,275.1655'},
    {'from': 'd', 'to': 'a' ,'symbol': 'USDbC', 'For': 605.941105, 'attr': 'USDbC-605.9411'},
    {'from': 'c', 'to': 'f' ,'symbol': 'TOSHI', 'For': 5749820.125656, 'attr': 'TOSHI-5,749,820.1257'},
    {'from': 'g', 'to': 'a' ,'symbol': 'WETH', 'For': 1.816715, 'attr': 'WETH-1.8167', 'color': 'red'},
    {'from': 'i', 'to': 'a' ,'symbol': 'WETH', 'For': 0.165007, 'attr': 'WETH-0.1650', 'color': 'red'},
    {'from': 'h', 'to': 'e' ,'symbol': 'TOSHI', 'For': 143656.687063, 'attr': 'TOSHI-143,656.6871'},
    {'from': 'h', 'to': 'f' ,'symbol': 'TOSHI', 'For': 4644899.548369, 'attr': 'TOSHI-4,644,899.5484'},
    {'from': 'f', 'to': 'a' ,'symbol': 'BRETT', 'For': 159636.24889999998, 'attr': 'BRETT-159,636.2489'},
]
start = 'f'  # Starting node


# Apply the function
if __name__ == "__main__":
    
     G = create_graph(transactions)
     
#      print("Original Graph:")
# #     print(G.edges(data=True))
#      num_nodes = G.number_of_nodes()      
#      num_edges = G.number_of_edges()
#      print(f"Number of nodes: {num_nodes}")
#      print(f"Number of edges (arrows): {num_edges}")
     
     main(G, start)
     
#      print("Processed Graph:")
# #     print(G.edges(data=True))
#      num_nodes = G.number_of_nodes()      
#      num_edges = G.number_of_edges()
#      print(f"Number of nodes: {num_nodes}")
#      print(f"Number of edges (arrows): {num_edges}")
     
#     check_bifurcation_node(G, 'h')
     
     check_transaction_has_uncategorized_node(G)
     
