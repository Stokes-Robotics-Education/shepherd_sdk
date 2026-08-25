from shepherd_sdk import Shepherd


robot = Shepherd()
print("Sources:", robot.camera.sources())
path = robot.camera.save_snapshot("front.jpg")
print("Saved", path)
print("Browser/OpenCV stream:", robot.camera.stream_url())

