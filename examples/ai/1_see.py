"""Step 1 of 3: the simplest possible AI example. Take one photo with the
robot's front camera and ask a pretrained YOLO model what's in it.

    1_see.py      <- you are here: look, and print everything found
    2_count.py    look for one specific kind of thing, and count it
    3_approach.py walk toward the closest match

Needs OpenCV, NumPy, and Ultralytics — deliberately not core SDK
dependencies, so install with the "all" extra: pip install -e '.[all]'

Usage:
    python3 examples/ai/1_see.py [host]
"""
import sys

import cv2
import numpy as np
from ultralytics import YOLO

from shepherd_sdk import Shepherd

OUTPUT_IMAGE = "snapshot_detected.jpg"


def main() -> None:
    robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()

    # One photo, not a live video stream — the simplest way to hand a
    # frame to a vision model. robot.camera.snapshot() returns the raw
    # JPEG bytes the front camera captured; cv2.imdecode turns those
    # into the pixel array YOLO (and OpenCV's drawing functions) expect.
    jpeg_bytes = robot.camera.snapshot("front")
    frame = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)

    # yolo11n.pt is Ultralytics' smallest pretrained model — downloaded
    # automatically the first time this runs, then cached locally. It
    # already knows 80 common object classes (COCO); no training needed.
    model = YOLO("yolo11n.pt")
    result = model(frame, verbose=False)[0]

    # result.names maps the numeric class id YOLO outputs (0, 1, 2, ...)
    # to a human name ("person", "bottle", ...) — that's what makes the
    # printout below readable instead of a list of numbers.
    print(f"Found {len(result.boxes)} object(s):")
    for box in result.boxes:
        name = result.names[int(box.cls[0])]
        confidence = float(box.conf[0])
        print(f"  {name} ({confidence:.0%} confident)")

    # result.plot() is Ultralytics' own "draw everything found" helper —
    # boxes, labels, and confidences all in one call. Saved to disk
    # rather than shown in a window, so there's nothing extra to set up
    # (no OpenCV GUI dependency, no display needed) just to see the result.
    cv2.imwrite(OUTPUT_IMAGE, result.plot())
    print(f"\nAnnotated snapshot saved to {OUTPUT_IMAGE}")


if __name__ == "__main__":
    main()
