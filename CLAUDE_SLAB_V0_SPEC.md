# Slab v0 — the bridge proof (SPEC, PROPOSED)

**Status:** APPROVED 2026-11-08 ("YEs for all three"). Proposed by Cowork 2026-11-06. Nothing built yet; ready for Code. All five questions ruled (bottom).
**Ruling it serves:** 11-06 "Replace the pivot with the two homes" (`_gamedocs/NOW.md`).
**Sources:** `WBTK_TALK_NOTES.md` part 7 · `CLAUDE.md` (SUPERSEDED banner, Build Mode architecture) ·
`_gamedocs/MODULAR_KITS_TRIM_SHEETS_v2.md` §2 (module grammar 400×350, naming) ·
`_gamedocs/DW_KIT_UE_IMPORT_v1.md` (export settings, pivot audit) · `config.py` · `bm_generate.py`.

---

## 0. What this proves, in one line

One wall slab leaves Build Mode with its joints stamped as `SOCKET_` empties, arrives in Unreal
with those joints as static-mesh sockets, and a second copy lands on the first **by its joint**
with no gap, no overlap and no turn. If that holds, the joint road holds.

**In scope:** a slab maker inside Build Mode, a slab exporter, one Blender-side check, one
Unreal-side check.
**Out of scope:** any Unreal-side WBTK tool, the stretch gesture, drag-up, room tags, pipes,
signs, walkways, Region DNA, landmarks, corners, open-end joint guessing, trim UVs, materials.

---

## 1. What a slab is

| | value | where it comes from |
|---|---|---|
| width (X) | **400 cm** — one bay | census main wall module 400×350 (`MODULAR_KITS_TRIM_SHEETS_v2.md` §2); also Build Mode's default block width |
| height (Z) | **350 cm** — one storey | Scale Bible, `Config.DEFAULT_WALL_HEIGHT = 3.5` |
| thickness (Y) | **20 cm** | `Config.WALL_THICKNESS = 0.2` |
| floor / roof plate | **none** — wall plane only | RULED 11-08 (Q1). Floors become their own piece later, snapped to `U` |
| authored units | 1 Blender unit = 1 m, scene scale 1.0 | `WBTK_OT_CheckUEScale`; FBX export multiplies by 100 into UE cm |

**Facing.** The exterior (street) face points **−Y** in Blender, so Front view (Numpad 1) looks
at the street side. The back (interior) face sits on **Y = 0**. Geometry spans
X 0 → 4.0, Y −0.2 → 0, Z 0 → 3.5.

**Origin.** **Back-bottom-left**: X = left end (as seen from the street), Y = back face,
Z = bottom. This is the Scale Bible's back-bottom-left law. The origin is also the left joint,
which is what lets stock Unreal snap the slab by its joint (§4). RULED 11-08 (Q2). The Dusk Ward kit
walls stay X-centred (`DW_KIT_UE_IMPORT_v1.md` §7), untouched; the 200 cm handle offset between
the two only matters if one is placed by typed coordinates beside the other.

**Joints (three `SOCKET_` empties, children of the slab mesh):**

| empty in Blender | position (m, slab-local) | UE socket name (expected) | job |
|---|---|---|---|
| `SOCKET_L` | (0, 0, 0) | `L` | the grab point: where this slab attaches to a neighbour |
| `SOCKET_R` | (4.0, 0, 0) | `R` | the drop spot: where the next slab's `L` lands |
| `SOCKET_U` | (0, 0, 3.5) | `U` | the storey above (for the later drag-up). **Stamped and checked for arrival only; not snapped in v0** |

All three: rotation (0, 0, 0), scale 1, empty type Plain Axes, display size 0.25. Parent = the
slab mesh object, parent inverse = identity (so the local position above is the real offset).
Joints sit on the **back-face line** at the bottom, so `L` = origin exactly.

Why WBTK picks the grab point and you pick the drop spot: talk part 4, "he picks the drop spot,
WBTK picks the grab point". `L` is the grab point baked into the piece.

**Name:** `SM_DW_WallSlab_<Type>_400x350_A` (naming standard `SM_[Region]_[Type]_[DimCm]_[Variant]`).
`WallSlab`, not `Slab`, because WBTK already uses "slab" for floor and roof plates
(`add_polygon_slab`, `wbtk_building_add_floor_slabs`). `DW` because Dusk Ward is the first kit;
Region DNA picks region codes later.

