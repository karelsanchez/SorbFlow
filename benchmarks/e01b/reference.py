"""Independent continuous Danckwerts/Neumann ADE eigenfunction reference.

Coordinates x=z/L and theta=t*v/L; returned concentrations are divided by c_in.
No production SorbFlow equation, matrix or Jacobian is used here.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq


def positive_number(value, name):
    if type(value) not in (int, float) or not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite positive")


@dataclass(frozen=True)
class ADEReference:
    peclet: float
    modes: int = 128

    def __post_init__(self):
        positive_number(self.peclet, "peclet")
        if self.peclet > 50:
            raise ValueError("Reference implemented only for 0<Pe<=50 (conditioning domain)")
        if type(self.modes) is not int or not 2 <= self.modes <= 512:
            raise ValueError("modes must be integer in [2,512]")

    @property
    def h(self):
        return self.peclet / 2

    @property
    def roots(self):
        return np.array(
            [
                brentq(
                    lambda k, n=n: k - 2 * np.arctan2(self.h, k) - n * np.pi,
                    n * np.pi,
                    (n + 1) * np.pi,
                    xtol=1e-13,
                )
                for n in range(self.modes)
            ]
        )

    @property
    def norms(self):
        k, h = self.roots, self.h
        return (
            0.5 * (1 + (h / k) ** 2)
            + (1 - (h / k) ** 2) * np.sin(2 * k) / (4 * k)
            + h * np.sin(k) ** 2 / k**2
        )

    @property
    def coefficients(self):
        k = self.roots
        return -(2 * self.h / (self.h**2 + k**2)) / self.norms

    @property
    def rates(self):
        return self.roots**2 / self.peclet + self.peclet / 4

    def mode(self, x):
        k = self.roots[:, None]
        x = np.asarray(x)[None, :]
        return np.cos(k * x) + self.h / k * np.sin(k * x)

    def _times(self, theta):
        times = np.asarray(theta, dtype=float)
        if (
            times.ndim != 1
            or times.size == 0
            or not np.all(np.isfinite(times))
            or np.any(times <= 0)
        ):
            raise ValueError("theta must be nonempty finite positive vector; t=0 corner excluded")
        return times

    def _points(self, x):
        values = np.asarray(x, dtype=float)
        if (
            values.ndim != 1
            or values.size == 0
            or not np.all(np.isfinite(values))
            or np.any((values < 0) | (values > 1))
        ):
            raise ValueError("x must be nonempty finite vector in [0,1]")
        return values

    def points(self, x, theta):
        x, times = self._points(x), self._times(theta)
        modes = np.exp(self.h * x)[None, :] * self.mode(x)
        return 1 + np.exp(-times[:, None] * self.rates) @ (self.coefficients[:, None] * modes)

    def cell_modes(self, edges):
        edges = self._points(edges)
        if edges.size < 2 or np.any(np.diff(edges) <= 0):
            raise ValueError("Cell edges must strictly increase")
        w = (self.h + 1j * self.roots)[:, None]
        width = np.diff(edges)[None, :]
        integral = np.exp(w * edges[:-1]) * np.expm1(w * width) / w / width
        return integral.real + self.h / self.roots[:, None] * integral.imag

    def averages(self, edges, theta):
        times = self._times(theta)
        return 1 + np.exp(-times[:, None] * self.rates) @ (
            self.coefficients[:, None] * self.cell_modes(edges)
        )

    def checks(self, theta):
        """Closed forms vs quadrature, modal BCs and integrated PDE identity."""
        times = self._times(theta)
        k, h = self.roots, self.h
        right_f = np.cos(k) + h / k * np.sin(k)
        right_df = -k * np.sin(k) + h * np.cos(k)
        bc = float(np.max(abs(right_df + h * right_f) / ((1 + k + h) * (1 + h / k))))
        quad_error = 0.0
        for root, norm, coefficient in zip(k, self.norms, self.coefficients, strict=True):

            def f(x, root=root):
                return np.cos(root * x) + h / root * np.sin(root * x)

            norm_quad = quad(lambda x: f(x) ** 2, 0, 1, epsabs=2e-13, epsrel=2e-13, limit=300)[0]
            projection = quad(
                lambda x: -np.exp(-h * x) * f(x), 0, 1, epsabs=2e-13, epsrel=2e-13, limit=300
            )[0]
            quad_error = max(
                quad_error,
                abs(norm - norm_quad) / max(1, abs(norm_quad)),
                abs(coefficient - projection / norm_quad) / max(1, abs(coefficient)),
            )
        decay = np.exp(-times[:, None] * self.rates)
        derivative_inventory = decay @ (
            -self.rates * self.coefficients * self.cell_modes([0, 1])[:, 0]
        )
        outlet = self.points([1], times)[:, 0]
        return dict(
            mode_boundary_scaled=bc,
            projection_quad_scaled=quad_error,
            reference_mass_identity=float(np.max(abs(derivative_inventory - (1 - outlet)))),
        )
