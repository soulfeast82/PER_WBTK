# CLAUDE_WBTK_fix_pass_Audit_v1 — surgical patches from the 2026-09-05 audit
**Companion to `WBTK_AUDIT_v1.md`.** 32 `str_replace` patches across 17 files, applied IN ORDER.
**Round 2 (same day, §at the end): 3 more patches, A10c/A10d/A10e, one file — applied AFTER round 1 with `tests/audit_v1_patches_r2.py`.**
Validated 2026-09-05 on a copy of `f653ff1`: every anchor matches exactly once, all 36 modules + the test file `py_compile` clean afterwards, pyflakes reports one warning *fewer* than before (ui.py's unused `op`).

## Rules for this run (non-negotiable)

1. **Backup first.** For each file below: copy to `<name>.py.bak_audit1` before its first patch (never `.py`; Blender registers stray `.py` files).
2. **Anchor not found exactly as written → STOP.** Report the patch id and wait. Never improvise a substitute anchor.
3. **`python -m py_compile <file>` after every patch.** Any error → STOP and report.
4. **Restate-before-edit:** list the patch ids you are about to apply and the files they touch, then wait for a go.
5. Line endings: 24 files are CRLF on disk (marked below). Use the Edit tool (it preserves the file's endings); do not rewrite whole files.
6. When all 32 are in: run the 6 viewport checks at the end, then commit as one commit per section (A1–A4 / A5–A6 / A7–A8 / A9–A16).

## Files touched (and their on-disk line endings)

- `operators_preview.py` — CRLF
- `ui.py` — LF
- `bm_details.py` — CRLF
- `geometry_walkways.py` — CRLF
- `operators_ue_pipeline.py` — LF
- `operators_live_preview.py` — LF
- `__init__.py` — LF
- `bm_operators.py` — LF
- `operators_kit_validator.py` — LF
- `operators_buildify.py` — LF
- `operators_build_engine.py` — LF
- `operators_block_composer.py` — CRLF
- `operators_structures.py` — LF
- `bm_generate.py` — CRLF
- `properties.py` — LF
- `region_dna.py` — CRLF
- `geometry_foliage.py` — CRLF

---

## Patches

### A1 — Preview & Place: move what the generator CREATED, not what is selected

**File:** `operators_preview.py`

**Why:** Every generator wired to Preview & Place (shell, tree, shrub) builds at the world origin and selects nothing; Utils.bm_to_obj then restores the (empty) selection. The move loop therefore moves zero objects and the ghost's position is discarded. Diffing bpy.data.objects around the generate call catches exactly what was made; only top-level new objects are moved so parented children are not moved twice.

**old_string (exact):**

```python
        bpy.ops.object.select_all(action='DESELECT')

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
```

**new_string:**

```python
        bpy.ops.object.select_all(action='DESELECT')
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
```

**Verify:** Foliage > Tree > Preview & Place, click ~10 m from the origin: the trunk appears under the cursor, not at (0,0,0). Same for Structures > Preview & Place in Viewport.

### A2 — Face Magnet: pipe the two panel controls into the operator

**File:** `ui.py`

**Why:** The Face Magnet panel draws scene props wbtk_fm_align_normal / wbtk_fm_offset but never hands them to the operator, which reads only its own `offset` and `align_to_normal` properties. The two controls do nothing.

**old_string (exact):**

```python
        row = box.row()
        row.scale_y = 1.5
        op = row.operator("wbtk.face_magnet", text="FACE MAGNET", icon='SNAP_FACE')
```

**new_string:**

```python
        row = box.row()
        row.scale_y = 1.5
        op = row.operator("wbtk.face_magnet", text="FACE MAGNET", icon='SNAP_FACE')
        # The operator reads its OWN properties; without these two lines the
        # panel controls above are decorative.
        op.offset = getattr(scene, 'wbtk_fm_offset', 0.0)
        op.align_to_normal = getattr(scene, 'wbtk_fm_align_normal', True)
```

**Verify:** Set Surface Offset to 0.5 m, run Face Magnet onto a wall: the object floats 0.5 m off the face. Untick Align: it keeps its rotation.

### A3 — Detail stamps: parent without doubling the block offset

**File:** `bm_details.py`

**Why:** place_detail computes a WORLD position (bx + ...) then sets obj.parent = block without a parent-inverse, so Blender treats that position as LOCAL to the block: the stamp lands at 2x the block's offset. Only a block sitting at the world origin looks right.

**old_string (exact):**

```python
    # Parent to block
    obj.parent = block_obj
```

**new_string:**

```python
    # Parent to block. The location above is WORLD space, so cancel the
    # parent's transform or the stamp lands at twice the block's offset.
    obj.parent = block_obj
    obj.matrix_parent_inverse = block_obj.matrix_world.inverted()
```

**Verify:** Add a block, Attach EAST (block at x=4), select it, add an AC Unit on South: it sits on that block's south face, not 4 m further east.

### A4 — Horizontal beams: build a real prism instead of a flat ribbon

**File:** `geometry_walkways.py`

**Why:** add_beam builds the rail profile in the XY plane and extrudes it along X or Y, i.e. INSIDE its own plane. Live-measured in Blender 5.1.1: a 2 m X beam has bbox 2.07 x 0.07 x 0.00. Every horizontal rail, grate bar and ladder rung is zero-thickness. _add_profile_beam_angled_internal already orients the profile perpendicular to the direction (verified 2.00 x 0.07 x 0.07), so delegate to it.

**old_string (exact):**

```python
        if axis == 'X': offset = Vector((length, 0, 0))
        elif axis == 'Y': offset = Vector((0, length, 0))
        elif axis == 'Z': offset = Vector((0, 0, length))
        else: print(f"Error: Invalid axis '{axis}'."); return None

        return GeometryWalkways._add_profile_beam_internal(bm, profile_verts, base_pos, offset)
```

**new_string:**

```python
        if axis == 'X': offset = Vector((length, 0, 0))
        elif axis == 'Y': offset = Vector((0, length, 0))
        elif axis == 'Z': offset = Vector((0, 0, length))
        else: print(f"Error: Invalid axis '{axis}'."); return None

        # The profile lives in the XY plane. Extruding it along X or Y keeps it
        # IN that plane (a zero-thickness ribbon); the angled helper builds an
        # orthonormal basis so the profile is perpendicular to the run.
        return GeometryWalkways._add_profile_beam_angled_internal(bm, profile_verts, Vector(base_pos), offset)
```

**Verify:** Walkways > Straight > Generate with Rails=Left: the horizontal rails are round tubes from the side view. Ladder rungs are tubes.

### A5 — UE Pipeline: the scale WBTK's exporters need is 1.0, not 0.01

**File:** `ui.py`  ·  **Risk:** policy — confirm no other pipeline step depends on 0.01

**Why:** Both WBTK FBX exporters use apply_scale_options='FBX_SCALE_NONE', and the exporter (read from the 5.1.1 install) applies unit_scale = 100 * scene.unit_settings.scale_length. Geometry is authored 1 BU = 1 m. At 1.0 a 3.5 m storey exports as 350 cm (correct); at 0.01 it exports as 3.5 cm and every unit='LENGTH' field starts displaying centimetres. The panel currently tells the user 1.0 'Needs fix!'.

**old_string (exact):**

```python
        current_scale = context.scene.unit_settings.scale_length
        is_correct = abs(current_scale - 0.01) < 0.0001

        row = box_scale.row()
        if is_correct:
            row.label(text=f"Scale: {current_scale:.4f} ✓ Ready for UE", icon='CHECKMARK')
        else:
            row.label(text=f"Scale: {current_scale:.4f} ✗ Needs fix!", icon='ERROR')

        op_scale = box_scale.operator("wbtk.check_ue_scale", text="Fix Scale to 0.01", icon='DRIVER_DISTANCE')
        op_scale.fix_scale = True
```

**new_string:**

```python
        current_scale = context.scene.unit_settings.scale_length
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
```

**Verify:** With scene scale 1.0 the panel shows a checkmark. Realize + Export a 1-storey Buildify building, import the FBX in UE: 350 cm tall.

### A5b — UE Pipeline: the operator side of the same fix

**File:** `operators_ue_pipeline.py`  ·  **Risk:** policy — same decision as A5

**Why:** Companion to A5: Config.UE_UNIT_SCALE is 0.01 and the operator sets it. Target 1.0 and say why.

**old_string (exact):**

```python
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
```

**new_string:**

```python
        scene = context.scene
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
```

**Verify:** Click the button at scale 0.01: scene goes to 1.0 and the Info bar explains why.

### A6 — Realize + Export: carry the kit's UVs and smooth flags into the realized mesh

**File:** `operators_ue_pipeline.py`

**Why:** _harvest rebuilds the realized mesh with from_pydata(verts, [], faces) — vertices and faces only. No UV layer is created, so the FBX ships with zero UVs and the whole kit-UV effort (Box Project, Validator) never reaches Unreal. Loops from from_pydata follow the face order given, so per-source-polygon UV lists can be flattened straight into a new layer.

**old_string (exact):**

```python
    verts, faces, mats = [], [], []
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
```

**new_string:**

```python
    verts, faces, mats = [], [], []
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
```

**Verify:** Realize + Export, then in the Outliner check SM_DW_Building_A > UV Maps: one 'UVMap' present; the FBX shows a UV channel in UE's static mesh editor.

### A6b — Realize + Export: write the collected UVs/smooth flags onto the output mesh

**File:** `operators_ue_pipeline.py`

**Why:** Second half of A6.

**old_string (exact):**

```python
    out = bpy.data.meshes.new(name + "_Mesh")
    out.from_pydata(verts, [], faces)
    out.validate(verbose=False)
```

**new_string:**

```python
    out = bpy.data.meshes.new(name + "_Mesh")
    out.from_pydata(verts, [], faces)
    if len(out.polygons) == len(faces):
        # validate() can drop degenerate faces, which would misalign per-loop data;
        # only write UVs/smooth when the face count survived intact.
        if len(out.loops) * 2 == len(uvs):
            layer = out.uv_layers.new(name="UVMap")
            layer.data.foreach_set("uv", uvs)
        out.polygons.foreach_set("use_smooth", smooth)
    out.validate(verbose=False)
```

**Verify:** Same as A6.

### A7 — Live preview: a toggle must not push an undo step

**File:** `operators_live_preview.py`

**Why:** WBTK_OT_LivePreviewToggle has 'UNDO', so Ctrl+Z after switching the preview on undoes the scene props and the preview object while the module-level timer keeps running — the panel shows OFF, the timer recreates the preview. live_preview_off already omits UNDO; match it.

**old_string (exact):**

```python
    bl_idname  = "wbtk.live_preview_toggle"
    bl_label   = "Toggle Live Preview"
    bl_options = {'REGISTER', 'UNDO'}
```

**new_string:**

```python
    bl_idname  = "wbtk.live_preview_toggle"
    bl_label   = "Toggle Live Preview"
    bl_options = {'REGISTER'}   # no UNDO: undoing a toggle desyncs the timer from the scene props
```

**Verify:** Toggle Live Preview on, press Ctrl+Z: nothing weird happens (the toggle is not an undo step).

### A7b — Live preview: reset module state when a different .blend is loaded

**File:** `operators_live_preview.py`

**Why:** bpy.app.timers.register defaults to persistent=False, so loading another file silently kills the timer while _live_state keeps 'active'/'timer_running' = True. The next toggle then either reports 'OFF' when you asked for ON, or (different generator type) never restarts the timer, so the preview freezes.

**old_string (exact):**

```python
def cleanup():
    """Call from addon unregister to clean up timer and preview object."""
    _stop_timer()
    _delete_live_preview()
```

**new_string:**

```python
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
```

**Verify:** Turn a preview on, File > New, open the sidebar: one click on Live Preview turns it ON (not 'OFF').

### A7c — Live preview: register/unregister the load handler

**File:** `__init__.py`

**Why:** Wires A7b. Guarded so a double-register on reload cannot duplicate the handler.

**old_string (exact):**

```python
    print(f"{bl_info['name']} Registered.")
```

**new_string:**

```python
    # 3. Load handler: reset live-preview module state when a file is loaded
    if operators_live_preview.on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(operators_live_preview.on_load_post)

    print(f"{bl_info['name']} Registered.")
```

**Verify:** Reload Scripts twice; bpy.app.handlers.load_post contains on_load_post exactly once.

### A7d — Live preview: unregister the load handler

**File:** `__init__.py`

**Why:** Wires A7b (teardown).

**old_string (exact):**

```python
    # 0. Stop live preview timer and clean up preview objects
    try:
        operators_live_preview.cleanup()
    except Exception as e:
        print(f"Warning: Live preview cleanup failed: {e}")
```

**new_string:**

```python
    # 0. Stop live preview timer and clean up preview objects
    try:
        operators_live_preview.cleanup()
    except Exception as e:
        print(f"Warning: Live preview cleanup failed: {e}")
    try:
        if operators_live_preview.on_load_post in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(operators_live_preview.on_load_post)
    except Exception as e:
        print(f"Warning: load_post handler removal failed: {e}")
```

**Verify:** Disable the addon: no handler left in bpy.app.handlers.load_post.

### A8 — Build Mode hotkeys: only over the 3D viewport, never with Shift/OSKey, Esc exits

**File:** `bm_operators.py`

**Why:** The modal eats A/S/D/X/G/I/C window-wide: Shift+A, Shift+D, Shift+S, G(grab), S(scale), X(delete), I(keyframe), C(circle select) all fire Build Mode ops instead, in every editor (typing 'a' in the Python console adds a block). There is also no keyboard way out of the mode.

**old_string (exact):**

```python
    def modal(self, context, event):
        if not getattr(context.scene, 'wbtk_bm_active', False):
            return {'FINISHED'}

        if event.value != 'PRESS' or event.ctrl or event.alt:
            return {'PASS_THROUGH'}

        key = event.type
```

**new_string:**

```python
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
```

**Verify:** In Build Mode: Shift+A over the viewport opens Blender's Add menu; typing 'a' in the Python Console types an 'a'; Esc over the viewport exits Build Mode.

### A8b — Build Mode hotkeys: the viewport hit-test helper

**File:** `bm_operators.py`

**Why:** Helper for A8.

**old_string (exact):**

```python
def _deferred_sync(scene):
```

**new_string:**

```python
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
```

**Verify:** Same as A8.

### A9 — Kit Validator: never judge WBTK's own helper objects

**File:** `operators_kit_validator.py`

**Why:** With nothing selected the validator scans every scene mesh, so from the Build Mode panel it reports the grid ('no faces'), the grid fill, every WBTK_BM_ block and the footprint as failures.

**old_string (exact):**

```python
    def _targets(self, context):
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        if sel:
            return sel, "selection"
        return [o for o in context.scene.objects if o.type == 'MESH'], "scene"
```

**new_string:**

```python
    # WBTK's own helpers are not kit pieces: the grid is edges-only ("no faces"),
    # the blocks and footprint carry no UVs by design.
    _HELPER_PREFIXES = ("WBTK_BM_", "WBTK_DTL_", "_WBTK_", "WBTK_BFY_", "WBTK_Live_Preview",
                        "WBTK_Preview_Object")

    def _targets(self, context):
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        if sel:
            return sel, "selection"
        return [o for o in context.scene.objects
                if o.type == 'MESH' and not o.name.startswith(self._HELPER_PREFIXES)], "scene"
```

**Verify:** Enter Build Mode, add two blocks, click Validate Kit with nothing selected: no FAIL lines for _WBTK_BM_Grid / WBTK_BM_0000.

### A10 — Export Footprints: hand the footprint to the next step (select + activate)

**File:** `operators_buildify.py`

**Why:** Summon Build Engine needs the footprint ACTIVE, but the export leaves the selection untouched, so the user has to find WBTK_BFY_Footprint in the Outliner between the two buttons.

**old_string (exact):**

```python
        if not ob.matrix_world.is_identity:
            # Deliberately NOT reset -- if the user moved it, that is a choice.
            # But the verts are absolute Build Mode world coordinates, so the
            # building will not land where the blocks are, and that mismatch is
            # invisible until you go looking for it.
            self.report(
                {'WARNING'},
                "'%s' has a non-identity transform - the Buildify result will "
                "be offset from the Build Mode blocks." % FOOTPRINT_NAME)
        return {'FINISHED'}
```

**new_string:**

```python
        if not ob.matrix_world.is_identity:
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
```

**Verify:** Export Footprints: WBTK_BFY_Footprint is highlighted/active afterwards; Summon Build Engine works immediately.

### A10b — Summon Build Engine: fall back to the footprint by name

**File:** `operators_build_engine.py`

**Why:** Companion to A10: if the active object is not a mesh, use WBTK_BFY_Footprint when it exists.

**old_string (exact):**

```python
    def execute(self, context):
        target = context.active_object
        if target is None or target.type != 'MESH':
            self.report({'ERROR'}, "Select the footprint mesh first "
                                   "(run 'Export Footprints for Buildify' if you have none).")
            return {'CANCELLED'}
```

**new_string:**

```python
    def execute(self, context):
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
```

**Verify:** Deselect everything, click Summon Build Engine: it builds on WBTK_BFY_Footprint.

### A11 — Block Composer: inverted Min/Max can no longer crash the generator

**File:** `operators_block_composer.py`

**Why:** randint(min, max) raises ValueError when min > max; the panel lets Min Fl > Max Fl and Min W > Max W.

**old_string (exact):**

```python
                bw_tiles = rng.randint(min_bldg_w, min(max_bldg_w, remaining_tiles))
```

**new_string:**

```python
                hi_w = max(min_bldg_w, min(max_bldg_w, remaining_tiles))
                bw_tiles = rng.randint(min_bldg_w, hi_w)
```

**Verify:** Block Composer with Min W 6 / Max W 5: generates instead of a traceback.

### A11b — Block Composer: floors half of A11

**File:** `operators_block_composer.py`

**Why:** Same defect for floors.

**old_string (exact):**

```python
                b_floors = rng.randint(min_floors, max_floors)
```

**new_string:**

```python
                b_floors = rng.randint(min(min_floors, max_floors), max(min_floors, max_floors))
```

**Verify:** Block Composer with Min Fl 5 / Max Fl 2: generates instead of a traceback.

### A12 — Zero rounded corners: bevel miters are sharp (parametric shell)

**File:** `operators_structures.py`

**Why:** MITER_ARC rounds every outer corner, against the locked 'Zero rounded corners' art law.

**old_string (exact):**

```python
                    mod.affect = 'EDGES'
                    mod.profile = 0.5
                    mod.miter_outer = 'MITER_ARC'
```

**new_string:**

```python
                    mod.affect = 'EDGES'
                    mod.profile = 0.5
                    mod.miter_outer = 'MITER_SHARP'   # art law: zero rounded corners
```

**Verify:** Edge Bevel on, Segments 1: corners are hard chamfers, no arcs.

### A12b — Zero rounded corners: same for Build Mode Generate

**File:** `bm_generate.py`

**Why:** Same law, second call site.

**old_string (exact):**

```python
        mod.affect = 'EDGES'; mod.profile = 0.5; mod.miter_outer = 'MITER_ARC'
```

**new_string:**

```python
        mod.affect = 'EDGES'; mod.profile = 0.5; mod.miter_outer = 'MITER_SHARP'   # art law: zero rounded corners
```

**Verify:** Same as A12 via Build Mode > Generate.

### A12c — Zero rounded corners: default bevel segments = 1 (hard chamfer)

**File:** `properties.py`

**Why:** The property's own tooltip says 1 = hard chamfer, 3+ = rounded; the default 2 is on the rounded side.

**old_string (exact):**

```python
        ('wbtk_building_bevel_segments', bpy.props.IntProperty(
            name="Bevel Segments", default=2, min=1, max=6,
```

**new_string:**

```python
        ('wbtk_building_bevel_segments', bpy.props.IntProperty(
            name="Bevel Segments", default=1, min=1, max=6,
```

**Verify:** Fresh scene: Bevel Segments reads 1.

### A13 — Canon spelling in the Region DNA dropdown (properties)

**File:** `properties.py`

**Why:** Canon is 'Neo Vespyr' and 'Sangre Neón'. Labels only — enum identifiers stay so saved files keep loading.

**old_string (exact):**

```python
                ('NEO_VESPER',  "Neo Vesper",        "Corporate district — tall, clean, glass and steel"),
                ('SANGRE_NEON', "Sangre Neon",       "Desert rust meets neon — weathered adobe and metal"),
```

**new_string:**

```python
                ('NEO_VESPER',  "Neo Vespyr",        "Corporate district — tall, clean, glass and steel"),
                ('SANGRE_NEON', "Sangre Neón",       "Desert rust meets neon — weathered adobe and metal"),
```

**Verify:** Global Settings / Structures > Region DNA dropdown reads Neo Vespyr / Sangre Neón.

### A13b — Canon spelling in region_dna.py (label)

**File:** `region_dna.py`

**Why:** Same as A13.

**old_string (exact):**

```python
    'NEO_VESPER': {
        'label': "Neo Vesper",
```

**new_string:**

```python
    'NEO_VESPER': {
        'label': "Neo Vespyr",
```

**Verify:** Apply DNA report reads 'Neo Vespyr'.

### A13c — Canon spelling in region_dna.py (enum items)

**File:** `region_dna.py`

**Why:** Same as A13.

**old_string (exact):**

```python
    ('NEO_VESPER',  "Neo Vesper",        REGION_PRESETS['NEO_VESPER']['description']),
    ('SANGRE_NEON', "Sangre Neon",       REGION_PRESETS['SANGRE_NEON']['description']),
```

**new_string:**

```python
    ('NEO_VESPER',  "Neo Vespyr",        REGION_PRESETS['NEO_VESPER']['description']),
    ('SANGRE_NEON', "Sangre Neón",       REGION_PRESETS['SANGRE_NEON']['description']),
```

**Verify:** n/a (list is currently unused; kept in sync).

### A13d — Canon spelling in region_dna.py (Sangre label)

**File:** `region_dna.py`

**Why:** Same as A13.

**old_string (exact):**

```python
        'label': "Sangre Neon (Tierra Oxidada)",
```

**new_string:**

```python
        'label': "Sangre Neón (Tierra Oxidada)",
```

**Verify:** Apply DNA report reads 'Sangre Neón'.

### A14 — bl_info: pin the real minimum Blender version and fix the two misleading import comments

**File:** `__init__.py`

**Why:** The version pin is 5.1 (set_sharp_from_angle keyword form is required there). '# Footprint Painter' heads an empty section (feature removed in v0.11.0) and '# Custom Builder' mislabels the Build Mode modules.

**old_string (exact):**

```python
    "blender": (5, 0, 0),
```

**new_string:**

```python
    "blender": (5, 1, 0),
```

**Verify:** Preferences > Add-ons shows the 5.1.0 requirement.

### A14b — Misleading import comments

**File:** `__init__.py`

**Why:** Second half of A14.

**old_string (exact):**

```python
# Footprint Painter

# Custom Builder (Viewport Block Painter)
from . import bm_data
```

**new_string:**

```python
# Build Mode (PRIMARY authoring workflow): data / operators / generation / stamps
from . import bm_data
```

**Verify:** py_compile only.

### A15 — Foliage: delete the back-face calls that can never succeed

**File:** `geometry_foliage.py`

**Why:** bm.faces.new raises 'face already exists' for the same vertex set in any winding (live-verified 5.1.1), so the 'double-sided' back face is swallowed by the except and every card is single-sided. Decision: keep cards single-sided and make the leaf MATERIAL two-sided (Blender: backface culling off; UE: Two Sided) — standard foliage practice and half the polycount. Removing the dead calls makes the code say what it does.

**old_string (exact):**

```python
        try:
            bm.faces.new((v0, v1, v2, v3))
            # Back face for double-sided appearance
            bm.faces.new((v0, v3, v2, v1))
        except ValueError:
            pass
```

**new_string:**

```python
        # Single-sided card. A reversed-winding "back face" cannot be added to the
        # same four verts (faces.new raises 'face already exists'); two-sidedness
        # belongs to the leaf MATERIAL (backface culling off / UE Two Sided).
        try:
            bm.faces.new((v0, v1, v2, v3))
        except ValueError:
            pass
```

**Verify:** Generate Tree: same leaf count as before (the back faces never existed); WBTK_Leaves material has Backface Culling off.

### A15b — Foliage: same dead call in the grass blades

**File:** `geometry_foliage.py`

**Why:** Same as A15.

**old_string (exact):**

```python
                    try:
                        bm.faces.new((v0, v1, v2, v3))
                        bm.faces.new((v0, v3, v2, v1))
                    except ValueError:
                        pass
```

**new_string:**

```python
                    try:
                        bm.faces.new((v0, v1, v2, v3))   # single-sided; see _add_leaf_card
                    except ValueError:
                        pass
```

**Verify:** Generate Ground Cover: unchanged output.

### A15c — Foliage: same dead call in the weed blades

**File:** `geometry_foliage.py`

**Why:** Same as A15.

**old_string (exact):**

```python
                try:
                    bm.faces.new((v0, v1, v2, v3))
                    bm.faces.new((v0, v3, v2, v1))
                except ValueError:
                    pass
```

**new_string:**

```python
                try:
                    bm.faces.new((v0, v1, v2, v3))   # single-sided; see _add_leaf_card
                except ValueError:
                    pass
```

**Verify:** Generate Ground Cover (weed type): unchanged output.

### A16 — Build Mode right-click: one menu, not two

**File:** `bm_operators.py`

**Why:** RIGHTMOUSE opens the Build Block popup AND passes the event through, so Blender's Object Context Menu opens on top of it (the 'right-click menu collision' in CLAUDE.md).

**old_string (exact):**

```python
        elif key == 'RIGHTMOUSE':
            if bm_data.get_selected(context):
                context.window_manager.popup_menu(
                    WBTK_MT_BuildBlockMenu.draw_items, title="Build Block", icon='MOD_BUILD')
            return {'PASS_THROUGH'}
```

**new_string:**

```python
        elif key == 'RIGHTMOUSE':
            if bm_data.get_selected(context):
                context.window_manager.popup_menu(
                    WBTK_MT_BuildBlockMenu.draw_items, title="Build Block", icon='MOD_BUILD')
                return {'RUNNING_MODAL'}   # consumed: no second (Object Context) menu on top
            return {'PASS_THROUGH'}
```

**Verify:** Right-click a block in Build Mode: only the Build Block menu appears. Right-click empty space: Blender's normal menu.

---

## After all 32 patches — the six viewport checks (Blender 5.1, this repo via the junction, Reload Scripts first)

1. **Preview & Place lands under the cursor.** Foliage → Tree → Preview & Place → click ~10 m from the origin. ✅ CONFIRMED WORKING when the trunk is under the cursor, not at (0,0,0).
2. **Rails are tubes.** Walkways → Straight (Rails = Left) → Generate → orbit to a side view. ✅ when the horizontal rails have thickness (they were flat ribbons).
3. **Face Magnet obeys the panel.** Face Magnet → Surface Offset 0.5 → FACE MAGNET onto any wall. ✅ when the object floats 0.5 m off the face.
4. **Stamps stay on their block.** Build Mode → Add → Attach EAST → select the new block → AC Unit (South). ✅ when it sits on that block's south face.
5. **Hotkeys stay in the viewport.** In Build Mode: move the mouse over the Outliner, press A → nothing happens; over the viewport, Shift+A → Blender's Add menu; Esc → Build Mode exits.
6. **UE scale reads green at 1.0.** UE Pipeline panel shows "✓ metres". Then: Export Footprints → Summon Build Engine (no Outliner trip) → Realize + Export → Outliner: SM_DW_Building_A has a UV map named UVMap.

If any check fails: screenshot, and we diagnose from the screen — no guessing.

## Rollback

`copy <name>.py.bak_audit1 <name>.py` for the affected file, Reload Scripts.

---

## Round 2 — A10c / A10d / A10e (2026-09-05, after the live Summon-on-helper incident)

**Why a second round.** During the smoke test Jermaine clicked Summon Build Engine with a Build Mode block (`WBTK_BM_0001`) active. A10b only falls back to the footprint when the active object is *not a mesh*; a helper block is a mesh, so Buildify tiled 26 instances onto the helper and three kit modules were dragged off the origin. The same run also left Buildify's eleven collections linked at the scene root beside the hidden host, so every module rendered loose next to the building. Both were repaired live in the scene by hand (unlink from root, activate footprint, re-Summon → the clean 44-instance building); these three patches make the operator do that itself.

**Applier:** `python tests/audit_v1_patches_r2.py --check` then `--apply` from the PER_WBTK folder. Backups go to `operators_build_engine.py.bak_audit1_r2` (the round-1 result, so a compile failure restores to *after* round 1, not before it). Round 1 must be in first: A10d's anchor is A10b's output. Validated on a copy of the round-1 tree: all 3 anchors match exactly once, `py_compile` clean, and the result is byte-identical to applying all 35 patches to `f653ff1` in one pass.

**Order:** A10c → A10d → A10e. All three in `operators_build_engine.py` (LF).

### A10c — Summon Build Engine: the target predicate - never WBTK scaffolding, never a kit module

**File:** `operators_build_engine.py`

**Why:** `type == 'MESH'` alone accepts Build Mode blocks, the grid, detail stamps, the live-preview mesh and the SM_DW_* kit modules - all meshes. Live on 2026-09-05 a Summon landed on WBTK_BM_0001 because it was the active object: 26 instances tiled onto a helper block, three kit modules dragged off the origin. One predicate names what a legitimate target is; A10d uses it.

**old_string (exact):**

```python
    return os.path.dirname(os.path.realpath(__file__))


def _get_or_make_collection(name, host):
```

**new_string:**

```python
    return os.path.dirname(os.path.realpath(__file__))


# Meshes Summon must never build on. Build Mode blocks, the grid, detail stamps
# and the live-preview mesh are WBTK's own scaffolding; SM_DW_* are the kit
# modules themselves. All of them are meshes, so `type == 'MESH'` alone accepts
# them - which is how a Summon landed on WBTK_BM_0001 on 2026-09-05: 26 instances
# on a helper block and three kit modules dragged off the origin.
# WBTK_BFY_ is deliberately NOT here: the footprint is the intended target.
_NEVER_TARGET_PREFIXES = ("WBTK_BM_", "WBTK_DTL_", "_WBTK_", "WBTK_Live_Preview", "SM_DW_")


def _is_summon_target(obj):
    """A mesh that is neither WBTK scaffolding nor a kit module."""
    if obj is None or obj.type != 'MESH':
        return False
    return not obj.name.startswith(_NEVER_TARGET_PREFIXES)


def _get_or_make_collection(name, host):
```

**Verify:** py_compile; behaviour is exercised by A10d.

### A10d — Summon Build Engine: refuse scaffolding and kit modules, prefer the footprint

**File:** `operators_build_engine.py`

**Why:** Supersedes A10b's fallback: the footprint is used not only when nothing is active but also when the active mesh is a WBTK helper or a kit module, and the Info bar says WHY the active object was passed over. With no usable footprint either, the operator cancels instead of building on the wrong mesh.

**old_string (exact):**

```python
    def execute(self, context):
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
```

**new_string:**

```python
    def execute(self, context):
        from .operators_buildify import FOOTPRINT_NAME
        target = context.active_object
        if not _is_summon_target(target):
            footprint = bpy.data.objects.get(FOOTPRINT_NAME)
            if _is_summon_target(footprint):
                why = ("No usable mesh active" if target is None or target.type != 'MESH'
                       else "'%s' is WBTK scaffolding or a kit module, not a footprint" % target.name)
                self.report({'INFO'}, "%s - using '%s'." % (why, FOOTPRINT_NAME))
                target = footprint
            else:
                self.report({'ERROR'}, "Select the footprint mesh first "
                                       "(run 'Export Footprints for Buildify' if you have none).")
                return {'CANCELLED'}
```

**Verify:** Select WBTK_BM_0000 (a Build Mode block), click Summon Build Engine: the modifier lands on WBTK_BFY_Footprint and the Info bar says the block was passed over. Select a kit module (SM_DW_*): same. Delete the footprint, select a block, Summon: ERROR, nothing built.

### A10e — Summon Build Engine: the module host is the ONE parent of the Buildify collections

**File:** `operators_build_engine.py`

**Why:** _get_or_make_collection links an existing collection under the hidden host but leaves any scene-root link in place. Appending the `building` node group drags Buildify's own eleven collections in through its socket defaults, linked at the root - measured live 2026-09-05 - so every module rendered loose beside the building as well as hidden under the host. Unlinking them from the root by hand and re-running Summon gave the clean 44-instance building; this makes the operator do that itself.

**old_string (exact):**

```python
    if host is not None and coll.name not in host.children:
        try:
            host.children.link(coll)
        except RuntimeError:
            pass  # already parented somewhere; harmless
    return coll
```

**new_string:**

```python
    if host is not None and coll.name not in host.children:
        try:
            host.children.link(coll)
        except RuntimeError:
            pass  # already parented somewhere; harmless
    if host is not None and coll.name in host.children:
        # The host is the ONE parent. Appending the `building` node group drags
        # Buildify's own collections in through its socket defaults, linked at the
        # scene root - measured 2026-09-05: eleven root-level collections after
        # one Summon, every module rendered loose beside the building as well as
        # hidden under the host. Unlink only once the host link is confirmed, so a
        # collection is never left with no parent at all (a parentless collection
        # is outside the depsgraph and Collection Info reads it as empty).
        for scene in bpy.data.scenes:
            if coll.name in scene.collection.children:
                try:
                    scene.collection.children.unlink(coll)
                except RuntimeError:
                    pass  # linked-library scene; leave it
        for other in bpy.data.collections:
            if other is not host and coll.name in other.children:
                try:
                    other.children.unlink(coll)
                except RuntimeError:
                    pass  # linked-library collection; leave it
    return coll
```

**Verify:** After Summon, the Outliner shows ground_floor_walls (and the other ten) ONLY under DW_BuildEngine_Modules - no second copy at the scene root, no kit modules loose in the scene.

### Round 2 viewport check (Reload Scripts first)

7. **Summon refuses the wrong mesh.** Build Mode ON → click a block so it is active → Summon Build Engine. ✅ CONFIRMED WORKING when the `DW_BuildEngine` modifier is on `WBTK_BFY_Footprint` (Modifier tab, blue wrench, with the footprint selected), the Info bar reads "'WBTK_BM_0000' is WBTK scaffolding or a kit module, not a footprint - using 'WBTK_BFY_Footprint'", and the Outliner shows `ground_floor_walls` only under `DW_BuildEngine_Modules` — no copy at the scene root.

### Round 2 rollback

`copy operators_build_engine.py.bak_audit1_r2 operators_build_engine.py`, Reload Scripts. That restores the round-1 state (A10b in, A10c–e out).
