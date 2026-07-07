# World_Building_Toolkit/operators_fences.py

import bpy
import bmesh
import math
from mathutils import Vector

# Import local modules
from .config import Config
from .utils import Utils

from .operators_walkways import OP_BaseGenerator

from .geometry_fences import GeometryFences


# === Fence Operators ===

class OP_GenerateVerticalFence(OP_BaseGenerator):
    bl_idname = "wbtk.generate_vertical_fence" # Use wbtk prefix
    bl_label = "Generate Vertical Fence"
    bl_description = "Generate a modular vertical-bar metal fence"
    # bl_options = {'REGISTER', 'UNDO'} # Inherited

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        fence_width = getattr(scene, 'wbtk_vfence_width', 4.0)
        fence_height = getattr(scene, 'wbtk_vfence_height', 1.0)
        bar_spacing = getattr(scene, 'wbtk_vfence_bar_spacing', 0.3)
        post_thickness = getattr(scene, 'wbtk_vfence_post_thickness', 0.05)

        if fence_width <= 0 or fence_height <= 0 or bar_spacing <= 0 or post_thickness <= 0:
            return self.report_warning("Fence dimensions and spacing must be positive.")

        master = Utils.create_master("VerticalFence")
        # Use a specific fence material or generic metal
        fence_material = Config.MATERIAL_FENCE # Or define MATERIAL_FENCE

        # --- Use GeometryFences (placeholder calls for now) ---
        # Create BMesh objects for different parts
        bm_posts_bars = bmesh.new() # Combine side posts and vertical bars
        bm_top_rail = bmesh.new()
        bm_bottom_rail = bmesh.new()

        # Side Posts
        GeometryFences.add_vertical_post(bm_posts_bars, (0, 0, 0), fence_height, thickness=post_thickness)
        GeometryFences.add_vertical_post(bm_posts_bars, (fence_width, 0, 0), fence_height, thickness=post_thickness)

        # Vertical Bars
        # Ensure at least one space to avoid division by zero
        num_spaces = max(1, int(fence_width // bar_spacing))
        actual_spacing = fence_width / num_spaces
        # Generate bars within the spaces
        for i in range(1, num_spaces): # Iterate through points between posts
            x = i * actual_spacing
            # Make bars slightly thinner than posts
            GeometryFences.add_vertical_post(bm_posts_bars, (x, 0, 0), fence_height, thickness=post_thickness * 0.5)

        # Top Rail
        start_top = Vector((0, 0, fence_height)); end_top = Vector((fence_width, 0, fence_height))
        GeometryFences.add_beam_straight(bm_top_rail, start_top, end_top, thickness=post_thickness)

        # Bottom Rail (Place slightly above ground if needed, e.g., Z=0.05)
        start_bottom = Vector((0, 0, 0)); end_bottom = Vector((fence_width, 0, 0))
        GeometryFences.add_beam_straight(bm_bottom_rail, start_bottom, end_bottom, thickness=post_thickness)

        # --- Create Objects ---
        self.create_and_parent(bm_posts_bars, "Fence_PostsBars", Vector((0,0,0)), fence_material, master)
        self.create_and_parent(bm_top_rail, "Fence_TopRail", Vector((0,0,0)), fence_material, master)
        self.create_and_parent(bm_bottom_rail, "Fence_BottomRail", Vector((0,0,0)), fence_material, master)

        return {'FINISHED'}


class OP_GenerateChainLinkFence(OP_BaseGenerator):
    bl_idname = "wbtk.generate_chainlink_fence" # Use wbtk prefix
    bl_label = "Generate Chain-Link Fence"
    bl_description = "Generate a modular chain-link fence (posts + rails + mesh panel)"
    # bl_options = {'REGISTER', 'UNDO'} # Inherited

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        width = getattr(scene, 'wbtk_clfence_width', 4.0)
        height = getattr(scene, 'wbtk_clfence_height', 2.0)
        post_spacing = getattr(scene, 'wbtk_clfence_post_spacing', 2.0)
        thickness = getattr(scene, 'wbtk_clfence_bar_thickness', 0.05)
        divisions = getattr(scene, 'wbtk_clfence_mesh_divisions', 10)
        post_shape = getattr(scene, 'wbtk_clfence_post_shape', 'SQUARE') # SQUARE or CYLINDER

        if width <= 0 or height <= 0 or post_spacing <= 0 or thickness <= 0:
            return self.report_warning("Fence dimensions must be positive.")

        master = Utils.create_master("ChainLinkFence")
        fence_material = Config.MATERIAL_FENCE # Or define MATERIAL_FENCE
        # Use a different material for the mesh panel, maybe semi-transparent later?
        mesh_material = Config.MATERIAL_FENCE_MESH# Placeholder - maybe MATERIAL_FENCE_MESH

        # --- Use GeometryFences (placeholder calls for now) ---
        bm_posts = bmesh.new()
        bm_top_rail = bmesh.new()
        bm_bottom_rail = bmesh.new()
        bm_mesh_panel = bmesh.new()

        # Posts
        num_sections = max(1, math.ceil(width / post_spacing)) # Use ceil to ensure end post
        actual_spacing = width / num_sections
        for i in range(num_sections + 1): # Add N+1 posts for N sections
            x = i * actual_spacing
            if post_shape == 'CYLINDER':
                GeometryFences.add_vertical_post_cylinder(bm_posts, (x, 0, 0), height, radius=thickness/2.0) # Pass radius
            else: # SQUARE
                GeometryFences.add_vertical_post(bm_posts, (x, 0, 0), height, thickness=thickness)

        # Rails
        start_top = Vector((0, 0, height)); end_top = Vector((width, 0, height))
        GeometryFences.add_beam_straight(bm_top_rail, start_top, end_top, thickness=thickness)
        start_bottom = Vector((0, 0, 0)); end_bottom = Vector((width, 0, 0))
        GeometryFences.add_beam_straight(bm_bottom_rail, start_bottom, end_bottom, thickness=thickness)

        # Chain-Link Mesh Panel (Simple subdivided plane)
        mesh_offset_y = 0.01 # Slightly offset from rails/posts
        v0 = bm_mesh_panel.verts.new((0, mesh_offset_y, 0))
        v1 = bm_mesh_panel.verts.new((width, mesh_offset_y, 0))
        v2 = bm_mesh_panel.verts.new((width, mesh_offset_y, height))
        v3 = bm_mesh_panel.verts.new((0, mesh_offset_y, height))
        try:
            face = bm_mesh_panel.faces.new((v0, v1, v2, v3))
            # Subdivide the mesh grid
            if divisions > 0 and face:
                bmesh.ops.subdivide_edges(bm_mesh_panel, edges=face.edges, cuts=divisions, use_grid_fill=True)
                # Optionally: could apply wireframe modifier later or use geometry nodes
        except ValueError: pass


        # --- Create Objects ---
        self.create_and_parent(bm_posts, "Fence_CL_Posts", Vector((0,0,0)), fence_material, master)
        self.create_and_parent(bm_top_rail, "Fence_CL_TopRail", Vector((0,0,0)), fence_material, master)
        self.create_and_parent(bm_bottom_rail, "Fence_CL_BottomRail", Vector((0,0,0)), fence_material, master)
        self.create_and_parent(bm_mesh_panel, "Fence_CL_Mesh", Vector((0,0,0)), mesh_material, master)

        return {'FINISHED'}


# --- List of Operator Classes to Register from THIS file ---
_classes_to_register = (
    OP_GenerateVerticalFence,
    OP_GenerateChainLinkFence,
)