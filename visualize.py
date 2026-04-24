"""
visualize.py — VNE çözüm görselleştirme modülü
Kullanım: main_v4.py'den visualize_solution() çağrılır.
"""

import math
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.animation as animation
import networkx as nx


# -----------------------------------------------------------------------
# Renk paleti (her sanal bağlantıya farklı renk)
# -----------------------------------------------------------------------
PALETTE = [
    '#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4',
    '#42d4f4', '#f032e6', '#bfef45', '#469990', '#9A6324',
    '#800000', '#aaffc3', '#000075', '#dcbeff', '#808000',
]


# -----------------------------------------------------------------------
# Yardımcı: yerleşim hesaplama
# -----------------------------------------------------------------------

def _domain_centers(num_domains, grid_cols=None, h_spacing=5.5, v_spacing=5.5):
    """Her domain'in merkez (x, y) koordinatını döndürür."""
    if grid_cols is None:
        grid_cols = math.ceil(math.sqrt(num_domains))
    centers = {}
    for d in range(num_domains):
        row = d // grid_cols
        col = d % grid_cols
        centers[d] = (col * h_spacing, -row * v_spacing)
    return centers


def _node_positions(num_nodes, center, radius=1.3):
    """Domain merkezi etrafında dairesel node pozisyonları."""
    cx, cy = center
    pos = {}
    for i in range(num_nodes):
        angle = 2 * math.pi * i / max(num_nodes, 1) - math.pi / 2
        pos[i] = (cx + radius * math.cos(angle),
                  cy + radius * math.sin(angle))
    return pos


def _compute_all_positions(solver, grid_cols=None):
    """
    Tüm (domain, local_node) çiftleri için (x, y) pozisyon sözlüğü döndürür.
    Ayrıca domain merkezlerini döndürür.
    """
    num_d = len(solver.intraNetworkGraphwithBWMatrix)
    centers = _domain_centers(num_d, grid_cols)
    pos = {}
    for d, G in enumerate(solver.intraNetworkGraphwithBWMatrix):
        node_pos = _node_positions(G.number_of_nodes(), centers[d])
        for n, xy in node_pos.items():
            pos[(d, n)] = xy
    return pos, centers


# -----------------------------------------------------------------------
# Yardımcı: yol segmentlerinden edge listesi çıkarma
# -----------------------------------------------------------------------

def _extract_solution_edges(path_details):
    """
    trace_solution() çıktısından her sanal bağlantı için fiziksel edge listesi üretir.
    Döner: [ [(u, v, tip), ...], ... ]   u/v = (domain_id, local_node_id)
    """
    result = []
    for link in path_details:
        segments = link.get('segmentler', [])
        link_edges = []

        for seg_idx, seg in enumerate(segments):
            tip = seg.get('tip', '')

            if tip == 'HATA':
                continue

            # Domain geçişi → önceki segment'in bitis_node ile sonraki baslangic_node
            if tip == 'domain gecisi':
                src_d = seg.get('kaynak_domain')
                dst_d = seg.get('hedef_domain')
                src_n = _prev_bitis_node(segments, seg_idx)
                dst_n = _next_baslangic_node(segments, seg_idx)
                if src_n is not None and dst_n is not None:
                    link_edges.append(((src_d, src_n), (dst_d, dst_n), 'inter'))
                continue

            # Intra segment
            domain = seg.get('domain')
            if domain is None:
                continue
            yol = seg.get('yol')

            if isinstance(yol, list) and yol:
                for i in range(len(yol) - 1):
                    link_edges.append(((domain, yol[i]), (domain, yol[i + 1]), 'intra'))
            elif isinstance(yol, str):
                try:
                    raw = [int(x.strip()) for x in yol.strip('[]').split(',')]
                    for i in range(len(raw) - 1):
                        n1, n2 = raw[i] % 1000, raw[i + 1] % 1000
                        link_edges.append(((domain, n1), (domain, n2), 'intra'))
                except (ValueError, AttributeError):
                    _fallback_edge(seg, domain, link_edges)
            else:
                _fallback_edge(seg, domain, link_edges)

        result.append(link_edges)
    return result


