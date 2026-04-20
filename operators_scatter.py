# World_Building_Toolkit/operators_scatter.py
# Surface Scatter — scatter props across any selected flat surface.
#
# HOW IT WORKS:
#  1. Select a mesh object (building roof, ground plane, walkway, etc.)
#  2. Choose prop type (or Random Mix)
#  3. Set count + seed
#  4. Click Scatter — props appear distributed across the surface
#
# Uses the selected object's bounding box top face as the scatter region.
# Each prop is generated as BMesh and parented under a scatter master empty.

import bpy
import bmesh
import math
import random
from mathutils import Vector

from .config import Config
from .utils import Utils
from .operators_walkways import OP_BaseGenerator


# ================================================================== #
#  PROP BUILDERS — small BMesh generators for scatter props            #
# ================================================================== #

def _build_ac_unit(bm, scale, rng):
    """Boxy AC unit with fan circle on top."""
    w = 0.8 * scale * rng.uniform(0.85, 1.15)
    d = 0.5 * scale * rng.uniform(0.85, 1.15)
    h = 0.4 * scale * rng.uniform(0.8, 1.2)

    # Main box
    _add_box(bm, 0, 0, 0, w, d, h)

    # Fan circle on top (simplified as octagon)
    fan_r = min(w, d) * 0.35
    cx, cy = w / 2, d / 2
    fan_segs = 8
    fan_verts = []
    for i in range(fan_segs):
        angle = 2.0 * math.pi * i / fan_segs
        fan_verts.append(bm.verts.new((
            cx + math.cos(angle) * fan_r,
            cy + math.sin(angle) * fan_r,
            h + 0.01
        )))
    try:
        bm.faces.new(fan_verts)
    except ValueError:
        pass


def _build_water_tank(bm, scale, rng):
    """Cylindrical water tank on short legs."""
    radius = 0.4 * scale * rng.uniform(0.8, 1.2)
    tank_h = 0.8 * scale * rng.uniform(0.7, 1.3)
    leg_h = 0.25 * scale
    segs = 12

    # Legs (4 small boxes)
    leg_thick = 0.04 * scale
    offsets = [
        (radius * 0.6, radius * 0.6),
        (-radius * 0.6, radius * 0.6),
        (radius * 0.6, -radius * 0.6),
        (-radius * 0.6, -radius * 0.6),
    ]
    for ox, oy in offsets:
        _add_box(bm, ox - leg_thick, oy - leg_thick, 0,
                 leg_thick * 2, leg_thick * 2, leg_h)

    # Tank cylinder
    bot_ring = []
    top_ring = []
    for i in range(segs):
        angle = 2.0 * math.pi * i / segs
        ca = math.cos(angle) * radius
        sa = math.sin(angle) * radius
        bot_ring.append(bm.verts.new((ca, sa, leg_h)))
        top_ring.append(bm.verts.new((ca, sa, leg_h + tank_h)))

    for i in range(segs):
        j = (i + 1) % segs
        try:
            bm.faces.new((bot_ring[i], bot_ring[j], top_ring[j], top_ring[i]))
        except ValueError:
            pass
    try:
        bm.faces.new(list(reversed(bot_ring)))
    except ValueError:
        pass
    try:
        bm.faces.new(top_ring)
    except ValueError:
        pass


def _build_antenna(bm, scale, rng):
    """Thin antenna mast with cross-bars."""
    mast_h = 2.0 * scale * rng.uniform(0.6, 1.4)
    mast_r = 0.02 * scale

    # Mast (thin box standing up)
    _add_box(bm, -mast_r, -mast_r, 0, mast_r * 2, mast_r * 2, mast_h)

    # Cross-bars at 60% and 80% height
    bar_len = 0.3 * scale * rng.uniform(0.7, 1.3)
    bar_r = 0.01 * scale
    for frac in [0.6, 0.8]:
        z = mast_h * frac
        _add_box(bm, -bar_len / 2, -bar_r, z, bar_len, bar_r * 2, bar_r * 2)


