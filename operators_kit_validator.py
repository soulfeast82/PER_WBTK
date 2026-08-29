# World_Building_Toolkit/operators_kit_validator.py
#
# Kit Validator - Strategic Pivot item #4.
#
# Enforces two rule sets, because the kit answers to two masters:
#
#   * Buildify's MODULE CONTRACT (_gamedocs/BUILDIFY_INTEGRATION_v1.md section 1) -
#     what a module must satisfy or Buildify silently builds the wrong thing.
#   * PER's own STANDING CHECKS - learned in the railing batch, where four meshes
#     shipped inside-out and watertight/dimensions/UE-import ALL passed.
#
# The signed-volume check is what earns this operator its place. It is the only
# check that catches inverted normals [RATIFIED 2026-08-24]. Reference value:
# SM_DW_Landing_200x200_A reads +0.8.
#
# RULES ARE APPLIED PER DESTINATION, which BUILDIFY_INTEGRATION_v1 section 1 rule 2
# demands - "the validator enforces per destination. Do not 'fix' one convention to
# match the other." Concretely:
#
#   * Pivot rules run ONLY on Buildify-destined modules. PIVOT LAW v2 is per-family,
#     and a cantilever hangs BELOW its attach point, a rail cap sits ON TOP of a post
#     and a railing starts above the floor. Failing those would be the validator
#     being wrong, not the mesh.
#   * The X-centred rule is enforced; the Y rule is REPORTED and never failed. Walls
#     carry a Y-back pivot while Buildify's manual says bottom-centre, and a complete
#     building has already generated from this kit - so Y-back demonstrably works.
#   * Signed volume is only meaningful on a CLOSED shell. On an open mesh the number
#     is arbitrary, so an open shell is reported as open and its volume is not judged.
#
# Not checkable here: contract 6 (module height is a modifier declaration), contract 7
# (flat base geometry - about footprints, not kit pieces), contract 8 (one style per
# object - a human judgement).

import bpy
import bmesh

# The ruled projection, imported rather than restated so the check and the tool that
# writes it cannot drift apart. A validator carrying its own copy of the convention
# would pass a mesh the operator can no longer produce.
from .operators_box_uv import _AXIS_MAP
from .operators_box_uv import DEFAULT_DIVISOR as _RULED_DIVISOR
from .operators_box_uv import DEFAULT_LAYER as _RULED_LAYER

# Pillar order Buildify requires, as it must appear when sorted ALPHABETICALLY. Link
# order is irrelevant - Collection Info sorts by name, which is why the ordinal in
# Pillar1Flat / Pillar2CC / Pillar3CV is load-bearing rather than cosmetic.
_PILLAR_ORDER = ("FLAT", "CC", "CV")

# The families Buildify actually consumes, per BUILDIFY_INTEGRATION_v1 section 4 item 2.
# Only these answer to the pivot half of the contract.
_BUILDIFY_TOKENS = ("WALL", "PILLAR", "TOPTRIM")

# Float32 vertex eps at ~2 m is ~0.12 um, so 0.1 mm sits well above the noise floor
# and well below any real authoring error.
_PIVOT_EPS = 1e-4
_XFORM_EPS = 1e-6

# UV spread below this in BOTH axes means every loop is effectively on one point.
_UV_EPS = 1e-6


def _face_components(bm):
    """Split a bmesh into edge-connected face groups.

    The kit's meshes are assemblies - a catwalk is a deck plus five separate boxes -
    and every watertightness question has to be asked of each piece on its own. Asking
    it of the object is what let 9 inverted components pass as clean.
    """
    seen, out = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, comp = [f], []
        seen.add(f.index)
        while stack:
            cf = stack.pop()
            comp.append(cf)
            for e in cf.edges:
                for nf in e.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index)
                        stack.append(nf)
        out.append(comp)
    return out


def _component_signed_volume(faces):
    """Signed volume of ONE component, via the divergence theorem over a fan.

    Not bmesh.calc_volume: that operates on the whole bmesh, which is the bug this
    replaces. Negative means the winding is inside-out.
    """
    total = 0.0
    for f in faces:
        vs = f.verts
        for i in range(1, len(vs) - 1):
            total += vs[0].co.dot(vs[i].co.cross(vs[i + 1].co)) / 6.0
    return total


