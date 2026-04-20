"""
main_v3.py — Algoritma Karşılaştırma Aracı
===========================================
Aynı sanal ağ gömme problemini altı farklı yöntemle çözer ve sonuçları
yan yana karşılaştırır:

    1. Genetik Algoritma      (GeneticDomainSolver)
    2. Karınca Kolonisi (ACO)  (ACODomainSolver)
    3. Greedy — CPU           (GreedyCPUSolver)
    4. Greedy — Closeness     (CentralityGreedySolver, method='closeness')
    5. Greedy — Betweenness   (CentralityGreedySolver, method='betweenness')
    6. Greedy — Degree        (CentralityGreedySolver, method='degree')

Mevcut kodlar (main_v2.py, algorithm/genetic.py, algorithm/aco.py) DEĞİŞTİRİLMEDİ.

burada greedyler var. aco var 18_04_2026 da değişti
Evrim hoca yeni yöntem önerdi burası gitti v4 geldi
"""

import os
import random
import datetime

from readFiles.InterNetworkReader import InterNetworkReader
from readFiles.readVirtualNetwork import VirtualNetworkRequest
from readFiles.IntraNetworkReader import IntraNetworkReader
from readFiles.TransactionReader import TransactionReader

from algorithm.genetic import GeneticDomainSolver
from algorithm.aco import ACODomainSolver
from algorithm.centrality import CentralityGreedySolver, GreedyCPUSolver

# -----------------------------------------------------------------------
# Ayarlar
# -----------------------------------------------------------------------
networkType = "NSFNET"
folder = f"topologies/{networkType}"
num_intranetwork_nodes = 5

# Genetik algoritma parametreleri
GA_POPULATION = 40
GA_GENERATIONS = 3
GA_MUTATION    = 0.1
GA_SEED        = None

# ACO parametreleri
ACO_ANTS       = 20
ACO_ITERATIONS = 3
ACO_ALPHA      = 1.0
ACO_BETA       = 2.0
ACO_RHO        = 0.1
ACO_Q          = 100.0
ACO_SEED       = None

# Karşılaştırılacak merkeziyetçilik metodları
CENTRALITY_METHODS = ['closeness', 'betweenness', 'degree']


# -----------------------------------------------------------------------
# Veri yükleme yardımcıları  (main_v2.py ile aynı mantık)
# -----------------------------------------------------------------------

def load_inter_network():
    directory = f"{folder}/internetwork/"
    interNetwork = None
    for fname in os.listdir(directory):
        if fname.endswith('.txt'):
            interNetwork = InterNetworkReader(os.path.join(directory, fname))
    if interNetwork is None:
        raise FileNotFoundError(f"Inter-network dosyası bulunamadı: {directory}")
    return interNetwork


def load_intra_networks(num_domains):
    directory = f"{folder}/intranetwork/"
    prefix = f"adjacency_{num_intranetwork_nodes}_"
    all_candidates = sorted([
        f for f in os.listdir(directory)
        if f.startswith(prefix) and f.endswith('.txt')
    ])
    if not all_candidates:
        raise FileNotFoundError(
            f"'{directory}' içinde '{prefix}*.txt' formatında dosya bulunamadı."
        )
    # Test tutarlılığı için sabit seçim (main_v2.selectFixedIntraNetwork ile aynı)
    fixed_file = all_candidates[0]
    selected = [fixed_file] * num_domains
    print(f"[Sabit Seçim] İntra topoloji: {fixed_file} × {num_domains} domain")
    return IntraNetworkReader.load_intra_topology(directory, selected), selected


def load_transaction():
    directory = f"{folder}/transactions/"
    prefix = None
    for fname in os.listdir(directory):
        if fname.endswith('.txt'):
            txt_name = os.path.splitext(fname)[0]
            parts = txt_name.split('_')
            prefix = "_".join(parts[:-1])
            break
    if prefix is None:
        raise FileNotFoundError(f"Transaction dosyası bulunamadı: {directory}")
    full_path = os.path.join(directory, f"{prefix}_{num_intranetwork_nodes}.txt")
    return TransactionReader(full_path)


