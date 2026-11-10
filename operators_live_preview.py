# World_Building_Toolkit/operators_live_preview.py
# Live Preview — persistent teal wireframe in the viewport that rebuilds
# automatically whenever you change any slider. No modal, no button press
# to update. Just toggle it on and tweak.
#
# HOW IT WORKS:
#  1. Toggle "Live Preview" ON in any generator panel
#  2. A teal wireframe appears at the 3D cursor position
#  3. Change ANY slider → the wireframe auto-rebuilds within ~0.25 seconds
#  4. Toggle OFF or click "Generate" → wireframe is cleaned up
#
# ARCHITECTURE:
#  - Reuses the preview registry from operators_preview.py (same build_fn / hash_fn)
#  - Uses bpy.app.timers for periodic hash checking (lightweight, ~4 checks/sec)
#  - Separate object name from Preview & Place so they don't conflict

import bpy
import bmesh
from mathutils import Vector

from .operators_preview import _PREVIEW_REGISTRY


# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

LIVE_OBJ_NAME  = "WBTK_Live_Preview"
LIVE_MESH_NAME = "WBTK_Live_Preview_Mesh"

# Module-level state
_live_state = {
    'active': False,
    'type': '',
    'last_hash': '',
    'timer_running': False,
}


# ─────────────────────────────────────────────────────────────────────────────
#  PREVIEW OBJECT MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def _get_live_preview_obj():
    """Return the live preview object if it exists."""
    return bpy.data.objects.get(LIVE_OBJ_NAME)


def _delete_live_preview():
    """Remove the live preview object and orphan mesh."""
    obj = bpy.data.objects.get(LIVE_OBJ_NAME)
    if obj:
        me = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if me and me.users == 0:
            bpy.data.meshes.remove(me)


def _rebuild_live_preview():
    """Rebuild the live preview mesh from the active generator's current settings."""
    gen_type = _live_state['type']
    entry = _PREVIEW_REGISTRY.get(gen_type)
    if not entry:
        return

    scene = None
    # Get scene from context safely
    try:
        scene = bpy.context.scene
    except Exception:
        pass
    if not scene:
        return

    # Build the preview BMesh
    try:
        bm = entry['build_fn'](scene)
    except Exception as e:
        print(f"WBTK Live Preview: build failed for {gen_type}: {e}")
        return

    if not bm or not bm.verts:
        if bm:
            bm.free()
        return

    # Get or create the preview object
    obj = _get_live_preview_obj()

    if obj:
        # Update existing mesh in-place
        old_me = obj.data
        new_me = bpy.data.meshes.new(LIVE_MESH_NAME + "_tmp")
        bm.to_mesh(new_me)
        bm.free()
        new_me.update()
        obj.data = new_me
        # Remove old mesh
        if old_me and old_me.users == 0:
            bpy.data.meshes.remove(old_me)
        # Rename to canonical
        new_me.name = LIVE_MESH_NAME
    else:
        # Create new preview object at 3D cursor
        me = bpy.data.meshes.new(LIVE_MESH_NAME)
        bm.to_mesh(me)
        bm.free()
        me.update()

        obj = bpy.data.objects.new(LIVE_OBJ_NAME, me)
        obj.display_type  = 'WIRE'
        obj.hide_render   = True
        obj.show_in_front = True
        obj.color         = (0.0, 0.85, 1.0, 0.9)  # Teal

        # Place at 3D cursor
        try:
            cursor_loc = bpy.context.scene.cursor.location.copy()
            obj.location = cursor_loc
        except Exception:
            obj.location = Vector((0, 0, 0))

        # Link to active collection
        try:
            bpy.context.collection.objects.link(obj)
        except Exception:
            try:
                bpy.context.scene.collection.objects.link(obj)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
#  TIMER — periodic hash check and rebuild
# ─────────────────────────────────────────────────────────────────────────────

def _live_preview_timer():
    """Called ~4 times per second. Checks if settings changed, rebuilds if so."""
    if not _live_state['active']:
        _live_state['timer_running'] = False
        return None  # Returning None unregisters the timer

    gen_type = _live_state['type']
    entry = _PREVIEW_REGISTRY.get(gen_type)
    if not entry:
        _live_state['timer_running'] = False
        return None

    try:
        scene = bpy.context.scene
        current_hash = entry['hash_fn'](scene)
    except Exception:
        return 0.25  # Retry

    if current_hash != _live_state['last_hash']:
        _live_state['last_hash'] = current_hash
        _rebuild_live_preview()

        # Force viewport redraw
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

    return 0.25  # Check again in 250ms


