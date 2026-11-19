"""Review provenance and prevention of automatic experimental admission."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "audit/claude_e04_20261119"


def test_imported_review_artifacts_remain_byte_identical() -> None:
    manifest = json.loads((ARCHIVE / "IMPORT_MANIFEST.json").read_text(encoding="utf-8"))
    for item in manifest["artifacts"]:
        path = ARCHIVE / item["path"]
        assert path.resolve().is_relative_to(ARCHIVE.resolve())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    assert manifest["input_hashes_matched_before_integration"] == 7
    assert manifest["source_hashes_and_sizes_matched"] == 5
    assert not manifest["auxiliary_scripts_executed_by_codex"]
    assert not manifest["auxiliary_files_bundled"]


def test_review_preserves_blocked_cases_and_uncertainty() -> None:
    review = json.loads((ROOT / "benchmarks/data_catalog/E04_REVIEW.json").read_text("utf-8"))
    with (ARCHIVE / "E04_METADATA_MATRIX.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        assert len(reader.fieldnames or ()) == 60
    assert review["case_count"] == len(rows) == len(review["cases"])
    assert {row["case_id"] for row in rows} == {case["case_id"] for case in review["cases"]}
    assert len({case["case_id"] for case in review["cases"]}) == len(rows)
    assert review["decision"] == "NOT_READY"
    assert review["physical_validation_ready_count"] == 0
    assert all(not case["admitted_for_physical_validation"] for case in review["cases"])
    assert all(not case["numeric_model_configuration_generated"] for case in review["cases"])
    assert review["split_status"] == "DRAFT_NOT_FROZEN"
    assert review["preferred_candidate"]["state"] == "CONDITIONAL_NOT_ADMITTED"
    assert review["lapse_checks"]["attempts_reported"] == 3
    assert review["lapse_checks"]["supplement_exists"] is None
    assert not review["lapse_checks"]["transport_attempts_independently_verified"]
    assert review["lapse_checks"]["new_requests_by_codex"] == 0
