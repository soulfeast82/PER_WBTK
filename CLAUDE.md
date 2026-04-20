# WBTK — World Building Toolkit

Blender 5.0 addon for procedural building and city generation.
Currently **v0.13.0**, targeting **v1.0.0 stabilization release**.

Author: Jermaine Dawson Peterson
Location in Blender: View3D > Sidebar > World Builder

---

## What v1.0.0 is

**A stabilization release, not a feature release.**

v1.0.0 ships what exists in v0.13.0, made solid and documented. Build Mode is
the primary authoring workflow. The parametric shape generator and Block
Composer continue to ship as alternates. Feature work in the Queued list
(drag handles, face click cycling, auto-setback preview, detail
randomization, Street Painter) is deferred to v1.1+.

The shape of this release is driven by three real risks found during
scoping — wall style stubs exposed to users, 299 unguarded scene property
reads that can crash during register/unregister/scene-load, and an
incomplete unregister path that orphans helper objects. Those three risks
determine the session order: stability work comes first, behavioral polish
second, documentation last.

---

## The authoring modes (priority order)

**1. Build Mode — PRIMARY.** The `bm_*` module family. Users toggle Build
Mode on, add/stack/attach blocks, set per-wall types and per-corner chamfers,
then place detail stamps (AC units, vents, pipes, balconies, fire escapes,
signs, antennas, canopies) on selected block faces, then generate the
building. Clean layer separation: data, operators, generation, details.

**2. Parametric Shape Generator — SECONDARY.** The original
`OP_GenerateBuildingShell` path. Users set shape (RECT, CORNER_CUT, L_SHAPE,
U_SHAPE, T_SHAPE), enhancements (parapet, plinth, corner columns, bands,
ledges, sills), and generate from parameters. Still useful for quick standard
buildings without painting blocks.

**3. Block Composer — TERTIARY.** City block generator that packs buildings
around a rectangular block perimeter. Still registered, still in the UI.
Known rotation issue on non-rect shapes documented, no new work planned.
Tooltip already present on `OP_GenerateCityBlock`.

**Removed in v0.11.0, confirmed absent in v0.13.0:** the old Custom Builder
viewport modal painter and the Footprint Painter grid UI. Their geometry
helpers (`geometry_footprints.py`) are still used by the parametric shape
generator — keep the file, it is not dead code.

---

## Build Mode architecture (primary path)

```
bm_data.py       — Block CRUD, adjacency, grid, sync. Pure library, no operators.
bm_operators.py  — All user actions. Delegates to bm_data and bm_generate.
bm_generate.py   — Blocks → BMesh. Preview build + full generation. Pure library.
bm_details.py    — Detail stamps: types, geometry, placement, operators.
```

Only `bm_operators` and `bm_details` register classes (via `_classes`
tuples). `bm_data` and `bm_generate` are pure library modules with no
registrations.

### Block data model

```python
DEFAULT_BLOCK = {
    "w": 4.0, "d": 4.0, "h": 3.0,
    "walls": {"north": "SOLID", "south": "SOLID", "east": "SOLID", "west": "SOLID"},
    "chamfers": [],
    "chamfer_size": 1.0,
}
```

Per-wall types and per-corner chamfers are first-class in the data model.
Both were features originally deferred to v1.1; they are present in v0.13.0.

### Build Mode operators

`bm_operators.py`: Toggle Mode, Add Block, Stack Block, Attach Block,
Delete Block, Duplicate Block, Sync From Block, Toggle Chamfer, Mirror X,
Mirror Y, Clear All, Iso View, Generate. Plus menu `WBTK_MT_BuildBlockMenu`.

`bm_details.py`: Add Detail, Clear Details. Eight detail types:
AC_UNIT, VENT, PIPE_CLUSTER, BALCONY, FIRE_ESCAPE, SIGN_MOUNT, ANTENNA,
CANOPY.

### Build Mode scene properties

`wbtk_bm_active`, `wbtk_bm_width`, `wbtk_bm_depth`, `wbtk_bm_height`,
`wbtk_bm_wall_north/south/east/west`, `wbtk_bm_chamfer_size`,
`wbtk_bm_attach_dir`, `wbtk_bm_auto_setback`, `wbtk_bm_grid_size`,
`wbtk_bm_grid_subdivs`, `wbtk_bm_block_color`, `wbtk_bm_detail_face`,
`wbtk_bm_detail_offset_x`, `wbtk_bm_detail_offset_z`, `wbtk_bm_detail_scale`.

