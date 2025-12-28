import random
from typing import List, Optional, Tuple, Dict

class GeneticDomainSolver:
    def __init__(self, cpu_value_all_intra_networks: List[List[int]], candidateDomains: List[List[int]], cpu_demand_VirtualNetwork: List[float]):
        
        self.cpu_value_all_intra_networks = cpu_value_all_intra_networks      # [DomainID][NodeIndex] = CPU Kapasitesi
        self.candidateDomains = candidateDomains      # [[Domain1, Domain2], ...]
        self.cpu_demand_VirtualNetwork = cpu_demand_VirtualNetwork        # [Talep1, Talep2, ...]
        self.num_genes = len(candidateDomains)
        
        self.sorted_indices = sorted(range(self.num_genes), key=lambda i: self.cpu_demand_VirtualNetwork[i], reverse=True)


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
            idx1 = i + 1  # 1-based index
            if idx1 in used_nodes:
                continue
            
            # Kapasite kontrolü
            if cap >= cpu_demand:
                # Buradaki strateji: En yüksek kapasiteli node'u seçmek (Best Fit)
                # İsterseniz burayı Random da yapabilirsiniz.
                if cap > best_cpu:
                    best_cpu = cap
                    best_idx = idx1
                
        return best_idx

    def _rebuild_mapping(self, domains: List[int], rng: random.Random) -> Optional[List[str]]:
        """
        Crossover sonrası sadece domainler belliyken node atamalarını onarır.
        """
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
        """ Rastgele geçerli bir kromozom (birey) oluşturur. """
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

    # --- GA BİLEŞENLERİ (YENİ EKLENENLER) ---

    def calculate_fitness(self, chromosome: List[str]) -> float:
        """
        FITNESS HESAPLAMA:
        Burada amaç, seçilen node'ların ne kadar verimli kullanıldığıdır.
        Örnek Fitness: (Toplam Node Kapasitesi - Toplam Kullanılan CPU) 
        Yani: Node'larda ne kadar çok boş yer kalırsa o kadar iyi (Load Balancing).
        """
        if chromosome is None: return 0.0

        total_residual_cpu = 0
        
        # Hangi domainde hangi node kullanılmış ve ne kadar talep var?
        # chromosome: ["1-5", "2-3", ...]
        for i, gene in enumerate(chromosome):
            d_id, n_id = self._parse_gene(gene)
            # n_id 1-based olduğu için array indexi n_id-1
            node_capacity = self.cpu_value_all_intra_networks[d_id][n_id - 1]
            demand = self.cpu_demand_VirtualNetwork[i]
            
            # Kalan kapasiteyi skora ekle
            residual = node_capacity - demand
            total_residual_cpu += residual

        return float(total_residual_cpu)

    def crossover(self, parent1: List[str], parent2: List[str], rng: random.Random) -> Optional[List[str]]:
        """ İki ebeveynden çocuk üretir (Segment Crossover). """
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
        """
        MUTASYON:
        Belirli bir olasılıkla genin Domain veya Node seçimini değiştirmeye çalışır.
        Ancak değişiklik sonrası çözümün HALA GEÇERLİ (Feasible) olması gerekir.
        """
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

    # --- ANA ÇALIŞTIRMA FONKSİYONU ---

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
        best_fitness = -1.0

        for gen in range(1, generations + 1):
            
            #Fitness
            # (Kromozom, FitnessPuanı) ikilisi
            scored_pop = []
            for chrom in population:
                fit = self.calculate_fitness(chrom)
                scored_pop.append((chrom, fit))
                
                # Global en iyiyi takip et
                if fit > best_fitness:
                    best_fitness = fit
                    best_solution = chrom
                print(f"({chrom}->{fit})")
            #Sıralama iyiden en kötüye
            scored_pop.sort(key=lambda x: x[1], reverse=True)
            #print(scored_pop)
            new_population = []
            
            # Elitizm: En iyi 2 taneyi doğrudan aktar
            new_population.append(scored_pop[0][0])
            if len(scored_pop) > 1:
                new_population.append(scored_pop[1][0])

            #Seçilim, Crossover ve Mutasyon ile popülasyonu tamamla
            while len(new_population) < population_size:
                # Turnuva Seçimi (Rastgele 3 tane al, en iyisini seç)
                candidates = rng.sample(scored_pop, min(3, len(scored_pop)))
                parent1 = max(candidates, key=lambda x: x[1])[0]
                
                candidates = rng.sample(scored_pop, min(3, len(scored_pop)))
                parent2 = max(candidates, key=lambda x: x[1])[0]

                # Crossover
                child = self.crossover(parent1, parent2, rng)
                
                if child is None:
                    # Crossover başarısızsa parentlardan biri geçer
                    child = parent1[:]
                
                # Mutasyon
                child = self.mutate(child, mutation_rate, rng)
                
                new_population.append(child)

            # Popülasyonu güncelle
            population = new_population
            
            # İsteğe bağlı: Her 10 jenerasyonda bilgi ver
            if gen % 10 == 0 or gen == 1:
                print(f"Jenerasyon {gen}: En İyi Fitness = {best_fitness}")
            
            

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

    solver = GeneticDomainSolver(cpu_value_all_intra_networks, istekler, cpu_demand_VirtualNetwork)
    en_iyi_cozum, puan = solver.run(population_size=4, generations=2, mutation_rate=0.1, seed=None)

    print("\n--- SONUÇ ---")
    print(f"En İyi Fitness Skoru: {puan}")
    print(f"En İyi Kromozom: {en_iyi_cozum}")