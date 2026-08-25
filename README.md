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
around sustained motion, as shown in `examples/high_level/movement.py`.

Live WebSocket telemetry is the sole optional SDK dependency:

```bash
python3 -m pip install -e '.[telemetry]'
python3 examples/telemetry/stream.py
```

## Examples

Every example takes the Shep host as an optional first positional argument,
the same convention as Unitree's own examples taking a network interface
(`python3 go2_sport_client.py eth0`):

```bash
python3 examples/core/health.py                # shep.local, or $SHEP_HOST if set
python3 examples/core/health.py 192.168.4.74    # explicit host/IP
```

`front_camera/live_view.py` additionally takes a camera source as a second
argument (default `front`).

Layered by capability, the same way as Unitree's own SDK examples
(`unitree_sdk2_python/example/go2/{front_camera,high_level}/`) — one folder
per subsystem. There is no `low_level/` folder: Shep intentionally exposes
only the high-level sport API, not raw joint control.

| Folder | Contents |
|---|---|
| `core/` | `health.py` — service/robot health and capability discovery |
| `high_level/` | `movement.py` (stand + short walk + stop), `emergency_stop.py`, `interactive_test.py` (menu-driven manual test of every action, styled after `go2_sport_client.py`) |
| `front_camera/` | `snapshot.py` (save one JPEG), `live_view.py` (optional, OpenCV window over the MJPEG stream) |
| `telemetry/` | `stream.py` — live WebSocket telemetry; `faults.py` — read the Fault Services diagnostic feed |
| `slam/` | `mapping.py` (start/end a mapping session), `navigate.py` (relocalize + one nav goal) — needs `shep`'s SLAM client available, see its README |
| `ai/` | `person_follow.py` — optional YOLO person-centering demo |

`front_camera/live_view.py` and `ai/person_follow.py` need OpenCV/NumPy (and
Ultralytics for the AI example) installed separately — deliberately not core
SDK dependencies.

