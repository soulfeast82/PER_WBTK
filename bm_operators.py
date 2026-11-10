# World_Building_Toolkit/bm_operators.py
# Build Mode — Operators
# All user actions. Delegates data work to bm_data, generation to bm_generate.

import bpy
import math
from mathutils import Vector, Euler

from . import bm_data


# ─────────────────────────────────────────────────────────────────────────────
#  ENTER / EXIT
# ─────────────────────────────────────────────────────────────────────────────

def _set_live_preview(context, on):
    """Drive the BUILD_MODE live preview without fighting the toggle operator.

    wbtk.live_preview_toggle is a TOGGLE, so calling it blind would switch a
    preview that is already correct back OFF. Check the state first.
    """
    scene = context.scene
    is_on = (getattr(scene, 'wbtk_live_preview_active', False)
             and getattr(scene, 'wbtk_live_preview_type', '') == 'BUILD_MODE')
    if is_on == bool(on):
        return
    try:
        if on:
            bpy.ops.wbtk.live_preview_toggle(generator_type='BUILD_MODE')
        else:
            bpy.ops.wbtk.live_preview_off()
    except Exception:
        pass  # never block entering/leaving Build Mode over the preview


class OP_ToggleMode(bpy.types.Operator):
    """Enter or exit Build Mode"""
    bl_idname = "wbtk.bm_toggle_mode"
    bl_label = "Toggle Build Mode"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        active = getattr(scene, 'wbtk_bm_active', False)

        if active:
            scene.wbtk_bm_active = False
            bm_data.destroy_grid()
            _set_live_preview(context, False)
            self.report({'INFO'}, "Build Mode OFF")
        else:
            scene.wbtk_bm_active = True
            bm_data.create_grid(scene)
            bpy.ops.wbtk.bm_iso_view()
            try:
                context.space_data.shading.type = 'SOLID'
                context.space_data.shading.color_type = 'OBJECT'
            except Exception:
                pass
            # ⚠️ AUTO-ENABLE REVERTED 2026-08-17, same day it shipped.
            #
            # Entering Build Mode used to switch live preview on here. Pulled
            # after reading the crash logs: 4 of 22 reports mention live
            # preview, and one from 12:54 that day crashed in
            # DepsgraphNodeBuilder::build_materials on this exact trail --
            #     Build Mode ON -> bm_add_block -> live_preview_toggle(BUILD_MODE)
            #     -> wbtk_bm_width = 8 -> crash
            # Suggestive rather than proven (1 of 22 carries that signature),
            # but defaulting every Build Mode session into a code path that
            # appears in crash reports is not a trade worth making for one
            # click. Jermaine's call, 2026-08-17.
            #
            # To restore, this is the whole change:
            #     if not getattr(scene, 'wbtk_bm_preview_optout', False):
            #         _set_live_preview(context, True)
            # The opt-out property and the get-or-set helper are deliberately
            # KEPT so that stays a one-line revert. Turning the preview OFF on
            # exit (below/above) is unrelated to this and stays -- it fixes a
            # real leak where nothing but Cleanup ever tore the preview down.
            # Start shortcut listener
            context.window_manager.modal_handler_add(self)
            self.report({'INFO'}, "Build Mode ON — A=add S=stack D=dupe X=del G=gen")
            return {'RUNNING_MODAL'}

        return {'FINISHED'}

    def modal(self, context, event):
        if not getattr(context.scene, 'wbtk_bm_active', False):
            return {'FINISHED'}

        if event.value != 'PRESS' or event.ctrl or event.alt or event.shift or event.oskey:
            return {'PASS_THROUGH'}

        if event.type == 'ESC':
            # keyboard exit — mirrors the panel's Exit button
            bpy.ops.wbtk.bm_toggle_mode()
            return {'FINISHED'}

        if not _mouse_over_view3d(context, event):
            # A window-level modal sees every keypress in every editor. Only
            # claim the letters while the mouse is over a 3D Viewport.
            return {'PASS_THROUGH'}

        key = event.type
        if key == 'A':
            bpy.ops.wbtk.bm_add_block()
        elif key == 'S':
            bpy.ops.wbtk.bm_stack_block()
        elif key == 'D':
            bpy.ops.wbtk.bm_duplicate_block()
        elif key == 'X':
            bpy.ops.wbtk.bm_delete_block()
        elif key == 'G':
            bpy.ops.wbtk.bm_generate()
        elif key == 'I':
            bpy.ops.wbtk.bm_iso_view()
        elif key == 'C':
            _cycle_chamfers(context)
        elif key == 'RIGHTMOUSE':
            if bm_data.get_selected(context):
                context.window_manager.popup_menu(
                    WBTK_MT_BuildBlockMenu.draw_items, title="Build Block", icon='MOD_BUILD')
                return {'RUNNING_MODAL'}   # consumed: no second (Object Context) menu on top
            return {'PASS_THROUGH'}
        elif key == 'LEFTMOUSE':
            # Delayed sync after selection
            bpy.app.timers.register(lambda: _deferred_sync(context.scene), first_interval=0.05)
            return {'PASS_THROUGH'}
        else:
            return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}


