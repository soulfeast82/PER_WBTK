# World_Building_Toolkit/bm_generate.py
# Build Mode — Generation layer
# Converts block data into building geometry.

import bmesh
import math
from mathutils import Vector

from .config import Config
from .utils import Utils
from . import bm_data


def build_preview_bm(scene):
    """Build a lightweight BMesh preview from all blocks. Used by live preview."""
    blocks = bm_data.get_all()
    if not blocks:
        return bmesh.new()

    from .geometry_buildings import GeometryBuildings
    add_roof  = getattr(scene, 'wbtk_building_add_roof', True)
    add_slabs = getattr(scene, 'wbtk_building_add_floor_slabs', True)
    thickness = Config.WALL_THICKNESS

    # Mirror generate_full's Config overrides so preview matches the final build.
    saved = (Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT, Config.DOOR_WIDTH, Config.DOOR_HEIGHT)
    Config.WINDOW_WIDTH  = getattr(scene, 'wbtk_building_window_width', 1.0)
    Config.WINDOW_HEIGHT = getattr(scene, 'wbtk_building_window_height', 1.0)
    Config.DOOR_WIDTH    = getattr(scene, 'wbtk_building_door_width', 1.2)
    Config.DOOR_HEIGHT   = getattr(scene, 'wbtk_building_door_height', 2.5)

    try:
        bm = bmesh.new()
        info = bm_data.all_bounds()

        for b in info:
            _build_block_walls(bm, b, info, add_slabs, add_roof, thickness, GeometryBuildings)
    finally:
        Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT, Config.DOOR_WIDTH, Config.DOOR_HEIGHT = saved

    return bm


def generate_full(scene):
    """Full generation with all enhancements. Returns (master_empty, wall_obj)."""
    import bpy
    blocks = bm_data.get_all()
    if not blocks:
        return None, None

    from .geometry_buildings import GeometryBuildings
    from .operators_structures import OP_GenerateBuildingShell

    add_roof  = getattr(scene, 'wbtk_building_add_roof', True)
    add_slabs = getattr(scene, 'wbtk_building_add_floor_slabs', True)
    thickness = Config.WALL_THICKNESS
    add_bevel = getattr(scene, 'wbtk_building_add_bevel', False)
    bevel_w   = getattr(scene, 'wbtk_building_bevel_width', 0.05)
    bevel_s   = getattr(scene, 'wbtk_building_bevel_segments', 2)

    door_style = getattr(scene, 'wbtk_building_door_style', 'RECESSED')
    door_in    = getattr(scene, 'wbtk_building_door_inset', 0.2)
    door_sp    = getattr(scene, 'wbtk_building_door_splay', 30.0)

    # Temp config overrides
    saved = (Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT, Config.DOOR_WIDTH, Config.DOOR_HEIGHT)
    Config.WINDOW_WIDTH = getattr(scene, 'wbtk_building_window_width', 1.0)   # fallbacks mirror properties.py (Scale Bible 2026-08-05)
    Config.WINDOW_HEIGHT = getattr(scene, 'wbtk_building_window_height', 1.0)
    Config.DOOR_WIDTH = getattr(scene, 'wbtk_building_door_width', 1.2)
    Config.DOOR_HEIGHT = getattr(scene, 'wbtk_building_door_height', 2.5)

    try:
        master = Utils.create_master("BuildMode")
        origin = Vector((0, 0, 0))
        bm = bmesh.new()
        info = bm_data.all_bounds()

        for b in info:
            _build_block_walls(bm, b, info, add_slabs, add_roof, thickness,
                               GeometryBuildings, door_style, door_in, door_sp)
    finally:
        Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT, Config.DOOR_WIDTH, Config.DOOR_HEIGHT = saved

    # Finalize
    wall_obj = OP_GenerateBuildingShell._finalize_bm(
        bm, "BM_Building", origin, Config.MATERIAL_WALL, master, _FinalizeShim())

    if add_bevel and wall_obj:
        mod = wall_obj.modifiers.new(name="WBTK_EdgeBevel", type='BEVEL')
        mod.width = bevel_w; mod.segments = bevel_s
        mod.limit_method = 'ANGLE'; mod.angle_limit = math.radians(60)
        mod.affect = 'EDGES'; mod.profile = 0.5; mod.miter_outer = 'MITER_SHARP'   # art law: zero rounded corners

    use_trim = getattr(scene, 'wbtk_use_trim_uvs', False)
    if use_trim:
        from .operators_trim_uv import auto_apply_trim_uvs
        auto_apply_trim_uvs(master, getattr(scene, 'wbtk_trim_texel_density', 1.0))

    return master, wall_obj


# ─────────────────────────────────────────────────────────────────────────────
#  INTERNALS
# ─────────────────────────────────────────────────────────────────────────────

