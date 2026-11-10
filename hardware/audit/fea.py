"""Linear-elastic FEA of the critical printed parts: gmsh meshes the STEP file, scikit-fem solves.
Run: uv run --no-project --python 3.12 --with gmsh --with scikit-fem --with matplotlib --with pyamg --with pypardiso python fea.py spec.json
The spec gives, for each part: the STEP file, the fixtures, the loads, the probe regions and the
print +Z direction. The script writes <out>/fea.json and one PNG for each part.

Model: 10-node tetrahedra (quadratic), solid PLA (no infill), small strain. The loads are
tractions on the selected faces. The fixtures hold the selected faces. A fixed face makes a
stress peak at its edge: the report gives the max away from the fixtures."""

import json
import math
import os
import sys
import time

import numpy as np


def mesh_step(path, h):
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("Geometry.OCCFixDegenerated", 1)
    gmsh.option.setNumber("Geometry.OCCFixSmallEdges", 1)
    gmsh.option.setNumber("Geometry.OCCFixSmallFaces", 1)
    gmsh.option.setNumber("Geometry.Tolerance", 1e-3)
    gmsh.model.occ.importShapes(path)
    gmsh.model.occ.synchronize()
    gmsh.option.setNumber("Mesh.MeshSizeMax", h)
    gmsh.option.setNumber("Mesh.MeshSizeMin", h / 4)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 6)
    gmsh.option.setNumber("Mesh.Algorithm3D", 10)
    gmsh.option.setNumber("Mesh.ElementOrder", 1)
    gmsh.model.mesh.generate(3)
    ntags, coords, _ = gmsh.model.mesh.getNodes()
    xyz = coords.reshape(-1, 3)
    idx = {t: i for i, t in enumerate(ntags)}
    tets = []
    for et, tags, nodes in zip(*gmsh.model.mesh.getElements(3)):
        if et == 4:
            tets.append(np.array([idx[n] for n in nodes]).reshape(-1, 4))
    gmsh.finalize()
    t = np.vstack(tets)
    used = np.unique(t)
    remap = -np.ones(len(xyz), int)
    remap[used] = np.arange(len(used))
    return xyz[used], remap[t]


def region_mask(x, r):
    """x: (3, n) points. True where the point is in the region r."""
    if r["type"] == "box":
        lo, hi = np.array(r["lo"])[:, None], np.array(r["hi"])[:, None]
        return np.all((x >= lo) & (x <= hi), axis=0)
    p = np.array(r["p"])[:, None]
    d = np.array(r["d"]) / np.linalg.norm(r["d"])
    w = x - p
    s = d @ w
    rad = np.linalg.norm(w - np.outer(d, s), axis=0)
    m = (s >= r["s0"] - 0.3) & (s <= r["s1"] + 0.3) & (rad <= r["r"])
    if r.get("half") and "F" in r:
        f = np.array(r["F"])
        f = f - (f @ d) * d
        if np.linalg.norm(f) > 0:
            m &= (f @ (w - np.outer(d, s))) > 0.0
    return m


def solve_amg(ib, K, f, D):
    """Smoothed aggregation AMG with the six rigid body modes, CG accelerated."""
    import pyamg
    N = ib.N
    free = np.setdiff1d(np.arange(N), D)
    x = ib.doflocs                      # (3, N)
    comp = np.zeros(N, int)
    dofs = ib.get_dofs()
    for c in range(3):
        comp[dofs.all([f"u^{c + 1}"])] = c
    B = np.zeros((N, 6))
    for c in range(3):
        B[comp == c, c] = 1.0
    xc = x - x.mean(axis=1, keepdims=True)
    # Rotations about x, y, z: u = w x r.
    for k, (i, j) in enumerate(((1, 2), (2, 0), (0, 1))):
        B[comp == i, 3 + k] = -xc[j, comp == i]
        B[comp == j, 3 + k] = xc[i, comp == j]
    A = K[free][:, free].tocsr()
    b = f[free]                          # (n_free, n_cases)
    try:
        import glob
        roots = {sys.prefix} | {os.path.abspath(os.path.join(p, "..", "..", "..")) for p in sys.path if "site-packages" in p}
        lib = sorted(f for r in roots for f in glob.glob(os.path.join(r, "lib", "libmkl_rt.so*")))
        if lib:
            os.environ.setdefault("PYPARDISO_MKL_RT", lib[0])
        import pypardiso
        u = np.zeros((N, b.shape[1]))
        u[free] = pypardiso.spsolve(A, np.ascontiguousarray(b)).reshape(len(free), -1)
        return [u[:, k] for k in range(b.shape[1])]
    except ImportError:
        pass
    ml = pyamg.smoothed_aggregation_solver(A, B=B[free], max_coarse=500)
    out = []
    for k in range(b.shape[1]):
        u = np.zeros(N)
        if np.any(b[:, k]):
            u[free] = ml.solve(b[:, k], tol=1e-8, accel="cg", maxiter=400)
        out.append(u)
    return out


