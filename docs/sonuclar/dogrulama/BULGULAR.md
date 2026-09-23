# Doğrulama Katman 1 — ilk sonuçlar (23 Eylül 2026)

Modelin gözlemle ilk kez karşılaştırıldığı tur. İki bağımsız ölçüt aynı yöne işaret ediyor:
**meteorolojik zorlama az enerjili.**

## 1. Su seviyesi — SCHISM ↔ Menteş mareografı

Gözlem: IOC `ment`, radar sensör, 30 sn; 365 gün indirildi, saatlik ortalamaya indirgendi.
Kapsama 6.518 / 8.784 saat (%74; mareograf kaydındaki boşluklar). Saat başına medyan 120 örnek (tam).
5 adet >20 cm saatlik sıçrama var (maks 36,6 cm) — kabarma mı sensör hatası mı, ayıklanmadı.

| ölçüt | değer |
|---|---|
| bias (model − gözlem) | −1,667 m (datum farkı, çıkarıldı) |
| merkezlenmiş RMSE | **0,100 m** |
| Pearson r | **0,659** (R² 0,43) |
| std gözlem / model | 0,132 / 0,098 m (**oran 0,75**) |

**Okuma:** model su seviyesi değişkenliğinin %43'ünü açıklıyor ve genliğini %25 eksik veriyor.
Hata (10 cm) gözlenen salınımın (13,2 cm) %76'sı kadar — yani ortalama bir sonuç, kötü değil ama
"doğrulandı" demek için yeterli değil.

### Hata nerede? (gelgit / kalan ayrıştırması)

Seri, en küçük kareler gelgit uyumuyla (M2 S2 N2 K1 O1 P1, numpy — utide gerekmiyor) ikiye ayrıldı:

| bileşen | std gözlem | std model | crmse | r |
|---|---|---|---|---|
| gelgit | 5,6 cm | 4,5 cm | **2,5 cm** | **0,896** |
| kalan (meteorolojik) | 12,0 cm | 8,8 cm | **9,7 cm** | **0,604** |
| toplam | 13,2 cm | 9,8 cm | 10,0 cm | 0,659 |

**Cevap net: hata gelgitte değil, kabarmada.** 10,0 cm'lik toplam hatanın 9,7 cm'i meteorolojik kalandan
geliyor. Gelgit iyi tutuyor (r 0,90, hata 2,5 cm).

Harmonikler (genlik cm / faz °):

| bileşen | gözlem | model | genlik oranı | faz farkı |
|---|---|---|---|---|
| M2 | 5,51 / 135,9 | 4,57 / 107,3 | 0,83 | −28,6° |
| S2 | 4,34 / 311,6 | 2,31 / 292,7 | **0,53** | −18,9° |
| N2 | 1,05 / 283,0 | 0,81 / 245,4 | 0,77 | −37,6° |
| K1 | 2,98 / 292,5 | 3,09 / 288,0 | **1,04** | −4,4° |
| O1 | 1,68 / 341,8 | 1,80 / 337,7 | **1,07** | −4,0° |
| P1 | 0,90 / 139,5 | 1,26 / 134,9 | 1,40 | −4,5° |

**Günlük bileşenler (K1, O1, P1) neredeyse kusursuz** — genlik oranı 1,04–1,07, faz hatası 4°.
**Yarı-günlük bileşenler (M2, S2, N2) sönümlü ve ~28° önde.**

Bu sönüm mareograf düğümünün sığ olmasından (1,0 m) DEĞİL: Menteş çevresinde 1 m'den 30 m'ye, 44 m'den
2,3 km'ye kadar beş düğüm denendi, M2 oranı 0,83–0,84 ve faz −28,6° sabit kaldı. Yani yerel batimetri ya da
dip sürtünmesi değil, **sınır koşulundan miras alınan** bir hata — CMEMS'in 4 km'lik `zos` alanı Ege'deki
küçük ve karmaşık yarı-günlük gelgiti yerel olarak tam çözemiyor. Günlük gelgitin daha geniş ölçekli
olması ve iyi tutması bu okumayı destekliyor.

**Ama düzeltmeye değmez:** gelgit toplam salınımın yalnız 5,6/13,2'si ve hatası 2,5 cm. `bctides.in`'e
FES2014/TPXO harmonikleri eklemek (`nbfr > 0`) en fazla ~2 cm kazandırır. Asıl açık kabarmada.

