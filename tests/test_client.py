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

    @patch("shepherd_sdk.transport.urlopen")
    def test_slam_pose_nav_sends_flat_params(self, urlopen):
        # Regression: shep's server-side dispatch does client.pose_nav(**body) —
        # the body must be flat kwargs (x, y, ...), NOT nested under "targetPose".
        # That nesting is something shep's own SlamClient does internally when
        # it calls the real SLAM RPC; pre-nesting it here breaks the dispatch.
        urlopen.return_value = FakeResponse({"ok": True})
        self.client.slam.pose_nav(x=1.0, y=2.0)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/slam/pose_nav")
        body = json.loads(request.data)
        self.assertEqual(body["x"], 1.0)
        self.assertEqual(body["y"], 2.0)
        self.assertNotIn("targetPose", body)

    @patch("shepherd_sdk.transport.urlopen")
    def test_end_mapping_by_slot_name(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        self.client.slam.end_mapping(name="map3")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/slam/end_mapping")
        self.assertEqual(json.loads(request.data), {"name": "map3"})

    @patch("shepherd_sdk.transport.urlopen")
    def test_end_mapping_by_address_still_works(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        self.client.slam.end_mapping(address="/custom/path.pcd")
        request = urlopen.call_args.args[0]
        self.assertEqual(json.loads(request.data), {"address": "/custom/path.pcd"})

    def test_end_mapping_requires_name_or_address(self):
        with self.assertRaises(ValueError):
            self.client.slam.end_mapping()

    @patch("shepherd_sdk.transport.urlopen")
    def test_goto_waypoint(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        self.client.slam.goto_waypoint("loading_zone")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/slam/nav/goto/loading_zone")
        self.assertEqual(request.method, "POST")

    @patch("shepherd_sdk.transport.urlopen")
    def test_record_waypoint(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        self.client.slam.record_waypoint("loading_zone")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/slam/waypoints")
        self.assertEqual(json.loads(request.data), {"name": "loading_zone"})


if __name__ == "__main__":
    unittest.main()

