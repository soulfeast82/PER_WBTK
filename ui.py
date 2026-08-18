# World_Building_Toolkit/ui.py

import bpy

# Operator IDs are used directly as strings, no specific imports needed here.
# Properties are accessed via context.scene, no specific imports needed here.

# --- Base Panel Settings ---
class WBTK_PanelBase(bpy.types.Panel):
    """ Base class for all World Builder Toolkit panels """
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'World Builder' # Sidebar Tab Name


def _draw_live_preview_toggle(layout, scene, gen_type):
    """Draw a Live Preview toggle button for a generator type.
    Shows ON state with green highlight when active."""
    is_active = (getattr(scene, 'wbtk_live_preview_active', False)
                 and getattr(scene, 'wbtk_live_preview_type', '') == gen_type)

    row = layout.row(align=True)
    if is_active:
        row.alert = True  # Orange highlight when ON
        op = row.operator("wbtk.live_preview_toggle",
                          text="Live Preview ON", icon='HIDE_OFF',
                          depress=True)
    else:
        op = row.operator("wbtk.live_preview_toggle",
                          text="Live Preview", icon='HIDE_ON')
    op.generator_type = gen_type

# --- Global Settings Panel ---
class WBTK_PT_GlobalSettings(WBTK_PanelBase):
    bl_label = "Global Settings"
    bl_idname = "WBTK_PT_GlobalSettings"
    # bl_options = {'DEFAULT_CLOSED'} # Start closed if preferred

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # --- Live Preview Status (global indicator) ---
        is_previewing = getattr(scene, 'wbtk_live_preview_active', False)
        preview_type = getattr(scene, 'wbtk_live_preview_type', '')
        if is_previewing and preview_type:
            box_lp = layout.box()
            row_lp = box_lp.row(align=True)
            row_lp.alert = True
            row_lp.label(text=f"Live Preview: {preview_type}", icon='HIDE_OFF')
            row_lp.operator("wbtk.live_preview_off", text="OFF", icon='X')

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Styles:")
        col.prop(scene, "wbtk_walkway_style", text="Walkway")
        col.prop(scene, "wbtk_rail_style", text="Railing")
        col.prop(scene, "wbtk_lowpoly", text="Low-Poly Rails")
        col.separator()
        col.label(text="Generation Options:")
        col.prop(scene, "wbtk_assign_materials", text="Assign Materials")
        col.prop(scene, "wbtk_auto_unwrap", text="Auto UV Unwrap")
        col.prop(scene, "wbtk_use_trim_uvs", text="Use Trim Sheet UVs")
        if scene.wbtk_use_trim_uvs:
            col.prop(scene, "wbtk_trim_texel_density", text="Texel Density")
        col.prop(scene, "wbtk_add_ucx", text="Add UCX Collision")

# --- Walkways Panel ---
class WBTK_PT_Walkways(WBTK_PanelBase):
    bl_label = "Walkways & Railings"
    bl_idname = "WBTK_PT_Walkways"
    bl_options = {'DEFAULT_CLOSED'}

    def _draw_op_box(self, context, label, op_idname, properties):
        scene = context.scene
        op_box = self.layout.box()
        row_header = op_box.row()
        row_header.label(text=label)
        op = row_header.operator(op_idname, text="Generate", icon='ADD')
        col_props = op_box.column(align=True)
        for prop_idname, prop_text_override in properties:
            col_props.prop(scene, prop_idname, text=prop_text_override if prop_text_override else None)

    def draw(self, context):
        # Use the helper to draw boxes for each walkway operator
        self._draw_op_box(context, "Bridge", "wbtk.bridge_chunk", [("wbtk_br_len", "Length"), ("wbtk_br_wid", "Width"), ("wbtk_br_rail", "Rails")])
        self._draw_op_box(context, "Straight", "wbtk.straight_railing", [("wbtk_sr_len", "Length"), ("wbtk_sr_chunk", "Chunk Meshes"), ("wbtk_sr_rail", "Rails")])
        self._draw_op_box(context, "Corner (L)", "wbtk.corner_railing", [("wbtk_cr_len1", "Length X"), ("wbtk_cr_len2", "Length Y"), ("wbtk_cr_chunk", "Chunk Meshes"), ("wbtk_cr_rail", "Rails")])
        self._draw_op_box(context, "T-Junction", "wbtk.tjunction_railing", [("wbtk_tr_len1", "Main Len (X)"), ("wbtk_tr_len2", "Branch Len (Y)"), ("wbtk_tr_rail", "Rails")]) # Chunking TBD
        self._draw_op_box(context, "X-Junction (+)", "wbtk.xjunction_railing", [("wbtk_xj_size", "Arm Size"), ("wbtk_xj_rail", "Rails")])
        self._draw_op_box(context, "Straight Endcap", "wbtk.straight_endcap", [("wbtk_sr_len", "Run Length"), ("wbtk_sr_rail", "Run Rails")])
        self._draw_op_box(context, "Ladder", "wbtk.ladder", [("wbtk_ld_height", "Height (m)"), ("wbtk_ld_steps", "Rungs"), ("wbtk_ld_rail", "Side Rails")])
        self._draw_op_box(context, "Stairs (Ramp)", "wbtk.stairs_railing", [
            ("wbtk_st_run", "Run (m)"),
            ("wbtk_st_rise", "Rise (m)"),
            ("wbtk_st_width", "Width"),
            ("wbtk_st_ramp_intermediate_posts", "Intermediate Posts"), # <<< USE RAMP PROPERTY
            ("wbtk_st_rail", "Rails")
        ])
        self._draw_op_box(context, "Stairs (Discrete)", "wbtk.discrete_stairs", [
            ("wbtk_ds_run", "Total Run (m)"),
            ("wbtk_ds_rise", "Total Rise (m)"),
            ("wbtk_ds_width_steps", "Width"),
            ("wbtk_ds_step_count", "Steps"),
            ("wbtk_st_discrete_intermediate_posts", "Intermediate Posts"), # <<< USE DISCRETE PROPERTY
            ("wbtk_ds_rail", "Rails")
        ])

