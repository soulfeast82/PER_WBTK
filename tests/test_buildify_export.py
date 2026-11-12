"""Regression tests for the WBTK -> Buildify footprint exporter.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" ^
        --background --factory-startup --python tests/test_buildify_export.py

Runs on Blender 5.2 and 5.1. 5.2 moved Geometry Nodes modifier inputs off the
modifier's ID properties (mod["Input_3"] and mod.keys() raise there), so every
input read and write goes through mod_inputs() / set_input() below.

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


def _plain(v):
    return list(v) if hasattr(v, "__len__") and not isinstance(v, str) else v


def _inputs_52(mod):
    """mod.properties.inputs on 5.2+, or None on 5.1 and older."""
    props = getattr(mod, "properties", None)
    return getattr(props, "inputs", None) if props is not None else None


def mod_inputs(mod):
    """{identifier: value} for every GN modifier input, on 5.1 and 5.2.

    5.2: each input is a socket at mod.properties.inputs.<identifier> with
    .value, .type (value / attribute) and .attribute_name; all three are kept
    so a lost attribute toggle is caught too. 5.1: the modifier's ID properties.
    """
    ins = _inputs_52(mod)
    if ins is None:
        return {k: _plain(mod[k]) for k in mod.keys()}
    out = {}
    for ident in dir(ins):
        if ident.startswith("_") or ident in ("bl_rna", "rna_type", "name",
                                              "bl_system_properties_get"):
            continue
        s = getattr(ins, ident)
        if not hasattr(s, "value"):
            continue                                   # geometry sockets
        out[ident] = (_plain(s.value), getattr(s, "type", None),
                      getattr(s, "attribute_name", None))
    return out


def set_input(mod, ident, value):
    """Set one GN modifier input, on 5.1 and 5.2 (same rule as
    operators_build_engine._set_modifier_input)."""
    ins = _inputs_52(mod)
    s = getattr(ins, ident, None) if ins is not None else None
    if s is not None and hasattr(s, "value"):
        s.value = value
    else:
        mod[ident] = value


def input_value(mod, ident):
    """The value of one GN modifier input, on 5.1 and 5.2."""
    ins = _inputs_52(mod)
    return getattr(ins, ident).value if ins is not None else mod[ident]


def int_input_ids(mod):
    """Identifiers of the plain int inputs (not bools, not attribute toggles)."""
    ins = _inputs_52(mod)
    if ins is None:
        return [k for k in mod.keys()
                if isinstance(mod[k], int) and not isinstance(mod[k], bool)
                and "use_attribute" not in k]
    return [k for k, (v, _t, _a) in mod_inputs(mod).items()
            if isinstance(v, int) and not isinstance(v, bool)]


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
            "inputs": mod_inputs(m) if m.type == 'NODES' else {},
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
    hand_set = int_input_ids(mod)
    for k in hand_set:
        try:
            set_input(mod, k, 7)
        except Exception:
            pass
    # Guard against the test going vacuous: if no input took the 7, "every
    # hand-set input preserved" below would compare defaults to defaults.
    check("test setup: hand-set int inputs took the value 7",
          bool(hand_set) and all(input_value(mod, k) == 7 for k in hand_set),
          str(hand_set))
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
# MEASURED on Blender 5.1, same on 5.2 (2026-11-11): vertex groups live on the
# MESH datablock, so clear_geometry() drops all of them. Delete-and-recreate
# dropped them too, so this is documented behaviour rather than a regression.
check("other groups dropped (mesh-datablock behaviour, not a regression)",
      gs == [LEVELS_VGROUP], str(gs))
check("and still no %s.001" % LEVELS_VGROUP,
      LEVELS_VGROUP + ".001" not in gs, str(gs))

print("\n-- G. a shielded (fake-user) mesh must not be forked --")
# ID.users COUNTS THE FAKE USER, so a naive `users > 1` reads a shielded but
# unshared mesh as shared and takes the swap path: name drifts to .001, the
# original is orphaned yet pinned forever by its own shield, and .copy() does
# not carry use_fake_user -- so the protection is silently removed.
wipe_footprint()
blocks(((0.0, 0.0, 0.0), 8.0, 4.0, 3.5))
bpy.ops.wbtk.export_buildify_footprints()
fp = bpy.data.objects[FOOTPRINT_NAME]
fp.data.use_fake_user = True
name_before, n_meshes = fp.data.name, len(bpy.data.meshes)
blocks(((0.0, 0.0, 0.0), 4.0, 4.0, 3.5))
bpy.ops.wbtk.export_buildify_footprints()
check("shielded mesh not forked to .001",
      bpy.data.objects[FOOTPRINT_NAME].data.name == name_before,
      "%s -> %s" % (name_before, bpy.data.objects[FOOTPRINT_NAME].data.name))
check("the user's shield survives",
      bpy.data.objects[FOOTPRINT_NAME].data.use_fake_user)
check("footprint still rebuilt correctly",
      len(bpy.data.objects[FOOTPRINT_NAME].data.vertices) == 4,
      "%d verts" % len(bpy.data.objects[FOOTPRINT_NAME].data.vertices))

print("\n-- H. footprint outside the active scene must not fail silently --")
# Reusing the object (instead of recreating it) means it can live somewhere the
# active scene cannot see. The export then rebuilds it perfectly and reports
# FINISHED while nothing appears. Not auto-relinked -- link_to_collection would
# yank a footprint the user filed elsewhere -- so it must WARN.
wipe_footprint()
blocks(((0.0, 0.0, 0.0), 8.0, 4.0, 3.5))
bpy.ops.wbtk.export_buildify_footprints()
fp = bpy.data.objects[FOOTPRINT_NAME]
for c in list(fp.users_collection):
    c.objects.unlink(fp)
bpy.data.scenes.new("Other").collection.objects.link(fp)
import PER_WBTK.operators_buildify as _bfy                       # noqa: E402

# Call execute() UNBOUND with a duck-typed self. It is a plain Python function
# and self.report is the only thing it uses self for, so this captures every
# report without touching bpy.types.Operator.report -- monkeypatching that RNA
# method hard-crashes Blender.
_warned = []


class _ReportProbe(object):
    def report(self, kind, msg):
        _warned.append((set(kind), msg))


blocks(((0.0, 0.0, 0.0), 4.0, 4.0, 3.5))
res = _bfy.OP_ExportBuildifyFootprints.execute(_ReportProbe(), bpy.context)
check("still rebuilds the geometry",
      res == {'FINISHED'}
      and len(bpy.data.objects[FOOTPRINT_NAME].data.vertices) == 4,
      str(res))
check("but WARNS that nothing will appear in this scene",
      any("not in the active scene" in m for k, m in _warned if 'WARNING' in k),
      str([m[:50] for k, m in _warned]))

# =============================================================================
print("\n=== 3. END TO END: does the levels weight actually drive Buildify? ===")
# =============================================================================
# Every other assertion here checks OUR data. This one checks that Buildify
# reads it -- the only assertion that would catch the group being renamed,
# the weights being wrong, or the modifier being wired to nothing.
# Section 2 ran read_factory_settings, so reload the bench to get the REAL
# Buildify node library back.
ng = None
if os.path.exists(BENCH):
    tmp2 = os.path.join(tempfile.mkdtemp(prefix="wbtk_bfy_e2e_"), "bench.blend")
    shutil.copy2(BENCH, tmp2)
    bpy.ops.wm.open_mainfile(filepath=tmp2)
    ng = bpy.data.node_groups.get("building")
if ng is None:
    print("  SKIPPED - the real 'building' node group is not available")
else:
    def instance_count(ob):
        # NO fallback to vertex count -- zero instances is a MEANINGFUL result
        # here (it is what a broken vertex-group name produces), and a fallback
        # would mask exactly the failure this section exists to catch.
        deps = bpy.context.evaluated_depsgraph_get()
        deps.update()
        return sum(1 for i in deps.object_instances
                   if i.is_instance and i.parent
                   and i.parent.original == ob.original)

    wipe_footprint()
    blocks(((0.0, 0.0, 0.0), 8.0, 8.0, 3.5))
    bpy.ops.wbtk.export_buildify_footprints()
    fp = bpy.data.objects[FOOTPRINT_NAME]
    if not fp.modifiers:
        fp.modifiers.new("Buildify", 'NODES').node_group = ng
    m = fp.modifiers[0]
    # ⚠️ A FRESH modifier does NOT read the vertex group. Measured 2026-08-17:
    # "- Randomize floor numbers -" defaults to True, so floors come from the
    # Min/Max ints at random and building:levels is ignored entirely. Module
    # size also defaults to 3.0 x 3.0, not the Scale Bible's 4.0 x 3.5. Match
    # the live configuration or this whole section measures nothing.
    set_input(m, "Input_5", True)    # - BLOSM or ADE -            (generating mode)
    set_input(m, "Input_8", False)   # - Randomize floor numbers - OFF
    set_input(m, "Input_3", 4.0)     # Module width
    set_input(m, "Input_9", 3.5)     # Module height

    counts = []
    for h in (3.5, 7.0, 14.0, 21.0):
        blocks(((0.0, 0.0, 0.0), 8.0, 8.0, h))
        bpy.ops.wbtk.export_buildify_footprints()
        fp = bpy.data.objects[FOOTPRINT_NAME]
        bpy.context.view_layer.update()
        counts.append((int(round(h / 3.5)), instance_count(fp)))
    print("  storeys -> Buildify instances: %s"
          % ", ".join("%d->%d" % c for c in counts))
    check("the levels weight actually drives Buildify output",
          all(a[1] < b[1] for a, b in zip(counts, counts[1:])), str(counts))
    check("a 1-storey block produces real geometry", counts[0][1] > 0,
          str(counts[0]))

    # The sharpest proof that the group NAME is load-bearing: break the name
    # and Buildify emits nothing, while the exporter would still report success.
    top = counts[-1][1]
    fp.vertex_groups[LEVELS_VGROUP].name = LEVELS_VGROUP + "_BROKEN"
    bpy.context.view_layer.update()
    broken = instance_count(fp)
    print("  after renaming the vertex group: %d (was %d)" % (broken, top))
    check("a wrong group name silently produces ZERO geometry "
          "(this is why the .001 guard exists)", broken == 0,
          "%d instances" % broken)

print("\n%s (%d failing)" % ("RESULT: GREEN" if not _fails else "RESULT: RED",
                             len(_fails)))
for f in _fails:
    print("   FAILED:", f)
sys.exit(1 if _fails else 0)
