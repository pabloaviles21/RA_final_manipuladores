from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


CONFIG_START_INDEX = 9
CONFIG_END_INDEX = 15


def parse_configurations(xml_path: Path) -> list[tuple[str, list[list[float]]]]:
	tree = ET.parse(xml_path)
	root = tree.getroot()

	blocks: list[tuple[str, list[list[float]]]] = []
	for element in root:
		if element.tag not in {"Transit", "Transfer"}:
			continue

		configurations: list[list[float]] = []
		for conf in element.findall("Conf"):
			text = (conf.text or "").strip()
			if not text:
				continue
			values = [float(value) for value in text.split()]
			configurations.append(values[CONFIG_START_INDEX:CONFIG_END_INDEX])

		blocks.append((element.tag, configurations))

	return blocks


def format_configurations(blocks: list[tuple[str, list[list[float]]]]) -> str:
	lines: list[str] = []
	for block_index, (block_type, configurations) in enumerate(blocks, start=1):
		variable_name = f"path_{block_index}_{block_type.lower()}"
		lines.append(f"{variable_name} = [")
		for configuration in configurations:
			lines.append(f"  {configuration},")
		lines.append("]")
		lines.append("")

	return "\n".join(lines).rstrip() + "\n"


def format_execution_commands(blocks: list[tuple[str, list[list[float]]]]) -> str:
	lines: list[str] = []
	for block_index, (block_type, _) in enumerate(blocks, start=1):
		variable_name = f"path_{block_index}_{block_type.lower()}"
		lines.append(f"send_joint_path({variable_name}, sock)")
		if block_index == len(blocks):
			continue

		next_block_type = blocks[block_index][0]
		if block_type == next_block_type:
			lines.append("# Se envia la trayectoria a la controladora del robot")
			continue

		if block_type == "Transit":
			lines.append("# Enviar archivo script abrir pinza")
			lines.append("with open(Cerrar_pinza, 'rb') as f: sock.sendall(f.read())")
		else:
			lines.append("# Enviar archivo script cerrar pinza")
			lines.append("with open(Abrir_pinza, 'rb') as f: sock.sendall(f.read())")
		lines.append("time.sleep(1)")
		lines.append("# Se envia la trayectoria a la controladora del robot")

	return "\n".join(lines).rstrip() + "\n"


def main() -> None:
	xml_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("taskfile_tampconfig_chess_PF.xml")
	result = parse_configurations(xml_file)
	out_file = xml_file.with_suffix(".txt")
	out_file.write_text(format_configurations(result), encoding="utf-8")
	commands_file = xml_file.with_name(f"{xml_file.stem}_calls.txt")
	commands_file.write_text(format_execution_commands(result), encoding="utf-8")
	print(f"Resultado guardado en {out_file}")
	print(f"Secuencia guardada en {commands_file}")


if __name__ == "__main__":
	main()
