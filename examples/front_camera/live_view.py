"""Optional example: live-view the front camera MJPEG stream in a window.

Mirrors Unitree's front_camera/camera_opencv.py (ESC to quit, 's' saves the
current frame), but reads Shep's browser-compatible MJPEG endpoint instead of
calling VideoClient directly.

Needs OpenCV and NumPy — deliberately not core SDK dependencies, so
install with the "all" extra: pip install -e '.[all]'.

Usage:
    python3 examples/front_camera/live_view.py [host] [source]

    host defaults to shep.local (or $SHEP_HOST if set); source defaults
    to "front".
"""
import sys
from urllib.request import urlopen

import cv2
import numpy as np

from shepherd_sdk import Shepherd


def main() -> None:
    source = sys.argv[2] if len(sys.argv) > 2 else "front"
    robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()

    stream = urlopen(robot.camera.stream_url(source))
    buffer = b""
    print("Press ESC to quit, 's' to save the current frame.")

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

        cv2.imshow(source, frame)
        key = cv2.waitKey(20) & 0xFF
        if key == 27:  # ESC
            break
        if key == ord("s"):
            cv2.imwrite(f"{source}_frame.jpg", frame)
            print(f"Saved {source}_frame.jpg")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
