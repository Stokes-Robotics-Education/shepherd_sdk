# shepherd_sdk

A lightweight Python 3.8+ client for a `shep` service. HTTP control, snapshots,
health, and telemetry snapshots use only the Python standard library.

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

(A venv isn't required — `pip install -e .` just installs into whatever
Python environment is active when you run it — but skipping it means
installing into your system or user Python instead of somewhere
self-contained.)

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

The base install (above) is everything the SDK itself needs — zero runtime
dependencies. Some examples need more (live WebSocket telemetry, camera
OpenCV windows, the YOLO demo); install everything at once instead of
picking dependencies apart per example:

```bash
.venv/bin/pip install -e '.[all]'
python3 examples/telemetry/stream.py
```

To uninstall:

```bash
.venv/bin/pip uninstall shepherd-sdk
```

(`shepherd-sdk` or `shepherd_sdk` both work — pip treats the hyphen and
underscore as equivalent. If you installed with the venv above, deleting
the whole `.venv/` directory works too. Either way, the source tree's own
`src/shepherd_sdk.egg-info/` build-metadata directory is harmless leftover,
not something uninstall needs to clean up — it's gitignored and safe to
ignore or delete by hand.)

## Capabilities

| Client | Covers |
|---|---|
| `robot.sport` | Velocity/stop, and every high-level action — postures (`stand_up`, `sit`, ...), gestures (`hello`, `dance1`, ...), and gait-mode switches (`free_walk`, `trot_run`, ...) via named methods or `action(name)` |
| `robot.slam` | Mapping/relocation/nav goals, the 10 named map-save slots (list/delete/render to PNG), waypoints (record/list/delete/goto), and the underlying SLAM service process (status/start/stop, with a `needs_password` handshake for the two process-management calls) |
| `robot.route` | Multi-waypoint route queues — build/run/stop live, or save/load/list named routes (capped per map) |
| `robot.camera` | Sources, snapshots, and an MJPEG stream URL |
| `robot.telemetry` | One-shot state, or a live WebSocket stream/callback |
| `robot` (top-level) | `health()`, `capabilities()`, `emergency_stop()`/`reset_emergency_stop()`, `obstacle_avoid()`/`set_obstacle_avoid()`, `vui_light()`/`set_vui_light()`, `low_battery()`, `restart_server()` |

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
| `slam/` | `mapping.py` (start/end a mapping session), `navigate.py` (relocalize + one nav goal), `service.py` (check/start/stop the SLAM service, handles the sudo-password handshake), `route_planner.py` (build a route from recorded waypoints, save it, run it) — all need the SLAM service actually running on the robot side |
| `ai/` | `person_follow.py` — optional YOLO person-centering demo |

`front_camera/live_view.py` and `ai/person_follow.py` need OpenCV/NumPy (and
Ultralytics for the AI example) — deliberately not core SDK dependencies,
covered by `pip install -e '.[all]'` above.

