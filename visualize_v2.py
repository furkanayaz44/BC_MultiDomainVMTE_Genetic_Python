"""
visualize_v2.py — VNE görselleştirme (statik, PNG)

Doğrudan çalıştır:
    python visualize_v2.py

Üretilen dosyalar:
    vne_vnr_<istek>.png              — sanal ağ isteği topolojisi + aday domain tablosu
    vne_<istek>_greedy_cpu.png       — Greedy CPU çözüm haritası + atama tablosu
    vne_<istek>_greedy_closeness.png — Greedy Closeness çözüm haritası + atama tablosu
    vne_<istek>_ga_qlearning.png     — Genetik Q-Learning çözüm haritası + atama tablosu
    vne_<istek>_ga_rank.png          — Genetik Rank çözüm haritası + atama tablosu
"""

import math
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import networkx as nx


PALETTE = [
    '#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4',
    '#42d4f4', '#f032e6', '#bfef45', '#469990', '#9A6324',
    '#800000', '#aaffc3', '#000075', '#dcbeff', '#808000',
]


# -----------------------------------------------------------------------
# Renk yardımcısı
# -----------------------------------------------------------------------

def _lighten(hex_color, factor=0.65):
    """Hex rengi açık tona çevirir (factor: 0=orijinal, 1=beyaz)."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f'#{r:02x}{g:02x}{b:02x}'


# -----------------------------------------------------------------------
# Fiziksel ağ yerleşim hesaplama
# -----------------------------------------------------------------------

def _domain_centers(num_domains, grid_cols=None, h_spacing=5.5, v_spacing=5.5):
    if grid_cols is None:
        grid_cols = math.ceil(math.sqrt(num_domains))
    centers = {}
    for d in range(num_domains):
        row = d // grid_cols
        col = d % grid_cols
        centers[d] = (col * h_spacing, -row * v_spacing)
    return centers


def _node_positions(num_nodes, center, radius=1.3):
    cx, cy = center
    pos = {}
    for i in range(num_nodes):
        angle = 2 * math.pi * i / max(num_nodes, 1) - math.pi / 2
        pos[i] = (cx + radius * math.cos(angle),
                  cy + radius * math.sin(angle))
    return pos


def _compute_all_positions(solver, grid_cols=None):
    num_d = len(solver.intraNetworkGraphwithBWMatrix)
    centers = _domain_centers(num_d, grid_cols)
    pos = {}
    for d, G in enumerate(solver.intraNetworkGraphwithBWMatrix):
        node_pos = _node_positions(G.number_of_nodes(), centers[d])
        for n, xy in node_pos.items():
            pos[(d, n)] = xy
    return pos, centers


# -----------------------------------------------------------------------
# Çözüm yolu yardımcıları
# -----------------------------------------------------------------------

def _extract_solution_edges(path_details):
    result = []
    for link in path_details:
        segments = link.get('segmentler', [])
        link_edges = []
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
                    link_edges.append(((src_d, src_n), (dst_d, dst_n), 'inter'))
                continue
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
# Link kullanım hesabı (BW etiketleri için)
# -----------------------------------------------------------------------

def _compute_link_usage(path_details):
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
                intra_usage.setdefault((domain, u, v), []).append((link_idx, bw))
    return intra_usage, inter_usage


# -----------------------------------------------------------------------
# Fiziksel ağ çizimi
# -----------------------------------------------------------------------

def _draw_static_network(ax, solver, pos, centers,
                         intra_usage=None, inter_usage=None):
    er_nodes = set()
    for er in solver.edgeRouter:
        er_nodes.add((er.edgeDomainIngress, er.edgeNodeIngress))
        er_nodes.add((er.edgeDomainEgress,  er.edgeNodeEgress))

    num_d = len(solver.intraNetworkGraphwithBWMatrix)
    intra_usage = intra_usage or {}
    inter_usage = inter_usage or {}

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

    for d, G in enumerate(solver.intraNetworkGraphwithBWMatrix):
        for u, v, data in G.edges(data=True):
            p0, p1 = pos[(d, u)], pos[(d, v)]
            orig_bw = data.get('bw', 0)
            ukey    = (d, min(u, v), max(u, v))
            users   = intra_usage.get(ukey)
            if users:
                ax.plot([p0[0], p1[0]], [p0[1], p1[1]],
                        color='#888888', linewidth=1.8, zorder=1, alpha=0.9)
                used_bw   = sum(bw for _, bw in users)
                label     = f"{orig_bw - used_bw} ({orig_bw})"
                lbl_color = '#333333'
                box_fc    = '#fffbe6'
            else:
                ax.plot([p0[0], p1[0]], [p0[1], p1[1]],
                        color='#cccccc', linewidth=0.9, zorder=1, alpha=0.7)
                label     = str(int(orig_bw))
                lbl_color = '#888888'
                box_fc    = 'white'
            mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            ax.text(mx, my, label, fontsize=5, ha='center', va='center',
                    color=lbl_color, zorder=4,
                    bbox=dict(boxstyle='round,pad=0.1', fc=box_fc, ec='none', alpha=0.8))

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
        ikey    = frozenset({(er.edgeDomainIngress, er.edgeNodeIngress),
                             (er.edgeDomainEgress,  er.edgeNodeEgress)})
        users   = inter_usage.get(ikey)
        if users:
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]],
                    color='#777777', linewidth=1.8, linestyle='--', zorder=2, alpha=0.9)
            used_bw   = sum(bw for _, bw in users)
            label     = f"{orig_bw - used_bw} ({orig_bw}) ER"
            lbl_color = '#333333'
            box_fc    = '#fffbe6'
        else:
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]],
                    color='#aabbdd', linewidth=1.0, linestyle='--', zorder=2, alpha=0.5)
            label     = f"{int(orig_bw)} ER"
            lbl_color = '#336699'
            box_fc    = '#e8f0ff'
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        ax.text(mx, my, label, fontsize=4.5, ha='center', va='center',
                color=lbl_color, zorder=4,
                bbox=dict(boxstyle='round,pad=0.08', fc=box_fc, ec='none', alpha=0.8))

    for d, G in enumerate(solver.intraNetworkGraphwithBWMatrix):
        cpu_vals = solver.cpu_value_all_intra_networks[d]
        for n in G.nodes():
            key = (d, n)
            if key not in pos:
                continue
            x, y = pos[key]
            is_er     = key in er_nodes
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


def _draw_solution_paths(ax, path_details, pos, palette):
    all_link_edges = _extract_solution_edges(path_details)
    patches = []
    for link_idx, (link, edges) in enumerate(zip(path_details, all_link_edges)):
        color = palette[link_idx % len(palette)]
        label = link.get('sanal_baglanti', f'VLink {link_idx}')
        patches.append(mpatches.Patch(color=color, label=label))
        for u, v, etype in edges:
            if u not in pos or v not in pos:
                continue
            lw = 2.8 if etype == 'intra' else 2.2
            ls = '-' if etype == 'intra' else '-.'
            ax.annotate(
                '', xy=pos[v], xytext=pos[u],
                arrowprops=dict(arrowstyle='->', color=color, lw=lw, linestyle=ls,
                                connectionstyle='arc3,rad=0.05'),
                zorder=8
            )
    return patches


def _highlight_assigned_nodes(ax, best_chrom, pos, palette, solver):
    for gene_idx, gene in enumerate(best_chrom):
        d, n = int(gene.split('-')[0]), int(gene.split('-')[1])
        key = (d, n)
        if key not in pos:
            continue
        x, y = pos[key]
        color = palette[gene_idx % len(palette)]
        ax.add_patch(plt.Circle((x, y), 0.38, facecolor=color,
                                edgecolor='white', linewidth=1.5, zorder=6, alpha=0.92))
        cpu = solver.cpu_value_all_intra_networks[d][n] \
              if n < len(solver.cpu_value_all_intra_networks[d]) else '?'
        ax.text(x, y, str(int(cpu)), fontsize=6.5, ha='center', va='center',
                color='white', fontweight='bold', zorder=7)
        ax.text(x, y - 0.52, f"VN{gene_idx}", fontsize=5.5, ha='center', va='top',
                color=color, fontweight='bold', zorder=7)


# -----------------------------------------------------------------------
# Atama tablosu
# -----------------------------------------------------------------------

def _draw_assignment_table(ax, best_chrom, vr, solver):
    """Atama sonuçlarını renkli tablo olarak çizer."""
    cpu_demands = [row[0] for row in vr.cpu_ram_demand] if vr else []
    cands       = vr.candidate_domains if vr else []

    col_labels  = ['VN#', 'CPU\nTalep', 'Aday\nISP 1', 'Aday\nISP 2',
                   'Atanan\nISP', 'Atanan\nNode', 'CPU\nKapasite', 'Durum']
    cell_text   = []
    cell_colors = []

    for i, gene in enumerate(best_chrom):
        d, n    = int(gene.split('-')[0]), int(gene.split('-')[1])
        cpu_cap = int(solver.cpu_value_all_intra_networks[d][n]) \
                  if n < len(solver.cpu_value_all_intra_networks[d]) else -1
        cpu_dem = cpu_demands[i] if i < len(cpu_demands) else -1
        d1      = cands[i][0] if i < len(cands) else '?'
        d2      = cands[i][1] if i < len(cands) else '?'
        ok      = cpu_cap >= cpu_dem >= 0

        status_txt   = '✓ OK'    if ok else '✗ Hata'
        status_color = '#c8f7c5' if ok else '#f7c5c5'
        base_color   = _lighten(PALETTE[i % len(PALETTE)], 0.72)
        vn_color     = _lighten(PALETTE[i % len(PALETTE)], 0.45)
        assign_color = '#fff9c4'   # atanan ISP + node sarı vurgu

        cell_text.append([
            f"VN{i}",
            str(cpu_dem),
            f"ISP {d1}",
            f"ISP {d2}",
            f"ISP {d}",
            str(n),
            str(cpu_cap),
            status_txt,
        ])
        cell_colors.append([
            vn_color,
            base_color, base_color, base_color,
            assign_color, assign_color,
            base_color,
            status_color,
        ])

    n_cols = len(col_labels)
    tbl = ax.table(
        cellText=cell_text,
        cellColours=cell_colors,
        colLabels=col_labels,
        loc='center',
        cellLoc='center',
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1.0, 1.9)

    for j in range(n_cols):
        tbl[(0, j)].set_facecolor('#2c3e50')
        tbl[(0, j)].set_text_props(color='white', fontweight='bold', fontsize=9)

    ax.set_title('  Sanal Düğüm Atamaları  (sarı = atanan ISP/node,  yeşil = CPU yeterli)',
                 fontsize=9, fontweight='bold', loc='left', pad=7, color='#222222')
    ax.axis('off')


# -----------------------------------------------------------------------
# Sanal ağ isteği (VNR) görselleştirmesi
# -----------------------------------------------------------------------

def draw_vnr(vr, vr_name="", save_path=None):
    """Sanal ağ isteğini topoloji + detay tablosu olarak çizer."""
    adj   = vr.adjacency_matrix
    bw_m  = vr.bandwidth_demand
    cpu   = [row[0] for row in vr.cpu_ram_demand]
    cands = vr.candidate_domains
    n_vn  = len(adj)

    G = nx.Graph()
    G.add_nodes_from(range(n_vn))
    for i in range(n_vn):
        for j in range(i + 1, n_vn):
            if adj[i][j]:
                G.add_edge(i, j, bw=bw_m[i][j])

    fig  = plt.figure(figsize=(20, 8))
    gs   = fig.add_gridspec(1, 2, width_ratios=[1.1, 1], wspace=0.22)
    ax_g = fig.add_subplot(gs[0])
    ax_t = fig.add_subplot(gs[1])

    # ---- Topoloji grafı ----
    pos_vn      = nx.spring_layout(G, seed=7)
    node_colors = [PALETTE[i % len(PALETTE)] for i in range(n_vn)]

    nx.draw_networkx_nodes(G, pos_vn, ax=ax_g, node_color=node_colors,
                           node_size=1600, alpha=0.93,
                           edgecolors='#333333', linewidths=1.5)
    nx.draw_networkx_labels(G, pos_vn,
                            labels={i: f"VN{i}" for i in range(n_vn)},
                            ax=ax_g, font_size=9,
                            font_color='white', font_weight='bold')
    nx.draw_networkx_edges(G, pos_vn, ax=ax_g,
                           width=2.2, edge_color='#555555', alpha=0.75)
    nx.draw_networkx_edge_labels(
        G, pos_vn,
        edge_labels={(i, j): f"BW:{d['bw']}" for i, j, d in G.edges(data=True)},
        ax=ax_g, font_size=8,
        bbox=dict(boxstyle='round,pad=0.2', fc='#ffffcc', ec='none', alpha=0.9)
    )
    # CPU etiketleri düğümün hemen altına
    for i, (x, y) in pos_vn.items():
        ax_g.text(x, y - 0.13, f"CPU:{cpu[i]}", fontsize=8, ha='center', va='top',
                  color='#111111', fontweight='bold',
                  bbox=dict(boxstyle='round,pad=0.18', fc='white',
                            ec=PALETTE[i % len(PALETTE)], linewidth=1.2, alpha=0.9))

    ax_g.set_title(f"Sanal Ağ Topolojisi  —  {n_vn} sanal düğüm",
                   fontsize=12, fontweight='bold', pad=10)
    ax_g.axis('off')

    # ---- Detay tablosu ----
    vn_links = {i: [] for i in range(n_vn)}
    for i in range(n_vn):
        for j in range(i + 1, n_vn):
            if adj[i][j]:
                vn_links[i].append(f"→VN{j}  (BW:{bw_m[i][j]})")
                vn_links[j].append(f"→VN{i}  (BW:{bw_m[i][j]})")

    col_labels  = ['VN#', 'CPU\nTalep', 'Aday\nISP 1', 'Aday\nISP 2', 'Bağlantılar']
    cell_text   = []
    cell_colors = []
    for i in range(n_vn):
        d1, d2    = cands[i][0], cands[i][1]
        links_str = '\n'.join(vn_links[i]) if vn_links[i] else '—'
        vn_color  = _lighten(PALETTE[i % len(PALETTE)], 0.42)
        base      = _lighten(PALETTE[i % len(PALETTE)], 0.70)
        cell_text.append([f"VN{i}", str(cpu[i]), f"ISP {d1}", f"ISP {d2}", links_str])
        cell_colors.append([vn_color, base, base, base, base])

    tbl = ax_t.table(
        cellText=cell_text,
        cellColours=cell_colors,
        colLabels=col_labels,
        loc='center',
        cellLoc='center',
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1.05, 2.1)

    for j in range(len(col_labels)):
        tbl[(0, j)].set_facecolor('#2c3e50')
        tbl[(0, j)].set_text_props(color='white', fontweight='bold', fontsize=9)

    ax_t.set_title('  Sanal Düğüm Detayları',
                   fontsize=11, fontweight='bold', loc='left', pad=8)
    ax_t.axis('off')

    fig.suptitle(f"Sanal Ağ İsteği (VNR)  |  {vr_name}",
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=180, bbox_inches='tight')
        print(f"  [PNG kaydedildi: {save_path}]")
    plt.close(fig)


# -----------------------------------------------------------------------
# Çözüm görselleştirmesi (ağ + atama tablosu)
# -----------------------------------------------------------------------

def visualize_solution(solver, best_chrom, path_details, vr=None,
                       vr_idx=0, method_label="Greedy", fitness=None,
                       grid_cols=None, save_path=None):
    """
    VNE çözümünü statik olarak görselleştirir.
    Üst panel: fiziksel ağ + çözüm yolları
    Alt panel: VN atama tablosu
    """
    pos, centers = _compute_all_positions(solver, grid_cols)

    fig = plt.figure(figsize=(22, 23))
    gs  = gridspec.GridSpec(2, 1, height_ratios=[3.2, 1], hspace=0.06)
    ax     = fig.add_subplot(gs[0])
    ax_tbl = fig.add_subplot(gs[1])

    ax.set_aspect('equal')
    ax.axis('off')
    fitness_str = f"  |  Fitness (toplam hop): {fitness}" if fitness is not None else ""
    ax.set_title(
        f"VNE Çözüm Haritası  —  {method_label}{fitness_str}\n"
        f"Düğümlerde CPU değerleri  •  Kenarlarda Kalan/Toplam BW  •  "
        f"Turuncu: Edge Router  •  Renkli oklar: Sanal Bağlantı Yolları",
        fontsize=11, fontweight='bold', pad=14
    )

    intra_usage, inter_usage = (
        _compute_link_usage(path_details) if path_details else ({}, {})
    )
    _draw_static_network(ax, solver, pos, centers, intra_usage, inter_usage)

    legend_patches = []
    if path_details and best_chrom:
        _highlight_assigned_nodes(ax, best_chrom, pos, PALETTE, solver)
        legend_patches = _draw_solution_paths(ax, path_details, pos, PALETTE)

    legend_items = [
        mpatches.Patch(facecolor='#ffaa66', edgecolor='#777777', label='Edge Router node'),
        mpatches.Patch(facecolor='#cce0f5', edgecolor='#777777', label='Normal node'),
        plt.Line2D([0], [0], color='#888888', lw=1.8, label='Kullanılan intra link'),
        plt.Line2D([0], [0], color='#cccccc', lw=0.9, label='Kullanılmayan intra link'),
        plt.Line2D([0], [0], color='#777777', lw=1.8, ls='--', label='Kullanılan ER link'),
        plt.Line2D([0], [0], color='#aabbdd', lw=1.0, ls='--', label='Kullanılmayan ER link'),
    ]
    ax.legend(
        handles=legend_items + legend_patches,
        loc='upper right', fontsize=7,
        title='Gösterim', title_fontsize=8, framealpha=0.9
    )

    # Atama tablosu
    if best_chrom and vr is not None:
        _draw_assignment_table(ax_tbl, best_chrom, vr, solver)
    else:
        ax_tbl.axis('off')
        ax_tbl.text(0.5, 0.5, 'Çözüm bulunamadı', ha='center', va='center',
                    fontsize=14, color='red', fontweight='bold')

    if save_path:
        plt.savefig(save_path, dpi=180, bbox_inches='tight')
        print(f"  [PNG kaydedildi: {save_path}]")
    plt.close(fig)


# -----------------------------------------------------------------------
# Ana blok: veri yükle → VNR çiz → 4 algoritma çöz ve görselleştir
# -----------------------------------------------------------------------

if __name__ == "__main__":
    HERE = os.path.dirname(os.path.abspath(__file__))

    from readFiles.InterNetworkReader import InterNetworkReader
    from readFiles.IntraNetworkReader import IntraNetworkReader
    from readFiles.TransactionReader import TransactionReader
    from readFiles.readVirtualNetwork import VirtualNetworkRequest
    from algorithm.centrality import GreedyCPUSolver, CentralityGreedySolver
    from algorithm.genetic import GeneticDomainSolver

    NETWORK = "guncel/NSFNET"
    FOLDER  = os.path.join(HERE, "topologies", NETWORK)
    N_NODES = 5
    VR_FILE = "virtual_10_10_15_15.txt"   # QL vs Rank farkının en belirgin olduğu istek

    GA_POP  = 100
    GA_GEN  = 50
    GA_MUT  = 0.1
    GA_SEED = 42

    # ---- Ortak veri yükleme ----
    inter_dir  = os.path.join(FOLDER, "internetwork")
    inter_file = next(f for f in os.listdir(inter_dir) if f.endswith('.txt'))
    interNetwork = InterNetworkReader(os.path.join(inter_dir, inter_file))
    NUM_DOMAINS  = interNetwork.get_numberOfInterNodes()
    print(f"[1] Inter-network: {inter_file}  |  {NUM_DOMAINS} domain")

    list_file = os.path.join(FOLDER, "intra_domain_used_list.txt")
    with open(list_file) as f:
        all_lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith('#')]
    selected    = [ln for ln in all_lines if ln.startswith(f"adjacency_{N_NODES}_")][:NUM_DOMAINS]
    intra_dir   = os.path.join(FOLDER, "intranetwork")
    intraTopologies = IntraNetworkReader.load_intra_topology(intra_dir, selected)
    print(f"[2] Intra-network: {N_NODES} node/ISP  |  {len(selected)} domain")

    trans_dir  = os.path.join(FOLDER, "transactions")
    trans_file = next(f for f in os.listdir(trans_dir) if f.endswith('.txt'))
    prefix_t   = "_".join(os.path.splitext(trans_file)[0].split('_')[:-1])
    allTransaction, edgeRouter = TransactionReader(
        os.path.join(trans_dir, f"{prefix_t}_{N_NODES}.txt")
    )
    print(f"[3] Transaction: {prefix_t}_{N_NODES}.txt")

    vr_path         = os.path.join(FOLDER, "virtualrequests", VR_FILE)
    virtualRequests = VirtualNetworkRequest(vr_path)
    vr_name         = os.path.splitext(VR_FILE)[0]
    print(f"[4] VR: {VR_FILE}\n")

    # ---- VNR çizimi ----
    print("[5] Sanal ağ isteği çiziliyor...")
    draw_vnr(
        virtualRequests,
        vr_name=VR_FILE,
        save_path=os.path.join(HERE, f"vne_vnr_{vr_name}.png"),
    )

    # ---- 4 algoritma ----
    ALGORITHMS = [
        {
            "label":  "Greedy CPU",
            "slug":   "greedy_cpu",
            "kind":   "greedy",
            "class":  GreedyCPUSolver,
            "kwargs": {},
        },
        {
            "label":  "Greedy Closeness",
            "slug":   "greedy_closeness",
            "kind":   "greedy",
            "class":  CentralityGreedySolver,
            "kwargs": {"method": "closeness"},
        },
        {
            "label":  "Genetik – Q-Learning",
            "slug":   "ga_qlearning",
            "kind":   "ga",
            "class":  GeneticDomainSolver,
            "kwargs": {"selection_mode": "qlearning"},
        },
        {
            "label":  "Genetik – Rank",
            "slug":   "ga_rank",
            "kind":   "ga",
            "class":  GeneticDomainSolver,
            "kwargs": {"selection_mode": "rank"},
        },
    ]

    for i, algo in enumerate(ALGORITHMS, start=6):
        print(f"[{i}] {algo['label']} çalışıyor...", end=" ", flush=True)

        solver = algo["class"](
            allTransaction, edgeRouter, interNetwork,
            intraTopologies, virtualRequests,
            **algo["kwargs"],
        )

        if algo["kind"] == "greedy":
            best_chrom, fitness, path_details = solver.solve()
        else:
            result = solver.run(
                population_size=GA_POP,
                generations=GA_GEN,
                mutation_rate=GA_MUT,
                seed=GA_SEED,
            )
            if result is None:
                best_chrom, fitness, path_details = None, None, []
            else:
                best_chrom, fitness = result
                path_details = solver.trace_solution(best_chrom) if best_chrom else []

        if best_chrom is None:
            print("çözüm YOK")
        else:
            print(f"fitness={fitness}  chrom={best_chrom}")

        visualize_solution(
            solver=solver,
            best_chrom=best_chrom,
            path_details=path_details,
            vr=virtualRequests,
            vr_idx=0,
            method_label=f"{algo['label']}  |  NSFNET  |  {N_NODES} node/ISP",
            fitness=fitness,
            save_path=os.path.join(HERE, f"vne_{vr_name}_{algo['slug']}.png"),
        )

    print("\nTamamlandı. 5 PNG dosyası kaydedildi.")
    print(f"  vne_vnr_{vr_name}.png")
    for algo in ALGORITHMS:
        print(f"  vne_{vr_name}_{algo['slug']}.png")
