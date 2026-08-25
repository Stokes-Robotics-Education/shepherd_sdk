"""Build and save a map with Unitree's built-in SLAM.

Requires the unitree_slam module's own server process already running on
the robot (not started by shep/shepherd_sdk) — see shep's README. Drive the
robot around (physical controller or shepherd_sdk.sport.move) between start
and end; this script only brackets the mapping session.

Usage:
    .venv/bin/python examples/slam/mapping.py [host] [save_path]
"""
import sys

from shepherd_sdk import Shepherd


def main() -> None:
    save_path = sys.argv[2] if len(sys.argv) > 2 else "/home/unitree/map.pcd"
    robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()

    print("WARNING: drive the robot through the area to be mapped between start and end.")
    input("Press Enter to start mapping...")
    print(robot.slam.start_mapping())

    input("Drive the robot around now. Press Enter here when done to save the map...")
    print(robot.slam.end_mapping(save_path))
    print("Map saved to", save_path)


if __name__ == "__main__":
    main()
