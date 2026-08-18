# World_Building_Toolkit/operators_buildify.py
# WBTK -> Buildify bridge.
#
# Exports Build Mode block footprints as flat base geometry for Buildify's
# `building` geometry-node modifier, with the `building:levels` vertex group
# Buildify reads to decide floor counts.
#
# Contract + rationale: _gamedocs/BUILDIFY_INTEGRATION_v1.md

import math

import bpy
import bmesh

from .config import Config
from .utils import Utils
from . import bm_data

FOOTPRINT_NAME = "WBTK_BFY_Footprint"

# Buildify reads this vertex group by exact name. Do not rename.
LEVELS_VGROUP = "building:levels"

# Buildify stores floor count as weight = floors / 100, so 100 is the ceiling.
LEVELS_DIVISOR = 100.0

# ⚠️ CALIBRATION (measured 2026-08-09, do not "simplify" this away).
# The declared level count is NOT the number of wall storeys placed. Buildify's
# stock `building` setup runs its Walls node with "remove from top" = 1, which
# reserves the top level, so:
#
#     wall storeys placed = declared - 1        (declared >= 2)
#
# Measured on two stacked 4x4 footprints (8 wall modules per storey):
#     declared  1  2  3  4  6
#     walls     8  8 16 24 40   -> storeys 1 1 2 3 5
#
# Emptying the trim collection did NOT change this, so the reserved level is the
# Walls node's own behaviour, not the trim occupying a tier. If anyone rewires
# the node group's remove-from-top, re-measure and change this constant.
TOP_LEVEL_RESERVED = 1

# Declared value is capped at 100 by the /100 encoding, so real storeys cap one
# lower.
MAX_FLOORS = 100 - TOP_LEVEL_RESERVED

# Buildify's own documented workaround for overlapping base-geometry edges,
# which otherwise flip wall orientation with no error. Adjacent Build Mode
# blocks that belong to DIFFERENT buildings would share exact coordinates, so
# each building is shrunk toward its own centroid by this much. 10 microns.
NUDGE_M = 1e-5

# Coincident verts WITHIN one building are welded instead, which removes the
# shared edge entirely rather than hiding it.
WELD_DIST = 1e-4

# Ruled 2026-08-08: Buildify buildings use one module, 400x350. Footprint runs
# that are not multiples of the module width get stretched modules.
BFY_MODULE_WIDTH = 4.0
EDGE_TOL = 1e-3


def _block_perimeter(b):
    """Footprint outline of one block, honouring chamfers.

    NOTE: mirrors the perimeter maths in bm_generate._build_block_walls. Kept
    local so the working generate path is not touched by this new operator.
    Fold both onto a shared helper in bm_data once this is viewport-verified.
    """
    bx, by = b['x0'], b['y0']
    w, d = b['w'], b['d']
    chamfers = b['data'].get("chamfers", [])
    cs = b['data'].get("chamfer_size", 1.0)

    corners = [(bx, by), (bx + w, by), (bx + w, by + d), (bx, by + d)]
    names = ["sw", "se", "ne", "nw"]
    if not chamfers:
        return corners

    per = []
    for ci in range(4):
        cx, cy = corners[ci]
        if names[ci] in chamfers:
            px, py = corners[(ci - 1) % 4]
            nx, ny = corners[(ci + 1) % 4]
            dpx, dpy = px - cx, py - cy
            dnx, dny = nx - cx, ny - cy
            dl_p = math.sqrt(dpx * dpx + dpy * dpy)
            dl_n = math.sqrt(dnx * dnx + dny * dny)
            if dl_p > 0.01 and dl_n > 0.01:
                c = min(cs, dl_p * 0.49, dl_n * 0.49)
                per.append((cx + dpx / dl_p * c, cy + dpy / dl_p * c))
                per.append((cx + dnx / dl_n * c, cy + dny / dl_n * c))
            else:
                per.append((cx, cy))
        else:
            per.append((cx, cy))
    return per


