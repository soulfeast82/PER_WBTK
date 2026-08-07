# World_Building_Toolkit/operators_structures.py

import bpy
import bmesh
from mathutils import Vector
import math

# Import local modules
from .config import Config
from .utils import Utils
# Import Base Class from walkways operators
from .operators_walkways import OP_BaseGenerator
# Import building geometry class (we'll define this class in geometry_buildings.py next)
# from .geometry_buildings import GeometryBuildings # Planned import
from .geometry_buildings import GeometryBuildings


class OP_GenerateWall(OP_BaseGenerator):
    bl_idname = "wbtk.generate_wall" # Use wbtk prefix
    bl_label = "Generate Wall"
    bl_description = "Generate a modular wall segment (solid, window, or door)"
    # bl_options = {'REGISTER', 'UNDO'} # Inherited from Base

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixed properties
        length_tiles = getattr(scene, 'wbtk_wall_length', 5)
        wall_height = getattr(scene, 'wbtk_wall_height', Config.DEFAULT_WALL_HEIGHT)
        wall_thickness = getattr(scene, 'wbtk_wall_thickness', Config.WALL_THICKNESS)
        wall_type = getattr(scene, 'wbtk_wall_type', 'SOLID')

        if length_tiles <= 0:
            return self.report_warning("Wall length must be > 0.")

        master = Utils.create_master("WallSegment")
        total_length = length_tiles * Config.DEFAULT_TILE_SIZE # Use Default tile size

        bm = bmesh.new()

        # --- Refactored Geometry Calls (using placeholder GeometryBuildings) ---
        if wall_type == 'SOLID':
            GeometryBuildings.build_wall_segment(bm, 0, total_length, 0, wall_height, wall_thickness)
        elif wall_type == 'WINDOW':
            window_w = Config.WINDOW_WIDTH
            window_h = Config.WINDOW_HEIGHT
            sill_h = Config.WINDOW_SILL_HEIGHT
            center_x = total_length / 2.0
            # Bottom part
            GeometryBuildings.build_wall_segment(bm, 0, total_length, 0, sill_h, wall_thickness)
            # Left side
            GeometryBuildings.build_wall_segment(bm, 0, center_x - (window_w/2), sill_h, wall_height, wall_thickness)
            # Right side
            GeometryBuildings.build_wall_segment(bm, center_x + (window_w/2), total_length, sill_h, wall_height, wall_thickness)
            # Top part
            GeometryBuildings.build_wall_segment(bm, center_x - (window_w/2), center_x + (window_w/2), sill_h + window_h, wall_height, wall_thickness)
        elif wall_type == 'DOOR':
            door_w = Config.DOOR_WIDTH
            door_h = Config.DOOR_HEIGHT
            center_x = total_length / 2.0
            # Left side
            GeometryBuildings.build_wall_segment(bm, 0, center_x - (door_w/2), 0, wall_height, wall_thickness)
            # Right side
            GeometryBuildings.build_wall_segment(bm, center_x + (door_w/2), total_length, 0, wall_height, wall_thickness)
            # Top part
            GeometryBuildings.build_wall_segment(bm, center_x - (door_w/2), center_x + (door_w/2), door_h, wall_height, wall_thickness)
        # --- End Refactored Geometry Calls ---

        # Use the create_and_parent helper from Base/Utils
        self.create_and_parent(bm, f"Wall_{wall_type}", Vector((0,0,0)), Config.MATERIAL_WALL, master)

        return {'FINISHED'}


