import sys

from shepherd_sdk import Shepherd


robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()
print("Sources:", robot.camera.sources())
path = robot.camera.save_snapshot("front.jpg")
print("Saved", path)
print("Browser/OpenCV stream:", robot.camera.stream_url())