Elenen diğer olasılıklar:
- Açık sınırda gelgit YOK gibi görünüyor (`bctides.in`: `nbfr = 0`) **ama** CMEMS `zos` ürünü gelgit
  içeriyor ([MEDSEA_ANALYSISFORECAST_PHY_006_013](https://data.marine.copernicus.eu/product/MEDSEA_ANALYSISFORECAST_PHY_006_013/description)
  — "including tides"; ayrıca ayrı bir "detided" sürümü var). Yani gelgit sınırdan zaman serisi olarak giriyor.
- Basınç (ters barometre) uygulanıyor: `nws = 2`, sflux dosyalarında `prmsl` var. Bu bir eksik değil.

## 2. Rüzgâr — ERA5 ↔ LTBJ METAR

Gözlem: Iowa State IEM ASOS, 18.095 kayıt, 8.141 ortak saat.

| ölçüt | değer |
|---|---|
| hız bias (ERA5 − METAR) | **−2,20 m/s** |
| ortalama hız METAR / ERA5 | 4,89 / **2,70** m/s |
| hız RMSE / r | 3,06 m/s / 0,691 |
| yön bias / RMSE | −3,2° / **52,0°** |
| vektör korelasyonu | 0,772 |

**Günlük döngü — teşhis burada:**

| yerel saat | METAR | ERA5 | oran | METAR yön | ERA5 yön |
|---|---|---|---|---|---|
| 04 | 3,67 | 2,00 | 0,55 | 5° | 43° |
| 10 | 5,07 | 2,69 | 0,53 | 357° | 41° |
| 16 | 6,46 | 3,66 | 0,57 | 343° | 337° |
| 20 | 5,02 | 2,78 | 0,55 | 360° | 353° |

**Okuma:** oran günün her saatinde 0,53–0,60 — **sabit çarpan**, eksik bir süreç değil. ERA5 imbat döngüsünü
yakalıyor (genlik 1,66 vs 2,95 m/s, aynı 0,56 katsayısıyla ölçeklenmiş) ve öğleden sonra yönü doğru
(337° vs 343°); gece/zayıf rüzgârda yön ~40° saat yönünde sapıyor — 52°'lik yön RMSE'sinin çoğu oradan.

Bu sabit çarpan büyük olasılıkla **yer uyuşmazlığı**: LTBJ açık bir havaalanı (düşük pürüzlülük, iyi maruz
anemometre), ERA5'in 0,25° hücresi (27,00–27,25 / 38,25–38,50) ise ağırlıkla engebeli arazi. **Bu sonuçtan
"ERA5 körfez üzerinde de %45 düşük" SONUCU ÇIKARILAMAZ** — su üzerinde pürüzlülük düşük ve ERA5 orada
genellikle çok daha iyidir.

**Ama bir uyarı gerçek:** ERA5 bu noktada **>10 m/s'yi hiç görmüyor** (%0,0), METAR ise saatlerin %2,8'inde
görüyor. Fırtına olaylarında rüzgâr zorlaması eksik kalıyor olabilir.

## 3. İki ölçütün birleşimi

Su seviyesi genliği %25 eksik + ERA5 uç rüzgârları kaçırıyor → **meteorolojik zorlama az enerjili**.
Menteş'teki kabarma, su üzerindeki rüzgâr stresinin dolaylı ölçüsü olduğu için bu iki bulgu birbirini
destekliyor ve kara istasyonu uyuşmazlığından bağımsız.

**Sürüklenme modeline etkisi:** windage %2 rüzgâr hızının oranı olarak uygulanıyor. Zorlama az enerjiliyse
sürüklenme de az enerjili demektir. Duyarlılık koşuları (windage 0,01 / 0,03) bu belirsizliği bracketlemenin
doğru yolu — artık keyfi bir duyarlılık testi değil, gözleme dayalı bir gerekçesi var.

## Sıradaki
1. ~~gelgit mi, kabarma mı~~ — **cevaplandı: kabarma.** Gelgit r 0,90 / 2,5 cm; kalan r 0,60 / 9,7 cm.
2. Kabarmayı iyileştirmek: ERA5 yerine daha yüksek çözünürlüklü rüzgâr (CARRA yok bu bölgede; alternatif
   ERA5 üzerinden bir rüzgâr ölçek katsayısı ya da WRF ile dinamik indirgeme) — maliyeti yüksek, önce
   duyarlılıkla bracketlemek daha mantıklı.
3. Duyarlılık koşuları — windage bandı artık gözleme dayalı gerekçeli (model zorlaması %25 az enerjili).
4. Mareograf kaydındaki 5 sıçramayı ayıkla, metrikleri yeniden hesapla (etkisi küçük olmalı).
5. Gelgit için `nbfr > 0` + FES2014 — ikinci sürüm, kazanç ~2 cm, öncelik düşük.
6. Katman 2 (drifter) hâlâ tek gerçek Lagrange doğrulaması.
