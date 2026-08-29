# operators_trim_uv.py
# Trim Sheet UV Generator — remaps building UVs to horizontal trim sheet rows.
#
# Trim sheet layout (8 rows, each 1/8 of V space):
#   Row 0  V 0.000–0.125  Wall (general)
#   Row 1  V 0.125–0.250  Window frame / inset
#   Row 2  V 0.250–0.375  Door frame
#   Row 3  V 0.375–0.500  Trim / band / ledge
#   Row 4  V 0.500–0.625  Column / corner
#   Row 5  V 0.625–0.750  Sill / plinth
#   Row 6  V 0.750–0.875  Parapet / roof
#   Row 7  V 0.875–1.000  Floor slab

import bpy
import bmesh
import math
from mathutils import Vector

# ── TRIM ROW DEFINITIONS ─────────────────────────────────────────────────────

TRIM_ROWS = {
    # row_index: (v_min, v_max, label)
    0: (0.000, 0.125, "Wall"),
    1: (0.125, 0.250, "Window"),
    2: (0.250, 0.375, "Door"),
    3: (0.375, 0.500, "Trim/Band/Ledge"),
    4: (0.500, 0.625, "Column/Corner"),
    5: (0.625, 0.750, "Sill/Plinth"),
    6: (0.750, 0.875, "Parapet/Roof"),
    7: (0.875, 1.000, "Floor/Ceiling"),
}

# Object name fragment → trim row index
_NAME_TO_ROW = {
    "Walls":   0,
    "Window":  1,
    "Door":    2,
    "Bands":   3,
    "Ledge":   3,
    "Corner":  4,
    "Column":  4,
    "Sill":    5,
    "Plinth":  5,
    "Parapet": 6,
    "Roof":    6,
    "Floor":   7,
    "Slab":    7,
}


# Where an unmatched name lands. Named rather than buried in a `return 0`, because
# it is not a lookup result - it is a guess, and callers must be able to tell the
# difference. Measured 2026-08-28 against PER_DW_Kit: of 54 meshes, 14 matched a
# fragment and 40 did NOT, so the guess was the majority answer while reporting
# success. Antennas, tanks, cables, barriers and railings were all being told they
# were wall.
#
# The keys are also stale against the kit's vocabulary: "Walls" is plural but every
# kit mesh reads `SM_DW_Wall_...`, "Column"/"Corner" never match `Pillar`, "Bands"/
# "Ledge" never match `TopTrim`, "Floor"/"Slab" never match `Grating`/`Landing`/
# `Stair`, and "Window" never matches the `_Win` abbreviation. Widening the map is a
# texturing decision, not a rename, so it is left for Jermaine rather than guessed at.
_DEFAULT_ROW = 0


def _get_trim_row(obj_name):
    """Which trim row this name maps to, or None if nothing matched.

    Returns None rather than defaulting, so a caller that wants the old behaviour
    has to write `_DEFAULT_ROW` and thereby say so. Behaviour is unchanged at both
    call sites - the parametric generator's children do not match either, so the
    default is load-bearing there and is deliberately preserved.
    """
    for fragment, row in _NAME_TO_ROW.items():
        if fragment.lower() in obj_name.lower():
            return row
    return None


