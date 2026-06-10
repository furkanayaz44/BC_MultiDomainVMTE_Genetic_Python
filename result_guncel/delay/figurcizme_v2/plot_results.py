"""
NSF + USnet Sonuç Görselleştirici  (tek dosya)
================================================
Klasör yapısı:
    proje/
    ├── plot_results.py        ← bu dosya
    ├── inputs/                ← Excel dosyaları buraya
    │   ├── sonuclar_NFS_guncel_isp5_3000req_delay.xlsx
    │   ├── ...  (isp 6..10)
    │   ├── sonuclar_US_guncel_isp5_3000req_delay.xlsx
    │   └── ...  (isp 6..10)
    └── outputs/               ← script otomatik oluşturur

Çalıştırma:
    pip install pandas numpy matplotlib openpyxl
    python3 plot_results.py

Üretilen çıktılar:
    outputs/nsf/             → 12 bireysel figür (PNG + PDF) + 3 doğrulama xlsx
    outputs/usnet/           → 12 bireysel figür (PNG + PDF) + 3 doğrulama xlsx
    outputs/combined_NSF/    → 1 birleşik 4×3 figür  (GENERATE_COMBINED=True ise)
    outputs/combined_USnet/  → 1 birleşik 4×3 figür  (GENERATE_COMBINED=True ise)

Tüm figürlerde NSF & USnet ortak y-ekseni + ortak heatmap renk skalası kullanılır
(SHARE_Y_AXIS=True iken).
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =============================================================================
# KONFİGÜRASYON
# =============================================================================

# --- Klasörler (script'in bulunduğu dizine göre göreceli) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR  = os.path.join(SCRIPT_DIR, "inputs")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "outputs")
SHEET_NAME = "Sonuclar"

# --- Hangi çıktılar üretilsin? ---
GENERATE_INDIVIDUAL = True   # 24 bireysel figür (12 NSF + 12 USnet)
GENERATE_COMBINED   = True   # 2 birleşik 4×3 figür (her veri seti için 1)

# --- Veri setleri (dosya adı deseni: {isp} ISP numarasıyla değiştirilir) ---
DATASETS = {
    "NSF":   {"pattern": "sonuclar_NFS_guncel_isp{isp}_3000req_delay.xlsx",
              "ind_subdir": "nsf",
              "comb_subdir": "combined_NSF"},
    "USnet": {"pattern": "sonuclar_US_guncel_isp{isp}_3000req_delay.xlsx",
              "ind_subdir": "usnet",
              "comb_subdir": "combined_USnet"},
}

# --- Deney parametreleri ---
ISPS_FOR_VBW_VN  = [6, 7, 8]               # VBW & VNode grafiklerinde kullanılan ISP'ler
VBW_VALUES       = [5, 10, 15, 20, 25]
VNODE_VALUES     = [5, 6, 7, 8, 9, 10]
ISP_AXIS_VALUES  = [5, 6, 7, 8, 9, 10]
ISP_VN_FILTER    = [6, 7, 8]               # ISP grafiklerinde dahil edilen VNode'lar
ISP_BW_FILTER    = [10, 15]                # ISP grafiklerinde dahil edilen VBW'ler

# --- Algoritmalar (dahili ad → görüntü adı) ---
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

# --- Eksen başlıkları & metrik etiketleri ---
XLABEL_VBW   = "Sanal Bağlantı BW Artışı"
XLABEL_VNODE = "Sanal Düğüm Sayısı (VN)"
XLABEL_ISP   = "ISP Sayısı"

METRICS = {
    "accept": {"title":  "İstek Kabul Oranı (%)",
               "ylabel": "Kabul Oranı (%)"},
    "res":    {"title":  ("Ortalama Kaynak Kullanımı (BW)\n"
                          "(tüm algoritmaların ortak çözdüğü istekler)"),
               "ylabel": "Ortalama Kaynak Kullanımı (BW)"},
    "hops":   {"title":  "Kabul Edilen İsteklerde Ortalama Hop Sayısı",
               "ylabel": "Ortalama Hop Sayısı"},
    "delay":  {"title":  "Kabul Edilen İsteklerde Gecikme Dağılımı",
               "ylabel": "Gecikme"},
}

# --- Y-EKSEN PAYLAŞIMI ---
SHARE_Y_AXIS = True   # NSF & USnet, aynı metrik için aynı y-aralığını paylaşır
YLIMS = {             # Manuel limit; SHARE_Y_AXIS=True iken otomatik doldurulur
    "accept": None,   # (vmin, vmax) — heatmap renk skalası için
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
BAR_WIDTH    = 0.18
BOX_WIDTH    = 0.16
SAVE_PNG     = True
SAVE_PDF     = True

# Birleşik 4×3 figür stili
COMBINED_FIG_SIZE   = (17, 18)
COMBINED_DPI        = 150
SUPTITLE_FONT       = 16
COL_TITLE_FONT      = 12
ROW_LABEL_FONT      = 12


# =============================================================================
# VERİ ANALİZİ
# =============================================================================

def load_isp_file(input_pattern, isp):
    path = os.path.join(INPUT_DIR, input_pattern.format(isp=isp))
    df = pd.read_excel(path, sheet_name=SHEET_NAME)
    for algo in ALGORITHMS:
        df[f"{algo}_acc"]  = pd.to_numeric(df[f"{algo}_BW"],        errors="coerce").notna()
        df[f"{algo}_BW_n"] = pd.to_numeric(df[f"{algo}_BW"],        errors="coerce")
        df[f"{algo}_Hp_n"] = pd.to_numeric(df[f"{algo}_NumofHops"], errors="coerce")
        df[f"{algo}_Dl_n"] = pd.to_numeric(df[f"{algo}_Delay"],     errors="coerce")
    common = np.ones(len(df), dtype=bool)
    for algo in ALGORITHMS:
        common &= df[f"{algo}_acc"].values
    df["_common"] = common
    return df


def aggregate_full(df, group_col, x_values):
    """Çizim için tüm gerekli istatistikleri toplar (mean, std, ham örnek)."""
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


def build_dataset_aggregates(pattern):
    """Bir veri seti için 3 x-ekseni (VBW, VNode, ISP) aggregate'lerini döndürür."""
    # VBW & VNode: ISP 6-7-8 birleşik
    frames = []
    for isp in ISPS_FOR_VBW_VN:
        d = load_isp_file(pattern, isp); d["ISP"] = isp
        frames.append(d)
    df_pool = pd.concat(frames, ignore_index=True)
    aggs = {
        "VBW":   aggregate_full(df_pool, "VBW",   VBW_VALUES),
        "VNode": aggregate_full(df_pool, "VNode", VNODE_VALUES),
    }
    # ISP: tüm ISP'ler + filtre
    rows = []
    for isp in ISP_AXIS_VALUES:
        d = load_isp_file(pattern, isp); d["ISP"] = isp
        d = d[d["VNode"].isin(ISP_VN_FILTER) & d["VBW"].isin(ISP_BW_FILTER)]
        rows.append(d)
    df_isp = pd.concat(rows, ignore_index=True)
    aggs["ISP"] = aggregate_full(df_isp, "ISP", ISP_AXIS_VALUES)
    return aggs