---

## Conventions I use

- **Property reads:** `getattr(scene, 'prop', default)` — never assume scene
  props exist. v1.0 stability sweep is migrating **299 direct
  `scene.wbtk_*` reads** across 15 files to this pattern. This is a
  stability issue, not style: direct attribute access is the classic
  Blender addon crash path during register/unregister ordering, scene
  switching, or loading a `.blend` saved before a property existed.
- **Shared geometry methods** live on `GeometryBuildings` class. Do not
  duplicate into operators.
- **BMesh conversion** for the parametric path goes through `_finalize_bm`
  (static method on `OP_GenerateBuildingShell`).
- **Build Mode helper objects** use prefixes: `WBTK_BM_` for blocks,
  `WBTK_DTL_` for details, `_WBTK_BM_Grid` / `_WBTK_BM_GridFill` for grid.
- **Operators register via tuples:**
  - Legacy modules use `_classes_to_register`
  - The `bm_*` modules that register classes (`bm_operators`, `bm_details`)
    use `_classes`. `bm_data` and `bm_generate` do not register anything.
- **Operators report results via** `self.report({'INFO'|'WARNING'|'ERROR'}, …)`.
  `print()` is for diagnostic errors and warnings, not user messages.
- **Every operator has a tooltip docstring** as the class docstring.

---

## How I work

- **Systems-first thinker.** Strong on macro structure, less natural on
  line-level detail.
- **Prefer complete files** over diffs when changes are substantial. For
  small edits (one function, one property), a clearly marked diff is fine.
- **Keep it real with me.** If an approach is wrong, say so and why. If the
  codebase disagrees with what I've told you in this file, tell me — the
  code is ground truth.
- **Voice-dumped fragments from phone** are common. When a prompt is
  fragmented or ambiguous, **ask clarifying questions before assuming**.
  Don't silently fill gaps in a precision-mode session.
- **Before large changes, restate what you understand I'm asking for as a
  short spec** — goal, what to preserve, deliverable format. Wait for my
  confirmation before editing files.
- **One thing per session.** "Polish Build Mode" is a scope. "Fix the
  stack-block Z calculation when attaching to a chamfered face" is a session.
- Opus 4.7 — literal instruction following is expected. State preferences
  explicitly; don't rely on the model inferring from past context.

---

## The three shipping risks (driving the roadmap order)

**Risk 1 — Stub wall styles exposed to users.** PANELED/RIBBED/TILED are
selectable in the UI (`properties.py:113-117`) and produce nothing or
garbage geometry. This is a shipping defect, not a cleanup item.
**Resolution:** drop the values from the enum entirely for v1.0. Add a
one-time migration handler to silently coerce loaded `.blend` files with
stale values back to FLAT. If/when wall styles ship (v1.2 per roadmap),
the enum options get added back with their implementations, not before.

**Risk 2 — 299 unguarded `scene.wbtk_*` reads across 32 files.** Classic
Blender crash path during register/unregister ordering, scene switching,
or loading a `.blend` saved before a property existed. The `bm_*` modules
— the primary authoring path — are among the offenders (16 reads in
`bm_data.py`, 13 in `bm_operators.py`). Any one of those can throw
AttributeError under the wrong load order. **This is a stability sweep,
not a style sweep.** It ships in two sessions (primary path first, legacy
second) so regressions are scoped.

**Risk 3 — Incomplete unregister path.** `register()` gathers classes from
multiple modules; `unregister()` only calls `operators_live_preview.cleanup()`.
No cleanup for orphaned `WBTK_BM_*` blocks, `WBTK_DTL_*` details,
`_WBTK_BM_Grid`, `_WBTK_BM_GridFill`. If a user disables the addon mid
Build-Mode-session, orphaned objects stay in the scene with no way to
clean them up. **This risk compounds Risks 1 and 2**: a user's instinct
when they hit a crash or broken output is to disable and re-enable the
addon, which is exactly the action that makes Risk 3 worst. The
"Cleanup All Helpers" operator is therefore not polish; it is the safety
net for the other two risks.

---

## In scope for v1.0.0

### Primary path: Build Mode

- Toggle Mode enters and exits cleanly (no orphaned grid, no stuck state)
- Add / Stack / Attach / Delete / Duplicate all work without crash on
  reasonable block counts (tested up to ~50 blocks)
