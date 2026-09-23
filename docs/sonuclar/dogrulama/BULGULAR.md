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

**Açık soru:** hata gelgitte mi, meteorolojik kabarmada mı? Ayrıştırmak için `pip install utide` +
`70_validate_sealevel.py` yeniden koşulmalı. Elenen olasılıklar:
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
1. `pip install utide` → `70` yeniden koş: gelgit mi, kabarma mı?
2. Mareograf kaydındaki 5 sıçramayı ayıkla, metrikleri yeniden hesapla.
3. Duyarlılık koşuları — windage bandı artık gerekçeli.
4. Katman 2 (drifter) hâlâ tek gerçek Lagrange doğrulaması.
