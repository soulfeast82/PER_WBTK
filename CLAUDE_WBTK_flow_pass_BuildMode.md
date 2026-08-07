# CLAUDE.md — WBTK Build Mode FLOW PASS
### For Claude Code · apply IN ORDER · one file at a time · Blender 5.1 / WBTK v0.13.0

**MISSION (one sentence):** give Build Mode buildings *rhythm* — WINDOW faces get an auto-fit row of windows like the parametric shell does, instead of one lonely centered opening — plus three mechanical safety fixes.

**Context you must trust:** the Scale Bible fix pass of 2026-08-05/06 is ALREADY APPLIED and live on disk (door 1.2×2.5, window 1×1, floor/block height 3.5 via `Config.DEFAULT_WALL_HEIGHT`, window-pane gap fixed in `geometry_buildings.py`). Do not re-apply it, do not "correct" those values back. Full record: `CLAUDE_WBTK_fix_pass_ScaleBible.md` in this folder.

---

## HOUSE LAWS (non-negotiable — from WBTK CLAUDE.md)

1. **Restate-before-edit.** Restate each fix's intent, flag any uncertainty, get Jermaine's confirmation before writing.
2. **Backup before any patch:** `copy <file>.py <file>.py.bak` — EXCEPT `operators_structures.py`: its `.bak` is the Session-5c rollback and MUST NOT be overwritten → use `operators_structures.py.bak2`. (`bm_generate.py.bak` from 2026-08-06 exists; overwriting it with current is fine.)
3. `python -m py_compile <file>` after EVERY file edit.
4. **STOP CONDITION:** any anchor below not found EXACTLY → STOP, report, wait. Line numbers are approximate; anchor TEXT is authoritative.
5. One file at a time. Smoke test per milestone before the next file.
6. Never run `arrange_nodes`-style bulk operations; surgical edits only.

---

## FIX 1 — Window rhythm in Build Mode · `bm_generate.py`

**Why:** `_build_block_walls` calls `build_shell_wall` once per face → exactly ONE centered window regardless of face width. An 8 m face gets a single 1 m window. The parametric path solves this with an AUTO multi-window split (`operators_structures.py` `_calc_win_count` / `_build_multi_window_wall`, min segment = window width + 0.8 m). Port that rule. Bonus: `build_preview_bm` shares `_build_block_walls`, so live preview inherits the rhythm for free.

### 1a. Insert helper — anchor: the line `def _build_block_walls(bm, b, all_info, add_slabs, add_roof, thickness,`

Insert IMMEDIATELY BEFORE that line:

```python
def _build_face_wall(bm, GB, bx, by, bz, length, h, thickness, axis, wtype,
                     door_style, door_in, door_sp):
    """One block face. WINDOW faces auto-fit a ROW of windows — same rhythm
    rule as the parametric shell (AUTO count, min segment = window width
    + 0.8m) — instead of one centered opening."""
    n = 1
    if wtype == 'WINDOW':
        n = max(1, int(length / (Config.WINDOW_WIDTH + 0.8)))
    if n <= 1:
        GB.build_shell_wall(bm, bx, by, bz, length, h, thickness, axis,
            wall_type=wtype, door_style=door_style, door_inset=door_in,
            door_splay=door_sp)
        return
    seg = length / n
    for i in range(n):
        off = i * seg
        if axis == 'X':
            GB.build_shell_wall(bm, bx + off, by, bz, seg, h, thickness, 'X',
                                wall_type='WINDOW')
        else:
            GB.build_shell_wall(bm, bx, by + off, bz, seg, h, thickness, 'Y',
                                wall_type='WINDOW')


```

(`Config` is already imported at the top of this file.)

### 1b. Reroute the dispatch — str_replace, BEFORE:

```python
        if abs(dy) < 0.001:
            GB.build_shell_wall(bm, min(sx,ex), sy, bz, abs(dx), h, thickness, 'X',
                wall_type=wtype, door_style=door_style, door_inset=door_in, door_splay=door_sp)
        elif abs(dx) < 0.001:
            GB.build_shell_wall(bm, sx, min(sy,ey), bz, abs(dy), h, thickness, 'Y',
                wall_type=wtype, door_style=door_style, door_inset=door_in, door_splay=door_sp)
```

AFTER:

```python
        if abs(dy) < 0.001:
            _build_face_wall(bm, GB, min(sx,ex), sy, bz, abs(dx), h, thickness, 'X',
                             wtype, door_style, door_in, door_sp)
        elif abs(dx) < 0.001:
            _build_face_wall(bm, GB, sx, min(sy,ey), bz, abs(dy), h, thickness, 'Y',
                             wtype, door_style, door_in, door_sp)
```

(Angled/chamfer edges keep the single-opening path — they are short; leave the `else:` branch untouched.)

