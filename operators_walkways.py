# World_Building_Toolkit/operators_walkways.py
# (Walkway, Ladder, Stair, and Export operators based on MRTK_v380)

import bpy
import bmesh
import os # Needed for export operator
from mathutils import Vector

# Import local modules using relative paths
from .config import Config
from .utils import Utils
from .geometry_walkways import GeometryWalkways # Use the renamed geometry class

# --- Base Class for Operators ---
class OP_BaseGenerator(bpy.types.Operator):
    """ Base class for WBTK generation operators with common methods. """
    bl_options = {'REGISTER', 'UNDO'} # Enable undo for generation

    def report_error(self, message):
        self.report({'ERROR'}, f"WBTK Error: {message}")
        return {'CANCELLED'}

    def report_warning(self, message):
        self.report({'WARNING'}, f"WBTK Warning: {message}")
        return {'FINISHED'} # Usually finish after warning

    def report_info(self, message):
        self.report({'INFO'}, f"WBTK Info: {message}")
        return {'FINISHED'}

    def get_styles(self, context):
        """ Convenience method to get current style settings from context. """
        # Assumes properties are named wbtk_walkway_style, wbtk_rail_style
        return context.scene.wbtk_walkway_style, context.scene.wbtk_rail_style

    def create_and_parent(self, bm, name, loc, material_name, master):
        """ Helper: Converts BMesh, links, parents, adds UCX. Returns the new object or None. """
        obj = Utils.bm_to_obj(bm, name, loc, material_name)
        if obj:
            obj.parent = master
            Utils.add_ucx_collider(obj, master) # UCX handled by Utils
        return obj

# --- Walkway Operators ---

