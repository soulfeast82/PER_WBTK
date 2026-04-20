# World_Building_Toolkit/operators_vents.py
# Vent & Grate generator — rectangular louver vents and circular exhaust fans.

import bpy
import bmesh
import math
from mathutils import Vector

from .config import Config
from .utils import Utils
from .operators_walkways import OP_BaseGenerator


# ================================================================== #
#  GEOMETRY HELPERS                                                    #
# ================================================================== #

def _create_rect_vent(bm, width, height, depth, slat_count, slat_angle_deg,
                      frame_thickness):
    """
    Build a rectangular wall vent with angled louver slats inside a frame.
    Oriented on the XZ plane (facing +Y), centered at origin.
    """
    hw = width / 2.0
    hh = height / 2.0
    ft = frame_thickness

    # ── OUTER FRAME (box with hollow center) ──────────────────────────
    # Front face of frame
    frame_verts_front = [
        Vector((-hw, 0, -hh)),        # 0: bottom-left outer
        Vector(( hw, 0, -hh)),        # 1: bottom-right outer
        Vector(( hw, 0,  hh)),        # 2: top-right outer
        Vector((-hw, 0,  hh)),        # 3: top-left outer
        Vector((-hw + ft, 0, -hh + ft)),  # 4: bottom-left inner
        Vector(( hw - ft, 0, -hh + ft)),  # 5: bottom-right inner
        Vector(( hw - ft, 0,  hh - ft)),  # 6: top-right inner
        Vector((-hw + ft, 0,  hh - ft)),  # 7: top-left inner
    ]
    fv_f = [bm.verts.new(v) for v in frame_verts_front]

    # Back face of frame (offset by depth)
    frame_verts_back = [v + Vector((0, -depth, 0)) for v in frame_verts_front]
    fv_b = [bm.verts.new(v) for v in frame_verts_back]

    # Frame front face (ring)
    for a, b, c, d in [(0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)]:
        try: bm.faces.new((fv_f[a], fv_f[b], fv_f[c], fv_f[d]))
        except ValueError: pass

    # Frame back face (ring, reversed winding)
    for a, b, c, d in [(0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)]:
        try: bm.faces.new((fv_b[d], fv_b[c], fv_b[b], fv_b[a]))
        except ValueError: pass

    # Frame sides (connect front to back — outer and inner edges)
    outer_pairs = [(0,1), (1,2), (2,3), (3,0)]
    inner_pairs = [(4,5), (5,6), (6,7), (7,4)]
    for (a, b) in outer_pairs:
        try: bm.faces.new((fv_f[a], fv_f[b], fv_b[b], fv_b[a]))
        except ValueError: pass
    for (a, b) in inner_pairs:
        try: bm.faces.new((fv_b[a], fv_b[b], fv_f[b], fv_f[a]))
        except ValueError: pass

    # ── LOUVER SLATS ──────────────────────────────────────────────────
    inner_w = width - 2 * ft
    inner_h = height - 2 * ft
    slat_angle = math.radians(slat_angle_deg)

    if slat_count > 0 and inner_h > 0:
        slat_spacing = inner_h / (slat_count + 1)
        slat_thick = min(0.008, slat_spacing * 0.15)
        half_depth = depth / 2.0

        for si in range(slat_count):
            center_z = -hh + ft + slat_spacing * (si + 1)

            # Slat is a thin rectangle rotated by slat_angle around X axis
            dz = math.cos(slat_angle) * slat_spacing * 0.4
            dy = math.sin(slat_angle) * slat_spacing * 0.4

            x_left  = -hw + ft
            x_right =  hw - ft

            s_verts = [
                Vector((x_left,  -half_depth - dy, center_z - dz)),
                Vector((x_right, -half_depth - dy, center_z - dz)),
                Vector((x_right, -half_depth + dy, center_z + dz)),
                Vector((x_left,  -half_depth + dy, center_z + dz)),
                # Back face offset by slat thickness
                Vector((x_left,  -half_depth - dy - slat_thick, center_z - dz)),
                Vector((x_right, -half_depth - dy - slat_thick, center_z - dz)),
                Vector((x_right, -half_depth + dy - slat_thick, center_z + dz)),
                Vector((x_left,  -half_depth + dy - slat_thick, center_z + dz)),
            ]
            sv = [bm.verts.new(v) for v in s_verts]

            # 6 faces for the slat box
            box_faces = [
                (0,1,2,3), (7,6,5,4),
                (0,1,5,4), (2,3,7,6),
                (1,2,6,5), (0,3,7,4),
            ]
            for a, b, c, d in box_faces:
                try: bm.faces.new((sv[a], sv[b], sv[c], sv[d]))
                except ValueError: pass


