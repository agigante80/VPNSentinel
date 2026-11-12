"""Receiver unit test and negative control (issue #143)."""

import os
import socket
import sys
import threading
from http.server import HTTPServer, ThreadingHTTPServer

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "fixtures"))
import notify_receiver  # noqa: E402


@pytest.fixture
def start_server():
    started = []

    def _start(server_cls=ThreadingHTTPServer):
        server = notify_receiver.make_server("127.0.0.1", 0, server_cls)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        started.append((server, thread))
        return server

    yield _start
    for server, _ in started:
        # Release open /hang handlers first; never call shutdown() while one is open
        # on the single-threaded server (it would block until the handler returns).
        server.stop_event.set()
    for server, thread in started:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _open_hang(port):
    """Send a POST /hang and leave it unanswered; returns the open socket."""
    sock = socket.create_connection(("127.0.0.1", port), timeout=5)
    sock.sendall(b"POST /hang HTTP/1.1\r\nHost: x\r\nContent-Length: 2\r\n\r\n{}")
    return sock


def test_default_server_class_is_threading():
    server = notify_receiver.make_server("127.0.0.1", 0)
    try:
        assert isinstance(server, ThreadingHTTPServer)
        assert server.daemon_threads is True
    finally:
        server.server_close()


def test_hook_served_while_hang_is_open(start_server):
    server = start_server()
    port = server.server_address[1]
    hang = _open_hang(port)
    try:
        resp = requests.post(f"http://127.0.0.1:{port}/hook", data='{"k":"v"}', timeout=1)
        assert resp.status_code == 200
        msgs = requests.get(f"http://127.0.0.1:{port}/messages", timeout=1)
        assert msgs.headers["Content-Type"] == "application/json"
        assert msgs.json() == {"hook": ['{"k":"v"}']}
        assert requests.get(f"http://127.0.0.1:{port}/health", timeout=1).text == "ok"
    finally:
        hang.close()


def test_single_threaded_server_is_starved_by_hang(start_server):
    """Negative control: with HTTPServer the same /hook request times out."""
    server = start_server(HTTPServer)
    port = server.server_address[1]
    hang = _open_hang(port)
    try:
        # Give the single thread time to enter the /hang handler.
        hang.settimeout(0.5)
        with pytest.raises(requests.exceptions.ReadTimeout):
            requests.post(f"http://127.0.0.1:{port}/hook", data="{}", timeout=2)
    finally:
        server.stop_event.set()
        hang.close()
