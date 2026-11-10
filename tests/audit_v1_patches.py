"""WBTK audit v1 fix pass -- the exact 32 patches from CLAUDE_WBTK_fix_pass_Audit_v1.md.

    python tests/audit_v1_patches.py --check    # verify every anchor matches exactly once, change nothing
    python tests/audit_v1_patches.py --apply    # back up each file to <name>.py.bak_audit1, apply, py_compile

Run from the PER_WBTK folder (or pass --root <folder>). NOT imported by the addon --
__init__.py never touches tests/. Line endings are preserved per file (24 modules are
CRLF on disk). Stops at the first anchor that does not match exactly once -- the STOP
CONDITION -- and applies nothing further. Re-running --apply on an already-patched tree
reports every anchor as missing, which is the expected "already applied" signal.
"""
import argparse
import os
import py_compile
import shutil
import sys

PATCHES = []

def P(id, title, file, why, old, new, verify, risk="mechanical"):
    PATCHES.append(dict(id=id, title=title, file=file, why=why, old=old, new=new, verify=verify, risk=risk))

# ---------------------------------------------------------------------------
P("A1", "Preview & Place: move what the generator CREATED, not what is selected",
  "operators_preview.py",
  "Every generator wired to Preview & Place (shell, tree, shrub) builds at the world origin and selects "
  "nothing; Utils.bm_to_obj then restores the (empty) selection. The move loop therefore moves zero objects "
  "and the ghost's position is discarded. Diffing bpy.data.objects around the generate call catches exactly "
  "what was made; only top-level new objects are moved so parented children are not moved twice.",
  """        bpy.ops.object.select_all(action='DESELECT')

        try:
            # Parse "wbtk.generate_tree" → getattr(bpy.ops.wbtk, "generate_tree")
            parts = entry['place_op'].split('.')
            op_module = getattr(bpy.ops, parts[0])
            op_func = getattr(op_module, parts[1])
            op_func()
        except Exception as e:
            self.report({'ERROR'}, f"Generation failed: {e}")
            return

        for obj in list(context.selected_objects):
            obj.location = obj.location + position
""",
  """        bpy.ops.object.select_all(action='DESELECT')
        before = {o.name for o in bpy.data.objects}

        try:
            # Parse "wbtk.generate_tree" → getattr(bpy.ops.wbtk, "generate_tree")
            parts = entry['place_op'].split('.')
            op_module = getattr(bpy.ops, parts[0])
            op_func = getattr(op_module, parts[1])
            op_func()
        except Exception as e:
            self.report({'ERROR'}, f"Generation failed: {e}")
            return

        # Move what the generator CREATED. The generators build at the origin and
        # select nothing (bm_to_obj restores the empty selection), so relying on
        # context.selected_objects moved nothing and every placement landed at
        # (0,0,0). Only top-level new objects are moved: a new child of a new
        # master follows its parent and must not be offset a second time.
        new_objs = [o for o in bpy.data.objects if o.name not in before]
        roots = [o for o in new_objs if o.parent is None or o.parent.name in before]
        if not roots:
            roots = list(context.selected_objects)
        for obj in roots:
            obj.location = obj.location + position
""",
  "Foliage > Tree > Preview & Place, click ~10 m from the origin: the trunk appears under the cursor, not at (0,0,0). Same for Structures > Preview & Place in Viewport.")

# ---------------------------------------------------------------------------
P("A2", "Face Magnet: pipe the two panel controls into the operator",
  "ui.py",
  "The Face Magnet panel draws scene props wbtk_fm_align_normal / wbtk_fm_offset but never hands them to the "
  "operator, which reads only its own `offset` and `align_to_normal` properties. The two controls do nothing.",
  """        row = box.row()
        row.scale_y = 1.5
        op = row.operator("wbtk.face_magnet", text="FACE MAGNET", icon='SNAP_FACE')
""",
  """        row = box.row()
        row.scale_y = 1.5
        op = row.operator("wbtk.face_magnet", text="FACE MAGNET", icon='SNAP_FACE')
        # The operator reads its OWN properties; without these two lines the
        # panel controls above are decorative.
        op.offset = getattr(scene, 'wbtk_fm_offset', 0.0)
        op.align_to_normal = getattr(scene, 'wbtk_fm_align_normal', True)
""",
  "Set Surface Offset to 0.5 m, run Face Magnet onto a wall: the object floats 0.5 m off the face. Untick Align: it keeps its rotation.")