class OP_BridgeChunk(OP_BaseGenerator):
    bl_idname = "wbtk.bridge_chunk" # Use wbtk prefix
    bl_label = "Generate Bridge"
    bl_description = "Generate a bridge section with optional railings"

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixed property names
        length_tiles = scene.wbtk_br_len
        width_tiles = scene.wbtk_br_wid
        rail_type = scene.wbtk_br_rail
        walkway_style, rail_style = self.get_styles(context)

        if length_tiles <= 0 or width_tiles <= 0:
            return self.report_warning("Bridge Length and Width must be > 0.")

        master = Utils.create_master("Bridge")
        chunk_id = 0
        full_width_units = width_tiles * Config.WIDTH_UNIT

        for chunk_start_x_tile in range(0, length_tiles, Config.CHUNK_LENGTH):
            tiles_x = min(Config.CHUNK_LENGTH, length_tiles - chunk_start_x_tile)
            chunk_base_x = chunk_start_x_tile * Config.LENGTH_UNIT
            for chunk_start_y_tile in range(0, width_tiles, Config.CHUNK_WIDTH):
                tiles_y = min(Config.CHUNK_WIDTH, width_tiles - chunk_start_y_tile)
                chunk_base_y = chunk_start_y_tile * Config.WIDTH_UNIT
                chunk_loc = Vector((chunk_base_x, chunk_base_y, 0))

                # Walkway (Use GeometryWalkways)
                bm_walk = GeometryWalkways.create_walkway_plane_bmesh(tiles_x, tiles_y, walkway_style, Config.LENGTH_UNIT, Config.WIDTH_UNIT)
                self.create_and_parent(bm_walk, f"Bridge_Walk_{chunk_id:04}", chunk_loc, Config.MATERIAL_WALKWAY, master)

                # Railings
                y_local_left = 0
                y_local_right = tiles_y * Config.WIDTH_UNIT
                is_left_edge = (chunk_start_y_tile == 0)
                is_right_edge = ((chunk_start_y_tile + tiles_y) == width_tiles)

                if rail_type in {Config.RAIL_LEFT, Config.RAIL_BOTH} and is_left_edge:
                    bm_rail_l = GeometryWalkways.create_rails_bmesh(tiles_x, y_local_left, chunk_start_x_tile, rail_style)
                    self.create_and_parent(bm_rail_l, f"Bridge_RailL_{chunk_id:04}", chunk_loc, Config.MATERIAL_RAIL, master)

                if rail_type in {Config.RAIL_RIGHT, Config.RAIL_BOTH} and is_right_edge:
                    bm_rail_r = GeometryWalkways.create_rails_bmesh(tiles_x, y_local_right, chunk_start_x_tile, rail_style)
                    self.create_and_parent(bm_rail_r, f"Bridge_RailR_{chunk_id:04}", chunk_loc, Config.MATERIAL_RAIL, master)

                chunk_id += 1

        # End Posts
        if length_tiles > 0 and rail_type != Config.RAIL_NONE:
            bm_ends = bmesh.new()
            end_x = length_tiles * Config.LENGTH_UNIT
            if rail_type in {Config.RAIL_LEFT, Config.RAIL_BOTH}:
                GeometryWalkways.add_beam(bm_ends, (end_x, 0, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style)
            if rail_type in {Config.RAIL_RIGHT, Config.RAIL_BOTH}:
                GeometryWalkways.add_beam(bm_ends, (end_x, full_width_units, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style)
            if bm_ends.verts:
                 self.create_and_parent(bm_ends, "Bridge_EndPosts", Vector((0,0,0)), Config.MATERIAL_RAIL, master)
            else: bm_ends.free()

        return {'FINISHED'}


class OP_StraightRailing(OP_BaseGenerator):
    bl_idname = "wbtk.straight_railing" # Use wbtk prefix
    bl_label = "Generate Straight"
    bl_description = "Generate a straight walkway section with optional railings"

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixed property names
        length_tiles = scene.wbtk_sr_len
        use_chunks = scene.wbtk_sr_chunk
        rail_type = scene.wbtk_sr_rail
        walkway_style, rail_style = self.get_styles(context)

        if length_tiles <= 0:
            return self.report_warning("Straight Length must be > 0.")

        master = Utils.create_master("Straight")
        chunk_size = Config.CHUNK_LENGTH if use_chunks and length_tiles > Config.CHUNK_LENGTH else length_tiles
        chunk_id = 0

        for chunk_start_tile in range(0, length_tiles, chunk_size):
            tiles = min(chunk_size, length_tiles - chunk_start_tile)
            chunk_loc = Vector((chunk_start_tile * Config.LENGTH_UNIT, 0, 0))

            # Walkway (Use GeometryWalkways, always 1 tile wide)
            bm_walk = GeometryWalkways.create_walkway_plane_bmesh(tiles, 1, walkway_style)
            self.create_and_parent(bm_walk, f"Straight_Walk_{chunk_id:04}", chunk_loc, Config.MATERIAL_WALKWAY, master)

            # Railings
            if rail_type in {Config.RAIL_LEFT, Config.RAIL_BOTH}:
                bm_rail_l = GeometryWalkways.create_rails_bmesh(tiles, 0, chunk_start_tile, rail_style)
                self.create_and_parent(bm_rail_l, f"Straight_RailL_{chunk_id:04}", chunk_loc, Config.MATERIAL_RAIL, master)
            if rail_type in {Config.RAIL_RIGHT, Config.RAIL_BOTH}:
                bm_rail_r = GeometryWalkways.create_rails_bmesh(tiles, Config.WIDTH_UNIT, chunk_start_tile, rail_style)
                self.create_and_parent(bm_rail_r, f"Straight_RailR_{chunk_id:04}", chunk_loc, Config.MATERIAL_RAIL, master)

            chunk_id += 1

        # End Posts
        if length_tiles > 0 and rail_type != Config.RAIL_NONE:
            bm_ends = bmesh.new()
            end_x = length_tiles * Config.LENGTH_UNIT
            if rail_type in {Config.RAIL_LEFT, Config.RAIL_BOTH}:
                GeometryWalkways.add_beam(bm_ends, (end_x, 0, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style)
            if rail_type in {Config.RAIL_RIGHT, Config.RAIL_BOTH}:
                GeometryWalkways.add_beam(bm_ends, (end_x, Config.WIDTH_UNIT, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style)
            if bm_ends.verts:
                 self.create_and_parent(bm_ends, "Straight_EndPosts", Vector((0,0,0)), Config.MATERIAL_RAIL, master)
            else: bm_ends.free()

        return {'FINISHED'}


class OP_CornerRailing(OP_BaseGenerator):
    bl_idname = "wbtk.corner_railing" # Use wbtk prefix
    bl_label = "Generate Corner (L)"
    bl_description = "Generate an L-shaped corner walkway section"

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixed property names
        len1_tiles = scene.wbtk_cr_len1 # X-leg
        len2_tiles = scene.wbtk_cr_len2 # Y-leg
        use_chunks = scene.wbtk_cr_chunk
        rail_type = scene.wbtk_cr_rail
        walkway_style, rail_style = self.get_styles(context)

        if len1_tiles <= 0 or len2_tiles <= 0:
            return self.report_warning("Corner lengths must be > 0.")

        master = Utils.create_master("Corner")
        chunk_size = Config.CHUNK_LENGTH # Use same chunk size for both legs for simplicity
        chunk_id_x = 0; chunk_id_y = 0;
        corner_pos_x = len1_tiles * Config.LENGTH_UNIT

        # --- X-Leg ---
        chunk_size_x = chunk_size if use_chunks and len1_tiles > chunk_size else len1_tiles
        for chunk_start_tile in range(0, len1_tiles, chunk_size_x):
            tiles = min(chunk_size_x, len1_tiles - chunk_start_tile)
            chunk_loc = Vector((chunk_start_tile * Config.LENGTH_UNIT, 0, 0))

            bm_walk_x = GeometryWalkways.create_walkway_plane_bmesh(tiles, 1, walkway_style)
            self.create_and_parent(bm_walk_x, f"Corner_X_Walk_{chunk_id_x:04}", chunk_loc, Config.MATERIAL_WALKWAY, master)

            if rail_type in {Config.RAIL_OUTER, Config.RAIL_BOTH}: # Outer = Y=0
                bm_rail_o = GeometryWalkways.create_rails_bmesh(tiles, 0, chunk_start_tile, rail_style)
                self.create_and_parent(bm_rail_o, f"Corner_X_RailO_{chunk_id_x:04}", chunk_loc, Config.MATERIAL_RAIL, master)
            if rail_type in {Config.RAIL_INNER, Config.RAIL_BOTH}: # Inner = Y=Width
                bm_rail_i = GeometryWalkways.create_rails_bmesh(tiles, Config.WIDTH_UNIT, chunk_start_tile, rail_style)
                self.create_and_parent(bm_rail_i, f"Corner_X_RailI_{chunk_id_x:04}", chunk_loc, Config.MATERIAL_RAIL, master)
            chunk_id_x += 1

        # --- Corner Cap ---
        cap_loc = Vector((corner_pos_x, 0, 0))
        cap_size = Config.WIDTH_UNIT
        bm_cap_walk = GeometryWalkways.create_walkway_cap_bmesh(walkway_style, cap_size, cap_size)
        self.create_and_parent(bm_cap_walk, "Corner_Cap_Walk", cap_loc, Config.MATERIAL_WALKWAY, master)

        # Cap Posts
        bm_cap_posts = bmesh.new()
        p_bl=(0,0,0); p_br=(cap_size,0,0); p_tl=(0,cap_size,0); p_tr=(cap_size,cap_size,0) # Local coords
        needs_bl = rail_type in {Config.RAIL_OUTER, Config.RAIL_BOTH}
        needs_br = rail_type in {Config.RAIL_INNER, Config.RAIL_BOTH}
        needs_tl = rail_type in {Config.RAIL_OUTER, Config.RAIL_BOTH}
        needs_tr = rail_type in {Config.RAIL_INNER, Config.RAIL_BOTH}
        if needs_bl: GeometryWalkways.add_beam(bm_cap_posts, p_bl, Config.RAIL_HEIGHTS[0], 'Z', rail_style)
        if needs_br: GeometryWalkways.add_beam(bm_cap_posts, p_br, Config.RAIL_HEIGHTS[0], 'Z', rail_style)
        if needs_tl: GeometryWalkways.add_beam(bm_cap_posts, p_tl, Config.RAIL_HEIGHTS[0], 'Z', rail_style)
        if needs_tr: GeometryWalkways.add_beam(bm_cap_posts, p_tr, Config.RAIL_HEIGHTS[0], 'Z', rail_style)
        if bm_cap_posts.verts:
             self.create_and_parent(bm_cap_posts, "Corner_Cap_Posts", cap_loc, Config.MATERIAL_RAIL, master)
        else: bm_cap_posts.free()

        # --- Y-Leg ---
        y_leg_start_y = Config.WIDTH_UNIT
        chunk_size_y = chunk_size if use_chunks and len2_tiles > chunk_size else len2_tiles
        for chunk_start_tile in range(0, len2_tiles, chunk_size_y):
            tiles = min(chunk_size_y, len2_tiles - chunk_start_tile)
            chunk_start_y = y_leg_start_y + (chunk_start_tile * Config.WIDTH_UNIT)
            chunk_loc = Vector((corner_pos_x, chunk_start_y, 0)) # World location

            # Walkway (1 tile wide along X, 'tiles' long along Y)
            bm_walk_y = GeometryWalkways.create_walkway_plane_bmesh(1, tiles, walkway_style, Config.WIDTH_UNIT, Config.WIDTH_UNIT, 'Y')
            self.create_and_parent(bm_walk_y, f"Corner_Y_Walk_{chunk_id_y:04}", chunk_loc, Config.MATERIAL_WALKWAY, master)

            # Rails (Outer=X=0 relative to corner_pos_x, Inner=X=Width)
            if rail_type in {Config.RAIL_OUTER, Config.RAIL_BOTH}:
                bm_rail_o = GeometryWalkways.create_rails_bmesh_y_leg(tiles, 0, chunk_start_tile, rail_style)
                self.create_and_parent(bm_rail_o, f"Corner_Y_RailO_{chunk_id_y:04}", chunk_loc, Config.MATERIAL_RAIL, master)
            if rail_type in {Config.RAIL_INNER, Config.RAIL_BOTH}:
                bm_rail_i = GeometryWalkways.create_rails_bmesh_y_leg(tiles, Config.WIDTH_UNIT, chunk_start_tile, rail_style)
                self.create_and_parent(bm_rail_i, f"Corner_Y_RailI_{chunk_id_y:04}", chunk_loc, Config.MATERIAL_RAIL, master)
            chunk_id_y += 1

        # End Posts for Y-Leg
        if len2_tiles > 0 and rail_type != Config.RAIL_NONE:
            bm_y_ends = bmesh.new()
            end_y = y_leg_start_y + len2_tiles * Config.WIDTH_UNIT
            end_x_outer = corner_pos_x
            end_x_inner = corner_pos_x + Config.WIDTH_UNIT
            if rail_type in {Config.RAIL_OUTER, Config.RAIL_BOTH}:
                GeometryWalkways.add_beam(bm_y_ends, (end_x_outer, end_y, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style)
            if rail_type in {Config.RAIL_INNER, Config.RAIL_BOTH}:
                GeometryWalkways.add_beam(bm_y_ends, (end_x_inner, end_y, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style)
            if bm_y_ends.verts:
                 self.create_and_parent(bm_y_ends, "Corner_Y_EndPosts", Vector((0,0,0)), Config.MATERIAL_RAIL, master)
            else: bm_y_ends.free()

        return {'FINISHED'}

# --- T-Junction, X-Junction, Endcap, Ladder, Stairs Operators (Simplified for brevity) ---
# (These would follow the same pattern: read wbtk_ properties, call Utils.create_master,
#  call GeometryWalkways methods, call self.create_and_parent)
class OP_TJunctionRailing(OP_BaseGenerator):
    bl_idname = "wbtk.tjunction_railing"
    bl_label = "Generate Tâ€‘Junction"
    bl_description = "Generate a T-shaped junction walkway section"

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        main_len_tiles = scene.wbtk_tr_len1
        branch_len_tiles = scene.wbtk_tr_len2
        # use_chunks = scene.wbtk_tr_chunk # Chunking still TBD for T-Junction
        rail_type = scene.wbtk_tr_rail
        walkway_style, rail_style = self.get_styles(context)

        if main_len_tiles < 3:
            return self.report_warning("Main Length needs >= 3 tiles for branch.")
        if branch_len_tiles <= 0:
            return self.report_warning("Branch length must be > 0.")

        master = Utils.create_master("TJunction")
        chunk_id = 0 # Placeholder

        branch_point_tile_index = (main_len_tiles - 1) // 2
        branch_point_x_units = branch_point_tile_index * Config.LENGTH_UNIT
        main_loc = Vector((0, 0, 0))

        # --- Main Run (X-axis) ---
        bm_main_walk = GeometryWalkways.create_walkway_plane_bmesh(main_len_tiles, 1, walkway_style)
        self.create_and_parent(bm_main_walk, f"TMain_Walk_{chunk_id:04}", main_loc, Config.MATERIAL_WALKWAY, master)

        has_outer_rail = rail_type in {Config.RAIL_OUTER, Config.RAIL_ALL}
        has_inner_rail_full = rail_type == Config.RAIL_ALL
        has_inner_rail_partial = rail_type == Config.RAIL_OUTER

        if has_outer_rail:
            bm_rail_o = GeometryWalkways.create_rails_bmesh(main_len_tiles, 0, 0, rail_style)
            self.create_and_parent(bm_rail_o, f"TMain_RailO_{chunk_id:04}", main_loc, Config.MATERIAL_RAIL, master)

        bm_rail_i = bmesh.new()
        if has_inner_rail_full:
            bm_rail_i = GeometryWalkways.create_rails_bmesh(main_len_tiles, Config.WIDTH_UNIT, 0, rail_style)
        elif has_inner_rail_partial:
            # Logic from original MRTK operator for partial inner rail:
            for ix in range(main_len_tiles):
                if ix == branch_point_tile_index: continue
                start_x = ix * Config.LENGTH_UNIT
                for zh in Config.RAIL_HEIGHTS: # Horizontal beams for segment
                    GeometryWalkways.add_beam(bm_rail_i, (start_x, Config.WIDTH_UNIT, zh), Config.LENGTH_UNIT, 'X', rail_style=rail_style)
                # Add post at start of segment
                GeometryWalkways.add_beam(bm_rail_i, (start_x, Config.WIDTH_UNIT, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style=rail_style)
            # Add final end post if needed
            if branch_point_tile_index != (main_len_tiles -1):
                GeometryWalkways.add_beam(bm_rail_i, (main_len_tiles * Config.LENGTH_UNIT, Config.WIDTH_UNIT, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style=rail_style)

        if bm_rail_i.verts:
            self.create_and_parent(bm_rail_i, f"TMain_RailI_{chunk_id:04}", main_loc, Config.MATERIAL_RAIL, master)
        else: bm_rail_i.free()

        # --- Junction Plate ---
        plate_loc = Vector((branch_point_x_units, 0, 0))
        plate_size_x = Config.LENGTH_UNIT
        plate_size_y = Config.WIDTH_UNIT
        bm_plate_walk = GeometryWalkways.create_walkway_cap_bmesh(walkway_style, plate_size_x, plate_size_y)
        self.create_and_parent(bm_plate_walk, "TJunc_Plate_Walk", plate_loc, Config.MATERIAL_WALKWAY, master)

        bm_posts = bmesh.new()
        needs_post_00 = has_outer_rail
        needs_post_L0 = has_outer_rail
        needs_post_0W = has_inner_rail_full or has_inner_rail_partial or has_outer_rail # Outer connects to branch
        needs_post_LW = has_inner_rail_full or has_inner_rail_partial or has_outer_rail # Outer connects to branch
        if needs_post_00: GeometryWalkways.add_beam(bm_posts, (0, 0, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style=rail_style)
        if needs_post_L0: GeometryWalkways.add_beam(bm_posts, (plate_size_x, 0, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style=rail_style)
        if needs_post_0W: GeometryWalkways.add_beam(bm_posts, (0, plate_size_y, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style=rail_style)
        if needs_post_LW: GeometryWalkways.add_beam(bm_posts, (plate_size_x, plate_size_y, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style=rail_style)
        if bm_posts.verts:
            self.create_and_parent(bm_posts, "TJunc_Plate_Posts", plate_loc, Config.MATERIAL_RAIL, master)
        else: bm_posts.free()

        # --- Branch Arm (Y-axis) ---
        branch_start_y = Config.WIDTH_UNIT
        branch_loc = Vector((branch_point_x_units, branch_start_y, 0))
        bm_branch_walk = GeometryWalkways.create_walkway_plane_bmesh(1, branch_len_tiles, walkway_style, Config.LENGTH_UNIT, Config.WIDTH_UNIT, 'Y')
        self.create_and_parent(bm_branch_walk, f"TBranch_Walk_{chunk_id:04}", branch_loc, Config.MATERIAL_WALKWAY, master)

        if rail_type in {Config.RAIL_OUTER, Config.RAIL_ALL}:
            # Left Branch Rail (X=0 relative to branch_loc = world X branch_point_x_units)
            bm_branch_l = GeometryWalkways.create_rails_bmesh_y_leg(branch_len_tiles, 0, 0, rail_style)
            self.create_and_parent(bm_branch_l, f"TBranch_RailL_{chunk_id:04}", branch_loc, Config.MATERIAL_RAIL, master)
            # Right Branch Rail (X=Length Unit relative to branch_loc = world X branch_point_x_units + Length Unit)
            bm_branch_r = GeometryWalkways.create_rails_bmesh_y_leg(branch_len_tiles, Config.LENGTH_UNIT, 0, rail_style)
            self.create_and_parent(bm_branch_r, f"TBranch_RailR_{chunk_id:04}", branch_loc, Config.MATERIAL_RAIL, master)

            # End posts for Branch
            bm_b_ends = bmesh.new()
            end_y = branch_start_y + branch_len_tiles * Config.WIDTH_UNIT
            end_x_left = branch_point_x_units
            end_x_right = branch_point_x_units + Config.LENGTH_UNIT
            GeometryWalkways.add_beam(bm_b_ends, (end_x_left, end_y, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style)
            GeometryWalkways.add_beam(bm_b_ends, (end_x_right, end_y, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style)
            if bm_b_ends.verts:
                self.create_and_parent(bm_b_ends, "TBranch_EndPosts", Vector((0,0,0)), Config.MATERIAL_RAIL, master)
            else: bm_b_ends.free()

        return {'FINISHED'}

# === Add these full implementations to operators_walkways.py ===
# Replace the placeholder execute methods for these classes

class OP_XJunctionRailing(OP_BaseGenerator):
    bl_idname = "wbtk.xjunction_railing"
    bl_label = "Generate X-Junction (+)"
    bl_description = "Generate a cross-shaped junction walkway section"

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        arm_size_tiles = scene.wbtk_xj_size # N
        rail_type = scene.wbtk_xj_rail
        walkway_style, rail_style = self.get_styles(context)

        if arm_size_tiles < 1:
            return self.report_warning("Arm Size must be at least 1.")

        master = Utils.create_master("XJunction")
        chunk_id = 0 # Keep for naming

        # --- Dimensions ---
        N = arm_size_tiles
        center_tiles = N # Center plate is NxN tiles
        center_len_x = center_tiles * Config.LENGTH_UNIT
        center_len_y = center_tiles * Config.WIDTH_UNIT
        half_plate_x = center_len_x / 2.0
        half_plate_y = center_len_y / 2.0
        arm_len_tiles = 1 # Arms are always 1 tile long from plate edge
        arm_len_units = arm_len_tiles * Config.LENGTH_UNIT
        arm_wid_tiles = N # Arms are N tiles wide
        arm_wid_units = arm_wid_tiles * Config.WIDTH_UNIT

        # --- Center Plate ---
        plate_loc = Vector((-half_plate_x, -half_plate_y, 0))
        bm_plate_walk = GeometryWalkways.create_walkway_plane_bmesh(center_tiles, center_tiles, walkway_style, Config.LENGTH_UNIT, Config.WIDTH_UNIT)
        self.create_and_parent(bm_plate_walk, f"XJunc_Plate_{N}x{N}_Walk", plate_loc, Config.MATERIAL_WALKWAY, master)

        # --- Generate Arms & Collect Post Locations ---
        post_locations_to_create = set() # Using tuples (x,y,z) rounded
        has_outer = rail_type in {Config.RAIL_OUTER, Config.RAIL_ALL}
        has_inner = rail_type == Config.RAIL_ALL

        # Helper to add posts, avoiding duplicates using the set
        def add_post_location(pos_vec):
            rounded_tuple = tuple(round(c, 4) for c in pos_vec)
            post_locations_to_create.add(rounded_tuple)

        # Arm generation logic (X+ Arm example)
        def generate_x_pos_arm():
            loc = Vector((half_plate_x, -half_plate_y, 0)) # Start at plate edge
            bm_walk = GeometryWalkways.create_walkway_plane_bmesh(arm_len_tiles, arm_wid_tiles, walkway_style, Config.LENGTH_UNIT, Config.WIDTH_UNIT, 'X')
            self.create_and_parent(bm_walk, f"XJunc_ArmXP_Walk_{chunk_id}", loc, Config.MATERIAL_WALKWAY, master)
            if has_outer:
                bm_rail_o = GeometryWalkways.create_rails_bmesh(arm_len_tiles, 0, N, rail_style) # Outer = local Y=0
                self.create_and_parent(bm_rail_o, f"XJunc_ArmXP_RailO_{chunk_id}", loc, Config.MATERIAL_RAIL, master)
                add_post_location(loc + Vector((arm_len_units, 0, 0))) # Far end outer post
            if has_inner:
                bm_rail_i = GeometryWalkways.create_rails_bmesh(arm_len_tiles, arm_wid_units, N, rail_style) # Inner = local Y=Width
                self.create_and_parent(bm_rail_i, f"XJunc_ArmXP_RailI_{chunk_id}", loc, Config.MATERIAL_RAIL, master)
                add_post_location(loc + Vector((arm_len_units, arm_wid_units, 0))) # Far end inner post
                add_post_location(loc + Vector((0, arm_wid_units, 0))) # Near end inner post (corner)

        # Generate all 4 arms (similar logic for X-, Y+, Y-)
        # X+ Arm
        generate_x_pos_arm()
        # X- Arm
        loc_xn = Vector((-half_plate_x - arm_len_units, -half_plate_y, 0))
        bm_walk_xn = GeometryWalkways.create_walkway_plane_bmesh(arm_len_tiles, arm_wid_tiles, walkway_style, Config.LENGTH_UNIT, Config.WIDTH_UNIT, 'X')
        self.create_and_parent(bm_walk_xn, f"XJunc_ArmXN_Walk_{chunk_id}", loc_xn, Config.MATERIAL_WALKWAY, master)
        if has_outer:
            bm_rail_o_xn = GeometryWalkways.create_rails_bmesh(arm_len_tiles, 0, 0, rail_style)
            self.create_and_parent(bm_rail_o_xn, f"XJunc_ArmXN_RailO_{chunk_id}", loc_xn, Config.MATERIAL_RAIL, master)
            add_post_location(loc_xn + Vector((0, 0, 0))) # Far end outer post (at origin of arm)
        if has_inner:
            bm_rail_i_xn = GeometryWalkways.create_rails_bmesh(arm_len_tiles, arm_wid_units, 0, rail_style)
            self.create_and_parent(bm_rail_i_xn, f"XJunc_ArmXN_RailI_{chunk_id}", loc_xn, Config.MATERIAL_RAIL, master)
            add_post_location(loc_xn + Vector((0, arm_wid_units, 0))) # Far end inner post
            add_post_location(loc_xn + Vector((arm_len_units, arm_wid_units, 0))) # Near end inner post (corner)

        # Y+ Arm
        loc_yp = Vector((-half_plate_x, half_plate_y, 0))
        bm_walk_yp = GeometryWalkways.create_walkway_plane_bmesh(arm_wid_tiles, arm_len_tiles, walkway_style, Config.WIDTH_UNIT, Config.LENGTH_UNIT, 'Y')
        self.create_and_parent(bm_walk_yp, f"XJunc_ArmYP_Walk_{chunk_id}", loc_yp, Config.MATERIAL_WALKWAY, master)
        if has_outer:
            bm_rail_o_yp = GeometryWalkways.create_rails_bmesh_y_leg(arm_len_tiles, 0, N, rail_style) # Outer = local X=0
            self.create_and_parent(bm_rail_o_yp, f"XJunc_ArmYP_RailO_{chunk_id}", loc_yp, Config.MATERIAL_RAIL, master)
            add_post_location(loc_yp + Vector((0, arm_len_units, 0))) # Far end outer post
        if has_inner:
            bm_rail_i_yp = GeometryWalkways.create_rails_bmesh_y_leg(arm_len_tiles, arm_wid_units, N, rail_style) # Inner = local X=Width
            self.create_and_parent(bm_rail_i_yp, f"XJunc_ArmYP_RailI_{chunk_id}", loc_yp, Config.MATERIAL_RAIL, master)
            add_post_location(loc_yp + Vector((arm_wid_units, arm_len_units, 0))) # Far end inner post
            add_post_location(loc_yp + Vector((arm_wid_units, 0, 0))) # Near end inner post (corner)

        # Y- Arm
        loc_yn = Vector((-half_plate_x, -half_plate_y - arm_len_units, 0))
        bm_walk_yn = GeometryWalkways.create_walkway_plane_bmesh(arm_wid_tiles, arm_len_tiles, walkway_style, Config.WIDTH_UNIT, Config.LENGTH_UNIT, 'Y')
        self.create_and_parent(bm_walk_yn, f"XJunc_ArmYN_Walk_{chunk_id}", loc_yn, Config.MATERIAL_WALKWAY, master)
        if has_outer:
            bm_rail_o_yn = GeometryWalkways.create_rails_bmesh_y_leg(arm_len_tiles, 0, 0, rail_style)
            self.create_and_parent(bm_rail_o_yn, f"XJunc_ArmYN_RailO_{chunk_id}", loc_yn, Config.MATERIAL_RAIL, master)
            add_post_location(loc_yn + Vector((0, 0, 0))) # Far end outer post
        if has_inner:
            bm_rail_i_yn = GeometryWalkways.create_rails_bmesh_y_leg(arm_len_tiles, arm_wid_units, 0, rail_style)
            self.create_and_parent(bm_rail_i_yn, f"XJunc_ArmYN_RailI_{chunk_id}", loc_yn, Config.MATERIAL_RAIL, master)
            add_post_location(loc_yn + Vector((arm_wid_units, 0, 0))) # Far end inner post
            add_post_location(loc_yn + Vector((arm_wid_units, arm_len_units, 0))) # Near end inner post (corner)

        # Add center plate corner posts if RAIL_ALL
        if has_inner:
            add_post_location(Vector((-half_plate_x, -half_plate_y, 0))) # SW
            add_post_location(Vector(( half_plate_x, -half_plate_y, 0))) # SE
            add_post_location(Vector(( half_plate_x,  half_plate_y, 0))) # NE
            add_post_location(Vector((-half_plate_x,  half_plate_y, 0))) # NW

        # --- Generate Posts ---
        if post_locations_to_create:
            bm_all_posts = bmesh.new()
            for post_loc_tuple in post_locations_to_create:
                GeometryWalkways.add_beam(bm_all_posts, post_loc_tuple, Config.RAIL_HEIGHTS[0], 'Z', rail_style=rail_style)
            self.create_and_parent(bm_all_posts, "XJunc_Posts", Vector((0,0,0)), Config.MATERIAL_RAIL, master)

        return {'FINISHED'}


class OP_StraightEndcap(OP_BaseGenerator):
    bl_idname = "wbtk.straight_endcap"
    bl_label = "Generate Straight Endcap"
    bl_description = "Generate a straight walkway section ending with a cap"

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ straight railing props
        length_tiles = scene.wbtk_sr_len
        rail_type = scene.wbtk_sr_rail
        walkway_style, rail_style = self.get_styles(context)

        if length_tiles <= 0:
            return self.report_warning("Length must be > 0.")

        master = Utils.create_master("StraightEndcap")
        run_loc = Vector((0, 0, 0))

        # --- Straight Run ---
        bm_run_walk = GeometryWalkways.create_walkway_plane_bmesh(length_tiles, 1, walkway_style)
        self.create_and_parent(bm_run_walk, f"Endcap_Run_Walk", run_loc, Config.MATERIAL_WALKWAY, master)
        if rail_type in {Config.RAIL_LEFT, Config.RAIL_BOTH}:
            bm_rail_l = GeometryWalkways.create_rails_bmesh(length_tiles, 0, 0, rail_style)
            self.create_and_parent(bm_rail_l, f"Endcap_Run_RailL", run_loc, Config.MATERIAL_RAIL, master)
        if rail_type in {Config.RAIL_RIGHT, Config.RAIL_BOTH}:
            bm_rail_r = GeometryWalkways.create_rails_bmesh(length_tiles, Config.WIDTH_UNIT, 0, rail_style)
            self.create_and_parent(bm_rail_r, f"Endcap_Run_RailR", run_loc, Config.MATERIAL_RAIL, master)

        # --- End Cap Plate ---
        cap_loc = Vector((length_tiles * Config.LENGTH_UNIT, 0, 0))
        cap_size = Config.WIDTH_UNIT
        bm_cap_walk = GeometryWalkways.create_walkway_cap_bmesh(walkway_style, cap_size, cap_size)
        self.create_and_parent(bm_cap_walk, "Endcap_Cap_Walk", cap_loc, Config.MATERIAL_WALKWAY, master)

        # --- End Cap Railing & Posts ---
        if rail_type != Config.RAIL_NONE:
            bm_cap_rail = bmesh.new()
            # Horizontal cap rail (along Y)
            for zh in Config.RAIL_HEIGHTS:
                GeometryWalkways.add_beam(bm_cap_rail, (0, 0, zh), cap_size, 'Y', rail_style=rail_style)
            # Posts at corners
            if rail_type in {Config.RAIL_LEFT, Config.RAIL_BOTH}:
                GeometryWalkways.add_beam(bm_cap_rail, (0, 0, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style=rail_style)
            if rail_type in {Config.RAIL_RIGHT, Config.RAIL_BOTH}:
                GeometryWalkways.add_beam(bm_cap_rail, (0, cap_size, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style=rail_style)
            self.create_and_parent(bm_cap_rail, "Endcap_Cap_Rail", cap_loc, Config.MATERIAL_RAIL, master)

        return {'FINISHED'}


class OP_Ladder(OP_BaseGenerator):
    bl_idname = "wbtk.ladder"
    bl_label = "Generate Ladder"
    bl_description = "Generate a vertical ladder"

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        height_meters = scene.wbtk_ld_height
        num_rungs = scene.wbtk_ld_steps
        add_side_rails = scene.wbtk_ld_rail
        _, rail_style = self.get_styles(context) # Use global rail style for sides
        rung_radius = Config.LADDER_RUNG_RADIUS # Use specific rung radius

        if height_meters <= 0 or num_rungs <= 0:
            return self.report_warning("Ladder Height and Rungs must be > 0.")

        master = Utils.create_master("Ladder")
        ladder_width = Config.LADDER_WIDTH
        base_loc = Vector((0, 0, 0))
        bm = bmesh.new()

        x_left = -ladder_width / 2.0
        x_right = ladder_width / 2.0

        if add_side_rails: # Side Rails
            GeometryWalkways.add_beam(bm, (x_left, 0, 0), height_meters, 'Z', rail_style=rail_style)
            GeometryWalkways.add_beam(bm, (x_right, 0, 0), height_meters, 'Z', rail_style=rail_style)

        # Rungs
        if num_rungs > 0:
            # Place first rung slightly off ground, last slightly below top
            bottom_offset = Config.RAIL_HEIGHTS[-1] * 0.5 # Approx based on bottom rail height
            top_offset = bottom_offset
            usable_height = height_meters - bottom_offset - top_offset
            if usable_height < 0: usable_height = 0

            if num_rungs == 1 and usable_height >= 0:
                rung_z = bottom_offset + usable_height / 2.0
                GeometryWalkways.add_beam(bm, (x_left, 0, rung_z), ladder_width, 'X', rail_style='ROUND', radius=rung_radius) # Rungs usually round
            elif num_rungs > 1 and usable_height >= 0:
                spacing = usable_height / (num_rungs - 1)
                for i in range(num_rungs):
                    rung_z = bottom_offset + i * spacing
                    GeometryWalkways.add_beam(bm, (x_left, 0, rung_z), ladder_width, 'X', rail_style='ROUND', radius=rung_radius)

        self.create_and_parent(bm, "Ladder_Mesh", base_loc, Config.MATERIAL_LADDER, master)
        return {'FINISHED'}


class OP_StairsRailing(OP_BaseGenerator):
    bl_idname = "wbtk.stairs_railing"
    bl_label = "Generate Stairs (Ramp)"
    bl_description = "Generate ramp-style stairs with optional railings"

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        run_meters = scene.wbtk_st_run
        rise_meters = scene.wbtk_st_rise
        width_tiles = scene.wbtk_st_width
        rail_type = scene.wbtk_st_rail
        num_intermediate = scene.wbtk_st_intermediate_posts
        walkway_style, rail_style = self.get_styles(context)

        if run_meters <= 0 or rise_meters <= 0 or width_tiles <= 0:
            return self.report_warning("Stair Run, Rise, and Width must be > 0.")

        master = Utils.create_master("StairsRamp")
        width_units = width_tiles * Config.WIDTH_UNIT
        pivot = Vector((0, 0, 0))

        # --- Ramp Walkway ---
        bm_walk = bmesh.new()
        v0 = bm_walk.verts.new((0, 0, 0))
        v1 = bm_walk.verts.new((run_meters, 0, rise_meters))
        v2 = bm_walk.verts.new((run_meters, width_units, rise_meters))
        v3 = bm_walk.verts.new((0, width_units, 0))
        try:
            ramp_face = bm_walk.faces.new((v0, v1, v2, v3))
            if ramp_face: # Apply style to the single ramp face
                GeometryWalkways._apply_walkway_style_to_face(bm_walk, ramp_face, walkway_style, run_meters, width_units)
        except ValueError: pass
        self.create_and_parent(bm_walk, "Stairs_Ramp", pivot, Config.MATERIAL_STAIR, master)

        # --- Railings ---
        if rail_type != Config.RAIL_NONE:
            bm_rails = bmesh.new()
            p_bl = (0, 0, 0); p_br = (0, width_units, 0)
            p_tl = (run_meters, 0, rise_meters); p_tr = (run_meters, width_units, rise_meters)
            if rail_type in {Config.RAIL_LEFT, Config.RAIL_BOTH}:
                bm_rail_l = GeometryWalkways.create_angled_rails_bmesh(p_bl, p_tl, rail_style, num_intermediate)
                if bm_rail_l: # Merge bmesh data
                    temp_mesh = bpy.data.meshes.new("temp"); bm_rail_l.to_mesh(temp_mesh); bm_rail_l.free()
                    bm_rails.from_mesh(temp_mesh); bpy.data.meshes.remove(temp_mesh)
            if rail_type in {Config.RAIL_RIGHT, Config.RAIL_BOTH}:
                bm_rail_r = GeometryWalkways.create_angled_rails_bmesh(p_br, p_tr, rail_style, num_intermediate)
                if bm_rail_r: # Merge bmesh data
                    temp_mesh = bpy.data.meshes.new("temp"); bm_rail_r.to_mesh(temp_mesh); bm_rail_r.free()
                    bm_rails.from_mesh(temp_mesh); bpy.data.meshes.remove(temp_mesh)
            if bm_rails.verts:
                self.create_and_parent(bm_rails, "Stairs_Rails", pivot, Config.MATERIAL_RAIL, master)
            else: bm_rails.free()

        return {'FINISHED'}


class OP_DiscreteStairs(OP_BaseGenerator):
    bl_idname = "wbtk.discrete_stairs"
    bl_label = "Generate Discrete Stairs"
    bl_description = "Generate stairs with individual step treads and risers"

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        total_run = scene.wbtk_ds_run
        total_rise = scene.wbtk_ds_rise
        width_tiles = scene.wbtk_ds_width_steps
        step_count = scene.wbtk_ds_step_count
        rail_type = scene.wbtk_ds_rail
        num_intermediate = scene.wbtk_st_discrete_intermediate_posts
        walkway_style, rail_style = self.get_styles(context)
        
        if total_run <= 0 or total_rise <= 0 or width_tiles <= 0 or step_count <= 0:
            return self.report_warning("Stair dimensions/count must be > 0.")

        master = Utils.create_master("DiscreteStairs")
        width_units = width_tiles * Config.WIDTH_UNIT
        pivot = Vector((0, 0, 0))
        tread_depth = total_run / step_count
        riser_height = total_rise / step_count
        
        # --- Generate Steps ---
        bm_steps = bmesh.new()
        current_x = 0.0; current_z = 0.0
        verts_riser_top_prev = None # Track verts for connecting treads

        for i in range(step_count):
            x_riser = current_x
            z_riser_b = current_z
            z_riser_t = current_z + riser_height
            x_tread = current_x + tread_depth
            z_tread = z_riser_t

            # Riser Verts
            vrbl = bm_steps.verts.new((x_riser, 0, z_riser_b))
            vrbr = bm_steps.verts.new((x_riser, width_units, z_riser_b))
            vrtl = bm_steps.verts.new((x_riser, 0, z_riser_t))
            vrtr = bm_steps.verts.new((x_riser, width_units, z_riser_t))
            verts_riser_top_current = [vrtl, vrtr]
            try: bm_steps.faces.new((vrbl, vrbr, vrtr, vrtl)) # Riser face
            except ValueError: pass

            # Tread Verts
            vtfl = bm_steps.verts.new((x_tread, 0, z_tread))
            vtfr = bm_steps.verts.new((x_tread, width_units, z_tread))

            # Tread Face (using current riser top verts and new front verts)
            try:
                tread_face = bm_steps.faces.new((vrtl, vrtr, vtfr, vtfl))
                if tread_face and walkway_style != 'GRATE': # Apply style to tread
                    # Apply face style for caps, or edge style for boundary
                    GeometryWalkways._apply_walkway_style_to_face(bm_steps, tread_face, walkway_style, tread_depth, width_units)
            except ValueError: pass

            # Update position for next step
            current_x = x_tread
            current_z = z_tread

        # Create steps object
        self.create_and_parent(bm_steps, "Stairs_Steps", pivot, Config.MATERIAL_STAIR, master)

        # --- Railings ---
        if rail_type != Config.RAIL_NONE:
            bm_rails = bmesh.new()
            p_bl=(0, 0, 0); p_br=(0, width_units, 0)
            p_tl=(total_run, 0, total_rise); p_tr=(total_run, width_units, total_rise)
            if rail_type in {Config.RAIL_LEFT, Config.RAIL_BOTH}:
                bm_rail_l = GeometryWalkways.create_angled_rails_bmesh(p_bl, p_tl, rail_style, num_intermediate)
                if bm_rail_l: # Merge
                    temp_mesh = bpy.data.meshes.new("temp"); bm_rail_l.to_mesh(temp_mesh); bm_rail_l.free()
                    bm_rails.from_mesh(temp_mesh); bpy.data.meshes.remove(temp_mesh)
            if rail_type in {Config.RAIL_RIGHT, Config.RAIL_BOTH}:
                bm_rail_r = GeometryWalkways.create_angled_rails_bmesh(p_br, p_tr, rail_style, num_intermediate)
                if bm_rail_r: # Merge
                    temp_mesh = bpy.data.meshes.new("temp"); bm_rail_r.to_mesh(temp_mesh); bm_rail_r.free()
                    bm_rails.from_mesh(temp_mesh); bpy.data.meshes.remove(temp_mesh)
            if bm_rails.verts:
                self.create_and_parent(bm_rails, "Stairs_Rails", pivot, Config.MATERIAL_RAIL, master)
            else: bm_rails.free()

        return {'FINISHED'}


class OP_ExportRailing(OP_BaseGenerator): # Renamed, based on
    """ Operator to export selected WBTK master objects and their children to FBX. """
    bl_idname = "wbtk.export_fbx" # Use wbtk prefix
    bl_label = "Export WBTK to FBX"
    bl_description = "Export selected WBTK master objects (and children) to FBX format"
    # bl_options = {'REGISTER', 'UNDO'} # UNDO not typical for export

    filepath: bpy.props.StringProperty(subtype="FILE_PATH", options={'HIDDEN'})
    filter_glob: bpy.props.StringProperty(default='*.fbx', options={'HIDDEN'})

    def invoke(self, context, event):
        """ Opens the file browser. """
        blend_filepath = context.blend_data.filepath
        default_filename = "WBTK_Export.fbx"
        default_path = os.path.join(os.path.dirname(blend_filepath), default_filename) if blend_filepath else f"//{default_filename}"
        self.filepath = default_path
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        """ Performs the FBX export. """
        if not self.filepath: return self.report_error("No filepath specified.")
        if not self.filepath.lower().endswith(".fbx"): self.filepath += ".fbx"

        selected_masters = [o for o in context.selected_objects if o.type == 'EMPTY' and o.name.endswith("_master")]
        if not selected_masters: return self.report_warning("No WBTK Master objects selected.")

        if context.active_object and context.active_object.mode != 'OBJECT':
             try: bpy.ops.object.mode_set(mode='OBJECT')
             except RuntimeError: return self.report_error("Could not switch to Object Mode.")

        original_selection = bpy.context.selected_objects[:]
        original_active = context.view_layer.objects.active
        export_failed = False

        try:
            bpy.ops.object.select_all(action='DESELECT')
            objects_to_export = []
            for master in selected_masters:
                 master.select_set(True)
                 objects_to_export.append(master)
                 # Select descendants recursively
                 children = list(master.children)
                 while children:
                     child = children.pop(0)
                     if child.type in {'MESH', 'EMPTY'}:
                         child.select_set(True)
                         objects_to_export.append(child)
                         children.extend(child.children) # Add grandchildren

            if len(objects_to_export) == len(selected_masters):
                 return self.report_warning("Selected Masters have no exportable children (MESH/EMPTY).")

            export_dir = os.path.dirname(self.filepath)
            if export_dir and not os.path.exists(export_dir): os.makedirs(export_dir)

            bpy.ops.export_scene.fbx(
                filepath=self.filepath,
                use_selection=True,
                object_types={'MESH', 'EMPTY'},
                apply_scale_options='FBX_SCALE_NONE',
                bake_space_transform=True,
                use_mesh_modifiers=True,
                mesh_smooth_type='FACE',
                add_leaf_bones=False,
                bake_anim=False,
                use_metadata=False
            )
        except Exception as e:
            self.report_error(f"FBX Export failed: {e}")
            export_failed = True
        finally: # Restore selection
            bpy.ops.object.select_all(action='DESELECT')
            for obj in original_selection:
                 try: obj.select_set(True)
                 except ReferenceError: pass
            try:
                if original_active and original_active.name in context.view_layer.objects:
                     context.view_layer.objects.active = original_active
            except ReferenceError: pass

        if export_failed: return {'CANCELLED'}
        else: return self.report_info(f"Exported {len(objects_to_export)} objects to {self.filepath}")

# --- List of Operator Classes to Register from THIS file ---
# This list is used by __init__.py
_classes_to_register = (
    OP_BridgeChunk,
    OP_StraightRailing,
    OP_CornerRailing,
    OP_TJunctionRailing,
    OP_XJunctionRailing,
    OP_StraightEndcap,
    OP_Ladder,
    OP_StairsRailing,
    OP_DiscreteStairs,
    OP_ExportRailing,
)