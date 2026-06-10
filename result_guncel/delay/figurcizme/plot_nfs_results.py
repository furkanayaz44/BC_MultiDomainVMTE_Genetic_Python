"""
NFS Sonuçları – 12 Grafik Üretici (metrik-başına farklı çizim tipi)
====================================================================
Metrik → Çizim tipi eşlemesi:
    accept → heatmap (algoritma × x, renk = kabul yüzdesi)
    res    → gruplandırılmış bar (kaynak kullanımı)
    hops   → çizgi + güven bandı (mean ± std)
    delay  → box plot (kabul edilen istek dağılımı)

Üretilen çıktılar (PNG + PDF):
    fig_{VBW|VNode|ISP}_{accept|res|hops|delay}.{png,pdf}
    aggregated_{VBW|VNode|ISP}.xlsx  (doğrulama)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =============================================================================
# KONFİGÜRASYON
# =============================================================================

INPUT_DIR     = "inputs"
INPUT_PATTERN = "sonuclar_NFS_guncel_isp{isp}_3000req_delay.xlsx"
SHEET_NAME    = "Sonuclar"
OUTPUT_DIR    = "outputs"

ALL_ISPS         = [5, 6, 7, 8, 9, 10]
ISPS_FOR_VBW_VN  = [6, 7, 8]
VBW_VALUES       = [5, 10, 15, 20, 25]
VNODE_VALUES     = [5, 6, 7, 8, 9, 10]
ISP_AXIS_VALUES  = [5, 6, 7, 8, 9, 10]
ISP_VN_FILTER    = [6, 7, 8]
ISP_BW_FILTER    = [10, 15]

ALGORITHMS = {
    "GreedyCPU":   "GreedyCPU",
    "GreedyClose": "GreedyClose",
    "GA_CPU":      "GA_CPU",
    "GA_QL":       "GA_QL",
}
COLORS  = {"GreedyCPU": "#1f77b4", "GreedyClose": "#ff7f0e",
           "GA_CPU":    "#2ca02c", "GA_QL":       "#9467bd"}
MARKERS = {"GreedyCPU": "o", "GreedyClose": "s",
           "GA_CPU":    "^", "GA_QL":       "v"}

XLABEL_VBW   = "Sanal Bağlantı BW Artışı"
XLABEL_VNODE = "Sanal Düğüm Sayısı (VN)"
XLABEL_ISP   = "ISP Sayısı"

METRICS = {
    "accept": {"title": "İstek Kabul Oranı (%)",
               "ylabel": "Kabul Oranı (%)"},
    "res":    {"title": "Ortalama Kaynak Kullanımı (BW)\n(tüm algoritmaların ortak çözdüğü istekler)",
               "ylabel": "Ortalama Kaynak Kullanımı (BW)"},
    "hops":   {"title": "Kabul Edilen İsteklerde Ortalama Hop Sayısı",
               "ylabel": "Ortalama Hop Sayısı"},
    "delay":  {"title": "Kabul Edilen İsteklerde Gecikme Dağılımı",
               "ylabel": "Gecikme"},
}

SUBTITLE_VBW   = f"VBW Artışına Göre (ISP {'-'.join(map(str, ISPS_FOR_VBW_VN))} ortalaması)"
SUBTITLE_VNODE = f"VN Artışına Göre (ISP {'-'.join(map(str, ISPS_FOR_VBW_VN))} ortalaması)"
SUBTITLE_ISP   = f"VNode ∈ {ISP_VN_FILTER}, VBW ∈ {ISP_BW_FILTER}"

# --- Y-EKSENİ LİMİTLERİ ---
# Her metrik için (ymin, ymax) tuple ya da None (oto-ölçek).
# `accept` heatmap olduğu için renk skalası zaten 0-100; YLIMS uygulanmaz.
# NSF & USnet aynı y aralığını paylaşsın istiyorsanız bu sözlüğü doldurun
# ya da plot_combined_4x3.py'i SHARE_Y_AXIS=True ile çalıştırın
# (her iki veri setinden otomatik hesaplar).
YLIMS = {
    "accept": None,  # heatmap; göz ardı edilir
    "res":    None,
    "hops":   None,
    "delay":  None,
}

# --- Stil ---
FIG_SIZE     = (8, 5.5)
DPI          = 150
LINEWIDTH    = 2
MARKERSIZE   = 7
TITLE_FONT   = 12
LABEL_FONT   = 11
LEGEND_FONT  = 10
GRID_ALPHA   = 0.3
HEATMAP_CMAP = "RdYlGn"
BAND_ALPHA   = 0.18
BAR_WIDTH    = 0.16
BOX_WIDTH    = 0.14
SAVE_PNG     = True
SAVE_PDF     = True

# =============================================================================
# VERİ ANALİZİ  (Excel okuma & toplulaştırma — DEĞİŞTİRİLMEDİ)
# =============================================================================

def load_isp_file(isp):
    path = os.path.join(INPUT_DIR, INPUT_PATTERN.format(isp=isp))
    df = pd.read_excel(path, sheet_name=SHEET_NAME)
    for algo in ALGORITHMS:
        df[f"{algo}_acc"]   = pd.to_numeric(df[f"{algo}_BW"],        errors="coerce").notna()
        df[f"{algo}_BW_n"]  = pd.to_numeric(df[f"{algo}_BW"],        errors="coerce")
        df[f"{algo}_Hp_n"]  = pd.to_numeric(df[f"{algo}_NumofHops"], errors="coerce")
        df[f"{algo}_Dl_n"]  = pd.to_numeric(df[f"{algo}_Delay"],     errors="coerce")
    common = np.ones(len(df), dtype=bool)
    for algo in ALGORITHMS:
        common &= df[f"{algo}_acc"].values
    df["_common"] = common
    return df


def compute_metrics(df_subset):
    """Eski API — skalar değerler (Excel export için kullanılıyor)."""
    dc = df_subset[df_subset["_common"]]
    out = {}
    for algo in ALGORITHMS:
        acc_mask  = df_subset[f"{algo}_acc"]
        acc_rows  = df_subset[acc_mask]
        out[algo] = {
            "accept": 100.0 * acc_mask.sum() / len(df_subset) if len(df_subset) else np.nan,
            "res":    dc[f"{algo}_BW_n"].mean() if len(dc) else np.nan,
            "hops":   acc_rows[f"{algo}_Hp_n"].mean() if len(acc_rows) else np.nan,
            "delay":  acc_rows[f"{algo}_Dl_n"].mean() if len(acc_rows) else np.nan,
        }
    return out


def aggregate_over_x(df, group_col, x_values):
    agg = {a: {m: [] for m in METRICS} for a in ALGORITHMS}
    for x in x_values:
        sub = df[df[group_col] == x]
        vals = compute_metrics(sub)
        for a in ALGORITHMS:
            for m in METRICS:
                agg[a][m].append(vals[a][m])
    return agg


def aggregate_full(df, group_col, x_values):
    """Yeni — çizim için std ve ham örnekleri de toplar."""
    agg = {a: {"accept": [], "res": [],
               "hops": [], "hops_std": [],
               "delay_mean": [], "delay_samples": []} for a in ALGORITHMS}
    for x in x_values:
        sub = df[df[group_col] == x]
        dc  = sub[sub["_common"]]
        for a in ALGORITHMS:
            acc_mask = sub[f"{a}_acc"]
            acc_rows = sub[acc_mask]
            agg[a]["accept"].append(
                100.0 * acc_mask.sum() / len(sub) if len(sub) else np.nan)
            agg[a]["res"].append(
                dc[f"{a}_BW_n"].mean() if len(dc) else np.nan)
            hops = acc_rows[f"{a}_Hp_n"].dropna()
            agg[a]["hops"].append(hops.mean() if len(hops) else np.nan)
            agg[a]["hops_std"].append(hops.std() if len(hops) > 1 else 0.0)
            dly = acc_rows[f"{a}_Dl_n"].dropna().values
            agg[a]["delay_mean"].append(dly.mean() if len(dly) else np.nan)
            agg[a]["delay_samples"].append(dly)
    return agg


def export_aggregate_xlsx(agg, x_values, x_label_col, out_xlsx_name):
    path = os.path.join(OUTPUT_DIR, out_xlsx_name)
    with pd.ExcelWriter(path) as w:
        for m in METRICS:
            rows = []
            for a in ALGORITHMS:
                for i, x in enumerate(x_values):
                    rows.append({"Algoritma": a, x_label_col: x, "Değer": agg[a][m][i]})
            pd.DataFrame(rows).to_excel(w, sheet_name=m, index=False)


# =============================================================================
# ÇİZİM FONKSİYONLARI (metrik başına; verilen ax üzerine çizer)
# =============================================================================

def draw_accept_heatmap(ax, agg, x_values, xlabel, *, add_colorbar=True):
    mat = np.array([agg[a]["accept"] for a in ALGORITHMS])
    # YLIMS["accept"] verilmişse renk skalasının min/max'ı için kullan.
    if YLIMS.get("accept") is not None:
        vmin, vmax = YLIMS["accept"]
    else:
        vmin, vmax = 0, 100
    im = ax.imshow(mat, aspect="auto", cmap=HEATMAP_CMAP, vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(x_values))); ax.set_xticklabels(x_values)
    ax.set_yticks(range(len(ALGORITHMS)))
    ax.set_yticklabels([ALGORITHMS[a] for a in ALGORITHMS])
    ax.set_xlabel(xlabel, fontsize=LABEL_FONT)
    # Etiket rengi: hücre rengi açıksa siyah, koyuysa beyaz
    mid = (vmin + vmax) / 2
    span = max(vmax - vmin, 1e-9)
    for (i, j), v in np.ndenumerate(mat):
        if np.isnan(v): continue
        # normalize: 0=en kırmızı, 1=en yeşil; uç değerlerde beyaz yazı
        norm = (v - vmin) / span
        color = "white" if (norm < 0.25 or norm > 0.85) else "black"
        ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                fontsize=9, color=color)
    if add_colorbar:
        cb = ax.figure.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
        cb.set_label("Kabul Oranı (%)", fontsize=LABEL_FONT - 1)
    return im


def draw_resource_bars(ax, agg, x_values, xlabel):
    x = np.arange(len(x_values)); n = len(ALGORITHMS)
    for k, a in enumerate(ALGORITHMS):
        offset = (k - (n - 1) / 2) * BAR_WIDTH
        ax.bar(x + offset, agg[a]["res"], width=BAR_WIDTH,
               color=COLORS[a], label=ALGORITHMS[a],
               edgecolor="black", linewidth=0.3)
    ax.set_xticks(x); ax.set_xticklabels(x_values)
    ax.set_xlabel(xlabel, fontsize=LABEL_FONT)
    ax.set_ylabel(METRICS["res"]["ylabel"], fontsize=LABEL_FONT)
    ax.grid(True, axis="y", alpha=GRID_ALPHA); ax.set_axisbelow(True)


def draw_hops_confband(ax, agg, x_values, xlabel):
    xv = np.array(x_values, dtype=float)
    for a in ALGORITHMS:
        mean = np.array(agg[a]["hops"], dtype=float)
        std  = np.array(agg[a]["hops_std"], dtype=float)
        ax.fill_between(xv, mean - std, mean + std,
                        color=COLORS[a], alpha=BAND_ALPHA, linewidth=0)
        ax.plot(xv, mean, color=COLORS[a], marker=MARKERS[a],
                linewidth=LINEWIDTH, markersize=MARKERSIZE,
                label=ALGORITHMS[a])
    ax.set_xticks(x_values)
    ax.set_xlabel(xlabel, fontsize=LABEL_FONT)
    ax.set_ylabel(METRICS["hops"]["ylabel"], fontsize=LABEL_FONT)
    ax.grid(True, alpha=GRID_ALPHA); ax.set_axisbelow(True)


def draw_delay_box(ax, agg, x_values, xlabel):
    x = np.arange(len(x_values)); n = len(ALGORITHMS)
    for k, a in enumerate(ALGORITHMS):
        offset = (k - (n - 1) / 2) * BOX_WIDTH
        positions = x + offset
        data = agg[a]["delay_samples"]
        safe = [d if len(d) else np.array([np.nan]) for d in data]
        ax.boxplot(
            safe, positions=positions, widths=BOX_WIDTH * 0.85,
            patch_artist=True, showfliers=False,
            boxprops=dict(facecolor=COLORS[a], alpha=0.75, linewidth=0.5),
            medianprops=dict(color="black", linewidth=1.2),
            whiskerprops=dict(linewidth=0.6),
            capprops=dict(linewidth=0.6),
        )
        means = [d.mean() if len(d) else np.nan for d in data]
        ax.scatter(positions, means, marker="D", s=14,
                   color="white", edgecolor="black", linewidth=0.6, zorder=5)
    ax.set_xticks(x); ax.set_xticklabels(x_values)
    ax.set_xlim(-0.5, len(x_values) - 0.5)
    ax.set_xlabel(xlabel, fontsize=LABEL_FONT)
    ax.set_ylabel(METRICS["delay"]["ylabel"], fontsize=LABEL_FONT)
    ax.grid(True, axis="y", alpha=GRID_ALPHA); ax.set_axisbelow(True)


DRAW_FUNCS = {
    "accept": draw_accept_heatmap,
    "res":    draw_resource_bars,
    "hops":   draw_hops_confband,
    "delay":  draw_delay_box,
}


def make_legend_handles(metric):
    if metric == "delay":
        h = [plt.Rectangle((0, 0), 1, 1, facecolor=COLORS[a], alpha=0.75,
                           edgecolor="black", linewidth=0.5,
                           label=ALGORITHMS[a]) for a in ALGORITHMS]
        h.append(plt.Line2D([0], [0], marker="D", color="black",
                            markerfacecolor="white", markersize=7,
                            linewidth=0, label="Ortalama"))
        return h
    if metric == "accept":
        return None
    return [plt.Line2D([0], [0], color=COLORS[a], marker=MARKERS[a],
                       linewidth=LINEWIDTH, markersize=MARKERSIZE,
                       label=ALGORITHMS[a]) for a in ALGORITHMS]


def plot_individual(metric, agg, x_values, xlabel, subtitle, out_basename):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    DRAW_FUNCS[metric](ax, agg, x_values, xlabel)
    ax.set_title(f"{METRICS[metric]['title']}\n({subtitle})", fontsize=TITLE_FONT)
    # YLIMS uygulaması (accept heatmap için anlamsız)
    if metric != "accept" and YLIMS.get(metric) is not None:
        ax.set_ylim(YLIMS[metric])
    handles = make_legend_handles(metric)
    if handles is not None:
        ax.legend(handles=handles, loc="best", fontsize=LEGEND_FONT)
    fig.tight_layout()
    if SAVE_PNG:
        fig.savefig(os.path.join(OUTPUT_DIR, out_basename + ".png"),
                    dpi=DPI, bbox_inches="tight")
    if SAVE_PDF:
        fig.savefig(os.path.join(OUTPUT_DIR, out_basename + ".pdf"),
                    bbox_inches="tight")
    plt.close(fig)


def compute_shared_ylims(aggs_list, pad=0.05):
    """
    Verilen tüm aggregate sözlüklerinden her metrik için ortak (ymin, ymax) döndürür.
    `aggs_list`: aggregate_full çıktı sözlüklerinin listesi (her biri {axis_key: agg}).
    """
    out = {"accept": None}  # accept aralığı aşağıda doldurulur
    # accept (yüzde) — heatmap renk skalası için
    accept_vals = []
    for aggs in aggs_list:
        for axis_key, agg in aggs.items():
            for a in ALGORITHMS:
                accept_vals.extend([v for v in agg[a]["accept"] if v == v])
    if accept_vals:
        # Sınırları biraz yuvarla ki colorbar tick'leri daha okunaklı olsun
        amin = max(0, np.floor(min(accept_vals) / 5) * 5)
        amax = min(100, np.ceil(max(accept_vals) / 5) * 5)
        out["accept"] = (amin, amax)
    # res
    vals = []
    for aggs in aggs_list:
        for axis_key, agg in aggs.items():
            for a in ALGORITHMS:
                vals.extend([v for v in agg[a]["res"] if v == v])  # NaN dışla
    out["res"] = (0, max(vals) * (1 + pad)) if vals else None
    # hops (mean ± std)
    lo_vals, hi_vals = [], []
    for aggs in aggs_list:
        for axis_key, agg in aggs.items():
            for a in ALGORITHMS:
                mean = np.array(agg[a]["hops"], dtype=float)
                std  = np.array(agg[a]["hops_std"], dtype=float)
                lo = mean - std; hi = mean + std
                lo_vals.extend([v for v in lo if v == v])
                hi_vals.extend([v for v in hi if v == v])
    if hi_vals:
        out["hops"] = (max(0, min(lo_vals) * (1 - pad) if min(lo_vals) > 0 else 0),
                       max(hi_vals) * (1 + pad))
    # delay (örneklerin 1-99 yüzdelik dilimini esas al; box-plot whisker'ları bu civar)
    all_samples = []
    for aggs in aggs_list:
        for axis_key, agg in aggs.items():
            for a in ALGORITHMS:
                for arr in agg[a]["delay_samples"]:
                    if len(arr):
                        all_samples.append(arr)
    if all_samples:
        flat = np.concatenate(all_samples)
        lo, hi = np.percentile(flat, [1, 99])
        out["delay"] = (max(0, lo * (1 - pad)), hi * (1 + pad))
    return out


# =============================================================================
# ANA AKIŞ
# =============================================================================

def build_aggregates():
    frames = []
    for isp in ISPS_FOR_VBW_VN:
        d = load_isp_file(isp); d["ISP"] = isp
        frames.append(d)
    df_pool = pd.concat(frames, ignore_index=True)
    aggs = {
        "VBW":   aggregate_full(df_pool, "VBW",   VBW_VALUES),
        "VNode": aggregate_full(df_pool, "VNode", VNODE_VALUES),
    }
    rows = []
    for isp in ISP_AXIS_VALUES:
        d = load_isp_file(isp); d["ISP"] = isp
        d = d[d["VNode"].isin(ISP_VN_FILTER) & d["VBW"].isin(ISP_BW_FILTER)]
        rows.append(d)
    df_isp = pd.concat(rows, ignore_index=True)
    aggs["ISP"] = aggregate_full(df_isp, "ISP", ISP_AXIS_VALUES)
    return aggs, df_pool, df_isp


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    aggs, df_pool, df_isp = build_aggregates()

    axis_specs = [
        ("VBW",   VBW_VALUES,      XLABEL_VBW,   SUBTITLE_VBW),
        ("VNode", VNODE_VALUES,    XLABEL_VNODE, SUBTITLE_VNODE),
        ("ISP",   ISP_AXIS_VALUES, XLABEL_ISP,   SUBTITLE_ISP),
    ]
    for key, vals, xlab, sub in axis_specs:
        for metric in METRICS:
            plot_individual(metric, aggs[key], vals, xlab, sub,
                            out_basename=f"fig_{key}_{metric}")

    # Doğrulama xlsx'leri
    agg_vbw_simple = aggregate_over_x(df_pool, "VBW",   VBW_VALUES)
    agg_vn_simple  = aggregate_over_x(df_pool, "VNode", VNODE_VALUES)
    agg_isp_simple = aggregate_over_x(df_isp,  "ISP",   ISP_AXIS_VALUES)
    export_aggregate_xlsx(agg_vbw_simple, VBW_VALUES,      "VBW",   "aggregated_VBW.xlsx")
    export_aggregate_xlsx(agg_vn_simple,  VNODE_VALUES,    "VNode", "aggregated_VNode.xlsx")
    export_aggregate_xlsx(agg_isp_simple, ISP_AXIS_VALUES, "ISP",   "aggregated_ISP.xlsx")

    print(f"✓ Tüm grafikler '{OUTPUT_DIR}' dizinine kaydedildi.")


if __name__ == "__main__":
    main()