# ---------------------------------------------------------------------------
P("A3", "Detail stamps: parent without doubling the block offset",
  "bm_details.py",
  "place_detail computes a WORLD position (bx + ...) then sets obj.parent = block without a parent-inverse, "
  "so Blender treats that position as LOCAL to the block: the stamp lands at 2x the block's offset. Only a "
  "block sitting at the world origin looks right.",
  """    # Parent to block
    obj.parent = block_obj
""",
  """    # Parent to block. The location above is WORLD space, so cancel the
    # parent's transform or the stamp lands at twice the block's offset.
    obj.parent = block_obj
    obj.matrix_parent_inverse = block_obj.matrix_world.inverted()
""",
  "Add a block, Attach EAST (block at x=4), select it, add an AC Unit on South: it sits on that block's south face, not 4 m further east.")

# ---------------------------------------------------------------------------
P("A4", "Horizontal beams: build a real prism instead of a flat ribbon",
  "geometry_walkways.py",
  "add_beam builds the rail profile in the XY plane and extrudes it along X or Y, i.e. INSIDE its own plane. "
  "Live-measured in Blender 5.1.1: a 2 m X beam has bbox 2.07 x 0.07 x 0.00. Every horizontal rail, grate "
  "bar and ladder rung is zero-thickness. _add_profile_beam_angled_internal already orients the profile "
  "perpendicular to the direction (verified 2.00 x 0.07 x 0.07), so delegate to it.",
  """        if axis == 'X': offset = Vector((length, 0, 0))
        elif axis == 'Y': offset = Vector((0, length, 0))
        elif axis == 'Z': offset = Vector((0, 0, length))
        else: print(f"Error: Invalid axis '{axis}'."); return None

        return GeometryWalkways._add_profile_beam_internal(bm, profile_verts, base_pos, offset)
""",
  """        if axis == 'X': offset = Vector((length, 0, 0))
        elif axis == 'Y': offset = Vector((0, length, 0))
        elif axis == 'Z': offset = Vector((0, 0, length))
        else: print(f"Error: Invalid axis '{axis}'."); return None

        # The profile lives in the XY plane. Extruding it along X or Y keeps it
        # IN that plane (a zero-thickness ribbon); the angled helper builds an
        # orthonormal basis so the profile is perpendicular to the run.
        return GeometryWalkways._add_profile_beam_angled_internal(bm, profile_verts, Vector(base_pos), offset)
""",
  "Walkways > Straight > Generate with Rails=Left: the horizontal rails are round tubes from the side view. Ladder rungs are tubes.")

# ---------------------------------------------------------------------------
P("A5", "UE Pipeline: the scale WBTK's exporters need is 1.0, not 0.01",
  "ui.py",
  "Both WBTK FBX exporters use apply_scale_options='FBX_SCALE_NONE', and the exporter (read from the 5.1.1 "
  "install) applies unit_scale = 100 * scene.unit_settings.scale_length. Geometry is authored 1 BU = 1 m. "
  "At 1.0 a 3.5 m storey exports as 350 cm (correct); at 0.01 it exports as 3.5 cm and every unit='LENGTH' "
  "field starts displaying centimetres. The panel currently tells the user 1.0 'Needs fix!'.",
  """        current_scale = context.scene.unit_settings.scale_length
        is_correct = abs(current_scale - 0.01) < 0.0001

        row = box_scale.row()
        if is_correct:
            row.label(text=f"Scale: {current_scale:.4f} ✓ Ready for UE", icon='CHECKMARK')
        else:
            row.label(text=f"Scale: {current_scale:.4f} ✗ Needs fix!", icon='ERROR')

        op_scale = box_scale.operator("wbtk.check_ue_scale", text="Fix Scale to 0.01", icon='DRIVER_DISTANCE')
        op_scale.fix_scale = True
""",
  """        current_scale = context.scene.unit_settings.scale_length
        # WBTK authors 1 BU = 1 m and both FBX exporters use FBX_SCALE_NONE, which
        # multiplies by 100 * scale_length: at 1.0 a 3.5 m storey lands in UE as
        # 350 cm; at 0.01 it lands as 3.5 cm and every (m) field shows cm.
        is_correct = abs(current_scale - 1.0) < 0.0001

        row = box_scale.row()
        if is_correct:
            row.label(text=f"Scale: {current_scale:.4f} ✓ metres — WBTK exports at UE cm", icon='CHECKMARK')
        else:
            row.label(text=f"Scale: {current_scale:.4f} ✗ WBTK exports will be {100*current_scale:.0f}% size", icon='ERROR')

        op_scale = box_scale.operator("wbtk.check_ue_scale", text="Reset Scale to 1.0 (metres)", icon='DRIVER_DISTANCE')
        op_scale.fix_scale = True
""",
  "With scene scale 1.0 the panel shows a checkmark. Realize + Export a 1-storey Buildify building, import the FBX in UE: 350 cm tall.",
  risk="policy — confirm no other pipeline step depends on 0.01")

