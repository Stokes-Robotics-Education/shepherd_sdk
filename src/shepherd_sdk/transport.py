import json
import socket
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .errors import ShepherdConnectionError, ShepherdResponseError


class HttpTransport:
    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

    def request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            urljoin(self.base_url, path.lstrip("/")),
            data=data,
            method=method,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                payload = json.loads(exc.read().decode("utf-8"))
                message = payload.get("error", str(exc))
            except (ValueError, UnicodeDecodeError):
                message = str(exc)
            raise ShepherdResponseError(message, exc.code) from exc
        except (URLError, socket.timeout, OSError) as exc:
            raise ShepherdConnectionError("cannot reach %s: %s" % (self.base_url, exc)) from exc

    def bytes(self, path: str) -> bytes:
        try:
            with urlopen(urljoin(self.base_url, path.lstrip("/")), timeout=self.timeout) as response:
                return response.read()
        except HTTPError as exc:
            raise ShepherdResponseError(str(exc), exc.code) from exc
        except (URLError, socket.timeout, OSError) as exc:
            raise ShepherdConnectionError(str(exc)) from exc

