# World_Building_Toolkit/operators_preview.py
# Universal Preview & Place system — any generator can register a preview.
#
# HOW IT WORKS:
#  1. Each generator module calls register_preview() with its callbacks
#  2. Panel buttons call wbtk.preview_place with generator_type="BUILDING" etc.
#  3. One modal handles cursor tracking, settings hash, wireframe ghost,
#     live rebuild on slider change, and confirm/cancel — for ALL generators.

import bpy
import bmesh
from mathutils import Vector
import hashlib
import json

from .config import Config


PREVIEW_OBJ_NAME  = "WBTK_Preview_Object"
PREVIEW_MESH_NAME = "WBTK_Preview_Mesh"


# ─────────────────────────────────────────────────────────────────────────────
#  PREVIEW REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

_PREVIEW_REGISTRY = {}


def register_preview(key, build_fn, hash_fn, place_op, label=None):
    """Register a generator's preview callbacks.

    Parameters
    ----------
    key       : str   — unique key like 'BUILDING', 'TREE', 'PIPE', etc.
    build_fn  : callable(scene) -> BMesh  — builds the wireframe preview
    hash_fn   : callable(scene) -> str    — returns hash that changes when sliders move
    place_op  : str   — bl_idname of the generate operator to call on confirm
    label     : str   — human label shown in header bar
    """
    _PREVIEW_REGISTRY[key] = {
        'build_fn': build_fn,
        'hash_fn':  hash_fn,
        'place_op': place_op,
        'label':    label or key.replace('_', ' ').title(),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  SHARED HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _rebuild_preview_object(context, location, generator_type):
    _delete_preview_object()

    entry = _PREVIEW_REGISTRY.get(generator_type)
    if not entry:
        return None

    bm = entry['build_fn'](context.scene)
    if not bm or not bm.verts:
        if bm:
            bm.free()
        return None

    me = bpy.data.meshes.new(PREVIEW_MESH_NAME)
    bm.to_mesh(me)
    bm.free()
    me.update()

    obj = bpy.data.objects.new(PREVIEW_OBJ_NAME, me)
    obj.display_type  = 'WIRE'
    obj.hide_render   = True
    obj.show_in_front = True
    obj.location      = location
    obj.color         = (0.0, 0.85, 1.0, 0.9)

    context.collection.objects.link(obj)
    return obj


def _delete_preview_object():
    obj = bpy.data.objects.get(PREVIEW_OBJ_NAME)
    if obj:
        me = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if me and me.users == 0:
            bpy.data.meshes.remove(me)


def _get_settings_hash(scene, generator_type):
    entry = _PREVIEW_REGISTRY.get(generator_type)
    if not entry:
        return ""
    return entry['hash_fn'](scene)


def _raycast_floor(context, event):
    from bpy_extras import view3d_utils

    region = context.region
    rv3d   = context.region_data
    coord  = (event.mouse_region_x, event.mouse_region_y)

    origin    = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
    direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)

    if not origin or not direction:
        return None

    depsgraph = context.evaluated_depsgraph_get()
    hit, location, _, _, obj, _ = context.scene.ray_cast(depsgraph, origin, direction)

    if hit and obj and obj.name == PREVIEW_OBJ_NAME:
        hit = False

    if hit:
        return location

    if abs(direction.z) > 1e-6:
        t = -origin.z / direction.z
        if t > 0:
            return origin + direction * t

    return None


def _merge_bm(source_bm, target_bm):
    """Merge all geometry from source_bm into target_bm."""
    if not source_bm.verts:
        return
    vert_map = {}
    for v in source_bm.verts:
        nv = target_bm.verts.new(v.co.copy())
        vert_map[v.index] = nv
    target_bm.verts.ensure_lookup_table()
    for f in source_bm.faces:
        try:
            target_bm.faces.new([vert_map[v.index] for v in f.verts])
        except (ValueError, KeyError):
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  UNIVERSAL MODAL OPERATOR
# ─────────────────────────────────────────────────────────────────────────────

