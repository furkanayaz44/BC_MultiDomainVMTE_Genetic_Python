import networkx as nx
import numpy as np
from .genetic import GeneticDomainSolver
from .centrality import GreedyCPUSolver, CentralityGreedySolver


class GeneticDelaySolver(GeneticDomainSolver):
    """
    Delay-bazlı GeneticDomainSolver.

    Farklar (GeneticDomainSolver'dan):
      - convertGxAllIntraNetwork : kenarlara 'delay' ağırlığı da eklenir.
      - _find_path_intra_residual: BW filtrelemesi aynen korunur;
            yol seçimi weight='delay' ile yapılır; dönüş değeri (path, total_delay).
      - _find_bc_residual        : min hops yerine min maxDelay seçilir;
            BW düşümü ve intra_res güncellemesi aynen korunur.

    Miras alınan her şey (calculate_fitness_v2, trace_solution, run, crossover,
    mutate, create_chromosome …) değişmez; sadece yukarıdaki 3 yardımcı override
    edilir, fitness metriği otomatik olarak delay'e dönüşür.
    """

    # ------------------------------------------------------------------
    # Intra-domain graf kurulumu — delay ağırlığı eklendi
    # ------------------------------------------------------------------
    def convertGxAllIntraNetwork(self):
        gx_list = []
        for intra in self.intraNetworkTopologies:
            adj_matrix   = np.array(intra.adjacency_matrix)
            bw_matrix    = np.array(intra.bandwidth_matrix)
            delay_matrix = np.array(intra.delay_matrix)
            G = nx.Graph()
            rows, cols = adj_matrix.shape
            for i in range(rows):
                for j in range(cols):
                    if adj_matrix[i][j] == 1:
                        G.add_edge(
                            i, j,
                            bw=int(bw_matrix[i][j]),
                            delay=int(delay_matrix[i][j]),
                        )
            gx_list.append(G)
        return gx_list

    # ------------------------------------------------------------------
    # Intra-domain yol bulma — delay minimize, BW filtreli
    # ------------------------------------------------------------------
    def _find_path_intra_residual(self, domain_id, src, dst, required_bw, intra_res):
        """
        BW kısıtına göre filtrelenmiş grafta delay-bazlı en kısa yol bulur.
        Kullanılan her linkten required_bw kadar residual BW düşer (aynen).

        Döner: (path, total_delay)  — bulunamazsa (None, 100000)
        """
        res    = intra_res[domain_id]
        base_G = self.intraNetworkGraphwithBWMatrix[domain_id]

        # Sadece yeterli artık BW'si olan kenarlardan delay ağırlıklı geçici graf
        filtered_G = nx.Graph()
        filtered_G.add_nodes_from(base_G.nodes())
        for (u, v), bw in res.items():
            if bw >= required_bw:
                edge_data = base_G.get_edge_data(u, v) or base_G.get_edge_data(v, u) or {}
                delay_val = edge_data.get('delay', 1)
                filtered_G.add_edge(u, v, delay=delay_val)

        try:
            path = nx.shortest_path(filtered_G, source=src, target=dst, weight='delay')
            total_delay = sum(
                filtered_G[path[i]][path[i + 1]]['delay']
                for i in range(len(path) - 1)
            )
            # BW güncelleme — aynen korunur
            for i in range(len(path) - 1):
                key = (min(path[i], path[i + 1]), max(path[i], path[i + 1]))
                if key in res:
                    res[key] -= required_bw
            return path, total_delay
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None, 100000

    # ------------------------------------------------------------------
    # BC transaction seçimi — min maxDelay, BW filtreli
    # ------------------------------------------------------------------
    def _find_bc_residual(self, domain, src_node, dst_node, required_bw, bc_res, intra_res):
        """
        Artık BW kısıtını karşılayan transaction'lar arasından en az maxDelay'li
        olanı seçer.  BW güncelleme ve intra_res düşümü aynen korunur.

        Döner: (transaction, delay)  — bulunamazsa (None, 100000)
        """
        best_t     = None
        best_delay = 100000

        for t in self.allTransaction:
            if t.edgeDomainEgress != domain:
                continue
            node_match = (
                (t.edgeNodeIngress == src_node and t.edgeNodeEgress == dst_node) or
                (t.edgeNodeIngress == dst_node  and t.edgeNodeEgress == src_node)
            )
            if not node_match:
                continue
            if bc_res.get(id(t), 0) < required_bw:
                continue
            if t.maxDelay < best_delay:
                best_delay = t.maxDelay
                best_t     = t

        if best_t is not None:
            bc_res[id(best_t)] -= required_bw
            # fullpath üzerindeki fiziksel intra linklerden BW düş — aynen korunur
            try:
                nodes = [int(n.strip()) for n in best_t.fullpath.strip('[]').split(',')]
                domain_links = intra_res.get(domain, {})
                for i in range(len(nodes) - 1):
                    n1 = nodes[i]     % 1000
                    n2 = nodes[i + 1] % 1000
                    key = (min(n1, n2), max(n1, n2))
                    if key in domain_links:
                        domain_links[key] -= required_bw
            except (ValueError, AttributeError):
                pass
            return best_t, best_delay

        return None, 100000

    # ------------------------------------------------------------------
    # calculate_fitness_v2 — delay versiyonu
    # GeneticDomainSolver'dan kopyalandı; tek fark:
    #   totalDelay += numOfDelay + chosen_er.maxDelay   (eskisi: + 1)
    # ------------------------------------------------------------------
    def calculate_fitness_v2(self, chromosome):
        import numpy as np

        if chromosome is None:
            return float('inf')

        adjMatrixVirtualRequests = self.virtualRequests.adjacency_matrix
        n = len(adjMatrixVirtualRequests)
        totalDelay = 0

        intra_res, _, bc_res, er_res = self._build_residual_maps()

        seen_genes = set()
        for gene in chromosome:
            if gene in seen_genes:
                totalDelay += 100000
            seen_genes.add(gene)

        for gene_idx, gene in enumerate(chromosome):
            d, node = self._parse_gene(gene)
            cpu_cap = self.cpu_value_all_intra_networks[d][node]
            cpu_req = self.cpu_demand_VirtualNetwork[gene_idx]
            if cpu_cap < cpu_req:
                totalDelay += 100000

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

                if sourceDomainId == destinationDomainId:
                    _, delay = self._find_path_intra_residual(
                        sourceDomainId, sourceIntraNodeId, destinationIntraNodeId,
                        required_bw, intra_res
                    )
                    totalDelay += delay
                    continue

                interDomainPathList = self._find_inter_path_residual(
                    sourceDomainId, destinationDomainId, required_bw, er_res
                )
                if interDomainPathList is None:
                    totalDelay += 100000
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
                            continue
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
                        totalDelay += 100000
                        path_broken = True
                        break

                    er_res[id(chosen_er)] -= required_bw

                    if sourceIndex.size == 0:
                        _, delay = self._find_path_intra_residual(
                            interDomainPathList[step], currentEdge, domainicihedefdugum,
                            required_bw, intra_res
                        )
                        totalDelay += delay
                    else:
                        t, numOfDelay = self._find_bc_residual(
                            currentDomain, currentEdge, domainicihedefdugum,
                            required_bw, bc_res, intra_res
                        )
                        if t is None:
                            _, numOfDelay = self._find_path_intra_residual(
                                interDomainPathList[step], currentEdge, domainicihedefdugum,
                                required_bw, intra_res
                            )
                        # edge router geçiş gecikmesi: chosen_er.maxDelay
                        totalDelay += numOfDelay + chosen_er.maxDelay

                    currentDomain = nextDomain
                    currentEdge = nextEdge

                if not path_broken and currentDomain == destinationDomainId:
                    destSearchEdge = (
                        (self.edgeRouterDomainVertexList[:, 0] == destinationDomainId) &
                        (self.edgeRouterDomainVertexList[:, 1] == destinationIntraNodeId)
                    )
                    destIsEdgeRouter = np.where(destSearchEdge)[0].size > 0

                    if destIsEdgeRouter:
                        t, numOfDelay = self._find_bc_residual(
                            destinationDomainId, currentEdge, destinationIntraNodeId,
                            required_bw, bc_res, intra_res
                        )
                        if t is None:
                            _, numOfDelay = self._find_path_intra_residual(
                                destinationDomainId, currentEdge, destinationIntraNodeId,
                                required_bw, intra_res
                            )
                        totalDelay += numOfDelay
                    else:
                        _, delay = self._find_path_intra_residual(
                            destinationDomainId, currentEdge, destinationIntraNodeId,
                            required_bw, intra_res
                        )
                        totalDelay += delay

        return totalDelay

    # ------------------------------------------------------------------
    # trace_solution — delay versiyonu
    # GeneticDomainSolver'dan kopyalandı; tek fark:
    #   'hop': chosen_er.maxDelay   (domain gecisi segmentinde, eskisi: 1)
    # ------------------------------------------------------------------
    def trace_solution(self, chromosome):
        import numpy as np

        if chromosome is None:
            return []

        intra_res, _, bc_res, er_res = self._build_residual_maps()

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

                if sourceDomainId == destinationDomainId:
                    path, delay = self._find_path_intra_residual(
                        sourceDomainId, sourceIntraNodeId, destinationIntraNodeId,
                        required_bw, intra_res
                    )
                    link['segmentler'].append({
                        'tip': 'intra (topoloji)',
                        'domain': sourceDomainId,
                        'baslangic_node': sourceIntraNodeId,
                        'bitis_node': destinationIntraNodeId,
                        'yol': path,
                        'hop': delay,
                        'bw_talebi': required_bw
                    })
                    virtual_links.append(link)
                    continue

                interDomainPathList = self._find_inter_path_residual(
                    sourceDomainId, destinationDomainId, required_bw, er_res
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
                            continue
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

                    er_res[id(chosen_er)] -= required_bw

                    if sourceIndex.size == 0:
                        path, delay = self._find_path_intra_residual(
                            interDomainPathList[step], currentEdge, domainicihedefdugum,
                            required_bw, intra_res
                        )
                        link['segmentler'].append({
                            'tip': 'intra (topoloji)',
                            'domain': interDomainPathList[step],
                            'baslangic_node': currentEdge,
                            'bitis_node': domainicihedefdugum,
                            'yol': path,
                            'hop': delay,
                            'bw_talebi': required_bw
                        })
                    else:
                        t, numOfDelay = self._find_bc_residual(
                            currentDomain, currentEdge, domainicihedefdugum,
                            required_bw, bc_res, intra_res
                        )
                        if t is not None:
                            tip = 'intra (blokzincir)'
                            yol = t.fullpath
                        else:
                            tip = 'intra (topoloji, bc bw yetersiz)'
                            yol, numOfDelay = self._find_path_intra_residual(
                                interDomainPathList[step], currentEdge, domainicihedefdugum,
                                required_bw, intra_res
                            )
                        link['segmentler'].append({
                            'tip': tip,
                            'domain': currentDomain,
                            'baslangic_node': currentEdge,
                            'bitis_node': domainicihedefdugum,
                            'yol': yol,
                            'hop': numOfDelay,
                            'bw_talebi': required_bw
                        })
                        # edge router geçiş gecikmesi: chosen_er.maxDelay
                        link['segmentler'].append({
                            'tip': 'domain gecisi',
                            'kaynak_domain': currentDomain,
                            'hedef_domain': nextDomain,
                            'hop': chosen_er.maxDelay
                        })

                    currentDomain = nextDomain
                    currentEdge = nextEdge

                if not path_broken and currentDomain == destinationDomainId:
                    destSearchEdge = (
                        (self.edgeRouterDomainVertexList[:, 0] == destinationDomainId) &
                        (self.edgeRouterDomainVertexList[:, 1] == destinationIntraNodeId)
                    )
                    destIsEdgeRouter = np.where(destSearchEdge)[0].size > 0

                    if destIsEdgeRouter:
                        t, numOfDelay = self._find_bc_residual(
                            destinationDomainId, currentEdge, destinationIntraNodeId,
                            required_bw, bc_res, intra_res
                        )
                        if t is not None:
                            link['segmentler'].append({
                                'tip': 'intra son domain (blokzincir)',
                                'domain': destinationDomainId,
                                'baslangic_node': currentEdge,
                                'bitis_node': destinationIntraNodeId,
                                'yol': t.fullpath,
                                'hop': numOfDelay,
                                'bw_talebi': required_bw
                            })
                        else:
                            path, delay = self._find_path_intra_residual(
                                destinationDomainId, currentEdge, destinationIntraNodeId,
                                required_bw, intra_res
                            )
                            link['segmentler'].append({
                                'tip': 'intra son domain (topoloji, bc yok)',
                                'domain': destinationDomainId,
                                'baslangic_node': currentEdge,
                                'bitis_node': destinationIntraNodeId,
                                'yol': path,
                                'hop': delay,
                                'bw_talebi': required_bw
                            })
                    else:
                        path, delay = self._find_path_intra_residual(
                            destinationDomainId, currentEdge, destinationIntraNodeId,
                            required_bw, intra_res
                        )
                        link['segmentler'].append({
                            'tip': 'intra son domain (topoloji)',
                            'domain': destinationDomainId,
                            'baslangic_node': currentEdge,
                            'bitis_node': destinationIntraNodeId,
                            'yol': path,
                            'hop': delay,
                            'bw_talebi': required_bw
                        })

                virtual_links.append(link)

        return virtual_links


# -----------------------------------------------------------------------
# Greedy çözücüler — Python MRO ile delay yol bulma otomatik devralınır
# -----------------------------------------------------------------------

class GreedyCPUDelaySolver(GreedyCPUSolver, GeneticDelaySolver):
    """
    CPU kapasitesi tabanlı greedy çözücü + delay-bazlı yol bulma.

    MRO: GreedyCPUDelaySolver → GreedyCPUSolver → GeneticDelaySolver → GeneticDomainSolver

    solve()                   → GreedyCPUSolver.solve()
    convertGxAllIntraNetwork  → GeneticDelaySolver (delay ağırlıklı graf)
    _find_path_intra_residual → GeneticDelaySolver (delay minimize)
    _find_bc_residual         → GeneticDelaySolver (min maxDelay)
    calculate_fitness_v2      → GeneticDomainSolver (değişmez)
    trace_solution            → GeneticDomainSolver (değişmez)
    """
    pass


class CentralityDelayGreedySolver(CentralityGreedySolver, GeneticDelaySolver):
    """
    Merkeziyetçilik tabanlı greedy çözücü + delay-bazlı yol bulma.

    MRO: CentralityDelayGreedySolver → CentralityGreedySolver → GeneticDelaySolver → GeneticDomainSolver

    solve()                   → CentralityGreedySolver.solve()
    convertGxAllIntraNetwork  → GeneticDelaySolver (delay ağırlıklı graf)
    _find_path_intra_residual → GeneticDelaySolver (delay minimize)
    _find_bc_residual         → GeneticDelaySolver (min maxDelay)
    calculate_fitness_v2      → GeneticDomainSolver (değişmez)
    trace_solution            → GeneticDomainSolver (değişmez)
    """
    pass
