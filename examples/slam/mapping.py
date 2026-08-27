"""Build and save a map with Unitree's built-in SLAM.

Requires the unitree_slam module's own server process already running on
the robot (not started by shep/shepherd_sdk) — see shep's README. Drive the
robot around (physical controller or shepherd_sdk.sport.move) between start
and end; this script only brackets the mapping session.

Usage:
    python3 examples/slam/mapping.py [host] [map_slot]

    map_slot is one of the 10 fixed save slots (robot.slam.list_maps()
    ["slots"], e.g. "map1"), not a freeform path — shep resolves the
    actual file location. Defaults to "map1".
"""
import sys
from pathlib import Path

try:
    import shepherd_sdk  # noqa: F401 -- just checking it's importable
except ImportError:
    import os
    for _parent in Path(__file__).resolve().parents:
        _venv_python = _parent / ".venv" / "bin" / "python3"
        if _venv_python.exists():
            os.execv(str(_venv_python), [str(_venv_python), *sys.argv])
    raise  # no .venv/ found either -- let the real error surface below

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
