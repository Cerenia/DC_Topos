import abc
import inspect
from networkx.drawing.nx_pydot import to_pydot

class Topology:
    """Base Topology Object"""

    def __init__(self, indices, descriptor, capacity_function):
        """

        :param indices: A List of switch indices by layer of the topology
        :param descriptor: String describing the architecture for convenient file creation & naming
        :param capacity_function: Function used to initialise link capacities based on their endpoints.
            Takes (a pair of indices / a pair or indices and a topology object) and returns a float.
        """
        self.indices = indices
        self.descriptor = descriptor
        # Check for the right number of arguments
        if capacity_function is not None:
            nr_of_params = len(inspect.signature(capacity_function).parameters)
            if nr_of_params < 2 or nr_of_params > 3:
                raise ValueError("Signature of capacity function is unsupported! Expected form: cap(source_id, dest_id, topology_object=None). (2 or 3 arguments!)")
        self.capacity_function = capacity_function

    @abc.abstractmethod
    def gen_graph(self):
        """ Generate a Networkx graph corresponding to the Topology

        :return: A graph of the Topology (networkx)
        """

    @abc.abstractmethod
    def set_node_positions(self):
        """Compute the x-axis coordinate of nodes for visualisation.

        :return: A 2-dimentional array representing the node positions which is as wide as the widest layer. (horizontal pos, layer)
        """

    def init_capacities(self, G):
        """ Initializes the capacities on the graph according to the passed capacity function on init.
        If no capacity function was passed, simply returns the graph G.

        :return: The Graph updated with capacities if self.capacity_function is not None. Otherwise returns G untouched.
        """

        if self.capacity_function is not None:
            # Initialize all the capacities, either pass topo object or don't depending on signature
            if len(inspect.signature(self.capacity_function).parameters) == 2:
                for (u, v) in G.edges:
                    G.edges[u, v]['capacity'] = self.capacity_function(u, v)
            elif len(inspect.signature(self.capacity_function).parameters) == 3:
                for (u, v) in G.edges:
                    G.edges[u, v]['capacity'] = self.capacity_function(u, v, self)
        return G

    def generate_drawing(self, G=None):
        """Sets some basic parameters for drawing and creates a G_dot object (Graphviz .dot format) for later drawing.

        :param G: The networkx graph you would like to draw
        :return: node_width (drawing parameter), index_limits (list of switch indices per layer), G_dot (the object used for drawing)
        """

        if G is None:
            G = self.gen_graph()

        node_width = 1.0
        index_limits = []
        for layer in self.indices:
            index_limits.append(layer[-1])

        # Generate Pydot graph object
        G_dot = to_pydot(G)

        # Set graph attributes
        G_dot.set_name(self)
        G_dot.set_ordering('in')  # order incoming edge at a node
        G_dot.set_rankdir('BT')  # core switches appear on top
        G_dot.set_layout('neato')
        G_dot.set_ratio('fill')
        G_dot.set_size('20,5!')
        # get the x-axis position of all nodes
        pos = self.set_node_positions()
        # Generate nodes per layer with label
        
        for node in G_dot.get_nodes():
            id = int(node.get_name())
            if id <= index_limits[0]:
                node.set_label("t-%d" % id)
                node.set_color('gray')
                node.set_layer('tor')
                node.set_pos('%.1f,1!' % pos[0, id - 1].astype(float))   
            elif id <= index_limits[1]:
                node.set_label("p-%d" % id)
                node.set_color('blue')
                node.set_layer('pod')
                node.set_pos('%.1f,3!' % pos[1, id - index_limits[0] - 1].astype(float))
            elif id <= index_limits[2]:
                node.set_label("s-%d" % id)
                node.set_color('black')
                node.set_layer('spine')
                node.set_pos('%.1f,5!' % pos[2, id - index_limits[1] - 1].astype(float))
            elif len(index_limits) > 3 and id <= index_limits[3]:
                node.set_label("ss-%d" % id)
                node.set_color('red')
                node.set_layer('sspine')
                node.set_pos('%.1f,7.5!' % pos[3, id - index_limits[2] - 1].astype(float))
            else:
                print('Invalid switch layer.')
            
            # Set node attributes
            node.set_shape('oval')
            node.set_height('0.8')
            node.set_width(str(node_width))
            node.set_fontsize('30')
        
        for edge in G_dot.get_edges():
            edge.set_color('gray')
            edge.set_arrowhead('vee')
            # Visualize capacities if present
            if self.capacity_function is not None:
                v1 = int(edge.get_source())
                v2 = int(edge.get_destination())
                edge.set_headlabel(str(G.edges[v1, v2]['capacity']))

        return node_width, index_limits, G_dot

    def draw_topology(self, G=None):
        """Draw the graph to a pdf file: uses Graphviz .dot format

        :param G (optional): The networkx graph which should be drawn.'
        """

        _, _, G_dot = self.generate_drawing(G)

        # Write to a file: change format to .png or .pdf
        filename = self.descriptor + '.pdf'
        G_dot.write_pdf(filename)