"""Build a route from already-recorded waypoints, optionally save it for
reuse, then run it and watch progress. Requires waypoints already recorded
against the target map (record_waypoint via interactive_test.py, or your
own script) and the SLAM service running.

Usage:
    .venv/bin/python examples/slam/route_planner.py [host] [map_slot]

    map_slot is one of the 10 fixed save slots — the same one your
    waypoints were recorded against. Defaults to "map1".
"""
import sys
import time

from shepherd_sdk import Shepherd


def build_queue(robot: Shepherd, available: list) -> None:
    print("Add stops one at a time (blank name to finish).")
    while True:
        name = input("Waypoint name: ").strip()
        if not name:
            return
        if name not in available:
            print("Unknown waypoint for this map, try again.")
            continue
        wait_raw = input("  Wait here, in seconds (blank for 0): ").strip()
        action = input("  Action on arrival (blank for none): ").strip() or None
        wait_s = float(wait_raw) if wait_raw else None
        queue = robot.route.add_stop(name, wait_s=wait_s, action=action)
        print("  Queue now:", queue)


def watch_progress(robot: Shepherd) -> None:
    print("Watching progress (Ctrl+C to stop watching — the route keeps running)...")
    try:
        while True:
            status = robot.route.status()
            total = len(status["queue"])
            print(f"  [{status['index'] + 1}/{total}] {status['log']}")
            if not status["running"]:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def main() -> None:
    slot = sys.argv[2] if len(sys.argv) > 2 else "map1"
    robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()

    waypoints = robot.slam.list_waypoints()
    available = [name for name, wp in waypoints.items() if wp.get("map") == slot]
    if not available:
        print(f"No waypoints recorded for {slot} yet — record some first.")
        return
    print("Waypoints for", slot, ":", ", ".join(available))

    robot.route.set_relocate_map(slot)
    robot.route.clear()
    build_queue(robot, available)

    if not robot.route.status()["queue"]:
        print("No stops added, nothing to run.")
        return

    save_name = input("Save this route for reuse? (name, blank to skip): ").strip()
    if save_name:
        print(robot.route.save(save_name))

    input("Press Enter to run the route now...")
    print(robot.route.run())
    watch_progress(robot)


if __name__ == "__main__":
    main()