def _mouse_over_view3d(context, event):
    """True when the mouse is inside the main region of any 3D Viewport."""
    x, y = event.mouse_x, event.mouse_y
    screen = context.screen
    if screen is None:
        return False
    for area in screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for region in area.regions:
            if region.type != 'WINDOW':
                continue
            if region.x <= x < region.x + region.width and region.y <= y < region.y + region.height:
                return True
    return False


def _deferred_sync(scene):
    try:
        obj = bpy.context.active_object
        if bm_data.is_block(obj):
            bm_data.sync_to_panel(scene, obj)
    except Exception:
        pass
    return None  # Don't repeat


def _cycle_chamfers(context):
    obj = bm_data.get_selected(context)
    if not obj:
        return
    data = bm_data.get_data(obj)
    ch = data.get("chamfers", [])
    all_c = ["sw", "se", "ne", "nw"]
    if len(ch) >= 4:
        data["chamfers"] = []
    elif len(ch) == 0:
        data["chamfers"] = list(all_c)
    else:
        for c in all_c:
            if c not in ch:
                ch.append(c); break
        data["chamfers"] = ch
    bm_data.set_data(obj, data)


# ─────────────────────────────────────────────────────────────────────────────
#  RIGHT-CLICK MENU
# ─────────────────────────────────────────────────────────────────────────────

class WBTK_MT_BuildBlockMenu(bpy.types.Menu):
    bl_label = "Build Block"
    bl_idname = "WBTK_MT_build_block"

    def draw(self, context):
        self.draw_items(self, context)

    @staticmethod
    def draw_items(menu, context):
        layout = menu.layout
        layout.operator("wbtk.bm_stack_block", text="Stack", icon='TRIA_UP')
        layout.operator("wbtk.bm_duplicate_block", text="Duplicate", icon='DUPLICATE')
        layout.separator()
        for d in ['NORTH','SOUTH','EAST','WEST']:
            op = layout.operator("wbtk.bm_attach_block", text=f"Attach {d.title()}", icon='LINKED')
            op.direction = d
        layout.separator()
        for c in ['NE','NW','SE','SW']:
            op = layout.operator("wbtk.bm_toggle_chamfer", text=f"Chamfer {c}")
            op.corner = c
        layout.separator()
        layout.operator("wbtk.bm_delete_block", text="Delete", icon='TRASH')


# ─────────────────────────────────────────────────────────────────────────────
#  PLACEMENT
# ─────────────────────────────────────────────────────────────────────────────

class OP_AddBlock(bpy.types.Operator):
    """Place a new block at the 3D cursor"""
    bl_idname = "wbtk.bm_add_block"
    bl_label = "Add Block"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        color = tuple(getattr(scene, 'wbtk_bm_block_color', (0.0, 0.7, 1.0)))
        data = {
            "w": getattr(scene, 'wbtk_bm_width', 4.0),
            "d": getattr(scene, 'wbtk_bm_depth', 4.0),
            "h": getattr(scene, 'wbtk_bm_height', 3.0),
            "walls": {
                "north": getattr(scene, 'wbtk_bm_wall_north', 'SOLID'),
                "south": getattr(scene, 'wbtk_bm_wall_south', 'SOLID'),
                "east": getattr(scene, 'wbtk_bm_wall_east', 'SOLID'),
                "west": getattr(scene, 'wbtk_bm_wall_west', 'SOLID'),
            },
            "chamfers": [],
            "chamfer_size": getattr(scene, 'wbtk_bm_chamfer_size', 1.0),
        }
        obj = bm_data.create(scene.cursor.location.copy(), data, color)
        bm_data.select(context, obj)
        self.report({'INFO'}, "Block placed")
        return {'FINISHED'}