def _build_face_wall(bm, GB, bx, by, bz, length, h, thickness, axis, wtype,
                     door_style, door_in, door_sp):
    """One block face. WINDOW faces auto-fit a ROW of windows — same rhythm
    rule as the parametric shell (AUTO count, min segment = window width
    + 0.8m) — instead of one centered opening."""
    n = 1
    if wtype == 'WINDOW':
        n = max(1, int(length / (Config.WINDOW_WIDTH + 0.8)))
    if n <= 1:
        GB.build_shell_wall(bm, bx, by, bz, length, h, thickness, axis,
            wall_type=wtype, door_style=door_style, door_inset=door_in,
            door_splay=door_sp)
        return
    seg = length / n
    for i in range(n):
        off = i * seg
        if axis == 'X':
            GB.build_shell_wall(bm, bx + off, by, bz, seg, h, thickness, 'X',
                                wall_type='WINDOW')
        else:
            GB.build_shell_wall(bm, bx, by + off, bz, seg, h, thickness, 'Y',
                                wall_type='WINDOW')


def _build_block_walls(bm, b, all_info, add_slabs, add_roof, thickness,
                       GB, door_style='FLAT', door_in=0.2, door_sp=30.0):
    """Add one block's geometry to the BMesh."""
    bx, by, bz = b['x0'], b['y0'], b['z0']
    w, d, h = b['w'], b['d'], b['h']
    walls = b['data'].get("walls", {})
    chamfers = b['data'].get("chamfers", [])
    cs = b['data'].get("chamfer_size", 1.0)

    # Build perimeter (with chamfers)
    corners = [(bx, by), (bx+w, by), (bx+w, by+d), (bx, by+d)]
    corner_names = ["sw", "se", "ne", "nw"]

    if chamfers:
        perimeter = []
        for ci in range(4):
            cx, cy = corners[ci]
            if corner_names[ci] in chamfers:
                px, py = corners[(ci-1)%4]; nx, ny = corners[(ci+1)%4]
                dpx, dpy = px-cx, py-cy; dl_p = math.sqrt(dpx*dpx+dpy*dpy)
                dnx, dny = nx-cx, ny-cy; dl_n = math.sqrt(dnx*dnx+dny*dny)
                if dl_p > 0.01 and dl_n > 0.01:
                    c = min(cs, dl_p*0.49, dl_n*0.49)
                    perimeter.append((cx+dpx/dl_p*c, cy+dpy/dl_p*c))
                    perimeter.append((cx+dnx/dl_n*c, cy+dny/dl_n*c))
                else:
                    perimeter.append((cx, cy))
            else:
                perimeter.append((cx, cy))
    else:
        perimeter = corners

    # Floor slab
    if add_slabs:
        GB.add_polygon_slab(bm, bz, perimeter)

    # Walls from perimeter edges
    n_p = len(perimeter)
    for i in range(n_p):
        sx, sy = perimeter[i]; ex, ey = perimeter[(i+1)%n_p]
        dx = ex-sx; dy = ey-sy; length = math.sqrt(dx*dx+dy*dy)
        if length < 0.001:
            continue

        # Which face does this edge belong to?
        mx = (sx+ex)/2; my = (sy+ey)/2
        cx_b = bx+w/2; cy_b = by+d/2
        rel_x = mx-cx_b; rel_y = my-cy_b
        face = ("north" if rel_y > 0 else "south") if abs(rel_y) > abs(rel_x) else ("east" if rel_x > 0 else "west")

        if bm_data.face_is_shared(b, face, all_info):
            continue

        wtype = walls.get(face, "SOLID")

        if abs(dy) < 0.001:
            _build_face_wall(bm, GB, min(sx,ex), sy, bz, abs(dx), h, thickness, 'X',
                             wtype, door_style, door_in, door_sp)
        elif abs(dx) < 0.001:
            _build_face_wall(bm, GB, sx, min(sy,ey), bz, abs(dy), h, thickness, 'Y',
                             wtype, door_style, door_in, door_sp)
        else:
            GB.build_angled_wall(bm, (sx,sy), (ex,ey), bz, h, thickness, wtype,
                door_style=door_style, door_inset=door_in, door_splay=door_sp)

    # Roof slab
    if add_roof and not bm_data.has_block_on_top(b, all_info):
        GB.add_polygon_slab(bm, bz+h, perimeter)


class _FinalizeShim:
    """Compatibility shim for OP_GenerateBuildingShell._finalize_bm."""
    def create_and_parent(self, bm, name, origin, material, master):
        import bpy
        if not bm.verts:
            bm.free(); return None
        mesh = bpy.data.meshes.new(f"{name}_Mesh")
        bm.to_mesh(mesh); bm.free()
        obj = bpy.data.objects.new(name, mesh)
        Utils.link_to_collection(obj, Config.TARGET_COLLECTION)
        obj.location = origin
        mat = Utils.get_or_create_material(material)
        if mat: obj.data.materials.append(mat)
        obj.parent = master
        return obj
