from shepherd_sdk import Shepherd


robot = Shepherd()
print(robot.emergency_stop())
print("E-stop remains latched. Reset it from the dashboard after checking the robot.")

