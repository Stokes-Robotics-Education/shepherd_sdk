import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional
from urllib.parse import urlparse, urlunparse

from .errors import ShepherdError
from .transport import HttpTransport


class SportClient:
    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    def move(self, vx: float, vy: float = 0.0, vyaw: float = 0.0) -> Dict[str, Any]:
        """Send velocity once. Refresh faster than the advertised dead-man timeout."""
        return self._transport.request("POST", "api/v1/motion/velocity", {
            "vx": vx, "vy": vy, "vyaw": vyaw,
        })

    def stop(self) -> Dict[str, Any]:
        return self._transport.request("POST", "api/v1/motion/stop")

    def action(self, name: str) -> Dict[str, Any]:
        return self._transport.request("POST", "api/v1/actions/%s" % name)

    def stand_up(self) -> Dict[str, Any]:
        return self.action("stand_up")

    def stand_down(self) -> Dict[str, Any]:
        return self.action("stand_down")

    def rise_sit(self) -> Dict[str, Any]:
        return self.action("rise_sit")

    def recovery_stand(self) -> Dict[str, Any]:
        return self.action("recovery_stand")

    def balance_stand(self) -> Dict[str, Any]:
        return self.action("balance_stand")

    def sit(self) -> Dict[str, Any]:
        return self.action("sit")

    def hello(self) -> Dict[str, Any]:
        return self.action("hello")

    def stretch(self) -> Dict[str, Any]:
        return self.action("stretch")

    def content(self) -> Dict[str, Any]:
        return self.action("content")

    def dance1(self) -> Dict[str, Any]:
        return self.action("dance1")

    def dance2(self) -> Dict[str, Any]:
        return self.action("dance2")

    def heart(self) -> Dict[str, Any]:
        return self.action("heart")

    def free_walk(self) -> Dict[str, Any]:
        """Gait-mode switch, not a gesture — how the robot walks after this,
        not a one-off pose. See static_walk()/trot_run() for the others."""
        return self.action("free_walk")

    def static_walk(self) -> Dict[str, Any]:
        return self.action("static_walk")

    def trot_run(self) -> Dict[str, Any]:
        return self.action("trot_run")


