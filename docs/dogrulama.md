# Doğrulama (validasyon) planı

> Modelin doğruluğunu dört katmanda gösteriyoruz. Katman 1 ücretsiz ve bugün yapılabilir; Katman 2 (drifter) makalenin en
> güçlü argümanı; Katman 3 drifter olmazsa B planı; Katman 4 hiç gözlem gerektirmez.
> Görev listesi: Claude dokümanı "Yapılacaklar" sekmesi, **Faz 3B**.

## Neyi doğruluyoruz
Zincir iki aşamalı: **SCHISM** (hidrodinamik) → **OpenDrift** (Lagrange sürüklenme). İkisi ayrı ayrı doğrulanmalı.
SCHISM'i zorlama alanlarıyla (deniz seviyesi, rüzgâr, sıcaklık) sınarız; OpenDrift'i ancak gerçek sürüklenme
gözlemiyle (drifter) ya da birikim deseniyle (plaj çöpü) sınayabiliriz. Yalnız SCHISM'i doğrulamak yetmez —
hakem doğrudan "parçacık yolları doğru mu?" diye soracak.

## Katman 1 — Zorlama alanları (ücretsiz, hemen)

### 1.1 Deniz seviyesi — Menteş mareografı
- İstasyon: **Menteş**, 38,4277°N 26,7166°E (Çeşme yarımadası, dış körfez ağzı). İşleten: Harita Genel Müdürlüğü (TUDES).
- IOC Sea Level Monitoring'de `ment` koduyla **operasyonel, radar sensör, 30 sn örnekleme, ücretsiz**.
  Eylül 2025 – Ağustos 2026 penceresi tam kapsanıyor (test edildi).
- İstasyon sayfası: https://www.ioc-sealevelmonitoring.org/station.php?code=ment
- API (gün/hafta bazında döngü kur, uzun aralık tek istekte gelmez):
  `https://www.ioc-sealevelmonitoring.org/service.php?query=data&code=ment&timestart=2025-09-01T00:00:00&timestop=2025-09-02T00:00:00&format=json`
- Metrikler: RMSE, bias, korelasyon; ayrıca gelgit harmonikleri (M2, S2, K1, O1) — `utide` ya da `ttide` ile ikisinden de
  çıkarılıp genlik/faz karşılaştırılır.
- Emsal: Bayram & Doğan (2022), ADCIRC ile İzmir Körfezi gelgit modelini aynı istasyonla doğrulamış.
  https://dergipark.org.tr/en/pub/uujes/issue/74654/1194112
- Not: PSMSL'deki Menteş kaydı (ID 1679) yalnız 1985–2009 **aylık ortalama** — saatlik yok, sadece datum/trend kontrolü için.
  TUDES'in kendi portalı ücretli abonelik ürünü gibi görünüyor; IOC'yi kullan, resmî seriyi yalnız hakem isterse talep et.