def compute_shared_ylims(aggs_list, pad=0.05):
    """Birden çok veri setinden her metrik için ortak (ymin, ymax) hesaplar."""
    out = {}
    # accept (heatmap renk skalası)
    accept_vals = []
    for aggs in aggs_list:
        for _, agg in aggs.items():
            for a in ALGORITHMS:
                accept_vals.extend([v for v in agg[a]["accept"] if v == v])
    if accept_vals:
        amin = max(0, np.floor(min(accept_vals) / 5) * 5)
        amax = min(100, np.ceil(max(accept_vals) / 5) * 5)
        out["accept"] = (amin, amax)
    # res
    vals = []
    for aggs in aggs_list:
        for _, agg in aggs.items():
            for a in ALGORITHMS:
                vals.extend([v for v in agg[a]["res"] if v == v])
    out["res"] = (0, max(vals) * (1 + pad)) if vals else None
    # hops (mean ± std)
    lo_vals, hi_vals = [], []
    for aggs in aggs_list:
        for _, agg in aggs.items():
            for a in ALGORITHMS:
                mean = np.array(agg[a]["hops"], dtype=float)
                std  = np.array(agg[a]["hops_std"], dtype=float)
                lo_vals.extend([v for v in (mean - std) if v == v])
                hi_vals.extend([v for v in (mean + std) if v == v])
    if hi_vals:
        lo = max(0, min(lo_vals) * (1 - pad)) if min(lo_vals) > 0 else 0
        out["hops"] = (lo, max(hi_vals) * (1 + pad))
    # delay (1-99 yüzdelik dilim — box-plot whisker'larıyla uyumlu)
    all_samples = []
    for aggs in aggs_list:
        for _, agg in aggs.items():
            for a in ALGORITHMS:
                for arr in agg[a]["delay_samples"]:
                    if len(arr):
                        all_samples.append(arr)
    if all_samples:
        flat = np.concatenate(all_samples)
        lo, hi = np.percentile(flat, [1, 99])
        out["delay"] = (max(0, lo * (1 - pad)), hi * (1 + pad))
    return out