- Sync From Block correctly updates UI props from selected block's data
- Toggle Chamfer respects per-corner state and visually updates
- Mirror X / Mirror Y produce correct output (verify with asymmetric block
  sets)
- Clear All removes blocks, details, and resets mode cleanly
- Generate produces building geometry matching the preview
- Preview stays in sync during block edits (live preview timer still firing)
- Detail stamps place correctly on selected block face with correct
  orientation, scale, and offsets across all 8 detail types
- Details are parented to blocks and survive block delete gracefully (either
  deleted with the block or explicitly re-parented)

### Secondary path: Parametric Shape Generator

- All 5 shapes (RECT, CORNER_CUT, L_SHAPE, U_SHAPE, T_SHAPE) + all 6
  enhancements working end-to-end
- Non-rectangular footprints stable
- WINDOW/DOOR on angled walls stable
- Wall style property reduced to FLAT only
- No new work — stability only

### Tertiary path: Block Composer

- Generates city blocks without crashing
- Known rotation alignment issue on non-rect shapes documented
- No new work

### Stability sweeps (driven by Risks 2 and 3)

- **`getattr` sweep for `bm_*` modules** — migrate 29 direct reads in
  `bm_data.py` and `bm_operators.py`
- **`getattr` sweep for top legacy offenders** — `operators_pipes` (42),
  `operators_structures` (37), `operators_walkways` (33),
  `operators_foliage` (32), `operators_cables` (25)
- **`getattr` sweep for remaining files** — `ui.py` (24), plus every
  remaining file with any direct reads
- **Unregister audit** — confirm every registered class is unregistered,
  every timer stopped, every handler removed
- **"Cleanup All Helpers" operator** — user-facing escape hatch that
  removes all objects with `WBTK_BM_*`, `WBTK_DTL_*`, `_WBTK_*` prefixes
  and clears orphaned collections

### Cleanup items (cheap, user-facing)

- Fix misleading comments in `__init__.py` lines 77–79 (Footprint Painter
  and Custom Builder comments remain after imports were removed)
- Verify Block Composer tooltip is present and readable

### Release essentials

- `bl_info` version → `(1, 0, 0)`
- `doc_url` populated
- `README.md` covering:
  - Install instructions
  - Build Mode as the primary workflow (with one screenshot or GIF of the
    block → detail → generate flow)
  - Parametric Shape Generator and Block Composer as alternates
  - Detail stamps showcase (the 8 types with visuals)
  - Known limitations section
- `LICENSE` file

---

## Explicitly OUT of scope for v1.0.0 (deferred to v1.1+)

From the handoff Queued list:

- **Drag handles** — viewport face dragging for block resize
- **Face click cycling** — click face in viewport to cycle wall type
- **Auto-setback preview** — visual indicator of setback amount
- **Detail randomization** — scatter details with randomized positions
- **Street Painter (Phase 4)** — Grease Pencil stroke → city generation

From the prior roadmap, still deferred:

- **Explode Building operator**
- **Wall style geometry** (PANELED, RIBBED, TILED implementations) — v1.2.
  For v1.0, the enum values are removed, not merely hidden.
- **Batch Row Generator** passing `building_shape`
- **Block Composer rotation alignment** fix
- **Wear Layer** (vertex color from geometry analysis) — Phase 4/5
- **Trim Sheet Intelligence** (aspect-ratio-aware UV per face) — Phase 5
- **TexForge integration** — separate product milestone

---

## Documented as known limitations in v1.0.0 README

Ship with these, document them, do not hide them:

- Block Composer has slight edge misalignment on rotated non-rect shapes at
  90°/180° block perimeter positions
- Corner columns at non-90° joints (e.g., 45° corner-cut) have slight
  visual overlap — works at game scale
- Detail stamps use fixed geometry (no randomization; coming in v1.1)
- Build Mode wall type changes currently require regenerate to see in final
  output (if that's still true — verify in the Build Mode behavioral
  session)

---

## Session roadmap (soft target: 6–8 weeks)

**Stability work first, behavioral verification second, release prep last.**

1. **Session 1 (complete) — Scoping + CLAUDE.md locked.**

2. **Session 2 — Stability sweep: `bm_*` modules.**
   Migrate `bm_data.py` (16 direct reads) and `bm_operators.py` (13) to
   `getattr(scene, 'prop', default)`. Primary authoring path gets hardened
   first. Test Build Mode end-to-end after migration.

