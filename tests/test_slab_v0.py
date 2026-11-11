"""Gate B for Slab v0 (CLAUDE_SLAB_V0_SPEC.md section 3): Blender writes the joints correctly.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" ^
        -b --factory-startup --python tests/test_slab_v0.py

NOT imported by the addon. Works in a temp folder; never writes to the repo.
Exit code 0 only when every check passes.

Gate B (spec, verbatim tolerances):
  1. WINDOW slab bounds X 0..4.0, Y -0.21..0 (ruled 11-10, glass 1 cm proud), Z 0..3.5
     (+-0.0005 m), origin (0,0,0).
  2. Three empties parented to the slab at L (0,0,0), R (4,0,0), U (0,0,3.5), rotation 0.
  3. Export Slab, open a fresh empty scene, import the FBX with Blender's importer.
  4. The three empties come back as children of the mesh, same positions (+-0.0005 m),
     rotation within 0.01 deg.
Extra (not in the spec's gate, for code Slab v0 added):
  E1. Re-running Generate replaces the slab: one object, no .001.
  E2. A second slab's joints (SOCKET_L.001 in Blender) still export as exactly SOCKET_L,
      and every name is back afterwards.
  E3. SOLID and DOOR bounds are exactly X 0..4.0, Y -0.2..0, Z 0..3.5.
"""
import math
import os
import sys
import tempfile

import bpy
import addon_utils

TOL = 0.0005
ROT_TOL = math.radians(0.01)
results = []


def check(label, cond, detail=""):
    results.append((label, bool(cond)))
    print("%s  %s%s" % ("PASS" if cond else "FAIL", label, ("   [%s]" % detail) if detail else ""))


def bounds(obj):
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


def near(a, b, tol=TOL):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def fmt(v):
    return "(%s)" % ", ".join("%.5f" % x for x in v)


mod = addon_utils.enable("PER_WBTK", default_set=True)
if mod is None:
    print("FAIL  PER_WBTK did not enable")
    sys.exit(1)
print("addon:", mod.__file__, "| Blender", bpy.app.version_string)
from PER_WBTK import bm_slab                                   # noqa: E402

tmp = tempfile.mkdtemp(prefix="wbtk_slab_v0_")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(tmp, "slab_gate.blend"))
scene = bpy.context.scene
EXPECT = dict(bm_slab.socket_layout())

# ---------------------------------------------------------------- Gate B 1
scene.wbtk_slab_wall_type = 'WINDOW'
r = bpy.ops.wbtk.bm_generate_slab()
name = bm_slab.slab_name('WINDOW')
slab = bpy.data.objects.get(name)
check("generate WINDOW -> %s" % name, r == {'FINISHED'} and slab is not None, str(r))
if slab is None:
    sys.exit(1)
(bx, by, bz) = bounds(slab)
check("B1 bounds X 0..4.0", near(bx, (0.0, 4.0)), "%.5f..%.5f" % bx)
# RULED 2026-11-10 "Keep it, 21 cm": the WINDOW slab keeps the existing wall code's
# glass, a 1 cm box proud of the street face (same as today's Build Mode south
# walls), so its depth is Y -0.21..0. SOLID and DOOR stay exactly -0.2..0 (E3).
check("B1 bounds Y -0.21..0 (Window glass 1 cm proud, ruled 11-10)", near(by, (-0.21, 0.0)),
      "%.5f..%.5f" % by)
check("B1 bounds Z 0..3.5", near(bz, (0.0, 3.5)), "%.5f..%.5f" % bz)
check("B1 origin (0,0,0)", near(slab.matrix_world.translation, (0, 0, 0)), fmt(slab.matrix_world.translation))


def uv_report(obj):
    """(uv layer names, faces whose UV area is ~0 while their 3D area is not)."""
    names = [u.name for u in obj.data.uv_layers]
    if not names:
        return names, None
    uvd = obj.data.uv_layers[0].data
    flat = 0
    for p in obj.data.polygons:
        pts = [uvd[i].uv for i in p.loop_indices]
        a = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            a += x1 * y2 - x2 * y1
        if p.area > 1e-6 and abs(a) / 2.0 < 1e-6:
            flat += 1
    return names, flat