# --- Build Mode Panel -------------------------------------------------------
# PRIMARY authoring workflow (Strategic Pivot item #1), so it is registered
# FIRST and opens expanded.
#
# Lifted out of WBTK_PT_Structures on 2026-08-17. It had been a *section*
# starting 156 lines into a 437-line panel, below the Wall / Room / Building
# Shell / Building Row generators -- i.e. the primary path was hidden inside
# the parametric paths Buildify superseded. Jermaine flagged the resulting
# fatigue; see CLAUDE.md "UI OVERHAUL".
#
# The body below is a VERBATIM move. Not one line was edited in the lift, so a
# diff -w against the old Structures panel is the correctness proof.
class WBTK_PT_BuildMode(WBTK_PanelBase):
    bl_label = "Build Mode"
    bl_idname = "WBTK_PT_BuildMode"

    def draw(self, context):
        layout = self.layout
        scene = context.scene


        # --- Build Mode ---
        from .bm_data import get_selected, get_all, get_data

        is_building = getattr(scene, 'wbtk_bm_active', False)
        n_blocks = len(get_all())
        sel = get_selected(context)

        box_bm = layout.box()

        # Mode indicator
        if is_building:
            header = box_bm.row()
            header.alert = True
            header.label(text="BUILD MODE", icon='LIGHT')
            header.operator("wbtk.bm_toggle_mode", text="Exit", icon='PANEL_CLOSE')
        else:
            row_enter = box_bm.row()
            row_enter.scale_y = 1.6
            row_enter.operator("wbtk.bm_toggle_mode", text="Enter Build Mode", icon='MOD_BUILD')
            if n_blocks > 0:
                box_bm.label(text=f"{n_blocks} block(s) placed", icon='INFO')
                row_gen_only = box_bm.row()
                row_gen_only.operator("wbtk.bm_generate", text="Generate", icon='MESH_CUBE')
                row_gen_only.operator("wbtk.bm_clear_all", text="", icon='X')

        if not is_building:
            pass  # Skip rest of panel when not in build mode
        else:
            col_bm = box_bm.column(align=True)

            # --- Placement ---
            row_add = col_bm.row(align=True)
            row_add.scale_y = 1.3
            row_add.operator("wbtk.bm_add_block", text="Add [A]", icon='ADD')
            row_add.operator("wbtk.bm_stack_block", text="Stack [S]", icon='TRIA_UP')

            row_attach = col_bm.row(align=True)
            row_attach.prop(scene, "wbtk_bm_attach_dir", expand=True)
            op_attach = col_bm.operator("wbtk.bm_attach_block", text="Attach", icon='LINKED')
            op_attach.direction = getattr(scene, 'wbtk_bm_attach_dir', 'EAST')

            col_bm.separator()

            # --- Grid ---
            row_grid = col_bm.row(align=True)
            row_grid.prop(scene, "wbtk_bm_grid_size", text="Grid")
            row_grid.prop(scene, "wbtk_bm_block_color", text="")

            col_bm.separator()

            # --- Selected Block ---
            if sel:
                block_box = col_bm.box()
                block_box.label(text=f"{sel.name}", icon='OBJECT_DATA')

                row_dim = block_box.row(align=True)
                row_dim.prop(scene, "wbtk_bm_width", text="W")
                row_dim.prop(scene, "wbtk_bm_depth", text="D")
                row_dim.prop(scene, "wbtk_bm_height", text="H")

                block_box.label(text="Walls:")
                row_ns = block_box.row(align=True)
                row_ns.prop(scene, "wbtk_bm_wall_north", text="N")
                row_ns.prop(scene, "wbtk_bm_wall_south", text="S")
                row_ew = block_box.row(align=True)
                row_ew.prop(scene, "wbtk_bm_wall_east", text="E")
                row_ew.prop(scene, "wbtk_bm_wall_west", text="W")

                block_box.prop(scene, "wbtk_bm_chamfer_size", text="Chamfer")
                block_data = get_data(sel)
                chamfers = block_data.get("chamfers", [])
                row_ch = block_box.row(align=True)
                for corner in ['NW', 'NE', 'SW', 'SE']:
                    is_on = corner.lower() in chamfers
                    op = row_ch.operator("wbtk.bm_toggle_chamfer", text=corner,
                        depress=is_on, icon='MESH_CIRCLE' if is_on else 'HANDLETYPE_FREE_VEC')
                    op.corner = corner

                row_ba = block_box.row(align=True)
                row_ba.operator("wbtk.bm_duplicate_block", text="Dupe [D]", icon='DUPLICATE')
                row_ba.operator("wbtk.bm_sync_from_block", text="Reload", icon='FILE_REFRESH')
                row_ba.operator("wbtk.bm_delete_block", text="", icon='TRASH')
            else:
                col_bm.label(text="Click a block to edit", icon='RESTRICT_SELECT_OFF')

            col_bm.separator()

            # --- Settings ---
            col_bm.prop(scene, "wbtk_bm_auto_setback", text="Stack Setback")

            col_bm.separator()

            # --- Actions ---
            row_gen = col_bm.row(align=True)
            row_gen.scale_y = 1.4
            row_gen.operator("wbtk.bm_generate", text="Generate [G]", icon='MESH_CUBE')
            row_gen.operator("wbtk.bm_clear_all", text="", icon='X')

            row_tools = col_bm.row(align=True)
            row_tools.operator("wbtk.bm_iso_view", text="Iso [I]", icon='VIEW_ORTHO')
            row_tools.operator("wbtk.bm_mirror_x", text="MirX", icon='MOD_MIRROR')
            row_tools.operator("wbtk.bm_mirror_y", text="MirY", icon='MOD_MIRROR')

            col_bm.label(text=f"{n_blocks} block(s)", icon='INFO')
            _draw_live_preview_toggle(box_bm, scene, 'BUILD_MODE')

            # --- Details ---
            detail_box = box_bm.box()
            detail_box.label(text="Detail Stamps", icon='OVERLAY')
            detail_col = detail_box.column(align=True)
            row_face = detail_col.row(align=True)
            row_face.prop(scene, "wbtk_bm_detail_face", text="")
            row_face.prop(scene, "wbtk_bm_detail_scale", text="Scale")
            row_pos = detail_col.row(align=True)
            row_pos.prop(scene, "wbtk_bm_detail_offset_x", text="X Pos")
            row_pos.prop(scene, "wbtk_bm_detail_offset_z", text="Z Pos")
            detail_col.separator()
            from .bm_details import DETAIL_TYPES
            row_d = None
            for i, (key, info) in enumerate(DETAIL_TYPES.items()):
                if i % 2 == 0:
                    row_d = detail_col.row(align=True)
                op = row_d.operator("wbtk.bm_add_detail", text=info['label'], icon=info['icon'])
                op.detail_type = key
            detail_col.separator()
            detail_col.operator("wbtk.bm_clear_details", text="Clear Details", icon='X')

            # --- Shortcuts ---
            sk = box_bm.box()
            sk.scale_y = 0.7
            sk.label(text="Shortcuts:", icon='EVENT_SPACEKEY')
            sk.label(text="A=add  S=stack  D=dupe  X=delete")
            sk.label(text="G=generate  I=iso  RClick=menu")

        # --- Buildify bridge (Strategic Pivot item #1) ---
        box_bm.separator(factor=1.0)
        row_bfy = box_bm.row()
        row_bfy.operator("wbtk.export_buildify_footprints",
                         text="Export Footprints for Buildify", icon='EXPORT')

        # --- Cleanup (destructive, always visible in the Build Mode section) ---
        box_bm.separator(factor=2.0)
        row_cleanup = box_bm.row()
        row_cleanup.alert = True
        row_cleanup.operator("wbtk.bm_cleanup_helpers",
                             text="Cleanup All Helpers", icon='TRASH')



