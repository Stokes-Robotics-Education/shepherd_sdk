"""Step 2 of 3: look for one specific kind of thing and count how many
the robot's camera can see, instead of listing everything (1_see.py did
that already).

    1_see.py      look, and print everything found
    2_count.py    <- you are here: count just one kind of thing
    3_approach.py walk toward the closest match

Needs OpenCV, NumPy, and Ultralytics — deliberately not core SDK
dependencies, so install with the "all" extra: pip install -e '.[all]'

Usage:
    python3 examples/ai/2_count.py [host]
"""
import sys

import cv2
import numpy as np
from ultralytics import YOLO

from shepherd_sdk import Shepherd

# Change this to look for something else — any class the pretrained
# model knows, e.g. "bottle", "chair", "cell phone". Full list of 80:
# https://docs.ultralytics.com/datasets/detect/coco/#dataset-yaml
TARGET = "person"


def main() -> None:
    robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()

    jpeg_bytes = robot.camera.snapshot("front")
    frame = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)

    model = YOLO("yolo11n.pt")
    result = model(frame, verbose=False)[0]

    # Same detection as 1_see.py — the only new part is filtering down
    # to boxes whose class name matches TARGET, ignoring everything
    # else YOLO happened to find in frame.
    matches = [box for box in result.boxes if result.names[int(box.cls[0])] == TARGET]

    print(f"Found {len(matches)} '{TARGET}' in frame.")
    for box in matches:
        print(f"  confidence: {float(box.conf[0]):.0%}")


if __name__ == "__main__":
    main()