def _apply_trim_uvs(obj, row_index, texel_density):
    """
    Remap an object's UVs to a specific trim sheet row.

    U = world-space horizontal extent * texel_density (tiles along surface)
    V = Z height mapped into the row's V range
    """
    if not obj or obj.type != 'MESH':
        return False

    mesh = obj.data
    if not mesh.polygons:
        return False

    v_min, v_max, _label = TRIM_ROWS[row_index]
    v_range = v_max - v_min

    # Work in BMesh for easier UV access
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()

    # Get or create UV layer
    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        uv_layer = bm.loops.layers.uv.new("TrimSheet")

    # World transform
    mat = obj.matrix_world

    for face in bm.faces:
        # Get world-space positions of all verts in this face
        world_cos = [(mat @ v.co) for v in face.verts]

        # Find the face's bounding box in world space
        xs = [c.x for c in world_cos]
        ys = [c.y for c in world_cos]
        zs = [c.z for c in world_cos]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        z_min, z_max = min(zs), max(zs)

        x_span = x_max - x_min
        y_span = y_max - y_min
        z_span = z_max - z_min

        # Determine face orientation from normal
        normal = face.normal
        abs_nx = abs(normal.x)
        abs_ny = abs(normal.y)
        abs_nz = abs(normal.z)

        for loop in face.loops:
            wco = mat @ loop.vert.co

            if abs_nz >= abs_nx and abs_nz >= abs_ny:
                # Horizontal face (floor/ceiling) — U from X, V from Y
                u = (wco.x - x_min) * texel_density if x_span > 0.001 else 0.0
                # For floors, map Y into the row range
                t = (wco.y - y_min) / y_span if y_span > 0.001 else 0.5
                v = v_min + t * v_range
            else:
                # Vertical face (wall) — U from horizontal extent, V from Z
                if abs_nx >= abs_ny:
                    # Facing X — U from Y
                    u = (wco.y - y_min) * texel_density if y_span > 0.001 else 0.0
                else:
                    # Facing Y — U from X
                    u = (wco.x - x_min) * texel_density if x_span > 0.001 else 0.0

                # V from Z, mapped into trim row range
                t = (wco.z - z_min) / z_span if z_span > 0.001 else 0.5
                v = v_min + t * v_range

            loop[uv_layer].uv = (u, v)

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return True


# ── OPERATOR: Apply to Selected Building ──────────────────────────────────────

class WBTK_OT_apply_trim_uvs(bpy.types.Operator):
    bl_idname = "wbtk.apply_trim_uvs"
    bl_label = "Apply Trim Sheet UVs"
    bl_description = "Remap UVs on all children of the selected building master to trim sheet rows"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'EMPTY' and obj.children

    def execute(self, context):
        scene = context.scene
        master = context.active_object
        texel_density = getattr(scene, 'wbtk_trim_texel_density', 1.0)

        count, guessed = 0, []
        for child in master.children:
            if child.type != 'MESH':
                continue
            row = _get_trim_row(child.name)
            if row is None:
                row = _DEFAULT_ROW
                guessed.append(child.name)
            if _apply_trim_uvs(child, row, texel_density):
                count += 1

        if count == 0:
            self.report({'WARNING'}, "No mesh children found to UV-remap.")
            return {'CANCELLED'}

        if guessed:
            print("\n--- Trim UVs: %d of %d names matched no trim row ---" % (len(guessed), count))
            for n in guessed:
                print("      %-46s -> row %d (%s) BY DEFAULT, not by match"
                      % (n, _DEFAULT_ROW, TRIM_ROWS[_DEFAULT_ROW][2]))
            print("--- end ---\n")
            # WARNING, not INFO. Silently calling an antenna a wall is how this
            # went unnoticed; the operator still succeeds, but it says what it guessed.
            self.report({'WARNING'},
                        "Trim UVs applied to %d objects - but %d matched NO trim row and were "
                        "mapped to '%s' by default. See Console."
                        % (count, len(guessed), TRIM_ROWS[_DEFAULT_ROW][2]))
            return {'FINISHED'}

        self.report({'INFO'}, f"Trim UVs applied to {count} objects.")
        return {'FINISHED'}


# ── AUTO-APPLY HELPER (called from operators_structures after generation) ──

def auto_apply_trim_uvs(master_empty, texel_density=1.0):
    """Apply trim UVs to all mesh children of a building master empty."""
    if not master_empty:
        return
    for child in master_empty.children:
        if child.type != 'MESH':
            continue
        row = _get_trim_row(child.name)
        if row is None:
            row = _DEFAULT_ROW      # same guess as before, now written down
        _apply_trim_uvs(child, row, texel_density)


_classes_to_register = (
    WBTK_OT_apply_trim_uvs,
)
