#!/usr/bin/env python3

import argparse
import copy
import xml.etree.ElementTree as ET
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    path = Path(args.model)

    if not path.exists():
        raise FileNotFoundError(path)

    tree = ET.parse(path)
    root = tree.getroot()

    total_visuals = 0
    total_collisions = 0

    for link in root.findall("link"):
        visuals = list(link.findall("visual"))

        if not visuals:
            continue

        # Eliminamos las colisiones anteriores del link para evitar
        # geometrías duplicadas o paredes antiguas.
        for collision in list(link.findall("collision")):
            link.remove(collision)

        for index, visual in enumerate(visuals, start=1):
            geometry = visual.find("geometry")

            if geometry is None:
                continue

            collision = ET.Element(
                "collision",
                {
                    "name": (
                        f'{link.attrib.get("name", "link")}'
                        f"_collision_{index}"
                    )
                },
            )

            origin = visual.find("origin")

            if origin is not None:
                collision.append(copy.deepcopy(origin))

            collision.append(copy.deepcopy(geometry))
            link.append(collision)

            total_visuals += 1
            total_collisions += 1

    if total_collisions == 0:
        raise RuntimeError(
            f"No se encontraron geometrías visuales en {path}"
        )

    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)

    print(f"Modelo actualizado: {path}")
    print(f"Visuales convertidas: {total_visuals}")
    print(f"Colisiones generadas: {total_collisions}")


if __name__ == "__main__":
    main()
