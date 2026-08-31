# operators_box_uv.py
#
# The ruled box projection: uv = local_metres / DIVISOR, axis-aligned per face.
#
# WHY THIS EXISTS. Until 2026-08-29 NOTHING in this addon could produce the kit's
# own UV convention. The only UV writers were utils.py's smart_project and
# operators_trim_uv.py, which writes a layer named "TrimSheet" and overwrites the
# ACTIVE layer if one exists. So the convention that 8 kit meshes already carry --
# and that 46 more need -- existed only as a fact about those 8 meshes and as a
# line in a doc. This makes it executable.
#
# THE CONVENTION WAS DERIVED FROM THE MESHES, NOT INVENTED. Measured across all 87
# faces of the 8 reference meshes, every face matched exactly one mapping and no
# face was unmatched:
#
#     dominant |n.x|  ->  U = y / D,  V = z / D
#     dominant |n.y|  ->  U = x / D,  V = z / D
#     dominant |n.z|  ->  U = x / D,  V = y / D
#
# All three use +1 signs, and THE SIGN OF THE NORMAL DOES NOT FLIP THE MAPPING --
# a face at x+ and a face at x- both map (y, z). That mirrors back faces, which is
# correct and invisible for a tiling material. It was described elsewhere as
# "winding-blind by construction", as though it were a defect; it is the authored
# convention, and the measurement is what settled it.
#
# D = 4.0 gives 512 px/m at 2K, the ruled density. It is a parameter because the
# density is a ruling and rulings move; it is not a magic number to bury.

import bpy

DEFAULT_DIVISOR = 4.0          # 4 m per UV tile == 512 px/m at 2048
DEFAULT_LAYER = "UVMap"        # what the 8 reference meshes call it

# dominant axis index -> (u index, v index). Matches the measured table above.
_AXIS_MAP = {0: (1, 2), 1: (0, 2), 2: (0, 1)}


def box_project(obj, divisor=DEFAULT_DIVISOR, layer_name=DEFAULT_LAYER, overwrite=False,
                slot_indices=None):
    """Apply the ruled projection to one mesh object.

    Returns (changed, message). Never raises on ordinary refusals -- callers get a
    reason instead, so a batch run can report per-object rather than dying.

    overwrite defaults to FALSE on purpose. operators_trim_uv.py takes
    `bm.loops.layers.uv.active` and writes into it, which silently destroys the
    reference unwrap on any mesh that already has one. This refuses instead, and
    the refusal is reported rather than swallowed.

    slot_indices restricts the projection to faces in those material slots, for the
    MIXED meshes: a BfyWall panel whose wall field tiles but whose pane is a UE
    masked cutout wanting a fitted 0-1 unwrap. Projecting the whole object would put
    tiling UVs on the pane, which is wrong rather than merely unhelpful; skipping the
    whole object leaves the wall field unwrapped, which is what the first pass did.

    Faces OUTSIDE the filter are not written. What they then contain is NOT (0,0) --
    measured in Blender 5.1, `uv_layers.new()` gives every face a UNIT SQUARE
    (0,0)(1,0)(1,1)(0,1) on a mesh with no existing layer, and COPIES THE ACTIVE
    LAYER on a mesh that has one. Both are traps if you assume zeros: the second in
    particular means calling this twice with different filters leaves the first
    call's projection sitting under the second's untouched faces.

    The unit square is a serviceable placeholder for a masked cutout -- a pane quad
    mapped 0-1 samples the whole mask -- but it is a default, not a decision, and the
    face still wants a real fitted unwrap. The mesh reads as non-conforming to the
    validator until it gets one, which is TRUE and is the point: a partial unwrap
    that reported clean would be the more dangerous outcome.
    """
    if obj is None or obj.type != 'MESH':
        return False, "not a mesh"
    me = obj.data
    if not me.polygons:
        return False, "no faces"
    if divisor <= 0.0:
        return False, "divisor must be > 0"

    existing = me.uv_layers.get(layer_name)
    if existing is not None and not overwrite:
        return False, ("already has '%s' - refusing to overwrite (pass overwrite=True "
                       "only if you mean to replace a reference unwrap)" % layer_name)

    if slot_indices is not None:
        want = set(slot_indices)
        if not want:
            return False, "empty slot filter - nothing to project"
        avail = set(range(max(1, len(obj.material_slots))))
        unknown = want - avail
        if unknown:
            return False, ("slot(s) %s do not exist on this mesh (has %d)"
                           % (sorted(unknown), len(obj.material_slots)))
    else:
        want = None

    lay = existing if existing is not None else me.uv_layers.new(name=layer_name)
    data = lay.data
    verts = me.vertices
    touched = 0

    for poly in me.polygons:
        if want is not None and poly.material_index not in want:
            continue
        touched += 1
        n = poly.normal
        # First-max on ties, matching the derivation. A 45-degree face is arbitrary
        # either way; what matters is that it is deterministic and documented.
        d = max(range(3), key=lambda i: abs(n[i]))
        ui, vi = _AXIS_MAP[d]
        for li in poly.loop_indices:
            co = verts[me.loops[li].vertex_index].co
            data[li].uv = (co[ui] / divisor, co[vi] / divisor)

    me.update()
    if want is not None:
        return True, ("%d of %d faces projected at 1/%.4g (slots %s); the other %d LEFT AS FOUND "
                      "and still need a fitted unwrap"
                      % (touched, len(me.polygons), divisor, sorted(want),
                         len(me.polygons) - touched))
    return True, "%d faces projected at 1/%.4g" % (touched, divisor)


