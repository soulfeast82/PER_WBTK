"""Build Mode window reveals face the street, on every side of every block.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" ^
        -b --factory-startup --python tests/test_buildmode_reveal.py

NOT imported by the addon. Works in a temp folder; never writes to the repo.
Exit code 0 only when every check passes.

Two free-standing 4 x 4 x 3.5 m blocks, all four faces WINDOW:
  A at (0, 0, 0)   - the spot the old left/right guess was written for
  B at (10, 6, 0)  - anywhere else, where the guess goes wrong on the west face
Each face gets a row of 2 windows (1 x 1 m, sill 1 m, centred 1 m and 3 m along it).

For every window, looking only at faces that lie inside the opening and are parallel
to the wall:
  G  the glass sits inside the wall's inner half (offset from the wall's centre line,
     measured toward the street, between -thickness/2 and 0: so not poking into the
     room either), and its normal faces the street. Expected: -0.09 m, a 19 cm reveal.
  O  nothing sits on the street half: the reveal is open to the street.
Checked on Generate (the final mesh) and on the live-preview BMesh.
  D  block C at (20, -10): RECESSED doors on south and west, inset 0.1 m. Both jambs
     of each door sit on the street half. Generate only: the preview builds FLAT doors.
"""
import os
import sys
import tempfile

import bpy
import addon_utils

TOL = 0.0005
results = []


def check(label, cond, detail=""):
    results.append((label, bool(cond)))
    print("%s  %s%s" % ("PASS" if cond else "FAIL", label, ("   [%s]" % detail) if detail else ""))


mod = addon_utils.enable("PER_WBTK", default_set=True)
if mod is None:
    print("FAIL  PER_WBTK did not enable")
    sys.exit(1)
print("addon:", mod.__file__, "| Blender", bpy.app.version_string)
from PER_WBTK import bm_data, bm_generate                      # noqa: E402
from PER_WBTK.config import Config                             # noqa: E402

tmp = tempfile.mkdtemp(prefix="wbtk_bm_reveal_")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(tmp, "bm_reveal.blend"))
scene = bpy.context.scene

W = D = 4.0
H = 3.5
ALL_WINDOWS = {"north": "WINDOW", "south": "WINDOW", "east": "WINDOW", "west": "WINDOW"}
BLOCKS = {"A": (0.0, 0.0), "B": (10.0, 6.0)}
for _name, (x, y) in BLOCKS.items():
    data = dict(bm_data.DEFAULT_BLOCK)
    data.update({"w": W, "d": D, "h": H, "walls": dict(ALL_WINDOWS), "chamfers": []})
    bm_data.create((x, y, 0.0), data)

# Block C: RECESSED doors on south and west, inset 0.1 m (half the wall), so the
# jambs only fill one half of the wall and show which side the recess opens to.
DOOR_BLOCK = (20.0, -10.0)
_c = dict(bm_data.DEFAULT_BLOCK)
_c.update({"w": W, "d": D, "h": H, "chamfers": [],
           "walls": {"north": "SOLID", "south": "DOOR", "east": "SOLID", "west": "DOOR"}})
bm_data.create((DOOR_BLOCK[0], DOOR_BLOCK[1], 0.0), _c)
# Chamfer blocks (2026-11-11): 6 x 6 m, all four corners cut 1.5 m, so each diagonal
# wall is 2.12 m long. D: every wall WINDOW. E: every wall DOOR (recessed, inset 0.1).
CW = 6.0
CS = 1.5
CHAMFER_BLOCKS = {"D": (30.0, 0.0), "E": (40.0, 0.0)}
for _name, (x, y) in CHAMFER_BLOCKS.items():
    _t = "WINDOW" if _name == "D" else "DOOR"
    data = dict(bm_data.DEFAULT_BLOCK)
    data.update({"w": CW, "d": CW, "h": H, "chamfers": ["sw", "se", "ne", "nw"],
                 "chamfer_size": CS, "walls": {f: _t for f in ("north", "south", "east", "west")}})
    bm_data.create((x, y, 0.0), data)

