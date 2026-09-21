# izmir-litter-drift

İzmir Körfezi'nde (ve il kıyılarında) denize giren yüzen çöpün akıntı ve rüzgârla nereye taşındığını, hangi kıyıya vurduğunu
modelleyen açık çalışma: **makale + "bu çöp nereye gider?" web haritası**.

**Durum (21 Eylül 2026):** yerel 3B hidrodinamik model (SCHISM, ~110 m iç körfez) + OpenDrift zinciri çalışıyor;
bir haftalık tam kaynak→kıyı matrisi çıktı; **yıllık koşunun (Eyl 2025–Ağu 2026) 8 ayı bitti, 22 Eylül sabahı tamamlanıyor**;
aylık OpenDrift partileri gözcü betiğiyle otomatik işleniyor; web sitesinin ilk sürümü `web/` altında (yayın bekliyor).
Nerede kaldık: **`docs/DURUM.md`**. Karar kaydı: `docs/decisions.md`. Doğrulama planı: `docs/dogrulama.md`.

**Öncelik (21 Eylül kararı):** modeli büyütmeyi bırak, sınamaya başla. Sıra: site yayını → kaynak ağırlıklandırma +
doğrulama Katman 1 → alan-dışı düzeltmesi + duyarlılık → makale. Ertelenenler: Stokes drift, ısı akısı, alan genişletme.

## Yöntem (kısa)
1. Batimetri EMODnet DTM 2024, kıyı GSHHS f → meshkernel ağı (76 bin düğüm; iç körfez ~110 m, dış ~430 m) → SCHISM `hgrid.gr3`.
2. SCHISM 3B (11 sigma, k-kl): açık sınırda Copernicus MED (su seviyesi + gevşetmeli akıntı + T/S), yüzeyde ERA5 rüzgârı.
3. Yüzey akıntısı → OpenDrift (windage %2, difüzyon 5 m²/s, kıyıya vurma GSHHS f): kaynaklardan ve 1 km ızgaradan salım.
4. Kıyı bölgesi payları, kıyıya vurma süreleri → matrisler, mevsimsel haritalar, web verisi.

## Doğrulama
Dört katman: (1) zorlama alanları — Menteş mareografı (IOC, ücretsiz), LTBJ METAR rüzgârı, Copernicus SST 1 km;
(2) Lagrange — düşük maliyetli GPS drifter kampanyası, skill score; (3) kıyı birikim deseni — EMODnet plaj çöpü ve
Urla transektleri ile korelasyon; (4) iç tutarlılık — duyarlılık koşuları, geriye doğru koşu, literatür karşılaştırması.
Veri kaynakları, API adresleri, izin mevzuatı ve bilinen yanlılıklar: **`docs/dogrulama.md`**.
Kurum/veri talepleri: `docs/kurumlar.md`.

## Betikler (`scripts/`, Windows conda `litter`; SCHISM WSL2 Ubuntu'da)
| Betik | İş |
|---|---|
| `00–02` | ortam denetimi, örnek Copernicus indirme, OpenDrift ilk test |
| `20_fetch_bathymetry.py` | EMODnet batimetri |
| `30_build_dflowfm.py` | ağ üretimi (dfm_tools/meshkernel; Delft3D kısmı kullanılmıyor) |
| `31_mesh_to_schism.py` | ağ → `hgrid.gr3`, açık sınır |
| `32_forcing_to_schism.py` | `download` CMEMS+ERA5; `boundary`/`sflux`/`all` → `.th.nc`, sflux |
| `33_schism_setup.py` | `param.nml`, `vgrid.in`, `bctides.in` (smoke/2d/3d, `--lean`) |
| `34_plot_schism.py` | koşu özeti ve haritalar |
| `40_schism_to_opendrift.py` | yüzey katmanı → OpenDrift dosyası |
| `41_opendrift_schism.py` | tek noktadan salım (Bostanlı testi) |
| `42_release_matrix.py`, `43_rezone.py`, `od_agg.py` | kaynak/ızgara matrisi, yeniden toplulaştırma |
| `50_year_pipeline.py` | yıllık koşu: plan/check/download/prepare/script/post/status |
| `51_year_opendrift.py`, `52_seasonal_maps.py` | aylık salım partileri, mevsimsel özetler |
| `watch_opendrift.bat` | gözcü: 30 dk'da bir tarayıp yüzey dosyası hazır olan ayları koşar |
| `60_web_data.py` | web sitesi veri paketi (`web/data/`) |
| `wsl_build_schism.sh` | SCHISM derleme (WSL2) |

## Web sitesi
`web/` — MapLibre + sade JS + Supabase (anonim atışlar, canlı akış). Yerel: `cd web && python -m http.server 8080`.
Yayın: GitHub Pages (`.github/workflows/pages.yml`). Ayrıntı: `docs/web.md`, `web/README.md`.

## Dizin yapısı

```
config/      çalışma alanı, kaynak noktaları, kıyı bölgeleri, model parametreleri, SCHISM param şablonu
data/raw/    indirilen ham veri (git dışı)      data/processed/  aylık yüzey akıntı dosyaları (git dışı)
runs/        SCHISM ve OpenDrift koşuları (git dışı)
scripts/     zincirin tamamı (yukarıdaki tablo)
docs/        DURUM, kararlar, faz notları, doğrulama planı, kurumlar, sonuçlar (docs/sonuclar), web notları
web/         site kaynak kodu + veri paketi
paper/       makale taslağı, şekiller
```

## Başlangıç
`docs/setup.md` (hesaplar, conda ortamı, ilk test), `docs/faz3-schism.md` (SCHISM kurulumu),
`docs/faz3-yillik-kosu.md` (yıllık koşu), `docs/dogrulama.md` (validasyon), `docs/kurumlar.md` (veri talepleri).

## Lisans
Kod: MIT. Veri lisansları kaynaklarına göre (Copernicus, ECMWF, EMODnet, GSHHS/OSM).
