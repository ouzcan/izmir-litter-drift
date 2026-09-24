// Bu Çöp Nereye Gider? — İzmir Körfezi
// Statik veri (web/data/*.json) + Supabase (herkesin çöpleri, canlı akış)

const CFG = window.APP_CONFIG;
const $ = (s) => document.querySelector(s);
const COSLAT = Math.cos((38.5 * Math.PI) / 180);

const ITEMS = {
  pet: { e: "🧴", tr: "Pet şişe", en: "Plastic bottle" },
  poset: { e: "🛍️", tr: "Poşet", en: "Plastic bag" },
  izmarit: { e: "🚬", tr: "İzmarit", en: "Cigarette butt" },
  maske: { e: "😷", tr: "Maske", en: "Face mask" },
  kapak: { e: "🔵", tr: "Şişe kapağı", en: "Bottle cap" },
  ag: { e: "🕸️", tr: "Ağ parçası", en: "Net fragment" },
  diger: { e: "🗑️", tr: "Başka bir şey", en: "Something else" },
};
const ZONE_COLORS = { Z01: "#1f77b4", Z02: "#aec7e8", Z03: "#ff7f0e", Z04: "#ffbb78", Z05: "#2ca02c", Z06: "#d62728", Z07: "#9467bd",
  Z08: "#8c564b", Z09: "#e377c2", Z10: "#bcbd22", Z11: "#17becf", Z12: "#7f7f7f", Z13: "#c7c7c7", Z14: "#dbdb8d", Z15: "#17a2b8", Z16: "#98df8a", Z00: "#000" };
const ZONE_EN = { Z01: "Bostanlı–Mavişehir", Z02: "Karşıyaka–Bayraklı", Z03: "Kordon–Konak", Z04: "İnciraltı–Balçova", Z05: "Güzelbahçe–Urla",
  Z06: "Karaburun–Mordoğan (east coast)", Z07: "Foça–Gediz delta", Z08: "Çeşme–Alaçatı", Z09: "Seferihisar–Sığacık", Z10: "Aliağa–Çandarlı–Dikili",
  Z11: "Selçuk–Pamucak", Z12: "Outside the bay / open Aegean", Z13: "Uzunada island", Z14: "Hekim–Pırnarlı–Yassıca islands", Z15: "Ildır–Gülbahçe bay", Z16: "Karaburun west coast", Z00: "unclassified coast" };

