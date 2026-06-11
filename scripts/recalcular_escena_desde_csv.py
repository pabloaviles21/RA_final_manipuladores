#!/usr/bin/env python3

import argparse
import csv
import math
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np


ARM_JOINT_SUFFIXES = [
    "shoulder_pan_joint",
    "shoulder_lift_joint",
    "elbow_joint",
    "wrist_1_joint",
    "wrist_2_joint",
    "wrist_3_joint",
]

LEFT_TIP_SUFFIX = "robotiq_85_left_finger_tip_link"
RIGHT_TIP_SUFFIX = "robotiq_85_right_finger_tip_link"


def parse_values(text, length):
    if not text:
        return np.zeros(length)

    values = [float(value) for value in text.split()]

    if len(values) != length:
        raise ValueError(f"Se esperaban {length} valores: {text}")

    return np.array(values, dtype=float)


def homogeneous(rotation=None, translation=None):
    matrix = np.eye(4)

    if rotation is not None:
        matrix[:3, :3] = rotation

    if translation is not None:
        matrix[:3, 3] = translation

    return matrix


def rotation_rpy(rpy):
    roll, pitch, yaw = rpy

    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)

    rx = np.array([
        [1, 0, 0],
        [0, cr, -sr],
        [0, sr, cr],
    ])

    ry = np.array([
        [cp, 0, sp],
        [0, 1, 0],
        [-sp, 0, cp],
    ])

    rz = np.array([
        [cy, -sy, 0],
        [sy, cy, 0],
        [0, 0, 1],
    ])

    return rz @ ry @ rx


def rotation_axis_angle(axis, angle):
    axis = np.array(axis, dtype=float)
    norm = np.linalg.norm(axis)

    if norm < 1e-12 or abs(angle) < 1e-12:
        return np.eye(3)

    axis /= norm
    x, y, z = axis

    skew = np.array([
        [0, -z, y],
        [z, 0, -x],
        [-y, x, 0],
    ])

    return (
        np.eye(3)
        + math.sin(angle) * skew
        + (1 - math.cos(angle)) * (skew @ skew)
    )


def read_csv_joints(path):
    configurations = {}

    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            name = row.get("name", "").strip()

            if not name:
                continue

            unit = row.get("unit", "deg").strip().lower()
            joints = []

            for index in range(1, 7):
                raw = row.get(f"j{index}", "").strip()

                if not raw:
                    break

                value = float(raw)

                if unit in ("deg", "degree", "degrees", "grados"):
                    value = math.radians(value)
                elif unit not in ("rad", "radian", "radians", "radianes"):
                    raise ValueError(
                        f"Unidad no válida en {name}: {unit}"
                    )

                joints.append(value)

            if len(joints) == 6:
                configurations[name] = np.array(joints)

    return configurations