class OP_StackBlock(bpy.types.Operator):
    """Stack a new block on top of the selected block"""
    bl_idname = "wbtk.bm_stack_block"
    bl_label = "Stack Block"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        base = bm_data.get_selected(context)
        if not base:
            self.report({'WARNING'}, "Select a block first"); return {'CANCELLED'}
        scene = context.scene
        base_data = bm_data.get_data(base)
        setback = getattr(scene, 'wbtk_bm_auto_setback', 0.0)
        loc = base.location.copy()
        loc.z += base_data["h"]
        loc.x += setback; loc.y += setback
        color = tuple(getattr(scene, 'wbtk_bm_block_color', (0.0, 0.7, 1.0)))
        data = {
            "w": max(0.5, base_data["w"] - setback*2),
            "d": max(0.5, base_data["d"] - setback*2),
            "h": getattr(scene, 'wbtk_bm_height', 3.0),
            "walls": {
                "north": getattr(scene, 'wbtk_bm_wall_north', 'SOLID'),
                "south": getattr(scene, 'wbtk_bm_wall_south', 'SOLID'),
                "east": getattr(scene, 'wbtk_bm_wall_east', 'SOLID'),
                "west": getattr(scene, 'wbtk_bm_wall_west', 'SOLID'),
            },
            "chamfers": [], "chamfer_size": base_data.get("chamfer_size", 1.0),
        }
        obj = bm_data.create(loc, data, color)
        bm_data.select(context, obj)
        bm_data.sync_to_panel(scene, obj)
        self.report({'INFO'}, "Stacked")
        return {'FINISHED'}


class OP_AttachBlock(bpy.types.Operator):
    """Attach a new block to the side of the selected block"""
    bl_idname = "wbtk.bm_attach_block"
    bl_label = "Attach Block"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(
        name="Side",
        items=[('NORTH',"N",""),('SOUTH',"S",""),('EAST',"E",""),('WEST',"W","")],
        default='EAST')

    def execute(self, context):
        base = bm_data.get_selected(context)
        if not base:
            self.report({'WARNING'}, "Select a block first"); return {'CANCELLED'}
        scene = context.scene
        base_data = bm_data.get_data(base)
        loc = base.location.copy()
        nw = getattr(scene, 'wbtk_bm_width', 4.0)
        nd = getattr(scene, 'wbtk_bm_depth', 4.0)
        if self.direction == 'NORTH': loc.y += base_data["d"]
        elif self.direction == 'SOUTH': loc.y -= nd
        elif self.direction == 'EAST': loc.x += base_data["w"]
        elif self.direction == 'WEST': loc.x -= nw
        color = tuple(getattr(scene, 'wbtk_bm_block_color', (0.0, 0.7, 1.0)))
        data = {
            "w": nw, "d": nd, "h": base_data["h"],
            "walls": {
                "north": getattr(scene, 'wbtk_bm_wall_north', 'SOLID'),
                "south": getattr(scene, 'wbtk_bm_wall_south', 'SOLID'),
                "east": getattr(scene, 'wbtk_bm_wall_east', 'SOLID'),
                "west": getattr(scene, 'wbtk_bm_wall_west', 'SOLID'),
            },
            "chamfers": [],
            "chamfer_size": getattr(scene, 'wbtk_bm_chamfer_size', 1.0),
        }
        obj = bm_data.create(loc, data, color)
        bm_data.select(context, obj)
        bm_data.sync_to_panel(scene, obj)
        self.report({'INFO'}, f"Attached {self.direction}")
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────
#  EDIT
# ─────────────────────────────────────────────────────────────────────────────

class OP_DeleteBlock(bpy.types.Operator):
    bl_idname = "wbtk.bm_delete_block"
    bl_label = "Delete Block"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        obj = bm_data.get_selected(context)
        if not obj: self.report({'WARNING'}, "Select a block"); return {'CANCELLED'}
        bm_data.delete(obj)
        self.report({'INFO'}, "Deleted"); return {'FINISHED'}


class OP_DuplicateBlock(bpy.types.Operator):
    bl_idname = "wbtk.bm_duplicate_block"
    bl_label = "Duplicate Block"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        obj = bm_data.get_selected(context)
        if not obj: self.report({'WARNING'}, "Select a block"); return {'CANCELLED'}
        data = bm_data.get_data(obj)
        loc = obj.location.copy(); loc.x += data["w"] + 1.0
        color = tuple(getattr(context.scene, 'wbtk_bm_block_color', (0.0, 0.7, 1.0)))
        new = bm_data.create(loc, dict(data), color)
        bm_data.select(context, new)
        bm_data.sync_to_panel(context.scene, new)
        self.report({'INFO'}, "Duplicated"); return {'FINISHED'}