const I18N = {
  tr: { title: "Bu çöp nereye gider?", subtitle: "İzmir Körfezi · akıntı modeline dayalı interaktif harita", layers: "Katmanlar", how: "Nasıl çalışır?",
    hint: "Denizde bir noktaya <b>tıkla</b> (kıyıdan da olur) — çöpün nereye sürükleneceğini gör.", again: "Bir tane daha at", share: "Paylaş",
    st_total: "atılan çöp", st_24h: "son 24 saat", st_mine: "senin attıkların", top_zones: "En çok çöp biriken kıyılar", live: "Canlı akış",
    foot: "Model: SCHISM (3B, ~110 m) + OpenDrift; rüzgâr ERA5. Bilimsel bir çalışmanın ön sürümüdür; seçili dönemin hava koşullarını yansıtır.",
    method: "Yöntem", data: "Veri", ly_cells: "Varış haritası (hücre → baskın kıyı)", ly_throws: "Herkesin çöpleri", ly_heat: "Yoğunluk (ısı haritası)", ly_sources: "Bilinen kaynaklar (dere ağızları, limanlar)",
    land: "Burası kara — denizde bir noktaya tıkla.",
    outside: "Burası model alanının dışında (haritadaki kesik çizgi). Model İzmir Körfezi ve yakın il kıyısını kapsıyor; güney kıyı (Sığacık, Pamucak) bu sürümde yok.",
    loading: "Dönem verisi yükleniyor…", stranded: "kıyıya vurdu", atsea: "denizde kaldı", left_area: "sonra model alanını terk etti (açık Ege)",
    hours: "saat", median: "medyan", where: "Nereye vurur?", pick: "Ne atıyorsun?", drifting: "sürükleniyor…", landed_in: "sonra kıyıya vurdu",
    fact1: (z, p, t) => `Buradan atılan çöplerin <b>%${p}</b>'i <b>${z}</b> kıyısına vuruyor; tipik yolculuk <b>${t} saat</b>.`,
    fact2: (p) => `Buradan atılanların <b>%${p}</b>'i körfezden çıkıp açık Ege'ye gidiyor.`,
    copied: "Bağlantı kopyalandı", saved: "Kaydedildi — haritadaki herkes görüyor", err: "Kaydedilemedi (çevrimdışı?)", ratelimit: "Çok hızlı atıyorsun, biraz bekle 🙂",
    n_throws: (n) => `${n} çöp`, feed_line: (it, z, t) => `${it} → <b>${z}</b>${t ? ` (${t} sa)` : ""}`, offline: "Çevrimdışı mod: attıkların yalnız sende görünür." },
  en: { title: "Where does this litter go?", subtitle: "İzmir Bay · interactive map based on a current model", layers: "Layers", how: "How it works",
    hint: "<b>Click</b> a point at sea (near the shore is fine) — see where the litter drifts.", again: "Throw another", share: "Share",
    st_total: "items thrown", st_24h: "last 24 h", st_mine: "yours", top_zones: "Coasts collecting the most litter", live: "Live feed",
    foot: "Model: SCHISM (3D, ~110 m) + OpenDrift; ERA5 wind. Preview of a scientific study; reflects the weather of the selected period.",
    method: "Method", data: "Data", ly_cells: "Arrival map (cell → dominant coast)", ly_throws: "Everyone's litter", ly_heat: "Density (heatmap)", ly_sources: "Known sources (river mouths, ports)",
    land: "That is land — click a point at sea.",
    outside: "Outside the model area (dashed line on the map). The model covers İzmir Bay and the nearby provincial coast; the southern coast (Sığacık, Pamucak) is not in this version.",
    loading: "Loading period data…", stranded: "beached", atsea: "stayed at sea", left_area: "later it left the model area (open Aegean)",
    hours: "h", median: "median", where: "Where does it end up?", pick: "What are you throwing?", drifting: "drifting…", landed_in: "later it beached",
    fact1: (z, p, t) => `<b>${p}%</b> of litter thrown here beaches on <b>${z}</b>; typical journey <b>${t} hours</b>.`,
    fact2: (p) => `<b>${p}%</b> of litter thrown here leaves the bay for the open Aegean.`,
    copied: "Link copied", saved: "Saved — everyone on the map can see it", err: "Could not save (offline?)", ratelimit: "Too fast, wait a moment 🙂",
    n_throws: (n) => `${n} items`, feed_line: (it, z, t) => `${it} → <b>${z}</b>${t ? ` (${t} h)` : ""}`, offline: "Offline mode: your throws are only visible to you." },
};

const state = { lang: localStorage.getItem("lang") || (navigator.language?.startsWith("tr") ? "tr" : "en"), period: null, item: "pet",
  meta: null, zones: {}, zonesOutside: new Set(), cells: [], cellById: {}, loaded: new Set(),
  sources: [], throws: [], mine: 0, device: deviceId(), busy: false, sb: null, online: true };
const t = (k, ...a) => { const v = I18N[state.lang][k]; return typeof v === "function" ? v(...a) : v; };
const zoneName = (z) => (state.lang === "en" ? ZONE_EN[z] : state.zones[z]) || z;

function deviceId() {
  try { let d = localStorage.getItem("device_id"); if (!d) { d = crypto.randomUUID(); localStorage.setItem("device_id", d); } return d; }
  catch { return crypto.randomUUID(); }
}
function toast(msg, ms = 2200) { const el = $("#toast"); el.innerHTML = msg; el.classList.remove("hidden"); clearTimeout(el._t); el._t = setTimeout(() => el.classList.add("hidden"), ms); }
function fmtInt(n) { return new Intl.NumberFormat(state.lang === "tr" ? "tr-TR" : "en-GB").format(n); }
function applyLang() {
  document.documentElement.lang = state.lang; $("#btn-lang").textContent = state.lang === "tr" ? "EN" : "TR";
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.innerHTML = t(el.dataset.i18n); });
  $("#about-tr").classList.toggle("hidden", state.lang !== "tr"); $("#about-en").classList.toggle("hidden", state.lang !== "en");
  renderItems(); renderStats(); renderFeed(); renderLegend();
}

