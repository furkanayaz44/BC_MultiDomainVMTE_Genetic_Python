"""
NSF + USnet birleşik üreteç.
- Her veri seti için 12 bireysel figürü + 1 birleşik 4×3 figürü oluşturur.
- SHARE_Y_AXIS=True iken NSF ve USnet aynı metriklerde aynı y-aralığını paylaşır.

plot_nfs_results.py modülünü import eder; aynı dizinde olmalı.
"""
import os, sys
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, "outputs")
import plot_nfs_results as m

# =============================================================================
# KONFİGÜRASYON
# =============================================================================
DATASETS = {
    "NSF":   {"pattern": "sonuclar_NFS_guncel_isp{isp}_3000req_delay.xlsx",
              "subdir":  "nsf",
              "combined_dir": "combined_NSF"},
    "USnet": {"pattern": "sonuclar_US_guncel_isp{isp}_3000req_delay.xlsx",
              "subdir":  "usnet",
              "combined_dir": "combined_USnet"},
}

# Tüm metriklerin y-aralığı her iki veri seti & her x-ekseni için ortak olsun mu?
SHARE_Y_AXIS = True

# True ise plot_nfs_results.YLIMS otomatik hesaplanan değerlerle doldurulur.
# Manuel limit kullanmak için SHARE_Y_AXIS=False yapıp YLIMS'i orada düzenleyin.

OUTPUT_ROOT = "outputs"

METRIC_ORDER = ["accept", "res", "hops", "delay"]
COLUMNS = [
    {"key": "VBW",   "xlabel": m.XLABEL_VBW,   "values": m.VBW_VALUES,
     "subtitle": "VBW Artışı (ISP 6-7-8)"},
    {"key": "VNode", "xlabel": m.XLABEL_VNODE, "values": m.VNODE_VALUES,
     "subtitle": "VN Artışı (ISP 6-7-8)"},
    {"key": "ISP",   "xlabel": m.XLABEL_ISP,   "values": m.ISP_AXIS_VALUES,
     "subtitle": f"ISP (VNode∈{m.ISP_VN_FILTER}, VBW∈{m.ISP_BW_FILTER})"},
]
FIG_SIZE       = (17, 18)
DPI            = 150
SUPTITLE_FONT  = 16
COL_TITLE_FONT = 12
ROW_LABEL_FONT = 12

# =============================================================================
# YARDIMCI
# =============================================================================
def load_dataset_aggregates(pattern):
    """Verilen veri seti deseni için 3 x-ekseni için aggregate_full sonuçları."""
    m.INPUT_PATTERN = pattern
    aggs, _, _ = m.build_aggregates()
    return aggs

def plot_dataset_individuals(dataset_name, pattern, subdir):
    """Bir veri setinin 12 bireysel figürünü üretir."""
    m.INPUT_PATTERN = pattern
    out_dir = os.path.join(OUTPUT_ROOT, subdir)
    m.OUTPUT_DIR = out_dir
    os.makedirs(out_dir, exist_ok=True)
    # Subtitle'lara veri seti adı ekleyelim (config'i geçici olarak değiştir)
    m.SUBTITLE_VBW   = f"{dataset_name} — VBW Artışı (ISP 6-7-8)"
    m.SUBTITLE_VNODE = f"{dataset_name} — VN Artışı (ISP 6-7-8)"
    m.SUBTITLE_ISP   = f"{dataset_name} — VNode ∈ {m.ISP_VN_FILTER}, VBW ∈ {m.ISP_BW_FILTER}"
    m.main()

def plot_combined_4x3(dataset_name, aggs, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    nrows, ncols = len(METRIC_ORDER), len(COLUMNS)
    fig, axes = plt.subplots(nrows, ncols, figsize=FIG_SIZE)

    for j, col in enumerate(COLUMNS):
        axes[0, j].set_title(col["subtitle"], fontsize=COL_TITLE_FONT,
                             fontweight="bold", pad=12)

    for i, metric in enumerate(METRIC_ORDER):
        for j, col in enumerate(COLUMNS):
            ax = axes[i, j]
            agg = aggs[col["key"]]
            if metric == "accept":
                m.draw_accept_heatmap(ax, agg, col["values"], "",
                                      add_colorbar=False)
            else:
                m.DRAW_FUNCS[metric](ax, agg, col["values"], "")
                # Ortak y-eksenini uygula
                if m.YLIMS.get(metric) is not None:
                    ax.set_ylim(m.YLIMS[metric])
            ax.tick_params(labelsize=9)
            if i == nrows - 1:
                ax.set_xlabel(col["xlabel"], fontsize=11)
            else:
                ax.set_xlabel("")
            if j != 0 and metric != "accept":
                ax.set_ylabel("")

    for i, metric in enumerate(METRIC_ORDER):
        label = m.METRICS[metric]["title"].split("\n")[0]
        axes[i, 0].annotate(
            label, xy=(-0.30, 0.5), xycoords="axes fraction",
            ha="center", va="center", rotation=90,
            fontsize=ROW_LABEL_FONT, fontweight="bold",
        )

    legend_handles = [plt.Line2D([0], [0], color=m.COLORS[a],
                                 marker=m.MARKERS[a],
                                 linewidth=m.LINEWIDTH, markersize=m.MARKERSIZE,
                                 label=m.ALGORITHMS[a])
                      for a in m.ALGORITHMS]
    fig.legend(handles=legend_handles, loc="lower center",
               ncol=len(m.ALGORITHMS), fontsize=11,
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
    fig.savefig(base + ".png", dpi=DPI, bbox_inches="tight")
    fig.savefig(base + ".pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"✓ Birleşik 4x3 ({dataset_name}): {base}.png/.pdf")


# =============================================================================
# ANA AKIŞ
# =============================================================================
def main():
    # 1) Her iki veri seti için aggregate'leri topla (sadece y-limit hesabı için)
    all_aggs = {}
    for name, cfg in DATASETS.items():
        all_aggs[name] = load_dataset_aggregates(cfg["pattern"])

    # 2) SHARE_Y_AXIS aktifse ortak y-limitlerini hesapla ve modüle yaz
    if SHARE_Y_AXIS:
        ylims = m.compute_shared_ylims(list(all_aggs.values()))
        m.YLIMS = ylims
        print("Ortak y-aralıkları hesaplandı:")
        for k, v in ylims.items():
            if v is not None:
                print(f"  {k}: ({v[0]:.2f}, {v[1]:.2f})")

    # 3) Bireysel + birleşik figürleri üret
    for name, cfg in DATASETS.items():
        plot_dataset_individuals(name, cfg["pattern"], cfg["subdir"])
        plot_combined_4x3(name, all_aggs[name],
                          os.path.join(OUTPUT_ROOT, cfg["combined_dir"]))

if __name__ == "__main__":
    main()