### 1.2 Rüzgâr — LTBJ METAR
- **Iowa State IEM ASOS arşivi**, ücretsiz, hesapsız, saatlik (:50'de).
  Arayüz: https://mesonet.agron.iastate.edu/request/download.phtml?network=TR__ASOS
- Doğrudan indirme:
  `https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=LTBJ&data=sknt&data=drct&data=gust&year1=2025&month1=9&day1=1&year2=2026&month2=9&day2=1&tz=Etc/UTC&format=onlycomma&latlon=no&missing=M&trace=T&direct=no&report_type=3&report_type=4`
- İstasyonlar: **LTBJ** Adnan Menderes (38,2667 / 27,1500, 120 m) — çalışıyor. LTBK Gaziemir 2023'te kapandı.
  **LTBL Çiğli** meta verisi aktif görünse de sorgularda boş dönüyor (muhtemelen askeri, METAR yayınlamıyor).
  LTFA test edilemedi. Pratikte elde **yalnız LTBJ** var.
- Kısıtlar: istasyon iç kesimde ve 120 m rakımda → körfez üzerindeki imbatı tam temsil etmez; METAR rüzgârı 10 dk ortalama,
  yön 10° adımlı, hız knot tamsayı. **Kullanım:** ERA5'in zamansal doğruluğu (geçişler, fırtına zamanlaması) için kullan;
  mutlak deniz üstü hız kalibrasyonu için tek başına yeterli sayma.
- MGM istasyon verisi ücretli: https://www.mgm.gov.tr/site/urunler.aspx?u=veriislem

### 1.3 Yüzey sıcaklığı — Copernicus SST
- **SST_MED_SST_L4_NRT_OBSERVATIONS_010_004**, UHR **1/100° (~1 km)**, günlük, 2008→bugün, ücretsiz.
  https://data.marine.copernicus.eu/product/SST_MED_SST_L4_NRT_OBSERVATIONS_010_004/description
- HR 1/16° (~7 km) iç körfezi tek piksele sıkıştırıyor — **kullanma**. OSTIA 0,05° de çok kaba.
- Kıyıya bitişik piksellerde kara kontaminasyonu var; körfez ekseni boyunca kıyıdan ≥2 piksel içeride örnekle.
- İnterpolasyonsuz alternatif (bulut boşluklu ama gerçek gözlem): SST_MED_SST_L3S_NRT_OBSERVATIONS_010_012.
- **Konumlandırma:** SST sürüklenmeyi doğrulamaz, SCHISM'in stratifikasyonunu doğrular (o da baroklinik akıntıyı etkiler).
  Makalede "dolaylı doğrulama" diye yaz, ana argüman yapma. (Isı akısı şu an kapalı — bu karşılaştırma onu da sınar.)

## Katman 2 — Lagrange doğrulaması (asıl kanıt)

### 2.1 Drifter
- Açık tasarım: Hut, Thatoe Nwe Win & Bogaard (2020), *Geosci. Instrum. Method. Data Syst.* — Particle Electron + Asset
  Tracker shield, SparkFun OpenLog SD kaydedici, güneş paneli, 1200 mAh batarya. Kod ve şemalar Zenodo'da
  (doi:10.5281/zenodo.1485899). PDF: https://gi.copernicus.org/preprints/gi-2019-27/gi-2019-27-AR2.pdf
  Parça listesinden birim maliyet ~150–200 USD mertebesinde çıkıyor (makalenin beyanı değil, çıkarım).
- Hazır alternatif: Student Drifters, 1.200–1.300 USD/adet (https://studentdrifters.org/) — bizim için pahalı.
- **İzmir'e özel tasarım notu:** körfez tamamen GSM/LTE kapsamında ve en geniş yeri ~20 km → **Iridium gereksiz**,
  GSM/LTE-M modem yeterli. Yüzen çöp taklidi için **drogue'suz** (yelkensiz) yap — amaç rüzgâr sürüklenmesi dahil
  yüzey hareketini yakalamak. SD kart yedeği şart (GSM kesilirse veri orada), aynı gün toplama planla.

### 2.2 İzinler
- **İzmir Liman Başkanlığı** — Limanlar Yönetmeliği m.22: şamandıralama, dalış vb. faaliyetler öncesinde liman
  başkanlığından izin zorunlu. Serbest yüzen GPS drifter'ın bu kapsamda sayılması kuvvetle muhtemel, yazılı sor.
  https://tkygm.uab.gov.tr/uploads/pages/limanlar-daire-baskanligi/limanlar-yonetmeligi.pdf
  Aynı yönetmelik m.12(4): İzmir Körfezi'nde trafik ayırım düzeni var → bırakma noktalarını gemi trafiğinden uzak seç.
- **SHOD** — Seyir, Hidrografi ve Oşinografi Hizmetleri Yönetmeliği m.14–15: araştırma faaliyeti için seyir duyurusu,
  faaliyetten **en az 15 gün önce** bildirim, sefer sonuç raporu 60 gün içinde. https://www.shodb.gov.tr/
  Yabancı ortaklı araştırmada ayrıca Dışişleri + MSB görüşü gerekiyor; tamamen yerli çalışmada gerekmiyor görünüyor.
- **Sahil Güvenlik** — ayrı bir drifter prosedürü bulunamadı; liman başkanlığına başvururken bildirim gerekip
  gerekmediğini doğrudan sor.

### 2.3 Metrikler
- **Normalized Cumulative Lagrangian Separation (NCLS)** + **Liu-Weisberg skill score**.
- Kurgu (Castro-Rosero vd. 2023 emsali): gözlenen drifter konumlarından saatte N parçacık salınır, tahmin ufku boyunca
  model ve gözlem yolu karşılaştırılır. https://doi.org/10.3389/fmars.2023.1213333
- **Ufuk seçimi kritik:** Révelard vd. (2021) — skill score ufuk uzadıkça *yapay olarak* artıyor, kıyı alanlarında
  **6 saatlik ufuk** öneriliyor; klasik SS negatifleri sıfıra kırptığı için ortalamalar yanlı, **SS\*** kullan;
  n=1 evrensel değil, senaryoya göre kalibre et. https://doi.org/10.3389/fmars.2021.630388
- Hedef mertebe: Ghaffari vd. (2025), OpenDrift + 24 GPS drifter, 3B skill 0,833 / 2B 0,804, bitiş noktası hatası <100 m.
  https://doi.org/10.3389/fmars.2025.1612395

## Katman 3 — Kıyı birikim deseni (drifter olmazsa B planı)

- **EMODnet Chemistry Beach Litter** — 12.390 kayıt, 2001–2020, 582 plaj, **CC BY 4.0**, doğrudan indirilebilir.
  ZIP: https://nodc.ogs.it/repository/aggregated-datasets/litter/EMD_beach_litter_Europe_2021_unrestricted.zip
  Katalog: https://emodnet.ec.europa.eu/geonetwork/srv/api/records/2b444000-036e-49ee-92c8-e5b265cf4a4f
  Türk kurumları (İÜ Deniz Bilimleri, ODTÜ DBE) veri sağlayıcı listesinde. **İzmir kaydı var mı — indirip kontrol et.**
- **Urla transektleri** — Güngören & Başaran (2021), *Ege J. Fish. Aquat. Sci.* 38(1): Kum Denizi Plajı **0,48 adet/m²**
  (130×20 m), Demircili Koyu **1,34 adet/m²** (120×13 m); Ekim 2017 – Ekim 2018, 4 mevsim, >2,5 cm çöpler.
  https://dergipark.org.tr/tr/download/article-file/963814
- **TÜRÇEV / Mavi Bayrak Deniz Çöpleri İzleme** — Ege'de 9 alan (Muğla, Aydın, İzmir/Çeşme), yılda 4 kez, 200+ kategori,
  EEA Marine LitterWatch'a yükleniyor. https://www.mavibayrak.org.tr/turkiye/icerik.aspx?icerik_refno=61 · (312) 222 12 90
  EEA veri seti: https://www.eea.europa.eu/en/datahub/datahubitem-view/fc3a040f-ee73-4747-97c1-458c02108cf5
- **DEN-İZ (ÇŞİDB + TÜBİTAK MAM ÇTÜE)** — ulusal izleme; ham veri kamuya açık değil, resmî yazı/CİMER gerekiyor.
  https://ctue.mam.tubitak.gov.tr/tr/icerik/2019-2022-donemi-denizlerde-butunlesik-kirlilik-izleme-programi-den-iz
- Metrik: bölge başına modellenen birikim yoğunluğu ↔ ölçülen çöp yoğunluğu, **Pearson/Spearman**.
  Emsal: Garcia-Gorriz vd. (2026), karaya vurmuş makroplastik için Akdeniz r=0,73, Karadeniz r=0,88.
  https://doi.org/10.3390/oceans7020026
- Sapmaların liman, nehir ağzı ve lagünlerde yoğunlaştığı biliniyor — tartışma bölümünde bekle.

## Katman 4 — İç tutarlılık (gözlem gerektirmez)

- **Duyarlılık koşuları:** windage 0,01 / 0,02 / 0,03, rüzgârsız, difüzyon 1 / 5 / 10 m²/s, 2B vs 3B yüzey.
  Çıktı: her kıyı bölgesi payı için belirsizlik bandı. (`51 --windage … --tag …`, `--no-wind`, `--diffusivity …`)
- **Geriye doğru koşu:** bir kıyı bölgesinden geriye salınan parçacıklar kaynaklara dönüyor mu (tutarlılık sınaması).
- **Literatür karşılaştırması:** Sayın & Eronat (2018) https://doi.org/10.5194/os-14-285-2018 ve "An overview on İzmir Bay
  physical oceanography" https://dergipark.org.tr/tr/download/article-file/277327 — Mordoğan Geçidi eşik derinliği 14 m,
  yaz termoklini 20 m, kış iç körfez <12 °C / <38 psu, yaz üst tabaka 25–28 °C / 39–39,7 psu. Model kesitini bunlarla kıyasla.
- **Sayısal sağlık:** her ay için kütle korunumu, kuru düğüm sayısı, maks hız, CFL — `34` çıktısından otomatik özet tablosu.

## Bilinen yanlılıklar — doğrulamadan önce düzelt

1. ~~**Kaynak ağırlıklandırma yok**~~ — **çözüldü (22 Eylül)**: `config/source_weights.csv` + `scripts/53_weighted_shares.py`.
   Üç senaryo (`esit` / `havza` / `kentsel`), grup payları UNEP/MAP 2015 ve İzmir 2024 kompozisyonundan türetildi,
   Gediz Kazancı vd. 2025 ile çapalandı. Post-processing, koşu tekrarı yok. **Sonuç manşeti değiştiriyor**:
   yıllık bazda iç körfez payı (Z02+Z04) eşit ağırlıkta %50, havza ağırlıklı senaryoda %11; tepeye Foça–Gediz
   deltası çıkıyor (%6,6 → %29,5). Makalede tek sayı yerine senaryo aralığı raporlanacak.
   Kalan eksik: dere bazında ölçülmüş yük. İZSU'nun dere ağzı bariyerlerinden topladığı yıllık katı atık
   (toplam 604 t/yıl yayımlanmış, kırılımı kurumda) bu belirsizliği tek başına kapatır — bkz. `docs/kurumlar.md`. Gerçek çöp yüküne göre ağırlıklandırılmalı
   (Gediz için Kazancı vd. 2025 mikroplastik akısı, dereler için İZSU debileri). Aksi halde "bölge payları" kaynak
   listesinin şekline bağlı kalıyor, gerçek çöp dağılımına değil.
2. **Alan dışı parçacık.** SCHISM kapsama dışında akıntı fallback ile 0'a düşüyor ama ERA5 rüzgârı devam ediyor →
   parçacık tek başına rüzgârla sürüklenip Sakız kıyısına "vuruyor". `drift:deactivate_west_of` / `_east_of` /
   `_north_of` / `_south_of` ile B_model sınırında (26,3–27,2 / 38,3–38,9) dondur. Sonra tüm yıl yeniden koşulmalı.
3. **Stokes drift yok.** Castro-Rosero vd. Karadeniz'de Stokes ekleyince karaya vuran oran %45,5 → %75,5 çıkmış.
   İç körfezde CMEMS dalga ürünü yok → WWM ya da rüzgârdan parametrelendirme (ikinci sürüm).
4. **Isı akısı kapalı.** Aylık yeniden başlatma bunu kısmen telafi ediyor; SST karşılaştırması ne kadar telafi ettiğini gösterir.

## Bulunamayanlar
- **İzmir Körfezi için yayımlanmış, paylaşılan ADCP akıntı zaman serisi yok.** Sayın & Eronat verisi açıkça kapalı
  ("İzmir Bay Marine Research Project"). Tek yol DEÜ-DBTE'ye resmî talep (bkz. `docs/kurumlar.md`).
- Türkiye kıyısında operasyonel **HF radar** bulunamadı (kesin negatif değil). En yakını Yunanistan POSEIDON.
- Aliağa, Çeşme, İzmir kentine ait IOC mareograf istasyonu yok; Ege'de tek istasyon Menteş.
