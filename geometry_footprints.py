# geometry_footprints.py
# Generates wall segment lists and floor slab polygons for non-rectangular
# building footprints: RECT, L_SHAPE, U_SHAPE, T_SHAPE, CORNER_CUT.
#
# Each wall segment is a dict:
#   { 'bx', 'by', 'length', 'axis', 'wall_type', 'angled': False }
# Angled segments (corner cut only) add:
#   { 'angled': True, 'start': (x,y), 'end': (x,y), 'wall_type' }
#
# Floor slab polygons are lists of (x, y) tuples for BMesh face creation.

from .config import Config
import math


def get_perimeter_edges(shape, width, depth, wing_w, wing_d,
                        cut_size=3.0, cut_pos='FRONT_LEFT',
                        wing_pos='BACK_LEFT'):
    """
    Return a list of perimeter edge dicts for a footprint shape.
    Each edge: {'start': (x,y), 'end': (x,y), 'normal': (nx,ny)}
    where normal points outward from the building.
    Edges are ordered clockwise (matching wall segment order).
    """
    verts = get_floor_slab_verts(shape, width, depth, wing_w, wing_d,
                                  cut_size, cut_pos, wing_pos)
    if not verts or len(verts) < 3:
        return []

    edges = []
    n = len(verts)
    for i in range(n):
        sx, sy = verts[i]
        ex, ey = verts[(i + 1) % n]
        # Edge direction
        dx = ex - sx
        dy = ey - sy
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-6:
            continue
        # Outward normal: for CW winding, right-hand normal is (dy, -dx)
        # For CCW winding (which get_floor_slab_verts uses), left-hand normal is (-dy, dx)
        # But we need outward. Let's compute and check.
        # CCW polygon: outward normal for edge (dx, dy) is (dy, -dx) normalized
        # Actually for CCW: the outward normal is (dy, -dx)
        nx = dy / length
        ny = -dx / length
        edges.append({
            'start': (sx, sy),
            'end': (ex, ey),
            'normal': (nx, ny),
            'length': length,
        })

    # Verify normals point outward by checking against polygon centroid
    if edges:
        cx = sum(v[0] for v in verts) / n
        cy = sum(v[1] for v in verts) / n
        # Test first edge midpoint + normal should point away from centroid
        e = edges[0]
        mx = (e['start'][0] + e['end'][0]) / 2.0
        my = (e['start'][1] + e['end'][1]) / 2.0
        # Vector from centroid to midpoint
        to_mid_x = mx - cx
        to_mid_y = my - cy
        dot = to_mid_x * e['normal'][0] + to_mid_y * e['normal'][1]
        if dot < 0:
            # Normals are flipped, reverse them all
            for edge in edges:
                edge['normal'] = (-edge['normal'][0], -edge['normal'][1])

    return edges


def get_corner_positions(shape, width, depth, wing_w, wing_d,
                         cut_size=3.0, cut_pos='FRONT_LEFT',
                         wing_pos='BACK_LEFT'):
    """
    Return corner vertex positions and their outward diagonal directions.
    """
    edges = get_perimeter_edges(shape, width, depth, wing_w, wing_d,
                                 cut_size, cut_pos, wing_pos)
    if not edges:
        return []

    corners = []
    n = len(edges)
    for i in range(n):
        prev = edges[(i - 1) % n]
        curr = edges[i]
        # Corner is at curr['start']
        # Outward direction = average of prev normal and curr normal
        dx = (prev['normal'][0] + curr['normal'][0])
        dy = (prev['normal'][1] + curr['normal'][1])
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-6:
            dx, dy = curr['normal']
        else:
            dx /= length
            dy /= length
        corners.append({
            'pos': curr['start'],
            'dir': (dx, dy),
        })

    return corners


