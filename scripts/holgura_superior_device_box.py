#!/usr/bin/env python3

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

HOLGURA = 0.004  # 4 mm


def vector(text):
    return [float(value) for value in text.split()]


parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True)
args = parser.parse_args()

path = Path(args.model)

tree = ET.parse(path)
root = tree.getroot()

modified = 0

print("=== GEOMETRÍAS DE COLISIÓN ===")

for link in root.findall("link"):
    for collision in link.findall("collision"):
        geometry = collision.find("geometry")
        origin = collision.find("origin")

        if geometry is None:
            continue

        box = geometry.find("box")

        if box is None:
            continue

        size = vector(box.attrib["size"])

        if origin is None:
            origin = ET.Element(
                "origin",
                {"xyz": "0 0 0", "rpy": "0 0 0"},
            )
            collision.insert(0, origin)

        xyz = vector(origin.attrib.get("xyz", "0 0 0"))

        print(
            f'{link.attrib.get("name", "link"):20s} '
            f'size={size} xyz={xyz}'
        )

        # Pared vertical:
        # - altura apreciable en Z;
        # - fina en X o en Y.
        is_vertical_wall = (
            size[2] > 0.015
            and min(size[0], size[1]) < 0.015
        )

        if not is_vertical_wall:
            continue

        if size[2] <= HOLGURA + 0.002:
            raise RuntimeError(
                f"Pared demasiado baja para aplicar holgura: {size}"
            )

        old_height = size[2]
        old_z = xyz[2]

        # Reducimos el borde superior manteniendo fija la parte inferior.
        size[2] -= HOLGURA
        xyz[2] -= HOLGURA / 2.0

        box.set(
            "size",
            " ".join(f"{value:.6f}" for value in size),
        )

        origin.set(
            "xyz",
            " ".join(f"{value:.6f}" for value in xyz),
        )

        print(
            "  MODIFICADA:"
            f" altura {old_height:.6f} -> {size[2]:.6f},"
            f" centro Z {old_z:.6f} -> {xyz[2]:.6f}"
        )

        modified += 1

if modified != 4:
    print(
        f"\nAVISO: se esperaban 4 paredes verticales "
        f"y se han modificado {modified}."
    )

ET.indent(tree, space="  ")
tree.write(path, encoding="utf-8", xml_declaration=True)

print(f"\nParedes modificadas: {modified}")
print("La geometría visual no se ha tocado.")
