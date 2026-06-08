#!/usr/bin/env python3
"""
parse_taskfile.py
=================
Converts a TAMP taskfile XML (output of Kautham / tamp_helper) into a sequence
of UR3e joint-space waypoints + gripper commands suitable for execution on the
real UR3e robot.

Usage
-----
    python3 parse_taskfile.py taskfile.xml [--dry-run]

    --dry-run  Print the command sequence without connecting to the robot.

Output
------
Prints (and optionally executes) a sequence of:
    MOVE   [j1, j2, j3, j4, j5, j6]   # joints in radians
    CLOSE_GRIPPER                       # at transit→transfer transitions (pick)
    OPEN_GRIPPER                        # at transfer→transit transitions (place)

Notes
-----
* Only the first 6 values of each waypoint are used (UR3e joints).
  The 7th value (gripper, index 6) is DISCARDED here because gripper state is
  inferred from the motion-type transition instead (more reliable).
* Normalization formulas (from assignment PDF):
    Joints 1, 2, 4, 5, 6:  q_rad = q_norm * 4π  − 2π
    Joint 3 (elbow):        q_rad = q_norm * 2π  − π
* A transit→transfer transition means a pick (close gripper).
* A transfer→transit transition means a place (open gripper).
* The sequence always starts and ends with a MOVE, never with a gripper command.

Dependencies (real-robot execution)
------------------------------------
    pip install ur-rtde
    # or: pip install urx  (legacy)
"""

import argparse
import math
import sys
import xml.etree.ElementTree as ET
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PI = math.pi
NUM_UR3_JOINTS = 6          # discard anything beyond index 5

# Normalization indices (0-based)
ELBOW_JOINT_IDX = 2         # joint 3 in 1-based = index 2 in 0-based

# Default speed / acceleration for real-robot motion (in rad/s, rad/s²)
DEFAULT_SPEED = 0.3         # TODO: tune for your setup
DEFAULT_ACCEL = 0.5         # TODO: tune for your setup
DEFAULT_BLEND  = 0.0        # blending radius (0 = precise stop)


# ---------------------------------------------------------------------------
# Normalised → radians conversion
# ---------------------------------------------------------------------------
def norm_to_rad(q_norm: float, joint_idx: int) -> float:
    """
    Convert a normalised Kautham control value [0, 1] to radians.

    Joints 1, 2, 4, 5, 6  (0-based: 0, 1, 3, 4, 5):
        q_rad = q_norm * 4π − 2π
    Joint 3 / elbow (0-based: 2):
        q_rad = q_norm * 2π − π
    """
    if joint_idx == ELBOW_JOINT_IDX:
        return q_norm * 2.0 * PI - PI
    else:
        return q_norm * 4.0 * PI - 2.0 * PI


def parse_controls(raw: str) -> List[float]:
    """
    Parse a space-separated control string from the taskfile.
    Returns only the first NUM_UR3_JOINTS values (gripper value is discarded).
    Converts normalised values to radians.
    """
    values = [float(v) for v in raw.strip().split()]
    if len(values) < NUM_UR3_JOINTS:
        raise ValueError(
            f"Expected at least {NUM_UR3_JOINTS} control values, got {len(values)}: {raw}"
        )
    # Discard gripper (index 6+) and convert joints to radians
    joints_rad = [
        norm_to_rad(values[i], i)
        for i in range(NUM_UR3_JOINTS)
    ]
    return joints_rad