class OP_GenerateRoom(OP_BaseGenerator):
    bl_idname = "wbtk.generate_room" # Use wbtk prefix
    bl_label = "Generate Room"
    bl_description = "Generate a modular room with walls and floor"
    # bl_options = {'REGISTER', 'UNDO'} # Inherited

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        width_tiles = getattr(scene, 'wbtk_room_width', 5)
        length_tiles = getattr(scene, 'wbtk_room_length', 5)
        # Use default wall height from config if not overridden by a specific room height property
        wall_height = getattr(scene, 'wbtk_wall_height', Config.DEFAULT_WALL_HEIGHT) # Assuming wall_height property applies here too

        if width_tiles <= 0 or length_tiles <= 0:
            return self.report_warning("Room dimensions must be > 0.")

        master = Utils.create_master("Room")
        width = width_tiles * Config.DEFAULT_TILE_SIZE
        length = length_tiles * Config.DEFAULT_TILE_SIZE

        # Create Floor
        bm_floor = bmesh.new()
        v0 = bm_floor.verts.new((0, 0, 0))
        v1 = bm_floor.verts.new((width, 0, 0))
        v2 = bm_floor.verts.new((width, length, 0))
        v3 = bm_floor.verts.new((0, length, 0))
        try: bm_floor.faces.new((v0, v1, v2, v3))
        except ValueError: pass # Ignore if face creation fails
        self.create_and_parent(bm_floor, "Room_Floor", Vector((0,0,0)), Config.MATERIAL_FLOOR, master)

        # Wall Data (Position, Length, Axis)
        wall_data = [
            (Vector((0, 0, 0)), width, 'X'),          # South Wall
            (Vector((width, 0, 0)), length, 'Y'),      # East Wall
            (Vector((0, length, 0)), width, 'X'),      # North Wall (adjust location)
            (Vector((0, 0, 0)), length, 'Y'),          # West Wall (adjust location)
        ]

        wall_thickness = getattr(scene, 'wbtk_wall_thickness', Config.WALL_THICKNESS)

        # --- Refactored Wall Generation ---
        # South Wall (Origin 0,0,0 - Extends along +X)
        bm_s = bmesh.new(); GeometryBuildings.build_room_wall(bm_s, Vector((0,0,0)), width, wall_height, wall_thickness, 'X');
        self.create_and_parent(bm_s, "Room_Wall_S", Vector((0,0,0)), Config.MATERIAL_WALL, master)

        # East Wall (Origin width,0,0 - Extends along +Y)
        bm_e = bmesh.new(); GeometryBuildings.build_room_wall(bm_e, Vector((width,0,0)), length, wall_height, wall_thickness, 'Y');
        self.create_and_parent(bm_e, "Room_Wall_E", Vector((width,0,0)), Config.MATERIAL_WALL, master)

        # North Wall (Origin 0,length,0 - Extends along +X)
        bm_n = bmesh.new(); GeometryBuildings.build_room_wall(bm_n, Vector((0,length,0)), width, wall_height, wall_thickness, 'X');
        self.create_and_parent(bm_n, "Room_Wall_N", Vector((0,length,0)), Config.MATERIAL_WALL, master)

        # West Wall (Origin 0,0,0 - Extends along +Y)
        bm_w = bmesh.new(); GeometryBuildings.build_room_wall(bm_w, Vector((0,0,0)), length, wall_height, wall_thickness, 'Y');
        self.create_and_parent(bm_w, "Room_Wall_W", Vector((0,0,0)), Config.MATERIAL_WALL, master)
        # --- End Refactored Calls ---

        return {'FINISHED'}

