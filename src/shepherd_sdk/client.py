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

    def health(self) -> Dict[str, Any]:
        return self._transport.request("GET", "api/v1/health")

    def capabilities(self) -> Dict[str, Any]:
        return self._transport.request("GET", "api/v1/capabilities")

    def emergency_stop(self) -> Dict[str, Any]:
        return self._transport.request("POST", "api/v1/estop")

    def reset_emergency_stop(self) -> Dict[str, Any]:
        return self._transport.request("POST", "api/v1/estop/reset")
