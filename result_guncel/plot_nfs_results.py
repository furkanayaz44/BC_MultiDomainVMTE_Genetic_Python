"""
NFS Sonuçları – 12 Grafik Üretici
=================================
Üretilen çıktılar (PNG + PDF):
  VBW x-ekseni  : 4 grafik (kabul, kaynak, hop, gecikme)
  VNode x-ekseni: 4 grafik (kabul, kaynak, hop, gecikme)
  ISP x-ekseni  : 4 grafik (kabul, kaynak, hop, gecikme) — VNode/VBW filtreli

Kullanım: girdi dosya yolları ve etiketleri aşağıdaki KONFIGÜRASYON
bloğundan değiştirebilirsin.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =============================================================================
# KONFİGÜRASYON  (istediğin gibi değiştir)
# =============================================================================

# --- Girdi/Çıktı yolları --------------------------------------------------
INPUT_DIR  = "/mnt/user-data/uploads"
INPUT_PATTERN = "sonuclar_NFS_guncel_isp{isp}_3000req_delay.xlsx"
SHEET_NAME = "Sonuclar"
OUTPUT_DIR = "/mnt/user-data/outputs"

# --- Veri kümesi parametreleri --------------------------------------------
ALL_ISPS         = [5, 6, 7, 8, 9, 10]     # mevcut tüm ISP dosyaları
ISPS_FOR_VBW_VN  = [6, 7, 8]               # VBW & VNode grafiklerinde kullanılacak ISP'ler
VBW_VALUES       = [5, 10, 15, 20, 25]     # VBW x-ekseni değerleri
VNODE_VALUES     = [5, 6, 7, 8, 9, 10]     # VNode x-ekseni değerleri
ISP_AXIS_VALUES  = [5, 6, 7, 8, 9, 10]     # ISP x-ekseni değerleri
ISP_VN_FILTER    = [6, 7, 8]               # ISP grafiklerinde dahil edilecek VNode'lar
ISP_BW_FILTER    = [10, 15]                # ISP grafiklerinde dahil edilecek VBW'ler

# --- Algoritmalar (görüntü adı: kolon ön-eki) -----------------------------
ALGORITHMS = {
    "GreedyCPU":   "GreedyCPU",
    "GreedyClose": "GreedyClose",
    "GA_CPU":      "GA_CPU",
    "GA_Rank":     "GA_Rank",
    "GA_QL":       "GA_QL",
}
COLORS  = {"GreedyCPU": "#1f77b4", "GreedyClose": "#ff7f0e",
           "GA_CPU":    "#2ca02c", "GA_Rank":     "#d62728",
           "GA_QL":     "#9467bd"}
MARKERS = {"GreedyCPU": "o", "GreedyClose": "s",
           "GA_CPU":    "^", "GA_Rank":     "D", "GA_QL": "v"}

# --- Eksen başlıkları -----------------------------------------------------
XLABEL_VBW   = "Sanal Bağlantı BW Artışı"
XLABEL_VNODE = "Sanal Düğüm Sayısı (VN)"
XLABEL_ISP   = "ISP Sayısı"

# --- Metrik tanımları (key -> (başlık, y-ekseni etiketi)) -----------------
METRICS = {
    "accept": {
        "title":  "İstek Kabul Oranı (%)",
        "ylabel": "Kabul Oranı (%)",
    },
    "res": {
        "title":  ("Ortalama Kaynak Kullanımı (BW)\n"
                   "(tüm algoritmaların ortak çözdüğü istekler)"),
        "ylabel": "Ortalama Kaynak Kullanımı (BW)",
    },
    "hops": {
        "title":  "Kabul Edilen İsteklerde Ortalama Hop Sayısı",
        "ylabel": "Ortalama Hop Sayısı",
    },
    "delay": {
        "title":  "Kabul Edilen İsteklerde Ortalama Gecikme",
        "ylabel": "Ortalama Gecikme",
    },
}

# --- Her grafik için alt-başlık (subtitle) --------------------------------
SUBTITLE_VBW   = f"VBW Artışına Göre (ISP {'-'.join(map(str, ISPS_FOR_VBW_VN))} ortalaması)"
SUBTITLE_VNODE = f"VN Artışına Göre (ISP {'-'.join(map(str, ISPS_FOR_VBW_VN))} ortalaması)"
SUBTITLE_ISP   = f"VNode ∈ {ISP_VN_FILTER}, VBW ∈ {ISP_BW_FILTER}"

# --- Stil seçenekleri -----------------------------------------------------
FIG_SIZE   = (8, 5.5)
DPI        = 150
LINEWIDTH  = 2
MARKERSIZE = 8
TITLE_FONT = 12
LABEL_FONT = 12
LEGEND_FONT = 10
GRID_ALPHA  = 0.3
SAVE_PNG    = True
SAVE_PDF    = True

# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def load_isp_file(isp):
    """Belirtilen ISP Excel dosyasını okur ve algoritma sütunlarını sayısallaştırır."""
    path = os.path.join(INPUT_DIR, INPUT_PATTERN.format(isp=isp))
    df = pd.read_excel(path, sheet_name=SHEET_NAME)
    for algo in ALGORITHMS:
        df[f"{algo}_acc"]   = pd.to_numeric(df[f"{algo}_BW"],        errors="coerce").notna()
        df[f"{algo}_BW_n"]  = pd.to_numeric(df[f"{algo}_BW"],        errors="coerce")
        df[f"{algo}_Hp_n"]  = pd.to_numeric(df[f"{algo}_NumofHops"], errors="coerce")
        df[f"{algo}_Dl_n"]  = pd.to_numeric(df[f"{algo}_Delay"],     errors="coerce")
    # Tüm algoritmaların kabul ettiği ortak satırlar
    common = np.ones(len(df), dtype=bool)
    for algo in ALGORITHMS:
        common &= df[f"{algo}_acc"].values
    df["_common"] = common
    return df


def compute_metrics(df_subset):
    """Bir alt veri kümesi üzerinden tüm algoritma & metrik değerlerini hesaplar."""
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
    """Verilen kolona göre grupla, her x için tüm metrikleri topla."""
    agg = {a: {m: [] for m in METRICS} for a in ALGORITHMS}
    for x in x_values:
        sub = df[df[group_col] == x]
        vals = compute_metrics(sub)
        for a in ALGORITHMS:
            for m in METRICS:
                agg[a][m].append(vals[a][m])
    return agg


def plot_metric(agg, x_values, metric_key, xlabel, subtitle, out_basename):
    """Tek bir metrik için 5 algoritmanın çizimini yapar; PNG ve PDF olarak kaydeder."""
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    for algo in ALGORITHMS:
        ax.plot(
            x_values, agg[algo][metric_key],
            marker=MARKERS[algo], color=COLORS[algo],
            linewidth=LINEWIDTH, markersize=MARKERSIZE,
            label=ALGORITHMS[algo],
        )
    ax.set_xlabel(xlabel, fontsize=LABEL_FONT)
    ax.set_ylabel(METRICS[metric_key]["ylabel"], fontsize=LABEL_FONT)
    ax.set_title(f"{METRICS[metric_key]['title']}\n({subtitle})", fontsize=TITLE_FONT)
    ax.set_xticks(x_values)
    ax.grid(True, alpha=GRID_ALPHA)
    ax.legend(loc="best", fontsize=LEGEND_FONT)
    fig.tight_layout()

    if SAVE_PNG:
        fig.savefig(os.path.join(OUTPUT_DIR, out_basename + ".png"),
                    dpi=DPI, bbox_inches="tight")
    if SAVE_PDF:
        fig.savefig(os.path.join(OUTPUT_DIR, out_basename + ".pdf"),
                    bbox_inches="tight")
    plt.close(fig)


def export_aggregate_xlsx(agg, x_values, x_label_col, out_xlsx_name):
    """Toplulaştırılmış değerleri Excel'e yaz (doğrulama amaçlı)."""
    path = os.path.join(OUTPUT_DIR, out_xlsx_name)
    with pd.ExcelWriter(path) as w:
        for m in METRICS:
            rows = []
            for a in ALGORITHMS:
                for i, x in enumerate(x_values):
                    rows.append({"Algoritma": a, x_label_col: x, "Değer": agg[a][m][i]})
            pd.DataFrame(rows).to_excel(w, sheet_name=m, index=False)


