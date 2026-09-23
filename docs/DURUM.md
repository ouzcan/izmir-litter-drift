# DURUM — nerede kaldık (23 Eylül 2026)

> Yeni oturuma başlarken önce bunu oku, sonra `docs/decisions.md` (karar kaydı) ve
> `docs/sonuclar/dogrulama/BULGULAR.md` (doğrulama sonuçları). Plan `docs/dogrulama.md`,
> kurum/veri talepleri `docs/kurumlar.md`, SCHISM ayrıntıları `docs/faz3-*.md`.
> Görev listesi: Claude dokümanı "İzmir Yüzen Çöp Taşınımı — Çalışma Planı" → "Yapılacaklar" sekmesi.

## Tek cümle
İzmir Körfezi için ~110 m'lik 3B SCHISM + OpenDrift zinciri kuruldu, **bir yıllık koşu (Eyl 2025 – Ağu 2026)
tamamlandı**, site **yayında**, kaynak ağırlıklandırma senaryolaştırıldı ve **Doğrulama Katman 1 bitti** —
sonuç: hidrodinamik çekirdek sağlam, **meteorolojik zorlama az enerjili**. Sırada duyarlılık koşuları ve makale.

## Şu an çalışan bir şey yok
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
- **Duyarlılık varyantları**: hangileri — windage 0,01/0,03, rüzgârsız, difüzyon 1/10, 2B karşılaştırma.
- **Drifter kampanyası**: yapılacak mı, kaç adet. Karar "makaleye engel değil, v2 ya da DEÜ tekne verirse paralel".
- **Kaynak grup payları**: `source_weights.csv`'deki 0,69/0,12/0,03/0,14/0,02 bölüşümü Claude'un kurgusu
  (dayanakları UNEP/MAP 2015 ve İzmir 2024 kompozisyonu). Gözden geçirilmeli.

## Eksikler
- `config/sources.csv`: S06 Çitlembik, S07 Irmak, S08 Kavaklıdere **koordinatsız** → 29 noktanın 23'ü koşuyor.
  M03 Teos, M04 Alaçatı, F04 Dikili model alanı dışında. Ayrıca İBB Meles raporuna göre Arap/Irmak/Çitlembik
  Meles'in KOLU olabilir, ayrı ağız olmayabilir — doğrulanmalı.
- `paper/` hâlâ boş.
- Alan-dışı parçacık düzeltmesi (`drift:deactivate_*`) yapılmadı — ızgara sonucundaki %24 "körfez dışı"
  rakamının bir kısmı rüzgârla Sakız'a sürüklenip orada "kıyıya vurmuş" sayılan parçacıklar.

## Zincir (betik sırası) — hepsi Windows conda `litter`, yalnız SCHISM WSL'de
`20` batimetri (EMODnet) → `30` ağ (dfm_tools/meshkernel) → `31` hgrid.gr3 → `32 download` (CMEMS+ERA5) →
`33 --mode 3d` → `32 all --mode 3d` → WSL `mpirun --oversubscribe -np 24 ~/schism/pschism 6` → `34` özet →
`40` yüzey katmanı → `41` tek nokta / `42` matris (`43` yeniden toplulaştırma) → `60` web verisi.
Yıllık: `50` (plan/check/download/prepare/script/post/status) → `51` → `52` → `60 --year` → `53` ağırlıklı paylar.
Doğrulama: `70` su seviyesi, `71` rüzgâr (ikisi de `--download` + argümansız koşu).
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

## Sıradaki adımlar
> Öncelik kararı (21 Eylül, `docs/decisions.md`): **modeli büyütmeyi bırak, sınamaya başla.**
> 1–4. maddeler bitti: site yayında, ağırlıklandırma yapıldı, Katman 1 doğrulaması tamam.

1. **Duyarlılık koşuları** — windage 0,01/0,03, rüzgârsız, difüzyon 1/10, 2B karşılaştırma. Gözcü bir gecede
   koşar. Artık gerekçeli: zorlamanın az enerjili olduğu ölçüldü, bant bunu bracketliyor.
2. **Alan-dışı düzeltmesi** aynı geçişte (`drift:deactivate_west_of` vb., B_model sınırı).
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
