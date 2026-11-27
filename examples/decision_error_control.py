"""Decision-oriented discretization error control for a synthetic LDF column.

Usage: python examples/decision_error_control.py [--output report.json]

Refines the axial grid until the breakthrough times t_5, t_10, t_50, the bed
volumes at 10 % breakthrough and the effluent at a service time are known to a
1 % discretization tolerance (GCI), then classifies two design constraints.
Synthetic parameters; no experimental validation is claimed.
"""

import argparse
from pathlib import Path

from run_ldf import configuration

from sorbflow.solvers import SolverOptions
from sorbflow.verification import (
    BedVolumesAt,
    BreakthroughTime,
    Constraint,
    EffluentAt,
    classify_report,
    converge,
)

SERVICE_TIME_S = 1400.0
LIMIT_KG_M3 = 1e-3  # declared effluent limit: 10 % of the inlet concentration


def main(output: Path | None) -> None:
    config = configuration()
    quantities = [
        BreakthroughTime(fraction=0.05),
        BreakthroughTime(fraction=0.1),
        BreakthroughTime(fraction=0.5),
        BedVolumesAt(fraction=0.1),
        service := EffluentAt(service_time_s=SERVICE_TIME_S),
    ]
    report = converge(
        config,
        quantities,
        rel_tol=0.01,
        # The effluent before breakthrough is ~0: judge it on an absolute scale.
        abs_tol={service.key: 2e-5},
        max_cells=1600,
        budget_solves=7,
        options=SolverOptions(axial_cells=25, rtol=1e-8),
    )
    print(f"stop: {report.stop_reason}; solves: {report.solves_used}; "
          f"CPU: {report.cpu_s_total:.1f} s; grids: {[g.axial_cells for g in report.grids]}")
    print(f"{'quantity':<24}{'finest':>12}{'extrapolated':>14}{'bound':>11}{'p':>7}  status")
    for q in report.quantities:
        p = None if q.estimate is None else q.estimate.p_observed
        print(f"{q.key:<24}{q.value or float('nan'):>12.5g}{q.extrapolated or float('nan'):>14.5g}"
              f"{q.error_bound or float('nan'):>11.3g}{p or float('nan'):>7.2f}  {q.status}")
    constraints = [
        Constraint(quantity_key="t_0.1_s", sense=">=", threshold=SERVICE_TIME_S,
                   label="10 % breakthrough after the required service time"),
        Constraint(quantity_key=service.key, sense="<=", threshold=LIMIT_KG_M3,
                   label="effluent below the limit at the service time"),
        Constraint(quantity_key="t_0.05_s", sense=">=", threshold=1285.0,
                   label="5 % breakthrough after 1285 s (near the threshold)"),
    ]
    for assessment in classify_report(report, constraints):
        print(f"{assessment.constraint.label}: {assessment.status} "
              f"{assessment.recommendation}".rstrip())
    print(f"fingerprint: {report.fingerprint}")
    if output is not None:
        output.write_text(report.to_json(), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    main(parser.parse_args().output)