class WBTK_OT_PreviewPlace(bpy.types.Operator):
    """Universal Preview & Place — teal wireframe ghost follows cursor,
    rebuilds live on slider changes. Left-Click = place, Esc = cancel."""
    bl_idname  = "wbtk.preview_place"
    bl_label   = "Preview & Place"
    bl_options = {'REGISTER', 'UNDO'}

    generator_type: bpy.props.StringProperty(
        name="Generator Type", default="BUILDING")

    _location      = None
    _settings_hash = ""
    _gen_type      = ""

    def invoke(self, context, event):
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "Must be run from a 3D Viewport.")
            return {'CANCELLED'}

        self._gen_type = self.generator_type

        if self._gen_type not in _PREVIEW_REGISTRY:
            self.report({'WARNING'},
                f"No preview registered for '{self._gen_type}'.")
            return {'CANCELLED'}

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        entry = _PREVIEW_REGISTRY[self._gen_type]
        label = entry['label']

        pos = _raycast_floor(context, event) or Vector((0, 0, 0))
        self._location      = pos
        self._settings_hash = _get_settings_hash(context.scene, self._gen_type)

        _rebuild_preview_object(context, pos, self._gen_type)

        context.area.header_text_set(
            f"WBTK {label} Preview  |  "
            "Move cursor to position  |  "
            "Edit sliders to update live  |  "
            "Left-Click = PLACE  |  Esc / Right-Click = CANCEL"
        )

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            _delete_preview_object()
            context.area.header_text_set(None)
            self.report({'INFO'}, "Placement cancelled.")
            return {'CANCELLED'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            place_pos = Vector(self._location)
            _delete_preview_object()
            context.area.header_text_set(None)
            self._place_at(context, place_pos)
            return {'FINISHED'}

        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            hit = _raycast_floor(context, event)
            if hit:
                self._location = hit
                preview = bpy.data.objects.get(PREVIEW_OBJ_NAME)
                if preview:
                    preview.location = hit

            h = _get_settings_hash(context.scene, self._gen_type)
            if h != self._settings_hash:
                _rebuild_preview_object(context, self._location, self._gen_type)
                self._settings_hash = h

        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    def _place_at(self, context, position):
        entry = _PREVIEW_REGISTRY.get(self._gen_type)
        if not entry:
            return

        bpy.ops.object.select_all(action='DESELECT')
        before = {o.name for o in bpy.data.objects}

        try:
            # Parse "wbtk.generate_tree" → getattr(bpy.ops.wbtk, "generate_tree")
            parts = entry['place_op'].split('.')
            op_module = getattr(bpy.ops, parts[0])
            op_func = getattr(op_module, parts[1])
            op_func()
        except Exception as e:
            self.report({'ERROR'}, f"Generation failed: {e}")
            return

        # Move what the generator CREATED. The generators build at the origin and
        # select nothing (bm_to_obj restores the empty selection), so relying on
        # context.selected_objects moved nothing and every placement landed at
        # (0,0,0). Only top-level new objects are moved: a new child of a new
        # master follows its parent and must not be offset a second time.
        new_objs = [o for o in bpy.data.objects if o.name not in before]
        roots = [o for o in new_objs if o.parent is None or o.parent.name in before]
        if not roots:
            roots = list(context.selected_objects)
        for obj in roots:
            obj.location = obj.location + position

        label = entry['label']
        self.report({'INFO'},
            f"{label} placed at  X:{position.x:.2f}  Y:{position.y:.2f}  Z:{position.z:.2f}")

    def execute(self, context):
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────
#  BACKWARD COMPAT — keep old bl_idname working
# ─────────────────────────────────────────────────────────────────────────────

class WBTK_OT_PreviewPlaceBuilding(bpy.types.Operator):
    """Preview & Place Building (legacy — calls universal preview)"""
    bl_idname  = "wbtk.preview_place_building"
    bl_label   = "Preview & Place Building"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        bpy.ops.wbtk.preview_place('INVOKE_DEFAULT', generator_type='BUILDING')
        return {'FINISHED'}

    def execute(self, context):
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────
#  BUILDING PREVIEW CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────

def _building_hash(scene):
    props = {
        'w':   getattr(scene, 'wbtk_building_width', 4),
        'd':   getattr(scene, 'wbtk_building_depth', 4),
        'f':   getattr(scene, 'wbtk_building_floors', 2),
        'fh':  round(getattr(scene, 'wbtk_building_floor_height', Config.DEFAULT_WALL_HEIGHT), 3),
        'r':   getattr(scene, 'wbtk_building_add_roof', True),
        'ft':  getattr(scene, 'wbtk_building_front_wall_type', 'SOLID'),
        'bt':  getattr(scene, 'wbtk_building_back_wall_type', 'SOLID'),
        'lt':  getattr(scene, 'wbtk_building_left_wall_type', 'SOLID'),
        'rt':  getattr(scene, 'wbtk_building_right_wall_type', 'SOLID'),
        'ac':  getattr(scene, 'wbtk_building_add_corners', False),
        'cw':  round(getattr(scene, 'wbtk_building_corner_width', 0.3), 3),
        'cp':  round(getattr(scene, 'wbtk_building_corner_protrusion', 0.15), 3),
        'ab':  getattr(scene, 'wbtk_building_add_bands', False),
        'bn':  getattr(scene, 'wbtk_building_band_every_n', 1),
        'bh':  round(getattr(scene, 'wbtk_building_band_height', 0.1), 3),
        'bp':  round(getattr(scene, 'wbtk_building_band_protrusion', 0.08), 3),
        'ap':  getattr(scene, 'wbtk_building_add_parapet', False),
        'ph':  round(getattr(scene, 'wbtk_building_parapet_height', 0.8), 3),
        'pt':  round(getattr(scene, 'wbtk_building_parapet_thickness', 0.2), 3),
        'apl': getattr(scene, 'wbtk_building_add_plinth', False),
        'plh': round(getattr(scene, 'wbtk_building_plinth_height', 0.6), 3),
        'plp': round(getattr(scene, 'wbtk_building_plinth_protrusion', 0.1), 3),
        'fs':  getattr(scene, 'wbtk_building_add_floor_slabs', True),
        'al':  getattr(scene, 'wbtk_building_add_ledge', False),
        'ln':  getattr(scene, 'wbtk_building_ledge_every_n_floors', 1),
        'lh':  round(getattr(scene, 'wbtk_building_ledge_height', 0.15), 3),
        'ld':  round(getattr(scene, 'wbtk_building_ledge_depth', 0.15), 3),
        'lz':  round(getattr(scene, 'wbtk_building_ledge_offset_z', 0.0), 3),
        'as':  getattr(scene, 'wbtk_building_add_sills', False),
        'sd':  round(getattr(scene, 'wbtk_building_sill_depth', 0.12), 3),
        'sh':  round(getattr(scene, 'wbtk_building_sill_height', 0.06), 3),
        'us':  getattr(scene, 'wbtk_building_use_seed', False),
        'sv':  getattr(scene, 'wbtk_building_seed', 1),
        'wc':  round(getattr(scene, 'wbtk_building_window_chance', 0.6), 2),
        'bv':  getattr(scene, 'wbtk_building_add_bevel', False),
        'bvw': round(getattr(scene, 'wbtk_building_bevel_width', 0.05), 3),
        'bvs': getattr(scene, 'wbtk_building_bevel_segments', 2),
        'ds':  getattr(scene, 'wbtk_building_door_style', 'RECESSED'),
        'dw':  round(getattr(scene, 'wbtk_building_door_width', 1.0), 3),
        'dh':  round(getattr(scene, 'wbtk_building_door_height', 2.0), 3),
        'di':  round(getattr(scene, 'wbtk_building_door_inset', 0.2), 3),
        'dsp': round(getattr(scene, 'wbtk_building_door_splay', 30.0), 2),
        'shp': getattr(scene, 'wbtk_building_shape', 'RECT'),
        'wgw': getattr(scene, 'wbtk_building_wing_width', 2),
        'wgd': getattr(scene, 'wbtk_building_wing_depth', 2),
        'wgt': getattr(scene, 'wbtk_building_wing_wall_type', 'WINDOW'),
        'ccs': round(getattr(scene, 'wbtk_building_corner_cut_size', 3.0), 2),
        'ccp': getattr(scene, 'wbtk_building_corner_cut_pos', 'FRONT_LEFT'),
        'wgp': getattr(scene, 'wbtk_building_wing_position', 'BACK_LEFT'),
        'cwt': getattr(scene, 'wbtk_building_courtyard_wall_type', 'SOLID'),
    }
    return hashlib.md5(json.dumps(props, sort_keys=True).encode()).hexdigest()[:8]


def _building_preview_bm(scene):
    from .geometry_buildings import GeometryBuildings
    from .geometry_footprints import get_wall_segments, get_floor_slab_verts, get_perimeter_edges, get_corner_positions
    import random as _random

    w_t  = getattr(scene, 'wbtk_building_width', 4)
    d_t  = getattr(scene, 'wbtk_building_depth', 4)
    fl   = getattr(scene, 'wbtk_building_floors', 2)
    fh   = getattr(scene, 'wbtk_building_floor_height', Config.DEFAULT_WALL_HEIGHT)
    roof = getattr(scene, 'wbtk_building_add_roof', True)
    ft   = getattr(scene, 'wbtk_building_front_wall_type', 'SOLID')
    bt   = getattr(scene, 'wbtk_building_back_wall_type', 'SOLID')
    lt   = getattr(scene, 'wbtk_building_left_wall_type', 'SOLID')
    rt   = getattr(scene, 'wbtk_building_right_wall_type', 'SOLID')

    ac  = getattr(scene, 'wbtk_building_add_corners', False)
    cw  = getattr(scene, 'wbtk_building_corner_width', 0.3)
    cp  = getattr(scene, 'wbtk_building_corner_protrusion', 0.15)
    ab_flag = getattr(scene, 'wbtk_building_add_bands', False)
    bn  = getattr(scene, 'wbtk_building_band_every_n', 1)
    bh  = getattr(scene, 'wbtk_building_band_height', 0.1)
    bp  = getattr(scene, 'wbtk_building_band_protrusion', 0.08)
    ap  = getattr(scene, 'wbtk_building_add_parapet', False)
    ph  = getattr(scene, 'wbtk_building_parapet_height', 0.8)
    pt  = getattr(scene, 'wbtk_building_parapet_thickness', 0.2)
    apl = getattr(scene, 'wbtk_building_add_plinth', False)
    plh = getattr(scene, 'wbtk_building_plinth_height', 0.6)
    plp = getattr(scene, 'wbtk_building_plinth_protrusion', 0.1)

    add_slabs = getattr(scene, 'wbtk_building_add_floor_slabs', True)
    add_ledge = getattr(scene, 'wbtk_building_add_ledge', False)
    ledge_n   = getattr(scene, 'wbtk_building_ledge_every_n_floors', 1)
    ledge_h   = getattr(scene, 'wbtk_building_ledge_height', 0.15)
    ledge_d   = getattr(scene, 'wbtk_building_ledge_depth', 0.15)
    ledge_z   = getattr(scene, 'wbtk_building_ledge_offset_z', 0.0)
    add_sills = getattr(scene, 'wbtk_building_add_sills', False)
    sill_d    = getattr(scene, 'wbtk_building_sill_depth', 0.12)
    sill_h    = getattr(scene, 'wbtk_building_sill_height', 0.06)
    use_seed  = getattr(scene, 'wbtk_building_use_seed', False)
    seed_val  = getattr(scene, 'wbtk_building_seed', 1)
    win_ch    = getattr(scene, 'wbtk_building_window_chance', 0.6)
    d_sty = getattr(scene, 'wbtk_building_door_style', 'RECESSED')
    d_w   = getattr(scene, 'wbtk_building_door_width', 1.0)
    d_h   = getattr(scene, 'wbtk_building_door_height', 2.0)
    d_in  = getattr(scene, 'wbtk_building_door_inset', 0.2)
    d_sp  = getattr(scene, 'wbtk_building_door_splay', 30.0)

    building_shape = getattr(scene, 'wbtk_building_shape', 'RECT')
    wing_w_tiles   = getattr(scene, 'wbtk_building_wing_width', 2)
    wing_d_tiles   = getattr(scene, 'wbtk_building_wing_depth', 2)
    wing_wall_type = getattr(scene, 'wbtk_building_wing_wall_type', 'WINDOW')
    corner_cut_size = getattr(scene, 'wbtk_building_corner_cut_size', 3.0)
    corner_cut_pos  = getattr(scene, 'wbtk_building_corner_cut_pos', 'FRONT_LEFT')
    wing_position   = getattr(scene, 'wbtk_building_wing_position', 'BACK_LEFT')
    courtyard_wtype = getattr(scene, 'wbtk_building_courtyard_wall_type', 'SOLID')

    width = w_t * Config.DEFAULT_TILE_SIZE
    depth = d_t * Config.DEFAULT_TILE_SIZE
    wing_w = wing_w_tiles * Config.DEFAULT_TILE_SIZE
    wing_d = wing_d_tiles * Config.DEFAULT_TILE_SIZE
    t     = Config.WALL_THICKNESS

    if add_ledge and (ledge_h <= 0 or ledge_d <= 0 or ledge_n <= 0):
        add_ledge = False

    # Precompute perimeter
    perimeter_edges = get_perimeter_edges(building_shape, width, depth, wing_w, wing_d,
                                           corner_cut_size, corner_cut_pos, wing_position)
    corner_positions = get_corner_positions(building_shape, width, depth, wing_w, wing_d,
                                             corner_cut_size, corner_cut_pos, wing_position)

    rng = _random.Random(seed_val) if use_seed else None
    bm = bmesh.new()

    # Override door dimensions
    _od_w = Config.DOOR_WIDTH; _od_h = Config.DOOR_HEIGHT
    Config.DOOR_WIDTH = d_w; Config.DOOR_HEIGHT = d_h

    if apl:
        GeometryBuildings.add_plinth_from_perimeter(bm, perimeter_edges, plh, plp)

    for i in range(fl):
        z = i * fh
        if i == 0:
            af, abk, al_t, ar_t = ft, bt, lt, rt
            aw = wing_wall_type
        elif use_seed and rng:
            def _pick():
                return 'WINDOW' if rng.random() < win_ch else 'SOLID'
            af, abk, al_t, ar_t = _pick(), _pick(), _pick(), _pick()
            aw = _pick()
        else:
            af   = ft if ft != 'DOOR' else 'SOLID'
            abk  = bt if bt != 'DOOR' else 'SOLID'
            al_t = lt if lt != 'DOOR' else 'SOLID'
            ar_t = rt if rt != 'DOOR' else 'SOLID'
            aw = wing_wall_type if wing_wall_type != 'DOOR' else 'WINDOW'

        if add_slabs:
            if building_shape == 'RECT':
                GeometryBuildings.add_floor_slab(bm, z, width, depth)
            else:
                slab_verts = get_floor_slab_verts(building_shape, width, depth, wing_w, wing_d,
                                                   corner_cut_size, corner_cut_pos, wing_position)
                GeometryBuildings.add_polygon_slab(bm, z, slab_verts)

        if add_ledge and (i % ledge_n == 0):
            GeometryBuildings.add_ledge_from_perimeter(bm, perimeter_edges, z + ledge_z, ledge_h, ledge_d)

        # Build walls from footprint segments
        wall_segs = get_wall_segments(building_shape, width, depth, wing_w, wing_d,
                                       af, abk, al_t, ar_t, aw,
                                       corner_cut_size, corner_cut_pos, i,
                                       wing_position, courtyard_wtype)
        for seg in wall_segs:
            if seg['angled']:
                wtype = seg['wall_type']
                if i > 0 and wtype == 'DOOR':
                    wtype = 'SOLID'
                GeometryBuildings.build_angled_wall(
                    bm, seg['start'], seg['end'], z, fh, t, wtype,
                    door_style=d_sty, door_inset=d_in, door_splay=d_sp)
            else:
                wtype = seg['wall_type']
                if i > 0 and wtype == 'DOOR':
                    wtype = 'SOLID'
                GeometryBuildings.build_shell_wall(bm, seg['bx'], seg['by'], z, seg['length'], fh, t,
                    seg['axis'], wall_type=wtype, door_style=d_sty, door_inset=d_in, door_splay=d_sp)

        if ac:
            GeometryBuildings.add_corners_from_perimeter(bm, corner_positions, z, z + fh, cw, cp)
        if ab_flag and i > 0 and (i % bn == 0):
            GeometryBuildings.add_band_from_perimeter(bm, perimeter_edges, z, bh, bp)

        if add_sills:
            sz = z + Config.WINDOW_SILL_HEIGHT
            GeometryBuildings.add_sills_from_segments(bm, wall_segs, sz, sill_d, sill_h, i)

    # Restore door config
    Config.DOOR_WIDTH = _od_w; Config.DOOR_HEIGHT = _od_h

    if roof:
        rz = fl * fh
        if building_shape == 'RECT':
            GeometryBuildings.add_floor_slab(bm, rz, width, depth)
        else:
            slab_verts = get_floor_slab_verts(building_shape, width, depth, wing_w, wing_d,
                                               corner_cut_size, corner_cut_pos)
            GeometryBuildings.add_polygon_slab(bm, rz, slab_verts)
        if ap:
            GeometryBuildings.add_parapet_from_perimeter(bm, perimeter_edges, rz, ph, pt)

    try:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.005)
    except Exception:
        pass
    return bm


