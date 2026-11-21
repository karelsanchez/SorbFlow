"""Regenerate the documentation figures from real SorbFlow simulations.

Usage, from the repository root::

    python scripts/make_figures.py [--output docs/assets/figures]

Every curve comes from the shipped synthetic examples in ``examples/`` and the
public SorbFlow API. The performance chart only re-plots values measured and
recorded during development (see ``docs/performance.md``); it runs no benchmark.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from sorbflow import BatchConfig, Freundlich, Langmuir, Linear, SimulationConfig  # noqa: E402
from sorbflow.equilibrium import isotherm_from_parameters  # noqa: E402
from sorbflow.simulate import batch, column  # noqa: E402
from sorbflow.solvers import SolverOptions  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"

INK = "#1f2933"
GRID = "#d9dee3"
BLUE = "#1f6feb"
ORANGE = "#d9622b"
GREEN = "#2e8b57"
PURPLE = "#7a4cc2"
GREY = "#8a949e"

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": INK,
        "ytick.color": INK,
        "font.size": 10.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
    }
)


def save(fig: plt.Figure, out: Path, name: str) -> None:
    path = out / name
    fig.savefig(path)
    plt.close(fig)
    print(f"wrote {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")


def isotherms(out: Path) -> None:
    c = np.linspace(0.0, 0.05, 400)  # kg/m^3 = 0-50 mg/L
    models = [
        ("Lineal  K = 0,5 m³/kg", Linear(distribution_m3_kg=0.5), BLUE),
        (
            "Langmuir  q_max = 0,03 kg/kg, b = 100 m³/kg",
            Langmuir(qmax_kg_kg=0.03, affinity_m3_kg=100.0),
            ORANGE,
        ),
        (
            "Freundlich  q_ref = 0,015 kg/kg, c_ref = 0,01 kg/m³, α = 0,45",
            Freundlich(q_ref_kg_kg=0.015, c_ref_kg_m3=0.01, exponent=0.45),
            GREEN,
        ),
    ]
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for label, params, colour in models:
        q = isotherm_from_parameters(params).loading(c)
        ax.plot(c * 1e3, q * 1e3, color=colour, lw=2.2, label=label)
    ax.set_xlabel("Concentración en equilibrio c (mg/L)")
    ax.set_ylabel("Carga en equilibrio q* (mg/g)")
    ax.set_xlim(0, 50)
    ax.set_ylim(bottom=0)
    ax.legend(loc="lower right", fontsize=9)
    save(fig, out, "isotherms.png")


def batch_kinetics(out: Path) -> None:
    config = BatchConfig.from_json((EXAMPLES / "batch_ldf.json").read_text(encoding="utf-8"))
    times = np.linspace(0.0, config.duration_s, 301)
    result = batch(config, time_s=times)
    t_min = result.time_s / 60.0
    c = np.asarray(result.outlet_concentration_kg_m3) * 1e3
    q = np.asarray(result.loading_kg_kg)[:, 0] * 1e3
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(t_min, c, color=BLUE, lw=2.2, label="Líquido c (mg/L)")
    ax.set_xlabel("Tiempo (min)")
    ax.set_ylabel("Concentración en el líquido (mg/L)", color=BLUE)
    ax2 = ax.twinx()
    ax2.plot(t_min, q, color=ORANGE, lw=2.2, ls="--", label="Adsorbente q̄ (mg/g)")
    ax2.set_ylabel("Carga media del adsorbente (mg/g)", color=ORANGE)
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax2.spines["top"].set_visible(False)
    ax.set_xlim(0, t_min[-1])
    ax.set_ylim(bottom=0)
    ax2.set_ylim(bottom=0)
    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(lines, [line.get_label() for line in lines], loc="lower right")
    save(fig, out, "batch_kinetics.png")


def breakthrough(out: Path) -> None:
    curves = []
    for name, label, colour, ls in (
        ("column_ldf.json", "LDF (fuerza impulsora lineal)", BLUE, "-"),
        ("column_hsdm.json", "HSDM (difusión superficial + película)", ORANGE, "--"),
    ):
        config = SimulationConfig.from_json((EXAMPLES / name).read_text(encoding="utf-8"))
        times = np.linspace(0.0, config.operation.duration_s, 401)
        options = SolverOptions(axial_cells=60, radial_cells=12)
        result = column(config, time_s=times, options=options)
        c0 = config.operation.inlet_concentration_kg_m3
        curves.append(
            (result.time_s / 60.0, result.outlet_concentration_kg_m3 / c0, label, colour, ls)
        )
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for t, ratio, label, colour, ls in curves:
        ax.plot(t, ratio, color=colour, lw=2.2, ls=ls, label=label)
    ax.set_xlabel("Tiempo (min)")
    ax.set_ylabel("C/C₀ a la salida (–)")
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlim(0, curves[0][0][-1])
    ax.legend(loc="upper left")
    save(fig, out, "breakthrough_ldf_hsdm.png")


def mesh_refinement(out: Path) -> None:
    config = SimulationConfig.from_json((EXAMPLES / "column_ldf.json").read_text(encoding="utf-8"))
    times = np.linspace(0.0, config.operation.duration_s, 401)
    c0 = config.operation.inlet_concentration_kg_m3
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    palette = [GREY, PURPLE, GREEN, BLUE]
    for cells, colour in zip((20, 40, 80, 160), palette, strict=True):
        result = column(config, time_s=times, options=SolverOptions(axial_cells=cells))
        ax.plot(
            result.time_s / 60.0,
            result.outlet_concentration_kg_m3 / c0,
            color=colour,
            lw=2.0,
            label=f"{cells} celdas axiales",
        )
    ax.set_xlabel("Tiempo (min)")
    ax.set_ylabel("C/C₀ a la salida (–)")
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlim(0, times[-1] / 60.0)
    ax.legend(loc="upper left")
    save(fig, out, "mesh_refinement.png")


def performance(out: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.0, 3.6))
    bars = ax1.bar(
        ["Diferencias\nfinitas", "Jacobiano\nanalítico"],
        [17.09, 7.77],
        color=[GREY, BLUE],
        width=0.55,
    )
    ax1.set_ylabel("Tiempo de simulación (s)")
    ax1.bar_label(bars, labels=["17,09 s", "7,77 s"], padding=3)
    ax1.set_ylim(0, 20)
    ax1.grid(axis="x", visible=False)
    bars = ax2.bar(
        ["Historia\ncompleta", "Streaming"], [1632.9, 956.7], color=[GREY, GREEN], width=0.55
    )
    ax2.set_ylabel("Memoria privada máxima (MB)")
    ax2.bar_label(bars, labels=["1.632,9 MB", "956,7 MB"], padding=3)
    ax2.set_ylim(0, 1900)
    ax2.grid(axis="x", visible=False)
    fig.text(
        0.5,
        -0.04,
        "Columna LDF de 620 celdas; medianas medidas en el equipo de desarrollo "
        "(Windows, Python 3.11).",
        ha="center",
        fontsize=9,
        color=GREY,
    )
    fig.tight_layout()
    save(fig, out, "performance.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "assets" / "figures")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    isotherms(args.output)
    batch_kinetics(args.output)
    breakthrough(args.output)
    mesh_refinement(args.output)
    performance(args.output)


if __name__ == "__main__":
    main()
