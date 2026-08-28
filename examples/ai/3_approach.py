"""Step 3 of 4: walk toward the closest match to TARGET, building on the
same detect-and-filter idea as 2_count.py, now on a loop that also
drives the robot.

    1_see.py          look, and print everything found
    2_count.py        count just one kind of thing
    3_approach.py     <- you are here: walk toward the closest match
    4_custom_model.py same walk, with a model you trained/downloaded yourself

Each pass through the loop: take one snapshot, look for TARGET, and if
found, take one small step toward it — turning to keep it centered,
walking forward until it fills enough of the frame to count as "close".
Then repeat, until it's close enough to stop and declare arrival.

One photo per loop (rather than a continuous video stream) keeps this
readable at the cost of a little smoothness — the robot updates its
movement at whatever pace a snapshot + a YOLO pass take, not real video
framerate. That's a fine trade for a first example; a live video feed
producing smoother motion is a step up from here, not a beginner concern.

Needs OpenCV, NumPy, and Ultralytics — deliberately not core SDK
dependencies, so install with the "all" extra: pip install -e '.[all]'.
Start with the Go2 supported and keep the physical controller ready.

Usage:
    python3 examples/ai/3_approach.py [host]

    Stops on its own once it arrives; Ctrl+C to stop early.
"""
import sys
import time

import cv2
import numpy as np
from ultralytics import YOLO

from shepherd_sdk import Shepherd

TARGET = "chair"        # any class the model knows — see 2_count.py
FORWARD_SPEED = 0.3     # m/s, while approaching
TURN_SPEED = 1.0        # rad/s, at most, while centering on TARGET
CLOSE_ENOUGH = 0.5      # stop walking forward once TARGET's box fills
                        # this fraction of the frame's height


def box_area(box) -> float:
    x1, y1, x2, y2 = box.xyxy[0].tolist()
    return (x2 - x1) * (y2 - y1)


def main() -> None:
    robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()
    model = YOLO("yolo11n.pt")
    print(f"Looking for '{TARGET}'. Ctrl+C to stop.")

    try:
        while True:
            jpeg_bytes = robot.camera.snapshot("front")
            frame = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
            frame_height, frame_width = frame.shape[:2]

            result = model(frame, verbose=False)[0]
            matches = [box for box in result.boxes if result.names[int(box.cls[0])] == TARGET]

            if not matches:
                print("nothing found, standing by")
                robot.sport.stop()
                time.sleep(0.5)
                continue

            # No depth sensing here (plain monocular camera) — the
            # biggest box in frame is treated as the nearest match,
            # and that's the one to walk toward.
            target = max(matches, key=box_area)
            x1, y1, x2, y2 = target.xyxy[0].tolist()

            # -1 (target at the frame's left edge) .. 0 (centered) .. +1 (right edge)
            offset = ((x1 + x2) / 2 - frame_width / 2) / (frame_width / 2)
            vyaw = -offset * TURN_SPEED

            box_height_ratio = (y2 - y1) / frame_height  # 0 (small/far) .. 1 (fills the frame)
            if box_height_ratio >= CLOSE_ENOUGH:
                robot.sport.stop()
                print(f"Arrived at '{TARGET}' ({box_height_ratio:.0%} of frame height).")
                break

            print(f"target at {offset:+.2f}, {box_height_ratio:.0%} of frame height "
                  f"-> vx={FORWARD_SPEED:.2f} vyaw={vyaw:.2f}")
            robot.sport.move(FORWARD_SPEED, 0.0, vyaw)
            time.sleep(0.15)
    finally:
        robot.sport.stop()


if __name__ == "__main__":
    main()
