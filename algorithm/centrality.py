import networkx as nx
from algorithm.genetic import GeneticDomainSolver


class GreedyCPUSolver(GeneticDomainSolver):
    """
    CPU kapasitesi tabanlı greedy çözücü.

    Her sanal düğüm için aday domainlerdeki (d1, d2) tüm node'lar incelenir;
    CPU talebi karşılayan ve henüz kullanılmamış node'lar arasından
    CPU kapasitesi EN YÜKSEK olan seçilir.

    solve() → (chromosome, fitness, path_details)  — tek geçiş, yol bulma dahil
    """

    def solve(self):
        used_in_domain = {
            d: set() for d in range(len(self.cpu_value_all_intra_networks))
        }
        chrom = [None] * self.num_genes

        for i in self.sorted_indices:
            demand = self.cpu_demand_VirtualNetwork[i]
            d1, d2 = self.candidateDomains[i]

            best_option = None
            best_cpu = -1

            for d in (d1, d2):
                for node, cap in enumerate(self.cpu_value_all_intra_networks[d]):
                    if node in used_in_domain[d]:
                        continue
                    if cap < demand:
                        continue
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


class GreedyCPUBWSolver(GreedyCPUSolver):
    """
    CPU + BW farkındalıklı greedy çözücü.

    Node seçimi sırasında hem CPU hem de zaten atanmış düğümlere olan
    sanal linklerin BW kısıtını kontrol eder. BW uygun adaylar arasından
    CPU'su en yüksek node seçilir.

    Atama sonrası o sanal linkin BW'si residual haritadan düşülür.
    """

    def _link_bw_feasible(self, d_src, n_src, d_dst, n_dst, bw, intra_res, er_res):
        """Okuma-only: mevcut residual ile iki node arasında BW kısıtlı yol var mı?"""
        if d_src == d_dst:
            res = intra_res.get(d_src, {})
            base_G = self.intraNetworkGraphwithBWMatrix[d_src]
            fg = nx.Graph()
            fg.add_nodes_from(base_G.nodes())
            for (u, v), avail in res.items():
                if avail >= bw:
                    fg.add_edge(u, v)
            try:
                return nx.has_path(fg, n_src, n_dst)
            except nx.NodeNotFound:
                return False
        else:
            return self._find_inter_path_residual(d_src, d_dst, bw, er_res) is not None

    def _deduct_link_bw(self, d_src, n_src, d_dst, n_dst, bw, intra_res, er_res, bc_res):
        """Fiziksel yolu bulur ve BW'yi residual haritalardan düşer."""
        if d_src == d_dst:
            self._find_path_intra_residual(d_src, n_src, n_dst, bw, intra_res)
            return

        inter_path = self._find_inter_path_residual(d_src, d_dst, bw, er_res)
        if inter_path is None:
            return

        current_n = n_src
        for step in range(len(inter_path) - 1):
            chosen_er = None
            domainicihedefdugum = None
            nextDomain = None
            nextEdge = None

            for er in self.edgeRouter:
                if er_res.get(id(er), 0) < bw:
                    continue
                if (er.edgeDomainIngress == inter_path[step] and
                        er.edgeDomainEgress == inter_path[step + 1]):
                    domainicihedefdugum = er.edgeNodeIngress
                    nextDomain = er.edgeDomainEgress
                    nextEdge = er.edgeNodeEgress
                    chosen_er = er
                    break
                if (er.edgeDomainEgress == inter_path[step] and
                        er.edgeDomainIngress == inter_path[step + 1]):
                    domainicihedefdugum = er.edgeNodeEgress
                    nextDomain = er.edgeDomainIngress
                    nextEdge = er.edgeNodeIngress
                    chosen_er = er
                    break

            if chosen_er is None:
                return

            er_res[id(chosen_er)] -= bw
            self._find_path_intra_residual(
                inter_path[step], current_n, domainicihedefdugum, bw, intra_res
            )
            current_n = nextEdge

        self._find_path_intra_residual(d_dst, current_n, n_dst, bw, intra_res)

    def _solve_with_bw(self, select_fn, sort_indices=None):
        """
        BW-aware greedy çekirdek döngüsü.
        select_fn(d, node, cap, intra_res) → score  — adayı puanlayan fonksiyon.
        sort_indices: VN'leri işleme sırası; None ise self.sorted_indices kullanılır.
        En yüksek puanlı, BW kısıtını da karşılayan node seçilir.
        """
        intra_res, _, bc_res, er_res = self._build_residual_maps()

        used_in_domain = {d: set() for d in range(len(self.cpu_value_all_intra_networks))}
        chrom    = [None] * self.num_genes
        assigned = {}

        adj    = self.virtualRequests.adjacency_matrix
        bw_dem = self.virtualRequests.bandwidth_demand
        n_vn   = len(adj)

        order = sort_indices if sort_indices is not None else self.sorted_indices
        for i in order:
            demand_cpu = self.cpu_demand_VirtualNetwork[i]
            d1, d2 = self.candidateDomains[i]

            linked = []
            for j in assigned:
                row, col = min(i, j), max(i, j)
                if row < n_vn and col < n_vn and adj[row][col] > 0:
                    bw = int(bw_dem[row][col])
                    if bw > 0:
                        linked.append((j, bw))

            best_option = None
            best_score  = -float('inf')

            for d in (d1, d2):
                for node, cap in enumerate(self.cpu_value_all_intra_networks[d]):
                    if node in used_in_domain[d]:
                        continue
                    if cap < demand_cpu:
                        continue

                    bw_ok = all(
                        self._link_bw_feasible(
                            d, node, *assigned[j], bw, intra_res, er_res
                        )
                        for j, bw in linked
                    )
                    if not bw_ok:
                        continue

                    score = select_fn(d, node, cap, intra_res)
                    if score > best_score:
                        best_score  = score
                        best_option = (d, node)

            if best_option is None:
                return None, float('inf'), []

            d, node = best_option
            used_in_domain[d].add(node)
            chrom[i]    = f"{d}-{node}"
            assigned[i] = (d, node)

            for j, bw in linked:
                d_j, n_j = assigned[j]
                self._deduct_link_bw(d, node, d_j, n_j, bw, intra_res, er_res, bc_res)

        fitness      = self.calculate_fitness_v2(chrom)
        path_details = self.trace_solution(chrom)
        return chrom, fitness, path_details

    def solve(self):
        return self._solve_with_bw(lambda d, node, cap, intra_res: cap)


