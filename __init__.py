# World_Building_Toolkit/__init__.py

bl_info = {
    "name": "World Builder Toolkit (WBTK)",
    "author": "Jermaine Dawson Peterson & AI Assistant",
    "version": (0, 13, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > World Builder",
    "description": "Generate modular walkways, structures, props, fences, ground planes, and more.",
    "warning": "",
    "doc_url": "",
    "category": "Add Mesh",
}

import bpy

# --- Import Addon Modules ---
# Use relative imports

# Core modules
from . import config
from . import utils
from . import properties

# Geometry modules (Import needed for Python's package structure)
from . import geometry_walkways
from . import geometry_buildings
from . import geometry_fences
from . import geometry_footprints

# Operator modules (Contain classes to register)
from . import operators_walkways
from . import operators_structures
from . import operators_props
from . import operators_fences
from . import operators_ground

# UI module(s) (Contain Panel classes to register)
from . import ui

# UE Pipeline + Face Magnet
from . import operators_ue_pipeline

# Foliage Generator
from . import geometry_foliage
from . import operators_foliage

# Preview placement
from . import operators_preview

# Pipe generator
from . import geometry_pipes
from . import operators_pipes

# Cable / wire generator
from . import operators_cables

# Vent / grate generator
from . import operators_vents

# Live preview (timer-based auto-rebuild)
from . import operators_live_preview

# Surface scatter
from . import operators_scatter

# Trim sheet UV generator
from . import operators_trim_uv

# Region DNA presets
from . import region_dna
from . import operators_region_dna

# Block Composer (Phase 2)
from . import operators_block_composer

# Buildify bridge (Strategic Pivot item #1: footprints -> Buildify)
from . import operators_buildify

# Footprint Painter

# Custom Builder (Viewport Block Painter)
from . import bm_data
from . import bm_operators
from . import bm_generate
from . import bm_details

# --- Combine Classes for Registration ---
# Gather the '_classes_to_register' tuples from each relevant module
_classes_to_register = (
    *operators_walkways._classes_to_register,
    *operators_structures._classes_to_register,
    *operators_props._classes_to_register,
    *operators_fences._classes_to_register,
    *operators_ground._classes_to_register,
    *operators_ue_pipeline._classes_to_register,
    *operators_foliage._classes_to_register,
    *operators_preview._classes_to_register,
    *operators_pipes._classes_to_register,
    *operators_cables._classes_to_register,
    *operators_vents._classes_to_register,
    *operators_live_preview._classes_to_register,
    *operators_scatter._classes_to_register,
    *operators_trim_uv._classes_to_register,
    *operators_region_dna._classes_to_register,
    *operators_block_composer._classes_to_register,
    *operators_buildify._classes_to_register,
    *bm_operators._classes,
    *bm_details._classes,
    *ui._classes_to_register,
)

# --- Registration Functions ---

def register():
    """ Registers all addon classes and properties. """
    # Reload prerequisite modules (useful during development)
    # You might comment these out for final release
    # import importlib
    # importlib.reload(config)
    # importlib.reload(utils)
    # importlib.reload(properties)
    # importlib.reload(geometry_walkways)
    # importlib.reload(geometry_buildings)
    # importlib.reload(geometry_fences)
    # importlib.reload(operators_walkways)
    # importlib.reload(operators_structures)
    # importlib.reload(operators_props)
    # importlib.reload(operators_fences)
    # importlib.reload(operators_ground)
    # importlib.reload(ui)
    # print("----- Modules Reloaded -----") # Debug message

    print(f"Registering {bl_info['name']} v{'.'.join(map(str, bl_info['version']))}...")

    # 1. Register Scene Properties
    try:
        properties.PropertyManager.register_properties()
    except Exception as e:
        print(f"ERROR: Failed to register properties: {e}")
        # Optionally raise error to prevent partial registration?
        # raise e

    # 2. Register Operator and Panel classes
    for cls in _classes_to_register:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            # Already registered, maybe from a previous failed unregister or dev reload
            print(f"Info: Class '{cls.__name__}' already registered. Skipping.")
            # You could optionally try to unregister and re-register here if needed during dev
            # try:
            #     bpy.utils.unregister_class(cls)
            #     bpy.utils.register_class(cls)
            # except Exception as e_re: print(f"ERROR: Failed to re-register {cls.__name__}: {e_re}")
        except Exception as e:
            print(f"ERROR: Failed to register class '{cls.__name__}': {e}")

    print(f"{bl_info['name']} Registered.")

def unregister():
    """ Unregisters all addon classes and properties in reverse order. """
    print(f"Unregistering {bl_info['name']}...")

    # 0. Stop live preview timer and clean up preview objects
    try:
        operators_live_preview.cleanup()
    except Exception as e:
        print(f"Warning: Live preview cleanup failed: {e}")

    # 1. Unregister Operator and Panel classes (in reverse order)
    for cls in reversed(_classes_to_register):
        try:
            if hasattr(bpy.types, cls.__name__): # Check if class exists in bpy.types
                bpy.utils.unregister_class(cls)
            #else: # Debugging
            #     print(f"Info: Class '{cls.__name__}' not found in bpy.types for unregistration.")
        except RuntimeError:
            print(f"Warning: Could not unregister class '{cls.__name__}' (might already be unregistered or in use).")
        except Exception as e:
            print(f"ERROR: Failed to unregister class '{cls.__name__}': {e}")

    # 2. Unregister Scene Properties
    try:
        properties.PropertyManager.unregister_properties()
    except Exception as e:
        print(f"ERROR: Failed to unregister properties: {e}")


    print(f"{bl_info['name']} Unregistered.")

# Note: The standard Blender addon template doesn't typically call register()
# within the if __name__ == "__main__": block in __init__.py
# if __name__ == "__main__":
#     register()