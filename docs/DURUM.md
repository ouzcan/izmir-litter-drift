# DURUM — nerede kaldık (23 Eylül 2026, öğle)

> Yeni oturuma başlarken önce bunu oku, sonra `docs/decisions.md` (karar kaydı) ve
> `docs/sonuclar/dogrulama/BULGULAR.md` (doğrulama sonuçları). Plan `docs/dogrulama.md`,
> kurum/veri talepleri `docs/kurumlar.md`, SCHISM ayrıntıları `docs/faz3-*.md`.
> Görev listesi: Claude dokümanı "İzmir Yüzen Çöp Taşınımı — Çalışma Planı" → "Yapılacaklar" sekmesi.

## Tek cümle
İzmir Körfezi için ~110 m'lik 3B SCHISM + OpenDrift zinciri kuruldu, **bir yıllık koşu (Eyl 2025 – Ağu 2026)
tamamlandı**, site **yayında**, kaynak ağırlıklandırma senaryolaştırıldı ve **Doğrulama Katman 1 bitti** —
sonuç: hidrodinamik çekirdek sağlam, **meteorolojik zorlama az enerjili**. **Duyarlılık geçişi hazır, koşulmayı
bekliyor** (`scripts\watch_sensitivity.bat`); sonra makale.

## Şu an çalışan bir şey yok — sıradaki komut
```
scripts\watch_sensitivity.bat
```
7 adım, sırayla (her adım biten ayları atlar, kesilirse aynı komutla devam): taban v2 `base2` (alan dışı biter) →
windage 0,03 `w3` → 0,01 `w1` → rüzgârsız `w0` → difüzyon 1 `d1` / 10 `d10` → yeniden yüzdürme `rf5` (pahalı, 2 km
ızgara). Her varyanttan sonra `52 --tag`, sonda `54_sensitivity.py` → `runs/opendrift/year/sensitivity/sensitivity_grid.md`
(bölge × varyant, tabana göre puan farkı, ilk-3 değişti mi). Ölçütler koşudan önce sabitlendi; seçme yok.
Süre bilinmiyor — taban bir ay ~? dk sürmüştü; `rf5`'i önce tek ayla ölç (bat içinde komut).
Sonuç beğenilirse site `60_web_data.py --year --tag base2` ile taban v2'ye geçer (henüz yapılmadı).

Yıl bitti. 12 aylık yüzey dosyası `data/processed/schism_surface_*.nc` (her biri ~550 MB, `elev` + `dahv` içerir —
ham SCHISM çıktısı silindi ama su seviyesi KAYIP DEĞİL), 12 ay × 2 mod OpenDrift `runs/opendrift/year/`,
mevsimsel çıktılar `runs/opendrift/year/summary/`, site verisi `web/data/`.

## Site — YAYINDA
- https://ouzcan.github.io/izmir-litter-drift/ · depo: https://github.com/ouzcan/izmir-litter-drift (public)
- Hücre verisi **dönem başına ayrı dosya** (`cells_<dönem>.json`); açılış yükü ~245 KB gzip (eskiden 2,6 MB),
  dönem değişince ~200 KB tembel yükleme. 17 dönem: yıl + 4 mevsim + 12 ay.
- Model alanı (26,3–27,2 / 38,3–38,9) haritada kesik çizgi; alan dışına tıklayınca ayrı açıklama.
  `zones.json`'da Z09 Seferihisar (%11) ve Z11 Selçuk (%0) `outside: true` — yapısal sıfır alıyorlar.
- Supabase `izmir-litter` canlı; `.env` hiçbir commit'te yok.

## Sonuçlar

### Izgara, yıl — "nereye atarsan at, nereye gider"
Karaburun–Mordoğan doğu kıyısı %24 · körfez dışı %24 · Çeşme–Alaçatı %9 · Aliağa–Çandarlı–Dikili %9 ·
Ildır–Gülbahçe %8 · Foça–Gediz %7 · Güzelbahçe–Urla %7 · iç körfez %1.

### Kaynaklar, yıl — ağırlıklandırma manşeti değiştiriyor
| bölge | eşit | havza | kentsel |
|---|---|---|---|
| Foça–Gediz deltası | 6,6% | **29,5%** | 26,2% |
| Karşıyaka–Bayraklı | **26,0%** | 5,0% | 10,5% |
| İnciraltı–Balçova | **24,2%** | 6,0% | 7,4% |
| Aliağa–Çandarlı–Dikili | 4,2% | 12,1% | 12,0% |

