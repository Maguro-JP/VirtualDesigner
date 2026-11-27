"""VirtualDesigner のローカルサーバー。

localhost (127.0.0.1:8770) 専用。現在のディレクトリを配信し、
3 つの対象（アバター・空間・道具）の API を提供する。

- POST /api/avatar?format=svg / /api/space?format=svg / /api/item?format=svg … 描画
- POST /api/validate?target=avatar|space|item … 検証して正規化した仕様を返す
- GET  /api/presets（?target= で対象を絞れる）… プリセット一覧
- GET  /api/random?target=…&seed=… … seed からランダムな仕様を返す
"""

from __future__ import annotations

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import avatar_core
import item_core
import space_core
from vd_common import VDError

HOST = "127.0.0.1"
PORT = 8770
MAX_BODY = 256 * 1024  # 256KB

HERE = os.path.dirname(os.path.abspath(__file__))

CORES = {"avatar": avatar_core, "space": space_core, "item": item_core}
FILENAMES = {"avatar": "avatar.svg", "space": "space.svg", "item": "item.svg"}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def log_message(self, format, *args):  # noqa: A002 - 標準のシグネチャ
        pass

    def _send_json(self, status: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        """リクエスト本文の JSON を読む。失敗したら (None, (status, payload)) を返す。"""
        length = self.headers.get("Content-Length")
        if length is None:
            return None, (400, {"error": "Content-Length が必要です"})
        try:
            size = int(length)
        except ValueError:
            return None, (400, {"error": "Content-Length が不正です"})
        if size > MAX_BODY:
            return None, (413, {"error": "リクエストが大きすぎます（上限 256KB）"})
        if size < 0:
            return None, (400, {"error": "Content-Length が不正です"})
        raw = self.rfile.read(size)
        try:
            return json.loads(raw.decode("utf-8")), None
        except (ValueError, UnicodeDecodeError) as exc:
            return None, (400, {"error": f"JSON が不正です: {exc}"})

    def do_GET(self):  # noqa: N802 - http.server の規約
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/api/presets":
            target = query.get("target", [None])[0]
            if target is not None and target not in CORES:
                self._send_json(400, {"error": f"target が不明です: {target!r}"})
                return
            payload = {name: core.PRESETS for name, core in CORES.items()
                       if target is None or name == target}
            self._send_json(200, payload)
            return
        if parsed.path == "/api/random":
            target = query.get("target", ["avatar"])[0]
            if target not in CORES:
                self._send_json(400, {"error": f"target が不明です: {target!r}"})
                return
            seed_raw = query.get("seed", ["0"])[0]
            try:
                seed = int(seed_raw)
            except ValueError:
                seed = seed_raw
            self._send_json(200, CORES[target].random_spec(seed))
            return
        super().do_GET()

    def do_POST(self):  # noqa: N802 - http.server の規約
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        render_target = None
        for name in CORES:
            if parsed.path == f"/api/{name}":
                render_target = name
        if render_target is not None:
            if query.get("format", [""])[0] != "svg":
                self._send_json(400, {"error": "format=svg が必要です"})
                return
            data, error = self._read_json_body()
            if error is not None:
                self._send_json(*error)
                return
            try:
                core = CORES[render_target]
                svg = core.build_svg(core.validate_spec(data))
            except VDError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            body = svg.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
            self.send_header("Content-Disposition",
                             f'attachment; filename="{FILENAMES[render_target]}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/validate":
            target = query.get("target", [""])[0]
            if target not in CORES:
                self._send_json(400, {"error": "target=avatar|space|item が必要です"})
                return
            data, error = self._read_json_body()
            if error is not None:
                self._send_json(*error)
                return
            try:
                spec = CORES[target].validate_spec(data)
            except VDError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, spec)
            return

        self._send_json(404, {"error": "not found"})


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"VirtualDesigner: http://{HOST}:{PORT}/", flush=True)
    print("終了するには Ctrl+C を押してください。", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
