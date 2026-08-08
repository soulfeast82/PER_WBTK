# WBTK — World Building Toolkit

*SINGLE SOURCE OF TRUTH. The file at
`WorkingFiles\WBTK\World_Building_Toolkit\CLAUDE.md` is a pointer to this one.
All project state lives here. **This copy (PER_WBTK) is the live codebase**;
the WorkingFiles code copy is a stale identical clone — do not work there.*

Blender 5.0 addon for procedural building and city generation.
Currently **v0.13.0**, targeting **v1.0.0 stabilization release**.

Author: Jermaine Dawson Peterson
Location in Blender: View3D > Sidebar > World Builder

---

## Current progress (AUDITED 2026-07-06 — machine-verified against code)

> The previous CLAUDE.md recorded Sessions 4a, 4b, and 5a as complete with
> commits `5b69ce1` and `1d29590`. A full audit on 2026-07-06 found **those
> commits do not exist in either clone and most of that work is absent from
> the code.** The progress below is what is actually in the source, verified
> by a per-file census (every access classified by reading the code).

- ✅ **Session 1** — Scoping + CLAUDE.md locked
- ✅ **Session 2** — `bm_*` read-sweep — **VERIFIED PRESENT** (bm_data 11
  guarded, bm_operators 29, bm_generate 16, bm_details 4; zero raw reads in
  bm_* — only the tracked writes remain)
- ✅ **Session 3** — Unregister hygiene + Cleanup All Helpers (commit `580edff`)
- ❌ **Sessions 4a / 4b / 5a** — **RECORDED AS DONE, NOT PRESENT IN CODE.**
  cables, foliage, pipes, walkways, props: zero getattr guards. structures,
  block_composer, ui: partial only. The ramp-stairs fix and the
  `set_sharp_from_angle` keyword fix claimed as "shipped" are also absent.
  Scope re-queued as Session 5c below.
- ✅ **Session 5b** — Tail sweep **DONE 2026-07-06**: `operators_vents.py`
  (11), `operators_fences.py` (10), `operators_scatter.py` (6),
  `operators_ground.py` (3) = **30 reads converted**. Adversarially
  machine-verified: all defaults exactly mirror properties.py, diffs contain
  only the intended lines, `py_compile` clean ×4, zero raw reads remain in
  the four files. **Viewport smoke test passed 2026-07-07; committed same
  day (backups removed).**
- 🔄 **Session 5c — RECOVERY SWEEP (in progress):** the missing 4a/4b/5a work.
  - ✅ Sitting 1 (2026-07-07): `operators_walkways.py` — 33 reads converted
    **+ ramp-stairs crash fix** (line 604 → `wbtk_st_ramp_intermediate_posts`).
    Three-lens adversarial verification passed (defaults exact incl.
    Config.RAIL_* symbols; diff clean; fix consistent with properties.py,
    ui.py, geometry_walkways.py). `py_compile` clean. **Viewport smoke test
    passed + committed 2026-07-07** (via the new addon junction).
  - ✅ Sitting 2 (2026-07-07): `operators_pipes.py` — 41 reads converted
    (wear helper, straight, run, bundle, randomize f-string). Three-lens
    verification passed; `py_compile` clean; L400 seed write + dead 'YZ'
    branch left for Session 6 as planned. **Smoke-tested + committed
    2026-07-07.**
  - ✅ Sitting 3 (2026-07-07): `operators_structures.py` — 36 reads
    converted (wall 4, room 4, shell 15, row 3, tower 10);
    `Config.DEFAULT_WALL_HEIGHT` / `Config.WALL_THICKNESS` symbols mirrored;
    override ternaries and the 47 pre-existing guards untouched. Three-lens
    verification passed; `py_compile` clean. Shell's try/except wrapper now
    fully dead → Session 6 removal. **Viewport smoke test passed
    2026-08-06; committed `202381e`.** Backup at
    `operators_structures.py.bak2` (`.bak` is the sitting-3 rollback and was
    preserved).
  - 🔲 Remaining raw crash-surface reads: foliage 31, cables 24,
    props 21, block_composer 4, ui.py 24 → **104 reads.**
    ⚠️ **Scope note (2026-08-08):** 76 of these 104 sit in `foliage`,
    `cables` and `props` — the decorator generators the Strategic Pivot
    handed to **BagaPie** — and `block_composer` has "no new work planned".
    Only `ui.py`'s 24 clearly still earn their keep, because ui.py is Build
    Mode's panel and Build Mode is pivot item #1. Worth deciding whether
    the rest is v1.0 scope at all before spending sessions on it.
