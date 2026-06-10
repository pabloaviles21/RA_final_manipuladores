#!/usr/bin/env python3
import csv
import math
import argparse
from pathlib import Path

ORDER = [
    ("path_1_go_pick_lid", "C_HOME_SAFE", "C_BOX_LID_PICK", "close"),
    ("path_2_go_place_lid", "C_HOME_SAFE", "C_LID_OPEN_PLACE", "open"),

    ("path_3_go_pick_old_battery", "C_HOME_SAFE", "C_BATTERY_OLD_PICK", "close"),
    ("path_4_go_place_old_battery", "C_HOME_SAFE", "C_USED_PLACE", "open"),

    ("path_5_go_pick_new_battery", "C_HOME_SAFE", "C_BATTERY_NEW_PICK", "close"),
    ("path_6_go_place_new_battery", "C_HOME_SAFE", "C_INSIDE_PLACE", "open"),

    ("path_7_go_pick_lid_again", "C_HOME_SAFE", "C_LID_OPEN_PLACE", "close"),
    ("path_8_go_close_lid", "C_HOME_SAFE", "C_BOX_LID_PICK", "open"),
]

def to_rad(row):
    unit = row["unit"].strip().lower()
    qs = [float(row[f"j{i}"].strip()) for i in range(1, 7)]

    if unit in ("deg", "degree", "degrees", "grados"):
        return [math.radians(q) for q in qs]
    if unit in ("rad", "radian", "radians", "radianes"):
        return qs

    raise ValueError(f"Unidad no reconocida en {row['name']}: {unit}")

def interpolate(q_start, q_goal, steps=10):
    path = []
    for s in range(steps + 1):
        a = s / steps
        q = [(1 - a) * q_start[i] + a * q_goal[i] for i in range(6)]
        path.append(q)
    return path

def fmt(q):
    return "[" + ", ".join(f"{x:.6f}" for x in q) + "]"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--steps", type=int, default=10)
    args = parser.parse_args()

    csv_path = Path(args.csv)
    out_path = Path(args.out)

    controls = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["name"].strip()
            if name:
                controls[name] = to_rad(row)

    missing = []
    for _, home_name, target_name, _ in ORDER:
        if home_name not in controls:
            missing.append(home_name)
        if target_name not in controls:
            missing.append(target_name)

    if missing:
        raise SystemExit(f"Faltan posiciones: {sorted(set(missing))}")

    path_lines = []
    call_lines = []

    path_lines.append("# Trayectorias generadas desde lab_controls.csv")
    path_lines.append("# Valores en radianes: [base, shoulder, elbow, wrist1, wrist2, wrist3]")
    path_lines.append("")

    for path_name, home_name, target_name, gripper_action in ORDER:
        home = controls[home_name]
        target = controls[target_name]

        full_path = interpolate(home, target, args.steps) + interpolate(target, home, args.steps)[1:]

        path_lines.append(f"{path_name} = [")
        for q in full_path:
            path_lines.append(f"  {fmt(q)},")
        path_lines.append("]")
        path_lines.append("")

        call_lines.append(f"send_joint_path({path_name}, sock)")

        if gripper_action == "close":
            call_lines.append("# Cerrar pinza")
            call_lines.append("with open(Cerrar_pinza, 'rb') as f: sock.sendall(f.read())")
        else:
            call_lines.append("# Abrir pinza")
            call_lines.append("with open(Abrir_pinza, 'rb') as f: sock.sendall(f.read())")

        call_lines.append("time.sleep(1)")
        call_lines.append("")

    out_path.write_text("\n".join(path_lines), encoding="utf-8")
    calls_path = out_path.with_name(out_path.stem + "_calls.py")
    calls_path.write_text("\n".join(call_lines), encoding="utf-8")

    print(f"OK: trayectorias guardadas en {out_path}")
    print(f"OK: llamadas guardadas en {calls_path}")

if __name__ == "__main__":
    main()
