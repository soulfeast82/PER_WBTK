# World_Building_Toolkit/operators_build_engine.py
#
# Engine Summon - QUEUED item #4, and pivot item #3 (Region DNA as kit switcher).
#
# One button that turns a Build Mode footprint into a Dusk Ward building. It
# appends Buildify's `building` node group, builds the module collections it
# reads, fills them from the DW kit, attaches the modifier and sets the Scale
# Bible numbers.
#
# WHY THIS EXISTS: Build Mode's own Generate makes a parametric box. That is the
# massing preview, not the deliverable. The kit is where the concept-art look
# lives, and Buildify is what tiles it. Until now, wiring the two together was a
# manual append-and-configure dance, so nobody did it and the box was what people
# saw.
#
# HOW BUILDIFY BINDS A KIT (measured 2026-08-26 from buildify_1.0.blend, not
# guessed): the `building` modifier exposes only Base geometry, floor counts and
# Module width/height. The kit is bound INSIDE the tree, on collection sockets of
# four group nodes. Eleven sockets in total, listed in _SOCKET_MAP below. That is
# why the pivot calls the kit switcher "collection swapping, not node surgery".
#
# WHAT BUILDIFY CAN AND CANNOT PLACE - the honest boundary:
#
#   INCLUDED   walls .......... ground_floor_walls / middle_floor_walls
#              pillars ........ ground_floor_pillars / middle_floor_pillars
#              trim ........... trim / top_trim_pillars
#              rooftop props .. rooftop_details small / medium / large
#
#   NOT INCLUDED, and not a defect - these have no slot in the engine:
#              cantilevers .... facade accretion volumes. Buildify tiles edges;
#                               it has no concept of a mass hung off a facade.
#              streetlight .... street furniture, not a building part at all.
#              barrier, cables, railings, stairs, catwalks, gratings - same.
#              These stay hand-placed, or go to BagaPie scatter later.
#
#   DELIBERATELY LEFT EMPTY: details_first_floor / details_other_floor. Those are
#   Buildify's WALL PROPS, and its own library fills them with street signs and
#   satellite dishes - things scattered ONTO a facade at semi-random positions.
#   Our window and door inserts are not that: an insert seats in its host
#   opening at local (0, 0, +92), 3 cm proud. Scattering them would put windows
#   in the middle of blank walls. The right home for an insert is a COMBINED
#   wall+insert module in the wall collection. That is an authoring decision, so
#   this operator does not pretend to make it - see the report it prints.

import os
import bpy

from .config import Config

_BUILDIFY_REL = os.path.join("..", "Buildify_1.0", "buildify_1.0.blend")
_KIT_REL = os.path.join("..", "..", "Meshes", "PER_DW_Kit.blend")

_NODE_GROUP = "building"
# Where the raw modules live so they do not render as loose objects in the scene.
_MODULE_HOST = "DW_BuildEngine_Modules"

# Scale Bible: wall module 400 x 350, storey 350 LOCKED.
_MODULE_WIDTH = 4.0
_MODULE_HEIGHT = 3.5

# The eleven collection sockets, measured off the shipped node tree.
# (group-node tree name, socket name) -> Buildify collection name
_SOCKET_MAP = {
    ("Walls", "Wall modules"):   ["ground_floor_walls", "middle_floor_walls", "trim"],
    ("Walls", "Pillar modules"): ["ground_floor_pillars", "middle_floor_pillars", "top_trim_pillars"],
    ("Wall props", "Collection"): ["details_first_floor", "details_other_floor"],
    ("Flat roof", "Details small"):  ["rooftop_details _small"],
    ("Flat roof", "Details medium"): ["rooftop_details_medium"],
    ("Flat roof", "Details big"):    ["rooftop_details_large"],
}