P("A5b", "UE Pipeline: the operator side of the same fix",
  "operators_ue_pipeline.py",
  "Companion to A5: Config.UE_UNIT_SCALE is 0.01 and the operator sets it. Target 1.0 and say why.",
  """        scene = context.scene
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
""",
  """        scene = context.scene
        current_scale = scene.unit_settings.scale_length
        # 1.0 (metres). WBTK geometry is authored 1 BU = 1 m and its FBX exporters
        # convert to UE centimetres themselves (FBX_SCALE_NONE = x100 at scale 1.0).
        # 0.01 would export everything at 1/100 size and flip every length field
        # in the sidebar to centimetres.
        target_scale = 1.0

        if abs(current_scale - target_scale) < 0.0001:
            self.report({'INFO'}, "Scene scale is 1.0 (metres) — WBTK exports land in UE at centimetre scale.")
            return {'FINISHED'}

        if self.fix_scale:
            scene.unit_settings.system = 'METRIC'
            scene.unit_settings.scale_length = target_scale
            self.report({'INFO'},
                f"Scene scale reset: {current_scale:.4f} → {target_scale} (Metric, metres). "
                "WBTK's Realize + Export and Export FBX now land at the right size in UE."
            )
        else:
            self.report({'WARNING'},
                f"Scene scale is {current_scale:.4f} — should be {target_scale} for WBTK's exporters. "
                "Run again with Fix Scale enabled."
            )
""",
  "Click the button at scale 0.01: scene goes to 1.0 and the Info bar explains why.",
  risk="policy — same decision as A5")

# ---------------------------------------------------------------------------
P("A6", "Realize + Export: carry the kit's UVs and smooth flags into the realized mesh",
  "operators_ue_pipeline.py",
  "_harvest rebuilds the realized mesh with from_pydata(verts, [], faces) — vertices and faces only. No UV "
  "layer is created, so the FBX ships with zero UVs and the whole kit-UV effort (Box Project, Validator) "
  "never reaches Unreal. Loops from from_pydata follow the face order given, so per-source-polygon UV "
  "lists can be flattened straight into a new layer.",
  """    verts, faces, mats = [], [], []
    kinds, no_uv = {}, set()
    count = 0

    for inst in depsgraph.object_instances:
        if not inst.is_instance:
            continue
        if not (inst.parent and inst.parent.original is obj):
            continue
        src = inst.object
        me = src.data
        if me is None or not me.polygons:
            continue

        count += 1
        oname = src.original.name if src.original else src.name
        kinds[oname] = kinds.get(oname, 0) + 1
        if not me.uv_layers:
            no_uv.add(oname)

        mtx = inst.matrix_world.copy()
        slots = [ms.material.name if ms.material else None for ms in src.material_slots]
        base = len(verts)
        verts.extend(tuple(mtx @ v.co) for v in me.vertices)
        for poly in me.polygons:
            faces.append(tuple(i + base for i in poly.vertices))
            mats.append(slots[poly.material_index] if poly.material_index < len(slots) else None)
""",
  """    verts, faces, mats = [], [], []
    uvs, smooth = [], []          # per loop (flat u,v pairs) / per polygon
    kinds, no_uv = {}, set()
    count = 0

    for inst in depsgraph.object_instances:
        if not inst.is_instance:
            continue
        if not (inst.parent and inst.parent.original is obj):
            continue
        src = inst.object
        me = src.data
        if me is None or not me.polygons:
            continue

        count += 1
        oname = src.original.name if src.original else src.name
        kinds[oname] = kinds.get(oname, 0) + 1
        uv_layer = me.uv_layers.active or (me.uv_layers[0] if me.uv_layers else None)
        if uv_layer is None:
            no_uv.add(oname)

        mtx = inst.matrix_world.copy()
        slots = [ms.material.name if ms.material else None for ms in src.material_slots]
        base = len(verts)
        verts.extend(tuple(mtx @ v.co) for v in me.vertices)
        for poly in me.polygons:
            faces.append(tuple(i + base for i in poly.vertices))
            mats.append(slots[poly.material_index] if poly.material_index < len(slots) else None)
            smooth.append(poly.use_smooth)
            # from_pydata emits loops in the order the face tuple lists its
            # verts, which is poly.loop_indices order here.
            if uv_layer is not None:
                for li in poly.loop_indices:
                    uvs.extend(uv_layer.data[li].uv)
            else:
                uvs.extend((0.0, 0.0) * len(poly.vertices))
""",
  "Realize + Export, then in the Outliner check SM_DW_Building_A > UV Maps: one 'UVMap' present; the FBX shows a UV channel in UE's static mesh editor.")

