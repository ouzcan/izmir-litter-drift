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
