# Faz 3 — Model çekirdeği: SCHISM (Delft3D FM lisans istediği için)

**Durum (19 Eylül 2026):** Delft3D FM Suite'in indirilen sürümü çalışmak için Deltares'in FlexNet
lisansını (DS_Flex + lisans dosyası) istiyor. Deltares'in kendi sayfalarına göre önceden derlenmiş
çekirdekler "Service Package" (ücretli sözleşme) ile veriliyor; ücretsiz yol yalnız kaynak koddan derlemek
(Windows'ta Visual Studio + Intel Fortran — ağır). Yüklediğin üç PDF (License Administration Guide,
Common Files Release Notes, License Management Installation Manual) lisans *yöneticisi* kurulum
kılavuzları; lisans dosyasının kendisini vermiyor.

**Karar:** hidrodinamik çekirdek olarak **SCHISM** (Apache 2.0, VIMS). Gerekçe:
- Tam açık kaynak, lisans yok; Ubuntu'nun hazır paketleriyle ~5 dakikada derleniyor (bu betik
  Ubuntu 24.04'te test edildi, aynısı Windows'ta WSL2 Ubuntu'da çalışır).
- Kıyı/körfez çalışmalarında en yaygın açık kaynak 3B yapılandırılmamış ağ modeli; hakem açısından sorunsuz.
- OpenDrift'in **yerel SCHISM okuyucusu** var (`reader_schism_native`) — Lagrangian adım için Delft3D'den daha kolay.
- Karma üçgen/dörtgen ağ destekler → meshkernel ile ürettiğimiz ağ dönüştürülerek kullanılır.

**Delft3D FM tarafından taşınanlar:** ağ (`izmir_net.nc` → `hgrid.gr3`), açık sınır polyline'ı,
gözlem noktaları, batimetri, indirilen CMEMS/ERA5 dosyaları (dfm_tools indirme fonksiyonları kalır).
Yeni yazılacak dönüştürücüler: ağ → hgrid, CMEMS → `elev2D.th.nc / TEM_3D.th.nc / SAL_3D.th.nc / uv3D.th.nc`,
ERA5 → `sflux/sflux_air_1.*.nc`, `param.nml`, `vgrid.in` (LSC2 veya sigma, 10–15 katman), `bctides.in`.

## Kurulum (senin tarafın)

1. WSL2 Ubuntu (yönetici PowerShell):
   ```
   wsl --install -d Ubuntu-24.04
   ```
   Yeniden başlat; ilk açılışta Linux kullanıcı adı/şifre belirle.
2. Ubuntu terminalinde depoya git (Windows diski `/mnt/c` altında) ve derle:
   ```
   cd /mnt/c/Users/PC/source/repos/izmir-litter-drift
   bash scripts/wsl_build_schism.sh
   ```
   Sonunda `schism develop / git hash ...` yazarsa tamam; çalıştırılabilir dosya `~/schism/pschism`.
3. WSL içindeki Python için ayrı bir ortam gerekmez: model girdilerini Windows tarafındaki
   `litter` conda ortamıyla üretiriz, WSL yalnız çekirdeği koşturur. Girdi/çıktı klasörü ortak (`/mnt/c/...`).

Not: `/mnt/c` üzerinden koşmak biraz yavaştır; uzun koşularda `runs/` klasörünü WSL diskine
(`~/runs`) kopyalayıp orada koşturmak 2–3 kat hız kazandırır.

## Sıra

1. `31_mesh_to_schism.py`: `izmir_net.nc` + `izmir.pli` → `hgrid.gr3`, `hgrid.ll`, açık sınır düğümleri.
2. `32_forcing_to_schism.py`: CMEMS günlük 3B alanlar → sınır `.th.nc`; ERA5 → `sflux`.
3. `33_param.py`: `param.nml` (2B barotropik önce, sonra 3B), `vgrid.in`, `bctides.in`.
4. 1 haftalık 2B koşu → kararlılık; 3B koşu → Sayın & Eronat desenleriyle karşılaştırma.
5. OpenDrift `reader_schism_native` ile Bostanlı testini yerel akıntıyla tekrar.

