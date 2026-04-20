# World_Building_Toolkit/operators_block_composer.py
# Phase 2 — Block Composer
# Generates an entire city block with buildings placed along the perimeter.
# Uses the existing building shell generator with per-building randomization.

import bpy
import math
import random as _random

from .config import Config
from .utils import Utils


class OP_GenerateCityBlock(bpy.types.Operator):
    bl_idname = "wbtk.generate_city_block"
    bl_label = "Generate City Block"
    bl_description = "Generate a rectangular city block with buildings around the perimeter"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene

        # --- Read block properties ---
        block_w_tiles = getattr(scene, 'wbtk_block_width', 20)
        block_d_tiles = getattr(scene, 'wbtk_block_depth', 20)
        alley_w       = getattr(scene, 'wbtk_block_alley_width', 0.5)
        seed          = getattr(scene, 'wbtk_block_seed', 42)
        min_floors    = getattr(scene, 'wbtk_block_min_floors', 1)
        max_floors    = getattr(scene, 'wbtk_block_max_floors', 5)
        min_bldg_w    = getattr(scene, 'wbtk_block_min_building_width', 2)
        max_bldg_w    = getattr(scene, 'wbtk_block_max_building_width', 5)
        bldg_depth_t  = getattr(scene, 'wbtk_block_building_depth', 3)
        fill_courtyard = getattr(scene, 'wbtk_block_fill_courtyard', False)
        use_shapes    = getattr(scene, 'wbtk_block_use_shapes', False)

        rng = _random.Random(seed)
        tile = Config.DEFAULT_TILE_SIZE
        block_w = block_w_tiles * tile
        block_d = block_d_tiles * tile
        bldg_depth = bldg_depth_t * tile

        # Create block master empty
        block_master = Utils.create_master("CityBlock")

        # Available shapes for random selection (weighted)
        shapes = ['RECT']
        if use_shapes:
            shapes = ['RECT', 'RECT', 'RECT', 'L_SHAPE', 'CORNER_CUT', 'L_SHAPE']

        # --- Place buildings along 4 sides ---
        # Each side: walk along the edge, pack buildings of random width
        # Side data: (start_x, start_y, direction_x, direction_y, available_length, rotation_z)
        sides = [
            # South edge: buildings face south (front at y=0), walk +X
            {'sx': 0, 'sy': 0, 'dx': 1, 'dy': 0, 'length': block_w, 'rot': 0},
            # East edge: buildings face east (front at x=block_w), walk +Y
            {'sx': block_w, 'sy': 0, 'dx': 0, 'dy': 1, 'length': block_d, 'rot': math.pi / 2},
            # North edge: buildings face north, walk -X
            {'sx': block_w, 'sy': block_d, 'dx': -1, 'dy': 0, 'length': block_w, 'rot': math.pi},
            # West edge: buildings face west, walk -Y
            {'sx': 0, 'sy': block_d, 'dx': 0, 'dy': -1, 'length': block_d, 'rot': -math.pi / 2},
        ]

        building_idx = 0

        for side in sides:
            cursor = 0.0
            available = side['length']

            while cursor + min_bldg_w * tile < available:
                # Pick random building width
                remaining_tiles = int((available - cursor) / tile)
                bw_tiles = rng.randint(min_bldg_w, min(max_bldg_w, remaining_tiles))
                bw = bw_tiles * tile

                # Don't create tiny leftover buildings
                leftover = available - cursor - bw
                if leftover > 0 and leftover < min_bldg_w * tile:
                    bw = available - cursor  # Absorb leftover
                    bw_tiles = max(min_bldg_w, round(bw / tile))

                # Random parameters
                b_floors = rng.randint(min_floors, max_floors)
                b_shape = rng.choice(shapes)
                b_seed = seed + building_idx * 7

                # Deselect all
                for obj in context.selected_objects:
                    obj.select_set(False)

                # Store current scene properties we'll override
                orig_shape = scene.wbtk_building_shape
                orig_width = scene.wbtk_building_width
                orig_depth = scene.wbtk_building_depth
                orig_floors = scene.wbtk_building_floors
                orig_use_seed = getattr(scene, 'wbtk_building_use_seed', False)
                orig_seed = getattr(scene, 'wbtk_building_seed', 1)

                # Set overrides on scene (the shell generator reads from scene)
                scene.wbtk_building_shape = b_shape
                scene.wbtk_building_width = bw_tiles
                scene.wbtk_building_depth = bldg_depth_t
                scene.wbtk_building_floors = b_floors
                scene.wbtk_building_use_seed = True
                scene.wbtk_building_seed = b_seed

                # Generate building
                master_name = f"Block_B{building_idx:03d}"
                bpy.ops.wbtk.generate_building_shell(
                    override_name=master_name
                )

                # Restore scene properties
                scene.wbtk_building_shape = orig_shape
                scene.wbtk_building_width = orig_width
                scene.wbtk_building_depth = orig_depth
                scene.wbtk_building_floors = orig_floors
                scene.wbtk_building_use_seed = orig_use_seed
                scene.wbtk_building_seed = orig_seed

                # Position and rotate the building
                master_obj = bpy.data.objects.get(f"{master_name}_master")
                if master_obj:
                    # Calculate world position along the side
                    px = side['sx'] + side['dx'] * (cursor + bw / 2.0)
                    py = side['sy'] + side['dy'] * (cursor + bw / 2.0)

                    # Offset inward by half building depth so buildings sit inside the block
                    # Inward normal: perpendicular to side direction, pointing inward
                    # For south side (dx=1,dy=0): inward is +Y
                    # For east side (dx=0,dy=1): inward is -X
                    # etc.
                    in_x = -side['dy']  # inward X component
                    in_y = side['dx']   # inward Y component
                    # For north and west, we need to flip inward direction
                    if side['rot'] == math.pi:        # North: inward is -Y
                        in_x, in_y = 0, -1
                    elif side['rot'] == -math.pi / 2: # West: inward is +X
                        in_x, in_y = 1, 0
                    elif side['rot'] == 0:             # South: inward is +Y
                        in_x, in_y = 0, 1
                    elif side['rot'] == math.pi / 2:  # East: inward is -X
                        in_x, in_y = -1, 0

                    # Building origin is at its (0,0) corner.
                    # We need to position it so the front face aligns with the block edge.
                    # The building extends from (0,0) to (width, depth) in local space.
                    # After rotation, we want the front face on the block perimeter.

                    # Simple approach: place at edge position, offset by depth inward
                    edge_x = side['sx'] + side['dx'] * cursor
                    edge_y = side['sy'] + side['dy'] * cursor

                    master_obj.location.x = edge_x
                    master_obj.location.y = edge_y
                    master_obj.rotation_euler.z = side['rot']

                    # Parent to block master
                    master_obj.parent = block_master

                cursor += bw + alley_w
                building_idx += 1

        # --- Optional: fill courtyard with a ground plane ---
        if fill_courtyard:
            import bmesh
            from mathutils import Vector
            bm_court = bmesh.new()
            inset = bldg_depth + alley_w
            if block_w > 2 * inset and block_d > 2 * inset:
                v0 = bm_court.verts.new((inset, inset, 0))
                v1 = bm_court.verts.new((block_w - inset, inset, 0))
                v2 = bm_court.verts.new((block_w - inset, block_d - inset, 0))
                v3 = bm_court.verts.new((inset, block_d - inset, 0))
                try:
                    bm_court.faces.new((v0, v1, v2, v3))
                except ValueError:
                    pass
                mesh = bpy.data.meshes.new("BlockCourtyard_Mesh")
                bm_court.to_mesh(mesh)
                bm_court.free()
                court_obj = bpy.data.objects.new("BlockCourtyard", mesh)
                Utils.link_to_collection(court_obj, Config.TARGET_COLLECTION)
                court_obj.parent = block_master
                mat = Utils.get_or_create_material(Config.MATERIAL_FLOOR)
                if mat:
                    court_obj.data.materials.append(mat)
            else:
                bm_court.free()

        self.report({'INFO'}, f"WBTK: City block generated — {building_idx} buildings")
        return {'FINISHED'}


class OP_RandomizeBlockSeed(bpy.types.Operator):
    """Randomize the block seed"""
    bl_idname = "wbtk.randomize_block_seed"
    bl_label = "New Block Variation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.wbtk_block_seed = _random.randint(0, 99999)
        return {'FINISHED'}


_classes_to_register = (
    OP_GenerateCityBlock,
    OP_RandomizeBlockSeed,
)