def expand_robot_xacro(robot_path):
    result = subprocess.run(
        ["xacro", str(robot_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    return ET.fromstring(result.stdout)


def read_urdf_joints(root):
    joints = {}
    child_to_joint = {}

    for element in root.findall("joint"):
        name = element.attrib["name"]
        joint_type = element.attrib.get("type", "fixed")

        parent = element.find("parent").attrib["link"]
        child = element.find("child").attrib["link"]

        origin = element.find("origin")

        xyz = np.zeros(3)
        rpy = np.zeros(3)

        if origin is not None:
            xyz = parse_values(origin.attrib.get("xyz", "0 0 0"), 3)
            rpy = parse_values(origin.attrib.get("rpy", "0 0 0"), 3)

        axis_element = element.find("axis")
        axis = np.array([1.0, 0.0, 0.0])

        if axis_element is not None:
            axis = parse_values(
                axis_element.attrib.get("xyz", "1 0 0"),
                3,
            )

        mimic_element = element.find("mimic")
        mimic = None

        if mimic_element is not None:
            mimic = {
                "joint": mimic_element.attrib["joint"],
                "multiplier": float(
                    mimic_element.attrib.get("multiplier", "1")
                ),
                "offset": float(
                    mimic_element.attrib.get("offset", "0")
                ),
            }

        joints[name] = {
            "name": name,
            "type": joint_type,
            "parent": parent,
            "child": child,
            "xyz": xyz,
            "rpy": rpy,
            "axis": axis,
            "mimic": mimic,
        }

        child_to_joint[child] = joints[name]

    return joints, child_to_joint


def find_name_by_suffix(names, suffix):
    exact = [name for name in names if name == suffix]

    if exact:
        return exact[0]

    matches = [name for name in names if name.endswith(suffix)]

    if len(matches) != 1:
        raise RuntimeError(
            f"No se puede identificar '{suffix}'. Coincidencias: {matches}"
        )

    return matches[0]


def build_chain(child_to_joint, target_link):
    chain = []
    current = target_link

    while current in child_to_joint:
        joint = child_to_joint[current]
        chain.append(joint)
        current = joint["parent"]

    chain.reverse()
    return chain


def joint_transform(joint, value):
    origin = homogeneous(
        rotation=rotation_rpy(joint["rpy"]),
        translation=joint["xyz"],
    )

    joint_type = joint["type"]

    if joint_type in ("revolute", "continuous"):
        movement = homogeneous(
            rotation=rotation_axis_angle(joint["axis"], value)
        )

    elif joint_type == "prismatic":
        movement = homogeneous(
            translation=joint["axis"] * value
        )

    else:
        movement = np.eye(4)

    return origin @ movement


def resolve_joint_value(name, joints, explicit_values, cache):
    if name in cache:
        return cache[name]

    if name in explicit_values:
        value = explicit_values[name]

    else:
        mimic = joints[name]["mimic"]

        if mimic is not None:
            source = resolve_joint_value(
                mimic["joint"],
                joints,
                explicit_values,
                cache,
            )

            value = (
                mimic["multiplier"] * source
                + mimic["offset"]
            )
        else:
            # Los joints de la pinza no afectan al punto medio de forma
            # significativa; se dejan en su valor neutro.
            value = 0.0

    cache[name] = value
    return value


def forward_kinematics(chain, joints, explicit_values):
    transform = np.eye(4)
    cache = {}

    for joint in chain:
        value = resolve_joint_value(
            joint["name"],
            joints,
            explicit_values,
            cache,
        )

        transform = transform @ joint_transform(joint, value)

    return transform


def robot_world_transform(robot_element):
    home = robot_element.find("Home")

    translation = np.array([
        float(home.attrib.get("X", "0")),
        float(home.attrib.get("Y", "0")),
        float(home.attrib.get("Z", "0")),
    ])

    axis = np.array([
        float(home.attrib.get("WX", "1")),
        float(home.attrib.get("WY", "0")),
        float(home.attrib.get("WZ", "0")),
    ])

    angle = float(home.attrib.get("TH", "0"))

    return homogeneous(
        rotation=rotation_axis_angle(axis, angle),
        translation=translation,
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--csv", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument(
        "--models",
        default="/usr/share/kautham/demos/models",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv)
    scenario = Path(args.scenario)
    models = Path(args.models)

    ompl_path = (
        scenario / "OMPL_RRTConnect_battery_change_ur3.xml"
    )
    tamp_path = scenario / "tampconfig_battery.xml"

    configurations = read_csv_joints(csv_path)

    required = {
        "C_BOX_LID_PICK",
        "C_BATTERY_OLD_PICK",
        "C_USED_PLACE",
        "C_BATTERY_NEW_PICK",
        "C_INSIDE_PLACE",
    }

    missing = required - configurations.keys()

    if missing:
        raise RuntimeError(
            "Faltan posiciones completas en el CSV: "
            + ", ".join(sorted(missing))
        )

    ompl_tree = ET.parse(ompl_path)
    ompl_root = ompl_tree.getroot()

    robot_element = ompl_root.find("Robot")

    if robot_element is None:
        raise RuntimeError("No se encuentra <Robot> en el OMPL")

    robot_reference = robot_element.attrib["robot"].lstrip("/")
    robot_path = models / robot_reference

    if not robot_path.exists():
        raise FileNotFoundError(robot_path)

    print("Robot Xacro:", robot_path)

    urdf_root = expand_robot_xacro(robot_path)
    joints, child_to_joint = read_urdf_joints(urdf_root)

    link_names = {
        link.attrib["name"]
        for link in urdf_root.findall("link")
    }

    left_tip = find_name_by_suffix(
        link_names,
        LEFT_TIP_SUFFIX,
    )

    right_tip = find_name_by_suffix(
        link_names,
        RIGHT_TIP_SUFFIX,
    )

    left_chain = build_chain(child_to_joint, left_tip)
    right_chain = build_chain(child_to_joint, right_tip)

    arm_joint_names = [
        find_name_by_suffix(joints.keys(), suffix)
        for suffix in ARM_JOINT_SUFFIXES
    ]

    print("Joints UR3:")
    for name in arm_joint_names:
        print(" ", name)

    world_from_robot = robot_world_transform(robot_element)

    centers = {}

    for config_name, q_values in configurations.items():
        explicit_values = {
            joint_name: float(q_value)
            for joint_name, q_value in zip(
                arm_joint_names,
                q_values,
            )
        }

        world_from_left = (
            world_from_robot
            @ forward_kinematics(
                left_chain,
                joints,
                explicit_values,
            )
        )

        world_from_right = (
            world_from_robot
            @ forward_kinematics(
                right_chain,
                joints,
                explicit_values,
            )
        )

        left_position = world_from_left[:3, 3]
        right_position = world_from_right[:3, 3]

        centers[config_name] = (
            left_position + right_position
        ) / 2.0

    print("\n=== CENTROS ENTRE LOS DEDOS ===")

    for name in sorted(required):
        point = centers[name]

        print(
            f"{name:22s} "
            f"X={point[0]:+.6f} "
            f"Y={point[1]:+.6f} "
            f"Z={point[2]:+.6f}"
        )

    inside_xy = np.mean([
        centers["C_BATTERY_OLD_PICK"][:2],
        centers["C_INSIDE_PLACE"][:2],
    ], axis=0)

    positions = {
        "device_box": inside_xy,
        "box_lid": centers["C_BOX_LID_PICK"][:2],
        "battery_old": centers["C_BATTERY_OLD_PICK"][:2],
        "used_battery_box": centers["C_USED_PLACE"][:2],
        "new_battery_box": centers["C_BATTERY_NEW_PICK"][:2],
        "battery_new": centers["C_BATTERY_NEW_PICK"][:2],
    }

    print("\n=== POSICIONES CALCULADAS ===")

    for name, xy in positions.items():
        print(
            f"{name:20s} "
            f"X={xy[0]:+.6f} "
            f"Y={xy[1]:+.6f}"
        )

    updated = set()

    for obstacle in ompl_root.findall("Obstacle"):
        kth_name = obstacle.find("KauthamName")
        home = obstacle.find("Home")

        if kth_name is None or home is None:
            continue

        name = kth_name.attrib.get("name")

        if name not in positions:
            continue

        xy = positions[name]

        old_x = home.attrib.get("X")
        old_y = home.attrib.get("Y")

        home.set("X", f"{xy[0]:.6f}")
        home.set("Y", f"{xy[1]:.6f}")

        print(
            f"OMPL {name:20s}: "
            f"({old_x}, {old_y}) -> "
            f"({xy[0]:+.6f}, {xy[1]:+.6f})"
        )

        updated.add(name)

    missing = set(positions) - updated

    if missing:
        raise RuntimeError(
            "No se encontraron obstáculos: "
            + ", ".join(sorted(missing))
        )

    try:
        ET.indent(ompl_tree, space="        ")
    except AttributeError:
        pass

    ompl_tree.write(
        ompl_path,
        encoding="utf-8",
        xml_declaration=True,
    )

    tamp_tree = ET.parse(tamp_path)
    tamp_root = tamp_tree.getroot()

    object_mapping = {
        "BOX_LID": "box_lid",
        "BATTERY_OLD": "battery_old",
        "BATTERY_NEW": "battery_new",
    }

    updated_objects = set()

    for obj in tamp_root.findall("./States/Initial/Object"):
        symbolic_name = obj.attrib.get("name")

        if symbolic_name not in object_mapping:
            continue

        obstacle_name = object_mapping[symbolic_name]
        xy = positions[obstacle_name]

        pose = [
            float(value)
            for value in (obj.text or "").split()
        ]

        if len(pose) != 7:
            raise RuntimeError(
                f"Pose inválida para {symbolic_name}: {pose}"
            )

        pose[0] = float(xy[0])
        pose[1] = float(xy[1])

        obj.text = " " + " ".join(
            f"{value:.6f}" for value in pose
        ) + " "

        updated_objects.add(symbolic_name)

    missing = set(object_mapping) - updated_objects

    if missing:
        raise RuntimeError(
            "No se actualizaron objetos: "
            + ", ".join(sorted(missing))
        )

    try:
        ET.indent(tamp_tree, space="    ")
    except AttributeError:
        pass

    tamp_tree.write(
        tamp_path,
        encoding="utf-8",
        xml_declaration=True,
    )

    print("\nOK: escena recalculada desde el CSV actual.")
    print("No se han usado posiciones antiguas.")
    print("No se han modificado alturas ni colisiones.")


if __name__ == "__main__":
    main()