def _is_buildify_module(name):
    upper = name.upper()
    return any(t in upper for t in _BUILDIFY_TOKENS)


def _pillar_rank(name):
    """FLAT/CC/CV rank from an object name, or -1 if it is not a pillar."""
    upper = name.upper()
    if "PILLAR" not in upper:
        return -1
    for rank, token in enumerate(_PILLAR_ORDER):
        if token in upper:
            return rank
    return -1


class OP_ValidateKit(bpy.types.Operator):
    """Check kit meshes against Buildify's module contract and PER's standing checks"""
    bl_idname = "wbtk.validate_kit"
    bl_label = "Validate Kit"
    bl_description = ("Check the selected meshes (or every mesh, if nothing is selected) "
                      "against Buildify's module contract and PER's standing checks")
    bl_options = {'REGISTER'}

    def _targets(self, context):
        sel = [o for o in context.selected_objects if o.type == 'MESH']
        if sel:
            return sel, "selection"
        return [o for o in context.scene.objects if o.type == 'MESH'], "scene"

    def _check_mesh(self, obj):
        """Returns (failures, notes) for one object."""
        fails, notes = [], []

        # --- Contract 1: applied rotation and scale. Applies to EVERY mesh. --------
        if not all(abs(a) < _XFORM_EPS for a in obj.rotation_euler):
            fails.append("unapplied ROTATION")
        if not all(abs(s - 1.0) < _XFORM_EPS for s in obj.scale):
            fails.append("unapplied SCALE")

        # --- Contract 2: pivot. Buildify-destined modules ONLY. -------------------
        xs = [c[0] for c in obj.bound_box]
        ys = [c[1] for c in obj.bound_box]
        zs = [c[2] for c in obj.bound_box]
        if _is_buildify_module(obj.name):
            if abs(min(zs)) > _PIVOT_EPS:
                fails.append("origin not at BASE (z_min=%.4f)" % min(zs))
            if abs((min(xs) + max(xs)) * 0.5) > _PIVOT_EPS:
                fails.append("origin not centred in X")
            y_mid = abs((min(ys) + max(ys)) * 0.5) <= _PIVOT_EPS
            notes.append("Y pivot %s" % ("centred" if y_mid
                                         else "back" if abs(min(ys)) <= _PIVOT_EPS else "other"))

        # --- Contract 3: UVs. Tracked separately, see _check_uv. -------------------
        uv = self._check_uv(obj)

        # --- PER standing checks --------------------------------------------------
        bm = bmesh.new()
        try:
            bm.from_mesh(obj.data)
            if not bm.faces:
                fails.append("no faces")
                return fails, notes, uv
            # PER COMPONENT, and the two reasons why are both defects this check
            # shipped with on 2026-08-24. Fixed 2026-08-28 after a component-level
            # audit found 9 inverted components in 3 meshes that this reported CLEAN.
            #
            #   1. It summed open edges over the WHOLE OBJECT and skipped the volume
            #      check entirely if any existed. CatwalkSpan, GratingChannel and
            #      GratingWalkway each carry ONE open single-quad grating card = 4
            #      boundary edges, which switched off "the only check that catches
            #      inverted normals" on exactly the three meshes that needed it -- and
            #      they are 3 of the 8 meshes carrying the reference tiling unwrap.
            #   2. bm.calc_volume(signed=True) SUMS every component, so a few small
            #      inverted boxes hide inside one large correct one and the total
            #      stays positive. Measured kit-wide: 260 closed components, 9
            #      negative, and the object totals never revealed it.
            #
            # An open component is still not judged -- volume genuinely is arbitrary
            # on an open shell, and some kit pieces are open by design. But an open
            # component no longer excuses its closed neighbours.
            open_comps = closed_comps = 0
            for comp in _face_components(bm):
                edges = set()
                for f in comp:
                    edges.update(f.edges)
                if not all(len(e.link_faces) == 2 for e in edges):
                    open_comps += 1
                    continue
                closed_comps += 1
                volume = _component_signed_volume(comp)
                if volume <= 0.0:
                    fails.append("closed component #%d (%d faces) has signed volume NOT "
                                 "POSITIVE (%+.6f) - normals are INVERTED. Fix with "
                                 "bmesh.ops.recalc_face_normals" % (closed_comps, len(comp), volume))
            if open_comps:
                notes.append("%d open component(s) - not volume-judged; %d closed one(s) were"
                             % (open_comps, closed_comps))
        finally:
            bm.free()

        return fails, notes, uv

    def _check_uv(self, obj):
        """Returns a problem string, or None if the mesh carries usable UVs.

        Presence of a uv_layer is NOT the check. A mesh can carry a UVMap whose
        every loop sits at the same coordinate - `from_pydata` and several mesh
        builders produce exactly that - and it passes any layer-count test while
        being just as untexturable as no UVs at all. So measure the SPREAD.

        Split from the fail list on purpose: a UV gap is a real defect, but it is
        currently a project-wide one, and folding 46 of them into the contract
        failures would bury the pivot/normal/order checks this operator exists to
        police. Counted and printed on its own line instead, so it cannot be
        mistaken for clean the way it was before this check existed.
        """
        me = obj.data
        if not me.uv_layers:
            return "no UV layer"
        layer = me.uv_layers.active or me.uv_layers[0]
        if not layer.data:
            return "UV layer '%s' has no loops" % layer.name
        us = [d.uv[0] for d in layer.data]
        vs = [d.uv[1] for d in layer.data]
        if (max(us) - min(us)) < _UV_EPS and (max(vs) - min(vs)) < _UV_EPS:
            return ("UV layer '%s' is DEGENERATE - all %d loops at (%.3f, %.3f). "
                    "Untexturable; same as having none." % (layer.name, len(us), us[0], vs[0]))

        # Presence and spread were the whole check until 2026-08-29, and they pass on
        # a smart-project, on trim-row UVs, and on the ruled projection at the wrong
        # divisor - three different surfaces that all "have UVs". So now conformance
        # is measured against the projection itself, reusing operators_box_uv's map
        # so the check and the tool cannot drift apart.
        return self._check_projection(obj, layer)

    def _check_projection(self, obj, layer):
        """Does this layer match the ruled box projection, and at what divisor?

        The divisor is DERIVED rather than assumed: for a conforming layer, every
        loop satisfies co[axis] = uv * D for a single D, so D is measured and then
        compared against the ruled 4.0 (= 512 px/m at 2K). That distinguishes 'wrong
        projection' from 'right projection, wrong density', which are different bugs
        with different fixes.

        A non-conforming layer is REPORTED, not failed: 0-1 packed UVs are correct
        for a Painter-bound mesh and wrong for a tiling one, and this operator does
        not know a mesh's destination. KIT_TEXTURE_ROUTING_v1.md does.
        """
        me = obj.data
        ratios, off = [], 0
        for poly in me.polygons:
            n = poly.normal
            d = max(range(3), key=lambda i: abs(n[i]))
            ui, vi = _AXIS_MAP[d]
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                uv = layer.data[li].uv
                for axis, val in ((ui, uv[0]), (vi, uv[1])):
                    c = co[axis]
                    if abs(val) < _UV_EPS:
                        if abs(c) > _PIVOT_EPS:
                            off += 1          # uv pinned at 0 where the coord is not
                    else:
                        ratios.append(c / val)

        if not ratios:
            return "UV layer '%s' carries no usable ratio - cannot judge" % layer.name

        d0 = sorted(ratios)[len(ratios) // 2]          # median: robust to a few strays
        bad = sum(1 for r in ratios if abs(r - d0) > 1e-4) + off
        if bad:
            return ("UV layer '%s' does NOT match the ruled box projection - %d of %d "
                    "components off. Correct for a Painter-bound mesh (0-1 packed), wrong "
                    "for a tiling one. See KIT_TEXTURE_ROUTING_v1.md"
                    % (layer.name, bad, len(ratios) + off))
        if abs(d0 - _RULED_DIVISOR) > 1e-4:
            return ("UV layer '%s' matches the box projection but at 1/%.4g, not the ruled "
                    "1/%.4g - texel density is %.0f px/m at 2K, not 512"
                    % (layer.name, d0, _RULED_DIVISOR, 2048.0 / d0))
        if layer.name != _RULED_LAYER:
            return ("UV layer is correct but named '%s'; the 8 reference meshes use '%s'"
                    % (layer.name, _RULED_LAYER))
        return None

    def _check_pillar_order(self, objects):
        """Contract 4, per collection."""
        fails = []
        by_collection = {}
        for obj in objects:
            if _pillar_rank(obj.name) < 0:
                continue
            for coll in obj.users_collection:
                by_collection.setdefault(coll.name, []).append(obj.name)

        for coll_name, names in sorted(by_collection.items()):
            ranks = [_pillar_rank(n) for n in sorted(names)]
            if ranks != sorted(ranks):
                fails.append("'%s': sorted alphabetically these read %s, so Buildify picks the "
                             "WRONG pillar for each corner - put an ordinal in the name "
                             "(Pillar1Flat / Pillar2CC / Pillar3CV)"
                             % (coll_name, ", ".join(sorted(names))))
        return fails

    def _check_one_module_size(self, objects):
        """Contract 5. Wall modules in one building must share a single size."""
        sizes = {}
        for obj in objects:
            if "WALL" not in obj.name.upper():
                continue
            key = tuple(round(v, 3) for v in obj.dimensions)
            sizes.setdefault(key, []).append(obj.name)
        if len(sizes) > 1:
            detail = " | ".join("%s: %s" % ("x".join("%.2f" % v for v in k), ", ".join(sorted(n)))
                                for k, n in sorted(sizes.items()))
            return ["more than one wall module size - Buildify supports exactly one per "
                    "building. Found %d: %s" % (len(sizes), detail)]
        return []

    def execute(self, context):
        objects, scope = self._targets(context)
        if not objects:
            self.report({'WARNING'}, "No mesh objects to validate.")
            return {'CANCELLED'}

        failures, notes, uv_bad = {}, {}, {}
        for obj in objects:
            f, n, u = self._check_mesh(obj)
            if f:
                failures[obj.name] = f
            if n:
                notes[obj.name] = n
            if u:
                uv_bad[obj.name] = u

        kit_fails = self._check_pillar_order(objects) + self._check_one_module_size(objects)

        print("\n--- WBTK Kit Validator (%d mesh(es), from %s) ---" % (len(objects), scope))
        for name in sorted(failures):
            print("  FAIL  %s" % name)
            for f in failures[name]:
                print("          - %s" % f)
        for f in kit_fails:
            print("  FAIL  kit-level: %s" % f)
        for name in sorted(uv_bad):
            print("  UV    %s: %s" % (name, uv_bad[name]))
        for name in sorted(notes):
            print("  note  %s: %s" % (name, "; ".join(notes[name])))
        clean = len(objects) - len(failures)
        print("  %d/%d clean, %d kit-level issue(s), %d/%d WITHOUT USABLE UVs"
              % (clean, len(objects), len(kit_fails), len(uv_bad), len(objects)))
        print("--- end ---\n")

        total = len(failures) + len(kit_fails)
        if not total:
            # UVs are reported even on a contract-clean kit. Staying silent here is
            # exactly how 46 untexturable meshes read as "44/44 clean" before.
            if uv_bad:
                self.report({'WARNING'},
                            "Kit Validator: %d/%d clean on contract, but %d mesh(es) have NO "
                            "USABLE UVs - untexturable. See Console."
                            % (clean, len(objects), len(uv_bad)))
                return {'FINISHED'}
            self.report({'INFO'}, "Kit Validator: %d/%d clean. Contract + standing checks pass."
                        % (clean, len(objects)))
            return {'FINISHED'}

        lines = ["%s: %s" % (n, "; ".join(failures[n])) for n in sorted(failures)]
        lines.extend(kit_fails)

        def draw(popup, _context):
            col = popup.layout.column(align=True)
            for line in lines[:20]:
                col.label(text=line, icon='ERROR')
            if len(lines) > 20:
                col.label(text="...and %d more - full report in the Console."
                          % (len(lines) - 20))
            else:
                col.label(text="Full report in Window > Toggle System Console.")

        context.window_manager.popup_menu(draw, title="Kit Validator", icon='CHECKMARK')
        self.report({'WARNING'}, "Kit Validator: %d issue(s) across %d mesh(es)%s. See Console."
                    % (total, len(failures),
                       ", plus %d without usable UVs" % len(uv_bad) if uv_bad else ""))
        return {'FINISHED'}


# --- List of Operator Classes to Register from THIS file ---
_classes_to_register = (
    OP_ValidateKit,
)
