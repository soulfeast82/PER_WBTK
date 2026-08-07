# WBTK Fix Pass — Scale Bible Alignment (2026-08-05)

**Applied directly by Claude (Cowork session) via the device bridge — this doc is the RECORD, not instructions.**
**Backups on disk before write:** `config.py.bak` · `properties.py.bak` (both 2026-08-05)
**Validation:** `py_compile` clean ×2 · diff verified to contain ONLY the lines below · committed with mtime guards (refuses to write over concurrent edits).

---

## WHY

WBTK's building defaults predated the locked Scale Bible (door 120×20×250 cm · building floor 350 cm · window insert 100×100). Every generated shell cut a 1.0×2.0 m door hole — the canon 1.2×2.5 m door mesh could not fit, and nothing warned, because Config IS the enforcement point and it enforced pre-canon numbers. Diagnosis verified against Jermaine's live panel screenshots (2026-08-05) before editing: panel showed door 1×2, window W 1.5, height 3.0 — exact match to code.

## WHAT CHANGED — 5 values, 2 files

### `config.py` (Building Defaults block, lines 27–36)

| Constant | Was | Now | Authority |
|---|---|---|---|
| `DEFAULT_WALL_HEIGHT` | 3.0 | **3.5** | Scale Bible: floor 350cm [LOCKED] |
| `WINDOW_WIDTH` | 1.5 | **1.0** | Asset Bible: window insert 100×100 |
| `DOOR_WIDTH` | 1.0 | **1.2** | Scale Bible: door 120cm [LOCKED] |
| `DOOR_HEIGHT` | 2.0 | **2.5** | Scale Bible: door 250cm [LOCKED] |
| `WALL_THICKNESS` | 0.2 | 0.2 *(unchanged — comment added)* | already canon (20cm) |

### `properties.py` (panel defaults — mirror Config per house convention)

| Property | Line | Was | Now |
|---|---|---|---|
| `wbtk_building_window_width` | 430 | 1.5 | **1.0** |
| `wbtk_building_door_width` | 447 | 1.0 | **1.2** |
| `wbtk_building_door_height` | 450 | 2.0 | **2.5** |

**Not touched, inherit automatically:** `wbtk_wall_height` (L102) and `wbtk_building_floor_height` (L187) both default to `Config.DEFAULT_WALL_HEIGHT` → Wall Generator and Building Shell heights become 3.5 with zero extra edits. `WINDOW_HEIGHT` 1.0 was already canon. Min/max ranges verified to admit all new defaults (door H max 4.0, window W min 0.3, heights max 10.0).

## SMOKE TEST (Jermaine — pending)

1. Blender: **F3 → "Reload Scripts"** (or restart Blender — cleaner with the addon junction).
2. N-panel → World Builder → Building Shell: confirm **H (m) 3.5 · Window W 1 m · Door W 1.2 m / H 2.5 m**.
   - Field still shows an old value? That .blend stored an override — right-click the field → **Reset to Default Value**.
3. Generate one Building Shell. Confirm the door hole reads noticeably taller/wider.
4. **Commit in PER_WBTK** (commit discipline: uncommitted work is how 4a/4b/5a died).

## ROLLBACK

Copy `config.py.bak` → `config.py`, `properties.py.bak` → `properties.py`, Reload Scripts.

## PART 2 (2026-08-06) — Build Mode reached + window-gap fix + a bridge near-miss

**Window pane gap (2026-08-05):** `geometry_buildings.py` — pane was 5cm smaller than its cutout on all sides with nothing filling the ring = see-through gap into the shell interior. `frame = 0.0` at BOTH sites (build_shell_wall L141, angled-wall L492); pane now fills the opening. Viewport-verified by Jermaine. Backup: `geometry_buildings.py.bak`.

**Build Mode Scale Bible pass (2026-08-06):** Build Mode kept its own height literals, so the Part-1 fix never reached it. Now Config-driven so it can't drift again:
- `bm_data.py` — `DEFAULT_BLOCK` h, sync fallbacks L149/L165 → `Config.DEFAULT_WALL_HEIGHT` (was 3.0)
- `properties.py` — `wbtk_bm_height` default → `Config.DEFAULT_WALL_HEIGHT` (was 3.0)
- `bm_generate.py` — getattr fallbacks mirrored to properties (1.5→1.0 window W, 1.0→1.2 / 2.0→2.5 door); Session-6 NOTE added at the 3rd try/finally-less Config-override site
- Backups: `properties.py.bak2` (morning `.bak` preserved — git still uncommitted), `bm_data.py.bak`, `bm_generate.py.bak`. `py_compile` clean ×3, guarded commit, live-disk verified.

> ### 🔒 BRIDGE LAW — RE-STAGED FILES CAN BE STALE
> Re-staging `properties.py` after committing to it served the **pre-edit content with a current mtime**. Caught by STOP condition (a value read "reverted"); live `device_bash` grep + md5 proved the disk was correct and the stage was cached. **After any commit, verify edits with a live on-disk read — never trust a re-stage.** Editing from the stale copy would have silently reverted the morning's work.

**Git note:** `git status` shows pre-existing modified files from unfinished sweep sessions — do NOT `git add -A`. Commit exactly: `config.py properties.py region_dna.py geometry_buildings.py bm_data.py bm_generate.py CLAUDE_WBTK_fix_pass_ScaleBible.md`.

**Queued for Session 6 (Build Mode behavioral pass):** window RHYTHM — port the parametric path's AUTO multi-window fit into Build Mode faces (currently ONE centered window per face regardless of width; the main "flow" gap Jermaine identified) · promote Build Mode box to top of Structures panel (matches the locked V2 Mode-dock direction) · the three try/finally Config-override sites.

## FLAGGED, NOT FIXED (Session 6 material — one thing per session)

1. **Config override/restore without try/finally** — `operators_structures.py` ~L329–390 saves/overwrites/restores `Config.WINDOW_*`/`DOOR_*` around the wall loop; an exception mid-loop leaves module-level Config mutated for the rest of the Blender session. Twin of Live Bug #3. Wrap in try/finally in Session 6.
2. **3.5 m floors vs the Buildify Kit Validator's 2 m-grid rule** — heights need an exemption from the 2m-multiple check, or module kits go to 4 m. Rule on this before the Buildify arc starts.
3. `DOOR_SPLAY_ANGLE`, `WINDOW_SILL_HEIGHT`, insets: no canon ruling exists — untouched.
