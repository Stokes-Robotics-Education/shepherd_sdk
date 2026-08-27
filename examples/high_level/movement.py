import sys
from pathlib import Path
import time

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


robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()
print("WARNING: clear the area around the robot before continuing.")
input("Press Enter to stand and walk briefly...")

try:
    robot.sport.stand_up()
    time.sleep(4)  # Go2 may not accept movement immediately after standing.
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        robot.sport.move(vx=0.2)
        time.sleep(0.2)  # Refreshes the server's dead-man watchdog.
finally:
    robot.sport.stop()

