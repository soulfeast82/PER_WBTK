# Slab v0: proof results (2026-11-10)

Spec: `CLAUDE_SLAB_V0_SPEC.md`. Blender 5.2.2 LTS, Unreal 5.8.4. **The joint road holds:** every gate passed.

## Gate B (Blender, `tests/test_slab_v0.py`): 36/36

- Window slab bounds X 0..4.0, Y -0.21..0, Z 0..3.5 m. The 21 cm depth was ruled 11-10 ("Keep it, 21 cm"): the glass sits 1 cm proud of the street face. *Superseded 11-11: the glass moved to the back and the slab is 20 cm deep (see the follow-up below).*
- Solid and Door slabs are exactly 0.2 m deep.
- Joints L (0,0,0), R (4,0,0), U (0,0,3.5) at 0° rotation. All three survive FBX export and a fresh-scene re-import unchanged.
- `bake_space_transform=True` worked as is; the spec's one fallback knob was not needed.

## Gate U1 (Unreal, `/Game/ER_Test/WBTK_SlabV0/SM_DW_WallSlab_Window_400x350_A`)

| | expected | measured |
|---|---|---|
| socket names | `L`, `R`, `U` | `L`, `R`, `U` (UE strips `SOCKET_`) |
| L | (0, 0, 0) | (0, 0, 0) |
| R | (400, 0, 0) | (400, 0, 0) |
| U | (0, 0, 350) | (0, 0, 350) |
| socket rotation / scale | 0 / 1 | 0 / 1, all three |
| mesh bounds | 400 × 21 × 350 | min (0, 0, 0), max (400, 21, 350) |

UE flips the Y sign: the street face is +Y in Unreal. All three sockets sit on Y = 0, the back face, so they agree with the mesh, which the spec allows.

## Gate U2: the snap (level `/Game/ER_Test/L_SlabV0_Proof`)

- Slab A was spawned at the origin. Slab B was spawned at (1000, 1000, 0) turned 37°.
- B was attached to A at socket `R` with Snap to Target for location, rotation and scale.
- B ended at (400, 0, 0) with rotation 0, attached to A.

| measure | pass | measured |
|---|---|---|
| gap: A's R to B's L | ≤ 0.05 cm | 0.000000 |
| turn: roll / pitch / yaw | ≤ 0.01° | 0 / 0 / 0 |
| seam: B min X − A max X | 0 ± 0.05 cm | 0.000000 (A 0..400, B 400..800) |
| front faces flush: Y min / max | ± 0.05 cm | 0 / 0 |
| bottoms level: Z min | ± 0.05 cm | 0 |
| window beat | 100, 300, 500, 700 | 100, 300, 500, 700 |

The window beat is the slab-local centres (100 and 300, measured in Gate B) carried through each actor's transform. It is not a fresh read of Unreal's triangles.

The level has a **Movable** DirectionalLight (technical law), a Movable SkyLight and a SkyAtmosphere.

## Screenshots: `proof_refs/`

- `SlabV0_canon.png`: canon camera, arm 1800, pitch −12, FOV 45. One 800 cm wall; the seam does not show.
- `SlabV0_close.png`: at 650 cm. Four window outlines on an even beat.

**Seen, not ruled:** from the street the windows barely read. The existing wall code puts the reveal on the back face, so the street side is flush glass in the same material. This needs a decision before slabs become real kit pieces. *Fixed 11-11, see the follow-up below.*

## Unreal 5.8 differences from the spec's sketch

- `StaticMesh.sockets` is protected from Python ("cannot be read"). Use `mesh.find_socket(name)` or `mesh.get_sockets_by_tag('')`.
- The FBX import defaults to the MCP `StaticMeshTools.import_file`, which does not follow the spec:
  - Nanite came in **off**; it was set on.
  - Collision came in as **1 convex hull**; it was replaced with one simple box.
  - The material slot `WBTK_Wall` came in bound to WorldGridMaterial, and no materials were imported.
- Everything else in the spec sketch ran as written: `spawn_actor_from_object`, `attach_to_actor(a, 'R', R, R, R, False)`, `get_socket_location`, `get_actor_bounds(False)`.
- Use keywords for `Rotator`: positionally it is (roll, pitch, yaw).

## Follow-up 2026-11-11: the slab gets a UV map

Unreal warned on the first import: "degenerate tangent bases" and "nearly zero bi-normals". The cause: the slab left Blender with **no UV map** (0 layers on 55 faces), so Unreal added an empty channel and MikkTSpace had nothing to build tangents from.

- `bm_slab._box_uvs` now gives every slab one UV map, `UVMap`: 1 UV unit = 1 m, each face projected along its main axis, laid out as seen from outside. The slab is a whole 4 m wide, so a 1 m texture runs on across the seam.
- Gate B gained UV1 (one UV map), UV2 (no face has a zero-area UV) and UV3 (both survive the FBX round trip): **39/39**.
- Reimported over the same asset. No tangent or bi-normal warning since. Sockets, bounds and Nanite unchanged. The reimport brought a convex hull back, so collision was reset to the one box again. Gap 0, turn 0, seam 0 re-measured in `L_SlabV0_Proof`.