// ---------- veri
async function loadData() {
  const j = async (f) => (await fetch(CFG.dataBase + f, { cache: "no-cache" })).json();
  const [meta, zones, sources] = await Promise.all([j("meta.json"), j("zones.json"), j("sources.json")]);
  state.meta = meta; state.sources = sources.features;
  zones.zones.forEach((z) => { state.zones[z.id] = z.name; if (z.outside) state.zonesOutside.add(z.id); });
  const url = new URL(location.href);
  state.period = meta.periods.find((p) => p.id === url.searchParams.get("p"))?.id || meta.default_period;
  const sel = $("#period"); sel.innerHTML = "";
  meta.periods.forEach((p) => { const o = document.createElement("option"); o.value = p.id; o.textContent = p.label; sel.appendChild(o); });
  sel.value = state.period;
  sel.onchange = async () => {
    const per = sel.value; if (per === state.period) return;
    sel.disabled = true;
    try { if (!state.loaded.has(per)) toast(t("loading"), 1500); await loadPeriod(per); state.period = per; refreshCells(); renderLegend(); updateDataLink(); }
    catch (err) { console.error(err); toast(t("err"), 4000); sel.value = state.period; }
    finally { sel.disabled = false; }
  };
  await loadPeriod(state.period);
  try { state.coast = await j("coast.geojson"); } catch { state.coast = null; }
}
// Hücre verisi dönem başına ayrı dosyada (cells_<dönem>.json); yalnız gösterilen dönem indirilir.
// Tek parça hâlinde 17 dönem 12 MB tutuyordu ve harita çizilmeden önce tamamı iniyordu.
async function loadPeriod(per) {
  if (state.loaded.has(per)) return;
  const r = await fetch(CFG.dataBase + `cells_${per}.json`, { cache: "no-cache" });
  if (!r.ok) throw new Error(`cells_${per}.json (${r.status})`);
  const fc = await r.json();
  for (const f of fc.features) {
    let c = state.cellById[f.id];
    if (!c) { c = { id: f.id, lon: f.lon, lat: f.lat, d: {} }; state.cellById[f.id] = c; state.cells.push(c); }
    c.d[per] = f.r;
  }
  state.loaded.add(per);
}
function updateDataLink() {
  const href = CFG.dataBase + `cells_${state.period}.json`;
  const a = $("#link-data"); if (a) a.href = href;
  document.querySelectorAll("[data-cells-link]").forEach((el) => { el.href = href; el.textContent = `cells_${state.period}.json`; });
}
// Model alanı: dışında hiç hücre yok, tıklama "alan dışı" uyarısı almalı.
function inDomain(lon, lat) { const d = state.meta?.domain; return !d || (lon >= d[0] && lon <= d[2] && lat >= d[1] && lat <= d[3]); }
function cellsGeo() {
  return { type: "FeatureCollection", features: state.cells.map((c) => {
    const d = c.d[state.period]; if (!d) return null;
    const dom = Object.entries(d.p).sort((a, b) => b[1] - a[1])[0] || ["Z12", 1];
    return { type: "Feature", geometry: { type: "Point", coordinates: [c.lon, c.lat] }, properties: { id: c.id, dom: dom[0], domp: dom[1], color: ZONE_COLORS[dom[0]] || "#999", t: d.t, s: d.s } };
  }).filter(Boolean) };
}
function nearestCell(lon, lat) {
  let best = null, bd = Infinity;
  for (const c of state.cells) { const dx = (c.lon - lon) * COSLAT * 111, dy = (c.lat - lat) * 111, d2 = dx * dx + dy * dy; if (d2 < bd) { bd = d2; best = c; } }
  return bd <= 1.2 * 1.2 ? best : null;   // 1 km hücre: 1,2 km içinde değilse kara/alan dışı
}
function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

