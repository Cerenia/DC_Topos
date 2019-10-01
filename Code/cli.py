# -*- coding: utf-8 -*-
"""
Created on Thu Nov  1 11:33:54 2018

@author: Christelle Gloor, Desislava Dimitrova
"""
import argparse

from Topologies.fatTree import FatTree
from Topologies.fabric import Fabric
from Topologies.jupiter import Jupiter
from Topologies.jupiter_blocks import Jupiter_bl

"""
Command line support
"""

def gen_draw_fatTree(args):
    arg_dict = vars(args)
    topology = FatTree(arg_dict["p_c"])
    topology.draw_topology()

def gen_draw_fabric(args):
    arg_dict = vars(args)
    if arg_dict["n_p"] is None and arg_dict["p_c"] is None:
        topology = Fabric(arg_dict["s_p"], arg_dict["e_p"])
    elif arg_dict["n_p"] is None:
        topology = Fabric(arg_dict["s_p"], arg_dict["e_p"], port_count=arg_dict["p_c"])
    elif arg_dict["p_c"] is None:
        topology = Fabric(arg_dict["s_p"], arg_dict["e_p"], nr_of_planes=arg_dict["n_p"])
    else:
        topology = Fabric(arg_dict["s_p"], arg_dict["e_p"], nr_of_planes=arg_dict["n_p"], port_count=arg_dict["p_c"])
    topology.draw_topology()

def gen_draw_jupiter_bl(args):
    arg_dict = vars(args)
    if arg_dict["s_b"] is None and arg_dict["a_b"] is None:
        topology = Jupiter_bl()
    elif arg_dict["s_b"] is None:
        topology = Jupiter_bl(aggregation_block_count=arg_dict["a_b"])
    elif arg_dict["a_b"] is None:
        topology = Jupiter_bl(spine_block_count=arg_dict["s_b"])
    else:
        topology = Jupiter_bl(spine_block_count=arg_dict["s_b"], aggregation_block_count=arg_dict["a_b"])
    topology.draw_topology()
    
def gen_draw_jupiter(args):
    arg_dict = vars(args)
    if arg_dict["s_b"] is None and arg_dict["a_b"] is None:
        topology = Jupiter()
    elif arg_dict["s_b"] is None:
        topology = Jupiter(aggregation_block_count=arg_dict["a_b"])
    elif arg_dict["a_b"] is None:
        topology = Jupiter(spine_block_count=arg_dict["s_b"])
    else:
        topology = Jupiter(spine_block_count=arg_dict["s_b"], aggregation_block_count=arg_dict["a_b"])
    topology.draw_topology()

# Handle parsing of command line parameters
parser = argparse.ArgumentParser()
# add parser for fat-tree topology
subparsers = parser.add_subparsers()
fatTree_parser = subparsers.add_parser("FatTree")
fatTree_parser.add_argument("p_c", type=int, help="port_count: scaling parameter for the FatTree, must be even!")
fatTree_parser.set_defaults(func=gen_draw_fatTree)
# add parser for Fabric topology
fabric_parser = subparsers.add_parser("Fabric")
fabric_parser.add_argument("s_p", type=int, help="server_pods: How many server pods to instantiate")
fabric_parser.add_argument("e_p", type=int, help="edge_pods: How many edge pods to instantiate")
fabric_parser.add_argument("--n_p", type=int, help="number_of_planes: (defaults to 4) Controls the level of redundancy")
fabric_parser.add_argument("--p_c", type=int, help="port_count: (defaults to 48) How many top of rack switches in each pod")
fabric_parser.set_defaults(func=gen_draw_fabric)
# add parser for Jupiter topology at the level of blocks (high abstraction)
jupiter_bl_parser = subparsers.add_parser("Jupiter_bl")
jupiter_bl_parser.add_argument("--s_b", type=int, help="spine_blocks: (defaults to 256), How many spine blocks to instantiate ,s_b >= a_b")
jupiter_bl_parser.add_argument("--a_b", type=int, help="aggregation_blocks: (defaults to 64), How many aggregation blocks to instantiate ,a_b < s_b")
jupiter_bl_parser.set_defaults(func=gen_draw_jupiter_bl)
# add parser for Jupiter topology at the level of switches (middle abstraction)
jupiter_parser = subparsers.add_parser("Jupiter")
jupiter_parser.add_argument("--s_b", type=int, help="spine_blocks: (defaults to 256), How many spine blocks to instantiate ,s_b >= a_b")
jupiter_parser.add_argument("--a_b", type=int, help="aggregation_blocks: (defaults to 64), How many aggregation blocks to instantiate ,a_b < s_b")
jupiter_parser.set_defaults(func=gen_draw_jupiter)

"""
Main body 
"""
def main():
    try:
        args = parser.parse_args()
        args.func(args)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()