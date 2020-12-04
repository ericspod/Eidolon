import math
import numpy as np
from .mathtypes import vec3, rotator
from .utils import frange

__all__ = [
    "calculate_bound_box", "generate_cylinder", "generate_arrow",
    "generate_axes_arrows", "generate_tri_normals", "add_indices"
]


def calculate_bound_box(vertices):
    """
    Calculates the bound box of the given iterable of vertices. This returns a 6-tuple of the minimum coordinates
    followed the maximum.
    """
    xmin = math.inf
    xmax = -math.inf
    ymin = math.inf
    ymax = -math.inf
    zmin = math.inf
    zmax = -math.inf

    for vert in vertices:
        x, y, z = vert
        xmin = min(xmin, x)
        xmax = max(xmax, x)
        ymin = min(ymin, y)
        ymax = max(ymax, y)
        zmin = min(zmin, z)
        zmax = max(zmax, z)

    return xmin, ymin, zmin, xmax, ymax, zmax


def add_indices(indices, offset):
    result = []

    for ind in indices:
        result.append(tuple(i + offset for i in ind))

    return result


def generate_tri_normals(nodes, indices):
    norms = [vec3.zero for i in nodes]

    for i, (a, b, c) in enumerate(indices):
        norm = nodes[a].plane_norm(nodes[b], nodes[c])
        norms[a] += norm
        norms[b] += norm
        norms[c] += norm

    return [n.norm() for n in norms]


def generate_cylinder(ctrls, radii, refine=0, start_cap=True, end_cap=True, align_rings=True):
    """
    Generate a cylinder using the given control points in `ctrls` to define each cross section. At every location of
    `ctrls` a cross section ring is define for the cylinder with a radius defined in `radii`, and which is rotated to
    orient correctly in the direction the line is going. These two first parameters must have the same length.The
    argument `refine` is used to state the radial refinement level, 0 producing a triangular cylinder. If `start_caps`
    or `end_caps` is true, triangle fans are included defining beginning and end caps over the cylinder respectively.

    If `align_rings` is true, each ring of points is rotated in its plane to orient on a common direction, this
    eliminates twisting of the cylinder at inflection points of the line (or in other situations).
    """
    assert refine >= 0
    assert len(ctrls) >= 2
    assert len(ctrls) == len(radii)
    refine += 3
    align_rings = align_rings and len(ctrls) >= 3

    # calculate the directional vectors as the differences between control points
    dirs = [(ctrls[1] - ctrls[0]).norm()]
    for n in range(1, len(ctrls) - 1):
        d1 = ctrls[n] - ctrls[n - 1]
        d2 = ctrls[n + 1] - ctrls[n]
        dirs.append(((d1 + d2) / 2).norm())

    dirs.append((ctrls[-1] - ctrls[-2]).norm())

    # define a circular ring of points on the XY plane
    ring = [vec3(-i * (math.pi * 2), math.pi / 2, 1.0).from_polar() for i in frange(0.0, 1.0, 1.0 / refine)]

    if align_rings:  # calculate the control point barycenter
        barycenter = sum(ctrls, vec3.zero) / len(ctrls)

    def make_ring(ctrlvec, dirvec, radius):
        """
        Define a ring of nodes centered at `ctrlvec' with radius `radius' lying on the plane whose normal is `dirvec'.
        """
        rot = rotator.between_vecs(vec3(0, 0, 1), dirvec)

        # Rotate the ring in its plane so that the locally rotated X axis is at right
        # angles with a vector towards the barycenter from the ring center.
        if align_rings:  # and dirvec.angleTo(alignplanes[ctrlvec])>0:
            rv = rot * vec3(1, 0, 0)  # rotate X axis
            line = dirvec.cross((barycenter - ctrlvec).norm())
            # rotate the ring in its plane so that the rotated X axis is at right angles with the barycenter
            rot = rotator.between_vecs(rv, line) * rot

        return [ctrlvec + (rot * r * radius) for r in ring]

    nodes = make_ring(ctrls[0], dirs[0], radii[0])  # first ring
    indices = []

    if start_cap:
        # Start cap composed of triangle fan, starting index is center of the fan, next indices are consecutive points
        # on the ring. The expression (i+1)%refine indexes the next point on the ring from point i since the indices
        # have to loop back around to the beginning. Note also that all triangles use counter-clockwise winding.
        indices += [(0, i + 1, (i + 1) % refine + 1) for i in range(refine)]
        nodes = [ctrls[0]] + make_ring(ctrls[0], dirs[0], radii[0]) + nodes  # duplicate first ring

    # cylinder midsections and final ring with triangle indices
    for n in range(1, len(ctrls)):
        for i in range(refine):  # fill in indices
            b = len(nodes) + i
            d = len(nodes) + (i + 1) % refine
            a = b - refine
            c = d - refine
            indices += [(a, b, c), (c, b, d)]

        nodes += make_ring(ctrls[n], dirs[n], radii[n])  # midsection ring of nodes

    if end_cap:  # the ending cap is defined in the same way as the start cap, ie. extra node ring and triangle fan
        ln = len(nodes)
        indices += [(ln + refine, ln + (i + 1) % refine, ln + i) for i in range(refine)]
        nodes += make_ring(ctrls[-1], dirs[-1], radii[-1]) + [ctrls[-1]]

    return nodes, indices


def generate_arrow(refine=1):
    """Generates a +Z pointing arrow centered at the origin occupying a 2*2*2 box using generateCylinder."""

    nodes, indices = generate_cylinder([vec3(0, 0, -1), vec3.zero, vec3(0, 0, 1)], [0.5, 0.5, 1], refine)
    for i in range((3 + refine) * 2):
        nodes[-2 - i] *= vec3(1, 1, 0)  # make the arrow point by moving the last 2 wide rings down to the X-Y plane

    return nodes, indices


def generate_axes_arrows(refine=5, length=10):
    zverts, zinds = generate_arrow(refine)
    zverts = [(v + vec3(0, 0, 1)) * vec3(1, 1, length/2) for v in zverts]

    xr = rotator.from_axis(vec3.Y, math.pi / 2)
    xverts = [xr * v for v in zverts]

    yr = rotator.from_axis(vec3.X, -math.pi / 2)
    yverts = [yr * v for v in zverts]

    verts = xverts + yverts + zverts
    inds = zinds + add_indices(zinds, len(zverts)) + add_indices(zinds, len(zverts) * 2)
    norms = generate_tri_normals(verts, inds)
    colors = [(1, 0, 0, 1)] * len(zverts) + [(0, 1, 0, 1)] * len(zverts) + [(0, 0, 1, 1)] * len(zverts)

    return verts, inds, norms, colors