# ─────────────────────────────────────────────────────────────────────────────
#  FOLIAGE PREVIEW CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────

def _tree_hash(scene):
    props = {
        'h': round(getattr(scene, 'wbtk_tree_height', 5.0), 2),
        'tr': round(getattr(scene, 'wbtk_trunk_radius', 0.15), 3),
        'tt': round(getattr(scene, 'wbtk_trunk_taper', 0.4), 2),
        'bl': getattr(scene, 'wbtk_branch_levels', 3),
        'bc': getattr(scene, 'wbtk_branch_count', 5),
        'ba': round(getattr(scene, 'wbtk_branch_angle', 35.0), 1),
        'bf': round(getattr(scene, 'wbtk_branch_length_factor', 0.6), 2),
        'bt': round(getattr(scene, 'wbtk_branch_taper', 0.5), 2),
        'ld': getattr(scene, 'wbtk_leaf_density', 35),
        'ls': round(getattr(scene, 'wbtk_leaf_size', 0.25), 2),
        'lp': getattr(scene, 'wbtk_leaf_shape', 'ROUND'),
        'dr': round(getattr(scene, 'wbtk_leaf_droop', 0.2), 2),
        'sd': getattr(scene, 'wbtk_foliage_seed', 1),
    }
    return hashlib.md5(json.dumps(props, sort_keys=True).encode()).hexdigest()[:8]


