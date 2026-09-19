# Faz 3 — İzmir Körfezi yerel hidrodinamik modeli (Delft3D FM)

**Neden:** Copernicus MED (4 km) iç körfezde tek bir geçerli hücre bile içermiyor
(`docs/notes/2026-09-19-ilk-test-kosusu.md`). Yüzen çöp için yüzey akıntısını körfezin
kendi ölçeğinde (100–200 m) çözen bir model gerekiyor.

**Seçim: Delft3D FM (D-Flow FM)** — açık kaynak, Windows'ta yerel çalışır, Deltares'in
`dfm_tools` Python paketi ağ üretimi + Copernicus sınır koşulu + ERA5 meteo zincirini
otomatikleştiriyor (Manila Körfezi çöp çalışması da Delft3D ile yapılmıştı). Alternatif
SCHISM Linux/WSL ister; gerekirse sonra geçilir.

**Alan:** `config/domain.geojson` → `B_model`: 26.30–27.20°D, 38.30–38.90°K. Açık sınır
yalnız kuzey (Karaburun–Aliağa arası) ve batı (Karaburun–Sakız arası) kenarlarında;
doğu ve güney kenarları kara (`open_edges` güvenliği).

**Çözünürlük:** taban 0,005° (~450×550 m) → derinliğe göre inceltme (dalga-Courant, 20 s):
dış körfez ~430 m, orta ~220 m, iç körfez ~110 m. Sentetik veriyle ~60 bin hücre çıktı;
gerçek batimetriyle benzer beklenir. 2D hızlı; 3D (10 sigma katman) masaüstünde çalışır.

## Kurulum (bir kez)

1. **Delft3D FM Suite** (ücretsiz, kayıt gerekir): https://download.deltares.nl/en/delft3d-fm
   → "Delft3D FM Suite 2026.01 HMWQ" (veya en yeni) Windows kurulumu. Kurulum yolu
   varsayılan kalırsa betik `dimrset` klasörünü kendisi bulur; değilse `.env` içine
   `DIMRSET_FOLDER=C:\...\plugins\DeltaShell.Dimr\kernels` yaz.
   *Alternatif:* Docker Desktop + `docker pull deltares/delft3dfm` (WSL2 gerekir).
2. Python paketleri (conda `litter` ortamında):
   ```
   pip install dfm_tools
   ```
   (`meshkernel`, `xugrid`, `hydrolib-core` ile birlikte gelir.)

## Veri (bir kez, kullanıcının bilgisayarında)

```
python scripts\20_fetch_bathymetry.py        # EMODnet DTM 2024, ~115 m, il kıyısı (+tampon)
python scripts\21_fetch_coastline_osm.py     # OSM kara poligonları (~700 MB indirme, isteğe bağlı ama önerilir)
```
OSM yoksa betik GSHHS 'f' kıyı çizgisine düşer (~200 m; iç körfezde mendirekler eksik kalır).

## Model kurma

```
python scripts\30_build_dflowfm.py --stage mesh
      → runs\dflowfm\izmir_2D\mesh.png ve mesh_ic_korfez.png'ye bak; ağ, kara kesimi, kırmızı açık sınır doğru mu?
python scripts\30_build_dflowfm.py --stage forcing --model 2D --start 2026-09-06 --end 2026-09-13
      → CMEMS (zos saatlik; so/thetao/uo/vo günlük 3D) + ERA5 (msl, u10n, v10n, chnk) indirir, .bc/.ext üretir
python scripts\30_build_dflowfm.py --stage mdu --model 2D --start 2026-09-06 --end 2026-09-13
      → izmir.mdu, dimr_config.xml, run_parallel.bat
```
Yeniden dönüştürme (indirmeden): `set LITTER_SKIP_DOWNLOAD=1` sonra `--stage forcing`.

## Koşturma

`runs\dflowfm\izmir_2D\run_parallel.bat` (nproc `config/model_params.yaml`'da, varsayılan 4).
Çıktılar `output\izmir_map.nc` (alan) ve `izmir_his.nc` (gözlem noktaları, `config/obs_points.csv`).

## Sıra

1. 2D barotropik, 1 hafta (6–13 Eylül 2026): kararlılık, açık sınır, kara kesimi kontrolü.
2. 3D, 10 sigma katman, aynı hafta: `--model 3D` (CMEMS başlangıç alanı + ERA5 ısı akısı değişkenleri otomatik eklenir).
3. Doğrulama: Sayın & Eronat desenleri (kuzey rüzgârında kıyı boyunca güneye akıntı, orta körfez antisiklonik),
   gözlem noktalarında su seviyesi/sıcaklık makul mu; sonra drifter'lar.
4. OpenDrift'e bağlama: D-Flow FM `map.nc` (UGRID) → `dfmt.rasterize_ugrid` ile 100 m düzenli gride
   → OpenDrift generic reader. (Ayrı betik: `40_dflowfm_to_opendrift.py`, sonra.)
5. Yıllık koşu (Eylül 2025–Ağustos 2026): CMEMS `my`/`myint` ürünleri, ERA5; süre ~günler.

## Bilinen sınırlar / notlar

- EMODnet derinlikleri LAT referanslı; Ege'de OSD farkı ~0,1–0,2 m, ihmal edildi.
- Gelgit: Ege'de küçük (~10–20 cm). `--tide` ile TPXO8 (opendap) eklenebilir; CMEMS zos saatlik verisi zaten gelgiti içerir.
- Dere debileri henüz yok (Gediz hariç önemsiz); Gediz için ileride `dischargebnd` eklenebilir.
- dfm_tools'un otomatik CMEMS seçimi GLOBAL (1/12°) ürünüdür; biz MED (1/24°) kimliklerini `model_params.yaml`'da açıkça veriyoruz.