---

## 2. Build Mode: first click and generate

**First click = wall type.** One dropdown: **SOLID · WINDOW · DOOR** (the three types Build Mode
already knows). The type is the piece's identity, not a setting on one face of a building.

**Generate = one slab.** Not a building, not blocks cut into pieces. It produces:

1. One mesh object `SM_DW_WallSlab_<Type>_400x350_A` in a collection `WBTK_Slabs`, origin as §1.
   Re-running Generate for the same type replaces it (same name, old mesh data removed).
2. The wall face built by the **existing** wall code, so openings match today's buildings:
   - SOLID: plain wall.
   - WINDOW: today's rhythm rule, `n = int(4.0 / (1.0 + 0.8)) = 2` windows, each 100×100 centred
     in its 200 cm half, sill at 100 cm. Window centres at X = 100 and 300 cm.
   - DOOR: one centred door, 120×250 (Scale Bible), current door style settings.
   - Call: `bm_generate._build_face_wall(bm, GB, 0.0, -0.1, 0.0, 4.0, 3.5, 0.2, 'X', wtype, ...)`.
     `build_shell_wall` centres thickness on its Y argument, so Y = −0.1 puts the back face on 0
     and the front on −0.2. (Code must confirm the face direction in the viewport, per STOP rule.)
3. The three `SOCKET_` empties of §1, parented.
4. Material slot `WBTK_Wall` (placeholder, as today). No UVs, no bevel (art law: no rounded corners anyway).

**Export Slab** (separate button) writes `<blend folder>/UE_Export/WBTK_Slabs/<name>.fbx`.
It selects the slab **and its three empties**, then uses the project's ratified settings
(`operators_ue_pipeline.py:533`):
`use_selection=True, object_types={'MESH','EMPTY'}, apply_scale_options='FBX_SCALE_NONE',
bake_space_transform=True, mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False,
use_metadata=False`, no `path_mode`.

> The existing Buildify exporter selects only the mesh, so its empties would be left behind.
> That is why the slab gets its own export step.

**Known risk:** `bake_space_transform` is marked experimental in Blender's FBX exporter and is
the most likely thing to move or turn the empties. The Blender check in §3 catches that before
Unreal is opened. If it fails, the only knob the build may turn is `bake_space_transform=False`,
re-measured. Anything beyond that is a STOP.

---

## 3. How the joints travel, and the Blender-side check

Road: Blender empty named `SOCKET_<x>`, child of the mesh → FBX node child of the mesh node →
Unreal static-mesh import turns `SOCKET_`-prefixed child nodes into sockets named `<x>`.

**Gate B (Blender, headless, before Unreal):** `tests/test_slab_v0.py`, run with
`blender -b --factory-startup --python tests/test_slab_v0.py`:

