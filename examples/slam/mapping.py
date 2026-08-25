"""Build and save a map with Unitree's built-in SLAM.

Requires the unitree_slam module's own server process already running on
the robot (not started by shep/shepherd_sdk) — see shep's README. Drive the
robot around (physical controller or shepherd_sdk.sport.move) between start
and end; this script only brackets the mapping session.

Usage:
    .venv/bin/python examples/slam/mapping.py [host] [map_slot]

    map_slot is one of the 10 fixed save slots (robot.slam.list_maps()
    ["slots"], e.g. "map1"), not a freeform path — shep resolves the
    actual file location. Defaults to "map1".
"""
import sys

from shepherd_sdk import Shepherd


def main() -> None:
    slot = sys.argv[2] if len(sys.argv) > 2 else "map1"
    robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()

    maps = robot.slam.list_maps()
    print("Slots:", ", ".join("%s%s" % (s, " (used)" if maps["used"].get(s) else "") for s in maps["slots"]))

    print("WARNING: drive the robot through the area to be mapped between start and end.")
    input("Press Enter to start mapping...")
    print(robot.slam.start_mapping())

    input("Drive the robot around now. Press Enter here when done to save the map...")
    result = robot.slam.end_mapping(name=slot)
    print(result)
    print("Map saved to slot", slot)


if __name__ == "__main__":
    main()
