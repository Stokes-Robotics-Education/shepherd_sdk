"""Read Unitree's Fault Services diagnostic feed from telemetry.

telemetry["faults"] is a list of {timestamp, source, code} — empty when
nothing's wrong. source ranges, per
https://support.unitree.com/home/en/developer/Fault_service:
100-200 bottom comm (MCU/motor/battery/fan), 300+ motors, 400 radar,
500 UWB. code is a bitmask within its source; this example prints raw
values rather than decoding individual bits.

Usage:
    python3 examples/telemetry/faults.py [host]
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

SOURCE_RANGES = (
    (100, 200, "bottom_comm"),
    (300, 400, "motors"),
    (400, 500, "radar"),
    (500, 600, "uwb"),
)


def describe_source(source: int) -> str:
    for low, high, name in SOURCE_RANGES:
        if low <= source < high:
            return name
    return "unknown"


def main() -> None:
    robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()
    state = robot.telemetry.get()
    faults = state.get("telemetry", {}).get("faults", [])

    if not faults:
        print("No active faults.")
        return

    for fault in faults:
        source = fault.get("source")
        print(f"[{fault.get('timestamp')}] source={source} ({describe_source(source)}) code={fault.get('code')}")


if __name__ == "__main__":
    main()
