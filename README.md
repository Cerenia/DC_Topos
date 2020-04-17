# DC_Topos

This is a collection of scalable datacentre topologies. This project is mainly intended for people doing research or teaching. A handy command line client gives easy access for people who are simply curious about the structure of these networks, and generates a visualisation in PDF format. 

Each topology object can create a Networkx DiGraph which represents an instance of this topology. These instances can in turn be visualized in PDF format. Additionally, we implemented the possibility to pass a function to the topologies to set link capacities throughout the network. The function takes two switch IDs as an argument&emdash;defining the link through the node IDs on each end&emdash;and should output a floating point number for the capacity value.
The topologies are constructed from bottom to top, the first layer always being the top of rack (TOR) layer. The lowest switch IDs will therefore be in the TOR-layer and work their way up in the connecting layers. We define internal ranges per layer that hold the switch IDs to make everything more legible. Instantiate some topologies to get a better feel for it.

This code runs with python version 3.

# Getting started
## Command Line Interface

If you just want to play around with the topologies and get a feel for their scaling, we encourage you to use the handy command line interface. First make sure that you have a version of python3 installed on your machine. Clone the repo and navigate to the "Code" folder where the file "cli.py" is located. Each topology has a different number of arguments you can pass to instantiate them. Try running:
```
python cli.py Fabric -h
```
To see the available parameters for the Fabric topology. 
Currently we support `FatTree` (a classical datacenter topology mostly used in research), `Fabric` (Facebooks topology), `Jupiter` and `Jupiter_bl` (Two different abstraction levels of Googles Jupiter topology).
To instantiate a topology pass the chosen arguments. E.g:
```
python cli.py Fabric 3 2 --n_p 4 --p_c 8
```
This will result in a drawing of the topology instance appearing in the Code folder as a PDF.

## Mid Level API

If you want to use the topologies as building blocks for other things, you can simply import their constructors. This opens up some additional options:

### Partial drawings

The visualiser is able to handle partial graphs. To do this you can trim the Networkx graph and pass the updated graph to the `draw_topology()` function.
```
    import networkx as nx
    from DC_Topos.Topologies.fatTree import FatTree
    
    topo = FatTree(8)
    graph = topo.gen_graph()
    nodes_in_first_pod = {1, 2, 3, 4}
    nodes_in_first_pod.update(graph.neighbors(1))
    topo.descriptor = topo.descriptor + "-first_pod"
    topo.draw_topology(graph.subgraph(nodes_in_first_pod))
```
This piece of code draws the first pod of FatTree(8) and appends "-first_pod" to the filename.

### Capacity function

You can pass a function as the last argument in each topology constructor. This function is used to set the link capacities and must takes two switch IDs as the argument (and optionally a topology object as third argument making it possible to access the switch ID ranges directly) and return a floating point number representing the capacity on this link. 
```
    from DC_Topos.Topologies.fatTree import FatTree
    def capacity(s1, s2):
        return 40

    topo = FatTree(4, capacity_function=capacity)
    topo.descriptor = topo.descriptor + "-cap-40"
    topo.draw_topology()
```
This piece of code assigns a static capacity of 40 on each link.
```
    from DC_Topos.Topologies.fatTree import FatTree
    
    def capacity(s1, s2, fatTree_topology_object):
        if s1 in fatTree_topology_object.tor_idx_range or s2 in fatTree_topology_object.tor_idx_range:
            return 10
        if s1 in fatTree_topology_object.core_idx_range or s2 in fatTree_topology_object.core_idx_range:
            return 20
            
    topo = FatTree(4, capacity_function=capacity)
    topo.descriptor = topo.descriptor + "-cap-layers"
    topo.draw_topology()
```
This code assigns a static capacity for links between the same layers.

Note that the capacities appear in the generated PDFs.

# Contributing

You are very welcome to contribute more topologies to this project! Please make sure to stick to the same style for the topologies.
- Build switch index ranges in the main topology object
- Implement the `gen_graph()` method on the topology which returns a networkx DiGraph
- Implement the `set_node_positions()` method on the topology needed for visualisation
