"""Loopback-only HTTP boundary for the optional stdlib PyFAST interface."""

from __future__ import annotations

import argparse
import hmac
import json
import sys
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from .app import BusyError, WebApplication
from .config import MAX_REQUEST_BYTES, SCIENTIFIC_STATUS, examples, parse_request, strict_object
from .ui import page


class PyFASTHTTPServer(ThreadingHTTPServer):
    """Local development server; it does not expose the filesystem as static content."""

    daemon_threads = True
    request_queue_size = 8

    def __init__(self, application: WebApplication, port: int) -> None:
        self.application = application
        super().__init__(("127.0.0.1", port), RequestHandler)
        application.port = self.server_port

    def server_close(self) -> None:
        self.application.close()
        super().server_close()


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "PyFAST-local"
    sys_version = ""

    @property
    def application(self) -> WebApplication:
        return cast(PyFASTHTTPServer, self.server).application

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, format: str, *args: Any) -> None:
        """Do not log tokens, arbitrary URL contents or control characters."""

    def _send(self, status: int, payload: bytes, kind: str, filename: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        nonce = self.application.nonce
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; "
            f"script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; "
            "connect-src 'self'; img-src 'self' blob:; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'self'; object-src 'none'",
        )
        self.send_header("Connection", "close")
        if filename is not None:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(payload)
        self.close_connection = True

    def _json(self, status: int, data: object) -> None:
        self._send(
            status,
            json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _security(self, *, token: bool, mutation: bool = False) -> bool:
        hosts = self.headers.get_all("Host", [])
        allowed = {f"127.0.0.1:{self.application.port}", f"localhost:{self.application.port}"}
        if len(hosts) != 1 or hosts[0].lower() not in allowed:
            self._json(403, {"error": "Only the exact local Host is accepted"})
            return False
        origins = self.headers.get_all("Origin", [])
        if len(origins) > 1 or (mutation and not origins):
            self._json(403, {"error": "A same-origin request is required"})
            return False
        if origins and origins[0] != f"http://{hosts[0].lower()}":
            self._json(403, {"error": "Cross-origin requests are not accepted"})
            return False
        tokens = self.headers.get_all("X-PyFAST-Token", [])
        if token and (
            len(tokens) != 1
            or len(tokens[0]) > 200
            or not tokens[0].isascii()
            or not hmac.compare_digest(tokens[0], self.application.token)
        ):
            self._json(403, {"error": "Invalid local session token"})
            return False
        return True

    def _path(self) -> str:
        parsed = urlsplit(self.path)
        if (
            not self.path.startswith("/")
            or parsed.scheme
            or parsed.netloc
            or parsed.query
            or parsed.fragment
            or len(parsed.path) > 2048
        ):
            raise ValueError("Only local paths without query parameters are accepted")
        return parsed.path

    def do_GET(self) -> None:
        try:
            path = self._path()
            if not self._security(token=path != "/"):
                return
            if path == "/":
                self._send(
                    200,
                    page(self.application.token, self.application.nonce),
                    "text/html; charset=utf-8",
                )
            elif path == "/api/info":
                self._json(
                    200,
                    {
                        "scientific_status": SCIENTIFIC_STATUS,
                        "job_timeout_s": self.application.job_timeout_s,
                        "units": "SI; dry adsorbent basis",
                        "limits": {
                            "request_bytes": MAX_REQUEST_BYTES,
                            "axial_cells": 64,
                            "radial_cells": 12,
                            "samples": 401,
                            "active_jobs": 1,
                        },
                    },
                )
            elif path == "/api/examples":
                self._json(200, {"examples": examples()})
            elif path == "/api/jobs":
                self._json(200, {"jobs": self.application.jobs()})
            else:
                parts = path.strip("/").split("/")
                if len(parts) == 3 and parts[:2] == ["api", "jobs"]:
                    self._json(200, self.application.get(parts[2]))
                elif len(parts) == 5 and parts[:2] == ["api", "jobs"] and parts[3] == "files":
                    data = self.application.download(parts[2], parts[4])
                    kind = (
                        "application/json"
                        if parts[4].endswith(".json")
                        else "text/csv"
                        if parts[4].endswith(".csv")
                        else "text/plain"
                    )
                    self._send(200, data, kind + "; charset=utf-8", parts[2] + "_" + parts[4])
                else:
                    self._json(404, {"error": "Unknown local endpoint"})
        except (KeyError, FileNotFoundError):
            self._json(404, {"error": "Unknown job or unavailable file"})
        except (ValueError, UnicodeError):
            self._json(400, {"error": "Invalid local request"})
        except OSError:
            self._json(500, {"error": "Local output could not be read"})

    def do_POST(self) -> None:
        if not self._security(token=True, mutation=True):
            return
        try:
            path = self._path()
            if path not in {"/api/validate", "/api/jobs"}:
                self._json(404, {"error": "Unknown local endpoint"})
                return
            if self.headers.get("Transfer-Encoding") is not None:
                self._json(400, {"error": "Transfer-Encoding is not supported"})
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].lower() != "application/json":
                self._json(415, {"error": "Content-Type must be application/json"})
                return
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1:
                self._json(411, {"error": "One Content-Length header is required"})
                return
            length = int(lengths[0])
            if not 0 < length <= MAX_REQUEST_BYTES:
                self._json(413, {"error": "Request exceeds the 64 KiB local limit"})
                return
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("Incomplete request body")
            spec = parse_request(strict_object(raw.decode("utf-8")))
            if path == "/api/validate":
                self._json(
                    200,
                    {
                        "ok": True,
                        "reactor": spec.reactor,
                        "config_sha256": spec.config_sha256,
                        "canonical_config_json": spec.config_json,
                        "solver_options": asdict(spec.options),
                        "scientific_status": SCIENTIFIC_STATUS,
                    },
                )
            else:
                self._json(202, self.application.submit(spec))
        except BusyError as exc:
            self._json(429, {"error": str(exc)})
        except (ValueError, UnicodeError, RecursionError) as exc:
            self._json(400, {"error": str(exc)[:600]})
        except OSError:
            self._json(500, {"error": "Local run directory could not be created"})

    def do_OPTIONS(self) -> None:
        self._json(405, {"error": "Only local GET and POST endpoints are supported"})


def create_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    output: str | Path = "runs/gui",
    job_timeout_s: float = 30,
) -> PyFASTHTTPServer:
    """Build a server without starting its request loop; port=0 supports isolated tests."""
    if host not in ("127.0.0.1", "localhost"):
        raise ValueError("The local GUI binds only to 127.0.0.1 (or localhost)")
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("port must be an integer within [0,65535]")
    return PyFASTHTTPServer(WebApplication(output, job_timeout_s=job_timeout_s), port)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="PyFAST local scientific interface (not production)"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--output", type=Path, default=Path("runs/gui"))
    args = parser.parse_args(argv)
    try:
        with create_server(host=args.host, port=args.port, output=args.output) as server:
            print(f"PyFAST local: http://127.0.0.1:{server.server_port}", flush=True)
            print(SCIENTIFIC_STATUS, flush=True)
            print("Press Ctrl+C to close this GUI and its own running job.", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    except (OSError, ValueError) as exc:
        print(f"PyFAST web error: {exc}", file=sys.stderr)
        return 2
    return 0
