import random
from typing import List, Optional, Tuple, Dict
import numpy as np
import networkx as nx
class GeneticDomainSolver:
    def __init__(self, allTransaction,edgeRouter,interNetwork, intraNetworkTopologies, virtualRequests):
        
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
        
        self.sorted_indices = sorted(range(self.num_genes), key=lambda i: self.cpu_demand_VirtualNetwork[i], reverse=True)

        self.interNetworkNumpyAjacencyGraph = self.convertGxInterNetwork()
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
         np_matris = np.array(self.interNetwork.adjacency_matrix)
         G = nx.from_numpy_array(np_matris)
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

    def calculate_fitness(self, chromosome: List[str]) -> float:
        
        if chromosome is None: return 0.0

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
            idx1 = i 
            if idx1 in used_nodes:
                continue
            
            # Kapasite kontrolü
            if cap >= cpu_demand:
                # Buradaki strateji: En yüksek kapasiteli node'u seçmek (Best Fit)
                if cap > best_cpu:
                    best_cpu = cap
                    best_idx = idx1
                
        return best_idx

    def _rebuild_mapping(self, domains: List[int], rng: random.Random) -> Optional[List[str]]:
        
        # Crossover sonrası sadece domainler belliyken node atamalarını onarır.
        
        used_in_domain = {d_id: set() for d_id in range(len(self.cpu_value_all_intra_networks))}
        genes = [None] * self.num_genes

        for i in self.sorted_indices:
            demand = self.cpu_demand_VirtualNetwork[i]
            d_primary = domains[i]
            d1, d2 = self.candidateDomains[i]
            d_alt = d2 if d_primary == d1 else d1 
            
            tried = []
            gene_assigned = False

            for d in (d_primary, d_alt):
                if d in tried: continue
                tried.append(d)
                
                node_idx = self._get_best_node(d, demand, used_in_domain.get(d, set()))
                
                if node_idx is not None:
                    used_in_domain[d].add(node_idx)
                    domains[i] = d 
                    genes[i] = f"{d}-{node_idx}"
                    gene_assigned = True
                    break 
            
            if not gene_assigned:
                return None # Çözüm geçersiz

        return genes

    def create_chromosome(self, rng: random.Random) -> Optional[List[str]]:
        # Rastgele geçerli bir kromozom (birey) oluşturur.
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
                    node_idx = self._get_best_node(d, demand, used_in_domain.get(d, set()))
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
            return chromosome[:] # Mutasyon yok, kopyasını döndür

        new_chrom = chromosome[:]
        
        # Rastgele bir geni seç
        idx = rng.randrange(self.num_genes)
        
        # Mevcut gen bilgilerini al
        current_domain, current_node = self._parse_gene(new_chrom[idx])
        demand = self.cpu_demand_VirtualNetwork[idx]
        
        # Alternatif domaini bul
        d1, d2 = self.candidateDomains[idx]
        alt_domain = d2 if current_domain == d1 else d1
        
        # ŞU ANKİ kullanılan node'ların haritasını çıkar (conflict olmaması için)
        used_nodes_in_domains = {d: set() for d in range(len(self.cpu_value_all_intra_networks))}
        for i, g in enumerate(new_chrom):
            if i == idx: continue # Değiştireceğimiz geni hariç tut
            d, n = self._parse_gene(g)
            used_nodes_in_domains[d].add(n)

        # Önce alternatif domainde yer var mı diye bak
        new_node = self._get_best_node(alt_domain, demand, used_nodes_in_domains.get(alt_domain, set()))
        
        if new_node is not None:
            # Mutasyon Başarılı: Domain değişti
            new_chrom[idx] = f"{alt_domain}-{new_node}"
        else:
            # Alternatifte yer yoksa, mevcut domainde BAŞKA bir node dene
            # Mevcut node'u da 'used' listesine ekleyelim ki aynısını seçmesin
            used_nodes_in_domains[current_domain].add(current_node)
            other_node = self._get_best_node(current_domain, demand, used_nodes_in_domains.get(current_domain, set()))
            
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
                fit = self.calculate_fitness(chrom)
                scored_pop.append((chrom, fit))
                
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
            
            if gen % 10 == 0 or gen == 1:
                print(f"Jenerasyon {gen}: En İyi Fitness (Maliyet) = {best_fitness}")
            
        return best_solution, best_fitness


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