# --- Structures Panel (Integrated from building_toolkit) ---
class WBTK_PT_Structures(WBTK_PanelBase):
    bl_label = "Structures"
    bl_idname = "WBTK_PT_Structures"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Wall Generator Box
        box_wall = layout.box()
        box_wall.label(text="Wall Generator", icon='MESH_CUBE')
        # Use wbtk_ prefix for properties
        box_wall.prop(scene, "wbtk_wall_type", text="Type")
        box_wall.prop(scene, "wbtk_wall_length", text="Length (Tiles)")
        box_wall.prop(scene, "wbtk_wall_height", text="Height (m)")
        box_wall.prop(scene, "wbtk_wall_thickness", text="Thickness (m)")
        # Use wbtk_ prefix for operator
        box_wall.operator("wbtk.generate_wall", text="Generate Wall", icon='ADD')

        # Room Generator Box
        box_room = layout.box()
        box_room.label(text="Room Generator", icon='MOD_BUILD')
        # Use wbtk_ prefix for properties
        box_room.prop(scene, "wbtk_room_width", text="Width (Tiles)")
        box_room.prop(scene, "wbtk_room_length", text="Length (Tiles)")
        # Use wbtk_ prefix for operator
        box_room.operator("wbtk.generate_room", text="Generate Room", icon='ADD')

        # Building Shell Generator Box
        box_building = layout.box()
        box_building.label(text="Building Shell", icon='HOME')

        # --- Region DNA Preset ---
        row_dna = box_building.row(align=True)
        row_dna.prop(scene, "wbtk_region_dna", text="")
        row_dna.operator("wbtk.apply_region_dna", text="Apply DNA", icon='RNA')

        # --- Main Dimensions (FIRST — always set these before anything else) ---
        col_dims = box_building.column(align=True)
        col_dims.prop(scene, "wbtk_building_shape", text="Shape")
        row_dims = col_dims.row(align=True)
        row_dims.prop(scene, "wbtk_building_width", text="Width")
        row_dims.prop(scene, "wbtk_building_depth", text="Depth")
        # Wing dimensions (only for L/U/T shapes)
        bshape = scene.wbtk_building_shape
        if bshape in ('L_SHAPE', 'U_SHAPE', 'T_SHAPE'):
            row_wing = col_dims.row(align=True)
            row_wing.prop(scene, "wbtk_building_wing_width", text="Wing W")
            row_wing.prop(scene, "wbtk_building_wing_depth", text="Wing D")
            col_dims.prop(scene, "wbtk_building_wing_wall_type", text="Wing Walls")
        if bshape == 'L_SHAPE':
            col_dims.prop(scene, "wbtk_building_wing_position", text="Wing Pos")
        if bshape == 'U_SHAPE':
            col_dims.prop(scene, "wbtk_building_courtyard_wall_type", text="Courtyard Walls")
        if bshape == 'CORNER_CUT':
            row_cut = col_dims.row(align=True)
            row_cut.prop(scene, "wbtk_building_corner_cut_size", text="Cut Size")
            row_cut.prop(scene, "wbtk_building_corner_cut_pos", text="")
        row_floors = col_dims.row(align=True)
        row_floors.prop(scene, "wbtk_building_floors", text="Floors")
        row_floors.prop(scene, "wbtk_building_floor_height", text="H (m)")

        col_dims.prop(scene, "wbtk_building_add_floor_slabs", text="Add Floor Slabs")
        col_dims.prop(scene, "wbtk_building_add_roof", text="Add Roof")

        # --- Facade Type Controls ---
        col_facade = box_building.column(align=True)
        col_facade.prop(scene, "wbtk_building_wall_style", text="Wall Style")
        col_facade.label(text="Facade Wall Types:")
        col_facade.prop(scene, "wbtk_building_front_wall_type", text="Front (+Y)")
        col_facade.prop(scene, "wbtk_building_back_wall_type", text="Back (-Y)")
        col_facade.prop(scene, "wbtk_building_left_wall_type", text="Left (-X)")
        col_facade.prop(scene, "wbtk_building_right_wall_type", text="Right (+X)")

        # --- Window Configuration ---
        box_building.separator()
        col_win = box_building.column(align=True)
        col_win.label(text="Window Settings:")
        col_win.prop(scene, "wbtk_building_window_count", text="Count")
        row_win = col_win.row(align=True)
        row_win.prop(scene, "wbtk_building_window_width", text="W")
        row_win.prop(scene, "wbtk_building_window_height", text="H")

        # --- Door Configuration (visible when any wall is DOOR) ---
        has_door = any(getattr(scene, f'wbtk_building_{s}_wall_type', 'SOLID') == 'DOOR'
                       for s in ('front', 'back', 'left', 'right'))
        if has_door:
            box_building.separator()
            col_door = box_building.column(align=True)
            col_door.label(text="Door Settings:")
            col_door.prop(scene, "wbtk_building_door_style", text="Style")
            row_door = col_door.row(align=True)
            row_door.prop(scene, "wbtk_building_door_width", text="W")
            row_door.prop(scene, "wbtk_building_door_height", text="H")
            if scene.wbtk_building_door_style != 'FLAT':
                col_door.prop(scene, "wbtk_building_door_inset", text="Inset Depth")
            if scene.wbtk_building_door_style == 'ANGLED':
                col_door.prop(scene, "wbtk_building_door_splay", text="Splay Angle")

        # --- Ledge / Trim Controls (with actual property draws) ---
        box_building.separator()
        col_ledge = box_building.column(align=True)
        col_ledge.prop(scene, "wbtk_building_add_ledge", text="Add Ledges/Trim")
        if scene.wbtk_building_add_ledge:
            sub = col_ledge.column(align=True)
            sub.prop(scene, "wbtk_building_ledge_every_n_floors", text="Every N Floors")
            sub.prop(scene, "wbtk_building_ledge_height",         text="Height (m)")
            sub.prop(scene, "wbtk_building_ledge_depth",          text="Depth (m)")
            sub.prop(scene, "wbtk_building_ledge_offset_z",       text="Z Offset (m)")

        # --- Generate Buttons ---
        box_building.operator("wbtk.generate_building_shell", text="Generate Building Shell", icon='ADD')

        # Preview & Place button — prominent placement
        row_preview = box_building.row()
        row_preview.scale_y = 1.4
        row_preview.operator(
            "wbtk.preview_place_building",
            text="Preview & Place in Viewport",
            icon='RESTRICT_SELECT_OFF'
        )
        box_building.label(text="^ Move cursor \u2192 Left-click to drop", icon='INFO')
        _draw_live_preview_toggle(box_building, scene, 'BUILDING')

        # --- Trim UV (standalone re-apply) ---
        if scene.wbtk_use_trim_uvs:
            row_trim = box_building.row()
            row_trim.operator("wbtk.apply_trim_uvs", text="Re-apply Trim UVs", icon='UV')

        # --- Randomization ---
        box_rand = layout.box()
        box_rand.label(text="Floor Randomization", icon='MOD_PARTICLES')
        col_r = box_rand.column(align=True)
        col_r.prop(scene, "wbtk_building_use_seed", text="Randomize Upper Floors")
        if scene.wbtk_building_use_seed:
            sub = col_r.column(align=True)
            row_s = sub.row(align=True)
            row_s.prop(scene, "wbtk_building_seed", text="Seed")
            row_s.operator("wbtk.randomize_building_seed", text="", icon='FILE_REFRESH')
            sub.prop(scene, "wbtk_building_window_chance", text="Window Chance", slider=True)
            sub.label(text="Ground floor keeps your facade settings", icon='INFO')

        # --- Batch Row Generator ---
        box_batch = layout.box()
        box_batch.label(text="Batch Row Generator", icon='MOD_ARRAY')
        col_batch = box_batch.column(align=True)
        col_batch.prop(scene, "wbtk_batch_count",     text="Count")
        col_batch.prop(scene, "wbtk_batch_spacing",   text="Gap (m)")
        col_batch.prop(scene, "wbtk_batch_direction",  text="Direction")
        col_batch.separator()
        col_batch.prop(scene, "wbtk_batch_vary_floors", text="Vary Floor Count (+/- 2)")
        col_batch.prop(scene, "wbtk_batch_vary_width",  text="Vary Width (+/- 1 tile)")
        row_batch = box_batch.row()
        row_batch.scale_y = 1.4
        row_batch.operator("wbtk.generate_building_row", text="Generate Building Row", icon='ADD')

        # --- Block Composer (Phase 2) ---
        box_block = layout.box()
        box_block.label(text="Block Composer", icon='GROUP')
        col_block = box_block.column(align=True)
        row_bk = col_block.row(align=True)
        row_bk.prop(scene, "wbtk_block_width", text="Block W")
        row_bk.prop(scene, "wbtk_block_depth", text="Block D")
        col_block.prop(scene, "wbtk_block_building_depth", text="Bldg Depth")
        col_block.prop(scene, "wbtk_block_alley_width", text="Alley Gap")
        col_block.separator()
        row_fl = col_block.row(align=True)
        row_fl.prop(scene, "wbtk_block_min_floors", text="Min Fl")
        row_fl.prop(scene, "wbtk_block_max_floors", text="Max Fl")
        row_bw = col_block.row(align=True)
        row_bw.prop(scene, "wbtk_block_min_building_width", text="Min W")
        row_bw.prop(scene, "wbtk_block_max_building_width", text="Max W")
        col_block.separator()
        col_block.prop(scene, "wbtk_block_use_shapes", text="Random Shapes (L / Corner Cut)")
        col_block.prop(scene, "wbtk_block_fill_courtyard", text="Fill Courtyard")
        row_seed = col_block.row(align=True)
        row_seed.prop(scene, "wbtk_block_seed", text="Seed")
        row_seed.operator("wbtk.randomize_block_seed", text="", icon='FILE_REFRESH')
        row_gen = box_block.row()
        row_gen.scale_y = 1.4
        row_gen.operator("wbtk.generate_city_block", text="Generate City Block", icon='ADD')

        # --- Building Enhancements Sub-panel ---
        box_enh = layout.box()
        box_enh.label(text="Building Enhancements", icon='MOD_SOLIDIFY')

        # Edge Bevel (futuristic edge definition)
        col_bev = box_enh.column(align=True)
        col_bev.prop(scene, "wbtk_building_add_bevel", text="Edge Bevel (Futuristic)")
        if getattr(scene, 'wbtk_building_add_bevel', False):
            sub = col_bev.column(align=True)
            sub.prop(scene, "wbtk_building_bevel_width",    text="Bevel Width (m)")
            sub.prop(scene, "wbtk_building_bevel_segments", text="Segments")

        box_enh.separator()

        # Corner Columns
        col_c = box_enh.column(align=True)
        col_c.prop(scene, "wbtk_building_add_corners", text="Corner Columns")
        if scene.wbtk_building_add_corners:
            sub = col_c.column(align=True)
            sub.prop(scene, "wbtk_building_corner_width",      text="Width (m)")
            sub.prop(scene, "wbtk_building_corner_protrusion", text="Protrusion (m)")

        box_enh.separator()

        # Horizontal Bands
        col_b = box_enh.column(align=True)
        col_b.prop(scene, "wbtk_building_add_bands", text="Horizontal Bands")
        if scene.wbtk_building_add_bands:
            sub = col_b.column(align=True)
            sub.prop(scene, "wbtk_building_band_every_n",    text="Every N Floors")
            sub.prop(scene, "wbtk_building_band_height",     text="Height (m)")
            sub.prop(scene, "wbtk_building_band_protrusion", text="Protrusion (m)")

        box_enh.separator()

        # Window Sills
        col_s = box_enh.column(align=True)
        col_s.prop(scene, "wbtk_building_add_sills", text="Window Sill Shelves")
        if scene.wbtk_building_add_sills:
            sub = col_s.column(align=True)
            sub.prop(scene, "wbtk_building_sill_depth",  text="Depth (m)")
            sub.prop(scene, "wbtk_building_sill_height", text="Height (m)")

        box_enh.separator()

        # Parapet
        col_p = box_enh.column(align=True)
        col_p.prop(scene, "wbtk_building_add_parapet", text="Parapet Wall")
        if scene.wbtk_building_add_parapet:
            sub = col_p.column(align=True)
            sub.prop(scene, "wbtk_building_parapet_height",    text="Height (m)")
            sub.prop(scene, "wbtk_building_parapet_thickness", text="Thickness (m)")

        box_enh.separator()

        # Base Plinth
        col_pl = box_enh.column(align=True)
        col_pl.prop(scene, "wbtk_building_add_plinth", text="Base Plinth")
        if scene.wbtk_building_add_plinth:
            sub = col_pl.column(align=True)
            sub.prop(scene, "wbtk_building_plinth_height",     text="Height (m)")
            sub.prop(scene, "wbtk_building_plinth_protrusion", text="Protrusion (m)")



        box_tower = layout.box()
        box_tower.label(text="Support Tower", icon='MESH_CYLINDER') # Use Cylinder icon as generic pillar
        # --- Main Tower Settings ---
        col_tower_main = box_tower.column(align=True)
        col_tower_main.prop(scene, "wbtk_tower_height", text="Height (m)")
        col_tower_main.prop(scene, "wbtk_tower_shape", text="Shape")
        # Use a more descriptive label for dimension based on shape
        if scene.wbtk_tower_shape == 'SQUARE':
            col_tower_main.prop(scene, "wbtk_tower_dimension", text="Width (m)")
        elif scene.wbtk_tower_shape == 'CYLINDER':
            col_tower_main.prop(scene, "wbtk_tower_dimension", text="Radius (m)")
            # Only show segments for Cylinder
            col_segments = col_tower_main.row()
            col_segments.enabled = True # Always enabled when Cylinder is selected
            col_segments.prop(scene, "wbtk_tower_segments", text="Segments")
        else: # Fallback just in case
            col_tower_main.prop(scene, "wbtk_tower_dimension", text="Dimension (m)")


        # --- Base Settings (Conditional) ---
        col_tower_base = box_tower.column(align=True)
        col_tower_base.prop(scene, "wbtk_tower_add_base", text="Add Base")
        row_base = col_tower_base.row(align=True)
        # Enable base settings only if checkbox is ticked
        row_base.enabled = scene.wbtk_tower_add_base
        row_base.prop(scene, "wbtk_tower_base_height", text="Height")
        row_base.prop(scene, "wbtk_tower_base_size_factor", text="Size Factor")

        # --- Cap Settings (Conditional) ---
        col_tower_cap = box_tower.column(align=True)
        col_tower_cap.prop(scene, "wbtk_tower_add_cap", text="Add Cap")
        row_cap = col_tower_cap.row(align=True)
        # Enable cap settings only if checkbox is ticked
        row_cap.enabled = scene.wbtk_tower_add_cap
        row_cap.prop(scene, "wbtk_tower_cap_height", text="Height")
        row_cap.prop(scene, "wbtk_tower_cap_size_factor", text="Size Factor")

        # --- Generate Button ---
        box_tower.operator("wbtk.generate_support_tower", text="Generate Support Tower", icon='ADD')
        # +++ END OF SUPPORT TOWER UI BOX +++


