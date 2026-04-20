import os
import random
import datetime
from readFiles.InterNetworkReader import InterNetworkReader
from readFiles.readVirtualNetwork import VirtualNetworkRequest
from readFiles.IntraNetworkReader import IntraNetworkReader
from readFiles.TransactionReader import TransactionReader
from algorithm.genetic import GeneticDomainSolver

from genetic import genetic_algorithm

networkType= "NSFNET"
folder =f"topologies/"+networkType

# intra-domain topoloji dosyalarında kaç node'lu ağlar kullanılacak (5, 6, 7 ...)
num_intranetwork_nodes = 5

def main():
    directory_path_InterNetwork = f"{folder}/internetwork/"
    all_files = os.listdir(directory_path_InterNetwork)
    txt_files_Names_InterNetwork = [file for file in all_files if file.endswith('.txt')]

    for file_name in txt_files_Names_InterNetwork:
        file_path_InterNetwork = os.path.join(directory_path_InterNetwork, file_name)
        interNetwork = InterNetworkReader(file_path_InterNetwork)

        #adjacencyInterNetwork = interNetwork.get_adjacency_matrix()
        #bandwidthInterNetwork = interNetwork.get_bandwidth_matrix()

    #-----------------------------------------------------------------------
    # INTRA NETWORK
    # Her run'da: klasörü tara → rastgele seç → txt'ye yaz → yükle
    directory_path_IntraNetwork = f"{folder}/intranetwork/"
    num_domains = interNetwork.get_numberOfInterNodes()  # inter-network kaç domain varsa o kadar intra seç

    intraNameList = selectFixedIntraNetwork(num_intranetwork_nodes, num_domains, directory_path_IntraNetwork)
    #intraNameList = selectAndSaveIntraNetworks(num_intranetwork_nodes, num_domains, directory_path_IntraNetwork)  # rastgele seçim
    intraNetworkTopologies = IntraNetworkReader.load_intra_topology(directory_path_IntraNetwork, intraNameList)

    #intra network düğüm sayısına göre okuma yapıyor
    #topologies = IntraNetworkReader.load_all_topologies_with_node_count(directory_path_IntraNetwork,num_intranetwork_nodes)

    #domain sayısına göre rastgele intranetwork seçiyor
    #selected_topologies = random.sample(topologies, interNetwork.get_numberOfInterNodes())

    #sadece cpu değerlerinin tutulduğu yer
    #cpu_value_all_intra_networks = [ [line[0] for line in topo.cpu_matrix] for topo in selected_topologies ]
    #----------------------------------------------------------------------------


    #-----------------------------------------------------------------------
    #read transaction
    directory_path_Transaction = f"{folder}/transactions/"

    for file_name in os.listdir(directory_path_Transaction):
        if file_name.endswith(".txt"):
            txt_name = os.path.splitext(file_name)[0]
            parts = txt_name.split('_')
            prefix = "_".join(parts[:-1])

    file_path_Transaction = f"{prefix}_{num_intranetwork_nodes}.txt"
    full_path_Transaction = os.path.join(directory_path_Transaction, file_path_Transaction)
    allTransaction, edgeRouter = TransactionReader(full_path_Transaction)
    #first = allTransaction[0]
    #print(first.fullpath)

    #read vn
    directory_path_VR = f"{folder}/virtualrequests/"
    all_files = os.listdir(directory_path_VR)
    txt_files_VR = [file for file in all_files if file.endswith('.txt')]

    for file_name in txt_files_VR:
        file_path = os.path.join(directory_path_VR, file_name)
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
        #population_size = 6
        #iterations = 50
        #vn_count = len(cpuVirtual)
        #best_chromosome, best_fitness = genetic_algorithm(vn_count, candidateDomains, population_size, iterations)
        #print("Best Chromosome:", best_chromosome)
        #print("Best Fitness:", best_fitness)
        #-----------------------------------------------

        solver = GeneticDomainSolver(allTransaction, edgeRouter, interNetwork, intraNetworkTopologies, virtualRequests)
        en_iyi_cozum, puan = solver.run(population_size=40, generations=1, mutation_rate=0.1, seed=None)

        print("\n--- SONUÇ ---")
        print(f"En İyi Fitness Skoru: {puan}")
        print(f"En İyi Kromozom:      {en_iyi_cozum}")

        # Kullanılan topoloji dosyaları
        print(f"\nKullanılan İntra Topolojiler ({len(intraNameList)} domain):")
        for idx, name in enumerate(intraNameList):
            print(f"  Domain {idx:>2}: {name}")

        # En iyi çözümün tüm yol detayları
        if en_iyi_cozum is not None:
            yol_detaylari = solver.trace_solution(en_iyi_cozum)
            yazYolDetaylari(yol_detaylari)