def _tree_preview_bm(scene):
    from .geometry_foliage import GeometryFoliage
    params = {
        'tree_height':          getattr(scene, 'wbtk_tree_height', 5.0),
        'trunk_radius':         getattr(scene, 'wbtk_trunk_radius', 0.15),
        'trunk_taper':          getattr(scene, 'wbtk_trunk_taper', 0.4),
        'branch_levels':        getattr(scene, 'wbtk_branch_levels', 3),
        'branch_count':         getattr(scene, 'wbtk_branch_count', 5),
        'branch_angle':         getattr(scene, 'wbtk_branch_angle', 35.0),
        'branch_length_factor': getattr(scene, 'wbtk_branch_length_factor', 0.6),
        'branch_taper':         getattr(scene, 'wbtk_branch_taper', 0.5),
        'leaf_density':         getattr(scene, 'wbtk_leaf_density', 35),
        'leaf_size':            getattr(scene, 'wbtk_leaf_size', 0.25),
        'leaf_shape':           getattr(scene, 'wbtk_leaf_shape', 'ROUND'),
        'leaf_droop':           getattr(scene, 'wbtk_leaf_droop', 0.2),
        'randomize_seed':       getattr(scene, 'wbtk_foliage_seed', 1),
    }
    bm_trunk, bm_leaves = GeometryFoliage.build_tree(params)
    combined = bmesh.new()
    _merge_bm(bm_trunk, combined)
    _merge_bm(bm_leaves, combined)
    bm_trunk.free()
    bm_leaves.free()
    return combined


