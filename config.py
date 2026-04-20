# World_Building_Toolkit/config.py
# CORRECTED VERSION - Removed imports from inside the class

import bpy # Keep imports outside the class
import math # Keep imports outside the class

# Config class definition should start immediately after imports
class Config:
    """ Configuration settings for the Modular World Builder Toolkit. """

    # --- Core Units & Scene ---
    SCALE = 1.0
    DEFAULT_TILE_SIZE = 2.0 * SCALE
    TARGET_COLLECTION = "World Builder Output"
    EXPORT_COLLECTION = "UE_Export"
    UE_UNIT_SCALE = 0.01  # Unreal expects scene unit scale of 0.01 (1 Blender unit = 1 UE cm)

    # --- Walkway / Railing Specific Dimensions ---
    LENGTH_UNIT = DEFAULT_TILE_SIZE
    WIDTH_UNIT = DEFAULT_TILE_SIZE
    RAIL_RADIUS = 0.035 * SCALE
    RAIL_HEIGHTS = [1.0 * SCALE, 0.7 * SCALE, 0.4 * SCALE]
    LADDER_WIDTH = 0.6 * SCALE
    LADDER_RUNG_RADIUS = RAIL_RADIUS * 0.75

    # --- Building Defaults ---
    WALL_THICKNESS = 0.2 * SCALE
    DEFAULT_WALL_HEIGHT = 3.0 * SCALE
    WINDOW_WIDTH = 1.5 * SCALE
    WINDOW_HEIGHT = 1.0 * SCALE
    WINDOW_SILL_HEIGHT = 1.0 * SCALE
    # +++ ADD THESE WINDOW DETAIL CONSTANTS +++
    WINDOW_FRAME_THICKNESS = 0.05 * SCALE # How thick the inset border is
    WINDOW_INSET_DEPTH = 0.2 * SCALE     # How far back the window surface is set
    DOOR_WIDTH = 1.0 * SCALE
    DOOR_HEIGHT = 2.0 * SCALE
    DOOR_INSET_DEPTH = 0.2 * SCALE
    DOOR_SPLAY_ANGLE = 30.0  # degrees for angled jambs

    # --- Chunking ---
    CHUNK_LENGTH = 25
    CHUNK_WIDTH = 10

    # --- Materials ---
    MATERIAL_PREFIX = "WBTK_"
    MATERIAL_WALKWAY = f"{MATERIAL_PREFIX}Walkway"
    MATERIAL_RAIL = f"{MATERIAL_PREFIX}Rail"
    MATERIAL_LADDER = f"{MATERIAL_PREFIX}Ladder"
    MATERIAL_STAIR = f"{MATERIAL_PREFIX}Stair"
    MATERIAL_WALL = f"{MATERIAL_PREFIX}Wall"
    MATERIAL_FLOOR = f"{MATERIAL_PREFIX}Floor"
    MATERIAL_ROOF = f"{MATERIAL_PREFIX}Roof"
    MATERIAL_PROP_WOOD = f"{MATERIAL_PREFIX}Prop_Wood"
    MATERIAL_PROP_METAL = f"{MATERIAL_PREFIX}Prop_Metal"
    MATERIAL_NEON_SIGN = f"{MATERIAL_PREFIX}Neon_Sign"
    MATERIAL_FENCE = f"{MATERIAL_PREFIX}Fence"
    MATERIAL_FENCE_MESH = f"{MATERIAL_PREFIX}Fence_Mesh"

    # --- Building Enhancement Materials ---
    MATERIAL_COLUMN  = f"{MATERIAL_PREFIX}Column"
    MATERIAL_BAND    = f"{MATERIAL_PREFIX}Band"
    MATERIAL_SILL    = f"{MATERIAL_PREFIX}Sill"
    MATERIAL_PARAPET = f"{MATERIAL_PREFIX}Parapet"
    MATERIAL_PLINTH  = f"{MATERIAL_PREFIX}Plinth"
    MATERIAL_LEDGE   = f"{MATERIAL_PREFIX}Ledge"
    MATERIAL_PIPE       = f"{MATERIAL_PREFIX}Pipe"
    MATERIAL_PIPE_CLAMP = f"{MATERIAL_PREFIX}Pipe_Clamp"
    MATERIAL_CABLE      = f"{MATERIAL_PREFIX}Cable"
    MATERIAL_VENT       = f"{MATERIAL_PREFIX}Vent"

    # --- Railing Placement Enums ---
    RAIL_NONE='NONE'
    RAIL_LEFT='LEFT'
    RAIL_RIGHT='RIGHT'
    RAIL_BOTH='BOTH'
    RAIL_OUTER='OUTER'
    RAIL_INNER='INNER'
    RAIL_ALL='ALL'

    # --- Style Parameters: Walkways ---
    WALKWAY_LIP_DEPTH = 0.05 * SCALE
    WALKWAY_GRATE_BAR_SIZE = 0.05 * SCALE
    WALKWAY_GRATE_SPACING = 0.1 * SCALE
    NEO_PANEL_BEVEL_WIDTH = 0.04 * SCALE
    INDUSTRIAL_PLATE_EDGE_HEIGHT = 0.03 * SCALE
    INDUSTRIAL_PLATE_EDGE_WIDTH = 0.04 * SCALE

    # --- Style Parameters: Railings ---
    NEO_RAIL_BEVEL_FACTOR = 0.3

    # --- UV Unwrap Parameters ---
    UV_ANGLE_LIMIT = math.radians(66.0)
    UV_ISLAND_MARGIN = 0.01

    # Geometry generation settings like segment count are handled elsewhere now