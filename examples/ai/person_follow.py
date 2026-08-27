"""Optional example: track and follow a detected person using yaw only,
with a live annotated view so you can see what the model sees while it's
driving the robot — a 640px-wide window with a bounding box drawn around
every person YOLO finds (green for the one being followed, the closest
match to center; yellow for anyone else in frame).

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


def resize_to_display(frame):
    """Fixed 640px-wide frame, aspect ratio preserved — keeps the window a
    manageable size and, since this same resized frame is what YOLO runs
    detection on, keeps inference fast too (running it against the camera's
    full native resolution every frame would make the control loop noticeably
    laggier)."""
    height = int(frame.shape[0] * DISPLAY_WIDTH / frame.shape[1])
    return cv2.resize(frame, (DISPLAY_WIDTH, height))


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

            people = [box for box in model(frame, verbose=False)[0].boxes if int(box.cls[0]) == 0]
            for i, box in enumerate(people):
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
                color = (0, 255, 0) if i == 0 else (0, 200, 255)  # target vs. other people
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame, f"person {float(box.conf[0]):.2f}", (x1, max(0, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
                )

            cv2.imshow("person_follow", frame)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC
                break

            if not people:
                robot.sport.stop()
                continue
            x1, _, x2, _ = people[0].xyxy[0].tolist()
            error = ((x1 + x2) / 2 - frame.shape[1] / 2) / (frame.shape[1] / 2)
            robot.sport.move(0.0, 0.0, max(-0.5, min(0.5, -error * 0.6)))
            time.sleep(0.15)
    finally:
        robot.sport.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