## Follow-up 2026-11-11: the window reveal faces the street

Jermaine: "Fix the window reveal so it faces the street."

- Cause: the shared wall code (`geometry_buildings.build_shell_wall`) treats +Y as outside, but a slab's street face is -Y. So each window's 1 cm glass box sat proud of the street face, and the 20 cm hole opened to the back.
- Fix, slab only: `bm_slab._glass_to_back` moves each glass box +20 cm in Y before the mesh is welded. The glass now sits at Y -0.01..0, inside the wall at the back, facing the street. Each window reads as a 19 cm deep reveal. The shared wall code and the block flow are not edited.
- **The window slab is now exactly 20 cm deep** (Y -0.2..0), like Solid and Door. This replaces the 11-10 "Keep it, 21 cm" depth, which only existed because the glass stuck out in front.
- Gate B: B1 now expects Y -0.2..0; new checks R1 (two glass faces at Y -0.01 facing the street) and R2 (nothing in front of the glass inside the openings). **41/41.** Run against the old code, B1, R1 and R2 fail (38/41), so the checks catch the old shape.
- Unreal: reimported over the same asset, no warnings in the log. Bounds 400 × 20 × 350, sockets L/R/U unchanged, Nanite on, 1 UV channel. Collision reset to the one box again. Gap 0, turn 0, seam 0 re-measured in `L_SlabV0_Proof`; level saved.
- Screenshots: `proof_refs/SlabV0_reveal_canon.png` and `SlabV0_reveal_close.png`, same cameras as before. Each window shows its jambs and head in shadow.
- Still open: Build Mode south walls use the same shared code, so their reveals still open inward. That is block-flow code, left alone here. *Fixed later 11-11, see below.*

## Follow-up 2026-11-11: Build Mode reveals face the street too

Jermaine: "Fix the Build Mode south walls too."

- Cause: `build_shell_wall` guessed the street side. Axis X walls always used +Y, which is wrong for every south wall. Axis Y walls used -X only when the wall sat at world X < 0.1, which is wrong for any west wall away from the origin. Recessed and angled doors used the same guess.
- Fix: `build_shell_wall` takes `outward_sign` (+1 / -1 along the wall's depth axis). Build Mode (`bm_generate._build_face_wall`) passes it from the block face: north/east +1, south/west -1. Window reveals and door recesses open toward it. Build Mode and its live preview both go through this.
- With `outward_sign` set, the 1 cm glass box is tucked inside the wall like the slab's: glass 1 cm in from the inner face, a 19 cm reveal. Before, it stuck 1 cm into the room, and after the normal recalculation the glass faced the room on every side, including north and east. In Unreal that back face is culled, so from the street you would see through it. Now it faces the street.
- Callers that do not pass `outward_sign` (parametric shell, its preview, the slab) keep the old maths unchanged. Slab Gate B still 41/41.
- New `tests/test_buildmode_reveal.py`: block A at the origin and B at (10, 6), all four faces WINDOW (16 windows), checked on Generate and on the live preview; block C, recessed doors (inset 0.1) on south and west, checked on Generate (the preview builds flat doors). **67/67.** Run against the old code: 21/67.
- Not touched: chamfer (diagonal) walls (`build_angled_wall`). Reading the code, their glass sits flush on the outer face (not measured). *Measured and fixed later 11-11, see below.* Not checked in Unreal: no Build Mode building is in the game repo to reimport.

## Follow-up 2026-11-11: chamfer walls face the street too

Jermaine: "Fix the chamfer wall windows too."

- Measured on the old code: each diagonal window's glass was one face flush on the street face (offset +0.100 from the wall's centre line), with the full 20 cm hole behind it opening to the room. Recessed doors on diagonals opened toward the room (jambs at -0.050).
- Cause: `build_angled_wall` calls the left of start->end its "outer" side. Build Mode's perimeter runs counter-clockwise, so the left side is the room.
- Fix: `build_angled_wall` takes `outward_sign` (+1 = left of start->end, -1 = right). Build Mode (`bm_generate._build_block_walls`) passes the side facing away from the block centre. With it set, the window gets the same 1 cm glass box as the straight walls: glass 1 cm in from the inner face (19 cm reveal), facing the street. Recessed and angled door jambs open toward the street.
- Callers that do not pass `outward_sign` (the parametric shell's corner cut and its preview) keep the old maths unchanged.
- `tests/test_buildmode_reveal.py` gained block D (6 × 6 m, all four corners cut 1.5 m, all WINDOW) and block E (same, all DOOR, recessed inset 0.1). Diagonal glass at -0.090 facing the street, nothing on the street half, door jambs at +0.050, on Generate and the live preview (doors Generate only). **87/87.** Run against the old code: 67/87, all 20 new checks fail. Slab Gate B still 41/41.
- Not checked in Unreal, for the same reason as above.

## Not done

- The `U` socket arrived and checked, but nothing snaps to it in v0, as the spec says.
- The Unreal assets are on disk in the game repo but **not committed**: `Content/ER_Test/WBTK_SlabV0/`, `Content/ER_Test/L_SlabV0_Proof.umap`. The main folder is on `bodykit-v1`, so where they land is Jermaine's call.
