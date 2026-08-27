import json
import tempfile
import unittest
from pathlib import Path
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


class FakeBytesResponse:
    """Like FakeResponse, but for transport.bytes() — no JSON encoding,
    and urlopen is called with a plain URL string, not a Request object."""

    def __init__(self, raw):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return self.raw


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
        # Regression: the request body must be flat kwargs (x, y, ...),
        # NOT nested under a "targetPose" key — shep expects the former.
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

    @patch("shepherd_sdk.transport.urlopen")
    def test_record_waypoint_takes_no_action(self, urlopen):
        # Regression: shep dropped per-waypoint action (moved to route
        # stops) — record_waypoint must not send an "action" field at all.
        urlopen.return_value = FakeResponse({"ok": True})
        self.client.slam.record_waypoint("loading_zone")
        request = urlopen.call_args.args[0]
        self.assertNotIn("action", json.loads(request.data))

    @patch("shepherd_sdk.transport.urlopen")
    def test_sport_action_wrappers(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        for method_name, action_name in [
            ("hello", "hello"), ("stretch", "stretch"), ("content", "content"),
            ("dance1", "dance1"), ("dance2", "dance2"), ("heart", "heart"),
            ("free_walk", "free_walk"), ("static_walk", "static_walk"), ("trot_run", "trot_run"),
        ]:
            getattr(self.client.sport, method_name)()
            request = urlopen.call_args.args[0]
            self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/actions/%s" % action_name)
            self.assertEqual(request.method, "POST")


    # --- Chunk 2: SLAM extras (service management, map render/delete) ---

    @patch("shepherd_sdk.transport.urlopen")
    def test_slam_service_status(self, urlopen):
        urlopen.return_value = FakeResponse({"available": True, "running": False})
        result = self.client.slam.service_status()
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/slam/service")
        self.assertEqual(request.method, "GET")
        self.assertFalse(result["running"])

    @patch("shepherd_sdk.transport.urlopen")
    def test_slam_start_service_no_password_sends_no_body(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        self.client.slam.start_service()
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/slam/service/start")
        self.assertIsNone(request.data)

    @patch("shepherd_sdk.transport.urlopen")
    def test_slam_start_service_with_password(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        self.client.slam.start_service(password="hunter2")
        request = urlopen.call_args.args[0]
        self.assertEqual(json.loads(request.data), {"password": "hunter2"})

    @patch("shepherd_sdk.transport.urlopen")
    def test_slam_start_service_needs_password(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": False, "needs_password": True, "msg": "sudo password required"})
        result = self.client.slam.start_service()
        self.assertTrue(result["needs_password"])

    @patch("shepherd_sdk.transport.urlopen")
    def test_slam_stop_service(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        self.client.slam.stop_service(password="hunter2")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/slam/service/stop")
        self.assertEqual(json.loads(request.data), {"password": "hunter2"})

    @patch("shepherd_sdk.transport.urlopen")
    def test_delete_map(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        self.client.slam.delete_map("map3")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/slam/maps/map3")
        self.assertEqual(request.method, "DELETE")

    @patch("shepherd_sdk.transport.urlopen")
    def test_render_map_returns_raw_bytes(self, urlopen):
        urlopen.return_value = FakeBytesResponse(b"\x89PNG\r\n...")
        result = self.client.slam.render_map("map1")
        self.assertEqual(result, b"\x89PNG\r\n...")
        called_url = urlopen.call_args.args[0]
        self.assertEqual(called_url, "http://127.0.0.1:8080/api/v1/slam/maps/map1/render.png")

    @patch("shepherd_sdk.transport.urlopen")
    def test_save_map_render(self, urlopen):
        urlopen.return_value = FakeBytesResponse(b"pngdata")
        with tempfile.TemporaryDirectory() as tmp:
            path = self.client.slam.save_map_render(str(Path(tmp) / "map1.png"), "map1")
            self.assertEqual(path.read_bytes(), b"pngdata")

    @patch("shepherd_sdk.transport.urlopen")
    def test_render_map_info(self, urlopen):
        urlopen.return_value = FakeResponse({"width": 900, "height": 700, "scale": 45.0, "origin_x": -1.2, "origin_y": -0.5})
        info = self.client.slam.render_map_info("map1")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/slam/maps/map1/render")
        self.assertEqual(info["scale"], 45.0)

    # --- Chunk 3: Route Planner (RouteClient — live queue + saved routes) ---

    @patch("shepherd_sdk.transport.urlopen")
    def test_route_status_unwraps_planner_block(self, urlopen):
        urlopen.return_value = FakeResponse({
            "ok": True, "planner": {"queue": [], "running": False, "index": -1, "log": "", "relocate_map": None},
        })
        status = self.client.route.status()
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/health")
        self.assertEqual(status["running"], False)

    @patch("shepherd_sdk.transport.urlopen")
    def test_route_set_queue(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True, "queue": [{"name": "wp0"}]})
        result = self.client.route.set_queue([{"name": "wp0"}])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/planner/queue")
        self.assertEqual(json.loads(request.data), {"queue": [{"name": "wp0"}]})
        self.assertEqual(result, [{"name": "wp0"}])

    @patch("shepherd_sdk.transport.urlopen")
    def test_route_add_stop_reads_then_writes(self, urlopen):
        # add_stop() is read-modify-write: GET /health for the current
        # queue, then POST the queue back with one more stop appended.
        urlopen.side_effect = [
            FakeResponse({"planner": {"queue": [{"name": "wp0"}], "running": False, "index": -1, "log": "", "relocate_map": None}}),
            FakeResponse({"ok": True, "queue": [{"name": "wp0"}, {"name": "wp1", "wait_s": 2.0, "action": "hello"}]}),
        ]
        result = self.client.route.add_stop("wp1", wait_s=2.0, action="hello")
        self.assertEqual(urlopen.call_count, 2)
        first_request = urlopen.call_args_list[0].args[0]
        second_request = urlopen.call_args_list[1].args[0]
        self.assertEqual(first_request.full_url, "http://127.0.0.1:8080/api/v1/health")
        self.assertEqual(second_request.full_url, "http://127.0.0.1:8080/api/v1/planner/queue")
        sent = json.loads(second_request.data)
        self.assertEqual(sent["queue"], [{"name": "wp0"}, {"name": "wp1", "wait_s": 2.0, "action": "hello"}])
        self.assertEqual(len(result), 2)

    @patch("shepherd_sdk.transport.urlopen")
    def test_route_add_stop_omits_unset_fields(self, urlopen):
        urlopen.side_effect = [
            FakeResponse({"planner": {"queue": [], "running": False, "index": -1, "log": "", "relocate_map": None}}),
            FakeResponse({"ok": True, "queue": [{"name": "wp0"}]}),
        ]
        self.client.route.add_stop("wp0")
        second_request = urlopen.call_args_list[1].args[0]
        sent_item = json.loads(second_request.data)["queue"][0]
        self.assertNotIn("wait_s", sent_item)
        self.assertNotIn("action", sent_item)

    @patch("shepherd_sdk.transport.urlopen")
    def test_route_clear(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True, "queue": []})
        result = self.client.route.clear()
        request = urlopen.call_args.args[0]
        self.assertEqual(json.loads(request.data), {"queue": []})
        self.assertEqual(result, [])

    @patch("shepherd_sdk.transport.urlopen")
    def test_route_set_relocate_map(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True, "relocate_map": "map1"})
        self.client.route.set_relocate_map("map1")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/planner/relocate_map")
        self.assertEqual(json.loads(request.data), {"name": "map1"})

    @patch("shepherd_sdk.transport.urlopen")
    def test_route_run_and_stop(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        self.client.route.run()
        self.assertEqual(urlopen.call_args.args[0].full_url, "http://127.0.0.1:8080/api/v1/planner/run")
        self.client.route.stop()
        self.assertEqual(urlopen.call_args.args[0].full_url, "http://127.0.0.1:8080/api/v1/planner/stop")

    @patch("shepherd_sdk.transport.urlopen")
    def test_route_list_saved_unwraps_routes(self, urlopen):
        urlopen.return_value = FakeResponse({"routes": {"patrol": {"map": "map1", "queue": []}}})
        routes = self.client.route.list_saved()
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/planner/routes")
        self.assertEqual(routes, {"patrol": {"map": "map1", "queue": []}})

    @patch("shepherd_sdk.transport.urlopen")
    def test_route_save(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True, "name": "patrol", "route": {"map": "map1", "queue": []}})
        self.client.route.save("patrol")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/planner/routes")
        self.assertEqual(json.loads(request.data), {"name": "patrol"})

    @patch("shepherd_sdk.transport.urlopen")
    def test_route_delete_saved(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        self.client.route.delete_saved("patrol")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/planner/routes/patrol")
        self.assertEqual(request.method, "DELETE")

    @patch("shepherd_sdk.transport.urlopen")
    def test_route_load_saved(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True, "relocate_map": "map1", "queue": [{"name": "wp0"}]})
        result = self.client.route.load_saved("patrol")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/planner/routes/patrol/load")
        self.assertEqual(request.method, "POST")
        self.assertEqual(result["relocate_map"], "map1")


    # --- Chunk 4: obstacle avoidance ---

    @patch("shepherd_sdk.transport.urlopen")
    def test_obstacle_avoid_get(self, urlopen):
        urlopen.return_value = FakeResponse({"available": True, "enabled": False})
        result = self.client.obstacle_avoid()
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/obstacle_avoid")
        self.assertEqual(request.method, "GET")
        self.assertEqual(result, {"available": True, "enabled": False})

    @patch("shepherd_sdk.transport.urlopen")
    def test_obstacle_avoid_set(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True, "enable": True})
        self.client.set_obstacle_avoid(True)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/obstacle_avoid")
        self.assertEqual(request.method, "POST")
        self.assertEqual(json.loads(request.data), {"enable": True})


    # --- Chunk 5: VUI light ---

    @patch("shepherd_sdk.transport.urlopen")
    def test_vui_light_get(self, urlopen):
        urlopen.return_value = FakeResponse({"available": True, "level": 4})
        result = self.client.vui_light()
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/vui/light")
        self.assertEqual(request.method, "GET")
        self.assertEqual(result["level"], 4)

    @patch("shepherd_sdk.transport.urlopen")
    def test_vui_light_set(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True, "level": 7})
        self.client.set_vui_light(7)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/vui/light")
        self.assertEqual(request.method, "POST")
        self.assertEqual(json.loads(request.data), {"level": 7})


    # --- Chunk 6: safety/lifecycle (low_battery surfacing, restart_server) ---

    @patch("shepherd_sdk.transport.urlopen")
    def test_low_battery_true(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True, "low_battery": True})
        self.assertTrue(self.client.low_battery())
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/health")

    @patch("shepherd_sdk.transport.urlopen")
    def test_low_battery_false_when_absent(self, urlopen):
        # health() predates this field on older shep versions — must not KeyError.
        urlopen.return_value = FakeResponse({"ok": True})
        self.assertFalse(self.client.low_battery())

    @patch("shepherd_sdk.transport.urlopen")
    def test_restart_server(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        result = self.client.restart_server()
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/api/v1/server/restart")
        self.assertEqual(request.method, "POST")
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()

