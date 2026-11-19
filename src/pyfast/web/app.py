"""Bounded local jobs, with an isolated process per simulation and immutable outputs."""

from __future__ import annotations

import json
import multiprocessing
import re
import secrets
import stat
import threading
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from multiprocessing.process import BaseProcess
from multiprocessing.queues import Queue
from pathlib import Path
from queue import Empty
from typing import Any, Literal
from uuid import uuid4

import numpy as np

from ..io import export_result
from ..schemas import BatchConfig, SimulationConfig
from ..simulate import batch, column
from .config import MAX_JOBS, SCIENTIFIC_STATUS, RequestSpec

_JOB_ID = re.compile(r"[0-9a-f]{32}\Z")
_FILES = {
    "result.json": "results/result.json",
    "timeseries.csv": "results/timeseries.csv",
    "files.sha256.json": "results/files.sha256.json",
    "input.json": "job_input.json",
    "summary.json": "web_summary.json",
    "job.log": "job.log",
}
_RESULT_FILES = {"result.json", "timeseries.csv", "files.sha256.json"}


class BusyError(RuntimeError):
    """The local UI's concurrency or session limit has been reached."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def guarded_output_root(path: str | Path) -> Path:
    """Reject protected names and reparse points before creating any run directories."""
    absolute = Path(path).absolute()
    protected = {".git", "src", "datasets_benchmark_pyfast"}
    if any(part.casefold() in protected for part in absolute.parts):
        raise ValueError("GUI outputs must be outside src, .git and raw dataset directories")
    for candidate in (absolute, *absolute.parents):
        if candidate.is_symlink():
            raise ValueError("Linked output paths are not supported")
        if candidate.exists():
            attributes = getattr(candidate.lstat(), "st_file_attributes", 0)
            if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise ValueError("Reparse-point output paths are not supported")
    if absolute.exists() and not absolute.is_dir():
        raise ValueError("Output root must be a directory")
    return absolute.resolve()


def _worker(spec: RequestSpec, job_folder: str, channel: Queue[dict[str, Any]]) -> None:
    """Only package APIs and validated data are invoked; never shell commands or user code."""
    try:
        times = np.linspace(0, spec.duration_s, spec.samples)
        if spec.reactor == "batch":
            result = batch(
                BatchConfig.from_json(spec.config_json), time_s=times, options=spec.options
            )
        else:
            result = column(
                SimulationConfig.from_json(spec.config_json), time_s=times, options=spec.options
            )
        folder = guarded_output_root(Path(job_folder).parent) / Path(job_folder).name
        if folder.is_symlink() or folder.resolve().parent != guarded_output_root(folder.parent):
            raise ValueError("Invalid job output directory")
        export_result(result, folder / "results")
        channel.put(
            {
                "ok": True,
                "numerical_sha256": result.numerical_sha256,
                "preview": {
                    "time_s": result.time_s.tolist(),
                    "outlet_concentration_kg_m3": result.outlet_concentration_kg_m3.tolist(),
                },
                "diagnostics": asdict(result.diagnostics),
            }
        )
    except Exception as exc:
        channel.put({"ok": False, "error": str(exc)[:600], "trace": traceback.format_exc()[-6000:]})


@dataclass(slots=True)
class Job:
    id: str
    reactor: str
    config_sha256: str
    created_utc: str
    status: Literal["queued", "running", "succeeded", "failed", "timed_out"] = "queued"
    finished_utc: str | None = None
    numerical_sha256: str | None = None
    error: str | None = None
    preview: dict[str, Any] | None = None
    diagnostics: dict[str, Any] | None = None


class WebApplication:
    """One active simulation and at most 50 retained job records per server session.

    A worker has a hard wall-clock limit. Only that UI-owned process is terminated
    on timeout/shutdown; no process discovery or intervention in other simulations.
    This is a local application, not a multi-user production service.
    """

    def __init__(self, output_root: str | Path, *, job_timeout_s: float = 30.0) -> None:
        if isinstance(job_timeout_s, bool) or not 0 < job_timeout_s <= 120:
            raise ValueError("job_timeout_s must lie within (0,120]")
        self.output_root = guarded_output_root(output_root)
        self.job_timeout_s = float(job_timeout_s)
        self.token = secrets.token_urlsafe(32)
        self.nonce = secrets.token_urlsafe(24)
        self.port = 0
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._active = False
        self._closed = False
        self._process: BaseProcess | None = None
        self._thread: threading.Thread | None = None

    def submit(self, spec: RequestSpec) -> dict[str, Any]:
        with self._lock:
            if self._closed or self._active or len(self._jobs) >= MAX_JOBS:
                raise BusyError("One simulation at a time; maximum 50 jobs per session")
            root = guarded_output_root(self.output_root)
            root.mkdir(parents=True, exist_ok=True)
            job = Job(uuid4().hex, spec.reactor, spec.config_sha256, _now())
            folder = root / job.id
            folder.mkdir(exist_ok=False)
            with (folder / "job_input.json").open("x", encoding="utf-8") as stream:
                stream.write(spec.input_json())
            self._jobs[job.id] = job
            self._active = True
            self._thread = threading.Thread(target=self._run, args=(job.id, spec), daemon=True)
            self._thread.start()
            return asdict(job)

    def _run(self, job_id: str, spec: RequestSpec) -> None:
        context = multiprocessing.get_context("spawn")
        channel: Queue[dict[str, Any]] = context.Queue()
        folder = self.output_root / job_id
        process = context.Process(target=_worker, args=(spec, str(folder), channel), daemon=True)
        status: Literal["succeeded", "failed", "timed_out"] = "failed"
        response: dict[str, Any] = {}
        log = ""
        try:
            with self._lock:
                if self._closed:
                    raise RuntimeError("Local server closed before simulation started")
                self._jobs[job_id].status = "running"
                self._process = process
                process.start()
            deadline = time.monotonic() + self.job_timeout_s
            received = False
            # Drain the queue before join: a child's feeder may otherwise block its
            # exit when the preview exceeds the OS pipe buffer (notably on Linux).
            while time.monotonic() < deadline:
                try:
                    response = channel.get(timeout=min(0.25, deadline - time.monotonic()))
                    received = True
                    break
                except Empty:
                    if not process.is_alive():
                        raise RuntimeError(
                            f"Simulation worker exited without a result ({process.exitcode})"
                        ) from None
            if received:
                process.join(max(0, deadline - time.monotonic()))
                if response.get("ok") is True:
                    status = "succeeded"
            if not received or process.is_alive():
                process.terminate()
                process.join(5)
                status = "timed_out"
                response = {"error": "Simulation exceeded the local GUI wall-clock limit"}
            log = (
                "Numerical simulation completed. "
                if status == "succeeded"
                else "Simulation failed. "
            )
            log += SCIENTIFIC_STATUS + "\n" + str(response.get("trace", response.get("error", "")))
        except Exception as exc:
            response = {"error": str(exc)[:600]}
            log = traceback.format_exc()
        finally:
            with self._lock:
                self._process = None
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                    process.join(5)
                process.close()
            channel.close()
            try:
                guarded_output_root(folder)
                with (folder / "job.log").open("x", encoding="utf-8") as stream:
                    stream.write(log)
                summary = {
                    "id": job_id,
                    "status": status,
                    "scientific_status": SCIENTIFIC_STATUS,
                    "config_sha256": spec.config_sha256,
                    "numerical_sha256": response.get("numerical_sha256"),
                    "error": response.get("error"),
                    "diagnostics": response.get("diagnostics"),
                }
                with (folder / "web_summary.json").open("x", encoding="utf-8") as stream:
                    json.dump(summary, stream, ensure_ascii=False, allow_nan=False, indent=2)
            except (OSError, ValueError) as exc:
                status = "failed"
                response["error"] = f"Could not persist local job record: {type(exc).__name__}"
            with self._lock:
                job = self._jobs[job_id]
                job.status, job.finished_utc = status, _now()
                job.error = response.get("error")
                job.preview, job.diagnostics = response.get("preview"), response.get("diagnostics")
                job.numerical_sha256 = response.get("numerical_sha256")
                self._process = None
                self._active = False

    def get(self, job_id: str) -> dict[str, Any]:
        if _JOB_ID.fullmatch(job_id) is None:
            raise KeyError("Unknown job")
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError("Unknown job")
            return asdict(self._jobs[job_id])

    def jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": job.id,
                    "status": job.status,
                    "reactor": job.reactor,
                    "created_utc": job.created_utc,
                }
                for job in reversed(list(self._jobs.values()))
            ]

    def download(self, job_id: str, name: str) -> bytes:
        job = self.get(job_id)
        if name not in _FILES or (name in _RESULT_FILES and job["status"] != "succeeded"):
            raise KeyError("File is not available")
        folder = guarded_output_root(self.output_root / job_id)
        file = folder / _FILES[name]
        guarded_output_root(file.parent)
        if file.is_symlink() or not file.is_file() or file.stat().st_size > 10 * 1024 * 1024:
            raise KeyError("File is not available")
        if getattr(file.lstat(), "st_file_attributes", 0) & 0x400:
            raise KeyError("Linked files are not available")
        data = file.read_bytes()
        if len(data) > 10 * 1024 * 1024:
            raise KeyError("File exceeds local download limit")
        return data

    def close(self) -> None:
        with self._lock:
            self._closed = True
            process, thread = self._process, self._thread
            if process is not None and process.is_alive():
                process.terminate()
        if thread is not None:
            thread.join(7)
