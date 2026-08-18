# World_Building_Toolkit/properties.py
# (Combined MRTK + Building Toolkit Properties)

import bpy

# Import Config for default values and enums (optional, but good practice if defaults reference Config)
from .config import Config


# --- Build Mode update callback ---
_WALL_ITEMS = [
    ('SOLID', "Solid", "Solid wall"),
    ('WINDOW', "Window", "Wall with window"),
    ('DOOR', "Door", "Wall with door"),
]


def _bm_update(self, context):
    from .bm_data import on_prop_update
    on_prop_update(self, context)


class PropertyManager:
    """ Manages registration and unregistration of addon properties for the Scene. """

    _properties = [

        # === Global Settings ===
        ('wbtk_walkway_style', bpy.props.EnumProperty(
            name="Walkway Style", items=[('SOLID', 'Solid', 'Standard solid walkway surface'), ('GRATE', 'Grate (Dusk)', 'Industrial grate style walkway'), ('SOLID_LIP', 'Solid + Lip', 'Solid walkway with a downward lip edge'), ('NEO_PANEL', 'Neo Panel (Beveled)', 'Solid walkway with beveled edges'), ('INDUSTRIAL_PLATE', 'Industrial Plate', 'Solid walkway with raised inset plate')], default='SOLID', description="Visual style for walkway surfaces")),
        ('wbtk_rail_style', bpy.props.EnumProperty(
            name="Rail Style", items=[('ROUND', 'Round', 'Standard cylindrical rails'), ('SQUARE', 'Square (Dusk)', 'Square profile rails'), ('NEO_RAIL', 'Neo Rail', 'Beveled square profile rails'), ('INDUSTRIAL_RAIL', 'Industrial Rail', 'Square rails with potential future variation')], default='ROUND', description="Visual style for railing beams and posts")),
        ('wbtk_assign_materials', bpy.props.BoolProperty(name="Assign Materials", default=True, description=f"Assign placeholder materials ({Config.MATERIAL_PREFIX}*)")),
        ('wbtk_auto_unwrap', bpy.props.BoolProperty(name="Auto UV Unwrap", default=True, description="Perform automatic Smart UV Project on generated meshes")),
        ('wbtk_use_trim_uvs', bpy.props.BoolProperty(name="Use Trim Sheet UVs", default=False, description="Remap building UVs to horizontal trim sheet rows instead of Smart UV Project")),
        ('wbtk_trim_texel_density', bpy.props.FloatProperty(name="Texel Density", default=1.0, min=0.1, max=10.0, description="UV tiling density — higher = more texture repetition per meter")),
        ('wbtk_region_dna', bpy.props.EnumProperty(
            name="Region DNA",
            items=[
                ('NONE',        "— Select Region —", "Choose a region preset to apply"),
                ('DUSK_WARD',   "Dusk Ward",         "Cyberpunk slums — cramped, decayed, neon-lit"),
                ('NEO_VESPER',  "Neo Vesper",        "Corporate district — tall, clean, glass and steel"),
                ('SANGRE_NEON', "Sangre Neon",       "Desert rust meets neon — weathered adobe and metal"),
                ('VJOLDRHEIM',  "Vjoldrheim",        "Ice and stone fortress — heavy, thick walls"),
                ('EOSRIA',      "Eosria Expanse",    "Divine, ornate, bright — grand scale"),
                ('UNDERTIDE',   "Undertide",         "Underground industrial — low, utilitarian"),
            ],
            default='NONE',
            description="District preset — sets all building properties to match a region's signature")),
        ('wbtk_add_ucx', bpy.props.BoolProperty(name="Add UCX Collision", default=True, description="Add simple box UCX collision mesh for generated parts")),
        ('wbtk_lowpoly', bpy.props.BoolProperty(name="Low-Poly Rails", default=False, description="Use fewer segments for round rails (performance improvement)")),

        # === Walkway Components ===
        # Bridge
        ('wbtk_br_len', bpy.props.IntProperty(name="Bridge Length (Tiles)", default=10, min=1, max=200, description="Length of the bridge in walkway tiles")),
        ('wbtk_br_wid', bpy.props.IntProperty(name="Bridge Width (Tiles)", default=2, min=1, max=100, description="Width of the bridge in walkway tiles")),
        ('wbtk_br_rail', bpy.props.EnumProperty(name="Bridge Rails", items=[(v, v.capitalize(), '') for v in [Config.RAIL_NONE, Config.RAIL_LEFT, Config.RAIL_RIGHT, Config.RAIL_BOTH]], default=Config.RAIL_BOTH, description="Which sides have railings")),
        # Straight
        ('wbtk_sr_len', bpy.props.IntProperty(name="Straight Length (Tiles)", default=5, min=1, max=100, description="Length of the straight section in walkway tiles")),
        ('wbtk_sr_chunk', bpy.props.BoolProperty(name="Chunk Meshes", default=True, description=f"Split long sections into mesh objects <= {Config.CHUNK_LENGTH} tiles long")),
        ('wbtk_sr_rail', bpy.props.EnumProperty(name="Straight Rails", items=[(v, v.capitalize(), '') for v in [Config.RAIL_NONE, Config.RAIL_LEFT, Config.RAIL_RIGHT, Config.RAIL_BOTH]], default=Config.RAIL_LEFT, description="Which sides have railings")),
        # Corner (L-Shape)
        ('wbtk_cr_len1', bpy.props.IntProperty(name="Corner Length 1 (X)", default=5, min=1, max=100, description="Length of the first leg (along X axis) in tiles, excluding corner cap")),
        ('wbtk_cr_len2', bpy.props.IntProperty(name="Corner Length 2 (Y)", default=5, min=1, max=100, description="Length of the second leg (along Y axis) in tiles, excluding corner cap")),
        ('wbtk_cr_chunk', bpy.props.BoolProperty(name="Chunk Meshes", default=True, description=f"Split long legs into mesh objects <= {Config.CHUNK_LENGTH} tiles long")),
        ('wbtk_cr_rail', bpy.props.EnumProperty(name="Corner Rails", items=[(v, v.capitalize(), '') for v in [Config.RAIL_NONE, Config.RAIL_OUTER, Config.RAIL_INNER, Config.RAIL_BOTH]], default=Config.RAIL_OUTER, description="Railings relative to the corner bend (Outer/Inner)")),
        # T-Junction
        ('wbtk_tr_len1', bpy.props.IntProperty(name="T-Junc Main Len (X)", default=5, min=3, max=100, description="Total length of the main run (must be >= 3 tiles for branch point)")),
        ('wbtk_tr_len2', bpy.props.IntProperty(name="T-Junc Branch Len (Y)", default=5, min=1, max=100, description="Length of the branching leg in tiles, excluding junction plate")),
        # ('wbtk_tr_chunk', bpy.props.BoolProperty(name="Chunk Meshes", default=True, description="Split long legs (Experimental for T)")), # Chunking TBD
        ('wbtk_tr_rail', bpy.props.EnumProperty(name="T-Junc Rails", items=[(v, v.capitalize(), '') for v in [Config.RAIL_NONE, Config.RAIL_OUTER, Config.RAIL_ALL]], default=Config.RAIL_OUTER, description="Outer covers perimeter, All adds inner rails along main run")),
        # X-Junction (+)
        ('wbtk_xj_size', bpy.props.IntProperty(name="X-Junc Arm Size (Tiles)", default=1, min=1, max=5, description="Tiles per arm from center plate (e.g., 1 -> 3x3 total footprint)")),
        ('wbtk_xj_rail', bpy.props.EnumProperty(name="X-Junc Rails", items=[(v, v.capitalize(), '') for v in [Config.RAIL_NONE, Config.RAIL_OUTER, Config.RAIL_ALL]], default=Config.RAIL_OUTER, description="Outer covers perimeter, All adds inner rails facing center")),
        # Ladder
        ('wbtk_ld_height', bpy.props.FloatProperty(name="Ladder Height (m)", default=3.0, min=0.5, max=50.0, unit='LENGTH', description="Vertical height of the ladder")),
        ('wbtk_ld_steps', bpy.props.IntProperty(name="Ladder Rungs", default=10, min=1, max=100, description="Number of rungs")),
        ('wbtk_ld_rail', bpy.props.BoolProperty(name="Ladder Side Rails", default=True, description="Include vertical side rails")),
        # Stairs (Ramp Style)
        ('wbtk_st_run', bpy.props.FloatProperty(name="Ramp Run (m)", default=4.0, min=0.1, max=50.0, unit='LENGTH', description="Horizontal length (footprint) of the stairs ramp")),
        ('wbtk_st_rise', bpy.props.FloatProperty(name="Ramp Rise (m)", default=2.0, min=0.1, max=50.0, unit='LENGTH', description="Vertical height of the stairs ramp")),
        ('wbtk_st_width', bpy.props.IntProperty(name="Ramp Width (Tiles)", default=1, min=1, max=20, description="Width of the stairs ramp in walkway tiles")),
        ('wbtk_st_rail', bpy.props.EnumProperty(name="Ramp Rails", items=[(v, v.capitalize(), '') for v in [Config.RAIL_NONE, Config.RAIL_LEFT, Config.RAIL_RIGHT, Config.RAIL_BOTH]], default=Config.RAIL_BOTH, description="Which sides have railings")),
        ('wbtk_st_ramp_intermediate_posts', bpy.props.IntProperty( # <<< RENAMED for Ramp
            name="Ramp Intermediate Posts", default=0, min=0, max=20,
            description="Extra posts for Ramp stairs railings (0=only start/end)")),
           
           
            # Stairs (Discrete Steps Style)
        ('wbtk_ds_run', bpy.props.FloatProperty(name="Steps Total Run (m)", default=4.0, min=0.1, max=50.0, unit='LENGTH', description="Total horizontal length covered by all steps")),
        ('wbtk_ds_rise', bpy.props.FloatProperty(name="Steps Total Rise (m)", default=2.0, min=0.1, max=50.0, unit='LENGTH', description="Total vertical height covered by all steps")),
        ('wbtk_ds_width_steps', bpy.props.IntProperty(name="Steps Width (Tiles)", default=1, min=1, max=20, description="Width of the steps in walkway tiles")),
        ('wbtk_ds_step_count', bpy.props.IntProperty(name="Steps Count", default=10, min=1, max=100, description="Number of individual steps")),
        ('wbtk_ds_rail', bpy.props.EnumProperty(name="Steps Rails", items=[(v, v.capitalize(), '') for v in [Config.RAIL_NONE, Config.RAIL_LEFT, Config.RAIL_RIGHT, Config.RAIL_BOTH]], default=Config.RAIL_BOTH, description="Which sides have railings")),
        ('wbtk_st_discrete_intermediate_posts', bpy.props.IntProperty(name="Discrete Intermediate Posts", default=0, min=0, max=20,description="Extra posts for Discrete stairs railings (0=only start/end)")),
   

        # === Structure Components (Merged from building_toolkit) ===
        # Wall Generator
        ('wbtk_wall_type', bpy.props.EnumProperty(name="Wall Type", items=[('SOLID', "Solid Wall", "Plain wall with no openings"), ('WINDOW', "Wall with Window", "Wall with window opening"), ('DOOR', "Wall with Door", "Wall with doorway opening")], default='SOLID', description="Type of wall segment to generate")),
        ('wbtk_wall_length', bpy.props.IntProperty(name="Wall Length (Tiles)", default=5, min=1, max=100, description="Length of the wall in default tiles (e.g., 2m)")),
        ('wbtk_wall_height', bpy.props.FloatProperty(name="Wall Height (m)", default=Config.DEFAULT_WALL_HEIGHT, min=1.0, max=10.0, description="Height of the wall in meters")),
        ('wbtk_wall_thickness', bpy.props.FloatProperty(name="Wall Thickness (m)", default=Config.WALL_THICKNESS, min=0.05, max=1.0, description="Thickness of the wall in meters")),
        # Room Generator
        ('wbtk_room_width', bpy.props.IntProperty(name="Room Width (Tiles)", default=5, min=1, max=50, description="Width of the room interior in default tiles")),
        ('wbtk_room_length', bpy.props.IntProperty(name="Room Length (Tiles)", default=5, min=1, max=50, description="Length of the room interior in default tiles")),
        # Inside properties.py -> PropertyManager class -> _properties list

        # --- Building Shell Generator ---
        ('wbtk_building_shape', bpy.props.EnumProperty(
            name="Building Shape",
            items=[
                ('RECT', "Rectangle", "Standard 4-sided building"),
                ('L_SHAPE', "L-Shape", "Main body with one wing"),
                ('U_SHAPE', "U-Shape", "Main body with two wings forming a courtyard"),
                ('T_SHAPE', "T-Shape", "Main body with a centered wing"),
                ('CORNER_CUT', "Corner Cut (5-sided)", "Rectangle with one chamfered corner for a corner entrance"),
            ],
            default='RECT',
            description="Footprint shape of the building")),
        ('wbtk_building_width', bpy.props.IntProperty(name="Building Width (Tiles)", default=4, min=1, max=50, description="Width of the building shell footprint in tiles")),
        ('wbtk_building_depth', bpy.props.IntProperty(name="Building Depth (Tiles)", default=4, min=1, max=50, description="Depth of the building shell footprint in tiles")),
        ('wbtk_building_wing_width', bpy.props.IntProperty(
            name="Wing Width (Tiles)", default=2, min=1, max=20,
            description="Width of each wing in tiles (L/U/T shapes)")),
        ('wbtk_building_wing_depth', bpy.props.IntProperty(
            name="Wing Depth (Tiles)", default=2, min=1, max=20,
            description="How far each wing extends in tiles (L/U/T shapes)")),
        ('wbtk_building_wing_wall_type', bpy.props.EnumProperty(
            name="Wing Walls", items=[('WINDOW', "Window", ""), ('SOLID', "Solid", ""), ('DOOR', "Door", "")],
            default='WINDOW', description="Wall type for wing exterior faces")),
        ('wbtk_building_wing_position', bpy.props.EnumProperty(
            name="Wing Position",
            items=[
                ('BACK_LEFT', "Back-Left", "Wing extends from back-left corner"),
                ('BACK_RIGHT', "Back-Right", "Wing extends from back-right corner"),
                ('FRONT_LEFT', "Front-Left", "Wing extends from front-left corner"),
                ('FRONT_RIGHT', "Front-Right", "Wing extends from front-right corner"),
            ],
            default='BACK_LEFT',
            description="Where the L-shape wing attaches (L-shape only)")),
        ('wbtk_building_courtyard_wall_type', bpy.props.EnumProperty(
            name="Courtyard Walls",
            items=[('SOLID', "Solid", ""), ('WINDOW', "Window", ""), ('DOOR', "Door", "")],
            default='SOLID',
            description="Wall type for inner courtyard-facing walls (U-shape only)")),
        ('wbtk_building_corner_cut_size', bpy.props.FloatProperty(
            name="Corner Cut (m)", default=3.0, min=1.0, max=15.0, unit='LENGTH',
            description="Size of the chamfered corner in meters")),
        ('wbtk_building_corner_cut_pos', bpy.props.EnumProperty(
            name="Cut Corner",
            items=[
                ('FRONT_LEFT', "Front-Left", "Cut the front-left corner"),
                ('FRONT_RIGHT', "Front-Right", "Cut the front-right corner"),
                ('BACK_LEFT', "Back-Left", "Cut the back-left corner"),
                ('BACK_RIGHT', "Back-Right", "Cut the back-right corner"),
            ],
            default='FRONT_LEFT',
            description="Which corner to chamfer")),
        ('wbtk_building_floors', bpy.props.IntProperty(name="Building Floors", default=2, min=1, max=10, description="Number of floors (each using default wall height)")),
        ('wbtk_building_add_roof', bpy.props.BoolProperty(name="Add Roof", default=True, description="Generate a flat roof on top of the building shell")),
        # +++ WALL SURFACE STYLE +++
        ('wbtk_building_wall_style', bpy.props.EnumProperty(
            name="Wall Style",
            items=[
                ('FLAT', "Flat", "Smooth flat walls (default)"),
                ('PANELED', "Paneled", "Vertical panel grooves"),
                ('RIBBED', "Ribbed", "Horizontal corrugation"),
                ('TILED', "Tiled", "Brick/tile subdivision"),
            ],
            default='FLAT',
            description="Surface treatment for wall faces (FLAT active, others planned)")),
        # +++ ADD FACADE WALL TYPE PROPERTIES BELOW +++
        ('wbtk_building_front_wall_type', bpy.props.EnumProperty(
            name="Front Wall", items=[('SOLID', "Solid", ""), ('WINDOW', "Window", ""), ('DOOR', "Door", "")],
            default='DOOR', description="Type for the front (+Y / South facing) wall sections")),
        ('wbtk_building_back_wall_type', bpy.props.EnumProperty(
            name="Back Wall", items=[('SOLID', "Solid", ""), ('WINDOW', "Window", ""), ('DOOR', "Door", "")],
            default='WINDOW', description="Type for the back (-Y / North facing) wall sections")),
        ('wbtk_building_left_wall_type', bpy.props.EnumProperty(
            name="Left Wall", items=[('SOLID', "Solid", ""), ('WINDOW', "Window", ""), ('DOOR', "Door", "")],
            default='WINDOW', description="Type for the left (-X / West facing) wall sections")),
        ('wbtk_building_right_wall_type', bpy.props.EnumProperty(
            name="Right Wall", items=[('SOLID', "Solid", ""), ('WINDOW', "Window", ""), ('DOOR', "Door", "")],
            default='WINDOW', description="Type for the right (+X / East facing) wall sections")),
        ('wbtk_building_floor_height', bpy.props.FloatProperty(
            name="Floor Height (m)", default=Config.DEFAULT_WALL_HEIGHT, min=1.0, max=10.0, unit='LENGTH',
            description="Height for each individual floor/story")),
        ('wbtk_building_add_floor_slabs', bpy.props.BoolProperty(
            name="Add Floor Slabs", default=True,
            description="Add horizontal plane geometry between floors (useful for interiors)")),
        ('wbtk_building_add_ledge', bpy.props.BoolProperty(
            name="Add Ledges", default=False,
            description="Add horizontal ledges/trim around the building exterior")),
        ('wbtk_building_ledge_every_n_floors', bpy.props.IntProperty(
            name="Ledge Every N Floors", default=1, min=1, max=10,
            description="Frequency of ledges (1 = every floor, 2 = every second floor, etc.)")),
        ('wbtk_building_ledge_height', bpy.props.FloatProperty(
            name="Ledge Height (m)", default=0.15, min=0.01, max=1.0, unit='LENGTH',
            description="Vertical thickness of the ledge geometry")),
        ('wbtk_building_ledge_depth', bpy.props.FloatProperty(
            name="Ledge Depth (m)", default=0.15, min=0.01, max=1.0, unit='LENGTH',
            description="How far the ledge protrudes outwards from the wall")),
        ('wbtk_building_ledge_offset_z', bpy.props.FloatProperty(
            name="Ledge Z Offset (m)", default=0.0, min=-1.0, max=5.0, unit='LENGTH',
            description="Vertical offset of the ledge's bottom relative to the floor level (e.g., 0 = at floor, -0.1 = slightly below)")),
        # +++ END FLOOR HEIGHT/SLAB PROPS +++
        
        # +++ END OF NEW PROPERTIES +++


        # === Support Components ===
        # ... (Support Tower properties) ...

        # === Prop Components (Merged from building_toolkit) ===
        # Crate Generator
        ('wbtk_crate_width', bpy.props.FloatProperty(name="Crate Width (m)", default=1.0, min=0.2, max=5.0)),
        ('wbtk_crate_depth', bpy.props.FloatProperty(name="Crate Depth (m)", default=1.0, min=0.2, max=5.0)),
        ('wbtk_crate_height', bpy.props.FloatProperty(name="Crate Height (m)", default=1.0, min=0.2, max=5.0)),
        ('wbtk_crate_inset_amount', bpy.props.FloatProperty(name="Crate Inset Amount (m)", default=0.02, min=0.0, max=0.1, description="How far to inset the crate panels")),
        ('wbtk_crate_add_insets', bpy.props.BoolProperty(name="Crate Add Insets", default=True, description="Add inset panels to the crate sides")),
        # Barrel Generator (Basic)
        ('wbtk_barrel_radius', bpy.props.FloatProperty(name="Barrel Radius (m)", default=0.25, min=0.1, max=1.0)),
        ('wbtk_barrel_height', bpy.props.FloatProperty(name="Barrel Height (m)", default=0.8, min=0.2, max=2.0)),
        ('wbtk_barrel_sides', bpy.props.IntProperty(name="Barrel Sides", default=16, min=8, max=32)),
        ('wbtk_barrel_ribs', bpy.props.IntProperty(name="Barrel Rib Count", default=2, min=0, max=5, description="Number of reinforcing ribs (ignored by Metal Barrel)")),
        ('wbtk_barrel_rib_width', bpy.props.FloatProperty(name="Barrel Rib Width (m)", default=0.05, min=0.01, max=0.2, description="Width of the rib geometry (ignored by Metal Barrel)")),
        ('wbtk_barrel_rib_extrude', bpy.props.FloatProperty(name="Barrel Rib Extrusion (m)", default=0.02, min=0.01, max=0.1, description="How far the ribs stick out (ignored by Metal Barrel)")),
        # Vendor Stall Generator
        ('wbtk_stall_width', bpy.props.FloatProperty(name="Stall Width (m)", default=2.0, min=0.5, max=5.0)),
        ('wbtk_stall_depth', bpy.props.FloatProperty(name="Stall Depth (m)", default=1.5, min=0.5, max=5.0)),
        ('wbtk_stall_height', bpy.props.FloatProperty(name="Stall Height (m)", default=2.0, min=1.0, max=5.0, description="Height of the back posts")),
        ('wbtk_stall_add_table', bpy.props.BoolProperty(name="Stall Add Table", default=True, description="Include a simple table surface")),
        ('wbtk_stall_slope_amount', bpy.props.FloatProperty(name="Stall Roof Slope (m)", default=0.2,min=0.0,max=1.0, description="Vertical drop from back to front posts for angled roof")),
        # Neon Sign Generator
        ('wbtk_sign_width', bpy.props.FloatProperty(name="Sign Width (m)", default=2.0, min=0.1, max=10.0)),
        ('wbtk_sign_height', bpy.props.FloatProperty(name="Sign Height (m)", default=1.0, min=0.1, max=10.0)),
        ('wbtk_sign_frame_thickness', bpy.props.FloatProperty(name="Sign Frame Thick (m)", default=0.05, min=0.01, max=0.2, description="Thickness of the sign's frame/border (if applicable)")),

        # === Fence Components (Merged from building_toolkit) ===
        # Vertical Fence Generator
        ('wbtk_vfence_width', bpy.props.FloatProperty(name="V-Fence Width (m)", default=4.0, min=1.0, max=50.0)),
        ('wbtk_vfence_height', bpy.props.FloatProperty(name="V-Fence Height (m)", default=1.0, min=0.5, max=5.0)),
        ('wbtk_vfence_bar_spacing', bpy.props.FloatProperty(name="V-Fence Bar Spacing (m)", default=0.3, min=0.1, max=2.0)),
        ('wbtk_vfence_post_thickness', bpy.props.FloatProperty(name="V-Fence Post Thick (m)", default=0.05, min=0.01, max=0.2)),
        # Chain-Link Fence Generator
        ('wbtk_clfence_width', bpy.props.FloatProperty(name="CL-Fence Width (m)", default=4.0, min=1.0, max=50.0)),
        ('wbtk_clfence_height', bpy.props.FloatProperty(name="CL-Fence Height (m)", default=2.0, min=1.0, max=5.0)),
        ('wbtk_clfence_post_spacing', bpy.props.FloatProperty(name="CL-Fence Post Spacing (m)", default=2.0, min=1.0, max=5.0)),
        ('wbtk_clfence_bar_thickness', bpy.props.FloatProperty(name="CL-Fence Bar Thick (m)", default=0.05, min=0.01, max=0.2)),
        ('wbtk_clfence_mesh_divisions', bpy.props.IntProperty(name="CL-Fence Mesh Divs", default=10, min=2, max=50, description="Subdivisions for the chainlink mesh panel")),
        ('wbtk_clfence_post_shape', bpy.props.EnumProperty(name="CL-Fence Post Shape", items=[('SQUARE', "Square", "Square posts"), ('CYLINDER', "Cylinder", "Cylindrical posts")], default='SQUARE', description="Shape for chain-link fence posts")),

        # === Ground / Surface Components (Merged from building_toolkit) ===
        ('wbtk_ground_width', bpy.props.IntProperty(name="Ground Width (Tiles)", default=10, min=1, max=100)),
        ('wbtk_ground_depth', bpy.props.IntProperty(name="Ground Depth (Tiles)", default=10, min=1, max=100)),
        ('wbtk_ground_tile_size', bpy.props.FloatProperty(name="Ground Tile Size (m)", default=Config.DEFAULT_TILE_SIZE, min=0.5, max=10.0)),


        ('wbtk_tower_height', bpy.props.FloatProperty(
            name="Tower Height (m)", default=5.0, min=0.1, max=100.0, unit='LENGTH',
            description="Total height of the support tower pillar (excluding base/cap unless they replace part of height)")),
        ('wbtk_tower_shape', bpy.props.EnumProperty(
            name="Tower Shape", items=[('SQUARE', "Square", "Square cross-section"), ('CYLINDER', "Cylinder", "Circular cross-section")],
            default='SQUARE', description="Cross-section shape of the main tower pillar")),
        ('wbtk_tower_dimension', bpy.props.FloatProperty(
            name="Tower Dimension (m)", default=0.5, min=0.05, max=10.0, unit='LENGTH',
            description="Width/Depth for Square shape, Radius for Cylinder shape")),
        ('wbtk_tower_segments', bpy.props.IntProperty(
            name="Tower Segments", default=16, min=3, max=64,
            description="Number of segments for Cylinder shape (higher is smoother)")),
        # Base Options
        ('wbtk_tower_add_base', bpy.props.BoolProperty(
            name="Add Base", default=False,
            description="Add a simple block base at the bottom of the tower")),
        ('wbtk_tower_base_height', bpy.props.FloatProperty(
            name="Base Height (m)", default=0.3, min=0.01, max=5.0, unit='LENGTH',
            description="Height of the base block")),
        ('wbtk_tower_base_size_factor', bpy.props.FloatProperty(
            name="Base Size Factor", default=1.5, min=1.0, max=5.0, precision=2,
            description="How much wider/larger the base is compared to the tower dimension (1.0 = same size)")),
        # Cap Options
        ('wbtk_tower_add_cap', bpy.props.BoolProperty(
            name="Add Cap", default=False,
            description="Add a simple block cap at the top of the tower")),
        ('wbtk_tower_cap_height', bpy.props.FloatProperty(
            name="Cap Height (m)", default=0.2, min=0.01, max=5.0, unit='LENGTH',
            description="Height of the cap block")),
        ('wbtk_tower_cap_size_factor', bpy.props.FloatProperty(
            name="Cap Size Factor", default=1.2, min=1.0, max=5.0, precision=2,
            description="How much wider/larger the cap is compared to the tower dimension (1.0 = same size)")),
        # --- END Support Components ---


        # === Foliage — Shared ===
        ('wbtk_foliage_preset', bpy.props.EnumProperty(
            name="Foliage Preset",
            items=[
                ('NONE', '— Select Preset —', ''),
                ('VJOLDRHEIM_PINE',    'Vjoldrheim — Pine',           ''),
                ('VJOLDRHEIM_BIRCH',   'Vjoldrheim — Birch',          ''),
                ('VJOLDRHEIM_SHRUB',   'Vjoldrheim — Nordic Shrub',   ''),
                ('VJOLDRHEIM_MOSS',    'Vjoldrheim — Forest Floor Moss', ''),
                ('TIERRA_DRY_TREE',    'Tierra Oxidada — Dead Tree',  ''),
                ('TIERRA_SCRUB',       'Tierra Oxidada — Desert Scrub', ''),
                ('TIERRA_DRY_GRASS',   'Tierra Oxidada — Dry Grass',  ''),
                ('DUSK_CITY_WEED',     'Dusk Ward — City Weed',       ''),
                ('DUSK_CITY_TREE',     'Dusk Ward — Scraggly City Tree', ''),
                ('RADIANT_ORNAMENTAL', 'Radiant Circle — Ornamental Tree', ''),
                ('RADIANT_HEDGE',      'Radiant Circle — Manicured Hedge', ''),
                ('GENERIC_TREE',       'Generic — Basic Tree',        ''),
                ('GENERIC_SHRUB',      'Generic — Basic Shrub',       ''),
                ('GENERIC_GRASS',      'Generic — Basic Grass',       ''),
            ],
            default='NONE',
            description="Load a region-specific foliage preset into the sliders"
        )),
        ('wbtk_foliage_seed', bpy.props.IntProperty(
            name="Random Seed",
            default=1, min=0, max=9999,
            description="Change this number to get a different variation of the same settings"
        )),

        # === Foliage — Tree ===
        ('wbtk_tree_height', bpy.props.FloatProperty(
            name="Tree Height (m)", default=5.0, min=0.5, max=30.0, unit='LENGTH')),
        ('wbtk_trunk_radius', bpy.props.FloatProperty(
            name="Trunk Radius (m)", default=0.15, min=0.02, max=2.0, unit='LENGTH')),
        ('wbtk_trunk_taper', bpy.props.FloatProperty(
            name="Trunk Taper", default=0.75, min=0.2, max=1.0,
            description="How much the trunk narrows toward the top (1.0 = no taper)")),
        ('wbtk_branch_levels', bpy.props.IntProperty(
            name="Branch Levels", default=2, min=1, max=4,
            description="Recursion depth — 1 = trunk only, 2 = primary branches, 3 = secondary")),
        ('wbtk_branch_count', bpy.props.IntProperty(
            name="Branches per Level", default=5, min=2, max=12)),
        ('wbtk_branch_angle', bpy.props.FloatProperty(
            name="Branch Angle (°)", default=55.0, min=10.0, max=90.0,
            description="Angle branches grow away from the parent — higher = more spread out")),
        ('wbtk_branch_length_factor', bpy.props.FloatProperty(
            name="Branch Length Factor", default=0.60, min=0.2, max=0.9,
            description="Child branch length as fraction of parent length")),
        ('wbtk_branch_taper', bpy.props.FloatProperty(
            name="Branch Taper", default=0.70, min=0.2, max=1.0)),
        ('wbtk_leaf_density', bpy.props.IntProperty(
            name="Leaf Density", default=35, min=0, max=150,
            description="Number of leaf cards per tip cluster")),
        ('wbtk_leaf_size', bpy.props.FloatProperty(
            name="Leaf Size (m)", default=0.25, min=0.02, max=1.5, unit='LENGTH')),
        ('wbtk_leaf_shape', bpy.props.EnumProperty(
            name="Leaf Shape",
            items=[('ROUND', 'Round', 'Broad round leaves'), ('NEEDLE', 'Needle', 'Elongated needle/pine leaves')],
            default='ROUND'
        )),
        ('wbtk_leaf_droop', bpy.props.FloatProperty(
            name="Leaf Droop", default=0.20, min=0.0, max=1.0,
            description="How much leaf tips droop downward — 0 = flat, 1 = heavy droop")),

        # === Foliage — Shrub ===
        ('wbtk_shrub_height', bpy.props.FloatProperty(
            name="Shrub Height (m)", default=1.0, min=0.1, max=5.0, unit='LENGTH')),
        ('wbtk_shrub_width', bpy.props.FloatProperty(
            name="Shrub Width (m)", default=1.2, min=0.1, max=8.0, unit='LENGTH')),
        ('wbtk_shrub_branch_count', bpy.props.IntProperty(
            name="Branch Count", default=10, min=3, max=40)),
        ('wbtk_shrub_branch_angle', bpy.props.FloatProperty(
            name="Branch Angle (°)", default=50.0, min=5.0, max=85.0)),
        ('wbtk_shrub_leaf_density', bpy.props.IntProperty(
            name="Leaf Density", default=30, min=0, max=120)),
        ('wbtk_shrub_leaf_size', bpy.props.FloatProperty(
            name="Leaf Size (m)", default=0.15, min=0.02, max=0.8, unit='LENGTH')),
        ('wbtk_shrub_leaf_shape', bpy.props.EnumProperty(
            name="Leaf Shape",
            items=[('ROUND', 'Round', ''), ('NEEDLE', 'Needle', '')],
            default='ROUND'
        )),

        # === Foliage — Ground Cover ===
        ('wbtk_ground_type', bpy.props.EnumProperty(
            name="Cover Type",
            items=[
                ('GRASS', 'Grass', 'Tapered grass blades'),
                ('WEED',  'Weed',  'Tufted weeds — good for alley cracks'),
                ('MOSS',  'Moss',  'Low flat moss patches'),
            ],
            default='GRASS'
        )),
        ('wbtk_ground_patch_radius', bpy.props.FloatProperty(
            name="Patch Radius (m)", default=0.5, min=0.05, max=5.0, unit='LENGTH')),
        ('wbtk_ground_blade_count', bpy.props.IntProperty(
            name="Blade / Tuft Count", default=40, min=5, max=300)),
        ('wbtk_ground_blade_height', bpy.props.FloatProperty(
            name="Blade Height (m)", default=0.20, min=0.02, max=1.5, unit='LENGTH')),
        ('wbtk_ground_blade_width', bpy.props.FloatProperty(
            name="Blade Width (m)", default=0.02, min=0.005, max=0.2, unit='LENGTH')),
        ('wbtk_ground_droop', bpy.props.FloatProperty(
            name="Droop / Tilt", default=0.25, min=0.0, max=1.0,
            description="How much blades lean and droop — 0 = straight up, 1 = heavily tilted")),
        ('wbtk_ground_cluster_scatter', bpy.props.FloatProperty(
            name="Scatter", default=0.5, min=0.0, max=1.0,
            description="How spread out blades are within the patch radius")),

        # === Building Enhancements ===

        # Edge bevel (futuristic edge definition)
        ('wbtk_building_add_bevel', bpy.props.BoolProperty(
            name="Add Edge Bevel", default=False,
            description="Add a bevel modifier for clean edge definition — gives that futuristic look")),
        ('wbtk_building_bevel_width', bpy.props.FloatProperty(
            name="Bevel Width (m)", default=0.05, min=0.005, max=0.3, unit='LENGTH',
            description="Width of the edge bevel chamfer")),
        ('wbtk_building_bevel_segments', bpy.props.IntProperty(
            name="Bevel Segments", default=2, min=1, max=6,
            description="Smoothness of the bevel — 1 = hard chamfer, 3+ = rounded")),

        # Window configuration
        ('wbtk_building_window_count', bpy.props.EnumProperty(
            name="Windows Per Wall",
            items=[
                ('AUTO', "Auto (fit to width)", "Automatically space windows based on wall width"),
                ('1', "1 Window", ""),
                ('2', "2 Windows", ""),
                ('3', "3 Windows", ""),
                ('4', "4 Windows", ""),
                ('5', "5 Windows", ""),
            ],
            default='AUTO',
            description="Number of windows per wall section per floor")),
        ('wbtk_building_window_width', bpy.props.FloatProperty(
            name="Window Width (m)", default=1.0, min=0.3, max=4.0, unit='LENGTH',
            description="Width of each window opening")),
        ('wbtk_building_window_height', bpy.props.FloatProperty(
            name="Window Height (m)", default=1.0, min=0.3, max=3.0, unit='LENGTH',
            description="Height of each window opening")),

        # Door entrance configuration
        ('wbtk_building_door_style', bpy.props.EnumProperty(
            name="Door Style",
            items=[
                ('FLAT', "Flat", "Simple opening with no depth"),
                ('RECESSED', "Recessed", "Straight inset doorway with depth"),
                ('ANGLED', "Angled", "Splayed jambs that angle inward"),
            ],
            default='RECESSED',
            description="Entrance style for doorway openings")),
        ('wbtk_building_door_width', bpy.props.FloatProperty(
            name="Door Width (m)", default=1.2, min=0.5, max=4.0, unit='LENGTH',
            description="Width of the doorway opening")),
        ('wbtk_building_door_height', bpy.props.FloatProperty(
            name="Door Height (m)", default=2.5, min=1.5, max=4.0, unit='LENGTH',
            description="Height of the doorway opening")),
        ('wbtk_building_door_inset', bpy.props.FloatProperty(
            name="Door Inset (m)", default=0.2, min=0.05, max=1.0, unit='LENGTH',
            description="How deep the doorway is recessed into the wall")),
        ('wbtk_building_door_splay', bpy.props.FloatProperty(
            name="Splay Angle (°)", default=30.0, min=5.0, max=60.0,
            description="Angle of the splayed jambs for angled doorways")),

        # Corner columns
        ('wbtk_building_add_corners', bpy.props.BoolProperty(
            name="Add Corner Columns", default=False,
            description="Add extruded pilaster columns at each corner of the building")),
        ('wbtk_building_corner_width', bpy.props.FloatProperty(
            name="Column Width (m)", default=0.3, min=0.05, max=2.0, unit='LENGTH',
            description="Width of the corner column face along the wall")),
        ('wbtk_building_corner_protrusion', bpy.props.FloatProperty(
            name="Column Protrusion (m)", default=0.15, min=0.02, max=1.0, unit='LENGTH',
            description="How far the corner columns stick out from the wall face")),

        # Horizontal banding
        ('wbtk_building_add_bands', bpy.props.BoolProperty(
            name="Add Horizontal Bands", default=False,
            description="Add decorative horizontal trim strips between floors")),
        ('wbtk_building_band_every_n', bpy.props.IntProperty(
            name="Band Every N Floors", default=1, min=1, max=10,
            description="Place a band at every N floor boundaries")),
        ('wbtk_building_band_height', bpy.props.FloatProperty(
            name="Band Height (m)", default=0.1, min=0.02, max=0.5, unit='LENGTH')),
        ('wbtk_building_band_protrusion', bpy.props.FloatProperty(
            name="Band Protrusion (m)", default=0.08, min=0.01, max=0.3, unit='LENGTH',
            description="How far the band sticks out from the wall face")),

        # Window sill shelves
        ('wbtk_building_add_sills', bpy.props.BoolProperty(
            name="Add Window Sills", default=False,
            description="Add protruding shelf below each window opening")),
        ('wbtk_building_sill_depth', bpy.props.FloatProperty(
            name="Sill Depth (m)", default=0.12, min=0.02, max=0.5, unit='LENGTH')),
        ('wbtk_building_sill_height', bpy.props.FloatProperty(
            name="Sill Height (m)", default=0.06, min=0.01, max=0.2, unit='LENGTH')),

        # Parapet wall
        ('wbtk_building_add_parapet', bpy.props.BoolProperty(
            name="Add Parapet Wall", default=False,
            description="Add a raised wall around the roof perimeter")),
        ('wbtk_building_parapet_height', bpy.props.FloatProperty(
            name="Parapet Height (m)", default=0.8, min=0.1, max=3.0, unit='LENGTH')),
        ('wbtk_building_parapet_thickness', bpy.props.FloatProperty(
            name="Parapet Thickness (m)", default=0.2, min=0.05, max=0.6, unit='LENGTH')),

        # Base plinth
        ('wbtk_building_add_plinth', bpy.props.BoolProperty(
            name="Add Base Plinth", default=False,
            description="Add a thicker protruding base section at ground level")),
        ('wbtk_building_plinth_height', bpy.props.FloatProperty(
            name="Plinth Height (m)", default=0.6, min=0.1, max=3.0, unit='LENGTH')),
        ('wbtk_building_plinth_protrusion', bpy.props.FloatProperty(
            name="Plinth Protrusion (m)", default=0.1, min=0.02, max=0.5, unit='LENGTH')),

        # === Building Randomization ===
        ('wbtk_building_use_seed', bpy.props.BoolProperty(
            name="Randomize Per Floor", default=False,
            description="Use a seed to randomize wall types per floor. "
                        "Ground floor keeps your facade settings, upper floors get random Solid/Window mix")),
        ('wbtk_building_seed', bpy.props.IntProperty(
            name="Building Seed", default=1, min=0, max=9999,
            description="Change this number for a different variation of the same base settings")),
        ('wbtk_building_window_chance', bpy.props.FloatProperty(
            name="Window Chance", default=0.6, min=0.0, max=1.0,
            description="Probability (0-1) that an upper floor wall gets a window when randomized. "
                        "0 = all solid, 1 = all windows")),

        # === Batch Row Generation ===
        ('wbtk_batch_count', bpy.props.IntProperty(
            name="Building Count", default=3, min=2, max=20,
            description="Number of buildings to generate in a row")),
        ('wbtk_batch_spacing', bpy.props.FloatProperty(
            name="Gap Between (m)", default=1.0, min=0.0, max=10.0, unit='LENGTH',
            description="Gap between buildings in the row")),
        ('wbtk_batch_direction', bpy.props.EnumProperty(
            name="Row Direction",
            items=[('X', "Along X", "Buildings placed along X axis"),
                   ('Y', "Along Y", "Buildings placed along Y axis")],
            default='X',
            description="Which axis the row of buildings follows")),
        ('wbtk_batch_vary_floors', bpy.props.BoolProperty(
            name="Vary Floor Count", default=True,
            description="Each building gets a random floor count within +/- 2 of your setting")),
        ('wbtk_batch_vary_width', bpy.props.BoolProperty(
            name="Vary Width", default=True,
            description="Each building gets a random width within +/- 1 tile of your setting")),

        # === UE Pipeline & Face Magnet ===
        ('wbtk_fm_offset', bpy.props.FloatProperty(
            name="Surface Offset",
            description="Gap between snapped object and target face (0 = flush contact)",
            default=0.0, min=0.0, max=2.0, step=1, precision=3, unit='LENGTH'
        )),
        ('wbtk_fm_align_normal', bpy.props.BoolProperty(
            name="Align to Face Normal",
            description="Rotate the snapped object to face outward from the target surface",
            default=True
        )),
        ('wbtk_export_include_ucx', bpy.props.BoolProperty(
            name="Include UCX Colliders",
            description="Also move UCX_ collision meshes when sending to UE Export collection",
            default=True
        )),

        # === Prop Components === # (Make sure this section comes AFTER the new props)
        # ... (Crate properties, etc.) ...

        # === Pipe Generator ===
        ('wbtk_pipe_length', bpy.props.FloatProperty(
            name="Pipe Length (m)", default=4.0, min=0.1, max=100.0, unit='LENGTH')),
        ('wbtk_pipe_radius', bpy.props.FloatProperty(
            name="Pipe Radius (m)", default=0.08, min=0.01, max=2.0, unit='LENGTH')),
        ('wbtk_pipe_wall_thickness', bpy.props.FloatProperty(
            name="Wall Thickness (m)", default=0.01, min=0.002, max=0.5, unit='LENGTH')),
        ('wbtk_pipe_segments', bpy.props.IntProperty(
            name="Pipe Segments", default=16, min=6, max=64)),
        ('wbtk_pipe_subdivisions', bpy.props.IntProperty(
            name="Pipe Subdivisions", default=8, min=1, max=50)),
        ('wbtk_pipe_axis', bpy.props.EnumProperty(
            name="Pipe Axis",
            items=[('X', "X Axis", ""), ('Y', "Y Axis", ""), ('Z', "Z Axis", "")],
            default='X')),
        ('wbtk_pipe_add_flanges', bpy.props.BoolProperty(
            name="Add Flanges", default=True)),
        ('wbtk_pipe_flange_spacing', bpy.props.FloatProperty(
            name="Flange Spacing (m)", default=2.0, min=0.2, max=20.0, unit='LENGTH')),
        ('wbtk_pipe_add_clamps', bpy.props.BoolProperty(
            name="Add Clamps", default=True)),
        ('wbtk_pipe_clamp_spacing', bpy.props.FloatProperty(
            name="Clamp Spacing (m)", default=1.5, min=0.3, max=10.0, unit='LENGTH')),
        ('wbtk_pipe_wear_preset', bpy.props.EnumProperty(
            name="Wear Preset",
            items=[
                ('CLEAN', "Clean", ""),
                ('WEATHERED', "Weathered", ""),
                ('CORRODED', "Corroded", ""),
                ('BUSTED', "Busted", ""),
                ('CUSTOM', "Custom", ""),
            ], default='WEATHERED')),
        ('wbtk_pipe_dent_intensity', bpy.props.FloatProperty(
            name="Dent Intensity", default=0.3, min=0.0, max=1.0, subtype='FACTOR')),
        ('wbtk_pipe_roughness', bpy.props.FloatProperty(
            name="Surface Roughness", default=0.4, min=0.0, max=1.0, subtype='FACTOR')),
        ('wbtk_pipe_corrosion', bpy.props.FloatProperty(
            name="Corrosion Holes", default=0.0, min=0.0, max=1.0, subtype='FACTOR')),
        ('wbtk_pipe_drip_count', bpy.props.IntProperty(
            name="Drip Count", default=2, min=0, max=20)),
        ('wbtk_pipe_wear_seed', bpy.props.IntProperty(
            name="Wear Seed", default=12345, min=1, max=99999)),
        ('wbtk_pipe_run_leg1', bpy.props.FloatProperty(
            name="Leg 1 Length (m)", default=3.0, min=0.1, max=50.0, unit='LENGTH')),
        ('wbtk_pipe_run_leg2', bpy.props.FloatProperty(
            name="Leg 2 Length (m)", default=2.0, min=0.1, max=50.0, unit='LENGTH')),
        ('wbtk_pipe_run_bend_plane', bpy.props.EnumProperty(
            name="Bend Plane",
            items=[('XY', "XY (Horizontal)", ""), ('XZ', "XZ (Vertical)", "")],
            default='XZ')),
        ('wbtk_pipe_run_bend_radius', bpy.props.FloatProperty(
            name="Bend Radius (m)", default=0.2, min=0.05, max=2.0, unit='LENGTH')),
        ('wbtk_pipe_bundle_count', bpy.props.IntProperty(
            name="Bundle Count", default=3, min=1, max=12)),
        ('wbtk_pipe_bundle_spread', bpy.props.FloatProperty(
            name="Bundle Spread (m)", default=0.3, min=0.05, max=2.0, unit='LENGTH')),

        # === Cable / Wire Generator ===
        ('wbtk_cable_span', bpy.props.FloatProperty(
            name="Cable Span (m)", default=8.0, min=0.5, max=200.0, unit='LENGTH')),
        ('wbtk_cable_sag', bpy.props.FloatProperty(
            name="Cable Sag (m)", default=0.8, min=0.0, max=20.0, unit='LENGTH')),
        ('wbtk_cable_radius', bpy.props.FloatProperty(
            name="Cable Radius (m)", default=0.015, min=0.002, max=0.2, unit='LENGTH')),
        ('wbtk_cable_segments', bpy.props.IntProperty(
            name="Cable Segments", default=24, min=4, max=100)),
        ('wbtk_cable_twist', bpy.props.FloatProperty(
            name="Cable Twist", default=0.02, min=0.0, max=0.5, unit='LENGTH')),
        ('wbtk_cable_height', bpy.props.FloatProperty(
            name="Cable Height (m)", default=4.0, min=0.0, max=50.0, unit='LENGTH')),
        ('wbtk_cable_seed', bpy.props.IntProperty(
            name="Cable Seed", default=7777, min=1, max=99999)),
        ('wbtk_cable_bundle_count', bpy.props.IntProperty(
            name="Cable Bundle Count", default=4, min=1, max=20)),
        ('wbtk_cable_bundle_spread', bpy.props.FloatProperty(
            name="Cable Spread (m)", default=0.15, min=0.01, max=1.0, unit='LENGTH')),
        ('wbtk_cable_between_mode', bpy.props.BoolProperty(
            name="Between Selected", default=False,
            description="Generate cable between two selected objects instead of manual span")),

        # === Surface Scatter ===
        # --- Block Composer (Phase 2) ---
        # --- Footprint Painter ---
        # --- Build Mode ---
        ('wbtk_bm_width', bpy.props.FloatProperty(
            name="Width", default=4.0, min=0.5, max=50.0, step=50,
            description="Block width (X)", update=_bm_update)),
        ('wbtk_bm_depth', bpy.props.FloatProperty(
            name="Depth", default=4.0, min=0.5, max=50.0, step=50,
            description="Block depth (Y)", update=_bm_update)),
        ('wbtk_bm_height', bpy.props.FloatProperty(
            name="Height", default=Config.DEFAULT_WALL_HEIGHT, min=0.5, max=20.0, step=50,
            description="Block height (Z)", update=_bm_update)),
        ('wbtk_bm_wall_north', bpy.props.EnumProperty(
            name="North", items=_WALL_ITEMS, default='SOLID', update=_bm_update)),
        ('wbtk_bm_wall_south', bpy.props.EnumProperty(
            name="South", items=_WALL_ITEMS, default='SOLID', update=_bm_update)),
        ('wbtk_bm_wall_east', bpy.props.EnumProperty(
            name="East", items=_WALL_ITEMS, default='SOLID', update=_bm_update)),
        ('wbtk_bm_wall_west', bpy.props.EnumProperty(
            name="West", items=_WALL_ITEMS, default='SOLID', update=_bm_update)),
        ('wbtk_bm_chamfer_size', bpy.props.FloatProperty(
            name="Chamfer", default=1.0, min=0.1, max=5.0, step=10,
            description="Corner chamfer size", update=_bm_update)),
        ('wbtk_bm_attach_dir', bpy.props.EnumProperty(
            name="Attach Direction",
            items=[
                ('NORTH', "N", "North (+Y)"),
                ('SOUTH', "S", "South (-Y)"),
                ('EAST', "E", "East (+X)"),
                ('WEST', "W", "West (-X)"),
            ],
            default='EAST')),
        ('wbtk_bm_auto_setback', bpy.props.FloatProperty(
            name="Auto Setback", default=0.0, min=0.0, max=5.0, step=10,
            description="Each stacked floor insets by this amount on all sides")),
        ('wbtk_bm_active', bpy.props.BoolProperty(
            name="Build Mode Active", default=False,
            description="Whether Build Mode is currently active")),
        ('wbtk_bm_grid_size', bpy.props.FloatProperty(
            name="Grid Size", default=20.0, min=5.0, max=100.0, step=100,
            description="Grid floor size in meters")),
        ('wbtk_bm_grid_subdivs', bpy.props.IntProperty(
            name="Grid Subdivisions", default=10, min=2, max=40,
            description="Number of grid line subdivisions")),
        ('wbtk_bm_block_color', bpy.props.FloatVectorProperty(
            name="Block Color", subtype='COLOR',
            default=(0.0, 0.7, 1.0), min=0.0, max=1.0,
            description="Wireframe color for new blocks")),
        ('wbtk_bm_detail_face', bpy.props.EnumProperty(
            name="Face",
            items=[('south',"South",""),('north',"North",""),
                   ('east',"East",""),('west',"West",""),('top',"Roof","")],
            default='south')),
        ('wbtk_bm_detail_offset_x', bpy.props.FloatProperty(
            name="Position X", default=0.5, min=0.0, max=1.0,
            description="Horizontal position along face (0=left, 1=right)")),
        ('wbtk_bm_detail_offset_z', bpy.props.FloatProperty(
            name="Position Z", default=0.5, min=0.0, max=1.0,
            description="Vertical position on face (0=bottom, 1=top)")),
        ('wbtk_bm_detail_scale', bpy.props.FloatProperty(
            name="Scale", default=1.0, min=0.2, max=3.0, step=10,
            description="Detail size multiplier")),

        # --- Custom Builder ---
        ('wbtk_builder_color', bpy.props.FloatVectorProperty(
            name="Block Color", subtype='COLOR',
            default=(0.0, 0.8, 1.0), min=0.0, max=1.0,
            description="Wireframe color for placed blocks")),
        ('wbtk_builder_block_type', bpy.props.EnumProperty(
            name="Block Type",
            items=[
                ('CUBE', "Building Block", "Standard 1-tile building block"),
                ('TOWER', "Tower Block", "Double-height tower column"),
                ('BRIDGE', "Bridge Span", "Horizontal connector between buildings"),
                ('WALKWAY', "Walkway", "Flat platform"),
            ],
            default='CUBE',
            description="Type of block to place")),
        ('wbtk_builder_grid_w', bpy.props.IntProperty(
            name="Grid Width", default=20, min=4, max=60,
            description="Width of the builder grid in tiles")),
        ('wbtk_builder_grid_d', bpy.props.IntProperty(
            name="Grid Depth", default=20, min=4, max=60,
            description="Depth of the builder grid in tiles")),
        ('wbtk_builder_chamfer_size', bpy.props.FloatProperty(
            name="Chamfer Size", default=1.0, min=0.1, max=5.0,
            description="Size of corner chamfer cut in meters")),
        ('wbtk_builder_chamfers', bpy.props.StringProperty(
            name="Chamfer Data", default='[]',
            description="Internal: JSON-encoded chamfered corner positions")),

        # --- Footprint Painter ---
        ('wbtk_fp_grid_w', bpy.props.IntProperty(
            name="Grid Width", default=8, min=2, max=30,
            description="Width of the footprint painting grid in tiles")),
        ('wbtk_fp_grid_h', bpy.props.IntProperty(
            name="Grid Height", default=8, min=2, max=30,
            description="Height of the footprint painting grid in tiles")),
        ('wbtk_fp_grid_data', bpy.props.StringProperty(
            name="Grid Data", default='{}',
            description="Internal: JSON-encoded per-floor tile coordinates")),
        ('wbtk_fp_current_floor', bpy.props.IntProperty(
            name="Floor", default=0, min=0, max=20,
            description="Current floor level to paint tiles on")),

        # --- Block Composer ---
        ('wbtk_block_width', bpy.props.IntProperty(
            name="Block Width (Tiles)", default=20, min=6, max=100,
            description="Width of the city block footprint in tiles")),
        ('wbtk_block_depth', bpy.props.IntProperty(
            name="Block Depth (Tiles)", default=20, min=6, max=100,
            description="Depth of the city block footprint in tiles")),
        ('wbtk_block_alley_width', bpy.props.FloatProperty(
            name="Alley Gap (m)", default=0.5, min=0.0, max=5.0, unit='LENGTH',
            description="Gap between adjacent buildings along each side")),
        ('wbtk_block_seed', bpy.props.IntProperty(
            name="Block Seed", default=42, min=0, max=99999,
            description="Random seed for block variation")),
        ('wbtk_block_min_floors', bpy.props.IntProperty(
            name="Min Floors", default=1, min=1, max=10)),
        ('wbtk_block_max_floors', bpy.props.IntProperty(
            name="Max Floors", default=5, min=1, max=10)),
        ('wbtk_block_min_building_width', bpy.props.IntProperty(
            name="Min Bldg Width", default=2, min=1, max=10,
            description="Minimum building width in tiles")),
        ('wbtk_block_max_building_width', bpy.props.IntProperty(
            name="Max Bldg Width", default=5, min=1, max=20,
            description="Maximum building width in tiles")),
        ('wbtk_block_building_depth', bpy.props.IntProperty(
            name="Bldg Depth (Tiles)", default=3, min=1, max=10,
            description="Depth of each building (how far inward from block edge)")),
        ('wbtk_block_fill_courtyard', bpy.props.BoolProperty(
            name="Fill Courtyard", default=False,
            description="Add a ground plane in the block center")),
        ('wbtk_block_use_shapes', bpy.props.BoolProperty(
            name="Random Shapes", default=False,
            description="Randomly assign L-shape and corner-cut to some buildings")),

        ('wbtk_scatter_prop_type', bpy.props.EnumProperty(
            name="Prop Type",
            items=[
                ('RANDOM_MIX', "Random Mix",  "Randomly pick from all prop types"),
                ('AC_UNIT',    "AC Unit",      "Boxy air conditioning unit"),
                ('WATER_TANK', "Water Tank",   "Cylindrical tank on legs"),
                ('ANTENNA',    "Antenna Mast", "Thin mast with cross-bars"),
                ('CRATE',      "Crate",        "Small wooden crate"),
                ('BARREL',     "Barrel",       "Metal barrel"),
                ('VENT_BOX',   "Vent Box",     "Exhaust vent chimney stub"),
            ],
            default='RANDOM_MIX')),
        ('wbtk_scatter_count', bpy.props.IntProperty(
            name="Prop Count", default=8, min=1, max=100,
            description="Number of props to scatter")),
        ('wbtk_scatter_seed', bpy.props.IntProperty(
            name="Scatter Seed", default=42, min=1, max=99999,
            description="Random seed — different seed = different layout")),
        ('wbtk_scatter_scale', bpy.props.FloatProperty(
            name="Prop Scale", default=1.0, min=0.2, max=3.0,
            description="Overall size multiplier for scattered props")),
        ('wbtk_scatter_margin', bpy.props.FloatProperty(
            name="Edge Margin (m)", default=0.3, min=0.0, max=5.0, unit='LENGTH',
            description="Keep props this far from the edge of the surface")),
        ('wbtk_scatter_random_rotation', bpy.props.BoolProperty(
            name="Random Rotation", default=True,
            description="Randomly rotate each prop around Z axis")),

        # === Live Preview State ===
        ('wbtk_live_preview_active', bpy.props.BoolProperty(
            name="Live Preview Active", default=False)),
        ('wbtk_live_preview_type', bpy.props.StringProperty(
            name="Live Preview Type", default='')),
        # Set when the user turns a BUILD_MODE preview off BY HAND, so entering
        # Build Mode again respects that instead of switching it back on. Live
        # preview is otherwise ON by default in Build Mode (see bm_operators).
        ('wbtk_bm_preview_optout', bpy.props.BoolProperty(
            name="Build Mode Preview Opt-Out", default=False)),

        # === Vent / Grate Generator ===
        ('wbtk_vent_width', bpy.props.FloatProperty(
            name="Vent Width (m)", default=0.6, min=0.1, max=3.0, unit='LENGTH')),
        ('wbtk_vent_height', bpy.props.FloatProperty(
            name="Vent Height (m)", default=0.4, min=0.1, max=3.0, unit='LENGTH')),
        ('wbtk_vent_depth', bpy.props.FloatProperty(
            name="Vent Depth (m)", default=0.06, min=0.01, max=0.5, unit='LENGTH')),
        ('wbtk_vent_slat_count', bpy.props.IntProperty(
            name="Slat Count", default=6, min=1, max=30)),
        ('wbtk_vent_slat_angle', bpy.props.FloatProperty(
            name="Slat Angle (°)", default=45.0, min=0.0, max=85.0)),
        ('wbtk_vent_frame_thickness', bpy.props.FloatProperty(
            name="Frame Thickness (m)", default=0.03, min=0.005, max=0.2, unit='LENGTH')),
        ('wbtk_vent_round_radius', bpy.props.FloatProperty(
            name="Round Vent Radius (m)", default=0.25, min=0.05, max=1.5, unit='LENGTH')),
        ('wbtk_vent_round_segments', bpy.props.IntProperty(
            name="Round Segments", default=24, min=8, max=64)),
        ('wbtk_vent_fan_blades', bpy.props.IntProperty(
            name="Fan Blades", default=5, min=0, max=12)),
    ]

    @staticmethod
    def register_properties():
        """ Registers all defined properties onto the Scene type. """
        scene_type = bpy.types.Scene
        for name, prop in PropertyManager._properties:
            if hasattr(scene_type, name):
                # print(f"Info: Property '{name}' already exists. Skipping registration.")
                pass
            else:
                setattr(scene_type, name, prop)

    @staticmethod
    def unregister_properties():
        """ Unregisters all defined properties from the Scene type. """
        scene_type = bpy.types.Scene
        for name, _ in reversed(PropertyManager._properties):
            if hasattr(scene_type, name):
                try:
                    prop_instance = getattr(scene_type, name, None)
                    # Check if it's actually a property before deleting
                    if isinstance(prop_instance, bpy.props._PropertyDeferred):
                        delattr(scene_type, name)
                except Exception as e:
                    print(f"Warning: Failed to delete scene property '{name}': {e}")