class SlamClient:
    """Unitree's built-in SLAM (mapping/relocation/nav goals) via shep's
    /api/v1/slam/{name}. Requires the unitree_slam module's own server
    process running on the robot — see shep's README for details. A call
    against a stopped SLAM service raises ShepherdResponseError with a
    nonzero RPC code in its message, the same as any other unreachable
    robot call; a 501 means shep itself never initialized a SLAM client.
    """

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    # --- The mid360_driver + unitree_slam OS processes that command()'s
    # RPCs actually depend on. A command() call fails one of two distinct
    # ways: SLAM support unavailable at all (501), vs. the service isn't
    # currently running (a clear error instead of a slow RPC timeout). ---

    def service_status(self) -> Dict[str, Any]:
        """{"available": <can shep launch it at all>, "running": <is it up
        right now>}. running is polled fresh on every call — don't call
        this in a tight loop."""
        return self._transport.request("GET", "api/v1/slam/service")

    def start_service(self, password: Optional[str] = None) -> Dict[str, Any]:
        """Launches mid360_driver + unitree_slam — needs root on the robot,
        so shep gates this behind sudo. Without a password and no cached
        sudo credential on shep's side, this returns
        {"ok": False, "needs_password": True, "msg": ...} instead of
        raising — call again with the password once you have one:

            result = robot.slam.start_service()
            if result.get("needs_password"):
                result = robot.slam.start_service(password=getpass.getpass())
        """
        body = {"password": password} if password is not None else None
        return self._transport.request("POST", "api/v1/slam/service/start", body)

    def stop_service(self, password: Optional[str] = None) -> Dict[str, Any]:
        """Same needs_password handshake as start_service(). Best-effort
        graceful stop (cancels any active mapping/nav task) before killing
        the processes; also restores obstacle avoidance and clears shep's
        own active-map/mapping-session state, even if nothing was actually
        found running."""
        body = {"password": password} if password is not None else None
        return self._transport.request("POST", "api/v1/slam/service/stop", body)

    def command(self, name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._transport.request("POST", "api/v1/slam/%s" % name, params)

    def start_mapping(self, slam_type: str = "indoor") -> Dict[str, Any]:
        return self.command("start_mapping", {"slam_type": slam_type})

    def list_maps(self) -> Dict[str, Any]:
        """The fixed 10 named map-save slots and which are already used —
        pick one of maps()["slots"] rather than an arbitrary path."""
        return self._transport.request("GET", "api/v1/slam/maps")

    def delete_map(self, name: str) -> Dict[str, Any]:
        """Removes a saved map slot's .pcd from disk — irreversible. name
        must be one of list_maps()["slots"]; deleting an already-empty slot
        is a no-op, not an error. If this slot happens to be shep's current
        active_map, that's cleared too."""
        return self._transport.request("DELETE", "api/v1/slam/maps/%s" % name)

    def render_map(self, name: str) -> bytes:
        """PNG bytes of a top-down scatter render of a saved map slot's
        point cloud — see render_map_info() for the pixel<->world transform
        needed to plot anything (a waypoint, the robot's own pose) on top
        of it."""
        return self._transport.bytes("api/v1/slam/maps/%s/render.png" % name)

    def save_map_render(self, path: str, name: str) -> Path:
        destination = Path(path)
        destination.write_bytes(self.render_map(name))
        return destination

    def render_map_info(self, name: str) -> Dict[str, Any]:
        """width/height (pixels), scale (pixels per meter), origin_x/
        origin_y (world meters at pixel (0, height)) for the same slot's
        render_map() PNG. Convert a world (x, y) to a pixel with:

            px = (x - origin_x) * scale
            py = height - (y - origin_y) * scale

        (Y is flipped: image rows grow downward, world Y is "up".)"""
        return self._transport.request("GET", "api/v1/slam/maps/%s/render" % name)

    def end_mapping(self, name: Optional[str] = None, address: Optional[str] = None) -> Dict[str, Any]:
        """Pass name (one of list_maps()["slots"]) for the common case; shep
        resolves the actual path. address is the escape hatch for a
        freeform path shep doesn't manage as a slot."""
        if not name and not address:
            raise ValueError("end_mapping needs name or address")
        return self.command("end_mapping", {"name": name} if name else {"address": address})

    def start_relocation(
        self, name: Optional[str] = None, address: Optional[str] = None,
        x: float = 0.0, y: float = 0.0, z: float = 0.0,
        q_x: float = 0.0, q_y: float = 0.0, q_z: float = 0.0, q_w: float = 1.0,
    ) -> Dict[str, Any]:
        if not name and not address:
            raise ValueError("start_relocation needs name or address")
        params = {"x": x, "y": y, "z": z, "q_x": q_x, "q_y": q_y, "q_z": q_z, "q_w": q_w}
        params.update({"name": name} if name else {"address": address})
        return self.command("start_relocation", params)

    def pose_nav(
        self, x: float, y: float, z: float = 0.0,
        q_x: float = 0.0, q_y: float = 0.0, q_z: float = 0.0, q_w: float = 1.0,
        mode: int = 1, speed: float = 0.8,
    ) -> Dict[str, Any]:
        """Drive the robot autonomously to (x, y) via Unitree's own SLAM
        planner. Unlike sport.move(), this is not subject to shep's
        dead-man timeout — it's a fire-and-forget goal, not a per-tick
        velocity command. Poll telemetry()["slam"]["task_result"] or watch
        telemetry.stream() for arrival."""
        return self.command("pose_nav", {
            "x": x, "y": y, "z": z, "q_x": q_x, "q_y": q_y, "q_z": q_z, "q_w": q_w,
            "mode": mode, "speed": speed,
        })

    def pause_nav(self) -> Dict[str, Any]:
        return self.command("pause_nav")

    def resume_nav(self) -> Dict[str, Any]:
        return self.command("resume_nav")

    def stop(self) -> Dict[str, Any]:
        return self.command("stop")

    def record_waypoint(self, name: str) -> Dict[str, Any]:
        """Capture the robot's current live SLAM pose under name — a button
        press, not typed x/y. Raises if no SLAM pose is available yet
        (telemetry()["slam"]["pose"] must have been published at least
        once) or if there's no active map (start mapping or relocate
        against a saved map first — shep tags the waypoint with it, since
        the pose only means anything relative to that map's frame).

        A waypoint is just a named pose now — no per-waypoint action.
        Action-on-arrival and wait are properties of a *route stop*
        instead (see RouteClient.add_stop), so the same waypoint can be
        reused across routes with different behavior at it."""
        return self._transport.request("POST", "api/v1/slam/waypoints", {"name": name})

    def list_waypoints(self) -> Dict[str, Any]:
        return self._transport.request("GET", "api/v1/slam/waypoints")["waypoints"]

    def delete_waypoint(self, name: str) -> Dict[str, Any]:
        return self._transport.request("DELETE", "api/v1/slam/waypoints/%s" % name)

    def goto_waypoint(self, name: str) -> Dict[str, Any]:
        """pose_nav to a previously recorded waypoint. Same fire-and-forget
        semantics as pose_nav() — poll telemetry for arrival. Unlike a
        route stop, this never fires an action or waits — those only exist
        as RouteClient stop properties."""
        return self._transport.request("POST", "api/v1/slam/nav/goto/%s" % name)


class RouteClient:
    """Sequential multi-waypoint route runner. Each stop is
    {"name": <waypoint name>, "wait_s": <float, optional>,
    "action": <one of capabilities()["actions"], optional>} — arrive ->
    fire the stop's action (if any) -> wait wait_s -> balance_stand ->
    next stop. If relocate_map is set, a run() first relocates against
    that map before touching any stop.

    The live queue is edited as a whole via set_queue(); add_stop() is a
    convenience that reads the current queue (from status()) and pushes
    back a copy with one more stop appended."""

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    def status(self) -> Dict[str, Any]:
        """{"queue": [...], "running": bool, "index": int, "log": str,
        "relocate_map": str|None} — the same block embedded under "planner"
        in Shepherd.health()."""
        return self._transport.request("GET", "api/v1/health")["planner"]

    def set_queue(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Replaces the live queue wholesale. A stop whose waypoint doesn't
        exist, or belongs to a different map than relocate_map, is silently
        dropped — check the returned (possibly shorter) queue rather than
        assuming everything you sent stuck."""
        result = self._transport.request("POST", "api/v1/planner/queue", {"queue": items})
        return result["queue"]

    def add_stop(
        self, name: str, wait_s: Optional[float] = None, action: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        item: Dict[str, Any] = {"name": name}
        if wait_s is not None:
            item["wait_s"] = wait_s
        if action:
            item["action"] = action
        return self.set_queue(self.status()["queue"] + [item])

    def clear(self) -> List[Dict[str, Any]]:
        return self.set_queue([])

    def set_relocate_map(self, name: Optional[str]) -> Dict[str, Any]:
        """A run() relocates against this map first, before any stop — set
        None for "no relocation" (only sensible if the robot's already
        localized against the right map some other way)."""
        return self._transport.request("POST", "api/v1/planner/relocate_map", {"name": name})

    def run(self) -> Dict[str, Any]:
        """Starts the live queue running — raises if already running or the
        queue is empty. Fire-and-forget: poll status() (running/index/log)
        or watch telemetry.stream()'s "planner" block for progress."""
        return self._transport.request("POST", "api/v1/planner/run")

    def stop(self) -> Dict[str, Any]:
        """Halts a running route (best-effort pause_nav on whatever leg is
        in flight). The queue itself is untouched, but shep doesn't resume
        mid-queue — a later run() starts over from the first stop."""
        return self._transport.request("POST", "api/v1/planner/stop")

    def list_saved(self) -> Dict[str, Any]:
        """{name: {"map": ..., "queue": [...]}, ...} for every saved
        route."""
        return self._transport.request("GET", "api/v1/planner/routes")["routes"]

    def save(self, name: str) -> Dict[str, Any]:
        """Snapshots the CURRENT live queue under name, scoped to whatever
        relocate_map is set to right now (set_relocate_map() first — a
        route needs a target map to be saved at all, since that's the
        frame its stops' x/y are only meaningful against). Capped at 5
        saved routes per map; re-saving the same name in place doesn't
        cost a slot."""
        return self._transport.request("POST", "api/v1/planner/routes", {"name": name})

    def delete_saved(self, name: str) -> Dict[str, Any]:
        return self._transport.request("DELETE", "api/v1/planner/routes/%s" % name)

    def load_saved(self, name: str) -> Dict[str, Any]:
        """Loads a saved route's queue + relocate_map into the live,
        editable queue — does NOT start running it, call run() after."""
        return self._transport.request("POST", "api/v1/planner/routes/%s/load" % name)


class CameraClient:
    def __init__(self, transport: HttpTransport, base_url: str) -> None:
        self._transport = transport
        self._base_url = base_url.rstrip("/")

    def sources(self):
        return self._transport.request("GET", "api/v1/capabilities")["cameras"]

    def snapshot(self, source: str = "front") -> bytes:
        return self._transport.bytes("api/v1/cameras/%s/snapshot.jpg" % source)

    def save_snapshot(self, path: str, source: str = "front") -> Path:
        destination = Path(path)
        destination.write_bytes(self.snapshot(source))
        return destination

    def stream_url(self, source: str = "front") -> str:
        return "%s/api/v1/cameras/%s/stream.mjpg" % (self._base_url, source)


class TelemetryClient:
    def __init__(self, transport: HttpTransport, base_url: str) -> None:
        self._transport = transport
        parsed = urlparse(base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        self._ws_url = urlunparse((scheme, parsed.netloc, "/api/v1/telemetry/ws", "", "", ""))

    def get(self) -> Dict[str, Any]:
        return self._transport.request("GET", "api/v1/telemetry")

    def stream(self) -> Iterator[Dict[str, Any]]:
        """Yield live state. Install `shepherd-sdk[telemetry]` for this method."""
        try:
            import json
            import websocket
        except ImportError as exc:
            raise ShepherdError("live telemetry requires: pip install 'shepherd-sdk[telemetry]'") from exc
        connection = websocket.create_connection(self._ws_url)
        try:
            while True:
                yield json.loads(connection.recv())
        finally:
            connection.close()

    def watch(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        for state in self.stream():
            callback(state)


class Shepherd:
    """Entry point for a Shep service; defaults to mDNS at shep.local.

    The default host can be overridden without code changes by setting the
    SHEP_HOST environment variable (useful before shep.local resolves, e.g.
    running against a service by IP during development).
    """

    def __init__(self, host: Optional[str] = None, port: int = 8080, timeout: float = 5.0) -> None:
        host = host or os.getenv("SHEP_HOST", "shep.local")
        if "://" in host:
            self.base_url = host.rstrip("/")
        else:
            self.base_url = "http://%s:%d" % (host, port)
        self._transport = HttpTransport(self.base_url, timeout)
        self.sport = SportClient(self._transport)
        self.camera = CameraClient(self._transport, self.base_url)
        self.telemetry = TelemetryClient(self._transport, self.base_url)
        self.slam = SlamClient(self._transport)
        self.route = RouteClient(self._transport)

    def health(self) -> Dict[str, Any]:
        return self._transport.request("GET", "api/v1/health")

    def capabilities(self) -> Dict[str, Any]:
        return self._transport.request("GET", "api/v1/capabilities")

    def emergency_stop(self) -> Dict[str, Any]:
        return self._transport.request("POST", "api/v1/estop")

    def reset_emergency_stop(self) -> Dict[str, Any]:
        return self._transport.request("POST", "api/v1/estop/reset")

    def obstacle_avoid(self) -> Dict[str, Any]:
        """{"available": bool, "enabled": bool|None} — the Go2's own
        built-in obstacle-avoidance mode (distinct from anything shep's
        own SLAM/route planning does). shep flips this off automatically
        while its SLAM service is up and back on when it stops (Unitree's
        own SLAM notes: the two otherwise fight over motion control) — this
        is the manual override + status readout on top of that."""
        return self._transport.request("GET", "api/v1/obstacle_avoid")

    def set_obstacle_avoid(self, enable: bool) -> Dict[str, Any]:
        return self._transport.request("POST", "api/v1/obstacle_avoid", {"enable": enable})

    def vui_light(self) -> Dict[str, Any]:
        """{"available": bool, "level": int|None} — the Go2's VUI head-LED
        brightness (unitree_sdk2py go2.vui.VuiClient.GetBrightness)."""
        return self._transport.request("GET", "api/v1/vui/light")

    def low_battery(self) -> bool:
        """True once battery has dropped below capabilities()
        ["low_battery_percent"] and shep has auto-stood the robot down —
        move()/sport.action()/slam.command() all then reject with "battery
        critically low" until this clears. Nothing resets it early: it
        only clears once the battery actually recovers, with some margin
        above the trigger point so it doesn't flap right at the edge."""
        return bool(self.health().get("low_battery"))

    def restart_server(self) -> Dict[str, Any]:
        """Gracefully restarts the whole shep process — e.g. to pick up a
        camera that wasn't connected at boot (shep only probes for it once,
        at startup). Returns normally once shep has accepted the request;
        the restart itself follows shortly after and takes shep off the
        network for a few seconds — any WebSocket telemetry stream or
        other in-flight call will drop, and a following request may need
        a retry once shep is back up."""
        return self._transport.request("POST", "api/v1/server/restart")

    def set_vui_light(self, level: int) -> Dict[str, Any]:
        """0-10, per VuiClient's own example script — shep clamps into that
        range server-side rather than raising on an out-of-range value.
        The response's "level" just echoes what you sent, though, not the
        clamped value actually applied — call vui_light() after if you
        need to confirm what the device landed on."""
        return self._transport.request("POST", "api/v1/vui/light", {"level": level})
