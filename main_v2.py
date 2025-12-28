import os
import random
from readFiles.InterNetworkReader import InterNetworkReader
from readFiles.readVirtualNetwork import VirtualNetworkRequest
from readFiles.IntraNetworkReader import IntraNetworkReader
from readFiles.TransactionReader import TransactionReader
from algorithm.genetic import GeneticDomainSolver

from genetic import genetic_algorithm 

networkType= "NSFNET"
folder =f"topologies/"+networkType

#bu sayı interdomain içerisindeki node sayısını ifade etmektedir
num_intranetwork_nodes = 5

def main():
    directory_path_InterNetwork = f"{folder}/internetwork/"
    all_files = os.listdir(directory_path_InterNetwork)
    txt_files_Names_InterNetwork = [file for file in all_files if file.endswith('.txt')]

    for file_name in txt_files_Names_InterNetwork:
        file_path_InterNetwork = os.path.join(directory_path_InterNetwork, file_name)
        
        interNetwork = InterNetworkReader(file_path_InterNetwork)

        #adjacencyInterNetwork = interNetwork.get_adjacency_matrix()
        #print(adjacencyInterNetwork)
        #bandwidthInterNetwork = interNetwork.get_bandwidth_matrix()

    #-----------------------------------------------------------------------
    # Randomly select and read intranetworks based on the number of internetwork nodes
    directory_path_IntraNetwork = f"{folder}/intranetwork/"
    
    #yeni kod gelen txt ye göre ekleme yapıyor
    intraNameList = readIntraNetwork_UsingTextFile(num_intranetwork_nodes)
    topologies = IntraNetworkReader.load_intra_topology(directory_path_IntraNetwork,intraNameList)

    #intra network düğüm sayısına göre okuma yapıyor
    #topologies = IntraNetworkReader.load_all_topologies_with_node_count(directory_path_IntraNetwork,num_intranetwork_nodes)

    #domain sayısına göre rastgele intranetwork seçiyor
    selected_topologies = random.sample(topologies, interNetwork.get_numberOfInterNodes())
    #sadece cpu değerlerinin tutulduğu yer
    cpu_value_all_intra_networks = [ [line[0] for line in topo.cpu_matrix] for topo in selected_topologies ]
    
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
    file_path_Transaction = f"{prefix}_{num_intranetwork_nodes}.txt"
    full_path_Transaction = os.path.join(directory_path_Transaction, file_path_Transaction)
    allTransaction,edgeRouter = TransactionReader(full_path_Transaction)
    first = allTransaction[0]
    #print(first.fullpath)

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
        cpu_demand_VirtualNetwork = [ [line[0] for line in cpuVirtual] ]
        candidateDomains = virtualRequests.candidate_domains

        #-----------------------------------------------
        #eski kod

        #population_size = 6  # Popülasyon büyüklüğü
        #iterations = 50  # Maksimum iterasyon sayısı

        #vn_count = len(cpuVirtual)
        #best_chromosome, best_fitness = genetic_algorithm(vn_count, candidateDomains, population_size, iterations)
        #print("Best Chromosome:", best_chromosome)
        #print("Best Fitness:", best_fitness)
        #-----------------------------------------------

        solver = GeneticDomainSolver(cpu_value_all_intra_networks, candidateDomains, cpu_demand_VirtualNetwork[0])
        en_iyi_cozum, puan = solver.run(population_size=4, generations=1, mutation_rate=0.1, seed=None)

        print("\n--- SONUÇ ---")
        print(f"En İyi Fitness Skoru: {puan}")
        print(f"En İyi Kromozom: {en_iyi_cozum}")


        print("aaa")


def readIntraNetwork_UsingTextFile(num_intranetwork_nodes):
    selected_paths = []
    list_file_path = f"{folder}/intra_domain_used_list.txt"

    try:
        with open(list_file_path, 'r', encoding='utf-8') as file:
            for line in file:
                filename = line.strip()
                if not filename:
                    continue
                parts = filename.split('_')
                if len(parts) > 1 and parts[0] == "adjacency":
                    try:
                        file_id = int(parts[1])
                        
                        if file_id == num_intranetwork_nodes:
                            directory_path_Substrate = f"{folder}/intranetwork/"
                            selected_paths.append(filename)
                    except ValueError:
                        continue
    except FileNotFoundError:
        print(f"Hata: {list_file_path} dosyası bulunamadı.")
        return []
    return selected_paths

if __name__ == "__main__":
    main()