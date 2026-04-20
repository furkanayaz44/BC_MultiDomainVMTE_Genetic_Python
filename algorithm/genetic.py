import random
import math
from typing import List, Optional, Tuple, Dict
import numpy as np
import networkx as nx

class GeneticDomainSolver:
    # selection_mode: 'cpu' | 'roulette' | 'rank' | 'softmax' | 'qlearning'
    def __init__(self, allTransaction, edgeRouter, interNetwork, intraNetworkTopologies,
                 virtualRequests, selection_mode: str = 'cpu', softmax_temperature: float = 1.0,
                 ql_alpha: float = 0.1, ql_epsilon: float = 0.8):

        self.selection_mode = selection_mode
        self.softmax_temperature = softmax_temperature

        # Q-Learning parametreleri (sadece selection_mode='qlearning' olduğunda kullanılır)
        self.ql_alpha         = ql_alpha    # öğrenme hızı
        self.ql_epsilon       = ql_epsilon  # keşif oranı (başlangıç: 0.8 → yüksek keşif)
        self.ql_epsilon_min   = 0.05        # epsilon bu değerin altına düşmez
        self.ql_epsilon_decay = 0.85        # her nesil sonunda epsilon *= 0.85
        # Q-tablosu: anahtar (gen_idx, domain_id, domain_doluluk, node_id) → öğrenilen değer
        self.q_table: Dict[Tuple, float] = {}

        #tanımlamalar
        self.allTransaction = allTransaction
        self.edgeRouter = edgeRouter
        self.interNetwork = interNetwork
        self.intraNetworkTopologies = intraNetworkTopologies
        self.virtualRequests = virtualRequests


        self.cpu_value_all_intra_networks = [ [line[0] for line in topo.cpu_matrix] for topo in self.intraNetworkTopologies ]
        self.candidateDomains = self.virtualRequests.candidate_domains      # [[Domain1, Domain2], ...]
        cpuVirtual = self.virtualRequests.cpu_ram_demand
        tmp = [ [line[0] for line in cpuVirtual] ]        # [Talep1, Talep2, ...]
        self.cpu_demand_VirtualNetwork = tmp[0]
        self.num_genes = len(self.candidateDomains)
        
        #vn ler cpu demand e göre sılandı
        self.sorted_indices = sorted(range(self.num_genes), key=lambda i: self.cpu_demand_VirtualNetwork[i], reverse=True)

        self.interNetworkNumpyAjacencyGraph = self.convertGxInterNetwork()
        #edge router seperate 
        self.edgeRouterDomainVertexList = self.edgeRouterDomainNodeListSeperate()
        self.intraNetworkGraphwithBWMatrix = self.convertGxAllIntraNetwork()
        


    def convertGxAllIntraNetwork(self):
        gx_list = []
        for intra in self.intraNetworkTopologies:
            adj_matrix = np.array(intra.adjacency_matrix)
            bw_matrix = np.array(intra.bandwidth_matrix)
            G = nx.Graph()
            rows, cols = adj_matrix.shape
            for i in range(rows):
                for j in range(cols):
                    if adj_matrix[i][j] == 1:
                        G.add_edge(i, j, bw=bw_matrix[i][j])
            #nparray = nx.from_numpy_array(G)
            gx_list.append(G)
        return gx_list

    def convertGxInterNetwork(self):
        adj_matrix = np.array(self.interNetwork.adjacency_matrix)
        bw_matrix  = np.array(self.interNetwork.bandwidth_matrix)
        G = nx.Graph()
        rows, cols = adj_matrix.shape
        for i in range(rows):
            for j in range(cols):
                if adj_matrix[i][j] == 1:
                    G.add_edge(i, j, bw=int(bw_matrix[i][j]))
        return G

    #edgeRouter bölme işlemi
    def edgeRouterDomainNodeListSeperate(self):
        list = []
        for edge in self.edgeRouter:
            transactionIdIngress = edge.TransactionId
            list.append([edge.edgeDomainIngress,edge.edgeNodeIngress,transactionIdIngress])

            transactionIdEgress = edge.TransactionId
            list.append([edge.edgeDomainEgress,edge.edgeNodeEgress,transactionIdEgress])
            np_matris = np.array(list)
        return np_matris
    

    def _find_inter_path_by_bw(self, source_domain: int, dest_domain: int, required_bw: int):
        """
        Inter-domain grafta BW kısıtını karşılayan en kısa domain yolunu döndürür.
        Yol bulunamazsa None döner.
        convertGxInterNetwork artık her edge'e bw niteliği ekliyor.
        """
        valid_edges = [
            (u, v) for u, v, attr in self.interNetworkNumpyAjacencyGraph.edges(data=True)
            if attr.get('bw', 0) >= required_bw
        ]
        filtered_G = self.interNetworkNumpyAjacencyGraph.edge_subgraph(valid_edges)
        try:
            return nx.shortest_path(filtered_G, source=source_domain, target=dest_domain)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def find_shortest_path_by_bw(self,graph, source, dest, required_bw):
        valid_edges = [
            (u, v) for u, v, attr in graph.edges(data=True) 
            if attr.get('bw', 0) >= required_bw
        ]
        
        filtered_G = graph.edge_subgraph(valid_edges)
        
        try:
            path = nx.shortest_path(filtered_G, source=source, target=dest)
            
            hop_count = len(path) - 1
            return path, hop_count
            
        except nx.NetworkXNoPath:
            return None, 0

    # -----------------------------------------------------------------------
    # Artık BW (residual bandwidth) takibi için yardımcı metodlar
    #
    # Her calculate_fitness_v2 / trace_solution çağrısı _build_residual_maps()
    # ile orijinal değerlerden başlayan bağımsız haritalar alır.
    # Haritalar yerel değişken olduğundan:
    #   - Aynı algoritma içindeki farklı kromozomlar birbirini etkilemez.
    #   - GA, ACO, Greedy tamamen bağımsız çalışır; biri bitince diğeri
    #     orijinal BW değerleriyle başlar.
    # -----------------------------------------------------------------------

    def _build_residual_maps(self):
        """
        Orijinal BW matrislerinden başlayarak bu çağrıya özgü artık BW
        haritaları oluşturur.

        intra_res : {domain_id: {(min_u, max_v): kalan_bw}}
        inter_res : {(min_d1, max_d2): kalan_bw}
        bc_res    : {id(transaction): kalan_bw}  — Python nesne kimliği
        """
        intra_res = {}
        for d, G in enumerate(self.intraNetworkGraphwithBWMatrix):
            intra_res[d] = {
                (min(u, v), max(u, v)): data.get('bw', 0)
                for u, v, data in G.edges(data=True)
            }

        inter_res = {
            (min(u, v), max(u, v)): data.get('bw', 0)
            for u, v, data in self.interNetworkNumpyAjacencyGraph.edges(data=True)
        }

        # Blockchain pathlet transactionları (ASId >= 0)
        bc_res = {id(t): t.minBandwidth for t in self.allTransaction}

        # Edge router bağlantıları (ASId == -1) — domain sınırı +1 hop kapasitesi
        er_res = {id(er): er.minBandwidth for er in self.edgeRouter}

        return intra_res, inter_res, bc_res, er_res

    def _find_path_intra_residual(self, domain_id, src, dst, required_bw, intra_res):
        """
        Artık BW kısıtına göre intra-domain en kısa yolu bulur.
        Yalnızca residual BW >= required_bw olan linkler kullanılır.
        Kullanılan her linkten required_bw kadar residual BW düşer.

        Döner: (path, hops)  — bulunamazsa (None, 100000)
        """
        res = intra_res[domain_id]
        base_G = self.intraNetworkGraphwithBWMatrix[domain_id]

        # Sadece yeterli residual BW'ye sahip kenarlardan oluşan geçici graf
        filtered_G = nx.Graph()
        filtered_G.add_nodes_from(base_G.nodes())
        for (u, v), bw in res.items():
            if bw >= required_bw:
                filtered_G.add_edge(u, v)

        try:
            path = nx.shortest_path(filtered_G, source=src, target=dst)
            hops = len(path) - 1
            for i in range(hops):
                key = (min(path[i], path[i + 1]), max(path[i], path[i + 1]))
                if key in res:
                    res[key] -= required_bw
            return path, hops
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None, 100000

    def _find_inter_path_residual(self, src_domain, dst_domain, required_bw, inter_res):
        """
        Artık BW haritasına göre inter-domain en kısa yolu bulur;
        kullanılan her domain bağlantısından required_bw kadar BW düşer.

        Döner: domain id listesi  — bulunamazsa None
        """
        filtered_G = nx.Graph()
        filtered_G.add_nodes_from(self.interNetworkNumpyAjacencyGraph.nodes())
        for (u, v), bw in inter_res.items():
            if bw >= required_bw:
                filtered_G.add_edge(u, v)

        try:
            path = nx.shortest_path(filtered_G, source=src_domain, target=dst_domain)
            for i in range(len(path) - 1):
                key = (min(path[i], path[i + 1]), max(path[i], path[i + 1]))
                if key in inter_res:
                    inter_res[key] -= required_bw
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def _find_bc_residual(self, domain, src_node, dst_node, required_bw, bc_res):
        """
        Artık BW haritasına göre en az hop'lu BC transaction'ını bulur;
        seçilen transaction'ın artık BW'sinden required_bw kadar düşer.

        Döner: (transaction, hops)  — bulunamazsa (None, 100000)
        """
        best_t = None
        best_hops = 100000

        for t in self.allTransaction:
            if t.edgeDomainEgress != domain:
                continue
            node_match = (
                (t.edgeNodeIngress == src_node and t.edgeNodeEgress == dst_node) or
                (t.edgeNodeIngress == dst_node  and t.edgeNodeEgress == src_node)
            )
            if not node_match:
                continue
            if bc_res.get(id(t), 0) < required_bw:   # artık BW yetersiz
                continue
            if t.getNumOfHops() < best_hops:
                best_hops = t.getNumOfHops()
                best_t = t

        if best_t is not None:
            bc_res[id(best_t)] -= required_bw
            return best_t, best_hops

        return None, 100000

    def calculate_fitness(self, chromosome: List[str]) -> float:
        
        #if chromosome is None: return 0.0
        if chromosome is None: return float('inf')


        adjMatrixVirtualRequests = self.virtualRequests.adjacency_matrix
        allIntraNetworkTopologies = self.intraNetworkTopologies

        total_residual_cpu = 0
        
        # Hangi domainde hangi node kullanılmış ve ne kadar talep var?
        #1. domain bilgisi 2. intra dügün bilgisi
        # kromozom istek boyutu kadar
        # chromosome: ["1-5", "2-3", ...]
        n = len(adjMatrixVirtualRequests)
        totalHops = 0
        for row in range(n -1):
            for column in range(row + 1, n):
                 
                source = chromosome[row]
                
                if adjMatrixVirtualRequests[row][column] > 0:
                    destination = chromosome[column]
                    if source != destination:
                        #source ve destination için domain ve intra vertex leri ayırma burada
                        sourceDomainId, sourceIntraNodeId  = self._parse_gene(source)
                        destinationDomainId, destinationIntraNodeId  = self._parse_gene(destination)
                        
                        #source eğer edgerouter ise onun bilgisini alıyoruz
                        # sourceSearchEdge = (self.edgeRouterDomainVertexList[:, 0] == sourceDomainId) & (self.edgeRouterDomainVertexList[:, 1] == sourceIntraNodeId)
                        # sourceIndex = np.where(sourceSearchEdge)[0]
                        
                        #destination eğer edgerouter ise onun bilgisini alıyoruz
                        # destinationSearchEdge = (self.edgeRouterDomainVertexList[:, 0] == destinationDomainId) & (self.edgeRouterDomainVertexList[:, 1] == destinationIntraNodeId)
                        # destinationindex = np.where(destinationSearchEdge)[0]
                        
                        interDomainPathList = nx.shortest_path(self.interNetworkNumpyAjacencyGraph, source=sourceDomainId, target=destinationDomainId, weight='weight')
                        length = nx.shortest_path_length(self.interNetworkNumpyAjacencyGraph, source=sourceDomainId, target=destinationDomainId, weight='weight')


                        #print(f"interDomainPathList-> {interDomainPathList}")
                        
                        currentDomain = sourceDomainId
                        currentEdge = sourceIntraNodeId
                        for i in range(len(interDomainPathList)-1):
                            
                            sourceSearchEdge = (self.edgeRouterDomainVertexList[:, 0] == currentDomain) & (self.edgeRouterDomainVertexList[:, 1] == currentEdge)
                            sourceIndex = np.where(sourceSearchEdge)[0]

                            if  interDomainPathList[i]== currentDomain:
                                #bu dongu ile edge routerlar üzerinde arama yapıp onun bilgisini alıyoruz.
                                #bu bilgiye göre intra içinde en kısa yol ile edge router gidilecek
                                #daha sonrasında diğer domain e geçilecek ve orada gezilecek
                                for counter,edge in enumerate(self.edgeRouter):
                                    if (edge.edgeDomainIngress == interDomainPathList[i] and edge.edgeDomainEgress == interDomainPathList[i+1]):
                                        domainicihedefdugum = edge.edgeNodeIngress
                                        nextDomain = edge.edgeDomainEgress
                                        nextEdge = edge.edgeNodeEgress
                                        break
                                    #egress te 
                                    if (edge.edgeDomainEgress == interDomainPathList[i] and edge.edgeDomainIngress == interDomainPathList[i+1]):
                                        domainicihedefdugum = edge.edgeNodeEgress
                                        nextDomain = edge.edgeDomainIngress
                                        nextEdge = edge.edgeNodeIngress
                                        break
                                if sourceIndex.size == 0:
                                    path, hops = self.find_shortest_path_by_bw(self.intraNetworkGraphwithBWMatrix[interDomainPathList[i]],currentEdge,domainicihedefdugum,1)
                                    totalHops = totalHops + hops
                                    #print(f"Seçilen Yol: {path}")
                                    #print(f"Adım Sayısı (Hop): {hops}")
                                #edge router else ise
                                else:
                                    numOfHops = 100000
                                    for count, transaction in enumerate(self.allTransaction):
                                        if transaction.edgeDomainEgress == currentDomain:
                                            if (transaction.edgeNodeIngress ==  currentEdge and transaction.edgeNodeEgress == domainicihedefdugum) or (transaction.edgeNodeIngress == domainicihedefdugum and transaction.edgeNodeEgress == currentEdge):
                                                if transaction.getNumOfHops() < numOfHops:
                                                    #burada sadece hop sayısı alıyoruz buraya guncelleme islemi gelecek
                                                    numOfHops = transaction.getNumOfHops()
                                                    path = transaction.getFullPath
                                    # +1 artık bu kısımla işim bitti sonra ki domain e geçtiğim için eklendi
                                    totalHops = totalHops + numOfHops + 1
                                    #print(numOfHops)
                            currentDomain = nextDomain
                            currentEdge = nextEdge




                        # for i in range(len(interDomainPathList)-1):
                        #     if  interDomainPathList[i]== sourceDomainId:
                        #         #bu dongu ile edge routerlar üzerinde arama yapıp onun bilgisini alıyoruz.
                        #             #bu bilgiye göre intra içinde en kısa yol ile edge router gidilecek
                        #             #daha sonrasında diğer domain e geçilecek ve orada gezilecek
                        #         for counter,edge in enumerate(self.edgeRouter):
                        #             if (edge.edgeDomainIngress == interDomainPathList[i] and edge.edgeDomainEgress == interDomainPathList[i+1]):
                        #                 domainicihedefdugum = edge.edgeNodeIngress
                        #                 nextDomain = edge.edgeDomainEgress
                        #                 nextEdge = edge.edgeNodeEgress
                        #                 break
                        #             #egress te 
                        #             if (edge.edgeDomainEgress == interDomainPathList[i] and edge.edgeDomainIngress == interDomainPathList[i+1]):
                        #                 domainicihedefdugum = edge.edgeNodeEgress
                        #                 nextDomain = edge.edgeDomainIngress
                        #                 nextEdge = edge.edgeNodeIngress
                        #                 break
                        #         if sourceIndex.size == 0:
                        #             path, hops = self.find_shortest_path_by_bw(self.intraNetworkGraphwithBWMatrix[interDomainPathList[i]],sourceIntraNodeId,domainicihedefdugum,1)
                        #             totalHops = totalHops + hops
                        #             print(f"Seçilen Yol: {path}")
                        #             print(f"Adım Sayısı (Hop): {hops}")

                        #         #edge router else ise
                        #         else:
                        #             numOfHops = 100000
                        #             for count, transaction in enumerate(self.allTransaction):
                        #                 if transaction.edgeDomainEgress == sourceDomainId:
                        #                     if (transaction.edgeNodeIngress ==  sourceIntraNodeId and transaction.edgeNodeEgress == domainicihedefdugum) or (transaction.edgeNodeIngress == domainicihedefdugum and transaction.edgeNodeEgress == sourceIntraNodeId):
                        #                         if transaction.getNumOfHops() < numOfHops:
                        #                             #burada sadece hop sayısı alıyoruz buraya guncelleme islemi gelecek
                        #                             numOfHops = transaction.getNumOfHops()
                        #             # +1 artık bu kısımla işim bitti sonra ki domain e geçtiğim için eklendi
                        #             totalHops = totalHops + hops + 1
                        #             print(numOfHops)
                            
                        #     #ara düğümler için transaction üzerinde sadece geçitler hesaplanmalı
                        #     elif interDomainPathList[i] != destinationDomainId:
                        #         for counter,edge in enumerate(self.edgeRouter):
                        #             if (edge.edgeDomainIngress == interDomainPathList[i] and edge.edgeDomainEgress == interDomainPathList[i+1]):
                        #                 domainicihedefdugum = edge.edgeNodeIngress
                        #                 nextDomain = edge.edgeDomainEgress
                        #                 nextEdge = edge.edgeNodeEgress
                        #                 break
                        #             #egress te 
                        #             if (edge.edgeDomainEgress == interDomainPathList[i] and edge.edgeDomainIngress == interDomainPathList[i+1]):
                        #                 domainicihedefdugum = edge.edgeNodeEgress
                        #                 nextDomain = edge.edgeDomainIngress
                        #                 nextEdge = edge.edgeNodeIngress
                        #                 break
                        #         print("dest")
                        

        return totalHops

    # -----------------------------------------------------------------------
    # calculate_fitness_v2: Orijinal metod korundu, bu versiyon düzeltilmiş halidir.
    #
    # Yapılan düzeltmeler:
    #   1. None kromozom → float('inf') döndürülür (eskisi 0.0 döndürüyordu,
    #      bu yüzden geçersiz kromozom "en iyi" seçilebiliyordu)
    #   2. Aynı domain, farklı node → intra-domain hop hesaplanır
    #      (eskisi 0 hop ekliyordu, çünkü interDomainPath tek elemanlıydı)
    #   3. Son domain'in iç yolu hesaplanır (destinasyon node'a kadar)
    #      (eskisi döngü son domain'e girmeden bitiyordu)
    #   4. nextDomain / nextEdge / domainicihedefdugum None ile başlatıldı
    #      (eskisi edge router bulunamazsa NameError veya stale değer üretiyordu)
    #   5. CPU kısıt ihlali tespiti ve ceza eklendi
    #      (eskisi total_residual_cpu tanımlı ama hiç kullanılmıyordu)
    #   6. Kullanılmayan 'length' ve 'allIntraNetworkTopologies' değişkenleri kaldırıldı
    #   7. Transaction bulunamazsa uyarı mesajı eklendi
    # -----------------------------------------------------------------------
    def calculate_fitness_v2(self, chromosome: List[str]) -> float:

        if chromosome is None:
            return float('inf')

        adjMatrixVirtualRequests = self.virtualRequests.adjacency_matrix
        n = len(adjMatrixVirtualRequests)
        totalHops = 0

        # ---- Artık BW haritaları: bu çağrıya özgü, orijinal değerlerden başlar ----
        # Yerel değişken olduğundan GA/ACO/Greedy ve farklı kromozomlar
        # birbirinin BW tüketimini görmez — tam bağımsızlık sağlanır.
        intra_res, inter_res, bc_res, er_res = self._build_residual_maps()

        # Tekil düğüm kısıtı: aynı (domain, node) iki farklı sanal düğüme atanamaz
        seen_genes = set()
        for gene in chromosome:
            if gene in seen_genes:
                totalHops += 100000   # çakışma → büyük ceza
            seen_genes.add(gene)

        # CPU kısıt kontrolü
        for gene_idx, gene in enumerate(chromosome):
            d, node = self._parse_gene(gene)
            cpu_cap = self.cpu_value_all_intra_networks[d][node]
            cpu_req = self.cpu_demand_VirtualNetwork[gene_idx]
            if cpu_cap < cpu_req:
                totalHops += 100000

        for row in range(n - 1):
            for column in range(row + 1, n):

                source = chromosome[row]
                if adjMatrixVirtualRequests[row][column] <= 0:
                    continue

                destination = chromosome[column]
                if source == destination:
                    continue

                required_bw = self.virtualRequests.bandwidth_demand[row][column]
                sourceDomainId, sourceIntraNodeId = self._parse_gene(source)
                destinationDomainId, destinationIntraNodeId = self._parse_gene(destination)

                # Aynı domain, farklı node
                if sourceDomainId == destinationDomainId:
                    _, hops = self._find_path_intra_residual(
                        sourceDomainId, sourceIntraNodeId, destinationIntraNodeId,
                        required_bw, intra_res
                    )
                    totalHops += hops
                    continue

                # Farklı domain: artık BW'ye göre inter-domain yolu bul
                interDomainPathList = self._find_inter_path_residual(
                    sourceDomainId, destinationDomainId, required_bw, inter_res
                )
                if interDomainPathList is None:
                    totalHops += 100000
                    continue

                currentDomain = sourceDomainId
                currentEdge = sourceIntraNodeId
                path_broken = False

                for step in range(len(interDomainPathList) - 1):

                    sourceSearchEdge = (
                        (self.edgeRouterDomainVertexList[:, 0] == currentDomain) &
                        (self.edgeRouterDomainVertexList[:, 1] == currentEdge)
                    )
                    sourceIndex = np.where(sourceSearchEdge)[0]

                    domainicihedefdugum = None
                    nextDomain = None
                    nextEdge = None
                    chosen_er = None

                    for edge in self.edgeRouter:
                        if er_res.get(id(edge), 0) < required_bw:
                            continue   # bu edge router'ın artık BW'si yetersiz
                        if (edge.edgeDomainIngress == interDomainPathList[step] and
                                edge.edgeDomainEgress == interDomainPathList[step + 1]):
                            domainicihedefdugum = edge.edgeNodeIngress
                            nextDomain = edge.edgeDomainEgress
                            nextEdge = edge.edgeNodeEgress
                            chosen_er = edge
                            break
                        if (edge.edgeDomainEgress == interDomainPathList[step] and
                                edge.edgeDomainIngress == interDomainPathList[step + 1]):
                            domainicihedefdugum = edge.edgeNodeEgress
                            nextDomain = edge.edgeDomainIngress
                            nextEdge = edge.edgeNodeIngress
                            chosen_er = edge
                            break

                    if domainicihedefdugum is None:
                        print(f"Uyari: {interDomainPathList[step]}->{interDomainPathList[step+1]} "
                              f"arasi BW={required_bw} icin uygun edge router bulunamadi.")
                        totalHops += 100000
                        path_broken = True
                        break

                    # Seçilen edge router'ın artık BW'sini düş
                    er_res[id(chosen_er)] -= required_bw

                    if sourceIndex.size == 0:
                        # Normal node: artık BW kısıtlı intra yol
                        _, hops = self._find_path_intra_residual(
                            interDomainPathList[step], currentEdge, domainicihedefdugum,
                            required_bw, intra_res
                        )
                        totalHops += hops
                    else:
                        # Edge router: önce BC transaction dene, bulamazsan topoloji
                        t, numOfHops = self._find_bc_residual(
                            currentDomain, currentEdge, domainicihedefdugum,
                            required_bw, bc_res
                        )
                        if t is None:
                            # BC yeterli BW'ye sahip değil → intra topoloji ile fallback
                            _, numOfHops = self._find_path_intra_residual(
                                interDomainPathList[step], currentEdge, domainicihedefdugum,
                                required_bw, intra_res
                            )
                        totalHops += numOfHops + 1

                    currentDomain = nextDomain
                    currentEdge = nextEdge

                # Son domain iç yolu
                if not path_broken and currentDomain == destinationDomainId:

                    destSearchEdge = (
                        (self.edgeRouterDomainVertexList[:, 0] == destinationDomainId) &
                        (self.edgeRouterDomainVertexList[:, 1] == destinationIntraNodeId)
                    )
                    destIsEdgeRouter = np.where(destSearchEdge)[0].size > 0

                    if destIsEdgeRouter:
                        t, numOfHops = self._find_bc_residual(
                            destinationDomainId, currentEdge, destinationIntraNodeId,
                            required_bw, bc_res
                        )
                        if t is None:
                            # BC bulunamadı → topoloji grafıyla dene
                            _, numOfHops = self._find_path_intra_residual(
                                destinationDomainId, currentEdge, destinationIntraNodeId,
                                required_bw, intra_res
                            )
                        totalHops += numOfHops
                    else:
                        _, hops = self._find_path_intra_residual(
                            destinationDomainId, currentEdge, destinationIntraNodeId,
                            required_bw, intra_res
                        )
                        totalHops += hops

        return totalHops

    # -----------------------------------------------------------------------
    # trace_solution: En iyi kromozom için tüm yol segmentlerini izler.
    # calculate_fitness_v2 ile aynı mantığı izler ama hop saymak yerine
    # her segmentin detayını (tip, domain, yol, kaynak) toplar ve döndürür.
    # -----------------------------------------------------------------------
    def trace_solution(self, chromosome: List[str]) -> List[dict]:
        if chromosome is None:
            return []

        # Artık BW haritaları: bu çağrıya özgü, orijinal değerlerden başlar
        intra_res, inter_res, bc_res, er_res = self._build_residual_maps()

        adjMatrixVirtualRequests = self.virtualRequests.adjacency_matrix
        n = len(adjMatrixVirtualRequests)
        virtual_links = []

        for row in range(n - 1):
            for column in range(row + 1, n):
                source = chromosome[row]
                if adjMatrixVirtualRequests[row][column] <= 0:
                    continue

                destination = chromosome[column]
                if source == destination:
                    continue

                sourceDomainId, sourceIntraNodeId = self._parse_gene(source)
                destinationDomainId, destinationIntraNodeId = self._parse_gene(destination)
                required_bw = self.virtualRequests.bandwidth_demand[row][column]

                link = {
                    'sanal_baglanti': f"VN{row}({source}) -> VN{column}({destination})",
                    'bw_talebi': required_bw,
                    'segmentler': []
                }

                # Aynı domain
                if sourceDomainId == destinationDomainId:
                    path, hops = self._find_path_intra_residual(
                        sourceDomainId, sourceIntraNodeId, destinationIntraNodeId,
                        required_bw, intra_res
                    )
                    link['segmentler'].append({
                        'tip': 'intra (topoloji)',
                        'domain': sourceDomainId,
                        'baslangic_node': sourceIntraNodeId,
                        'bitis_node': destinationIntraNodeId,
                        'yol': path,
                        'hop': hops,
                        'bw_talebi': required_bw
                    })
                    virtual_links.append(link)
                    continue

                # Farklı domain: artık BW'ye göre inter-domain yol
                interDomainPathList = self._find_inter_path_residual(
                    sourceDomainId, destinationDomainId, required_bw, inter_res
                )
                if interDomainPathList is None:
                    link['segmentler'].append({
                        'tip': 'HATA',
                        'mesaj': f"BW={required_bw} artik BW'si yeterli inter-domain yol bulunamadi: "
                                 f"domain {sourceDomainId} -> {destinationDomainId}"
                    })
                    virtual_links.append(link)
                    continue
                link['inter_domain_yolu'] = interDomainPathList

                currentDomain = sourceDomainId
                currentEdge = sourceIntraNodeId
                path_broken = False

                for step in range(len(interDomainPathList) - 1):
                    sourceSearchEdge = (
                        (self.edgeRouterDomainVertexList[:, 0] == currentDomain) &
                        (self.edgeRouterDomainVertexList[:, 1] == currentEdge)
                    )
                    sourceIndex = np.where(sourceSearchEdge)[0]

                    domainicihedefdugum = None
                    nextDomain = None
                    nextEdge = None
                    chosen_er = None

                    for edge in self.edgeRouter:
                        if er_res.get(id(edge), 0) < required_bw:
                            continue   # artık BW yetersiz
                        if (edge.edgeDomainIngress == interDomainPathList[step] and
                                edge.edgeDomainEgress == interDomainPathList[step + 1]):
                            domainicihedefdugum = edge.edgeNodeIngress
                            nextDomain = edge.edgeDomainEgress
                            nextEdge = edge.edgeNodeEgress
                            chosen_er = edge
                            break
                        if (edge.edgeDomainEgress == interDomainPathList[step] and
                                edge.edgeDomainIngress == interDomainPathList[step + 1]):
                            domainicihedefdugum = edge.edgeNodeEgress
                            nextDomain = edge.edgeDomainIngress
                            nextEdge = edge.edgeNodeIngress
                            chosen_er = edge
                            break

                    if domainicihedefdugum is None:
                        link['segmentler'].append({
                            'tip': 'HATA',
                            'mesaj': f"Edge router bulunamadi (BW={required_bw}): "
                                     f"domain {interDomainPathList[step]} -> {interDomainPathList[step+1]}"
                        })
                        path_broken = True
                        break

                    # Seçilen edge router'ın artık BW'sini düş
                    er_res[id(chosen_er)] -= required_bw

                    if sourceIndex.size == 0:
                        # Normal node → artık BW kısıtlı topoloji yolu
                        path, hops = self._find_path_intra_residual(
                            interDomainPathList[step], currentEdge, domainicihedefdugum,
                            required_bw, intra_res
                        )
                        link['segmentler'].append({
                            'tip': 'intra (topoloji)',
                            'domain': interDomainPathList[step],
                            'baslangic_node': currentEdge,
                            'bitis_node': domainicihedefdugum,
                            'yol': path,
                            'hop': hops,
                            'bw_talebi': required_bw
                        })
                    else:
                        # Edge router → BC transaction dene, bulamazsan topoloji fallback
                        t, numOfHops = self._find_bc_residual(
                            currentDomain, currentEdge, domainicihedefdugum,
                            required_bw, bc_res
                        )
                        if t is not None:
                            tip = 'intra (blokzincir)'
                            yol = t.fullpath
                        else:
                            tip = 'intra (topoloji, bc bw yetersiz)'
                            yol, numOfHops = self._find_path_intra_residual(
                                interDomainPathList[step], currentEdge, domainicihedefdugum,
                                required_bw, intra_res
                            )
                        link['segmentler'].append({
                            'tip': tip,
                            'domain': currentDomain,
                            'baslangic_node': currentEdge,
                            'bitis_node': domainicihedefdugum,
                            'yol': yol,
                            'hop': numOfHops,
                            'bw_talebi': required_bw
                        })
                        link['segmentler'].append({
                            'tip': 'domain gecisi',
                            'kaynak_domain': currentDomain,
                            'hedef_domain': nextDomain,
                            'hop': 1
                        })

                    currentDomain = nextDomain
                    currentEdge = nextEdge

                # Son domain iç yolu
                if not path_broken and currentDomain == destinationDomainId:
                    destSearchEdge = (
                        (self.edgeRouterDomainVertexList[:, 0] == destinationDomainId) &
                        (self.edgeRouterDomainVertexList[:, 1] == destinationIntraNodeId)
                    )
                    destIsEdgeRouter = np.where(destSearchEdge)[0].size > 0

                    if destIsEdgeRouter:
                        t, numOfHops = self._find_bc_residual(
                            destinationDomainId, currentEdge, destinationIntraNodeId,
                            required_bw, bc_res
                        )
                        if t is not None:
                            link['segmentler'].append({
                                'tip': 'intra son domain (blokzincir)',
                                'domain': destinationDomainId,
                                'baslangic_node': currentEdge,
                                'bitis_node': destinationIntraNodeId,
                                'yol': t.fullpath,
                                'hop': numOfHops,
                                'bw_talebi': required_bw
                            })
                        else:
                            path, hops = self._find_path_intra_residual(
                                destinationDomainId, currentEdge, destinationIntraNodeId,
                                required_bw, intra_res
                            )
                            link['segmentler'].append({
                                'tip': 'intra son domain (topoloji, bc yok)',
                                'domain': destinationDomainId,
                                'baslangic_node': currentEdge,
                                'bitis_node': destinationIntraNodeId,
                                'yol': path,
                                'hop': hops,
                                'bw_talebi': required_bw
                            })
                    else:
                        path, hops = self._find_path_intra_residual(
                            destinationDomainId, currentEdge, destinationIntraNodeId,
                            required_bw, intra_res
                        )
                        link['segmentler'].append({
                            'tip': 'intra son domain (topoloji)',
                            'domain': destinationDomainId,
                            'baslangic_node': currentEdge,
                            'bitis_node': destinationIntraNodeId,
                            'yol': path,
                            'hop': hops,
                            'bw_talebi': required_bw
                        })

                virtual_links.append(link)

        return virtual_links

    def _parse_gene(self, gene: str) -> Tuple[int, int]:
        """ '5-2' stringini (5, 2) tuple'ına çevirir. (DomainID, NodeID) """
        parts = gene.split("-")
        return int(parts[0]), int(parts[1])

    def _get_best_node(self, domain_id: int, cpu_demand: float, used_nodes: set) -> Optional[int]:
        if domain_id < 0 or domain_id >= len(self.cpu_value_all_intra_networks):
            return None

        domain_nodes = self.cpu_value_all_intra_networks[domain_id]
        best_idx = None
        best_cpu = -1

        for i, cap in enumerate(domain_nodes):
            if i in used_nodes:
                continue
            if cap >= cpu_demand:
                if cap > best_cpu:
                    best_cpu = cap
                    best_idx = i

        return best_idx

    def _get_feasible_nodes(self, domain_id: int, cpu_demand: float, used_nodes: set) -> List[Tuple[int, float]]:
        """Returns [(node_idx, cpu_cap)] for all feasible nodes in domain."""
        if domain_id < 0 or domain_id >= len(self.cpu_value_all_intra_networks):
            return []
        return [
            (i, cap)
            for i, cap in enumerate(self.cpu_value_all_intra_networks[domain_id])
            if i not in used_nodes and cap >= cpu_demand
        ]

    def _select_node(self, domain_id: int, cpu_demand: float, used_nodes: set,
                     rng: random.Random, gene_idx: int = 0) -> Optional[int]:
        """
        Seçim moduna göre domain içinden bir düğüm seçer.
          'cpu'       → en yüksek CPU (deterministik)
          'roulette'  → CPU ile orantılı olasılık (rulet tekerleği)
          'rank'      → sıralama tabanlı olasılık
          'softmax'   → Boltzmann sıcaklık parametreli olasılık
          'qlearning' → epsilon-greedy: keşif veya Q-tablosundaki en iyi düğüm
        gene_idx: kromozom içindeki gen sırası (Q-Learning state için gerekli)
        """
        feasible = self._get_feasible_nodes(domain_id, cpu_demand, used_nodes)
        if not feasible:
            return None

        if self.selection_mode == 'cpu':
            return max(feasible, key=lambda x: x[1])[0]

        elif self.selection_mode == 'roulette':
            scores = [cap for _, cap in feasible]
            total = sum(scores)
            if total == 0:
                return rng.choice(feasible)[0]
            r = rng.random() * total
            cumulative = 0.0
            for node_idx, cap in feasible:
                cumulative += cap
                if cumulative >= r:
                    return node_idx
            return feasible[-1][0]

        elif self.selection_mode == 'rank':
            sorted_f = sorted(feasible, key=lambda x: x[1])   # küçükten büyüğe
            n = len(sorted_f)
            total = n * (n + 1) // 2
            r = rng.random() * total
            cumulative = 0.0
            for rank, (node_idx, _) in enumerate(sorted_f, start=1):
                cumulative += rank
                if cumulative >= r:
                    return node_idx
            return sorted_f[-1][0]

        elif self.selection_mode == 'softmax':
            T = self.softmax_temperature
            raw = [cap / T for _, cap in feasible]
            max_raw = max(raw)
            exp_scores = [math.exp(s - max_raw) for s in raw]   # numerik kararlılık
            total = sum(exp_scores)
            r = rng.random() * total
            cumulative = 0.0
            for (node_idx, _), exp_s in zip(feasible, exp_scores):
                cumulative += exp_s
                if cumulative >= r:
                    return node_idx
            return feasible[-1][0]

        elif self.selection_mode == 'qlearning':
            # epsilon-greedy seçim:
            #   ql_epsilon olasılıkla → rastgele (keşif / exploration)
            #   1-ql_epsilon olasılıkla → Q-tablosundaki en iyi düğüm (sömürü / exploitation)
            #
            # State = (gene_idx, domain_id, domain_doluluk)
            #   domain_doluluk: bu domain'e şu ana kadar kaç node atandı
            #   → "domain dolu iken bu node'u seç" vs "domain boşken seç" farkını öğrenir
            domain_doluluk = len(used_nodes)

            if rng.random() < self.ql_epsilon:
                return rng.choice(feasible)[0]
            else:
                best_node = None
                best_q    = -float('inf')
                for node_idx, _ in feasible:
                    anahtar  = (gene_idx, domain_id, domain_doluluk, node_idx)
                    q_degeri = self.q_table.get(anahtar, 0.0)
                    if q_degeri > best_q:
                        best_q    = q_degeri
                        best_node = node_idx
                return best_node

        else:
            raise ValueError(f"Bilinmeyen selection_mode: {self.selection_mode}")

    def _ql_update(self, chromosome, fitness: float):
        """
        Bir kromozomun fitness değerine göre Q-tablosunu günceller.
        Sadece selection_mode='qlearning' olduğunda çalışır; diğerleri için no-op.

        Ödül hesabı (iyileştirilmiş):
          - Cezalı kromozom (fitness >= 100000) → negatif ödül (-1.0)
            Eski halde bu durum 0.00001 gibi neredeyse sıfır ödül veriyordu;
            iyi ile kötü arasındaki fark çok küçüktü. Şimdi açıkça cezalandırılıyor.
          - Normal → 1 / (1 + fitness): küçük fitness = yüksek ödül

        State (zenginleştirilmiş):
          (gene_idx, domain_id, domain_doluluk, node_idx)
          domain_doluluk: atama sırasında o domain'e kaç node atanmıştı
          → "domain doluyken bu node'u seçmek iyi mi?" sorusunu öğrenir
        """
        if self.selection_mode != 'qlearning' or chromosome is None:
            return

        # Cezalı → negatif ödül; normal → 0-1 arası normalize ödül
        CEZA_ESIGI = 100000
        if fitness >= CEZA_ESIGI:
            odul = -1.0
        else:
            odul = 1.0 / (1.0 + fitness)

        # Genleri atama sırasına göre (sorted_indices) işle;
        # her gen için o anki domain doluluk bilgisini yeniden türet
        domain_doluluk = {}   # domain_id → kaç node atandı

        for i in self.sorted_indices:
            gene      = chromosome[i]
            domain_id, node_idx = self._parse_gene(gene)
            doluluk   = domain_doluluk.get(domain_id, 0)
            anahtar   = (i, domain_id, doluluk, node_idx)
            eski_q    = self.q_table.get(anahtar, 0.0)
            self.q_table[anahtar] = eski_q + self.ql_alpha * (odul - eski_q)
            domain_doluluk[domain_id] = doluluk + 1


    def _rebuild_mapping(self, domains: List[int], rng: random.Random) -> Optional[List[str]]:
        # Crossover sonrası sadece domainler belliyken node atamalarını onarır.
        used_in_domain = {d_id: set() for d_id in range(len(self.cpu_value_all_intra_networks))}
        genes = [None] * self.num_genes

        for i in self.sorted_indices:
            demand = self.cpu_demand_VirtualNetwork[i]
            d_primary = domains[i]
            d1, d2 = self.candidateDomains[i]
            d_alt = d2 if d_primary == d1 else d1

            gene_assigned = False
            for d in dict.fromkeys((d_primary, d_alt)):   # sıralı, tekrarsız
                node_idx = self._select_node(d, demand, used_in_domain.get(d, set()), rng, gene_idx=i)
                if node_idx is not None:
                    used_in_domain[d].add(node_idx)
                    domains[i] = d
                    genes[i] = f"{d}-{node_idx}"
                    gene_assigned = True
                    break

            if not gene_assigned:
                return None

        return genes

    #eski kod rastgele atıyordu
    # def create_chromosome(self, rng: random.Random) -> Optional[List[str]]:
    #     # Her sanal düğümü, aday domainler arasında en yüksek CPU kapasiteli node'a atar.
    #     # Aynı domain içinde bir node daha önce seçildiyse, bir sonraki en yüksek CPU'lu node seçilir.
    #     used_in_domain = {d_id: set() for d_id in range(len(self.cpu_value_all_intra_networks))}
    #     chrom = [None] * self.num_genes

    #     for i in self.sorted_indices:
    #         demand = self.cpu_demand_VirtualNetwork[i]
    #         d1, d2 = self.candidateDomains[i]
    #         feasible = []

    #         for d in (d1, d2):
    #             node_idx = self._get_best_node(d, demand, used_in_domain.get(d, set()))
    #             if node_idx is not None:
    #                 feasible.append((d, node_idx))

    #         if not feasible:
    #             return None

    #         # Aday (domain, node) çiftleri arasından CPU'su en yüksek olanı seç
    #         d, node_idx = max(feasible, key=lambda x: self.cpu_value_all_intra_networks[x[0]][x[1]])
    #         used_in_domain[d].add(node_idx)
    #         chrom[i] = f"{d}-{node_idx}"

    #     return chrom

    def create_chromosome(self, rng: random.Random) -> Optional[List[str]]:
        """
        Seçim moduna göre domain içi düğüm seçimini yaparak geçerli bir kromozom oluşturur.
        Domain seçimi (d1 vs d2) tüm modlarda rastgeledir; düğüm seçimi selection_mode'a göre değişir.
        """
        max_tries = 50
        for _ in range(max_tries):
            used_in_domain = {d_id: set() for d_id in range(len(self.cpu_value_all_intra_networks))}
            chrom = [None] * self.num_genes
            ok = True

            for i in self.sorted_indices:
                demand = self.cpu_demand_VirtualNetwork[i]
                d1, d2 = self.candidateDomains[i]
                feasible = []

                for d in (d1, d2):
                    node_idx = self._select_node(d, demand, used_in_domain.get(d, set()), rng, gene_idx=i)
                    if node_idx is not None:
                        feasible.append((d, node_idx))

                if not feasible:
                    ok = False
                    break

                d, node_idx = rng.choice(feasible)
                used_in_domain[d].add(node_idx)
                chrom[i] = f"{d}-{node_idx}"

            if ok:
                return chrom
        return None




    def crossover(self, parent1: List[str], parent2: List[str], rng: random.Random) -> Optional[List[str]]:
        d1_list = [self._parse_gene(g)[0] for g in parent1]
        d2_list = [self._parse_gene(g)[0] for g in parent2]

        a = rng.randrange(self.num_genes)
        b = rng.randrange(self.num_genes)
        l, r = (a, b) if a <= b else (b, a)

        child_domains = d1_list[:]
        for i in range(l, r + 1):
            child_domains[i] = d2_list[i]

        # Domainlerin isteklere uygunluğunu kontrol et
        for i in range(self.num_genes):
            if child_domains[i] not in self.candidateDomains[i]:
                child_domains[i] = rng.choice(self.candidateDomains[i])

        return self._rebuild_mapping(child_domains, rng)

    def mutate(self, chromosome: List[str], mutation_rate: float, rng: random.Random) -> List[str]:
        if rng.random() > mutation_rate:
            return chromosome[:]

        new_chrom = chromosome[:]
        idx = rng.randrange(self.num_genes)

        current_domain, current_node = self._parse_gene(new_chrom[idx])
        demand = self.cpu_demand_VirtualNetwork[idx]

        d1, d2 = self.candidateDomains[idx]
        alt_domain = d2 if current_domain == d1 else d1

        used_nodes_in_domains = {d: set() for d in range(len(self.cpu_value_all_intra_networks))}
        for i, g in enumerate(new_chrom):
            if i == idx:
                continue
            d, n = self._parse_gene(g)
            used_nodes_in_domains[d].add(n)

        # Alternatif domainde stokastik düğüm seçimi
        new_node = self._select_node(alt_domain, demand, used_nodes_in_domains.get(alt_domain, set()), rng, gene_idx=idx)
        if new_node is not None:
            new_chrom[idx] = f"{alt_domain}-{new_node}"
        else:
            # Alternatif domain doluysa mevcut domainde başka düğüm dene
            used_nodes_in_domains[current_domain].add(current_node)
            other_node = self._select_node(current_domain, demand, used_nodes_in_domains.get(current_domain, set()), rng, gene_idx=idx)
            if other_node is not None:
                new_chrom[idx] = f"{current_domain}-{other_node}"

        return new_chrom



    def run(self, population_size=20, generations=100, mutation_rate=0.1, seed=None):
        rng = random.Random(seed)

        # Başlangıç Popülasyonu Oluştur
        population = []
        for _ in range(population_size):
            ind = self.create_chromosome(rng)
            if ind:
                population.append(ind)


        if not population:
            print("Hata: Başlangıç popülasyonu oluşturulamadı (Kısıtlar çok sıkı).")
            return None

        best_solution = None
        # Minimizasyon olduğu için başlangıç değeri çok büyük olmalı
        best_fitness = float('inf')

        for gen in range(1, generations + 1):

            scored_pop = []
            for chrom in population:
                fit = self.calculate_fitness_v2(chrom)
                # Q-Learning için: bu kromozomun fitness'ına göre Q-tablosunu güncelle
                self._ql_update(chrom, fit)
                scored_pop.append((chrom, fit))
                print(f"kromozom:-> {chrom} : fitness:-> {fit}")
                if fit < best_fitness:
                    best_fitness = fit
                    best_solution = chrom
                    # print(f"Yeni En İyi: {fit}")

            scored_pop.sort(key=lambda x: x[1], reverse=False)

            new_population = []

            new_population.append(scored_pop[0][0])
            if len(scored_pop) > 1:
                new_population.append(scored_pop[1][0])

            while len(new_population) < population_size:

                candidates = rng.sample(scored_pop, min(3, len(scored_pop)))

                parent1 = min(candidates, key=lambda x: x[1])[0]

                candidates = rng.sample(scored_pop, min(3, len(scored_pop)))
                parent2 = min(candidates, key=lambda x: x[1])[0]

                child = self.crossover(parent1, parent2, rng)

                if child is None:
                    child = parent1[:]

                child = self.mutate(child, mutation_rate, rng)

                new_population.append(child)

            population = new_population

            # Her nesil sonunda dışarıdan izleme yapılabilmesi için hook
            self._on_generation_end(gen, best_fitness)

            # Q-Learning: epsilon'u nesil sonunda azalt (keşif → sömürü geçişi)
            if self.selection_mode == 'qlearning':
                self.ql_epsilon = max(self.ql_epsilon_min,
                                      self.ql_epsilon * self.ql_epsilon_decay)

            if gen % 10 == 0 or gen == 1:
                eps_str = f"  epsilon={self.ql_epsilon:.3f}" if self.selection_mode == 'qlearning' else ""
                print(f"Jenerasyon {gen}: En Iyi Fitness (Maliyet) = {best_fitness}{eps_str}")

        return best_solution, best_fitness

    def _on_generation_end(self, gen: int, best_fitness: float):
        """Her nesil bitişinde çağrılır. Alt sınıflar override edebilir."""
        pass


#test
if __name__ == "__main__":
    
    # Veriler
    cpu_value_all_intra_networks = [[48, 12, 46, 31, 10], [38, 13, 32, 37, 21], [37, 40, 33, 43, 44], 
     [46, 13, 28, 32, 47], [36, 49, 10, 35, 14], [45, 17, 29, 15, 21], 
     [48, 43, 25, 40, 40], [48, 29, 47, 32, 49], [21, 48, 48, 18, 21],
     [41, 21, 23, 35, 33], [12, 48, 12, 16, 20], [35, 45, 37, 34, 12],
     [43, 13, 15, 13, 14], [37, 23, 41, 25, 35]]
    
    istekler =  [[5, 3], [4, 10], [6, 1], [5, 2], [4, 3]]
    cpu_demand_VirtualNetwork = [15, 11, 16, 11, 18]

    #solver = GeneticDomainSolver(cpu_value_all_intra_networks, istekler, cpu_demand_VirtualNetwork)
    #en_iyi_cozum, puan = solver.run(population_size=4, generations=2, mutation_rate=0.1, seed=None)

    print("\n--- SONUÇ ---")
    #print(f"En İyi Fitness Skoru: {puan}")
    #print(f"En İyi Kromozom: {en_iyi_cozum}")