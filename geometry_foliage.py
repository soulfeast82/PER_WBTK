# World_Building_Toolkit/geometry_foliage.py
# Pure geometry functions for the foliage generator.
# No bpy.ops calls — all BMesh operations for performance.

import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix, Euler


# =============================================================================
#  REGION PRESETS
#  Each preset is a dict of property values that gets loaded into the UI sliders.
#  Phase 2 will add CACTUS, VINE, BIOLUMINESCENT presets.
# =============================================================================

FOLIAGE_PRESETS = {

    # ── VJOLDRHEIM ─────────────────────────────────────────────────────────────
    'VJOLDRHEIM_PINE': {
        'label': 'Vjoldrheim — Pine',
        'type': 'TREE',
        'tree_height':          8.0,
        'trunk_radius':         0.20,
        'trunk_taper':          0.75,
        'branch_levels':        3,
        'branch_count':         6,
        'branch_angle':         50.0,
        'branch_length_factor': 0.55,
        'branch_taper':         0.65,
        'leaf_density':         50,
        'leaf_size':            0.35,
        'leaf_shape':           'NEEDLE',
        'leaf_droop':           0.15,
        'randomize_seed':       42,
    },
    'VJOLDRHEIM_BIRCH': {
        'label': 'Vjoldrheim — Birch',
        'type': 'TREE',
        'tree_height':          6.0,
        'trunk_radius':         0.12,
        'trunk_taper':          0.85,
        'branch_levels':        2,
        'branch_count':         5,
        'branch_angle':         60.0,
        'branch_length_factor': 0.65,
        'branch_taper':         0.70,
        'leaf_density':         40,
        'leaf_size':            0.25,
        'leaf_shape':           'ROUND',
        'leaf_droop':           0.30,
        'randomize_seed':       17,
    },
    'VJOLDRHEIM_SHRUB': {
        'label': 'Vjoldrheim — Nordic Shrub',
        'type': 'SHRUB',
        'shrub_height':         1.2,
        'shrub_width':          1.0,
        'shrub_branch_count':   12,
        'shrub_branch_angle':   55.0,
        'shrub_leaf_density':   35,
        'shrub_leaf_size':      0.18,
        'shrub_leaf_shape':     'ROUND',
        'randomize_seed':       33,
    },
    'VJOLDRHEIM_MOSS': {
        'label': 'Vjoldrheim — Forest Floor Moss',
        'type': 'GROUND',
        'ground_type':          'MOSS',
        'ground_patch_radius':  0.8,
        'ground_blade_count':   80,
        'ground_blade_height':  0.08,
        'ground_blade_width':   0.04,
        'ground_droop':         0.5,
        'ground_cluster_scatter': 0.6,
        'randomize_seed':       9,
    },

    # ── TIERRA OXIDADA ─────────────────────────────────────────────────────────
    'TIERRA_DRY_TREE': {
        'label': 'Tierra Oxidada — Dead Tree',
        'type': 'TREE',
        'tree_height':          4.0,
        'trunk_radius':         0.18,
        'trunk_taper':          0.60,
        'branch_levels':        2,
        'branch_count':         4,
        'branch_angle':         70.0,
        'branch_length_factor': 0.50,
        'branch_taper':         0.55,
        'leaf_density':         5,   # Almost no leaves — dead tree
        'leaf_size':            0.15,
        'leaf_shape':           'NEEDLE',
        'leaf_droop':           0.0,
        'randomize_seed':       55,
    },
    'TIERRA_SCRUB': {
        'label': 'Tierra Oxidada — Desert Scrub',
        'type': 'SHRUB',
        'shrub_height':         0.7,
        'shrub_width':          0.9,
        'shrub_branch_count':   8,
        'shrub_branch_angle':   65.0,
        'shrub_leaf_density':   20,
        'shrub_leaf_size':      0.10,
        'shrub_leaf_shape':     'NEEDLE',
        'randomize_seed':       71,
    },
    'TIERRA_DRY_GRASS': {
        'label': 'Tierra Oxidada — Dry Grass',
        'type': 'GROUND',
        'ground_type':          'GRASS',
        'ground_patch_radius':  0.6,
        'ground_blade_count':   30,
        'ground_blade_height':  0.25,
        'ground_blade_width':   0.02,
        'ground_droop':         0.7,
        'ground_cluster_scatter': 0.8,
        'randomize_seed':       88,
    },

    # ── DUSK WARD ──────────────────────────────────────────────────────────────
    'DUSK_CITY_WEED': {
        'label': 'Dusk Ward — City Weed',
        'type': 'GROUND',
        'ground_type':          'WEED',
        'ground_patch_radius':  0.25,
        'ground_blade_count':   15,
        'ground_blade_height':  0.18,
        'ground_blade_width':   0.025,
        'ground_droop':         0.4,
        'ground_cluster_scatter': 0.3,
        'randomize_seed':       13,
    },
    'DUSK_CITY_TREE': {
        'label': 'Dusk Ward — Scraggly City Tree',
        'type': 'TREE',
        'tree_height':          5.0,
        'trunk_radius':         0.14,
        'trunk_taper':          0.70,
        'branch_levels':        2,
        'branch_count':         4,
        'branch_angle':         65.0,
        'branch_length_factor': 0.60,
        'branch_taper':         0.65,
        'leaf_density':         20,
        'leaf_size':            0.22,
        'leaf_shape':           'ROUND',
        'leaf_droop':           0.45,
        'randomize_seed':       7,
    },

    # ── RADIANT CIRCLE ─────────────────────────────────────────────────────────
    'RADIANT_ORNAMENTAL': {
        'label': 'Radiant Circle — Ornamental Tree',
        'type': 'TREE',
        'tree_height':          4.5,
        'trunk_radius':         0.12,
        'trunk_taper':          0.90,
        'branch_levels':        2,
        'branch_count':         8,
        'branch_angle':         40.0,
        'branch_length_factor': 0.45,
        'branch_taper':         0.80,
        'leaf_density':         60,
        'leaf_size':            0.20,
        'leaf_shape':           'ROUND',
        'leaf_droop':           0.05,
        'randomize_seed':       100,
    },
    'RADIANT_HEDGE': {
        'label': 'Radiant Circle — Manicured Hedge',
        'type': 'SHRUB',
        'shrub_height':         1.5,
        'shrub_width':          2.0,
        'shrub_branch_count':   20,
        'shrub_branch_angle':   30.0,
        'shrub_leaf_density':   60,
        'shrub_leaf_size':      0.12,
        'shrub_leaf_shape':     'ROUND',
        'randomize_seed':       200,
    },

    # ── GENERIC ────────────────────────────────────────────────────────────────
    'GENERIC_TREE': {
        'label': 'Generic — Basic Tree',
        'type': 'TREE',
        'tree_height':          5.0,
        'trunk_radius':         0.15,
        'trunk_taper':          0.75,
        'branch_levels':        2,
        'branch_count':         5,
        'branch_angle':         55.0,
        'branch_length_factor': 0.60,
        'branch_taper':         0.70,
        'leaf_density':         35,
        'leaf_size':            0.25,
        'leaf_shape':           'ROUND',
        'leaf_droop':           0.20,
        'randomize_seed':       1,
    },
    'GENERIC_SHRUB': {
        'label': 'Generic — Basic Shrub',
        'type': 'SHRUB',
        'shrub_height':         1.0,
        'shrub_width':          1.2,
        'shrub_branch_count':   10,
        'shrub_branch_angle':   50.0,
        'shrub_leaf_density':   30,
        'shrub_leaf_size':      0.15,
        'shrub_leaf_shape':     'ROUND',
        'randomize_seed':       2,
    },
    'GENERIC_GRASS': {
        'label': 'Generic — Basic Grass',
        'type': 'GROUND',
        'ground_type':          'GRASS',
        'ground_patch_radius':  0.5,
        'ground_blade_count':   40,
        'ground_blade_height':  0.20,
        'ground_blade_width':   0.02,
        'ground_droop':         0.25,
        'ground_cluster_scatter': 0.5,
        'randomize_seed':       3,
    },
}