class OP_GenerateBuildingShell(OP_BaseGenerator):
    bl_idname = "wbtk.generate_building_shell"
    bl_label = "Generate Building Shell"
    bl_description = "Generate a simple modular building exterior"
    bl_options = {'REGISTER', 'UNDO'}

    # --- Allow override from batch operator ---
    override_floors: bpy.props.IntProperty(default=0)
    override_width:  bpy.props.IntProperty(default=0)
    override_seed:   bpy.props.IntProperty(default=-1)
    override_name:   bpy.props.StringProperty(default="")  # Unique name for batch row

    @staticmethod
    def _finalize_bm(bm, name, origin, material, master, base_gen):
        """Merge doubles, recalc normals, create object, apply smoothing, parent."""
        if not bm.verts:
            bm.free()
            return None
        try:
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.005)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        except Exception as e:
            print(f"Warning: finalize cleanup for {name}: {e}")
        obj = base_gen.create_and_parent(bm, name, origin, material, master)
        if obj:
            try:
                mesh_data = obj.data
                mesh_data.polygons.foreach_set("use_smooth", [True] * len(mesh_data.polygons))
                if hasattr(mesh_data, 'set_sharp_from_angle'):
                    mesh_data.set_sharp_from_angle(math.radians(30.0))
                mesh_data.update()
            except Exception as e:
                print(f"Warning: smoothing failed for {name}: {e}")
        return obj

    def execute(self, context):
        scene = context.scene
        import random as _random

        # --- Read Properties ---
        try:
            width_tiles = self.override_width if self.override_width > 0 else getattr(scene, 'wbtk_building_width', 4)
            depth_tiles = getattr(scene, 'wbtk_building_depth', 4)
            floors      = self.override_floors if self.override_floors > 0 else getattr(scene, 'wbtk_building_floors', 2)
            add_roof    = getattr(scene, 'wbtk_building_add_roof', True)
            floor_height = getattr(scene, 'wbtk_building_floor_height', Config.DEFAULT_WALL_HEIGHT)
            add_slabs   = getattr(scene, 'wbtk_building_add_floor_slabs', True)
            front_type  = getattr(scene, 'wbtk_building_front_wall_type', 'DOOR')
            back_type   = getattr(scene, 'wbtk_building_back_wall_type', 'WINDOW')
            left_type   = getattr(scene, 'wbtk_building_left_wall_type', 'WINDOW')
            right_type  = getattr(scene, 'wbtk_building_right_wall_type', 'WINDOW')
            add_ledge   = getattr(scene, 'wbtk_building_add_ledge', False)
            ledge_every_n = getattr(scene, 'wbtk_building_ledge_every_n_floors', 1)
            ledge_height  = getattr(scene, 'wbtk_building_ledge_height', 0.15)
            ledge_depth   = getattr(scene, 'wbtk_building_ledge_depth', 0.15)
            ledge_offset_z = getattr(scene, 'wbtk_building_ledge_offset_z', 0.0)
            add_corners  = getattr(scene, 'wbtk_building_add_corners', False)
            corner_width = getattr(scene, 'wbtk_building_corner_width', 0.3)
            corner_prot  = getattr(scene, 'wbtk_building_corner_protrusion', 0.15)
            add_bands    = getattr(scene, 'wbtk_building_add_bands', False)
            band_every_n = getattr(scene, 'wbtk_building_band_every_n', 1)
            band_height  = getattr(scene, 'wbtk_building_band_height', 0.1)
            band_prot    = getattr(scene, 'wbtk_building_band_protrusion', 0.08)
            add_sills    = getattr(scene, 'wbtk_building_add_sills', False)
            sill_depth   = getattr(scene, 'wbtk_building_sill_depth', 0.12)
            sill_height  = getattr(scene, 'wbtk_building_sill_height', 0.06)
            add_parapet  = getattr(scene, 'wbtk_building_add_parapet', False)
            parapet_height = getattr(scene, 'wbtk_building_parapet_height', 0.8)
            parapet_thick  = getattr(scene, 'wbtk_building_parapet_thickness', 0.2)
            add_plinth   = getattr(scene, 'wbtk_building_add_plinth', False)
            plinth_height = getattr(scene, 'wbtk_building_plinth_height', 0.6)
            plinth_prot   = getattr(scene, 'wbtk_building_plinth_protrusion', 0.1)
            thickness    = Config.WALL_THICKNESS
            # Seed / randomization
            use_seed     = getattr(scene, 'wbtk_building_use_seed', False)
            seed_val     = self.override_seed if self.override_seed >= 0 else getattr(scene, 'wbtk_building_seed', 1)
            win_chance   = getattr(scene, 'wbtk_building_window_chance', 0.6)
            # Window configuration
            win_count_mode = getattr(scene, 'wbtk_building_window_count', 'AUTO')
            custom_win_w   = getattr(scene, 'wbtk_building_window_width', 1.0)
            custom_win_h   = getattr(scene, 'wbtk_building_window_height', 1.0)
            # Door configuration
            door_style_val = getattr(scene, 'wbtk_building_door_style', 'RECESSED')
            custom_door_w  = getattr(scene, 'wbtk_building_door_width', 1.2)
            custom_door_h  = getattr(scene, 'wbtk_building_door_height', 2.5)
            door_inset_val = getattr(scene, 'wbtk_building_door_inset', 0.2)
            door_splay_val = getattr(scene, 'wbtk_building_door_splay', 30.0)
            # Shape and wing configuration
            building_shape = getattr(scene, 'wbtk_building_shape', 'RECT')
            wing_w_tiles   = getattr(scene, 'wbtk_building_wing_width', 2)
            wing_d_tiles   = getattr(scene, 'wbtk_building_wing_depth', 2)
            wing_wall_type = getattr(scene, 'wbtk_building_wing_wall_type', 'WINDOW')
            corner_cut_size = getattr(scene, 'wbtk_building_corner_cut_size', 3.0)
            corner_cut_pos  = getattr(scene, 'wbtk_building_corner_cut_pos', 'FRONT_LEFT')
            wing_position   = getattr(scene, 'wbtk_building_wing_position', 'BACK_LEFT')
            courtyard_wtype = getattr(scene, 'wbtk_building_courtyard_wall_type', 'SOLID')
        except AttributeError as e:
            return self.report_error(f"Missing scene property: {e}")

        # --- Validation ---
        if width_tiles <= 0 or depth_tiles <= 0 or floors <= 0 or floor_height <= 0:
            return self.report_warning("Building dimensions and floor height must be > 0.")
        if add_ledge and (ledge_height <= 0 or ledge_depth <= 0 or ledge_every_n <= 0):
            add_ledge = False

        # --- Seed RNG ---
        rng = _random.Random(seed_val) if use_seed else None

        # --- Create Master and Base Dimensions ---
        master_name = self.override_name if self.override_name else "BuildingShell"
        master = Utils.create_master(master_name)
        width = width_tiles * Config.DEFAULT_TILE_SIZE
        depth = depth_tiles * Config.DEFAULT_TILE_SIZE
        wing_w = wing_w_tiles * Config.DEFAULT_TILE_SIZE
        wing_d = wing_d_tiles * Config.DEFAULT_TILE_SIZE
        origin = Vector((0, 0, 0))

        from .geometry_footprints import get_wall_segments, get_floor_slab_verts, get_perimeter_edges, get_corner_positions

        # --- Precompute perimeter for enhancements ---
        perimeter_edges = get_perimeter_edges(building_shape, width, depth, wing_w, wing_d,
                                               corner_cut_size, corner_cut_pos, wing_position)
        corner_positions = get_corner_positions(building_shape, width, depth, wing_w, wing_d,
                                                 corner_cut_size, corner_cut_pos, wing_position)

        # --- Edge bevel settings ---
        add_bevel    = getattr(scene, 'wbtk_building_add_bevel', False)
        bevel_width  = getattr(scene, 'wbtk_building_bevel_width', 0.05)
        bevel_segs   = getattr(scene, 'wbtk_building_bevel_segments', 2)

        # --- Separate BMeshes for walls vs enhancements ---
        bm_walls   = bmesh.new()  # Walls + floor slabs + roof
        bm_corners = bmesh.new() if add_corners else None
        bm_bands   = bmesh.new() if add_bands   else None
        bm_sills   = bmesh.new() if add_sills   else None
        bm_ledges  = bmesh.new() if add_ledge   else None
        bm_parapet = bmesh.new() if (add_parapet and add_roof) else None
        bm_plinth  = bmesh.new() if add_plinth  else None

        # --- Floor Loop ---
        for floor_idx in range(floors):
            current_z = floor_idx * floor_height

            if add_slabs:
                if building_shape == 'RECT':
                    GeometryBuildings.add_floor_slab(bm_walls, current_z, width, depth)
                else:
                    slab_verts = get_floor_slab_verts(building_shape, width, depth, wing_w, wing_d,
                                                      corner_cut_size, corner_cut_pos, wing_position)
                    GeometryBuildings.add_polygon_slab(bm_walls, current_z, slab_verts)

            if add_ledge and (floor_idx % ledge_every_n == 0):
                ledge_z = current_z + ledge_offset_z
                GeometryBuildings.add_ledge_from_perimeter(bm_ledges, perimeter_edges, ledge_z, ledge_height, ledge_depth)

            # --- Determine wall types for this floor ---
            if floor_idx == 0:
                af, ab, al, ar = front_type, back_type, left_type, right_type
                aw = wing_wall_type
            elif use_seed and rng:
                def _pick():
                    return 'WINDOW' if rng.random() < win_chance else 'SOLID'
                af, ab, al, ar = _pick(), _pick(), _pick(), _pick()
                aw = _pick()
            else:
                af = front_type if front_type != 'DOOR' else 'SOLID'
                ab = back_type  if back_type  != 'DOOR' else 'SOLID'
                al = left_type  if left_type  != 'DOOR' else 'SOLID'
                ar = right_type if right_type != 'DOOR' else 'SOLID'
                aw = wing_wall_type if wing_wall_type != 'DOOR' else 'WINDOW'

            # --- Enhancements (into separate BMeshes) ---
            if add_corners:
                GeometryBuildings.add_corners_from_perimeter(
                    bm_corners, corner_positions,
                    current_z, current_z + floor_height,
                    corner_width, corner_prot)

            if add_bands and floor_idx > 0 and (floor_idx % band_every_n == 0):
                GeometryBuildings.add_band_from_perimeter(
                    bm_bands, perimeter_edges,
                    current_z, band_height, band_prot)

            if add_sills:
                sill_z = current_z + Config.WINDOW_SILL_HEIGHT
                # Get wall segments for this floor (needed for per-segment sills)
                sill_wall_segs = get_wall_segments(building_shape, width, depth, wing_w, wing_d,
                                                    af, ab, al, ar, aw,
                                                    corner_cut_size, corner_cut_pos, floor_idx,
                                                    wing_position, courtyard_wtype)
                GeometryBuildings.add_sills_from_segments(
                    bm_sills, sill_wall_segs, sill_z, sill_depth, sill_height, floor_idx)

            # --- Walls (into main BMesh) ---
            orig_win_w = Config.WINDOW_WIDTH
            orig_win_h = Config.WINDOW_HEIGHT
            Config.WINDOW_WIDTH = custom_win_w
            Config.WINDOW_HEIGHT = custom_win_h
            orig_door_w = Config.DOOR_WIDTH
            orig_door_h = Config.DOOR_HEIGHT
            Config.DOOR_WIDTH = custom_door_w
            Config.DOOR_HEIGHT = custom_door_h

            try:
                def _calc_win_count(wall_length, mode, win_w):
                    if mode == 'AUTO':
                        min_segment = win_w + 0.8
                        return max(1, int(wall_length / min_segment))
                    else:
                        return int(mode)

                def _build_multi_window_wall(bm_target, bx, by, z, wall_len, wall_h, t, ax, wtype, n_wins):
                    if wtype != 'WINDOW' or n_wins <= 1:
                        GeometryBuildings.build_shell_wall(bm_target, bx, by, z, wall_len, wall_h, t, ax,
                            wall_type=wtype, door_style=door_style_val,
                            door_inset=door_inset_val, door_splay=door_splay_val)
                        return
                    seg_len = wall_len / n_wins
                    for i in range(n_wins):
                        offset = i * seg_len
                        if ax == 'X':
                            GeometryBuildings.build_shell_wall(bm_target, bx + offset, by, z, seg_len, wall_h, t, ax, wall_type='WINDOW')
                        else:
                            GeometryBuildings.build_shell_wall(bm_target, bx, by + offset, z, seg_len, wall_h, t, ax, wall_type='WINDOW')

                # --- Get footprint wall segments ---
                wall_segs = get_wall_segments(building_shape, width, depth, wing_w, wing_d,
                                              af, ab, al, ar, aw,
                                              corner_cut_size, corner_cut_pos, floor_idx,
                                              wing_position, courtyard_wtype)

                for seg in wall_segs:
                    if seg['angled']:
                        # Diagonal wall (corner cut)
                        wtype = seg['wall_type']
                        if floor_idx > 0 and wtype == 'DOOR':
                            wtype = 'SOLID'
                        GeometryBuildings.build_angled_wall(
                            bm_walls, seg['start'], seg['end'],
                            current_z, floor_height, thickness, wtype,
                            door_style=door_style_val, door_inset=door_inset_val,
                            door_splay=door_splay_val)
                    else:
                        wtype = seg['wall_type']
                        # Upper floors: no doors
                        if floor_idx > 0 and wtype == 'DOOR':
                            wtype = 'SOLID'
                        n_wins = _calc_win_count(seg['length'], win_count_mode, custom_win_w) if wtype == 'WINDOW' else 1
                        _build_multi_window_wall(bm_walls, seg['bx'], seg['by'], current_z,
                                                 seg['length'], floor_height, thickness,
                                                 seg['axis'], wtype, n_wins)
            finally:
                # Restore Config
                Config.WINDOW_WIDTH = orig_win_w
                Config.WINDOW_HEIGHT = orig_win_h
                Config.DOOR_WIDTH = orig_door_w
                Config.DOOR_HEIGHT = orig_door_h

        # --- Roof ---
        if add_roof:
            roof_z = floors * floor_height
            if building_shape == 'RECT':
                GeometryBuildings.add_floor_slab(bm_walls, roof_z, width, depth)
            else:
                slab_verts = get_floor_slab_verts(building_shape, width, depth, wing_w, wing_d,
                                                  corner_cut_size, corner_cut_pos, wing_position)
                GeometryBuildings.add_polygon_slab(bm_walls, roof_z, slab_verts)
            if add_parapet:
                GeometryBuildings.add_parapet_from_perimeter(bm_parapet, perimeter_edges, roof_z, parapet_height, parapet_thick)

        if add_plinth:
            GeometryBuildings.add_plinth_from_perimeter(bm_plinth, perimeter_edges, plinth_height, plinth_prot)

        # --- Finalize all BMeshes into separate child objects ---
        wall_obj = self._finalize_bm(bm_walls, "Shell_Walls", origin, Config.MATERIAL_WALL, master, self)

        corner_obj = None
        if bm_corners:
            corner_obj = self._finalize_bm(bm_corners, "Shell_Corners", origin, Config.MATERIAL_COLUMN, master, self)
        if bm_bands:
            self._finalize_bm(bm_bands, "Shell_Bands", origin, Config.MATERIAL_BAND, master, self)
        if bm_sills:
            self._finalize_bm(bm_sills, "Shell_Sills", origin, Config.MATERIAL_SILL, master, self)
        if bm_ledges:
            self._finalize_bm(bm_ledges, "Shell_Ledges", origin, Config.MATERIAL_LEDGE, master, self)
        if bm_parapet:
            self._finalize_bm(bm_parapet, "Shell_Parapet", origin, Config.MATERIAL_PARAPET, master, self)
        if bm_plinth:
            self._finalize_bm(bm_plinth, "Shell_Plinth", origin, Config.MATERIAL_PLINTH, master, self)

        # --- Edge Bevel Pass (non-destructive modifier) ---
        if add_bevel:
            bevel_targets = [wall_obj]
            if corner_obj:
                bevel_targets.append(corner_obj)
            for bev_obj in bevel_targets:
                if bev_obj:
                    mod = bev_obj.modifiers.new(name="WBTK_EdgeBevel", type='BEVEL')
                    mod.width = bevel_width
                    mod.segments = bevel_segs
                    mod.limit_method = 'ANGLE'
                    mod.angle_limit = math.radians(60)  # Only bevel edges sharper than 60°
                    mod.affect = 'EDGES'
                    mod.profile = 0.5
                    mod.miter_outer = 'MITER_ARC'

        # --- Auto Trim Sheet UVs ---
        use_trim = getattr(scene, 'wbtk_use_trim_uvs', False)
        if use_trim:
            from .operators_trim_uv import auto_apply_trim_uvs
            texel_density = getattr(scene, 'wbtk_trim_texel_density', 1.0)
            auto_apply_trim_uvs(master, texel_density)

        return {'FINISHED'}