## Durum — 19 Eylül 2026, akşam

- `31_mesh_to_schism.py`: gerçek ağ (76.326 düğüm) → `hgrid.gr3`. Kıyıda EMODnet'in NaN bıraktığı 10.529 düğüm en yakın
  deniz hücresinden dolduruldu (Delft3D adımındaki koyu kare artıkları buradan geliyordu); 301 tuzla/kara artığı yüz,
  21 "kıstırma" (papyon) yüzü ve kopan parçalar atıldı → 76.087 düğüm, 76.544 eleman, 1 açık sınır (394 düğüm,
  batı + kuzey kenarı), 52 ada. Derinlik 1–685 m, medyan 7,8 m; kenar 108–488 m.
- `33_schism_setup.py --mode smoke`: 2B barotropik, sabit su seviyesi, zorlama yok, 6 saat.
- **Duman testi başarılı** (bulut sanal makinesi, 1 hesap çekirdeği + 2 scribe): 360 adım × 60 s, 2 dk 37 s,
  "Run completed successfully"; su seviyesi ve hız sıfır kaldı (beklenen), kuru düğüm yok. Ağ ve sınır tanımı geçerli.
- Hız tahmini: 2B ~0,4 s/adım/çekirdek → 7 gün 2B ≈ 1 saat (1 çekirdek); 4 çekirdekte ~20 dk. 3B 11 katman ~5–8×.

Sonraki: `32_forcing_to_schism.py` (CMEMS → elev2D/uv3D/TEM/SAL .th.nc, ERA5 → sflux) ve 2B rüzgârlı 1 hafta.

## Zorlama dosyaları — `32_forcing_to_schism.py`

- `download`: Copernicus MED (zos saatlik 2B; so/thetao/uo/vo günlük 3B, `model_params.yaml` → `cmems_datasets`) + ERA5
  (u10, v10, msl, t2m, d2m) → `data/raw/forcing/`. Kullanıcının bilgisayarında çalışır.
- `boundary`: açık sınır düğümlerine en yakın geçerli CMEMS hücresi (KD-ağacı), zamanda doğrusal interpolasyon →
  `elev2D.th.nc` (saatlik); `--mode 3d` ile ayrıca `uv3D/TEM_3D/SAL_3D.th.nc` (6 saatlik, sigma seviyelerine dikey
  interpolasyon) ve `temp.ic/salt.ic` (CMEMS yüzey alanı).
- `sflux`: ERA5 → `sflux/sflux_air_1.N.nc` (günlük; **dosya numarası sıfır dolgusuz**: `.1.nc`, `.2.nc` …),
  `uwind vwind prmsl stmp spfh`, `time` günler, `base_date` koşu başlangıcı; `sflux_inputs.txt` boş namelist.
- `.th.nc` kuralı: kayıt k → t = k·time_step, t=0 koşu başlangıcı (`--start` 00:00 UTC); SCHISM ilk iki kaydı okur,
  time_step < dt ise durur.
- Test (bulut, sentetik CMEMS + gerçek ERA5 rüzgârı, 1 gün 2B): dosyalar okundu, koşu ilerledi (0,65 s/adım, 1 çekirdek).

## İlk rüzgârlı 2B koşu — 19 Eylül 2026, gece

- Girdi: gerçek ERA5 rüzgârı (6 Eylül 2026, KKD 4–5 m/s), sentetik CMEMS su seviyesi (gerçek CMEMS indirmesi kullanıcının
  makinesinde yapılacak), 1 gün, dt=60 s, çıktı 30 dk.
- İlk deneme **kararsızdı**: açık sınırın kıyıya girdiği sığ uçlarda (Aliağa önü 26.82–26.85°D ve batı kenarın
  Çeşme ucu) 9. saatten sonra 5 m/s'lik sınır jetleri, ±0,9 m su seviyesi. Neden: yalnız-su-seviyesi sınırı (iettype=4)
  sığ suda kıyıya dayanınca serbest akış jeti üretiyor.
