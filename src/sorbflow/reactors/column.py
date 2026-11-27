"""Conservative method-of-lines fixed-bed LDF model, independent of FAST."""

from __future__ import annotations

import json
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.sparse import csc_matrix

from .._arrays import FloatArray
from ..equilibrium import isotherm_from_parameters
from ..equilibrium.isotherms import trial_loading
from ..schemas import LDF, Langmuir, Linear, SimulationConfig
from ..solvers.integration import integrate, integrate_streaming
from ..solvers.options import SolverOptions, sample_times
from ..solvers.results import SimulationResult, StreamingPhysics, check_physics, result_metadata
from ..units import finite_scalar
from ._ldf_jacobian import LDFColumnJacobian

AxialScheme = Literal["upwind1", "tvd"]
IntArray = NDArray[np.int64]


def _van_albada(a: FloatArray, b: FloatArray) -> FloatArray:
    """Limited slope s(a, b) = ab(a+b)/(a^2+b^2) if ab > 0, else 0 (van Albada 1).

    This is phi(r) = (r^2+r)/(r^2+1), r = a/b, written symmetrically, so that
    0 <= s/a <= (1+sqrt 2)/2 and 0 <= s/b <= (1+sqrt 2)/2: the semi-discrete scheme is
    local-extremum diminishing and positivity preserving. If ab underflows the slope
    is zero (first order on differences below ~1e-154, which is still TVD).
    """
    ab = a * b
    s = np.zeros_like(a)
    same = ab > 0
    x, y = a[same], b[same]
    s[same] = ab[same] * (x + y) / (x * x + y * y)
    return s