def _build_crate_small(bm, scale, rng):
    """Small crate with slight size variation."""
    w = 0.5 * scale * rng.uniform(0.7, 1.3)
    d = 0.5 * scale * rng.uniform(0.7, 1.3)
    h = 0.4 * scale * rng.uniform(0.7, 1.3)
    _add_box(bm, 0, 0, 0, w, d, h)


def _build_barrel_simple(bm, scale, rng):
    """Metal barrel with bulge profile and rib indentations — matches standalone barrel quality."""
    radius = 0.2 * scale * rng.uniform(0.8, 1.2)
    height = 0.6 * scale * rng.uniform(0.8, 1.2)
    segs = 12
    rings_n = 8  # Vertical subdivisions

    # Build rings with sine bulge
    rings = []
    for ri in range(rings_n + 1):
        z_frac = ri / rings_n
        z = z_frac * height
        bulge = 1.0 + math.sin(z_frac * math.pi) * 0.08
        ring = []
        for si in range(segs):
            angle = 2.0 * math.pi * si / segs
            r = radius * bulge
            ring.append(bm.verts.new((math.cos(angle) * r, math.sin(angle) * r, z)))
        rings.append(ring)

    # Side faces
    for ri in range(rings_n):
        for si in range(segs):
            sj = (si + 1) % segs
            try:
                bm.faces.new((rings[ri][si], rings[ri][sj], rings[ri + 1][sj], rings[ri + 1][si]))
            except ValueError:
                pass

    # Cap faces
    try:
        bm.faces.new(list(reversed(rings[0])))
    except ValueError:
        pass
    try:
        bm.faces.new(rings[-1])
    except ValueError:
        pass

    # Rib indentations — push rib-ring verts inward slightly
    rib_fracs = [0.25, 0.5, 0.75]
    for rf in rib_fracs:
        ri = round(rf * rings_n)
        if 0 < ri < rings_n:
            for v in rings[ri]:
                v.co.x *= 0.96
                v.co.y *= 0.96


def _build_vent_box(bm, scale, rng):
    """Exhaust vent box (like a chimney stub)."""
    w = 0.3 * scale * rng.uniform(0.8, 1.2)
    d = 0.3 * scale * rng.uniform(0.8, 1.2)
    h = 0.5 * scale * rng.uniform(0.6, 1.4)
    _add_box(bm, 0, 0, 0, w, d, h)
    # Cap overhang
    overhang = 0.04 * scale
    _add_box(bm, -overhang, -overhang, h,
             w + overhang * 2, d + overhang * 2, 0.03 * scale)


# ── HELPER ────────────────────────────────────────────────────────────

def _add_box(bm, x, y, z, w, d, h):
    """Add a simple box to the BMesh."""
    v = [
        bm.verts.new((x,     y,     z)),
        bm.verts.new((x + w, y,     z)),
        bm.verts.new((x + w, y + d, z)),
        bm.verts.new((x,     y + d, z)),
        bm.verts.new((x,     y,     z + h)),
        bm.verts.new((x + w, y,     z + h)),
        bm.verts.new((x + w, y + d, z + h)),
        bm.verts.new((x,     y + d, z + h)),
    ]
    faces = [(0,1,2,3), (4,7,6,5), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)]
    for a, b, c, d_i in faces:
        try:
            bm.faces.new((v[a], v[b], v[c], v[d_i]))
        except ValueError:
            pass


# ── PROP TYPE REGISTRY ────────────────────────────────────────────────

PROP_BUILDERS = {
    'AC_UNIT':    (_build_ac_unit,       Config.MATERIAL_PROP_METAL),
    'WATER_TANK': (_build_water_tank,    Config.MATERIAL_PROP_METAL),
    'ANTENNA':    (_build_antenna,       Config.MATERIAL_PROP_METAL),
    'CRATE':      (_build_crate_small,   Config.MATERIAL_PROP_WOOD),
    'BARREL':     (_build_barrel_simple, Config.MATERIAL_PROP_METAL),
    'VENT_BOX':   (_build_vent_box,      Config.MATERIAL_PROP_METAL),
}

