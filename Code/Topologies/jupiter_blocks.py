from .topology import Topology
from .util import gen_nodes, preprocess_node_positions
import numpy as np

class Jupiter_bl(Topology):
    """ Google's Jupiter Topology, simplified to blocks

    Structure extracted from: https://dl.acm.org/citation.cfm?doid=2785956.2787508

    AB = Aggregation Blocks
    MB = Middle Blocks
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
        self.ports_per_middle_block_up = 32 #depop
        self.aggregation_block_count = aggregation_block_count
        self.tors_per_aggregation_block = 32
        self.tor_idx_range = range(1, self.aggregation_block_count * self.tors_per_aggregation_block + 1)
        last_tor_idx = self.tor_idx_range[-1]
        self.aggregation_idx_range = range(last_tor_idx + 1, last_tor_idx + self.aggregation_block_count* self.middle_block_per_aggregation + 1)
        last_agg_idx = self.aggregation_idx_range[-1]
        self.spine_idx_range = range(last_agg_idx + 1, last_agg_idx + self.spine_block_count + 1)
        indices = [self.tor_idx_range, self.aggregation_idx_range, self.spine_idx_range]
        super().__init__(indices, "Jupiter_bl_" + str(spine_block_count) + "_" + str(aggregation_block_count), capacity_function)
        

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

        # Prestructure the switch indexes to make link creation more concise
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
        for agg in range(0, self.aggregation_block_count):
            agg_block = []
            for middle_block in range(0, 8):
                agg_block.append(current_idx)
                current_idx += 1
            aggregation.append(agg_block) 
        # Spine
        assert (current_idx == self.spine_idx_range[0])
        spines = []
        for spine in range(0, self.spine_block_count):
            spines.append(current_idx)
            current_idx += 1

        # Links
        # TOR to middle blocks:
        tor_idx = 0
        for aggregation_block in range(0, self.aggregation_block_count):
            for tor in range(0, self.tors_per_aggregation_block):
                for out in range(0, 8):
                    v1 = self.tor_idx_range[tor_idx]
                    v2 = aggregation[aggregation_block][out]
                    G.add_edge(v1, v2)
                    G.add_edge(v2, v1)
                tor_idx += 1
                        
        # Aggregation to spine blocks:
        agg_idx = 0
        spine_block_idx = 0        
        for aggregation_block in range(0, self.aggregation_block_count):
            for middle_block in range(0, 8):
                # spine blocks less than number of MBs in AB leading to multiple links between an MB and an SB
                if self.ports_per_middle_block_up >= self.spine_block_count:
                    for spine in range(0,len(self.spine_idx_range)):
                        v1 = self.aggregation_idx_range[agg_idx]
                        v2 = self.spine_idx_range[spine]
                        G.add_edge(v1, v2)
                        G.add_edge(v2, v1)
                    agg_idx += 1
                    
                # spine blocks more than MBs leading to MBs connecting to a subset of spine blocks    
                else:
                    for _ in range(0,self.ports_per_middle_block_up):
                        v1 = self.aggregation_idx_range[agg_idx]
                        v2 = spines[spine_block_idx]
                        G.add_edge(v1, v2)
                        G.add_edge(v2, v1)
                        spine_block_idx += 1
                        
                        if spine_block_idx == self.spine_block_count:
                            spine_block_idx = 0
                    agg_idx += 1

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

        # For each aggregation block, extra spacing at TORs
        for aggregation_block in range(1, self.aggregation_block_count):
            position[TOR_LAYER, aggregation_block * self.tors_per_aggregation_block:] = position[TOR_LAYER,
                                                                                  aggregation_block * self.tors_per_aggregation_block:] + 2
            
        # Group the aggregation switches for each block
        for aggregation_block in range(0, self.aggregation_block_count):
            middle_tor = aggregation_block * self.tors_per_aggregation_block + self.tors_per_aggregation_block / 2
            pos_step = node_width + node_gap
            pos_start = position[TOR_LAYER ,int(middle_tor)] - pos_step * int(self.middle_block_per_aggregation / 2)
            pos_stop = pos_start + self.middle_block_per_aggregation * pos_step - 0.1
            position[AGGREGATION_LAYER,
            aggregation_block * self.middle_block_per_aggregation: aggregation_block * self.middle_block_per_aggregation + self.middle_block_per_aggregation] = np.arange(
                pos_start, pos_stop, pos_step)
                            
        # Align the spines in the middle
        middle_tor = position[TOR_LAYER, int(self.tor_idx_range[-1] / 2)]
        pos_start = middle_tor - 2*pos_step * int(len(self.spine_idx_range) / 2)
        pos_step = 2*pos_step
        for i in range(0, len(self.spine_idx_range)):
            position[SPINE_LAYER, i] = pos_start + i * pos_step

        return position

