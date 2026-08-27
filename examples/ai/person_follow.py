"""Optional example: follow a detected person — turn to center them
left/right in frame, and walk toward them until they're at a comfortable
following distance — with a live annotated view so you can see what the
model sees while it's driving the robot. A 640px-wide window shows a
bounding box around every person YOLO finds (green for the one being
followed, the closest match to center; yellow for anyone else in frame),
a center line marking the yaw target, and the velocity command each frame
is actually sending.

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
MAX_VX = 0.4     # m/s forward cap
MAX_VYAW = 0.5   # rad/s turn cap

# There's no depth sensing here (plain monocular camera) — the person's
# bounding-box height relative to the frame is a rough stand-in for
# distance instead: small box = far away = walk forward, box at/above this
# ratio = "close enough" = stop advancing. Height (not width) on purpose:
# it stays comparatively stable even when someone's turned partway
# sideways, unlike width. Exact value is scene/lens dependent — adjust to
# taste for your camera and desired following distance.
TARGET_BOX_HEIGHT_RATIO = 0.4


def resize_to_display(frame):
    """Fixed 640px-wide frame, aspect ratio preserved — keeps the window a
    manageable size and, since this same resized frame is what YOLO runs
    detection on, keeps inference fast too (running it against the camera's
    full native resolution every frame would make the control loop noticeably
    laggier)."""
    height = int(frame.shape[0] * DISPLAY_WIDTH / frame.shape[1])
    return cv2.resize(frame, (DISPLAY_WIDTH, height))


def command_for(box, frame_width: int, frame_height: int):
    """(vx, vyaw) to center `box` horizontally and close to
    TARGET_BOX_HEIGHT_RATIO — pure function of the box + frame size so it's
    easy to unit test independent of the camera/model/robot."""
    x1, y1, x2, y2 = box.xyxy[0].tolist()

    yaw_error = ((x1 + x2) / 2 - frame_width / 2) / (frame_width / 2)
    vyaw = max(-MAX_VYAW, min(MAX_VYAW, -yaw_error * 0.6))

    distance_error = TARGET_BOX_HEIGHT_RATIO - (y2 - y1) / frame_height
    # Never auto-reverses if someone gets too close — just stops advancing.
    # Backing away automatically is a bigger surprise/safety concern than
    # just halting for a teaching example like this one.
    vx = max(0.0, min(MAX_VX, distance_error))

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