def _prev_bitis_node(segments, idx):
    for s in reversed(segments[:idx]):
        if s.get('tip', '') != 'domain gecisi' and 'bitis_node' in s:
            return s['bitis_node']
    return None


def _next_baslangic_node(segments, idx):
    for s in segments[idx + 1:]:
        if s.get('tip', '') != 'domain gecisi' and 'baslangic_node' in s:
            return s['baslangic_node']
    return None


def _fallback_edge(seg, domain, edge_list):
    src = seg.get('baslangic_node')
    dst = seg.get('bitis_node')
    if src is not None and dst is not None and src != dst:
        edge_list.append(((domain, src), (domain, dst), 'intra'))


# -----------------------------------------------------------------------
# Kullanılan linkleri ve BW tüketimlerini hesapla
# -----------------------------------------------------------------------

def _compute_link_usage(path_details):
    """
    path_details'ten her fiziksel linkin hangi sanal bağlantılar tarafından
    ve ne kadar BW ile kullanıldığını çıkarır.

    Döner:
        intra_usage : {(domain, min_n, max_n): [(link_idx, bw), ...]}
        inter_usage : {frozenset{(d1,n1),(d2,n2)}: [(link_idx, bw), ...]}
    """
    intra_usage = {}
    inter_usage = {}

    for link_idx, link in enumerate(path_details):
        bw = link.get('bw_talebi', 0) or 0
        segments = link.get('segmentler', [])

        for seg_idx, seg in enumerate(segments):
            tip = seg.get('tip', '')
            if tip == 'HATA':
                continue

            if tip == 'domain gecisi':
                src_d = seg.get('kaynak_domain')
                dst_d = seg.get('hedef_domain')
                src_n = _prev_bitis_node(segments, seg_idx)
                dst_n = _next_baslangic_node(segments, seg_idx)
                if src_n is not None and dst_n is not None:
                    key = frozenset({(src_d, src_n), (dst_d, dst_n)})
                    inter_usage.setdefault(key, []).append((link_idx, bw))
                continue

            domain = seg.get('domain')
            if domain is None:
                continue
            yol = seg.get('yol')

            edges = []
            if isinstance(yol, list) and yol:
                for i in range(len(yol) - 1):
                    edges.append((min(yol[i], yol[i+1]), max(yol[i], yol[i+1])))
            elif isinstance(yol, str):
                try:
                    raw = [int(x.strip()) for x in yol.strip('[]').split(',')]
                    for i in range(len(raw) - 1):
                        n1, n2 = raw[i] % 1000, raw[i+1] % 1000
                        edges.append((min(n1, n2), max(n1, n2)))
                except (ValueError, AttributeError):
                    src = seg.get('baslangic_node')
                    dst = seg.get('bitis_node')
                    if src is not None and dst is not None and src != dst:
                        edges.append((min(src, dst), max(src, dst)))
            else:
                src = seg.get('baslangic_node')
                dst = seg.get('bitis_node')
                if src is not None and dst is not None and src != dst:
                    edges.append((min(src, dst), max(src, dst)))

            for u, v in edges:
                key = (domain, u, v)
                intra_usage.setdefault(key, []).append((link_idx, bw))

    return intra_usage, inter_usage


def _draw_parallel_lines(ax, p0, p1, users, palette, lw, zorder, linestyle='-'):
    """
    Aynı fiziksel linki kullanan her sanal bağlantıyı paralel ofsetli renkli
    çizgi olarak çizer (birden fazla kullanıcı varsa üst üste binmez).
    """
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return
    px, py = -dy / length, dx / length   # dike birim vektör

    n = len(users)
    offsets = [(i - (n - 1) / 2) * 0.07 for i in range(n)]

    for (link_idx, _), offset in zip(users, offsets):
        color = palette[link_idx % len(palette)]
        ox, oy = px * offset, py * offset
        ax.plot(
            [x0 + ox, x1 + ox], [y0 + oy, y1 + oy],
            color=color, linewidth=lw, linestyle=linestyle,
            zorder=zorder, alpha=0.85, solid_capstyle='round'
        )


