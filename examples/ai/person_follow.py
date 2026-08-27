"""Optional example: follow a detected person using plain high-level
motion — walk toward them, slowing smoothly as they get close, while
turning to keep them centered left/right in frame — with a live annotated
view so you can see what the model sees while it's driving the robot. A
640px-wide window shows a bounding box around every person YOLO finds
(green for the one being followed, the closest match to center; yellow
for anyone else in frame), a center line marking the yaw target, and the
velocity command each frame is actually sending.

Needs OpenCV, NumPy, and Ultralytics — deliberately not core SDK dependencies,
so install with the "all" extra: pip install -e '.[all]'. Start with the Go2
supported and keep the physical controller ready.

Usage:
    python3 examples/ai/person_follow.py [host]

    Press ESC to quit.
"""
import sys
import time
from urllib.request import urlopen

import cv2
import numpy as np
from ultralytics import YOLO

from shepherd_sdk import Shepherd

DISPLAY_WIDTH = 640
FORWARD_VX = 0.5   # m/s — the *peak* forward speed, not a fixed constant one
MAX_VYAW = 3.0     # rad/s — same idea, the peak turn rate. shep's own
                   # server-side max_vyaw (1.5 rad/s by default) is the
                   # real final ceiling on what the robot actually does;
                   # this is just the request.

# There's no depth sensing here (plain monocular camera), so this is a
# relative stand-in for distance, not a real one: the person's bounding-box
# height relative to the frame. A fixed speed all the way up to a hard stop
# would mean walking at full FORWARD_VX right up until the cutoff, then an
# abrupt halt — this instead tapers vx linearly from FORWARD_VX down to 0
# as box_height_ratio climbs from 0 (as far away as it gets) to this value
# (close enough to stop advancing), so it actually slows down on approach.
STOP_BOX_HEIGHT_RATIO = 0.6


def resize_to_display(frame):
    """Fixed 640px-wide frame, aspect ratio preserved — keeps the window a
    manageable size and, since this same resized frame is what YOLO runs
    detection on, keeps inference fast too (running it against the camera's
    full native resolution every frame would make the control loop noticeably
    laggier)."""
    height = int(frame.shape[0] * DISPLAY_WIDTH / frame.shape[1])
    return cv2.resize(frame, (DISPLAY_WIDTH, height))


def command_for(box, frame_width: int, frame_height: int):
    """(vx, vyaw) from plain high-level motion, both proportional (relative
    to how far off-target the box is) rather than fixed constants — walk
    toward `box`, slowing as it gets close, while turning to keep it
    centered left/right: the goal is simply the box's horizontal center
    (not the box's vertical position, not the frame's exact center *point*
    — just left/right) landing on the frame's horizontal center. Pure
    function of the box + frame size so it's easy to unit test independent
    of the camera/model/robot."""
    x1, y1, x2, y2 = box.xyxy[0].tolist()

    yaw_error = ((x1 + x2) / 2 - frame_width / 2) / (frame_width / 2)  # -1..1
    vyaw = max(-MAX_VYAW, min(MAX_VYAW, -yaw_error * MAX_VYAW))

    box_height_ratio = (y2 - y1) / frame_height  # 0 (far) .. 1 (fills the frame)
    approach_headroom = max(0.0, 1.0 - box_height_ratio / STOP_BOX_HEIGHT_RATIO)  # 1 (far) .. 0 (at the stop distance)
    vx = FORWARD_VX * approach_headroom

    return vx, vyaw


def main() -> None:
    robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()
    model = YOLO("yolo11n.pt")
    stream = urlopen(robot.camera.stream_url("front"))
    buffer = b""
    print("Press ESC to quit.")

    try:
        while True:
            buffer += stream.read(4096)
            start = buffer.find(b"\xff\xd8")
            end = buffer.find(b"\xff\xd9", start + 2)
            if start < 0 or end < 0:
                continue
            frame = cv2.imdecode(np.frombuffer(buffer[start:end + 2], np.uint8), cv2.IMREAD_COLOR)
            buffer = buffer[end + 2:]
            if frame is None:
                continue
            frame = resize_to_display(frame)
            frame_height, frame_width = frame.shape[:2]

            people = [box for box in model(frame, verbose=False)[0].boxes if int(box.cls[0]) == 0]
            for i, box in enumerate(people):
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
                color = (0, 255, 0) if i == 0 else (0, 200, 255)  # target vs. other people
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame, f"person {float(box.conf[0]):.2f}", (x1, max(0, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
                )
            # Yaw target: turn until the followed person's box straddles this line.
            cv2.line(frame, (frame_width // 2, 0), (frame_width // 2, frame_height), (255, 255, 255), 1)

            if people:
                vx, vyaw = command_for(people[0], frame_width, frame_height)
            else:
                vx, vyaw = 0.0, 0.0
            cv2.putText(
                frame, f"vx={vx:.2f} vyaw={vyaw:.2f}", (8, frame_height - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
            )

            cv2.imshow("person_follow", frame)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC
                break

            if not people:
                robot.sport.stop()
                continue
            robot.sport.move(vx, 0.0, vyaw)
            time.sleep(0.15)
    finally:
        robot.sport.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
