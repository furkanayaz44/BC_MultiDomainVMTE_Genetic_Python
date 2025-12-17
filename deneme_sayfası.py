import random

def best_unused_node_in_domain(domain_mat, cpu_demand, used_node_idxs_1based):
    """
    domain_mat: diagonal CPU kapasitesi
    used_node_idxs_1based: bu domain'de daha önce kullanılan fiziksel düğüm indexleri (1-based)
    Dönüş: (node_index_1based) veya None
    """
    best_idx = None
    best_cpu = -1
    n = len(domain_mat)
    for i in range(n):
        idx1 = i + 1
        if idx1 in used_node_idxs_1based:
            continue
        cap = domain_mat[i][i]
        if cap >= cpu_demand and cap > best_cpu:
            best_cpu = cap
            best_idx = idx1
    return best_idx

def build_chromosome_sorted_cpu_random_domain_unique_nodes(
    istekler, v_cpu_demands, domain_mats, seed=None, max_tries=500
):
    """
    istekler: [[d1,d2], ...] (her sanal düğümün domain adayları)
    v_cpu_demands: [cpu1,cpu2,...]
    domain_mats: {domain_id: adjacency_matrix} (CPU diagonal'da)
    çıktı: ["5-1","10-2","4-5", ...] veya None
    """
    rng = random.Random(seed)
    m = len(istekler)

    # büyük CPU talebinden küçüğe sırala
    order = sorted(range(m), key=lambda i: v_cpu_demands[i], reverse=True)

    for _ in range(max_tries):
        used_in_domain = {d: set() for d in domain_mats.keys()}  # domain -> {nodeIdx1based}
        chrom = [None] * m
        ok = True

        for i in order:
            demand = v_cpu_demands[i]
            d1, d2 = istekler[i]

            feasible = []

            for d in (d1, d2):
                if d not in domain_mats:
                    continue
                node_idx = best_unused_node_in_domain(domain_mats[d], demand, used_in_domain[d])
                if node_idx is not None:
                    feasible.append((d, node_idx))

            if not feasible:
                ok = False
                break

            # Domain seçimi rastgele (feasible içinden)
            d, node_idx = rng.choice(feasible)
            used_in_domain[d].add(node_idx)
            chrom[i] = f"{d}-{node_idx}"

        if ok:
            return chrom

    return None

def build_domain_mats(num_domains, scope):
    """
    scope: globals() veya locals() ver.
    domain1, domain2, ... domainN değişkenlerini okuyup dict'e çevirir.
    """
    mats = {}
    for d in range(1, num_domains + 1):
        name = f"domain{d}"
        if name in scope:
            mats[d] = scope[name]
    return mats

import random
from typing import List, Dict, Optional, Tuple

def parse_domain(gene: str) -> int:
    # "5-2" -> 5
    return int(gene.split("-")[0])

def best_unused_node_in_domain(domain_mat, cpu_demand: float, used_nodes_1based: set) -> Optional[int]:
    """
    Seçilen domain'de cpu_demand'i karşılayanlar içinde CPU'su en büyük VE boş node'u seçer.
    domain_mat diagonal CPU kapasitesi.
    """
    best_idx = None
    best_cpu = -1
    n = len(domain_mat)
    for i in range(n):
        idx1 = i + 1
        if idx1 in used_nodes_1based:
            continue
        cap = domain_mat[i][i]
        if cap >= cpu_demand and cap > best_cpu:
            best_cpu = cap
            best_idx = idx1
    return best_idx

