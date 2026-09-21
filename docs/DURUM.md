# DURUM — nerede kaldık (21 Eylül 2026, ~03:15)

> Yeni oturuma başlarken önce bunu, sonra `docs/decisions.md` ve ilgili `docs/faz3-*.md` dosyalarını oku.
> Plan/görev listesi: Claude dokümanı "İzmir Yüzen Çöp Taşınımı — Çalışma Planı" (Yapılacaklar sekmesi).

## Tek cümle
İzmir Körfezi için ~110 m'lik 3B SCHISM modeli + OpenDrift zinciri çalışıyor; bir haftalık (6–13 Eylül 2026) tam
"kaynak → kıyı" matrisi çıktı; **yıllık koşunun 3 ayı bitti (Eyl–Kas 2025), Aralık sürüyor**; OpenDrift yıllık partileri
için gözcü betiği hazır; web sitesinin ilk sürümü yazıldı, GitHub'a push + Pages ayarı bekliyor.

## Şu an çalışan / bekleyen şeyler
- **SCHISM yıllık koşu** (WSL, `runs/schism/run_year.sh`, `nohup`): ay başına **3 sa 20 dk** (ölçüldü).
  Biten: Eyl 2025 (16:13→19:33), Eki (→22:55), Kas (→02:11). Aralık 02:11'de başladı. Kalan 9 ay → **~22 Eylül 08:00**.
  Durum: `tail -f runs/schism/run_year.log`. Kesilirse aynı komutla yeniden başlat; biten aylar atlanır. Bir ay "HATA"
  verirse `runs/schism/<ay>/run.log` ve `outputs/fatal.error`; `python scripts\50_year_pipeline.py prepare --month YYYY-MM --force`.
- **OpenDrift aylık partileri**: `scripts\watch_opendrift.bat` — 30 dk'da bir tarayıp hazır ayları koşar, bitenleri atlar.
  Ay M'nin partisi ancak M+1'in yüzey dosyası varken koşulur (yoksa ay sonunda salınanlar takip edilemiyordu); bu yüzden
  şu an Eyl + Eki koşulabilir, Kas Aralık bitince sıraya girer. Süre: sources ~30 dk/ay, grid ~2,5 sa/ay.
- **Eyl 2025 sources partisi kesik**: Ekim yüzey dosyası yokken koştu (izleme 30 Eylül'de kesildi, `days: 29`).
  `python scripts\51_year_opendrift.py --mode both --month 2025-09 --force` ile yenilenmeli (grid de o koşuda çıkar).
- **Web sitesi**: `web/` hazır ve commit'li; depoda **uzak sunucu yok**, makinede `gh` de kurulu değil. Kullanıcı: GitHub'da
  `izmir-litter-drift` deposu aç, `git remote add origin …`, `git push -u origin main`, Settings → Pages → Source
  "GitHub Actions". `web/config.js` içindeki `repo` adresi kullanıcı adına göre doğrulanmalı (`oguzcanozupek` varsayıldı).
- **`config/sources.csv` eksikleri**: S06 Çitlembik, S07 Irmak, S08 Kavaklıdere **koordinatsız** → hiçbir koşuya girmiyor
  (23/29 nokta koşuyor). M03 Teos, M04 Alaçatı, F04 Dikili model alanı dışında kaldığı için düşüyor. Çoğu nokta
  "doğrulanacak" işaretli.

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
1. Yıl koşusu bitince: `51 --mode both` (tüm aylar) → `52` → `60 --year` → `web/data` güncelle, dönem seçicide yıl+mevsimler.
2. Web yayını (push + Pages), `config.js` repo adresi, og:image.
3. Duyarlılık: `51 --windage 0.01/0.03 --tag …`, `--no-wind`, difüzyon 1/10; 2B yıl karşılaştırması (5 saat).
4. Sayın & Eronat (2003/2006) dolaşım karşılaştırma notu; kaynak koordinatlarını doğrula (`sources.csv`, S06–S08 eksik).
5. Makale taslağı (`paper/`): yöntem bölümü bu dosyadaki notlardan; şekiller `docs/sonuclar` + `52` çıktıları.
6. İkinci sürüm: Stokes drift (WWM ya da rüzgârdan), ısı akısı (ERA5 radyasyon), alanı batıya (Sakız) genişletme, il kıyısı
   için Copernicus hücreleri (web sitesi il geneli).
