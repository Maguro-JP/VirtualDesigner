"""server.py のスモークテスト。エフェメラルポートで起動し、各 API を実際に叩く。"""

import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

import server


class ServerSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def request(self, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = json.dumps(body) if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        conn.request(method, path, body=payload, headers=headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, res.getheader("Content-Type"), data

    def test_render_each_target(self):
        for target in ("avatar", "space", "item"):
            with self.subTest(target=target):
                status, ctype, data = self.request("POST", f"/api/{target}?format=svg", {})
                self.assertEqual(status, 200)
                self.assertIn("image/svg+xml", ctype)
                self.assertIn(b"<svg", data)

    def test_render_requires_format_and_valid_spec(self):
        status, _, _ = self.request("POST", "/api/avatar", {})
        self.assertEqual(status, 400)
        status, _, data = self.request("POST", "/api/avatar?format=svg", {"face_shape": "star"})
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(data))

    def test_validate_endpoint(self):
        status, _, data = self.request("POST", "/api/validate?target=space",
                                       {"wall_color": "#AABBCC"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["wall_color"], "#aabbcc")
        status, _, _ = self.request("POST", "/api/validate?target=space", {"door": "wide"})
        self.assertEqual(status, 400)
        status, _, _ = self.request("POST", "/api/validate", {})
        self.assertEqual(status, 400)

    def test_presets_endpoint(self):
        status, _, data = self.request("GET", "/api/presets")
        self.assertEqual(status, 200)
        payload = json.loads(data)
        self.assertEqual(set(payload), {"avatar", "space", "item"})
        self.assertGreaterEqual(len(payload["avatar"]), 6)
        status, _, data = self.request("GET", "/api/presets?target=item")
        self.assertEqual(set(json.loads(data)), {"item"})
        status, _, _ = self.request("GET", "/api/presets?target=nope")
        self.assertEqual(status, 400)

    def test_random_endpoint(self):
        status, _, data = self.request("GET", "/api/random?target=avatar&seed=7")
        self.assertEqual(status, 200)
        spec = json.loads(data)
        self.assertEqual(spec["format"], "virtualdesigner.avatar.v1")
        _, _, data2 = self.request("GET", "/api/random?target=avatar&seed=7")
        self.assertEqual(json.loads(data2), spec)

    def test_index_served(self):
        status, _, data = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("VirtualDesigner".encode(), data)


if __name__ == "__main__":
    unittest.main()