def _shrub_hash(scene):
    props = {
        'h': round(getattr(scene, 'wbtk_shrub_height', 1.0), 2),
        'w': round(getattr(scene, 'wbtk_shrub_width', 1.2), 2),
        'bc': getattr(scene, 'wbtk_shrub_branch_count', 10),
        'ba': round(getattr(scene, 'wbtk_shrub_branch_angle', 50.0), 1),
        'ld': getattr(scene, 'wbtk_shrub_leaf_density', 30),
        'ls': round(getattr(scene, 'wbtk_shrub_leaf_size', 0.15), 2),
        'lp': getattr(scene, 'wbtk_shrub_leaf_shape', 'ROUND'),
        'sd': getattr(scene, 'wbtk_foliage_seed', 1),
    }
    return hashlib.md5(json.dumps(props, sort_keys=True).encode()).hexdigest()[:8]


def _shrub_preview_bm(scene):
    from .geometry_foliage import GeometryFoliage
    params = {
        'shrub_height':       getattr(scene, 'wbtk_shrub_height', 1.0),
        'shrub_width':        getattr(scene, 'wbtk_shrub_width', 1.2),
        'shrub_branch_count': getattr(scene, 'wbtk_shrub_branch_count', 10),
        'shrub_branch_angle': getattr(scene, 'wbtk_shrub_branch_angle', 50.0),
        'shrub_leaf_density': getattr(scene, 'wbtk_shrub_leaf_density', 30),
        'shrub_leaf_size':    getattr(scene, 'wbtk_shrub_leaf_size', 0.15),
        'shrub_leaf_shape':   getattr(scene, 'wbtk_shrub_leaf_shape', 'ROUND'),
        'randomize_seed':     getattr(scene, 'wbtk_foliage_seed', 1),
    }
    bm_branches, bm_leaves = GeometryFoliage.build_shrub(params)
    combined = bmesh.new()
    _merge_bm(bm_branches, combined)
    _merge_bm(bm_leaves, combined)
    bm_branches.free()
    bm_leaves.free()
    return combined