Eşit ağırlıkta "yükün yarısı iç körfeze" çıkıyor; havza ağırlıklı senaryoda Z02+Z04 %11'e düşüyor ve tepeye
Foça–Gediz geçiyor. Sebep: Gediz havzası 15.123 km² ve **dış** körfeze döküyor. `scripts/53_weighted_shares.py`,
ağırlıklar `config/source_weights.csv` (her satırda güven düzeyi ve kaynak referansı). Koşu tekrarı gerekmez —
`sources_matrix_*.csv` üzerinden post-processing.

### Mevsimsellik (ızgara, medyan kıyıya vurma)
Eyl 21 sa · Ara 27 sa (%95 vuruyor, yılın en düşüğü) · Oca 24 sa · Mar 18 sa · Haz 21 sa.
Kış ayrışıyor: çöp daha uzun suda kalıyor, daha büyük kısmı körfezi terk ediyor.

### Doğrulama Katman 1 — BİTTİ (ayrıntı: `docs/sonuclar/dogrulama/BULGULAR.md`)
**Su seviyesi** (Menteş mareografı, IOC `ment`, 6.517 ortak saat): merkezlenmiş RMSE 10,0 cm, r 0,659,
model genliği gözlemin %75'i. Gelgit/kalan ayrıştırması:

| bileşen | std gözlem | std model | crmse | r |
|---|---|---|---|---|
| gelgit | 5,6 cm | 4,5 cm | 2,5 cm | **0,896** |
| kalan (meteorolojik) | 12,0 cm | 8,8 cm | **9,7 cm** | 0,604 |

**Rüzgâr** (ERA5 ↔ LTBJ METAR, 8.141 saat): ERA5 hızı günün her saatinde 0,53–0,60 çarpanı kadar düşük
(sabit çarpan = yer uyuşmazlığı, eksik fizik değil); imbat döngüsü ve öğleden sonra yönü doğru; gece yön ~40°
sapıyor; ERA5 bu noktada >10 m/s'yi **hiç** görmüyor (METAR %2,8).

**Teşhis: meteorolojik zorlama az enerjili, hidrodinamik model değil.** Üç bağımsız kanıt aynı yöne bakıyor:
kabarma genliği %27 eksik, ERA5 uç rüzgârları kaçırıyor, gelgit tutuyor (yani ağ ve çekirdek sağlam).
Windage duyarlılık bandının (0,01–0,03) artık ölçüme dayalı gerekçesi var.

Yarı-günlük gelgit sönümü (M2 0,83, S2 0,53, ~28° önde) **yerel batimetri değil** — 1 m'den 30 m'ye beş
düğümde aynı çıktı, yani CMEMS 4 km sınır alanından miras. Düzeltmesi (bctides `nbfr>0` + FES2014) en fazla
2 cm kazandırır, önceliği düşük.