// ---------- Supabase
function initSupabase() {
  if (!CFG.supabaseUrl || !CFG.supabaseKey) { state.online = false; return; }
  try { state.sb = window.supabase.createClient(CFG.supabaseUrl, CFG.supabaseKey, { auth: { persistSession: false } }); } catch { state.online = false; }
}
async function loadThrows() {
  if (!state.sb) return;
  const { data, error } = await state.sb.from("throws").select("id,created_at,item,lon,lat,end_lon,end_lat,zone_id,t_hours,stranded,device_id").order("created_at", { ascending: false }).limit(CFG.maxThrowsShown);
  if (error) { console.warn(error); state.online = false; toast(t("offline"), 4000); return; }
  state.throws = data || []; state.mine = state.throws.filter((x) => x.device_id === state.device).length;
  refreshThrows(); renderStats(); renderFeed(); renderTopZones();
  state.sb.channel("throws-live").on("postgres_changes", { event: "INSERT", schema: "public", table: "throws" }, (payload) => {
    if (state.throws.some((x) => x.id === payload.new.id)) return;
    state.throws.unshift(payload.new); if (state.throws.length > CFG.maxThrowsShown) state.throws.pop();
    refreshThrows(); renderStats(); renderFeed(); renderTopZones();
  }).subscribe();
}
async function saveThrow(rec) {
  if (!state.sb) return null;
  const { data, error } = await state.sb.from("throws").insert(rec).select().single();
  if (error) { if ((error.message || "").includes("rate_limit")) toast(t("ratelimit")); else { console.warn(error); toast(t("err")); } return null; }
  return data;
}

