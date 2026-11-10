"""WBTK audit v1 fix pass, ROUND 2 -- patches A10c/A10d/A10e from CLAUDE_WBTK_fix_pass_Audit_v1.md §Round 2.

    python tests/audit_v1_patches_r2.py --check    # verify every anchor matches exactly once, change nothing
    python tests/audit_v1_patches_r2.py --apply    # back up to <name>.py.bak_audit1_r2, apply, py_compile

Requires round 1 (audit_v1_patches.py) to be applied first: A10d's anchor is A10b's output.
Run from the PER_WBTK folder (or pass --root <folder>). NOT imported by the addon --
__init__.py never touches tests/. Line endings are preserved per file (24 modules are
CRLF on disk). Stops at the first anchor that does not match exactly once -- the STOP
CONDITION -- and applies nothing further. Re-running --apply on an already-patched tree
reports every anchor as missing, which is the expected "already applied" signal.
"""
import argparse
import os
import py_compile
import shutil
import sys

PATCHES = []

def P(id, title, file, why, old, new, verify, risk="mechanical"):
    PATCHES.append(dict(id=id, title=title, file=file, why=why, old=old, new=new, verify=verify, risk=risk))

# ---------------------------------------------------------------------------
P('A10c', 'Summon Build Engine: the target predicate - never WBTK scaffolding, never a kit module',
  'operators_build_engine.py',
  "`type == 'MESH'` alone accepts Build Mode blocks, the grid, detail stamps, the live-preview mesh and the SM_DW_* kit modules - all meshes. Live on 2026-09-05 a Summon landed on WBTK_BM_0001 because it was the active object: 26 instances tiled onto a helper block, three kit modules dragged off the origin. One predicate names what a legitimate target is; A10d uses it.",
  """    return os.path.dirname(os.path.realpath(__file__))


def _get_or_make_collection(name, host):
""",
  """    return os.path.dirname(os.path.realpath(__file__))


# Meshes Summon must never build on. Build Mode blocks, the grid, detail stamps
# and the live-preview mesh are WBTK's own scaffolding; SM_DW_* are the kit
# modules themselves. All of them are meshes, so `type == 'MESH'` alone accepts
# them - which is how a Summon landed on WBTK_BM_0001 on 2026-09-05: 26 instances
# on a helper block and three kit modules dragged off the origin.
# WBTK_BFY_ is deliberately NOT here: the footprint is the intended target.
_NEVER_TARGET_PREFIXES = ("WBTK_BM_", "WBTK_DTL_", "_WBTK_", "WBTK_Live_Preview", "SM_DW_")


def _is_summon_target(obj):
    \"\"\"A mesh that is neither WBTK scaffolding nor a kit module.\"\"\"
    if obj is None or obj.type != 'MESH':
        return False
    return not obj.name.startswith(_NEVER_TARGET_PREFIXES)


def _get_or_make_collection(name, host):
""",
  'py_compile; behaviour is exercised by A10d.')

P('A10d', 'Summon Build Engine: refuse scaffolding and kit modules, prefer the footprint',
  'operators_build_engine.py',
  "Supersedes A10b's fallback: the footprint is used not only when nothing is active but also when the active mesh is a WBTK helper or a kit module, and the Info bar says WHY the active object was passed over. With no usable footprint either, the operator cancels instead of building on the wrong mesh.",
  """    def execute(self, context):
        target = context.active_object
        if target is None or target.type != 'MESH':
            from .operators_buildify import FOOTPRINT_NAME
            target = bpy.data.objects.get(FOOTPRINT_NAME)
            if target is not None and target.type == 'MESH':
                self.report({'INFO'}, "No mesh active - using '%s'." % FOOTPRINT_NAME)
        if target is None or target.type != 'MESH':
            self.report({'ERROR'}, "Select the footprint mesh first "
                                   "(run 'Export Footprints for Buildify' if you have none).")
            return {'CANCELLED'}
""",
  """    def execute(self, context):
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
""",
  'Select WBTK_BM_0000 (a Build Mode block), click Summon Build Engine: the modifier lands on WBTK_BFY_Footprint and the Info bar says the block was passed over. Select a kit module (SM_DW_*): same. Delete the footprint, select a block, Summon: ERROR, nothing built.')

P('A10e', 'Summon Build Engine: the module host is the ONE parent of the Buildify collections',
  'operators_build_engine.py',
  "_get_or_make_collection links an existing collection under the hidden host but leaves any scene-root link in place. Appending the `building` node group drags Buildify's own eleven collections in through its socket defaults, linked at the root - measured live 2026-09-05 - so every module rendered loose beside the building as well as hidden under the host. Unlinking them from the root by hand and re-running Summon gave the clean 44-instance building; this makes the operator do that itself.",
  """    if host is not None and coll.name not in host.children:
        try:
            host.children.link(coll)
        except RuntimeError:
            pass  # already parented somewhere; harmless
    return coll
""",
  """    if host is not None and coll.name not in host.children:
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
""",
  'After Summon, the Outliner shows ground_floor_walls (and the other ten) ONLY under DW_BuildEngine_Modules - no second copy at the scene root, no kit modules loose in the scene.')


def _read(path):
    raw = open(path, "rb").read()
    crlf = b"\r\n" in raw
    return raw.decode("utf-8").replace("\r\n", "\n"), crlf


def _write(path, text, crlf):
    data = text.replace("\n", "\r\n") if crlf else text
    open(path, "wb").write(data.encode("utf-8"))


def run(root, apply):
    files = []
    for p in PATCHES:
        if p["file"] not in files:
            files.append(p["file"])
    # 1. check every anchor first, on the current disk state, in order
    state = {}
    for f in files:
        state[f] = _read(os.path.join(root, f))
    problems = []
    for p in PATCHES:
        text, _ = state[p["file"]]
        n = text.count(p["old"])
        if n != 1:
            problems.append("%s %s: anchor found %d time(s), expected 1" % (p["id"], p["file"], n))
        else:
            state[p["file"]] = (text.replace(p["old"], p["new"]), state[p["file"]][1])
    if problems:
        print("STOP -- anchors did not match exactly once:")
        for line in problems:
            print("   " + line)
        print("Nothing was written.")
        return 2
    print("all %d anchors match exactly once across %d files" % (len(PATCHES), len(files)))
    if not apply:
        return 0
    # 2. backup, write, compile -- one file at a time
    for f in files:
        path = os.path.join(root, f)
        bak = path + ".bak_audit1_r2"
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
        text, crlf = state[f]
        _write(path, text, crlf)
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as exc:
            print("COMPILE FAILED for %s -- restoring from backup" % f)
            print(exc)
            shutil.copy2(bak, path)
            return 3
        print("patched + py_compile OK  %-32s (%s, backup %s)" % (f, "CRLF" if crlf else "LF", os.path.basename(bak)))
    print("done: %d patches, %d files" % (len(PATCHES), len(files)))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sys.exit(run(a.root, a.apply))