def load_virtual_requests():
    directory = f"{folder}/virtualrequests/"
    requests = []
    for fname in os.listdir(directory):
        if fname.endswith('.txt'):
            vr = VirtualNetworkRequest(os.path.join(directory, fname))
            if vr:
                requests.append(vr)
    if not requests:
        raise FileNotFoundError(f"Sanal ağ istek dosyası bulunamadı: {directory}")
    return requests


# -----------------------------------------------------------------------
# Sonuç yazdırma
# -----------------------------------------------------------------------

def print_comparison_table(results: list):
    """
    results: [(algoritma_adi, chromosome, fitness), ...]
    """
    print("\n" + "=" * 70)
    print("  KARŞILAŞTIRMA TABLOSU")
    print("=" * 70)
    print(f"  {'Algoritma':<30}  {'Fitness (Hop)':<15}  {'Kromozom'}")
    print("-" * 70)

    best_fitness = min(r[2] for r in results if r[2] != float('inf'))

    for name, chrom, fitness in results:
        marker = " ◄ EN İYİ" if fitness == best_fitness else ""
        chrom_str = str(chrom) if chrom is not None else "Çözüm bulunamadı"
        print(f"  {name:<30}  {fitness:<15}  {chrom_str}{marker}")
    print("=" * 70)


def yazYolDetaylari(yol_detaylari: list):
    print("\n--- YOL DETAYLARI ---")
    if not yol_detaylari:
        print("  (yol bulunamadı)")
        return

    toplam_hop = 0
    for link in yol_detaylari:
        print(f"\n  {link['sanal_baglanti']}")
        if 'inter_domain_yolu' in link:
            print(f"    Inter-domain yolu: {link['inter_domain_yolu']}")
        for seg in link['segmentler']:
            tip = seg['tip']
            if tip == 'domain gecisi':
                print(f"    [Geçiş] Domain {seg['kaynak_domain']} → Domain {seg['hedef_domain']}  (+1 hop)")
                toplam_hop += 1
            elif tip == 'HATA':
                print(f"    [HATA]  {seg['mesaj']}")
            else:
                yol_str = str(seg.get('yol', '?'))
                hop     = seg.get('hop', '?')
                domain  = seg.get('domain', '?')
                bas     = seg.get('baslangic_node', '?')
                bit     = seg.get('bitis_node', '?')
                bw      = seg.get('bw_talebi', '?')
                print(f"    [{tip}]  Domain {domain} | node {bas} → node {bit} | yol: {yol_str} | hop: {hop} | BW: {bw}")
                if isinstance(hop, int) and hop < 100000:
                    toplam_hop += hop

    print(f"\n  Toplam Hop: {toplam_hop}")


# -----------------------------------------------------------------------
# Ana fonksiyon
# -----------------------------------------------------------------------