def rebuild_genes_from_domains(
    domains: List[int],
    istekler: List[List[int]],
    v_cpu_demands: List[float],
    domain_mats: Dict[int, List[List[float]]],
    rng: random.Random
) -> Optional[List[str]]:
    """
    Child'ın sadece domain seçimleri verili iken,
    nodeIndex'leri 'max cpu unused' kuralına göre yeniden üretir (repair + rebuild).
    """
    m = len(domains)

    # domain -> kullanılan node indexleri (1-based)
    used_in_domain = {d: set() for d in domain_mats.keys()}

    genes = [None] * m

    # CPU talebi büyükten küçüğe yerleştir (daha az tıkanır)
    order = sorted(range(m), key=lambda i: v_cpu_demands[i], reverse=True)

    for i in order:
        demand = v_cpu_demands[i]

        # Önce crossover'ın verdiği domain'i dene, olmazsa alternatif domain'i dene
        d_primary = domains[i]
        d1, d2 = istekler[i]
        d_alt = d2 if d_primary == d1 else d1  # diğer aday (d1==d2 ise aynı kalır)

        tried = []
        for d in (d_primary, d_alt):
            if d in tried:
                continue
            tried.append(d)
            if d not in domain_mats:
                continue
            node_idx = best_unused_node_in_domain(domain_mats[d], demand, used_in_domain[d])
            if node_idx is not None:
                used_in_domain[d].add(node_idx)
                domains[i] = d  # domain repair (gerekirse alternatif domain'e geç)
                genes[i] = f"{d}-{node_idx}"
                break

        if genes[i] is None:
            return None  # bu child için mapping mümkün değil

    return genes

def crossover_domains_then_rebuild(
    parent1: List[str],
    parent2: List[str],
    istekler: List[List[int]],
    v_cpu_demands: List[float],
    domain_mats: Dict[int, List[List[float]]],
    seed: Optional[int] = None
) -> Optional[List[str]]:
    """
    2-point segment crossover (domain seviyesinde) + rebuild node mapping.
    """
    rng = random.Random(seed)
    m = len(parent1)

    # 1) Parent domain'lerini çıkar
    d1 = [parse_domain(g) for g in parent1]
    d2 = [parse_domain(g) for g in parent2]

    # 2) 2-point segment seç
    a = rng.randrange(m)
    b = rng.randrange(m)
    l, r = (a, b) if a <= b else (b, a)

    # 3) Child domains: Parent1 kopyası, [l..r] Parent2'den
    child_domains = d1[:]
    for i in range(l, r + 1):
        child_domains[i] = d2[i]

    # 4) (Opsiyonel) Domain kısıt repair: child_domains[i] mutlaka istekler[i] içinde olmalı
    for i in range(m):
        if child_domains[i] not in istekler[i]:
            child_domains[i] = rng.choice(istekler[i])

    # 5) Node mapping'i yeniden kur (max cpu unused)
    return rebuild_genes_from_domains(child_domains, istekler, v_cpu_demands, domain_mats, rng)

# ------------------ SENİN ÖRNEK ------------------
if __name__ == "__main__":

    domain1 = [[100]]
    domain2 = [[8,0],[0,7]]
    domain3 = [[8,0,0,0],[0,7,0,0],[0,0,6,0],[0,0,5,0]]
    domain4 = [[5,0],[0,20]]
    domain5 = [[8,0,0,0],[0,7,0,0],[0,0,6,0],[0,0,5,0]]
    domain6 = [[6,0],[0,6]]
    domain10 = [[14,0,0,0],[0,13,0,0],[0,0,2,0],[0,0,0,1]]  # ister kullan ister kullanma

    num_domains = 10  # bunu sen vereceksin

    # domain1..domainN değişkenlerinden domain_mats üret
    domain_mats = build_domain_mats(num_domains, globals())



    istekler = [[3, 5], [3, 10], [2, 4], [3, 1]]
    v_cpu_demands = [1, 2, 3, 4]

    

    p1 = build_chromosome_sorted_cpu_random_domain_unique_nodes(
        istekler, v_cpu_demands, domain_mats
    )
    p2 = build_chromosome_sorted_cpu_random_domain_unique_nodes(
        istekler, v_cpu_demands, domain_mats
    )
    print(f"p1->{p1}")
    print(f"p2->{p2}")

    child = crossover_domains_then_rebuild(p1, p2, istekler, v_cpu_demands, domain_mats)
    print(child)