# =============================================================================
# ANA AKIŞ
# =============================================================================

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ---- 1) ISP 6-7-8 verisini birleştir; VBW & VNode grafikleri için kullan
    frames = []
    for isp in ISPS_FOR_VBW_VN:
        d = load_isp_file(isp)
        d["ISP"] = isp
        frames.append(d)
    df_pool = pd.concat(frames, ignore_index=True)

    # VBW x-ekseni
    agg_vbw = aggregate_over_x(df_pool, "VBW", VBW_VALUES)
    for m in METRICS:
        plot_metric(agg_vbw, VBW_VALUES, m,
                    xlabel=XLABEL_VBW, subtitle=SUBTITLE_VBW,
                    out_basename=f"fig_VBW_{m}")
    export_aggregate_xlsx(agg_vbw, VBW_VALUES, "VBW", "aggregated_VBW.xlsx")

    # VNode x-ekseni
    agg_vn = aggregate_over_x(df_pool, "VNode", VNODE_VALUES)
    for m in METRICS:
        plot_metric(agg_vn, VNODE_VALUES, m,
                    xlabel=XLABEL_VNODE, subtitle=SUBTITLE_VNODE,
                    out_basename=f"fig_VNode_{m}")
    export_aggregate_xlsx(agg_vn, VNODE_VALUES, "VNode", "aggregated_VNode.xlsx")

    # ---- 2) ISP x-ekseni grafikleri (VNode ∈ {6,7,8} ve VBW ∈ {10,15} filtreli)
    agg_isp = {a: {m: [] for m in METRICS} for a in ALGORITHMS}
    for isp in ISP_AXIS_VALUES:
        d = load_isp_file(isp)
        d = d[d["VNode"].isin(ISP_VN_FILTER) & d["VBW"].isin(ISP_BW_FILTER)].reset_index(drop=True)
        vals = compute_metrics(d)
        for a in ALGORITHMS:
            for m in METRICS:
                agg_isp[a][m].append(vals[a][m])

    for m in METRICS:
        plot_metric(agg_isp, ISP_AXIS_VALUES, m,
                    xlabel=XLABEL_ISP, subtitle=SUBTITLE_ISP,
                    out_basename=f"fig_ISP_{m}")
    export_aggregate_xlsx(agg_isp, ISP_AXIS_VALUES, "ISP", "aggregated_ISP.xlsx")

    print(f"✓ Tüm grafikler '{OUTPUT_DIR}' dizinine kaydedildi (PNG + PDF).")


if __name__ == "__main__":
    main()