# --- End of OP_GenerateBuildingShell class ---


# ─────────────────────────────────────────────────────────────────────────────
#  BATCH ROW GENERATOR
#  Generates N buildings in a row with seed-based variation.
# ─────────────────────────────────────────────────────────────────────────────

class OP_GenerateBuildingRow(OP_BaseGenerator):
    bl_idname = "wbtk.generate_building_row"
    bl_label = "Generate Building Row"
    bl_description = "Generate multiple buildings in a row with optional variation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import random as _random
        scene = context.scene

        count     = getattr(scene, 'wbtk_batch_count', 3)
        gap       = getattr(scene, 'wbtk_batch_spacing', 1.0)
        direction = getattr(scene, 'wbtk_batch_direction', 'X')
        vary_f    = getattr(scene, 'wbtk_batch_vary_floors', True)
        vary_w    = getattr(scene, 'wbtk_batch_vary_width', True)
        base_w    = getattr(scene, 'wbtk_building_width', 4)
        base_d    = getattr(scene, 'wbtk_building_depth', 4)
        base_f    = getattr(scene, 'wbtk_building_floors', 2)
        base_seed = getattr(scene, 'wbtk_building_seed', 1)
        use_seed  = getattr(scene, 'wbtk_building_use_seed', False)

        rng = _random.Random(base_seed)

        # Track cursor position along the row
        cursor = 0.0

        for i in range(count):
            # Determine per-building variation
            b_floors = base_f
            b_width  = base_w
            if vary_f:
                b_floors = max(1, base_f + rng.randint(-2, 2))
            if vary_w:
                b_width = max(1, base_w + rng.randint(-1, 1))

            b_seed = base_seed + i if use_seed else -1

            # Calculate building footprint in world units
            if direction == 'X':
                footprint = b_width * Config.DEFAULT_TILE_SIZE
            else:
                footprint = base_d * Config.DEFAULT_TILE_SIZE

            # Deselect all before generating
            for obj in context.selected_objects:
                obj.select_set(False)

            # Call the shell generator with overrides + unique name
            master_name = f"BuildingRow_{i:02d}"
            bpy.ops.wbtk.generate_building_shell(
                override_floors=b_floors,
                override_width=b_width,
                override_seed=b_seed,
                override_name=master_name
            )

            # Move the master empty (and all its children) to row position
            master_obj = bpy.data.objects.get(f"{master_name}_master")
            if master_obj:
                if direction == 'X':
                    master_obj.location.x = cursor
                else:
                    master_obj.location.y = cursor

            cursor += footprint + gap

        self.report({'INFO'}, f"Generated {count} buildings in a row along {direction} axis")
        return {'FINISHED'}


