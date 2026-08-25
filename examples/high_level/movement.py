import sys
import time

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