P("A6b", "Realize + Export: write the collected UVs/smooth flags onto the output mesh",
  "operators_ue_pipeline.py",
  "Second half of A6.",
  """    out = bpy.data.meshes.new(name + "_Mesh")
    out.from_pydata(verts, [], faces)
    out.validate(verbose=False)
""",
  """    out = bpy.data.meshes.new(name + "_Mesh")
    out.from_pydata(verts, [], faces)
    if len(out.polygons) == len(faces):
        # validate() can drop degenerate faces, which would misalign per-loop data;
        # only write UVs/smooth when the face count survived intact.
        if len(out.loops) * 2 == len(uvs):
            layer = out.uv_layers.new(name="UVMap")
            layer.data.foreach_set("uv", uvs)
        out.polygons.foreach_set("use_smooth", smooth)
    out.validate(verbose=False)
""",
  "Same as A6.")

# ---------------------------------------------------------------------------
P("A7", "Live preview: a toggle must not push an undo step",
  "operators_live_preview.py",
  "WBTK_OT_LivePreviewToggle has 'UNDO', so Ctrl+Z after switching the preview on undoes the scene props and "
  "the preview object while the module-level timer keeps running — the panel shows OFF, the timer recreates "
  "the preview. live_preview_off already omits UNDO; match it.",
  """    bl_idname  = "wbtk.live_preview_toggle"
    bl_label   = "Toggle Live Preview"
    bl_options = {'REGISTER', 'UNDO'}
""",
  """    bl_idname  = "wbtk.live_preview_toggle"
    bl_label   = "Toggle Live Preview"
    bl_options = {'REGISTER'}   # no UNDO: undoing a toggle desyncs the timer from the scene props
""",
  "Toggle Live Preview on, press Ctrl+Z: nothing weird happens (the toggle is not an undo step).")

P("A7b", "Live preview: reset module state when a different .blend is loaded",
  "operators_live_preview.py",
  "bpy.app.timers.register defaults to persistent=False, so loading another file silently kills the timer "
  "while _live_state keeps 'active'/'timer_running' = True. The next toggle then either reports 'OFF' when "
  "you asked for ON, or (different generator type) never restarts the timer, so the preview freezes.",
  """def cleanup():
    \"\"\"Call from addon unregister to clean up timer and preview object.\"\"\"
    _stop_timer()
    _delete_live_preview()
""",
  """def cleanup():
    \"\"\"Call from addon unregister to clean up timer and preview object.\"\"\"
    _stop_timer()
    _delete_live_preview()


from bpy.app.handlers import persistent as _persistent


@_persistent
def on_load_post(*_args):
    \"\"\"Loading a .blend drops non-persistent timers; drop our state with them.
    (*_args: handler signatures vary across Blender versions.)\"\"\"
    _live_state['active'] = False
    _live_state['type'] = ''
    _live_state['last_hash'] = ''
    _live_state['timer_running'] = False
""",
  "Turn a preview on, File > New, open the sidebar: one click on Live Preview turns it ON (not 'OFF').")

P("A7c", "Live preview: register/unregister the load handler",
  "__init__.py",
  "Wires A7b. Guarded so a double-register on reload cannot duplicate the handler.",
  """    print(f"{bl_info['name']} Registered.")
""",
  """    # 3. Load handler: reset live-preview module state when a file is loaded
    if operators_live_preview.on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(operators_live_preview.on_load_post)

    print(f"{bl_info['name']} Registered.")
""",
  "Reload Scripts twice; bpy.app.handlers.load_post contains on_load_post exactly once.")

