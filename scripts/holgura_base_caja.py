#!/usr/bin/env python3

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

HOLGURA = 0.002  # 2 mm


def values(text):
    return [float(value) for value in text.split()]


parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True)
args = parser.parse_args()

path = Path(args.model)

tree = ET.parse(path)
root = tree.getroot()

candidates = []

for link in root.findall("link"):
    for collision in link.findall("collision"):
        geometry = collision.find("geometry")
        origin = collision.find("origin")

        if geometry is None:
            continue

        box = geometry.find("box")

        if box is None:
            continue

        size = values(box.attrib["size"])

        # Buscamos piezas horizontales finas.
        if size[2] <= 0.010:
            footprint = size[0] * size[1]
            candidates.append(
                (footprint, link, collision, box, origin, size)
            )

if not candidates:
    raise RuntimeError("No se ha encontrado ninguna base horizontal.")

# La base es la pieza horizontal con mayor superficie.
_, link, collision, box, origin, size = max(
    candidates,
    key=lambda item: item[0],
)

if origin is None:
    origin = ET.Element(
        "origin",
        {"xyz": "0 0 0", "rpy": "0 0 0"},
    )
    collision.insert(0, origin)

xyz = values(origin.attrib.get("xyz", "0 0 0"))

old_height = size[2]
old_z = xyz[2]

if old_height <= HOLGURA + 0.001:
    raise RuntimeError(
        f"La base es demasiado fina: altura={old_height}"
    )

# Reducimos la cara superior manteniendo fija la cara inferior.
size[2] = old_height - HOLGURA
xyz[2] = old_z - HOLGURA / 2.0

box.set(
    "size",
    " ".join(f"{value:.6f}" for value in size),
)

origin.set(
    "xyz",
    " ".join(f"{value:.6f}" for value in xyz),
)

ET.indent(tree, space="  ")
tree.write(path, encoding="utf-8", xml_declaration=True)

print("Base modificada en:", path)
print("Link:", link.attrib.get("name"))
print(f"Altura:  {old_height:.6f} -> {size[2]:.6f}")
print(f"Centro Z: {old_z:.6f} -> {xyz[2]:.6f}")
print("Visuales y paredes sin modificar.")
