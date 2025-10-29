#!/usr/bin/env python3
"""
Tiny dummy TCP server for tests. Listens on a port and accepts one connection then sleeps.
Usage: python3 tests/fixtures/dummy_server.py <port>
"""
import socket
import sys
import time

def run(port: int):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('127.0.0.1', port))
    s.listen(1)
    try:
        while True:
            time.sleep(1)
    finally:
        s.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: dummy_server.py <port>')
        sys.exit(2)
    run(int(sys.argv[1]))
