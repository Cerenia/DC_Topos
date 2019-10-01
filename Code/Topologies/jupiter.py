from .topology import Topology
from .util import gen_nodes, preprocess_node_positions
import numpy as np

class Jupiter(Topology):
    """ Google's Jupiter Topology, Centauri level abstraction*

    Structure extracted from: https://dl.acm.org/citation.cfm?doid=2785956.2787508

    *Some redundant connections outside the server pods simplified
    """

    def __init__(self, spine_block_count = 256, aggregation_block_count=64, capacity_function=None):
        """

        Raises a ValueError if there are less spine blocks than aggregation blocks
        :param spine_block_count (optional, defaults to 256): How many spine blocks are be instantiated
        :param aggregation_block_count (optional, defaults to 64): How many aggregation blocks should be instantiated?
        :param capacity_function (optional, defaults to None): Function used to initialise link capacities based on their endpoints.
        """

        if spine_block_count < aggregation_block_count:
            raise ValueError("We need at least as many spine blocks as aggregation blocks!")
        self.spine_block_count = spine_block_count
        self.switches_per_spine = 6
        self.switches_per_middle_block = 4
        self.middle_block_per_aggregation = 8
        self.aggregation_block_count = aggregation_block_count
        self.tors_per_aggregation_block = 32
        self.tor_idx_range = range(1, self.aggregation_block_count * self.tors_per_aggregation_block + 1)
        last_tor_idx = self.tor_idx_range[-1]
        self.aggregation_idx_range = range(last_tor_idx + 1, last_tor_idx + self.aggregation_block_count * self.middle_block_per_aggregation * 4 + 1)
        last_agg_idx = self.aggregation_idx_range[-1]
        self.spine_idx_range = range(last_agg_idx + 1, last_agg_idx + self.spine_block_count * self.switches_per_spine + 1)
        indices = [self.tor_idx_range, self.aggregation_idx_range, self.spine_idx_range]
        super().__init__(indices, "Jupiter_" + str(spine_block_count) + "_" + str(aggregation_block_count), capacity_function)

    def gen_graph(self):
        """Constructs a Networkx Graph of Google's Jupiter

        :param topo: The FatTree Topology object holding the parameters
        :return: A networkx Graph representing a Network in form of Jupiter
        """

        # Generate nodes
        s_tor = len(self.tor_idx_range)
        s_agg = len(self.aggregation_idx_range)
        s_sp = len(self.spine_idx_range)
        G = gen_nodes(s_tor, s_agg, s_sp)

        # Prestructure the switch indices to make link creation more concise
        current_idx = 1
        # TOR
        assert (current_idx == self.tor_idx_range[0])
        tors = []
        for _ in range(0, self.aggregation_block_count):
            tor_agg = []
            for tor in range(0, self.tors_per_aggregation_block):
                tor_agg.append(current_idx)
                current_idx += 1
            tors.append(tor_agg)
        # Aggregation
        assert (current_idx == self.aggregation_idx_range[0])
        aggregation = []
        for _ in range(0, self.aggregation_block_count):
            agg_block = []
            for middle_block in range(0, 8):
                agg_block_mb = []
                for switch in range(0, 4):
                    agg_block_mb.append(current_idx)
                    current_idx += 1
                agg_block.append(agg_block_mb)
            aggregation.append(agg_block)
        # Spine
        assert (current_idx == self.spine_idx_range[0])
        spines = []
        for _ in range(0, self.spine_block_count):
            spine = []
            for j in range(0, self.switches_per_spine):
                spine.append(current_idx)
                current_idx += 1
            spines.append(spine)

        # Links
        # Intra spine links:
        spine_idx = 0
        for spine_block in range(0, self.spine_block_count):
            for switch in range(0, self.switches_per_spine):
                for previous in range(0, switch):
                    v1 = self.spine_idx_range[spine_idx]
                    v2 = spines[spine_block][previous]
                    G.add_edge(v1, v2)
                    G.add_edge(v2, v1)
                spine_idx += 1
        # Aggregation:
        agg_idx = 0
        spine_block_idx = 0
        spine_switch_pos = 0
        for aggregation_block in range(0, self.aggregation_block_count):
            for middle_block in range(0, 8):
                for switch in range(0, 4):
                    # Intra aggregation
                    for previous in range(0, switch):
                        v1 = self.aggregation_idx_range[agg_idx]
                        v2 = aggregation[aggregation_block][middle_block][previous]
                        G.add_edge(v1, v2)
                        G.add_edge(v2, v1)
                    # Aggregation to spine
                    # 8 connections per switch up to the spine
                    for _ in range(0, 8):
                        v1 = self.aggregation_idx_range[agg_idx]
                        v2 = spines[spine_block_idx][spine_switch_pos]
                        G.add_edge(v1, v2)
                        G.add_edge(v2, v1)
                        # Distribute the connections evenly over spine blocks
                        spine_block_idx = (spine_block_idx + 1) % self.spine_block_count
                        # When we come back to the first spine block, change switch position
                        if spine_block_idx == 0:
                            spine_switch_pos = (spine_switch_pos + 1) % self.switches_per_spine
                    agg_idx += 1
        # TORS:
        tor_idx = 0
        for aggregation_block in range(0, self.aggregation_block_count):
            for tor in range(0, self.tors_per_aggregation_block):
                for out in range(0, 8):
                    # Dual redundant, finishing at different Centauri chassis in the same MB
                    switch_pos = int(
                        tor / 8)  # 0 ... 3, to evenly split the links for the connecting switches on the Agg layer
                    v1 = self.tor_idx_range[tor_idx]
                    v2 = aggregation[aggregation_block][out][switch_pos]
                    G.add_edge(v1, v2)
                    G.add_edge(v2, v1)
                    second_switch_pos = (switch_pos + 1) % 4  # Connect to "next" centauri cassis in same MB
                    v2 = aggregation[aggregation_block][out][second_switch_pos]
                    G.add_edge(v1, v2)
                    G.add_edge(v2, v1)
                tor_idx += 1

        # Initialize Capacities
        G = self.init_capacities(G)

        return G

    def set_node_positions(self):
        """Compute the x-axis coordinate of nodes for later drawing.

        :return: A 2-dimentional array representing the node positions. (horizontal pos, layer)
        """

        # Layer indices
        TOR_LAYER = 0
        AGGREGATION_LAYER = 1
        SPINE_LAYER = 2

        node_width, node_gap, position = preprocess_node_positions(self)

        # For each aggregation block, extra spacing at TORs & Agg
        for aggregation_block in range(1, self.aggregation_block_count):
            position[TOR_LAYER, aggregation_block * self.middle_block_per_aggregation:] = position[TOR_LAYER,
                                                                                  aggregation_block * self.middle_block_per_aggregation:] + 2
            position[AGGREGATION_LAYER, aggregation_block * self.middle_block_per_aggregation:] = position[AGGREGATION_LAYER,
                                                                                  aggregation_block * self.middle_block_per_aggregation:] + 2
        # Group the aggregation switches for each block
        for aggregation_block in range(0, self.aggregation_block_count):
            middle_tor = aggregation_block * self.tors_per_aggregation_block + self.tors_per_aggregation_block / 2
            pos_step = node_width + node_gap
            pos_start = position[TOR_LAYER, int(middle_tor - int(self.tors_per_aggregation_block / 2))]
            pos_stop = pos_start + self.tors_per_aggregation_block * pos_step - 0.1
            position[AGGREGATION_LAYER,
            aggregation_block * self.tors_per_aggregation_block: aggregation_block * self.tors_per_aggregation_block + self.tors_per_aggregation_block] = np.arange(
                pos_start, pos_stop, pos_step)
        # Align the spines in the middle
        middle_tor = position[TOR_LAYER, int(self.tor_idx_range[-1] / 2)]
        pos_start = middle_tor - pos_step * int(len(self.spine_idx_range) / 2)
        pos_step = node_width + node_gap
        for i in range(0, len(self.spine_idx_range)):
            position[SPINE_LAYER, i] = pos_start + i * pos_step
        # Group the spines in blocks
        for i in range(0, self.spine_block_count):
            position[SPINE_LAYER, i * self.switches_per_spine:] = position[2, i * self.switches_per_spine:] + 2

        return position

    def draw_topology(self, G=None):
        """Draw the graph to a pdf file: uses Graphviz .dot format.

        This function was overwritten to pull apart the switches forming the middle blocks and the aggregation block onto seperate layers to increase visibility.

        :param G: The networkx graph which should be drawn.
        """

        node_width, index_limits, G_dot = super().generate_drawing(G)
        pos = self.set_node_positions()
        # Change the positioning for the spine and aggregate layer for better visibility
        counterAgg = 0
        for node in G_dot.get_nodes():
            id = int(node.get_name())
            if id <= index_limits[0]:
                pass # Don't touch the TORs
            elif id <= index_limits[1]:
                if counterAgg < 2:
                    node.set_pos('%.1f,1.5!' % pos[1, id - index_limits[0] - 1].astype(float))
                else:
                    node.set_pos('%.1f,1.8!' % (pos[1, id - index_limits[0] - 1] - 2 * node_width).astype(float))
                counterAgg = (counterAgg + 1) % 4
            elif id <= index_limits[2]:
                # Group the interconnected aggregation switches above each other
                if id % 2 == 0:
                    node.set_pos('%.1f,2.4!' % pos[2, id - index_limits[1] - 1].astype(float))
                else:
                    node.set_pos('%.1f,2.7!' % (pos[2, id - index_limits[1] - 1] - node_width).astype(float))

        # Write to a file: change format to .png or .pdf
        filename = self.descriptor + '.pdf'
        G_dot.write_pdf(filename)

