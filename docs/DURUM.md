# DURUM — nerede kaldık (20 Eylül 2026, ~20:00)

> Yeni oturuma başlarken önce bunu, sonra `docs/decisions.md` ve ilgili `docs/faz3-*.md` dosyalarını oku.
> Plan/görev listesi: Claude dokümanı "İzmir Yüzen Çöp Taşınımı — Çalışma Planı" (Yapılacaklar sekmesi).

## Tek cümle
İzmir Körfezi için ~110 m'lik 3B SCHISM modeli + OpenDrift zinciri çalışıyor; bir haftalık (6–13 Eylül 2026) tam
"kaynak → kıyı" matrisi çıktı; **yıllık koşu (Eyl 2025–Ağu 2026) kullanıcının makinesinde sürüyor**; web sitesinin ilk
sürümü yazıldı, GitHub'a push + Pages ayarı bekliyor.

## Şu an çalışan / bekleyen şeyler
- **SCHISM yıllık koşu** (WSL, `runs/schism/run_year.sh`, `nohup`, 20 Eyl 16:13'te başladı): ay başına ~3 sa 20 dk;
  Eylül 2025 bitti (`data/processed/schism_surface_2025-09.nc`, 562 MB), Ekim 19:33'te başladı → yıl ~21 Eyl akşamı biter.
  Durum: `python scripts\50_year_pipeline.py status` (Windows) ya da `tail -1 runs/schism/y2025-10/outputs/mirror.out` (WSL).
  Kesilirse aynı komutla yeniden başlat; biten aylar atlanır. Bir ay "HATA" verirse `runs/schism/<ay>/run.log` ve
  `outputs/fatal.error`'a bak; `python scripts\50_year_pipeline.py prepare --month YYYY-MM --force` ile yeniden hazırlanabilir.
- **OpenDrift aylık partiler**: `python scripts\51_year_opendrift.py --mode both` — hazır yüzey dosyası olan ayları koşar,
  bitenleri atlar. `runs/opendrift/year/sources_2025-09/` klasörü açılmış ama `summary.txt` yok → ya sürüyordu ya yarım kaldı;
  `--force` ile tekrar koş. Yıl bitince `52_seasonal_maps.py` ve `60_web_data.py --year`.
- **Web sitesi**: `web/` hazır ve commit'li; depoda **uzak sunucu yok**. Kullanıcı: GitHub'da `izmir-litter-drift` deposu aç,
  `git remote add origin …`, `git push -u origin main`, Settings → Pages → Source "GitHub Actions". `web/config.js` içindeki
  `repo` adresi kullanıcı adına göre düzeltilmeli (`oguzcanozupek` varsayıldı).

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