class OP_SyncFromBlock(bpy.types.Operator):
    bl_idname = "wbtk.bm_sync_from_block"
    bl_label = "Load Block"
    bl_options = {'INTERNAL'}
    def execute(self, context):
        obj = bm_data.get_selected(context)
        if obj: bm_data.sync_to_panel(context.scene, obj)
        return {'FINISHED'}


class OP_ToggleChamfer(bpy.types.Operator):
    bl_idname = "wbtk.bm_toggle_chamfer"
    bl_label = "Toggle Chamfer"
    bl_options = {'REGISTER', 'UNDO'}
    corner: bpy.props.EnumProperty(name="Corner",
        items=[('NE',"NE",""),('NW',"NW",""),('SE',"SE",""),('SW',"SW","")])
    def execute(self, context):
        obj = bm_data.get_selected(context)
        if not obj: self.report({'WARNING'}, "Select a block"); return {'CANCELLED'}
        data = bm_data.get_data(obj)
        ch = data.get("chamfers", [])
        c = self.corner.lower()
        if c in ch: ch.remove(c)
        else: ch.append(c)
        data["chamfers"] = ch
        bm_data.set_data(obj, data)
        self.report({'INFO'}, f"{self.corner}: {'ON' if c in ch else 'OFF'}"); return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────
#  MIRROR
# ─────────────────────────────────────────────────────────────────────────────

class OP_MirrorX(bpy.types.Operator):
    bl_idname = "wbtk.bm_mirror_x"
    bl_label = "Mirror X"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        return _mirror(context, self, 'X')

class OP_MirrorY(bpy.types.Operator):
    bl_idname = "wbtk.bm_mirror_y"
    bl_label = "Mirror Y"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        return _mirror(context, self, 'Y')

def _mirror(context, op, axis):
    blocks = bm_data.get_all()
    if not blocks: op.report({'WARNING'}, "No blocks"); return {'CANCELLED'}
    vals = []
    for o in blocks:
        d = bm_data.get_data(o)
        if axis == 'X':
            vals.append(o.location.x); vals.append(o.location.x + d["w"])
        else:
            vals.append(o.location.y); vals.append(o.location.y + d["d"])
    center = (min(vals)+max(vals))/2
    created = 0
    color = tuple(getattr(context.scene, 'wbtk_bm_block_color', (0.0, 0.7, 1.0)))
    for o in list(blocks):
        d = bm_data.get_data(o)
        md = dict(d)
        if axis == 'X':
            mx = 2*center - o.location.x - d["w"]
            loc = Vector((mx, o.location.y, o.location.z))
            w = md.get("walls",{}); w["east"],w["west"] = w.get("west","SOLID"),w.get("east","SOLID")
            swaps = {"ne":"nw","nw":"ne","se":"sw","sw":"se"}
        else:
            my = 2*center - o.location.y - d["d"]
            loc = Vector((o.location.x, my, o.location.z))
            w = md.get("walls",{}); w["north"],w["south"] = w.get("south","SOLID"),w.get("north","SOLID")
            swaps = {"ne":"se","se":"ne","nw":"sw","sw":"nw"}
        md["walls"] = w
        md["chamfers"] = [swaps.get(c,c) for c in md.get("chamfers",[])]
        exists = any(abs(x.location.x-loc.x)<0.01 and abs(x.location.y-loc.y)<0.01
                     and abs(x.location.z-loc.z)<0.01 for x in bm_data.get_all())
        if not exists:
            bm_data.create(loc, md, color); created += 1
    op.report({'INFO'}, f"Mirrored {created}"); return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────
#  UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

class OP_ClearAll(bpy.types.Operator):
    bl_idname = "wbtk.bm_clear_all"
    bl_label = "Clear All"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        bm_data.clear_all(context.scene)
        self.report({'INFO'}, "Cleared"); return {'FINISHED'}


class OP_IsoView(bpy.types.Operator):
    bl_idname = "wbtk.bm_iso_view"
    bl_label = "Iso View"
    bl_options = {'REGISTER'}
    def execute(self, context):
        for area in context.screen.areas:
            if area.type != 'VIEW_3D': continue
            for space in area.spaces:
                if space.type != 'VIEW_3D': continue
                rv3d = space.region_3d
                rv3d.view_perspective = 'ORTHO'
                rv3d.view_rotation = Euler((math.radians(60),0,math.radians(45)),'XYZ').to_quaternion()
                blocks = bm_data.get_all()
                if blocks:
                    centers = []
                    for o in blocks:
                        d = bm_data.get_data(o)
                        centers.append(o.location + Vector((d["w"]/2,d["d"]/2,d["h"]/2)))
                    rv3d.view_location = sum(centers, Vector())/len(centers)
                    rv3d.view_distance = max(max(bm_data.get_data(o)["w"] for o in blocks)*2.5, 20.0)
                else:
                    rv3d.view_distance = 20.0
                try:
                    space.shading.type = 'SOLID'; space.shading.color_type = 'OBJECT'
                except Exception: pass
                break
            break
        return {'FINISHED'}