# -----------------------------------------------------------------------
# Her run başında intranetwork klasöründen rastgele seçim yapar ve
# intra_domain_used_list.txt dosyasını güncel seçimle sıfırlar.
#
# Parametreler:
#   num_intranetwork_nodes : kaç node'lu dosyalar aransın (5, 6, 7 ...)
#   num_domains            : kaç dosya seçilecek (inter-network node sayısı)
#   directory_path         : intranetwork klasör yolu
# -----------------------------------------------------------------------
def selectFixedIntraNetwork(num_intranetwork_nodes, num_domains, directory_path):
    """
    Sabit tek bir dosyayı num_domains kez tekrarlayarak döndürür.
    Test aşamasında tutarlı sonuç almak için kullanılır.
    Geçici — rastgele seçim için selectAndSaveIntraNetworks kullan.
    """
    list_file_path = f"{folder}/intra_domain_used_list.txt"
    prefix = f"adjacency_{num_intranetwork_nodes}_"

    all_candidates = sorted([
        f for f in os.listdir(directory_path)
        if f.startswith(prefix) and f.endswith('.txt')
    ])

    if not all_candidates:
        print(f"Hata: '{directory_path}' içinde '{prefix}*.txt' formatında dosya bulunamadı.")
        return []

    # Alfabetik sırada ilk dosyayı num_domains kez kullan
    fixed_file = all_candidates[0]
    selected = [fixed_file] * num_domains

    run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(list_file_path, 'w', encoding='utf-8') as f:
        f.write(f"# Run: {run_time} | SABİT | node_count={num_intranetwork_nodes} | domains={num_domains}\n")
        for fname in selected:
            f.write(fname + '\n')

    print(f"\n[Sabit Seçim] Tüm domainler için: {fixed_file}")
    return selected


def selectAndSaveIntraNetworks(num_intranetwork_nodes, num_domains, directory_path):
    list_file_path = f"{folder}/intra_domain_used_list.txt"
    prefix = f"adjacency_{num_intranetwork_nodes}_"

    # Klasördeki uygun tüm dosyaları tara
    all_candidates = [
        f for f in os.listdir(directory_path)
        if f.startswith(prefix) and f.endswith('.txt')
    ]

    if not all_candidates:
        print(f"Hata: '{directory_path}' içinde '{prefix}*.txt' formatında dosya bulunamadı.")
        return []

    if len(all_candidates) < num_domains:
        print(f"Uyarı: Gereken {num_domains} domain için yalnızca {len(all_candidates)} dosya var. Tümü kullanılıyor.")
        selected = all_candidates[:]
    else:
        selected = random.sample(all_candidates, num_domains)

    # Her run başında txt'yi sıfırla, seçilenleri yaz
    run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(list_file_path, 'w', encoding='utf-8') as f:
        f.write(f"# Run: {run_time} | node_count={num_intranetwork_nodes} | domains={num_domains}\n")
        for fname in selected:
            f.write(fname + '\n')

    print(f"\n[Seçim] {num_domains} domain için {num_intranetwork_nodes}-node'lu topoloji seçildi → {list_file_path}")
    return selected


# -----------------------------------------------------------------------
# En iyi çözümün yol detaylarını ekrana yazdırır.
# -----------------------------------------------------------------------
def yazYolDetaylari(yol_detaylari: list):
    print("\n--- YOL DETAYLARI ---")
    if not yol_detaylari:
        print("  (yol bulunamadı)")
        return

    toplam_hop = 0
    for link in yol_detaylari:
        print(f"\n  {link['sanal_baglanti']}")
        if 'inter_domain_yolu' in link:
            print(f"    Inter-domain yolu: {link['inter_domain_yolu']}")
        for seg in link['segmentler']:
            tip = seg['tip']
            if tip == 'domain gecisi':
                print(f"    [Geçiş] Domain {seg['kaynak_domain']} → Domain {seg['hedef_domain']}  (+1 hop)")
                toplam_hop += 1
            elif tip == 'HATA':
                print(f"    [HATA]  {seg['mesaj']}")
            else:
                yol_str = str(seg.get('yol', '?'))
                hop     = seg.get('hop', '?')
                domain  = seg.get('domain', '?')
                bas     = seg.get('baslangic_node', '?')
                bit     = seg.get('bitis_node', '?')
                bw      = seg.get('bw_talebi', '?')
                print(f"    [{tip}]  Domain {domain} | node {bas} → node {bit} | yol: {yol_str} | hop: {hop} | BW: {bw}")
                if isinstance(hop, int) and hop < 100000:
                    toplam_hop += hop

    print(f"\n  Toplam Hop: {toplam_hop}")


# -----------------------------------------------------------------------
# ESKİ FONKSİYON — txt dosyasını elle doldurulmuş varsayarak okurdu.
# Artık kullanılmıyor, referans için bırakıldı.
# -----------------------------------------------------------------------
# def readIntraNetwork_UsingTextFile(num_intranetwork_nodes):
#     selected_paths = []
#     list_file_path = f"{folder}/intra_domain_used_list.txt"
#     try:
#         with open(list_file_path, 'r', encoding='utf-8') as file:
#             for line in file:
#                 filename = line.strip()
#                 if not filename:
#                     continue
#                 parts = filename.split('_')
#                 if len(parts) > 1 and parts[0] == "adjacency":
#                     try:
#                         file_id = int(parts[1])
#                         if file_id == num_intranetwork_nodes:
#                             selected_paths.append(filename)
#                     except ValueError:
#                         continue
#     except FileNotFoundError:
#         print(f"Hata: {list_file_path} dosyası bulunamadı.")
#         return []
#     return selected_paths

if __name__ == "__main__":
    main()