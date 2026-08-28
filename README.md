# shepherd_sdk

A lightweight Python 3.8+ client for a `shep` service. HTTP control, snapshots,
health, and telemetry snapshots use only the Python standard library.

## Setup

Full instructions below, one section per OS — system packages first, then
the SDK itself. (Already have Python 3.8+, pip, and venv working? The
short version is the same everywhere: `python3 -m venv .venv`, activate
it, `pip install -e .`.)

Once activated, `source .venv/bin/activate` (or the Windows equivalents
below) is a one-time thing per terminal session — do it again any time you
open a new terminal to work on this. After that, plain `python3
your_script.py` (or `python your_script.py` on Windows — check
`python3 --version` / `python --version` to see which resolves for you)
and plain `pip` both just work, isolated from your system Python. Forgot
to activate? `ModuleNotFoundError: No module named 'shepherd_sdk'` is the
tell.

### Linux (Debian/Ubuntu-based — including the Jetson dock's own OS)

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git
```

`python3-venv` matters specifically: on Debian/Ubuntu, the `venv` module
is packaged *separately* from the base `python3` interpreter — skip it
and `python3 -m venv .venv` fails with an "ensurepip is not available"
error. (Same reason shep's own installer apt-get's it explicitly.)

```bash
git clone https://github.com/Stokes-Robotics-Education/shepherd_sdk.git
cd shepherd_sdk
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Planning to run `front_camera/live_view.py` or the `ai/` examples (the
OpenCV/YOLO ones)? Two extra system libraries are commonly missing on
minimal or headless installs (fresh VMs, WSL, Docker containers) — OpenCV
needs them for window support even though it's installed via pip:

```bash
sudo apt-get install -y libgl1 libglib2.0-0
pip install -e '.[all]'
```

(Ubuntu 20.04 or earlier: the package is named `libgl1-mesa-glx` instead
of `libgl1`.)

### macOS

