import os
import random
from readFiles.readInterNetwork import InterNetworkReader
from readFiles.readVirtualNetwork import VirtualNetworkRequest
from readFiles.IntraNetworkReader import IntraNetworkReader
from readFiles.TransactionReader import TransactionReader


from genetic import genetic_algorithm 

networkType= "NSFNET"
folder =f"topologies/"+networkType


def main():
    directory_path_Substrate = f"{folder}/internetwork/"
    all_files = os.listdir(directory_path_Substrate)
    txt_files_Substrate = [file for file in all_files if file.endswith('.txt')]

    for file_name in txt_files_Substrate:
        file_path = os.path.join(directory_path_Substrate, file_name)
        
        interNetwork = InterNetworkReader(file_path)

        adjacencyInterNetwork = interNetwork.get_adjacency_matrix()
        domainSayisi = len(adjacencyInterNetwork)
        
        #print(adjacencyInterNetwork)
        bandwidthInterNetwork = interNetwork.get_bandwidth_matrix()

    #-----------------------------------------------------------------------
    # Randomly select and read intranetworks based on the number of internetwork nodes
    directory_path_Substrate = f"{folder}/intranetwork/"
    #bu sayı interdomain içerisindeki node sayısını ifade etmektedir
    numberOfInterNodes = 10

    topologies = IntraNetworkReader.load_all_topologies_with_node_count(directory_path_Substrate,numberOfInterNodes)
    
    selected_topologies = random.sample(topologies, interNetwork.get_numberOfInterNodes())
    for topo in selected_topologies:
        file_name = topo.file_name
        print(file_name)
    #----------------------------------------------------------------------------

    #-----------------------------------------------------------------------
    #read transaction
    directory_path_Transaction = f"{folder}/transactions/"

    for file_name in os.listdir(directory_path_Transaction):
        if file_name.endswith(".txt"):
            txt_name = os.path.splitext(file_name)[0]
            parts = txt_name.split('_')
            prefix = "_".join(parts[:-1])

    #print(prefix)
    file_path_Transaction = f"{prefix}_{numberOfInterNodes}.txt"
    full_path_Transaction = os.path.join(directory_path_Transaction, file_path_Transaction)
    all_transactions = TransactionReader(full_path_Transaction)
    ilk = all_transactions[0]
    print(ilk.fullpath)

    #read vn
    directory_path_VR = f"{folder}/virtualrequests/"
    all_files = os.listdir(directory_path_VR)
    txt_files_VR = [file for file in all_files if file.endswith('.txt')]

    for file_name in txt_files_VR:
        file_path = os.path.join(directory_path_VR, file_name)
        #matrices = vread_matrices_with_specific_types(file_path)
        virtualRequests = VirtualNetworkRequest(file_path)

        if not virtualRequests:
            continue

        adjacencyVirtual = virtualRequests.adjacency_matrix
        #bandwidthVirtual = matrices.bandwidth_demand
        #delayVirtual = matrices.delay_matrix
        #reliabilityVirtual = matrices.reliability_matrix
        cpuVirtual = virtualRequests.cpu_ram_demand
        candidateDomains = virtualRequests.candidate_domains

        # print("Adjacency Matrix:", adjacencyVirtual)
        # print("Bandwidth Matrix:", bandwidthVirtual)
        # print("Delay Matrix:", delayVirtual)
        # print("Reliability Matrix:", reliabilityVirtual)
        # print("CPU Matrix:", cpuVirtual)

        population_size = 6  # Popülasyon büyüklüğü
        iterations = 50  # Maksimum iterasyon sayısı

        vn_count = len(cpuVirtual)
        best_chromosome, best_fitness = genetic_algorithm(vn_count, candidateDomains, population_size, iterations)
        print("Best Chromosome:", best_chromosome)
        print("Best Fitness:", best_fitness)

        intra_folder = f"{folder}/intranetwork/"
        topology_list = IntraNetworkReader.load_all_topologies_with_node_count(intra_folder)

        print("aaa")



if __name__ == "__main__":
    main()