class WBTK_OT_BoxProjectUVs(bpy.types.Operator):
    """Apply the ruled box projection (uv = local metres / divisor) to selected meshes"""
    bl_idname = "wbtk.box_project_uvs"
    bl_label = "Box Project UVs (ruled)"
    bl_description = ("Write the kit's ruled tiling UVs: axis-aligned per-face box projection, "
                      "uv = local metres / divisor. Skips meshes that already have the layer "
                      "unless Overwrite is ticked")
    bl_options = {'REGISTER', 'UNDO'}

    divisor: bpy.props.FloatProperty(
        name="Metres per UV tile",
        description="4.0 gives the ruled 512 px/m at 2K. Change only if the density ruling changes",
        default=DEFAULT_DIVISOR, min=0.001, soft_min=0.5, soft_max=16.0,
    )
    layer_name: bpy.props.StringProperty(
        name="UV Layer", default=DEFAULT_LAYER,
        description="The reference meshes use 'UVMap'",
    )
    overwrite: bpy.props.BoolProperty(
        name="Overwrite existing",
        description="Replace the layer if it already exists. OFF by default so a reference "
                    "unwrap cannot be destroyed by accident",
        default=False,
    )
    selected_only: bpy.props.BoolProperty(
        name="Selected only", default=True,
        description="Off = every mesh object in the scene",
    )
    only_slots: bpy.props.StringProperty(
        name="Only slots",
        default="",
        description="Blank = every face. Otherwise a comma-separated list of material slot "
                    "indices, e.g. '0'. Faces outside it are left untouched - for a mesh whose "
                    "wall field tiles but whose pane needs a fitted 0-1 unwrap",
    )

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        if self.selected_only:
            targets = [o for o in context.selected_objects if o.type == 'MESH']
            scope = "selection"
        else:
            targets = [o for o in context.scene.objects if o.type == 'MESH']
            scope = "scene"

        if not targets:
            self.report({'WARNING'}, "No mesh objects in the %s." % scope)
            return {'CANCELLED'}

        slot_filter = None
        if self.only_slots.strip():
            try:
                slot_filter = [int(x) for x in self.only_slots.replace(" ", "").split(",") if x]
            except ValueError:
                self.report({'ERROR'}, "Only slots must be comma-separated integers, e.g. '0,2'.")
                return {'CANCELLED'}

        done, skipped = [], []
        for ob in targets:
            changed, msg = box_project(ob, self.divisor, self.layer_name, self.overwrite,
                                       slot_filter)
            (done if changed else skipped).append((ob.name, msg))

        print("")
        print("--- WBTK Box Project UVs (1/%.4g, layer '%s', %s) ---"
              % (self.divisor, self.layer_name, scope))
        for n, m in done:
            print("  ok    %-46s %s" % (n, m))
        for n, m in skipped:
            print("  SKIP  %-46s %s" % (n, m))
        print("  %d projected, %d skipped" % (len(done), len(skipped)))
        print("--- end ---")

        if skipped and not done:
            self.report({'WARNING'},
                        "Projected nothing - all %d skipped. See Console." % len(skipped))
            return {'CANCELLED'}
        if skipped:
            # Never silent. A partial run that reports INFO is how a half-done kit
            # gets mistaken for a done one.
            self.report({'WARNING'}, "Projected %d, SKIPPED %d (see Console)."
                        % (len(done), len(skipped)))
        else:
            self.report({'INFO'}, "Projected %d mesh(es) at 1/%.4g." % (len(done), self.divisor))
        return {'FINISHED'}


_classes_to_register = (
    WBTK_OT_BoxProjectUVs,
)
