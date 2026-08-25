# shepherd_sdk

A lightweight Python 3.8+ client for a `shep` service. HTTP control, snapshots,
health, and telemetry snapshots use only the Python standard library.

```bash
python3 -m pip install -e .
```

`shep.local:8080` is the default, so the usual case is concise:

```python
from shepherd_sdk import Shepherd

robot = Shepherd()
print(robot.health())
robot.sport.stand_up()
robot.sport.move(vx=0.2)
robot.sport.stop()
```

Velocity commands are intentionally ephemeral: refresh them at least every
200–250 ms or Shep's dead-man watchdog stops the robot. Always use `try/finally`
around sustained motion, as shown in `examples/high_level.py`.

Live WebSocket telemetry is the sole optional SDK dependency:

```bash
python3 -m pip install -e '.[telemetry]'
python3 examples/telemetry.py
```

Examples cover health/capability discovery, high-level motion, camera snapshots,
live telemetry, e-stop, and an optional YOLO person-centering demonstration. The
AI example's model stack is intentionally separate from the core SDK.

