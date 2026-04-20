# World_Building_Toolkit/operators_foliage.py
# Foliage generator operators for WBTK v0.3.0
# Three generators: Tree, Shrub, Ground Cover
# Each supports region presets + manual tweaking

import bpy
import bmesh
from mathutils import Vector

from .config import Config
from .utils import Utils
from .geometry_foliage import GeometryFoliage, FOLIAGE_PRESETS, PRESET_ENUM_ITEMS


# =============================================================================
#  BASE FOLIAGE OPERATOR
# =============================================================================

class OP_FoliageBase(bpy.types.Operator):
    """Shared helpers for all foliage operators."""

    def get_params_from_scene(self, scene):
        raise NotImplementedError

    def finalize_mesh(self, bm, name, material_name, loc, scene):
        """Convert BMesh to object, assign material, UV unwrap, link to collection."""
        obj = Utils.bm_to_obj(bm, name, loc, material_name)
        if obj and scene.wbtk_add_ucx:
            master = Utils.create_master(name)
            Utils.add_ucx_collider(obj, master)
        return obj

    def report_warning(self, msg):
        self.report({'WARNING'}, msg)
        return {'CANCELLED'}


# =============================================================================
#  OPERATOR — LOAD PRESET
#  Loads preset values into scene properties so the sliders update live.
# =============================================================================

class WBTK_OT_LoadFoliagePreset(bpy.types.Operator):
    """Load a region foliage preset into the current sliders"""
    bl_idname = "wbtk.load_foliage_preset"
    bl_label  = "Load Preset"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        preset_key = scene.wbtk_foliage_preset

        if preset_key == 'NONE' or preset_key not in FOLIAGE_PRESETS:
            self.report({'WARNING'}, "Select a preset from the dropdown first.")
            return {'CANCELLED'}

        preset = FOLIAGE_PRESETS[preset_key]

        # Map preset keys to scene property names and set them
        prop_map = {
            # Tree
            'tree_height':          'wbtk_tree_height',
            'trunk_radius':         'wbtk_trunk_radius',
            'trunk_taper':          'wbtk_trunk_taper',
            'branch_levels':        'wbtk_branch_levels',
            'branch_count':         'wbtk_branch_count',
            'branch_angle':         'wbtk_branch_angle',
            'branch_length_factor': 'wbtk_branch_length_factor',
            'branch_taper':         'wbtk_branch_taper',
            'leaf_density':         'wbtk_leaf_density',
            'leaf_size':            'wbtk_leaf_size',
            'leaf_shape':           'wbtk_leaf_shape',
            'leaf_droop':           'wbtk_leaf_droop',
            # Shrub
            'shrub_height':         'wbtk_shrub_height',
            'shrub_width':          'wbtk_shrub_width',
            'shrub_branch_count':   'wbtk_shrub_branch_count',
            'shrub_branch_angle':   'wbtk_shrub_branch_angle',
            'shrub_leaf_density':   'wbtk_shrub_leaf_density',
            'shrub_leaf_size':      'wbtk_shrub_leaf_size',
            'shrub_leaf_shape':     'wbtk_shrub_leaf_shape',
            # Ground
            'ground_type':          'wbtk_ground_type',
            'ground_patch_radius':  'wbtk_ground_patch_radius',
            'ground_blade_count':   'wbtk_ground_blade_count',
            'ground_blade_height':  'wbtk_ground_blade_height',
            'ground_blade_width':   'wbtk_ground_blade_width',
            'ground_droop':         'wbtk_ground_droop',
            'ground_cluster_scatter': 'wbtk_ground_cluster_scatter',
            # Shared
            'randomize_seed':       'wbtk_foliage_seed',
        }

        for preset_key_name, scene_prop in prop_map.items():
            if preset_key_name in preset and hasattr(scene, scene_prop):
                try:
                    setattr(scene, scene_prop, preset[preset_key_name])
                except Exception as e:
                    print(f"WBTK Foliage: Could not set {scene_prop}: {e}")

        self.report({'INFO'}, f"Loaded preset: {preset.get('label', preset_key)}")
        return {'FINISHED'}


# =============================================================================
#  OPERATOR — TREE GENERATOR
# =============================================================================