class OP_Generate(bpy.types.Operator):
    bl_idname = "wbtk.bm_generate"
    bl_label = "Generate Building"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        blocks = bm_data.get_all()
        if not blocks: self.report({'WARNING'}, "No blocks"); return {'CANCELLED'}
        from . import bm_generate
        bm_generate.generate_full(context.scene)
        self.report({'INFO'}, f"Generated from {len(blocks)} blocks"); return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────
#  CLEANUP — destructive safety net for orphaned WBTK helpers
# ─────────────────────────────────────────────────────────────────────────────

class OP_CleanupHelpers(bpy.types.Operator):
    """Remove all WBTK Build Mode blocks, detail stamps, grids, live preview, and their empty collections"""
    bl_idname = "wbtk.bm_cleanup_helpers"
    bl_label = "Cleanup All Helpers"
    bl_options = {'REGISTER'}

    # Prefixes and exact names that identify WBTK helper objects.
    _OBJ_PREFIXES = ("WBTK_BM_", "WBTK_DTL_", "_WBTK_")
    _OBJ_EXACT    = ("WBTK_Live_Preview",)
    _MESH_EXACT   = ("WBTK_Live_Preview_Mesh",)

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(
            self, event,
            message="Remove all Build Mode blocks, details, grids, and helper objects? "
                    "This cannot be undone.")

    def execute(self, context):
        from . import bm_details as _bmd
        from . import operators_live_preview as _olp

        scene = context.scene
        was_active = getattr(scene, 'wbtk_bm_active', False)

        # Stop the live preview timer first so it cannot recreate the
        # WBTK_Live_Preview object we're about to delete.
        try:
            _olp.cleanup()
        except Exception as e:
            print(f"WBTK Cleanup: live preview cleanup failed: {e}")

        collections_to_try = (bm_data.COLLECTION_NAME, _bmd.DETAIL_COLLECTION)

        # 1) Objects by prefix or exact name.
        obj_count = 0
        for obj in list(bpy.data.objects):
            name = obj.name
            if name.startswith(self._OBJ_PREFIXES) or name in self._OBJ_EXACT:
                try:
                    bpy.data.objects.remove(obj, do_unlink=True)
                    obj_count += 1
                except Exception as e:
                    print(f"WBTK Cleanup: could not remove object '{name}': {e}")

        # 2) Orphan meshes by exact name (catches datablocks whose owning
        #    object was removed earlier or never existed).
        for me in list(bpy.data.meshes):
            if me.name in self._MESH_EXACT and me.users == 0:
                try:
                    bpy.data.meshes.remove(me)
                except Exception as e:
                    print(f"WBTK Cleanup: could not remove mesh '{me.name}': {e}")

        # 3) Empty WBTK helper collections.
        col_count = 0
        for col_name in collections_to_try:
            col = bpy.data.collections.get(col_name)
            if col and len(col.objects) == 0 and len(col.children) == 0:
                try:
                    bpy.data.collections.remove(col)
                    col_count += 1
                except Exception as e:
                    print(f"WBTK Cleanup: could not remove collection '{col_name}': {e}")

        # 4) Auto-exit Build Mode if it was active at the start of cleanup.
        #    Mirrors OP_ToggleMode's exit path so the user lands in a clean
        #    known-off state instead of a half-state (mode on, grid gone).
        if was_active:
            try:
                scene.wbtk_bm_active = False
                bm_data.destroy_grid()
            except Exception as e:
                print(f"WBTK Cleanup: auto-exit Build Mode failed: {e}")

        msg = f"Cleanup complete: removed {obj_count} objects, {col_count} collections"
        if was_active:
            msg += ". Build Mode exited."
        self.report({'INFO'}, msg)
        return {'FINISHED'}


# ─────────────────────────────────────────────────────────────────────────────

_classes = (
    OP_ToggleMode,
    WBTK_MT_BuildBlockMenu,
    OP_AddBlock,
    OP_StackBlock,
    OP_AttachBlock,
    OP_DeleteBlock,
    OP_DuplicateBlock,
    OP_SyncFromBlock,
    OP_ToggleChamfer,
    OP_MirrorX,
    OP_MirrorY,
    OP_ClearAll,
    OP_IsoView,
    OP_Generate,
    OP_CleanupHelpers,
)