# --- Props Panel (Integrated from building_toolkit) ---
class WBTK_PT_Props(WBTK_PanelBase):
    bl_label = "Props"
    bl_idname = "WBTK_PT_Props"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Crate Generator Box
        box_crate = layout.box()
        box_crate.label(text="Crate Generator", icon='CUBE')
        # Use wbtk_ prefix for properties
        box_crate.prop(scene, "wbtk_crate_width", text="Width (m)")
        box_crate.prop(scene, "wbtk_crate_depth", text="Depth (m)")
        box_crate.prop(scene, "wbtk_crate_height", text="Height (m)")
        box_crate.prop(scene, "wbtk_crate_inset_amount", text="Inset Amount (m)")
        box_crate.prop(scene, "wbtk_crate_add_insets", text="Add Insets")
        # Use wbtk_ prefix for operator
        box_crate.operator("wbtk.generate_crate", text="Generate Crate", icon='ADD')

        # Barrel Generator Box
        box_barrel = layout.box()
        box_barrel.label(text="Barrel Generator", icon='MESH_CYLINDER')
        # Use wbtk_ prefix for properties
        box_barrel.prop(scene, "wbtk_barrel_radius", text="Radius (m)")
        box_barrel.prop(scene, "wbtk_barrel_height", text="Height (m)")
        box_barrel.prop(scene, "wbtk_barrel_sides", text="Sides")
        # Separator for basic barrel specific props
        col_basic = box_barrel.column(align=True)
        col_basic.prop(scene, "wbtk_barrel_ribs", text="Rib Count (Basic)")
        col_basic.prop(scene, "wbtk_barrel_rib_width", text="Rib Width (Basic)")
        col_basic.prop(scene, "wbtk_barrel_rib_extrude", text="Rib Extrude (Basic)")
        # Use wbtk_ prefix for operators
        row_barrel_ops = box_barrel.row(align=True)
        row_barrel_ops.operator("wbtk.generate_barrel", text="Basic", icon='MESH_CYLINDER')
        row_barrel_ops.operator("wbtk.generate_metal_barrel", text="Metal", icon='MESH_CYLINDER')

        # Vendor Stall Box
        box_stall = layout.box()
        box_stall.label(text="Vendor Stall", icon='MOD_ARMATURE') # Changed icon
        # Use wbtk_ prefix for properties
        box_stall.prop(scene, "wbtk_stall_width", text="Width (m)")
        box_stall.prop(scene, "wbtk_stall_depth", text="Depth (m)")
        box_stall.prop(scene, "wbtk_stall_height", text="Height (m)")
        box_stall.prop(scene, "wbtk_stall_add_table", text="Add Table")
        box_stall.prop(scene, "wbtk_stall_slope_amount", text="Roof Slope (m)")
        # Use wbtk_ prefix for operator
        box_stall.operator("wbtk.generate_vendor_stall", text="Generate Vendor Stall", icon='ADD')

        # Neon Sign Box
        box_sign = layout.box()
        box_sign.label(text="Neon Sign", icon='OUTLINER_OB_LIGHT') # Changed icon
        # Use wbtk_ prefix for properties
        box_sign.prop(scene, "wbtk_sign_width", text="Width (m)")
        box_sign.prop(scene, "wbtk_sign_height", text="Height (m)")
        # box_sign.prop(scene, "wbtk_sign_frame_thickness") # Add if frame logic is implemented
        # Use wbtk_ prefix for operator
        box_sign.operator("wbtk.generate_neon_sign", text="Generate Neon Sign", icon='ADD')

        # Placement Tools (Barrel Pyramid)
        box_place = layout.box()
        box_place.label(text="Placement Tools", icon='GROUP')
        # Use wbtk_ prefix for operator
        # The operator itself defines base_count/spacing props in its definition
        box_place.operator("wbtk.generate_barrel_pyramid", text="Barrel Pyramid", icon='GROUP')