P("A7d", "Live preview: unregister the load handler",
  "__init__.py",
  "Wires A7b (teardown).",
  """    # 0. Stop live preview timer and clean up preview objects
    try:
        operators_live_preview.cleanup()
    except Exception as e:
        print(f"Warning: Live preview cleanup failed: {e}")
""",
  """    # 0. Stop live preview timer and clean up preview objects
    try:
        operators_live_preview.cleanup()
    except Exception as e:
        print(f"Warning: Live preview cleanup failed: {e}")
    try:
        if operators_live_preview.on_load_post in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(operators_live_preview.on_load_post)
    except Exception as e:
        print(f"Warning: load_post handler removal failed: {e}")
""",
  "Disable the addon: no handler left in bpy.app.handlers.load_post.")

# ---------------------------------------------------------------------------
P("A8", "Build Mode hotkeys: only over the 3D viewport, never with Shift/OSKey, Esc exits",
  "bm_operators.py",
  "The modal eats A/S/D/X/G/I/C window-wide: Shift+A, Shift+D, Shift+S, G(grab), S(scale), X(delete), "
  "I(keyframe), C(circle select) all fire Build Mode ops instead, in every editor (typing 'a' in the Python "
  "console adds a block). There is also no keyboard way out of the mode.",
  """    def modal(self, context, event):
        if not getattr(context.scene, 'wbtk_bm_active', False):
            return {'FINISHED'}

        if event.value != 'PRESS' or event.ctrl or event.alt:
            return {'PASS_THROUGH'}

        key = event.type
""",
  """    def modal(self, context, event):
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
""",
  "In Build Mode: Shift+A over the viewport opens Blender's Add menu; typing 'a' in the Python Console types an 'a'; Esc over the viewport exits Build Mode.")

P("A8b", "Build Mode hotkeys: the viewport hit-test helper",
  "bm_operators.py",
  "Helper for A8.",
  """def _deferred_sync(scene):
""",
  """def _mouse_over_view3d(context, event):
    \"\"\"True when the mouse is inside the main region of any 3D Viewport.\"\"\"
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
""",
  "Same as A8.")

# ---------------------------------------------------------------------------
P("A9", "Kit Validator: never judge WBTK's own helper objects",
  "operators_kit_validator.py",
  "With nothing selected the validator scans every scene mesh, so from the Build Mode panel it reports the "
  "grid ('no faces'), the grid fill, every WBTK_BM_ block and the footprint as failures.",
  """    def _targets(self, context):
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        if sel:
            return sel, "selection"
        return [o for o in context.scene.objects if o.type == 'MESH'], "scene"
""",
  """    # WBTK's own helpers are not kit pieces: the grid is edges-only ("no faces"),
    # the blocks and footprint carry no UVs by design.
    _HELPER_PREFIXES = ("WBTK_BM_", "WBTK_DTL_", "_WBTK_", "WBTK_BFY_", "WBTK_Live_Preview",
                        "WBTK_Preview_Object")

    def _targets(self, context):
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        if sel:
            return sel, "selection"
        return [o for o in context.scene.objects
                if o.type == 'MESH' and not o.name.startswith(self._HELPER_PREFIXES)], "scene"
""",
  "Enter Build Mode, add two blocks, click Validate Kit with nothing selected: no FAIL lines for _WBTK_BM_Grid / WBTK_BM_0000.")