def _floors_for(b, floor_h):
    """Block height -> Buildify floor count."""
    h = float(b.get('h', 0.0) or 0.0)
    if floor_h <= 0.0:
        return 1
    return max(1, min(MAX_FLOORS, int(round(h / floor_h))))


def _declared_levels(floors):
    """Wall storeys wanted -> the level count Buildify must be told.

    Buildify reserves the top level (see TOP_LEVEL_RESERVED), so asking for N
    storeys means declaring N + 1. Kept as its own function so the calibration
    can be tested without a scene.
    """
    return min(100, max(1, int(floors)) + TOP_LEVEL_RESERVED)


def _group_key(b, floor_h):
    """Blocks merge into one building only if they share an elevation AND a
    floor count. Same elevation but different heights are genuinely different
    buildings, and Buildify needs them as separate geometry."""
    return (round(float(b['z0']), 4), _floors_for(b, floor_h))


def _build_group(blocks, z):
    """One building: block rectangles -> welded, dissolved outline."""
    bm = bmesh.new()
    for b in blocks:
        pts = _block_perimeter(b)
        if len(pts) < 3:
            continue
        try:
            bm.faces.new([bm.verts.new((p[0], p[1], z)) for p in pts])
        except ValueError:
            pass  # duplicate face, harmless
    # ORDER MATTERS — all four steps, in this sequence.
    #
    # 1. Subdivide FIRST. Abutting blocks of different widths make T-junctions:
    #    an 8m block edge has no vertex where a neighbouring 4m block ends, so
    #    the two faces share a point rather than an edge and never merge, and
    #    you are left with overlapping collinear edges — Buildify's bug, again.
    #    Cutting to module spans first puts a vertex at every module boundary so
    #    the abutting edges actually line up.
    _subdivide_to_module(bm)
    # 2. Weld those now-aligned verts.
    if bm.verts:
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=WELD_DIST)
    # 3. Merge coplanar neighbours; this is what removes the shared edge.
    #    use_verts=False — with True it also dissolves the collinear
    #    module-boundary verts we just created, undoing step 1.
    if bm.faces:
        bmesh.ops.dissolve_faces(bm, faces=bm.faces[:], use_verts=False)
    # 4. Anything still shared by two faces.
    interior = [e for e in bm.edges if len(e.link_faces) > 1]
    if interior:
        bmesh.ops.dissolve_edges(bm, edges=interior, use_verts=False)
    return bm


def _subdivide_to_module(bm):
    """Cut every outline edge down to module-width spans.

    ⚠️ Buildify places ONE wall module per EDGE and stretches it to fit — it
    does not tile modules along a long edge. Measured 2026-08-09: an 8 m edge
    against a 4 m module produced a single wall at 1.75x width, not two walls.
    The manual says the same thing ("if the stretching is very noticeable, I
    suggest making an edge loop or subdividing the edge").

    So a footprint being a multiple of the module width is necessary but NOT
    sufficient — the edges have to actually be cut. Without this, long walls
    ship with rivets and trim stretched well past what the 512 px/m texel
    ruling allows.
    """
    if not bm.edges:
        return
    by_cuts = {}
    for e in bm.edges:
        L = (e.verts[1].co - e.verts[0].co).length
        spans = int(round(L / BFY_MODULE_WIDTH))
        if spans >= 2 and abs(L) > EDGE_TOL:
            by_cuts.setdefault(spans - 1, []).append(e)
    # group by cut count: subdivide_edges takes one `cuts` value per call.
    # Note this can split a face (subdividing opposite edges of a quad adds a
    # connecting edge) — that is fine here, because _build_group dissolves
    # interior edges afterwards.
    for cuts, edges in sorted(by_cuts.items(), reverse=True):
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=False)