// ---------- harita
let map, marker;
function throwsGeo() {
  const pts = [], ends = [], lines = [];
  for (const x of state.throws) {
    const p = { item: x.item, e: ITEMS[x.item]?.e || "🗑️", zone: x.zone_id, color: ZONE_COLORS[x.zone_id] || "#999", mine: x.device_id === state.device ? 1 : 0 };
    pts.push({ type: "Feature", geometry: { type: "Point", coordinates: [x.lon, x.lat] }, properties: p });
    ends.push({ type: "Feature", geometry: { type: "Point", coordinates: [x.end_lon, x.end_lat] }, properties: p });
    lines.push({ type: "Feature", geometry: { type: "LineString", coordinates: curve([x.lon, x.lat], [x.end_lon, x.end_lat], 6, x.id) }, properties: p });
  }
  return { pts: fc(pts), ends: fc(ends), lines: fc(lines) };
}
const fc = (f) => ({ type: "FeatureCollection", features: f });
function curve(a, b, n = 24, seed = "") {
  // hafif kıvrımlı temsili yol (deterministik: id'den tohum)
  let h = 0; for (const ch of String(seed)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  const s = ((h % 1000) / 1000 - 0.5) * 0.35;
  const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, dx = b[0] - a[0], dy = b[1] - a[1];
  const cx = mx - dy * s, cy = my + dx * s * COSLAT;
  const out = []; for (let i = 0; i <= n; i++) { const u = i / n, w = 1 - u; out.push([w * w * a[0] + 2 * w * u * cx + u * u * b[0], w * w * a[1] + 2 * w * u * cy + u * u * b[1]]); }
  return out;
}
const FALLBACK_STYLE = { version: 8, name: "fallback", glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf", sources: {},
  layers: [{ id: "bg", type: "background", paint: { "background-color": "#cfe0ea" } }] };
async function resolveStyle() {
  try { const c = new AbortController(); const tm = setTimeout(() => c.abort(), 6000);
    const r = await fetch(CFG.mapStyle, { signal: c.signal }); clearTimeout(tm); if (r.ok) return await r.json(); } catch {}
  console.warn("harita stili yüklenemedi, yalın arka plan"); return FALLBACK_STYLE;
}
async function initMap() {
  const style = await resolveStyle();
  map = window.__map = new maplibregl.Map({ container: "map", style, center: [26.85, 38.52], zoom: 9.6, minZoom: 8, maxZoom: 15, attributionControl: { compact: true } });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-left");
  map.addControl(new maplibregl.GeolocateControl({ positionOptions: { enableHighAccuracy: true } }), "bottom-left");
  map.on("load", addLayers);
  map.on("click", onMapClick);
  map.on("mouseenter", "cells", () => (map.getCanvas().style.cursor = "crosshair")); map.on("mouseleave", "cells", () => (map.getCanvas().style.cursor = ""));
  return new Promise((res) => map.once("load", res));
}
function addLayers() {
  if (map.getSource("cells")) return;
  if (state.coast) { map.addSource("coast", { type: "geojson", data: state.coast }); map.addLayer({ id: "coast", type: "line", source: "coast", paint: { "line-color": "#3b4a5a", "line-width": ["interpolate", ["linear"], ["zoom"], 9, 0.7, 13, 1.6], "line-opacity": 0.85 } }); }
  const dm = state.meta?.domain;
  if (dm) {   // model alanı sınırı — dışarıda veri yok; kullanıcı nereye kadar modellendiğini görsün
    const [ax, ay, bx, by] = dm;
    map.addSource("domain", { type: "geojson", data: { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [[ax, ay], [bx, ay], [bx, by], [ax, by], [ax, ay]] } } });
    map.addLayer({ id: "domain", type: "line", source: "domain", paint: { "line-color": "#8a98a8", "line-width": 1.4, "line-dasharray": [3, 3], "line-opacity": 0.85 } });
  }
  map.addSource("cells", { type: "geojson", data: cellsGeo() });
  map.addLayer({ id: "cells", type: "circle", source: "cells", paint: {
    "circle-radius": ["interpolate", ["exponential", 2], ["zoom"], 8, 1.1, 10, 4.4, 12, 17.5, 14, 70],
    "circle-color": ["get", "color"], "circle-opacity": ["interpolate", ["linear"], ["get", "domp"], 0.3, 0.18, 1, 0.45], "circle-blur": 0.15 } });
  const g = throwsGeo();
  map.addSource("t-lines", { type: "geojson", data: g.lines }); map.addSource("t-pts", { type: "geojson", data: g.pts }); map.addSource("t-ends", { type: "geojson", data: g.ends });
  map.addLayer({ id: "t-heat", type: "heatmap", source: "t-ends", layout: { visibility: "none" }, paint: { "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 9, 12, 14, 40], "heatmap-opacity": 0.75, "heatmap-intensity": 0.8 } });
  map.addLayer({ id: "t-lines", type: "line", source: "t-lines", paint: { "line-color": ["get", "color"], "line-width": ["case", ["==", ["get", "mine"], 1], 2.2, 1], "line-opacity": ["case", ["==", ["get", "mine"], 1], 0.9, 0.35] } });
  map.addLayer({ id: "t-ends", type: "circle", source: "t-ends", paint: { "circle-radius": ["case", ["==", ["get", "mine"], 1], 5, 3.2], "circle-color": ["get", "color"], "circle-stroke-color": "#fff", "circle-stroke-width": 1 } });
  map.addLayer({ id: "t-pts", type: "circle", source: "t-pts", paint: { "circle-radius": ["case", ["==", ["get", "mine"], 1], 5, 3], "circle-color": "#14202b", "circle-opacity": ["case", ["==", ["get", "mine"], 1], 0.9, 0.45], "circle-stroke-color": "#fff", "circle-stroke-width": 1 } });
  map.addSource("sources", { type: "geojson", data: fc(state.sources.map((s) => ({ type: "Feature", geometry: { type: "Point", coordinates: [s.lon, s.lat] }, properties: { id: s.id, name: s.name } }))) });
  map.addLayer({ id: "sources", type: "circle", source: "sources", layout: { visibility: "none" }, paint: { "circle-radius": 6, "circle-color": "#7a2d00", "circle-stroke-color": "#fff", "circle-stroke-width": 1.5 } });
  map.addLayer({ id: "sources-lbl", type: "symbol", source: "sources", layout: { visibility: "none", "text-field": ["get", "name"], "text-size": 11, "text-anchor": "left", "text-offset": [0.8, 0], "text-optional": true }, paint: { "text-color": "#7a2d00", "text-halo-color": "#fff", "text-halo-width": 1.5 } });
  map.on("click", "sources", (e) => { const s = state.sources.find((x) => x.id === e.features[0].properties.id); if (s) { e.originalEvent._srcHit = true; showSource(s); } });
  map.on("click", "t-pts", (e) => { const p = e.features[0].properties; e.originalEvent._srcHit = true; new maplibregl.Popup({ closeButton: false }).setLngLat(e.lngLat).setHTML(`${p.e} → <b>${zoneName(p.zone)}</b>`).addTo(map); });
  map.on("click", "t-ends", (e) => { const p = e.features[0].properties; e.originalEvent._srcHit = true; new maplibregl.Popup({ closeButton: false }).setLngLat(e.lngLat).setHTML(`${p.e} → <b>${zoneName(p.zone)}</b>`).addTo(map); });
  bindLayerToggles();
}
function refreshCells() { map.getSource("cells")?.setData(cellsGeo()); history.replaceState(null, "", `?p=${state.period}`); }
function refreshThrows() { const g = throwsGeo(); map.getSource("t-lines")?.setData(g.lines); map.getSource("t-pts")?.setData(g.pts); map.getSource("t-ends")?.setData(g.ends); }
function bindLayerToggles() {
  const vis = (ids, on) => ids.forEach((id) => map.getLayer(id) && map.setLayoutProperty(id, "visibility", on ? "visible" : "none"));
  $("#ly-cells").onchange = (e) => vis(["cells"], e.target.checked);
  $("#ly-throws").onchange = (e) => vis(["t-lines", "t-pts", "t-ends"], e.target.checked);
  $("#ly-heat").onchange = (e) => vis(["t-heat"], e.target.checked);
  $("#ly-sources").onchange = (e) => vis(["sources", "sources-lbl"], e.target.checked);
}
function renderLegend() {
  const used = new Set(state.cells.map((c) => Object.entries(c.d[state.period]?.p || {}).sort((a, b) => b[1] - a[1])[0]?.[0]).filter(Boolean));
  $("#legend").innerHTML = [...used].sort().map((z) => `<span><i style="background:${ZONE_COLORS[z]}"></i>${zoneName(z)}</span>`).join("");
}

// ---------- atış
async function onMapClick(e) {
  if (e.originalEvent._srcHit || state.busy) return;
  const { lng, lat } = e.lngLat; const cell = nearestCell(lng, lat);
  if (!cell) { toast(inDomain(lng, lat) ? t("land") : t("outside"), 5500); return; }
  const d = cell.d[state.period]; if (!d) { toast(t("land")); return; }
  state.busy = true; $("#result").classList.add("hidden");
  // Sonuç, hücrenin kıyıya vurma oranıyla (s) örneklenir: e = vuran örnekler, x = alan dışına çıkış noktaları
  const hasE = d.e.length > 0, hasX = (d.x || []).length > 0;
  const stranded = hasE && (Math.random() < d.s || !hasX);
  const end = stranded ? pick(d.e) : (hasX ? pick(d.x) : null);
  const endLon = end ? end[0] : lng, endLat = end ? end[1] : lat, tHours = end ? end[2] : null;
  const zone = stranded ? zoneOfPoint(endLon, endLat, d) : "Z12";
  await animateThrow([lng, lat], [endLon, endLat], tHours);
  const rec = { device_id: state.device, item: state.item, period: state.period, cell_id: cell.id, lon: +lng.toFixed(5), lat: +lat.toFixed(5),
    end_lon: +endLon.toFixed(5), end_lat: +endLat.toFixed(5), zone_id: zone, t_hours: tHours, stranded, locale: state.lang };
  const local = { ...rec, id: "local-" + Date.now(), created_at: new Date().toISOString() };
  state.throws.unshift(local); state.mine++; refreshThrows(); renderStats(); renderFeed(); renderTopZones();
  showResult(cell, d, zone, tHours, stranded, [lng, lat]);
  state.busy = false;
  const saved = await saveThrow(rec);
  if (saved) { const i = state.throws.findIndex((x) => x.id === local.id); if (i >= 0) state.throws[i] = saved; toast(t("saved")); }
}
function zoneOfPoint(lon, lat, d) {
  // Zon kutuları client'ta yok; hücrenin dağılımından en olası bölgeyi varış noktasına göre seç: kutu verisi zones.json'da
  const Z = state.zoneBoxes || [];
  for (const z of Z) { if (z.bbox[0] != null && lon >= z.bbox[0] && lon <= z.bbox[1] && lat >= z.bbox[2] && lat <= z.bbox[3]) return z.id; }
  return Object.entries(d.p).sort((a, b) => b[1] - a[1])[0]?.[0] || "Z12";
}
function animateThrow(a, b, tHours) {
  return new Promise((resolve) => {
    const path = curve(a, b, 60, Math.random()); const el = document.createElement("div"); el.className = "marker"; el.innerHTML = `<span class="splash">${ITEMS[state.item].e}</span>`;
    marker?.remove(); marker = new maplibregl.Marker({ element: el, anchor: "center" }).setLngLat(a).addTo(map);
    const dur = Math.min(4500, Math.max(1800, (tHours || 12) * 120)); const t0 = performance.now();
    $("#res-sub").textContent = t("drifting");
    const step = (now) => { const u = Math.max(0, Math.min(1, (now - t0) / dur)), k = u * (path.length - 1), i = Math.floor(k), f = k - i;
      const p = i >= path.length - 1 ? path[path.length - 1] : [path[i][0] + (path[i + 1][0] - path[i][0]) * f, path[i][1] + (path[i + 1][1] - path[i][1]) * f];
      marker.setLngLat(p); if (u < 1) requestAnimationFrame(step); else resolve(); };
    requestAnimationFrame(step);
  });
}
function showResult(cell, d, zone, tHours, stranded, start) {
  const it = ITEMS[state.item]; $("#res-emoji").textContent = it.e;
  $("#res-title").textContent = stranded ? `${it[state.lang]} → ${zoneName(zone)}` : `${it[state.lang]} → ${zoneName("Z12")}`;
  $("#res-sub").textContent = stranded ? `${tHours} ${t("hours")} ${t("landed_in")}` : (tHours ? `${tHours} ${t("hours")} ${t("left_area")}` : t("atsea"));
  const entries = Object.entries(d.p).sort((a, b) => b[1] - a[1]).slice(0, 6);
  $("#res-bars").innerHTML = `<div class="muted" style="margin-bottom:4px">${t("where")}</div>` + entries.map(([z, p]) =>
    `<div class="bar"><div class="track"><div class="fill" style="width:${Math.round(p * 100)}%;background:${ZONE_COLORS[z]}66"></div><span class="lbl">${zoneName(z)}</span></div><span class="pct">%${Math.round(p * 100)}</span></div>`).join("");
  const top = entries[0];
  $("#res-fact").innerHTML = top && top[0] !== "Z12" ? t("fact1", zoneName(top[0]), Math.round(top[1] * 100), d.t ?? "?") : t("fact2", Math.round((d.p.Z12 || 0) * 100));
  $("#result").classList.remove("hidden"); $("#panel").classList.remove("collapsed"); $("#result").scrollIntoView?.({ block: "nearest" });
  $("#btn-share").onclick = () => { const u = new URL(location.href); u.search = `?p=${state.period}&lon=${start[0].toFixed(4)}&lat=${start[1].toFixed(4)}&item=${state.item}`;
    if (navigator.share) navigator.share({ title: t("title"), url: u.toString() }).catch(() => {}); else { navigator.clipboard?.writeText(u.toString()); toast(t("copied")); } };
  $("#btn-again").onclick = () => { $("#result").classList.add("hidden"); marker?.remove(); };
}
function showSource(s) {
  const d = s.d[state.period]; if (!d) return;
  const entries = Object.entries(d.p).sort((a, b) => b[1] - a[1]).slice(0, 5);
  new maplibregl.Popup({ maxWidth: "280px" }).setLngLat([s.lon, s.lat]).setHTML(`<b>${s.name}</b><br>${entries.map(([z, p]) => `${zoneName(z)}: %${Math.round(p * 100)}`).join("<br>")}<br><span style="color:#666">${t("median")} ${d.t ?? "?"} ${t("hours")}</span>`).addTo(map);
}

// ---------- panel
function renderItems() {
  $("#items").innerHTML = `<div class="muted" style="width:100%;margin-bottom:2px">${t("pick")}</div>` + Object.entries(ITEMS).map(([k, v]) =>
    `<button class="item ${k === state.item ? "active" : ""}" data-k="${k}">${v.e} ${v[state.lang]}</button>`).join("");
  $("#items").querySelectorAll(".item").forEach((b) => (b.onclick = () => { state.item = b.dataset.k; renderItems(); }));
}
function renderStats() {
  const n = state.throws.length; const day = Date.now() - 86400e3;
  $("#st-total").textContent = fmtInt(state.total ?? n); $("#st-24h").textContent = fmtInt(state.throws.filter((x) => new Date(x.created_at).getTime() > day).length); $("#st-mine").textContent = fmtInt(state.mine);
}
function renderTopZones() {
  const c = {}; state.throws.forEach((x) => (c[x.zone_id] = (c[x.zone_id] || 0) + 1));
  const rows = Object.entries(c).sort((a, b) => b[1] - a[1]).slice(0, 6);
  $("#top-zones").innerHTML = rows.map(([z, n]) => `<li><span><i style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${ZONE_COLORS[z]};margin-right:6px"></i>${zoneName(z)}</span><span class="n">${t("n_throws", fmtInt(n))}</span></li>`).join("") || `<li class="muted">—</li>`;
}
function renderFeed() {
  const rel = (iso) => { const s = (Date.now() - new Date(iso).getTime()) / 1000; if (s < 60) return state.lang === "tr" ? "az önce" : "just now"; if (s < 3600) return `${Math.floor(s / 60)} dk`; if (s < 86400) return `${Math.floor(s / 3600)} sa`; return `${Math.floor(s / 86400)} g`; };
  $("#feed").innerHTML = state.throws.slice(0, 12).map((x) => `<li>${t("feed_line", (ITEMS[x.item]?.e || "🗑️") + " " + (ITEMS[x.item]?.[state.lang] || ""), zoneName(x.zone_id), x.t_hours ? Math.round(x.t_hours) : "")}<time>${rel(x.created_at)}</time></li>`).join("") || `<li class="muted">—</li>`;
}
async function loadStats() {
  if (!state.sb) return;
  const { data } = await state.sb.from("throw_stats").select("*").single();
  if (data) { state.total = data.total; renderStats(); }
}

// ---------- başlat
async function main() {
  $("#repo-link").href = CFG.repo; $("#about-repo").href = CFG.repo; $("#about-repo-en").href = CFG.repo;
  $("#btn-lang").onclick = () => { state.lang = state.lang === "tr" ? "en" : "tr"; localStorage.setItem("lang", state.lang); applyLang(); };
  $("#btn-about").onclick = () => $("#about").classList.remove("hidden"); $("#about-close").onclick = () => $("#about").classList.add("hidden");
  $("#about").onclick = (e) => { if (e.target.id === "about") $("#about").classList.add("hidden"); };
  $("#btn-layers").onclick = () => $("#layers").classList.toggle("hidden");
  $("#panel-toggle").onclick = () => $("#panel").classList.toggle("collapsed");
  if (matchMedia("(max-width: 760px)").matches) $("#panel").classList.add("collapsed");
  $("#link-method").onclick = (e) => { e.preventDefault(); $("#about").classList.remove("hidden"); };
  await loadData();
  updateDataLink();
  const zj = await (await fetch(CFG.dataBase + "zones.json")).json(); state.zoneBoxes = zj.zones;
  applyLang(); initSupabase(); await initMap();
  await Promise.all([loadThrows(), loadStats()]);
  const u = new URL(location.href); const lon = parseFloat(u.searchParams.get("lon")), lat = parseFloat(u.searchParams.get("lat"));
  if (u.searchParams.get("item") in ITEMS) { state.item = u.searchParams.get("item"); renderItems(); }
  if (isFinite(lon) && isFinite(lat)) { map.jumpTo({ center: [lon, lat], zoom: 12 }); setTimeout(() => onMapClick({ lngLat: { lng: lon, lat }, originalEvent: {} }), 600); }
  setInterval(renderFeed, 30000);
}
main().catch((e) => { console.error(e); toast("Hata: " + e.message, 6000); });