# Enum items for the UI dropdown — (identifier, label, description)
PRESET_ENUM_ITEMS = [
    ('NONE', '— Select Preset —', ''),
] + [
    (key, data['label'], '')
    for key, data in FOLIAGE_PRESETS.items()
]


# =============================================================================
#  GEOMETRY — TREE
# =============================================================================

class GeometryFoliage:
    """
    Pure geometry functions for foliage generation.
    All return BMesh objects or lists of vertices/faces — no bpy.ops.
    """

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _add_cylinder_segment(bm, base_pos, tip_pos, base_radius, tip_radius, segments=6):
        """
        Add a tapered cylinder (frustum) between two points to a BMesh.
        Used for trunk and branch segments.
        Returns the list of tip verts so the next segment can reuse them.
        """
        direction = tip_pos - base_pos
        length = direction.length
        if length < 0.001:
            return []

        # Build a rotation matrix aligning Z axis to the branch direction
        z_axis = direction.normalized()
        # Choose an arbitrary up vector that isn't parallel to z_axis
        up = Vector((0, 1, 0)) if abs(z_axis.dot(Vector((0, 0, 1)))) > 0.99 else Vector((0, 0, 1))
        x_axis = z_axis.cross(up).normalized()
        y_axis = z_axis.cross(x_axis).normalized()
        rot = Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()

        angle_step = 2 * math.pi / segments
        base_verts = []
        tip_verts = []

        for i in range(segments):
            angle = i * angle_step
            offset_x = math.cos(angle)
            offset_y = math.sin(angle)
            local_offset = Vector((offset_x, offset_y, 0))

            base_world = base_pos + (rot.to_3x3() @ (local_offset * base_radius))
            tip_world  = tip_pos  + (rot.to_3x3() @ (local_offset * tip_radius))

            base_verts.append(bm.verts.new(base_world))
            tip_verts.append(bm.verts.new(tip_world))

        # Side faces
        for i in range(segments):
            next_i = (i + 1) % segments
            try:
                bm.faces.new((
                    base_verts[i], base_verts[next_i],
                    tip_verts[next_i], tip_verts[i]
                ))
            except ValueError:
                pass

        return tip_verts

    @staticmethod
    def _add_leaf_card(bm, position, normal, size, droop_factor, rng):
        """
        Add a single leaf card (billboard quad) at the given position.
        The card faces outward along the normal with slight random tilt.
        """
        # Random rotation around the normal
        angle = rng.uniform(0, math.pi * 2)
        tilt = rng.uniform(-0.3, 0.3) + droop_factor * 0.5

        # Build an orthonormal basis for the leaf plane
        up = Vector((0, 0, 1))
        if abs(normal.dot(up)) > 0.95:
            up = Vector((1, 0, 0))

        right = normal.cross(up).normalized()
        up_leaf = normal.cross(right).normalized()

        # Rotate right/up by random angle around normal
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        right_rot  = right  * cos_a + up_leaf * sin_a
        up_rot     = right  * (-sin_a) + up_leaf * cos_a

        half = size * 0.5
        # Apply droop: tip of leaf bends downward
        droop_vec = Vector((0, 0, -droop_factor * size * 0.5))

        v0 = bm.verts.new(position - right_rot * half - up_rot * half)
        v1 = bm.verts.new(position + right_rot * half - up_rot * half)
        v2 = bm.verts.new(position + right_rot * half + up_rot * half + droop_vec)
        v3 = bm.verts.new(position - right_rot * half + up_rot * half + droop_vec)

        try:
            bm.faces.new((v0, v1, v2, v3))
            # Back face for double-sided appearance
            bm.faces.new((v0, v3, v2, v1))
        except ValueError:
            pass

    @staticmethod
    def _build_branch(bm_trunk, bm_leaves, start_pos, direction, length,
                      base_radius, taper, branch_levels, branch_count,
                      branch_angle_deg, branch_length_factor, branch_taper,
                      leaf_density, leaf_size, leaf_droop, leaf_shape,
                      current_level, segments, rng):
        """
        Recursive branch builder.
        current_level 0 = trunk, 1 = primary branches, 2 = secondary, etc.
        """
        if current_level > branch_levels or length < 0.05:
            return

        tip_radius = base_radius * taper
        tip_pos = start_pos + direction * length

        # Add this branch segment to the trunk mesh
        GeometryFoliage._add_cylinder_segment(
            bm_trunk, start_pos, tip_pos,
            base_radius, max(tip_radius, 0.01),
            segments
        )

        is_tip = (current_level == branch_levels)

        if is_tip:
            # Add leaves clustered around the tip
            for _ in range(leaf_density):
                scatter = rng.uniform(0, length * 0.6)
                leaf_pos = start_pos + direction * (length * 0.4 + scatter)
                leaf_pos += Vector((
                    rng.uniform(-leaf_size, leaf_size),
                    rng.uniform(-leaf_size, leaf_size),
                    rng.uniform(-leaf_size * 0.5, leaf_size * 0.5)
                ))
                leaf_normal = (leaf_pos - start_pos).normalized()
                if leaf_normal.length < 0.001:
                    leaf_normal = direction

                if leaf_shape == 'NEEDLE':
                    # Needle leaves are elongated and oriented along the branch
                    GeometryFoliage._add_leaf_card(
                        bm_leaves, leaf_pos, direction,
                        leaf_size * 2.0, leaf_droop, rng
                    )
                else:
                    GeometryFoliage._add_leaf_card(
                        bm_leaves, leaf_pos, leaf_normal,
                        leaf_size, leaf_droop, rng
                    )
        else:
            # Spawn child branches
            child_length = length * branch_length_factor
            child_radius = tip_radius * 0.7

            for i in range(branch_count):
                # Distribute child branches evenly around the parent direction
                azimuth = (2 * math.pi / branch_count) * i
                azimuth += rng.uniform(-0.3, 0.3)  # slight random offset

                branch_angle_rad = math.radians(branch_angle_deg)
                branch_angle_rad += rng.uniform(-0.15, 0.15)

                # Build rotation: tilt away from parent direction then rotate around it
                perp = direction.cross(Vector((0, 0, 1)))
                if perp.length < 0.001:
                    perp = direction.cross(Vector((1, 0, 0)))
                perp.normalize()

                # Tilt matrix around perpendicular axis
                tilt_mat = Matrix.Rotation(branch_angle_rad, 4, perp)
                # Twist matrix around parent direction
                twist_mat = Matrix.Rotation(azimuth, 4, direction)

                child_dir = (twist_mat @ tilt_mat @ direction.to_4d()).to_3d().normalized()

                # Place child branch starting partway along the parent
                t = rng.uniform(0.5, 0.85)
                child_start = start_pos + direction * (length * t)

                GeometryFoliage._build_branch(
                    bm_trunk, bm_leaves,
                    child_start, child_dir, child_length,
                    child_radius, branch_taper,
                    branch_levels, branch_count,
                    branch_angle_deg, branch_length_factor, branch_taper,
                    leaf_density, leaf_size, leaf_droop, leaf_shape,
                    current_level + 1,
                    max(3, segments - 1),
                    rng
                )

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    @staticmethod
    def build_tree(params):
        """
        Build a complete tree.
        Returns (bm_trunk, bm_leaves) — two separate BMeshes.
        The trunk mesh also contains all branch geometry.
        The leaves mesh contains all leaf cards.
        """
        rng = random.Random(params.get('randomize_seed', 1))

        bm_trunk  = bmesh.new()
        bm_leaves = bmesh.new()

        trunk_dir    = Vector((0, 0, 1))
        trunk_start  = Vector((0, 0, 0))
        trunk_height = params.get('tree_height', 5.0)
        trunk_radius = params.get('trunk_radius', 0.15)
        trunk_taper  = params.get('trunk_taper', 0.75)

        branch_levels        = params.get('branch_levels', 2)
        branch_count         = params.get('branch_count', 5)
        branch_angle         = params.get('branch_angle', 55.0)
        branch_length_factor = params.get('branch_length_factor', 0.60)
        branch_taper         = params.get('branch_taper', 0.70)
        leaf_density         = params.get('leaf_density', 35)
        leaf_size            = params.get('leaf_size', 0.25)
        leaf_shape           = params.get('leaf_shape', 'ROUND')
        leaf_droop           = params.get('leaf_droop', 0.2)

        GeometryFoliage._build_branch(
            bm_trunk, bm_leaves,
            trunk_start, trunk_dir, trunk_height,
            trunk_radius, trunk_taper,
            branch_levels, branch_count,
            branch_angle, branch_length_factor, branch_taper,
            leaf_density, leaf_size, leaf_droop, leaf_shape,
            current_level=0,
            segments=8,
            rng=rng
        )

        bmesh.ops.recalc_face_normals(bm_trunk,  faces=bm_trunk.faces[:])
        bmesh.ops.recalc_face_normals(bm_leaves, faces=bm_leaves.faces[:])

        return bm_trunk, bm_leaves


    @staticmethod
    def build_shrub(params):
        """
        Build a shrub/bush.
        Returns (bm_branches, bm_leaves).
        Shrub is a dense cluster of branches emanating from a low origin point.
        """
        rng = random.Random(params.get('randomize_seed', 2))

        bm_branches = bmesh.new()
        bm_leaves   = bmesh.new()

        height       = params.get('shrub_height', 1.0)
        width        = params.get('shrub_width', 1.2)
        branch_count = params.get('shrub_branch_count', 10)
        branch_angle = params.get('shrub_branch_angle', 50.0)
        leaf_density = params.get('shrub_leaf_density', 30)
        leaf_size    = params.get('shrub_leaf_size', 0.15)
        leaf_shape   = params.get('shrub_leaf_shape', 'ROUND')
        leaf_droop   = 0.15

        for i in range(branch_count):
            # Distribute branches evenly in azimuth with random variation
            azimuth = (2 * math.pi / branch_count) * i + rng.uniform(-0.2, 0.2)
            tilt = math.radians(branch_angle + rng.uniform(-15, 15))

            # Direction: tilted outward from centre
            dir_x = math.sin(tilt) * math.cos(azimuth)
            dir_y = math.sin(tilt) * math.sin(azimuth)
            dir_z = math.cos(tilt)
            branch_dir = Vector((dir_x, dir_y, dir_z)).normalized()

            # Length varies with width/height ratio
            branch_len = rng.uniform(height * 0.7, height * 1.1)

            # Small random start offset from origin
            start = Vector((
                rng.uniform(-0.05, 0.05),
                rng.uniform(-0.05, 0.05),
                rng.uniform(0.0, height * 0.15)
            ))

            branch_radius = rng.uniform(0.015, 0.03)
            tip_radius    = branch_radius * 0.4

            GeometryFoliage._add_cylinder_segment(
                bm_branches, start, start + branch_dir * branch_len,
                branch_radius, tip_radius, segments=4
            )

            # Leaves distributed along the branch
            for _ in range(leaf_density // branch_count + 1):
                t = rng.uniform(0.3, 1.0)
                leaf_pos = start + branch_dir * (branch_len * t)
                leaf_pos += Vector((
                    rng.uniform(-leaf_size * 0.5, leaf_size * 0.5),
                    rng.uniform(-leaf_size * 0.5, leaf_size * 0.5),
                    rng.uniform(-leaf_size * 0.3, leaf_size * 0.3),
                ))
                leaf_normal = (leaf_pos - Vector((0, 0, 0))).normalized()
                GeometryFoliage._add_leaf_card(
                    bm_leaves, leaf_pos, leaf_normal,
                    leaf_size, leaf_droop, rng
                )

        bmesh.ops.recalc_face_normals(bm_branches, faces=bm_branches.faces[:])
        bmesh.ops.recalc_face_normals(bm_leaves,   faces=bm_leaves.faces[:])

        return bm_branches, bm_leaves


    @staticmethod
    def build_ground_cover(params):
        """
        Build a ground cover patch (grass, weeds, or moss).
        Returns a single BMesh — ground cover doesn't need separate material meshes
        for basic use, but each blade/tuft can have a different face for painting.
        """
        rng = random.Random(params.get('randomize_seed', 3))

        bm = bmesh.new()

        ground_type    = params.get('ground_type', 'GRASS')
        patch_radius   = params.get('ground_patch_radius', 0.5)
        blade_count    = params.get('ground_blade_count', 40)
        blade_height   = params.get('ground_blade_height', 0.20)
        blade_width    = params.get('ground_blade_width', 0.02)
        droop          = params.get('ground_droop', 0.25)
        scatter        = params.get('ground_cluster_scatter', 0.5)

        for i in range(blade_count):
            # Random position within the patch radius
            angle  = rng.uniform(0, math.pi * 2)
            radius = rng.uniform(0, patch_radius) ** 0.5  # sqrt for uniform distribution
            base_x = math.cos(angle) * radius * scatter * patch_radius / max(scatter, 0.01)
            base_y = math.sin(angle) * radius * scatter * patch_radius / max(scatter, 0.01)
            base_pos = Vector((base_x, base_y, 0.0))

            if ground_type == 'MOSS':
                # Moss: very short, wide, flat overlapping cards
                h = blade_height * rng.uniform(0.5, 1.0)
                w = blade_width  * rng.uniform(3.0, 6.0)
                normal = Vector((
                    rng.uniform(-0.3, 0.3),
                    rng.uniform(-0.3, 0.3),
                    1.0
                )).normalized()
                tip = base_pos + normal * h
                GeometryFoliage._add_leaf_card(bm, tip, normal, w, droop, rng)

            elif ground_type == 'WEED':
                # Weeds: a few taller, wider blades per tuft
                tuft_blades = rng.randint(2, 5)
                for j in range(tuft_blades):
                    offset = Vector((
                        rng.uniform(-0.03, 0.03),
                        rng.uniform(-0.03, 0.03),
                        0
                    ))
                    tilt_x = rng.uniform(-0.4, 0.4)
                    tilt_y = rng.uniform(-0.4, 0.4)
                    tip = base_pos + offset + Vector((
                        tilt_x * blade_height,
                        tilt_y * blade_height,
                        blade_height * rng.uniform(0.7, 1.3)
                    ))
                    mid = (base_pos + offset + tip) * 0.5
                    # Blade as a narrow quad
                    blade_dir = (tip - base_pos - offset).normalized()
                    perp = blade_dir.cross(Vector((0, 0, 1)))
                    if perp.length < 0.001:
                        perp = Vector((1, 0, 0))
                    perp.normalize()
                    half_w = blade_width * rng.uniform(0.8, 1.5) * 0.5
                    droop_offset = Vector((0, 0, -droop * blade_height * 0.3))

                    v0 = bm.verts.new(base_pos + offset - perp * half_w)
                    v1 = bm.verts.new(base_pos + offset + perp * half_w)
                    v2 = bm.verts.new(tip + perp * half_w * 0.3 + droop_offset)
                    v3 = bm.verts.new(tip - perp * half_w * 0.3 + droop_offset)
                    try:
                        bm.faces.new((v0, v1, v2, v3))
                        bm.faces.new((v0, v3, v2, v1))
                    except ValueError:
                        pass

            else:
                # GRASS: single tapered blade per position
                tilt_x = rng.uniform(-droop, droop)
                tilt_y = rng.uniform(-droop, droop)
                tip = base_pos + Vector((
                    tilt_x * blade_height,
                    tilt_y * blade_height,
                    blade_height * rng.uniform(0.8, 1.2)
                ))

                blade_dir = (tip - base_pos).normalized()
                perp = blade_dir.cross(Vector((0, 0, 1)))
                if perp.length < 0.001:
                    perp = Vector((1, 0, 0))
                perp.normalize()

                half_w = blade_width * 0.5
                tip_w  = half_w * 0.15  # Taper to point

                v0 = bm.verts.new(base_pos - perp * half_w)
                v1 = bm.verts.new(base_pos + perp * half_w)
                v2 = bm.verts.new(tip + perp * tip_w)
                v3 = bm.verts.new(tip - perp * tip_w)
                try:
                    bm.faces.new((v0, v1, v2, v3))
                    bm.faces.new((v0, v3, v2, v1))
                except ValueError:
                    pass

        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return bm
