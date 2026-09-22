# Bu Çöp Nereye Gider? — web sitesi

Statik tek sayfa (MapLibre GL + sade JS) + Supabase (herkesin çöpleri, canlı akış).

- `data/` — `scripts/60_web_data.py` üretir: `cells_<dönem>.json` (1 km hücre → kıyı payları, örnek varış noktaları; dönem başına ayrı dosya, açılışta yalnız biri iner),
  `sources.json`, `zones.json`, `coast.geojson` (model ağının kıyısı), `meta.json` (dönemler).
- `config.js` — Supabase URL + publishable anahtar (herkese açık; RLS koruyor), harita stili, depo adresi.
- `vendor/` — maplibre-gl 4.7.1, supabase-js 2 (UMD). CDN'siz çalışır; harita zemini openfreemap.org'dan gelir, ulaşılamazsa
  yalın zemin + ağ kıyısı çizilir.
- Yerelde: `cd web && python -m http.server 8080` → http://localhost:8080
- Yayın: GitHub Pages (`.github/workflows/pages.yml`, `web/` klasörü). Bir kez Settings → Pages → Source: GitHub Actions.

Supabase (proje `izmir-litter`, eu-central-1): tablo `throws` (RLS: anon okur+ekler, değiştiremez; cihaz başına 10 dk'da 40
kayıt sınırı), görünümler `throw_stats`, `zone_totals`, `item_totals`, `daily_totals`; realtime açık.
