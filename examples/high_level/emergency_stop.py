import sys

from shepherd_sdk import Shepherd


robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()
print(robot.emergency_stop())
print("E-stop remains latched. Reset it from the dashboard after checking the robot.")

