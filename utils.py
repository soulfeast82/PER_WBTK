# World_Building_Toolkit/utils.py
# (Based on MRTK_v380/utils.py)

import bpy
import bmesh
import math
import os
from mathutils import Vector, Matrix

# Import Config using relative import - adjusted for the combined toolkit
from .config import Config

class Utils:
    """ Helper functions for Blender operations, context access, object management. """

    @staticmethod
    def get_context_safe_bool(prop_name, default=False):
        """ Safely get a boolean scene property, returning default if context/property missing. """
        try:
            if bpy.context and bpy.context.scene and hasattr(bpy.context.scene, prop_name):
                return getattr(bpy.context.scene, prop_name)
            else:
                return default
        except (AttributeError, RuntimeError, ReferenceError):
            # Added ReferenceError for cases where scene might not exist during certain calls
            # print(f"Debug: Could not access property '{prop_name}', returning default {default}.") # Optional debug
            return default

    @staticmethod
    def create_master(name_prefix):
        """ Creates an empty object to act as the parent for generated components. """
        master_name = f"{name_prefix}_master"
        # Check if master already exists, if so, return it to avoid duplicates
        if master_name in bpy.data.objects:
            print(f"Info: Reusing existing master object: '{master_name}'")
            return bpy.data.objects[master_name]

        master = bpy.data.objects.new(master_name, None)
        master.empty_display_type = 'PLAIN_AXES'
        master.empty_display_size = Config.DEFAULT_TILE_SIZE * 0.5 # Use default tile size

        # Link to scene collection first (robustness)
        try:
            if bpy.context and bpy.context.collection:
                bpy.context.collection.objects.link(master)
            else: # Fallback
                root_coll = bpy.data.collections.get("Collection") or bpy.context.scene.collection # Try scene collection as fallback
                if root_coll: root_coll.objects.link(master)

        except Exception as e:
            print(f"Warning: Linking master '{master_name}' to context collection failed: {e}")

        # Ensure it's linked to the target collection
        Utils.link_to_collection(master, Config.TARGET_COLLECTION)
        return master

    @staticmethod
    def get_or_create_material(mat_name):
        """ Retrieves a material by name or creates a simple placeholder if it doesn't exist. """
        if mat_name in bpy.data.materials:
            return bpy.data.materials[mat_name]
        else:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            # Optional: Add basic node setup
            # nodes = mat.node_tree.nodes
            # principle_bsdf = nodes.get("Principled BSDF")
            # if principle_bsdf:
            #     principle_bsdf.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1) # Default grey
            print(f"Info: Created placeholder material: '{mat_name}'")
            return mat

    @staticmethod
    def link_to_collection(obj, target_coll_name):
        """ Links an object to a specific collection, creating it if necessary, and unlinks from others if needed. """
        if not obj:
            print("Warning: Attempted to link a None object.")
            return

        # Ensure object exists in Blender's data
        if obj.name not in bpy.data.objects:
            print(f"Warning: Object '{obj.name}' not found in bpy.data.objects during link_to_collection.")
            return

        target_coll = None
        # Get or create the target collection
        if target_coll_name in bpy.data.collections:
            target_coll = bpy.data.collections[target_coll_name]
        else:
            target_coll = bpy.data.collections.new(target_coll_name)
            # Link the new collection to the scene's root collection
            try:
                if bpy.context and bpy.context.scene and bpy.context.scene.collection:
                    bpy.context.scene.collection.children.link(target_coll)
                else: # Fallback
                    root_coll = bpy.data.collections.get("Collection") or bpy.context.scene.collection
                    if root_coll: root_coll.children.link(target_coll)
            except Exception as e:
                print(f"Warning: Linking new collection '{target_coll_name}' to scene failed: {e}")

        if not target_coll:
            print(f"Error: Failed to get or create target collection '{target_coll_name}'.")
            return

        # Link object to the target collection if not already linked
        if obj.name not in target_coll.objects:
            try:
                target_coll.objects.link(obj)
            except RuntimeError as e:
                print(f"Warning: Linking object '{obj.name}' to collection '{target_coll_name}' failed (might already be linked indirectly?): {e}")

        # Unlink from other collections (except the target collection)
        # Important to avoid object appearing in multiple places
        collections_to_unlink_from = [coll for coll in obj.users_collection if coll != target_coll]
        for coll in collections_to_unlink_from:
            try:
                coll.objects.unlink(obj)
            except RuntimeError as e:
                # This might fail if it's the object's only collection link (shouldn't happen if linked to target first)
                print(f"Warning: Unlinking object '{obj.name}' from collection '{coll.name}' failed: {e}")

    @staticmethod
    def bm_to_obj(bm, name, loc, material_name=None):
        """ Converts a BMesh to a Blender object, applies material, optionally UV unwraps, and links to collection. """
        if not bm.verts:
            # print(f"Info: BMesh for '{name}' has no vertices, skipping object creation.") # Can be noisy
            bm.free()
            return None

        # Use utility functions for settings
        # Assuming property names start with 'wbtk_' in the combined addon
        assign_mats = Utils.get_context_safe_bool('wbtk_assign_materials', default=True)
        auto_unwrap = Utils.get_context_safe_bool('wbtk_auto_unwrap', default=True)

        me = bpy.data.meshes.new(name)
        obj = None

        # --- Material Assignment ---
        mat_index = -1 # Default to no material index assigned
        if material_name and assign_mats:
            mat = Utils.get_or_create_material(material_name)
            if mat:
                me.materials.append(mat)
                mat_index = 0 # Assign the first (and only) material

        # Assign material index to BMesh faces *before* converting to mesh
        if mat_index >= 0:
            for f in bm.faces:
                f.material_index = mat_index

        # --- BMesh to Mesh Conversion and Object Creation ---
        try:
            bm.to_mesh(me)
            bm.free()
            me.update()
            # Fix potential invalid normals after bmesh conversion
         

            obj = bpy.data.objects.new(name, me)
            obj.location = loc # Set location *before* linking

            # Link to target collection (handles scene linking/unlinking internally)
            Utils.link_to_collection(obj, Config.TARGET_COLLECTION)

        except Exception as e:
            print(f"Error: Failed converting BMesh to object '{name}': {e}")
            if 'bm' in locals() and bm.is_valid: bm.free()
            if 'me' in locals() and me.name in bpy.data.meshes: bpy.data.meshes.remove(me)
            if 'obj' in locals() and obj and obj.name in bpy.data.objects: bpy.data.objects.remove(obj)
            return None

        # --- Auto UV Unwrapping ---
        if obj and auto_unwrap:
            # Store context safely
            view_layer = bpy.context.view_layer if bpy.context else None
            active_obj_orig = view_layer.objects.active if view_layer else None
            selected_objs_orig = bpy.context.selected_objects[:] if bpy.context else []

            # Perform operations only if view_layer exists
            if view_layer:
                try:
                    # Ensure object mode
                    if active_obj_orig and active_obj_orig.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
                    # Deselect all, select only the new object, make it active
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    view_layer.objects.active = obj

                    # UV unwrap
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.uv.smart_project(angle_limit=Config.UV_ANGLE_LIMIT, island_margin=Config.UV_ISLAND_MARGIN)
                    bpy.ops.object.mode_set(mode='OBJECT')
                except Exception as e:
                    print(f"Warning: UV unwrapping failed for '{name}': {e}")
                    # Ensure we are back in object mode even if unwrapping failed
                    if obj and obj.mode != 'OBJECT':
                        try: bpy.ops.object.mode_set(mode='OBJECT')
                        except RuntimeError: pass
                finally:
                    # Restore original selection and active object carefully
                    try:
                        bpy.ops.object.select_all(action='DESELECT')
                        for s_obj in selected_objs_orig:
                            if s_obj and s_obj.name in view_layer.objects: # Check if still exists
                                s_obj.select_set(True)
                        if active_obj_orig and active_obj_orig.name in view_layer.objects: # Check if still exists
                            view_layer.objects.active = active_obj_orig
                    except (ReferenceError, RuntimeError) as e_restore:
                        print(f"Warning: Error restoring selection/active state after UV unwrapping: {e_restore}")
                        pass # Avoid crashing if restoration fails

        return obj

    @staticmethod
    def add_ucx_collider(visual_obj, master_obj):
        """ Creates a simple box UCX collider matching the visual object's bounds and parents it. """
        # Use the utility function for setting check
        if not visual_obj or not Utils.get_context_safe_bool('wbtk_add_ucx', default=True):
            return None

        ucx_name = f"UCX_{visual_obj.name}_00"

        # --- Improved Bounding Box Calculation (World Space) ---
        min_dimension = 0.01 # Minimum size for any axis to avoid zero-volume issues
        try:
            # Ensure dependencies are calculated for accurate bounding box
            if bpy.context and bpy.context.evaluated_depsgraph_get:
                depsgraph = bpy.context.evaluated_depsgraph_get()
                visual_eval = visual_obj.evaluated_get(depsgraph)
                world_bbox_corners = [visual_eval.matrix_world @ Vector(corner) for corner in visual_eval.bound_box]
            else: # Fallback if no context/depsgraph
                world_bbox_corners = [visual_obj.matrix_world @ Vector(corner) for corner in visual_obj.bound_box]

            if not world_bbox_corners: raise ValueError("No bounding box corners found.")

            min_c = Vector((min(c[i] for c in world_bbox_corners) for i in range(3)))
            max_c = Vector((max(c[i] for c in world_bbox_corners) for i in range(3)))
            dims = max_c - min_c
            center = (min_c + max_c) / 2.0

            # Ensure minimum dimensions
            dims.x = max(dims.x, min_dimension)
            dims.y = max(dims.y, min_dimension)
            dims.z = max(dims.z, min_dimension)

        except (AttributeError, ValueError, TypeError, ReferenceError) as e:
            print(f"Warning: Bounding box calculation failed for '{visual_obj.name}': {e}. Collider might be inaccurate.")
            # Fallback: Use visual object's dimensions directly (less accurate for rotated objects)
            dims = visual_obj.dimensions
            center = visual_obj.matrix_world.translation # Use object origin as center
            dims.x = max(dims.x, min_dimension)
            dims.y = max(dims.y, min_dimension)
            dims.z = max(dims.z, min_dimension)

        # --- Check/Create UCX Object ---
        ucx_obj = None
        if ucx_name in bpy.data.objects:
            ucx_obj = bpy.data.objects[ucx_name]
            print(f"Info: Reusing existing UCX collider: '{ucx_name}'")
            # Update mesh if needed? Generally no for simple boxes.
        else:
            ucx_mesh = bpy.data.meshes.new(f"{ucx_name}_Mesh") # Give mesh distinct name
            ucx_obj = bpy.data.objects.new(ucx_name, ucx_mesh)

            # Create cube BMesh and scale it
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1.0) # Start with unit cube
            # Scale vertices relative to origin (0,0,0)
            scale_mat = Matrix.Diagonal((dims.x / 2.0, dims.y / 2.0, dims.z / 2.0)).to_4x4()
            bmesh.ops.transform(bm, matrix=scale_mat, verts=bm.verts)
            bm.to_mesh(ucx_mesh)
            bm.free()
            ucx_mesh.update()
            # Link new object
            Utils.link_to_collection(ucx_obj, Config.TARGET_COLLECTION)

        # --- Set Transform and Parenting ---
        # Create a new matrix for the collider at the calculated world center
        # Set rotation/scale to identity (collider is axis-aligned in world space)
        ucx_obj.matrix_world = Matrix.Translation(center)
        ucx_obj.location = center # Ensure location is set directly too
        ucx_obj.rotation_euler = (0, 0, 0)
        ucx_obj.scale = (1, 1, 1)

        if master_obj and ucx_obj.parent != master_obj:
            ucx_obj.parent = master_obj
            # After parenting, reset collider's matrix relative to parent IF NEEDED.
            # For UCX, often world alignment is desired.
            # If you want it parented WITH offset:
            # ucx_obj.matrix_parent_inverse = master_obj.matrix_world.inverted()

        # --- Set Display Properties ---
        ucx_obj.display_type = 'WIRE'
        ucx_obj.hide_render = True
        ucx_obj.select_set(False)

        return ucx_obj