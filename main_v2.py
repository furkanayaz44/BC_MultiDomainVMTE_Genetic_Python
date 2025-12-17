import os
from readInterNetwork import InterNetworkReader
from readVirtualNetwork import VirtualNetworkRequest
from readIntraNetwork import load_all_topologies_with_node_count

from genetic import genetic_algorithm 
def main():
    
    networkType= "NSFNET"
    folder =f"topologies/"+networkType

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
        #delayInterNetwork = interNetwork.get_delay_matrix()
        #reliabilityInterNetwork = interNetwork.get_reliability_matrix()
        #spectrumInterNetwork = interNetwork.get_spectrum_matrix()
        
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
        topology_list = load_all_topologies_with_node_count(intra_folder)

        print("aaa")



if __name__ == "__main__":
    main()