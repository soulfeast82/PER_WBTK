"""Regression tests for the WBTK -> Buildify footprint exporter.

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" ^
        --background --factory-startup --python tests/test_buildify_export.py

NOT imported by the addon -- __init__.py never touches this folder, so Blender
never loads it. Runs headless on a COPY of the bench blend; never writes to the
repo.

THE CONTRACT UNDER TEST
    Re-running the export must update the footprint GEOMETRY in place and
    change nothing else. The user attaches Buildify's `building` geometry-nodes
    modifier to that object BY HAND and configures module width, module height
    and the floor range on it. Before 2026-08-17 the exporter called
    bpy.data.objects.remove() first, so every re-export silently destroyed all
    of that -- and the bench file was committed with an empty modifier stack
    because of it. These tests exist so that cannot come back.
"""
import os
import shutil
import sys
import tempfile

import bpy
import addon_utils

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BENCH = os.path.join(REPO, "Meshes", "PER_DW_Buildify_Test.blend")

_fails = []


def check(label, cond, detail=""):
    print("  %-56s %s %s" % (label, "PASS" if cond else "** FAIL **", detail))
    if not cond:
        _fails.append(label)


def snapshot(ob):
    """Everything a re-export is contractually forbidden from changing."""
    if ob is None:
        return None
    mods = []
    for m in ob.modifiers:
        mods.append({
            "name": m.name,
            "type": m.type,
            "node_group": getattr(getattr(m, "node_group", None), "name", None),
            "inputs": {k: (list(m[k]) if hasattr(m[k], "__len__")
                           and not isinstance(m[k], str) else m[k])
                       for k in m.keys()},
        })
    vg = ob.vertex_groups.get(LEVELS_VGROUP)
    weights = {}
    if vg and ob.data:
        for v in ob.data.vertices:
            for g in v.groups:
                if g.group == vg.index:
                    weights[v.index] = round(g.weight, 5)
    return {
        "modifiers": mods,
        "vgroups": [g.name for g in ob.vertex_groups],
        "weights": weights,
        "collections": sorted(c.name for c in ob.users_collection),
        "matrix": [round(x, 6) for r in ob.matrix_world for x in r],
        "custom_props": {k: str(ob[k]) for k in ob.keys()},
        "mesh_name": ob.data.name if ob.data else None,
        "geo": (len(ob.data.vertices), len(ob.data.polygons)) if ob.data else (0, 0),
        "display_type": ob.display_type,
    }


def blocks(*specs):
    for b in list(bm_data.get_all()):
        bm_data.delete(b)
    for loc, w, d, h in specs:
        bm_data.create(loc, {"w": w, "d": d, "h": h, "chamfers": []})


def wipe_footprint():
    for o in [o for o in bpy.data.objects if o.name.startswith(FOOTPRINT_NAME)]:
        bpy.data.objects.remove(o, do_unlink=True)


# ---------------------------------------------------------------- bootstrap --
addon_utils.enable("PER_WBTK", default_set=False, persistent=True)
from PER_WBTK import bm_data                                    # noqa: E402
from PER_WBTK.operators_buildify import (                       # noqa: E402
    FOOTPRINT_NAME, LEVELS_VGROUP)

# =============================================================================
print("\n=== 1. RE-EXPORT PRESERVES THE HAND-CONFIGURED OBJECT ===")
# =============================================================================
if not os.path.exists(BENCH):
    print("  SKIPPED - bench file not found at %s" % BENCH)
