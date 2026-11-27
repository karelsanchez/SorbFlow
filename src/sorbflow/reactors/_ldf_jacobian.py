"""Sparse derivative of the finite-volume LDF column equations (upwind1 or TVD)."""
from __future__ import annotations

from typing import Protocol

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import csc_matrix

from .._arrays import FloatArray
from ..equilibrium import isotherm_from_parameters
from ..schemas import LDF, Langmuir, Linear, SimulationConfig
from ..units import finite_scalar


class AxialFluxDerivative(Protocol):
    """Face-flux derivative provider, see ``column.AxialTransport``."""

    def face_derivatives(self, c: FloatArray) -> FloatArray: ...

    def stencil(self) -> tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.int64]]: ...


class LDFColumnJacobian:
    """Precomputed CSC structure; no change to fluxes, states or boundary conditions.

    State order is c[0:N], q[0:N], inlet mass, outlet mass. For the odd extension
    used by trial_loading, its slope is q_star_prime(abs(c)), also at zero for
    the supported Langmuir and Linear models. Freundlich is intentionally absent.
    """

    def __init__(self, config: SimulationConfig, cells: int,
                 transport: AxialFluxDerivative | None = None) -> None:
        if (not isinstance(config, SimulationConfig)
                or not isinstance(config.kinetics, LDF)
                or not isinstance(config.equilibrium, (Langmuir, Linear))):
            raise ValueError("Analytic Jacobian supports LDF with Langmuir or Linear only")
        if type(cells) is not int or cells < 2:
            raise ValueError("cells must be an integer >=2")
        bed, operation = config.bed, config.operation
        self.cells = cells
        self.rate = config.kinetics.rate_s_inv
        self.model = isotherm_from_parameters(config.equilibrium)
        self.rho_over_epsilon = bed.bulk_density_kg_m3 / bed.porosity
        dz = bed.length_m / cells
        area = finite_scalar(bed.volume_m3 / bed.length_m, "cross-sectional area")
        v = finite_scalar(operation.flow_m3_s / area, "superficial velocity")
        epsilon, dispersion = bed.porosity, operation.axial_dispersion_m2_s
        i = np.arange(cells)
        rows = np.concatenate((i[1:], i, i[:-1], i, cells+i, cells+i, [2*cells+1]))
        cols = np.concatenate((i[:-1], i, i[1:], cells+i, i, cells+i, [cells-1]))
        self.order = np.lexsort((rows, cols))
        self.rows = rows[self.order]
        self.indptr = np.concatenate(([0], np.cumsum(np.bincount(cols, minlength=2*cells+2))))
        self.sub = np.full(cells-1, (v + epsilon*dispersion/dz)/(epsilon*dz))
        self.sup = np.full(cells-1, dispersion/dz**2)
        incoming = np.where(i >= 1, -epsilon*dispersion/dz, 0.)
        outgoing = np.where(i+1 < cells, v + epsilon*dispersion/dz, v)
        self.transport = (incoming-outgoing)/(epsilon*dz)
        self.cq = np.full(cells, self.rho_over_epsilon*self.rate)
        self.qq = np.full(cells, -self.rate)
        self.mass = np.array([operation.flow_m3_s])
        self.flux_model = transport
        if transport is not None:
            self._init_general(transport, epsilon * dz, area)

    def _init_general(self, transport: AxialFluxDerivative, epsilon_dz: float,
                      area: float) -> None:
        """Assemble the wider (TVD) stencil once; values are summed per call."""
        n = self.cells
        faces, cols, slots = transport.stencil()
        interior = faces < n
        outlet = faces == n
        i = np.arange(n)
        # Face f leaves cell f-1, enters cell f (f<N) and the outlet-mass row (f=N).
        rows = np.concatenate((faces - 1, faces[interior], np.full(int(outlet.sum()), 2*n+1),
                               i, i, n + i, n + i))
        columns = np.concatenate((cols, cols[interior], cols[outlet], i, n + i, i, n + i))
        size = 2*n + 2
        unique, self.inverse = np.unique(columns*size + rows, return_inverse=True)
        self.general_rows = (unique % size).astype(np.int32)
        self.general_indptr = np.concatenate(
            ([0], np.cumsum(np.bincount(unique // size, minlength=size)))).astype(np.int32)
        self.slot_face = (slots, faces)
        self.interior, self.outlet = interior, outlet
        self.scale = np.array([-1/epsilon_dz, 1/epsilon_dz, area])

    def _general(self, state: FloatArray) -> csc_matrix:
        assert self.flux_model is not None
        n = self.cells
        c = state[:n]
        values = self.flux_model.face_derivatives(c)[self.slot_face]
        slope = self.model.derivative(np.abs(c))
        data = np.concatenate((self.scale[0]*values, self.scale[1]*values[self.interior],
                               self.scale[2]*values[self.outlet],
                               -self.rho_over_epsilon*self.rate*slope, self.cq,
                               self.rate*slope, self.qq))
        summed = np.bincount(self.inverse, weights=data, minlength=self.general_rows.size)
        return csc_matrix((summed, self.general_rows, self.general_indptr),
                          shape=(2*n+2, 2*n+2))

    def __call__(self, _time: float, state: FloatArray) -> csc_matrix:
        if self.flux_model is not None:
            return self._general(state)
        slope = self.model.derivative(np.abs(state[:self.cells]))
        diag = self.transport - self.rho_over_epsilon*self.rate*slope
        data = np.concatenate((self.sub, diag, self.sup, self.cq,
                               self.rate*slope, self.qq, self.mass))
        return csc_matrix((data[self.order], self.rows, self.indptr),
                          shape=(2*self.cells+2, 2*self.cells+2))
