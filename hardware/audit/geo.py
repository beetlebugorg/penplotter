"""Geometry tools for the audit: meshes, screw axes, radial ray profiles, print orientation.

The audit reads the CAD of the hardware (shape.py, parts.py, fasteners.py, model.py).
It does not change these files."""

import math
import os
import sys

import numpy as np
import trimesh

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HW not in sys.path:
    sys.path.insert(0, HW)

try:  # Embree is about 50 times faster. It needs Python 3.12 (embreex wheels).
    from trimesh.ray.ray_pyembree import RayMeshIntersector
    FAST_RAYS = True
except Exception:  # noqa: BLE001
    from trimesh.ray.ray_triangle import RayMeshIntersector
    FAST_RAYS = False


# The context names of model.ctx_static / ctx_gantry / ctx_carriage that are printed parts, and
# the part names of fasteners.py for them. The audit flags each fastener part with no entry here.
CTX_PART = {
    "left Y carriage": "y_carriage_left",
    "right Y carriage": "y_carriage_right",
    "X idler fork": "x_idler_fork",
    "Y front base": "y_front_left",
    "right Y front base": "y_front_right",
    "Y sled": "y_tensioner_left",
    "right Y sled": "y_tensioner_right",
    "Y back anchor": "y_rear_anchor_left",
    "right Y back anchor": "y_rear_anchor_right",
    "Y chain anchor": "y_chain_anchor",
    "pole foot": "mast_foot",
    "pen carriage": "pen_carriage",
    "X plate": "x_carriage_plate",
    "Y motor bracket": "y_motor_mount_left",
    "right Y motor bracket": "y_motor_mount_right",
    "Y idler fork": "y_idler_fork_left",
    "Y idler bracket": "y_idler_bracket_left",
    "right Y idler bracket": "y_idler_bracket_right",
    "right Y idler fork": "y_idler_fork_right",
    "slider": "pen_slider",
}

# The STL file (stl/<name>.stl) of each part. The left and right copies of a part share one file
# unless the file of the side exists.
def stl_name(part):
    for n in (part, part.replace("_left", "").replace("_right", "")):
        if os.path.exists(os.path.join(HW, "stl", n + ".stl")):
            return n
    return None


def to_mesh(shape, tol=0.03, ang=0.2):
    try:
        v, t = shape.tessellate(tol, ang)
        m = trimesh.Trimesh(np.array([(p.X, p.Y, p.Z) for p in v]), np.array(t), process=True)
    except Exception:  # noqa: BLE001
        # Some faces do not tessellate in place: export an STL and read it back.
        import tempfile
        from build123d import export_stl
        with tempfile.NamedTemporaryFile(suffix=".stl") as fh:
            export_stl(shape, fh.name, tolerance=tol, angular_tolerance=ang)
            m = trimesh.load(fh.name)
    m.merge_vertices()
    return m


class Body:
    """One solid of the assembly: its name, solid, mesh and ray engine."""

    def __init__(self, name, solid, part=None, tol=0.03):
        self.name, self.solid, self.part = name, solid, part
        self.mesh = to_mesh(solid, tol)
        self.rays = RayMeshIntersector(self.mesh)
        self.lo, self.hi = self.mesh.bounds

    def near(self, lo, hi, pad=0.0):
        return bool(np.all(self.lo - pad <= hi) and np.all(lo <= self.hi + pad))

    def inside(self, pts):
        pts = np.atleast_2d(pts)
        if not self.mesh.is_watertight:
            if self.solid is not None:
                return np.array([self.solid.is_inside(tuple(p)) for p in pts])
            # A moved copy with an open mesh: count the hits of a ray (odd: inside).
            hs = hits_along(self, pts, np.tile([0.577, 0.577, 0.578], (len(pts), 1)))
            return np.array([len(h) % 2 == 1 for h in hs])
        return self.mesh.contains(pts)


def basis(d):
    d = np.asarray(d, float)
    d = d / np.linalg.norm(d)
    a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(d, a)
    u /= np.linalg.norm(u)
    v = np.cross(d, u)
    return d, u, v


def hits_along(body, origins, dirs, tmax=1e9):
    """For each ray, the sorted distances of its hits with the mesh (close duplicates removed)."""
    out = [[] for _ in range(len(origins))]
    if len(origins) == 0:
        return out
    loc, ir, _ = body.rays.intersects_location(origins, dirs, multiple_hits=True)
    if len(loc):
        t = np.einsum("ij,ij->i", loc - origins[ir], dirs[ir])
        for k, tt in zip(ir, t):
            if 1e-6 < tt < tmax:
                out[k].append(tt)
    for k in range(len(out)):
        s = sorted(out[k])
        ded = []
        for x in s:
            if not ded or x - ded[-1] > 2e-3:
                ded.append(x)
        out[k] = ded
    return out


