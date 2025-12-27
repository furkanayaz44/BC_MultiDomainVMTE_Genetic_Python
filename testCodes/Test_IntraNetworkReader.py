import random
import sys
import os
import unittest

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from readFiles.IntraNetworkReader import IntraNetworkReader

networkType = "NSFNET"
folder = f"topologies/{networkType}"

class Test_IntraNetworkReader(unittest.TestCase):
    def test_readIntraNetwork(self):
        directory_path_Substrate = f"{folder}/intranetwork/"
        numberofNodes = 10


        topologies = IntraNetworkReader.load_all_topologies_with_node_count(directory_path_Substrate,numberofNodes)

        selected_topologies = random.sample(topologies, 10)
        for topo in selected_topologies:
            print(topo.file_name)

    def test_readIntraNetwork_Alone_CPU_Value(self):
        directory_path_Substrate = f"{folder}/intranetwork/"
        numberofNodes = 5


        topologies = IntraNetworkReader.load_all_topologies_with_node_count(directory_path_Substrate,numberofNodes)
        number_of_domain = 10
        selected_topologies = random.sample(topologies, number_of_domain)
        cpu_value_all_intra_networks = [ [line[0] for line in topo.cpu_matrix] for topo in selected_topologies ]
        print(cpu_value_all_intra_networks)


if __name__ == '__main__':
    unittest.main()
