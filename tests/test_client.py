import json
import unittest
from unittest.mock import patch

from shepherd_sdk import Shepherd


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return json.dumps(self.payload).encode()


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.client = Shepherd("127.0.0.1", 8080)

    @patch("shepherd_sdk.transport.urlopen")
    def test_health(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        self.assertTrue(self.client.health()["ok"])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/health")
        self.assertEqual(request.method, "GET")

    @patch("shepherd_sdk.transport.urlopen")
    def test_move(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        self.client.sport.move(0.2, 0.1, -0.1)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/motion/velocity")
        self.assertEqual(json.loads(request.data), {"vx": 0.2, "vy": 0.1, "vyaw": -0.1})


if __name__ == "__main__":
    unittest.main()