class OP_GenerateSupportTower(OP_BaseGenerator):
    bl_idname = "wbtk.generate_support_tower"
    bl_label = "Generate Support Tower"
    bl_description = "Generate a basic support pillar with optional base and cap"
    # bl_options = {'REGISTER', 'UNDO'} # Inherited
    def execute(self, context):
        scene = context.scene
        # Read tower properties using wbtk_ prefix
        height = getattr(scene, 'wbtk_tower_height', 5.0)
        shape = getattr(scene, 'wbtk_tower_shape', 'SQUARE')
        dimension = getattr(scene, 'wbtk_tower_dimension', 0.5)
        segments = getattr(scene, 'wbtk_tower_segments', 16)
        add_base = getattr(scene, 'wbtk_tower_add_base', False)
        base_height = getattr(scene, 'wbtk_tower_base_height', 0.3)
        base_factor = getattr(scene, 'wbtk_tower_base_size_factor', 1.5)
        add_cap = getattr(scene, 'wbtk_tower_add_cap', False)
        cap_height = getattr(scene, 'wbtk_tower_cap_height', 0.2)
        cap_factor = getattr(scene, 'wbtk_tower_cap_size_factor', 1.2)

        # Validation
        if height <= 0 or dimension <= 0:
            return self.report_warning("Tower Height and Dimension must be positive.")
        if add_base and base_height <= 0: add_base = False # Ignore zero-height base
        if add_cap and cap_height <= 0: add_cap = False # Ignore zero-height cap

        # Calculate heights and positions
        pillar_z_start = 0.0
        pillar_height = height
        base_center_z = 0.0
        cap_center_z = 0.0

        if add_base:
            pillar_z_start = base_height # Pillar starts on top of base
            pillar_height -= base_height # Reduce pillar height
            base_center_z = base_height / 2.0 # Center of base block

        if add_cap:
            pillar_height -= cap_height # Reduce pillar height further
            cap_center_z = pillar_z_start + pillar_height + (cap_height / 2.0) # Center of cap block

        # Ensure pillar height didn't become negative
        pillar_height = max(0.01, pillar_height) # Minimum pillar height

        # Create Master and BMesh
        # Use shape and dimension in name for clarity
        master = Utils.create_master(f"SupportTower_{shape}_{dimension:.2f}m")
        bm = bmesh.new()
        base_pos_pillar = (0, 0, pillar_z_start) # Pillar base relative to origin

        # --- Generate Geometry ---
        # 1. Add Pillar
        GeometryBuildings.add_tower_pillar(bm, base_pos_pillar, pillar_height, shape, dimension, segments)

        # 2. Add Base (Optional)
        if add_base:
            base_center_pos = (0, 0, base_center_z)
            GeometryBuildings.add_tower_base_or_cap(bm, base_center_pos, dimension, shape, base_factor, base_height)

        # 3. Add Cap (Optional)
        if add_cap:
            cap_center_pos = (0, 0, cap_center_z)
            GeometryBuildings.add_tower_base_or_cap(bm, cap_center_pos, dimension, shape, cap_factor, cap_height)

        # --- Create Object ---
        # Use a generic structural material, maybe WALL or FLOOR? Let's use FLOOR for now.
        tower_material = Config.MATERIAL_FLOOR
        origin = Vector((0,0,0)) # Generate at world origin (or cursor location)
        # If generating at cursor: origin = context.scene.cursor.location
        self.create_and_parent(bm, f"SupportTowerMesh", origin, tower_material, master)

        # Select the master empty after creation
        # bpy.ops.object.select_all(action='DESELECT')
        # master.select_set(True)
        # context.view_layer.objects.active = master

        return {'FINISHED'}



class OP_RandomizeBuildingSeed(bpy.types.Operator):
    """Randomize the building seed for a new variation"""
    bl_idname  = "wbtk.randomize_building_seed"
    bl_label   = "New Variation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import random
        context.scene.wbtk_building_seed = random.randint(0, 9999)
        return {'FINISHED'}


# --- List of Operator Classes to Register from THIS file ---
_classes_to_register = (
    OP_GenerateWall,
    OP_GenerateRoom,
    OP_GenerateBuildingShell,
    OP_GenerateBuildingRow,
    OP_GenerateSupportTower,
    OP_RandomizeBuildingSeed
)