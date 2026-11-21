import io
import json
import socket
import threading
import time
from dataclasses import dataclass
from email.message import Message
from http import HTTPStatus
from http.client import HTTPResponse
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import pytest

import pyfast.web.server as web_server
from pyfast.web import create_server
from pyfast.web.app import guarded_output_root
from pyfast.web.config import MAX_REQUEST_BYTES, examples, parse_request, strict_object
from pyfast.web.server import PyFASTHTTPServer, RequestHandler, main


class DrainConnection:
    def __init__(self):
        self.timeout = 5

    def gettimeout(self):
        return self.timeout

    def settimeout(self, timeout):
        self.timeout = timeout


@pytest.mark.parametrize(
    "framing,expected",
    [
        ({"Content-Length": "4"}, 4),
        ({"Content-Length": str(MAX_REQUEST_BYTES + 1)}, MAX_REQUEST_BYTES + 1),
        ({"Content-Length": str(2 * MAX_REQUEST_BYTES)}, 2 * MAX_REQUEST_BYTES),
        ({"Content-Length": str(2 * MAX_REQUEST_BYTES + 1)}, 0),
        ({"Content-Length": "bad"}, 0),
        ({"Content-Length": "-1"}, 0),
        ({"Content-Length": "4", "Transfer-Encoding": "chunked"}, 0),
        ({}, 0),
    ],
)
def test_rejected_post_drain_trusts_only_bounded_framing(framing, expected):
    handler = RequestHandler.__new__(RequestHandler)
    handler.headers = Message()
    for key, value in framing.items():
        handler.headers[key] = value
    body = b"x" * expected if expected > 4 else b"body"
    handler.rfile = io.BytesIO(body + b"trailing")
    handler.connection = DrainConnection()
    handler._discard_rejected_body()
    assert handler.rfile.tell() == expected
    assert handler.connection.timeout == 5
    handler._discard_rejected_body()
    assert handler.rfile.tell() == expected  # An error response never drains twice.


def test_rejected_post_drain_does_not_read_duplicate_or_consumed_body():
    handler = RequestHandler.__new__(RequestHandler)
    handler.headers = Message()
    handler.headers["Content-Length"] = "4"
    handler.headers["Content-Length"] = "4"
    handler.rfile = io.BytesIO(b"body")
    handler.connection = DrainConnection()
    handler._discard_rejected_body()
    assert handler.rfile.tell() == 0
    del handler.headers["Content-Length"]
    handler.headers["Content-Length"] = "4"
    handler._discard_rejected_body()
    assert handler.rfile.tell() == 0


