import networkx as nx
from algorithm.genetic import GeneticDomainSolver


class CentralityGreedySolver(GeneticDomainSolver):
    """
    Merkeziyetçilik (centrality) tabanlı greedy çözücü.

    Sanal düğümleri CPU talebi yüksekten düşüğe sıralayarak atar.
    Her atamada, aday domainlerdeki tüm uygun node'ların merkeziyetçilik
    puanı hesaplanır ve en yüksek puanlı node seçilir.

    Desteklenen metodlar:
        'closeness'   — Closeness Centrality  (nx.closeness_centrality)
        'betweenness' — Betweenness Centrality (nx.betweenness_centrality)
        'degree'      — Degree Centrality      (nx.degree_centrality)
        'pagerank'    — PageRank               (nx.pagerank)
        'eigenvector' — Eigenvector Centrality (nx.eigenvector_centrality_numpy)

    Devraldığı sınıf: GeneticDomainSolver
        - Aynı __init__ arayüzü (allTransaction, edgeRouter, interNetwork,
          intraNetworkTopologies, virtualRequests)
        - Aynı graf dönüşüm yardımcıları (convertGxInterNetwork, vb.)
        - Aynı fitness hesaplama (calculate_fitness_v2)
        - Yeni: solve() — tek seferlik greedy çözüm üretir
    """

    METHODS = {
        'closeness':   nx.closeness_centrality,
        'betweenness': nx.betweenness_centrality,
        'degree':      nx.degree_centrality,
        'pagerank':    nx.pagerank,
        'eigenvector': None,   # özel çağrı: numpy versiyonu
    }

    def __init__(
        self,
        allTransaction,
        edgeRouter,
        interNetwork,
        intraNetworkTopologies,
        virtualRequests,
        method: str = 'closeness',
    ):
        super().__init__(
            allTransaction, edgeRouter, interNetwork,
            intraNetworkTopologies, virtualRequests
        )
        if method not in self.METHODS:
            raise ValueError(
                f"Bilinmeyen metod: '{method}'. "
                f"Geçerli seçenekler: {list(self.METHODS.keys())}"
            )
        self.method = method
        self._centrality_cache: dict = {}   # domain_id → {node: score}

    # ------------------------------------------------------------------
    # Merkeziyetçilik hesaplama
    # ------------------------------------------------------------------

    def _compute_centrality(self, graph: nx.Graph, domain_id: int) -> dict:
        """
        Verilen domain'in intra-domain grafı üzerinde merkeziyetçilik hesaplar.
        Sonuçlar önbelleğe alınır; aynı domain için tekrar hesaplanmaz.

        Döner: {node_id: centrality_score}  (0.0–1.0 arası normalleştirilmiş)
        """
        if domain_id in self._centrality_cache:
            return self._centrality_cache[domain_id]

        if graph.number_of_nodes() == 0:
            self._centrality_cache[domain_id] = {}
            return {}

        try:
            if self.method == 'eigenvector':
                result = nx.eigenvector_centrality_numpy(graph)
            else:
                fn = self.METHODS[self.method]
                result = fn(graph)
        except Exception:
            # Bağlantısız graf veya yakınsama hatası → tüm node'lara 0
            result = {n: 0.0 for n in graph.nodes()}

        self._centrality_cache[domain_id] = result
        return result

    # ------------------------------------------------------------------
    # Greedy çözüm üretme
    # ------------------------------------------------------------------

    def solve(self):
        """
        Tek seferlik greedy atama + yol bulma yapar.  Genetik/ACO gibi
        popülasyon ya da nesil döngüsü yoktur; tek bir geçişte biter.

        Adım 1 — Greedy atama (tek döngü):
            Sanal düğümler CPU talebi yüksekten düşüğe sıralanır.
            Her sanal düğüm için aday domainlerdeki node'lar merkeziyetçilik
            puanına göre değerlendirilir; en yüksek puanlı, CPU kısıtını
            karşılayan ilk node seçilir.

        Adım 2 — Yol bulma (genetik ile aynı):
            trace_solution() çağrısıyla atanan (domain, node) çiftleri
            arasındaki fiziksel yollar (intra/inter/blokzincir) bulunur.
            calculate_fitness_v2() ile toplam hop sayısı hesaplanır.

        Döner: (chromosome, fitness, path_details)
            chromosome   : ["domainId-nodeId", ...]  veya None
            fitness      : toplam hop sayısı          veya float('inf')
            path_details : trace_solution() çıktısı  veya []
        """
        self._centrality_cache.clear()

        used_in_domain = {
            d: set() for d in range(len(self.cpu_value_all_intra_networks))
        }
        chrom = [None] * self.num_genes

        # ---- Adım 1: tek döngüde greedy atama ----
        for i in self.sorted_indices:
            demand = self.cpu_demand_VirtualNetwork[i]
            d1, d2 = self.candidateDomains[i]

            best_option = None
            best_score = -1.0

            for d in (d1, d2):
                G = self.intraNetworkGraphwithBWMatrix[d]
                centrality = self._compute_centrality(G, d)

                for node, cap in enumerate(self.cpu_value_all_intra_networks[d]):
                    if node in used_in_domain[d]:
                        continue
                    if cap < demand:
                        continue
                    score = centrality.get(node, 0.0)
                    if score > best_score:
                        best_score = score
                        best_option = (d, node)

            if best_option is None:
                return None, float('inf'), []

            d, node = best_option
            used_in_domain[d].add(node)
            chrom[i] = f"{d}-{node}"

        # ---- Adım 2: genetik ile aynı yol bulma ----
        fitness = self.calculate_fitness_v2(chrom)
        path_details = self.trace_solution(chrom)
        return chrom, fitness, path_details


class GreedyCPUSolver(GeneticDomainSolver):
    """
    CPU kapasitesi tabanlı greedy çözücü.

    Her sanal düğüm için aday domainlerdeki (d1, d2) tüm node'lar incelenir;
    CPU talebi karşılayan ve henüz kullanılmamış node'lar arasından
    CPU kapasitesi EN YÜKSEK olan seçilir.

    Kısıt: farklı sanal düğümler aynı fiziksel (domain, node) çiftini
    kullanamaz — used_in_domain ile her atamada takip edilir.

    solve() → (chromosome, fitness, path_details)  — tek geçiş, yol bulma dahil
    """

    def solve(self):
        used_in_domain = {
            d: set() for d in range(len(self.cpu_value_all_intra_networks))
        }
        chrom = [None] * self.num_genes

        # Sanal düğümler CPU talebi yüksekten düşüğe sıralı işlenir
        for i in self.sorted_indices:
            demand = self.cpu_demand_VirtualNetwork[i]
            d1, d2 = self.candidateDomains[i]

            best_option = None
            best_cpu = -1

            for d in (d1, d2):
                for node, cap in enumerate(self.cpu_value_all_intra_networks[d]):
                    if node in used_in_domain[d]:
                        continue        # bu node başka sanal düğüme atandı
                    if cap < demand:
                        continue        # CPU talebi karşılanmıyor
                    if cap > best_cpu:
                        best_cpu = cap
                        best_option = (d, node)

            if best_option is None:
                return None, float('inf'), []

            d, node = best_option
            used_in_domain[d].add(node)
            chrom[i] = f"{d}-{node}"

        fitness = self.calculate_fitness_v2(chrom)
        path_details = self.trace_solution(chrom)
        return chrom, fitness, path_details