scene.wbtk_building_door_style = 'RECESSED'
scene.wbtk_building_door_inset = 0.1

HALF = Config.WALL_THICKNESS / 2.0
SILL = Config.WINDOW_SILL_HEIGHT
WIN_CENTRES = (1.0, 3.0)      # 2 windows: int(4 / (1.0 + 0.8)) = 2, segments of 2 m
WIN_W = WIN_H = 1.0


def faces_to_check(x0, y0):
    """(label, outward unit (ox, oy), wall centre line value, along-axis origin)."""
    return [
        ("south", (0.0, -1.0), y0,     x0),
        ("north", (0.0, 1.0),  y0 + D, x0),
        ("west",  (-1.0, 0.0), x0,     y0),
        ("east",  (1.0, 0.0),  x0 + W, y0),
    ]


def scan(polys, where):
    """polys: list of (centre Vector, normal Vector) in world space."""
    for bname, (x0, y0) in BLOCKS.items():
        for face, (ox, oy), line, start in faces_to_check(x0, y0):
            along = 0 if ox == 0.0 else 1           # south/north run along X, west/east along Y
            depth = 1 if ox == 0.0 else 0
            sign = oy if ox == 0.0 else ox
            for wc in WIN_CENTRES:
                a0 = start + wc - WIN_W / 2 + TOL
                a1 = start + wc + WIN_W / 2 - TOL
                z0 = SILL + TOL
                z1 = SILL + WIN_H - TOL
                glass, street = [], []
                for c, n in polys:
                    if not (a0 < c[along] < a1 and z0 < c.z < z1):
                        continue
                    if abs(n[depth]) < 0.99:
                        continue                    # not parallel to the wall
                    off = (c[depth] - line) * sign  # + = toward the street
                    if abs(off) > HALF + 0.05:
                        continue                    # some other wall
                    if off > -TOL:
                        street.append(off)
                    else:
                        glass.append((off, n[depth] * sign))
                tag = "%s %s %s win@%.0f" % (where, bname, face, wc)
                check("G %s glass inside the wall's inner half, facing the street" % tag,
                      len(glass) >= 1
                      and all(-HALF + TOL < o < 0 and f > 0.99 for o, f in glass),
                      "glass offsets/facing %s" % [("%.3f" % o, "%.2f" % f) for o, f in glass])
                check("O %s nothing on the street half" % tag,
                      not street, "street-side offsets %s" % ["%.3f" % o for o in street])


def scan_doors(polys, where):
    """D: each recessed door's two jambs sit on the street half of the wall."""
    x0, y0 = DOOR_BLOCK
    dw = scene.wbtk_building_door_width
    dh = scene.wbtk_building_door_height
    for face, (ox, oy), line, start in faces_to_check(x0, y0):
        if face not in ("south", "west"):
            continue
        along = 0 if ox == 0.0 else 1
        depth = 1 if ox == 0.0 else 0
        sign = oy if ox == 0.0 else ox
        edges = (start + W / 2 - dw / 2, start + W / 2 + dw / 2)
        offs = []
        for c, n in polys:
            if abs(n[along]) < 0.99 or not (0 < c.z < dh):
                continue
            if min(abs(c[along] - e) for e in edges) > TOL:
                continue
            off = (c[depth] - line) * sign
            if abs(off) > HALF + 0.05 or abs(off) < 0.01:
                continue                            # other walls / full-depth wall caps
            offs.append(off)
        check("D %s C %s door jambs on the street half" % (where, face),
              len(offs) == 2 and all(0 < o < HALF for o in offs),
              "jamb offsets %s" % ["%.3f" % o for o in offs])


