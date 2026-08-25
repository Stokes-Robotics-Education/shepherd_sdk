import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional
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

    def command(self, name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._transport.request("POST", "api/v1/slam/%s" % name, params)

    def start_mapping(self, slam_type: str = "indoor") -> Dict[str, Any]:
        return self.command("start_mapping", {"slam_type": slam_type})

    def list_maps(self) -> Dict[str, Any]:
        """The fixed 10 named map-save slots and which are already used —
        pick one of maps()["slots"] rather than an arbitrary path."""
        return self._transport.request("GET", "api/v1/slam/maps")

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

    def record_waypoint(self, name: str, action: Optional[str] = None) -> Dict[str, Any]:
        """Capture the robot's current live SLAM pose under name — a button
        press, not typed x/y. Raises if no SLAM pose is available yet
        (telemetry()["slam"]["pose"] must have been published at least
        once).

        action, if given, must be one of capabilities()["actions"] — shep
        fires it automatically once the robot arrives after a later
        goto_waypoint(name), server-side, independent of whether this
        process is still connected when arrival happens."""
        body = {"name": name}
        if action:
            body["action"] = action
        return self._transport.request("POST", "api/v1/slam/waypoints", body)

    def list_waypoints(self) -> Dict[str, Any]:
        return self._transport.request("GET", "api/v1/slam/waypoints")["waypoints"]

    def delete_waypoint(self, name: str) -> Dict[str, Any]:
        return self._transport.request("DELETE", "api/v1/slam/waypoints/%s" % name)

    def goto_waypoint(self, name: str) -> Dict[str, Any]:
        """pose_nav to a previously recorded waypoint. Same fire-and-forget
        semantics as pose_nav() — poll telemetry for arrival."""
        return self._transport.request("POST", "api/v1/slam/nav/goto/%s" % name)


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

    def health(self) -> Dict[str, Any]:
        return self._transport.request("GET", "api/v1/health")

    def capabilities(self) -> Dict[str, Any]:
        return self._transport.request("GET", "api/v1/capabilities")

    def emergency_stop(self) -> Dict[str, Any]:
        return self._transport.request("POST", "api/v1/estop")

    def reset_emergency_stop(self) -> Dict[str, Any]:
        return self._transport.request("POST", "api/v1/estop/reset")
