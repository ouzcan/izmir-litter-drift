# DURUM — nerede kaldık (21 Eylül 2026, ~20:15)

> Yeni oturuma başlarken önce bunu, sonra `docs/decisions.md` ve ilgili `docs/faz3-*.md` dosyalarını oku.
> Doğrulama planı `docs/dogrulama.md`, kurum/veri talepleri `docs/kurumlar.md`.
> Plan/görev listesi: Claude dokümanı "İzmir Yüzen Çöp Taşınımı — Çalışma Planı" (Yapılacaklar sekmesi).

## Tek cümle
İzmir Körfezi için ~110 m'lik 3B SCHISM modeli + OpenDrift zinciri çalışıyor; bir haftalık (6–13 Eylül 2026) tam
"kaynak → kıyı" matrisi çıktı; **yıllık koşunun 8 ayı bitti (Eyl 2025 – Nis 2026), Mayıs sürüyor**; OpenDrift aylık
partileri gözcü betiğiyle otomatik işleniyor (7 ay × 2 mod hazır); web sitesinin ilk sürümü yazıldı, GitHub'a push +
Pages ayarı bekliyor; doğrulama planı çıkarıldı, henüz hiç doğrulama yapılmadı.

## Şu an çalışan / bekleyen şeyler
- **SCHISM yıllık koşu** (WSL, `runs/schism/run_year.sh`, `nohup`): **3 sa 20 dk/ay** (ölçüldü, çok kararlı).
  Biten: Eyl–Ara 2025, Oca–Nis 2026. Mayıs 21 Eylül 18:52'de başladı. Kalan 4 ay → **22 Eylül ~08:10**.
  Durum: `tail -f runs/schism/run_year.log`. Kesilirse aynı komutla başlat; biten aylar atlanır.
- **OpenDrift gözcüsü** (`scripts/watch_opendrift.bat`): 30 dk'da bir tarar, yüzey dosyası hazır ayları koşar,
  bitenleri atlar. Eyl 2025 – Mar 2026 arası 7 ay × 2 mod bitti. sources ~30–50 dk/ay, grid ~30 dk/ay.
  Ay M ancak M+1'in yüzey dosyası varken koşulur (yoksa ay sonunda salınanlar takip edilemiyordu).
- **Yıl bitince elle (2 komut, ~10 dk):** `python scripts\52_seasonal_maps.py` → `python scripts\60_web_data.py --year`.
- **Web sitesi**: `web/` hazır ve commit'li; depoda **uzak sunucu yok**, makinede `gh` de kurulu değil, git'te
  credential.helper ayarlı değil. Kullanıcı: GitHub'da `izmir-litter-drift` deposu aç (boş), `git remote add origin …`,
  `git push -u origin main`, Settings → Pages → Source "GitHub Actions". `web/config.js` içindeki `repo` adresi
  `oguzcanozupek` varsayıldı. `.env` `.gitignore`'da ve hiçbir commit'te yok — depo herkese açık olabilir (2,8 MB).