# -----------------------------------------------------------------------
# Statik ağ çizimi
# -----------------------------------------------------------------------

def _draw_static_network(ax, solver, pos, centers,
                         intra_usage=None, inter_usage=None):
    """Arka plan ağı çizer: domain kutuları, intra edge'ler, inter edge'ler, node'lar."""
    er_nodes = set()
    for er in solver.edgeRouter:
        er_nodes.add((er.edgeDomainIngress, er.edgeNodeIngress))
        er_nodes.add((er.edgeDomainEgress,  er.edgeNodeEgress))

    num_d = len(solver.intraNetworkGraphwithBWMatrix)

    # Domain arka plan kutuları
    for d in range(num_d):
        cx, cy = centers[d]
        rect = plt.Rectangle(
            (cx - 2.1, cy - 2.1), 4.2, 4.2,
            linewidth=1.2, edgecolor='#999999',
            facecolor='#f5f8ff', alpha=0.45, zorder=0
        )
        ax.add_patch(rect)
        ax.text(cx, cy + 2.35, f"ISP {d}", fontsize=7.5,
                ha='center', va='bottom', color='#444444',
                fontweight='bold', zorder=2)

    intra_usage  = intra_usage  or {}
    inter_usage  = inter_usage  or {}

    # Intra-domain edge'ler
    for d, G in enumerate(solver.intraNetworkGraphwithBWMatrix):
        for u, v, data in G.edges(data=True):
            p0, p1 = pos[(d, u)], pos[(d, v)]
            orig_bw = data.get('bw', 0)
            ukey = (d, min(u, v), max(u, v))
            users = intra_usage.get(ukey)

            if users:
                _draw_parallel_lines(ax, p0, p1, users, PALETTE,
                                     lw=1.8, zorder=2, linestyle='-')
                used_bw  = sum(bw for _, bw in users)
                remaining = orig_bw - used_bw
                label = f"{remaining} ({orig_bw})"
                lbl_color = '#333333'
                box_fc    = '#fffbe6'
            else:
                ax.plot([p0[0], p1[0]], [p0[1], p1[1]],
                        color='#bbbbbb', linewidth=0.9, zorder=1, alpha=0.8)
                label = str(int(orig_bw))
                lbl_color = '#666666'
                box_fc    = 'white'

            mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            ax.text(mx, my, label, fontsize=5, ha='center', va='center',
                    color=lbl_color, zorder=4,
                    bbox=dict(boxstyle='round,pad=0.1', fc=box_fc, ec='none', alpha=0.8))

    # Edge router bağlantıları (inter-domain)
    drawn_er = set()
    for er in solver.edgeRouter:
        nkey = ((er.edgeDomainIngress, er.edgeNodeIngress),
                (er.edgeDomainEgress,  er.edgeNodeEgress))
        if nkey in drawn_er:
            continue
        drawn_er.add(nkey)
        u = (er.edgeDomainIngress, er.edgeNodeIngress)
        v = (er.edgeDomainEgress,  er.edgeNodeEgress)
        if u not in pos or v not in pos:
            continue
        p0, p1 = pos[u], pos[v]
        orig_bw = er.minBandwidth
        ikey = frozenset({(er.edgeDomainIngress, er.edgeNodeIngress),
                          (er.edgeDomainEgress,  er.edgeNodeEgress)})
        users = inter_usage.get(ikey)

        if users:
            _draw_parallel_lines(ax, p0, p1, users, PALETTE,
                                 lw=1.5, zorder=2, linestyle='--')
            used_bw   = sum(bw for _, bw in users)
            remaining = orig_bw - used_bw
            label     = f"{remaining} ({orig_bw}) (ER)"
            lbl_color = '#333333'
            box_fc    = '#fffbe6'
        else:
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]],
                    color='#5588bb', linewidth=1.0,
                    linestyle='--', zorder=2, alpha=0.5)
            label     = f"{int(orig_bw)} (ER)"
            lbl_color = '#336699'
            box_fc    = '#e8f0ff'

        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        ax.text(mx, my, label, fontsize=4.5, ha='center', va='center',
                color=lbl_color, zorder=4,
                bbox=dict(boxstyle='round,pad=0.08', fc=box_fc, ec='none', alpha=0.8))

    # Node daireleri (edge router → turuncu, normal → açık mavi)
    for d, G in enumerate(solver.intraNetworkGraphwithBWMatrix):
        cpu_vals = solver.cpu_value_all_intra_networks[d]
        for n in G.nodes():
            key = (d, n)
            if key not in pos:
                continue
            x, y = pos[key]
            is_er = key in er_nodes
            facecolor = '#ffaa66' if is_er else '#cce0f5'
            radius    = 0.28 if is_er else 0.22
            circle = plt.Circle((x, y), radius, facecolor=facecolor,
                                 edgecolor='#777777', linewidth=0.6, zorder=4)
            ax.add_patch(circle)
            cpu = cpu_vals[n] if n < len(cpu_vals) else '?'
            ax.text(x, y, str(int(cpu)), fontsize=5.5, ha='center', va='center',
                    color='#222222', fontweight='bold', zorder=5)
            ax.text(x, y + radius + 0.06, str(n), fontsize=4.5,
                    ha='center', va='bottom', color='#555555', zorder=5)


