# World_Building_Toolkit/bm_details.py
# Build Mode — Detail Stamps
# Procedural attachments that get placed on block faces after generation.
# AC units, vents, pipes, balconies, fire escapes, signs, antennas, canopies.

import bpy
import bmesh
import math
import json
from mathutils import Vector, Matrix

from .config import Config
from .utils import Utils
from . import bm_data

DETAIL_COLLECTION = "WBTK_Details"
DETAIL_PREFIX = "WBTK_DTL_"
DETAIL_KEY = "wbtk_detail"

# ─────────────────────────────────────────────────────────────────────────────
#  DETAIL DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

DETAIL_TYPES = {
    'AC_UNIT': {
        'label': "AC Unit",
        'icon': 'MESH_CUBE',
        'default_w': 0.8, 'default_h': 0.6, 'default_d': 0.4,
        'material': "WBTK_Detail_Metal",
        'color': (0.5, 0.5, 0.55),
    },
    'VENT': {
        'label': "Vent",
        'icon': 'MESH_GRID',
        'default_w': 0.6, 'default_h': 0.4, 'default_d': 0.15,
        'material': "WBTK_Detail_Metal",
        'color': (0.4, 0.42, 0.45),
    },
    'PIPE_CLUSTER': {
        'label': "Pipe Cluster",
        'icon': 'CURVES_DATA',
        'default_w': 0.3, 'default_h': 2.0, 'default_d': 0.25,
        'material': "WBTK_Detail_Pipe",
        'color': (0.6, 0.35, 0.2),
    },
    'BALCONY': {
        'label': "Balcony",
        'icon': 'MOD_SOLIDIFY',
        'default_w': 2.0, 'default_h': 1.2, 'default_d': 1.0,
        'material': "WBTK_Detail_Metal",
        'color': (0.35, 0.38, 0.4),
    },
    'FIRE_ESCAPE': {
        'label': "Fire Escape",
        'icon': 'IPO_CONSTANT',
        'default_w': 1.5, 'default_h': 3.0, 'default_d': 1.2,
        'material': "WBTK_Detail_Metal",
        'color': (0.3, 0.32, 0.35),
    },
    'SIGN_MOUNT': {
        'label': "Sign Mount",
        'icon': 'FONT_DATA',
        'default_w': 1.5, 'default_h': 0.8, 'default_d': 0.1,
        'material': "WBTK_Detail_Sign",
        'color': (0.9, 0.3, 0.2),
    },
    'ANTENNA': {
        'label': "Antenna",
        'icon': 'OUTLINER_DATA_LIGHT',
        'default_w': 0.1, 'default_h': 1.5, 'default_d': 0.1,
        'material': "WBTK_Detail_Metal",
        'color': (0.55, 0.55, 0.6),
    },
    'CANOPY': {
        'label': "Canopy",
        'icon': 'MOD_TRIANGULATE',
        'default_w': 2.5, 'default_h': 0.1, 'default_d': 1.0,
        'material': "WBTK_Detail_Metal",
        'color': (0.3, 0.35, 0.32),
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  GEOMETRY BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def build_ac_unit(w, h, d):
    bm = bmesh.new()
    # Main box
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= w; v.co.y *= d; v.co.z *= h
        v.co.z += h / 2
    # Fan circle indent on front
    bmesh.ops.create_circle(bm, cap_ends=True, segments=12, radius=min(w, h) * 0.35)
    for v in bm.verts:
        if abs(v.co.z) < 0.01 and abs(v.co.x) < min(w,h)*0.36:
            v.co.y = -d/2 - 0.02
            v.co.z += h * 0.55
    return bm


def build_vent(w, h, d):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= w; v.co.y *= d; v.co.z *= h
        v.co.z += h / 2
    # Slat lines
    n_slats = max(2, int(h / 0.08))
    for i in range(n_slats):
        z = h * 0.1 + (h * 0.8) * i / max(1, n_slats - 1)
        v0 = bm.verts.new((-w/2, -d/2 - 0.01, z))
        v1 = bm.verts.new((w/2, -d/2 - 0.01, z))
        v2 = bm.verts.new((w/2, -d/2 - 0.01, z + 0.02))
        v3 = bm.verts.new((-w/2, -d/2 - 0.01, z + 0.02))
        bm.faces.new((v0, v1, v2, v3))
    return bm


def build_pipe_cluster(w, h, d):
    bm = bmesh.new()
    # 2-3 vertical pipes
    radii = [w * 0.4, w * 0.3, w * 0.2]
    offsets = [0, w * 0.5, -w * 0.3]
    for i, (r, ox) in enumerate(zip(radii[:3], offsets[:3])):
        pipe = bmesh.ops.create_cone(bm, cap_ends=True, segments=8,
            radius1=r, radius2=r, depth=h)
        for v in pipe['verts']:
            v.co.x += ox
            v.co.z += h / 2
    return bm


def build_balcony(w, h, d):
    bm = bmesh.new()
    # Floor plate
    v = [bm.verts.new(p) for p in [
        (-w/2, 0, 0), (w/2, 0, 0), (w/2, -d, 0), (-w/2, -d, 0),
        (-w/2, 0, 0.08), (w/2, 0, 0.08), (w/2, -d, 0.08), (-w/2, -d, 0.08),
    ]]
    for face in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]:
        bm.faces.new([v[i] for i in face])
    # Railing posts
    rail_h = h - 0.08
    post_r = 0.03
    for px in (-w/2 + 0.05, w/2 - 0.05):
        for py in (0, -d + 0.05):
            post = bmesh.ops.create_cube(bm, size=1.0)
            for pv in post['verts']:
                pv.co.x = pv.co.x * post_r + px
                pv.co.y = pv.co.y * post_r + py
                pv.co.z = pv.co.z * rail_h / 2 + 0.08 + rail_h / 2
    # Top rail
    rail = bmesh.ops.create_cube(bm, size=1.0)
    for rv in rail['verts']:
        rv.co.x *= w; rv.co.z *= 0.04
        rv.co.y = rv.co.y * d + (-d/2)
        rv.co.z += 0.08 + rail_h
    return bm


def build_fire_escape(w, h, d):
    bm = bmesh.new()
    # Platform
    v = [bm.verts.new(p) for p in [
        (-w/2, 0, 0), (w/2, 0, 0), (w/2, -d, 0), (-w/2, -d, 0),
        (-w/2, 0, 0.06), (w/2, 0, 0.06), (w/2, -d, 0.06), (-w/2, -d, 0.06),
    ]]
    for face in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]:
        bm.faces.new([v[i] for i in face])
    # Ladder
    rung_w = w * 0.3
    n_rungs = max(3, int(h / 0.4))
    for i in range(n_rungs):
        z = 0.06 + (h - 0.06) * i / max(1, n_rungs - 1)
        rung = bmesh.ops.create_cube(bm, size=1.0)
        for rv in rung['verts']:
            rv.co.x *= rung_w; rv.co.y *= 0.03; rv.co.z *= 0.03
            rv.co.x += w/2 - rung_w/2
            rv.co.y -= d * 0.3
            rv.co.z += z
    return bm


