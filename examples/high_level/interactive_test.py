"""Interactive test menu for shepherd_sdk, styled after Unitree's
go2_sport_client.py example (same pick-a-number-and-go workflow), but
driving the robot through Shep's HTTP/WebSocket API instead of raw DDS.

Usage:
    .venv/bin/python examples/high_level/interactive_test.py [host]

    host defaults to shep.local (or $SHEP_HOST if set). Pass an IP or
    hostname to override, e.g.:
    .venv/bin/python examples/high_level/interactive_test.py 192.168.4.74
"""

import sys
import time
from dataclasses import dataclass
from pprint import pprint

from shepherd_sdk import Shepherd


@dataclass
class TestOption:
    name: str
    id: int


option_list = [
    TestOption(name="health", id=0),
    TestOption(name="capabilities", id=1),
    TestOption(name="stand_up", id=2),
    TestOption(name="stand_down", id=3),
    TestOption(name="rise_sit", id=4),
    TestOption(name="balance_stand", id=5),
    TestOption(name="recovery_stand", id=6),
    TestOption(name="hello", id=7),
    TestOption(name="stretch", id=8),
    TestOption(name="move forward", id=9),
    TestOption(name="move lateral", id=10),
    TestOption(name="move rotate", id=11),
    TestOption(name="stop_move", id=12),
    TestOption(name="deadman check", id=13),
    TestOption(name="telemetry snapshot", id=14),
    TestOption(name="telemetry stream", id=15),
    TestOption(name="camera snapshot", id=16),
    TestOption(name="estop", id=17),
    TestOption(name="estop reset", id=18),
]


class UserInterface:
    def __init__(self):
        self.test_option_ = None

    def convert_to_int(self, input_str):
        try:
            return int(input_str)
        except ValueError:
            return None

    def terminal_handle(self):
        input_str = input("Enter id or name ('list' to show options): \n")

        if input_str == "list":
            self.test_option_.name = None
            self.test_option_.id = None
            for option in option_list:
                print(f"{option.name}, id: {option.id}")
            return

        for option in option_list:
            if input_str == option.name or self.convert_to_int(input_str) == option.id:
                self.test_option_.name = option.name
                self.test_option_.id = option.id
                print(f"Test: {self.test_option_.name}, test_id: {self.test_option_.id}")
                return

        print("No matching test option found.")


if __name__ == "__main__":
    print("WARNING: Please ensure there are no obstacles around the robot while running this example.")
    input("Press Enter to continue...")

    robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()

    test_option = TestOption(name=None, id=None)
    user_interface = UserInterface()
    user_interface.test_option_ = test_option

    while True:
        user_interface.terminal_handle()
        print(f"Updated Test Option: Name = {test_option.name}, ID = {test_option.id}\n")

        if test_option.id == 0:
            pprint(robot.health())
        elif test_option.id == 1:
            pprint(robot.capabilities())
        elif test_option.id == 2:
            pprint(robot.sport.stand_up())
        elif test_option.id == 3:
            pprint(robot.sport.stand_down())
        elif test_option.id == 4:
            pprint(robot.sport.rise_sit())
        elif test_option.id == 5:
            pprint(robot.sport.balance_stand())
        elif test_option.id == 6:
            pprint(robot.sport.recovery_stand())
        elif test_option.id == 7:
            pprint(robot.sport.action("hello"))
        elif test_option.id == 8:
            pprint(robot.sport.action("stretch"))
        elif test_option.id == 9:
            pprint(robot.sport.move(vx=0.3))
        elif test_option.id == 10:
            pprint(robot.sport.move(vx=0, vy=0.3))
        elif test_option.id == 11:
            pprint(robot.sport.move(vx=0, vy=0, vyaw=0.5))
        elif test_option.id == 12:
            pprint(robot.sport.stop())
        elif test_option.id == 13:
            print("Sending one move() and then doing nothing for 2s.")
            print("Robot should stop on its own within ~500ms (shep's dead-man timeout).")
            pprint(robot.sport.move(vx=0.2))
            time.sleep(2)
            print("Check the robot now — it should already be stopped.")
        elif test_option.id == 14:
            pprint(robot.telemetry.get())
        elif test_option.id == 15:
            print("Streaming telemetry for 5 updates (Ctrl+C to stop early)...")
            count = 0
            for state in robot.telemetry.stream():
                telemetry = state["telemetry"]
                print("battery:", telemetry.get("battery"), "position:", telemetry.get("position"))
                count += 1
                if count >= 5:
                    break
        elif test_option.id == 16:
            path = robot.camera.save_snapshot("snapshot.jpg")
            print("Saved", path)
        elif test_option.id == 17:
            pprint(robot.emergency_stop())
            print("E-stop is latched. Use 'estop reset' before further motion/posture commands.")
        elif test_option.id == 18:
            pprint(robot.reset_emergency_stop())

        time.sleep(1)
