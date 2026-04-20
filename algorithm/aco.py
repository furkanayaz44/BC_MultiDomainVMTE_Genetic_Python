import random
from typing import List, Optional, Tuple
import numpy as np
import networkx as nx

from algorithm.genetic import GeneticDomainSolver


class ACODomainSolver(GeneticDomainSolver):
    """
    Ant Colony Optimization tabanlı multi-domain sanal ağ gömme çözücüsü.

    Her sanal düğümün hangi fiziksel (domain, node) çiftine atanacağını
    feromon izleri ve CPU sezgisel bilgisi kullanarak optimize eder.

    Feromon matrisi: self.pheromone[i][(d, n)]
        i  : sanal düğüm indeksi
        d  : fiziksel domain ID
        n  : o domain içindeki node ID
    Değer: τ (feromon yoğunluğu) — yükseldikçe o atamanın tercih edilme olasılığı artar.

    Olasılık formülü:
        P(d,n | i) = τ[i][(d,n)]^α × η[i][(d,n)]^β  /  Σ_j (τ[i][j]^α × η[i][j]^β)
        η[i][(d,n)] = cpu_value[d][n] / cpu_demand[i]   (sezgisel: yüksek CPU tercih edilir)

    Feromon güncelleme (her iterasyon sonunda):
        Buharlaşma : τ ← (1 - ρ) × τ
        Yatırım    : τ[i][(d,n)] += Q / fitness(çözüm)   (daha iyi çözüme daha fazla feromon)
    """

    def __init__(self, allTransaction, edgeRouter, interNetwork, intraNetworkTopologies, virtualRequests):
        super().__init__(allTransaction, edgeRouter, interNetwork, intraNetworkTopologies, virtualRequests)

        # ACO parametreleri (run() çağrısında güncellenir)
        self.alpha = 1.0
        self.beta = 2.0
        self.rho = 0.1
        self.Q = 100.0
        self.tau_init = 1.0
        self.tau_min = 0.01        # feromon alt sınırı (buharlaşma sıfıra düşmesin)
        self.pheromone: List[dict] = [{} for _ in range(self.num_genes)]

    # ------------------------------------------------------------------ #
    #  ACO yardımcıları                                                    #
    # ------------------------------------------------------------------ #

    def _get_feasible_nodes(self, domain_id: int, cpu_demand: float, used_nodes: set) -> List[int]:
        """
        Verilen domain içinde CPU talebi karşılayan ve henüz kullanılmamış
        tüm node indekslerini döndürür.
        """
        if domain_id < 0 or domain_id >= len(self.cpu_value_all_intra_networks):
            return []
        return [
            idx for idx, cap in enumerate(self.cpu_value_all_intra_networks[domain_id])
            if idx not in used_nodes and cap >= cpu_demand
        ]

    def _tau(self, gene_idx: int, d: int, n: int) -> float:
        """Feromon değerini döndürür; kayıtlı değer yoksa tau_init kullanılır."""
        return self.pheromone[gene_idx].get((d, n), self.tau_init)

    def _eta(self, gene_idx: int, d: int, n: int) -> float:
        """
        Sezgisel bilgi: node'un CPU kapasitesinin talebe oranı.
        Yüksek CPU → daha çekici.
        """
        demand = max(self.cpu_demand_VirtualNetwork[gene_idx], 1)
        return self.cpu_value_all_intra_networks[d][n] / demand

    # ------------------------------------------------------------------ #
    #  Çözüm inşası  (bir karıncanın turu)                                 #
    # ------------------------------------------------------------------ #

    def construct_solution(self, rng: random.Random) -> Optional[List[str]]:
        """
        Tek bir karınca, sanal düğümleri sırayla fiziksel (domain, node)
        çiftlerine atar. Her adımda atama feromon × sezgisel olasılıkla seçilir.
        """
        used_in_domain = {d: set() for d in range(len(self.cpu_value_all_intra_networks))}
        chrom = [None] * self.num_genes

        for i in self.sorted_indices:
            demand = self.cpu_demand_VirtualNetwork[i]
            d1, d2 = self.candidateDomains[i]

            # Tüm uygun (domain, node) seçeneklerini topla
            all_options = []
            for d in (d1, d2):
                for n in self._get_feasible_nodes(d, demand, used_in_domain.get(d, set())):
                    all_options.append((d, n))

            if not all_options:
                return None  # Bu karınca geçerli çözüm bulamadı

            # Olasılık hesapla: τ^α × η^β
            weights = [
                (self._tau(i, d, n) ** self.alpha) * (self._eta(i, d, n) ** self.beta)
                for d, n in all_options
            ]
            total = sum(weights)
            if total == 0:
                norm = [1.0 / len(all_options)] * len(all_options)
            else:
                norm = [w / total for w in weights]

            # Rulet tekerleği seçimi
            r = rng.random()
            cumsum = 0.0
            chosen_d, chosen_n = all_options[-1]   # varsayılan: son eleman
            for (opt_d, opt_n), p in zip(all_options, norm):
                cumsum += p
                if r <= cumsum:
                    chosen_d, chosen_n = opt_d, opt_n
                    break

            used_in_domain[chosen_d].add(chosen_n)
            chrom[i] = f"{chosen_d}-{chosen_n}"

        return chrom

    # ------------------------------------------------------------------ #
    #  Feromon güncelleme                                                  #
    # ------------------------------------------------------------------ #

    def _evaporate(self):
        """Tüm feromon değerlerini (1-ρ) ile çarp; alt sınırın altına inme."""
        for i in range(self.num_genes):
            for key in self.pheromone[i]:
                self.pheromone[i][key] = max(
                    self.tau_min,
                    self.pheromone[i][key] * (1 - self.rho)
                )

    def _deposit(self, solutions_with_fitness: list):
        """
        Her karınca kendi çözümüne göre feromon yatırır.
        Δτ = Q / fitness   (düşük hop → yüksek feromon yatırımı)
        """
        for chrom, fitness in solutions_with_fitness:
            if chrom is None or fitness <= 0 or fitness == float('inf'):
                continue
            delta = self.Q / fitness
            for i, gene in enumerate(chrom):
                d, n = self._parse_gene(gene)
                if (d, n) not in self.pheromone[i]:
                    self.pheromone[i][(d, n)] = self.tau_init
                self.pheromone[i][(d, n)] += delta

    def _deposit_best_only(self, best_chrom: List[str], best_fitness: float):
        """
        Yalnızca o iterasyonun en iyi karıncası feromon yatırır (elitist strateji).
        Yakınsama hızlanır; çeşitlilik azalır.
        """
        if best_chrom is None or best_fitness <= 0 or best_fitness == float('inf'):
            return
        delta = self.Q / best_fitness
        for i, gene in enumerate(best_chrom):
            d, n = self._parse_gene(gene)
            if (d, n) not in self.pheromone[i]:
                self.pheromone[i][(d, n)] = self.tau_init
            self.pheromone[i][(d, n)] += delta

    # ------------------------------------------------------------------ #
    #  Ana döngü                                                           #
    # ------------------------------------------------------------------ #

    def run(
        self,
        n_ants: int = 20,
        iterations: int = 100,
        alpha: float = 1.0,
        beta: float = 2.0,
        rho: float = 0.1,
        Q: float = 100.0,
        tau_init: float = 1.0,
        elitist: bool = False,
        seed=None
    ):
        """
        Parametreler
        ------------
        n_ants     : Her iterasyondaki karınca sayısı (genetikteki population_size)
        iterations : İterasyon sayısı (genetikteki generations)
        alpha      : Feromon ağırlığı (büyüdükçe feromon daha belirleyici)
        beta       : Sezgisel ağırlık (büyüdükçe CPU kapasitesi daha belirleyici)
        rho        : Buharlaşma oranı (0–1 arası; yüksek → hızlı unutma)
        Q          : Feromon yatırım sabiti
        tau_init   : Başlangıç feromon değeri
        elitist    : True → sadece iterasyon en iyisi feromon yatırır
        seed       : Tekrarlanabilirlik için rastgelelik tohumu
        """
        rng = random.Random(seed)

        # Parametreleri kaydet
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.Q = Q
        self.tau_init = tau_init
        self.tau_min = tau_init * 0.01

        # Feromon matrisini sıfırla
        self.pheromone = [{} for _ in range(self.num_genes)]

        best_solution = None
        best_fitness = float('inf')

        for it in range(1, iterations + 1):

            iter_solutions = []
            iter_best_chrom = None
            iter_best_fitness = float('inf')

            for ant in range(n_ants):
                chrom = self.construct_solution(rng)
                if chrom is None:
                    continue
                fitness = self.calculate_fitness_v2(chrom)
                iter_solutions.append((chrom, fitness))
                print(f"  [it={it} ant={ant+1}] {chrom} -> hop={fitness}")

                if fitness < iter_best_fitness:
                    iter_best_fitness = fitness
                    iter_best_chrom = chrom

                if fitness < best_fitness:
                    best_fitness = fitness
                    best_solution = chrom

            # Feromon güncelle
            self._evaporate()
            if elitist:
                self._deposit_best_only(iter_best_chrom, iter_best_fitness)
            else:
                self._deposit(iter_solutions)

            if it % 10 == 0 or it == 1:
                print(f"İterasyon {it}: En İyi Fitness (Hop) = {best_fitness}")

        return best_solution, best_fitness