def test_rejected_post_drain_has_total_deadline_for_fragmented_input(monkeypatch):
    class FragmentedBody(io.BytesIO):
        def read1(self, size):
            assert size <= 8192
            return super().read1(1)

    handler = RequestHandler.__new__(RequestHandler)
    handler.headers = Message()
    handler.headers["Content-Length"] = "4"
    handler.connection = DrainConnection()
    handler.rfile = FragmentedBody(b"body")
    ticks = iter((0.0, 0.1, 0.6))
    monkeypatch.setattr(web_server, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    handler._discard_rejected_body()
    assert handler.rfile.tell() == 1
    assert handler.connection.timeout == 5


def test_rejected_post_drain_restores_timeout_after_read_error():
    class FailedBody(io.BytesIO):
        def read1(self, size):
            raise TimeoutError("fragment did not arrive")

    handler = RequestHandler.__new__(RequestHandler)
    handler.headers = Message()
    handler.headers["Content-Length"] = "4"
    handler.connection = DrainConnection()
    handler.rfile = FailedBody()
    handler._discard_rejected_body()
    assert handler.connection.timeout == 5
    assert handler._post_body_started


def test_fragmented_unauthorized_post_returns_403_after_bounded_discard(client):
    body = b"x" * 128
    with socket.create_connection(
        ("127.0.0.1", client.server.server_port), timeout=8
    ) as connection:
        headers = (
            "POST /api/validate HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{client.server.server_port}\r\n"
            "Origin: https://other.example\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n\r\n"
        ).encode("ascii")
        connection.sendall(headers + body[:1])
        connection.settimeout(0.05)
        with pytest.raises(TimeoutError):
            connection.recv(1)
        connection.sendall(body[1:])
        connection.settimeout(8)
        response = HTTPResponse(connection)
        response.begin()
        assert response.status == 403
        assert "Cross-origin" in json.loads(response.read())["error"]
    assert not client.output.exists()


@dataclass
class Client:
    server: PyFASTHTTPServer
    output: Path

    @property
    def base(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def call(self, path, body=None, *, headers=None, raw=None):
        supplied = {"X-PyFAST-Token": self.server.application.token}
        data = raw
        if body is not None or raw is not None:
            supplied |= {"Origin": self.base, "Content-Type": "application/json"}
            if body is not None:
                data = json.dumps(body).encode()
        if headers:
            supplied |= headers
        request = Request(self.base + path, data=data, headers=supplied)
        opener = build_opener(ProxyHandler({}))
        try:
            response = opener.open(request, timeout=8)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, response.headers, response.read()

    def json(self, path, body=None, **kwargs):
        status, headers, raw = self.call(path, body, **kwargs)
        return status, headers, json.loads(raw)


@pytest.fixture
def client(tmp_path):
    output = tmp_path / "gui_outputs"
    server = create_server(port=0, output=output, job_timeout_s=15)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield Client(server, output)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)


def request_for(example="batch_linear", **changes):
    selected = next(item for item in examples() if item["id"] == example)
    return {
        "reactor": selected["reactor"],
        "config_json": selected["config_json"],
        "samples": 31,
        "options": {"axial_cells": 8, "radial_cells": 4},
    } | changes


def wait_for_job(client, job_id, seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        status, _, job = client.json(f"/api/jobs/{job_id}")
        assert status == 200
        if job["status"] not in {"queued", "running"}:
            return job
        time.sleep(0.05)
    pytest.fail("Local GUI job did not finish within the test deadline")


def test_home_has_local_assets_csp_and_scientific_status(client):
    code, headers, page = client.call("/")
    assert code == 200
    text = page.decode()
    assert "Sin validación experimental" in text
    assert "__TOKEN__" not in text
    assert client.server.application.token in text
    assert "textContent" in text and "innerHTML" not in text
    assert "<script src=" not in text and "https://" not in text
    assert "unsafe-inline" not in headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Cache-Control"] == "no-store"
    assert not client.output.exists()


def test_examples_and_read_only_validation(client):
    status, _, data = client.json("/api/examples")
    assert status == 200
    assert {x["id"] for x in data["examples"]} == {"batch_linear", "column_ldf", "column_hsdm"}
    for example in data["examples"]:
        status, _, validation = client.json("/api/validate", request_for(example["id"]))
        assert status == 200
        assert validation["ok"]
        assert len(validation["config_sha256"]) == 64
        assert "sin validación experimental" in validation["scientific_status"]
    assert not client.output.exists()


@pytest.mark.parametrize(
    "extra",
    [
        {"output": "../../datasets_benchmark_pyfast"},
        {"options": {"axial_cells": 65}},
        {"options": {"radial_cells": 13}},
        {"options": {"max_step_s": 1e-20}},
        {"options": {"rtol": 1e-15}},
        {"samples": 402},
        {"samples": True},
        {"reactor": "shell"},
    ],
)
def test_bad_web_requests_fail_without_writes(client, extra):
    code, _, data = client.json("/api/validate", request_for(**extra))
    assert code == 400
    assert "error" in data
    assert not client.output.exists()


def test_duplicate_keys_nonfinite_units_and_unknown_config_are_rejected(client):
    normal = request_for()
    raw = b'{"reactor":"batch","reactor":"column","config_json":"{}"}'
    assert client.json("/api/validate", raw=raw)[0] == 400
    duplicate = normal["config_json"].replace(
        '"schema_version":1', '"schema_version":1,"schema_version":1'
    )
    assert duplicate != normal["config_json"]
    assert client.json("/api/validate", normal | {"config_json": duplicate})[0] == 400
    physical = json.loads(normal["config_json"])
    physical["duration_s"] = "300 s"
    assert client.json("/api/validate", normal | {"config_json": json.dumps(physical)})[0] == 400
    assert client.json("/api/validate", raw=b'{"reactor":NaN}')[0] == 400
    with pytest.raises(ValueError):
        strict_object("[]")
    assert not client.output.exists()


@pytest.mark.parametrize(
    "headers",
    [
        {"X-PyFAST-Token": "wrong"},
        {"X-PyFAST-Token": "é"},
        {"Origin": "https://other.example"},
        {"Origin": "null"},
        {"Host": "other.example"},
    ],
)
def test_post_requires_local_host_origin_and_token(client, headers):
    assert client.json("/api/validate", request_for(), headers=headers)[0] == 403
    assert not client.output.exists()


def test_origin_is_required_and_large_body_rejected(client):
    # Empty Origin is different from the exact browser origin and must be rejected.
    assert client.json("/api/validate", request_for(), headers={"Origin": ""})[0] == 403
    assert client.json("/api/validate", raw=b"a" * (MAX_REQUEST_BYTES + 1))[0] == 413
    assert (
        client.json("/api/validate", request_for(), headers={"Content-Type": "text/plain"})[0]
        == 415
    )
    assert client.json("/api/info", headers={"X-PyFAST-Token": ""})[0] == 403
    assert not client.output.exists()


def test_completed_batch_max_preview_payload_and_downloads(client):
    code, _, started = client.json("/api/jobs", request_for(samples=401))
    assert code == HTTPStatus.ACCEPTED
    job = wait_for_job(client, started["id"])
    assert job["status"] == "succeeded", job.get("error")
    assert len(job["preview"]["time_s"]) == 401
    assert job["diagnostics"]["max_scaled_mass_residual"] < 1e-6
    code, headers, raw = client.call(f"/api/jobs/{job['id']}/files/result.json")
    assert code == 200 and "attachment" in headers["Content-Disposition"]
    report = json.loads(raw)
    assert report["experimental_validation"] == "not_performed"
    assert report["config"]["material"] == "Adsorbente sintético"
    code, _, csv = client.call(f"/api/jobs/{job['id']}/files/timeseries.csv")
    assert code == 200 and b"outlet_concentration_kg_m3" in csv
    assert client.json(f"/api/jobs/{job['id']}/files/summary.json")[2]["status"] == "succeeded"
    assert client.call(f"/api/jobs/{job['id']}/files/job.log")[0] == 200
    assert client.call(f"/api/jobs/{job['id']}/files/%2e%2e%2fREADME.md")[0] == 404
    assert client.json("/api/jobs/../../datasets_benchmark_pyfast")[0] == 404
    assert client.json("/api/jobs")[2]["jobs"][0]["id"] == job["id"]


def test_column_uses_existing_solver_and_unique_run_folders(client):
    first = client.json("/api/jobs", request_for("column_ldf", samples=5))[2]
    assert wait_for_job(client, first["id"])["status"] == "succeeded"
    second = client.json("/api/jobs", request_for("column_ldf", samples=5))[2]
    assert wait_for_job(client, second["id"])["status"] == "succeeded"
    assert first["id"] != second["id"]
    assert len(list(client.output.iterdir())) == 2


def test_concurrency_guard_and_timeout_are_explicit(client):
    with client.server.application._lock:
        client.server.application._active = True
    try:
        assert client.json("/api/jobs", request_for())[0] == 429
    finally:
        with client.server.application._lock:
            client.server.application._active = False
    assert not client.output.exists()
    client.server.application.job_timeout_s = 0.001
    created = client.json("/api/jobs", request_for())[2]
    failed = wait_for_job(client, created["id"])
    assert failed["status"] == "timed_out"
    assert client.call(f"/api/jobs/{failed['id']}/files/result.json")[0] == 404
    assert client.call(f"/api/jobs/{failed['id']}/files/job.log")[0] == 200


def test_no_raw_mutation_or_arbitrary_path_routes(client, tmp_path):
    protected = tmp_path / "datasets_benchmark_pyfast"
    protected.mkdir()
    sentinel = protected / "raw.csv"
    sentinel.write_bytes(b"unaltered external measurement")
    assert client.call("/datasets_benchmark_pyfast/raw.csv")[0] == 404
    assert client.json("/api/validate", request_for() | {"path": str(sentinel)})[0] == 400
    assert sentinel.read_bytes() == b"unaltered external measurement"
    with pytest.raises(ValueError):
        guarded_output_root(protected / "gui")


def test_non_loopback_startup_and_invalid_config_limits(tmp_path):
    with pytest.raises(ValueError, match="127.0.0.1"):
        create_server(host="0.0.0.0", port=0, output=tmp_path / "new")
    with pytest.raises(ValueError):
        create_server(port=True, output=tmp_path / "new")
    assert not (tmp_path / "new").exists()
    assert main(["--host", "0.0.0.0", "--output", str(tmp_path / "new")]) == 2
    payload = request_for()
    config = json.loads(payload["config_json"])
    config["duration_s"] = 172801
    with pytest.raises(ValueError, match="duration_s"):
        parse_request(payload | {"config_json": json.dumps(config)})
