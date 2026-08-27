"""Relocalize against a saved map, then send one autonomous nav goal.

Requires the unitree_slam module's own server process already running, and
a map already saved via mapping.py (or the physical UI). pose_nav is a
fire-and-forget goal driven by Unitree's own planner — not a per-tick
velocity command, so it isn't subject to shep's dead-man timeout. This
polls telemetry for arrival instead of the sport.move()/refresh pattern.

Usage:
    python3 examples/slam/navigate.py [host] [map_slot] [x] [y]

    map_slot is one of the 10 fixed save slots (robot.slam.list_maps()
    ["slots"], e.g. "map1"), the same one used with mapping.py.
"""
import sys
import time

from shepherd_sdk import Shepherd


def main() -> None:
    slot = sys.argv[2] if len(sys.argv) > 2 else "map1"
    x = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    y = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()

    print("WARNING: ensure the robot is at the map's recorded origin pose before relocating.")
    input("Press Enter to relocalize...")
    print(robot.slam.start_relocation(name=slot))

    input(f"Press Enter to send the robot to (x={x}, y={y})...")
    print(robot.slam.pose_nav(x=x, y=y))

    print("Waiting for arrival (Ctrl+C to give up watching, task keeps running)...")
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        state = robot.telemetry.get()
        result = state.get("telemetry", {}).get("slam", {}).get("task_result")
        if result:
            print(result)
            if result.get("is_arrived"):
                print("Arrived.")
                return
        time.sleep(1)
    print("Timed out waiting for arrival; task may still be in progress.")


if __name__ == "__main__":
    main()
