import random
from typing import List, Optional

# --- YARDIMCI FONKSİYONLAR ---

def parse_domain(gene: str) -> int:
    # "5-2" -> 5
    return int(gene.split("-")[0])

def best_unused_node_in_domain(domain_cpu_list: List[int], cpu_demand: float, used_nodes_1based: set) -> Optional[int]:
    """
    GÜNCELLENDİ: Artık Matris değil, düz CPU listesi alıyor.
    domain_cpu_list: [45, 17, 29...] gibi.
    """
    best_idx = None
    best_cpu = -1
    n = len(domain_cpu_list) # Node sayısı listenin uzunluğudur
    
    for i in range(n):
        idx1 = i + 1 # 1-based index
        if idx1 in used_nodes_1based:
            continue
            
        # ESKİSİ: cap = domain_mat[i][i]
        # YENİSİ: Doğrudan listeden çekiyoruz (Çok daha hızlı)
        cap = domain_cpu_list[i] 
        
        if cap >= cpu_demand and cap > best_cpu:
            best_cpu = cap
            best_idx = idx1
    return best_idx

def build_chromosome_sorted_cpu_random_domain_unique_nodes(istekler, v_cpu_demands, all_domains_cpu_list, seed=None, max_tries=500):
    rng = random.Random(seed)
    m = len(istekler)
    order = sorted(range(m), key=lambda i: v_cpu_demands[i], reverse=True)

    for _ in range(max_tries):
        # Dictionary yerine artık list indexi kullanıyoruz ama mantık aynı kalsın diye dict tuttum
        # Sadece key'ler 0,1,2... domain ID olacak.
        used_in_domain = {d_id: set() for d_id in range(len(all_domains_cpu_list))}
        
        chrom = [None] * m
        ok = True

        for i in order:
            demand = v_cpu_demands[i]
            d1, d2 = istekler[i]
            feasible = []

            for d in (d1, d2):
                # Doğrudan ana listeden domain'in CPU listesini çekiyoruz
                if d >= len(all_domains_cpu_list): continue # Hata koruması
                
                domain_cpu_data = all_domains_cpu_list[d]
                
                node_idx = best_unused_node_in_domain(domain_cpu_data, demand, used_in_domain[d])
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

def rebuild_genes_from_domains(
    domains: List[int],
    istekler: List[List[int]],
    v_cpu_demands: List[float],
    all_domains_cpu_list: List[List[int]], # İsim değişti: Dict yerine List of Lists
    rng: random.Random
) -> Optional[List[str]]:
    
    m = len(domains)
    # 0'dan len-1'e kadar tüm domainler için set oluştur
    used_in_domain = {d_id: set() for d_id in range(len(all_domains_cpu_list))}
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
            
            # Domain ID listede var mı kontrolü
            if d >= len(all_domains_cpu_list): continue 
            
            # Matris yerine doğrudan listeyi gönderiyoruz
            node_idx = best_unused_node_in_domain(all_domains_cpu_list[d], demand, used_in_domain[d])
            
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
    all_domains_cpu_list: List[List[int]],
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

    return rebuild_genes_from_domains(child_domains, istekler, v_cpu_demands, all_domains_cpu_list, rng)


# ------------------ MAIN TEST ------------------
if __name__ == "__main__":
    
    # SENİN VERDİĞİN HAM LİSTE (Artık doğrudan bunu kullanıyoruz)
    # Index 0 -> Domain 0, Index 1 -> Domain 1 ...
    cpu_value_all_intra_networks = [
        [45, 17, 29, 15, 21], 
        [46, 13, 28, 32, 47], 
        [36, 49, 10, 35, 14], 
        [21, 48, 48, 18, 21], 
        [48, 29, 47, 32, 49], 
        [48, 12, 46, 31, 10], 
        [37, 23, 41, 25, 35], 
        [41, 21, 23, 35, 33], 
        [35, 45, 37, 34, 12], 
        [38, 13, 32, 37, 21], 
        [43, 13, 15, 13, 14], 
        [48, 43, 25, 40, 40], 
        [37, 40, 33, 43, 44], 
        [12, 48, 12, 16, 20] 
    ]
    
    print(f"Toplam Domain Sayısı: {len(cpu_value_all_intra_networks)}")
    print(f"Domain 0, Node 1 CPU: {cpu_value_all_intra_networks[0][0]}")

    # Örnek İstekler
    istekler = [
        [0, 1],   
        [2, 4],   
        [12, 13], 
        [12, 13]  
    ]
    
    v_cpu_demands = [15, 20, 10, 30] 

    # --- Parentleri Oluştururken Artık Matris Değil Doğrudan Listeyi Veriyoruz ---
    p1 = build_chromosome_sorted_cpu_random_domain_unique_nodes(
        istekler, v_cpu_demands, cpu_value_all_intra_networks, seed=None
    )
    p2 = build_chromosome_sorted_cpu_random_domain_unique_nodes(
        istekler, v_cpu_demands, cpu_value_all_intra_networks, seed=None
    )
    
    print("\n--- Parentler ---")
    print(f"P1: {p1}")
    print(f"P2: {p2}")

    # --- Crossover ---
    if p1 and p2:
        child = crossover_domains_then_rebuild(p1, p2, istekler, v_cpu_demands, cpu_value_all_intra_networks, seed=None)
        print("\n--- Child (Sonuç) ---")
        print(f"Child: {child}")
    else:
        print("\nParent oluşturulamadı.")