def main():
    # --- Veri yükleme ---
    print("[1/4] Inter-network yükleniyor...")
    interNetwork = load_inter_network()
    num_domains = interNetwork.get_numberOfInterNodes()

    print(f"[2/4] İntra-network yükleniyor ({num_domains} domain)...")
    intraTopologies, intraNameList = load_intra_networks(num_domains)

    print("[3/4] Transaction yükleniyor...")
    allTransaction, edgeRouter = load_transaction()

    print("[4/4] Sanal ağ istekleri yükleniyor...")
    virtual_requests_list = load_virtual_requests()

    # --- Her sanal ağ isteği için çalıştır ---
    for vr_idx, virtualRequests in enumerate(virtual_requests_list):
        print(f"\n{'#' * 70}")
        print(f"  Sanal Ağ İsteği #{vr_idx + 1}")
        print(f"{'#' * 70}")

        results = []

        # ---- 1. Genetik Algoritma ----
        print("\n[GA] Genetik Algoritma çalışıyor...")
        ga_solver = GeneticDomainSolver(
            allTransaction, edgeRouter, interNetwork, intraTopologies, virtualRequests
        )
        ga_chrom, ga_fitness = ga_solver.run(
            population_size=GA_POPULATION,
            generations=GA_GENERATIONS,
            mutation_rate=GA_MUTATION,
            seed=GA_SEED,
        )
        results.append(("Genetik Algoritma", ga_chrom, ga_fitness))
        print(f"[GA] Fitness: {ga_fitness}  Kromozom: {ga_chrom}")

        # ---- 2. ACO ----
        print("\n[ACO] Karınca Kolonisi çalışıyor...")
        aco_solver = ACODomainSolver(
            allTransaction, edgeRouter, interNetwork, intraTopologies, virtualRequests
        )
        aco_chrom, aco_fitness = aco_solver.run(
            n_ants=ACO_ANTS,
            iterations=ACO_ITERATIONS,
            alpha=ACO_ALPHA,
            beta=ACO_BETA,
            rho=ACO_RHO,
            Q=ACO_Q,
            seed=ACO_SEED,
        )
        results.append(("ACO", aco_chrom, aco_fitness))
        print(f"[ACO] Fitness: {aco_fitness}  Kromozom: {aco_chrom}")

        # ---- 3. CPU Greedy ----
        greedy_paths = {}
        label_cpu = "Greedy (CPU)"
        print(f"\n[{label_cpu}] çalışıyor...")
        cpu_solver = GreedyCPUSolver(
            allTransaction, edgeRouter, interNetwork, intraTopologies, virtualRequests
        )
        cpu_chrom, cpu_fitness, cpu_paths = cpu_solver.solve()
        greedy_paths[label_cpu] = cpu_paths
        results.append((label_cpu, cpu_chrom, cpu_fitness))
        print(f"[{label_cpu}] Fitness: {cpu_fitness}  Kromozom: {cpu_chrom}")

        # ---- 4–6. Merkeziyetçilik tabanlı greedy ----
        for method in CENTRALITY_METHODS:
            label = f"Greedy ({method.capitalize()})"
            print(f"\n[{label}] çalışıyor...")
            c_solver = CentralityGreedySolver(
                allTransaction, edgeRouter, interNetwork, intraTopologies, virtualRequests,
                method=method,
            )
            # solve() → (chromosome, fitness, path_details)  — tek döngü, yol bulma dahil
            c_chrom, c_fitness, c_paths = c_solver.solve()
            greedy_paths[label] = c_paths
            results.append((label, c_chrom, c_fitness))
            print(f"[{label}] Fitness: {c_fitness}  Kromozom: {c_chrom}")

        # ---- Karşılaştırma tablosu ----
        print_comparison_table(results)

        # ---- Greedy yol detayları (her greedy için ayrı) ----
        for label, paths in greedy_paths.items():
            print(f"\n{'─' * 50}")
            print(f"  {label} — Yol Detayları")
            print(f"{'─' * 50}")
            yazYolDetaylari(paths)

        # ---- En iyi çözümün yol detayları (GA / ACO / Greedy fark etmez) ----
        best_name, best_chrom, best_fit = min(results, key=lambda r: r[2])
        print(f"\n{'═' * 50}")
        print(f"  En İyi Algoritma: {best_name}  (Fitness={best_fit})")
        print(f"{'═' * 50}")

        if best_chrom is not None:
            if best_name in greedy_paths:
                # Greedy'nin yolları zaten yukarıda yazdırıldı, tekrar etme
                pass
            else:
                # GA veya ACO: trace_solution ile yol detaylarını bul
                tracer = GeneticDomainSolver(
                    allTransaction, edgeRouter, interNetwork, intraTopologies, virtualRequests
                )
                yazYolDetaylari(tracer.trace_solution(best_chrom))

        # Kullanılan topoloji dosyaları
        print(f"\nKullanılan İntra Topolojiler ({len(intraNameList)} domain):")
        for idx, name in enumerate(intraNameList):
            print(f"  Domain {idx:>2}: {name}")


if __name__ == "__main__":
    main()
