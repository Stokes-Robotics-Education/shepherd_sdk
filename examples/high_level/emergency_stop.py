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


robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()
print(robot.emergency_stop())
print("E-stop remains latched. Reset it from the dashboard after checking the robot.")

