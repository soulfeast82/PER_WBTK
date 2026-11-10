# World_Building_Toolkit/geometry_walkways.py
# (Based on MRTK_v380/geometry.py - Renamed class)

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

# Import required local modules
from .config import Config
from .utils import Utils # Needed for get_circle_segments access

class GeometryWalkways:
    """ Functions for creating BMesh geometry for Walkway and Railing components. """

    # === PROFILE GENERATION ===

    @staticmethod
    def get_circle_segments():
        """ Get number of segments for round rails based on Low Poly setting. """
        # Access lowpoly setting safely via Utils helper
        # Ensure 'wbtk_lowpoly' matches the name defined in properties.py
        low_poly = Utils.get_context_safe_bool('wbtk_lowpoly', default=False)
        return 8 if low_poly else 24

    @staticmethod
    def _circle_profile_verts(radius, segments=None):
        """ Generates vertex coordinates (List[Vector]) for a circle profile in XY plane. """
        if segments is None:
            segments = GeometryWalkways.get_circle_segments() # Call static method correctly
        segments = max(3, segments) # Ensure at least 3 segments
        step = 2 * math.pi / segments
        return [Vector((math.cos(a * step) * radius, math.sin(a * step) * radius, 0)) for a in range(segments)]

    @staticmethod
    def _square_profile_verts(half_width):
        """ Generates vertex coordinates (List[Vector]) for a square profile in XY plane. """
        hw = half_width
        return [ Vector((-hw, -hw, 0)), Vector(( hw, -hw, 0)), Vector(( hw,  hw, 0)), Vector((-hw,  hw, 0)) ]

    @staticmethod
    def _beveled_square_profile_verts(half_width, bevel_factor):
        """ Generates vertex coordinates (List[Vector]) for a beveled square profile in XY plane. """
        hw = half_width
        bevel_size = hw * max(0.0, min(0.9, bevel_factor)) # Clamp factor for safety
        inner_hw = hw - bevel_size
        # Define the 8 vertices
        return [
            Vector(( inner_hw, -hw, 0)), Vector(( hw, -inner_hw, 0)), # Bottom Right
            Vector(( hw,  inner_hw, 0)), Vector(( inner_hw,  hw, 0)), # Top Right
            Vector((-inner_hw,  hw, 0)), Vector((-hw,  inner_hw, 0)), # Top Left
            Vector((-hw, -inner_hw, 0)), Vector((-inner_hw, -hw, 0)), # Bottom Left
        ]

    @staticmethod
    def get_rail_profile_verts(radius, rail_style):
        """ Returns a list of Vector points defining the cross-section profile for a rail. """
        beam_half_width = radius # Radius is used as half-width for square/beveled
        if rail_style == 'ROUND':
            return GeometryWalkways._circle_profile_verts(radius)
        elif rail_style == 'NEO_RAIL':
            return GeometryWalkways._beveled_square_profile_verts(beam_half_width, Config.NEO_RAIL_BEVEL_FACTOR)
        elif rail_style in ('SQUARE', 'INDUSTRIAL_RAIL'): # Treat Industrial as Square for now
            return GeometryWalkways._square_profile_verts(beam_half_width)
        else: # Fallback
            print(f"Warning: Unknown rail style '{rail_style}', defaulting to ROUND.")
            return GeometryWalkways._circle_profile_verts(radius)

    # === BEAM GENERATION (Internal Helpers) ===

    @staticmethod
    def _add_profile_beam_internal(bm, profile_verts_local, base_pos, offset_vec):
        """ Internal: Extrudes a profile along an offset vector. Returns end verts or None. """
        num_profile_verts = len(profile_verts_local)
        if num_profile_verts < 3: return None

        verts_start = [bm.verts.new(v + Vector(base_pos)) for v in profile_verts_local]
        verts_end = [bm.verts.new(v.co + offset_vec) for v in verts_start]

        if len(verts_start) != num_profile_verts or len(verts_end) != num_profile_verts:
            print("Warning: Vertex creation mismatch in _add_profile_beam_internal.")
            # Minimal cleanup attempt
            for v in verts_start + verts_end:
                 if v.is_valid and v in bm.verts: bm.verts.remove(v)
            return None

        for i in range(num_profile_verts):
            v1 = verts_start[i]
            v2 = verts_start[(i + 1) % num_profile_verts]
            v3 = verts_end[(i + 1) % num_profile_verts]
            v4 = verts_end[i]
            try: bm.faces.new((v1, v2, v3, v4))
            except ValueError: pass # Ignore degenerate faces

        # Caps are generally not needed for railing segments
        # try: bm.faces.new(verts_start) except ValueError: pass
        # try: bm.faces.new(reversed(verts_end)) except ValueError: pass

        return verts_end

    @staticmethod
    def _add_profile_beam_angled_internal(bm, profile_verts_local, p1_vec, direction_vec):
        """ Internal: Creates a beam oriented along a direction vector. Returns end verts or None. """
        num_profile_verts = len(profile_verts_local);
        if num_profile_verts < 3: return None
        length = direction_vec.length;
        if length < 0.0001: return None

        # Calculate orientation matrix robustly
        vec_norm = direction_vec.normalized()
        up_ref = Vector((0, 0, 1))
        # If vec nearly parallel to up_ref, use a different reference
        if abs(vec_norm.dot(up_ref)) > 0.999: up_ref = Vector((0, 1, 0))

        side = vec_norm.cross(up_ref).normalized()
        # If cross product resulted in zero vector (shouldn't happen with check above)
        if side.length < 0.001: side = vec_norm.cross(Vector((1,0,0))).normalized() # Fallback
        if side.length < 0.001: print("Warning: Could not determine side vector."); return None

        up = side.cross(vec_norm).normalized() # Order matters for right-handed coords
        if up.length < 0.001: print("Warning: Could not determine up vector."); return None

        # Basis vectors form columns of rotation matrix
        rot_mat = Matrix((side, up, vec_norm)).transposed().to_4x4()

        verts_start = [bm.verts.new(p1_vec + (rot_mat @ v)) for v in profile_verts_local]
        verts_end = [bm.verts.new(v.co + direction_vec) for v in verts_start]

        if len(verts_start) != num_profile_verts or len(verts_end) != num_profile_verts:
             print("Warning: Vertex creation mismatch in _add_profile_beam_angled_internal.")
             # Minimal cleanup attempt
             for v in verts_start + verts_end:
                  if v.is_valid and v in bm.verts: bm.verts.remove(v)
             return None

        for i in range(num_profile_verts):
            v1 = verts_start[i]
            v2 = verts_start[(i + 1) % num_profile_verts]
            v3 = verts_end[(i + 1) % num_profile_verts]
            v4 = verts_end[i]
            try: bm.faces.new((v1, v2, v3, v4))
            except ValueError: pass

        return verts_end

    # === BEAM GENERATION (Public Methods) ===

    @staticmethod
    def add_beam(bm, base_pos, length, axis='X', rail_style='ROUND', radius=None):
        """ Creates a straight beam along X, Y, or Z axis using a specified profile. """
        eff_radius = radius if radius is not None else Config.RAIL_RADIUS
        profile_verts = GeometryWalkways.get_rail_profile_verts(eff_radius, rail_style)
        if not profile_verts: return None

        if axis == 'X': offset = Vector((length, 0, 0))
        elif axis == 'Y': offset = Vector((0, length, 0))
        elif axis == 'Z': offset = Vector((0, 0, length))
        else: print(f"Error: Invalid axis '{axis}'."); return None

        # The profile lives in the XY plane. Extruding it along X or Y keeps it
        # IN that plane (a zero-thickness ribbon); the angled helper builds an
        # orthonormal basis so the profile is perpendicular to the run.
        return GeometryWalkways._add_profile_beam_angled_internal(bm, profile_verts, Vector(base_pos), offset)

    @staticmethod
    def add_beam_angled(bm, point1, point2, rail_style='ROUND', radius=None):
        """ Creates a beam between two arbitrary 3D points using a specified profile. """
        eff_radius = radius if radius is not None else Config.RAIL_RADIUS
        profile_verts = GeometryWalkways.get_rail_profile_verts(eff_radius, rail_style)
        if not profile_verts: return None

        p1 = Vector(point1); p2 = Vector(point2)
        direction_vec = p2 - p1

        return GeometryWalkways._add_profile_beam_angled_internal(bm, profile_verts, p1, direction_vec)

    # === WALKWAY TILE / SURFACE GENERATION ===

    @staticmethod
    def _create_grate_tile_internal(bm, x_base, y_base, length, width, main_axis='X', z_offset=0.0):
        """ Internal: Creates BMesh geometry for a single grate tile. """
        BAR_SIZE = Config.WALKWAY_GRATE_BAR_SIZE; SPACING = Config.WALKWAY_GRATE_SPACING
        HALF_BAR = BAR_SIZE / 2.0; GRATE_STYLE = 'SQUARE'; RADIUS = HALF_BAR
        base_offset = Vector((x_base, y_base, z_offset))

        # Frame (Parallel to main_axis)
        if main_axis == 'X':
            frame_coord1 = 0; frame_coord2 = width; frame_axis = 'Y'; beam_axis = 'X'
        else: # main_axis == 'Y'
            frame_coord1 = 0; frame_coord2 = width; frame_axis = 'X'; beam_axis = 'Y'

        p1_frame1 = base_offset + Vector((frame_coord1 if frame_axis=='X' else 0, frame_coord1 if frame_axis=='Y' else 0, 0))
        p1_frame2 = base_offset + Vector((frame_coord2 if frame_axis=='X' else 0, frame_coord2 if frame_axis=='Y' else 0, 0))
        GeometryWalkways.add_beam(bm, p1_frame1, length, beam_axis, rail_style=GRATE_STYLE, radius=RADIUS)
        GeometryWalkways.add_beam(bm, p1_frame2, length, beam_axis, rail_style=GRATE_STYLE, radius=RADIUS)

        # Cross Bars (Perpendicular to main_axis)
        cross_bar_length = width - BAR_SIZE # Length of bars perpendicular to main axis
        effective_main_length = length - BAR_SIZE # Space available along main axis
        if cross_bar_length < 0.001 or effective_main_length < 0.001: return

        num_spaces = max(0, math.floor(effective_main_length / SPACING))
        num_bars = num_spaces + 1
        actual_spacing = effective_main_length / num_bars if num_bars > 0 else 0

        for i in range(num_bars):
             bar_center_main = HALF_BAR + actual_spacing / 2.0 + i * actual_spacing
             if bar_center_main + HALF_BAR > length + 0.001: continue # Ensure within bounds

             # Start position of the cross bar
             if main_axis == 'X': # Cross bar runs along Y
                 start_pos = base_offset + Vector((bar_center_main, HALF_BAR, 0))
                 GeometryWalkways.add_beam(bm, start_pos, cross_bar_length, 'Y', rail_style=GRATE_STYLE, radius=RADIUS)
             else: # Cross bar runs along X
                 start_pos = base_offset + Vector((HALF_BAR, bar_center_main, 0))
                 GeometryWalkways.add_beam(bm, start_pos, cross_bar_length, 'X', rail_style=GRATE_STYLE, radius=RADIUS)

    @staticmethod
    def _apply_walkway_style_to_edges(bm, boundary_edges, walkway_style):
        """ Internal: Applies style modifications to a list of boundary edges. """
        if not boundary_edges or walkway_style in ('SOLID', 'GRATE'): return

        try:
            if walkway_style == 'SOLID_LIP':
                ret = bmesh.ops.extrude_edge_only(bm, edges=boundary_edges)
                verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
                if verts: bmesh.ops.translate(bm, verts=verts, vec=(0, 0, -Config.WALKWAY_LIP_DEPTH))
            elif walkway_style == 'NEO_PANEL':
                bmesh.ops.bevel(bm, geom=boundary_edges, offset=Config.NEO_PANEL_BEVEL_WIDTH,
                                offset_type='WIDTH', segments=2, profile=0.5, affect='EDGES')
            elif walkway_style == 'INDUSTRIAL_PLATE':
                # Extrude edges up slightly for multi-tile sections
                ret = bmesh.ops.extrude_edge_only(bm, edges=boundary_edges)
                verts = [v for v in ret['geom'] if isinstance(v, bmesh.types.BMVert)]
                if verts: bmesh.ops.translate(bm, verts=verts, vec=(0, 0, Config.INDUSTRIAL_PLATE_EDGE_HEIGHT))
        except Exception as e:
            print(f"Warning: Failed applying edge style '{walkway_style}': {e}")

    @staticmethod
    def _apply_walkway_style_to_face(bm, face, walkway_style, size_x, size_y):
        """ Internal: Applies style modifications to a single face (used for caps). """
        if not face or not face.is_valid or walkway_style in ('SOLID', 'GRATE'): return

        if walkway_style in ('SOLID_LIP', 'NEO_PANEL'):
             # Apply these styles to the boundary edges of the face
             GeometryWalkways._apply_walkway_style_to_edges(bm, list(face.edges), walkway_style)
        elif walkway_style == 'INDUSTRIAL_PLATE':
             # Extrude face up, inset, move up again (plate effect)
             try:
                  # Ensure face normal is pointing up
                  face.normal_update()
                  if face.normal.z < 0.9: face.normal_flip() # Flip if needed

                  ret = bmesh.ops.extrude_face_region(bm, geom=[face])
                  new_top_faces = [f for f in ret['geom'] if isinstance(f, bmesh.types.BMFace) and f.normal.z > 0.9]
                  if not new_top_faces: return
                  new_top_face = new_top_faces[0]
                  new_verts = list(new_top_face.verts)

                  center = new_top_face.calc_center_median()
                  scale_x = max(0.01, 1.0 - (Config.INDUSTRIAL_PLATE_EDGE_WIDTH * 2 / size_x)) if size_x > 0.001 else 0.01
                  scale_y = max(0.01, 1.0 - (Config.INDUSTRIAL_PLATE_EDGE_WIDTH * 2 / size_y)) if size_y > 0.001 else 0.01
                  # Use Matrix for scaling around center
                  mat_trans = Matrix.Translation(center)
                  mat_scale = Matrix.Scale(scale_x, 4, (1, 0, 0)) @ Matrix.Scale(scale_y, 4, (0, 1, 0))
                  mat_trans_inv = Matrix.Translation(-center)
                  bmesh.ops.transform(bm, verts=new_verts, matrix=mat_trans @ mat_scale @ mat_trans_inv)
                  bmesh.ops.translate(bm, verts=new_verts, vec=(0, 0, Config.INDUSTRIAL_PLATE_EDGE_HEIGHT))
             except Exception as e:
                  print(f"Warning: Failed applying Industrial Plate style to face: {e}")

    # === WALKWAY GENERATION (Public Methods) ===

    @staticmethod
    def create_walkway_plane_bmesh(tiles_x, tiles_y, walkway_style='SOLID', size_x=Config.LENGTH_UNIT, size_y=Config.WIDTH_UNIT, main_axis='X'):
        """ Creates a BMesh for a flat walkway section potentially composed of multiple tiles. """
        bm = bmesh.new()
        is_grate = (walkway_style == 'GRATE')
        initial_faces = [] if not is_grate else None # Only track faces for solid styles

        for ix in range(tiles_x):
            for iy in range(tiles_y):
                # Calculate base position for this tile
                base_x = ix * size_x if main_axis == 'X' else ix * size_y # size_y is width for X-axis main
                base_y = iy * size_y if main_axis == 'X' else iy * size_x # size_x is length for X-axis main

                # Use correct length/width based on main axis for the tile generation
                tile_len = size_x if main_axis == 'X' else size_y
                tile_wid = size_y if main_axis == 'X' else size_x

                if is_grate:
                    GeometryWalkways._create_grate_tile_internal(bm, base_x, base_y, tile_len, tile_wid, main_axis)
                else: # Solid-based styles
                    v0 = bm.verts.new((base_x, base_y, 0))
                    v1 = bm.verts.new((base_x + tile_len, base_y, 0))
                    v2 = bm.verts.new((base_x + tile_len, base_y + tile_wid, 0))
                    v3 = bm.verts.new((base_x, base_y + tile_wid, 0))
                    try: initial_faces.append(bm.faces.new((v0, v1, v2, v3)))
                    except ValueError: pass

        # Post-processing for Solid-based styles (merge verts, apply edge styles)
        if initial_faces and walkway_style != 'SOLID':
            try: bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
            except Exception: pass # Ignore errors
            bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
            boundary_edges = [e for e in bm.edges if len(e.link_faces) <= 1] # Edges with 1 or 0 faces are boundary
            GeometryWalkways._apply_walkway_style_to_edges(bm, boundary_edges, walkway_style)

        # Final cleanup for grate style
        if is_grate:
            try: bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
            except Exception: pass

        return bm

    @staticmethod
    def create_walkway_cap_bmesh(walkway_style='SOLID', size_x=Config.WIDTH_UNIT, size_y=Config.WIDTH_UNIT):
        """ Creates a BMesh for a single cap tile (e.g., corners, endcaps). """
        bm = bmesh.new()
        if walkway_style == 'GRATE':
            GeometryWalkways._create_grate_tile_internal(bm, 0, 0, size_x, size_y, 'X') # Assume X main axis
            try: bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
            except Exception: pass
        else:
            v0=bm.verts.new((0,0,0)); v1=bm.verts.new((size_x,0,0));
            v2=bm.verts.new((size_x,size_y,0)); v3=bm.verts.new((0,size_y,0))
            try: top_face = bm.faces.new((v0,v1,v2,v3))
            except ValueError: return bm # Return empty if face fails
            GeometryWalkways._apply_walkway_style_to_face(bm, top_face, walkway_style, size_x, size_y)
        return bm

    # === RAILINGS GENERATION (Public Methods) ===

    @staticmethod
    def create_rails_bmesh(num_tiles, y_local_offset, start_tile_index=0, rail_style='ROUND', length_per_tile=Config.LENGTH_UNIT):
        """ Creates BMesh geometry for a straight run of railing along the X axis. """
        bm = bmesh.new()
        for ix in range(num_tiles):
            start_x = ix * length_per_tile
            for rh in Config.RAIL_HEIGHTS:
                GeometryWalkways.add_beam(bm, (start_x, y_local_offset, rh), length_per_tile, 'X', rail_style)
        for ix in range(num_tiles + 1):
            if start_tile_index > 0 and ix == 0: continue # Skip first post on continuation chunks
            post_x = ix * length_per_tile
            GeometryWalkways.add_beam(bm, (post_x, y_local_offset, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style)
        return bm

    @staticmethod
    def create_rails_bmesh_y_leg(num_tiles, x_local_offset, start_tile_index=0, rail_style='ROUND', width_per_tile=Config.WIDTH_UNIT):
        """ Creates BMesh geometry for a straight run of railing along the Y axis. """
        bm = bmesh.new()
        for iy in range(num_tiles):
            start_y = iy * width_per_tile
            for rh in Config.RAIL_HEIGHTS:
                GeometryWalkways.add_beam(bm, (x_local_offset, start_y, rh), width_per_tile, 'Y', rail_style)
        for iy in range(num_tiles + 1):
            if start_tile_index > 0 and iy == 0: continue
            post_y = iy * width_per_tile
            GeometryWalkways.add_beam(bm, (x_local_offset, post_y, 0), Config.RAIL_HEIGHTS[0], 'Z', rail_style)
        return bm

    # Inside world_building_toolkit/geometry_walkways.py -> GeometryWalkways class

    # --- REPLACE THIS ENTIRE METHOD ---
    @staticmethod
    def create_angled_rails_bmesh(p1_base, p2_base, rail_style='ROUND', num_intermediate_posts=0): # Added parameter
        """ Creates BMesh geometry for angled railing (e.g., stairs), including intermediate posts. """
        bm = bmesh.new()
        p1 = Vector(p1_base); p2 = Vector(p2_base)
        base_vector = p2 - p1 # Vector along the slope base
        if base_vector.length < 0.001: # Check for valid length
            bm.free(); return bmesh.new() # Return empty bmesh

        all_post_bases = [p1] # Start with the first post base

        # Calculate intermediate post base positions
        num_intermediate_posts = max(0, int(num_intermediate_posts)) # Ensure non-negative integer
        if num_intermediate_posts > 0:
            total_segments = num_intermediate_posts + 1
            for i in range(1, total_segments): # i=1 to num_intermediate_posts
                fraction = i / total_segments
                intermediate_base_pos = p1 + base_vector * fraction
                all_post_bases.append(intermediate_base_pos)

        all_post_bases.append(p2) # Add the last post base

        # Sort posts primarily by the dominant run axis (assume X or Y, not Z)
        # to ensure beams are created between consecutive posts along the run.
        dominant_axis_index = 0 if abs(base_vector.x) >= abs(base_vector.y) else 1
        all_post_bases.sort(key=lambda p: p[dominant_axis_index])

        # Add vertical posts at each base location
        for post_base in all_post_bases:
            GeometryWalkways.add_beam(bm, post_base, Config.RAIL_HEIGHTS[0], 'Z', rail_style=rail_style)

        # Add angled horizontal rails between consecutive posts
        for i in range(len(all_post_bases) - 1):
            start_base = all_post_bases[i]
            end_base = all_post_bases[i+1]
            # Create angled beam segments for each rail height level
            for rh in Config.RAIL_HEIGHTS:
                p_start = start_base + Vector((0,0,rh))
                p_end = end_base + Vector((0,0,rh))
                GeometryWalkways.add_beam_angled(bm, p_start, p_end, rail_style)

        return bm
    # --- END OF REPLACEMENT ---