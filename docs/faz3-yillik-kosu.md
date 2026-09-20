# Yıllık koşu planı — Eylül 2025 – Ağustos 2026 (karar: 20 Eylül 2026)

**Amaç:** mevsimsel "kaynak → kıyı" haritası (makale) ve web sitesinin "nereden atarsam nereye gider" katmanı için
dört mevsimi kapsayan yüzey akıntısı alanı.

**Kararlar (kullanıcı, 20 Eylül):** dönem Eylül 2025 – Ağustos 2026; 3B, aylık parçalar; ısı akısı kapalı.

## Tasarım

- 12 aylık parça, her biri ayrı koşu klasörü `runs/schism/y2025-09 … y2026-08`. Her parça ayın 1'inden **5 gün önce**
  CMEMS T/S dikey profiliyle (`ts.ic`) soğuk başlar; ısınma payı sonradan atılır. Aylık yeniden başlatma, ısı akısı
  kapalıyken sıcaklık sapmasını bir ayla sınırlar; hotstart/combine_hotstart karmaşası yok; bir ay çökerse yalnız o ay tekrar.
- Model: 3B, 11 sigma, k-kl, TVD; **yalın çıktı** (`33 --lean`): yalnız su seviyesi, derinlik-ort. hız ve 3B yatay hız,
  **saatlik** (`--out_min 60`); T/S/z çıktısı yok (haftalık koşuda doğrulandı). 3 scribe → `mpirun -np 21`.
- Ay bitince `40` en üst sigma katmanını ısınma payı atılmış olarak `data/processed/schism_surface_YYYY-MM.nc` dosyasına yazar
  (zaman birimi tüm aylarda **`seconds since 2025-01-01`** → OpenDrift 12 dosyayı `schism_surface_*.nc` deseniyle tek okuyucuda
  birleştirir; bulutta iki parçalı test edildi). Ham çıktı (~5 GB/ay) silinir; yüzey dosyaları ~0,7 GB/ay, yıl ~8 GB.
- Süre: 425 model günü; 7 gün 3B ≈ 25 dk ölçümüyle **≈ 27 saat** (18 çekirdek). `run_year.sh` yeniden başlatılabilir
  (biten aylar `outputs/done` ile atlanır).
- Veri: CMEMS MED analiz ürünü (aynı kimlikler) tüm dönem tek dosya/değişken (~250 MB); ERA5 **ay ay** CDS isteği
  (çok aylı tek istek yıl×ay×gün çarpımı yüzünden fazla veri çeker), sonra birleştirilir. `32` artık istenen pencereyi
  **kapsayan** dosyayı seçer (dosya adındaki tarih aralığından).
- Kapsam riski: analiz ürünü Ağustos 2025'i kapsamıyorsa `model_params.yaml` → `cmems_datasets` içinde `my`/`myint`
  (reanaliz/ara reanaliz) kimliklerine geçilir; `50 check` bunu indirmeden önce gösterir.

## Adımlar (senin tarafın)

WSL Ubuntu, bir kez (ay bitince dönüştürme WSL'den çağrılır):
```
python3 -m venv ~/odenv && ~/odenv/bin/pip install numpy xarray netcdf4 pyyaml scipy dask
```
Windows, `litter` ortamı, depo kökü:
```
python scripts\50_year_pipeline.py plan
python scripts\50_year_pipeline.py check        # ürün zaman kapsamı 2025-08-26 → 2026-09-02'yi içermeli
python scripts\50_year_pipeline.py download     # CMEMS 5 dosya + ERA5 13 aylık istek (30–60 dk; kuyruk)
python scripts\50_year_pipeline.py prepare      # 12 koşu klasörü (birkaç dk)
python scripts\50_year_pipeline.py script       # runs\schism\run_year.sh
```
WSL:
```
cd /mnt/c/Users/PC/source/repos/izmir-litter-drift
nohup bash runs/schism/run_year.sh > runs/schism/run_year.log 2>&1 &
tail -f runs/schism/run_year.log
```
Durum: `python scripts\50_year_pipeline.py status` (Windows). Bilgisayar uyumasın (güç ayarı); WSL penceresi kapansa da
`nohup` ile devam eder — ama Windows oturumu kapanırsa WSL durur.

## Sonrası

- `51_year_opendrift.py`: aylık salım partileri (kaynaklar 6 saatte bir, ızgara haftada bir; her parti 30 gün izlenir),
  `52_seasonal_maps.py`: mevsim/ay bazında matrisler, kıyı yükü haritası, web sitesi GeoJSON'ları.
- Duyarlılık: windage %1/%3, rüzgârsız, difüzyon 1/10 m²/s; 2B yıl (5 saat) yüzey/derinlik-ort. karşılaştırması.
- Stokes drift ve ısı akısı (ERA5 radyasyon) makale hakem turu için ikinci sürüme.
