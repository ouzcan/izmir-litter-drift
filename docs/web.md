# Web sitesi — "Bu çöp nereye gider?" (20 Eylül 2026)

**Kararlar (kullanıcı):** statik site + Supabase; yeni Supabase projesi (`izmir-litter`, eu-central-1); Türkçe + İngilizce.

## Ne yapıyor
- Haritada denizde bir noktaya tıklanır, çöp türü seçilir (pet şişe, poşet, izmarit, maske, kapak, ağ, diğer). Çöp, o noktanın
  1 km'lik model hücresinden çıkan gerçek bir OpenDrift parçacığının varış noktasına doğru animasyonla sürüklenir; sonuç kartında
  hücrenin kıyı bölgesi dağılımı (çubuklar), tipik yolculuk süresi ve "buradan atılanların %X'i …" cümlesi gösterilir.
- Her atış Supabase'e yazılır (anonim cihaz kimliği). Herkesin çöpleri haritada (başlangıç noktası, yol, varış), canlı akış
  (realtime), toplam / son 24 saat / senin attıkların sayaçları, en çok çöp biriken kıyılar sıralaması.
- Katmanlar: varış haritası (hücre → baskın kıyı, renkli noktalar), herkesin çöpleri, yoğunluk (ısı haritası, varış noktaları),
  bilinen kaynaklar (dere ağızları/limanlar; tıklayınca kaynağın dağılımı). Dönem seçici (şimdilik 6–13 Eylül haftası; yıllık
  koşu bitince yıl + 4 mevsim eklenecek). Paylaş (URL'de nokta + tür → açılışta otomatik atış). TR/EN. Mobil düzen.
- "Nasıl çalışır?" penceresi: yöntem, sınırlar, veri/kod bağlantıları (iki dilde).

## Teknik
- `web/`: `index.html`, `style.css`, `app.js` (bağımlılık: `vendor/` maplibre-gl 4.7.1 + supabase-js 2 UMD — CDN'siz),
  `config.js` (Supabase URL + publishable anahtar; herkese açık, RLS koruyor), `data/` (60 üretir).
- Harita zemini: OpenFreeMap positron (ücretsiz, anahtar yok). Ulaşılamazsa yalın zemin + `coast.geojson` (model ağının kıyısı).
- `scripts/60_web_data.py`: 42/51 koşularından `cells.json` (hücre → dönem → {p: bölge payları, t: medyan saat, s: kıyıya vurma
  oranı, e: 8 örnek varış noktası}), `sources.json`, `zones.json`, `meta.json`. Yıllık: `60 --year`.
- Supabase: `throws` tablosu (RLS: anon okur+ekler, güncelleme/silme yok; koordinat/tür kısıtları; cihaz başına 10 dk'da 40 kayıt
  tetikleyicisi, fonksiyon API'den çağrılamaz), görünümler `throw_stats`, `zone_totals`, `item_totals`, `daily_totals`
  (security_invoker), realtime yayını açık. Güvenlik danışmanı: uyarı yok.
- Yayın: GitHub Pages, `.github/workflows/pages.yml` (`web/` klasörü). **Bir kez:** depo → Settings → Pages → Source:
  "GitHub Actions". Site adresi: `https://<kullanıcı>.github.io/izmir-litter-drift/`. Özel alan adı istenirse Pages'ta CNAME.
- Yerel deneme: `cd web && python -m http.server 8080` → http://localhost:8080 (Supabase'e internetle bağlanır).

## Sonraki
- Yıllık koşu bitince: `51` → `60 --year` → `web/data` güncelle → dönem seçicide yıl + mevsimler.
- Sosyal önizleme görseli (og:image), basit istatistik sayfası (`daily_totals`), il kıyısı (körfez dışı) için Copernicus hücreleri.
- Kötüye kullanım gözlemi: Supabase panelinde `throws` — gerekirse rate limit sıkılaştırılır / captcha.
