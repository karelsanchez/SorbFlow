"""Sparse derivative of the existing upwind finite-volume LDF column equations."""
from __future__ import annotations

import numpy as np
from scipy.sparse import csc_matrix

from .._arrays import FloatArray
from ..equilibrium import isotherm_from_parameters
from ..schemas import LDF, Langmuir, Linear, SimulationConfig
from ..units import finite_scalar


class LDFColumnJacobian:
    """Precomputed CSC structure; no change to fluxes, states or boundary conditions.

    State order is c[0:N], q[0:N], inlet mass, outlet mass. For the odd extension
    used by trial_loading, its slope is q_star_prime(abs(c)), also at zero for
    the supported Langmuir and Linear models. Freundlich is intentionally absent.
    """

    def __init__(self, config: SimulationConfig, cells: int) -> None:
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

    def __call__(self, _time: float, state: FloatArray) -> csc_matrix:
        slope = self.model.derivative(np.abs(state[:self.cells]))
        diag = self.transport - self.rho_over_epsilon*self.rate*slope
        data = np.concatenate((self.sub, diag, self.sup, self.cq,
                               self.rate*slope, self.qq, self.mass))
        return csc_matrix((data[self.order], self.rows, self.indptr),
                          shape=(2*self.cells+2, 2*self.cells+2))
