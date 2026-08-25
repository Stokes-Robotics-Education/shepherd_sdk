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
    TestOption(name="sit", id=9),
    TestOption(name="content", id=10),
    TestOption(name="dance1", id=11),
    TestOption(name="dance2", id=12),
    TestOption(name="move forward", id=13),
    TestOption(name="move lateral", id=14),
    TestOption(name="move rotate", id=15),
    TestOption(name="stop_move", id=16),
    TestOption(name="deadman check", id=17),
    TestOption(name="telemetry snapshot", id=18),
    TestOption(name="telemetry stream", id=19),
    TestOption(name="faults", id=20),
    TestOption(name="camera snapshot", id=21),
    TestOption(name="list_maps", id=22),
    TestOption(name="start_mapping", id=23),
    TestOption(name="end_mapping", id=24),
    TestOption(name="start_relocation", id=25),
    TestOption(name="record_waypoint", id=26),
    TestOption(name="list_waypoints", id=27),
    TestOption(name="goto_waypoint", id=28),
    TestOption(name="delete_waypoint", id=29),
    TestOption(name="pose_nav", id=30),
    TestOption(name="pause_nav", id=31),
    TestOption(name="resume_nav", id=32),
    TestOption(name="slam stop", id=33),
    TestOption(name="estop", id=34),
    TestOption(name="estop reset", id=35),
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

        name = test_option.name
        if name == "health":
            pprint(robot.health())
        elif name == "capabilities":
            pprint(robot.capabilities())
        elif name == "stand_up":
            pprint(robot.sport.stand_up())
        elif name == "stand_down":
            pprint(robot.sport.stand_down())
        elif name == "rise_sit":
            pprint(robot.sport.rise_sit())
        elif name == "balance_stand":
            pprint(robot.sport.balance_stand())
        elif name == "recovery_stand":
            pprint(robot.sport.recovery_stand())
        elif name == "hello":
            pprint(robot.sport.action("hello"))
        elif name == "stretch":
            pprint(robot.sport.action("stretch"))
        elif name == "sit":
            pprint(robot.sport.sit())
        elif name == "content":
            pprint(robot.sport.action("content"))
        elif name == "dance1":
            pprint(robot.sport.action("dance1"))
        elif name == "dance2":
            pprint(robot.sport.action("dance2"))
        elif name == "move forward":
            pprint(robot.sport.move(vx=0.3))
        elif name == "move lateral":
            pprint(robot.sport.move(vx=0, vy=0.3))
        elif name == "move rotate":
            pprint(robot.sport.move(vx=0, vy=0, vyaw=0.5))
        elif name == "stop_move":
            pprint(robot.sport.stop())
        elif name == "deadman check":
            print("Sending one move() and then doing nothing for 2s.")
            print("Robot should stop on its own within ~500ms (shep's dead-man timeout).")
            pprint(robot.sport.move(vx=0.2))
            time.sleep(2)
            print("Check the robot now — it should already be stopped.")
        elif name == "telemetry snapshot":
            pprint(robot.telemetry.get())
        elif name == "telemetry stream":
            print("Streaming telemetry for 5 updates (Ctrl+C to stop early)...")
            count = 0
            for state in robot.telemetry.stream():
                telemetry = state["telemetry"]
                print("battery:", telemetry.get("battery"), "position:", telemetry.get("position"))
                count += 1
                if count >= 5:
                    break
        elif name == "faults":
            faults = robot.telemetry.get().get("telemetry", {}).get("faults", [])
            print("No active faults." if not faults else faults)
        elif name == "camera snapshot":
            path = robot.camera.save_snapshot("snapshot.jpg")
            print("Saved", path)
        elif name == "list_maps":
            pprint(robot.slam.list_maps())
        elif name == "start_mapping":
            pprint(robot.slam.start_mapping())
        elif name == "end_mapping":
            maps = robot.slam.list_maps()
            print("Slots:", ", ".join("%s%s" % (s, " (used)" if maps["used"].get(s) else "") for s in maps["slots"]))
            slot = input("Save to slot: ").strip()
            pprint(robot.slam.end_mapping(name=slot))
        elif name == "start_relocation":
            maps = robot.slam.list_maps()
            print("Slots:", ", ".join("%s%s" % (s, " (used)" if maps["used"].get(s) else "") for s in maps["slots"]))
            slot = input("Relocate against slot: ").strip()
            pprint(robot.slam.start_relocation(name=slot))
        elif name == "record_waypoint":
            wp_name = input("Waypoint name: ").strip()
            pprint(robot.slam.record_waypoint(wp_name))
        elif name == "list_waypoints":
            pprint(robot.slam.list_waypoints())
        elif name == "goto_waypoint":
            wp_name = input("Waypoint name: ").strip()
            pprint(robot.slam.goto_waypoint(wp_name))
        elif name == "delete_waypoint":
            wp_name = input("Waypoint name: ").strip()
            pprint(robot.slam.delete_waypoint(wp_name))
        elif name == "pose_nav":
            x = float(input("Target x: ") or 0)
            y = float(input("Target y: ") or 0)
            pprint(robot.slam.pose_nav(x=x, y=y))
        elif name == "pause_nav":
            pprint(robot.slam.pause_nav())
        elif name == "resume_nav":
            pprint(robot.slam.resume_nav())
        elif name == "slam stop":
            pprint(robot.slam.stop())
        elif name == "estop":
            pprint(robot.emergency_stop())
            print("E-stop is latched. Use 'estop reset' before further motion/posture commands.")
        elif name == "estop reset":
            pprint(robot.reset_emergency_stop())

        time.sleep(1)