def build_sign_mount(w, h, d):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= w; v.co.y *= d; v.co.z *= h
        v.co.z += h / 2
    return bm


def build_antenna(w, h, d):
    bm = bmesh.new()
    # Main pole
    pole = bmesh.ops.create_cone(bm, cap_ends=True, segments=6,
        radius1=w*0.5, radius2=w*0.2, depth=h)
    for v in pole['verts']:
        v.co.z += h / 2
    # Cross bar
    bar = bmesh.ops.create_cube(bm, size=1.0)
    for v in bar['verts']:
        v.co.x *= w * 4; v.co.y *= 0.02; v.co.z *= 0.02
        v.co.z += h * 0.7
    return bm


def build_canopy(w, h, d):
    bm = bmesh.new()
    # Angled sheet
    v = [bm.verts.new(p) for p in [
        (-w/2, 0, 0), (w/2, 0, 0),
        (w/2, -d, -d*0.15), (-w/2, -d, -d*0.15),
        (-w/2, 0, h), (w/2, 0, h),
        (w/2, -d, h-d*0.15), (-w/2, -d, h-d*0.15),
    ]]
    for face in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]:
        bm.faces.new([v[i] for i in face])
    return bm


_BUILDERS = {
    'AC_UNIT': build_ac_unit,
    'VENT': build_vent,
    'PIPE_CLUSTER': build_pipe_cluster,
    'BALCONY': build_balcony,
    'FIRE_ESCAPE': build_fire_escape,
    'SIGN_MOUNT': build_sign_mount,
    'ANTENNA': build_antenna,
    'CANOPY': build_canopy,
}


# ─────────────────────────────────────────────────────────────────────────────
#  PLACEMENT
# ─────────────────────────────────────────────────────────────────────────────

def get_detail_collection():
    col = bpy.data.collections.get(DETAIL_COLLECTION)
    if not col:
        col = bpy.data.collections.new(DETAIL_COLLECTION)
        bpy.context.scene.collection.children.link(col)
    return col


