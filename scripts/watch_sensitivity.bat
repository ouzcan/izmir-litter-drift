@echo off
rem Duyarlilik sirasi (23 Eylul karari): once taban v2 (alan-disi duzeltmesi), sonra en cok sonuc degistirmesi
rem beklenen varyantlar. Her adim biten aylari atlar (endpoints.csv varsa) -> kesilirse ayni komutla devam eder.
rem Izgara modu her varyantta; kaynak modu yalniz taban v2, windage 0.03 ve refloat'ta (kaynak mansetini
rem agirliklar belirliyor, windage degil). Her varyanttan sonra 52 mevsim/yil ozeti; sonda 54 karsilastirma tablosu.
rem Sure (23 Eylul olcumu, Haziran): 1 km izgara ayi ~6 dk; rf5 2 km x 5 parcacik 45 gun ~32 dk/ay.
rem Kaba toplam: base2+w3 (both) ~4 sa, w1/w0/d1/d10 (grid) ~5 sa, b2k ~20 dk, rf5 grid ~6.5 sa + kaynak (n_src 3) ~3 sa.
rem Kullanim (Windows, conda litter): scripts\watch_sensitivity.bat
setlocal
cd /d "%~dp0.."
set PY=python
set S51=%PY% scripts\51_year_opendrift.py --deactivate_outside

echo [duyarlilik] %date% %time% - 1/8 taban v2 (alan disi biter)
%S51% --mode both --tag base2
%PY% scripts\52_seasonal_maps.py --tag base2

echo [duyarlilik] %date% %time% - 2/8 windage 0.03
%S51% --mode both --windage 0.03 --tag w3
%PY% scripts\52_seasonal_maps.py --tag w3

echo [duyarlilik] %date% %time% - 3/8 windage 0.01
%S51% --mode grid --windage 0.01 --tag w1
%PY% scripts\52_seasonal_maps.py --tag w1

echo [duyarlilik] %date% %time% - 4/8 dogrudan ruzgar suruklemesi yok (windage 0)
%S51% --mode grid --no-wind --tag w0
%PY% scripts\52_seasonal_maps.py --tag w0

echo [duyarlilik] %date% %time% - 5/8 difuzyon 1 m2/s
%S51% --mode grid --diffusivity 1 --tag d1
%PY% scripts\52_seasonal_maps.py --tag d1

echo [duyarlilik] %date% %time% - 6/8 difuzyon 10 m2/s
%S51% --mode grid --diffusivity 10 --tag d10
%PY% scripts\52_seasonal_maps.py --tag d10

rem 7/8 KONTROL: rf5 2 km izgarada kosuyor (pahali); 2 km izgaranin kiyi tohumlari 1 km'den farkli (Haziran: 3 saatte
rem vuran yuzde 15,8 vs 11,8). Adil karsilastirma icin ayni izgarada refloat'siz taban: b2k (ucuz, ~1-2 dk/ay).
echo [duyarlilik] %date% %time% - 7/8 taban v2, 2 km izgara (rf5 kontrolu)
%S51% --mode grid --cell_km 2 --n_grid 5 --tag b2k
%PY% scripts\52_seasonal_maps.py --tag b2k

rem 8/8 PAHALI: refloat'ta oturan parcacik aktif kalir (donuk), tabandaki gibi 1 gunde pasiflesmez -> her adimda
rem cok daha fazla parcacik icin ortam okunur (Haziran 2 km x 5: 32 dk). Kaynak modunda n_src 3 (8.3k parcacik/ay).
echo [duyarlilik] %date% %time% - 8/8 yeniden yuzdurme (lambda_R 5 gun, izleme 45 gun)
%S51% --mode grid --refloat_days 5 --track_days 45 --cell_km 2 --n_grid 5 --tag rf5
%S51% --mode sources --refloat_days 5 --track_days 45 --n_src 3 --tag rf5
%PY% scripts\52_seasonal_maps.py --tag rf5

echo [duyarlilik] %date% %time% - karsilastirma tablolari
%PY% scripts\54_sensitivity.py --base base2 --tags w3 w1 w0 d1 d10 --name 1km
%PY% scripts\54_sensitivity.py --base b2k --tags rf5 --modes grid --name rf
%PY% scripts\54_sensitivity.py --base base2 --tags rf5 --modes sources --name rf
echo [duyarlilik] %date% %time% - bitti: runs\opendrift\year\sensitivity\
pause
