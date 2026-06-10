# Lokal Kullanım Talimatı

## Dosya Yerleşimi

Proje klasörünüzü şu şekilde kurun:

```
proje_klasörü/
├── plot_nfs_results.py
├── plot_combined_4x3.py
├── inputs/                    # Excel sonuç dosyaları buraya
│   ├── sonuclar_NFS_guncel_isp5_3000req_delay.xlsx
│   ├── sonuclar_NFS_guncel_isp6_3000req_delay.xlsx
│   ├── ... (isp7, 8, 9, 10)
│   ├── sonuclar_US_guncel_isp5_3000req_delay.xlsx
│   └── ... (US için isp5-10)
└── outputs/                   # Otomatik oluşur (script ilk çalıştırmada üretir)
    ├── nsf/                   # NSF 12 bireysel figür (PNG + PDF + xlsx)
    ├── usnet/                 # USnet 12 bireysel figür (PNG + PDF + xlsx)
    ├── combined_NSF/          # NSF 4×3 birleşik
    └── combined_USnet/        # USnet 4×3 birleşik
```

## Bağımlılıklar

```bash
pip install pandas numpy matplotlib openpyxl
```

## Yol Ayarı

`plot_nfs_results.py`'in tepe kısmında, KONFİGÜRASYON bloğunda:

```python
INPUT_DIR  = "inputs"          # ya da mutlak yol: "/home/kullanici/proje/inputs"
OUTPUT_DIR = "outputs"
```

(`plot_combined_4x3.py` aynı modülü kullandığı için yolu burada bir kere ayarlamak yeterli; o script de `OUTPUT_ROOT` üzerinden buna ekleme yapar — gerekirse onu da düzenleyin.)

## Çalıştırma

Tek komut, tüm çıktıları üretir:

```bash
python3 plot_combined_4x3.py
```

Çıktı:
- **24 bireysel figür** (12 NSF + 12 USnet) — her biri PNG ve PDF
- **2 birleşik 4×3 figür** (NSF + USnet) — her biri PNG ve PDF
- 6 doğrulama xlsx (toplulaştırılmış sayılar)

Hepsi `SHARE_Y_AXIS = True` sayesinde **ortak y-eksenleri** ve **ortak heatmap renk skalası** ile üretilir; iki ağ topolojisinin sonuçları doğrudan karşılaştırılabilir.

## Sık Yapılan Değişiklikler

| İstek | Yer |
|---|---|
| Algoritma adı/rengi değiştirmek | `plot_nfs_results.py` → `ALGORITHMS`, `COLORS`, `MARKERS` |
| Y eksenini elle sabitlemek | `plot_nfs_results.py` → `YLIMS = {"res": (0, 1000), ...}` ve `SHARE_Y_AXIS = False` |
| Yalnızca bir veri seti üretmek | `plot_combined_4x3.py` → `DATASETS` sözlüğünden diğerini sil |
| Sadece PNG (PDF üretme) | `plot_nfs_results.py` → `SAVE_PDF = False` |
| ISP filtre değerleri | `plot_nfs_results.py` → `ISP_VN_FILTER`, `ISP_BW_FILTER` |
| Eksen başlıkları | `plot_nfs_results.py` → `XLABEL_VBW`, `XLABEL_VNODE`, `XLABEL_ISP` |
| Metrik başlıkları | `plot_nfs_results.py` → `METRICS` sözlüğü |
| Heatmap renk haritası | `plot_nfs_results.py` → `HEATMAP_CMAP = "RdYlGn"` (örn. "viridis", "RdBu_r") |

## Hızlı Kontrol

Script çalışınca terminale şunu yazdırır:

```
Ortak y-aralıkları hesaplandı:
  accept: (25.00, 100.00)
  res:    (0.00, 969.89)
  hops:   (7.05, 76.81)
  delay:  (66.50, 574.35)
✓ Tüm grafikler '.../nsf' dizinine kaydedildi.
✓ Birleşik 4x3 (NSF): .../combined_NSF/combined_NSF_4x3.png/.pdf
✓ Tüm grafikler '.../usnet' dizinine kaydedildi.
✓ Birleşik 4x3 (USnet): .../combined_USnet/combined_USnet_4x3.png/.pdf
```