- Düzeltme: `min_open_depth_m: 30` — 30 m'den sığ kutu-kenarı düğümleri kara duvarı oldu; açık sınır 394 → 274 düğüm,
  4 parça (kuzey kenarında 2 kısa, ana batı+kuzey yay, batıda kısa). Ayrıca sflux dosyaları gün sonunun 2 saat ötesine
  uzatıldı (SCHISM son adımda bir sonraki kaydı istiyor) ve çıktı yığını 12 saate indirildi.
- Sonuç: **kararlı** — hız maks 0,24 m/s (sığ kıyı düğümleri), medyan iç körfez ~2 cm/s, orta ~4, dış ~4 cm/s;
  su seviyesi ±0,2 m (sınır sinyali + rüzgâr yığılması), kuru düğüm yok. t=24 h'te Yenikale'den iç körfeze ~5 cm/s giriş,
  iç körfez batı yarısında saat yönünde dönüş eğilimi (`plots/ic_korfez_t047.png`). Süre: 1 gün 2B = 13 dk (1 çekirdek).
- Betikler: `34_plot_schism.py` özet + görsel üretir.

Sonraki: kullanıcı makinesinde gerçek CMEMS ile 7 gün 2B; ardından 3B (11 katman) aynı hafta ve OpenDrift bağlantısı.

## 7 günlük 2B koşu (gerçek CMEMS + ERA5, 6–13 Eylül 2026) — kararsızlık ve düzeltme

- Kullanıcı makinesi, WSL2, 4 çekirdek: 7 gün 2B ≈ 22 dk. Koşu bitti ama **36. saatten sonra kararsız**: hız maks 7,1 m/s
  (63,5 h), su seviyesi −0,86..+0,56 m, son adımda 7.385 düğümde hız > 0,5 m/s.
- Tanı (`out2d_4/5/6/14.nc`): bozulma iki yerde başlıyor — (a) açık sınırın KB köşesi (26,34°D 38,90°K, ~350 m derin) ve
  (b) `min_open_depth_m: 30` filtresinin kuzey kenarın *ortasında* bıraktığı yapay kara duvarları (26,825–26,848°D,
  derinlik 1–43 m). Duvarların iki yanında su seviyesi yığılıp (+0,49) boşalıyor (−0,86) ve 6–7 m/s'lik jetler çıkıyor;
  1 günlük testte görünmemesinin nedeni bozulmanın 36 h sonra büyümesi.
- Kök neden: yalnız-su-seviyesi açık sınırı (iettype=4, hız serbest) + sınır ortasında kesintiler. Sığ uçları kesmek jeti
  yer değiştirdi, çözmedi.