def get_wall_segments(shape, width, depth, wing_w, wing_d,
                      front_type, back_type, left_type, right_type,
                      wing_type, cut_size=3.0, cut_pos='FRONT_LEFT',
                      floor_idx=0, wing_pos='BACK_LEFT',
                      courtyard_type='SOLID'):
    """
    Return a list of wall segment descriptors for one floor.

    All dimensions are in world units (meters), not tiles.
    Wings only appear on ground floor for DOOR walls; upper floors
    convert DOOR→SOLID automatically (handled by caller).
    """
    segs = []

    if shape == 'RECT':
        # Standard 4 walls
        segs = [
            {'bx': 0, 'by': 0,     'length': width, 'axis': 'X', 'wall_type': front_type},
            {'bx': 0, 'by': depth,  'length': width, 'axis': 'X', 'wall_type': back_type},
            {'bx': 0, 'by': 0,     'length': depth, 'axis': 'Y', 'wall_type': left_type},
            {'bx': width, 'by': 0, 'length': depth, 'axis': 'Y', 'wall_type': right_type},
        ]

    elif shape == 'L_SHAPE':
        ww = min(wing_w, width - 0.5)
        wd = wing_d

        if wing_pos == 'BACK_LEFT':
            # Wing extends from (0, depth) to (ww, depth+wd)
            segs = [
                {'bx': 0,    'by': 0,          'length': width,        'axis': 'X', 'wall_type': front_type},
                {'bx': width,'by': 0,          'length': depth,        'axis': 'Y', 'wall_type': right_type},
                {'bx': ww,   'by': depth,      'length': width - ww,   'axis': 'X', 'wall_type': back_type},
                {'bx': ww,   'by': depth,      'length': wd,           'axis': 'Y', 'wall_type': wing_type},
                {'bx': 0,    'by': depth + wd, 'length': ww,           'axis': 'X', 'wall_type': wing_type},
                {'bx': 0,    'by': 0,          'length': depth + wd,   'axis': 'Y', 'wall_type': left_type},
            ]
        elif wing_pos == 'BACK_RIGHT':
            # Wing extends from (width-ww, depth) to (width, depth+wd)
            segs = [
                {'bx': 0,    'by': 0,          'length': width,            'axis': 'X', 'wall_type': front_type},
                {'bx': width,'by': 0,          'length': depth + wd,       'axis': 'Y', 'wall_type': right_type},
                {'bx': width - ww, 'by': depth + wd, 'length': ww,        'axis': 'X', 'wall_type': wing_type},
                {'bx': width - ww, 'by': depth, 'length': wd,             'axis': 'Y', 'wall_type': wing_type},
                {'bx': 0,    'by': depth,      'length': width - ww,       'axis': 'X', 'wall_type': back_type},
                {'bx': 0,    'by': 0,          'length': depth,            'axis': 'Y', 'wall_type': left_type},
            ]
        elif wing_pos == 'FRONT_LEFT':
            # Wing extends from (0, -wd) to (ww, 0)
            segs = [
                {'bx': ww,   'by': 0,          'length': width - ww,   'axis': 'X', 'wall_type': front_type},
                {'bx': width,'by': 0,          'length': depth,        'axis': 'Y', 'wall_type': right_type},
                {'bx': 0,    'by': depth,      'length': width,        'axis': 'X', 'wall_type': back_type},
                {'bx': 0,    'by': -wd,        'length': depth + wd,   'axis': 'Y', 'wall_type': left_type},
                {'bx': 0,    'by': -wd,        'length': ww,           'axis': 'X', 'wall_type': wing_type},
                {'bx': ww,   'by': -wd,        'length': wd,           'axis': 'Y', 'wall_type': wing_type},
            ]
        elif wing_pos == 'FRONT_RIGHT':
            # Wing extends from (width-ww, -wd) to (width, 0)
            segs = [
                {'bx': 0,    'by': 0,          'length': width - ww,   'axis': 'X', 'wall_type': front_type},
                {'bx': width - ww, 'by': -wd,  'length': wd,           'axis': 'Y', 'wall_type': wing_type},
                {'bx': width - ww, 'by': -wd,  'length': ww,           'axis': 'X', 'wall_type': wing_type},
                {'bx': width,'by': -wd,        'length': depth + wd,   'axis': 'Y', 'wall_type': right_type},
                {'bx': 0,    'by': depth,      'length': width,        'axis': 'X', 'wall_type': back_type},
                {'bx': 0,    'by': 0,          'length': depth,        'axis': 'Y', 'wall_type': left_type},
            ]
        else:
            # Fallback to back-left
            return get_wall_segments(shape, width, depth, wing_w, wing_d,
                                     front_type, back_type, left_type, right_type,
                                     wing_type, cut_size, cut_pos, floor_idx,
                                     'BACK_LEFT', courtyard_type)

    elif shape == 'U_SHAPE':
        ww = min(wing_w, (width / 2.0) - 0.5)
        wd = wing_d
        courtyard_w = width - 2 * ww

        segs = [
            {'bx': 0,    'by': 0,          'length': width,          'axis': 'X', 'wall_type': front_type},
            {'bx': width,'by': 0,          'length': depth + wd,     'axis': 'Y', 'wall_type': right_type},
            {'bx': width - ww, 'by': depth + wd, 'length': ww,      'axis': 'X', 'wall_type': wing_type},
            {'bx': width - ww, 'by': depth, 'length': wd,           'axis': 'Y', 'wall_type': courtyard_type},
            {'bx': ww,   'by': depth,      'length': courtyard_w,    'axis': 'X', 'wall_type': back_type},
            {'bx': ww,   'by': depth,      'length': wd,            'axis': 'Y', 'wall_type': courtyard_type},
            {'bx': 0,    'by': depth + wd, 'length': ww,            'axis': 'X', 'wall_type': wing_type},
            {'bx': 0,    'by': 0,          'length': depth + wd,     'axis': 'Y', 'wall_type': left_type},
        ]

    elif shape == 'T_SHAPE':
        # Main body + centered wing extending from back
        # Main body: (0,0) to (width, depth)
        # Wing: centered, ((width-wing_w)/2, depth) to ((width+wing_w)/2, depth+wing_d)
        ww = min(wing_w, width - 1.0)
        wd = wing_d
        wing_left = (width - ww) / 2.0
        wing_right = wing_left + ww

        segs = [
            # Front wall
            {'bx': 0,           'by': 0,          'length': width,             'axis': 'X', 'wall_type': front_type},
            # Right wall (main body only)
            {'bx': width,       'by': 0,          'length': depth,             'axis': 'Y', 'wall_type': right_type},
            # Back-right section (wing_right to width)
            {'bx': wing_right,  'by': depth,      'length': width - wing_right,'axis': 'X', 'wall_type': back_type},
            # Wing right wall
            {'bx': wing_right,  'by': depth,      'length': wd,               'axis': 'Y', 'wall_type': wing_type},
            # Wing top
            {'bx': wing_left,   'by': depth + wd, 'length': ww,              'axis': 'X', 'wall_type': wing_type},
            # Wing left wall
            {'bx': wing_left,   'by': depth,      'length': wd,              'axis': 'Y', 'wall_type': wing_type},
            # Back-left section (0 to wing_left)
            {'bx': 0,           'by': depth,      'length': wing_left,        'axis': 'X', 'wall_type': back_type},
            # Left wall (main body only)
            {'bx': 0,           'by': 0,          'length': depth,             'axis': 'Y', 'wall_type': left_type},
        ]

    elif shape == 'CORNER_CUT':
        # Rectangle with one corner chamfered at 45°
        cs = min(cut_size, width - 0.5, depth - 0.5)  # Clamp to building size

        if cut_pos == 'FRONT_LEFT':
            segs = [
                # Front wall (shortened: cs to width)
                {'bx': cs,   'by': 0,     'length': width - cs, 'axis': 'X', 'wall_type': front_type},
                {'bx': width,'by': 0,     'length': depth,      'axis': 'Y', 'wall_type': right_type},
                {'bx': 0,    'by': depth, 'length': width,      'axis': 'X', 'wall_type': back_type},
                # Left wall (shortened: cs to depth)
                {'bx': 0,    'by': cs,    'length': depth - cs,  'axis': 'Y', 'wall_type': left_type},
                # Angled wall: (cs, 0) to (0, cs)
                {'angled': True, 'start': (cs, 0), 'end': (0, cs), 'wall_type': front_type},
            ]
        elif cut_pos == 'FRONT_RIGHT':
            segs = [
                # Front wall (shortened: 0 to width-cs)
                {'bx': 0,         'by': 0,     'length': width - cs, 'axis': 'X', 'wall_type': front_type},
                # Right wall (shortened: cs to depth)
                {'bx': width,     'by': cs,    'length': depth - cs,  'axis': 'Y', 'wall_type': right_type},
                {'bx': 0,         'by': depth, 'length': width,       'axis': 'X', 'wall_type': back_type},
                {'bx': 0,         'by': 0,     'length': depth,       'axis': 'Y', 'wall_type': left_type},
                # Angled wall: (width-cs, 0) to (width, cs)
                {'angled': True, 'start': (width - cs, 0), 'end': (width, cs), 'wall_type': front_type},
            ]
        elif cut_pos == 'BACK_LEFT':
            segs = [
                {'bx': 0,    'by': 0,         'length': width,       'axis': 'X', 'wall_type': front_type},
                {'bx': width,'by': 0,         'length': depth,       'axis': 'Y', 'wall_type': right_type},
                # Back wall (shortened: cs to width)
                {'bx': cs,   'by': depth,     'length': width - cs,  'axis': 'X', 'wall_type': back_type},
                # Left wall (shortened: 0 to depth-cs)
                {'bx': 0,    'by': 0,         'length': depth - cs,  'axis': 'Y', 'wall_type': left_type},
                # Angled wall: (0, depth-cs) to (cs, depth)
                {'angled': True, 'start': (0, depth - cs), 'end': (cs, depth), 'wall_type': back_type},
            ]
        elif cut_pos == 'BACK_RIGHT':
            segs = [
                {'bx': 0,         'by': 0,         'length': width,       'axis': 'X', 'wall_type': front_type},
                # Right wall (shortened: 0 to depth-cs)
                {'bx': width,     'by': 0,         'length': depth - cs,  'axis': 'Y', 'wall_type': right_type},
                # Back wall (shortened: 0 to width-cs)
                {'bx': 0,         'by': depth,     'length': width - cs,  'axis': 'X', 'wall_type': back_type},
                {'bx': 0,         'by': 0,         'length': depth,       'axis': 'Y', 'wall_type': left_type},
                # Angled wall: (width, depth-cs) to (width-cs, depth)
                {'angled': True, 'start': (width, depth - cs), 'end': (width - cs, depth), 'wall_type': back_type},
            ]
        else:
            # Fallback to rect
            return get_wall_segments('RECT', width, depth, wing_w, wing_d,
                                     front_type, back_type, left_type, right_type,
                                     wing_type, cut_size, cut_pos, floor_idx)

    else:
        # Unknown shape — fallback to rect
        return get_wall_segments('RECT', width, depth, wing_w, wing_d,
                                 front_type, back_type, left_type, right_type,
                                 wing_type, cut_size, cut_pos, floor_idx)

    # Mark all non-angled segments
    for seg in segs:
        if 'angled' not in seg:
            seg['angled'] = False

    return segs


