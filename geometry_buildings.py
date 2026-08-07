# World_Building_Toolkit/geometry_buildings.py
# Ensure this file contains the add_tower_pillar method correctly

import bpy
import bmesh
from mathutils import Vector, Matrix

# Import local modules
from .config import Config
# from .utils import Utils # Not needed here

class GeometryBuildings:
    """ Functions for creating BMesh geometry for Building components (Walls, Rooms, Shells, Towers). """

    @staticmethod
    def build_wall_segment(bm, x_start, x_end, z_start, z_end, thickness, axis='X'):
        # ... (code for build_wall_segment as provided before) ...
        half_thick = thickness / 2.0
        if axis == 'X':
            v = [ Vector((x_start, -half_thick, z_start)), Vector((x_end, -half_thick, z_start)), Vector((x_end,  half_thick, z_start)), Vector((x_start,  half_thick, z_start)), Vector((x_start, -half_thick, z_end)),   Vector((x_end, -half_thick, z_end)), Vector((x_end,  half_thick, z_end)),   Vector((x_start,  half_thick, z_end)) ]
        elif axis == 'Y':
            v = [ Vector((-half_thick, x_start, z_start)), Vector(( half_thick, x_start, z_start)), Vector(( half_thick, x_end, z_start)),   Vector((-half_thick, x_end, z_start)), Vector((-half_thick, x_start, z_end)),   Vector(( half_thick, x_start, z_end)), Vector(( half_thick, x_end, z_end)),   Vector((-half_thick, x_end, z_end)) ]
        else: return
        verts = [bm.verts.new(coord) for coord in v]
        try:
            bm.faces.new((verts[0], verts[1], verts[2], verts[3])) # Bottom
            bm.faces.new((verts[7], verts[6], verts[5], verts[4])) # Top (Reversed order)
            bm.faces.new((verts[0], verts[1], verts[5], verts[4])) # Side 1
            bm.faces.new((verts[1], verts[2], verts[6], verts[5])) # Side 2
            bm.faces.new((verts[2], verts[3], verts[7], verts[6])) # Side 3
            bm.faces.new((verts[3], verts[7], verts[4], verts[0])) # Side 4 (Reversed order)
        except ValueError: pass


    @staticmethod
    def build_room_wall(bm, base_pos, run_length, height, thickness, axis):
        """
        Builds a simple solid wall segment for a room layout.
        'base_pos' is currently unused as build_wall_segment assumes local origin.
        """
        # This function just calls the basic segment builder
        # Ensure build_wall_segment method exists and is correct
        # Note: build_wall_segment currently builds relative to 0,0, so the base_pos
        #       argument here isn't actually used by it. The positioning happens
        #       in the operator that calls this (OP_GenerateRoom).
        GeometryBuildings.build_wall_segment(bm, 0, run_length, 0, height, thickness, axis)

    # In geometry_buildings.py -> GeometryBuildings class

    @staticmethod
    def build_shell_wall(bm, base_pos_x, base_pos_y, z_start, length, height, thickness, axis, wall_type='SOLID', door_style='FLAT', door_inset=0.2, door_splay=30.0):
    
        # --- Define Helper Function INSIDE build_shell_wall ---
        # (Ensure this helper is correctly indented relative to the main method)
        # It needs access to axis, base_pos_x, base_pos_y, thickness from the outer scope
        # It calculates its own v_coords and uses them to make verts
        def build_offset_wall_segment(current_bm, seg_start_local, seg_end_local, seg_z_start, seg_z_end):
            # Use half_thick defined in the outer scope
            nonlocal half_thick
            v_coords = [] # Local list for this segment's coordinates
    
            if axis == 'X':
                x_start_world = base_pos_x + seg_start_local
                x_end_world = base_pos_x + seg_end_local
                y_base_world = base_pos_y
                # Calculate the 8 vertex coordinates for this segment
                v_coords = [ Vector((x_start_world, y_base_world - half_thick, seg_z_start)), Vector((x_end_world, y_base_world - half_thick, seg_z_start)),
                             Vector((x_end_world, y_base_world + half_thick, seg_z_start)), Vector((x_start_world, y_base_world + half_thick, seg_z_start)),
                             Vector((x_start_world, y_base_world - half_thick, seg_z_end)), Vector((x_end_world, y_base_world - half_thick, seg_z_end)),
                             Vector((x_end_world, y_base_world + half_thick, seg_z_end)), Vector((x_start_world, y_base_world + half_thick, seg_z_end)) ]
            elif axis == 'Y':
                y_start_world = base_pos_y + seg_start_local
                y_end_world = base_pos_y + seg_end_local
                x_base_world = base_pos_x
                # Calculate the 8 vertex coordinates for this segment
                v_coords = [ Vector((x_base_world - half_thick, y_start_world, seg_z_start)), Vector((x_base_world + half_thick, y_start_world, seg_z_start)),
                             Vector((x_base_world + half_thick, y_end_world, seg_z_start)), Vector((x_base_world - half_thick, y_end_world, seg_z_start)),
                             Vector((x_base_world - half_thick, y_start_world, seg_z_end)), Vector((x_base_world + half_thick, y_start_world, seg_z_end)),
                             Vector((x_base_world + half_thick, y_end_world, seg_z_end)), Vector((x_base_world - half_thick, y_end_world, seg_z_end)) ]
            else:
                print(f"ERROR: Invalid axis '{axis}' in build_offset_wall_segment")
                return # Don't proceed if axis is wrong
    
            if not v_coords: # Check if coordinates were actually calculated
                print(f"ERROR: Could not calculate v_coords in build_offset_wall_segment for axis '{axis}'")
                return
    
            # --- *** THE CORRECT WAY TO CREATE VERTS HERE *** ---
            # Create BMesh vertices from the calculated v_coords list
            verts = [current_bm.verts.new(coord) for coord in v_coords]
            # --- *** END CORRECTION *** ---
    
            try:
                # Create faces using the 'verts' list indices
                current_bm.faces.new((verts[0], verts[1], verts[2], verts[3])) # Bottom
                current_bm.faces.new((verts[7], verts[6], verts[5], verts[4])) # Top
                current_bm.faces.new((verts[0], verts[1], verts[5], verts[4])) # Side 1
                current_bm.faces.new((verts[1], verts[2], verts[6], verts[5])) # Side 2
                current_bm.faces.new((verts[2], verts[3], verts[7], verts[6])) # Side 3
                current_bm.faces.new((verts[3], verts[0], verts[4], verts[7])) # Side 4
                current_bm.faces.ensure_lookup_table()
            except (ValueError, IndexError) as e_face: # Catch potential errors
                print(f"Warning: Face creation failed in build_offset_wall_segment: {e_face}")
                # Consider removing 'verts' here if faces fail? Optional.
    
        # --- End of build_offset_wall_segment definition ---
    
    
        # --- Main build_shell_wall Logic ---
        # Define constants and variables needed in the main scope AND potentially by the helper
        window_w = Config.WINDOW_WIDTH; window_h = Config.WINDOW_HEIGHT
        sill_h = Config.WINDOW_SILL_HEIGHT; frame_thick = Config.WINDOW_FRAME_THICKNESS
        inset_depth = Config.WINDOW_INSET_DEPTH; door_w = Config.DOOR_WIDTH
        door_h = Config.DOOR_HEIGHT
        half_thick = thickness / 2.0 # Define half_thick used by helper and below
        center_along_length = length / 2.0
    
        # --- Handle wall types ---
        if wall_type == 'SOLID':
            build_offset_wall_segment(bm, 0, length, z_start, z_start + height)
    
        elif wall_type == 'WINDOW':
            # --- INSET BOX LOGIC (from response #43 / #26) ---
            min_width = window_w
            min_height = window_h + sill_h
    
            if length >= min_width and height >= min_height:
                win_z_bottom = z_start + sill_h; win_z_top = win_z_bottom + window_h
                win_start_local = center_along_length - (window_w / 2.0); win_end_local = center_along_length + (window_w / 2.0)
    
                # 1. Build Solid Wall Segments AROUND the hole space
                build_offset_wall_segment(bm, 0, length, z_start, win_z_bottom)       # Bottom
                build_offset_wall_segment(bm, 0, length, win_z_top, z_start + height) # Top
                build_offset_wall_segment(bm, 0, win_start_local, win_z_bottom, win_z_top) # Left side
                build_offset_wall_segment(bm, win_end_local, length, win_z_bottom, win_z_top) # Right side
    
                # 2. Define Coordinates for the Inset Box Faces
                # FIX 2026-08-05: frame was frame_thick (0.05) — pane sat 5cm smaller than
                # the hole on all sides with NOTHING filling the ring = see-through gap
                # into the shell interior. Pane must fill the opening exactly.
                frame = 0.0; depth = inset_depth
                z_f_min = win_z_bottom + frame; z_f_max = win_z_top - frame
                z_b_min = z_f_min; z_b_max = z_f_max
                xy_f_min_local = win_start_local + frame; xy_f_max_local = win_end_local - frame
                xy_b_min_local = xy_f_min_local; xy_b_max_local = xy_f_max_local
                vb0_coords, vb1_coords, vb2_coords, vb3_coords = None, None, None, None
                vf0_coords, vf1_coords, vf2_coords, vf3_coords = None, None, None, None
                front_depth_coord = 0; back_depth_coord = 0; pane_thickness = 0.01
    
                if axis == 'X':
                    world_x_f_min = base_pos_x + xy_f_min_local; world_x_f_max = base_pos_x + xy_f_max_local
                    world_x_b_min = base_pos_x + xy_b_min_local; world_x_b_max = base_pos_x + xy_b_max_local
                    outward_face_y = base_pos_y + half_thick
                    front_depth_coord = outward_face_y - depth
                    back_depth_coord = front_depth_coord - pane_thickness
                    vf0_coords = Vector((world_x_f_min, front_depth_coord, z_f_min)); vf1_coords = Vector((world_x_f_max, front_depth_coord, z_f_min))
                    vf2_coords = Vector((world_x_f_max, front_depth_coord, z_f_max)); vf3_coords = Vector((world_x_f_min, front_depth_coord, z_f_max))
                    vb0_coords = Vector((world_x_b_min, back_depth_coord, z_b_min)); vb1_coords = Vector((world_x_b_max, back_depth_coord, z_b_min))
                    vb2_coords = Vector((world_x_b_max, back_depth_coord, z_b_max)); vb3_coords = Vector((world_x_b_min, back_depth_coord, z_b_max))
                elif axis == 'Y':
                    world_y_f_min = base_pos_y + xy_f_min_local; world_y_f_max = base_pos_y + xy_f_max_local
                    world_y_b_min = base_pos_y + xy_b_min_local; world_y_b_max = base_pos_y + xy_b_max_local
                    if base_pos_x < thickness / 2.0: # Left Wall
                        outward_face_x = base_pos_x - half_thick
                        front_depth_coord = outward_face_x + depth
                        back_depth_coord = front_depth_coord + pane_thickness
                    else: # Right Wall
                        outward_face_x = base_pos_x + half_thick
                        front_depth_coord = outward_face_x - depth
                        back_depth_coord = front_depth_coord - pane_thickness
                    vf0_coords = Vector((front_depth_coord, world_y_f_min, z_f_min)); vf1_coords = Vector((front_depth_coord, world_y_f_max, z_f_min))
                    vf2_coords = Vector((front_depth_coord, world_y_f_max, z_f_max)); vf3_coords = Vector((front_depth_coord, world_y_f_min, z_f_max))
                    vb0_coords = Vector((back_depth_coord, world_y_b_min, z_b_min)); vb1_coords = Vector((back_depth_coord, world_y_b_max, z_b_min))
                    vb2_coords = Vector((back_depth_coord, world_y_b_max, z_b_max)); vb3_coords = Vector((back_depth_coord, world_y_b_min, z_b_max))
    
                # 3. Create Inset Box Vertices and Faces
                if vb0_coords and vf0_coords:
                    verts_f = []; verts_b = []
                    vb0, vb1, vb2, vb3 = None, None, None, None
                    vf0, vf1, vf2, vf3 = None, None, None, None
                    try:
                        vf0 = bm.verts.new(vf0_coords); vf1 = bm.verts.new(vf1_coords); vf2 = bm.verts.new(vf2_coords); vf3 = bm.verts.new(vf3_coords)
                        vb0 = bm.verts.new(vb0_coords); vb1 = bm.verts.new(vb1_coords); vb2 = bm.verts.new(vb2_coords); vb3 = bm.verts.new(vb3_coords)
                        verts_f = [vf0, vf1, vf2, vf3]; verts_b = [vb0, vb1, vb2, vb3]
                        bm.faces.new((vb3, vb2, vb1, vb0)) # Back Face
                        bm.faces.new((vf0, vf1, vb1, vb0)) # Bottom connecting face
                        bm.faces.new((vf1, vf2, vb2, vb1)) # Right connecting face
                        bm.faces.new((vf2, vf3, vb3, vb2)) # Top connecting face
                        bm.faces.new((vf3, vf0, vb0, vb3)) # Left connecting face
                        bm.faces.ensure_lookup_table()
                        # print(f"   SUCCESS: Created inset box geom for Axis={axis}")
                    except Exception as e:
                        print(f"   ERROR: Could not create inset box for Axis={axis}: {e}")
                        for v in verts_f + verts_b:
                            if v and v.is_valid: bm.verts.remove(v)
                # No separate recalc needed here, done by operator
    
            else: # Wall too small
                build_offset_wall_segment(bm, 0, length, z_start, z_start + height) # Build solid
    
        elif wall_type == 'DOOR':
            # --- DOOR with FLAT / RECESSED / ANGLED entrance ---
            import math
            min_width_door = door_w
            min_height_door = door_h
            if length >= min_width_door and height >= min_height_door:
                door_z_top = z_start + door_h
                door_start_local = center_along_length - (door_w / 2.0)
                door_end_local = center_along_length + (door_w / 2.0)

                if door_style == 'FLAT':
                    # Original: just wall segments around the opening
                    build_offset_wall_segment(bm, 0, door_start_local, z_start, z_start + height)
                    build_offset_wall_segment(bm, door_end_local, length, z_start, z_start + height)
                    build_offset_wall_segment(bm, door_start_local, door_end_local, door_z_top, z_start + height)

                elif door_style == 'RECESSED':
                    # Straight inset — outer wall has opening, inner plane recessed by door_inset
                    depth = door_inset
                    build_offset_wall_segment(bm, 0, door_start_local, z_start, z_start + height)
                    build_offset_wall_segment(bm, door_end_local, length, z_start, z_start + height)
                    build_offset_wall_segment(bm, door_start_local, door_end_local, door_z_top, z_start + height)

                    # Build inset jamb + header faces connecting outer wall plane to inner plane
                    try:
                        if axis == 'X':
                            outward_y = base_pos_y + half_thick
                            inner_y = outward_y - depth
                            wx_l = base_pos_x + door_start_local
                            wx_r = base_pos_x + door_end_local
                            # Left jamb (4 verts, 1 face)
                            jl0 = bm.verts.new(Vector((wx_l, outward_y, z_start)))
                            jl1 = bm.verts.new(Vector((wx_l, outward_y, door_z_top)))
                            jl2 = bm.verts.new(Vector((wx_l, inner_y, door_z_top)))
                            jl3 = bm.verts.new(Vector((wx_l, inner_y, z_start)))
                            bm.faces.new((jl0, jl1, jl2, jl3))
                            # Right jamb
                            jr0 = bm.verts.new(Vector((wx_r, outward_y, z_start)))
                            jr1 = bm.verts.new(Vector((wx_r, outward_y, door_z_top)))
                            jr2 = bm.verts.new(Vector((wx_r, inner_y, door_z_top)))
                            jr3 = bm.verts.new(Vector((wx_r, inner_y, z_start)))
                            bm.faces.new((jr3, jr2, jr1, jr0))
                            # Header (top soffit)
                            bm.faces.new((jl1, jr1, jr2, jl2))
                            # Floor threshold
                            bm.faces.new((jl3, jl0, jr0, jr3))
                        elif axis == 'Y':
                            wy_l = base_pos_y + door_start_local
                            wy_r = base_pos_y + door_end_local
                            if base_pos_x < thickness / 2.0:  # Left wall
                                outward_x = base_pos_x - half_thick
                                inner_x = outward_x + depth
                            else:  # Right wall
                                outward_x = base_pos_x + half_thick
                                inner_x = outward_x - depth
                            # Left jamb
                            jl0 = bm.verts.new(Vector((outward_x, wy_l, z_start)))
                            jl1 = bm.verts.new(Vector((outward_x, wy_l, door_z_top)))
                            jl2 = bm.verts.new(Vector((inner_x, wy_l, door_z_top)))
                            jl3 = bm.verts.new(Vector((inner_x, wy_l, z_start)))
                            bm.faces.new((jl3, jl2, jl1, jl0))
                            # Right jamb
                            jr0 = bm.verts.new(Vector((outward_x, wy_r, z_start)))
                            jr1 = bm.verts.new(Vector((outward_x, wy_r, door_z_top)))
                            jr2 = bm.verts.new(Vector((inner_x, wy_r, door_z_top)))
                            jr3 = bm.verts.new(Vector((inner_x, wy_r, z_start)))
                            bm.faces.new((jr0, jr1, jr2, jr3))
                            # Header (top soffit)
                            bm.faces.new((jl1, jl2, jr2, jr1))
                            # Floor threshold
                            bm.faces.new((jl0, jr0, jr3, jl3))
                        bm.faces.ensure_lookup_table()
                    except Exception as e:
                        print(f"WBTK Door Recess Error (axis={axis}): {e}")

                elif door_style == 'ANGLED':
                    # Splayed jambs — outer opening wider, narrows to door_w at inset depth
                    depth = door_inset
                    splay_extra = depth * math.tan(math.radians(door_splay))
                    outer_start = max(0.0, door_start_local - splay_extra)
                    outer_end = min(length, door_end_local + splay_extra)

                    # Wall segments around the WIDER outer opening
                    build_offset_wall_segment(bm, 0, outer_start, z_start, z_start + height)
                    build_offset_wall_segment(bm, outer_end, length, z_start, z_start + height)
                    build_offset_wall_segment(bm, outer_start, outer_end, door_z_top, z_start + height)

                    try:
                        if axis == 'X':
                            outward_y = base_pos_y + half_thick
                            inner_y = outward_y - depth
                            # Outer corners (wider)
                            ox_l = base_pos_x + outer_start
                            ox_r = base_pos_x + outer_end
                            # Inner corners (door_w)
                            ix_l = base_pos_x + door_start_local
                            ix_r = base_pos_x + door_end_local
                            # Left angled jamb
                            jl0 = bm.verts.new(Vector((ox_l, outward_y, z_start)))
                            jl1 = bm.verts.new(Vector((ox_l, outward_y, door_z_top)))
                            jl2 = bm.verts.new(Vector((ix_l, inner_y, door_z_top)))
                            jl3 = bm.verts.new(Vector((ix_l, inner_y, z_start)))
                            bm.faces.new((jl0, jl1, jl2, jl3))
                            # Right angled jamb
                            jr0 = bm.verts.new(Vector((ox_r, outward_y, z_start)))
                            jr1 = bm.verts.new(Vector((ox_r, outward_y, door_z_top)))
                            jr2 = bm.verts.new(Vector((ix_r, inner_y, door_z_top)))
                            jr3 = bm.verts.new(Vector((ix_r, inner_y, z_start)))
                            bm.faces.new((jr3, jr2, jr1, jr0))
                            # Header soffit (trapezoid — outer wider, inner narrower)
                            bm.faces.new((jl1, jr1, jr2, jl2))
                            # Floor threshold (trapezoid)
                            bm.faces.new((jl3, jl0, jr0, jr3))
                        elif axis == 'Y':
                            oy_l = base_pos_y + max(0.0, door_start_local - splay_extra)
                            oy_r = base_pos_y + min(length, door_end_local + splay_extra)
                            iy_l = base_pos_y + door_start_local
                            iy_r = base_pos_y + door_end_local
                            if base_pos_x < thickness / 2.0:  # Left wall
                                outward_x = base_pos_x - half_thick
                                inner_x = outward_x + depth
                            else:  # Right wall
                                outward_x = base_pos_x + half_thick
                                inner_x = outward_x - depth
                            # Left angled jamb
                            jl0 = bm.verts.new(Vector((outward_x, oy_l, z_start)))
                            jl1 = bm.verts.new(Vector((outward_x, oy_l, door_z_top)))
                            jl2 = bm.verts.new(Vector((inner_x, iy_l, door_z_top)))
                            jl3 = bm.verts.new(Vector((inner_x, iy_l, z_start)))
                            bm.faces.new((jl3, jl2, jl1, jl0))
                            # Right angled jamb
                            jr0 = bm.verts.new(Vector((outward_x, oy_r, z_start)))
                            jr1 = bm.verts.new(Vector((outward_x, oy_r, door_z_top)))
                            jr2 = bm.verts.new(Vector((inner_x, iy_r, door_z_top)))
                            jr3 = bm.verts.new(Vector((inner_x, iy_r, z_start)))
                            bm.faces.new((jr0, jr1, jr2, jr3))
                            # Header soffit
                            bm.faces.new((jl1, jl2, jr2, jr1))
                            # Floor threshold
                            bm.faces.new((jl0, jr0, jr3, jl3))
                        bm.faces.ensure_lookup_table()
                    except Exception as e:
                        print(f"WBTK Door Angled Error (axis={axis}): {e}")

                else:
                    # Fallback to flat
                    build_offset_wall_segment(bm, 0, door_start_local, z_start, z_start + height)
                    build_offset_wall_segment(bm, door_end_local, length, z_start, z_start + height)
                    build_offset_wall_segment(bm, door_start_local, door_end_local, door_z_top, z_start + height)
            else:
                build_offset_wall_segment(bm, 0, length, z_start, z_start + height)
    
        else: # Solid wall (explicitly or default)
            build_offset_wall_segment(bm, 0, length, z_start, z_start + height)
    
        # ... (keep rest of GeometryBuildings class) ...

  
    @staticmethod
    def add_floor_slab(bm, base_z, width, depth):
        """
        Adds a simple rectangular plane (floor slab) to the BMesh at a specific height.

        Args:
            bm (bmesh.types.BMesh): The BMesh object to modify.
            base_z (float): The Z height where the floor slab should be placed.
            width (float): The width (X-dimension) of the building/slab.
            depth (float): The depth (Y-dimension) of the building/slab.
        """
        # Define corners at the specified base_z
        v0 = bm.verts.new((0, 0, base_z))
        v1 = bm.verts.new((width, 0, base_z))
        v2 = bm.verts.new((width, depth, base_z))
        v3 = bm.verts.new((0, depth, base_z))

        # Create the face (counter-clockwise for normal pointing up)
        try:
            bm.faces.new((v0, v3, v2, v1)) # CCW order: BL, NW, NE, SE
            bm.faces.ensure_lookup_table() # Update face table
        except ValueError as e:
            print(f"Warning: Could not create floor slab face at Z={base_z}: {e}")
            # Clean up verts if face failed? Optional, depends on desired robustness.
            # for v in [v0, v1, v2, v3]:
            #     if v.is_valid: bm.verts.remove(v)

    @staticmethod
    def add_polygon_slab(bm, base_z, vert_list):
        """
        Adds a polygon floor slab from a list of (x, y) tuples.
        Handles any convex polygon (L, U, T, corner-cut, etc.).
        For concave polygons (U-shape), uses triangle fan via bmesh.ops.
        """
        if len(vert_list) < 3:
            return
        verts = [bm.verts.new((x, y, base_z)) for x, y in vert_list]
        try:
            bm.faces.new(reversed(verts))  # Reversed for upward-facing normal
            bm.faces.ensure_lookup_table()
        except ValueError:
            # Concave polygon — try triangulation
            try:
                from mathutils import Vector
                # Create edges for the polygon boundary
                edges = []
                for i in range(len(verts)):
                    e = bm.edges.new((verts[i], verts[(i + 1) % len(verts)]))
                    edges.append(e)
                bmesh.ops.triangle_fill(bm, edges=edges)
                bm.faces.ensure_lookup_table()
            except Exception as e2:
                print(f"Warning: Polygon slab failed at Z={base_z}: {e2}")

    @staticmethod
    def build_angled_wall(bm, start_xy, end_xy, z_start, height, thickness, wall_type='SOLID',
                          door_style='FLAT', door_inset=0.2, door_splay=30.0):
        """
        Build a wall along an arbitrary 2D line (for corner-cut diagonal walls).
        Supports SOLID, WINDOW, and DOOR wall types.
        """
        from mathutils import Vector
        import math

        sx, sy = start_xy
        ex, ey = end_xy
        z_top = z_start + height
        ht = thickness / 2.0

        # Wall direction and normal
        dx = ex - sx
        dy = ey - sy
        wall_len = math.sqrt(dx * dx + dy * dy)
        if wall_len < 0.001:
            return

        # Unit vectors: along wall and outward normal
        ux, uy = dx / wall_len, dy / wall_len  # along wall
        nx, ny = -uy * ht, ux * ht              # outward normal * half thickness

        def _point(t_along, normal_sign):
            """Get 2D point at fraction t_along wall, offset by normal_sign * half_thick."""
            px = sx + ux * t_along + nx * normal_sign
            py = sy + uy * t_along + ny * normal_sign
            return (px, py)

        def _make_box(bm_target, t0, t1, z0, z1):
            """Create a wall box segment between t0..t1 along wall, z0..z1 height."""
            if t1 <= t0 + 0.001 or z1 <= z0 + 0.001:
                return
            try:
                # Outer face (normal_sign=+1), inner face (normal_sign=-1)
                o0 = _point(t0, 1); o1 = _point(t1, 1)
                i0 = _point(t0, -1); i1 = _point(t1, -1)
                v_coords = [
                    Vector((*o0, z0)), Vector((*o1, z0)),
                    Vector((*i1, z0)), Vector((*i0, z0)),
                    Vector((*o0, z1)), Vector((*o1, z1)),
                    Vector((*i1, z1)), Vector((*i0, z1)),
                ]
                verts = [bm_target.verts.new(c) for c in v_coords]
                bm_target.faces.new((verts[0], verts[1], verts[2], verts[3]))  # bottom
                bm_target.faces.new((verts[7], verts[6], verts[5], verts[4]))  # top
                bm_target.faces.new((verts[0], verts[1], verts[5], verts[4]))  # outer
                bm_target.faces.new((verts[2], verts[3], verts[7], verts[6]))  # inner
                bm_target.faces.new((verts[0], verts[3], verts[7], verts[4]))  # start cap
                bm_target.faces.new((verts[1], verts[2], verts[6], verts[5]))  # end cap
                bm_target.faces.ensure_lookup_table()
            except (ValueError, IndexError) as e:
                print(f"Warning: Angled wall box failed: {e}")

        if wall_type == 'SOLID':
            _make_box(bm, 0, wall_len, z_start, z_top)

        elif wall_type == 'WINDOW':
            window_w = Config.WINDOW_WIDTH
            window_h = Config.WINDOW_HEIGHT
            sill_h = Config.WINDOW_SILL_HEIGHT

            if wall_len >= window_w and height >= (window_h + sill_h):
                win_start = (wall_len - window_w) / 2.0
                win_end = win_start + window_w
                win_z_bot = z_start + sill_h
                win_z_top = win_z_bot + window_h

                # Four solid segments around the opening
                _make_box(bm, 0, wall_len, z_start, win_z_bot)             # below
                _make_box(bm, 0, wall_len, win_z_top, z_top)               # above
                _make_box(bm, 0, win_start, win_z_bot, win_z_top)          # left
                _make_box(bm, win_end, wall_len, win_z_bot, win_z_top)     # right

                # Inset window box (reveals)
                # FIX 2026-08-05: same gap bug as build_shell_wall — pane must fill the hole
                frame = 0.0  # was Config.WINDOW_FRAME_THICKNESS
                inset = Config.WINDOW_INSET_DEPTH
                f_start = win_start + frame
                f_end = win_end - frame
                f_z_bot = win_z_bot + frame
                f_z_top = win_z_top - frame

                if f_end > f_start and f_z_top > f_z_bot and inset > 0:
                    # Inset face sits at normal_sign offset reduced by inset
                    inset_frac = 1.0 - (inset / ht) if ht > 0 else 0.5
                    try:
                        # Front pane (slightly recessed from outer face)
                        pf0 = _point(f_start, inset_frac)
                        pf1 = _point(f_end, inset_frac)
                        vf = [
                            bm.verts.new(Vector((*pf0, f_z_bot))),
                            bm.verts.new(Vector((*pf1, f_z_bot))),
                            bm.verts.new(Vector((*pf1, f_z_top))),
                            bm.verts.new(Vector((*pf0, f_z_top))),
                        ]
                        bm.faces.new((vf[0], vf[1], vf[2], vf[3]))
                        bm.faces.ensure_lookup_table()
                    except Exception as e:
                        print(f"Warning: Angled window inset failed: {e}")
            else:
                # Wall too small for window — solid fallback
                _make_box(bm, 0, wall_len, z_start, z_top)

        elif wall_type == 'DOOR':
            door_w = Config.DOOR_WIDTH
            door_h = Config.DOOR_HEIGHT

            if wall_len >= door_w and height >= door_h:
                door_start = (wall_len - door_w) / 2.0
                door_end = door_start + door_w
                door_z_top = z_start + door_h

                # Three solid segments around the door opening
                _make_box(bm, 0, door_start, z_start, z_top)              # left
                _make_box(bm, door_end, wall_len, z_start, z_top)         # right
                _make_box(bm, door_start, door_end, door_z_top, z_top)    # above

                # Door reveal faces (jambs, header, threshold)
                inset = door_inset
                if door_style in ('RECESSED', 'ANGLED') and inset > 0:
                    try:
                        inset_frac = 1.0 - (inset / ht) if ht > 0 else 0.5
                        # Outer jamb positions (on outer face)
                        ol = _point(door_start, 1); or_ = _point(door_end, 1)
                        # Inner jamb positions (recessed)
                        il = _point(door_start, inset_frac); ir = _point(door_end, inset_frac)

                        if door_style == 'ANGLED':
                            splay_extra = inset * math.tan(math.radians(door_splay))
                            splay_start = max(0, door_start - splay_extra)
                            splay_end = min(wall_len, door_end + splay_extra)
                            ol = _point(splay_start, 1); or_ = _point(splay_end, 1)

                        # Left jamb
                        jl0 = bm.verts.new(Vector((*ol, z_start)))
                        jl1 = bm.verts.new(Vector((*ol, door_z_top)))
                        jl2 = bm.verts.new(Vector((*il, door_z_top)))
                        jl3 = bm.verts.new(Vector((*il, z_start)))
                        bm.faces.new((jl0, jl1, jl2, jl3))

                        # Right jamb
                        jr0 = bm.verts.new(Vector((*or_, z_start)))
                        jr1 = bm.verts.new(Vector((*or_, door_z_top)))
                        jr2 = bm.verts.new(Vector((*ir, door_z_top)))
                        jr3 = bm.verts.new(Vector((*ir, z_start)))
                        bm.faces.new((jr3, jr2, jr1, jr0))

                        # Header soffit
                        bm.faces.new((jl1, jr1, jr2, jl2))
                        # Threshold
                        bm.faces.new((jl3, jl0, jr0, jr3))

                        bm.faces.ensure_lookup_table()
                    except Exception as e:
                        print(f"Warning: Angled wall door reveals failed: {e}")
            else:
                # Wall too small for door — solid fallback
                _make_box(bm, 0, wall_len, z_start, z_top)

    # --- Support Tower Geometry ---

    @staticmethod
    def _add_pillar_square(bm, base_center_tuple, height, width):
        # ... (code for _add_pillar_square as provided before) ...
        x, y, z = base_center_tuple; half_w = width / 2.0; created_verts = []
        try:
            v_coords = [ Vector((x - half_w, y - half_w, z)), Vector((x + half_w, y - half_w, z)), Vector((x + half_w, y + half_w, z)), Vector((x - half_w, y + half_w, z)), Vector((x - half_w, y - half_w, z + height)), Vector((x + half_w, y - half_w, z + height)), Vector((x + half_w, y + half_w, z + height)), Vector((x - half_w, y + half_w, z + height)), ]
            verts = [bm.verts.new(coord) for coord in v_coords]; created_verts.extend(verts)
            bm.faces.new((verts[0], verts[1], verts[2], verts[3])); bm.faces.new((verts[7], verts[6], verts[5], verts[4])); bm.faces.new((verts[0], verts[1], verts[5], verts[4])); bm.faces.new((verts[1], verts[2], verts[6], verts[5])); bm.faces.new((verts[2], verts[3], verts[7], verts[6])); bm.faces.new((verts[3], verts[0], verts[4], verts[7])); bm.faces.ensure_lookup_table()
        except (ValueError, IndexError) as e: print(f"Warning: Face creation failed for square pillar: {e}"); [v.is_valid and bm.verts.remove(v) for v in created_verts]

    @staticmethod
    def _add_pillar_cylinder(bm, base_center_tuple, height, radius, segments=16):
        # ... (code for _add_pillar_cylinder as provided before) ...
        if radius <= 0 or height <= 0: return
        try:
            geom_data = bmesh.ops.create_cone(bm, cap_ends=True, segments=max(3, segments), radius1=radius, radius2=radius, depth=height); created_verts = geom_data.get('verts')
            if created_verts: translate_vec = Vector(base_center_tuple) + Vector((0, 0, height / 2.0)); bmesh.ops.translate(bm, verts=created_verts, vec=translate_vec)
        except Exception as e: print(f"Error creating cylindrical pillar: {e}")

    # +++ ENSURE THIS METHOD IS DEFINED CORRECTLY +++
    @staticmethod
    def add_tower_pillar(bm, base_pos_tuple, height, shape, dimension, segments=16):
        """ Adds the main pillar geometry for the support tower. """
        if shape == 'SQUARE':
            GeometryBuildings._add_pillar_square(bm, base_pos_tuple, height, dimension)
        elif shape == 'CYLINDER':
            GeometryBuildings._add_pillar_cylinder(bm, base_pos_tuple, height, dimension, segments)
        else:
            print(f"Error: Unknown tower shape '{shape}'")
    # +++ END METHOD +++

    @staticmethod
    def add_tower_base_or_cap(bm, center_pos_tuple, pillar_dimension, pillar_shape, size_factor, height):
        # ... (code for add_tower_base_or_cap using manual vertex calculation, as provided before) ...
        if height <= 0 or size_factor <= 0: return
        if pillar_shape == 'SQUARE': size_x = pillar_dimension * size_factor; size_y = size_x
        elif pillar_shape == 'CYLINDER': diameter = pillar_dimension * 2.0; size_x = diameter * size_factor; size_y = size_x
        else: size_x = pillar_dimension * size_factor; size_y = size_x
        size_z = height; hx = size_x / 2.0; hy = size_y / 2.0; hz = size_z / 2.0; cx, cy, cz = center_pos_tuple
        v_coords = [ Vector((cx - hx, cy - hy, cz - hz)), Vector((cx + hx, cy - hy, cz - hz)), Vector((cx + hx, cy + hy, cz - hz)), Vector((cx - hx, cy + hy, cz - hz)), Vector((cx - hx, cy - hy, cz + hz)), Vector((cx + hx, cy - hy, cz + hz)), Vector((cx + hx, cy + hy, cz + hz)), Vector((cx - hx, cy + hy, cz + hz)), ]
        try:
            verts = [bm.verts.new(coord) for coord in v_coords]
            bm.faces.new((verts[0], verts[1], verts[2], verts[3])); bm.faces.new((verts[7], verts[6], verts[5], verts[4])); bm.faces.new((verts[0], verts[1], verts[5], verts[4])); bm.faces.new((verts[1], verts[2], verts[6], verts[5])); bm.faces.new((verts[2], verts[3], verts[7], verts[6])); bm.faces.new((verts[3], verts[0], verts[4], verts[7])); bm.faces.ensure_lookup_table()
        except (ValueError, IndexError) as e: print(f"Warning: Face creation failed for base/cap: {e}")

        # Inside world_building_toolkit/geometry_buildings.py -> GeometryBuildings class

    # ... (existing methods like add_tower_pillar, add_tower_base_or_cap, etc.) ...


    # +++ ADD NEW METHOD FOR BUILDING LEDGES +++
    @staticmethod
    def add_building_ledge(bm, building_width, building_depth, ledge_base_z, ledge_height, ledge_depth):
        """
        Adds ledge/trim geometry around the perimeter of the building footprint.

        Args:
            bm (bmesh.types.BMesh): The BMesh object to modify.
            building_width (float): The width (X-dimension) of the building footprint.
            building_depth (float): The depth (Y-dimension) of the building footprint.
            ledge_base_z (float): The Z height for the BOTTOM of the ledge.
            ledge_height (float): The vertical thickness/height of the ledge.
            ledge_depth (float): How far the ledge protrudes outwards from the wall footprint.
        """
        if ledge_height <= 0 or ledge_depth <= 0:
            return # Ledge must have dimensions

        ledge_top_z = ledge_base_z + ledge_height

        # Define the 8 vertices for the TOP surface of the ledge
        # Inner corners (align with building footprint)
        v_in_sw = Vector((0, 0, ledge_top_z))
        v_in_se = Vector((building_width, 0, ledge_top_z))
        v_in_ne = Vector((building_width, building_depth, ledge_top_z))
        v_in_nw = Vector((0, building_depth, ledge_top_z))
        # Outer corners (offset by ledge_depth)
        v_out_sw = Vector((-ledge_depth, -ledge_depth, ledge_top_z))
        v_out_se = Vector((building_width + ledge_depth, -ledge_depth, ledge_top_z))
        v_out_ne = Vector((building_width + ledge_depth, building_depth + ledge_depth, ledge_top_z))
        v_out_nw = Vector((-ledge_depth, building_depth + ledge_depth, ledge_top_z))

        verts_top = []
        # Create BMesh vertices for the top surface
        try:
            verts_top_inner = [bm.verts.new(v_in_sw), bm.verts.new(v_in_se), bm.verts.new(v_in_ne), bm.verts.new(v_in_nw)]
            verts_top_outer = [bm.verts.new(v_out_sw), bm.verts.new(v_out_se), bm.verts.new(v_out_ne), bm.verts.new(v_out_nw)]
            verts_top = verts_top_inner + verts_top_outer # Combine for potential later use
        except Exception as e:
            print(f"Error creating ledge top vertices: {e}")
            return

        # Create the 4 faces for the top surface of the ledge
        top_faces = []
        try:
            # Connect inner and outer vertices to form top faces
            # Ensure winding order is counter-clockwise for upward normal
            top_faces.append(bm.faces.new((verts_top_inner[0], verts_top_outer[0], verts_top_outer[1], verts_top_inner[1]))) # South face
            top_faces.append(bm.faces.new((verts_top_inner[1], verts_top_outer[1], verts_top_outer[2], verts_top_inner[2]))) # East face
            top_faces.append(bm.faces.new((verts_top_inner[2], verts_top_outer[2], verts_top_outer[3], verts_top_inner[3]))) # North face
            top_faces.append(bm.faces.new((verts_top_inner[3], verts_top_outer[3], verts_top_outer[0], verts_top_inner[0]))) # West face
            bm.faces.ensure_lookup_table()
        except (ValueError, IndexError) as e:
            print(f"Warning: Face creation failed for ledge top surface: {e}")
            # Clean up if face creation failed severely?
            # for v in verts_top:
            #     if v.is_valid: bm.verts.remove(v)
            return # Cannot extrude if top faces failed

        # Find the outer edges of the top surface to extrude downwards
        outer_edges = []
        for face in top_faces:
            for edge in face.edges:
                # An edge is outer if both its vertices are outer vertices
                is_outer_edge = all(v in verts_top_outer for v in edge.verts)
                if is_outer_edge:
                    outer_edges.append(edge)

        # Remove duplicates just in case
        outer_edges = list(set(outer_edges))

        # Extrude the outer edges downwards to form the sides and bottom
        if outer_edges:
            try:
                extrude_result = bmesh.ops.extrude_edge_only(bm, edges=outer_edges)
                # Get the newly created vertices at the bottom
                extruded_verts = [ele for ele in extrude_result['geom'] if isinstance(ele, bmesh.types.BMVert)]
                if extruded_verts:
                    # Translate the new vertices down by ledge_height
                    bmesh.ops.translate(bm, verts=extruded_verts, vec=(0, 0, -ledge_height))

                    # --- Optional: Fill bottom face ---
                    # Find the bottom loop of edges created by the extrusion
                    # bottom_edges = [ele for ele in extrude_result['geom'] if isinstance(ele, bmesh.types.BMEdge) and all(v in extruded_verts for v in ele.verts)]
                    # if len(bottom_edges) == 4 * 2: # Should have 8 edges in loop for square
                    #     try:
                    #          bmesh.ops.contextual_create(bm, geom=bottom_edges) # Try to fill face
                    #          # Or potentially: bm.faces.new(...) using sorted extruded_verts
                    #     except Exception as e_fill:
                    #          print(f"Warning: Could not fill ledge bottom face: {e_fill}")
                    # --- End Optional Bottom Fill ---

            except Exception as e_extrude:
                print(f"Error extruding ledge edges: {e_extrude}")

    # +++ END OF NEW METHOD +++


    # =========================================================================
    #  ENHANCEMENT 1 — EXTRUDED CORNER COLUMNS (PILASTERS)
    #  Square columns that protrude from the wall face at each corner.
    #  Dramatically improves architectural read vs plain box corners.
    # =========================================================================

    @staticmethod
    def add_corner_columns(bm, building_width, building_depth, z_start, z_end,
                           col_width, col_protrusion):
        """
        Adds four extruded corner columns at the building's corners.

        Args:
            building_width (float): Width (X) of the building footprint.
            building_depth (float): Depth (Y) of the building footprint.
            z_start (float): Z bottom of the column.
            z_end (float): Z top of the column.
            col_width (float): Width of the column face (along wall direction).
            col_protrusion (float): How far the column sticks out from the wall face.
        """
        if col_width <= 0 or col_protrusion <= 0 or z_end <= z_start:
            return

        half_thick = Config.WALL_THICKNESS / 2.0
        half_w = col_width / 2.0

        # Four corner positions and their outward protrusion directions.
        # Each corner: (centre_x, centre_y, protrude_x, protrude_y)
        corners = [
            # SW corner — protrudes in -X, -Y direction
            (0,              0,             -1, -1),
            # SE corner — protrudes in +X, -Y direction
            (building_width, 0,              1, -1),
            # NE corner — protrudes in +X, +Y direction
            (building_width, building_depth, 1,  1),
            # NW corner — protrudes in -X, +Y direction
            (0,              building_depth,-1,  1),
        ]

        for (cx, cy, dx, dy) in corners:
            # Column occupies col_width along each wall face
            # and protrudes col_protrusion outward from wall outer face
            # Outer face X: cx + dx * half_thick (wall outer face)
            # Column outer face: wall outer + dx * col_protrusion

            # For an X-aligned wall face (dy != 0 means it's a Y-direction wall)
            # Build as a simple box at this corner
            x_inner = cx - dx * half_thick
            x_outer = cx + dx * (half_thick + col_protrusion)
            y_inner = cy - dy * half_thick
            y_outer = cy + dy * (half_thick + col_protrusion)

            # Add col_width coverage along the wall in both directions
            # Column extends half_w on each side of the corner vertex along each axis
            x0 = min(x_inner, x_outer) - half_w
            x1 = max(x_inner, x_outer) + half_w
            y0 = min(y_inner, y_outer) - half_w
            y1 = max(y_inner, y_outer) + half_w

            v_coords = [
                Vector((x0, y0, z_start)), Vector((x1, y0, z_start)),
                Vector((x1, y1, z_start)), Vector((x0, y1, z_start)),
                Vector((x0, y0, z_end)),   Vector((x1, y0, z_end)),
                Vector((x1, y1, z_end)),   Vector((x0, y1, z_end)),
            ]
            try:
                verts = [bm.verts.new(c) for c in v_coords]
                bm.faces.new((verts[0], verts[1], verts[2], verts[3]))
                bm.faces.new((verts[7], verts[6], verts[5], verts[4]))
                bm.faces.new((verts[0], verts[1], verts[5], verts[4]))
                bm.faces.new((verts[1], verts[2], verts[6], verts[5]))
                bm.faces.new((verts[2], verts[3], verts[7], verts[6]))
                bm.faces.new((verts[3], verts[0], verts[4], verts[7]))
                bm.faces.ensure_lookup_table()
            except (ValueError, IndexError) as e:
                print(f"Warning: Corner column face creation failed: {e}")


    # =========================================================================
    #  ENHANCEMENT 2 — HORIZONTAL BANDING
    #  Thin decorative strips running around the building perimeter.
    #  Placed between floors to break up plain wall surfaces.
    # =========================================================================

    @staticmethod
    def add_horizontal_band(bm, building_width, building_depth, band_z,
                            band_height, band_protrusion):
        """
        Adds a thin horizontal trim band around the building perimeter.

        Args:
            band_z (float): Bottom Z of the band.
            band_height (float): Vertical thickness of the band.
            band_protrusion (float): How far the band sticks out from the wall.
        """
        if band_height <= 0 or band_protrusion <= 0:
            return

        half_thick = Config.WALL_THICKNESS / 2.0
        p = band_protrusion
        band_top = band_z + band_height

        # Four sides as flat extruded boxes
        # South side (Y=0, extends along X)
        GeometryBuildings._add_band_segment(
            bm,
            (-p, -half_thick - p, band_z),
            (building_width + p, -half_thick - p, band_z),
            (building_width + p, -half_thick,     band_z),
            (-p, -half_thick,     band_z),
            band_height
        )
        # North side (Y=depth, extends along X)
        GeometryBuildings._add_band_segment(
            bm,
            (-p,                 building_depth + half_thick,     band_z),
            (building_width + p, building_depth + half_thick,     band_z),
            (building_width + p, building_depth + half_thick + p, band_z),
            (-p,                 building_depth + half_thick + p, band_z),
            band_height
        )
        # West side (X=0, extends along Y)
        GeometryBuildings._add_band_segment(
            bm,
            (-half_thick - p, 0,             band_z),
            (-half_thick,     0,             band_z),
            (-half_thick,     building_depth, band_z),
            (-half_thick - p, building_depth, band_z),
            band_height
        )
        # East side (X=width, extends along Y)
        GeometryBuildings._add_band_segment(
            bm,
            (building_width + half_thick,     0,             band_z),
            (building_width + half_thick + p, 0,             band_z),
            (building_width + half_thick + p, building_depth, band_z),
            (building_width + half_thick,     building_depth, band_z),
            band_height
        )

    @staticmethod
    def _add_band_segment(bm, p0, p1, p2, p3, height):
        """Helper: extrude a flat quad upward by height to create a band segment."""
        try:
            z = p0[2]
            h = height
            v_coords = [
                Vector(p0), Vector(p1), Vector(p2), Vector(p3),
                Vector((p0[0], p0[1], z + h)),
                Vector((p1[0], p1[1], z + h)),
                Vector((p2[0], p2[1], z + h)),
                Vector((p3[0], p3[1], z + h)),
            ]
            verts = [bm.verts.new(c) for c in v_coords]
            bm.faces.new((verts[0], verts[1], verts[2], verts[3]))
            bm.faces.new((verts[7], verts[6], verts[5], verts[4]))
            bm.faces.new((verts[0], verts[1], verts[5], verts[4]))
            bm.faces.new((verts[1], verts[2], verts[6], verts[5]))
            bm.faces.new((verts[2], verts[3], verts[7], verts[6]))
            bm.faces.new((verts[3], verts[0], verts[4], verts[7]))
            bm.faces.ensure_lookup_table()
        except (ValueError, IndexError) as e:
            print(f"Warning: Band segment face creation failed: {e}")


    # =========================================================================
    #  ENHANCEMENT 3 — WINDOW SILL SHELF
    #  Thin protruding shelf directly below window openings.
    # =========================================================================

    @staticmethod
    def add_window_sill_shelf(bm, base_pos_x, base_pos_y, wall_length,
                              sill_z, axis, shelf_depth, shelf_height):
        """
        Adds a protruding shelf below the window opening on a wall face.

        Args:
            base_pos_x / base_pos_y: Wall origin position.
            wall_length: Length of the wall (to centre the sill).
            sill_z: Z height of the bottom of the window (top of the sill shelf).
            axis: 'X' or 'Y' — wall axis.
            shelf_depth: How far the shelf protrudes from the wall face.
            shelf_height: Vertical thickness of the shelf.
        """
        if shelf_depth <= 0 or shelf_height <= 0:
            return

        win_w = Config.WINDOW_WIDTH
        half_thick = Config.WALL_THICKNESS / 2.0
        center = wall_length / 2.0

        # Shelf is slightly wider than window opening
        shelf_w = win_w + shelf_height * 2.0
        half_shelf = shelf_w / 2.0
        shelf_z_bottom = sill_z - shelf_height
        shelf_z_top    = sill_z

        if axis == 'X':
            # Wall faces along Y — shelf protrudes in +Y (outward)
            x0 = base_pos_x + center - half_shelf
            x1 = base_pos_x + center + half_shelf
            y_inner = base_pos_y + half_thick
            y_outer = base_pos_y + half_thick + shelf_depth

            v_coords = [
                Vector((x0, y_inner, shelf_z_bottom)), Vector((x1, y_inner, shelf_z_bottom)),
                Vector((x1, y_outer, shelf_z_bottom)), Vector((x0, y_outer, shelf_z_bottom)),
                Vector((x0, y_inner, shelf_z_top)),    Vector((x1, y_inner, shelf_z_top)),
                Vector((x1, y_outer, shelf_z_top)),    Vector((x0, y_outer, shelf_z_top)),
            ]
        else:  # 'Y'
            # Wall faces along X — determine outward direction
            y0 = base_pos_y + center - half_shelf
            y1 = base_pos_y + center + half_shelf
            if base_pos_x < Config.WALL_THICKNESS:
                x_inner = base_pos_x - half_thick
                x_outer = base_pos_x - half_thick - shelf_depth
            else:
                x_inner = base_pos_x + half_thick
                x_outer = base_pos_x + half_thick + shelf_depth

            v_coords = [
                Vector((x_inner, y0, shelf_z_bottom)), Vector((x_outer, y0, shelf_z_bottom)),
                Vector((x_outer, y1, shelf_z_bottom)), Vector((x_inner, y1, shelf_z_bottom)),
                Vector((x_inner, y0, shelf_z_top)),    Vector((x_outer, y0, shelf_z_top)),
                Vector((x_outer, y1, shelf_z_top)),    Vector((x_inner, y1, shelf_z_top)),
            ]

        try:
            verts = [bm.verts.new(c) for c in v_coords]
            bm.faces.new((verts[0], verts[1], verts[2], verts[3]))
            bm.faces.new((verts[7], verts[6], verts[5], verts[4]))
            bm.faces.new((verts[0], verts[1], verts[5], verts[4]))
            bm.faces.new((verts[1], verts[2], verts[6], verts[5]))
            bm.faces.new((verts[2], verts[3], verts[7], verts[6]))
            bm.faces.new((verts[3], verts[0], verts[4], verts[7]))
            bm.faces.ensure_lookup_table()
        except (ValueError, IndexError) as e:
            print(f"Warning: Window sill shelf face creation failed: {e}")


    # =========================================================================
    #  ENHANCEMENT 4 — PARAPET WALL
    #  Raised wall running around the roof perimeter.
    # =========================================================================

    @staticmethod
    def add_parapet(bm, building_width, building_depth, roof_z,
                    parapet_height, parapet_thickness):
        """
        Adds a raised parapet wall around the roof perimeter.

        Args:
            roof_z (float): Z level of the roof slab top surface.
            parapet_height (float): How tall the parapet wall rises above roof.
            parapet_thickness (float): Thickness of the parapet wall.
        """
        if parapet_height <= 0 or parapet_thickness <= 0:
            return

        t = parapet_thickness
        h = parapet_height
        w = building_width
        d = building_depth
        z0 = roof_z
        z1 = roof_z + h

        # Four parapet walls matching the building perimeter
        # South
        GeometryBuildings._add_parapet_segment(bm, 0, 0, w, 0, z0, z1, t, 'X_SOUTH')
        # North
        GeometryBuildings._add_parapet_segment(bm, 0, d, w, d, z0, z1, t, 'X_NORTH')
        # West
        GeometryBuildings._add_parapet_segment(bm, 0, 0, 0, d, z0, z1, t, 'Y_WEST')
        # East
        GeometryBuildings._add_parapet_segment(bm, w, 0, w, d, z0, z1, t, 'Y_EAST')

    @staticmethod
    def _add_parapet_segment(bm, x0, y0, x1, y1, z_bot, z_top, thickness, side):
        """Helper: builds one parapet wall segment."""
        t = thickness / 2.0
        try:
            if 'X' in side:
                # Wall runs along X axis
                if 'SOUTH' in side:
                    v_coords = [
                        Vector((x0, y0 - t, z_bot)), Vector((x1, y0 - t, z_bot)),
                        Vector((x1, y0 + t, z_bot)), Vector((x0, y0 + t, z_bot)),
                        Vector((x0, y0 - t, z_top)), Vector((x1, y0 - t, z_top)),
                        Vector((x1, y0 + t, z_top)), Vector((x0, y0 + t, z_top)),
                    ]
                else:  # NORTH
                    v_coords = [
                        Vector((x0, y1 - t, z_bot)), Vector((x1, y1 - t, z_bot)),
                        Vector((x1, y1 + t, z_bot)), Vector((x0, y1 + t, z_bot)),
                        Vector((x0, y1 - t, z_top)), Vector((x1, y1 - t, z_top)),
                        Vector((x1, y1 + t, z_top)), Vector((x0, y1 + t, z_top)),
                    ]
            else:  # Y axis
                if 'WEST' in side:
                    v_coords = [
                        Vector((x0 - t, y0, z_bot)), Vector((x0 + t, y0, z_bot)),
                        Vector((x0 + t, y1, z_bot)), Vector((x0 - t, y1, z_bot)),
                        Vector((x0 - t, y0, z_top)), Vector((x0 + t, y0, z_top)),
                        Vector((x0 + t, y1, z_top)), Vector((x0 - t, y1, z_top)),
                    ]
                else:  # EAST
                    v_coords = [
                        Vector((x1 - t, y0, z_bot)), Vector((x1 + t, y0, z_bot)),
                        Vector((x1 + t, y1, z_bot)), Vector((x1 - t, y1, z_bot)),
                        Vector((x1 - t, y0, z_top)), Vector((x1 + t, y0, z_top)),
                        Vector((x1 + t, y1, z_top)), Vector((x1 - t, y1, z_top)),
                    ]
            verts = [bm.verts.new(c) for c in v_coords]
            bm.faces.new((verts[0], verts[1], verts[2], verts[3]))
            bm.faces.new((verts[7], verts[6], verts[5], verts[4]))
            bm.faces.new((verts[0], verts[1], verts[5], verts[4]))
            bm.faces.new((verts[1], verts[2], verts[6], verts[5]))
            bm.faces.new((verts[2], verts[3], verts[7], verts[6]))
            bm.faces.new((verts[3], verts[0], verts[4], verts[7]))
            bm.faces.ensure_lookup_table()
        except (ValueError, IndexError) as e:
            print(f"Warning: Parapet segment failed: {e}")


    # =========================================================================
    #  ENHANCEMENT 5 — BASE PLINTH
    #  A thicker, slightly protruding base section at ground level.
    #  Grounds the building visually — makes it feel anchored.
    # =========================================================================

    @staticmethod
    def add_base_plinth(bm, building_width, building_depth,
                        plinth_height, plinth_protrusion):
        """
        Adds a protruding plinth/base section around the building at ground level.

        Args:
            plinth_height (float): How tall the plinth section is.
            plinth_protrusion (float): How far it protrudes from the wall faces.
        """
        if plinth_height <= 0 or plinth_protrusion <= 0:
            return

        half_thick = Config.WALL_THICKNESS / 2.0
        p = plinth_protrusion
        h = plinth_height
        w = building_width
        d = building_depth

        # Four plinth sides — each is a box that protrudes outward from the wall
        sides = [
            # (x0, y0, x1, y1) of plinth outer face at z=0
            # South: Y face outward
            (0 - p, 0 - half_thick - p, w + p, 0 - half_thick),
            # North
            (0 - p, d + half_thick,     w + p, d + half_thick + p),
            # West
            (0 - half_thick - p, 0,     0 - half_thick,     d),
            # East
            (w + half_thick,     0,     w + half_thick + p, d),
        ]

        for (x0, y0, x1, y1) in sides:
            v_coords = [
                Vector((x0, y0, 0)),  Vector((x1, y0, 0)),
                Vector((x1, y1, 0)),  Vector((x0, y1, 0)),
                Vector((x0, y0, h)),  Vector((x1, y0, h)),
                Vector((x1, y1, h)),  Vector((x0, y1, h)),
            ]
            try:
                verts = [bm.verts.new(c) for c in v_coords]
                bm.faces.new((verts[0], verts[1], verts[2], verts[3]))
                bm.faces.new((verts[7], verts[6], verts[5], verts[4]))
                bm.faces.new((verts[0], verts[1], verts[5], verts[4]))
                bm.faces.new((verts[1], verts[2], verts[6], verts[5]))
                bm.faces.new((verts[2], verts[3], verts[7], verts[6]))
                bm.faces.new((verts[3], verts[0], verts[4], verts[7]))
                bm.faces.ensure_lookup_table()
            except (ValueError, IndexError) as e:
                print(f"Warning: Plinth side failed: {e}")

    # =========================================================================
    #  PERIMETER-AWARE ENHANCEMENTS
    #  These work with arbitrary footprint polygons via perimeter edge lists.
    # =========================================================================

    @staticmethod
    def _add_extruded_strip(bm, x0, y0, x1, y1, x2, y2, x3, y3, z_bot, z_top):
        """
        Creates a box from a 2D quad (4 corners at z_bot) extruded up to z_top.
        Points should be ordered: inner_start, inner_end, outer_end, outer_start
        (forms the top face in CCW order for upward normal).
        """
        if z_top <= z_bot:
            return
        try:
            v_coords = [
                Vector((x0, y0, z_bot)), Vector((x1, y1, z_bot)),
                Vector((x2, y2, z_bot)), Vector((x3, y3, z_bot)),
                Vector((x0, y0, z_top)), Vector((x1, y1, z_top)),
                Vector((x2, y2, z_top)), Vector((x3, y3, z_top)),
            ]
            verts = [bm.verts.new(c) for c in v_coords]
            bm.faces.new((verts[0], verts[1], verts[2], verts[3]))  # bottom
            bm.faces.new((verts[7], verts[6], verts[5], verts[4]))  # top
            bm.faces.new((verts[0], verts[1], verts[5], verts[4]))  # side 1
            bm.faces.new((verts[1], verts[2], verts[6], verts[5]))  # side 2
            bm.faces.new((verts[2], verts[3], verts[7], verts[6]))  # side 3
            bm.faces.new((verts[3], verts[0], verts[4], verts[7]))  # side 4
            bm.faces.ensure_lookup_table()
        except (ValueError, IndexError) as e:
            print(f"Warning: Extruded strip failed: {e}")

    @staticmethod
    def add_parapet_from_perimeter(bm, perimeter_edges, roof_z,
                                    parapet_height, parapet_thickness):
        """Parapet wall along arbitrary perimeter edges."""
        if parapet_height <= 0 or parapet_thickness <= 0:
            return
        ht = parapet_thickness / 2.0
        z0 = roof_z
        z1 = roof_z + parapet_height
        for edge in perimeter_edges:
            sx, sy = edge['start']
            ex, ey = edge['end']
            nx, ny = edge['normal']
            # Inner edge (toward building center)
            ix0, iy0 = sx - nx * ht, sy - ny * ht
            ix1, iy1 = ex - nx * ht, ey - ny * ht
            # Outer edge
            ox0, oy0 = sx + nx * ht, sy + ny * ht
            ox1, oy1 = ex + nx * ht, ey + ny * ht
            GeometryBuildings._add_extruded_strip(
                bm, ix0, iy0, ix1, iy1, ox1, oy1, ox0, oy0, z0, z1)

    @staticmethod
    def add_plinth_from_perimeter(bm, perimeter_edges, plinth_height, plinth_protrusion):
        """Plinth around arbitrary perimeter edges."""
        if plinth_height <= 0 or plinth_protrusion <= 0:
            return
        ht = Config.WALL_THICKNESS / 2.0
        p = plinth_protrusion
        for edge in perimeter_edges:
            sx, sy = edge['start']
            ex, ey = edge['end']
            nx, ny = edge['normal']
            # Inner: at wall outer face
            ix0, iy0 = sx + nx * ht, sy + ny * ht
            ix1, iy1 = ex + nx * ht, ey + ny * ht
            # Outer: wall outer face + protrusion
            ox0, oy0 = sx + nx * (ht + p), sy + ny * (ht + p)
            ox1, oy1 = ex + nx * (ht + p), ey + ny * (ht + p)
            GeometryBuildings._add_extruded_strip(
                bm, ix0, iy0, ix1, iy1, ox1, oy1, ox0, oy0, 0, plinth_height)

    @staticmethod
    def add_band_from_perimeter(bm, perimeter_edges, band_z, band_height, band_protrusion):
        """Horizontal band around arbitrary perimeter edges."""
        if band_height <= 0 or band_protrusion <= 0:
            return
        ht = Config.WALL_THICKNESS / 2.0
        p = band_protrusion
        for edge in perimeter_edges:
            sx, sy = edge['start']
            ex, ey = edge['end']
            nx, ny = edge['normal']
            # Inner: at wall outer face
            ix0, iy0 = sx + nx * ht, sy + ny * ht
            ix1, iy1 = ex + nx * ht, ey + ny * ht
            # Outer: wall outer face + protrusion
            ox0, oy0 = sx + nx * (ht + p), sy + ny * (ht + p)
            ox1, oy1 = ex + nx * (ht + p), ey + ny * (ht + p)
            GeometryBuildings._add_extruded_strip(
                bm, ix0, iy0, ix1, iy1, ox1, oy1, ox0, oy0, band_z, band_z + band_height)

    @staticmethod
    def add_ledge_from_perimeter(bm, perimeter_edges, ledge_z, ledge_height, ledge_depth):
        """Ledge/trim around arbitrary perimeter edges."""
        if ledge_height <= 0 or ledge_depth <= 0:
            return
        z0 = ledge_z
        z1 = ledge_z + ledge_height
        for edge in perimeter_edges:
            sx, sy = edge['start']
            ex, ey = edge['end']
            nx, ny = edge['normal']
            # Inner: at footprint edge
            # Outer: footprint edge + ledge_depth outward
            ox0, oy0 = sx + nx * ledge_depth, sy + ny * ledge_depth
            ox1, oy1 = ex + nx * ledge_depth, ey + ny * ledge_depth
            GeometryBuildings._add_extruded_strip(
                bm, sx, sy, ex, ey, ox1, oy1, ox0, oy0, z0, z1)

    @staticmethod
    def add_corners_from_perimeter(bm, corner_positions, z_start, z_end,
                                    col_width, col_protrusion):
        """Corner columns at each vertex of arbitrary perimeter polygon."""
        if col_width <= 0 or col_protrusion <= 0 or z_end <= z_start:
            return
        hw = col_width / 2.0
        ht = Config.WALL_THICKNESS / 2.0
        for corner in corner_positions:
            cx, cy = corner['pos']
            dx, dy = corner['dir']
            # Column center offset outward from corner
            # Column box: from corner inward to corner + protrusion outward
            # Along the diagonal direction
            c_inner_x = cx - dx * ht
            c_inner_y = cy - dy * ht
            c_outer_x = cx + dx * (ht + col_protrusion)
            c_outer_y = cy + dy * (ht + col_protrusion)
            # Perpendicular to diagonal for width
            px, py = -dy, dx  # perpendicular
            x0 = min(c_inner_x, c_outer_x) - abs(px) * hw
            x1 = max(c_inner_x, c_outer_x) + abs(px) * hw
            y0 = min(c_inner_y, c_outer_y) - abs(py) * hw
            y1 = max(c_inner_y, c_outer_y) + abs(py) * hw
            v_coords = [
                Vector((x0, y0, z_start)), Vector((x1, y0, z_start)),
                Vector((x1, y1, z_start)), Vector((x0, y1, z_start)),
                Vector((x0, y0, z_end)),   Vector((x1, y0, z_end)),
                Vector((x1, y1, z_end)),   Vector((x0, y1, z_end)),
            ]
            try:
                verts = [bm.verts.new(c) for c in v_coords]
                bm.faces.new((verts[0], verts[1], verts[2], verts[3]))
                bm.faces.new((verts[7], verts[6], verts[5], verts[4]))
                bm.faces.new((verts[0], verts[1], verts[5], verts[4]))
                bm.faces.new((verts[1], verts[2], verts[6], verts[5]))
                bm.faces.new((verts[2], verts[3], verts[7], verts[6]))
                bm.faces.new((verts[3], verts[0], verts[4], verts[7]))
                bm.faces.ensure_lookup_table()
            except (ValueError, IndexError) as e:
                print(f"Warning: Corner column (perimeter) failed: {e}")

    @staticmethod
    def add_sills_from_segments(bm, wall_segments, sill_z, shelf_depth, shelf_height, floor_idx=0):
        """Add window sills for each wall segment that is WINDOW type."""
        if shelf_depth <= 0 or shelf_height <= 0:
            return
        for seg in wall_segments:
            if seg.get('angled') or seg.get('wall_type') != 'WINDOW':
                continue
            # Upper floors: doors become solid, already handled by caller
            wtype = seg['wall_type']
            if floor_idx > 0 and wtype == 'DOOR':
                continue
            GeometryBuildings.add_window_sill_shelf(
                bm, seg['bx'], seg['by'], seg['length'],
                sill_z, seg['axis'], shelf_depth, shelf_height)