# -----------------------------------------------------------------------
# Çözüm yollarını çiz (statik)
# -----------------------------------------------------------------------

def _draw_solution_paths(ax, path_details, pos, palette):
    """Çözüm segmentlerini renkli çizgilerle çizer."""
    all_link_edges = _extract_solution_edges(path_details)
    patches = []

    for link_idx, (link, edges) in enumerate(zip(path_details, all_link_edges)):
        color = palette[link_idx % len(palette)]
        label = link.get('sanal_baglanti', f'VLink {link_idx}')
        patches.append(mpatches.Patch(color=color, label=label))

        for u, v, etype in edges:
            if u not in pos or v not in pos:
                continue
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            lw = 2.8 if etype == 'intra' else 2.2
            ls = '-' if etype == 'intra' else '-.'
            ax.annotate(
                '', xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(
                    arrowstyle='->', color=color,
                    lw=lw, linestyle=ls,
                    connectionstyle='arc3,rad=0.05'
                ),
                zorder=8
            )

    return patches


# -----------------------------------------------------------------------
# Atanan node'ları vurgula
# -----------------------------------------------------------------------

def _highlight_assigned_nodes(ax, best_chrom, pos, palette, solver):
    """Kromozomda atanan node'ları renkli daire ile vurgular."""
    if not best_chrom:
        return
    for gene_idx, gene in enumerate(best_chrom):
        parts = gene.split('-')
        d, n = int(parts[0]), int(parts[1])
        key = (d, n)
        if key not in pos:
            continue
        x, y = pos[key]
        color = palette[gene_idx % len(palette)]
        circle = plt.Circle((x, y), 0.35, facecolor=color,
                              edgecolor='white', linewidth=1.2, zorder=6, alpha=0.9)
        ax.add_patch(circle)
        cpu = solver.cpu_value_all_intra_networks[d][n] if n < len(solver.cpu_value_all_intra_networks[d]) else '?'
        ax.text(x, y, str(int(cpu)), fontsize=6, ha='center', va='center',
                color='white', fontweight='bold', zorder=7)
        ax.text(x, y - 0.47, f"VN{gene_idx}", fontsize=5, ha='center', va='top',
                color=color, fontweight='bold', zorder=7)


# -----------------------------------------------------------------------
# Animasyonlu görselleştirme
# -----------------------------------------------------------------------