- **`config/sources.csv` eksikleri**: S06 Çitlembik, S07 Irmak, S08 Kavaklıdere **koordinatsız** → koşuya girmiyor
  (29 noktanın 23'ü koşuyor). M03 Teos, M04 Alaçatı, F04 Dikili model alanı (26,3–27,2 / 38,3–38,9) dışında.

## Bekleyen kararlar (kullanıcı girdisi gerekiyor)
- **Duyarlılık varyantları**: hangileri koşulacak — windage 0,01/0,03, rüzgârsız, difüzyon 1/10, 2B karşılaştırma.
- **Drifter kampanyası**: yapılacak mı, kaç adet. Makalenin en güçlü argümanı ama izin + donanım en çok takılacak yer;
  karar "makaleye engel değil, v2 ya da DEÜ tekne verirse paralel" yönünde (bkz. `docs/decisions.md` 21 Eylül).

## Zincir (betik sırası) — hepsi Windows conda `litter`, yalnız SCHISM WSL'de
`20` batimetri (EMODnet) → `30` ağ (dfm_tools/meshkernel) → `31` hgrid.gr3 → `32 download` (CMEMS+ERA5) →
`33 --mode 3d` (kurulum) → `32 all --mode 3d` (sınır + sflux) → WSL `mpirun --oversubscribe -np 24 ~/schism/pschism 6`
(yalın çıktıda 3 scribe: `-np 21 … 3`) → `34` özet/çizim → `40` yüzey katmanı → OpenDrift dosyası → `41` tek nokta /
`42` kaynak+ızgara matrisi (`43` yeniden toplulaştırma) → `60` web verisi. Yıllık: `50` (plan/check/download/prepare/script/
post/status) → `51` → `52` → `60 --year`. Ortak toplulaştırma: `scripts/od_agg.py`; kıyı bölgeleri `config/coast_zones.csv`
(kutular sırayla, adalar önce; alan içi kutusuz kıyı Z00 uyarısı).

## Önemli teknik notlar (tekrar keşfetme)
- Copernicus MED 4 km ürünü iç körfezde 0 hücre → yerel model şart. Delft3D FM lisans istedi → SCHISM (Apache, WSL2'de derli).
- Açık sınır: su seviyesi + gevşetmeli derinlik-ort. CMEMS hızı (`bctides` `394 4 -4 0 0` + tek satır `1.0 0.3`), kutu kenarı
  tek parça (`min_open_depth_m: 0`), `ihorcon=1 hvis_coef0=0.025`. Yalnız-su-seviyesi sınırı 36 h sonra 7 m/s jet üretmişti.
- CMEMS zos ortalaması (−0,37 m, jeoid) `zos_demean` ile çıkarılır. sflux dosya numarası sıfır dolgusuz; gün sonu +2 h uzatılır.
- 3B: `tvd.prop` şart (itr_met=3); `ts.ic` biçimi "satır sayısı; no z T S"; scribe ≥ çıktı değişkeni sayısı; ısı akısı kapalı
  (aylık yeniden başlatma bunu telafi eder). Open MPI WSL'de `--oversubscribe` ister.
- OpenDrift `reader_schism_native` enlem-boylam ağda 3B kullanamaz → 3B'nin en üst sigma katmanı `dahv` adıyla verilir (40).
  Okuyucu Delaunay + dışbükey zarf; kıyıya vurma GSHHS f maskesiyle. ERA5 CDS dosyası `valid_time`, standard_name `unknown` →
  `prepare_wind` dönüştürür. CDS isteği ay ay yapılır (çok aylı istek çarpım yüzünden şişer).
- Windows'ta `--run izmir3d.` (sondaki nokta) klasör adına yansımaz ama plots yolu tuhaf görünür; zararsız.
- `51` grid modu: `np.arange(0, (t1-t0).days, 7)` int64 üretiyordu, `timedelta(days=…)` reddediyor (sources modunda
  stop float olduğu için görünmemişti) → her iki satırda `float()`. Düzeltme 85bd610.
- Git: `.git/*.lock` dosyaları bağlı klasörde kalabiliyor → commit sonrası `rm -f .git/index.lock …`. Commit kimliği
  `-c user.name="Oguzcan" -c user.email="oguzcanozupek@gmail.com"`.
- Supabase `izmir-litter` (znpsohjjeorqhxjyuiqn, eu-central-1): `throws` (RLS anon okur+ekler), görünümler, realtime,
  hız sınırı tetikleyicisi (API'den çağrılamaz). Publishable anahtar `web/config.js`'te (herkese açık olması normal).

## Sonuçların özeti (makale için)
- 6–13 Eylül 2026 (K–KD rüzgârı 4,4 ort / 12,6 maks m/s): iç körfez doğu kaynakları → %79–94 Karşıyaka–Bayraklı (3–6 h);
  kuzey/batı kaynakları (Bostanlı, Mavişehir) → %96–100 İnciraltı–Balçova (15 h); Gediz → %59 orta körfez adaları (24 h);
  1 km ızgara (158 bin parçacık) tümü kıyıya vurdu, medyan 15 h; Karaburun doğu kıyısı %29, alan dışı (Sakız yönü) %19,
  Uzunada/adalar tuzak. Dosyalar: `docs/sonuclar/2026-09-06_hafta/`.
- 2B vs 3B yüzey: yüzey akıntısı derinlik ortalamasının ~2 katı; Bostanlı→İnciraltı 25 h (2B) vs 15 h (3B yüzey).

## Sıradaki adımlar — 21 Eylül öncelik kararı
> Tek cümle: **modeli büyütmeyi bırak, sınamaya başla.** Gerekçe `docs/decisions.md` 21 Eylül maddesi.
> Ayrıntılı görev listesi: Claude dokümanı "Yapılacaklar" → "Öncelik" bölümü.

**1 · Yıl biter bitmez (~1 saat)**
1. `python scripts\52_seasonal_maps.py` → `python scripts\60_web_data.py --year`
2. Siteyi yayına al: GitHub deposu (boş) + `git remote add origin …` + `git push -u origin main` +
   Settings → Pages → Source "GitHub Actions". Site yan ürün değil — kurumlara yazarken elde gösterilecek şey.

**2 · Bu hafta (2–3 gün)**
3. **Kaynak ağırlıklandırma — en acil madde.** `od_agg.py` satır 71 bölge paylarını 23 kaynağın düz ortalaması
   olarak alıyor (`tot = {z: np.mean([r[z] for r in rows])}`). `matrix.csv` kaynak bazında payları tuttuğu için
   ağırlıklı ortalamaya çevirmek **post-processing; hiçbir koşu tekrarlanmıyor**. Ağırlık: Gediz → Kazancı vd. 2025,
   dereler → İZSU debisi, iskele/marina → sefer/bağlama sayısı; yoksa açıkça beyan edilmiş varsayım.
4. **Doğrulama Katman 1** (`docs/dogrulama.md`): Menteş mareografı (IOC API, ücretsiz, koşu dönemini kapsıyor) →
   su seviyesi RMSE + gelgit harmonikleri; LTBJ METAR (Iowa State) → ERA5 rüzgâr bias/RMSE; Copernicus SST UHR →
   yüzey sıcaklığı. İzin yok, para yok, kimseye bağımlı değil.

**3 · Bir gece (gözcü koşar)**
5. Alan-dışı parçacık düzeltmesi (`drift:deactivate_*`, B_model sınırı) + duyarlılık varyantları **tek geçişte** →
   her kıyı bölgesi payı için belirsizlik bandı.

**4 · Makale (iki hafta sonra yazılabilir)**
6. `paper/` hâlâ boş. Yöntem bölümü bu dosyadan + `docs/faz3-*.md`'den derlenir; şekiller `docs/sonuclar` + `52`.
   Çerçeve: drifter'sız "çöpün nereye gittiğini tahmin ediyoruz" denmez; "dolaşım + bağlanabilirlik modeli,
   deniz seviyesi ve rüzgârla doğrulanmış, duyarlılık sınırlarıyla" denir. Literatür boşluğu: Politikos vd. (2017)
   Ege çalışması Türk kıyısını kapsamıyor. Sayın & Eronat karşılaştırma notu.
7. Kaynak koordinatları: S06–S08'i bul, `verified=no` olanları OSM'den doğrula.

**5 · Paralel**
8. Site yayına girer girmez DEÜ-DBTE e-postası (`docs/kurumlar.md`); sonra İBB/İZSU/TÜRÇEV.
9. Drifter kararı verilirse Liman Başkanlığı + SHOD başvurusu.

**Şimdi yapılmayacaklar** (doğru fikir, yanlış zaman): Stokes drift, ısı akısı, alanı batıya genişletme,
il kıyısı için Copernicus hücreleri. Doğrulanmamış modele fizik eklemek hatanın kaynağını bulmayı zorlaştırıyor.
