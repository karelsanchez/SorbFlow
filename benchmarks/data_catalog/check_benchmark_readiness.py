"""Read-only consistency report; metadata declarations are not scientific certification.

Install destination: benchmarks/data_catalog/check_benchmark_readiness.py
Python >=3.11, standard library only. JSON stdout; exits 0 report, 1 malformed
registry/files, 2 unmet gate when --require-confirmatory is requested.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import ntpath
from pathlib import Path, PureWindowsPath
from typing import Any


class RegistryError(ValueError):
    """Input does not satisfy the supported registry contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegistryError(message)


def text(value: object, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{label}: nonempty string required")
    return str(value)


def boolean(value: object, label: str) -> bool:
    require(type(value) is bool, f"{label}: explicit JSON boolean required")
    return bool(value)


def count(value: object, label: str) -> int:
    require(type(value) is int and value >= 0, f"{label}: nonnegative integer required")
    return int(value)


def strings(value: object, label: str) -> list[str]:
    require(isinstance(value, list), f"{label}: list required")
    return [text(item, label) for item in value]


def mapping(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label}: object required")
    return value


def reserved_windows_name(value: str) -> bool:
    # Explicit Windows semantics are needed even when the catalog is checked on Linux.
    checker = getattr(ntpath, "isreserved", None)
    if checker is not None:
        return bool(checker(value))
    return PureWindowsPath(value).is_reserved()  # Python 3.11/3.12 compatibility.


def safe_relative(value: object) -> str:
    directory = text(value, "relative_directory")
    win = PureWindowsPath(directory)
    parts = directory.replace("\\", "/").split("/")
    require(not win.drive and not win.root, f"Unsafe relative_directory: {directory}")
    require(
        all(
            part not in ("", ".", "..")
            and part == part.strip()
            and not reserved_windows_name(part)
            and not part.endswith(".")
            and not any(ord(c) < 32 or c in ':<>"|?*' for c in part)
            for part in parts
        ),
        f"Unsafe relative_directory: {directory}",
    )
    return directory


def load_json(path: Path) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise RegistryError(f"Nonfinite JSON constant: {value}")

    data = json.loads(
        path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique, parse_constant=nonfinite
    )
    require(isinstance(data, dict), f"{path.name}: root object required")
    require(
        type(data.get("schema_version")) is int and data["schema_version"] == 1,
        f"{path.name}: integer schema_version=1 required",
    )
    return data


def inspect_catalog(catalog: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    sources = catalog.get("sources")
    require(isinstance(sources, list), "sources: list required")
    require(
        count(catalog.get("source_count"), "source_count") == len(sources),
        "source_count does not match sources",
    )
    groups: dict[str, list[str]] = {
        name: []
        for name in (
            "analytical_candidates",
            "simulated_reference_candidates",
            "aqueous_experimental_candidates",
            "out_of_domain_references",
            "other_catalogued_sources",
            "physical_validation_ready_as_declared",
        )
    }
    ids: set[str] = set()
    summaries = []
    for index, raw in enumerate(sources):
        source = mapping(raw, f"sources[{index}]")
        source_id = text(source.get("source_id"), "source_id")
        require(source_id not in ids, f"Duplicate source_id: {source_id}")
        ids.add(source_id)
        directory = safe_relative(source.get("relative_directory"))
        domain = text(source.get("domain"), f"{source_id}.domain")
        ready = boolean(source.get("ready_for_pyfast_physical_validation"), f"{source_id}.ready")
        blockers = strings(source.get("blockers_reported_by_local_audit"), f"{source_id}.blockers")
        license_data = mapping(source.get("license"), f"{source_id}.license")
        license_status = text(license_data.get("status"), f"{source_id}.license.status")
        boolean(
            license_data.get("web_reverified_this_review"), f"{source_id}.license.web_reverified"
        )
        provenance = mapping(source.get("provenance"), f"{source_id}.provenance")
        boolean(provenance.get("integrity_claims_reverified"), f"{source_id}.integrity_reverified")
        if "local_curve_records" in source:
            count(source["local_curve_records"], f"{source_id}.local_curve_records")
        roles = mapping(source.get("roles"), f"{source_id}.roles")
        preparation = strings(
            roles.get("allowed_for_preparation"), f"{source_id}.preparation_roles"
        )
        if ready:
            require(not blockers, f"{source_id}: ready=true conflicts with blockers")
            unresolved = "report" in license_status.lower() or license_status.lower() in (
                "unknown",
                "pending",
                "unverified",
                "not_reviewed",
            )
            require(
                not unresolved,
                f"{source_id}: ready=true conflicts with unresolved/reported license",
            )
            require(
                not any(
                    tag in domain.lower() for tag in ("analytical", "simulated", "out_of_domain")
                )
                and not domain.lower().startswith("gas"),
                f"{source_id}: declared domain is not a physical validation dataset",
            )
            groups["physical_validation_ready_as_declared"].append(source_id)
        if "out_of_domain" in domain.lower() or domain.lower().startswith("gas"):
            group = "out_of_domain_references"
        elif "analytical" in domain.lower():
            group = "analytical_candidates"
        elif "simulated" in domain.lower():
            group = "simulated_reference_candidates"
        elif domain.lower().startswith("aqueous"):
            group = "aqueous_experimental_candidates"
        else:
            group = "other_catalogued_sources"
        groups[group].append(source_id)
        summaries.append(
            {
                "source_id": source_id,
                "relative_directory": directory,
                "domain": domain,
                "preparation_roles": preparation,
                "physical_validation_ready_as_declared": ready,
                "license_status_as_declared": license_status,
                "blockers": blockers,
            }
        )
    declared_count = len(groups["physical_validation_ready_as_declared"])
    require(
        count(catalog.get("physical_validation_ready_count"), "physical_validation_ready_count")
        == declared_count,
        "physical_validation_ready_count does not match declarations",
    )
    return summaries, groups


def inspect_experiments(claims: dict[str, Any], csv_path: Path) -> list[dict[str, Any]]:
    entries = claims.get("claims")
    experiments = mapping(claims.get("experiments"), "claims.experiments")
    require(isinstance(entries, list), "claims: list required")
    claim_ids: set[str] = set()
    expected_refs: dict[str, set[str]] = {key: set() for key in experiments}
    for raw in entries:
        claim = mapping(raw, "claim")
        claim_id = text(claim.get("claim_id"), "claim_id")
        require(claim_id not in claim_ids, f"Duplicate claim_id: {claim_id}")
        claim_ids.add(claim_id)
        boolean(claim.get("superiority_demonstrated"), f"{claim_id}.superiority_demonstrated")
        references = strings(claim.get("experiments"), f"{claim_id}.experiments")
        require(
            len(references) == len(set(references)), f"Duplicate experiment reference: {claim_id}"
        )
        for experiment_id in references:
            require(experiment_id in experiments, f"Unknown experiment reference: {experiment_id}")
            expected_refs[experiment_id].add(claim_id)
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        fields = reader.fieldnames or []
        require(
            len(fields) == 4
            and set(fields)
            == {"experiment_id", "status", "claim_ids", "confirmatory_result_available"},
            "EXPERIMENT_REGISTRY.csv: unexpected or duplicate headers",
        )
        rows = list(reader)
    seen: set[str] = set()
    reports = []
    for row in rows:
        require(
            None not in row and all(value is not None for value in row.values()),
            "EXPERIMENT_REGISTRY.csv: malformed row",
        )
        experiment_id = text(row["experiment_id"], "experiment_id")
        require(experiment_id not in seen, f"Duplicate experiment_id: {experiment_id}")
        seen.add(experiment_id)
        require(experiment_id in experiments, f"Unknown CSV experiment: {experiment_id}")
        status = text(row["status"], "experiment status")
        declared = mapping(experiments[experiment_id], experiment_id)
        require(status == declared.get("status"), f"Experiment status mismatch: {experiment_id}")
        raw_bool = row["confirmatory_result_available"].strip().lower()
        require(raw_bool in ("true", "false"), f"{experiment_id}: explicit CSV true/false required")
        references = row["claim_ids"].split(";") if row["claim_ids"] else []
        require(
            len(references) == len(set(references))
            and set(references) == expected_refs[experiment_id],
            f"Claim references mismatch: {experiment_id}",
        )
        reports.append(
            {
                "experiment_id": experiment_id,
                "status_as_declared": status,
                "claim_ids": references,
                "confirmatory_result_available": raw_bool == "true",
            }
        )
    require(seen == set(experiments), "Experiment IDs differ between JSON and CSV")
    return reports


def report_readiness(repo: Path) -> dict[str, Any]:
    catalog = load_json(repo / "benchmarks/data_catalog/DATASET_REGISTRY.json")
    claims = load_json(repo / "PAPER_ENVSOFT/CLAIMS_REGISTRY.json")
    sources, groups = inspect_catalog(catalog)
    experiments = inspect_experiments(claims, repo / "PAPER_ENVSOFT/EXPERIMENT_REGISTRY.csv")
    version = text(claims.get("protocol_version"), "protocol_version")
    preregistered = boolean(claims.get("public_preregistration"), "public_preregistration")
    decision = mapping(claims.get("decision_rule"), "decision_rule")
    threshold = decision.get("practical_effect_threshold")
    numeric_threshold = type(threshold) in (int, float) and math.isfinite(threshold)
    if numeric_threshold:
        require(0 <= threshold <= 1, "practical_effect_threshold must be within [0,1]")
    pending = not numeric_threshold
    draft = (
        any(marker in version.lower() for marker in ("draft", "proposal", "proposed")) or pending
    )
    blockers = ["protocol_is_draft"] if draft else []
    if pending:
        blockers.append("practical_effect_threshold_not_final_numeric_value")
    ready_count = len(groups["physical_validation_ready_as_declared"])
    if ready_count == 0:
        blockers.append("no_physical_validation_dataset_ready_as_declared")
    return {
        "report_schema_version": 1,
        "status": "draft" if draft else ("blocked" if blockers else "declared_requirements_met"),
        "confirmatory_gate_passed_as_declared": not blockers,
        "confirmatory_gate_blockers": blockers,
        "protocol": {
            "version": version,
            "draft": draft,
            "public_preregistration_as_declared": preregistered,
            "practical_effect_threshold_pending": pending,
        },
        "source_count": len(sources),
        "physical_validation_ready_count_as_declared": ready_count,
        "prepared_groups": groups,
        "sources": sources,
        "experiments": experiments,
        "limitations": [
            "Checks registry consistency only; no scientific or licensing certification.",
            "Does not inspect dataset presence, content, download integrity "
            "or model compatibility.",
            "Prepared groups are catalogued candidates, not admitted datasets "
            "or PASSED experiments.",
            "A non-draft declaration is not proof of a frozen Git protocol "
            "or public preregistration.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--require-confirmatory", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = report_readiness(args.repo)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, csv.Error) as exc:
        print(json.dumps({"report_schema_version": 1, "status": "error", "error": str(exc)}))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return (
        2 if args.require_confirmatory and not report["confirmatory_gate_passed_as_declared"] else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