def radial_profile(body, p0, d, s_values, n_ang=24, rmax=40.0):
    """Cast rays out from the axis (p0, d) at each depth s and each angle.
    Returns r_in[s, a] (where the material starts; 0 if the axis point is in the material; inf if
    no material) and r_out[s, a] (where the first band of material ends)."""
    d, u, v = basis(d)
    ang = np.linspace(0, 2 * math.pi, n_ang, endpoint=False)
    dirs1 = np.array([math.cos(a) * u + math.sin(a) * v for a in ang])
    pts = np.array([np.asarray(p0) + s * d for s in s_values])
    inside = body.inside(pts)
    origins = np.repeat(pts, n_ang, axis=0)
    dirs = np.tile(dirs1, (len(pts), 1))
    hs = hits_along(body, origins, dirs, rmax)
    r_in = np.full((len(pts), n_ang), np.inf)
    r_out = np.full((len(pts), n_ang), np.inf)
    for i in range(len(pts)):
        for j in range(n_ang):
            h = hs[i * n_ang + j]
            if inside[i]:
                r_in[i, j] = 0.0
                r_out[i, j] = h[0] if h else rmax
            elif h:
                r_in[i, j] = h[0]
                r_out[i, j] = h[1] if len(h) > 1 else rmax
    return r_in, r_out, inside, ang


def axial_free(bodies, p0, d, radius, n=12, tmax=200.0):
    """The free length along d from the plane through p0, for a cylinder of the given radius:
    the shortest hit of rays parallel to d from the centre and from n points on the circle."""
    d, u, v = basis(d)
    pts = [np.asarray(p0, float)]
    for a in np.linspace(0, 2 * math.pi, n, endpoint=False):
        pts.append(np.asarray(p0) + radius * (math.cos(a) * u + math.sin(a) * v))
    pts = np.array(pts)
    dirs = np.tile(d, (len(pts), 1))
    best, who = tmax, None
    lo = pts.min(axis=0) - radius
    hi = pts.max(axis=0) + tmax * np.abs(d) + radius
    hi = np.maximum(hi, (pts + tmax * d).max(axis=0) + radius)
    lo = np.minimum(lo, (pts + tmax * d).min(axis=0) - radius)
    for b in bodies:
        if not b.near(lo, hi):
            continue
        for h in hits_along(b, pts, dirs, tmax):
            if h and h[0] < best:
                best, who = h[0], b.name
        ins = b.inside(pts)
        if np.any(ins):
            best, who = 0.0, b.name
    return best, who


def cyl_axis(solid, r_hint):
    """The axis of the cylinder face of solid with the radius nearest r_hint: (point, dir, face)."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from build123d import GeomType
    best = None
    for f in solid.faces():
        if f.geom_type != GeomType.CYLINDER:
            continue
        cy = BRepAdaptor_Surface(f.wrapped).Cylinder()
        r = cy.Radius()
        if best is None or abs(r - r_hint) < abs(best[0] - r_hint):
            ax = cy.Axis()
            best = (r, np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()]),
                    np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()]), f)
    return best


def extent_along(solid, p0, d):
    """The range of the projection of the solid's vertices on the axis (p0, d)."""
    pts = np.array([(v.X, v.Y, v.Z) for v in solid.vertices()])
    if len(pts) == 0:
        bb = solid.bounding_box()
        pts = np.array([(bb.min.X, bb.min.Y, bb.min.Z), (bb.max.X, bb.max.Y, bb.max.Z)])
    s = (pts - p0) @ d
    return float(s.min()), float(s.max())


def dist_to_axis(pt, p0, d):
    w = np.asarray(pt) - p0
    return float(np.linalg.norm(w - (w @ d) * d))


# The 24 rotations that keep the axes on the axes.
def _rotations():
    out = []
    for perm in ((0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)):
        for sg in ((1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1), (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1)):
            r = np.zeros((3, 3))
            for i in range(3):
                r[i, perm[i]] = sg[i]
            if np.linalg.det(r) > 0:
                out.append(r)
    return out


ROTS = _rotations()


def print_up(world_mesh, part):
    """The print +Z direction in frame coordinates, read from stl/<part>.stl: the rotation (of the
    24 axis rotations, with or without the mirror image) that best puts the part mesh on the STL.
    Returns (up vector, mean distance in mm, stl name) or (None, None, None)."""
    from scipy.spatial import cKDTree
    n = stl_name(part)
    if n is None:
        return None, None, None
    stl = trimesh.load(os.path.join(HW, "stl", n + ".stl"))
    tree = cKDTree(stl.sample(20000))
    pts = world_mesh.sample(1500, return_index=False) if len(world_mesh.faces) else world_mesh.vertices
    best = (1e9, None)
    for mir in (1.0, -1.0):
        p = pts * np.array([mir, 1, 1])
        for r in ROTS:
            q = p @ r.T
            lo, hi = q.min(axis=0), q.max(axis=0)
            q = q - np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
            slo, shi = stl.bounds
            q = q + np.array([(slo[0] + shi[0]) / 2, (slo[1] + shi[1]) / 2, slo[2]])
            dd = tree.query(q)[0].mean()
            if dd < best[0]:
                best = (dd, (r, mir))
    r, mir = best[1]
    # Print +Z in world: the world vector w with (M w) mapped by r to (0, 0, 1).
    up = r.T @ np.array([0, 0, 1.0])
    up = up * np.array([mir, 1, 1])
    return up, best[0], n