# --- Ground Panel (Integrated from building_toolkit) ---
class WBTK_PT_Ground(WBTK_PanelBase):
    bl_label = "Ground & Surfaces"
    bl_idname = "WBTK_PT_Ground"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box_ground = layout.box()
        box_ground.label(text="Ground Plane", icon='GRID') # Changed icon
        # Use wbtk_ prefix for properties
        box_ground.prop(scene, "wbtk_ground_width", text="Width (Tiles)")
        box_ground.prop(scene, "wbtk_ground_depth", text="Depth (Tiles)")
        box_ground.prop(scene, "wbtk_ground_tile_size", text="Tile Size (m)")
        # Use wbtk_ prefix for operator
        box_ground.operator("wbtk.generate_ground_plane", text="Generate Ground Plane", icon='ADD')


# --- Fences Panel (Integrated from building_toolkit) ---
class WBTK_PT_Fences(WBTK_PanelBase):
    bl_label = "Fences"
    bl_idname = "WBTK_PT_Fences"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Vertical Fence Box
        box_vfence = layout.box()
        box_vfence.label(text="Vertical Fence", icon='BORDERMOVE') # Changed icon
        # Use wbtk_ prefix for properties
        box_vfence.prop(scene, "wbtk_vfence_width", text="Width (m)")
        box_vfence.prop(scene, "wbtk_vfence_height", text="Height (m)")
        box_vfence.prop(scene, "wbtk_vfence_bar_spacing", text="Bar Spacing (m)")
        box_vfence.prop(scene, "wbtk_vfence_post_thickness", text="Post Thick (m)")
        # Use wbtk_ prefix for operator
        box_vfence.operator("wbtk.generate_vertical_fence", text="Generate Vertical Fence", icon='ADD')

        # Chain-Link Fence Box
        box_clfence = layout.box()
        box_clfence.label(text="Chain-Link Fence", icon='MESH_GRID') # Changed icon
        # Use wbtk_ prefix for properties
        box_clfence.prop(scene, "wbtk_clfence_width", text="Width (m)")
        box_clfence.prop(scene, "wbtk_clfence_height", text="Height (m)")
        box_clfence.prop(scene, "wbtk_clfence_post_spacing", text="Post Spacing (m)")
        box_clfence.prop(scene, "wbtk_clfence_bar_thickness", text="Bar Thick (m)")
        box_clfence.prop(scene, "wbtk_clfence_mesh_divisions", text="Mesh Divisions")
        box_clfence.prop(scene, "wbtk_clfence_post_shape", text="Post Shape")
        # Use wbtk_ prefix for operator
        box_clfence.operator("wbtk.generate_chainlink_fence", text="Generate Chain-Link Fence", icon='ADD')