def place_detail(block_obj, face, detail_type, offset_x=0.5, offset_z=0.5, scale=1.0):
    """Place a detail stamp on a block face.

    Args:
        block_obj: The build block to attach to
        face: 'north', 'south', 'east', 'west', 'top'
        detail_type: Key from DETAIL_TYPES
        offset_x: 0-1 position along face width
        offset_z: 0-1 position along face height
        scale: Size multiplier
    """
    if detail_type not in DETAIL_TYPES:
        return None

    info = DETAIL_TYPES[detail_type]
    bd = bm_data.get_data(block_obj)
    bx, by, bz = block_obj.location
    bw, bdepth, bh = bd["w"], bd["d"], bd["h"]

    # Size
    dw = info['default_w'] * scale
    dh = info['default_h'] * scale
    dd = info['default_d'] * scale

    # Compute position + rotation based on face
    if face == 'south':
        x = bx + bw * offset_x - dw / 2
        y = by - dd
        z = bz + bh * offset_z - dh / 2
        rot = (0, 0, 0)
    elif face == 'north':
        x = bx + bw * offset_x - dw / 2
        y = by + bdepth
        z = bz + bh * offset_z - dh / 2
        rot = (0, 0, math.radians(180))
    elif face == 'east':
        x = bx + bw
        y = by + bdepth * offset_x - dw / 2
        z = bz + bh * offset_z - dh / 2
        rot = (0, 0, math.radians(-90))
    elif face == 'west':
        x = bx - dd
        y = by + bdepth * offset_x - dw / 2
        z = bz + bh * offset_z - dh / 2
        rot = (0, 0, math.radians(90))
    elif face == 'top':
        x = bx + bw * offset_x - dw / 2
        y = by + bdepth * offset_z - dd / 2
        z = bz + bh
        rot = (0, 0, 0)
    else:
        return None

    # Build geometry
    builder = _BUILDERS.get(detail_type)
    if not builder:
        return None

    detail_bm = builder(dw, dh, dd)
    mesh = bpy.data.meshes.new(f"{DETAIL_PREFIX}{detail_type}_mesh")
    detail_bm.to_mesh(mesh); detail_bm.free()

    col = get_detail_collection()
    obj = bpy.data.objects.new(f"{DETAIL_PREFIX}{detail_type}", mesh)
    obj.location = (x, y, z)
    obj.rotation_euler = rot
    obj.color = (*info['color'], 1.0)

    # Material
    mat = Utils.get_or_create_material(info['material'])
    if mat:
        obj.data.materials.append(mat)

    # Store metadata
    obj[DETAIL_KEY] = json.dumps({
        'type': detail_type,
        'face': face,
        'block': block_obj.name,
        'offset_x': offset_x,
        'offset_z': offset_z,
        'scale': scale,
    })

    # Parent to block. The location above is WORLD space, so cancel the
    # parent's transform or the stamp lands at twice the block's offset.
    obj.parent = block_obj
    obj.matrix_parent_inverse = block_obj.matrix_world.inverted()

    col.objects.link(obj)
    return obj


def clear_details():
    col = bpy.data.collections.get(DETAIL_COLLECTION)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)


def get_all_details():
    col = bpy.data.collections.get(DETAIL_COLLECTION)
    if not col:
        return []
    return [o for o in col.objects if DETAIL_KEY in o]


# ─────────────────────────────────────────────────────────────────────────────
#  OPERATORS
# ─────────────────────────────────────────────────────────────────────────────

class OP_AddDetail(bpy.types.Operator):
    """Add a detail stamp to the selected block"""
    bl_idname = "wbtk.bm_add_detail"
    bl_label = "Add Detail"
    bl_options = {'REGISTER', 'UNDO'}

    detail_type: bpy.props.EnumProperty(
        name="Type",
        items=[(k, v['label'], v['label']) for k, v in DETAIL_TYPES.items()],
        default='AC_UNIT',
    )

    def execute(self, context):
        block = bm_data.get_selected(context)
        if not block:
            self.report({'WARNING'}, "Select a build block first")
            return {'CANCELLED'}

        scene = context.scene
        face = getattr(scene, 'wbtk_bm_detail_face', 'south')
        ox = getattr(scene, 'wbtk_bm_detail_offset_x', 0.5)
        oz = getattr(scene, 'wbtk_bm_detail_offset_z', 0.5)
        scale = getattr(scene, 'wbtk_bm_detail_scale', 1.0)

        obj = place_detail(block, face, self.detail_type, ox, oz, scale)
        if obj:
            self.report({'INFO'}, f"Placed {DETAIL_TYPES[self.detail_type]['label']}")
        else:
            self.report({'WARNING'}, "Failed to place detail")
        return {'FINISHED'}


class OP_ClearDetails(bpy.types.Operator):
    """Remove all detail stamps"""
    bl_idname = "wbtk.bm_clear_details"
    bl_label = "Clear Details"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        clear_details()
        self.report({'INFO'}, "Details cleared")
        return {'FINISHED'}


_classes = (
    OP_AddDetail,
    OP_ClearDetails,
)
