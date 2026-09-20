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

## Koşu başladı — 20 Eylül 2026, 16:13 (kullanıcı saati)

- İlk deneme `mpirun` "not enough slots" ile durdu: Open MPI slotu fiziksel çekirdek sayıyor (24 iş parçacığı = 12 slot);
  `--oversubscribe` eklendi. Hız: ~4,1 adım/s (21 süreç, /mnt/c üzerinden saatlik çıktı) → 35 günlük ay ≈ 3,4 saat,
  **yıl ≈ 40 saat** (25 dk/7 gün ölçümünden yavaş; muhtemelen aşırı abonelik ve /mnt/c yazma).
- Girdi özeti (32 çıktısı): sınırda kış aylarında |u| 0,6 m/s'ye, ERA5 rüzgârı Ocak–Nisan'da 20 m/s'ye çıkıyor; Şubat–Mart
  başlangıç tuzluluğu 34–36'ya düşüyor (Gediz tatlı suyu CMEMS'te görünüyor) — mevsimsel fark belirgin olacak.

## OpenDrift yıl akışı (hazır, bulutta test edildi)

- `51_year_opendrift.py`: her ay ayrı parti; kaynaklar 6 saatte bir 10 parçacık (23 kaynak → ~28 bin/ay), ızgara 1 km haftada
  bir 10 parçacık (2.627 hücre → ~120 bin/ay); her parti ay sonu + 30 gün izlenir (sonraki ay dosyası varsa okunur).
  Çıktı `runs/opendrift/year/<mode>_<YYYY-MM>/`; `track.nc` silinir (endpoints.csv yeter). Yüzey dosyası hazır olan aylar
  otomatik seçilir; koşu sürerken ay ay çalıştırılabilir: `python scripts\51_year_opendrift.py --mode both`.
- `52_seasonal_maps.py`: yıl, mevsim (DJF/MAM/JJA/SON) ve ay bazında kaynak matrisleri, hücre→baskın bölge haritaları,
  kıyı yükü payları; web sitesi girdileri `runs/opendrift/year/summary/web/{cells.geojson, sources.json, zones.json}` —
  hücre/kaynak başına `{dönem: {strand, t_med_h, zones: {bölge: pay}}}`.
- Duyarlılık: `51 --windage 0.01 --tag w1`, `--windage 0.03 --tag w3`, `--no-wind --tag nowind`, `--diffusivity 1 --tag d1`;
  `52 --tag w1` ayrı özet üretir.
- Duyarlılık: windage %1/%3, rüzgârsız, difüzyon 1/10 m²/s; 2B yıl (5 saat) yüzey/derinlik-ort. karşılaştırması.
- Stokes drift ve ısı akısı (ERA5 radyasyon) makale hakem turu için ikinci sürüme.
