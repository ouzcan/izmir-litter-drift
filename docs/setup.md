# Kurulum

## 1. Hesaplar (bir kez)

| Servis | Adres | Ne için | Sonra ne yapılır |
| --- | --- | --- | --- |
| Copernicus Marine | https://marine.copernicus.eu (Register) | Akıntı ve dalga verisi | Kullanıcı adı/şifre → `copernicusmarine login` |
| Copernicus CDS | https://cds.climate.copernicus.eu (Register) | ERA5 rüzgâr | Profil sayfasındaki API anahtarı → `~/.cdsapirc`; ERA5 lisansını kabul et |
| GitHub | https://github.com | Kod deposu | `izmir-litter-drift` deposu aç, bu klasörü push et |
| ORCID | https://orcid.org | Makale | Kayıt ol, numarayı `paper/authors.md`'ye yaz |
| Zenodo | https://zenodo.org | Veri/kod DOI | GitHub ile bağla (Faz 4) |

Kimlik bilgileri asla depoya girmez (`.gitignore` içinde `.env`, `.cdsapirc`, `.copernicusmarine/`).

## 2. Python ortamı (Windows)

OpenDrift Windows'ta en sorunsuz conda-forge ile kurulur.

```powershell
# Miniforge kur: https://github.com/conda-forge/miniforge (Windows x86_64)
conda env create -f environment.yml
conda activate litter
python -c "import opendrift, copernicusmarine; print(opendrift.__version__)"
```

Linux/macOS/VM için aynı komutlar geçerli; `uv`/`pip` ile kurulum da mümkün ama
`cartopy`/`netcdf4` derlemesi zahmetli olabilir.

## 3. Copernicus girişleri

```powershell
copernicusmarine login          # kullanıcı adı + şifre sorar, ~/.copernicusmarine altına yazar
```

`~/.cdsapirc` (Windows: `C:\Users\<kullanıcı>\.cdsapirc`):

```
url: https://cds.climate.copernicus.eu/api
key: <profil sayfandaki anahtar>
```

## 4. İlk veri ve ilk koşu

Copernicus, CDS, EMODnet ve OSM sunucularına Claude'un çalışma ortamlarından erişilemiyor;
veri indiren ve model koşan betikler **senin bilgisayarında** çalışır. Çıktılar depo klasörüne
yazıldığı için Claude sonuçları oradan okur.

```powershell
cd C:\Users\PC\source\repos\izmir-litter-drift
python scripts\01_download_sample.py 2026-09-06 7   # 1 hafta MED akıntı + dalga + ERA5 rüzgâr, alan A
python scripts\02_test_run.py 2026-09-06            # Bostanlı'dan 100 parçacık, 3 gün
```

Çıktılar `runs/test_bostanli/20260906/` altına: `track.nc`, `track.png`, `track.gif`, `summary.txt`.

## 5. Kontrol

```powershell
python scripts/00_check_env.py
```
