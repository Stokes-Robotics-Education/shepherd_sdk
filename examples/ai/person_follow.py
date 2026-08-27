"""Optional example: center a detected person using yaw only.

Needs OpenCV, NumPy, and Ultralytics — deliberately not core SDK dependencies,
so install with the "all" extra: pip install -e '.[all]'. Start with the Go2
supported and keep the physical controller ready.
"""
import sys
import time
from urllib.request import urlopen

import cv2
import numpy as np
from ultralytics import YOLO

from shepherd_sdk import Shepherd


robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()
model = YOLO("yolo11n.pt")
stream = urlopen(robot.camera.stream_url("front"))
buffer = b""

try:
    while True:
        buffer += stream.read(4096)
        start = buffer.find(b"\xff\xd8")
        end = buffer.find(b"\xff\xd9", start + 2)
        if start < 0 or end < 0:
            continue
        frame = cv2.imdecode(np.frombuffer(buffer[start:end + 2], np.uint8), cv2.IMREAD_COLOR)
        buffer = buffer[end + 2:]
        people = [box for box in model(frame, verbose=False)[0].boxes if int(box.cls[0]) == 0]
        if not people:
            robot.sport.stop()
            continue
        x1, _, x2, _ = people[0].xyxy[0].tolist()
        error = ((x1 + x2) / 2 - frame.shape[1] / 2) / (frame.shape[1] / 2)
        robot.sport.move(0.0, 0.0, max(-0.5, min(0.5, -error * 0.6)))
        time.sleep(0.15)
finally:
    robot.sport.stop()

