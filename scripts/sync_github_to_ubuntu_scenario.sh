#!/usr/bin/env bash
# sync_github_to_ubuntu_scenario.sh
# ==================================
# Prepara el entorno Ubuntu para ejecutar la tarea de cambio de batería.
#
# Lo que hace:
#   1. Instala los modelos URDF en el directorio de obstáculos de Kautham.
#   2. Actualiza el tampconfig con los controles normalizados del CSV de lab.
#
# Uso:
#   bash scripts/sync_github_to_ubuntu_scenario.sh
#
# Requiere:
#   - Kautham instalado (kautham disponible en PATH o en /usr/share/kautham)
#   - Python 3
#   - El CSV scripts/lab_controls.csv con las posiciones del robot real
set -e

# Ruta raíz del repositorio (un nivel por encima de este script)
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Repositorio: $REPO"

# ── 1. Instalar modelos URDF en Kautham ────────────────────────────────────
bash "$REPO/scripts/install_battery_models.sh"

# ── 2. Actualizar tampconfig con posiciones del CSV del laboratorio ─────────
TAMPCONFIG="$REPO/kautham/tampconfig_battery.xml"
CSV="$REPO/scripts/lab_controls.csv"

if [ -f "$CSV" ]; then
    echo ""
    echo "=== Actualizando tampconfig con valores del CSV..."
    python3 "$REPO/scripts/ur3_real_to_kautham_controls.py" \
        --csv "$CSV" \
        --tampconfig "$TAMPCONFIG" \
        --write
    echo "OK: tampconfig actualizado."
else
    echo "AVISO: no se encontró $CSV. El tampconfig NO ha sido actualizado."
fi

echo ""
echo "=== Listo. Ficheros Kautham en:"
echo "    Escena:       $REPO/kautham/OMPL_RRTConnect_battery_change_ur3.xml"
echo "    Tampconfig:   $REPO/kautham/tampconfig_battery.xml"
echo "    Kthconfig:    $REPO/kautham/kthconfig.xml"
echo "    PDDL dominio: $REPO/pddl/battery_domain.pddl"
echo "    PDDL problema: $REPO/pddl/battery_problem.pddl"
echo ""
echo "Para abrir Kautham:"
echo "    kautham $REPO/kautham/kthconfig.xml"
echo ""
echo "Para el pipeline TAMP (ajusta el nombre del launch si difiere):"
echo "    source ~/ws_tamp/install/setup.bash"
echo "    ros2 launch ktmpb tamp.launch.py \\"
echo "        kthconfig:=$REPO/kautham/kthconfig.xml \\"
echo "        tampconfig:=$REPO/kautham/tampconfig_battery.xml"