def solve(spec, part, out):
    from skfem import (Basis, ElementTetP2, ElementVector, FacetBasis, LinearForm, MeshTet, asm, condense,
                       solve as fsolve)
    from skfem.helpers import dot
    from skfem.models.elasticity import lame_parameters, linear_elasticity
    t0 = time.time()
    E, nu = spec["E"], spec["nu"]
    xyz, tets = mesh_step(part["step"], part.get("h", 3.0))
    m = MeshTet(xyz.T.copy(), tets.T.copy())
    print(f"  {part['name']}: mesh {m.t.shape[1]} tets in {time.time() - t0:.0f} s", file=sys.stderr, flush=True)
    e = ElementVector(ElementTetP2())
    ib = Basis(m, e, intorder=2)
    K = asm(linear_elasticity(*lame_parameters(E, nu)), ib)
    f = np.zeros(ib.N)
    bnd = m.boundary_facets()
    fmid = m.p[:, m.facets[:, bnd]].mean(axis=1)
    info = {"nodes": int(m.p.shape[1]), "tets": int(m.t.shape[1]), "dofs": int(ib.N), "loads": [], "fixtures": []}
    load_facets = []
    f_op = np.zeros(ib.N)
    for ld in part.get("op_loads", []):
        sel = bnd[region_mask(fmid, ld)]
        if len(sel) == 0:
            continue
        fb = FacetBasis(m, e, facets=sel, intorder=3)
        tr = np.array(ld["F"]) / float(fb.dx.sum())

        @LinearForm
        def trac_op(v, w, tr=tr):
            return tr[0] * v.value[0] + tr[1] * v.value[1] + tr[2] * v.value[2]
        f_op += asm(trac_op, fb)
    for ld in part["loads"]:
        sel = bnd[region_mask(fmid, ld)]
        if len(sel) == 0:
            info["loads"].append({"name": ld["name"], "facets": 0})
            continue
        fb = FacetBasis(m, e, facets=sel, intorder=3)
        area = float(fb.dx.sum())
        tr = np.array(ld["F"]) / area

        @LinearForm
        def trac(v, w, tr=tr):
            return tr[0] * v.value[0] + tr[1] * v.value[1] + tr[2] * v.value[2]
        f += asm(trac, fb)
        load_facets.append(sel)
        info["loads"].append({"name": ld["name"], "facets": int(len(sel)), "area": area, "F": ld["F"]})
    D = []
    fix_facets = []
    for fx in part["fix"]:
        sel = bnd[region_mask(fmid, fx)]
        info["fixtures"].append({"name": fx["name"], "facets": int(len(sel))})
        if len(sel) == 0:
            continue
        dofs = ib.get_dofs(facets=sel)
        for c in fx["dofs"]:
            D.append(dofs.all([f"u^{c + 1}"]))
        fix_facets.append(sel)
    D = np.unique(np.concatenate(D)) if D else np.array([], int)
    print(f"  {part['name']}: assembled {ib.N} dofs in {time.time() - t0:.0f} s", file=sys.stderr, flush=True)
    if len(D) == 0:
        return {"error": "no fixture"}
    u, u_op = solve_amg(ib, K, np.column_stack([f, f_op]), D)
    print(f"  {part['name']}: solved in {time.time() - t0:.0f} s", file=sys.stderr, flush=True)
    # The stress at the element centres (the gradient of P2 is linear: the mean over the quadrature points).
    from skfem import ElementTetP0
    from skfem.helpers import sym_grad
    lam, mu = lame_parameters(E, nu)
    uu = ib.interpolate(u)
    eps = sym_grad(uu)
    tr = eps[0, 0] + eps[1, 1] + eps[2, 2]
    sig = 2 * mu * eps + lam * np.einsum("ij,...->ij...", np.eye(3), tr)
    sig = sig.mean(axis=-1)        # (3, 3, n_el)
    s = sig
    vm = np.sqrt(0.5 * ((s[0, 0] - s[1, 1]) ** 2 + (s[1, 1] - s[2, 2]) ** 2 + (s[2, 2] - s[0, 0]) ** 2) +
                 3 * (s[0, 1] ** 2 + s[1, 2] ** 2 + s[0, 2] ** 2))
    # The max principal stress and its direction (for the layer check).
    S = np.moveaxis(sig, -1, 0)
    w, v = np.linalg.eigh(S)
    s1 = w[:, -1]
    n1 = v[:, :, -1]
    up = np.array(part["up"]) / np.linalg.norm(part["up"])
    zf = np.abs(n1 @ up)
    xy, z = spec["pla_xy"], spec["pla_z"]
    strength = 1.0 / np.sqrt(((np.sqrt(1 - zf ** 2)) / xy) ** 2 + (zf / z) ** 2)
    # Elements away from the fixtures (2 mm): the fixed edges give a false peak.
    cen = m.p[:, m.t].mean(axis=1)
    near = np.zeros(m.t.shape[1], bool)
    if fix_facets:
        fp = m.p[:, np.unique(m.facets[:, np.concatenate(fix_facets)])]
        from scipy.spatial import cKDTree
        dd, _ = cKDTree(fp.T).query(cen.T)
        near = dd < 2.0
    away = ~near
    vm_a = np.where(away, vm, 0)
    k = int(np.argmax(vm_a))
    ratio = np.where(away, np.maximum(s1, 0) / strength, 0)
    kr = int(np.argmax(ratio))
    # The displacement at the nodes.
    un = u[ib.nodal_dofs].T                    # (n_nodes, 3)
    umag = np.linalg.norm(un, axis=1)
    uop = np.linalg.norm(u_op[ib.nodal_dofs].T, axis=1)
    probes = []
    for pr in part.get("probes", []):
        msk = region_mask(m.p, pr)
        val = float(uop[msk].max()) if msk.any() else float("nan")
        worst = float(umag[msk].max()) if msk.any() else float("nan")
        probes.append({"name": pr["name"], "max_disp": val, "worst_disp": worst, "limit": pr.get("limit"),
                       "nodes": int(msk.sum())})
    res = {
        **info,
        "vm_max": float(vm.max()), "vm_max_away": float(vm_a[k]), "vm_at": cen[:, k].tolist(),
        "vm_p99": float(np.percentile(vm[away], 99)) if away.any() else float(vm.max()),
        "s1_crit": float(s1[kr]), "s1_crit_zfrac": float(zf[kr]), "s1_crit_strength": float(strength[kr]),
        "sf_layers": float(1.0 / ratio[kr]) if ratio[kr] > 0 else float("inf"),
        "sf_vm": float(xy / vm_a[k]) if vm_a[k] > 0 else float("inf"),
        "disp_max": float(umag.max()), "probes": probes, "seconds": round(time.time() - t0, 1),
    }
    res["png"] = plot(m, vm, umag, part, out, res, load_facets, fix_facets)
    return res


