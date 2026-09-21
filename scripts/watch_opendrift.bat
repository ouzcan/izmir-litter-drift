@echo off
rem Yillik OpenDrift partileri icin gozcu: yuzey dosyasi hazir olan aylari kosar,
rem biten aylari ve izleme ayi henuz hazir olmayan aylari atlar. SCHISM yillik
rem kosusu sururken acik birakilabilir; her turdan sonra 30 dk bekler.
rem Kullanim (Windows, conda litter): scripts\watch_opendrift.bat
setlocal
cd /d "%~dp0.."
:loop
echo [gozcu] %date% %time% - tarama basliyor
python scripts\51_year_opendrift.py --mode both
echo [gozcu] %date% %time% - tur bitti, 30 dk bekleniyor (cikmak icin Ctrl+C)
timeout /t 1800 /nobreak >nul
goto loop