# --- Utilities Panel ---
class WBTK_PT_Utilities(WBTK_PanelBase):
    bl_label = "Utilities"
    bl_idname = "WBTK_PT_Utilities"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        row = box.row()
        row.label(text="Export:")
        row.operator("wbtk.export_fbx", text="Export Selected to FBX", icon='EXPORT')


# --- Foliage Panel ---
class WBTK_PT_Foliage(WBTK_PanelBase):
    bl_label = "Foliage Generator"
    bl_idname = "WBTK_PT_Foliage"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # ── Preset loader ──────────────────────────────────────────────────
        box_preset = layout.box()
        box_preset.label(text="Region Presets", icon='WORLD')
        row = box_preset.row(align=True)
        row.prop(scene, "wbtk_foliage_preset", text="")
        row.operator("wbtk.load_foliage_preset", text="Load", icon='IMPORT')

        layout.separator()

        # ── Tree Generator ─────────────────────────────────────────────────
        box_tree = layout.box()
        box_tree.label(text="Tree", icon='OUTLINER_OB_CURVES')

        col = box_tree.column(align=True)
        col.prop(scene, "wbtk_tree_height",          text="Height (m)")
        col.prop(scene, "wbtk_trunk_radius",         text="Trunk Radius")
        col.prop(scene, "wbtk_trunk_taper",          text="Trunk Taper")
        col.separator()
        col.prop(scene, "wbtk_branch_levels",        text="Branch Levels")
        col.prop(scene, "wbtk_branch_count",         text="Branches per Level")
        col.prop(scene, "wbtk_branch_angle",         text="Branch Angle °")
        col.prop(scene, "wbtk_branch_length_factor", text="Branch Length Factor")
        col.prop(scene, "wbtk_branch_taper",         text="Branch Taper")
        col.separator()
        col.prop(scene, "wbtk_leaf_shape",           text="Leaf Shape")
        col.prop(scene, "wbtk_leaf_density",         text="Leaf Density")
        col.prop(scene, "wbtk_leaf_size",            text="Leaf Size")
        col.prop(scene, "wbtk_leaf_droop",           text="Leaf Droop")

        row_seed = box_tree.row(align=True)
        row_seed.prop(scene, "wbtk_foliage_seed", text="Seed")
        row_seed.operator("wbtk.randomize_foliage_seed", text="", icon='FILE_REFRESH')

        box_tree.operator("wbtk.generate_tree", text="Generate Tree", icon='ADD')
        op = box_tree.operator("wbtk.preview_place", text="Preview & Place", icon='RESTRICT_VIEW_OFF')
        op.generator_type = 'TREE'
        _draw_live_preview_toggle(box_tree, scene, 'TREE')

        layout.separator()

        # ── Shrub Generator ────────────────────────────────────────────────
        box_shrub = layout.box()
        box_shrub.label(text="Shrub / Bush", icon='OUTLINER_OB_POINTCLOUD')

        col = box_shrub.column(align=True)
        col.prop(scene, "wbtk_shrub_height",        text="Height (m)")
        col.prop(scene, "wbtk_shrub_width",         text="Width (m)")
        col.prop(scene, "wbtk_shrub_branch_count",  text="Branch Count")
        col.prop(scene, "wbtk_shrub_branch_angle",  text="Branch Angle °")
        col.separator()
        col.prop(scene, "wbtk_shrub_leaf_shape",    text="Leaf Shape")
        col.prop(scene, "wbtk_shrub_leaf_density",  text="Leaf Density")
        col.prop(scene, "wbtk_shrub_leaf_size",     text="Leaf Size")

        row_seed = box_shrub.row(align=True)
        row_seed.prop(scene, "wbtk_foliage_seed", text="Seed")
        row_seed.operator("wbtk.randomize_foliage_seed", text="", icon='FILE_REFRESH')

        box_shrub.operator("wbtk.generate_shrub", text="Generate Shrub", icon='ADD')
        op = box_shrub.operator("wbtk.preview_place", text="Preview & Place", icon='RESTRICT_VIEW_OFF')
        op.generator_type = 'SHRUB'
        _draw_live_preview_toggle(box_shrub, scene, 'SHRUB')

        layout.separator()

        # ── Ground Cover Generator ─────────────────────────────────────────
        box_ground = layout.box()
        box_ground.label(text="Ground Cover", icon='OUTLINER_OB_GREASEPENCIL')

        col = box_ground.column(align=True)
        col.prop(scene, "wbtk_ground_type",             text="Type")
        col.prop(scene, "wbtk_ground_patch_radius",     text="Patch Radius")
        col.prop(scene, "wbtk_ground_blade_count",      text="Blade / Tuft Count")
        col.prop(scene, "wbtk_ground_blade_height",     text="Height (m)")
        col.prop(scene, "wbtk_ground_blade_width",      text="Width (m)")
        col.prop(scene, "wbtk_ground_droop",            text="Droop / Tilt")
        col.prop(scene, "wbtk_ground_cluster_scatter",  text="Scatter")

        row_seed = box_ground.row(align=True)
        row_seed.prop(scene, "wbtk_foliage_seed", text="Seed")
        row_seed.operator("wbtk.randomize_foliage_seed", text="", icon='FILE_REFRESH')

        box_ground.operator("wbtk.generate_ground_cover", text="Generate Ground Cover", icon='ADD')



