# DURUM — nerede kaldık (21 Eylül 2026, ~20:00)

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

## Bekleyen kararlar
- **Alan dışı parçacık** (kullanıcı erteledi, yıl bitince): SCHISM kapsama dışında akıntı fallback ile 0'a düşüyor ama
  ERA5 rüzgârı sürüyor → parçacık tek başına rüzgârla Sakız kıyısına "vuruyor". Hafta koşusundaki "%19 alan dışı"
  rakamı bu artefakt. `drift:deactivate_west_of/_east_of/_north_of/_south_of` ile B_model sınırında dondur → tüm yılı
  yeniden koş (gözcü hallediyor, bir gece).
- **Duyarlılık varyantları**: hangileri koşulacak (windage 0,01/0,03, rüzgârsız, difüzyon 1/10, 2B) — kullanıcıya soruldu.
- **Kaynak ağırlıklandırma**: 23 kaynak şu an eşit salıyor. Gerçek çöp yüküne göre ağırlıklandırılmadan "bölge payları"
  kaynak listesinin şekline bağlı. Bkz. `docs/dogrulama.md` "Bilinen yanlılıklar".

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

## Sıradaki adımlar (öncelik sırasıyla)
1. Yıl bitince: `52` → `60 --year` → `web/data` güncelle, dönem seçicide yıl + 4 mevsim.
2. Web yayını (push + Pages), `config.js` repo adresi, og:image.
3. Alan dışı parçacık düzenlemesi + tüm yılın yeniden koşulması.
4. Duyarlılık koşuları → her kıyı bölgesi payı için belirsizlik bandı.
5. **Doğrulama Katman 1** (ücretsiz, hemen yapılabilir): Menteş mareografı (IOC API) → su seviyesi RMSE + gelgit
   harmonikleri; LTBJ METAR (Iowa State) → ERA5 rüzgâr bias/RMSE; Copernicus SST UHR → yüzey sıcaklığı.
   Ayrıntı ve adresler: `docs/dogrulama.md`.
6. Kaynak koordinatları: S06–S08'i bul, `verified=no` olanları OSM'den doğrula; kaynakları çöp yüküne göre ağırlıklandır.
7. Makale taslağı (`paper/` hâlâ boş): yöntem bölümü bu dosyadan + `docs/faz3-*.md`'den derlenir; şekiller
   `docs/sonuclar` + `52` çıktıları. Sayın & Eronat karşılaştırma notu.
8. Kurum temasları (`docs/kurumlar.md`): DEÜ-DBTE (ADCP/CTD + olası ortak yazarlık), İBB/İZSU, TÜRÇEV.
   Sıralama önemli — önce önbaskı ve yayında site, sonra e-posta.
9. Doğrulama Katman 2 (drifter) kararı: 3–5 adet GSM drifter + Liman Başkanlığı/SHOD izni. Makalenin en güçlü argümanı.
10. İkinci sürüm: Stokes drift (WWM ya da rüzgârdan), ısı akısı (ERA5 radyasyon), alanı batıya (Sakız) genişletme,
    il kıyısı için Copernicus hücreleri (web sitesi il geneli).
