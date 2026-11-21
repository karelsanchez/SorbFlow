"""Explicit, read-only CSV import for one experimental breakthrough series."""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path

from ..schemas import Observations
from ..units import quantity, to_si


def _column_name(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be an explicit nonempty column name")


def _number(
    value: str,
    *,
    row: int,
    column: str,
    unit: str,
    target: str,
    positive: bool = False,
) -> float:
    try:
        result = to_si(quantity(float(value), unit), target)
        if result < 0 or (positive and result == 0):
            raise ValueError("value must be positive" if positive else "value must be nonnegative")
        return result
    except ValueError as exc:
        raise ValueError(f"CSV row {row}, column {column!r}: {exc}") from exc


def _check_records(text: str, delimiter: str, width: int) -> None:
    """Detect blank records that DictReader would otherwise silently skip."""
    scanner = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    try:
        for record in scanner:
            if not record:
                raise ValueError(f"CSV row {scanner.line_num}: blank records are not supported")
            if len(record) != width:
                raise ValueError(
                    f"CSV row {scanner.line_num}: expected {width} fields, found {len(record)}"
                )
    except csv.Error as exc:
        raise ValueError(f"CSV row {scanner.line_num}: malformed CSV: {exc}") from exc


def load_breakthrough_csv(
    path: str | Path,
    *,
    experiment_id: str,
    species_name: str,
    time_column: str,
    concentration_column: str,
    time_unit: str,
    concentration_unit: str,
    std_column: str | None = None,
    std_unit: str | None = None,
    delimiter: str = ",",
) -> Observations:
    """Read one explicitly mapped UTF-8 CSV without mutating or cleaning its source.

    Time is converted to seconds; concentration and optional measurement standard
    deviation become kg solute/m3 liquid. Units, identities and column mappings are
    mandatory. Molar concentration, ppm and censored values are not inferred.
    Standard-deviation column and unit must be supplied together.

    Source SHA-256 covers the exact original bytes, including any UTF-8 BOM. Times
    must already strictly increase. Blank/malformed records, duplicate headers,
    nonfinite numbers and invalid physical values fail rather than being removed,
    sorted, imputed or averaged. Additional metadata columns are ignored in the
    returned Observations and remain untouched in the source file.
    """
    if not isinstance(delimiter, str) or len(delimiter) != 1 or delimiter in "\r\n\0":
        raise ValueError("delimiter must be one non-newline, non-NUL character")
    _column_name(time_column, "time_column")
    _column_name(concentration_column, "concentration_column")
    if (std_column is None) != (std_unit is None):
        raise ValueError("std_column and std_unit must be supplied together")
    required = [time_column, concentration_column]
    if std_column is not None:
        _column_name(std_column, "std_column")
        required.append(std_column)
    if len(set(required)) != len(required):
        raise ValueError("Mapped measurement columns must be distinct")
    for name, unit, target in (
        ("time_unit", time_unit, "s"),
        ("concentration_unit", concentration_unit, "kg/m^3"),
    ):
        try:
            to_si(quantity(1, unit), target)
        except ValueError as exc:
            raise ValueError(f"Invalid {name}: {exc}") from exc
    if std_unit is not None:
        try:
            to_si(quantity(1, std_unit), "kg/m^3")
        except ValueError as exc:
            raise ValueError(f"Invalid std_unit: {exc}") from exc

    source = Path(path).read_bytes()
    try:
        text = source.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Experimental CSV must use UTF-8 encoding") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    try:
        headers = reader.fieldnames
    except csv.Error as exc:
        raise ValueError(f"CSV header: malformed CSV: {exc}") from exc
    if not headers or any(not header.strip() for header in headers):
        raise ValueError("CSV requires nonempty named headers")
    if len(set(headers)) != len(headers):
        raise ValueError("CSV header names must be unique")
    missing = set(required) - set(headers)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")
    _check_records(text, delimiter, len(headers))

    times: list[float] = []
    concentrations: list[float] = []
    deviations: list[float] = []
    for record in reader:
        row = reader.line_num
        time = _number(record[time_column], row=row, column=time_column, unit=time_unit, target="s")
        if times and time <= times[-1]:
            raise ValueError(f"CSV row {row}, column {time_column!r}: times must strictly increase")
        times.append(time)
        concentrations.append(
            _number(
                record[concentration_column],
                row=row,
                column=concentration_column,
                unit=concentration_unit,
                target="kg/m^3",
            )
        )
        if std_column is not None and std_unit is not None:
            deviations.append(
                _number(
                    record[std_column],
                    row=row,
                    column=std_column,
                    unit=std_unit,
                    target="kg/m^3",
                    positive=True,
                )
            )
    return Observations(
        experiment_id=experiment_id,
        species_name=species_name,
        time_s=tuple(times),
        concentration_kg_m3=tuple(concentrations),
        source_sha256=hashlib.sha256(source).hexdigest(),
        std_kg_m3=tuple(deviations) if std_column is not None else None,
    )