class WBTK_OT_GenerateTree(OP_FoliageBase):
    """Generate a procedural tree with trunk, branches, and leaf cards"""
    bl_idname  = "wbtk.generate_tree"
    bl_label   = "Generate Tree"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene

        params = {
            'tree_height':          scene.wbtk_tree_height,
            'trunk_radius':         scene.wbtk_trunk_radius,
            'trunk_taper':          scene.wbtk_trunk_taper,
            'branch_levels':        scene.wbtk_branch_levels,
            'branch_count':         scene.wbtk_branch_count,
            'branch_angle':         scene.wbtk_branch_angle,
            'branch_length_factor': scene.wbtk_branch_length_factor,
            'branch_taper':         scene.wbtk_branch_taper,
            'leaf_density':         scene.wbtk_leaf_density,
            'leaf_size':            scene.wbtk_leaf_size,
            'leaf_shape':           scene.wbtk_leaf_shape,
            'leaf_droop':           scene.wbtk_leaf_droop,
            'randomize_seed':       scene.wbtk_foliage_seed,
        }

        bm_trunk, bm_leaves = GeometryFoliage.build_tree(params)

        loc = Vector((0, 0, 0))

        # Trunk mesh
        trunk_obj = self.finalize_mesh(
            bm_trunk,
            f"WBTK_Tree_Trunk",
            Config.MATERIAL_PROP_WOOD,
            loc, scene
        )

        # Leaves mesh
        leaves_obj = self.finalize_mesh(
            bm_leaves,
            f"WBTK_Tree_Leaves",
            "WBTK_Leaves",
            loc, scene
        )

        # Parent leaves to trunk for clean hierarchy
        if trunk_obj and leaves_obj:
            leaves_obj.parent = trunk_obj

        self.report({'INFO'},
            f"Tree generated — Height: {params['tree_height']}m | "
            f"Branch levels: {params['branch_levels']} | "
            f"Seed: {params['randomize_seed']}"
        )
        return {'FINISHED'}


# =============================================================================
#  OPERATOR — SHRUB GENERATOR
# =============================================================================

class WBTK_OT_GenerateShrub(OP_FoliageBase):
    """Generate a procedural shrub or bush"""
    bl_idname  = "wbtk.generate_shrub"
    bl_label   = "Generate Shrub"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene

        params = {
            'shrub_height':       scene.wbtk_shrub_height,
            'shrub_width':        scene.wbtk_shrub_width,
            'shrub_branch_count': scene.wbtk_shrub_branch_count,
            'shrub_branch_angle': scene.wbtk_shrub_branch_angle,
            'shrub_leaf_density': scene.wbtk_shrub_leaf_density,
            'shrub_leaf_size':    scene.wbtk_shrub_leaf_size,
            'shrub_leaf_shape':   scene.wbtk_shrub_leaf_shape,
            'randomize_seed':     scene.wbtk_foliage_seed,
        }

        bm_branches, bm_leaves = GeometryFoliage.build_shrub(params)

        loc = Vector((0, 0, 0))

        branch_obj = self.finalize_mesh(
            bm_branches,
            "WBTK_Shrub_Branches",
            Config.MATERIAL_PROP_WOOD,
            loc, scene
        )

        leaves_obj = self.finalize_mesh(
            bm_leaves,
            "WBTK_Shrub_Leaves",
            "WBTK_Leaves",
            loc, scene
        )

        if branch_obj and leaves_obj:
            leaves_obj.parent = branch_obj

        self.report({'INFO'},
            f"Shrub generated — Height: {params['shrub_height']}m | "
            f"Branches: {params['shrub_branch_count']} | "
            f"Seed: {params['randomize_seed']}"
        )
        return {'FINISHED'}


# =============================================================================
#  OPERATOR — GROUND COVER GENERATOR
# =============================================================================

class WBTK_OT_GenerateGroundCover(OP_FoliageBase):
    """Generate a ground cover patch — grass, weeds, or moss"""
    bl_idname  = "wbtk.generate_ground_cover"
    bl_label   = "Generate Ground Cover"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene

        params = {
            'ground_type':            scene.wbtk_ground_type,
            'ground_patch_radius':    scene.wbtk_ground_patch_radius,
            'ground_blade_count':     scene.wbtk_ground_blade_count,
            'ground_blade_height':    scene.wbtk_ground_blade_height,
            'ground_blade_width':     scene.wbtk_ground_blade_width,
            'ground_droop':           scene.wbtk_ground_droop,
            'ground_cluster_scatter': scene.wbtk_ground_cluster_scatter,
            'randomize_seed':         scene.wbtk_foliage_seed,
        }

        bm = GeometryFoliage.build_ground_cover(params)

        loc = Vector((0, 0, 0))

        type_names = {'GRASS': 'Grass', 'WEED': 'Weed', 'MOSS': 'Moss'}
        type_label = type_names.get(params['ground_type'], 'Ground')

        obj = self.finalize_mesh(
            bm,
            f"WBTK_{type_label}_Patch",
            "WBTK_Leaves",
            loc, scene
        )

        self.report({'INFO'},
            f"{type_label} patch generated — "
            f"Radius: {params['ground_patch_radius']}m | "
            f"Blades: {params['ground_blade_count']} | "
            f"Seed: {params['randomize_seed']}"
        )
        return {'FINISHED'}


# =============================================================================
#  OPERATOR — RANDOMIZE SEED
# =============================================================================

class WBTK_OT_RandomizeFoliageSeed(bpy.types.Operator):
    """Set a new random seed to get a different variation of the same settings"""
    bl_idname  = "wbtk.randomize_foliage_seed"
    bl_label   = "New Variation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import random
        context.scene.wbtk_foliage_seed = random.randint(0, 9999)
        return {'FINISHED'}


# =============================================================================
#  REGISTRATION
# =============================================================================

_classes_to_register = (
    WBTK_OT_LoadFoliagePreset,
    WBTK_OT_GenerateTree,
    WBTK_OT_GenerateShrub,
    WBTK_OT_GenerateGroundCover,
    WBTK_OT_RandomizeFoliageSeed,
)