# --- Unreal Engine Pipeline Panel ---
class WBTK_PT_UEPipeline(WBTK_PanelBase):
    bl_label = "Unreal Engine Pipeline"
    bl_idname = "WBTK_PT_UEPipeline"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # --- Scale Check ---
        box_scale = layout.box()
        box_scale.label(text="Scene Scale", icon='DRIVER_DISTANCE')
        current_scale = context.scene.unit_settings.scale_length
        is_correct = abs(current_scale - 0.01) < 0.0001

        row = box_scale.row()
        if is_correct:
            row.label(text=f"Scale: {current_scale:.4f} ✓ Ready for UE", icon='CHECKMARK')
        else:
            row.label(text=f"Scale: {current_scale:.4f} ✗ Needs fix!", icon='ERROR')

        op_scale = box_scale.operator("wbtk.check_ue_scale", text="Fix Scale to 0.01", icon='DRIVER_DISTANCE')
        op_scale.fix_scale = True

        layout.separator()

        # --- Export Collection ---
        box_export = layout.box()
        box_export.label(text="UE Export Collection", icon='EXPORT')
        box_export.label(text="Xavier150 exports objects in 'UE_Export'", icon='INFO')
        box_export.prop(scene, "wbtk_export_include_ucx", text="Include UCX Colliders")

        row_export = box_export.row(align=True)
        op_send = row_export.operator(
            "wbtk.send_to_export_collection",
            text="Send Selected",
            icon='OBJECT_DATA'
        )
        op_send.include_ucx = scene.wbtk_export_include_ucx

        box_export.operator(
            "wbtk.auto_tag_for_export",
            text="Send ALL World Builder Output",
            icon='COLLECTION_NEW'
        )


# --- Pipes Panel ---
class WBTK_PT_Pipes(WBTK_PanelBase):
    bl_label = "Pipes"
    bl_idname = "WBTK_PT_Pipes"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Straight Pipe
        box = layout.box()
        box.label(text="Straight Pipe", icon='IPO_CONSTANT')
        col = box.column(align=True)
        col.prop(scene, "wbtk_pipe_length", text="Length (m)")
        row = col.row(align=True)
        row.prop(scene, "wbtk_pipe_radius", text="Radius")
        row.prop(scene, "wbtk_pipe_wall_thickness", text="Wall")
        row2 = col.row(align=True)
        row2.prop(scene, "wbtk_pipe_segments", text="Segs")
        row2.prop(scene, "wbtk_pipe_subdivisions", text="Subdivs")
        col.prop(scene, "wbtk_pipe_axis", text="Axis")
        col.separator()
        row_fl = col.row(align=True)
        row_fl.prop(scene, "wbtk_pipe_add_flanges", text="Flanges")
        sub_fl = row_fl.row(align=True)
        sub_fl.enabled = scene.wbtk_pipe_add_flanges
        sub_fl.prop(scene, "wbtk_pipe_flange_spacing", text="Gap")
        row_cl = col.row(align=True)
        row_cl.prop(scene, "wbtk_pipe_add_clamps", text="Clamps")
        sub_cl = row_cl.row(align=True)
        sub_cl.enabled = scene.wbtk_pipe_add_clamps
        sub_cl.prop(scene, "wbtk_pipe_clamp_spacing", text="Gap")
        box.operator("wbtk.generate_straight_pipe", text="Generate Straight Pipe", icon='ADD')

        # Pipe Run
        box_run = layout.box()
        box_run.label(text="Pipe Run (L-Shape)", icon='ORIENTATION_GIMBAL')
        col_r = box_run.column(align=True)
        row_legs = col_r.row(align=True)
        row_legs.prop(scene, "wbtk_pipe_run_leg1", text="Leg 1")
        row_legs.prop(scene, "wbtk_pipe_run_leg2", text="Leg 2")
        col_r.prop(scene, "wbtk_pipe_run_bend_plane", text="Bend")
        col_r.prop(scene, "wbtk_pipe_run_bend_radius", text="Bend Radius")
        box_run.operator("wbtk.generate_pipe_run", text="Generate Pipe Run", icon='ADD')

        # Pipe Bundle
        box_bun = layout.box()
        box_bun.label(text="Pipe Bundle", icon='MOD_ARRAY')
        row_b = box_bun.row(align=True)
        row_b.prop(scene, "wbtk_pipe_bundle_count", text="Pipes")
        row_b.prop(scene, "wbtk_pipe_bundle_spread", text="Spread")
        box_bun.operator("wbtk.generate_pipe_bundle", text="Generate Pipe Bundle", icon='ADD')

        # Wear & Tear (pipe-specific)
        box_w = layout.box()
        row_h = box_w.row()
        row_h.label(text="Pipe Wear", icon='MOD_NOISE')
        row_h.operator("wbtk.randomize_pipe_seed", text="", icon='FILE_REFRESH')
        col_w = box_w.column(align=True)
        col_w.prop(scene, "wbtk_pipe_wear_preset", text="Preset")
        col_w.prop(scene, "wbtk_pipe_wear_seed", text="Seed")
        if scene.wbtk_pipe_wear_preset == 'CUSTOM':
            col_w.separator()
            col_w.prop(scene, "wbtk_pipe_dent_intensity", text="Dents")
            col_w.prop(scene, "wbtk_pipe_roughness", text="Roughness")
            col_w.prop(scene, "wbtk_pipe_corrosion", text="Holes")
            col_w.prop(scene, "wbtk_pipe_drip_count", text="Drips")