def _create_round_vent(bm, radius, depth, blade_count, segments,
                       frame_thickness):
    """
    Build a circular exhaust fan vent.
    Oriented facing +Y, centered at origin.
    """
    ft = frame_thickness
    inner_r = radius - ft

    # ── OUTER RIM ─────────────────────────────────────────────────────
    for ring_z in [0, -depth]:
        outer_ring = []
        inner_ring = []
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            ca = math.cos(angle)
            sa = math.sin(angle)
            outer_ring.append(bm.verts.new((ca * radius, ring_z, sa * radius)))
            inner_ring.append(bm.verts.new((ca * inner_r, ring_z, sa * inner_r)))

        # Annular face ring
        for i in range(segments):
            j = (i + 1) % segments
            try: bm.faces.new((outer_ring[i], outer_ring[j],
                               inner_ring[j], inner_ring[i]))
            except ValueError: pass

    # Connect front and back outer rings
    front_outer = []
    back_outer = []
    front_inner = []
    back_inner = []

    # Rebuild for skinning (the rings above were for face caps)
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments
        ca = math.cos(angle)
        sa = math.sin(angle)
        front_outer.append(bm.verts.new((ca * radius, 0, sa * radius)))
        back_outer.append(bm.verts.new((ca * radius, -depth, sa * radius)))
        front_inner.append(bm.verts.new((ca * inner_r, 0, sa * inner_r)))
        back_inner.append(bm.verts.new((ca * inner_r, -depth, sa * inner_r)))

    for i in range(segments):
        j = (i + 1) % segments
        # Outer barrel
        try: bm.faces.new((front_outer[i], front_outer[j],
                           back_outer[j], back_outer[i]))
        except ValueError: pass
        # Inner barrel
        try: bm.faces.new((back_inner[i], back_inner[j],
                           front_inner[j], front_inner[i]))
        except ValueError: pass

    # ── FAN BLADES ────────────────────────────────────────────────────
    if blade_count > 0:
        hub_r = inner_r * 0.15
        blade_w = inner_r * 0.08
        mid_y = -depth / 2.0

        # Center hub disc
        hub_verts = []
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            hub_verts.append(bm.verts.new((
                math.cos(angle) * hub_r, mid_y, math.sin(angle) * hub_r
            )))
        try: bm.faces.new(hub_verts)
        except ValueError: pass

        # Individual blades
        for bi in range(blade_count):
            blade_angle = 2.0 * math.pi * bi / blade_count
            ca = math.cos(blade_angle)
            sa = math.sin(blade_angle)

            # Blade goes from hub edge to inner rim
            tip_r = inner_r * 0.92

            # Slightly swept blade (offset in Y for 3D look)
            sweep = 0.02

            bv = [
                bm.verts.new((ca * hub_r,   mid_y,          sa * hub_r)),
                bm.verts.new((ca * tip_r,   mid_y + sweep,  sa * tip_r)),
                bm.verts.new((ca * tip_r + sa * blade_w, mid_y + sweep,
                              sa * tip_r - ca * blade_w)),
                bm.verts.new((ca * hub_r + sa * blade_w, mid_y,
                              sa * hub_r - ca * blade_w)),
            ]
            try: bm.faces.new(bv)
            except ValueError: pass


# ================================================================== #
#  OPERATOR — RECTANGULAR VENT                                         #
# ================================================================== #

class OP_GenerateRectVent(OP_BaseGenerator):
    bl_idname = "wbtk.generate_rect_vent"
    bl_label = "Generate Rectangular Vent"
    bl_description = "Generate a wall-mounted rectangular louver vent"

    def execute(self, context):
        scene = context.scene
        width  = scene.wbtk_vent_width
        height = scene.wbtk_vent_height
        depth  = scene.wbtk_vent_depth
        slats  = scene.wbtk_vent_slat_count
        angle  = scene.wbtk_vent_slat_angle
        frame  = scene.wbtk_vent_frame_thickness

        master = Utils.create_master("RectVent")
        bm = bmesh.new()

        _create_rect_vent(bm, width, height, depth, slats, angle, frame)

        self.create_and_parent(bm, "RectVent_Mesh", Vector((0, 0, 0)),
                               Config.MATERIAL_VENT, master)

        self.report({'INFO'}, f"WBTK: Rectangular vent ({width:.1f}x{height:.1f}m, {slats} slats)")
        return {'FINISHED'}


# ================================================================== #
#  OPERATOR — CIRCULAR VENT / EXHAUST FAN                              #
# ================================================================== #

class OP_GenerateRoundVent(OP_BaseGenerator):
    bl_idname = "wbtk.generate_round_vent"
    bl_label = "Generate Round Vent"
    bl_description = "Generate a circular exhaust fan vent"

    def execute(self, context):
        scene = context.scene
        radius   = scene.wbtk_vent_round_radius
        depth    = scene.wbtk_vent_depth
        blades   = scene.wbtk_vent_fan_blades
        segments = scene.wbtk_vent_round_segments
        frame    = scene.wbtk_vent_frame_thickness

        master = Utils.create_master("RoundVent")
        bm = bmesh.new()

        _create_round_vent(bm, radius, depth, blades, segments, frame)

        self.create_and_parent(bm, "RoundVent_Mesh", Vector((0, 0, 0)),
                               Config.MATERIAL_VENT, master)

        self.report({'INFO'}, f"WBTK: Round vent (r={radius:.2f}m, {blades} blades)")
        return {'FINISHED'}


# ================================================================== #
#  REGISTRATION                                                        #
# ================================================================== #

_classes_to_register = (
    OP_GenerateRectVent,
    OP_GenerateRoundVent,
)