# ---------------------------------------------------------------------------
P("A10", "Export Footprints: hand the footprint to the next step (select + activate)",
  "operators_buildify.py",
  "Summon Build Engine needs the footprint ACTIVE, but the export leaves the selection untouched, so the user "
  "has to find WBTK_BFY_Footprint in the Outliner between the two buttons.",
  """        if not ob.matrix_world.is_identity:
            # Deliberately NOT reset -- if the user moved it, that is a choice.
            # But the verts are absolute Build Mode world coordinates, so the
            # building will not land where the blocks are, and that mismatch is
            # invisible until you go looking for it.
            self.report(
                {'WARNING'},
                "'%s' has a non-identity transform - the Buildify result will "
                "be offset from the Build Mode blocks." % FOOTPRINT_NAME)
        return {'FINISHED'}
""",
  """        if not ob.matrix_world.is_identity:
            # Deliberately NOT reset -- if the user moved it, that is a choice.
            # But the verts are absolute Build Mode world coordinates, so the
            # building will not land where the blocks are, and that mismatch is
            # invisible until you go looking for it.
            self.report(
                {'WARNING'},
                "'%s' has a non-identity transform - the Buildify result will "
                "be offset from the Build Mode blocks." % FOOTPRINT_NAME)
        # Make the footprint the active object so Summon Build Engine can run
        # next without a trip to the Outliner. Selection only; no data change.
        if ob.name in context.view_layer.objects:
            try:
                for o in context.selected_objects:
                    o.select_set(False)
                ob.select_set(True)
                context.view_layer.objects.active = ob
            except RuntimeError:
                pass
        return {'FINISHED'}
""",
  "Export Footprints: WBTK_BFY_Footprint is highlighted/active afterwards; Summon Build Engine works immediately.")

P("A10b", "Summon Build Engine: fall back to the footprint by name",
  "operators_build_engine.py",
  "Companion to A10: if the active object is not a mesh, use WBTK_BFY_Footprint when it exists.",
  """    def execute(self, context):
        target = context.active_object
        if target is None or target.type != 'MESH':
            self.report({'ERROR'}, "Select the footprint mesh first "
                                   "(run 'Export Footprints for Buildify' if you have none).")
            return {'CANCELLED'}
""",
  """    def execute(self, context):
        target = context.active_object
        if target is None or target.type != 'MESH':
            from .operators_buildify import FOOTPRINT_NAME
            target = bpy.data.objects.get(FOOTPRINT_NAME)
            if target is not None and target.type == 'MESH':
                self.report({'INFO'}, "No mesh active - using '%s'." % FOOTPRINT_NAME)
        if target is None or target.type != 'MESH':
            self.report({'ERROR'}, "Select the footprint mesh first "
                                   "(run 'Export Footprints for Buildify' if you have none).")
            return {'CANCELLED'}
""",
  "Deselect everything, click Summon Build Engine: it builds on WBTK_BFY_Footprint.")

# ---------------------------------------------------------------------------
P("A11", "Block Composer: inverted Min/Max can no longer crash the generator",
  "operators_block_composer.py",
  "randint(min, max) raises ValueError when min > max; the panel lets Min Fl > Max Fl and Min W > Max W.",
  """                bw_tiles = rng.randint(min_bldg_w, min(max_bldg_w, remaining_tiles))
""",
  """                hi_w = max(min_bldg_w, min(max_bldg_w, remaining_tiles))
                bw_tiles = rng.randint(min_bldg_w, hi_w)
""",
  "Block Composer with Min W 6 / Max W 5: generates instead of a traceback.")

P("A11b", "Block Composer: floors half of A11",
  "operators_block_composer.py",
  "Same defect for floors.",
  """                b_floors = rng.randint(min_floors, max_floors)
""",
  """                b_floors = rng.randint(min(min_floors, max_floors), max(min_floors, max_floors))
""",
  "Block Composer with Min Fl 5 / Max Fl 2: generates instead of a traceback.")

# ---------------------------------------------------------------------------
P("A12", "Zero rounded corners: bevel miters are sharp (parametric shell)",
  "operators_structures.py",
  "MITER_ARC rounds every outer corner, against the locked 'Zero rounded corners' art law.",
  """                    mod.affect = 'EDGES'
                    mod.profile = 0.5
                    mod.miter_outer = 'MITER_ARC'
""",
  """                    mod.affect = 'EDGES'
                    mod.profile = 0.5
                    mod.miter_outer = 'MITER_SHARP'   # art law: zero rounded corners
""",
  "Edge Bevel on, Segments 1: corners are hard chamfers, no arcs.")

P("A12b", "Zero rounded corners: same for Build Mode Generate",
  "bm_generate.py",
  "Same law, second call site.",
  """        mod.affect = 'EDGES'; mod.profile = 0.5; mod.miter_outer = 'MITER_ARC'
""",
  """        mod.affect = 'EDGES'; mod.profile = 0.5; mod.miter_outer = 'MITER_SHARP'   # art law: zero rounded corners
""",
  "Same as A12 via Build Mode > Generate.")