# Which kit meshes fill which Buildify collection.
# Ground floor gets the door; upper floors do not - a door on floor three reads as
# an error, and Buildify picks one module per edge at random from what it is given.
_KIT_MAP = {
    # COMBINED wall+infill modules [RATIFIED 2026-08-26]. The bare walls are NOT used
    # here: Buildify places one module per edge and never seats an insert, so a bare
    # wall tiles as a HOLE. The plain wall stays in the list as the accretion ruling's
    # "bricked-up" state, which is the one case where no opening is correct.
    #
    # Ground floor reads as occupied - door, glazing, and some blank frontage. Upper
    # floors carry the full infill spread, which is how the accretion ruling's "no two
    # bays identical" gets enforced by the engine rather than by anyone remembering it.
    "ground_floor_walls": ["SM_DW_BfyWall_Door_400x350_A",
                           "SM_DW_BfyWall_WinClosed_400x350_A",
                           "SM_DW_BfyWall_PairClosed_400x350_A",
                           "SM_DW_Wall_400x350_A"],
    "middle_floor_walls": ["SM_DW_BfyWall_WinClosed_400x350_A",
                           "SM_DW_BfyWall_WinBoarded_400x350_A",
                           "SM_DW_BfyWall_WinShuttered_400x350_A",
                           "SM_DW_BfyWall_WinTarped_400x350_A",
                           "SM_DW_BfyWall_WinOpen_400x350_A",
                           "SM_DW_BfyWall_PairClosed_400x350_A",
                           "SM_DW_BfyWall_PairMixed_400x350_A",
                           "SM_DW_BfyWall_PairBoarded_400x350_A",
                           "SM_DW_Wall_400x350_A"],
    "ground_floor_pillars": ["SM_DW_Pillar1Flat_100x350_A", "SM_DW_Pillar2CC_100x350_A",
                             "SM_DW_Pillar3CV_100x350_A"],
    "middle_floor_pillars": ["SM_DW_Pillar1Flat_100x350_A", "SM_DW_Pillar2CC_100x350_A",
                             "SM_DW_Pillar3CV_100x350_A"],
    "trim": ["SM_DW_TopTrim_400x50_A"],
    "top_trim_pillars": ["SM_DW_TrimPillar1Flat_100x50_A", "SM_DW_TrimPillar2CC_100x50_A",
                         "SM_DW_TrimPillar3CV_100x50_A"],
    # Rooftop props, split by footprint so Buildify's size buckets read sensibly.
    "rooftop_details _small": ["SM_DW_RoofVent_50x60_A", "SM_DW_Antenna2Dish_100_A"],
    "rooftop_details_medium": ["SM_DW_RoofVent_80x100_A", "SM_DW_ACUnit_100x80_A",
                               "SM_DW_Antenna3Array_200_A"],
    "rooftop_details_large": ["SM_DW_TankBody_150x200_A", "SM_DW_TankLegs_150x100_A",
                              "SM_DW_Antenna1Mast_300_A"],
    # See the module header: left empty on purpose.
    "details_first_floor": [],
    "details_other_floor": [],
}

# Pillar order must be flat -> CC -> CV when sorted ALPHABETICALLY, because
# Collection Info sorts children by name. The ordinals in the kit names already
# satisfy this; the Kit Validator enforces it.


def _addon_dir():
    """The addon's REAL directory, following the symlink.

    WBTK is installed by symlinking Blender's addons folder at the repo copy, so
    abspath(__file__) reports the AppData path and '..' lands in scripts/addons
    rather than Blender_Plugins. realpath follows the link to the repo, which is
    where Buildify and the kit actually live. Found by running the operator.
    """
    return os.path.dirname(os.path.realpath(__file__))


# Meshes Summon must never build on. Build Mode blocks, the grid, detail stamps
# and the live-preview mesh are WBTK's own scaffolding; SM_DW_* are the kit
# modules themselves. All of them are meshes, so `type == 'MESH'` alone accepts
# them - which is how a Summon landed on WBTK_BM_0001 on 2026-09-05: 26 instances
# on a helper block and three kit modules dragged off the origin.
# WBTK_BFY_ is deliberately NOT here: the footprint is the intended target.
_NEVER_TARGET_PREFIXES = ("WBTK_BM_", "WBTK_DTL_", "_WBTK_", "WBTK_Live_Preview", "SM_DW_")


def _is_summon_target(obj):
    """A mesh that is neither WBTK scaffolding nor a kit module."""
    if obj is None or obj.type != 'MESH':
        return False
    return not obj.name.startswith(_NEVER_TARGET_PREFIXES)