# ---------------------------------------------------------------------------
# Taskfile parser
# ---------------------------------------------------------------------------
def parse_taskfile(xml_path: str) -> List[Tuple[str, object]]:
    """
    Parse the TAMP taskfile XML and return an ordered list of commands.

    Each command is a tuple:
        ('MOVE',          [j1, j2, j3, j4, j5, j6])   # radians
        ('CLOSE_GRIPPER', None)
        ('OPEN_GRIPPER',  None)

    Gripper commands are INSERTED at motion-type transitions:
        transit → transfer  =>  CLOSE after the last transit waypoint
        transfer → transit  =>  OPEN  after the last transfer waypoint
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    commands: List[Tuple[str, object]] = []

    # The taskfile is a sequence of <Step> or <Waypoint> elements.
    # Each element has a motion type ("transit" or "transfer") and a Controls
    # value.  Adapt the XPath below if your Kautham version uses different tags.
    #
    # TODO: Inspect your actual taskfile XML and adjust the element names.
    # Common alternatives:
    #   <Step type="transit">  <Controls>...</Controls>  </Step>
    #   <Waypoint mode="transfer"><q>...</q></Waypoint>
    #   <Config motionType="transit" controls="..."/>

    # ── Try generic approach: look for elements with a type/mode attribute ──
    waypoints = (
        root.findall('.//Step')
        or root.findall('.//Waypoint')
        or root.findall('.//Config')
        or root.findall('.//waypoint')
        or list(root.iter())   # fallback: all elements
    )

    prev_motion_type = None

    for elem in waypoints:
        # Determine motion type
        motion_type = (
            elem.get('type')
            or elem.get('mode')
            or elem.get('motionType')
            or elem.get('motion_type')
        )
        if motion_type is None:
            # Try child element
            mt_elem = elem.find('Type') or elem.find('MotionType') or elem.find('mode')
            if mt_elem is not None:
                motion_type = mt_elem.text.strip() if mt_elem.text else None

        if motion_type is None:
            continue   # element has no motion type; skip

        motion_type = motion_type.lower()
        if motion_type not in ('transit', 'transfer'):
            continue

        # Extract controls
        controls_raw = elem.get('controls') or elem.get('Controls')
        if controls_raw is None:
            ctrl_elem = elem.find('Controls') or elem.find('controls') or elem.find('q')
            if ctrl_elem is not None and ctrl_elem.text:
                controls_raw = ctrl_elem.text
        if controls_raw is None:
            continue

        joints = parse_controls(controls_raw)

        # ── Detect motion-type transition and insert gripper command ─────────
        if prev_motion_type is not None and motion_type != prev_motion_type:
            if prev_motion_type == 'transit' and motion_type == 'transfer':
                # Arriving at grasp pose → close gripper (pick)
                commands.append(('CLOSE_GRIPPER', None))
            elif prev_motion_type == 'transfer' and motion_type == 'transit':
                # Leaving a carry pose → open gripper (place)
                commands.append(('OPEN_GRIPPER', None))

        commands.append(('MOVE', joints))
        prev_motion_type = motion_type

    # Ensure the sequence doesn't end on a gripper command (it won't since we
    # append MOVE last), but add a safety check anyway.
    if commands and commands[-1][0] != 'MOVE':
        commands.append(('MOVE', commands[-2][1]))   # repeat last joint pose

    return commands


# ---------------------------------------------------------------------------
# Dry-run printer
# ---------------------------------------------------------------------------
def print_commands(commands: List[Tuple[str, object]]) -> None:
    print("\n=== UR3e Command Sequence ===")
    print(f"  Total steps: {len(commands)}\n")
    for i, (cmd, data) in enumerate(commands):
        if cmd == 'MOVE':
            formatted = "[" + ", ".join(f"{v:+.4f}" for v in data) + "]"
            print(f"  {i+1:3d}. MOVE           {formatted}  (rad)")
        elif cmd == 'CLOSE_GRIPPER':
            print(f"  {i+1:3d}. CLOSE_GRIPPER  ← pick transition")
        elif cmd == 'OPEN_GRIPPER':
            print(f"  {i+1:3d}. OPEN_GRIPPER   ← place transition")
    print("\n=== End of Sequence ===\n")


# ---------------------------------------------------------------------------
# Real-robot execution via ur_rtde
# ---------------------------------------------------------------------------
def execute_on_robot(commands: List[Tuple[str, object]], robot_ip: str) -> None:
    """
    Execute the command sequence on the real UR3e using ur_rtde.

    Prerequisites:
        pip install ur-rtde
        Robot must be in Remote Control mode (polyscope ≥ 5.x)

    TODO: Adjust DEFAULT_SPEED, DEFAULT_ACCEL, DEFAULT_BLEND for your task.
    TODO: Adjust gripper_close_pos and gripper_open_pos for your object sizes.
    """
    try:
        import rtde_control  # type: ignore
        import rtde_io       # type: ignore
    except ImportError:
        print("[ERROR] ur_rtde not installed.  Run: pip install ur-rtde", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Connecting to UR3e at {robot_ip} ...")
    rtde_c = rtde_control.RTDEControlInterface(robot_ip)
    rtde_io_interface = rtde_io.RTDEIOInterface(robot_ip)

    # TODO: Replace with your actual gripper control method.
    # Options:
    #   A. Digital I/O:  rtde_io_interface.setStandardDigitalOut(0, True/False)
    #   B. Robotiq ROS2 driver topic:  publish to /gripper_cmd
    #   C. Script via rtde_c.sendCustomScriptCommand(...)
    def close_gripper():
        print("  [GRIPPER] Close")
        # TODO: rtde_io_interface.setStandardDigitalOut(0, True)

    def open_gripper():
        print("  [GRIPPER] Open")
        # TODO: rtde_io_interface.setStandardDigitalOut(0, False)

    print("[INFO] Starting execution ...\n")

    for i, (cmd, data) in enumerate(commands):
        print(f"  Step {i+1}/{len(commands)}: {cmd}", end="")
        if cmd == 'MOVE':
            print(f"  {data}")
            rtde_c.moveJ(data, DEFAULT_SPEED, DEFAULT_ACCEL)
        elif cmd == 'CLOSE_GRIPPER':
            print()
            close_gripper()
            import time; time.sleep(0.5)   # TODO: adjust wait for gripper
        elif cmd == 'OPEN_GRIPPER':
            print()
            open_gripper()
            import time; time.sleep(0.5)   # TODO: adjust wait for gripper

    print("\n[INFO] Task complete.  Robot stopped.")
    rtde_c.stopScript()


# ---------------------------------------------------------------------------
# Utility: inverse of norm_to_rad (for debugging / generating test inputs)
# ---------------------------------------------------------------------------
def rad_to_norm(q_rad: float, joint_idx: int) -> float:
    """Inverse of norm_to_rad.  Useful when manually computing control values."""
    if joint_idx == ELBOW_JOINT_IDX:
        return (q_rad + PI) / (2.0 * PI)
    else:
        return (q_rad + 2.0 * PI) / (4.0 * PI)


def print_norm_table(joints_rad: List[float]) -> None:
    """Print a joint-by-joint normalisation table for debugging."""
    print("\nJoint normalization table:")
    print(f"  {'Joint':>6}  {'q_rad':>8}  {'q_norm':>8}  {'q_deg':>8}")
    print(f"  {'-'*6}  {'-'*8}  {'-'*8}  {'-'*8}")
    for idx, q_rad in enumerate(joints_rad):
        q_norm = rad_to_norm(q_rad, idx)
        q_deg = math.degrees(q_rad)
        print(f"  {idx+1:>6}  {q_rad:>+8.4f}  {q_norm:>8.4f}  {q_deg:>+8.2f}°")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Convert Kautham TAMP taskfile to UR3e joint trajectory + gripper commands."
    )
    parser.add_argument(
        "taskfile",
        help="Path to the taskfile XML generated by Kautham TAMP."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the command sequence without connecting to the robot."
    )
    parser.add_argument(
        "--robot-ip",
        default="192.168.1.100",   # TODO: replace with your UR3e IP address
        help="IP address of the real UR3e (default: 192.168.1.100)."
    )
    args = parser.parse_args()

    print(f"[INFO] Parsing taskfile: {args.taskfile}")
    commands = parse_taskfile(args.taskfile)

    if not commands:
        print("[WARNING] No commands extracted.  Check the taskfile XML structure.")
        print("          Inspect the file and update the XPath queries in parse_taskfile().")
        sys.exit(1)

    print_commands(commands)

    if args.dry_run:
        print("[DRY RUN] Not connecting to robot.")
    else:
        execute_on_robot(commands, args.robot_ip)


if __name__ == "__main__":
    main()
