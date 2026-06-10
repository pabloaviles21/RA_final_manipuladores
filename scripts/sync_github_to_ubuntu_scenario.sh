#!/usr/bin/env bash
set -e

GIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCENARIO="${SCENARIO:-$HOME/ws_tamp/src/task_and_motion_planning2/ktmpb/ktmpb_demos/OMPL_geometric_demos/battery_change_ur3}"

echo "Sincronizando GitHub -> Ubuntu scenario"
echo "GitHub:   $GIT_DIR"
echo "Scenario: $SCENARIO"

mkdir -p "$SCENARIO"
mkdir -p "$SCENARIO/ff-domains"
mkdir -p "$SCENARIO/controls"

cp "$GIT_DIR/kautham/OMPL_RRTConnect_battery_change_ur3.xml" "$SCENARIO/"
cp "$GIT_DIR/kautham/tampconfig_battery.xml" "$SCENARIO/"
cp "$GIT_DIR/kautham/kthconfig.xml" "$SCENARIO/"

cp "$GIT_DIR/kautham/controls/right_ur3_with_gripper.cntr" "$SCENARIO/controls/"

if [ -f "$GIT_DIR/kautham/taskfile_tampconfig_battery.xml" ]; then
  cp "$GIT_DIR/kautham/taskfile_tampconfig_battery.xml" "$SCENARIO/"
fi

cp "$GIT_DIR/pddl/battery_domain.pddl" "$SCENARIO/ff-domains/"
cp "$GIT_DIR/pddl/battery_problem.pddl" "$SCENARIO/ff-domains/"

bash "$GIT_DIR/scripts/install_battery_models.sh"

echo "OK: sincronización completada."
