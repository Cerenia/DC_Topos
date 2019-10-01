import numpy as np
import networkx as nx

#####               #####
####                 ####
###    Visualisation  ###
####                 ####
#####               #####

def gen_nodes(*switches):
    """Creates a networkx DiGraph object and adds the nr. of nodes defined by the sum of the values in switches to the object.

    :param topo: The base topology object holding the parameters.
    :param switches: A list of switch counts (int) per layer
    :return: A networkx DiGraph containing as many nodes as the sum of the values in switches
    """
    
    s_total = 0
    for s in switches:
        s_total = s_total + s
    switch_id = np.arange(1,s_total+1,1)
    G = nx.DiGraph()
    G.add_nodes_from(switch_id)

    return G

def preprocess_node_positions(topo):
    """Constructs the 2D array which will later hold the node positions of each node and pre-fills the TOR_Layer (0) with evenly spaced nodes.

    This is done in this way because for most datacenters, the TOR layer will be the most populated and it is straight forward to populate other
    layers in reference to the most populated layer. If you are planning to use more varied topologies or weird scalings of them, you might have
    to write some extra logic handling the edge cases. For an example check out "set_node_positions" in Fabric.

    :param topo: The topology you want to draw
    :return: The set node_width, node_gap and a container of the right size for this topology which will hold the final node positions.
    """

    # Make sure to use numbers that are fully representable in binary otherwise rounding errors may become a problem at scale
    node_width = 1.0
    node_gap = 0.5

    # Define dimentionality per topology
    # x dimention is defined by the layers of the topology
    # y dimention is defined by the layer with the most switches
    indices = topo.indices
    x = len(indices)
    y = len(indices[0])
    for layer in indices:
        if len(layer) > y:
            y = len(layer)

    # 2D array to hold values for each layer for each node
    position = np.zeros((x, y), dtype=float)

    # ToRs position: same for most standard scaled topologies
    # divide equally the space over all ToRs accommodating for a gap between switches
    pos_start = node_width * 0.5
    pos_stop = node_width * 0.5 + y * (node_width + node_gap)
    position[0, :] = np.arange(pos_start, pos_stop, (node_width + node_gap))

    return node_width, node_gap, position