Python 3 doesn't ship with modern macOS by default — install it first,
via either the [official installer](https://www.python.org/downloads/macos/)
or Homebrew:

```bash
brew install python3 git   # or use the python.org installer instead
```

Then the same venv flow as Linux:

```bash
git clone https://github.com/Stokes-Robotics-Education/shepherd_sdk.git
cd shepherd_sdk
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

No extra system libraries needed for `pip install -e '.[all]'` — OpenCV's
macOS wheels (both Intel and Apple Silicon) are self-contained.

### Windows

Install Python from the [official installer](https://www.python.org/downloads/windows/)
— **tick "Add python.exe to PATH"** during setup, or `python`/`pip` won't
be found afterward. Install [Git for Windows](https://git-scm.com/download/win)
too, if you don't already have it.

PowerShell:

```powershell
git clone https://github.com/Stokes-Robotics-Education/shepherd_sdk.git
cd shepherd_sdk
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

cmd.exe: identical, except activate with `.venv\Scripts\activate.bat`
instead of the `.ps1` script.

(PowerShell refusing to run the activate script with a "running scripts
is disabled on this system" error? Run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then retry —
a default-Windows security setting, not anything specific to this SDK.)

No extra system packages needed for `pip install -e '.[all]'` in the
common case. If a wheel install ever falls back to compiling from source,
installing the
[Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
fixes it — but that shouldn't come up for opencv-python/numpy/ultralytics
on a normal 64-bit Windows install.

---

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
OpenCV windows, the YOLO demo) — `pip install -e '.[all]'` (see Setup
above for OS-specific notes) installs everything at once instead of
picking dependencies apart per example:

```bash
python3 examples/telemetry/stream.py
```

To uninstall (with the venv activated):

```bash
pip uninstall shepherd-sdk
```

(`shepherd-sdk` or `shepherd_sdk` both work — pip treats the hyphen and
underscore as equivalent. Deleting the whole `.venv/` directory works too,
and if you're not sure the package is really gone, that's the surest way.
The source tree's own `src/shepherd_sdk.egg-info/` build-metadata
directory is harmless leftover either way — it's gitignored and not
something uninstall needs to clean up.)

## Capabilities

| Client | Covers |
|---|---|
| `robot.sport` | Velocity/stop, and every high-level action — postures (`stand_up`, `sit`, ...), gestures (`hello`, `dance1`, ...), and gait-mode switches (`free_walk`, `trot_run`, ...) via named methods or `action(name)` |
| `robot.slam` | Mapping/relocation/nav goals, the 10 named map-save slots (list/delete/render to PNG), waypoints (record/list/delete/goto), and the underlying SLAM service process (status/start/stop, with a `needs_password` handshake for the two process-management calls) |
| `robot.route` | Multi-waypoint route queues — build/run/stop live, or save/load/list named routes (capped per map) |
| `robot.camera` | Sources, snapshots, and an MJPEG stream URL |
| `robot.telemetry` | One-shot state, or a live WebSocket stream/callback |
| `robot` (top-level) | `health()`, `capabilities()`, `emergency_stop()`/`reset_emergency_stop()`, `obstacle_avoid()`/`set_obstacle_avoid()`, `vui_light()`/`set_vui_light()`, `low_battery()`, `restart_server()` |

## Usage examples

One runnable snippet per client, beyond the quick-start above. All of
these assume `robot = Shepherd()` (or `Shepherd("192.168.4.74")`) already
ran — see the linked `examples/` script for the full, safety-prompted
version of each.

**Movement and actions** (`robot.sport`) — full version:
`examples/high_level/movement.py`

```python
robot.sport.stand_up()
robot.sport.hello()                 # any named gesture/posture method...
robot.sport.action("dance1")        # ...or the same thing via action(name)
robot.sport.free_walk()             # gait-mode switch, not a one-off pose

try:
    robot.sport.move(vx=0.2)        # m/s forward; vy=lateral, vyaw=turn rad/s
    time.sleep(0.15)                # refresh well under the ~200-250ms
    robot.sport.move(vx=0.2)        # dead-man timeout while driving
finally:
    robot.sport.stop()
```

**Camera** (`robot.camera`) — full version:
`examples/front_camera/snapshot.py`, `examples/front_camera/live_view.py`

```python
print(robot.camera.sources())              # e.g. ["front"]
robot.camera.save_snapshot("front.jpg")    # one JPEG frame, saved to disk
jpeg_bytes = robot.camera.snapshot()       # or the raw bytes, e.g. for OpenCV/YOLO
print(robot.camera.stream_url())           # paste into a browser for live MJPEG
```

**Telemetry** (`robot.telemetry`) — full version:
`examples/telemetry/stream.py`, `examples/telemetry/faults.py`

```python
state = robot.telemetry.get()                       # one-shot snapshot
print(state["battery"], state["position"])

for state in robot.telemetry.stream():               # live, needs '.[all]'
    print(state["telemetry"]["battery"])              # (websocket-client)
    break

robot.telemetry.watch(lambda state: print(state))    # same stream, callback style
```

**SLAM — mapping, relocation, waypoints** (`robot.slam`) — full version:
`examples/slam/mapping.py`, `examples/slam/navigate.py`, `examples/slam/service.py`

```python
print(robot.slam.service_status())          # {"available": ..., "running": ...}

robot.slam.start_mapping()
# ... drive the robot around the area (physical controller, or sport.move) ...
robot.slam.end_mapping(name="map1")          # one of the 10 fixed slots

robot.slam.start_relocation(name="map1")     # localize against a saved map
robot.slam.pose_nav(x=1.0, y=0.0)            # fire-and-forget autonomous goal
# poll for arrival — pose_nav is NOT subject to the dead-man timeout:
state = robot.telemetry.get()
print(state["telemetry"]["slam"]["task_result"])

robot.slam.record_waypoint("kitchen")        # names the robot's CURRENT pose
robot.slam.goto_waypoint("kitchen")          # pose_nav back to it later
```

**Routes — sequenced multi-waypoint runs** (`robot.route`) — full version:
`examples/slam/route_planner.py`

```python
robot.route.set_relocate_map("map1")                       # relocalize first, each run()
robot.route.add_stop("kitchen", wait_s=3, action="hello")  # waypoints from robot.slam above
robot.route.add_stop("hallway")
robot.route.save("morning_patrol")                         # reuse later (max 5 per map)

robot.route.run()
status = robot.route.status()
print(status["running"], status["index"], status["log"])

robot.route.load_saved("morning_patrol")                   # ... another day:
robot.route.run()
```

## Examples

Every example takes the Shep host as an optional first positional argument,
the same convention as Unitree's own examples taking a network interface
(`python3 go2_sport_client.py eth0`):

```bash
python3 examples/core/health.py                # shep.local, or $SHEP_HOST if set
python3 examples/core/health.py 192.168.4.74    # explicit host/IP
```

(Remember to activate the venv first if it's a new terminal session —
see Setup above.)

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
| `ai/` | Optional AI demos, in four build-up steps: `1_see.py` (snapshot + detect, print everything found), `2_count.py` (same, but filtered to one class of object), `3_approach.py` (loop: detect, then walk toward the closest match) — all three via Ultralytics/YOLO — then `4_custom_model.py`, the same approach loop driven by a model you bring yourself |

`front_camera/live_view.py` and the `ai/` examples need OpenCV/NumPy (and
Ultralytics for `1_see.py`/`2_count.py`/`3_approach.py`) — deliberately not
core SDK dependencies, covered by `pip install -e '.[all]'` above.

**Bring your own model (`4_custom_model.py`):** this example doesn't use
Ultralytics — it's built around a `detect()` function you replace with a
call into whatever model you trained or downloaded, typically a
TensorFlow Lite export since that's the common target for anything
running on a Pi/Jetson-class board. `pip install -e '.[all]'` does **not**
cover this — it only knows about Ultralytics. Install whatever your own
model needs yourself (e.g. `pip install tflite-runtime` for a `.tflite`
model, or `pip install tensorflow` if `tflite-runtime` isn't available for
your platform; `onnxruntime` for a `.onnx` model, etc.), and adjust
`detect()` to match your model's actual inputs/outputs — the reference
version in the file assumes the classic SSD MobileNet TFLite layout, which
your export may not match.

