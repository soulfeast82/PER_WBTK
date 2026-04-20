# World_Building_Toolkit/operators_ue_pipeline.py
# Unreal Engine Pipeline Tools + Face Magnetism
# v0.2.0

import bpy
import bmesh
import math
from mathutils import Vector, Matrix, Quaternion
from bpy_extras import view3d_utils

from .config import Config


# =============================================================================
# OPERATOR 1 — Check & Fix Scene Scale for Unreal
# =============================================================================

class WBTK_OT_CheckUEScale(bpy.types.Operator):
    """Check if scene unit scale is set correctly for Unreal Engine export (requires 0.01)"""
    bl_idname = "wbtk.check_ue_scale"
    bl_label = "Check UE Scale"
    bl_options = {'REGISTER', 'UNDO'}

    fix_scale: bpy.props.BoolProperty(
        name="Fix Scale",
        description="Automatically set unit scale to 0.01 if wrong",
        default=True
    )

    def execute(self, context):
        scene = context.scene
        current_scale = scene.unit_settings.scale_length
        target_scale = Config.UE_UNIT_SCALE  # 0.01

        if abs(current_scale - target_scale) < 0.0001:
            self.report({'INFO'}, "Scene scale is already correct (0.01) — ready for Unreal export.")
            return {'FINISHED'}

        if self.fix_scale:
            scene.unit_settings.system = 'METRIC'
            scene.unit_settings.scale_length = target_scale
            self.report({'INFO'},
                f"Scene scale fixed: {current_scale:.4f} → {target_scale} (Metric). "
                "Xavier150 addon will now export at correct UE scale."
            )
        else:
            self.report({'WARNING'},
                f"Scene scale is {current_scale:.4f} — should be {target_scale} for Unreal. "
                "Run again with Fix Scale enabled."
            )

        return {'FINISHED'}


# =============================================================================
# OPERATOR 2 — Send Object to UE Export Collection
# =============================================================================

class WBTK_OT_SendToExportCollection(bpy.types.Operator):
    """Move selected objects into the UE_Export collection so Xavier150 addon can batch-send them to Unreal"""
    bl_idname = "wbtk.send_to_export_collection"
    bl_label = "Send to UE Export"
    bl_options = {'REGISTER', 'UNDO'}

    include_ucx: bpy.props.BoolProperty(
        name="Include UCX Colliders",
        description="Also move any UCX_ collision meshes that belong to selected objects",
        default=True
    )

    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not selected:
            self.report({'WARNING'}, "No mesh objects selected. Select the objects you want to export first.")
            return {'CANCELLED'}

        export_coll_name = Config.EXPORT_COLLECTION  # "UE_Export"

        # Get or create the UE_Export collection
        if export_coll_name in bpy.data.collections:
            export_coll = bpy.data.collections[export_coll_name]
        else:
            export_coll = bpy.data.collections.new(export_coll_name)
            context.scene.collection.children.link(export_coll)

        moved_count = 0
        ucx_count = 0

        for obj in selected:
            _move_to_collection(obj, export_coll)
            moved_count += 1

            # Optionally find and move associated UCX colliders
            if self.include_ucx:
                ucx_name = f"UCX_{obj.name}_00"
                ucx_obj = bpy.data.objects.get(ucx_name)
                if ucx_obj:
                    _move_to_collection(ucx_obj, export_coll)
                    ucx_count += 1

        msg = f"Moved {moved_count} object(s) to '{export_coll_name}'."
        if ucx_count > 0:
            msg += f" Included {ucx_count} UCX collider(s)."
        msg += " Now run Xavier150's export from the N-panel > BFU tab."

        self.report({'INFO'}, msg)
        return {'FINISHED'}


def _move_to_collection(obj, target_coll):
    """Helper: move object to target collection, removing from all others."""
    if obj.name not in target_coll.objects:
        target_coll.objects.link(obj)
    for coll in list(obj.users_collection):
        if coll != target_coll:
            try:
                coll.objects.unlink(obj)
            except RuntimeError:
                pass


# =============================================================================
# OPERATOR 3 — Face Magnetism (Snap Object to Face)
# =============================================================================

