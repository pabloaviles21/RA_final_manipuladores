#!/usr/bin/env python3
import argparse
import csv
import math
import xml.etree.ElementTree as ET
from pathlib import Path

GRIPPER = 0.813

ACTION_MAP = {
    ("Pick", "BOX_LID", "BOX_CLOSED_POS"): "C_BOX_LID_PICK",
    ("Place", "BOX_LID", "LID_OPEN_AREA"): "C_LID_OPEN_PLACE",
    ("Pick", "BATTERY_OLD", "INSIDE_BOX"): "C_BATTERY_OLD_PICK",
    ("Place", "BATTERY_OLD", "DISCARD_AREA"): "C_USED_PLACE",
    ("Pick", "BATTERY_NEW", "BATTERY_STORAGE"): "C_BATTERY_NEW_PICK",
    ("Place", "BATTERY_NEW", "INSIDE_BOX"): "C_INSIDE_PLACE",
    ("Pick", "BOX_LID", "LID_OPEN_AREA"): "C_LID_OPEN_PLACE",
    ("Place", "BOX_LID", "BOX_CLOSED_POS"): "C_BOX_LID_PICK",
}

def rad_to_norm(q, index):
    if index == 2:
        return (q + math.pi) / (2 * math.pi)
    return (q + 2 * math.pi) / (4 * math.pi)

def read_csv(path):
    result = {}

    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row.get("name", "").strip()
            if not name:
                continue

            unit = row.get("unit", "deg").strip().lower()
            values = []

            for i in range(1, 7):
                raw = row.get(f"j{i}", "").strip()
                if not raw:
                    raise ValueError(f"Falta {name}.j{i}")

                q = float(raw)

                if unit == "deg":
                    q = math.radians(q)
                elif unit != "rad":
                    raise ValueError(f"Unidad no válida en {name}: {unit}")

                values.append(q)

            normalized = [
                rad_to_norm(q, i)
                for i, q in enumerate(values)
            ]
            result[name] = normalized + [GRIPPER]

    return result

def text(values):
    return " ".join(f"{v:.6f}" for v in values)

parser = argparse.ArgumentParser()
parser.add_argument("--csv", required=True)
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()

controls = read_csv(Path(args.csv))

required = {
    "C_HOME_SAFE",
    "C_TRANSIT_SAFE",
    *ACTION_MAP.values(),
}

missing = required - controls.keys()
if missing:
    raise ValueError("Faltan controles: " + ", ".join(sorted(missing)))

tree = ET.parse(args.input)
root = tree.getroot()

# Kautham empieza en TRANSIT_SAFE.
robot = root.find("./States/Initial/Robot")
if robot is None:
    raise ValueError("No se encuentra ./States/Initial/Robot")

robot.text = text(controls["C_TRANSIT_SAFE"])

actions = root.find("./Actions")
if actions is None:
    raise ValueError("No se encuentra <Actions>")

updated = 0

for action in list(actions):
    key = (
        action.tag,
        action.attrib.get("object"),
        action.attrib.get("region"),
    )

    if key not in ACTION_MAP:
        continue

    home = action.find("HomeControls")
    grasp = action.find("GraspControls")

    if home is None or grasp is None:
        raise ValueError(f"Acción incompleta: {key}")

    # Todos los retornos intermedios van a TRANSIT_SAFE.
    home.text = text(controls["C_TRANSIT_SAFE"])

    target_name = ACTION_MAP[key]
    grasp.text = text(controls[target_name])

    print(f"{key} -> home=C_TRANSIT_SAFE, grasp={target_name}")
    updated += 1

ET.indent(tree, space="    ")
tree.write(args.output, encoding="utf-8", xml_declaration=True)

print(f"\nAcciones actualizadas: {updated}")
print(f"Generado: {args.output}")