# --- Cables Panel ---
class WBTK_PT_Cables(WBTK_PanelBase):
    bl_label = "Cables & Wires"
    bl_idname = "WBTK_PT_Cables"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="Cable Generator", icon='CURVE_PATH')

        col = box.column(align=True)

        # Cable count: 1 = single, 2+ = bundle
        row_count = col.row(align=True)
        row_count.prop(scene, "wbtk_cable_bundle_count", text="Cables")
        if scene.wbtk_cable_bundle_count > 1:
            row_count.prop(scene, "wbtk_cable_bundle_spread", text="Spread")

        col.separator()
        col.prop(scene, "wbtk_cable_sag", text="Sag (m)")
        row_dim = col.row(align=True)
        row_dim.prop(scene, "wbtk_cable_radius", text="Radius")
        row_dim.prop(scene, "wbtk_cable_segments", text="Segs")
        col.prop(scene, "wbtk_cable_twist", text="Twist")

        # Mode: between objects or manual span
        col.separator()
        col.prop(scene, "wbtk_cable_between_mode", text="Between Selected Objects")

        if not scene.wbtk_cable_between_mode:
            col.prop(scene, "wbtk_cable_span", text="Span (m)")
            col.prop(scene, "wbtk_cable_height", text="Height (m)")

        # Seed
        row_seed = col.row(align=True)
        row_seed.prop(scene, "wbtk_cable_seed", text="Seed")
        row_seed.operator("wbtk.randomize_cable_seed", text="", icon='FILE_REFRESH')

        # Generate button
        box.separator()
        row_gen = box.row()
        row_gen.scale_y = 1.3
        if scene.wbtk_cable_between_mode:
            row_gen.operator("wbtk.cable_between_selected",
                             text="Generate Between Selected", icon='ADD')
            box.label(text="Select 2 objects first — cables connect at tops", icon='INFO')
        else:
            if scene.wbtk_cable_bundle_count > 1:
                row_gen.operator("wbtk.generate_cable_bundle",
                                 text="Generate Cable Bundle", icon='ADD')
            else:
                row_gen.operator("wbtk.generate_cable",
                                 text="Generate Cable", icon='ADD')


# --- Vents & Grates Panel ---
class WBTK_PT_Vents(WBTK_PanelBase):
    bl_label = "Vents & Grates"
    bl_idname = "WBTK_PT_Vents"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Rectangular Vent
        box_rect = layout.box()
        box_rect.label(text="Rectangular Vent", icon='MESH_PLANE')
        col = box_rect.column(align=True)
        row_dim = col.row(align=True)
        row_dim.prop(scene, "wbtk_vent_width", text="W")
        row_dim.prop(scene, "wbtk_vent_height", text="H")
        col.prop(scene, "wbtk_vent_depth", text="Depth")
        col.prop(scene, "wbtk_vent_slat_count", text="Slats")
        col.prop(scene, "wbtk_vent_slat_angle", text="Slat Angle")
        col.prop(scene, "wbtk_vent_frame_thickness", text="Frame")
        box_rect.operator("wbtk.generate_rect_vent", text="Generate Rect Vent", icon='ADD')

        # Round Vent / Exhaust Fan
        box_round = layout.box()
        box_round.label(text="Round Vent / Fan", icon='MESH_CIRCLE')
        col_r = box_round.column(align=True)
        col_r.prop(scene, "wbtk_vent_round_radius", text="Radius")
        col_r.prop(scene, "wbtk_vent_depth", text="Depth")
        col_r.prop(scene, "wbtk_vent_fan_blades", text="Fan Blades")
        col_r.prop(scene, "wbtk_vent_round_segments", text="Segments")
        col_r.prop(scene, "wbtk_vent_frame_thickness", text="Frame")
        box_round.operator("wbtk.generate_round_vent", text="Generate Round Vent", icon='ADD')

        # Tip
        layout.label(text="Use Face Magnet to snap onto walls", icon='INFO')


# --- Surface Scatter Panel ---
class WBTK_PT_Scatter(WBTK_PanelBase):
    bl_label = "Surface Scatter"
    bl_idname = "WBTK_PT_Scatter"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="Scatter Props on Surface", icon='MOD_SCATTER_ON_SURFACE')

        # Instructions
        if not context.active_object or context.active_object.type != 'MESH':
            box.label(text="Select a mesh surface first", icon='ERROR')

        col = box.column(align=True)
        col.prop(scene, "wbtk_scatter_prop_type", text="Type")
        col.prop(scene, "wbtk_scatter_count", text="Count")

        row = col.row(align=True)
        row.prop(scene, "wbtk_scatter_scale", text="Scale")
        row.prop(scene, "wbtk_scatter_margin", text="Margin")

        col.prop(scene, "wbtk_scatter_random_rotation", text="Random Rotation")

        # Seed with re-roll
        row_seed = col.row(align=True)
        row_seed.prop(scene, "wbtk_scatter_seed", text="Seed")

        box.separator()
        row_go = box.row()
        row_go.scale_y = 1.3
        row_go.operator("wbtk.surface_scatter",
                        text="Scatter on Selected Surface", icon='ADD')


# --- Face Magnet Panel ---
class WBTK_PT_FaceMagnet(WBTK_PanelBase):
    bl_label = "Face Magnet"
    bl_idname = "WBTK_PT_FaceMagnet"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="Snap Object to Face", icon='SNAP_FACE')

        col = box.column(align=True)
        col.label(text="1. Select the object to move", icon='OBJECT_DATA')
        col.label(text="2. Click Face Magnet below", icon='MOUSE_LMB')
        col.label(text="3. Hover over target face", icon='RESTRICT_SELECT_OFF')
        col.label(text="4. Left-click to confirm snap", icon='CHECKMARK')
        col.label(text="   Right-click / Esc to cancel", icon='X')

        box.separator()
        box.prop(scene, "wbtk_fm_align_normal", text="Align to Face Normal")
        box.prop(scene, "wbtk_fm_offset", text="Surface Offset (m)")

        row = box.row()
        row.scale_y = 1.5
        op = row.operator("wbtk.face_magnet", text="FACE MAGNET", icon='SNAP_FACE')



# Ensure this list includes all panels defined above
_classes_to_register = (
    # Build Mode first: it is the primary workflow, and panel order in a
    # category follows registration order when bl_order is unset (all are).
    WBTK_PT_BuildMode,
    WBTK_PT_GlobalSettings,
    WBTK_PT_Walkways,
    WBTK_PT_Structures,
    WBTK_PT_Props,
    WBTK_PT_Ground,
    WBTK_PT_Fences,
    WBTK_PT_Foliage,
    WBTK_PT_Pipes,
    WBTK_PT_Cables,
    WBTK_PT_Vents,
    WBTK_PT_Scatter,
    WBTK_PT_FaceMagnet,
    WBTK_PT_UEPipeline,
    WBTK_PT_Utilities,
)