class WBTK_OT_FaceMagnet(bpy.types.Operator):
    """Snap the selected object flush to a face on another object.
    
    HOW TO USE:
    1. Select the object you want to MOVE (the one that snaps)
    2. Click 'Face Magnet' in the panel
    3. Hover over any face on any other object in the viewport
    4. The moving object previews its position snapped to that face
    5. Left-click to CONFIRM the snap
    6. Right-click or Escape to CANCEL
    """
    bl_idname = "wbtk.face_magnet"
    bl_label = "Face Magnet"
    bl_options = {'REGISTER', 'UNDO'}

    # --- Internal state (not user-facing properties) ---
    _snap_object = None        # The object being moved
    _original_matrix = None    # Save original transform for cancel
    _handler = None            # Draw handler reference (unused but kept for future)

    offset: bpy.props.FloatProperty(
        name="Surface Offset",
        description="Gap between the snapped object and the target face (0 = flush)",
        default=0.0,
        min=0.0,
        max=1.0,
        step=1,
        precision=3,
        unit='LENGTH'
    )

    align_to_normal: bpy.props.BoolProperty(
        name="Align to Face Normal",
        description="Rotate the object so it faces out from the target surface",
        default=True
    )

    def invoke(self, context, event):
        # Must have exactly one active mesh object selected
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Select a mesh object first — that's the object that will snap.")
            return {'CANCELLED'}

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Save the object and its original transform
        self._snap_object = obj
        self._original_matrix = obj.matrix_world.copy()

        # Start modal
        context.window_manager.modal_handler_add(self)
        context.area.header_text_set(
            "FACE MAGNET  |  Hover over a face → Left-Click to SNAP  |  Right-Click / Esc to CANCEL"
        )
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        context.area.tag_redraw()

        # --- CANCEL ---
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            # Restore original transform
            self._snap_object.matrix_world = self._original_matrix
            context.area.header_text_set(None)
            self.report({'INFO'}, "Face Magnet cancelled — object returned to original position.")
            return {'CANCELLED'}

        # --- CONFIRM ---
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            context.area.header_text_set(None)
            self.report({'INFO'},
                f"Snapped '{self._snap_object.name}' to face. "
                "Use F9 to adjust offset or alignment."
            )
            return {'FINISHED'}

        # --- MOUSE MOVE — update preview ---
        if event.type == 'MOUSEMOVE':
            self._update_snap_preview(context, event)

        # Pass through navigation events so user can orbit/pan while using the tool
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    def _update_snap_preview(self, context, event):
        """Raycast from mouse position, find nearest face, snap object to it."""
        region = context.region
        rv3d = context.region_data
        obj_to_snap = self._snap_object

        if not region or not rv3d or not obj_to_snap:
            return

        # Convert mouse position to a 3D ray
        mouse_coord = (event.mouse_region_x, event.mouse_region_y)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse_coord)
        ray_direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse_coord)

        if not ray_origin or not ray_direction:
            return

        # Raycast against the scene, excluding the object being moved
        depsgraph = context.evaluated_depsgraph_get()
        hit, location, normal, face_index, hit_object, matrix = context.scene.ray_cast(
            depsgraph, ray_origin, ray_direction
        )

        if not hit:
            return

        # Don't snap to yourself
        if hit_object == obj_to_snap:
            return

        # --- Calculate snap position ---
        # Get the bounding box of the snapping object to find its "bottom" extent
        # We want the face of the object touching the target face, not its origin
        snap_offset = self._get_snap_offset(obj_to_snap, normal) + self.offset

        # Position: hit point + normal * offset
        new_location = location + (normal * snap_offset)

        if self.align_to_normal:
            # Build a rotation that aligns the object's local -Z axis to the face normal
            # This makes the object "stand up" on the face correctly
            new_rotation = normal.to_track_quat('Z', 'Y')
            obj_to_snap.matrix_world = (
                Matrix.Translation(new_location) @
                new_rotation.to_matrix().to_4x4()
            )
        else:
            # Keep original rotation, just move position
            rot_mat = obj_to_snap.matrix_world.to_3x3().to_4x4()
            obj_to_snap.matrix_world = Matrix.Translation(new_location) @ rot_mat

    def _get_snap_offset(self, obj, face_normal):
        """
        Calculate how far the object's origin is from the face that should
        contact the surface. Uses the bounding box projected onto the normal.
        
        For a wall panel snapping to a wall face, this gives you the correct
        offset so the panel face — not the origin — is flush with the surface.
        """
        try:
            # Get bounding box corners in local space
            bbox_local = [Vector(corner) for corner in obj.bound_box]

            # Transform to world space using current rotation/scale (no translation)
            rot_scale = obj.matrix_world.to_3x3()
            bbox_world_relative = [rot_scale @ corner for corner in bbox_local]

            # Project all corners onto the face normal
            # The minimum projection value tells us how far the "back" of the object is
            projections = [corner.dot(face_normal) for corner in bbox_world_relative]
            min_proj = min(projections)

            # Return negative of min so origin moves to align the back face to surface
            return -min_proj

        except Exception:
            # Fallback: just use 0 offset if bbox calculation fails
            return 0.0

    def execute(self, context):
        # execute() is called when re-applying from F9 redo panel
        # The object should already be positioned from modal, just return
        return {'FINISHED'}


# =============================================================================
# OPERATOR 4 — Generate and auto-send to Export Collection
# =============================================================================

class WBTK_OT_AutoTagForExport(bpy.types.Operator):
    """Tag all objects currently in 'World Builder Output' collection for UE export.
    Moves them to the UE_Export collection in one click."""
    bl_idname = "wbtk.auto_tag_for_export"
    bl_label = "Tag All WB Output for Export"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        source_coll = bpy.data.collections.get(Config.TARGET_COLLECTION)
        if not source_coll:
            self.report({'WARNING'},
                f"'{Config.TARGET_COLLECTION}' collection not found. "
                "Generate some objects first."
            )
            return {'CANCELLED'}

        # Get all mesh objects from World Builder Output
        wb_objects = [obj for obj in source_coll.objects if obj.type == 'MESH']

        if not wb_objects:
            self.report({'WARNING'}, "No mesh objects found in World Builder Output collection.")
            return {'CANCELLED'}

        # Select them all and run Send to Export
        bpy.ops.object.select_all(action='DESELECT')
        for obj in wb_objects:
            obj.select_set(True)
        if wb_objects:
            context.view_layer.objects.active = wb_objects[0]

        bpy.ops.wbtk.send_to_export_collection()
        return {'FINISHED'}


# =============================================================================
# REGISTRATION
# =============================================================================

_classes_to_register = (
    WBTK_OT_CheckUEScale,
    WBTK_OT_SendToExportCollection,
    WBTK_OT_FaceMagnet,
    WBTK_OT_AutoTagForExport,
)