def chamfer_walls(bname):
    """(label, mid (x, y), along unit (ux, uy), outward unit (ox, oy)) per diagonal."""
    x0, y0 = CHAMFER_BLOCKS[bname]
    out = []
    for corner, (cx, cy) in (("sw", (x0, y0)), ("se", (x0 + CW, y0)),
                             ("ne", (x0 + CW, y0 + CW)), ("nw", (x0, y0 + CW))):
        sx = 1.0 if cx > x0 else -1.0                 # corner direction from the centre
        sy = 1.0 if cy > y0 else -1.0
        r = 2 ** -0.5
        mid = (cx - sx * CS / 2, cy - sy * CS / 2)
        out.append((corner, mid, (-sy * r, sx * r), (sx * r, sy * r)))
    return out


def _frame(c, mid, u, o):
    along = (c.x - mid[0]) * u[0] + (c.y - mid[1]) * u[1]
    off = (c.x - mid[0]) * o[0] + (c.y - mid[1]) * o[1]     # + = toward the street
    return along, off


def scan_chamfer_windows(polys, where):
    """G / O on each diagonal window of block D (one centred 1 x 1 m window)."""
    for corner, mid, u, o in chamfer_walls("D"):
        glass, street = [], []
        for c, n in polys:
            along, off = _frame(c, mid, u, o)
            if not (abs(along) < WIN_W / 2 - TOL and SILL + TOL < c.z < SILL + WIN_H - TOL):
                continue
            facing = n.x * o[0] + n.y * o[1]
            if abs(facing) < 0.99 or abs(off) > HALF + 0.05:
                continue
            if off > -TOL:
                street.append(off)
            else:
                glass.append((off, facing))
        tag = "%s D %s chamfer" % (where, corner)
        check("G %s glass inside the wall's inner half, facing the street" % tag,
              len(glass) >= 1 and all(-HALF + TOL < g < 0 and f > 0.99 for g, f in glass),
              "glass offsets/facing %s" % [("%.3f" % g, "%.2f" % f) for g, f in glass])
        check("O %s nothing on the street half" % tag,
              not street, "street-side offsets %s" % ["%.3f" % s for s in street])


def scan_chamfer_doors(polys, where):
    """D on each diagonal door of block E: both jambs on the street half."""
    dw = scene.wbtk_building_door_width
    dh = scene.wbtk_building_door_height
    for corner, mid, u, o in chamfer_walls("E"):
        offs = []
        for c, n in polys:
            if abs(n.x * u[0] + n.y * u[1]) < 0.99 or not (0 < c.z < dh):
                continue
            along, off = _frame(c, mid, u, o)
            if abs(abs(along) - dw / 2) > TOL:
                continue
            if abs(off) > HALF + 0.05 or abs(off) < 0.01:
                continue
            offs.append(off)
        check("D %s E %s chamfer door jambs on the street half" % (where, corner),
              len(offs) == 2 and all(0 < f < HALF for f in offs),
              "jamb offsets %s" % ["%.3f" % f for f in offs])


# ---------------------------------------------------------------- Generate
master, wall = bm_generate.generate_full(scene)
check("Generate made a wall object", wall is not None)
if wall is not None:
    mw = wall.matrix_world
    rot = mw.to_3x3()
    polys = [(mw @ p.center, (rot @ p.normal).normalized()) for p in wall.data.polygons]
    scan(polys, "gen")
    scan_doors(polys, "gen")
    scan_chamfer_windows(polys, "gen")
    scan_chamfer_doors(polys, "gen")

# ---------------------------------------------------------------- Live preview
bm = bm_generate.build_preview_bm(scene)
import bmesh                                                   # noqa: E402
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.005)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
polys = [(f.calc_center_median(), f.normal.copy()) for f in bm.faces]
bm.free()
scan(polys, "preview")
scan_chamfer_windows(polys, "preview")
# No door check here: the live preview always builds FLAT doors (no jambs).

passed = sum(1 for _l, ok in results if ok)
total = len(results)
print("BUILDMODE REVEAL %s  %d/%d" % ("PASSED" if passed == total else "FAILED", passed, total))
sys.exit(0 if passed == total else 1)
