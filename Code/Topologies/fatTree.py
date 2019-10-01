from .topology import Topology
from .util import gen_nodes, preprocess_node_positions
import numpy as np

class FatTree(Topology):
    """ A classical FatTree

    Structure extracted from: http://ccr.sigcomm.org/online/files/p63-alfares.pdf
    """

    def __init__(self, port_count, capacity_function=None):
        """

        Raises a ValueError if port_count is not even.
        :param port_count: How many ports the building switches have.
        :param capacity_function (optional, defaults to None): Function used to initialise link capacities based on their endpoints.
        """

        if port_count % 2 != 0:
            raise ValueError("There must be an even nr. of ports to construct a fat-tree")
        # Calculate the nr. of switches in each layer and store them directly in the instance of the topology
        # a spine group has as many switches as uplinks on a pod switch (i.e., ports/2)
        self.port_count = port_count
        pods = port_count
        self.tor_switches = int(pods * (port_count / 2))
        self.aggregation_switches = int(pods * (port_count / 2))
        self.core_switches = int(pow(port_count / 2, 2))
        self.tor_idx_range = range(1, self.tor_switches + 1)
        last_tor_idx = self.tor_idx_range[-1]
        self.aggregation_idx_range = range(last_tor_idx + 1, last_tor_idx + 1 + self.aggregation_switches)
        last_agg_idx = self.aggregation_idx_range[-1]
        self.core_idx_range = range(last_agg_idx + 1, last_agg_idx + 1 + self.core_switches)
        indices = [self.tor_idx_range, self.aggregation_idx_range, self.core_idx_range]
        super().__init__(indices, "FatTree_" + str(port_count), capacity_function)

    def gen_graph(self):
        """Constructs a Networkx Graph of a FatTree

        :return: A networkx DiGraph of the FatTree
        """

        # Adding nodes
        G = gen_nodes(self.tor_switches, self.aggregation_switches, self.core_switches)

        # Wiring inside pods
        pod_step = 0
        pods = self.port_count
        for i in range(self.tor_switches):  # rotate over ToR switches
            if i and not i % int(
                    self.tor_switches / pods):  # upon reaching the first ToR of a new pod (divisible without reminder by the number of ToRs per pod) update the pod index
                pod_step = pod_step + int(self.aggregation_switches / pods)
            for j in range(int(self.aggregation_switches / pods)):
                v1 = i + 1
                v2 = self.tor_switches + pod_step + j + 1
                G.add_edge(v1, v2)
                G.add_edge(v2, v1)

        # Wiring to the core
        pods = self.port_count
        s_per_core_group = int(pods / 2)
        group_step = 0
        for i in range(self.aggregation_switches):
            if i and not i % int(self.aggregation_switches / pods):
                group_step = 0
            # to minimize passing of parameters we can express edge indeces via s_pod
            # pod switch indeces start at s_tor + 1 and in fattree s_tor=s_pod
            # spine switch indeces start at s_tor + s_pod + 1
            # we add +1 because indeces in python start at 0 but we want switch numbers starting at 1
            for j in range(s_per_core_group):
                v1 = self.aggregation_switches + i + 1
                v2 = 2 * self.aggregation_switches + group_step + j + 1
                G.add_edge(v1, v2)
                G.add_edge(v2, v1)
            group_step = group_step + s_per_core_group

        # Initialize Capacities
        G = self.init_capacities(G)

        return G

    def set_node_positions(self):
        """Compute the x-axis coordinate of nodes for later drawing.

        :return: A 2-dimentional array representing the node positions. (horizontal pos, layer)
        """

        # Layer Indices
        TOR_LAYER = 0
        AGGREGATION_LAYER = 1
        CORE_LAYER = 2

        node_width, node_gap, position = preprocess_node_positions(self)

        # extraxting topology features
        s_tor = len(self.tor_idx_range)
        s_spine = len(self.core_idx_range)
        s_tor_unit = int(np.sqrt(s_tor / 2))
        pod = int(s_tor / s_tor_unit)

        for aggregation_block in range(1, pod):
            # for each new pod add extra spacing of 2
            position[TOR_LAYER, aggregation_block * s_tor_unit:] = position[0, aggregation_block * s_tor_unit:] + 2
        position[AGGREGATION_LAYER, :] = position[TOR_LAYER, :]

        # use the layer with the most switches to determine the right plot width
        largest_layer = 0
        layer_idx = 0
        for i, layer in enumerate(self.indices):
            if len(layer) > largest_layer:
                largest_layer = len(layer)
                layer_idx = i
        plot_width = position[layer_idx, -1] - position[layer_idx, 0] + node_width

        # set spacing between core groups
        core_width = int(self.port_count / 2) * node_width + int(self.port_count / 2 - 1) * node_gap
        core_step = plot_width / int(self.port_count / 2) - core_width  # represents padding within a core group
        pos_start = core_step / 2 + node_width / 2
        pos_step = node_width + node_gap
        # the 0.1 comes to avoid rounding effects in arrange operator which causes more values to be generated than we need
        pos_stop = pos_start + s_spine * pos_step - 0.1
        position[CORE_LAYER, 0:s_spine] = np.arange(pos_start, pos_stop, pos_step)
        for aggregation_block in range(1, int(self.port_count / 2)):
            position[CORE_LAYER, aggregation_block * int(self.port_count / 2):] = position[2, aggregation_block * int(
                self.port_count / 2):] + core_step

        return position