- ✅ **Flow pass (2026-08-06)** — Build Mode window rhythm: `bm_generate.py`
  gained `_build_face_wall`, so WINDOW faces auto-fit a ROW of windows
  (AUTO count, min segment = window width + 0.8m) instead of one centred
  opening — the same rule the parametric shell uses. `build_preview_bm` now
  applies the same Config overrides as `generate_full`, so live preview
  matches the final build in window count AND window/door size (it
  previously ignored the user's panel values entirely). try/finally added to
  all four Config/scene override sites. Scale-Bible fallbacks aligned in
  `operators_structures.py`. Viewport-verified, committed `202381e`. Record:
  `CLAUDE_WBTK_flow_pass_BuildMode.md`.
- 🔲 **Session 6** — Wall style enum drop + Build Mode behavioral pass +
  accumulated fixes
- 🔲 **Session 7** — Detail stamps behavioral pass
- 🔲 **Session 8** — Release prep

**Audited sweep state (2026-07-06): ~308 reads getattr-guarded (incl.
operators_preview.py's 142); 214 raw reads remain (190 in operators + 24 in
ui.py draw code); 34 raw writes tracked.**

**Git state (re-verified 2026-08-08):** head is `202381e` (flow pass) on top
of `a59fab8` (5c-2 pipes), `0340943` (5c-1 walkways), `d62ddd9` (5b),
`580edff` (session 3), `7860f38` (baseline). The 4-commit history in the
older doc was fiction; the WorkingFiles clone is stale at `580edff`.

⚠️ **Correction — there is NO uncommitted code drift.** This doc previously
claimed "pre-existing session-2-era and partial-sweep changes in other files
remain uncommitted working-tree changes." That is **false and was never
true in this clone.** `git status` lists 16 .py files as modified, but every
one is **byte-identical to HEAD** once normalised — verified 2026-08-08 by
comparing `git hash-object` against `git rev-parse HEAD:<file>` for all 16.
They are flagged only because `core.autocrlf=true` with no `.gitattributes`,
so on-disk LF endings don't match the CRLF a checkout would write.

**Do not treat that file list as pending work.** Only `CLAUDE.md` ever had
real uncommitted content. Optional cleanup: add a `.gitattributes` with
`*.py text eol=lf` (or run `git add --renormalize .`) to stop the phantom
modifications, which otherwise keep masquerading as lost sweep work.

---

## Known LIVE bugs (census 2026-07-06 — fix in Session 5c/6)

1. ~~**Generate Ramp Stairs crashes.**~~ **CLOSED 2026-07-07 (5c sitting 1):**
   `operators_walkways.py` now reads `wbtk_st_ramp_intermediate_posts` (the
   property properties.py:84 actually defines). Verified consistent with
   ui.py:96 and `create_angled_rails_bmesh`; **viewport-verified and
   committed.** (Previous doc claimed this shipped in "Session 4b" — it
   had not.) Release note: "Ramp stairs no longer crash on Generate."
2. **`set_sharp_from_angle` called positionally** at
   `operators_props.py:277` and `operators_structures.py:164`
   (hasattr-wrapped, so no crash on old Blender, but the previous doc says
   Blender 5.0 requires the keyword form — if true, both calls raise
   TypeError at runtime). Verify on Blender 5.0 and convert to
   `angle=` keyword. (Previous doc claimed this shipped in "5a" — absent.)
3. ~~**Block Composer can clobber user settings.**~~ **CLOSED 2026-08-06
   (flow pass):** the shell-generate call in `operators_block_composer.py` is
   now wrapped in try/finally with the six-line scene-prop restore in the
   `finally`, so an exception mid-generation can no longer leave the user's
   building panel overwritten. The same guard was applied to the other two
   Config-override sites (`bm_generate.generate_full`,
   `operators_structures.py` per-floor walls) plus a fourth in
   `build_preview_bm`. Viewport-verified; committed `202381e`.
4. Minor: `operators_pipes.py` has an unreachable `'YZ'` bend-plane branch
   (L218–220; enum defines only XY/XZ) and an unused `flange_spacing` read
   (L193). `operators_props.py:89` reads `wbtk_barrel_rib_width` and never
   uses it. `wbtk_cable_between_mode` is defined in properties.py but read
   nowhere.
5. Minor (found in 5c sitting-3 verification): `operators_preview.py`
   L287–290 / L346–349 use `'SOLID'` getattr fallbacks for the four
   building wall-type props, but properties.py defaults are 'DOOR' (front)
   / 'WINDOW' (back/left/right). Harmless while props register normally;
   align the fallbacks in Session 6 for consistency.

---

## What v1.0.0 is

**A stabilization release, not a feature release.**

v1.0.0 ships what exists in v0.13.0, made solid and documented. Build Mode is
the primary authoring workflow. The parametric shape generator and Block
Composer continue to ship as alternates. Feature work in the Queued list is
deferred to v1.1+.

The shape of this release is driven by three real risks found during scoping:

- **Risk 1** — wall style stubs exposed to users. Resolution in Session 6.
- **Risk 2** — unguarded scene property reads. **Audited 2026-07-06: 214 raw
  reads remain (Session 5c scope); ~308 already guarded incl. Sessions 2 + 5b.**
- **Risk 3** — incomplete unregister path. **Resolved in Session 3.**

---

## Design Laws (locked — do not violate)

- **"Butter" standard:** 80% automation, 20% manual control. Any knob position produces plausible results. Zero friction, zero manual guard rails.
- **Shape first, details second:** doors, windows, pipes, panels, vents are POST-generation overlays — never baked into shell generation.
- **2m tile grid** is the measurement backbone. Scale Bible: 50cm primary grid, door 120×20×250cm, building 800×800×350cm.
- **Region DNA** drives defaults: loading a district profile switches building heights, pipe density, palettes, foliage presets across all generators.
- **Zero rounded corners** anywhere in the game world (hard art rule).
- Blocking/layout happens in UE5; WBTK output = architecture assets for locked layouts.

---

## The authoring modes (priority order)

**1. Build Mode — PRIMARY.** The `bm_*` module family. Users toggle Build
Mode on, add/stack/attach blocks, set per-wall types and per-corner chamfers,
then place detail stamps on selected block faces, then generate the
building.

**2. Parametric Shape Generator — SECONDARY.** The original
`OP_GenerateBuildingShell` path. Users set shape (RECT, CORNER_CUT, L_SHAPE,
U_SHAPE, T_SHAPE), enhancements (parapet, plinth, corner columns, bands,
ledges, sills), and generate from parameters. Audited: 47 reads guarded,
36 still raw (Session 5c).

**3. Block Composer — TERTIARY.** City block generator. Still registered.
Known rotation issue documented, no new work planned.

**Removed in v0.11.0:** Custom Builder viewport modal painter and Footprint
Painter grid UI.

---

## Long-term vision (for v1.1+ planning, not v1.0 scope)

*Where this section conflicts with the Strategic Pivot below (locked
2026-07-06), the pivot governs.*

WBTK is becoming an **object-first building editor**, not three separate
authoring modes. The intended unified flow:

1. Place a core object (a building)
2. Select it, pick a face, assign wall types (door, window, with sizing)
3. Layer architectural elements (trim, moldings, details)
4. Texture/trim-sheet assignment on the object
5. Environment elements (pipes, cables, vents, signs, canopies) snap onto
   surfaces
6. UE5 export pipeline

A Claude Design exploration session produced V2 Mode-dock prototype as
the chosen direction. Filed under v1.1+. Pipes/cables/walkways are
**decorators, not objects with faces** — they fit step 5 (Decorate) as
tool types, not as objects flowing through the 5-stage building flow.

**v1.1+ implication:** the trim-sheet schema becomes the interop contract
between WBTK and TexForge. WBTK's `operators_trim_uv.py` should consume a
trim-layout schema (region → cornice/band/window-trim/baseboard) authored
separately. Worth designing deliberately in v1.1.

---

## Strategic Pivot (locked 2026-07-06) — WBTK is the BRAIN, not the building engine

Two third-party GN tools own generation duties:

- **Buildify 1.0** = the building engine. Verified working on Blender 5.1
  (2026-07-06): loads, generates, live-edits.
- **BagaPie v11.0.5** = the greeble/scatter engine (pipes, cables, fences,
  arrays, scattering).

WBTK = the Project Earl Ray brain:

1. **Build Mode block footprints → Buildify input.** Build Mode exports flat
   Z=0 base geometry as Buildify input.
2. **Region DNA = kit switcher.** District profile switches Buildify
   module-kit collections + parameters per district.
3. **Kit Validator (new op):** enforces Buildify's module contract — applied
   rotation/scale, bottom-center origins, pillar collection order
   flat→CC→CV, +Y facing, single module size per building, 2m grid
   multiples. Reports violations by name.
4. **Buildify export chain** (Realize Instances → visual geometry to mesh →
   UV attribute convert → FBX) **extends `operators_ue_pipeline.py`** rather
   than living as a new module.
5. **PANELED/RIBBED/TILED: confirmed cancelled** — Session 6's enum drop
   stands; wall styles are module kits now, not code.

### Evolution Clause (locked 2026-07-07)

Long-term, WBTK forks Buildify's node groups into its own asset library
("ER-BFY", WBTK_BuildingCore.blend) and caters them to Project Earl Ray:
2m grid + Scale Bible defaults, Region DNA as modifier-level district
inputs, Dusk Ward floor-material verticality, sloped-roof and sign node
groups as needed, game-export-aware realize path.

**Rule: fork when forced by a concrete need stock Buildify can't serve —
never preemptively.** Until then, the integration arc runs on stock
Buildify 1.0 (frozen upstream; license check required only if WBTK ever
ships publicly with forked nodes).

---

## Build Mode architecture (primary path)

```
bm_data.py       — Block CRUD, adjacency, grid, sync. Pure library.
bm_operators.py  — All user actions. Delegates to bm_data and bm_generate.
bm_generate.py   — Blocks → BMesh. Preview build + full generation.
bm_details.py    — Detail stamps: types, geometry, placement, operators.
```

### Block data model

```python
DEFAULT_BLOCK = {
    "w": 4.0, "d": 4.0, "h": 3.0,
    "walls": {"north": "SOLID", "south": "SOLID", "east": "SOLID", "west": "SOLID"},
    "chamfers": [],
    "chamfer_size": 1.0,
}
```

### Build Mode operators (in `bm_operators.py`)

Toggle Mode, Add Block, Stack Block, Attach Block, Delete Block, Duplicate
Block, Sync From Block, Toggle Chamfer, Mirror X, Mirror Y, Clear All, Iso
View, Generate, **Cleanup All Helpers** (Session 3).

### Detail stamps (in `bm_details.py`)

Eight types: AC_UNIT, VENT, PIPE_CLUSTER, BALCONY, FIRE_ESCAPE,
SIGN_MOUNT, ANTENNA, CANOPY.

---

## Conventions I use

- **Property reads:** `getattr(scene, 'prop', default)` — never assume scene
  props exist.
- **Defaults in `getattr` must mirror `properties.py` exactly.** Use
  `Config.*` symbols where properties.py does
  (e.g., `Config.DEFAULT_WALL_HEIGHT`, `Config.WALL_THICKNESS`,
  `Config.RAIL_BOTH/LEFT/OUTER`, `Config.DEFAULT_TILE_SIZE`).
- **Operators use** `self.report({'INFO'|'WARNING'|'ERROR'}, …)` not `print()`.
- **Class registration:** legacy modules use `_classes_to_register`,
  bm_* modules that register classes use `_classes`.
- **Helper object prefixes:** `WBTK_BM_` (blocks), `WBTK_DTL_` (details),
  `_WBTK_BM_Grid` / `_WBTK_BM_GridFill` (grid).

---

## Standing instructions for sweep sessions

- **Restate-before-edit pattern:** Claude Code restates spec, flags
  uncertainty, gets confirmation before any file writes. Always.
- **One file at a time** for high-stakes files (anything in the parametric
  pipeline or with 20+ reads). Approve, smoke test, then next file.
- **Batch approval acceptable for low-stakes files** with <10 reads each
  (e.g., Session 5b's 4 small files reviewed as combined diff).
- **Skip rewrites of files with zero reads to migrate.** Pure no-op
  rewrites add drift risk for zero benefit. Apply this to:
  - Files with 0 `scene.wbtk_*` reads (no work to do)
  - Files with reads already migrated to getattr from prior work
  - Log any writes in such files as follow-ups without touching the file
- **Accept non-functional drift in full-file rewrites.** When complete-file
  rewrites round-trip through Write and produce non-functional drift
  (Unicode escape vs literal char, trailing newline policy), accept as a
  known consequence rather than fighting it. Note in summary, don't loop
  on corrective edits.
- **API audit pattern:** when Blender API changes are surfaced, grep the
  entire codebase for the same pattern and fix all instances together.
  Don't fix one and find another next session.
- **Trust nothing undocumented-by-code (added 2026-07-06):** progress claims
  are only real once verified against the source and committed. Audit before
  building on any "done" claim; commit at the end of every session so the
  git log IS the progress record.

---

## Workflow rules (non-negotiable)

- **Backup before any patch run:** copy target to `<name>.py.bak` (never
  `.py` — Blender registers stray .py files).
- `python -m py_compile` after EVERY file edit. One file at a time for
  high-stakes files.
- **STOP CONDITION:** anchor/menu/API not found exactly as expected → STOP,
  report, wait. Never improvise a substitute.
- Surgical edits over rewrites. Preserve working code paths.
- Jermaine verifies in the Blender viewport after each milestone; wait for
  confirmation before stacking risky changes.
- Model policy: sweep sessions default to Opus; escalate to Fable only
  after two failed attempts on the same problem.
- **Deploy setup (2026-07-07):** Blender loads this addon via a directory
  junction — `%APPDATA%\Blender Foundation\Blender\5.1\scripts\addons\PER_WBTK`
  → this repo folder. Edits here are live in Blender after a restart /
  Reload Scripts; there is NO separate installed copy to sync. (The old
  installed copy caused the 2026-07-07 stale-smoke-test incident and is
  the likely mechanism that lost the 4a/4b/5a work. Never reinstall from
  zip over the junction.)

---

## How I work

- **Systems-first thinker.** Strong on macro structure, less on line-level.
- **Prefer complete files** for substantial changes. Small targeted edits
  (1 function, ≤10 lines in large files) acceptable.
- **Keep it real.** If an approach is wrong, say so and why.
- **Ask clarifying questions** when prompts are ambiguous. Don't silently
  fill gaps in a precision-mode session.
- **Restate-before-edit.** Goal, what to preserve, deliverable format.
  Wait for my confirmation before editing files.
- **One thing per session.**
- Literal instruction following. State preferences explicitly.

---

## Voice & communication

Jermaine is ADHD, voice-types, wants decisive single recommendations (no
option menus), numbered steps, one clear next action per response, and
celebrations ONLY on verified outcomes (clean compile, confirmed viewport
behavior).

---

## Follow-ups consolidated (census-verified 2026-07-06)

### Unguarded writes — 34 total (census-verified; supersedes the old "44")

`getattr` doesn't cover writes. Same crash surface as reads during
register/unregister/stale-`.blend` ordering.

| File | Line(s) | Writes | Context |
|---|---|---|---|
| `bm_data.py` | 147–155 | 8 | sync_props_from_block: width, depth, height, 4× wall_*, chamfer_size |
| `bm_operators.py` | 27, 31, 491 | 3 | `wbtk_bm_active` toggles |
| `operators_live_preview.py` | 215–216, 227–228, 252–253 | 6 | `wbtk_live_preview_active` / `wbtk_live_preview_type` |
| `operators_cables.py` | 312 | 1 | `wbtk_cable_seed` (randomize) |
| `operators_foliage.py` | 278 | 1 | `wbtk_foliage_seed` (randomize) |
| `operators_pipes.py` | 400 | 1 | `wbtk_pipe_wear_seed` (randomize) |
| `operators_structures.py` | 614 | 1 | `wbtk_building_seed` (randomize) |
| `operators_block_composer.py` | 100–105, 114–119, 202 | 13 | override/restore paths + `wbtk_block_seed` |

Note: `operators_foliage.py`'s preset loader performs ~28 additional
`setattr` writes but they are hasattr-guarded (L94–99) — not crash surface;
all names verified to exist in properties.py.

**Disposition:** wrap in `hasattr` guards or try/except AttributeError in
Session 6 if scope permits; else defer to v1.0.1. Template pattern exists in
the foliage preset loader. Block Composer's override/restore writes already
gained their try/finally in the 2026-08-06 flow pass (Live bug #3 CLOSED);
the remaining exposure there is the writes themselves, not the guard.

### Pre-existing geometry / behavior issues (Session 6 / v1.0.1)

**Pipe bend flange orientation bug.** `OP_GeneratePipeRun` produces a
bend where the flange on the turn-pipe end faces the wrong direction at
the joint. Pre-existing in `geometry_pipes.py`, not related to sweep.

**UCX collision boxes visible in viewport for cables-between-selected.**
Generated `UCX_Cable_Span_*` boxes are visible instead of hidden; should be
auto-hidden per UE5 export convention. Not a sweep regression.

**Partially-guarded shell read block in `operators_structures.py:176–190`.**
15 raw reads sit inside a try/except AttributeError — caught, but should be
migrated to getattr in Session 5c, after which the wrapper is dead code to
remove in Session 6.

### From Session 3's audit (deferred)

**#9 Modal `OP_ToggleMode` survives addon unregister.** Architectural
defer. Cleanup All Helpers gives users the manual escape.

**#10 Material leak in `bm_data.create_grid`.** Creates new
`WBTK_BM_GridFill` and `WBTK_BM_GridMat` every Build Mode toggle cycle.
**Fix in Session 6:** two `get-or-create` conversions.

**#11 Orphan `WBTK_Live_Preview_Mesh` edge case.** Defer — no real-world
repro.

### Corrected record — claims from the previous doc that are NOT in the code

- ~~"Ramp stairs fix shipped in 4b"~~ → **bug is LIVE** (see Live bugs #1).
- ~~"set_sharp_from_angle keyword fixes shipped in 5a"~~ → **calls are still
  positional** (see Live bugs #2).
- ~~"Sessions 4a/4b/5a sweeps complete, 243/299 (81%)"~~ → actual audited
  state: 214 raw reads remain; see Session 5c scope.
- ~~"ui.py `→`/newline cosmetic drift accepted in 5a rewrite"~~ → no such
  rewrite exists in this code; irrelevant.

---

## In scope for v1.0.0

### Stability sweeps (Risk 2)

- ✅ Session 2: `bm_data.py`, `bm_operators.py`, `bm_generate.py`,
  `bm_details.py` — verified fully guarded (reads)
- ✅ Session 5b (2026-07-06): `operators_vents.py` (11),
  `operators_fences.py` (10), `operators_scatter.py` (6),
  `operators_ground.py` (3) — verified, smoke-tested + committed 2026-07-07
- 🔲 Session 5c (recovery, ~214 reads): `operators_pipes.py` (41),
  `operators_walkways.py` (33 + ramp crash fix), `operators_foliage.py`
  (31), `operators_structures.py` (36 residual), `operators_cables.py`
  (24), `operators_props.py` (21), `ui.py` (24), `operators_block_composer.py`
  (4). Also convert the two positional `set_sharp_from_angle` calls.
  - Skip: `operators_preview.py` (142 already guarded),
    `operators_live_preview.py`, `operators_region_dna.py`,
    `operators_trim_uv.py`, `operators_ue_pipeline.py`, `properties.py`,
    `utils.py` — zero raw reads (writes logged above).

### Cleanup items (Session 6)

- Fix misleading comments in `__init__.py` lines 77–79
- Remove the then-dead try/except in `operators_structures.py` shell block
  (after 5c migrates its reads)
- Verify Block Composer tooltip presence
- Remove dead `'YZ'` branch + unused `flange_spacing` read in
  `operators_pipes.py`; unused `wbtk_barrel_rib_width` read in
  `operators_props.py`

### Behavioral pass (Session 6)

- Remove PANELED/RIBBED/TILED from wall style enum (Risk 1; cancellation
  confirmed by Strategic Pivot — wall styles are module kits now)
- Migration handler for old `.blend` files (coerce stale wall style → FLAT)
- Material leak fix #10 (two `get-or-create` conversions in bm_data.py)
- Right-click menu collision fix (Build Mode)
- Grid live-update — add `update=` callbacks to `wbtk_bm_grid_size`,
  `wbtk_bm_grid_subdivs`, `wbtk_bm_block_color`
- Pipe bend flange orientation fix (geometry_pipes.py)
- UCX visibility fix for cables-between-selected
- Build Mode behavioral checklist: Toggle Mode edge cases, Mirror X/Y
  correctness, Clear All completeness
- 34 unguarded writes if time permits; else defer to v1.0.1

### Detail stamps polish (Session 7)

5 faces × 8 types = 40 combinations. Parenting-on-delete behavior.
Offset/scale edge cases. UX polish (specific issues to be captured at
session start).

### Release essentials (Session 8)

- `bl_info` version → `(1, 0, 0)`
- `doc_url` populated
- README with Build Mode primary workflow + 1+ visual
- LICENSE file
- Changelog including ramp stairs fix and `set_sharp_from_angle` fixes
  (once actually shipped in 5c)
- Final install → reload → uninstall smoke test on fresh Blender 5.0

---

## Explicitly OUT of scope for v1.0.0 (deferred to v1.1+)

- Drag handles (viewport face dragging for block resize)
- Face click cycling (click face in viewport to cycle wall type)
- Auto-setback preview
- Detail randomization (scatter details with randomized positions)
- Street Painter (Phase 4) — post-1.0, rides on Buildify's curve drawing
  mode + WBTK wrappers per the Strategic Pivot
- Explode Building operator
- Wall style geometry (PANELED, RIBBED, TILED implementations) —
  **cancelled outright by the Strategic Pivot** (module kits, not code)
- Batch Row Generator passing `building_shape`
- Block Composer rotation alignment fix
- Wear Layer (vertex color from geometry analysis) — Phase 4/5
- Trim Sheet Intelligence (aspect-ratio-aware UV per face) — Phase 5
- Object-first unified editor flow — v1.1+ design exploration
- Pipes panel UI consolidation (Jermaine, 2026-07-07: the pipe generators'
  UI "will probably be consolidated" — design pass later, not v1.0)
- TexForge integration + trim-sheet schema contract — v1.1+
- Buildify/BagaPie integration arc (Kit Validator, Region DNA kit
  switching, footprint export, UE5 export chain) — post-v1.0, per the
  Strategic Pivot

---

## Documented as known limitations in v1.0.0 README

- Block Composer slight edge misalignment on rotated non-rect shapes
- Corner columns at non-90° joints have slight visual overlap (game-scale fine)
- Detail stamps use fixed geometry (no randomization; coming in v1.1)
- Pipe Run (L-shape) minor flange orientation quirk at bend joint —
  to be fixed in v1.0.1 if not in Session 6
- UCX cables-between-selected visibility — to be fixed in v1.0.1 if not in
  Session 6

---

## Session roadmap

1. ✅ **Session 1** — Scoping + CLAUDE.md locked
2. ✅ **Session 2** — `bm_*` modules sweep (verified in code)
3. ✅ **Session 3** — Unregister hygiene + Cleanup All Helpers (`580edff`)
4. ✅ **Session 5b** — Tail sweep (vents/fences/scatter/ground, 30 reads),
   done + machine-verified 2026-07-06; smoke-tested + committed 2026-07-07.
5. 🔲 **Session 5c** — Recovery sweep: the 214 raw reads that Sessions
   4a/4b/5a were supposed to cover, plus the ramp-stairs crash fix and the
   two `set_sharp_from_angle` keyword conversions. Biggest remaining chunk;
   split across multiple sittings (pipes+walkways / foliage+cables /
   structures+props / ui+block_composer), one-file-at-a-time rules apply
   (several files have 20+ reads).
6. 🔲 **Session 6** — Wall style enum drop + Build Mode behavioral pass +
   accumulated fixes (material leak, right-click collision, grid
   live-update, pipe bend, UCX, dead code, possibly the 34 writes
   — block-composer try/finally already landed 2026-08-06)
7. 🔲 **Session 7** — Detail stamps behavioral pass + UX polish
8. 🔲 **Session 8** — Release prep (README, LICENSE, version bump,
   documentation, final smoke test)

**Commit discipline going forward:** every session ends with a commit in
PER_WBTK. Uncommitted work is how the 4a/4b/5a loss happened.

---

## Codebase quick reference (v0.13.0)

- **32 `.py` files**
- **New in v0.13.0:** `bm_data.py`, `bm_details.py`, `bm_generate.py`,
  `bm_operators.py`
- **Largest files:** `geometry_buildings.py`, `ui.py`,
  `operators_walkways.py`, `properties.py`, `operators_structures.py`,
  `operators_preview.py`

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

Safety net: Cleanup All Helpers (Session 3) sweeps `WBTK_BM_*`,
`WBTK_DTL_*`, `_WBTK_*`, live preview helpers. Auto-exits Build Mode if
active.

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
- All 8 detail types place correctly on all 5 faces
- Parametric Shape Generator works for all 5 shapes + 6 enhancements
- Block Composer generates city blocks without crashing
- Read sweep complete (Sessions 2, 5b, 5c) — zero raw crash-surface reads
- Ramp-stairs crash fixed and viewport-verified (Session 5c ✅ 2026-07-07)
- `set_sharp_from_angle` keyword conversions verified on Blender 5.0
- Unregister path clean (Session 3 ✅)
- "Cleanup All Helpers" operator available (Session 3 ✅)
- Wall style property is FLAT-only with migration handler (Session 6)
- Grid live-update callbacks wired (Session 6)
- Right-click menu collision resolved (Session 6)
- Material leak #10 fixed (Session 6)
- Dead code removed in `operators_structures.py` (Session 6)
- Pipe bend flange direction fixed (Session 6)
- UCX cables visibility fixed (Session 6 or v1.0.1 in known limitations)
- Detail stamps UX polished (Session 7)
- Addon installs, reloads, uninstalls cleanly on fresh Blender 5.0
- README covers Build Mode as primary with at least one visual
- LICENSE in place
- `bl_info` is `(1, 0, 0)`
- Known limitations documented, not hidden
- Misleading `__init__.py` comments cleaned up
- Changelog reflects only fixes that are verifiably in the code
