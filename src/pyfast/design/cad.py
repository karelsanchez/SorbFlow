"""Neutral process-envelope DXF export; no CAD runtime in the scientific core."""

from pathlib import Path

from ..schemas import Bed


def export_dxf(bed: Bed, path: str | Path) -> Path:
    """Export a cylindrical bed envelope: elevation and plan in meters.

    This contains process geometry, not wall thickness, vessel heads, connections,
    pressure-vessel calculations or a fabrication drawing. STEP requires a future
    optional CAD adapter. Existing files are never overwritten.
    """
    pairs: list[tuple[int, str | float | int]] = [
        (0, "SECTION"),
        (2, "HEADER"),
        (9, "$ACADVER"),
        (1, "AC1015"),
        (9, "$INSUNITS"),
        (70, 6),
        (0, "ENDSEC"),
        (0, "SECTION"),
        (2, "ENTITIES"),
    ]
    d, length = bed.diameter_m, bed.length_m
    corners = ((0, 0), (d, 0), (d, length), (0, length))
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        pairs.extend(
            [
                (0, "LINE"),
                (8, "PROCESS_ENVELOPE"),
                (10, a[0]),
                (20, a[1]),
                (30, 0),
                (11, b[0]),
                (21, b[1]),
                (31, 0),
            ]
        )
    pairs.extend(
        [
            (0, "CIRCLE"),
            (8, "PROCESS_ENVELOPE"),
            (10, 2 * d),
            (20, d / 2),
            (30, 0),
            (40, d / 2),
            (0, "TEXT"),
            (8, "NOTES"),
            (10, 0),
            (20, -d / 4),
            (30, 0),
            (40, d / 12),
            (1, "PROCESS ENVELOPE - METERS - NOT A FABRICATION DRAWING"),
            (0, "ENDSEC"),
            (0, "EOF"),
        ]
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="ascii", newline="\n") as stream:
        stream.write("".join(f"{code}\n{value}\n" for code, value in pairs))
    return target