def _shrink_to_centroid(bm, amount):
    """Separate this building from any neighbour that touches it exactly."""
    if not bm.verts or amount <= 0.0:
        return
    n = len(bm.verts)
    cx = sum(v.co.x for v in bm.verts) / n
    cy = sum(v.co.y for v in bm.verts) / n
    for v in bm.verts:
        dx, dy = v.co.x - cx, v.co.y - cy
        L = math.hypot(dx, dy)
        if L > 1e-9:
            v.co.x -= dx / L * amount
            v.co.y -= dy / L * amount


def _non_module_edges(verts, faces):
    """Axis-aligned outline runs that are not multiples of the module width.
    Buildify stretches modules to fit, so these are a quality warning."""
    bad = 0
    seen = set()
    for f in faces:
        n = len(f)
        for i in range(n):
            a, b = f[i], f[(i + 1) % n]
            key = (min(a, b), max(a, b))
            if key in seen:
                continue
            seen.add(key)
            ax, ay, _ = verts[a]
            bx, by, _ = verts[b]
            dx, dy = abs(bx - ax), abs(by - ay)
            if dx < EDGE_TOL or dy < EDGE_TOL:      # axis-aligned run
                length = max(dx, dy)
                if length > EDGE_TOL:
                    rem = math.fmod(length + EDGE_TOL, BFY_MODULE_WIDTH)
                    if abs(rem - EDGE_TOL) > EDGE_TOL * 2:
                        bad += 1
    return bad


def _is_shared(me):
    """Is this mesh really used by more than one object?

    ⚠️ ID.users COUNTS THE FAKE USER (measured 2026-08-17, Blender 5.1). A bare
    `me.users > 1` therefore reads a shielded-but-unshared mesh as shared, and
    the shared-mesh path would fork it: the name drifts to "..._Mesh.001", the
    original is orphaned but pinned forever by its own shield, and -- the sharp
    end -- the new datablock does NOT inherit use_fake_user, so the protection
    the user explicitly asked for is silently removed.
    """
    if me is None:
        return False
    return (me.users - (1 if me.use_fake_user else 0)) > 1


