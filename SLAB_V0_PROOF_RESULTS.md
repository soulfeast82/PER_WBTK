# Slab v0: proof results (2026-11-10)

Spec: `CLAUDE_SLAB_V0_SPEC.md`. Blender 5.2.2 LTS, Unreal 5.8.4. **The joint road holds:** every gate passed.

## Gate B (Blender, `tests/test_slab_v0.py`): 36/36

- Window slab bounds X 0..4.0, Y -0.21..0, Z 0..3.5 m. The 21 cm depth was ruled 11-10 ("Keep it, 21 cm"): the glass sits 1 cm proud of the street face.
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

**Seen, not ruled:** from the street the windows barely read. The existing wall code puts the reveal on the back face, so the street side is flush glass in the same material. This needs a decision before slabs become real kit pieces.

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

## Not done

- The `U` socket arrived and checked, but nothing snaps to it in v0, as the spec says.
- The Unreal assets are on disk in the game repo but **not committed**: `Content/ER_Test/WBTK_SlabV0/`, `Content/ER_Test/L_SlabV0_Proof.umap`. The main folder is on `bodykit-v1`, so where they land is Jermaine's call.
