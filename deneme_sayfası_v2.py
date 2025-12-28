import random
from typing import List, Dict, Optional


def parse_domain(gene: str) -> int:
    # "5-2" -> 5 (Gene stringinden domain ID'sini çeker)
    return int(gene.split("-")[0])

def best_unused_node_in_domain(domain_mat, cpu_demand: float, used_nodes_1based: set) -> Optional[int]:

    best_idx = None
    best_cpu = -1
    n = len(domain_mat)
    
    for i in range(n):
        idx1 = i + 1 # 1-based index (Node'lar 1'den başlar: 1, 2, 3...)
        if idx1 in used_nodes_1based:
            continue
            
        # Matrisin köşegenindeki (diagonal) değer CPU kapasitesidir
        cap = domain_mat[i][i] 
        
        if cap >= cpu_demand and cap > best_cpu:
            best_cpu = cap
            best_idx = idx1
    return best_idx

def build_chromosome_sorted_cpu_random_domain_unique_nodes(istekler, v_cpu_demands, domain_mats, seed=None, max_tries=500):

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

def rebuild_genes_from_domains(
    domains: List[int],
    istekler: List[List[int]],
    v_cpu_demands: List[float],
    domain_mats: Dict[int, List[List[float]]],
    rng: random.Random
) -> Optional[List[str]]:
    """
    Child'ın sadece domain seçimleri verili iken,
    nodeIndex'leri 'max cpu unused' kuralına göre yeniden üretir.
    """
    m = len(domains)
    used_in_domain = {d: set() for d in domain_mats.keys()}
    genes = [None] * m

    order = sorted(range(m), key=lambda i: v_cpu_demands[i], reverse=True)

    for i in order:
        demand = v_cpu_demands[i]
        d_primary = domains[i]
        d1, d2 = istekler[i]
        d_alt = d2 if d_primary == d1 else d1 

        tried = []
        for d in (d_primary, d_alt):
            if d in tried: continue
            tried.append(d)
            
            if d not in domain_mats: continue
            
            node_idx = best_unused_node_in_domain(domain_mats[d], demand, used_in_domain[d])
            if node_idx is not None:
                used_in_domain[d].add(node_idx)
                domains[i] = d 
                genes[i] = f"{d}-{node_idx}"
                break

        if genes[i] is None:
            return None 

    return genes

def crossover_domains_then_rebuild(
    parent1: List[str],
    parent2: List[str],
    istekler: List[List[int]],
    v_cpu_demands: List[float],
    domain_mats: Dict[int, List[List[float]]],
    seed: Optional[int] = None
) -> Optional[List[str]]:

    rng = random.Random(seed)
    m = len(parent1)

    d1 = [parse_domain(g) for g in parent1]
    d2 = [parse_domain(g) for g in parent2]

    a = rng.randrange(m)
    b = rng.randrange(m)
    l, r = (a, b) if a <= b else (b, a)

    child_domains = d1[:]
    for i in range(l, r + 1):
        child_domains[i] = d2[i]

    # Domain kısıt repair
    for i in range(m):
        if child_domains[i] not in istekler[i]:
            child_domains[i] = rng.choice(istekler[i])

    return rebuild_genes_from_domains(child_domains, istekler, v_cpu_demands, domain_mats, rng)

# --- YENİ EKLENEN KISIM: LİSTEDEN MATRİS OLUŞTURMA ---

def build_domain_mats_from_list(cpu_values_list):
    """
    cpu_value_all_intra_networks listesini alır.
    Her bir satırı (örn: [45, 17, 29]) alır ve köşegen matris formatına çevirir.
    GÜNCELLEME: Index 0 -> Domain 0, Index 1 -> Domain 1 şeklinde haritalar (0-13 arası).
    """
    mats = {}
    for index, cpu_row in enumerate(cpu_values_list):
        # BURASI DEĞİŞTİ: Artık index neyse Domain ID o (0'dan başlar)
        domain_id = index 
        
        n = len(cpu_row)
        
        # NxN boyutunda sıfır matrisi oluştur
        matrix = [[0] * n for _ in range(n)]
        
        # CPU değerlerini köşegene (diagonal) yerleştir
        for i in range(n):
            matrix[i][i] = cpu_row[i]
            
        mats[domain_id] = matrix
    return mats

# ------------------ MAIN TEST ------------------
if __name__ == "__main__":
    

    cpu_value_all_intra_networks = [
        [45, 17, 29, 15, 21], # Domain 0
        [46, 13, 28, 32, 47], # Domain 1
        [36, 49, 10, 35, 14], # Domain 2
        [21, 48, 48, 18, 21], # Domain 3
        [48, 29, 47, 32, 49], # Domain 4
        [48, 12, 46, 31, 10], # Domain 5
        [37, 23, 41, 25, 35], # Domain 6
        [41, 21, 23, 35, 33], # Domain 7
        [35, 45, 37, 34, 12], # Domain 8
        [38, 13, 32, 37, 21], # Domain 9
        [43, 13, 15, 13, 14], # Domain 10
        [48, 43, 25, 40, 40], # Domain 11
        [37, 40, 33, 43, 44], # Domain 12
        [12, 48, 12, 16, 20]  # Domain 13 
    ]

    # Domain Matrislerini Oluştur (Artık Key'ler 0, 1, ..., 13)
    domain_mats = build_domain_mats_from_list(cpu_value_all_intra_networks)
    
    print(f"Toplam Domain Sayısı: {len(domain_mats)}")
   
    print(f"Domain 0 (Listenin ilk satırı): {domain_mats[0][0][0]} CPU") 


    istekler = [
        [0, 1],   # 1. istek için Domain 0 veya 1
        [2, 4],   # 2. istek için Domain 2 veya 4
        [12, 13], # 3. istek için Domain 12 veya 13 (Listenin son iki satırı)
        [12, 13]  # 4. istek tekrar
    ]
    
    # Sanal CPU talepleri
    v_cpu_demands = [15, 20, 10, 30] 

    p1 = build_chromosome_sorted_cpu_random_domain_unique_nodes(
        istekler, v_cpu_demands, domain_mats, seed=42
    )
    p2 = build_chromosome_sorted_cpu_random_domain_unique_nodes(
        istekler, v_cpu_demands, domain_mats, seed=99
    )
    
    print("\n--- Parentler ---")
    print(f"P1: {p1}")
    print(f"P2: {p2}")

    if p1 and p2:
        child = crossover_domains_then_rebuild(p1, p2, istekler, v_cpu_demands, domain_mats, seed=None)
        print("\n--- Child (Sonuç) ---")
        print(f"Child: {child}")
    else:
        print("\nParent oluşturulamadı (Kaynak yetersiz olabilir).")