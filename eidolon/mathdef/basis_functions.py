

from typing import Tuple
from .compile_support import jit


@jit
def tet_1NL(xi0: float, xi1: float, xi2: float) -> Tuple[float, float, float, float]:
    """
    Tetrahedal linear nodal lagrange basis function. Returned values correspond to coefficients for (xi0, xi1, xi2) at
    coordinates (0,0,0), (1,0,0), (0,1,0), and (0,0,1).
    """
    return 1.0 - xi0 - xi1 - xi2, xi0, xi1, xi2


@jit
def hex_1NL(xi0: float, xi1: float, xi2: float) -> Tuple[float, float, float, float, float, float, float, float]:
    """
    Hexahedal linear nodal lagrange basis function. Returned values correspond to coefficients for (xi0, xi1, xi2) at
    coordinates (0,0,0), (1,0,0), (0,1,0), (1,1,0), (0,0,1), (1,0,1), (0,1,1), and (1,1,1)."""
    xi012: float = xi0 * xi1 * xi2
    xi12: float = xi1 * xi2
    xi01: float = xi0 * xi1
    xi02: float = xi0 * xi2

    return 1.0 - xi0 - xi1 - xi2 + xi01 + xi02 + xi12 - xi012, \
           xi0 - xi01 - xi02 + xi012, \
           xi1 - xi01 - xi12 + xi012, \
           xi01 - xi012, \
           xi2 - xi02 - xi12 + xi012, \
           xi02 - xi012, \
           xi12 - xi012, \
           xi012