def export_aggregate_xlsx(aggs, axis_key, x_values, x_label_col, out_path):
    """Skalar değerleri xlsx olarak yaz (doğrulama)."""
    with pd.ExcelWriter(out_path) as w:
        for metric in METRICS:
            field = {"accept": "accept", "res": "res",
                     "hops": "hops",   "delay": "delay_mean"}[metric]
            rows = []
            for a in ALGORITHMS:
                for i, x in enumerate(x_values):
                    rows.append({"Algoritma": a, x_label_col: x,
                                 "Değer": aggs[axis_key][a][field][i]})
            pd.DataFrame(rows).to_excel(w, sheet_name=metric, index=False)


# =============================================================================
# ÇİZİM FONKSİYONLARI (her metrik için; verilen ax üzerine çizer)
# =============================================================================

def draw_accept_heatmap(ax, agg, x_values, xlabel, *, add_colorbar=True):
    mat = np.array([agg[a]["accept"] for a in ALGORITHMS])
    if YLIMS.get("accept") is not None:
        vmin, vmax = YLIMS["accept"]
    else:
        vmin, vmax = 0, 100
    im = ax.imshow(mat, aspect="auto", cmap=HEATMAP_CMAP, vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(x_values))); ax.set_xticklabels(x_values)
    ax.set_yticks(range(len(ALGORITHMS)))
    ax.set_yticklabels([ALGORITHMS[a] for a in ALGORITHMS])
    ax.set_xlabel(xlabel, fontsize=LABEL_FONT)
    span = max(vmax - vmin, 1e-9)
    for (i, j), v in np.ndenumerate(mat):
        if np.isnan(v): continue
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
        mean = np.array(agg[a]["hops"],     dtype=float)
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
    if metric == "accept":
        return None  # colorbar var
    if metric == "delay":
        h = [plt.Rectangle((0, 0), 1, 1, facecolor=COLORS[a], alpha=0.75,
                           edgecolor="black", linewidth=0.5,
                           label=ALGORITHMS[a]) for a in ALGORITHMS]
        h.append(plt.Line2D([0], [0], marker="D", color="black",
                            markerfacecolor="white", markersize=7,
                            linewidth=0, label="Ortalama"))
        return h
    return [plt.Line2D([0], [0], color=COLORS[a], marker=MARKERS[a],
                       linewidth=LINEWIDTH, markersize=MARKERSIZE,
                       label=ALGORITHMS[a]) for a in ALGORITHMS]


# =============================================================================
# BİREYSEL FİGÜR ÜRETİCİ
# =============================================================================