### 1c. `py_compile` → **SMOKE TEST 1:** Reload Scripts → Enter Build Mode → add one block, set Width 8, walls WINDOW → Generate. Expect a **row of ~4 windows** per long face, evenly spaced, sills aligned. Stack a second block: rows align across floors.

---

## FIX 2 — Stale Scale-Bible fallbacks · `operators_structures.py` (⚠️ backup to `.bak2`)

Same defaults-mirror-properties law the Scale Bible pass applied elsewhere. str_replace, BEFORE:

```python
            custom_win_w   = getattr(scene, 'wbtk_building_window_width', 1.5)
            custom_win_h   = getattr(scene, 'wbtk_building_window_height', 1.0)
```

AFTER:

```python
            custom_win_w   = getattr(scene, 'wbtk_building_window_width', 1.0)
            custom_win_h   = getattr(scene, 'wbtk_building_window_height', 1.0)
```

BEFORE:

```python
            custom_door_w  = getattr(scene, 'wbtk_building_door_width', 1.0)
            custom_door_h  = getattr(scene, 'wbtk_building_door_height', 2.0)
```

AFTER:

```python
            custom_door_w  = getattr(scene, 'wbtk_building_door_width', 1.2)
            custom_door_h  = getattr(scene, 'wbtk_building_door_height', 2.5)
```

`py_compile` → **SMOKE TEST 2:** Generate Building Shell (parametric) once — normal result, no errors. **This doubles as the still-pending Session-5c sitting-3 viewport smoke test** — if it passes, sitting 3 is finally verified and this file may be committed.

---

## FIX 3 — try/finally on all three Config/scene override sites

Same bug family as Live Bug #3: overrides restored with no exception guard → an error mid-generate permanently corrupts state for the session.

### 3a. `bm_generate.py` — the block marked `# NOTE Session 6: wrap in try/finally`

Wrap: everything from `master = Utils.create_master("BuildMode")` through the loop, so the restore runs unconditionally. BEFORE (abridged anchors — the block spans from the `saved = (` line to the restore line):

```python
    saved = (Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT, Config.DOOR_WIDTH, Config.DOOR_HEIGHT)
```
…
```python
    Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT, Config.DOOR_WIDTH, Config.DOOR_HEIGHT = saved
```

AFTER pattern: keep `saved = (...)` and the four override assignments as-is; then `try:` before `master = Utils.create_master("BuildMode")`, indent the body (master/origin/bm/info/loop) one level, and replace the bare restore with:

```python
    finally:
        Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT, Config.DOOR_WIDTH, Config.DOOR_HEIGHT = saved
```

Everything after the restore (`# Finalize` onward) stays OUTSIDE the try. Remove the `# NOTE Session 6` comment line — it's done.

### 3b. `operators_structures.py` — the per-floor Config override (starts `orig_win_w = Config.WINDOW_WIDTH`, restore at `# Restore Config`)

Same pattern at its indent level: `try:` immediately after the four `Config.* = custom_*` assignments, body indented, restore under `finally:`. The four `orig_*` captures stay above the try.

### 3c. `operators_block_composer.py` — scene prop override (Live Bug #3 proper)

Anchor: the six `scene.wbtk_building_* = ...` override lines beginning `scene.wbtk_building_shape = b_shape`, and the restore block under the comment `# Restore scene properties`. Wrap: `try:` before the `# Generate building` comment; move the ENTIRE restore block (six lines) into `finally:`; the positioning code (`# Position and rotate the building` onward) stays after the finally, outside.

`py_compile` after each of the three → **SMOKE TEST 3:** Build Mode Generate (3a) · parametric Generate (3b) · Block Composer generate one small block (3c). All three normal.

---

## OUT OF SCOPE — do not touch

- **`ui.py`** — the Build-Mode-to-top-of-panel move is deliberately deferred: ui.py carries old uncommitted sweep drift and 24 unguarded reads; it lands in Session 6 with its own sweep. Resist the urge.
- Session 5c's remaining read sweeps (foliage/cables/props/block_composer/ui) — separate sessions.
- Any value the Scale Bible pass set. Any `.bak` file except creating the ones named above.

## COMMIT (after all smoke tests pass — exact list, NEVER `git add -A`; the working tree holds unfinished old-session changes)

```
git add config.py properties.py region_dna.py geometry_buildings.py bm_data.py bm_generate.py operators_structures.py operators_block_composer.py CLAUDE_WBTK_fix_pass_ScaleBible.md CLAUDE_WBTK_flow_pass_BuildMode.md
git commit -m "Build Mode window rhythm (auto-fit rows) + Scale Bible alignment + try/finally on all 3 override sites; closes 5c sitting-3 smoke test"
```

This one commit lands: both Scale Bible passes (2026-08-05/06), the window-gap fix, the flow pass, and closes Session 5c sitting 3. **Report each fix's verified result to Jermaine as you go — celebrations only on green compiles and confirmed viewport behavior.**