P("A12c", "Zero rounded corners: default bevel segments = 1 (hard chamfer)",
  "properties.py",
  "The property's own tooltip says 1 = hard chamfer, 3+ = rounded; the default 2 is on the rounded side.",
  """        ('wbtk_building_bevel_segments', bpy.props.IntProperty(
            name="Bevel Segments", default=2, min=1, max=6,
""",
  """        ('wbtk_building_bevel_segments', bpy.props.IntProperty(
            name="Bevel Segments", default=1, min=1, max=6,
""",
  "Fresh scene: Bevel Segments reads 1.")

# ---------------------------------------------------------------------------
P("A13", "Canon spelling in the Region DNA dropdown (properties)",
  "properties.py",
  "Canon is 'Neo Vespyr' and 'Sangre Neón'. Labels only — enum identifiers stay so saved files keep loading.",
  """                ('NEO_VESPER',  "Neo Vesper",        "Corporate district — tall, clean, glass and steel"),
                ('SANGRE_NEON', "Sangre Neon",       "Desert rust meets neon — weathered adobe and metal"),
""",
  """                ('NEO_VESPER',  "Neo Vespyr",        "Corporate district — tall, clean, glass and steel"),
                ('SANGRE_NEON', "Sangre Neón",       "Desert rust meets neon — weathered adobe and metal"),
""",
  "Global Settings / Structures > Region DNA dropdown reads Neo Vespyr / Sangre Neón.")

P("A13b", "Canon spelling in region_dna.py (label)",
  "region_dna.py",
  "Same as A13.",
  """    'NEO_VESPER': {
        'label': "Neo Vesper",
""",
  """    'NEO_VESPER': {
        'label': "Neo Vespyr",
""",
  "Apply DNA report reads 'Neo Vespyr'.")

P("A13c", "Canon spelling in region_dna.py (enum items)",
  "region_dna.py",
  "Same as A13.",
  """    ('NEO_VESPER',  "Neo Vesper",        REGION_PRESETS['NEO_VESPER']['description']),
    ('SANGRE_NEON', "Sangre Neon",       REGION_PRESETS['SANGRE_NEON']['description']),
""",
  """    ('NEO_VESPER',  "Neo Vespyr",        REGION_PRESETS['NEO_VESPER']['description']),
    ('SANGRE_NEON', "Sangre Neón",       REGION_PRESETS['SANGRE_NEON']['description']),
""",
  "n/a (list is currently unused; kept in sync).")

P("A13d", "Canon spelling in region_dna.py (Sangre label)",
  "region_dna.py",
  "Same as A13.",
  """        'label': "Sangre Neon (Tierra Oxidada)",
""",
  """        'label': "Sangre Neón (Tierra Oxidada)",
""",
  "Apply DNA report reads 'Sangre Neón'.")

# ---------------------------------------------------------------------------
P("A14", "bl_info: pin the real minimum Blender version and fix the two misleading import comments",
  "__init__.py",
  "The version pin is 5.1 (set_sharp_from_angle keyword form is required there). '# Footprint Painter' heads "
  "an empty section (feature removed in v0.11.0) and '# Custom Builder' mislabels the Build Mode modules.",
  """    "blender": (5, 0, 0),
""",
  """    "blender": (5, 1, 0),
""",
  "Preferences > Add-ons shows the 5.1.0 requirement.")

P("A14b", "Misleading import comments",
  "__init__.py",
  "Second half of A14.",
  """# Footprint Painter

# Custom Builder (Viewport Block Painter)
from . import bm_data
""",
  """# Build Mode (PRIMARY authoring workflow): data / operators / generation / stamps
from . import bm_data
""",
  "py_compile only.")

# ---------------------------------------------------------------------------
P("A15", "Foliage: delete the back-face calls that can never succeed",
  "geometry_foliage.py",
  "bm.faces.new raises 'face already exists' for the same vertex set in any winding (live-verified 5.1.1), "
  "so the 'double-sided' back face is swallowed by the except and every card is single-sided. Decision: keep "
  "cards single-sided and make the leaf MATERIAL two-sided (Blender: backface culling off; UE: Two Sided) — "
  "standard foliage practice and half the polycount. Removing the dead calls makes the code say what it does.",
  """        try:
            bm.faces.new((v0, v1, v2, v3))
            # Back face for double-sided appearance
            bm.faces.new((v0, v3, v2, v1))
        except ValueError:
            pass
""",
  """        # Single-sided card. A reversed-winding "back face" cannot be added to the
        # same four verts (faces.new raises 'face already exists'); two-sidedness
        # belongs to the leaf MATERIAL (backface culling off / UE Two Sided).
        try:
            bm.faces.new((v0, v1, v2, v3))
        except ValueError:
            pass
""",
  "Generate Tree: same leaf count as before (the back faces never existed); WBTK_Leaves material has Backface Culling off.")