def plot(m, vm, umag, part, out, res, load_facets, fix_facets):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    bf = m.boundary_facets()
    el = m.f2t[0, bf]
    tri = m.p[:, m.facets[:, bf]].transpose(2, 1, 0)       # (n, 3 nodes, 3 xyz)
    vals = vm[el]
    vmax = max(np.percentile(vals, 99.5), 1e-6)
    cmap = plt.get_cmap("turbo")
    fig = plt.figure(figsize=(13, 6.2))
    lo, hi = m.p.min(axis=1), m.p.max(axis=1)
    c = (lo + hi) / 2
    r = (hi - lo).max() / 2
    for i, (elev, azim) in enumerate(((25, -60), (25, 120))):
        ax = fig.add_subplot(1, 2, i + 1, projection="3d")
        col = Poly3DCollection(tri, facecolors=cmap(np.clip(vals / vmax, 0, 1)), edgecolors="none", linewidths=0)
        ax.add_collection3d(col)
        for sel, colr in ((load_facets, "magenta"), (fix_facets, "black")):
            for s in sel:
                p = m.p[:, m.facets[:, s]].mean(axis=1)
                ax.scatter(p[0], p[1], p[2], s=1, c=colr, depthshade=False)
        ax.set_xlim(c[0] - r, c[0] + r)
        ax.set_ylim(c[1] - r, c[1] + r)
        ax.set_zlim(c[2] - r, c[2] + r)
        ax.view_init(elev, azim)
        ax.set_box_aspect((1, 1, 1))
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_zlabel("z")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, vmax))
    fig.colorbar(sm, ax=fig.axes, shrink=0.7, label="von Mises stress (MPa)")
    fig.suptitle(f"{part['name']}: max {res['vm_max_away']:.1f} MPa away from the fixtures, "
                 f"max displacement {res['disp_max'] * 1000:.0f} um (black: fixed, magenta: loads)")
    path = os.path.join(out, f"fea_{part['name']}.png")
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return os.path.basename(path)


def main():
    spec = json.load(open(sys.argv[1]))
    out = spec["out"]
    os.makedirs(out, exist_ok=True)
    results = {}
    for part in spec["parts"]:
        try:
            results[part["name"]] = solve(spec, part, out)
        except Exception as ex:  # noqa: BLE001
            results[part["name"]] = {"error": f"{type(ex).__name__}: {ex}"}
        print(part["name"], json.dumps({k: v for k, v in results[part["name"]].items() if k not in ("loads", "fixtures")}),
              flush=True)
    json.dump(results, open(os.path.join(out, "fea.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
