#!/usr/bin/env bash
# SCHISM'i Ubuntu (WSL2) üzerinde kaynak koddan derler — lisans gerekmez.
# Aynı betik 19 Eyl 2026'da Ubuntu 24.04'te test edildi (gfortran 13, netCDF 4.9, ~5 dk).
#
# Kullanım (WSL2 Ubuntu terminalinde):
#   bash scripts/wsl_build_schism.sh            # ~/schism altına kurar
#   SCHISM_PREFIX=$HOME/schism bash scripts/wsl_build_schism.sh
set -euo pipefail
PREFIX="${SCHISM_PREFIX:-$HOME/schism}"
JOBS="${JOBS:-$(nproc)}"

echo "[1/4] paketler (sudo şifresi sorabilir)"
sudo apt-get update -q
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
  build-essential gfortran cmake git \
  libopenmpi-dev openmpi-bin \
  libnetcdf-dev libnetcdff-dev \
  libmetis-dev libparmetis-dev \
  python3 python3-pip python-is-python3

echo "[2/4] kaynak kod -> $PREFIX/src"
mkdir -p "$PREFIX"
if [ ! -d "$PREFIX/src/.git" ]; then
  git clone --depth 1 https://github.com/schism-dev/schism.git "$PREFIX/src"
else
  git -C "$PREFIX/src" pull --ff-only || true
fi

echo "[3/4] cmake + make (-j$JOBS)"
export CC=mpicc CXX=mpicxx FC=mpif90
rm -rf "$PREFIX/build"; mkdir -p "$PREFIX/build"
cmake -S "$PREFIX/src/src" -B "$PREFIX/build" \
  -DBLD_STANDALONE=ON -DCMAKE_BUILD_TYPE=Release \
  -DOLDIO=OFF -DTVD_LIM=VL \
  -DCMAKE_Fortran_FLAGS_RELEASE_INIT="-O2 -ffree-line-length-none" > "$PREFIX/cmake.log" 2>&1
make -C "$PREFIX/build" -j"$JOBS" pschism > "$PREFIX/build.log" 2>&1

echo "[4/4] kontrol"
EXE=$(ls "$PREFIX"/build/bin/pschism_* | head -1)
ln -sf "$EXE" "$PREFIX/pschism"
mpirun -np 1 "$EXE" -v
echo
echo "Hazır: $PREFIX/pschism  (çalıştırma: mpirun -np 4 $PREFIX/pschism 1   # son sayı: scribe sayısı)"
