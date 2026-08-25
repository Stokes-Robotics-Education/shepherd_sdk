from shepherd_sdk import Shepherd


robot = Shepherd()
for state in robot.telemetry.stream():
    telemetry = state["telemetry"]
    print("battery:", telemetry.get("battery"), "position:", telemetry.get("position"))

