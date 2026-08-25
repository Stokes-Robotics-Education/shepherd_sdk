import sys

from shepherd_sdk import Shepherd


robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()
for state in robot.telemetry.stream():
    telemetry = state["telemetry"]
    print("battery:", telemetry.get("battery"), "position:", telemetry.get("position"))