P("A15b", "Foliage: same dead call in the grass blades",
  "geometry_foliage.py",
  "Same as A15.",
  """                    try:
                        bm.faces.new((v0, v1, v2, v3))
                        bm.faces.new((v0, v3, v2, v1))
                    except ValueError:
                        pass
""",
  """                    try:
                        bm.faces.new((v0, v1, v2, v3))   # single-sided; see _add_leaf_card
                    except ValueError:
                        pass
""",
  "Generate Ground Cover: unchanged output.")

P("A15c", "Foliage: same dead call in the weed blades",
  "geometry_foliage.py",
  "Same as A15.",
  """                try:
                    bm.faces.new((v0, v1, v2, v3))
                    bm.faces.new((v0, v3, v2, v1))
                except ValueError:
                    pass
""",
  """                try:
                    bm.faces.new((v0, v1, v2, v3))   # single-sided; see _add_leaf_card
                except ValueError:
                    pass
""",
  "Generate Ground Cover (weed type): unchanged output.")

# ---------------------------------------------------------------------------
P("A16", "Build Mode right-click: one menu, not two",
  "bm_operators.py",
  "RIGHTMOUSE opens the Build Block popup AND passes the event through, so Blender's Object Context Menu "
  "opens on top of it (the 'right-click menu collision' in CLAUDE.md).",
  """        elif key == 'RIGHTMOUSE':
            if bm_data.get_selected(context):
                context.window_manager.popup_menu(
                    WBTK_MT_BuildBlockMenu.draw_items, title="Build Block", icon='MOD_BUILD')
            return {'PASS_THROUGH'}
""",
  """        elif key == 'RIGHTMOUSE':
            if bm_data.get_selected(context):
                context.window_manager.popup_menu(
                    WBTK_MT_BuildBlockMenu.draw_items, title="Build Block", icon='MOD_BUILD')
                return {'RUNNING_MODAL'}   # consumed: no second (Object Context) menu on top
            return {'PASS_THROUGH'}
""",
  "Right-click a block in Build Mode: only the Build Block menu appears. Right-click empty space: Blender's normal menu.")


def _read(path):
    raw = open(path, "rb").read()
    crlf = b"\r\n" in raw
    return raw.decode("utf-8").replace("\r\n", "\n"), crlf


def _write(path, text, crlf):
    data = text.replace("\n", "\r\n") if crlf else text
    open(path, "wb").write(data.encode("utf-8"))


def run(root, apply):
    files = []
    for p in PATCHES:
        if p["file"] not in files:
            files.append(p["file"])
    # 1. check every anchor first, on the current disk state, in order
    state = {}
    for f in files:
        state[f] = _read(os.path.join(root, f))
    problems = []
    for p in PATCHES:
        text, _ = state[p["file"]]
        n = text.count(p["old"])
        if n != 1:
            problems.append("%s %s: anchor found %d time(s), expected 1" % (p["id"], p["file"], n))
        else:
            state[p["file"]] = (text.replace(p["old"], p["new"]), state[p["file"]][1])
    if problems:
        print("STOP -- anchors did not match exactly once:")
        for line in problems:
            print("   " + line)
        print("Nothing was written.")
        return 2
    print("all %d anchors match exactly once across %d files" % (len(PATCHES), len(files)))
    if not apply:
        return 0
    # 2. backup, write, compile -- one file at a time
    for f in files:
        path = os.path.join(root, f)
        bak = path + ".bak_audit1"
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
        text, crlf = state[f]
        _write(path, text, crlf)
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as exc:
            print("COMPILE FAILED for %s -- restoring from backup" % f)
            print(exc)
            shutil.copy2(bak, path)
            return 3
        print("patched + py_compile OK  %-32s (%s, backup %s)" % (f, "CRLF" if crlf else "LF", os.path.basename(bak)))
    print("done: %d patches, %d files" % (len(PATCHES), len(files)))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.exit(run(a.root, a.apply))
