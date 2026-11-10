# World_Building_Toolkit/bm_slab.py
# Slab v0 - the bridge proof. Spec: CLAUDE_SLAB_V0_SPEC.md (approved 2026-11-08).
#
# One wall slab, one bay by one storey, with its joints stamped as SOCKET_
# empties, exported so Unreal reads the joints as static-mesh sockets. Additive:
# the block flow (Add / Stack / Attach, per-wall types, Generate) is untouched,
# and bm_generate is imported, never edited.
#
# Slab-local frame (metres, 1 BU = 1 m, scene scale 1.0):
#   X 0 -> 4.0 along the wall, left end as seen from the street
#   Y -0.2 -> 0, the street face points -Y, the back face sits on Y = 0
#   Z 0 -> 3.5
#   origin = back-bottom-left = the L joint
#
# Measured 2026-11-10 on Blender 5.2.2: the WINDOW slab's glass is a 1 cm box
# that sits proud of the street face (Y -0.20 -> -0.21), the same as today's
# Build Mode south walls. SOLID and DOOR fill Y -0.2 -> 0 exactly.

import contextlib
import os

import bpy
import bmesh
from mathutils import Matrix

from .config import Config
from .utils import Utils
from . import bm_generate


SLAB_KEY = "wbtk_slab"            # on the slab mesh object: its wall type
SOCKET_KEY = "wbtk_slab_socket"   # on each joint empty: "L" / "R" / "U"

_TYPE_LABEL = {'SOLID': "Solid", 'WINDOW': "Window", 'DOOR': "Door"}


def _dims():
    return Config.SLAB_BAY_WIDTH, Config.WALL_THICKNESS, Config.DEFAULT_WALL_HEIGHT


def slab_name(wtype):
    """SM_DW_WallSlab_<Type>_<W>x<H>_A, sizes in cm (naming standard SM_[Region]_[Type]_[DimCm]_[Variant])."""
    w, _t, h = _dims()
    return "SM_DW_WallSlab_%s_%dx%d_A" % (_TYPE_LABEL[wtype], round(w * 100), round(h * 100))


def socket_layout():
    """(key, slab-local position) for the three joints, spec section 1."""
    w, _t, h = _dims()
    return (("L", (0.0, 0.0, 0.0)),    # grab point: where this slab attaches to a neighbour
            ("R", (w, 0.0, 0.0)),      # drop spot: where the next slab's L lands
            ("U", (0.0, 0.0, h)))      # storey above; stamped for arrival only in v0


def is_slab(obj):
    return obj is not None and obj.type == 'MESH' and SLAB_KEY in obj


def slab_sockets(slab):
    """The slab's own joint empties, keyed "L" / "R" / "U"."""
    return {c[SOCKET_KEY]: c for c in slab.children
            if c.type == 'EMPTY' and SOCKET_KEY in c}


def _remove_slab(slab):
    """Remove a slab, its joint empties and its mesh data."""
    for e in slab_sockets(slab).values():
        bpy.data.objects.remove(e, do_unlink=True)
    mesh = slab.data
    bpy.data.objects.remove(slab, do_unlink=True)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def build_slab(scene, wtype):
    """Build (or rebuild) the slab for wtype. Returns (slab, error)."""
    if wtype not in _TYPE_LABEL:
        return None, "Unknown wall type '%s'" % wtype
    name = slab_name(wtype)

    old = bpy.data.objects.get(name)
    if old is not None:
        if not is_slab(old) or old.library is not None:
            return None, ("'%s' already exists and is not a WBTK slab - rename or remove it first."
                          % name)
        _remove_slab(old)
    # an orphaned mesh with the name would push ours to .001
    stale = bpy.data.meshes.get(name)
    if stale is not None and stale.users == 0:
        bpy.data.meshes.remove(stale)

    from .geometry_buildings import GeometryBuildings
    w, t, h = _dims()
    door_style = getattr(scene, 'wbtk_building_door_style', 'RECESSED')
    door_in = getattr(scene, 'wbtk_building_door_inset', 0.2)
    door_sp = getattr(scene, 'wbtk_building_door_splay', 30.0)

    bm = bmesh.new()
    try:
        # build_shell_wall centres the thickness on its Y argument, so -t/2 puts
        # the back face on Y = 0 and the street face on Y = -t.
        bm_generate._build_face_wall(bm, GeometryBuildings, 0.0, -t / 2.0, 0.0, w, h, t, 'X',
                                     wtype, door_style, door_in, door_sp)
        # Same cleanup as every Build Mode building (OP_GenerateBuildingShell._finalize_bm).
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.005)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
    finally:
        bm.free()

    slab = bpy.data.objects.new(name, mesh)
    slab[SLAB_KEY] = wtype
    Utils.link_to_collection(slab, Config.SLAB_COLLECTION)
    mat = Utils.get_or_create_material(Config.MATERIAL_WALL)
    if mat:
        mesh.materials.append(mat)

    coll = bpy.data.collections.get(Config.SLAB_COLLECTION)
    for key, pos in socket_layout():
        e = bpy.data.objects.new("SOCKET_" + key, None)
        e.empty_display_type = 'PLAIN_AXES'
        e.empty_display_size = 0.25
        e[SOCKET_KEY] = key
        e.parent = slab
        e.matrix_parent_inverse = Matrix.Identity(4)
        e.location = pos
        e.rotation_euler = (0.0, 0.0, 0.0)
        e.scale = (1.0, 1.0, 1.0)
        (coll or scene.collection).objects.link(e)
    return slab, None