def _get_or_make_collection(name, host):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    if host is not None and coll.name not in host.children:
        try:
            host.children.link(coll)
        except RuntimeError:
            pass  # already parented somewhere; harmless
    if host is not None and coll.name in host.children:
        # The host is the ONE parent. Appending the `building` node group drags
        # Buildify's own collections in through its socket defaults, linked at the
        # scene root - measured 2026-09-05: eleven root-level collections after
        # one Summon, every module rendered loose beside the building as well as
        # hidden under the host. Unlink only once the host link is confirmed, so a
        # collection is never left with no parent at all (a parentless collection
        # is outside the depsgraph and Collection Info reads it as empty).
        for scene in bpy.data.scenes:
            if coll.name in scene.collection.children:
                try:
                    scene.collection.children.unlink(coll)
                except RuntimeError:
                    pass  # linked-library scene; leave it
        for other in bpy.data.collections:
            if other is not host and coll.name in other.children:
                try:
                    other.children.unlink(coll)
                except RuntimeError:
                    pass  # linked-library collection; leave it
    return coll


class OP_SummonBuildEngine(bpy.types.Operator):
    """Wire Buildify to the Dusk Ward kit and drive it from the selected footprint"""
    bl_idname = "wbtk.summon_build_engine"
    bl_label = "Summon Build Engine"
    bl_description = ("Append Buildify's building node group, fill its module collections "
                      "from the Dusk Ward kit, and attach it to the selected footprint")
    bl_options = {'REGISTER', 'UNDO'}

    def _append_node_group(self, report):
        if _NODE_GROUP in bpy.data.node_groups:
            report.append("node group '%s' already present" % _NODE_GROUP)
            return bpy.data.node_groups[_NODE_GROUP]
        path = os.path.normpath(os.path.join(_addon_dir(), _BUILDIFY_REL))
        if not os.path.exists(path):
            self.report({'ERROR'}, "Buildify library not found at %s" % path)
            return None
        bpy.ops.wm.append(filepath=os.path.join(path, "NodeTree", _NODE_GROUP),
                          directory=os.path.join(path, "NodeTree") + os.sep,
                          filename=_NODE_GROUP)
        ng = bpy.data.node_groups.get(_NODE_GROUP)
        report.append("appended '%s' from buildify_1.0.blend" % _NODE_GROUP if ng
                      else "FAILED to append '%s'" % _NODE_GROUP)
        return ng

    def _append_kit(self, wanted, report):
        missing = [n for n in wanted if n not in bpy.data.objects]
        if not missing:
            report.append("kit already in this file (%d modules)" % len(wanted))
            return
        path = os.path.normpath(os.path.join(_addon_dir(), _KIT_REL))
        if not os.path.exists(path):
            self.report({'ERROR'}, "Kit not found at %s" % path)
            return
        directory = os.path.join(path, "Object") + os.sep
        for name in missing:
            try:
                bpy.ops.wm.append(filepath=os.path.join(path, "Object", name),
                                  directory=directory, filename=name,
                                  do_reuse_local_id=True)
            except RuntimeError as exc:
                report.append("could not append %s: %s" % (name, exc))
        got = sum(1 for n in missing if n in bpy.data.objects)
        report.append("appended %d/%d missing kit modules" % (got, len(missing)))

    def _fill_collections(self, host, report):
        empties = []
        for coll_name, members in _KIT_MAP.items():
            coll = _get_or_make_collection(coll_name, host)
            # clear so a re-run is idempotent rather than additive
            for obj in list(coll.objects):
                coll.objects.unlink(obj)
            for name in members:
                obj = bpy.data.objects.get(name)
                if obj is None:
                    continue
                if obj.name not in coll.objects:
                    coll.objects.link(obj)
                # A module must not ALSO sit in a scene collection, or it renders
                # as a loose object beside the building. But it may legitimately
                # belong to several BUILDIFY collections at once - the plain wall
                # is both a ground-floor and a middle-floor module, and the
                # pillars are in both pillar sets. Unlinking from "everything
                # else" wiped exactly those, which is why the first run left
                # ground_floor_pillars empty and Buildify emitted nothing.
                for other in list(obj.users_collection):
                    if other is not coll and other.name not in _KIT_MAP:
                        other.objects.unlink(obj)
            if not coll.objects:
                empties.append(coll_name)
        if empties:
            report.append("left empty (by design): %s" % ", ".join(sorted(empties)))

    def _bind_sockets(self, ng, report):
        bound, unbound = 0, []
        for node in ng.nodes:
            if node.bl_idname != 'GeometryNodeGroup' or not node.node_tree:
                continue
            for sock in node.inputs:
                if sock.bl_idname != 'NodeSocketCollection':
                    continue
                key = (node.node_tree.name, sock.name)
                if key not in _SOCKET_MAP:
                    continue
                current = getattr(sock, "default_value", None)
                # keep whichever of this socket's candidate collections it already
                # points at - that is how ground/middle/trim tell each other apart
                target = current.name if current else None
                if target not in _SOCKET_MAP[key]:
                    unbound.append("%s.%s" % key)
                    continue
                coll = bpy.data.collections.get(target)
                if coll:
                    sock.default_value = coll
                    bound += 1
        report.append("bound %d collection socket(s)" % bound)
        if unbound:
            report.append("could not identify: %s" % ", ".join(unbound))

    def execute(self, context):
        from .operators_buildify import FOOTPRINT_NAME
        target = context.active_object
        if not _is_summon_target(target):
            footprint = bpy.data.objects.get(FOOTPRINT_NAME)
            if _is_summon_target(footprint):
                why = ("No usable mesh active" if target is None or target.type != 'MESH'
                       else "'%s' is WBTK scaffolding or a kit module, not a footprint" % target.name)
                self.report({'INFO'}, "%s - using '%s'." % (why, FOOTPRINT_NAME))
                target = footprint
            else:
                self.report({'ERROR'}, "Select the footprint mesh first "
                                       "(run 'Export Footprints for Buildify' if you have none).")
                return {'CANCELLED'}

        report = []
        ng = self._append_node_group(report)
        if ng is None:
            return {'CANCELLED'}

        wanted = sorted({n for members in _KIT_MAP.values() for n in members})
        self._append_kit(wanted, report)

        host = _get_or_make_collection(_MODULE_HOST, None)
        if host.name not in {c.name for c in context.scene.collection.children}:
            context.scene.collection.children.link(host)
        host.hide_viewport = True
        host.hide_render = True

        self._fill_collections(host, report)
        self._bind_sockets(ng, report)

        mod = None
        for m in target.modifiers:
            if m.type == 'NODES' and m.node_group is ng:
                mod = m
                break
        if mod is None:
            mod = target.modifiers.new(name="DW_BuildEngine", type='NODES')
            mod.node_group = ng
            report.append("attached modifier to '%s'" % target.name)
        else:
            report.append("modifier already on '%s' - reused" % target.name)

        # Scale Bible numbers, and floor randomising OFF so building:levels rules.
        for item in ng.interface.items_tree:
            if getattr(item, "in_out", None) != 'INPUT':
                continue
            if item.name == "Module width":
                mod[item.identifier] = _MODULE_WIDTH
            elif item.name == "Module height":
                mod[item.identifier] = _MODULE_HEIGHT
            elif item.name.strip().startswith("- Randomize floor numbers"):
                mod[item.identifier] = False
        report.append("module %.1f x %.1f m, floor randomising off" % (_MODULE_WIDTH, _MODULE_HEIGHT))

        target.update_tag()
        context.view_layer.update()

        print("\n--- WBTK Summon Build Engine ---")
        for line in report:
            print("  " + line)
        print("  NOT placed by Buildify (no slot in the engine): cantilevers, streetlight,")
        print("  barrier, cables, railings, stairs, catwalks, gratings - hand-place those.")
        print("--- end ---\n")

        self.report({'INFO'}, "Build Engine summoned on '%s'. See Console for details."
                    % target.name)
        return {'FINISHED'}


# --- List of Operator Classes to Register from THIS file ---
_classes_to_register = (
    OP_SummonBuildEngine,
)