# ---------------------------------------------------------------- U1 (added 11-10: UE warned of degenerate tangents)
uvn, uvflat = uv_report(slab)
check("UV1 one UV map", len(uvn) == 1, str(uvn))
check("UV2 no face has a zero-area UV", uvflat == 0, "%s flat" % uvflat)

# ---------------------------------------------------------------- Gate B 2
socks = bm_slab.slab_sockets(slab)
check("B2 three joints L, R, U", sorted(socks) == ["L", "R", "U"], str(sorted(socks)))
for key, pos in EXPECT.items():
    e = socks.get(key)
    if e is None:
        check("B2 joint %s exists" % key, False)
        continue
    loc = e.matrix_local.translation
    rot = e.matrix_local.to_euler()
    check("B2 %s named SOCKET_%s, Plain Axes 0.25" % (key, key),
          e.name == "SOCKET_" + key and e.empty_display_type == 'PLAIN_AXES'
          and abs(e.empty_display_size - 0.25) < 1e-6, e.name)
    check("B2 %s parented to the slab" % key, e.parent == slab)
    check("B2 %s at %s" % (key, fmt(pos)), near(loc, pos), fmt(loc))
    check("B2 %s rotation 0, scale 1" % key,
          all(abs(a) <= ROT_TOL for a in rot) and near(e.matrix_local.to_scale(), (1, 1, 1)),
          fmt([math.degrees(a) for a in rot]))

# ---------------------------------------------------------------- E1
r = bpy.ops.wbtk.bm_generate_slab()
dupes = [o.name for o in bpy.data.objects if o.name.startswith(name)]
joints = [o.name for o in bpy.data.objects if o.type == 'EMPTY']
check("E1 re-Generate replaces: one slab, three joints", dupes == [name] and len(joints) == 3,
      "%s / %s" % (dupes, joints))
slab = bpy.data.objects[name]

# ---------------------------------------------------------------- Gate B 3
for o in list(bpy.context.selected_objects):
    o.select_set(False)
bpy.context.view_layer.objects.active = slab
r = bpy.ops.wbtk.bm_export_slab()
fbx = os.path.join(bm_slab.export_dir(), name + ".fbx")
check("B3 export -> UE_Export/WBTK_Slabs/%s.fbx" % name, r == {'FINISHED'} and os.path.exists(fbx),
      "%d bytes" % (os.path.getsize(fbx) if os.path.exists(fbx) else 0))

# ---------------------------------------------------------------- E2 (before the fresh scene)
scene.wbtk_slab_wall_type = 'DOOR'
bpy.ops.wbtk.bm_generate_slab()
door = bpy.data.objects[bm_slab.slab_name('DOOR')]
door_names_before = sorted(e.name for e in bm_slab.slab_sockets(door).values())
win_names_before = sorted(e.name for e in bm_slab.slab_sockets(slab).values())
for o in list(bpy.context.selected_objects):
    o.select_set(False)
bpy.context.view_layer.objects.active = door
bpy.ops.wbtk.bm_export_slab()
door_fbx = os.path.join(bm_slab.export_dir(), door.name + ".fbx")
check("E2 names restored after export",
      sorted(e.name for e in bm_slab.slab_sockets(door).values()) == door_names_before
      and sorted(e.name for e in bm_slab.slab_sockets(slab).values()) == win_names_before,
      "door %s, window %s" % (door_names_before, win_names_before))

# ---------------------------------------------------------------- E3
for wt in ('SOLID', 'DOOR'):
    scene.wbtk_slab_wall_type = wt
    bpy.ops.wbtk.bm_generate_slab()
    o = bpy.data.objects[bm_slab.slab_name(wt)]
    b = bounds(o)
    check("E3 %s bounds X 0..4.0, Y -0.2..0, Z 0..3.5" % wt,
          near(b[0], (0.0, 4.0)) and near(b[1], (-0.2, 0.0)) and near(b[2], (0.0, 3.5)),
          "X %.5f..%.5f  Y %.5f..%.5f  Z %.5f..%.5f" % (*b[0], *b[1], *b[2]))


