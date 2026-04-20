# World_Building_Toolkit/operators_ground.py

import bpy
import bmesh
from mathutils import Vector

# Import local modules
from .config import Config
from .utils import Utils
# Import Base Class
from .operators_walkways import OP_BaseGenerator
# Geometry modules not needed for this simple operator

# === Ground Operator ===

class OP_GenerateGroundPlane(OP_BaseGenerator):
    bl_idname = "wbtk.generate_ground_plane" # Use wbtk prefix
    bl_label = "Generate Ground Plane"
    bl_description = "Generate a modular ground plane composed of tiles"
    # bl_options = {'REGISTER', 'UNDO'} # Inherited

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        tiles_x = scene.wbtk_ground_width
        tiles_y = scene.wbtk_ground_depth
        tile_size = scene.wbtk_ground_tile_size # Use the specific ground tile size property

        if tiles_x <= 0 or tiles_y <= 0 or tile_size <= 0:
            return self.report_warning("Ground dimensions and tile size must be positive.")

        master = Utils.create_master("GroundPlane")
        bm = bmesh.new()

        # Create grid of faces
        for x in range(tiles_x):
            for y in range(tiles_y):
                x0 = x * tile_size
                x1 = (x + 1) * tile_size
                y0 = y * tile_size
                y1 = (y + 1) * tile_size

                # Define vertices for one tile (quad)
                v0 = bm.verts.new((x0, y0, 0))
                v1 = bm.verts.new((x1, y0, 0))
                v2 = bm.verts.new((x1, y1, 0))
                v3 = bm.verts.new((x0, y1, 0))
                # Create the face
                try:
                    bm.faces.new((v0, v1, v2, v3))
                except ValueError:
                    print(f"Warning: Could not create ground tile face at ({x},{y})")
                    pass # Ignore degenerate faces potentially caused by zero size

        # Use create_and_parent helper
        # Use the generic FLOOR material for the ground plane
        self.create_and_parent(bm, "GroundPlane_Mesh", Vector((0,0,0)), Config.MATERIAL_FLOOR, master)

        return {'FINISHED'}


# --- List of Operator Classes to Register from THIS file ---
_classes_to_register = (
    OP_GenerateGroundPlane,
)