#!/usr/bin/env python3
"""启动 AIGUI Builder 本地静态服务。"""

from __future__ import annotations

import argparse
import functools
import http.server
import os
import socketserver
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 8000


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=str(directory or ROOT), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def end_headers(self) -> None:
        # 方便本地开发时避免缓存旧 JS
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def find_free_port(host: str, start: int, attempts: int = 20) -> int:
    import socket

    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"无法在 {start}-{start + attempts - 1} 找到可用端口")


def main() -> int:
    parser = argparse.ArgumentParser(description="启动 AIGUI Builder")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    os.chdir(ROOT)
    port = find_free_port(args.host, args.port)
    handler = functools.partial(QuietHandler, directory=ROOT)

    with socketserver.ThreadingTCPServer((args.host, port), handler) as httpd:
        httpd.allow_reuse_address = True
        url = f"http://{args.host}:{port}/"
        print("=" * 48)
        print(" AIGUI Builder")
        print(f" 目录: {ROOT}")
        print(f" 地址: {url}")
        print(f" 预览: {url}preview.html")
        print(" 按 Ctrl+C 停止")
        print("=" * 48)

        if not args.no_browser:
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止。")
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