def import_fresh(path):
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    empties = {o.name: o for o in bpy.data.objects if o.type == 'EMPTY'}
    return meshes, empties


# ---------------------------------------------------------------- Gate B 3 + 4
meshes, empties = import_fresh(fbx)
check("B3 import: one mesh", len(meshes) == 1, str([m.name for m in meshes]))
if meshes:
    uvn, uvflat = uv_report(meshes[0])
    check("UV3 the UV map survives the FBX round trip", len(uvn) == 1 and uvflat == 0,
          "%s, %s flat" % (uvn, uvflat))
check("B4 import: empties SOCKET_L, SOCKET_R, SOCKET_U",
      sorted(empties) == ["SOCKET_L", "SOCKET_R", "SOCKET_U"], str(sorted(empties)))
if meshes:
    m = meshes[0]
    print("INFO  imported mesh '%s' matrix_world translation %s euler %s scale %s" % (
        m.name, fmt(m.matrix_world.translation),
        fmt([math.degrees(a) for a in m.matrix_world.to_euler()]), fmt(m.matrix_world.to_scale())))
    # Blender's importer puts the unit + axis conversion on the imported OBJECT
    # (measured 5.2.2: rotation X 90, scale 0.01), so the mesh's local frame is
    # FBX cm, Y up. Positions are therefore compared in world space, where the
    # mesh's own vertices are back in metres Z-up: the joints must sit at the
    # same place on the slab's geometry as before the round trip.
    inv = m.matrix_world.inverted()
    wv = [m.matrix_world @ v.co for v in m.data.vertices]
    wb = ((min(v.x for v in wv), max(v.x for v in wv)), (min(v.y for v in wv), max(v.y for v in wv)),
          (min(v.z for v in wv), max(v.z for v in wv)))
    check("B4 imported mesh lands where it left (world bounds = B1 bounds)",
          all(near(wb[i], (bx, by, bz)[i]) for i in range(3)),
          "X %.5f..%.5f Y %.5f..%.5f Z %.5f..%.5f" % (*wb[0], *wb[1], *wb[2]))
    for key, pos in EXPECT.items():
        e = empties.get("SOCKET_" + key)
        if e is None:
            check("B4 SOCKET_%s came back" % key, False)
            continue
        rel = inv @ e.matrix_world
        check("B4 SOCKET_%s child of the mesh" % key, e.parent == m,
              e.parent.name if e.parent else "no parent")
        check("B4 SOCKET_%s at %s (world, mesh at origin)" % (key, fmt(pos)),
              near(e.matrix_world.translation, pos), fmt(e.matrix_world.translation))
        check("B4 SOCKET_%s rotation within 0.01 deg" % key,
              all(abs(a) <= ROT_TOL for a in rel.to_euler()),
              fmt([math.degrees(a) for a in rel.to_euler()]))
        print("INFO  SOCKET_%s raw matrix_local translation %s euler %s" % (
            key, fmt(e.matrix_local.translation),
            fmt([math.degrees(a) for a in e.matrix_local.to_euler()])))

# ---------------------------------------------------------------- E2 (the FBX side)
_m, door_empties = import_fresh(door_fbx)
check("E2 second slab's FBX carries exactly SOCKET_L, SOCKET_R, SOCKET_U",
      sorted(door_empties) == ["SOCKET_L", "SOCKET_R", "SOCKET_U"], str(sorted(door_empties)))

failed = [l for l, ok in results if not ok]
print("\nSLAB V0 GATE B: %d/%d checks pass%s" % (
    len(results) - len(failed), len(results), "" if not failed else " -- FAILED: " + "; ".join(failed)))
sys.exit(1 if failed else 0)