class OP_ExportBuildifyFootprints(bpy.types.Operator):
    """Export Build Mode block footprints as flat base geometry for Buildify"""
    bl_idname = "wbtk.export_buildify_footprints"
    bl_label = "Export Footprints for Buildify"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        info = bm_data.all_bounds()
        if not info:
            self.report({'WARNING'}, "No Build Mode blocks to export.")
            return {'CANCELLED'}

        floor_h = getattr(Config, 'DEFAULT_WALL_HEIGHT', 3.5) or 3.5

        grouped = {}
        for b in info:
            grouped.setdefault(_group_key(b, floor_h), []).append(b)

        all_verts, all_faces, spans = [], [], []
        for (z, floors), blocks in sorted(grouped.items()):
            bm = _build_group(blocks, z)
            _shrink_to_centroid(bm, NUDGE_M)
            base = len(all_verts)
            idx = {}
            for i, v in enumerate(bm.verts):
                idx[v] = base + i
                all_verts.append((v.co.x, v.co.y, v.co.z))
            for f in bm.faces:
                all_faces.append([idx[v] for v in f.verts])
            if len(all_verts) > base:
                spans.append((base, len(all_verts), floors))
            bm.free()

        if not all_verts:
            self.report({'WARNING'}, "Blocks produced no footprint geometry.")
            return {'CANCELLED'}

        # ⚠️ UPDATE IN PLACE. Never delete and recreate this object.
        #
        # The user attaches Buildify's `building` geometry-nodes modifier to it
        # BY HAND and configures module width, module height and the floor
        # range on that modifier. The old code called bpy.data.objects.remove()
        # first, so every single re-export silently threw all of it away --
        # measured 2026-08-17 against the bench file: 1 modifier + 7 hand-set
        # input values + custom properties + display settings lost per run, and
        # the bench file had been committed with modifiers already empty
        # because of it. Rebuilding the mesh under the SAME object keeps the
        # object, and everything hanging off it survives.
        ob = bpy.data.objects.get(FOOTPRINT_NAME)
        if ob is not None and (ob.type != 'MESH' or ob.library is not None):
            self.report(
                {'ERROR'},
                "'%s' already exists as %s%s. Rename or remove it, then export "
                "again." % (FOOTPRINT_NAME, ob.type.lower(),
                            " linked from a library" if ob.library else " data"))
            return {'CANCELLED'}

        if ob is None:
            ob = bpy.data.objects.new(
                FOOTPRINT_NAME, bpy.data.meshes.new(FOOTPRINT_NAME + "_Mesh"))
            # ON CREATE ONLY. Utils.link_to_collection unlinks the object from
            # every collection but the target (utils.py), so running it on an
            # existing footprint would yank one the user had deliberately filed
            # somewhere else.
            Utils.link_to_collection(ob, Config.TARGET_COLLECTION)
        elif _is_shared(ob.data):
            # Mesh shared with another object -- clearing it would wipe their
            # geometry too. Give this one a private mesh instead; the OBJECT is
            # still reused, so the modifier is still safe.
            ob.data = bpy.data.meshes.new(FOOTPRINT_NAME + "_Mesh")
        else:
            ob.data.clear_geometry()

        ob.data.from_pydata(all_verts, [], all_faces)
        ob.data.update()
        ob.update_tag()

        # ⚠️ MEASURED 2026-08-17 on Blender 5.1: vertex groups live on the MESH
        # datablock now, so clear_geometry() (and a data swap) wipes ALL of them.
        # The .get() therefore always misses today and .new() always returns the
        # clean name. Keep the get-or-new form anyway: if a future Blender ever
        # preserves them, a bare .new() would hand back "building:levels.001",
        # and Buildify resolves this group BY NAME -- the export would report
        # success while driving nothing. Exactly the quiet failure this
        # integration is prone to, and it would cost a session to find.
        #
        # Side effect of the same fact: any OTHER vertex group a user put on the
        # footprint is lost on re-export. Not a regression (delete-and-recreate
        # lost them too) and the object is a generated artifact, so left alone.
        vg = (ob.vertex_groups.get(LEVELS_VGROUP)
              or ob.vertex_groups.new(name=LEVELS_VGROUP))
        declared_by_span = []
        for start, end, floors in spans:
            # +TOP_LEVEL_RESERVED so the storeys actually built match the block.
            # clear_geometry() dropped every old weight, so no stale assignment
            # from a longer previous export can survive this.
            declared = _declared_levels(floors)
            vg.add(list(range(start, end)), declared / LEVELS_DIVISOR, 'REPLACE')
            declared_by_span.append((floors, declared))

        stretched = _non_module_edges(all_verts, all_faces)
        self.report(
            {'INFO'},
            "Buildify footprint: %d building(s), %d verts, storeys %s "
            "(declared %s, +%d reserved top level)"
            % (len(spans), len(all_verts),
               ",".join(str(f) for f, _ in declared_by_span),
               ",".join(str(d) for _, d in declared_by_span),
               TOP_LEVEL_RESERVED))
        if stretched:
            self.report(
                {'WARNING'},
                "%d outline run(s) are not multiples of %.1fm - Buildify will "
                "stretch modules there." % (stretched, BFY_MODULE_WIDTH))
        if ob.name not in context.scene.objects:
            # Regression guard. The old delete-and-recreate always re-linked the
            # object into the target collection, so it could not end up outside
            # the scene. Reusing the object can -- if it lives only in another
            # scene, or in a collection linked to no scene, the export rebuilds
            # it perfectly and reports FINISHED while nothing appears here.
            # Deliberately NOT auto-relinked: Utils.link_to_collection unlinks
            # from every non-target collection, which would yank a footprint the
            # user deliberately filed elsewhere. Warn instead.
            self.report(
                {'WARNING'},
                "'%s' is not in the active scene - the export succeeded but "
                "nothing will appear here." % FOOTPRINT_NAME)
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


_classes_to_register = (
    OP_ExportBuildifyFootprints,
)
