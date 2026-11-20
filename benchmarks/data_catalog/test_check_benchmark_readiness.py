"""Five standard-library fixture tests; never touch the D: project or dataset files."""

from __future__ import annotations

import copy
import json
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

CHECKER = Path(__file__).with_name("check_benchmark_readiness.py")


class ReadinessTests(unittest.TestCase):
    def test_modern_windows_reserved_path_check_avoids_legacy_api(self) -> None:
        namespace = runpy.run_path(str(CHECKER), run_name="readiness_test_import")
        with (
            patch.object(
                namespace["ntpath"], "isreserved", lambda name: name == "AUX", create=True,
            ),
            patch.object(namespace["PureWindowsPath"], "is_reserved", side_effect=AssertionError),
        ):
            self.assertTrue(namespace["reserved_windows_name"]("AUX"))
            self.assertFalse(namespace["reserved_windows_name"]("dataset"))

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="readiness_test_", dir=CHECKER.parent)
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        (self.repo / "benchmarks/data_catalog").mkdir(parents=True)
        (self.repo / "PAPER_ENVSOFT").mkdir()
        self.catalog = {
            "schema_version": 1,
            "source_count": 1,
            "physical_validation_ready_count": 0,
            "sources": [
                {
                    "source_id": "example",
                    "relative_directory": "01_example",
                    "domain": "aqueous_experimental_with_reservations",
                    "ready_for_pyfast_physical_validation": False,
                    "blockers_reported_by_local_audit": ["missing geometry"],
                    "license": {
                        "status": "reported_by_local_inventory",
                        "web_reverified_this_review": False,
                    },
                    "provenance": {"integrity_claims_reverified": False},
                    "roles": {"allowed_for_preparation": ["provenance_review"]},
                }
            ],
        }
        self.claims = {
            "schema_version": 1,
            "protocol_version": "0.1-draft",
            "public_preregistration": False,
            "decision_rule": {"practical_effect_threshold": "TO_BE_SET_BEFORE_CONFIRMATORY_RUN"},
            "claims": [
                {"claim_id": "C01", "experiments": ["E01"], "superiority_demonstrated": False}
            ],
            "experiments": {"E01": {"status": "PLANNED"}},
        }
        self.csv_text = (
            "experiment_id,status,claim_ids,confirmatory_result_available\nE01,PLANNED,C01,false\n"
        )

    def run_cli(self, *, require: bool = False) -> tuple[int, dict]:
        (self.repo / "benchmarks/data_catalog/DATASET_REGISTRY.json").write_text(
            json.dumps(self.catalog), encoding="utf-8"
        )
        (self.repo / "PAPER_ENVSOFT/CLAIMS_REGISTRY.json").write_text(
            json.dumps(self.claims), encoding="utf-8"
        )
        (self.repo / "PAPER_ENVSOFT/EXPERIMENT_REGISTRY.csv").write_text(
            self.csv_text, encoding="utf-8"
        )
        before = {p: p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}
        command = [sys.executable, str(CHECKER), "--repo", str(self.repo)]
        if require:
            command.append("--require-confirmatory")
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual({p: p.read_bytes() for p in self.repo.rglob("*") if p.is_file()}, before)
        self.assertEqual(result.stderr, "")
        return result.returncode, json.loads(result.stdout)

    def test_draft_report_is_read_only_and_confirmation_is_blocked(self) -> None:
        # Presence is deliberately absent; source_count is a catalog count, not a disk scan.
        code, report = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "draft")
        self.assertEqual(report["physical_validation_ready_count_as_declared"], 0)
        self.assertEqual(report["prepared_groups"]["aqueous_experimental_candidates"], ["example"])
        self.assertFalse(report["confirmatory_gate_passed_as_declared"])
        self.assertEqual(self.run_cli(require=True)[0], 2)

    def test_declared_complete_metadata_passes_without_certification(self) -> None:
        source = self.catalog["sources"][0]
        source["ready_for_pyfast_physical_validation"] = True
        source["blockers_reported_by_local_audit"] = []
        source["license"]["status"] = "reviewed_for_declared_use"
        self.catalog["physical_validation_ready_count"] = 1
        self.claims["protocol_version"] = "1.0"
        self.claims["decision_rule"]["practical_effect_threshold"] = 0.05
        code, report = self.run_cli(require=True)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "declared_requirements_met")
        self.assertIn("no scientific or licensing certification", report["limitations"][0])
        # A frozen internal declaration does not require claiming public preregistration.
        self.assertFalse(report["protocol"]["public_preregistration_as_declared"])

    def test_duplicate_counts_and_unsafe_paths_are_structural_errors(self) -> None:
        original = copy.deepcopy(self.catalog)
        for mutation in ("duplicate", "count", "../escape", "C:\\absolute", "CON"):
            with self.subTest(mutation=mutation):
                self.catalog = copy.deepcopy(original)
                if mutation == "duplicate":
                    self.catalog["sources"].append(copy.deepcopy(self.catalog["sources"][0]))
                    self.catalog["source_count"] = 2
                elif mutation == "count":
                    self.catalog["source_count"] = True
                else:
                    self.catalog["sources"][0]["relative_directory"] = mutation
                code, report = self.run_cli()
                self.assertEqual((code, report["status"]), (1, "error"))

    def test_explicit_booleans_and_ready_declaration_guards(self) -> None:
        original = copy.deepcopy(self.catalog)
        for mutation in (
            "string_bool",
            "blockers",
            "reported_license",
            "wrong_count",
            "analytical",
        ):
            with self.subTest(mutation=mutation):
                self.catalog = copy.deepcopy(original)
                source = self.catalog["sources"][0]
                source["ready_for_pyfast_physical_validation"] = True
                self.catalog["physical_validation_ready_count"] = 1
                if mutation != "blockers":
                    source["blockers_reported_by_local_audit"] = []
                if mutation != "reported_license":
                    source["license"]["status"] = "reviewed_for_declared_use"
                if mutation == "string_bool":
                    source["provenance"]["integrity_claims_reverified"] = "false"
                elif mutation == "wrong_count":
                    self.catalog["physical_validation_ready_count"] = 0
                elif mutation == "analytical":
                    source["domain"] = "analytical_ADE_reference"
                self.assertEqual(self.run_cli()[0], 1)

    def test_claim_csv_boolean_and_cross_reference_consistency(self) -> None:
        original = copy.deepcopy(self.claims)
        original_csv = self.csv_text
        for mutation in ("claim_bool", "csv_bool", "status", "references"):
            with self.subTest(mutation=mutation):
                self.claims, self.csv_text = copy.deepcopy(original), original_csv
                if mutation == "claim_bool":
                    self.claims["claims"][0]["superiority_demonstrated"] = 0
                elif mutation == "csv_bool":
                    self.csv_text = original_csv.replace("false", "0")
                elif mutation == "status":
                    self.csv_text = original_csv.replace("PLANNED", "PASSED")
                else:
                    self.csv_text = original_csv.replace("C01,false", "C02,false")
                self.assertEqual(self.run_cli()[0], 1)


if __name__ == "__main__":
    unittest.main()