## Bekleyen kararlar (kullanıcı girdisi)
- **2B karşılaştırma**: tam yıl değil, iki zıt ay (Aralık + Haziran) 2B SCHISM + OpenDrift; "3B neden gerekliydi"
  gerekçesi için yeter. Henüz kurulmadı (33 `--mode 2d`, 40'ın 2B çıktısı için uyarlanması gerekir).
- **Drifter kampanyası**: yapılacak mı, kaç adet. Karar "makaleye engel değil, v2 ya da DEÜ tekne verirse paralel".
- **Kaynak grup payları**: `source_weights.csv`'deki 0,69/0,12/0,03/0,14/0,02 bölüşümü Claude'un kurgusu
  (dayanakları UNEP/MAP 2015 ve İzmir 2024 kompozisyonu). Gözden geçirilmeli.

## Eksikler
- `config/sources.csv`: S06 Çitlembik, S07 Irmak, S08 Kavaklıdere **koordinatsız** → 29 noktanın 23'ü koşuyor.
  M03 Teos, M04 Alaçatı, F04 Dikili model alanı dışında. Ayrıca İBB Meles raporuna göre Arap/Irmak/Çitlembik
  Meles'in KOLU olabilir, ayrı ağız olmayabilir — doğrulanmalı.
- `paper/` hâlâ boş.
- Alan-dışı düzeltmesi **koda girdi, henüz koşulmadı** (`51 --deactivate_outside`, bat'ta `base2`). Eski tabanda
  ızgara %24 "Z12"nin %22,7'si alan dışında (Sakız/Koyun/Çandarlı kuzeyi) "kıyıya vurmuş" sayılan parçacık —
  orada akıntı 0, yalnız rüzgârla sürüklenmişler. Yeni tabanda bunlar `outside` olur; Z10 payı da düşecek (38,9°K
  kuzeyi alan dışı). Site hâlâ eski tabanı gösteriyor.

## Zincir (betik sırası) — hepsi Windows conda `litter`, yalnız SCHISM WSL'de
`20` batimetri (EMODnet) → `30` ağ (dfm_tools/meshkernel) → `31` hgrid.gr3 → `32 download` (CMEMS+ERA5) →
`33 --mode 3d` → `32 all --mode 3d` → WSL `mpirun --oversubscribe -np 24 ~/schism/pschism 6` → `34` özet →
`40` yüzey katmanı → `41` tek nokta / `42` matris (`43` yeniden toplulaştırma) → `60` web verisi.
Yıllık: `50` (plan/check/download/prepare/script/post/status) → `51` → `52` → `60 --year` → `53` ağırlıklı paylar.
Doğrulama: `70` su seviyesi, `71` rüzgâr (ikisi de `--download` + argümansız koşu).
Duyarlılık: `51 --tag <t> [--deactivate_outside --windage --no-wind --diffusivity --refloat_days]` → `52 --tag <t>` →
`54_sensitivity.py --base base2 --tags ...` (sıra: `scripts/watch_sensitivity.bat`). Yeniden yüzdürme modeli `scripts/od_refloat.py`.
Gözcü: `scripts/watch_opendrift.bat`. Ortak toplulaştırma `scripts/od_agg.py`; bölgeler `config/coast_zones.csv`.

## Önemli teknik notlar (tekrar keşfetme)
- Copernicus MED 4 km iç körfezde 0 hücre → yerel model şart. Delft3D FM lisans istedi → SCHISM (WSL2'de derli).
- Açık sınır: su seviyesi + gevşetmeli derinlik-ort. CMEMS hızı (`bctides` `394 4 -4 4 4` + `1.0 0.3`),
  kutu kenarı tek parça (`min_open_depth_m: 0`), `ihorcon=1 hvis_coef0=0.025`. Yalnız-su-seviyesi sınırı
  36 h sonra 7 m/s jet üretmişti. `nbfr=0` — gelgit CMEMS `zos` zaman serisinden geliyor (ürün gelgit içeriyor).
- `nws=2`, sflux'ta `prmsl` var → ters barometre uygulanıyor. `ihconsv=0` (ısı akısı kapalı).
- CMEMS zos ortalaması (−0,37 m) `zos_demean` ile çıkarılır. sflux dosya numarası sıfır dolgusuz; gün sonu +2 h.
- 3B: `tvd.prop` şart (itr_met=3); `ts.ic` "satır sayısı; no z T S"; scribe ≥ çıktı değişkeni sayısı.
  Open MPI WSL'de `--oversubscribe` ister. Ay başına **3 sa 20 dk** (24 çekirdek).
- OpenDrift `reader_schism_native` enlem-boylam ağda 3B kullanamaz → 3B'nin en üst sigma katmanı `dahv` adıyla
  verilir (40). ERA5 CDS dosyası `valid_time`, standard_name `unknown` → `prepare_wind` dönüştürür.
- `41 prepare_wind`: hazır ERA5 dosyası yeniden yazılmaz — aynı süreçte önceki koşunun okuyucusu dosyayı açık
  tutuyor, Windows'ta üzerine yazmak PermissionError veriyordu (ce06be6).
- `51` grid modu: `np.arange(0,(t1-t0).days,7)` int64 üretiyordu, `timedelta` reddediyor → `float()` (85bd610).
  Ay M ancak M+1'in yüzey dosyası varken koşulur, yoksa ay sonunda salınanlar takip edilemiyor.
- **GitHub Actions YAML tuzağı**: `${{ }}` ifadesi tek satırlık akış eşlemesi (`{ ... }`) içinde kullanılamaz —
  süslü parantezler ayrıştırıcıyı bozar, iş akışı "Invalid workflow file" ile hiç koşmaz (1b21779).
- **Gözlem sunucuları engelli**: IOC ve Iowa State IEM hem bulut konteynerinden hem cihaz VM'inden proxy
  tarafından 403 alıyor. `70 --download` / `71 --download` **yalnız Windows'tan** koşulur.
- `70` gelgit harmoniklerini numpy en küçük karelerle çözüyor — **utide gerekmiyor**.
- Git: `.git/*.lock` ve `tmp_obj_*` bağlı klasörde kalabiliyor → commit sonrası temizlenmeli, yoksa sonraki
  commit "Unable to create .git/HEAD.lock" verir. Commit kimliği
  `-c user.name="Oguzcan" -c user.email="oguzcanozupek@gmail.com"`.
- Supabase `izmir-litter` (znpsohjjeorqhxjyuiqn, eu-central-1): `throws` (RLS anon okur+ekler), görünümler,
  realtime, hız sınırı tetikleyicisi. Publishable anahtar `web/config.js`'te (açık olması normal).
- **OpenDrift 1.14 erken biten koşu tuzağı**: bütün parçacıklar pasifleşince koşu erken biter; son çıktı adımından
  sonra pasifleşenler bir sonraki çıktı zamanına yazılır, final'de tampon kesilince sonuçta `active` görünürler
  (taban ızgarada %0,1–1,3 "denizde"). `od_agg.endpoints_from_result(ds, model=o)` bunları `o.elements_deactivated`
  ile düzeltir (51 ve 42 böyle çağırır). Sentetik test bulutta geçti (`RefloatDrift` + `deactivate_*`).
- **Yeniden yüzdürme (`od_refloat.RefloatDrift`)**: `coastline_action: previous` + kıyıya değen parçacık dondurulur
  (`elements.moving = 0`, OpenDrift'in kendi bayrağı; `update_positions` ve `horizontal_diffusion` buna uyar),
  üstel bekleme (ortalama λ_R gün) sonra yüzer; izleme sonunda karada olan `stranded` sayılır; vurma süresi =
  `t_first_beach` (ilk temas; tabandaki ölçünün birebir karşılığı). Salım anında karada olan tabanla aynı: kalıcı vurar.
  Onink vd. 2021 λ_R = 69 g (Hinata 2017); 30–45 gün izlemede tabandan ayırt edilemez → band 5 günle çizilir.
  **Pahalı**: oturanlar aktif kalır (pasifleşmez) → ortam okuması ~10× → bat'ta 2 km ızgara × 5 parçacık.
- Varyant karşılaştırması tohumla: `51 --seed 0` (varsayılan) `np.random.seed` → salım yarıçapı ve difüzyon aynı
  rastgele diziyle; varyantlar arası fark yalnız fizik parametresinden.
- `endpoints.csv`'de yeni `status` sütunu (stranded/outside/active/…); eski dosyalar sütunsuz da okunur (`stranded`'dan türetilir).

## Sıradaki adımlar
> Öncelik kararı (21 Eylül, `docs/decisions.md`): **modeli büyütmeyi bırak, sınamaya başla.**
> 1–4. maddeler bitti: site yayında, ağırlıklandırma yapıldı, Katman 1 doğrulaması tamam.

1. **`scripts\watch_sensitivity.bat`'ı başlat** (taban v2 + 6 varyant; alan-dışı düzeltmesi tabana girdi). Bitince
   `sensitivity_grid.md`'yi oku: windage 0,03 tabana göre kaç puan oynatıyor, ilk-3 değişiyor mu, refloat Karaburun
   %24'ünü nereye taşıyor. Sonra karar: site taban v2'ye geçsin mi (`60 --year --tag base2`).
   Gerekçe (23 Eylül): kabarma %27 eksik → stres ∝ U² → körfez rüzgârı ~%15 düşük → telafi windage ≈ 0,025;
   0,03 bunu bracketliyor ama SCHISM akıntısındaki rüzgâr eksikliğini değil — makalede "alt sınır" diye yazılacak.
   ERA5 ×1,3 ile SCHISM tekrarı (40 saat) gelecek iş.
2. **2B karşılaştırma** — yalnız Aralık + Haziran (bekleyen karar).
3. **Makale taslağı** (`paper/`). Yöntem bu dosyadan + `docs/faz3-*.md`'den; sonuçlar `docs/sonuclar`;
   doğrulama bölümü `BULGULAR.md`'den. Çerçeve: "İzmir Körfezi için ilk yüksek çözünürlüklü dolaşım +
   sürüklenme modeli, deniz seviyesi ve rüzgârla doğrulanmış, kaynak→kıyı bağlanabilirliği ve duyarlılık
   sınırlarıyla". Literatür boşluğu: Politikos vd. (2017) Ege çalışması Türk kıyısını kapsamıyor.
4. **Kurum temasları** (`docs/kurumlar.md`): site yayında olduğuna göre DEÜ-DBTE e-postası atılabilir;
   İZSU'dan dere bazında bariyer atığı verisi ağırlıklandırma belirsizliğini tek başına kapatır.
5. Kaynak koordinatları: S06–S08, `verified=no` olanlar, Meles kolu meselesi.
6. Katman 2 (drifter) — tek gerçek Lagrange doğrulaması, karar bekliyor.

**Şimdi yapılmayacaklar** (doğru fikir, yanlış zaman): Stokes drift, ısı akısı, alanı batıya genişletme,
il kıyısı Copernicus hücreleri, gelgit harmonik sınırı. Önce elde olanı sına ve yaz.