ALL_PROP_KEYS = list(PROP_BUILDERS.keys())


# ================================================================== #
#  OPERATOR — SURFACE SCATTER                                          #
# ================================================================== #

class OP_SurfaceScatter(OP_BaseGenerator):
    bl_idname = "wbtk.surface_scatter"
    bl_label = "Scatter Props on Surface"
    bl_description = (
        "Scatter props across the top of the selected mesh object. "
        "Select a roof, ground plane, or any flat surface first"
    )

    def execute(self, context):
        scene = context.scene

        # --- Validate selection ---
        target = context.active_object
        if not target or target.type != 'MESH':
            return self.report_warning(
                "Select a mesh object first — the surface to scatter props on.")

        prop_type   = scene.wbtk_scatter_prop_type
        count       = scene.wbtk_scatter_count
        seed        = scene.wbtk_scatter_seed
        scale       = scene.wbtk_scatter_scale
        margin      = scene.wbtk_scatter_margin
        random_rot  = scene.wbtk_scatter_random_rotation

        rng = random.Random(seed)

        # --- Get scatter region from bounding box ---
        # Use evaluated object for accurate bbox after modifiers
        try:
            depsgraph = context.evaluated_depsgraph_get()
            target_eval = target.evaluated_get(depsgraph)
            bbox_corners = [target_eval.matrix_world @ Vector(c) for c in target_eval.bound_box]
        except Exception:
            bbox_corners = [target.matrix_world @ Vector(c) for c in target.bound_box]

        min_x = min(c.x for c in bbox_corners) + margin
        max_x = max(c.x for c in bbox_corners) - margin
        min_y = min(c.y for c in bbox_corners) + margin
        max_y = max(c.y for c in bbox_corners) - margin
        top_z = max(c.z for c in bbox_corners)

        if max_x <= min_x or max_y <= min_y:
            return self.report_warning(
                "Surface too small for scattering with current margin. "
                "Reduce margin or use a larger surface.")

        # --- Create scatter master ---
        master = Utils.create_master(f"Scatter_{prop_type}")

        # --- Place props ---
        placed = 0
        positions = []  # Track positions for minimum spacing

        min_spacing = 0.3 * scale  # Minimum distance between props

        attempts = 0
        max_attempts = count * 10  # Avoid infinite loops on tight surfaces

        while placed < count and attempts < max_attempts:
            attempts += 1

            px = rng.uniform(min_x, max_x)
            py = rng.uniform(min_y, max_y)

            # Check minimum spacing against existing placements
            too_close = False
            for existing in positions:
                dx = px - existing[0]
                dy = py - existing[1]
                if math.sqrt(dx * dx + dy * dy) < min_spacing:
                    too_close = True
                    break

            if too_close:
                continue

            positions.append((px, py))

            # Pick prop type
            if prop_type == 'RANDOM_MIX':
                chosen_key = rng.choice(ALL_PROP_KEYS)
            else:
                chosen_key = prop_type

            builder_fn, mat_name = PROP_BUILDERS[chosen_key]

            # Build prop mesh
            bm = bmesh.new()
            builder_fn(bm, scale, rng)

            if not bm.verts:
                bm.free()
                continue

            # Convert to object
            prop_name = f"Scatter_{chosen_key}_{placed:03d}"
            obj = Utils.bm_to_obj(bm, prop_name, Vector((px, py, top_z)), mat_name)

            if obj:
                obj.parent = master

                # Random rotation around Z
                if random_rot:
                    obj.rotation_euler.z = rng.uniform(0, math.pi * 2)

                placed += 1

        # Select master
        bpy.ops.object.select_all(action='DESELECT')
        master.select_set(True)
        context.view_layer.objects.active = master

        self.report({'INFO'},
                    f"WBTK: Scattered {placed} props on '{target.name}' (seed {seed})")
        return {'FINISHED'}


# ================================================================== #
#  REGISTRATION                                                        #
# ================================================================== #

_classes_to_register = (
    OP_SurfaceScatter,
)
