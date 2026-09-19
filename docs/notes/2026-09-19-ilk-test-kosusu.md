# İlk test koşusu — Bostanlı, 6 Eylül 2026

**Sonuç:** 100 parçacığın 100'ü 27 saat içinde iç körfezin güney kıyısına (Konak–Alsancak–Kordon hattı,
27.08–27.13°D, 38.40–38.42°K) vurdu. Rüzgâr 6–7 Eylül'de kuzey-kuzeydoğudan ort. 3,2 m/s (ERA5, maks 4,7).
Görsel: `runs/test_bostanli/20260906/track.png`.

**Asıl bulgu:** Copernicus MED (1/24°, ~4,2 km) iç körfezde **hiç geçerli hücre içermiyor**:
akıntı (uo/vo) ve dalga (VSDX/VSDY) için iç körfez kutusunda 0/15 hücre; Körfez kutusunda (B) 43/165.
Yani bu koşuda parçacıklar yalnız rüzgâr sürüklemesiyle (%2 windage) hareket etti; akıntı ve Stokes
terimleri sıfırdı ("Only NaNs input to linearNDFast" uyarılarının nedeni bu).

**Çıkarımlar**
- İç körfez için Copernicus tek başına kullanılamaz. Faz 3 (yerel hidrodinamik model) gerekçesi
  sayısal olarak kanıtlandı; öne alınmalı.
- Orta/dış körfez ve il kıyısı için Copernicus geçerli; Faz 1 bu alanlarda yürütülebilir.
- Rüzgâr-tek başına sonucu bile Sayın & Eronat (2018) kuzey rüzgârı deseniyle (kıyı boyunca güneye
  taşınım) tutarlı; ama tek başına yayımlanabilir bulgu değildir.
- GSHHG kara maskesinde Bostanlı salım noktası kıyı çizgisine çok yakın çıktı (100 noktanın 39'u
  karadan suya taşındı); pilot nokta ~400 m açığa alındı.

**Sonraki adım seçenekleri**
1. Faz 1'i orta/dış körfez + il kıyısı ile sınırlı yürüt (Copernicus geçerli), iç körfezi Faz 3'e bırak.
2. Faz 3'ü öne al: SCHISM/Delft3D FM ile 100–300 m körfez modeli; EMODnet batimetri + Copernicus sınır koşulu.
3. Geçici: iç körfez için yalnız rüzgâr + Sayın-Eronat analitik akıntı deseni ile "rüzgâr rejimi haritası"
   (hızlı ama bilimsel olarak zayıf; yalnız ön görselleştirme için).
