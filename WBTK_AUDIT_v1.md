# WBTK Audit v1 — is it hitting the bar?

**Date:** 2026-09-05 · **Codebase:** PER_WBTK @ `f653ff1` (v0.13.0, 36 modules + 1 test, 15,311 lines) · **Target:** Blender 5.1 · **Auditor:** Claude (Fable)

---

## 0. The short version

**Verdict: not v1.0 yet — but closer than the sidebar makes it look.**

The code that matters (the Buildify chain: footprint export → Summon Build Engine → Kit Validator → Box UV → Realize + Export) is the best-engineered part of the addon. The tool's *shape* is still the pre-pivot one: 15 panels, ~258 controls, and the primary workflow is 3 buttons hidden between a hotkey mode that hijacks Blender and a legacy panel with 89 knobs.

**Your three questions, answered:**

| Question | Answer |
|---|---|
| Is it truly aiming at the expectation (the pivot)? | **Code: yes. UI: no.** Every commit since Aug 8 is on the pivot; 12 of 15 panels are pre-pivot. |
| Is it easy to use? | **Not yet.** The primary path needs an Outliner trip between buttons, reports to a hidden System Console, and the hotkey mode eats G/S/X/A. |
| Is it hitting the quality bars? | **4 of 11 pass.** See the scorecard. Three bars fail on things nobody has seen yet because they only show up off-origin, off-default, or in Unreal. |

### Scorecard

| # | Quality bar | Grade | One line |
|---|---|---|---|
| 1 | Pivot alignment | **B** | Engine chain is real and measured; sidebar weight is 89 legacy controls vs 3 engine buttons |
| 2 | Primary path works end-to-end | **C** | Export/Summon solid; Realize+Export ships **zero UVs**; detail stamps land at 2× offset |
| 3 | "No lying UI" | **D** | 14 verified dead or disconnected controls (Face Magnet ×2, Wall Style, shrub width/shape, …) |
| 4 | "Butter" (any knob → plausible) | **D** | 2 crash inputs in Block Composer, 12M-vert tree at max sliders, vent frame inverts at min radius |
| 5 | Scale Bible / units | **C** | Defaults are right (3.5 / 1.2 / 2.5 / 4.0); the UE panel's "Fix Scale to 0.01" makes exports **100× too small** |
| 6 | Zero rounded corners | **F → trivial fix** | Both bevel paths use `MITER_ARC` with 2 segments by default; ladder rungs hard-coded ROUND |
| 7 | Stability / crash surface | **B−** | getattr sweeps verified exact; 72/74 operators have no `poll()`; datablock churn inside `update=` callbacks |
| 8 | UE export correctness | **C−** | UVs dropped, UCX boxes visible + parent-inverse bug, scale trap |
| 9 | Tests | **C** | The one suite is excellent; it covers 1 of 74 operators |
| 10 | Ease of use / fatigue | **C−** | 98 props and 9 Build Mode ops with no tooltip; no Esc exit; view hijacked on enter, not restored on exit |
| 11 | Hygiene / docs | **B−** | CLAUDE.md discipline is exemplary; 29% of geometry_buildings.py is dead; "Neo Vesper" ×3 |

### Top findings (all verified — details in §4)

