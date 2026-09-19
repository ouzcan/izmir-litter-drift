# Karar kaydı

Tarih · karar · gerekçe. Yeni kararlar en üste.

- 2026-09-19 · Çalışma iki kademeli: il kıyısı (A, Copernicus 4 km) + Körfez (B, Faz 3 yerel model 100–300 m). · Web sitesi il geneli istiyor; makale körfeze odaklanır; iç körfez Copernicus'la çözülmez.
- 2026-09-19 · Lagrangian araç: OpenDrift. · Açık kaynak, Copernicus'u doğrudan okur, windage/Stokes/beaching hazır; LOCATE (Parcels) yedek.
- 2026-09-19 · Kod ve veri kullanıcının bilgisayarında (`source/repos/izmir-litter-drift`), GitHub'a push. · Uzun süreli proje; buluttaki oturum kalıcı değil.
- 2026-09-19 · TÜBİTAK başvurusu yok; bağımsız akademik çalışma + web sitesi. · Kullanıcı kararı.
- 2026-09-19 · Kaynak koordinatları ilk sürümde yaklaşık (`verified=no`); OSM/Overpass bu ortamdan erişilemedi. · Sonraki adımda haritadan doğrulanacak.
- 2026-09-19 · Veri indirme ve model koşuları kullanıcının Windows makinesinde (conda `litter` ortamı); Claude betikleri yazar, çıktıları depo klasöründen okur. · Copernicus/CDS/EMODnet/OSM sunucuları Claude'un iki ortamından da erişilemiyor (yalnız GitHub ve PyPI açık).
- 2026-09-19 · İlk test koşusu: Copernicus MED iç körfezde 0 geçerli hücre (akıntı ve dalga). Faz 1 orta/dış körfez + il kıyısıyla sınırlı; iç körfez yerel model (Faz 3) ister. · `docs/notes/2026-09-19-ilk-test-kosusu.md`
- 2026-09-19 · Faz 3 öne alındı (Faz 1 il kıyısı koşuları sonraya). · Kullanıcı kararı; Copernicus iç körfezi çözmüyor.
- 2026-09-19 · Yerel model: Delft3D FM (D-Flow FM) + dfm_tools zinciri; alan B_model 26.30–27.20°D / 38.30–38.90°K; açık sınır yalnız kuzey+batı; taban 0,005°, iç körfez ~110 m. · Windows'ta yerel çalışır, ağ+CMEMS+ERA5 otomasyonu hazır; SCHISM yedek. Zincir sentetik veriyle uçtan uca test edildi (`docs/mesh_sentetik_test.png`).
- 2026-09-19 · Batimetri: EMODnet DTM 2024 (ERDDAP `bathymetry_dtm_2024`, ~115 m, LAT referanslı); kıyı: OSM kara poligonları (yedek GSHHS f). · İç körfezde GEBCO çok kaba.
- 2026-09-19 · CMEMS sınır koşulları MED 1/24° kimlikleriyle (zos saatlik 2D; so/thetao/uo/vo günlük 3D); dfm_tools varsayılanı GLOBAL 1/12° olduğu için açıkça verildi.
