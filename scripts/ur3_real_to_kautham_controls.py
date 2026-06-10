#!/usr/bin/env python3
import argparse
import csv
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

GRIPPER_DEFAULT = 0.813

# Conversión a controles normalizados de Kautham:
# j1, j2, j4, j5, j6: q_norm = (q_rad + 2*pi) / (4*pi)
# j3 / elbow:          q_norm = (q_rad + pi)   / (2*pi)
def rad_to_norm(q_rad: float, joint_index: int) -> float:
    if joint_index == 2:  # j3 = elbow
        return (q_rad + math.pi) / (2 * math.pi)
    return (q_rad + 2 * math.pi) / (4 * math.pi)

def parse_float(value: str, field: str) -> float:
    value = value.strip()
    if value == "":
        raise ValueError(f"Campo vacío en {field}")
    return float(value)

def row_to_controls(row):
    name = row["name"].strip()
    unit = row.get("unit", "deg").strip().lower() or "deg"

    qs = []
    for i in range(1, 7):
        q = parse_float(row[f"j{i}"], f"{name}.j{i}")

        if unit in ("deg", "degree", "degrees", "grados"):
            q = math.radians(q)
        elif unit in ("rad", "radian", "radians", "radianes"):
            pass
        else:
            raise ValueError(f"Unidad no reconocida en {name}: {unit}")

        qs.append(q)

    controls = [rad_to_norm(q, i) for i, q in enumerate(qs)]
    controls.append(GRIPPER_DEFAULT)

    warnings = []
    for i, c in enumerate(controls[:6], start=1):
        if not (0.0 <= c <= 1.0):
            warnings.append(f"{name}: j{i} normalizado fuera de [0,1]: {c:.4f}")

    return name, controls, warnings

def controls_to_text(controls):
    return " ".join(f"{c:.6f}" for c in controls)

ACTION_TO_CONTROL = {
    ("Pick",  "BOX_LID",     "BOX_CLOSED_POS"):  "C_BOX_LID_PICK",
    ("Place", "BOX_LID",     "LID_OPEN_AREA"):   "C_LID_OPEN_PLACE",

    ("Pick",  "BATTERY_OLD", "INSIDE_BOX"):      "C_BATTERY_OLD_PICK",
    ("Place", "BATTERY_OLD", "DISCARD_AREA"):    "C_USED_PLACE",

    ("Pick",  "BATTERY_NEW", "BATTERY_STORAGE"): "C_BATTERY_NEW_PICK",
    ("Place", "BATTERY_NEW", "INSIDE_BOX"):      "C_INSIDE_PLACE",

    ("Pick",  "BOX_LID",     "LID_OPEN_AREA"):   "C_LID_OPEN_PLACE",
    ("Place", "BOX_LID",     "BOX_CLOSED_POS"):  "C_BOX_LID_PICK",
}

def read_controls_csv(csv_path: Path):
    controls_by_name = {}
    all_warnings = []

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if not row.get("name", "").strip():
                continue

            name, controls, warnings = row_to_controls(row)
            controls_by_name[name] = controls
            all_warnings.extend(warnings)

    return controls_by_name, all_warnings

def patch_tampconfig(tampconfig_path: Path, controls_by_name: dict, write: bool):
    tree = ET.parse(tampconfig_path)
    root = tree.getroot()

    home_controls = controls_by_name.get("C_HOME_SAFE")
    if home_controls is None:
        raise ValueError("Falta C_HOME_SAFE en el CSV")

    robot = root.find("./States/Initial/Robot")
    if robot is not None:
        robot.text = controls_to_text(home_controls)

    updated = []

    actions = root.find("./Actions")
    if actions is None:
        raise ValueError("No encuentro <Actions> en tampconfig")

    for action in list(actions):
        tag = action.tag
        obj = action.attrib.get("object")
        region = action.attrib.get("region")
        key = (tag, obj, region)

        if key not in ACTION_TO_CONTROL:
            continue

        control_name = ACTION_TO_CONTROL[key]

        if control_name not in controls_by_name:
            raise ValueError(f"Falta {control_name} en el CSV para acción {key}")

        home = action.find("HomeControls")
        if home is not None:
            home.text = controls_to_text(home_controls)

        grasp = action.find("GraspControls")
        if grasp is not None:
            grasp.text = controls_to_text(controls_by_name[control_name])

        updated.append((tag, obj, region, control_name))

    if write:
        tree.write(tampconfig_path, encoding="utf-8", xml_declaration=True)

    return updated

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="CSV con articulaciones reales")
    parser.add_argument("--tampconfig", help="Ruta a tampconfig_battery.xml")
    parser.add_argument("--write", action="store_true", help="Escribe cambios en tampconfig")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    controls_by_name, warnings = read_controls_csv(csv_path)

    print("\n=== CONTROLES NORMALIZADOS PARA KAUTHAM ===")
    for name, controls in controls_by_name.items():
        print(f"{name}: {controls_to_text(controls)}")

    if warnings:
        print("\n=== AVISOS ===", file=sys.stderr)
        for w in warnings:
            print(w, file=sys.stderr)

    if args.tampconfig:
        updated = patch_tampconfig(Path(args.tampconfig), controls_by_name, args.write)

        print("\n=== ACCIONES ACTUALIZADAS ===")
        for tag, obj, region, control_name in updated:
            print(f"{tag} {obj} {region} <- {control_name}")

        if args.write:
            print(f"\nOK: tampconfig actualizado: {args.tampconfig}")
        else:
            print("\nModo seco: no se ha escrito el tampconfig. Añade --write para modificarlo.")

if __name__ == "__main__":
    main()