1. **Preview & Place drops everything at the world origin.** The move loop moves `context.selected_objects`; the generators select nothing. Ghost follows the cursor, the building doesn't. *(Confirmed by code; affects Building, Tree, Shrub.)*
2. **"Fix Scale to 0.01" breaks WBTK's own exporters.** Read from the FBX exporter in your 5.1.1 install: `unit_scale = 100 × scale_length`. At 0.01 a 3.5 m storey exports as **3.5 cm**, and every `(m)` field in the sidebar starts showing centimetres. Your live scene is at 1.0 — keep it there.
3. **Realize + Export ships no UVs.** `_harvest` rebuilds the mesh with `from_pydata(verts, [], faces)` — no UV layer is ever created. The kit-UV work (Box Project, Validator's projection check) never reaches Unreal.
4. **Detail stamps land at 2× the block's offset.** `obj.parent = block` with no parent-inverse turns a world position into a local one. Only blocks at (0,0,0) look right.
5. **Every horizontal rail, grate bar and ladder rung is a zero-thickness ribbon.** Live-measured in your Blender: a 2 m X-beam has bbox 2.07 × 0.07 × **0.00**. Posts (Z) and stair rails (angled) are fine.
6. **Face Magnet's two panel controls do nothing.** The operator reads its own `offset`/`align_to_normal`; the panel never pipes the scene props in.
7. **Build Mode's hotkeys hijack Blender window-wide.** No Shift/OSKey check, no viewport check: Shift+A → add block, G → generate, S → stack, X → delete, typing `a` in the Python Console adds a block. No keyboard exit.
8. **The parametric shell carves openings on the inside face** of the front wall in all 11 shape variants, and on every non-RECT −X wall. Sills never line up with windows. Ledges are buried in the wall. *(Sub-audit, numerically verified.)*

### What to do next

**One action:** run `CLAUDE_WBTK_fix_pass_Audit_v1.md` (companion doc, 32 anchored patches, all validated `py_compile`-clean on a copy) in Claude Code, then smoke-test the 6 viewport checks listed at its end. That closes findings 1, 2, 3, 4, 5, 6, 7 and the art-law violation in one sitting.

---

## 1. What I actually did

1. **Read every line** of all 36 modules + the test suite + CLAUDE.md + the two fix-pass records (15,311 lines).
2. **Machine census** (AST): 265 scene props, 74 operators, 15 panels — cross-referenced every `wbtk_*` name against its definition, every `layout.operator()` against a `bl_idname`, every `getattr` default against `properties.py`.
3. **pyflakes + py_compile** on everything.
4. **Three adversarial sub-audits** on the legacy modules (parametric shell · walkways/props/fences/vents · pipes/cables/foliage/scatter), each required to quote line numbers and rate confidence; I spot-checked their headline claims myself.
5. **Live verification in your running Blender 5.1.1** (read-only, nothing linked to your scene): beam flatness, the foliage back-face `ValueError`, the FBX exporter's unit math, `_PropertyDeferred` presence, timer `persistent=False` default, panel registration.
6. **Wrote and validated a patch set** (32 anchors, 17 files touched, 174 changed lines) on a scratch copy: every anchor unique, all files compile, pyflakes delta = one warning *fewer*.

Confidence labels used below: **LIVE** = executed in your Blender · **CONFIRMED** = traced in code with a concrete repro · **PLAUSIBLE** = strong reasoning, not executed.

---

## 2. Is it aiming at the expectation? (pivot alignment)

**Where the work went (git, Aug 8 → Aug 31):** 100% pivot. Footprint export (in-place, tested), floor calibration, edge subdivision, Kit Validator (component-level signed volume — the check that caught 9 inverted components the object-level check missed), Box UV (derived from the 8 reference meshes), Summon Build Engine, Realize + Export.

**Where the UI weight is:**

| Panel | Controls | Buttons | Pivot status |
|---|---|---|---|
| Build Mode | 16 | 22 | **PRIMARY** — but 14 of those 22 buttons are legacy (parametric Generate, 8 detail stamps, mirror, iso…) |
| Structures | **89** | 11 | Superseded by Buildify |
| Foliage | 30 | 9 | Decorator (no BagaPie equivalent — keep) |
| Pipes | 22 | 4 | BagaPie |
| Props | 19 | 6 | Legacy |
| Vents · Cables · Fences · Scatter · Ground · Walkways | 71 | 20 | BagaPie / legacy |
| Global · UE Pipeline · Face Magnet · Utilities | 11 | 7 | Pipeline |

That's **~258 property controls and ~79 buttons across 15 panels**, and the three buttons that make a Dusk Ward building (Export Footprints → Summon → Realize + Export) are split across two panels with a kit-authoring tool (Validate Kit) wedged between the first two.

**What the primary path still doesn't do (by design, but unlabelled):**

- Build Mode's per-wall types (N/S/E/W Door/Window/Solid) and Detail Stamps only feed the *legacy* `bm_generate` path. Buildify decides openings from the kit. A user who sets "Door" on South and hits Summon gets no door — and nothing on screen says so.
- Region DNA (pivot item #2, "kit switcher") is not wired to the engine. `_KIT_MAP` is hard-coded Dusk Ward; the DNA dropdown lives in the legacy Structures panel and only touches parametric props. Honest fix for v1.0: label the button "Summon Build Engine (Dusk Ward)".
- Build Mode's own Generate/preview read roof, slabs, window size, door style, bevel and trim-UV settings from the **Structures** panel (`bm_generate.py:21-30, 54-63`). The primary panel depends on knobs in the closed legacy panel.

---

## 3. The primary path, walked as a user

**CURRENT MISSION for a user:** turn blocks into a Dusk Ward building in Unreal.

| Step | What you do | What happens | Finding |
|---|---|---|---|
| 1 | Enter Build Mode | View snaps to ortho/iso/solid/object-colour — **never restored on exit** | UX |
| 2 | Add / Stack / Attach blocks | Works. Blocks don't snap to the grid you're shown (`bm_data.create` uses the raw cursor) | UX |
| 2b | Press A/S/D/X/G/I/C | Fires **everywhere** (Outliner, Console, Text Editor), also with Shift held; no Esc exit | **F6** |
| 2c | Right-click a block | Build Block menu **and** Blender's Object Context Menu open together | CONFIRMED (`bm_operators.py:109-113`) |
| 2d | Drag Width slider | Each tick destroys and recreates the block's mesh datablock inside the `update=` callback (`bm_data.rebuild_mesh`); that is the trail in your one WBTK crash log | PLAUSIBLE root cause |
| 3 | Add a Detail Stamp | Lands at 2× the block offset unless the block is at the origin | **F4** |
| 4 | Export Footprints for Buildify | Solid. Footprint is **not selected/activated** afterwards | UX |
| 5 | Validate Kit | With nothing selected, scans the whole scene: reports `_WBTK_BM_Grid` "no faces", every block "no UV layer" | CONFIRMED (`operators_kit_validator.py:125-129`) |
| 6 | Summon Build Engine | Needs the footprint *active* → Outliner trip. Report goes to the **System Console** (hidden by default on Windows) | UX |
| 7 | UE Pipeline → "Fix Scale to 0.01" | Panel says 1.0 "✗ Needs fix!" — the fix shrinks your exports 100× | **F2** |
| 8 | Realize + Export Building | One clean mesh, materials by name — **no UVs, no smooth flags, no UCX** | **F3** |
| 9 | Cleanup All Helpers | Deletes the detail stamps too (prefix `WBTK_DTL_`) — they were never part of the building anyway | design gap |

**PROGRESS reading:** steps 4, 6 and 8 are engineered to a high standard. Steps 3, 5, 7, 8-UV and the mode ergonomics are what stand between this and "butter".

---

## 4. Verified findings

Severity: **CRASH** · **WRONG-OUTPUT** · **LYING-UI** · **PERF** · **HYGIENE**. Every entry has a file:line and a repro.

### 4.1 Primary path (Build Mode, Buildify chain, UE export)

| ID | Sev | Where | Defect | Repro | Conf |
|---|---|---|---|---|---|
| F1 | WRONG-OUTPUT | `operators_preview.py:247-248` | `_place_at` moves `context.selected_objects`; `generate_building_shell`/`generate_tree`/`generate_shrub` build at `Vector((0,0,0))` and select nothing; `Utils.bm_to_obj` restores the empty selection (`utils.py:203-208`) | Foliage → Tree → Preview & Place, click 10 m away: tree appears at (0,0,0) | CONFIRMED |
| F2 | WRONG-OUTPUT | `ui.py:831,839`, `operators_ue_pipeline.py:33-41`, `config.py:16` | Panel demands `scale_length == 0.01`; both FBX exporters use `FBX_SCALE_NONE`, which the 5.1.1 exporter implements as `global_matrix *= 100 × scale_length`. At 1.0 → 3.5 m = 350 cm ✓; at 0.01 → 3.5 cm ✗. Also flips all 63 `unit='LENGTH'` props to centimetre display (Ladder Height max becomes 50 cm) | Click Fix Scale → Pipes panel: "Pipe Length 4 cm" | **LIVE** (exporter source) |
| F3 | WRONG-OUTPUT | `operators_ue_pipeline.py:381-428` | `_harvest` collects verts/faces/material names only; `from_pydata` → no `uv_layers`, `use_smooth` all False. FBX has zero UV channels | Realize + Export → check SM_DW_Building_A UV Maps: none | CONFIRMED |
| F4 | WRONG-OUTPUT | `bm_details.py:313, 333` | World-space `obj.location` then `obj.parent = block_obj` without `matrix_parent_inverse` → world = block + (block + local) | Attach a block EAST (x=4), stamp AC Unit on South: sits at x≈9.6 | CONFIRMED |
| F5 | LYING-UI | `ui.py:1103-1108` vs `operators_ue_pipeline.py:147-162` | Panel draws `wbtk_fm_align_normal`, `wbtk_fm_offset`; operator uses only its own `offset`/`align_to_normal`; `op` assigned, never configured | Set offset 0.5 → object still flush | CONFIRMED |
| F5b | PLAUSIBLE | `operators_ue_pipeline.py:199-203, 294-297` | Report says "Use F9 to adjust offset"; `execute()` is a no-op, so an F9 change = undo the snap, re-run nothing → object jumps back | Snap, F9, change offset | PLAUSIBLE |
| F6 | WRONG-OUTPUT | `bm_operators.py:87-120` | Modal ignores `event.shift`/`oskey`, never checks the mouse is over a viewport; window-level handler runs before every editor's keymap | Build Mode on → Shift+A in viewport adds a block; type `a` in Python Console | CONFIRMED |
| F6b | UX | `bm_operators.py:52-59` | Enter forces ortho + iso + SOLID/OBJECT shading; exit restores nothing | Enter, exit → viewport stuck in ortho | CONFIRMED |
| F6c | WRONG-OUTPUT | `bm_operators.py:109-113` | RIGHTMOUSE opens popup **and** returns `PASS_THROUGH` → Blender's context menu opens too (the "right-click collision") | Right-click a block | CONFIRMED |
| F7 | PLAUSIBLE-HIGH | `bm_data.py:101-129` + `properties.py:647-666` | `update=_bm_update` → `rebuild_mesh` → new mesh datablock + `bpy.data.meshes.remove(old)` **inside the property update callback**, per slider tick. Your crash log's trail: `wbtk_bm_width = 8 → DepsgraphNodeBuilder::build_materials`. `bm.to_mesh(obj.data)` in place needs no datablock churn | Drag W with live preview on | PLAUSIBLE |
| F7b | PLAUSIBLE | `bm_data.py:146-156` | `scene['_bm_syncing']` guard set/deleted without try/finally; one failed enum assignment (e.g. stale `PANELED` in an old .blend) leaves the guard stuck → sliders silently stop updating blocks forever | Old-file migration case | PLAUSIBLE |
| F8 | WRONG-OUTPUT | `operators_live_preview.py:32-37, 171` | Timer registered with default `persistent=False` → killed on file load; `_live_state` never reset (no `load_post` handler). Same generator: next click reports "OFF"; different generator: `timer_running` still True → preview **freezes** | Preview on → File > New → toggle | **LIVE** (timer doc) + CONFIRMED |
| F8b | PLAUSIBLE-HIGH | `operators_live_preview.py:195` | `bl_options` has `UNDO` on a stateful toggle; Ctrl+Z reverts scene props/preview object, timer keeps running and recreates it | Toggle on, Ctrl+Z | PLAUSIBLE |
| F9 | LYING-UI | `operators_kit_validator.py:125-129` | Scene fallback validates WBTK helper objects: grid = "no faces" FAIL, blocks/footprint = "no UV layer" | Build Mode → Validate Kit (nothing selected) | CONFIRMED |
| F10 | UX | `operators_buildify.py:383`, `operators_build_engine.py:242-246` | Export leaves selection alone; Summon requires the footprint active; report printed to System Console | Export → Summon = "Select the footprint mesh first" | CONFIRMED |
| F11 | WRONG-OUTPUT | `operators_buildify.py:63-98` vs `bm_generate.py:139-160` | Per-wall types & chamfer perimeter duplicated in two files (flagged in code as "fold later") — fine; but wall types/stamps never reach Buildify and nothing in the panel says so | Set South=Door → Summon: no door | design gap |
| F12 | WRONG-OUTPUT | `bm_generate.py:92`, `operators_structures.py:439`, `properties.py:412-414` | `miter_outer='MITER_ARC'` + default `bevel_segments=2` → rounded corners; art law says zero | Edge Bevel on, generate | CONFIRMED |
| F13 | HYGIENE | `bm_data.py:260, 287` | New `WBTK_BM_GridFill` / `WBTK_BM_GridMat` material every Build Mode entry (known #10) | Enter/exit ×5 → 10 orphan materials | CONFIRMED |
| F14 | HYGIENE | `bm_data.py:77-78` | Block names from `len(blocks)` → after a delete the next block collides and gets `.001` | Add 3, delete #2, add | CONFIRMED |

### 4.2 Parametric shell + Block Composer (sub-audit A, numerically verified against `geometry_footprints`)

| ID | Sev | Where | Defect | Repro |
|---|---|---|---|---|
| P1 | CRASH | `operators_block_composer.py:83` | `rng.randint(min_floors, max_floors)` with Min > Max → `ValueError` | Min Fl 5 / Max Fl 2 |
| P2 | CRASH | `operators_block_composer.py:73` | Same for building width | Min W 6 / Max W 5 |
| P3 | WRONG-OUTPUT | `geometry_buildings.py:153-154, 227-228` | X-axis walls assume +Y is outward; the front wall's outward is −Y in **all 11 shape variants** → door reveal/window inset built on the interior face. At default inset (= wall thickness) it reads as "no reveal"; at 0.5 m the jamb box protrudes into the street | Default shell, Door Inset 0.5 |
| P4 | WRONG-OUTPUT | `geometry_buildings.py:163` | Y-axis left/right test `base_pos_x < thickness/2` is RECT-only; every non-RECT −X wall (L/U/T wings, U courtyard) carves on the inside | T-Shape, Wing Walls = Window |
| P5 | WRONG-OUTPUT | `geometry_buildings.py:437` | `build_angled_wall` normal is inverted for `FRONT_RIGHT` and `BACK_RIGHT` corner cuts | Corner Cut Front-Right + Door |
| P6 | WRONG-OUTPUT | `operators_structures.py:318-326` + `geometry_buildings.py:912-914` | Sills: one shelf per wall, centred, sized from stock `Config.WINDOW_WIDTH` (sill block runs *before* the Config override) — never under a window at AUTO ≥ 2 | 8 m wall, Sills on |
| P7 | WRONG-OUTPUT | `geometry_buildings.py:1214` | Ledge depth measured from the wall centreline (bands/plinth measure from the face) → 0.1 m buried; depth ≤ 0.10 is invisible | Ledge Depth 0.10 |
| P8 | WRONG-OUTPUT | `operators_structures.py:286` | Ledges fire on floor 0 (z = 0 trim ring) while bands correctly skip it | Ledges on, Floors 2 |
| P9 | WRONG-OUTPUT | `operators_block_composer.py:53-62, 152-157` | All four sides pack the full edge → corners double-occupied; at defaults 7 interpenetrating pairs, largest 6×6 m; 2 buildings overhang the block | Defaults, seed 42 |
| P10 | WRONG-OUTPUT | `geometry_buildings.py:26-31`, `utils.py:156-157` | `build_wall_segment` winds 3 of 6 faces inside-out and only the shell path recalcs normals; the "Fix potential invalid normals" comment in `bm_to_obj` sits over two blank lines | Wall Generator + backface culling |
| P11 | WRONG-OUTPUT | `operators_structures.py:55, 65` | Wall Generator has no height guard: Height 1.5 with Window → inverted header box | Wall H 1.5, Window |
| P12 | LYING-UI | `geometry_buildings.py:125-127` | Window Height > 2.5 (at 3.5 floor) → every WINDOW wall silently SOLID | Window H 3.0 |
| P13 | LYING-UI | `operators_structures.py:271, 402` | Parapet silently disabled when Add Roof is off; controls stay live | Roof off, Parapet on |
| P14 | LYING-UI | `ui.py:360` | `wbtk_building_wall_style` drawn, read nowhere (Risk 1) | — |
| P15 | LYING-UI | `operators_preview.py:411-412, 280-334, 482-483` | Parametric preview ignores window width/height/count (hash omits them) and passes no `wing_position` to the roof slab → preview ≠ Generate | Preview vs Generate at defaults: 1 vs 4 windows |
| P16 | WRONG-OUTPUT | `utils.py:33-36` | `create_master` reuses `BuildingShell_master` → second Generate parents `Shell_Walls.001` coincident under the same master (z-fighting, doubled tris) | Generate twice |
| P17 | PERF | `utils.py:173-213` | 6-building row × 7 children = **84 mode switches, 42 smart-projects, 42 depsgraph evals**, and with Trim UVs on all 42 unwraps are immediately overwritten | Building Row, Count 6 |
| P18 | HYGIENE | `geometry_buildings.py:629-1105` | ~370 lines (29%) unreachable: RECT-only enhancement builders superseded by `*_from_perimeter` | — |

### 4.3 Walkways · Props · Fences · Vents · Ground (sub-audit B)

| ID | Sev | Where | Defect | Repro | Conf |
|---|---|---|---|---|---|
| W1 | WRONG-OUTPUT | `geometry_walkways.py:155-160` | `add_beam` extrudes the XY profile *inside* its own plane for X/Y → flat ribbon; every horizontal rail, grate bar, ladder rung | Any walkway with rails | **LIVE** (2.07×0.07×0.00) |
| W2 | CRASH | `operators_props.py:97-102, 194-199` | Barrels call `primitive_cylinder_add` with no `poll()`; in Edit Mode the user's mesh is renamed, reparented, moved to origin | Tab into Edit Mode, Props → Basic | CONFIRMED |
| W3 | CRASH | `operators_props.py:544` | Barrel Pyramid: unguarded `select_all` in Edit Mode → RuntimeError | Same | CONFIRMED |
| W4 | WRONG-OUTPUT | `operators_props.py:118, 129-131` | Basic barrel ribs: subdivision at `rib_count+2`, targets at `rib_count+1` → **never match** for 1–5; 3 rib controls inert | Rib Count 2 | CONFIRMED |
| W5 | WRONG-OUTPUT | `operators_props.py:228-239` | Metal barrel: 2 of 4 targets match, dedupe keeps one edge per ring → bevel on 2 lone edges | Props → Metal | CONFIRMED |
| W6 | WRONG-OUTPUT | `operators_props.py:165-167, 297-298` | UCX computed, *then* mesh moved by h/2 → collider offset 50 %; prop ends half below Z=0 | Basic barrel | CONFIRMED |
| W7 | WRONG-OUTPUT | `utils.py:281-291` | UCX world matrix then `parent = master` without parent-inverse → doubled offset when a master is non-identity (reused master after the user moved it) | Move Bridge_master, generate again | CONFIRMED |
| W8 | WRONG-OUTPUT | `operators_walkways.py:688-706` | Discrete stairs: every face inside-out, no weld | Backface culling on | CONFIRMED |
| W9 | WRONG-OUTPUT | `operators_props.py:44-49` | Crate: 4 of 6 faces inverted → insets bulge outward on 2 sides | Crate, insets on | CONFIRMED |
| W10 | WRONG-OUTPUT | `geometry_walkways.py:249` | `if face.normal.z < 0.9: flip` inverts the default ramp (cos = 0.894) → degenerate rim | Industrial Plate + Ramp defaults | CONFIRMED |
| W11 | WRONG-OUTPUT | `geometry_walkways.py:339` + callers | Duplicate coincident end posts in every walkway type (each with its own UCX) | Straight, len 5 | CONFIRMED |
| W12 | WRONG-OUTPUT | `operators_walkways.py:290, 325` | T-junction plate stamped on top of the main run → coplanar z-fight | T-junction defaults | CONFIRMED |
| W13 | LYING-UI | `operators_walkways.py:396` | "X-Junc Arm Size (Tiles)" sizes the centre plate; arms fixed at 1 | Arm Size 5 → 7×7 not 15×15 | CONFIRMED |
| W14 | LYING-UI | `geometry_walkways.py:239` | Walkway Style GRATE (the Dusk Ward surface) ignored by both stair generators | Style Grate + Stairs | CONFIRMED |
| W15 | LYING-UI | `operators_walkways.py:582, 587` | Ladder rungs hard-coded `'ROUND'` (art law) | Rail Style Square + Ladder | CONFIRMED |
| W16 | LYING-UI | `operators_props.py:156-160, 282-284, 502-504` | Barrels/pyramid bypass `bm_to_obj` → ignore Assign Materials / Auto Unwrap / Add UCX; mesh left in the active collection | Untick globals → Metal barrel | CONFIRMED |
| W17 | LYING-UI | `operators_fences.py:131-133` | "Mesh Divisions" only subdivides a solid quad | 2 vs 50 identical | CONFIRMED |
| W18 | LYING-UI | `ui.py:91` | Endcap box re-draws the Straight props under different labels | Change "Run Length" → Straight Length changes | CONFIRMED |
| W19 | WRONG-OUTPUT | `operators_vents.py:67, 117` | Frame thickness unclamped → inner radius negative at min radius / max frame | Radius 0.05, Frame 0.2 | CONFIRMED |
| W20 | WRONG-OUTPUT | `operators_fences.py:65, 123` | Bottom rail centred on Z=0 (half buried); chain-link panel intersects posts | Defaults | CONFIRMED |
| W21 | HYGIENE | `operators_walkways.py:23-25` | `report_warning` returns `{'FINISHED'}` on validation failure → undo step + F9 panel for nothing (10 call sites) | — | CONFIRMED |

### 4.4 Pipes · Cables · Foliage · Scatter (sub-audit C)

| ID | Sev | Where | Defect | Repro | Conf |
|---|---|---|---|---|---|
| D1 | CRASH | `operators_scatter.py:333` | Unguarded `select_all` with Auto Unwrap off in Edit Mode | F3 → Scatter in Edit Mode | CONFIRMED |
| D2 | WRONG-OUTPUT | `operators_pipes.py:216, 235` | Pipe Run leg 2 starts 0.2 m from the elbow and runs the wrong way (XZ **and** XY) — this, not the flange, is the "bend bug" | Defaults | CONFIRMED |
| D3 | WRONG-OUTPUT | `geometry_pipes.py:169-174` | Elbow up-vector flips at ring 0 → first quad band twisted 90° | Bend XZ | CONFIRMED |
| D4 | WRONG-OUTPUT | `geometry_pipes.py:259-291` | `add_clamp` builds 36 loose verts per clamp, never faced (comment admits it) | Straight pipe defaults → 72 stray verts | CONFIRMED |
| D5 | WRONG-OUTPUT | `geometry_foliage.py:332-337, 620-624, 649-653` | "Back face for double-sided" → `faces.new` raises *face already exists* (same vert set) → swallowed → all leaves/blades single-sided | Any tree | **LIVE** |
| D6 | WRONG-OUTPUT | `geometry_foliage.py:573-575` | Patch radius = `patch_radius^1.5`; Scatter cancels algebraically for any value ≥ 0.01 | Radius 5 → blades at 11.2 m | CONFIRMED |
| D7 | WRONG-OUTPUT | `geometry_pipes.py:458-474` | Dents use the world axis as radial → bundle pipes sheared, not dented | Bundle, Weathered | CONFIRMED |
| D8 | WRONG-OUTPUT | `operators_scatter.py:256-264, 321` | World AABB + single `top_z` → props float at the box apex on any rotated/sloped surface | 30° roof | CONFIRMED |
| D9 | WRONG-OUTPUT | `operators_cables.py:255-256` | Pair = last two in view-layer order; active object ignored; 3 selected → arbitrary pair | Select 3 | CONFIRMED |
| D10 | PERF | `geometry_foliage.py:349, 394` | `branch_count ** branch_levels` unbounded: max sliders = 20,736 tips × 150 = **3.1 M leaf cards (~12 M verts)** then smart-project | Levels 4, Count 12, Density 150 | CONFIRMED |
| D11 | LYING-UI | `geometry_foliage.py:493, 498` | `wbtk_shrub_width` and `wbtk_shrub_leaf_shape` read and discarded | Width 0.1 vs 8 identical | CONFIRMED |
| D12 | LYING-UI | `geometry_pipes.py:506-510` | Corrosion 1.0 = 15 % of faces; "outer only" unimplemented (deletes inner wall/flange faces) | Holes 1.0 | CONFIRMED |
| D13 | LYING-UI | `operators_pipes.py:207` | Pipe Run ignores Axis (hard `'X'`); Length/Radius/Segs drawn under "Straight Pipe" silently drive Run and Bundle | Axis Z + Run | CONFIRMED |
| D14 | HYGIENE | `operators_foliage.py:29-30` | One tree = two orphan masters + leaves parented to trunk | UCX on → 6 objects | CONFIRMED |
| D15 | HYGIENE | `utils.py:294-296` | UCX boxes never hidden — **every** generator, not just cables (known issue is broader than filed) | — | CONFIRMED |

### 4.5 Cross-cutting

| ID | Sev | Where | Defect |
|---|---|---|---|
| X1 | ARCH | `properties.py:26-840, 843-851` | 265 props registered flat on `bpy.types.Scene` → 265 attribute crash surfaces; the entire getattr-sweep saga (Sessions 2/5b/5c/6) is treating the symptom. A single `PointerProperty` to one `PropertyGroup` collapses the surface to **one** attribute. Right call for v1.1, not v1.0 — noted so the sweeps stop being open-ended |
| X2 | HYGIENE | AST census | **72 of 74 operators have no `poll()`** → every one is runnable from F3 in Edit/Pose mode (W2, W3, D1 are the ones that bite) |
| X3 | HYGIENE | AST census | **98 properties have no `description`** (no tooltip); 9 Build Mode operators have neither `bl_description` nor a docstring (delete, duplicate, sync, chamfer, mirror ×2, clear, iso, generate) |
| X4 | HYGIENE | `properties.py:42-43`, `region_dna.py:66, 114, 300-301` | **"Neo Vesper"** ×3 and **"Sangre Neon"** ×3 — canon is *Neo Vespyr* / *Sangre Neón* (user-visible dropdown labels) |
| X5 | HYGIENE | `region_dna.py:297-305`, `properties.py:37-49`; `geometry_foliage.py:230-235`, `properties.py:296-317` | Two enum tables each maintained twice by hand (region list, foliage presets). Currently in sync; nothing keeps them so |
| X6 | HYGIENE | `__init__.py:7, 87-89` | `bl_info["blender"] = (5,0,0)` while the pin (and the keyword-only `set_sharp_from_angle`) is 5.1; "Footprint Painter" heads an empty section; "Custom Builder" mislabels Build Mode |
| X7 | HYGIENE | working tree | **24 of 36 modules are CRLF on disk** despite `.gitattributes` `eol=lf` (git shows clean because it normalises on commit). `git rm -r --cached . && git reset --hard` refreshes the tree |
| X8 | HYGIENE | `operators_preview.py:614` | Unreachable `return bm` after `return build_preview_bm(scene)` |
| X9 | DOC | `CLAUDE.md` | Stale: Live bug #2 (`set_sharp_from_angle`) is **fixed** at both sites; Block Composer tooltip **present**; "slight edge misalignment" is whole buildings inside each other; `wbtk_cable_between_mode` is a legit UI-mode switch (census entry wrong); `wbtk_tr_chunk` at `operators_walkways.py:273` is a comment; "32 .py files" is now 36; header says "Blender 5.0 addon" |

---

## 5. Quality bars — the evidence behind each grade

**Bar 1 — Pivot alignment (B).** `operators_buildify.py` is measured, not guessed (`TOP_LEVEL_RESERVED`, per-EDGE tiling, weld/nudge, `_is_shared`). `operators_build_engine.py` binds the 11 collection sockets and states the honest boundary of what Buildify can place. Grade capped by the sidebar (89 legacy controls vs 3 engine buttons) and by pivot item #2 (Region DNA → kit) not being wired.

**Bar 2 — Primary path (C).** F3 (no UVs) and F4 (stamps) are the two that break the deliverable; F10 (Outliner trip, hidden console) is friction; F11 (wall types don't reach the engine) is an unlabelled expectation gap.

**Bar 3 — No lying UI (D).** Fourteen controls verified dead or disconnected: Face Magnet ×2 (F5), Wall Style (P14), Parapet-without-roof (P13), Window Height > 2.5 (P12), shrub width + leaf shape (D11), ground-cover Scatter (D6), pipe Corrosion (D12), Pipe Run Axis (D13), X-Junc Arm Size (W13), GRATE on stairs (W14), rail style on rungs (W15), chain-link Divisions (W17), barrel ribs ×3 (W4), globals on barrels (W16).

**Bar 4 — Butter (D).** Two crash inputs (P1/P2), one hang (D10), and a handful of in-range positions that invert geometry (P11, W10, W19).

**Bar 5 — Scale Bible (C).** Every default I checked matches the Bible (floor 3.5, door 1.2×2.5, window 1.0, module 4.0×3.5, wall 0.2). F2 is the one real hazard. Minor: Build Mode W/D/H have `step=50` (0.5 m — good) but no `unit='LENGTH'`, unlike the rest.

**Bar 6 — Zero rounded corners (F).** F12 in both generate paths (`MITER_ARC`, default 2 segments), W15 (round rungs regardless of rail style). All three are one-line fixes.

**Bar 7 — Stability (B−).** The sweeps are real: sub-audits machine-checked **96 + 33 + 41 + 30 + 6** getattr defaults — zero mismatches (the only drift is the tree-preview quartet at `operators_preview.py:503-528`, harmless because hash and builder share the same wrong values). Unregister path clean; `_PropertyDeferred` exists in 5.1.1 (LIVE). Debits: X2 (no polls), F7 (datablock churn in update callbacks), F8 (timer/state desync).

**Bar 8 — UE export (C−).** F2, F3, D15 (visible UCX everywhere), W7 (UCX parent-inverse), and no UCX at all on the realized Buildify building.

**Bar 9 — Tests (C).** See §7. One superb suite; 73 operators uncovered.

**Bar 10 — Ease of use (C−).** X3 (tooltips), F6/F6b/F6c (mode ergonomics), F10 (console reports), no Esc, no grid snap, and the view/shading hijack. The good news: the Aug 17 panel move already got Build Mode to index 0 with 2-of-15 open.

**Bar 11 — Hygiene/docs (B−).** CLAUDE.md's "trust nothing undocumented-by-code" discipline is the single best thing in this repo. Debits: P18 (29 % dead), X4–X9.

---

## 6. QOL / UX — the Fable pass

### 6.1 The sidebar: 15 panels → 5

Registration order is display order, so this is a reorganisation, not a rewrite (`bl_parent_id` sub-panels, all legacy ones `DEFAULT_CLOSED`).

```
World Builder
├─ 1 · BUILD                       (open)   the primary path as numbered steps
│    1. Blocks       Enter/Exit · Add · Stack · Attach · grid · selected block
│    2. Engine       Export Footprints → Summon Build Engine (Dusk Ward) → [Realize + Export]
│    3. Preview      Live Preview toggle (kept opt-out)
│    ▸ Legacy generate (closed sub-panel): Generate [G] · Detail Stamps · Mirror · Iso
├─ 2 · KIT                          (closed)  Validate Kit · Box Project UVs · Apply Trim UVs · Send to UE_Export
├─ 3 · SETTINGS                     (closed)  Global Settings + Region DNA + Scene Scale check
├─ 4 · LEGACY GENERATORS            (closed)  Structures · Walkways · Props · Fences · Ground   ("superseded by Buildify")
└─ 5 · DECORATORS                   (closed)  Foliage · Pipes · Cables · Vents · Scatter        ("BagaPie owns pipes/cables/scatter")
```

What this buys: the two things a Dusk Ward building needs (Export → Summon) sit next to each other as steps 2a/2b; Validate Kit stops looking like step 2 of 3; `wbtk.box_project_uvs` (currently **F3-only** — never drawn anywhere) gets a home next to the validator that tells you to run it.

### 6.2 Build Mode ergonomics (all in the patch set except the last two)

1. **Hotkeys only over the viewport, never with Shift/OSKey, Esc exits** (patch A8).
2. **One right-click menu** (A16).
3. **Export selects the footprint; Summon falls back to it by name** (A10/A10b) — no Outliner trip.
4. **Validator ignores WBTK helpers** (A9).
5. **Header text** while in Build Mode (`context.area.header_text_set("BUILD MODE  A add · S stack · … · Esc exit")`) — the viewport itself should say you're in a mode. *(Not patched: 4 lines in `OP_ToggleMode`.)*
6. **Save/restore view + shading on exit** — store `rv3d.view_perspective/rotation/location/distance` and `shading.type/color_type` on enter. *(Not patched: ~12 lines.)*
7. **Snap Add/Attach to the grid step** (`grid_size / grid_subdivs`, default 2 m) so blocks land on the grid you're looking at.
8. **Reports in a popup, not the System Console** — Summon's 6-line report is exactly what `wm.popup_menu` (already used by the validator) is for.

### 6.3 Honesty labels (cheap, high trust)

- "Summon Build Engine **(Dusk Ward kit)**" until Region DNA drives `_KIT_MAP`.
- Under the N/S/E/W wall types: *"Legacy Generate only — Buildify decides openings from the kit."*
- Grey out Parapet when Roof is off (`col_p.enabled = scene.wbtk_building_add_roof`).
- Tooltips on the 98 silent props (the census in the patch-spec appendix lists them) and the 9 Build Mode ops.

### 6.4 Defaults & units

- `unit='LENGTH'` on Build Mode W/D/H for consistency; keep `step=50`.
- Bevel Segments default 1 (A12c); `MITER_SHARP` (A12/A12b).
- `wbtk_branch_levels` max 3, `wbtk_branch_count` max 8 (kills the 12 M-vert hang without touching geometry code).

### 6.5 Decide-for-you calls on the legacy surface

| Module | Call | Why |
|---|---|---|
| Pipe Run (L) | **Hide** for v1.0 | Leg 2 detached + twisted elbow = two rewrites; BagaPie covers it |
| Surface Scatter | **Hide** | AABB placement is wrong on any slope; BagaPie's job |
| Detail Stamps | **Move under "Legacy generate"** | They never reach the engine or the export |
| Structures (parametric shell) | **Keep, closed, labelled legacy** | 5 shapes work; openings face inward (P3–P5) is one helper fix (pass the perimeter normal down) |
| Foliage | **Keep and fix** | Only decorator with no BagaPie equivalent; 3 dead knobs + single-sided cards are cheap |
| Walkways | **Keep after A4** | With real beams it is the strongest legacy family; then delete the duplicate posts |
| Props barrels | **Rewrite as bmesh** | `OP_GenerateBarrelPyramid` is the template already in the file |

---

## 7. Testing — what you liked, and how to get more of it

### 7.1 Why `tests/test_buildify_export.py` is good (name the moves so they can be repeated)

1. **It states the contract first** ("re-running the export must update the geometry in place and change nothing else") and every assertion is derived from that sentence.
2. **Snapshot-diff, not spot checks.** `snapshot()` captures modifiers, inputs, vertex groups, weights, collections, matrix, custom props, mesh name, geo counts, display type — so a regression *anywhere* on the object fails a named line.
3. **It was RED before the fix.** The suite proved it could detect the bug before claiming the fix.
4. **Edge cases are the user's mistakes, not the happy path:** name taken by an Empty, shared mesh, fake-user mesh, non-identity transform, footprint in another scene.
5. **The end-to-end section measures the *other* tool** (Buildify instance counts 32/49/85/122 per storey; renaming the group → 0) — the only assertion that would catch the integration silently dying.
6. **No fallbacks that mask failure** (`instance_count` deliberately refuses to fall back to a vertex count).
7. **Headless, on a copy, never imported by the addon**, exit code = result.

### 7.2 The suite v1.0 needs (six files, same pattern)

| File | Contract under test | Key assertions |
|---|---|---|
| `test_ui_contract.py` | "Every control works or is removed" — **the census as a test** | every drawn `wbtk_*` is read by ≥1 operator; every `layout.operator()` id exists; every prop has a description; every operator has a tooltip; every operator has `poll()`; no `getattr` default disagrees with `properties.py` |
| `test_build_mode.py` | Blocks → footprint geometry | add/stack/attach positions; mirror symmetry; chamfer perimeter == `_block_perimeter`; stamp lands on the face for a block at (10, 5, 0) (F4); `_bm_syncing` guard cleared after a failed enum write (F7b) |
| `test_engine_summon.py` | Footprint → configured modifier | modifier attached once (idempotent on re-run); 11 sockets bound; module 4.0 × 3.5; randomize off; instance count > 0 with the real kit; fallback to `WBTK_BFY_Footprint` when nothing is active |
| `test_ue_export.py` | Realize + FBX round-trip | realized mesh has 1 UV layer with non-degenerate spread (reuse the validator's `_check_uv`); material slots by name; **re-import the FBX into an empty scene and assert `dimensions.z ≈ 3.5 m` at scene scale 1.0** (F2 guard); UCX present |
| `test_preview_place.py` | Ghost position == placed position | for BUILDING/TREE/SHRUB: place at (10, 7, 0) → new root objects within 1e-3 (F1) |
| `test_geometry_invariants.py` | Every generator's output is game-legal | for each `wbtk.generate_*` at defaults: every closed component has **positive signed volume** (reuse `_component_signed_volume`); no object bbox with a zero axis (W1); no duplicate verts within 1e-4 (W11/W8); no orphan datablocks after undo |

A `tests/run_all.bat` that invokes each with `--background --factory-startup` and greps `RESULT: GREEN` turns this into the release gate CLAUDE.md's Session 8 asks for.

---

## 8. Re-planned road to v1.0

The existing Session 6/7/8 plan predates the pivot. Replan around user-visible impact:

| Session | Scope | Closes |
|---|---|---|
| **6a — Fix pass (this doc's patches)** | Run `CLAUDE_WBTK_fix_pass_Audit_v1.md`; 6 viewport checks | F1 F2 F3 F4 F5 F6 F6c F8 F9 F10 F12 W1 D5 P1 P2 X4 X6 |
| **6b — Build Mode behaviour** | In-place mesh rewrite (F7), try/finally guard (F7b), header text, view restore, grid snap, material get-or-create (F13), name allocator (F14), wall-style enum drop + migration | F7 F7b F13 F14 Risk 1 |
| **6c — Kit Slots (the control surface)** | The 11 Buildify slots of `_KIT_MAP` as visible lists under Build Mode (add/remove a module per slot, re-Summon), stacked-block merge (N3), stamp origin convention (N4), wall-variety check (N5). Fork trigger logged, not pulled: Seed + Pillars-off need a socket stock Buildify lacks | N3 N4 N5 the "no control" fatigue |
| **7 — Sidebar restructure + honesty** | §6.1 layout, tooltips ×98 + ×9, honesty labels, `poll()` on all 74 (one base-class mixin), hide Pipe Run/Scatter, stamps under Legacy | X2 X3 D1 W2 W3 |
| **7b — Legacy geometry (optional for v1.0)** | Perimeter-normal helper (P3–P5), sills after override (P6), ledge from face (P7), MITER, walkway duplicate posts, ramp flip threshold, foliage knobs | P3–P8 W8–W12 D6 D11 |
| **8 — Tests + release** | §7.2 suite + run_all.bat; `bl_info` 1.0.0; README with the 3-step flow; LICENSE; changelog from git; CLAUDE.md corrections (X9) | DoD |

**Explicitly deferred to v1.1:** X1 (PropertyGroup migration — do it once the sweeps stop), Region DNA *presets* per district (the switcher's data; the slot UI itself is 6c), UCX for realized buildings, trim-sheet schema.

### 8.1 Logged during the 2026-09-05 live smoke test (Jermaine's Blender 5.1.1, verified on screen)

The fix pass (32 patches, round 1) is applied on the live tree; checks #4 (stamps on their block) and Export → Summon on the footprint (44 instances, measured) are ✅ CONFIRMED. These came out of the same session and are queued, not fixed:

| # | What was seen | Where it lives | Disposition |
|---|---|---|---|
| N1 | Kit Validator reports `WBTK_BM_0001` as inverted normals (−108 signed volume) with no UV | `bm_data.rebuild_mesh` winds all six block faces inward | Real, but only for helper blocks the validator should never judge — see N2. Fix the winding in 6b so the live preview and Generate inherit correct normals |
| N2 | Validator still judges a *selected* helper block | A9 filters helpers only on the scene-wide fallback path | Extend `_HELPER_PREFIXES` filtering to the selection path (one condition) — 6b |
| N3 | A stacked block becomes a **second Buildify building** at z = 3.5: trim ring under the upper block, a second set of corner pillars, a door on storey 2 | `operators_buildify._group_key = (round(z0, 4), floors)` groups by base height | Merge coincident footprints: same outline at z = h → floors += 1 on the block below. This is most of the "weird columns" complaint — 6c |
| N4 | Detail stamps sit 0.2 m off the face (AC unit) or a full depth off (balcony, fire escape, canopy) | `bm_details.place_detail` assumes one mesh-origin convention; the eight builders use three | Ratify one origin (back-face centre) and fix the eight builders — Session 7 as planned |
| N5 | Every wall came out the plain `SM_DW_Wall_400x350_A` although 9 candidates are offered | Either the `SM_DW_BfyWall_*` modules are not in `PER_DW_Kit.blend` yet (Summon's Console line "appended N/M missing kit modules" says), or Buildify's pick | Read the Console line first. If the modules are missing, this is kit authoring, not code |
| N6 | Summon built on the active helper block `WBTK_BM_0001` (26 instances) and left Buildify's 11 collections at the scene root | `type == 'MESH'` accepted a helper; `_get_or_make_collection` kept the root link | **Round 2 patches A10c/A10d/A10e** — written and validated, apply after the six checks |
| N7 | The Build Mode "Shortcuts:" header wears the **Space** keycap icon (`EVENT_SPACEKEY`, `ui.py:260`) although Space does nothing in Build Mode | `ui.py` Build Mode shortcuts box | Cosmetic; swap to `EVENT_A` (the first real shortcut) — Session 7 |
| N8 | Changing a block does not re-export the footprint; Buildify only updates when Export is clicked again | `bm_operators` ↔ `OP_ExportBuildifyFootprints` | Auto-export on block change when a footprint with the modifier exists (no timer — call it from the block operators) — 6b |

**The control question, answered (2026-09-05).** Today the user sets footprint and floors in the panel; WBTK *code* sets module size and the candidate list per slot (`_KIT_MAP`); Buildify decides which candidate lands on which edge (no seed exposed), puts a pillar on every corner, and places trim and roof props. The engine is not the problem — the control WBTK already has is invisible because it lives in a dict. Session 6c makes it a panel. Two knobs stock Buildify cannot give (a Seed for the wall pick; Pillars off — one measured run had an empty pillar collection produce *no* output) are the first legitimate Evolution Clause trigger: a small surgical fork exposing one or two group inputs, never a rewrite, and not before 6c has shown the dict-as-panel is not enough.

---

## 9. What is genuinely good (say it, because it's true)

- **`operators_buildify.py`** — measured calibration constants with the measurement written next to them, per-edge subdivision because Buildify tiles per edge, weld-then-dissolve order documented with *why*, `_is_shared()` after the fake-user trap, and warnings instead of silent relinks. This is the reference quality level for the rest of the addon.
- **`operators_kit_validator.py`** — component-level signed volume (the object-level check let 9 inverted parts through), per-destination rules, a *derived* UV divisor that distinguishes "wrong projection" from "right projection, wrong density".
- **`operators_box_uv.py`** — the convention was measured off 87 faces of 8 reference meshes rather than invented; refuses to overwrite by default; the validator imports its constants so the two cannot drift.
- **`geometry_footprints.py`** — all 11 shape variants CCW, correct outward normals, wall-segment set identical to the perimeter-edge set (sub-audit A machine-checked this). The enhancement families land on the walls for free because of it.
- **The getattr sweeps held under adversarial checking** — 206 defaults compared, zero mismatches. Rare.
- **Deterministic seeding everywhere** (local `random.Random(seed)`, no global state leakage); the foliage preset table is airtight (14 presets, every key/enum/range valid).
- **The Aug 17 UI move** (Build Mode first, 13 panels closed) was the right first cut, done as a verbatim lift with a diff as proof.
- **CLAUDE.md** — the 2026-07-06 audit that caught "sessions recorded as done, not present in code" is exactly the discipline that makes this repo recoverable.

---

## Appendix A — Census numbers (AST, this snapshot)

| Metric | Value |
|---|---|
| Scene properties defined / referenced / never referenced | 265 / 255 / **10** (`wbtk_builder_*` ×6, `wbtk_fp_*` ×4 — Custom Builder & Footprint Painter remnants) |
| Properties without `description` | **98** |
| Operators / with `poll()` / without tooltip | 74 / **2** / 9 |
| Operators reachable only via F3 | `wbtk.box_project_uvs` (real gap); `wbtk.preview_place_building` (legacy alias); walkway ops drawn via helper (fine) |
| Panels / open by default | 15 / 2 |
| `getattr` default mismatches | 25 (all in `operators_preview.py`; 12 are the wall-type `'SOLID'` fallbacks already logged as Live bug #5, 8 are the tree quartet, 4 door dims) |
| Raw `scene.wbtk_*` accesses remaining | foliage 32 · cables 25 · ui 24 · props 22 · block_composer 17 · bm_data 8 · live_preview 8 · bm_operators 3 · 1 each in pipes/structures/walkways (seed writes) |
| Timers / handlers / keymaps | 5 timer sites · **0** handlers · 0 keymaps · 3 modals |
| Files CRLF on disk | 24 / 36 modules (+ the test file is LF) |

## Appendix B — Live verification transcript (your Blender 5.1.1, read-only)

```
blender 5.1.1 · file erat_bodymeshd.blend · scene_scale_length 1.0 METRIC
PER_WBTK enabled, bl_info (0,13,0), 72 wbtk.* operators, 265 wbtk_ scene props, 15 WBTK_PT panels
add_beam bbox (dx,dy,dz):  X → [2.07, 0.07, 0.00]   Y → [0.07, 2.07, 0.00]   Z → [0.07, 0.07, 2.0]
add_beam_angled X         → [2.00, 0.07, 0.07]
faces.new(reversed winding) → ValueError: faces.new(...): face already exists   (1 face, not 2)
io_scene_fbx.units_blender_to_fbx_factor = 100.0 * scene.unit_settings.scale_length
save_single: FBX_SCALE_NONE → global_matrix = Scale(unit_scale * global_scale) ; unit_scale = 1.0
bpy.props._PropertyDeferred: present     bpy.app.timers.register(..., persistent=False) default
bpy.ops.export_scene.fbx: present (legacy exporter available; wm.fbx_export absent)
```

## Appendix C — Corrections to carry into CLAUDE.md

1. Live bug #2 → **CLOSED** (both sites keyword form, `63582b9`).
2. "Verify Block Composer tooltip presence" → present (`operators_block_composer.py:17`).
3. Known limitation "slight edge misalignment" → rewrite as P9.
4. Unguarded-writes table: `wbtk_cable_between_mode` is a UI-mode switch, not dead; `wbtk_tr_chunk` is a comment.
5. Pipe "flange orientation" → re-file as D2 + D3.
6. "UCX visible for cables" → all generators (D15).
7. Header "Blender 5.0 addon" → 5.1; "32 .py files" → 36.
8. `set_sharp_from_angle` line refs: `operators_props.py:277`, `operators_structures.py:164` (unchanged).
