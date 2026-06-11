#!/usr/bin/env python3

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

# Base visual: 6 mm.
# Base de colisión: 4 mm.
# Se mantiene fija la cara inferior y se baja 2 mm la cara superior.
TARGET_HEIGHT = 0.004
TARGET_CENTER_Z = 0.002


def values(text):
    return [float(value) for value in text.split()]


parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True)
args = parser.parse_args()

path = Path(args.model)

tree = ET.parse(path)
root = tree.getroot()

modified = 0

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

        if origin is None:
            origin = ET.Element(
                "origin",
                {"xyz": "0 0 0", "rpy": "0 0 0"},
            )
            collision.insert(0, origin)

        xyz = values(origin.attrib.get("xyz", "0 0 0"))

        # Identificar la base horizontal:
        # ocupa prácticamente toda la caja y tiene poca altura.
        is_base = (
            size[0] > 0.060
            and size[1] > 0.090
            and size[2] <= 0.010
        )

        if not is_base:
            continue

        print("Base encontrada:")
        print("  size anterior:", size)
        print("  xyz anterior: ", xyz)

        size[2] = TARGET_HEIGHT
        xyz[2] = TARGET_CENTER_Z

        box.set(
            "size",
            " ".join(f"{value:.6f}" for value in size),
        )

        origin.set(
            "xyz",
            " ".join(f"{value:.6f}" for value in xyz),
        )

        print("  size nueva:   ", size)
        print("  xyz nueva:    ", xyz)

        modified += 1

if modified != 1:
    raise RuntimeError(
        f"Se esperaba modificar una base y se modificaron {modified}"
    )

ET.indent(tree, space="  ")
tree.write(path, encoding="utf-8", xml_declaration=True)

print("\nOK: holgura inferior de 2 mm aplicada.")
print("Las paredes y las geometrías visuales no se han modificado.")
