# World_Building_Toolkit/bm_data.py
# Build Mode — Data layer
# Block storage, queries, adjacency detection, mesh rebuild.
# No UI code, no operators.

import bpy
import bmesh
import json
import math
from mathutils import Vector

from .config import Config

COLLECTION_NAME = "WBTK_Build_Blocks"
BLOCK_PREFIX = "WBTK_BM_"
DATA_KEY = "wbtk_bm"
GRID_OBJ = "_WBTK_BM_Grid"
GRID_FILL_OBJ = "_WBTK_BM_GridFill"

DEFAULT_BLOCK = {
    "w": 4.0, "d": 4.0, "h": 3.0,
    "walls": {"north": "SOLID", "south": "SOLID", "east": "SOLID", "west": "SOLID"},
    "chamfers": [],
    "chamfer_size": 1.0,
}


# ─────────────────────────────────────────────────────────────────────────────
#  COLLECTION
# ─────────────────────────────────────────────────────────────────────────────

def get_collection(create=True):
    col = bpy.data.collections.get(COLLECTION_NAME)
    if not col and create:
        col = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(col)
    return col


# ─────────────────────────────────────────────────────────────────────────────
#  BLOCK CRUD
# ─────────────────────────────────────────────────────────────────────────────

def is_block(obj):
    return (obj is not None
            and obj.name.startswith(BLOCK_PREFIX)
            and DATA_KEY in obj)


def get_data(obj):
    try:
        return json.loads(obj[DATA_KEY])
    except Exception:
        return dict(DEFAULT_BLOCK)


def set_data(obj, data):
    obj[DATA_KEY] = json.dumps(data)


def get_all():
    col = get_collection(create=False)
    if not col:
        return []
    return [o for o in col.objects if is_block(o)]


def get_selected(context):
    obj = context.active_object
    return obj if is_block(obj) else None


def create(location, data=None, color=(0.0, 0.7, 1.0)):
    if data is None:
        data = dict(DEFAULT_BLOCK)
    col = get_collection()
    idx = len([o for o in col.objects if is_block(o)])
    name = f"{BLOCK_PREFIX}{idx:04d}"

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    obj.display_type = 'WIRE'
    obj.show_in_front = True
    obj.color = (*color[:3], 0.9)

    mat = _block_material()
    obj.data.materials.append(mat)

    set_data(obj, data)
    col.objects.link(obj)
    rebuild_mesh(obj)
    return obj


def delete(obj):
    if obj and is_block(obj):
        bpy.data.objects.remove(obj, do_unlink=True)


def rebuild_mesh(obj):
    data = get_data(obj)
    w, d, h = data["w"], data["d"], data["h"]

    old_mesh = obj.data
    bm = bmesh.new()
    v = [
        bm.verts.new((0, 0, 0)), bm.verts.new((w, 0, 0)),
        bm.verts.new((w, d, 0)), bm.verts.new((0, d, 0)),
        bm.verts.new((0, 0, h)), bm.verts.new((w, 0, h)),
        bm.verts.new((w, d, h)), bm.verts.new((0, d, h)),
    ]
    bm.faces.new((v[0], v[1], v[2], v[3]))  # bottom
    bm.faces.new((v[4], v[7], v[6], v[5]))  # top
    bm.faces.new((v[0], v[4], v[5], v[1]))  # south
    bm.faces.new((v[2], v[6], v[7], v[3]))  # north
    bm.faces.new((v[1], v[5], v[6], v[2]))  # east
    bm.faces.new((v[0], v[3], v[7], v[4]))  # west

    new_mesh = bpy.data.meshes.new(f"{obj.name}_mesh")
    bm.to_mesh(new_mesh); bm.free()

    if old_mesh and old_mesh.materials:
        for mat in old_mesh.materials:
            new_mesh.materials.append(mat)

    obj.data = new_mesh
    if old_mesh and old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)


