from .topology import Topology
from .util import gen_nodes, preprocess_node_positions
import numpy as np

class Fabric(Topology):
    """ Facebook's Fabric Topology

    Structure extracted from: https://code.fb.com/production-engineering/introducing-data-center-fabric-the-next-generation-facebook-data-center-network/
    """

    def __init__(self, server_pods, edge_pods, nr_of_planes=4, port_count=48, capacity_function=None):
        """

        :param server_pods: How many server pods should the architecture hold?
        :param edge_pods: How many edge pods connecting to the Internet should there be?
        :param nr_of_planes (optional, defaults to 4): How many connecting fabric switches in a pod?
        :param port_count (optional, defaults to 48): How many in or out ports the building switches have.
        :param capacity_function (optional, defaults to None): Function used to initialise link capacities based on their endpoints.
        """

        self.server_pods = server_pods
        self.edge_pods = edge_pods
        # how many fabric switches are there per server pods?
        self.nr_of_planes = nr_of_planes
        self.port_count = port_count
        # Define which indices are in which category for legibility
        last_tor_idx = port_count * server_pods
        last_fabric_idx = last_tor_idx + nr_of_planes * server_pods
        last_spine_idx = last_fabric_idx + nr_of_planes * server_pods
        last_edge_idx = last_spine_idx + edge_pods * nr_of_planes
        self.tor_idx_range = range(1, last_tor_idx + 1)
        self.fabric_idx_range = range(last_tor_idx + 1, last_fabric_idx + 1)
        self.spine_idx_range = range(last_fabric_idx + 1, last_spine_idx + 1)
        self.edge_idx_range = range(last_spine_idx + 1, last_edge_idx + 1)
        indices = [self.tor_idx_range, self.fabric_idx_range, self.spine_idx_range, self.edge_idx_range]
        super().__init__(indices,
                         "Fabric_" + str(server_pods) + "_" + str(edge_pods) + "_" + str(nr_of_planes) + "_"
                         + str(port_count), capacity_function)

    def gen_graph(self):
        """Generates Facebook's Fabric Topology

        :param topo: Object holding all the parameters
        :return: A graph of the Topology (networkx)
        """

        def connect_to_plane_switches(G, topo, plane, switch_idx):
            """Generates connections between one switch and a complete plane of fabric switches. Raises a ValueError if the plane
            is invalid.

            :param G: The graph which will be edited
            :param topo: The base Fabric Topology object holding the parameters
            :param plane: Which plane to connect to (0 to topo.nr_of_planes-1)
            :param switch_idx: Which switch to connect to the plane
            :return: The updated graph G
            """

            if plane < 0 or plane > topo.nr_of_planes:
                raise ValueError(
                    "There are only %d different spine plates. Choose the plane parameter accordingly".format(
                        topo.nr_of_planes))
            current = topo.spine_idx_range[0] + plane
            while current <= topo.spine_idx_range[-1]:
                v1 = current
                v2 = switch_idx
                G.add_edge(v1, v2)
                G.add_edge(v2, v1)
                current += topo.nr_of_planes

            return G

        s_tor = len(self.tor_idx_range)
        s_pods = len(self.fabric_idx_range)
        s_spines = len(self.spine_idx_range)
        s_edge = len(self.edge_idx_range)

        # Adding nodes
        G = gen_nodes(s_tor, s_pods, s_spines, s_edge)
        # Intra Pod links
        first_fabric_s_idx = self.fabric_idx_range[0]
        for i in self.tor_idx_range:  # rotate over ToR switches
            # rotate over fabric switches in pod
            pod_idx = int((i - 1) / self.port_count)
            for j in range(self.nr_of_planes):
                # connect with every fabric switch in pod
                v1 = i
                v2 = first_fabric_s_idx + self.nr_of_planes * pod_idx + j
                G.add_edge(v1, v2)
                G.add_edge(v2, v1)

        # Intra Fabric Links
        # Iterate over all the fabric switches and connect to the spine switches in correct plane
        plane = 0
        for i in self.fabric_idx_range:
            G = connect_to_plane_switches(G, self, plane, i)
            plane = (plane + 1) % self.nr_of_planes
        # Edge pod - spine Links
        plane = 0
        for i in self.edge_idx_range:
            G = connect_to_plane_switches(G, self, plane, i)
            plane = (plane + 1) % self.nr_of_planes

        # Initialize Capacities
        G = self.init_capacities(G)

        return G

    def set_node_positions(self):
        """Compute the x-axis coordinate of nodes for later drawing.

        :return: A 2-dimentional array representing the node positions. (horizontal pos, layer)
        """

        # Since Fabric is very flexibly scalable, we have to do some extra computations here if we wanna provide sensible visualisations

        # Layer indices
        TOR_LAYER = 0
        FABRIC_LAYER = 1
        SPINE_LAYER = 2
        EDGE_LAYER = 4

        def group_layer_relative(static_idx, switches_per_pod_static, pods_static, relative_idx, switches_per_pod_relative, position):
            """Helper method to symmetrically group one layer relative to another"""
            for pod in range(0, pods_static):
                if switches_per_pod_static == switches_per_pod_relative:
                    # Just mirror
                    first_idx_in_pod = pod * switches_per_pod_relative
                    last_idx_in_pod = pod * switches_per_pod_relative + switches_per_pod_relative
                    position[relative_idx, first_idx_in_pod : last_idx_in_pod] = position[static_idx, first_idx_in_pod : last_idx_in_pod]
                else: # Initialize equivalently to static layer & shift
                    first_idx_in_pod = int(pod * switches_per_pod_static)
                    pos_start = position[static_idx, first_idx_in_pod]
                    pos_stop = pos_start + switches_per_pod_relative * pos_step - 0.1
                    # and do the shift
                    shift = (switches_per_pod_static - switches_per_pod_relative) * (pos_step/2.0)
                    position[relative_idx, pod * switches_per_pod_relative: pod * switches_per_pod_relative + switches_per_pod_relative] = np.arange(pos_start,
                                                                                                                                                     pos_stop,
                                                                                                                                                     pos_step) + shift
            return position

        def mirror_positions(mirror_idx, target_idx, position):
            """Helper method to mirror positions between layers"""
            position[target_idx, :] = position[mirror_idx, :]
            return position

        def add_pod_spacing(idx, switches_per_pod, pods, position):
            """Helper method to add the spacing between pods on any layer"""
            for pod in range(1, pods):
                position[idx, pod * switches_per_pod:] = position[idx, pod * switches_per_pod:] + 2
            return position

        def shift_layer(idx, margin, position):
            """Helper method shifting a whole layer by the provided margin"""
            position[idx, :] = position[idx, :] + margin
            return position

        node_width, node_gap, position = preprocess_node_positions(self)
        pos_step = node_width + node_gap

        # find widest layer
        widest_layer = 0
        nr_of_nodes = 0
        for i in range(0, 4):
            if self.indices[i][-1] + 1 - self.indices[i][0] > nr_of_nodes:
                # '>' favours tor layer as init layer
                widest_layer = i
                nr_of_nodes = self.indices[i][-1] + 1 - self.indices[i][0]
        # Init widest layer:
        if widest_layer == TOR_LAYER:
            # TORS
            # Keep original values and add extra spacing for each server pod. This should be the most common case
            position = add_pod_spacing(TOR_LAYER, self.port_count, self.server_pods, position)
            # For the fabric switches, group them on pods relative to the tors
            position = group_layer_relative(TOR_LAYER, self.port_count, self.server_pods, FABRIC_LAYER, self.nr_of_planes, position)
            # There are always as many spine switches as fabric switches, just mirror positions
            position = mirror_positions(FABRIC_LAYER, SPINE_LAYER, position)
            # Edge switches
            # Spacing between server pods
            edge_spacing = self.port_count * pos_step + 2
            if self.edge_pods < self.server_pods:
                # Assuming there are at least as many Spine switches as Edge switches!
                position = mirror_positions(SPINE_LAYER, EDGE_LAYER, position)
                # Shift for symmetry
                extra_server_pods = self.server_pods - self.edge_pods
                edge_shift = ((extra_server_pods/2.0) * (self.port_count * pos_step + 2))
                position = shift_layer(EDGE_LAYER, edge_shift, position)
            elif self.edge_pods == self.server_pods:
                # Mirror positions for edge and spine layer
                position = mirror_positions(SPINE_LAYER, EDGE_LAYER, position)
            else: # More edge groups than spine groups
                pos_start = position[SPINE_LAYER, 0]
                # Initialize with out using the underlying layer for starting positions in each group
                for pod in range(0, self.edge_pods):
                    pos1_in_group = pos_start + pod * edge_spacing
                    last_pos_in_group = pos1_in_group + self.nr_of_planes * pos_step - 0.1
                    position[EDGE_LAYER, pod * self.nr_of_planes: pod * self.nr_of_planes + self.nr_of_planes] = np.arange(pos1_in_group,
                                                                                                                  last_pos_in_group,
                                                                                                                  pos_step)
                # Adding extra spacing in the lower layers to arrive at a symmetrical visualisation
                extra_edge_groups = self.edge_pods - self.server_pods
                # /2 for symmetry
                fabric_shift = (extra_edge_groups/2.0) * edge_spacing
                for i in range(0, 3):
                    position = shift_layer(i, fabric_shift, position)
        else:
            # widest layer found either in the middle or for the edge switches
            # Initialize this layer
            pos_start = node_width * 0.5
            pos_stop = node_width * 0.5 + (self.indices[widest_layer][-1] + 1 - self.indices[widest_layer][0]) * (node_width + node_gap)
            new_pos = np.arange(pos_start, pos_stop, (node_width + node_gap))
            position[widest_layer, :] = new_pos
            # Now do the pod grouping
            nr_of_pods = self.edge_pods if widest_layer == EDGE_LAYER else self.server_pods
            position = add_pod_spacing(widest_layer, self.nr_of_planes, nr_of_pods, position)
            # How much spacing is one pod worth?
            layer_shift = (self.nr_of_planes * pos_step + 2)/2.0
            if widest_layer == EDGE_LAYER: # widest layer was edge
                # Mirror positions for spine and fabric layer & shift
                for i in range(1, 3):
                    position = mirror_positions(widest_layer, i, position)
                for i in range(1, 3):
                    position = shift_layer(i, (self.edge_pods - self.server_pods)*layer_shift, position)
            else: # widest layers were spine and fabric
                # Mirror position for the second layer
                other_widest = FABRIC_LAYER if widest_layer == SPINE_LAYER else SPINE_LAYER
                position[other_widest, :] = position[widest_layer, :]
                # Initialize Edge layer relative to spine
                position = group_layer_relative(SPINE_LAYER, self.nr_of_planes, self.server_pods, EDGE_LAYER, self.nr_of_planes, position)
                # Shift
                position = shift_layer(EDGE_LAYER, (self.server_pods - self.edge_pods)*layer_shift, position)
            # Centralize TOR switches below fabric layer
            position = group_layer_relative(FABRIC_LAYER, self.nr_of_planes, self.server_pods, TOR_LAYER, self.port_count, position)
        return position