class CentralityGreedySolver(GreedyCPUBWSolver):
    """
    Merkeziyetçilik (centrality) + BW farkındalıklı greedy çözücü.

    BW kısıtını karşılayan adaylar arasından centrality skoru en yüksek
    node seçilir.

    Desteklenen metodlar:
        'closeness'   — Closeness Centrality
        'betweenness' — Betweenness Centrality
        'degree'      — Degree Centrality
        'pagerank'    — PageRank
        'eigenvector' — Eigenvector Centrality
    """

    METHODS = {
        'closeness':   nx.closeness_centrality,
        'betweenness': nx.betweenness_centrality,
        'degree':      nx.degree_centrality,
        'pagerank':    nx.pagerank,
        'eigenvector': None,
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
        self._centrality_cache: dict = {}

    def _compute_centrality(self, graph: nx.Graph, domain_id: int) -> dict:
        if domain_id in self._centrality_cache:
            return self._centrality_cache[domain_id]

        if graph.number_of_nodes() == 0:
            self._centrality_cache[domain_id] = {}
            return {}

        try:
            if self.method == 'eigenvector':
                result = nx.eigenvector_centrality_numpy(graph)
            else:
                result = self.METHODS[self.method](graph)
        except Exception:
            result = {n: 0.0 for n in graph.nodes()}

        self._centrality_cache[domain_id] = result
        return result

    def solve(self):
        self._centrality_cache.clear()

        # Centrality haritalarını önceden hesapla
        cent = {
            d: self._compute_centrality(self.intraNetworkGraphwithBWMatrix[d], d)
            for d in range(len(self.intraNetworkGraphwithBWMatrix))
        }

        return self._solve_with_bw(lambda d, node, cap, intra_res: cent[d].get(node, 0.0))


class GreedyBWSortSolver(GreedyCPUBWSolver):
    """
    BW-demand sıralamalı greedy çözücü.

    VN'ler toplam BW talebine göre büyükten küçüğe işlenir.
    Node skoru: residual grafikte o node'a bağlı minimum kenar BW'si
    (bottleneck BW). Yüksek min-BW'li node tercih edilir.
    """

    def _vn_sort_indices(self):
        adj    = self.virtualRequests.adjacency_matrix
        bw_dem = self.virtualRequests.bandwidth_demand
        n_vn   = len(adj)
        total_bw = []
        for i in range(n_vn):
            s = 0.0
            for j in range(n_vn):
                row, col = min(i, j), max(i, j)
                if adj[row][col] > 0:
                    s += float(bw_dem[row][col])
            total_bw.append(s)
        return sorted(range(n_vn), key=lambda i: total_bw[i], reverse=True)

    def _node_min_bw(self, d, node, intra_res):
        G   = self.intraNetworkGraphwithBWMatrix[d]
        res = intra_res.get(d, {})
        nbrs = list(G.neighbors(node))
        if not nbrs:
            return 0.0
        return min(res.get((min(node, nb), max(node, nb)), 0) for nb in nbrs)

    def solve(self):
        sort_idx = self._vn_sort_indices()
        return self._solve_with_bw(
            lambda d, node, cap, intra_res: self._node_min_bw(d, node, intra_res),
            sort_indices=sort_idx,
        )


class GreedyDegreeSortSolver(GreedyCPUBWSolver):
    """
    Sanal-derece sıralamalı greedy çözücü.

    VN'ler sanal ağdaki derece sayısına göre büyükten küçüğe işlenir.
    Node skoru: fiziksel intra-domain grafiğindeki derece sayısı.
    Yüksek dereceli (merkezi) fiziksel node tercih edilir.
    """

    def _vn_sort_indices(self):
        adj  = self.virtualRequests.adjacency_matrix
        n_vn = len(adj)
        degrees = [
            sum(1 for j in range(n_vn) if adj[min(i, j)][max(i, j)] > 0)
            for i in range(n_vn)
        ]
        return sorted(range(n_vn), key=lambda i: degrees[i], reverse=True)

    def solve(self):
        sort_idx = self._vn_sort_indices()
        graphs   = self.intraNetworkGraphwithBWMatrix
        return self._solve_with_bw(
            lambda d, node, cap, intra_res: graphs[d].degree(node),
            sort_indices=sort_idx,
        )


class CentralityBWSortSolver(CentralityGreedySolver):
    """
    Closeness centrality skoru + sanal BW-demand sıralaması.

    VN'ler toplam BW talebine göre büyükten küçüğe işlenir (GreedyBWSortSolver sırası).
    Node skoru: closeness centrality (veya yapılandırılan metod).
    """

    def solve(self):
        self._centrality_cache.clear()
        cent = {
            d: self._compute_centrality(self.intraNetworkGraphwithBWMatrix[d], d)
            for d in range(len(self.intraNetworkGraphwithBWMatrix))
        }
        sort_idx = GreedyBWSortSolver._vn_sort_indices(self)
        return self._solve_with_bw(
            lambda d, node, cap, intra_res: cent[d].get(node, 0.0),
            sort_indices=sort_idx,
        )


class CentralityDegreeSortSolver(CentralityGreedySolver):
    """
    Closeness centrality skoru + sanal derece sıralaması.

    VN'ler sanal ağdaki derece sayısına göre büyükten küçüğe işlenir (GreedyDegreeSortSolver sırası).
    Node skoru: closeness centrality (veya yapılandırılan metod).
    """

    def solve(self):
        self._centrality_cache.clear()
        cent = {
            d: self._compute_centrality(self.intraNetworkGraphwithBWMatrix[d], d)
            for d in range(len(self.intraNetworkGraphwithBWMatrix))
        }
        sort_idx = GreedyDegreeSortSolver._vn_sort_indices(self)
        return self._solve_with_bw(
            lambda d, node, cap, intra_res: cent[d].get(node, 0.0),
            sort_indices=sort_idx,
        )