def select(context, obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    context.view_layer.objects.active = obj


# ─────────────────────────────────────────────────────────────────────────────
#  PANEL ↔ BLOCK SYNC
# ─────────────────────────────────────────────────────────────────────────────

def sync_to_panel(scene, obj):
    if not obj:
        return
    data = get_data(obj)
    scene['_bm_syncing'] = True
    scene.wbtk_bm_width = data.get("w", 4.0)
    scene.wbtk_bm_depth = data.get("d", 4.0)
    scene.wbtk_bm_height = data.get("h", 3.0)
    walls = data.get("walls", {})
    scene.wbtk_bm_wall_north = walls.get("north", "SOLID")
    scene.wbtk_bm_wall_south = walls.get("south", "SOLID")
    scene.wbtk_bm_wall_east = walls.get("east", "SOLID")
    scene.wbtk_bm_wall_west = walls.get("west", "SOLID")
    scene.wbtk_bm_chamfer_size = data.get("chamfer_size", 1.0)
    del scene['_bm_syncing']


def sync_from_panel(scene, obj):
    if not obj:
        return
    data = get_data(obj)
    data["w"] = getattr(scene, 'wbtk_bm_width', 4.0)
    data["d"] = getattr(scene, 'wbtk_bm_depth', 4.0)
    data["h"] = getattr(scene, 'wbtk_bm_height', 3.0)
    data["walls"] = {
        "north": getattr(scene, 'wbtk_bm_wall_north', 'SOLID'),
        "south": getattr(scene, 'wbtk_bm_wall_south', 'SOLID'),
        "east": getattr(scene, 'wbtk_bm_wall_east', 'SOLID'),
        "west": getattr(scene, 'wbtk_bm_wall_west', 'SOLID'),
    }
    data["chamfer_size"] = getattr(scene, 'wbtk_bm_chamfer_size', 1.0)
    set_data(obj, data)
    rebuild_mesh(obj)


def on_prop_update(self, context):
    if self.get('_bm_syncing'):
        return
    obj = get_selected(context)
    if obj:
        sync_from_panel(self, obj)


# ─────────────────────────────────────────────────────────────────────────────
#  ADJACENCY
# ─────────────────────────────────────────────────────────────────────────────

def block_bounds(obj):
    data = get_data(obj)
    loc = obj.location
    return {
        'obj': obj, 'data': data, 'loc': loc,
        'w': data["w"], 'd': data["d"], 'h': data["h"],
        'x0': loc.x, 'y0': loc.y, 'z0': loc.z,
        'x1': loc.x + data["w"],
        'y1': loc.y + data["d"],
        'z1': loc.z + data["h"],
    }


def all_bounds():
    return [block_bounds(o) for o in get_all()]


def face_is_shared(b, face, all_info):
    for other in all_info:
        if other['obj'] == b['obj']:
            continue
        z_overlap = min(b['z1'], other['z1']) - max(b['z0'], other['z0'])
        if z_overlap < 0.01:
            continue
        if face == "south" and abs(b['y0'] - other['y1']) < 0.01:
            if min(b['x1'], other['x1']) - max(b['x0'], other['x0']) > 0.01:
                return True
        elif face == "north" and abs(b['y1'] - other['y0']) < 0.01:
            if min(b['x1'], other['x1']) - max(b['x0'], other['x0']) > 0.01:
                return True
        elif face == "west" and abs(b['x0'] - other['x1']) < 0.01:
            if min(b['y1'], other['y1']) - max(b['y0'], other['y0']) > 0.01:
                return True
        elif face == "east" and abs(b['x1'] - other['x0']) < 0.01:
            if min(b['y1'], other['y1']) - max(b['y0'], other['y0']) > 0.01:
                return True
    return False


def has_block_on_top(b, all_info):
    for other in all_info:
        if other['obj'] == b['obj']:
            continue
        if abs(other['z0'] - b['z1']) < 0.01:
            if (min(b['x1'], other['x1']) - max(b['x0'], other['x0']) > 0.01 and
                min(b['y1'], other['y1']) - max(b['y0'], other['y0']) > 0.01):
                return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
#  GRID FLOOR
# ─────────────────────────────────────────────────────────────────────────────

def create_grid(scene):
    destroy_grid()
    col = get_collection()
    size = getattr(scene, 'wbtk_bm_grid_size', 20.0)
    subdivs = getattr(scene, 'wbtk_bm_grid_subdivs', 10)
    half = size / 2.0
    step = size / subdivs

    # Fill plane
    bm_f = bmesh.new()
    vs = [bm_f.verts.new(p) for p in [
        (-half,-half,0.005),(half,-half,0.005),(half,half,0.005),(-half,half,0.005)]]
    bm_f.faces.new(vs)
    fm = bpy.data.meshes.new(f"{GRID_FILL_OBJ}_mesh")
    bm_f.to_mesh(fm); bm_f.free()
    fo = bpy.data.objects.new(GRID_FILL_OBJ, fm)
    fo.show_in_front = True
    fmat = bpy.data.materials.new(name="WBTK_BM_GridFill")
    fmat.use_nodes = True
    n = fmat.node_tree.nodes; l = fmat.node_tree.links; n.clear()
    out = n.new('ShaderNodeOutputMaterial')
    em = n.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0.1, 0.12, 0.15, 1.0)
    em.inputs['Strength'].default_value = 0.3
    l.new(em.outputs[0], out.inputs['Surface'])
    fmat.diffuse_color = (0.1, 0.12, 0.15, 0.2)
    fo.data.materials.append(fmat)
    fo.color = (0.1, 0.12, 0.15, 0.2)
    col.objects.link(fo)

    # Grid lines
    gc = (0.3, 0.4, 0.35)
    bm = bmesh.new()
    for i in range(subdivs + 1):
        p = -half + i * step
        bm.edges.new((bm.verts.new((p,-half,0.01)), bm.verts.new((p,half,0.01))))
        bm.edges.new((bm.verts.new((-half,p,0.01)), bm.verts.new((half,p,0.01))))
    for z in (0.02, 0.03):
        b = [bm.verts.new(c) for c in [(-half,-half,z),(half,-half,z),(half,half,z),(-half,half,z)]]
        for i in range(4): bm.edges.new((b[i], b[(i+1)%4]))
    gm = bpy.data.meshes.new(f"{GRID_OBJ}_mesh")
    bm.to_mesh(gm); bm.free()
    go = bpy.data.objects.new(GRID_OBJ, gm)
    go.display_type = 'WIRE'; go.show_in_front = True
    gmat = bpy.data.materials.new(name="WBTK_BM_GridMat")
    gmat.use_nodes = True
    gn = gmat.node_tree.nodes; gl = gmat.node_tree.links; gn.clear()
    gout = gn.new('ShaderNodeOutputMaterial')
    gem = gn.new('ShaderNodeEmission')
    gem.inputs['Color'].default_value = (*gc, 1.0)
    gem.inputs['Strength'].default_value = 2.0
    gl.new(gem.outputs[0], gout.inputs['Surface'])
    gmat.diffuse_color = (*gc, 0.5)
    go.data.materials.append(gmat)
    go.color = (*gc, 0.5)
    col.objects.link(go)


def destroy_grid():
    for name in (GRID_OBJ, GRID_FILL_OBJ):
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)


def clear_all(scene):
    col = bpy.data.collections.get(COLLECTION_NAME)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(col)
    if getattr(scene, 'wbtk_bm_active', False):
        create_grid(scene)


# ─────────────────────────────────────────────────────────────────────────────
#  INTERNAL
# ─────────────────────────────────────────────────────────────────────────────

def _block_material():
    mat = bpy.data.materials.get("WBTK_BuildBlock")
    if not mat:
        mat = bpy.data.materials.new(name="WBTK_BuildBlock")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes; links = mat.node_tree.links
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        emit = nodes.new('ShaderNodeEmission')
        emit.inputs['Color'].default_value = (0.0, 0.7, 1.0, 1.0)
        emit.inputs['Strength'].default_value = 1.5
        links.new(emit.outputs[0], out.inputs['Surface'])
        mat.diffuse_color = (0.0, 0.7, 1.0, 0.8)
    return mat
