# World_Building_Toolkit/geometry_fences.py

import bpy # bmesh.ops might need it implicitly
import bmesh
from mathutils import Vector, Matrix

# Import local modules
from .config import Config
# from .utils import Utils # Likely not needed here

class GeometryFences:
    """ Functions for creating BMesh geometry for Fence components. """

    @staticmethod
    def add_beam_straight(bm, start_vec, end_vec, thickness=0.05):
        """
        Adds a simple, straight square beam between start and end points.
        (Based on building_toolkit/geometry_building.py logic)

        Note: Creates an X-aligned beam then transforms it. Could potentially
              use profile extrusion from GeometryWalkways for more complex shapes.

        Args:
            bm (bmesh.types.BMesh): The BMesh to modify.
            start_vec (Vector): Start point of the beam.
            end_vec (Vector): End point of the beam.
            thickness (float): Thickness of the square beam profile.
        """
        dir_vec = end_vec - start_vec
        length = dir_vec.length
        if length < 0.0001: return # Avoid zero-length beam

        dir_vec_norm = dir_vec.normalized()
        half_thick = thickness / 2.0

        # Create local verts for an X-aligned beam
        local_verts = [
            Vector((0, -half_thick, -half_thick)), Vector((length, -half_thick, -half_thick)),
            Vector((length,  half_thick, -half_thick)), Vector((0,  half_thick, -half_thick)),
            Vector((0, -half_thick,  half_thick)), Vector((length, -half_thick,  half_thick)),
            Vector((length,  half_thick,  half_thick)), Vector((0,  half_thick,  half_thick)),
        ]
        verts = [bm.verts.new(v) for v in local_verts]

        # Create faces
        try:
            bm.faces.new((verts[0], verts[1], verts[2], verts[3])) # Bottom
            bm.faces.new((verts[7], verts[6], verts[5], verts[4])) # Top
            bm.faces.new((verts[0], verts[1], verts[5], verts[4])) # Side
            bm.faces.new((verts[1], verts[2], verts[6], verts[5])) # Side
            bm.faces.new((verts[2], verts[3], verts[7], verts[6])) # Side
            bm.faces.new((verts[3], verts[0], verts[4], verts[7])) # Side
        except ValueError: pass # Ignore potential face errors

        # Calculate alignment matrix (track X along direction, Z remains up if possible)
        # Use track_quat for robust rotation handling
        try:
            # Align local X axis of beam with the direction vector
            # Keep local Z axis pointing as close to world Z as possible
            quat_rot = dir_vec_norm.to_track_quat('X', 'Z')
            mat_align = quat_rot.to_matrix().to_4x4()
        except ValueError:
            # Fallback if to_track_quat fails (e.g., direction is straight up/down)
            if abs(dir_vec_norm.z) > 0.999: # Aligned with Z
                # Simple rotation if aligned with Z might depend on desired 'up'
                # For simplicity, let's skip complex alignment in this edge case for now
                # Or default to an identity matrix if no rotation is strictly needed
                mat_align = Matrix.Identity(4)
            else: # Try a different up vector
                try:
                    quat_rot = dir_vec_norm.to_track_quat('X', 'Y') # Try Y-up
                    mat_align = quat_rot.to_matrix().to_4x4()
                except ValueError:
                    print("Warning: Could not determine alignment matrix for fence beam.")
                    mat_align = Matrix.Identity(4)


        # Apply transformation: Rotate first, then translate to start position
        # Transformation matrix = Translation * Rotation
        mat_trans = Matrix.Translation(start_vec)
        mat_final = mat_trans @ mat_align

        bmesh.ops.transform(bm, matrix=mat_final, verts=verts)


    @staticmethod
    def add_vertical_post(bm, base_pos_tuple, height, thickness=0.05):
        """
        Adds a vertical post (simple square prism) at a position.
        (Based on building_toolkit/geometry_building.py logic)

        Args:
            bm (bmesh.types.BMesh): The BMesh to modify.
            base_pos_tuple (tuple): (x, y, z) coordinates for the base center.
            height (float): Height of the post.
            thickness (float): Thickness (width/depth) of the square post.
        """
        x, y, z = base_pos_tuple
        half_thick = thickness / 2.0
        # Define 8 vertices
        v = [
            Vector((x - half_thick, y - half_thick, z)), Vector((x + half_thick, y - half_thick, z)),
            Vector((x + half_thick, y + half_thick, z)), Vector((x - half_thick, y + half_thick, z)),
            Vector((x - half_thick, y - half_thick, z + height)), Vector((x + half_thick, y - half_thick, z + height)),
            Vector((x + half_thick, y + half_thick, z + height)), Vector((x - half_thick, y + half_thick, z + height)),
        ]
        verts = [bm.verts.new(coord) for coord in v]

        # Create 6 faces
        try:
            bm.faces.new((verts[0], verts[1], verts[2], verts[3])) # Bottom
            bm.faces.new((verts[7], verts[6], verts[5], verts[4])) # Top
            bm.faces.new((verts[0], verts[1], verts[5], verts[4])) # Side
            bm.faces.new((verts[1], verts[2], verts[6], verts[5])) # Side
            bm.faces.new((verts[2], verts[3], verts[7], verts[6])) # Side
            bm.faces.new((verts[3], verts[0], verts[4], verts[7])) # Side
        except ValueError: pass


    @staticmethod
    def add_vertical_post_cylinder(bm, base_pos_tuple, height, radius, segments=16):
        """
        Adds a cylindrical vertical post using bmesh.ops.create_cone.
        Uses radius parameters suitable for Blender 3.0+.

        Args:
            bm (bmesh.types.BMesh): The BMesh to modify.
            base_pos_tuple (tuple): (x, y, z) coordinates for the base center.
            height (float): Height of the cylinder.
            radius (float): Radius of the cylinder.
            segments (int): Number of segments around the cylinder.
        """
        try:
            # Use create_cone which can create cylinders with radius1 == radius2
            geom_data = bmesh.ops.create_cone(
                bm,
                cap_ends=True,
                segments=max(3, segments), # Ensure at least 3 segments
                radius1=radius, # Use radius parameter (Blender 3.0+)
                radius2=radius, # Use radius parameter
                depth=height
            )
            # The cone/cylinder is created centered at the world origin.
            # We need to translate its vertices so the *bottom center* is at base_pos.
            # The cone base is at Z = -height/2, so we translate by base_pos + (0,0,height/2)
            translate_vec = Vector(base_pos_tuple) + Vector((0, 0, height / 2.0))
            created_verts = geom_data.get('verts')
            if created_verts:
                bmesh.ops.translate(bm, verts=created_verts, vec=translate_vec)

        except Exception as e:
            print(f"Error creating cylindrical post: {e}")

# Note: This file does not contain classes to register with Blender.
# It only provides helper functions for geometry generation.