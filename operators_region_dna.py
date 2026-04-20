# operators_region_dna.py
# Region DNA system — apply district presets to building properties.

import bpy
from .region_dna import REGION_PRESETS


class WBTK_OT_apply_region_dna(bpy.types.Operator):
    bl_idname = "wbtk.apply_region_dna"
    bl_label = "Apply Region DNA"
    bl_description = "Set all building properties to match the selected region's DNA preset"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        region_key = getattr(scene, 'wbtk_region_dna', 'NONE')

        if region_key == 'NONE' or region_key not in REGION_PRESETS:
            self.report({'WARNING'}, "No region selected.")
            return {'CANCELLED'}

        preset = REGION_PRESETS[region_key]
        props = preset['props']
        count = 0

        for prop_name, value in props.items():
            try:
                setattr(scene, prop_name, value)
                count += 1
            except Exception as e:
                print(f"WBTK Region DNA: Could not set {prop_name} = {value}: {e}")

        self.report({'INFO'}, f"Region DNA '{preset['label']}' applied ({count} properties set).")
        return {'FINISHED'}


_classes_to_register = (
    WBTK_OT_apply_region_dna,
)