def _van_albada_derivatives(a: FloatArray, b: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Exact ds/da and ds/db of ``_van_albada``, scaled to avoid underflow."""
    da, db = np.zeros_like(a), np.zeros_like(a)
    same = a * b > 0
    x, y = a[same], b[same]
    m = np.maximum(np.abs(x), np.abs(y))
    x, y = x / m, y / m
    den2 = (x * x + y * y) ** 2
    da[same] = y * y * (y * y + 2 * x * y - x * x) / den2
    db[same] = x * x * (x * x + 2 * x * y - y * y) / den2
    return da, db


def _outlet_ghost(last: FloatArray, previous: FloatArray
                  ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    """Backward difference a, ghost difference g and dg/da, dg/dc_{N-1} at the outlet."""
    a = last - previous
    cp = np.maximum(last, 0.0)
    falling = a < 0
    den = np.where(falling & (cp - a > 0), cp - a, 1.0)
    g = np.where(falling, a * cp / den, a)
    g_a = np.where(falling, (cp / den) ** 2, 1.0)
    g_c = np.where(falling & (last > 0), -((a / den) ** 2), 0.0)
    return a, g, g_a, g_c


def outlet_face_value(last: ArrayLike, previous: ArrayLike) -> FloatArray:
    """TVD effluent face value from the last two cell averages (any equal shapes).

    Limited linear extrapolation c_{N-1} + s(a, g)/2 with a = c_{N-1}-c_{N-2} and
    ghost difference g = a (a >= 0) or g = a*c+/(c+ - a) (a < 0, c+ = max(c_{N-1},0)).
    g -> a smoothly (C1 at a=0) for resolved profiles, recovering the second-order
    extrapolation 1.5c_{N-1}-0.5c_{N-2}, and |s| <= 1.21*c+ for a falling profile,
    so the effluent face value is never negative.
    """
    c = np.atleast_1d(np.asarray(last, dtype=np.float64))
    a, g, _, _ = _outlet_ghost(c, np.atleast_1d(np.asarray(previous, dtype=np.float64)))
    return np.asarray(c + 0.5 * _van_albada(a, g))


def _outlet_face_scalar(last: float, previous: float) -> float:
    """Scalar ``outlet_face_value`` for the right-hand side (same formulas)."""
    a = last - previous
    if a < 0:
        cp = max(last, 0.0)
        g = a * cp / (cp - a) if cp - a > 0 else a * cp
    else:
        g = a
    ab = a * g
    return last + 0.5 * (ab * (a + g) / (a * a + g * g)) if ab > 0 else last


def _outlet_face_derivatives(last: FloatArray, previous: FloatArray) -> tuple[float, float]:
    a, g, g_a, g_c = _outlet_ghost(last, previous)
    s_a, s_b = _van_albada_derivatives(a, g)
    return (float(1 + 0.5 * (s_a + s_b * (g_a + g_c))[0]),
            float(-0.5 * (s_a + s_b * g_a)[0]))


class AxialTransport:
    """Superficial face fluxes of the axial liquid balance, shared by all columns.

    Faces are numbered 0..N (inlet..outlet). The inlet face carries the Danckwerts
    total flux v*c_in (Dirichlet c_in when D_ax=0); the outlet face carries v*c_face
    with zero dispersive flux (Danckwerts outlet). Interior dispersion is central.
    Cell updates are -(F[i+1]-F[i])/(eps*dz) and the cumulative inlet/outlet mass
    rates are area*F[0] and area*F[N], so conservation is exact for either scheme.

    ``upwind1``: c_face = c_upwind (historical first-order scheme).
    ``tvd``: MUSCL reconstruction c_face = c_i + s_i/2, van Albada limiter. Cell 0
    uses the backward difference 2*(c_0 - c_b) to the Danckwerts face value
    c_b = c_in + w*(c_0 - c_in), w = (2 eps D/dz)/(v + 2 eps D/dz), which is the
    Dirichlet value c_in for plug flow; the outlet face uses ``outlet_face_value``.
    """

    def __init__(self, *, cells: int, dz: float, velocity: float, porosity: float,
                 dispersion_m2_s: float, inlet_concentration_kg_m3: float,
                 scheme: AxialScheme = "upwind1") -> None:
        if scheme not in ("upwind1", "tvd"):
            raise ValueError("axial_scheme must be upwind1 or tvd")
        if type(cells) is not int or cells < 2:
            raise ValueError("cells must be an integer >=2")
        self.cells, self.dz, self.velocity = cells, dz, velocity
        self.scheme: AxialScheme = scheme
        self.inlet = inlet_concentration_kg_m3
        self.eps_dispersion = porosity * dispersion_m2_s
        self.diffusion = self.eps_dispersion / dz
        self.inlet_weight = 2 * self.diffusion / (velocity + 2 * self.diffusion)

    @classmethod
    def from_config(cls, config: SimulationConfig, cells: int,
                    scheme: AxialScheme = "upwind1") -> AxialTransport:
        bed, op = config.bed, config.operation
        area = finite_scalar(bed.volume_m3 / bed.length_m, "cross-sectional area")
        return cls(cells=cells, dz=bed.length_m / cells,
                   velocity=finite_scalar(op.flow_m3_s / area, "superficial velocity"),
                   porosity=bed.porosity, dispersion_m2_s=op.axial_dispersion_m2_s,
                   inlet_concentration_kg_m3=op.inlet_concentration_kg_m3, scheme=scheme)

    def _differences(self, c: FloatArray) -> tuple[FloatArray, FloatArray]:
        """Backward/forward differences of cells 0..N-2 (owners of faces 1..N-1)."""
        backward = np.empty(self.cells - 1)
        backward[0] = 2 * (1 - self.inlet_weight) * (c[0] - self.inlet)
        backward[1:] = c[1:-1] - c[:-2]
        return backward, c[1:] - c[:-1]

    def face_values(self, c: FloatArray) -> FloatArray:
        """Advected face concentrations at faces 1..N (face N is the effluent)."""
        if self.scheme == "upwind1":
            return np.array(c, dtype=np.float64, copy=True)
        face = np.empty(self.cells)
        face[:-1] = c[:-1] + 0.5 * _van_albada(*self._differences(c))
        face[-1] = _outlet_face_scalar(float(c[-1]), float(c[-2]))
        return face

    def face_flux(self, c: FloatArray) -> FloatArray:
        """Total superficial flux (kg m^-2 s^-1) at faces 0..N."""
        flux = np.empty(self.cells + 1)
        flux[0] = self.velocity * self.inlet
        if self.scheme == "upwind1":
            # Historical expressions kept verbatim, so trajectories are bitwise unchanged.
            flux[1:self.cells] = (self.velocity * c[:-1]
                                  - self.eps_dispersion * np.diff(c) / self.dz)
            flux[self.cells] = self.velocity * c[-1]
            return flux
        flux[1:] = self.velocity * self.face_values(c)
        flux[1:self.cells] -= self.eps_dispersion * np.diff(c) / self.dz
        return flux

    def face_derivatives(self, c: FloatArray) -> FloatArray:
        """Exact dF_f/dc_{f-2}, dF_f/dc_{f-1}, dF_f/dc_f for faces 0..N, shape (3, N+1).

        The limiter derivative is exact away from its switching set a*b=0, where the
        one-sided value (zero limiter slope) is still a valid Newton direction.
        """
        n, v = self.cells, self.velocity
        d = np.zeros((3, n + 1))
        if self.scheme == "upwind1":
            d[1, 1:] = v
        else:
            ds_da, ds_db = _van_albada_derivatives(*self._differences(c))
            f = np.arange(1, n)
            d[0, f[1:]] = -0.5 * v * ds_da[1:]
            d[1, f] = v * (1 + 0.5 * (ds_da - ds_db))
            d[1, 1] = v * (1 + 0.5 * (2 * (1 - self.inlet_weight) * ds_da[0] - ds_db[0]))
            d[2, f] = 0.5 * v * ds_db
            d_last, d_previous = _outlet_face_derivatives(c[-1:], c[-2:-1])
            d[1, n], d[0, n] = v * d_last, v * d_previous
        d[1, 1:n] += self.diffusion
        d[2, 1:n] -= self.diffusion
        return d

    def stencil(self) -> tuple[IntArray, IntArray, IntArray]:
        """Face, concentration column and derivative slot of each structural nonzero."""
        f = np.arange(self.cells + 1, dtype=np.int64)
        faces, cols, slots = [], [], []
        for slot in ((1, 2) if self.scheme == "upwind1" else (0, 1, 2)):
            col = f - 2 + slot
            keep = (col >= 0) & (col < self.cells) & (f >= 1)
            faces.append(f[keep])
            cols.append(col[keep])
            slots.append(np.full(int(keep.sum()), slot, dtype=np.int64))
        return np.concatenate(faces), np.concatenate(cols), np.concatenate(slots)


def _jacobian_pattern(cells: int, scheme: AxialScheme = "upwind1") -> csc_matrix:
    rows: list[int] = []
    cols: list[int] = []
    lower = 1 if scheme == "upwind1" else 2
    for i in range(cells):
        for j in range(max(0, i - lower), min(cells, i + 2)):
            rows.append(i)
            cols.append(j)
        rows.extend((i, cells + i, cells + i))
        cols.extend((cells + i, i, cells + i))
    outlet = [cells - 1] if scheme == "upwind1" else [cells - 2, cells - 1]
    rows.extend([2 * cells + 1] * len(outlet))
    cols.extend(outlet)
    return csc_matrix((np.ones(len(rows)), (rows, cols)), shape=(2 * cells + 2, 2 * cells + 2))


def effluent_concentration(result: SimulationResult) -> FloatArray:
    """Concentration carried by the outlet face, d(outlet_mass_kg)/dt / Q.

    ``result.outlet_concentration_kg_m3`` is the last cell average, centred at
    z = L - dz/2. For ``upwind1`` both coincide; for ``tvd`` this is the limited
    linear extrapolation to z = L, i.e. the second-order effluent value.
    """
    if result.reactor != "column":
        raise ValueError("effluent_concentration requires a column result")
    scheme = json.loads(result.options_json).get("axial_scheme", "upwind1")
    c = np.asarray(result.concentration_kg_m3, dtype=np.float64)
    if scheme == "upwind1":
        return np.array(c[:, -1], dtype=np.float64)
    return outlet_face_value(c[:, -1], c[:, -2])


def simulate_column(
    config: SimulationConfig,
    *,
    time_s: ArrayLike | None = None,
    options: SolverOptions | None = None,
    code_revision: str = "uncommitted",
) -> SimulationResult:
    """Solve a uniform aqueous column using upwind or TVD FV, dispersion and LDF.

    Constant positive flow/inlet, dry mass basis, one solute and fixed T only.
    HSDM dispatches to its radial solver; it is never replaced by LDF.
    """
    if not isinstance(config, SimulationConfig):
        raise ValueError("config must be a SimulationConfig")
    settings = SolverOptions() if options is None else options
    if not isinstance(settings, SolverOptions):
        raise ValueError("options must be SolverOptions")
    if settings.jacobian == "analytic" and (
        not isinstance(config.kinetics, LDF)
        or not isinstance(config.equilibrium, (Langmuir, Linear))
    ):
        raise ValueError("Analytic Jacobian supports only LDF with Langmuir or Linear")
    if settings.history == "streaming" and not isinstance(config.kinetics, LDF):
        raise ValueError("Streaming history supports LDF columns only")
    if not isinstance(config.kinetics, LDF):
        from .hsdm import simulate_hsdm_column

        return simulate_hsdm_column(
            config, time_s=time_s, options=options, code_revision=code_revision
        )
    times = sample_times(config.operation.duration_s, time_s)
    options_json, fingerprint, manifest = result_metadata(
        config.to_json(), times, settings, "column", code_revision
    )
    bed, op = config.bed, config.operation
    cells = settings.axial_cells
    dz = bed.length_m / cells
    area = finite_scalar(bed.volume_m3 / bed.length_m, "cross-sectional area")
    epsilon, rho_b = bed.porosity, bed.bulk_density_kg_m3
    model = isotherm_from_parameters(config.equilibrium)
    rate = config.kinetics.rate_s_inv
    transport = AxialTransport.from_config(config, cells, settings.axial_scheme)
    upwind = settings.axial_scheme == "upwind1"
    initial = np.concatenate(
        (
            np.full(cells, op.initial_concentration_kg_m3),
            np.full(cells, op.initial_loading_kg_kg),
            np.zeros(2),
        )
    )
    initial_mass = finite_scalar(
        bed.volume_m3
        * (epsilon * op.initial_concentration_kg_m3 + rho_b * op.initial_loading_kg_kg),
        "initial mass",
    )

    def rhs(_time: float, state: FloatArray) -> FloatArray:
        c, q = state[:cells], state[cells : 2 * cells]
        source = rate * (trial_loading(model, c) - q)
        flux = transport.face_flux(c)
        dc = -np.diff(flux) / (epsilon * dz) - (rho_b / epsilon) * source
        # Mass rates use the same face fluxes as the cell updates (Q*c_face = area*F).
        if upwind:
            rates = [op.flow_m3_s * op.inlet_concentration_kg_m3, op.flow_m3_s * c[-1]]
        else:
            rates = [area * flux[0], area * flux[cells]]
        return np.concatenate((dc, source, rates))

    atol = np.concatenate(
        (
            np.full(cells, settings.atol_concentration_kg_m3),
            np.full(cells, settings.atol_loading_kg_kg),
            np.full(2, settings.atol_mass_kg),
        )
    )
    jac = (LDFColumnJacobian(config, cells, transport=None if upwind else transport)
           if settings.jacobian == "analytic" else None)
    pattern = _jacobian_pattern(cells, settings.axial_scheme)

    def inventory(states: FloatArray) -> FloatArray:
        return np.asarray(
            area
            * dz
            * (
                epsilon * np.sum(states[:cells], axis=0)
                + rho_b * np.sum(states[cells : 2 * cells], axis=0)
            )
        )

    if settings.history == "streaming":
        physics = StreamingPhysics(cells=cells, area=area, dz=dz, epsilon=epsilon,
            rho_b=rho_b, initial_mass=initial_mass, options=settings, n_states=initial.size)
        streamed = integrate_streaming(rhs, initial, times, atol, settings,
            pattern, jac=jac, on_state=physics.push_state)
        sampled = streamed.samples
        physics.push_block(sampled, [("sample", i, float(t)) for i, t in enumerate(times)])
        diagnostics = physics.finalize(streamed.nfev, streamed.njev, streamed.nlu,
                                       streamed.accepted_steps)
    else:
        solution = integrate(rhs, initial, times, atol, settings, pattern, jac=jac)
        checked = solution.checkpoints
        diagnostics = check_physics(checked[:cells], checked[cells:2*cells], inventory(checked),
            checked[-2], checked[-1], initial_mass, settings, solution)
        sampled = solution.samples
    mass = inventory(sampled)
    return SimulationResult(
        reactor="column",
        time_s=times,
        concentration_kg_m3=sampled[:cells].T,
        loading_kg_kg=sampled[cells : 2 * cells].T,
        inventory_kg=mass,
        inlet_mass_kg=sampled[-2],
        outlet_mass_kg=sampled[-1],
        mass_residual_kg=mass - initial_mass - sampled[-2] + sampled[-1],
        z_m=np.asarray((np.arange(cells, dtype=np.float64) + 0.5) * dz),
        config_json=config.to_json(),
        options_json=options_json,
        numerical_sha256=fingerprint,
        manifest=manifest,
        diagnostics=diagnostics,
    )