def _animate_solution(fig, ax, path_details, pos, palette):
    """
    Her frame'de bir sonraki segment'i açar.
    Döner: FuncAnimation nesnesi (plt.show() öncesinde tutulmalı).
    """
    all_link_edges = _extract_solution_edges(path_details)

    # Tüm (renk, u, v, etype) adımlarını düz listeye çevir
    steps = []
    for link_idx, (link, edges) in enumerate(zip(path_details, all_link_edges)):
        color = palette[link_idx % len(palette)]
        for edge in edges:
            steps.append((color, edge[0], edge[1], edge[2]))

    artists = []

    def _frame(frame_no):
        if frame_no >= len(steps):
            return artists
        color, u, v, etype = steps[frame_no]
        if u not in pos or v not in pos:
            return artists
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        lw = 2.8 if etype == 'intra' else 2.2
        ann = ax.annotate(
            '', xy=(x1, y1), xytext=(x0, y0),
            arrowprops=dict(
                arrowstyle='->', color=color, lw=lw,
                connectionstyle='arc3,rad=0.05'
            ),
            zorder=8, animated=True
        )
        artists.append(ann)
        return artists

    anim = animation.FuncAnimation(
        fig, _frame,
        frames=len(steps) + 5,   # +5 boş frame → son durum görünür kalır
        interval=600,
        blit=False,
        repeat=False
    )
    return anim


# -----------------------------------------------------------------------
# Ana giriş noktası
# -----------------------------------------------------------------------

def visualize_solution(solver, best_chrom, path_details,
                       vr_idx: int = 0,
                       method_label: str = "GA Rank",
                       animate: bool = True,
                       grid_cols: int = None,
                       save_path: str = None):
    """
    VNE çözümünü görselleştirir.

    Parametreler
    ------------
    solver        : GeneticDomainSolver (veya alt sınıf) nesnesi
    best_chrom    : ['d-n', ...] formatında en iyi kromozom
    path_details  : solver.trace_solution(best_chrom) çıktısı
    vr_idx        : Sanal ağ isteği sırası (başlık için)
    method_label  : Algoritma adı (başlık için)
    animate       : True → animasyonlu yol açılımı, False → statik
    grid_cols     : Domain grid sütun sayısı (None → otomatik)
    save_path     : Kayıt yolu (ör. 'vne_vr1.png'); None → yalnızca göster
    """
    pos, centers = _compute_all_positions(solver, grid_cols)

    fig, ax = plt.subplots(figsize=(22, 16))
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(
        f"VNE Çözüm Haritası  —  VR #{vr_idx + 1}  |  {method_label}\n"
        f"Düğümlerde CPU değerleri • Kenarlarda BW değerleri • "
        f"Turuncu: Edge Router • Renkli: Çözüm Yolları",
        fontsize=11, fontweight='bold', pad=14
    )

    intra_usage, inter_usage = (
        _compute_link_usage(path_details) if path_details else ({}, {})
    )
    _draw_static_network(ax, solver, pos, centers, intra_usage, inter_usage)

    anim_obj = None
    legend_patches = []

    if path_details and best_chrom:
        _highlight_assigned_nodes(ax, best_chrom, pos, PALETTE, solver)
        if animate:
            anim_obj = _animate_solution(fig, ax, path_details, pos, PALETTE)
        else:
            legend_patches = _draw_solution_paths(ax, path_details, pos, PALETTE)

    # Legend (sanal bağlantılar)
    if legend_patches:
        ax.legend(
            handles=legend_patches, loc='lower right',
            fontsize=7, title='Sanal Bağlantılar', title_fontsize=8,
            framealpha=0.85
        )

    # Bilgi kutusu
    if best_chrom:
        info = f"Kromozom: {best_chrom}"
        fig.text(0.01, 0.01, info, fontsize=6, color='#444444',
                 va='bottom', wrap=True)

    plt.tight_layout(rect=[0, 0.02, 1, 1])

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  [Görselleştirme kaydedildi: {save_path}]")

    plt.show()

    # FuncAnimation nesnesini tutmak için döndür
    return anim_obj