def get_floor_slab_verts(shape, width, depth, wing_w, wing_d,
                          cut_size=3.0, cut_pos='FRONT_LEFT',
                          wing_pos='BACK_LEFT'):
    """
    Return a list of (x, y) tuples defining the floor slab polygon (CCW).
    Used for floor slabs and roof geometry.
    """
    if shape == 'RECT':
        return [(0, 0), (width, 0), (width, depth), (0, depth)]

    elif shape == 'L_SHAPE':
        ww = min(wing_w, width - 0.5)
        wd = wing_d
        if wing_pos == 'BACK_LEFT':
            return [
                (0, 0), (width, 0), (width, depth),
                (ww, depth), (ww, depth + wd), (0, depth + wd),
            ]
        elif wing_pos == 'BACK_RIGHT':
            return [
                (0, 0), (width, 0), (width, depth + wd),
                (width - ww, depth + wd), (width - ww, depth),
                (0, depth),
            ]
        elif wing_pos == 'FRONT_LEFT':
            return [
                (ww, 0), (width, 0), (width, depth),
                (0, depth), (0, -wd), (ww, -wd),
            ]
        elif wing_pos == 'FRONT_RIGHT':
            return [
                (0, 0), (width - ww, 0), (width - ww, -wd),
                (width, -wd), (width, depth), (0, depth),
            ]
        # Fallback
        return [
            (0, 0), (width, 0), (width, depth),
            (ww, depth), (ww, depth + wd), (0, depth + wd),
        ]

    elif shape == 'U_SHAPE':
        ww = min(wing_w, (width / 2.0) - 0.5)
        wd = wing_d
        return [
            (0, 0), (width, 0), (width, depth + wd),
            (width - ww, depth + wd), (width - ww, depth),
            (ww, depth), (ww, depth + wd), (0, depth + wd),
        ]

    elif shape == 'T_SHAPE':
        ww = min(wing_w, width - 1.0)
        wd = wing_d
        wl = (width - ww) / 2.0
        wr = wl + ww
        return [
            (0, 0), (width, 0), (width, depth),
            (wr, depth), (wr, depth + wd), (wl, depth + wd),
            (wl, depth), (0, depth),
        ]

    elif shape == 'CORNER_CUT':
        cs = min(cut_size, width - 0.5, depth - 0.5)
        if cut_pos == 'FRONT_LEFT':
            return [(cs, 0), (width, 0), (width, depth), (0, depth), (0, cs)]
        elif cut_pos == 'FRONT_RIGHT':
            return [(0, 0), (width - cs, 0), (width, cs), (width, depth), (0, depth)]
        elif cut_pos == 'BACK_LEFT':
            return [(0, 0), (width, 0), (width, depth), (cs, depth), (0, depth - cs)]
        elif cut_pos == 'BACK_RIGHT':
            return [(0, 0), (width, 0), (width, depth - cs), (width - cs, depth), (0, depth)]
        return [(0, 0), (width, 0), (width, depth), (0, depth)]

    return [(0, 0), (width, 0), (width, depth), (0, depth)]