1. Generate a WINDOW slab. Assert bounds X 0..4.0, Y −0.2..0, Z 0..3.5 (±0.0005 m), origin (0,0,0).
   **RULED 11-10 "Keep it, 21 cm":** measured, the existing wall code's window glass is a 1 cm box
   proud of the street face (same as today's Build Mode south walls), so the WINDOW slab is
   Y −0.21..0. Kept; SOLID and DOOR are exactly −0.2..0.
2. Assert three empties, each parented to the slab, at the §1 positions (±0.0005 m), rotation 0.
3. Export Slab. Open a fresh empty scene, import the FBX with Blender's importer.
4. Assert the same three empties came back as children of the mesh, same positions (±0.0005 m),
   rotation within 0.01°.

Gate B passing means Blender wrote the joints correctly. It does not prove Unreal reads them.

---

## 4. The Unreal side: import, snap, measure

**Where:** new folder `/Game/ER_Test/WBTK_SlabV0/` and new level `/Game/ER_Test/L_SlabV0_Proof`.
If the level gets a DirectionalLight, it is **Movable** (technical law, Lighting).

**Import:** drag `SM_DW_WallSlab_Window_400x350_A.fbx` into `/Game/ER_Test/WBTK_SlabV0/`.
Socket import ON (5.8's Interchange dialog label to be read off the screen; if no socket option
exists and the sockets don't arrive → STOP, screenshot). Nanite ON, materials not imported,
simple box collision (same as the DW kit sheet §2).

**Gate U1 — sockets arrived.** Open the mesh, Window › Socket Manager:

- three sockets, named `L`, `R`, `U` (if UE keeps `SOCKET_L` etc., record the real names and use them)
- `L` at (0, 0, 0) · `R` at (400, 0, 0) · `U` at (0, 0, 350), in cm, ±0.05. A Y sign flip on
  the mesh is fine as long as all three agree with the mesh.
- every socket rotation (0, 0, 0) ±0.01°, scale 1.
- mesh bounds 400 × 20 × 350 cm. **For the Window slab, 400 × 21 × 350** (ruled 11-10, §3).

**The snap — stock Unreal only, no tool.** Place slab A at the world origin. Place slab B
anywhere. Attach B to A at socket `R` with **Snap to Target** for location, rotation and scale.
Because B's origin is B's `L` joint, this puts B's grab point on A's drop spot. This is the
built-in attach-to-socket, the same thing the right-click › Attach To › socket menu does.

Code runs it through the UE MCP (port 3000) or the Output Log's Python, as one script that
snaps **and** measures. Sketch (API names must be checked against 5.8 before running; STOP if any
differ):

```python
import unreal
eas  = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mesh = unreal.load_asset('/Game/ER_Test/WBTK_SlabV0/SM_DW_WallSlab_Window_400x350_A')
a = eas.spawn_actor_from_object(mesh, unreal.Vector(0, 0, 0))
b = eas.spawn_actor_from_object(mesh, unreal.Vector(1000, 1000, 0), unreal.Rotator(0, 0, 37))
R = unreal.AttachmentRule.SNAP_TO_TARGET
b.attach_to_actor(a, 'R', R, R, R, False)

ca, cb = a.static_mesh_component, b.static_mesh_component
drop = ca.get_socket_location('R');  grab = cb.get_socket_location('L')
gap_cm   = (drop - grab).length()
turn_deg = abs((a.get_actor_rotation() - b.get_actor_rotation()).yaw)   # plus pitch, roll
ab, bb   = a.get_actor_bounds(False), b.get_actor_bounds(False)       # origin, extent
seam_cm  = (bb[0].x - bb[1].x) - (ab[0].x + ab[1].x)                  # B min X minus A max X
print('gap', gap_cm, 'turn', turn_deg, 'seam', seam_cm)
```

B starts at a random spot and a 37° turn on purpose: if B ends up right, the snap put it there,
not the starting position.

**Gate U2 — the numbers:**

| measure | pass |
|---|---|
| `gap` — A's `R` to B's `L`, world space | ≤ 0.05 cm |
| `turn` — A vs B rotation, each axis | ≤ 0.01° |
| `seam` — B's left face minus A's right face | 0 ± 0.05 cm (negative = overlap, positive = gap) |
| front faces flush — bounds Y min/max equal | ± 0.05 cm |
| bottoms equal — bounds Z min | ± 0.05 cm |
| window beat across the seam — centres at 100, 300, 500, 700 cm | each ± 0.05 cm |

---

## 5. Acceptance: what you see

**Pass — you see:**

1. In the Socket Manager: three dots on the slab, at its bottom-left, bottom-right and top-left
   corners of the back face.
2. In the viewport, at the canon camera (arm 1800, pitch −12, FOV 45) and up close: **one
   800 cm wall** with four windows on an even beat. You cannot tell where one slab ends from
   the front, only from the mesh outline in wireframe.
3. In the Output Log: the Gate U2 numbers, all inside the pass column.

**Fail — what a broken road looks like, and what it points at:**

| you see | what broke |
|---|---|
| no sockets in the Socket Manager | the road itself: export didn't write them, or 5.8's import drops them |
| sockets at 4 cm / 40,000 cm instead of 400 | unit scale on the empties |
| sockets turned 90° (B lands standing up or sideways) | axis conversion on the empties (`bake_space_transform`) |
| B lands 400 cm too far, or sitting inside A | the origin isn't the `L` joint |
| B faces the other way (back to the street) | facing or socket rotation |
| a visible gap or overlap at the seam, or the window beat breaks | socket position off; read `gap` and `seam` |
| B still at its starting spot | the attach didn't happen; not a joint result |

A fail is still a result. Record the numbers, the screenshot and which row, and stop. No fix
attempts beyond the one `bake_space_transform` knob in §2.

---

## 6. What this touches in today's WBTK, and what it leaves alone

**Touches (all additive):**

| file | change |
|---|---|
| `bm_slab.py` (new) | slab geometry (calls `bm_generate._build_face_wall`, read-only use), socket stamping, two operators: `wbtk.bm_generate_slab`, `wbtk.bm_export_slab`; `_classes` list per bm_* convention |
| `properties.py` | one new scene enum `wbtk_slab_wall_type` (SOLID / WINDOW / DOOR, default WINDOW). Not the existing `wbtk_wall_type`, which belongs to the parametric generator |
| `config.py` | `SLAB_BAY_WIDTH = 4.0 * SCALE`, `SLAB_COLLECTION = "WBTK_Slabs"` |
| `ui.py` | a "Slab v0" box at the top of `WBTK_PT_BuildMode`: wall-type dropdown, Generate Slab, Export Slab. Visible with or without Build Mode on |
| `__init__.py` | import `bm_slab`, add `*bm_slab._classes`; `bl_info` version bump |
| `tests/test_slab_v0.py` (new) | Gate B |
| `CLAUDE.md` | one line under Build Mode architecture pointing to this spec, after the proof passes |

**Leaves alone:** the block flow (Add / Stack / Attach blocks, per-wall types, chamfers, the
existing Generate), `bm_data.py`, `bm_generate.py` (imported, not edited), `bm_details.py`,
`bm_operators.py`, Buildify ops and `WBTK_OT_ExportBuildifyToUE`, Kit Validator, Region DNA,
walkways, pipes, cables, foliage, the parametric generator, Block Composer, the Dusk Ward kit and
its FBXs and pivots, `RPGUIToolkit` (no C++), CHARTA.

---

## 7. Order for the build (when asked)

1. **Branch.** RULED 11-07 ("new branch") and 11-08 (Q5). `Blender_Plugins/PER_WBTK/` is its own git repo
   (`soulfeast82/PER_WBTK`, `master`); the game repo ignores it (`.gitignore:97`), so `bodykit-v1` / `ue5-game`
   are not involved. Order:
   a. **Smoke test first (his rule: smoke test, then commit).** WBTK `master` holds the uncommitted Audit v1 fix
      pass (18 files, +212/−43, rounds 1 and 2 applied 2026-09-05). Its own spec,
      `CLAUDE_WBTK_fix_pass_Audit_v1.md`, ends with 7 viewport checks (6 after round 1, line 1069; #7 after
      round 2, line 1229). Jermaine runs them with Code guiding, Reload Scripts first. About 20 minutes.
      Any fail → screenshot, STOP, diagnose; that fix lands on `master` before step b.
   b. Commit on `master` as that spec's rule 6 says: one commit per section (A1–A4 / A5–A6 / A7–A8 / A9–A16),
      plus round 2 (A10c–e) and the audit docs (`WBTK_AUDIT_v1.md`, `CLAUDE_WBTK_fix_pass_Audit_v1.md`,
      `tests/audit_v1_patches*.py`). The 14 added lines in `CLAUDE.md` include the 11-06 SUPERSEDED banner;
      commit them with the docs. `*.bak_audit1*` files stay uncommitted (backups).
   c. `git switch -c wbtk-slab-v0`. First commit on it: this spec, `WBTK_TALK_NOTES.md`, `talk_refs/`.
2. Backups `*_BACKUP_v1.py` of every file in §6 that already exists.
3. `bm_slab.py` + property + config + UI + registration. `py_compile` all.
4. Gate B green.
5. Jermaine looks at the slab in Blender (Object Mode, Front view): street face toward camera,
   three empties at the corners.
6. Unreal import → Gate U1 → snap script → Gate U2 → canon-camera screenshot.
7. Hand back: numbers, screenshots, the socket names UE actually used, any 5.8 API differences,
   and a NOW.md line.

Rough time: Blender side 2–3 hours of Code work; Unreal side 45–60 minutes including import.

---

## Questions for Jermaine — all ruled

1. Floor plate — **RULED 11-08: wall only.**
2. Origin — **RULED 11-08: back-bottom-left; DW kit untouched.**
3. Old block flow stays beside the Slab box until after the proof — **RULED 11-07: "Yes".**
4. Branch — **RULED 11-07: "Let's go with the new branch"** → `wbtk-slab-v0` in the WBTK repo.
5. Commit the Audit v1 fix pass to `master` first, then cut the branch — **RULED 11-08: yes**, after its smoke test (§7 step 1a).
