# izmir-litter-drift

İzmir il kıyılarından denize giren yüzen çöpün akıntı, rüzgâr ve dalga etkisiyle
nereye taşındığını ve nerede kıyıya vurduğunu modelleyen açık çalışma.

- Yöntem: Copernicus Marine akıntı/dalga + ERA5 rüzgâr üzerinde OpenDrift ile
  Lagrangian parçacık takibi; ileride körfez için yerel hidrodinamik model.
- Çıktılar: kıyıya vurma haritaları, kalış süresi, kaynak-hedef matrisi,
  "buradan atarsam nereye gider" web haritası.
- Plan ve görev listesi: Claude dokümanı "İzmir Yüzen Çöp Taşınımı — Çalışma Planı".

## Dizin yapısı

```
config/      çalışma alanı, kaynak noktaları, kıyı bölgeleri (elle bakılan girdiler)
data/raw/    indirilen ham veri (git dışı)
data/processed/  kesilmiş/işlenmiş veri (git dışı)
runs/        OpenDrift çıktıları (git dışı)
scripts/     veri indirme, koşu, analiz betikleri
notebooks/   keşif defterleri
docs/        kurulum, notlar, karar kayıtları
paper/       makale taslağı, şekiller
web/         site kaynak kodu
```

## Başlangıç

`docs/setup.md` dosyasına bak: hesaplar, ortam kurulumu, ilk test koşusu.

## Lisans

Kod: MIT. Veri lisansları kaynaklarına göre (Copernicus, ECMWF, EMODnet, OSM).