else:
    tmp = os.path.join(tempfile.mkdtemp(prefix="wbtk_bfy_"), "bench.blend")
    shutil.copy2(BENCH, tmp)
    bpy.ops.wm.open_mainfile(filepath=tmp)

    # differing block widths, so edge subdivision is exercised too
    blocks(((0.0, 0.0, 0.0), 8.0, 4.0, 3.5), ((12.0, 0.0, 0.0), 4.0, 4.0, 7.0))
    assert bpy.ops.wbtk.export_buildify_footprints() == {'FINISHED'}
    ob = bpy.data.objects.get(FOOTPRINT_NAME)
    assert ob, "export produced no footprint object"

    # the user's hand configuration, applied AFTER the first export
    if not ob.modifiers:
        ng = (bpy.data.node_groups.get("building")
              or bpy.data.node_groups.new("building_stub", "GeometryNodeTree"))
        ob.modifiers.new("Buildify", 'NODES').node_group = ng
    mod = ob.modifiers[0]
    for k in list(mod.keys()):
        if isinstance(mod[k], int) and not isinstance(mod[k], bool) \
                and "use_attribute" not in k:
            try:
                mod[k] = 7
            except Exception:
                pass
    ob["wbtk_test_sentinel"] = "do-not-lose-me"
    ob.display_type = 'WIRE'

    before = snapshot(ob)
    orphans_before = len([m for m in bpy.data.meshes if m.users == 0])
    meshes_before = len(bpy.data.meshes)

    bpy.ops.wbtk.export_buildify_footprints()          # <-- under test
    after = snapshot(bpy.data.objects.get(FOOTPRINT_NAME))

    check("footprint object still exists", after is not None)
    check("modifier survived",
          len(after["modifiers"]) == len(before["modifiers"]),
          "%d -> %d" % (len(before["modifiers"]), len(after["modifiers"])))
    if after["modifiers"] and before["modifiers"]:
        check("modifier still bound to the same node group",
              after["modifiers"][0]["node_group"]
              == before["modifiers"][0]["node_group"])
        bi, ai = before["modifiers"][0]["inputs"], after["modifiers"][0]["inputs"]
        lost = {k: (bi[k], ai.get(k, "<GONE>")) for k in bi if ai.get(k) != bi[k]}
        check("every hand-set modifier input preserved", not lost, str(lost)[:200])
    check("vertex group is EXACTLY [%s]" % LEVELS_VGROUP,
          after["vgroups"] == [LEVELS_VGROUP], str(after["vgroups"]))
    check("levels weights identical to baseline",
          after["weights"] == before["weights"])
    check("no stale weights (every vert carries one)",
          len(after["weights"]) == after["geo"][0],
          "%d of %d" % (len(after["weights"]), after["geo"][0]))
    check("geometry identical for identical blocks",
          after["geo"] == before["geo"],
          "%s -> %s" % (before["geo"], after["geo"]))
    check("object transform unchanged", after["matrix"] == before["matrix"])
    check("collection membership unchanged",
          after["collections"] == before["collections"],
          "%s -> %s" % (before["collections"], after["collections"]))
    check("custom property preserved",
          after["custom_props"].get("wbtk_test_sentinel") == "do-not-lose-me")
    check("display_type preserved", after["display_type"] == 'WIRE',
          after["display_type"])
    check("mesh datablock name stable (no .001 drift)",
          after["mesh_name"] == before["mesh_name"],
          "%s -> %s" % (before["mesh_name"], after["mesh_name"]))
    check("no orphan meshes leaked",
          len([m for m in bpy.data.meshes if m.users == 0]) == orphans_before)
    check("no mesh datablock growth", len(bpy.data.meshes) == meshes_before,
          "%d -> %d" % (meshes_before, len(bpy.data.meshes)))

    bpy.ops.wbtk.export_buildify_footprints()
    check("stable across a third export",
          snapshot(bpy.data.objects.get(FOOTPRINT_NAME)) == after)

# =============================================================================
print("\n=== 2. EDGE CASES ===")
# =============================================================================
print("\n-- A. first run, nothing exists yet --")
bpy.ops.wm.read_factory_settings(use_empty=True)
blocks(((0.0, 0.0, 0.0), 8.0, 4.0, 3.5))
res = bpy.ops.wbtk.export_buildify_footprints()
ob = bpy.data.objects.get(FOOTPRINT_NAME)
check("operator FINISHED", res == {'FINISHED'}, str(res))
check("object created", ob is not None)
check("linked to the target collection",
      bool(ob) and [c.name for c in ob.users_collection] == ["World Builder Output"],
      str([c.name for c in ob.users_collection]) if ob else "")
check("8m edge subdivided to module width (6 verts)",
      bool(ob) and len(ob.data.vertices) == 6,
      "%d verts" % len(ob.data.vertices) if ob else "")

print("\n-- B. five consecutive re-exports --")
n_me, n_ob = len(bpy.data.meshes), len(bpy.data.objects)
seen = []
for _ in range(5):
    bpy.ops.wbtk.export_buildify_footprints()
    seen.append([g.name for g in bpy.data.objects[FOOTPRINT_NAME].vertex_groups])
