#!/usr/bin/env bash
set -e

GIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$GIT_DIR/kautham/battery_task_models"
DST="/usr/share/kautham/demos/models/obstacles/battery_task"

echo "Instalando modelos battery_task..."
echo "Desde: $SRC"
echo "Hacia: $DST"

if [ ! -d "$SRC" ]; then
  echo "ERROR: no existe $SRC"
  exit 1
fi

sudo mkdir -p "$DST"
sudo cp "$SRC"/*.urdf "$DST"/

echo "OK: modelos instalados en $DST"
