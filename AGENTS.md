# PyFAST research workflow

Use this repository's `.venv/Scripts/python.exe` on this Windows workstation.
The working repository moved from D: to C:; commands in current documentation
should run relative to the repository. Paths in historical audit manifests remain
historical evidence. Do not rewrite downloaded source data to correct metadata.

## Scientific evidence

- Keep framework code independent of the four-material application. Species,
  materials and mixtures are data, not branches for particular materials.
- Preserve SI quantities, dry-mass conventions, initial/boundary conditions and
  the distinction between superficial and interstitial velocity.
- A successful pytest suite or smoke demo is not full numerical verification or
  experimental validation. Update claims only using the corresponding experiment.
- Freeze and hash a benchmark's definitions before its execution. Report prior
  pilot knowledge, failed cases and amendments; do not relax thresholds afterward.
- Data inventories are not observations. Keep analytic, synthetic, simulated and
  experimental evidence separate; split independent complete experiments.
- FAST is an optional external interoperability proposal. Never package its ZIP,
  executables or resources, or claim legal permission from interoperability alone.
  Publication licensing remains subject to ownership review.

## Changes, documentation and version control

- Assign workers nonoverlapping files. The integrating worker owns root metadata,
  README, CI and commits; finish edits before the final checks run.
- Check `git status` before editing/staging. Stage explicit paths, preserve changes
  unrelated to the task, and exclude `datasets_benchmark_pyfast/` and generated runs.
- Link functional documentation from `docs/index.md`. Keep implemented behavior,
  limitations, commands and scientific status consistent with API/tests.
- Run `.venv/Scripts/python.exe scripts/project_checks.py --output runs/<new-id>`
  after integration. It records logs and source hashes; it does not execute E01/E04.
  `--quick` skips pytest and is not the complete quality gate.
- Version in `pyproject.toml` and `src/pyfast/_version.py` must match. Keep the dev
  designation until the release criteria and rights are satisfied. Build artifacts
  from a known commit; publishing/uploading is a separate user-authorized action.
- Create focused local commits after checks. Remote CI is configured, not claimed
  successful until its actual run is available. Never fabricate benchmark outputs.
