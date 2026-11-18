"""Serve the fixed fictional scenarios using fresh local Relate queries."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import relate

from trace import DEMO_WRITES, TRACE, trace


PAGE = Path(__file__).with_name("index.html")


def query_step(step):
    with relate.connect(":memory:") as db:
        for statement in DEMO_WRITES[: min(step + 1, len(DEMO_WRITES))]:
            db.execute(statement)
        result = trace(db, "missing" if step == 5 else "share-01")
    return {
        "step": step,
        "engine": f"Relate {version('relate-db')}",
        "data_kind": "fictional",
        "trace": result,
        "query": TRACE.strip(),
    }


class DemoHandler(BaseHTTPRequestHandler):
    def respond(self, status, content, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'",
        )
        self.end_headers()
        self.wfile.write(content)

    def error(self, status, message):
        self.respond(
            status,
            json.dumps({"error": message}).encode(),
            "application/json; charset=utf-8",
        )

    def do_GET(self):
        port = self.server.server_port
        if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            self.error(403, "Use the local demo address.")
            return
        path = urlsplit(self.path)
        if path.path in {"/", "/index.html"} and not path.query:
            self.respond(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            return
        if path.path == "/favicon.ico":
            self.respond(204, b"", "image/x-icon")
            return
        if path.path != "/api/trace":
            self.error(404, "Page not found.")
            return
        args = parse_qs(path.query, keep_blank_values=True)
        if (
            set(args) != {"step"}
            or len(args["step"]) != 1
            or args["step"][0] not in {"0", "1", "2", "3", "4", "5"}
        ):
            self.error(400, "Choose a step from 0 to 5.")
            return
        try:
            result = query_step(int(args["step"][0]))
        except Exception as exc:
            self.log_error("Relate query failed (%s)", type(exc).__name__)
            self.error(500, "Could not query the local graph. Try again.")
            return
        self.respond(200, json.dumps(result).encode(), "application/json; charset=utf-8")

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8768)
    options = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", options.port), DemoHandler) as server:
        print(f"Handoff Record Trail: http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()
