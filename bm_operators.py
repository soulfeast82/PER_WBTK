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
            # Start shortcut listener
            context.window_manager.modal_handler_add(self)
            self.report({'INFO'}, "Build Mode ON — A=add S=stack D=dupe X=del G=gen")
            return {'RUNNING_MODAL'}

        return {'FINISHED'}

    def modal(self, context, event):
        if not getattr(context.scene, 'wbtk_bm_active', False):
            return {'FINISHED'}

        if event.value != 'PRESS' or event.ctrl or event.alt:
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
            return {'PASS_THROUGH'}
        elif key == 'LEFTMOUSE':
            # Delayed sync after selection
            bpy.app.timers.register(lambda: _deferred_sync(context.scene), first_interval=0.05)
            return {'PASS_THROUGH'}
        else:
            return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}


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
)