- Düzeltme (bu sürüm):
  1. `min_open_depth_m: 0` — kutu kenarı baştan sona tek açık sınır (394 düğüm), duvar yok.
  2. Sınırda su seviyesi **+ gevşetmeli hız** (`bctides.in`: `394 4 -4 0 0`, ardından tek satırda `1.0 0.3` =
     içeri akışta CMEMS'e tam, dışarı akışta %30 bağlanma). `uv3D.th.nc` 2B'de CMEMS günlük 3B `uo/vo`'nun
     derinlik ortalamasından (yeni `depth_avg_series`), 6 saatlik, 2 seviyeye kopyalanarak yazılıyor.
  3. Yatay viskozite açık: `ihorcon=1`, `hvis_coef0=0.025` (sınır gürültüsünü söndürür); `dramp=1.0`.
  Not: SCHISM gevşetme katsayılarını `vobc1 vobc2` olarak **aynı satırdan** okur (`schism_init.F90:2644`); iki satıra
  bölünce "Bad real number in item 2 of list input" hatası veriyor.
- Doğrulama (bulut, aynı gerçek CMEMS+ERA5 dosyaları, 6–9 Eylül, 3 gün 2B, 1 çekirdek ≈ 72 dk): **kararlı**. Hız maks
  0,47 m/s (54,5 h; Karaburun batı kıyısında 1–5 m derinlikteki düğümler, 7 m/s rüzgâr altında — fiziksel), hiçbir adımda
  hız > 0,5 m/s düğümü yok, su seviyesi −0,15..+0,09 m (CMEMS sınırı ± rüzgâr yığılması), kuru düğüm 0. Medyan hız iç körfez
  1–3 cm/s, orta 2–6, dış 4–9 cm/s. Önceki koşuda 63,5 h'te 7,1 m/s olan yerde şimdi 0,34 m/s.
- Kullanıcı makinesinde tekrar: `31` (hgrid, 394 açık düğüm) → `33 --mode 2d --days 7` → `32 all --mode 2d` → WSL `mpirun -np 22`.

- **7 günlük 2B koşu (kullanıcı makinesi, 22 çekirdek, 6–13 Eylül 2026): kararlı.** 336 kayıt; hız maks 0,40 m/s (42,5 h),
  hiçbir adımda hız > 0,5 m/s düğümü yok, su seviyesi −0,15..+0,10 m, kuru düğüm 0. Medyan hız: iç körfez 0,7–3 cm/s,
  orta 1–6, dış 3–7 cm/s; rüzgârın zayıfladığı 4.–6. günlerde tüm alan 1–4 cm/s'e iniyor (`plots/summary.txt`).
  t=168 h iç körfez haritası: Yenikale boğazından doğuya doğru 5–10 cm/s giriş, iç körfez ortasında zayıf (<2 cm/s)
  dağınık alan, Bostanlı–Karşıyaka önünde doğuya kıyı akıntısı, Bayraklı köşesinde küçük dönüş (`plots/ic_korfez_t335.png`).

Sonraki: 7 günlük sonucu Sayın & Eronat desenleriyle karşılaştır; 3B (11 sigma) aynı hafta; `40_schism_to_opendrift.py`.

## 3B kurulum (baroklinik, 11 sigma) — 20 Eylül 2026

- `33 --mode 3d`: `ibc=0 ibtp=1`, `itur=3` (k-kl, KC), `itr_met=3 h_tvd=5` + `tvd.prop` (her elemanda 1), `flag_ic=2`
  → `ts.ic` (CMEMS bölge-ortalaması dikey T/S profili; biçim: satır sayısı, sonra `no z T S`, z dipten yüzeye artan,
  en üst +5 m tampon), `diffmin/diffmax/albedo/watertype.gr3`. `ihconsv=0`: ısı akısı kapalı — açmak için ERA5 `ssrd/strd`
  indirip `sflux_rad_1.N.nc` yazmak gerekir (ilk 3B sürümde T sınırdan taşınır, yüzeyden ısınmaz; 1 haftalık koşuda kabul edilebilir).
- `32 --mode 3d`: `TEM_3D/SAL_3D/uv3D.th.nc` (6 saatlik, sigma seviyelerine dikey interpolasyon; sınırda T 14,7–24,2 °C,
  S 39,2–39,4), `ts.ic`, ayrıca `temp.ic/salt.ic` (flag_ic=1 yedeği).
- vgrid: SZ, kz=1, h_c=20 m, theta_b=0,7, theta_f=3 → yüzeye doğru sıklaşan 10 katman.
- Bulut duman testi (1 saat, gerçek veri, 1 çekirdek + 4 scribe): "Run completed successfully"; ~5 s/adım (2B'nin ~5 katı).
  Yüzey hızı maks 0,08 m/s, dip ~0, NaN yok, su seviyesi ±1 cm. Giderilen hatalar: `tvd.prop` eksikti; `ts.ic` satırları
  sıra numarası ister ("Bad integer for item 1"); 3B çıktı bayrakları `iof_hydro(18)/(19)` (T/S) — 14/15 rüzgârdı.
- **Scribe sayısı:** 3B'de çıktı değişkeni başına bir scribe gerekir (horizontalVelX/Y, T, S, zCoordinates → 5; 6 verilir):
  `mpirun -np <çekirdek+6> ~/schism/pschism 6`. 2B'de 2 yeter. Az verilirse "Too few scribes" ile durur.
- Koşu klasörü ayrı: `--run izmir3d` (33 hgrid'i `izmir`den kopyalar); 2B sonuçları `izmir/` içinde kalır.
- Tahmini süre (kullanıcı, 18 hesap çekirdeği): 7 gün 3B ≈ 30–45 dk.

## 3B 7 günlük koşu ve OpenDrift bağlantısı — 20 Eylül 2026

- **3B 7 gün (kullanıcı, 18 çekirdek + 6 scribe): kararlı.** Derinlik-ort. alan 2B ile aynı düzeyde (hız maks 0,43 m/s);
  yüzey katmanı derinlik-ortalamasının ~2 katı: t=168 h yüzey medyan iç körfez 1,8 cm/s, orta 3,1, dış 6,5 cm/s, maks 0,25 m/s.
  Yüzey sıcaklığı 20,4–23,7 °C (medyan 22,9; başlangıç 23,4 — ısı akısı kapalı, soğuma sınırdan/karışımdan), tuzluluk 39,28–39,36.
- `40_schism_to_opendrift.py`: scribe çıktısı (out2d + horizontalVelX/Y) → OpenDrift `reader_schism_native` biçimi
  (`elev`, `dahv[time,node,2]`, üçgenlenmiş `SCHISM_hgrid_face_nodes`, `time` saniye). OpenDrift 1.14 okuyucusu enlem-boylam
  ağda 3B hızı kullanamıyor (`use_3d` kapanır; kodda `pdb.set_trace()` bile var) → 3B koşunun **en üst sigma katmanı**
  `dahv` adıyla yazılır; yüzen çöp için gereken zaten yüzey akıntısı. 2B koşuda `--layer dav`. Kuru düğümde hız 0.
  Dosya: 7 gün 30 dk × 76 bin düğüm ≈ 280 MB.
- `41_opendrift_schism.py`: OceanDrift; akıntı SCHISM, rüzgâr ERA5 (CDS dosyası `x_wind/y_wind` adlarıyla `data/processed/`e
  yazılır), kıyı maskesi GSHHS f (`reader_global_landmask`; ağın kıyısı da GSHHS f — tutarlı), windage %2, difüzyon 5 m²/s,
  RK4, stranding. Stokes drift yok (CMEMS dalga iç körfezi çözmüyor; sonraki: WWM ya da rüzgârdan parametre).
  Çıktı: `runs/opendrift/<koşu>_<nokta>_<tarih>/{track.nc, track.png, summary.txt, zones.csv, endpoints.csv}` —
  `zones.csv` kıyı bölgesi payları (`config/coast_zones.csv`), `endpoints.csv` parçacık başına son konum (web sitesi girdisi).
- Bulut testi (2B derinlik-ort. alan, 6–9 Eylül, Bostanlı 300 parçacık): tümü 39 saatte kıyıya vurdu; %97 İnciraltı–Balçova
  (Z04), %3 Bostanlı (Z01); medyan vurma süresi 25 saat. 6–7 Eylül'ün K–KD rüzgârı çöpü iç körfezi güneye geçirip
  İnciraltı sahiline yığıyor (`docs/opendrift_bostanli_2d_test.png`). Koşu süresi 4 s.
- Bilinen sınırlar: okuyucu dışbükey zarf + Delaunay doğrusal interpolasyon (kara üzerinden komşuluk; kıyıya vurma GSHHS
  maskesiyle karar verildiği için pratikte sorun çıkmadı); `config/coast_zones.csv` Z12 satırında eksik virgül düzeltildi.

## Bostanlı testi (3B yüzey alanı) ve kaynak → kıyı matrisi — 20 Eylül 2026

- Kullanıcı makinesi, `41 --run izmir3d` (500 parçacık, 6 Eylül 00:00, %2 windage): **tümü 20 saatte kıyıya vurdu, %98
  İnciraltı–Balçova (Z04), medyan 15 saat** (2B derinlik-ort. alanla 25 saatti: yüzey akıntısı rüzgârla aynı yönde ve ~2 kat
  hızlı). Yörüngeler iç körfezi düz bir hatla GGB yönünde geçiyor (`runs/opendrift/izmir3d_P_bostanli_20260906/track.png`).
- `42_release_matrix.py`: (a) `--mode sources` — `config/sources.csv`'deki 23 alan-içi kaynaktan (S06–S08 koordinatsız,
  M03/M04/F04 alan dışı) ilk 3 gün her 6 saatte 50 parçacık; (b) `--mode grid` — `--cell_km` aralıklı deniz hücrelerinden
  24 saat arayla 3 salım (web sitesinin "nereden atarsam" katmanı). Kaynaklar en yakın ≥2 m derinlikli ağ düğümüne
  kaydırılır (iç körfezde 400–1100 m açığa; kaynak koordinatları zaten yaklaşık). Çıktı: `matrix.csv` (kaynak/hücre ×
  bölge payları, kıyıya vurma oranı, medyan süre, baskın bölge), `endpoints.csv`, `cells.geojson` (grid), `matrix.png`.
- Bulut testi (2B alan, 6–9 Eylül): kaynaklar — iç körfez doğu kaynakları (Meles, Manda, Arap, Laka, Alsancak, Bayraklı) →
  %88–97 Karşıyaka–Bayraklı kıyısı 6–9 saatte; Bostanlı/Karşıyaka/Mavişehir → %87–100 İnciraltı–Balçova 18–24 saatte;
  Gediz ağzı → %60 Güzelbahçe–Urla 42 saatte; Foça/Mordoğan → Karaburun kıyısı. Izgara (2 km, 696 hücre): %89 kıyıya
  vurdu, Karaburun batı+doğu kıyıları en büyük alıcı; orta körfez kuzey yarısı Karaburun'a, güney yarısı Güzelbahçe–Urla'ya
  gidiyor; dış körfez KB'si alan dışına çıkıyor (`docs/matrix_grid_2d_test.png`). Tek haftalık K rüzgârı senaryosu — mevsimsel
  genelleme için yıllık koşu gerekir.

## Izgara matrisi (3B yüzey, 1 km, 6–13 Eylül) ve kıyı bölgelerinin yenilenmesi — 20 Eylül 2026

- Kullanıcı, `42 --mode grid --cell_km 1`: 2.627 deniz hücresi × 3 salım × 20 = 157.620 parçacık, **%100 kıyıya vurdu**,
  medyan 15 saat. İlk sürümde %31 "Z12" çıktı; `endpoints.csv` incelendi: ~28.500 parçacık batı sınırından çıkıp Koyun
  Adaları/Sakız'a (26,2–26,35°D) vurmuş (gerçek "alan dışı"), ~12.000 Ildır–Gülbahçe körfezine, ~4.500 Karaburun batı
  kıyısına, ~2.000 orta körfez adalarına — bunlar kıyı kutularının kapsamadığı gerçek kıyılardı.
- `config/coast_zones.csv` yenilendi: kutular **sırayla** denenir (ilk eşleşen); adalar önce. Yeni: Z13 Uzunada, Z14 Hekim–
  Pırnarlı–Yassıca adaları, Z15 Ildır–Gülbahçe körfezi, Z16 Karaburun batı kıyısı; Z07 Çamaltı–Sasalı'yı, Z10 Çandarlı'yı
  kapsayacak şekilde genişletildi; Z03/Z04 38,38'e indirildi. Alan içinde kutusuz kalan kıyı noktası "Z00" olarak sayılır
  ve uyarı basılır (bulut testinde 0'a indi). Z12 = alan dışına çıkan + denizde kalan.
- Toplulaştırma `scripts/od_agg.py`'ye alındı (41/42 ortak); `43_rezone.py` var olan koşuyu OpenDrift'i tekrar koşturmadan
  yeni kutularla yeniden toplulaştırır (`origins.csv`/`meta.json` yoksa `cells.geojson`/`matrix.csv`'den okur).
- Bulut (2B alan, 3 gün) ızgara haritası yeni kutularla: orta körfezin doğu yarısı Uzunada ve orta körfez adalarına, kuzey
  yarısı Karaburun doğu kıyısına, güneybatı Ildır–Gülbahçe'ye; batı sınırına yakın hücreler alan dışına. Uzunada ve orta
  körfez adaları K rüzgârında belirgin birer tuzak (`docs/matrix_grid_2d_test.png`).
- Sınır: batıdan çıkan parçacıklar alan dışında yalnız rüzgârla sürüklenir (akıntı 0) — Yunan adalarına varış sayısı nitel.
  Makale için alanın batıya (Sakız'a kadar) genişletilmesi düşünülebilir; şimdilik "alan dışı" olarak raporlanır.

## İlk tam matris — 6–13 Eylül 2026 haftası, 3B yüzey alanı (kullanıcı makinesi, 20 Eylül)

**Kaynak modu** (23 kaynak × 13 salım × 50 = 14.950 parçacık): tümü kıyıya vurdu; medyan 3 saat (kaynaklar kıyıya 0,4–2 km).
Ortalama bölge payları: İnciraltı–Balçova %37, Karşıyaka–Bayraklı %22, Güzelbahçe–Urla %14, Karaburun doğu %7, Kordon–Konak %6.
- İç körfez doğu grubu (Meles, Manda, Arap, Laka, Alsancak Limanı, Bayraklı İskelesi) → %79–94 **Karşıyaka–Bayraklı**, 3–6 saat.
- İç körfez kuzey/batı grubu (Bostanlı Deresi, Karşıyaka ve Bostanlı iskeleleri, Levent Marina) → %96–100 **İnciraltı–Balçova**, 15 saat.
- Güney kıyı kaynakları (Poligon, Balçova, Üçkuyular; Konak %75, Pasaport %51) → İnciraltı–Balçova, 3–6 saat; Ilıca Deresi → Güzelbahçe–Urla.
- **Gediz ağzı** → %59 Hekim–Pırnarlı–Yassıca adaları, 24 saat (2B alanda Güzelbahçe–Urla'ydı: yüzey akıntısı adalara yöneltiyor).
- Foça → Karaburun doğu kıyısı %70; Mordoğan → yerinde %87; Aliağa → yerinde %94; Çeşme → yerinde %100.

**Izgara modu** (2.627 hücre × 3 salım × 20 = 157.620): tümü kıyıya vurdu, medyan 15 saat. Karaburun doğu kıyısı %29, alan dışı
(Koyun Adaları/Sakız) %19, Çeşme %12, Ildır–Gülbahçe %10, Güzelbahçe–Urla %9, Foça–Gediz %5, Karaburun batı %4, Aliağa %4,
adalar %5, İnciraltı %2. Uzunada ve orta körfez adaları K rüzgârında tuzak.

Yorum: 6–13 Eylül'de ERA5 rüzgârı K–KD, ortalama 4,4, maks 12,6 m/s (tipik yaz sonu etezyen). Bu rejimde çöp iç körfezde
1 günden kısa sürede karşı kıyıya geçiyor, körfezin batı yarısı Ege'ye boşalıyor. Kış lodos rejiminde tablo tersine dönecek —
bu yüzden **yıllık koşu** şart. Tek haftalık sonuç makalede "senaryo örneği", web sitesinde "bu haftanın haritası" olarak kullanılabilir.