@contextlib.contextmanager
def _exact_socket_names(slab):
    """Give the slab's joints their exact SOCKET_<x> names for the export, then restore.

    Object names are unique per file, so a second slab's joints come out as
    SOCKET_L.001 and Unreal would name that socket "L.001". Whoever holds the
    exact name is parked on a temporary name and gets it back afterwards.
    """
    renamed = []   # (object, original name), in rename order
    try:
        for key, e in slab_sockets(slab).items():
            want = "SOCKET_" + key
            if e.name == want:
                continue
            holder = bpy.data.objects.get(want)
            if holder is not None:
                renamed.append((holder, holder.name))
                holder.name = "_WBTK_park_" + want
            renamed.append((e, e.name))
            e.name = want
        yield
    finally:
        # Free every name first, then put the originals back.
        for obj, _orig in renamed:
            obj.name = "_WBTK_tmp_" + obj.name
        for obj, orig in renamed:
            obj.name = orig


def export_dir():
    return os.path.join(os.path.dirname(bpy.data.filepath), "UE_Export", "WBTK_Slabs")


def export_slab(context, slab):
    """Write <blend folder>/UE_Export/WBTK_Slabs/<name>.fbx. Returns (path, error)."""
    if not bpy.data.filepath:
        return None, "Save the .blend first - the slab FBX goes next to it in UE_Export/WBTK_Slabs."
    sockets = slab_sockets(slab)
    missing = [k for k, _p in socket_layout() if k not in sockets]
    if missing:
        return None, "'%s' is missing joint(s) %s - run Generate Slab again." % (slab.name, ", ".join(missing))

    out_dir = export_dir()
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, slab.name + ".fbx")

    for o in list(context.selected_objects):
        o.select_set(False)
    slab.select_set(True)
    for e in sockets.values():
        e.select_set(True)
    context.view_layer.objects.active = slab

    with _exact_socket_names(slab):
        # Settings ratified at operators_ue_pipeline.py:533. No path_mode.
        bpy.ops.export_scene.fbx(
            filepath=path, use_selection=True, object_types={'MESH', 'EMPTY'},
            apply_scale_options='FBX_SCALE_NONE', bake_space_transform=True,
            mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False,
            use_metadata=False)
    if not os.path.exists(path):
        return None, "The FBX exporter reported no error but wrote no file at %s" % path
    return path, None


class OP_GenerateSlab(bpy.types.Operator):
    """Build one 400 x 350 cm wall slab of the chosen type, with its L / R / U joints"""
    bl_idname = "wbtk.bm_generate_slab"
    bl_label = "Generate Slab"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        wtype = getattr(scene, 'wbtk_slab_wall_type', 'WINDOW')
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, "Switch to Object Mode first.")
            return {'CANCELLED'}
        slab, err = build_slab(scene, wtype)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        for o in list(context.selected_objects):
            o.select_set(False)
        slab.select_set(True)
        context.view_layer.objects.active = slab
        self.report({'INFO'}, "Built '%s' with joints L, R, U." % slab.name)
        return {'FINISHED'}


class OP_ExportSlab(bpy.types.Operator):
    """Export the active slab (or the slab of the chosen type) with its three joints, for Unreal"""
    bl_idname = "wbtk.bm_export_slab"
    bl_label = "Export Slab"
    bl_options = {'REGISTER'}

    def execute(self, context):
        slab = context.active_object
        if not is_slab(slab):
            wtype = getattr(context.scene, 'wbtk_slab_wall_type', 'WINDOW')
            slab = bpy.data.objects.get(slab_name(wtype))
        if not is_slab(slab):
            self.report({'ERROR'}, "No slab to export - click Generate Slab first.")
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, "Switch to Object Mode first.")
            return {'CANCELLED'}
        path, err = export_slab(context, slab)
        if err:
            self.report({'ERROR'}, err)
            return {'CANCELLED'}
        self.report({'INFO'}, "Exported '%s' -> %s (%d bytes)"
                    % (slab.name, path, os.path.getsize(path)))
        return {'FINISHED'}


_classes = (
    OP_GenerateSlab,
    OP_ExportSlab,
)