def plot_individual(metric, agg, x_values, xlabel, subtitle, out_basename, out_dir):
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    DRAW_FUNCS[metric](ax, agg, x_values, xlabel)
    ax.set_title(f"{METRICS[metric]['title']}\n({subtitle})", fontsize=TITLE_FONT)
    if metric != "accept" and YLIMS.get(metric) is not None:
        ax.set_ylim(YLIMS[metric])
    handles = make_legend_handles(metric)
    if handles is not None:
        ax.legend(handles=handles, loc="best", fontsize=LEGEND_FONT)
    fig.tight_layout()
    if SAVE_PNG:
        fig.savefig(os.path.join(out_dir, out_basename + ".png"),
                    dpi=DPI, bbox_inches="tight")
    if SAVE_PDF:
        fig.savefig(os.path.join(out_dir, out_basename + ".pdf"),
                    bbox_inches="tight")
    plt.close(fig)


def generate_individual_figures(dataset_name, aggs, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    axis_specs = [
        ("VBW",   VBW_VALUES,      XLABEL_VBW,
         f"{dataset_name} — VBW Artışı (ISP 6-7-8)"),
        ("VNode", VNODE_VALUES,    XLABEL_VNODE,
         f"{dataset_name} — VN Artışı (ISP 6-7-8)"),
        ("ISP",   ISP_AXIS_VALUES, XLABEL_ISP,
         f"{dataset_name} — VNode ∈ {ISP_VN_FILTER}, VBW ∈ {ISP_BW_FILTER}"),
    ]
    for axis_key, vals, xlab, sub in axis_specs:
        for metric in METRICS:
            plot_individual(metric, aggs[axis_key], vals, xlab, sub,
                            out_basename=f"fig_{axis_key}_{metric}",
                            out_dir=out_dir)
    # Doğrulama xlsx'leri
    for axis_key, vals, _, _ in axis_specs:
        col = {"VBW": "VBW", "VNode": "VNode", "ISP": "ISP"}[axis_key]
        export_aggregate_xlsx(aggs, axis_key, vals, col,
                              os.path.join(out_dir, f"aggregated_{axis_key}.xlsx"))
    print(f"  ✓ {dataset_name} bireysel: {out_dir}")


# =============================================================================
# BİRLEŞİK 4×3 FİGÜR ÜRETİCİ
# =============================================================================

COMBINED_COLUMNS = [
    {"key": "VBW",   "xlabel": XLABEL_VBW,   "values": VBW_VALUES,
     "subtitle": "VBW Artışı (ISP 6-7-8)"},
    {"key": "VNode", "xlabel": XLABEL_VNODE, "values": VNODE_VALUES,
     "subtitle": "VN Artışı (ISP 6-7-8)"},
    {"key": "ISP",   "xlabel": XLABEL_ISP,   "values": ISP_AXIS_VALUES,
     "subtitle": f"ISP (VNode∈{ISP_VN_FILTER}, VBW∈{ISP_BW_FILTER})"},
]
METRIC_ORDER = ["accept", "res", "hops", "delay"]


def generate_combined_figure(dataset_name, aggs, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    nrows, ncols = len(METRIC_ORDER), len(COMBINED_COLUMNS)
    fig, axes = plt.subplots(nrows, ncols, figsize=COMBINED_FIG_SIZE)

    for j, col in enumerate(COMBINED_COLUMNS):
        axes[0, j].set_title(col["subtitle"], fontsize=COL_TITLE_FONT,
                             fontweight="bold", pad=12)

    for i, metric in enumerate(METRIC_ORDER):
        for j, col in enumerate(COMBINED_COLUMNS):
            ax = axes[i, j]
            agg = aggs[col["key"]]
            if metric == "accept":
                draw_accept_heatmap(ax, agg, col["values"], "",
                                    add_colorbar=False)
            else:
                DRAW_FUNCS[metric](ax, agg, col["values"], "")
                if YLIMS.get(metric) is not None:
                    ax.set_ylim(YLIMS[metric])
            ax.tick_params(labelsize=9)
            if i == nrows - 1:
                ax.set_xlabel(col["xlabel"], fontsize=11)
            else:
                ax.set_xlabel("")
            if j != 0 and metric != "accept":
                ax.set_ylabel("")

    for i, metric in enumerate(METRIC_ORDER):
        label = METRICS[metric]["title"].split("\n")[0]
        axes[i, 0].annotate(label, xy=(-0.30, 0.5),
                            xycoords="axes fraction",
                            ha="center", va="center", rotation=90,
                            fontsize=ROW_LABEL_FONT, fontweight="bold")

    legend_handles = [plt.Line2D([0], [0], color=COLORS[a], marker=MARKERS[a],
                                 linewidth=LINEWIDTH, markersize=MARKERSIZE,
                                 label=ALGORITHMS[a]) for a in ALGORITHMS]
    fig.legend(handles=legend_handles, loc="lower center",
               ncol=len(ALGORITHMS), fontsize=11,
               bbox_to_anchor=(0.5, -0.01), frameon=True)

    heatmap_im = axes[0, -1].images[0] if axes[0, -1].images else None
    if heatmap_im is not None:
        pos = axes[0, -1].get_position()
        cax = fig.add_axes([pos.x1 + 0.012, pos.y0, 0.010, pos.height])
        cb = fig.colorbar(heatmap_im, cax=cax)
        cb.set_label("Kabul Oranı (%)", fontsize=10)

    fig.suptitle(f"{dataset_name} — Tüm Sonuçlar (4 metrik × 3 eksen)",
                 fontsize=SUPTITLE_FONT, fontweight="bold", y=0.995)
    fig.tight_layout(rect=[0.03, 0.02, 0.96, 0.985])

    base = os.path.join(out_dir, f"combined_{dataset_name}_4x3")
    if SAVE_PNG:
        fig.savefig(base + ".png", dpi=COMBINED_DPI, bbox_inches="tight")
    if SAVE_PDF:
        fig.savefig(base + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {dataset_name} birleşik 4×3: {base}.png/.pdf")


# =============================================================================
# ANA AKIŞ
# =============================================================================

def main():
    global YLIMS

    if not os.path.isdir(INPUT_DIR):
        raise SystemExit(
            f"HATA: Girdi klasörü bulunamadı: {INPUT_DIR}\n"
            f"Excel dosyalarını '{INPUT_DIR}' altına koyun "
            f"(ya da bu script'in tepesinden INPUT_DIR yolunu değiştirin)."
        )
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1) Her veri seti için aggregate'leri topla
    print("Veri setleri yükleniyor...")
    all_aggs = {}
    for name, cfg in DATASETS.items():
        all_aggs[name] = build_dataset_aggregates(cfg["pattern"])
        print(f"  • {name} yüklendi")

    # 2) Ortak y-aralıkları
    if SHARE_Y_AXIS:
        YLIMS = compute_shared_ylims(list(all_aggs.values()))
        print("\nOrtak y-aralıkları:")
        for k, v in YLIMS.items():
            if v is not None:
                print(f"  {k:>6}: ({v[0]:.2f}, {v[1]:.2f})")

    # 3) Bireysel figürler
    if GENERATE_INDIVIDUAL:
        print("\nBireysel figürler üretiliyor:")
        for name, cfg in DATASETS.items():
            out_dir = os.path.join(OUTPUT_DIR, cfg["ind_subdir"])
            generate_individual_figures(name, all_aggs[name], out_dir)

    # 4) Birleşik 4×3 figürler
    if GENERATE_COMBINED:
        print("\nBirleşik 4×3 figürler üretiliyor:")
        for name, cfg in DATASETS.items():
            out_dir = os.path.join(OUTPUT_DIR, cfg["comb_subdir"])
            generate_combined_figure(name, all_aggs[name], out_dir)

    print(f"\n✓ Tamamlandı. Çıktılar: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
