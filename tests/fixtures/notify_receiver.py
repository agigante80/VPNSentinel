"""Test-only HTTP receiver for the Apprise delivery E2E (issue #143).

Endpoints:
  POST /hook      record the body (UTF-8) and answer 200
  POST /hang      read the body, then hold the connection without answering
  GET  /messages  200 application/json {"hook": [<body>, ...]} in arrival order
  GET  /health    200 ok

The server class MUST be threaded: with the single-threaded HTTPServer one open
/hang request holds the only thread and /hook is starved.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer

HANG_SECONDS = 600


class _Handler(BaseHTTPRequestHandler):
    def _reply(self, code, body, ctype="text/plain"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length).decode("utf-8", errors="replace") if length else ""

    def do_POST(self):  # noqa: N802 (http.server naming)
        body = self._read_body()
        if self.path == "/hook":
            with self.server.records_lock:
                self.server.records.append(body)
            self._reply(200, "ok")
        elif self.path == "/hang":
            # Released by server.stop_event (tests) or after HANG_SECONDS.
            self.server.stop_event.wait(HANG_SECONDS)
        else:
            self._reply(404, "not found")

    def do_GET(self):  # noqa: N802
        if self.path == "/messages":
            with self.server.records_lock:
                payload = {"hook": list(self.server.records)}
            self._reply(200, json.dumps(payload), "application/json")
        elif self.path == "/health":
            self._reply(200, "ok")
        else:
            self._reply(404, "not found")

    def log_message(self, fmt, *args):  # keep container logs quiet
        pass


def make_server(host, port, server_cls=ThreadingHTTPServer):
    """Build a receiver. `stop_event` releases any open /hang request."""
    server = server_cls((host, port), _Handler)
    server.daemon_threads = True
    server.records = []
    server.records_lock = threading.Lock()
    server.stop_event = threading.Event()
    return server


__all__ = ["make_server", "HTTPServer", "ThreadingHTTPServer"]

if __name__ == "__main__":
    make_server("0.0.0.0", 8099).serve_forever()