# ─────────────────────────────────────────────────────────────────────────────
#  BOOTSTRAP — register built-in previews at import time
# ─────────────────────────────────────────────────────────────────────────────

register_preview('BUILDING', _building_preview_bm, _building_hash,
                 'wbtk.generate_building_shell', 'Building')
register_preview('TREE', _tree_preview_bm, _tree_hash,
                 'wbtk.generate_tree', 'Tree')
register_preview('SHRUB', _shrub_preview_bm, _shrub_hash,
                 'wbtk.generate_shrub', 'Shrub')


# ─── BUILD MODE PREVIEW ─────────────────────────────────────────────────────

def _buildmode_hash(scene):
    from .bm_data import get_all, get_data
    blocks = get_all()
    if not blocks:
        return "empty"
    parts = []
    for obj in blocks:
        d = get_data(obj)
        loc = obj.location
        parts.append(f"{loc.x:.2f},{loc.y:.2f},{loc.z:.2f}|{d['w']:.2f},{d['d']:.2f},{d['h']:.2f}|{d.get('walls',{})}")
    combined = ";".join(sorted(parts))
    combined += f"|r={getattr(scene,'wbtk_building_add_roof',True)}"
    combined += f"|s={getattr(scene,'wbtk_building_add_floor_slabs',True)}"
    combined += f"|sb={getattr(scene,'wbtk_bm_auto_setback',0.0):.2f}"
    return hashlib.md5(combined.encode()).hexdigest()[:8]


def _buildmode_preview_bm(scene):
    from .bm_generate import build_preview_bm
    return build_preview_bm(scene)

    return bm


register_preview('BUILD_MODE', _buildmode_preview_bm, _buildmode_hash,
                 'wbtk.bm_generate', 'Build Mode')


# ─────────────────────────────────────────────────────────────────────────────

_classes_to_register = (
    WBTK_OT_PreviewPlace,
    WBTK_OT_PreviewPlaceBuilding,
)