check("vertex group never gains a .001 suffix",
      all(n == [LEVELS_VGROUP] for n in seen), str(seen[-1]))
check("no mesh datablock growth", len(bpy.data.meshes) == n_me,
      "%d -> %d" % (n_me, len(bpy.data.meshes)))
check("no object growth", len(bpy.data.objects) == n_ob,
      "%d -> %d" % (n_ob, len(bpy.data.objects)))

print("\n-- C. the name is taken by a non-mesh object --")
wipe_footprint()
bpy.context.scene.collection.objects.link(
    bpy.data.objects.new(FOOTPRINT_NAME, None))
# report({'ERROR'}) makes bpy.ops raise from Python; that IS the refusal
try:
    r = bpy.ops.wbtk.export_buildify_footprints()
    refused, how = (r == {'CANCELLED'}), "returned %s" % (r,)
except RuntimeError as e:
    refused, how = ("already exists as empty" in str(e)), "raised"
check("refuses cleanly instead of clobbering", refused, how)
check("the user's Empty was not destroyed",
      bpy.data.objects.get(FOOTPRINT_NAME) is not None
      and bpy.data.objects[FOOTPRINT_NAME].type == 'EMPTY')

print("\n-- D. the mesh is shared with another object --")
wipe_footprint()
bpy.ops.wbtk.export_buildify_footprints()
ob = bpy.data.objects[FOOTPRINT_NAME]
sibling = bpy.data.objects.new("Innocent_Bystander", ob.data)
bpy.context.scene.collection.objects.link(sibling)
ob.modifiers.new("Buildify", 'NODES').node_group = \
    bpy.data.node_groups.new("stub", "GeometryNodeTree")
sib_before = len(sibling.data.vertices)
blocks(((0.0, 0.0, 0.0), 4.0, 4.0, 3.5))                 # smaller than before
bpy.ops.wbtk.export_buildify_footprints()
check("the bystander's geometry was NOT wiped",
      len(sibling.data.vertices) == sib_before,
      "%d -> %d" % (sib_before, len(sibling.data.vertices)))
check("footprint took a private mesh",
      bpy.data.objects[FOOTPRINT_NAME].data is not sibling.data)
check("modifier survived the mesh swap",
      len(bpy.data.objects[FOOTPRINT_NAME].modifiers) == 1)
check("footprint rebuilt to the new block",
      len(bpy.data.objects[FOOTPRINT_NAME].data.vertices) == 4,
      "%d verts" % len(bpy.data.objects[FOOTPRINT_NAME].data.vertices))

print("\n-- E. non-identity transform: warn, never silently reset --")
wipe_footprint()
blocks(((0.0, 0.0, 0.0), 8.0, 4.0, 3.5))
bpy.ops.wbtk.export_buildify_footprints()
bpy.data.objects[FOOTPRINT_NAME].location = (100.0, 0.0, 0.0)
bpy.ops.wbtk.export_buildify_footprints()
check("the user's move was respected",
      abs(bpy.data.objects[FOOTPRINT_NAME].location.x - 100.0) < 1e-6,
      "x=%.3f" % bpy.data.objects[FOOTPRINT_NAME].location.x)

print("\n-- F. an unrelated vertex group on the footprint --")
wipe_footprint()
blocks(((0.0, 0.0, 0.0), 8.0, 4.0, 3.5))
bpy.ops.wbtk.export_buildify_footprints()
bpy.data.objects[FOOTPRINT_NAME].vertex_groups.new(name="some_other_group")
bpy.ops.wbtk.export_buildify_footprints()
gs = [g.name for g in bpy.data.objects[FOOTPRINT_NAME].vertex_groups]
# MEASURED on Blender 5.1: vertex groups live on the MESH datablock, so
# clear_geometry() drops all of them. Delete-and-recreate dropped them too, so
# this is documented behaviour rather than a regression.
check("other groups dropped (5.1 mesh-datablock behaviour, not a regression)",
      gs == [LEVELS_VGROUP], str(gs))
check("and still no %s.001" % LEVELS_VGROUP,
      LEVELS_VGROUP + ".001" not in gs, str(gs))

print("\n%s (%d failing)" % ("RESULT: GREEN" if not _fails else "RESULT: RED",
                             len(_fails)))
for f in _fails:
    print("   FAILED:", f)
sys.exit(1 if _fails else 0)
