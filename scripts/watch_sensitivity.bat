@echo off
rem Duyarlilik sirasi (23 Eylul karari): once taban v2 (alan-disi duzeltmesi), sonra en cok sonuc degistirmesi
rem beklenen varyantlar. Her adim biten aylari atlar (endpoints.csv varsa) -> kesilirse ayni komutla devam eder.
rem Izgara modu her varyantta; kaynak modu yalniz taban v2, windage 0.03 ve refloat'ta (kaynak mansetini
rem agirliklar belirliyor, windage degil). Her varyanttan sonra 52 mevsim/yil ozeti; sonda 54 karsilastirma tablosu.
rem Kullanim (Windows, conda litter): scripts\watch_sensitivity.bat
setlocal
cd /d "%~dp0.."
set PY=python
set S51=%PY% scripts\51_year_opendrift.py --deactivate_outside

echo [duyarlilik] %date% %time% - 1/7 taban v2 (alan disi biter)
%S51% --mode both --tag base2
%PY% scripts\52_seasonal_maps.py --tag base2

echo [duyarlilik] %date% %time% - 2/7 windage 0.03
%S51% --mode both --windage 0.03 --tag w3
%PY% scripts\52_seasonal_maps.py --tag w3

echo [duyarlilik] %date% %time% - 3/7 windage 0.01
%S51% --mode grid --windage 0.01 --tag w1
%PY% scripts\52_seasonal_maps.py --tag w1

echo [duyarlilik] %date% %time% - 4/7 dogrudan ruzgar suruklemesi yok (windage 0)
%S51% --mode grid --no-wind --tag w0
%PY% scripts\52_seasonal_maps.py --tag w0

echo [duyarlilik] %date% %time% - 5/7 difuzyon 1 m2/s
%S51% --mode grid --diffusivity 1 --tag d1
%PY% scripts\52_seasonal_maps.py --tag d1

echo [duyarlilik] %date% %time% - 6/7 difuzyon 10 m2/s
%S51% --mode grid --diffusivity 10 --tag d10
%PY% scripts\52_seasonal_maps.py --tag d10

rem 7/7 PAHALI: refloat'ta oturan parcacik aktif kalir (donuk), tabandaki gibi 1 gunde pasiflesmez -> her adimda
rem ~10x fazla parcacik icin ortam okunur. O yuzden 2 km izgara x 5 parcacik (~16k/ay). Once tek ayla sure olc:
rem   %S51% --mode grid --refloat_days 5 --track_days 45 --cell_km 2 --n_grid 5 --tag rf5 --month 2026-06
echo [duyarlilik] %date% %time% - 7/7 yeniden yuzdurme (lambda_R 5 gun, izleme 45 gun, 2 km izgara)
%S51% --mode both --refloat_days 5 --track_days 45 --cell_km 2 --n_grid 5 --tag rf5
%PY% scripts\52_seasonal_maps.py --tag rf5

echo [duyarlilik] %date% %time% - karsilastirma tablosu
%PY% scripts\54_sensitivity.py --base base2 --tags w3 w1 w0 d1 d10 rf5
echo [duyarlilik] %date% %time% - bitti: runs\opendrift\year\sensitivity\
pause