def _start_timer():
    """Start the periodic timer if not already running."""
    if not _live_state['timer_running']:
        _live_state['timer_running'] = True
        bpy.app.timers.register(_live_preview_timer, first_interval=0.1)


def _stop_timer():
    """Stop the timer immediately if registered; flag inactive as a backstop."""
    # Flip the active flag first so any in-flight tick bails out.
    _live_state['active'] = False
    # Explicit unregister so addon teardown doesn't race a pending callback.
    try:
        if bpy.app.timers.is_registered(_live_preview_timer):
            bpy.app.timers.unregister(_live_preview_timer)
    except Exception:
        pass
    _live_state['timer_running'] = False


# ─────────────────────────────────────────────────────────────────────────────
#  OPERATORS
# ─────────────────────────────────────────────────────────────────────────────

class WBTK_OT_LivePreviewToggle(bpy.types.Operator):
    """Toggle live preview for a generator — wireframe updates as you change sliders"""
    bl_idname  = "wbtk.live_preview_toggle"
    bl_label   = "Toggle Live Preview"
    bl_options = {'REGISTER'}   # no UNDO: undoing a toggle desyncs the timer from the scene props

    generator_type: bpy.props.StringProperty(
        name="Generator Type", default="BUILDING")

    def execute(self, context):
        gen_type = self.generator_type

        if gen_type not in _PREVIEW_REGISTRY:
            self.report({'WARNING'}, f"No preview registered for '{gen_type}'.")
            return {'CANCELLED'}

        # Toggle
        if _live_state['active'] and _live_state['type'] == gen_type:
            # Turn OFF
            _stop_timer()
            _delete_live_preview()
            _live_state['active'] = False
            _live_state['type'] = ''
            _live_state['last_hash'] = ''
            context.scene.wbtk_live_preview_active = False
            context.scene.wbtk_live_preview_type = ''
            if gen_type == 'BUILD_MODE':
                # Turned off by hand -> stay off next time Build Mode opens.
                context.scene.wbtk_bm_preview_optout = True
            self.report({'INFO'}, f"Live preview OFF")
        else:
            # Turn ON (or switch type)
            if _live_state['active']:
                _stop_timer()
                _delete_live_preview()

            _live_state['active'] = True
            _live_state['type'] = gen_type
            _live_state['last_hash'] = ''  # Force immediate rebuild
            context.scene.wbtk_live_preview_active = True
            context.scene.wbtk_live_preview_type = gen_type
            if gen_type == 'BUILD_MODE':
                context.scene.wbtk_bm_preview_optout = False

            # Immediate first build
            _rebuild_live_preview()
            _start_timer()

            label = _PREVIEW_REGISTRY[gen_type]['label']
            self.report({'INFO'}, f"Live preview ON — {label}")

        return {'FINISHED'}


class WBTK_OT_LivePreviewOff(bpy.types.Operator):
    """Turn off any active live preview"""
    bl_idname  = "wbtk.live_preview_off"
    bl_label   = "Live Preview Off"
    bl_options = {'REGISTER'}

    def execute(self, context):
        _stop_timer()
        _delete_live_preview()
        _live_state['active'] = False
        _live_state['type'] = ''
        _live_state['last_hash'] = ''
        context.scene.wbtk_live_preview_active = False
        context.scene.wbtk_live_preview_type = ''
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────
#  CLEANUP — called on addon unregister to stop timer and remove preview
# ─────────────────────────────────────────────────────────────────────────────

def cleanup():
    """Call from addon unregister to clean up timer and preview object."""
    _stop_timer()
    _delete_live_preview()


from bpy.app.handlers import persistent as _persistent


@_persistent
def on_load_post(*_args):
    """Loading a .blend drops non-persistent timers; drop our state with them.
    (*_args: handler signatures vary across Blender versions.)"""
    _live_state['active'] = False
    _live_state['type'] = ''
    _live_state['last_hash'] = ''
    _live_state['timer_running'] = False


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER — check if a specific type is currently live-previewing
# ─────────────────────────────────────────────────────────────────────────────

def is_live_preview_active(gen_type=None):
    """Check if live preview is active (optionally for a specific type)."""
    if gen_type:
        return _live_state['active'] and _live_state['type'] == gen_type
    return _live_state['active']


# ─────────────────────────────────────────────────────────────────────────────
#  REGISTRATION
# ─────────────────────────────────────────────────────────────────────────────

_classes_to_register = (
    WBTK_OT_LivePreviewToggle,
    WBTK_OT_LivePreviewOff,
)
