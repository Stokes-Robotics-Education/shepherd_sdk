"""Check, start, or stop the SLAM service (the mid360_driver + unitree_slam
OS processes that Unitree's SLAM RPCs actually depend on). Starting/stopping
needs root on the robot side, so shep may ask for a sudo password — this
handles that handshake with getpass rather than a hardcoded password.

Usage:
    python3 examples/slam/service.py [host] [status|start|stop]

    Defaults to "status". host defaults to shep.local (or $SHEP_HOST if set).
"""
import sys
from pathlib import Path
from getpass import getpass

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


def start_or_stop(robot: Shepherd, action: str) -> None:
    call = robot.slam.start_service if action == "start" else robot.slam.stop_service
    result = call()
    if result.get("needs_password"):
        password = getpass((result.get("msg") or "Password required") + ": ")
        result = call(password=password)
    print(result)


def main() -> None:
    robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()
    action = sys.argv[2] if len(sys.argv) > 2 else "status"

    if action == "status":
        print(robot.slam.service_status())
    elif action in ("start", "stop"):
        start_or_stop(robot, action)
    else:
        print("Unknown action %r — use status, start, or stop." % action)


if __name__ == "__main__":
    main()
