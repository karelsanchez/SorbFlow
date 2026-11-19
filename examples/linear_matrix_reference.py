"""Independent linear affine-matrix reference for the discrete PyFAST equations.

This constructs a separate full matrix and evaluates its exponential. It does not
reuse PyFAST RHS closures, Jacobian patterns or film-flux code. It verifies the
discrete system, not convergence of the continuum PDE or experimental validity.

Run with the project virtual-environment Python interpreter.
"""

from __future__ import annotations

import json

import numpy as np
from scipy.linalg import expm

from pyfast import HSDM, LDF, Bed, Linear, Operation, SimulationConfig, Species
from pyfast.simulate import column
from pyfast.solvers import SolverOptions


def run_reference() -> dict[str, dict[str, float]]:
    bed = Bed(
        length_m=0.1,
        diameter_m=0.01,
        particle_diameter_m=0.0002,
        porosity=0.4,
        particle_density_kg_m3=1000,
        material="matrix-reference-material",
    )
    operation = Operation(
        flow_m3_s=1e-7,
        inlet_concentration_kg_m3=0.01,
        duration_s=100,
        axial_dispersion_m2_s=1e-5,
        initial_concentration_kg_m3=0.003,
        initial_loading_kg_kg=0.0001,
    )
    axial_cells, radial_cells = 4, 5
    distribution, rate = 0.03, 0.02
    epsilon = bed.porosity
    particle_density = bed.particle_density_kg_m3
    bulk_density = bed.bulk_density_kg_m3
    dz = bed.length_m / axial_cells
    column_area = bed.volume_m3 / bed.length_m
    superficial_velocity = operation.flow_m3_s / column_area
    advective_rate = superficial_velocity / (epsilon * dz)
    dispersive_rate = operation.axial_dispersion_m2_s / dz**2

    # Prescribed total inlet flux; zero dispersive outlet flux.
    transport = np.zeros((axial_cells, axial_cells))
    for i in range(axial_cells):
        transport[i, i] = -advective_rate - dispersive_rate * (
            int(i > 0) + int(i < axial_cells - 1)
        )
        if i > 0:
            transport[i, i - 1] = advective_rate + dispersive_rate
        if i < axial_cells - 1:
            transport[i, i + 1] = dispersive_rate

    output: dict[str, dict[str, float]] = {}
    kinetics_options = (
        LDF(rate_s_inv=rate),
        HSDM(surface_diffusivity_m2_s=1e-11, film_coefficient_m_s=1e-5),
    )
    for kinetics in kinetics_options:
        nr = 1 if isinstance(kinetics, LDF) else radial_cells
        state_count = axial_cells * (1 + nr)
        # An appended constant state converts the constant inlet forcing to an
        # affine matrix exponential without inverting a potentially singular M.
        matrix = np.zeros((state_count + 1, state_count + 1))
        matrix[:axial_cells, :axial_cells] = transport
        matrix[0, -1] = advective_rate * operation.inlet_concentration_kg_m3

        if isinstance(kinetics, LDF):
            for i in range(axial_cells):
                matrix[i, i] -= bulk_density / epsilon * rate * distribution
                matrix[i, axial_cells + i] += bulk_density / epsilon * rate
                matrix[axial_cells + i, i] = rate * distribution
                matrix[axial_cells + i, axial_cells + i] = -rate
        else:
            radius = bed.particle_diameter_m / 2
            dr = radius / nr
            faces = np.arange(nr + 1) * dr
            shell_volumes = np.diff(faces**3) / 3
            ds = kinetics.surface_diffusivity_m2_s
            kf = kinetics.film_coefficient_m_s
            conductance = particle_density * ds / (dr / 2)
            # Exact linear algebraic elimination of the film/surface interface:
            # j = j_c*c + j_q*q_last.
            j_c = kf * conductance * distribution / (kf + conductance * distribution)
            j_q = -kf * conductance / (kf + conductance * distribution)
            external_area_per_bed_volume = 3 * (1 - epsilon) / radius
            for i in range(axial_cells):
                outer_index = axial_cells + i * nr + nr - 1
                matrix[i, i] -= external_area_per_bed_volume / epsilon * j_c
                matrix[i, outer_index] -= external_area_per_bed_volume / epsilon * j_q
                for radial_index in range(nr):
                    index = axial_cells + i * nr + radial_index
                    if radial_index > 0:
                        coefficient = (
                            ds * faces[radial_index] ** 2 / (dr * shell_volumes[radial_index])
                        )
                        matrix[index, index - 1] += coefficient
                        matrix[index, index] -= coefficient
                    if radial_index < nr - 1:
                        coefficient = (
                            ds * faces[radial_index + 1] ** 2 / (dr * shell_volumes[radial_index])
                        )
                        matrix[index, index + 1] += coefficient
                        matrix[index, index] -= coefficient
                    else:
                        coefficient = radius**2 / (particle_density * shell_volumes[radial_index])
                        matrix[index, i] += coefficient * j_c
                        matrix[index, index] += coefficient * j_q

        initial = np.r_[
            np.full(axial_cells, operation.initial_concentration_kg_m3),
            np.full(axial_cells * nr, operation.initial_loading_kg_kg),
            1.0,
        ]
        times = np.linspace(0, 100, 11)
        exact = np.array([(expm(matrix * time) @ initial)[:-1] for time in times])
        configuration = SimulationConfig(
            species=Species(name="matrix-reference-solute"),
            bed=bed,
            operation=operation,
            equilibrium=Linear(distribution_m3_kg=distribution),
            kinetics=kinetics,
        )
        result = column(
            configuration,
            time_s=times,
            options=SolverOptions(
                axial_cells=axial_cells,
                radial_cells=radial_cells,
                rtol=1e-10,
                atol_concentration_kg_m3=1e-14,
                atol_loading_kg_kg=1e-16,
            ),
        )
        c_error = float(np.max(np.abs(result.concentration_kg_m3 - exact[:, :axial_cells])))
        if nr == 1:
            q_error = float(np.max(np.abs(result.loading_kg_kg - exact[:, axial_cells:])))
        else:
            q_exact = exact[:, axial_cells:].reshape(len(times), axial_cells, nr)
            q_error = float(np.max(np.abs(result.radial_loading_kg_kg - q_exact)))
        assert c_error < 2e-10
        assert q_error < 2e-12
        assert result.diagnostics.max_scaled_mass_residual < 1e-10
        output[kinetics.kind] = {
            "max_concentration_error_kg_m3": c_error,
            "max_loading_error_kg_kg": q_error,
            "max_scaled_mass_residual": result.diagnostics.max_scaled_mass_residual,
        }
    return output


if __name__ == "__main__":
    print(json.dumps(run_reference(), indent=2))