3. **Session 3 — Unregister hygiene + "Cleanup All Helpers" operator.**
   Audit unregister path. Add cleanup for orphaned `WBTK_BM_*`,
   `WBTK_DTL_*`, `_WBTK_*` objects and collections. Build the user-facing
   Cleanup All Helpers operator in the Build Mode panel. Test disable →
   re-enable cycles with active Build Mode state.

4. **Session 4 — Stability sweep: top legacy offenders.**
   `operators_pipes.py` (42), `operators_structures.py` (37),
   `operators_walkways.py` (33), `operators_foliage.py` (32),
   `operators_cables.py` (25). One file per round of review within the
   session; test each area in Blender before moving to the next.

5. **Session 5 — Stability sweep: remaining files.**
   `ui.py` (24) and every remaining file with any direct reads. Smaller
   targets, but completeness matters for the audit story.

6. **Session 6 — Wall style drop + Build Mode behavioral pass.**
   Remove PANELED/RIBBED/TILED from the wall style enum. Add migration
   handler for old `.blend` files (coerce stale values to FLAT on load).
   Then run the Build Mode behavioral checklist: Toggle Mode edge cases,
   Mirror X/Y correctness on asymmetric block sets, Clear All
   completeness.

7. **Session 7 — Detail stamps behavioral pass.**
   Verify every detail type places correctly on every supported face
   (5 faces × 8 types = 40 combinations). Parenting-on-delete behavior.
   Offset and scale edge cases. Visual orientation sanity on non-flat
   block configurations.

8. **Session 8 — Release prep.**
   Fix misleading `__init__.py` comments. Verify Block Composer tooltip.
   Bump `bl_info` to `(1, 0, 0)`. Add `doc_url`. Write README. Add
   LICENSE. Capture one screenshot or GIF of the Build Mode flow. Final
   install → reload → uninstall smoke test on a fresh Blender 5.0.

One session at a time. Test in Blender between sessions. Commit to git
(local-only is fine) before the next session.

---

## Codebase quick reference (v0.13.0)

- **32 `.py` files** as of v0.13.0
- **New in v0.13.0:** `bm_data.py` (~335 lines), `bm_details.py` (~405),
  `bm_generate.py` (~179), `bm_operators.py` (~424)
- **Largest files:** `geometry_buildings.py`, `ui.py`, `operators_walkways.py`,
  `properties.py`, `operators_structures.py`, `operators_preview.py`
- **Registration:** `__init__.py` gathers class tuples from each module;
  legacy modules use `_classes_to_register`, new `bm_*` modules with
  operators use `_classes`
- **Property management:** `properties.PropertyManager.register_properties()`
  / `unregister_properties()`

### Build Mode pipeline

```
User toggles Build Mode (OP_ToggleMode)
    ↓
Add/Stack/Attach blocks → bm_data stores block records
    ↓
Live preview rebuilds from bm_generate.build_preview_bm()
    ↓
User places details via OP_AddDetail → bm_details.place_detail()
    ↓
OP_Generate calls into bm_generate for final building geometry
    ↓
Optional: trim UV via operators_trim_uv
```

### Parametric pipeline (unchanged)

```
UI parameters → OP_GenerateBuildingShell (operators_structures.py)
    ↓
Shape selection → geometry_footprints helpers
    ↓
Floor loop in geometry_buildings (GeometryBuildings class)
    ↓
_finalize_bm → bevel modifiers → trim UV
```

---

## Release definition of done

v1.0.0 is ready to ship when:

- Build Mode works end-to-end without crashing on reasonable input
- All 8 detail types place correctly on all 5 faces without visual bugs
- Parametric Shape Generator continues to work for all 5 shapes +
  6 enhancements
- Block Composer generates city blocks without crashing
- The `getattr` stability sweep is complete across `bm_*` and legacy
  modules (299 → 0 direct `scene.wbtk_*` reads)
- Unregister path cleans up every registered class and helper object
- "Cleanup All Helpers" operator is available to users as a safety net
- Wall style property is FLAT-only, migration handler in place for old
  `.blend` files
- Addon installs, reloads, and uninstalls cleanly on a fresh Blender 5.0
- README covers Build Mode as primary with at least one visual
- LICENSE is in place
- `bl_info` is `(1, 0, 0)`
- Known limitations are documented, not hidden
- Misleading `__init__.py` comments cleaned up
