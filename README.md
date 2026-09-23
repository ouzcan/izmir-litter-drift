# izmir-litter-drift

İzmir Körfezi'nde (ve il kıyılarında) denize giren yüzen çöpün akıntı ve rüzgârla nereye taşındığını, hangi kıyıya vurduğunu
modelleyen açık çalışma: **makale + "bu çöp nereye gider?" web haritası**.

**Site yayında: https://ouzcan.github.io/izmir-litter-drift/**

**Durum (23 Eylül 2026):** yıllık koşu (Eyl 2025 – Ağu 2026) **tamamlandı** — 12 ay 3B SCHISM + 12 ay × 2 mod
OpenDrift, mevsimsel haritalar, site verisi. Kaynak ağırlıklandırma senaryolaştırıldı. **Doğrulama Katman 1 bitti**:
su seviyesi (Menteş mareografı) ve rüzgâr (LTBJ METAR) karşılaştırmaları yapıldı — hidrodinamik çekirdek sağlam,
meteorolojik zorlama az enerjili. Sırada duyarlılık koşuları ve makale.
Nerede kaldık: **`docs/DURUM.md`**. Karar kaydı: `docs/decisions.md`. Doğrulama sonuçları:
`docs/sonuclar/dogrulama/BULGULAR.md`.

## Yöntem (kısa)
1. Batimetri EMODnet DTM 2024, kıyı GSHHS f → meshkernel ağı (76 bin düğüm; iç körfez ~110 m, dış ~430 m) → SCHISM `hgrid.gr3`.
2. SCHISM 3B (11 sigma, k-kl): açık sınırda Copernicus MED (su seviyesi + gevşetmeli akıntı + T/S), yüzeyde ERA5 rüzgârı.
3. Yüzey akıntısı → OpenDrift (windage %2, difüzyon 5 m²/s, kıyıya vurma GSHHS f): kaynaklardan ve 1 km ızgaradan salım.
4. Kıyı bölgesi payları, kıyıya vurma süreleri → matrisler, mevsimsel haritalar, web verisi.

## Doğrulama
Dört katman: (1) zorlama alanları — Menteş mareografı, LTBJ METAR, Copernicus SST; (2) Lagrange — GPS drifter
kampanyası + skill score; (3) kıyı birikim deseni — EMODnet plaj çöpü ve Urla transektleriyle korelasyon;
(4) iç tutarlılık — duyarlılık koşuları, geriye doğru koşu, literatür karşılaştırması.
Plan ve veri kaynakları: **`docs/dogrulama.md`** · kurum talepleri: `docs/kurumlar.md`.

**Katman 1 sonuçları (23 Eylül)** — `docs/sonuclar/dogrulama/BULGULAR.md`:

| | gözlem | model | crmse | r |
|---|---|---|---|---|
| su seviyesi, gelgit bileşeni | 5,6 cm | 4,5 cm | 2,5 cm | 0,896 |
| su seviyesi, meteorolojik kalan | 12,0 cm | 8,8 cm | 9,7 cm | 0,604 |

Gelgit tutuyor, kabarma tutmuyor; ERA5 rüzgârı kara istasyonunda 0,55 çarpanı kadar düşük ve >10 m/s'yi
hiç görmüyor. Teşhis: **meteorolojik zorlama az enerjili, hidrodinamik model değil.**

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
| `53_weighted_shares.py` | kaynak yüküne göre ağırlıklı bölge payları (3 senaryo; koşu tekrarı gerekmez) |
| `70_validate_sealevel.py` | doğrulama: SCHISM ↔ Menteş mareografı (gelgit/kalan ayrıştırmalı) |
| `71_validate_wind.py` | doğrulama: ERA5 ↔ LTBJ METAR (günlük döngü analizli) |
| `watch_opendrift.bat` | gözcü: 30 dk'da bir tarayıp yüzey dosyası hazır olan ayları koşar |
| `60_web_data.py` | web sitesi veri paketi (`web/data/`) |
| `wsl_build_schism.sh` | SCHISM derleme (WSL2) |

## Web sitesi
`web/` — MapLibre + sade JS + Supabase (anonim atışlar, canlı akış). Yerel: `cd web && python -m http.server 8080`.
Yayın: GitHub Pages (`.github/workflows/pages.yml`). Ayrıntı: `docs/web.md`, `web/README.md`.

## Dizin yapısı

```
config/      çalışma alanı, kaynak noktaları + ağırlıkları, kıyı bölgeleri, model parametreleri
data/raw/    indirilen ham veri (git dışı)      data/processed/  aylık yüzey akıntı dosyaları (git dışı)
runs/        SCHISM ve OpenDrift koşuları (git dışı)
scripts/     zincirin tamamı (yukarıdaki tablo)
docs/        DURUM, kararlar, faz notları, doğrulama planı + sonuçları, kurumlar, sonuçlar, web notları
web/         site kaynak kodu + veri paketi
paper/       makale taslağı, şekiller
```

## Başlangıç
`docs/setup.md` (hesaplar, conda ortamı, ilk test), `docs/faz3-schism.md` (SCHISM kurulumu),
`docs/faz3-yillik-kosu.md` (yıllık koşu), `docs/dogrulama.md` (validasyon), `docs/kurumlar.md` (veri talepleri).

## Lisans
Kod: MIT. Veri lisansları kaynaklarına göre (Copernicus, ECMWF, EMODnet, GSHHS/OSM).
