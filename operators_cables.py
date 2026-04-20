# World_Building_Toolkit/operators_cables.py
# Cable / wire generator — catenary curves for urban environments.

import bpy
import bmesh
import math
import random
from mathutils import Vector

from .config import Config
from .utils import Utils
from .operators_walkways import OP_BaseGenerator


# ================================================================== #
#  CABLE GEOMETRY                                                      #
# ================================================================== #

def _catenary_point(t, span, sag):
    """
    Compute a point on a catenary-like curve at parameter t (0..1).
    Uses parabolic approximation: y = 4*sag*t*(t-1)
    This is cheaper than true catenary (cosh) and looks identical
    at game-relevant scales.
    """
    return 4.0 * sag * t * (t - 1.0)


def _create_cable_mesh(bm, start, end, radius, segments, sag, twist_noise, seed):
    """
    Generate a tube mesh following a sagging cable path from *start* to *end*.

    *segments*    = subdivisions along the cable length
    *sag*         = maximum droop at midpoint (meters)
    *twist_noise* = random lateral wobble (0 = perfectly straight path)
    """
    rng = random.Random(seed)

    # Cable direction vector
    direction = end - start
    cable_length = direction.length
    if cable_length < 0.001:
        return

    forward = direction.normalized()

    # Build local coordinate frame
    up = Vector((0, 0, 1))
    if abs(forward.dot(up)) > 0.99:
        up = Vector((0, 1, 0))

    right = forward.cross(up).normalized()
    local_up = right.cross(forward).normalized()

    # Profile segments (tube cross-section)
    profile_segs = max(6, segments // 4)

    rings = []
    for s_idx in range(segments + 1):
        t = s_idx / max(segments, 1)

        # Position along cable
        pos = start + forward * (cable_length * t)

        # Sag (parabolic droop in local_up direction, which is gravity-opposing)
        droop = _catenary_point(t, cable_length, sag)
        pos += Vector((0, 0, droop))  # Droop is always in world Z (gravity)

        # Twist noise (lateral wobble)
        if twist_noise > 0:
            lateral = rng.uniform(-twist_noise, twist_noise) * math.sin(t * math.pi * 3)
            pos += right * lateral

        # Create tube ring at this position
        ring = []
        for p_idx in range(profile_segs):
            angle = 2.0 * math.pi * p_idx / profile_segs
            ca = math.cos(angle)
            sa = math.sin(angle)
            offset = right * (ca * radius) + local_up * (sa * radius)
            ring.append(bm.verts.new(pos + offset))
        rings.append(ring)

    # Skin the rings
    for i in range(len(rings) - 1):
        ring_a = rings[i]
        ring_b = rings[i + 1]
        n = len(ring_a)
        for j in range(n):
            k = (j + 1) % n
            try:
                bm.faces.new((ring_a[j], ring_a[k], ring_b[k], ring_b[j]))
            except ValueError:
                pass

    # Cap ends
    try:
        bm.faces.new(list(reversed(rings[0])))
    except ValueError:
        pass
    try:
        bm.faces.new(rings[-1])
    except ValueError:
        pass


# ================================================================== #
#  OP: GENERATE CABLE                                                  #
# ================================================================== #

class OP_GenerateCable(OP_BaseGenerator):
    bl_idname = "wbtk.generate_cable"
    bl_label = "Generate Cable"
    bl_description = "Generate a sagging cable/wire between two points"

    def execute(self, context):
        scene = context.scene

        span_length = scene.wbtk_cable_span
        sag         = scene.wbtk_cable_sag
        radius      = scene.wbtk_cable_radius
        segments    = scene.wbtk_cable_segments
        twist       = scene.wbtk_cable_twist
        height      = scene.wbtk_cable_height
        seed        = scene.wbtk_cable_seed

        if span_length <= 0:
            return self.report_warning("Cable span must be > 0.")

        master = Utils.create_master("Cable")
        origin = Vector((0, 0, 0))

        start = Vector((0, 0, height))
        end   = Vector((span_length, 0, height))

        bm = bmesh.new()
        _create_cable_mesh(bm, start, end, radius, segments, sag, twist, seed)

        self.create_and_parent(bm, "Cable_Mesh", origin,
                               Config.MATERIAL_CABLE, master)

        self.report({'INFO'},
                    f"WBTK: Cable generated ({span_length:.1f}m span, {sag:.1f}m sag)")
        return {'FINISHED'}


# ================================================================== #
#  OP: GENERATE CABLE BUNDLE                                           #
# ================================================================== #

class OP_GenerateCableBundle(OP_BaseGenerator):
    bl_idname = "wbtk.generate_cable_bundle"
    bl_label = "Generate Cable Bundle"
    bl_description = "Generate a cluster of cables with random sag and thickness variation"

    def execute(self, context):
        scene = context.scene

        count       = scene.wbtk_cable_bundle_count
        span_length = scene.wbtk_cable_span
        sag         = scene.wbtk_cable_sag
        radius      = scene.wbtk_cable_radius
        segments    = scene.wbtk_cable_segments
        twist       = scene.wbtk_cable_twist
        height      = scene.wbtk_cable_height
        spread      = scene.wbtk_cable_bundle_spread
        seed        = scene.wbtk_cable_seed

        if count < 1 or span_length <= 0:
            return self.report_warning("Need at least 1 cable and span > 0.")

        master = Utils.create_master("CableBundle")
        origin = Vector((0, 0, 0))
        rng = random.Random(seed + 88)

        for c_idx in range(count):
            # Random offsets for each cable
            y_off = rng.uniform(-spread, spread)
            z_off = rng.uniform(-spread * 0.3, spread * 0.3)
            c_radius = radius * rng.uniform(0.5, 1.3)
            c_sag = sag * rng.uniform(0.6, 1.4)
            c_twist = twist * rng.uniform(0.5, 1.5)

            start = Vector((0, y_off, height + z_off))
            end   = Vector((span_length, y_off, height + z_off))

            bm = bmesh.new()
            _create_cable_mesh(bm, start, end, c_radius, segments,
                               c_sag, c_twist, seed + c_idx * 73)

            self.create_and_parent(bm, f"Cable_{c_idx:02d}", origin,
                                   Config.MATERIAL_CABLE, master)

        self.report({'INFO'},
                    f"WBTK: Cable bundle ({count} cables, {span_length:.1f}m)")
        return {'FINISHED'}


# ================================================================== #
#  OP: CABLE BETWEEN SELECTED                                         #
# ================================================================== #

class OP_CableBetweenSelected(OP_BaseGenerator):
    bl_idname = "wbtk.cable_between_selected"
    bl_label = "Cable Between Selected"
    bl_description = "Generate a cable between two selected objects (connects at their tops)"

    def _get_top_center(self, obj):
        """Get the world-space center-top of an object's bounding box.
        For empties with mesh children (e.g. building masters),
        computes combined bounding box of all children."""
        try:
            # If this is an empty with children, use children's combined bbox
            mesh_children = [
                c for c in obj.children_recursive
                if c.type == 'MESH' and c.data and len(c.data.vertices) > 0
            ]

            if obj.type != 'MESH' and mesh_children:
                all_corners = []
                for child in mesh_children:
                    all_corners.extend(
                        [child.matrix_world @ Vector(c) for c in child.bound_box]
                    )
                if all_corners:
                    top_z = max(c.z for c in all_corners)
                    cx = (min(c.x for c in all_corners) + max(c.x for c in all_corners)) / 2
                    cy = (min(c.y for c in all_corners) + max(c.y for c in all_corners)) / 2
                    return Vector((cx, cy, top_z))

            # Standard mesh object
            bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            top_z = max(c.z for c in bbox)
            center_x = (min(c.x for c in bbox) + max(c.x for c in bbox)) / 2
            center_y = (min(c.y for c in bbox) + max(c.y for c in bbox)) / 2
            return Vector((center_x, center_y, top_z))
        except Exception:
            return obj.matrix_world.translation.copy()

    def execute(self, context):
        scene = context.scene

        selected = [obj for obj in context.selected_objects]
        if len(selected) < 2:
            return self.report_warning("Select exactly 2 objects to span a cable between them.")

        sag      = scene.wbtk_cable_sag
        radius   = scene.wbtk_cable_radius
        segments = scene.wbtk_cable_segments
        twist    = scene.wbtk_cable_twist
        seed     = scene.wbtk_cable_seed
        count    = scene.wbtk_cable_bundle_count
        spread   = scene.wbtk_cable_bundle_spread

        obj_a = selected[-2]
        obj_b = selected[-1]

        # Connect at the TOP of each object's bounding box
        start = self._get_top_center(obj_a)
        end   = self._get_top_center(obj_b)

        master = Utils.create_master("Cable_Span")
        origin = Vector((0, 0, 0))

        if count <= 1:
            # Single cable
            bm = bmesh.new()
            _create_cable_mesh(bm, start, end, radius, segments, sag, twist, seed)
            self.create_and_parent(bm, "Cable_Span_Mesh", origin,
                                   Config.MATERIAL_CABLE, master)
        else:
            # Bundle between selected
            rng = random.Random(seed + 88)
            direction = (end - start).normalized()
            up = Vector((0, 0, 1))
            if abs(direction.dot(up)) > 0.99:
                up = Vector((0, 1, 0))
            right = direction.cross(up).normalized()
            local_up = right.cross(direction).normalized()

            for c_idx in range(count):
                off_r = rng.uniform(-spread, spread)
                off_u = rng.uniform(-spread * 0.3, spread * 0.3)
                offset = right * off_r + local_up * off_u
                c_start = start + offset
                c_end = end + offset
                c_sag = sag * rng.uniform(0.6, 1.4)
                c_radius = radius * rng.uniform(0.5, 1.3)

                bm = bmesh.new()
                _create_cable_mesh(bm, c_start, c_end, c_radius, segments,
                                   c_sag, twist, seed + c_idx * 73)
                self.create_and_parent(bm, f"Cable_Span_{c_idx:02d}", origin,
                                       Config.MATERIAL_CABLE, master)

        span = (end - start).length
        self.report({'INFO'},
                    f"WBTK: {count} cable(s) from '{obj_a.name}' → '{obj_b.name}' ({span:.1f}m)")
        return {'FINISHED'}


# ================================================================== #
#  OP: RANDOMIZE CABLE SEED                                            #
# ================================================================== #

class OP_RandomizeCableSeed(OP_BaseGenerator):
    bl_idname = "wbtk.randomize_cable_seed"
    bl_label = "Randomize Cable Seed"
    bl_description = "Roll a new random seed for cable variation"

    def execute(self, context):
        context.scene.wbtk_cable_seed = random.randint(1, 99999)
        self.report({'INFO'},
                    f"WBTK: New cable seed = {context.scene.wbtk_cable_seed}")
        return {'FINISHED'}


# ================================================================== #
#  REGISTRATION                                                        #
# ================================================================== #

_classes_to_register = (
    OP_GenerateCable,
    OP_GenerateCableBundle,
    OP_CableBetweenSelected,
    OP_RandomizeCableSeed,
)
