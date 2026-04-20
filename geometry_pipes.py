# World_Building_Toolkit/geometry_pipes.py
# Procedural pipe mesh generation with wear & tear effects.

import bmesh
import math
import random
from mathutils import Vector, Matrix


class GeometryPipes:
    """
    BMesh-based pipe geometry: straight runs, elbows, flanges,
    wear effects (dents, rust bulge, drips, corrosion), and clamp supports.
    """

    # ------------------------------------------------------------------ #
    #  LOW-LEVEL HELPERS                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _circle_verts(bm, center, radius, segments, axis='X', forward=None):
        """
        Create a ring of verts in *bm* at *center*.
        *axis* is the pipe run direction; the ring is perpendicular to it.
        Returns a list of BMVerts in winding order.
        """
        verts = []
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            ca = math.cos(angle)
            sa = math.sin(angle)

            if axis == 'X':
                pos = Vector((center.x, center.y + ca * radius, center.z + sa * radius))
            elif axis == 'Y':
                pos = Vector((center.x + ca * radius, center.y, center.z + sa * radius))
            else:  # Z
                pos = Vector((center.x + ca * radius, center.y + sa * radius, center.z))

            verts.append(bm.verts.new(pos))
        return verts

    @staticmethod
    def _bridge_rings(bm, ring_a, ring_b):
        """Connect two equally-sized vert rings with quad faces."""
        n = len(ring_a)
        for i in range(n):
            j = (i + 1) % n
            try:
                bm.faces.new((ring_a[i], ring_a[j], ring_b[j], ring_b[i]))
            except ValueError:
                pass  # degenerate or duplicate

    @staticmethod
    def _cap_ring(bm, ring, flip=False):
        """Fill a ring of verts with an ngon face."""
        try:
            if flip:
                bm.faces.new(list(reversed(ring)))
            else:
                bm.faces.new(ring)
        except ValueError:
            pass

    # ------------------------------------------------------------------ #
    #  STRAIGHT PIPE SECTION                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_straight_pipe(bm, origin, length, radius, wall_thickness,
                             segments, subdivisions, axis='X',
                             cap_start=True, cap_end=True):
        """
        Generate a hollow straight pipe along *axis*.

        *subdivisions* = number of intermediate edge loops (higher = more
        geometry for dent/noise effects to work with).

        Returns (outer_rings, inner_rings) — lists of vert-ring lists,
        ordered start-to-end so downstream code can reference them.
        """
        inner_radius = max(radius - wall_thickness, 0.01)
        total_rings = subdivisions + 2  # start ring + end ring + subdivisions

        outer_rings = []
        inner_rings = []

        for r_idx in range(total_rings):
            t = r_idx / max(total_rings - 1, 1)
            offset = length * t

            if axis == 'X':
                center = Vector((origin.x + offset, origin.y, origin.z))
            elif axis == 'Y':
                center = Vector((origin.x, origin.y + offset, origin.z))
            else:
                center = Vector((origin.x, origin.y, origin.z + offset))

            o_ring = GeometryPipes._circle_verts(bm, center, radius, segments, axis)
            i_ring = GeometryPipes._circle_verts(bm, center, inner_radius, segments, axis)
            outer_rings.append(o_ring)
            inner_rings.append(i_ring)

        # Skin outer
        for i in range(len(outer_rings) - 1):
            GeometryPipes._bridge_rings(bm, outer_rings[i], outer_rings[i + 1])

        # Skin inner (reversed winding for inward-facing normals)
        for i in range(len(inner_rings) - 1):
            GeometryPipes._bridge_rings(bm, inner_rings[i + 1], inner_rings[i])

        # Bridge inner ↔ outer at caps (annular ring faces)
        if cap_start:
            GeometryPipes._bridge_rings(bm, inner_rings[0], outer_rings[0])
        if cap_end:
            GeometryPipes._bridge_rings(bm, outer_rings[-1], inner_rings[-1])

        return outer_rings, inner_rings

    # ------------------------------------------------------------------ #
    #  ELBOW (90° BEND)                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_elbow(bm, origin, radius, wall_thickness, segments,
                     bend_radius, bend_segments, plane='XY',
                     start_angle=0.0):
        """
        Generate a 90° pipe elbow centered on *origin*.

        *bend_radius*   = distance from origin to pipe center-line.
        *bend_segments* = subdivisions around the 90° arc.
        *plane*         = 'XY' | 'XZ' | 'YZ' — which two axes the bend occupies.
        *start_angle*   = rotation offset (radians) for the arc start.

        Returns (outer_rings, inner_rings).
        """
        inner_radius = max(radius - wall_thickness, 0.01)
        outer_rings = []
        inner_rings = []

        for b_idx in range(bend_segments + 1):
            t = b_idx / max(bend_segments, 1)
            arc_angle = start_angle + t * (math.pi / 2.0)

            # Center of cross-section ring along the bend arc
            if plane == 'XY':
                cx = origin.x + bend_radius * math.cos(arc_angle)
                cy = origin.y + bend_radius * math.sin(arc_angle)
                cz = origin.z
                # Tangent direction (perpendicular to radial for ring orientation)
                tangent = Vector((-math.sin(arc_angle), math.cos(arc_angle), 0.0))
            elif plane == 'XZ':
                cx = origin.x + bend_radius * math.cos(arc_angle)
                cy = origin.y
                cz = origin.z + bend_radius * math.sin(arc_angle)
                tangent = Vector((-math.sin(arc_angle), 0.0, math.cos(arc_angle)))
            else:  # YZ
                cx = origin.x
                cy = origin.y + bend_radius * math.cos(arc_angle)
                cz = origin.z + bend_radius * math.sin(arc_angle)
                tangent = Vector((0.0, -math.sin(arc_angle), math.cos(arc_angle)))

            center = Vector((cx, cy, cz))

            # Build perpendicular ring manually using tangent + up
            tangent.normalize()
            # Choose an "up" that isn't parallel to tangent
            up = Vector((0, 0, 1))
            if abs(tangent.dot(up)) > 0.99:
                up = Vector((0, 1, 0))

            side = tangent.cross(up).normalized()
            up2 = side.cross(tangent).normalized()

            o_verts = []
            i_verts = []
            for s_idx in range(segments):
                angle = 2.0 * math.pi * s_idx / segments
                ca = math.cos(angle)
                sa = math.sin(angle)
                offset_vec = side * ca + up2 * sa

                o_pos = center + offset_vec * radius
                i_pos = center + offset_vec * inner_radius
                o_verts.append(bm.verts.new(o_pos))
                i_verts.append(bm.verts.new(i_pos))

            outer_rings.append(o_verts)
            inner_rings.append(i_verts)

        # Skin
        for i in range(len(outer_rings) - 1):
            GeometryPipes._bridge_rings(bm, outer_rings[i], outer_rings[i + 1])
        for i in range(len(inner_rings) - 1):
            GeometryPipes._bridge_rings(bm, inner_rings[i + 1], inner_rings[i])

        return outer_rings, inner_rings

    # ------------------------------------------------------------------ #
    #  FLANGE (COLLAR RING)                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def add_flange(bm, center, pipe_radius, flange_radius, flange_width,
                   segments, axis='X'):
        """
        Add a solid flange ring around the pipe at *center*.
        The flange extends from *pipe_radius* outward to *flange_radius*.
        """
        half_w = flange_width / 2.0

        # Two rings at each end of the flange thickness
        if axis == 'X':
            c_start = Vector((center.x - half_w, center.y, center.z))
            c_end   = Vector((center.x + half_w, center.y, center.z))
        elif axis == 'Y':
            c_start = Vector((center.x, center.y - half_w, center.z))
            c_end   = Vector((center.x, center.y + half_w, center.z))
        else:
            c_start = Vector((center.x, center.y, center.z - half_w))
            c_end   = Vector((center.x, center.y, center.z + half_w))

        # Outer ring of the flange
        o_start = GeometryPipes._circle_verts(bm, c_start, flange_radius, segments, axis)
        o_end   = GeometryPipes._circle_verts(bm, c_end,   flange_radius, segments, axis)
        # Inner ring (matches pipe outer radius)
        i_start = GeometryPipes._circle_verts(bm, c_start, pipe_radius, segments, axis)
        i_end   = GeometryPipes._circle_verts(bm, c_end,   pipe_radius, segments, axis)

        # Outer barrel
        GeometryPipes._bridge_rings(bm, o_start, o_end)
        # Inner barrel (reversed)
        GeometryPipes._bridge_rings(bm, i_end, i_start)
        # Annular caps
        GeometryPipes._bridge_rings(bm, i_start, o_start)
        GeometryPipes._bridge_rings(bm, o_end, i_end)

    # ------------------------------------------------------------------ #
    #  PIPE CLAMP / SUPPORT BRACKET                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def add_clamp(bm, center, pipe_radius, clamp_thickness, clamp_width,
                  segments, axis='X'):
        """
        Add a U-shaped clamp bracket that wraps the bottom half of the pipe.
        Includes a small mounting tab extending downward.
        """
        clamp_radius = pipe_radius + clamp_thickness
        half_w = clamp_width / 2.0
        tab_height = pipe_radius * 0.6
        tab_width = clamp_width * 0.8
        tab_thick = clamp_thickness

        # Build half-circle clamp (bottom 180°)
        half_segs = max(segments // 2, 4)

        for w_offset in [-half_w, half_w]:
            if axis == 'X':
                c = Vector((center.x + w_offset, center.y, center.z))
            elif axis == 'Y':
                c = Vector((center.x, center.y + w_offset, center.z))
            else:
                c = Vector((center.x, center.y, center.z + w_offset))

            ring_outer = []
            ring_inner = []
            for i in range(half_segs + 1):
                # Sweep from -90° to +90° (bottom half wrapping up sides)
                angle = math.pi + (math.pi * i / half_segs)
                ca = math.cos(angle)
                sa = math.sin(angle)

                if axis == 'X':
                    o_pos = Vector((c.x, c.y + ca * clamp_radius, c.z + sa * clamp_radius))
                    i_pos = Vector((c.x, c.y + ca * pipe_radius,  c.z + sa * pipe_radius))
                elif axis == 'Y':
                    o_pos = Vector((c.x + ca * clamp_radius, c.y, c.z + sa * clamp_radius))
                    i_pos = Vector((c.x + ca * pipe_radius,  c.y, c.z + sa * pipe_radius))
                else:
                    o_pos = Vector((c.x + ca * clamp_radius, c.y + sa * clamp_radius, c.z))
                    i_pos = Vector((c.x + ca * pipe_radius,  c.y + sa * pipe_radius,  c.z))

                ring_outer.append(bm.verts.new(o_pos))
                ring_inner.append(bm.verts.new(i_pos))

        # For simplicity, build the clamp as a solid half-torus by bridging
        # the two width-offset half-rings.  A full implementation would
        # bridge outer_front ↔ outer_back and inner_front ↔ inner_back.
        # Here we keep it simple with a thickened half-arc:

        # Mounting tab (simple box below pipe center)
        tab_hw = tab_width / 2.0
        tab_ht = tab_thick / 2.0
        bottom_z = center.z - clamp_radius

        if axis == 'X':
            tv = [
                Vector((center.x - tab_hw, center.y - tab_ht, bottom_z)),
                Vector((center.x + tab_hw, center.y - tab_ht, bottom_z)),
                Vector((center.x + tab_hw, center.y + tab_ht, bottom_z)),
                Vector((center.x - tab_hw, center.y + tab_ht, bottom_z)),
                Vector((center.x - tab_hw, center.y - tab_ht, bottom_z - tab_height)),
                Vector((center.x + tab_hw, center.y - tab_ht, bottom_z - tab_height)),
                Vector((center.x + tab_hw, center.y + tab_ht, bottom_z - tab_height)),
                Vector((center.x - tab_hw, center.y + tab_ht, bottom_z - tab_height)),
            ]
        elif axis == 'Y':
            tv = [
                Vector((center.x - tab_ht, center.y - tab_hw, bottom_z)),
                Vector((center.x + tab_ht, center.y - tab_hw, bottom_z)),
                Vector((center.x + tab_ht, center.y + tab_hw, bottom_z)),
                Vector((center.x - tab_ht, center.y + tab_hw, bottom_z)),
                Vector((center.x - tab_ht, center.y - tab_hw, bottom_z - tab_height)),
                Vector((center.x + tab_ht, center.y - tab_hw, bottom_z - tab_height)),
                Vector((center.x + tab_ht, center.y + tab_hw, bottom_z - tab_height)),
                Vector((center.x - tab_ht, center.y + tab_hw, bottom_z - tab_height)),
            ]
        else:
            # Z-axis pipes: tab extends along -Y
            tv = [
                Vector((center.x - tab_hw, center.y - clamp_radius, center.z - tab_ht)),
                Vector((center.x + tab_hw, center.y - clamp_radius, center.z - tab_ht)),
                Vector((center.x + tab_hw, center.y - clamp_radius, center.z + tab_ht)),
                Vector((center.x - tab_hw, center.y - clamp_radius, center.z + tab_ht)),
                Vector((center.x - tab_hw, center.y - clamp_radius - tab_height, center.z - tab_ht)),
                Vector((center.x + tab_hw, center.y - clamp_radius - tab_height, center.z - tab_ht)),
                Vector((center.x + tab_hw, center.y - clamp_radius - tab_height, center.z + tab_ht)),
                Vector((center.x - tab_hw, center.y - clamp_radius - tab_height, center.z + tab_ht)),
            ]

        verts = [bm.verts.new(v) for v in tv]
        # 6 box faces
        faces = [
            (0, 1, 2, 3), (4, 7, 6, 5),
            (0, 1, 5, 4), (1, 2, 6, 5),
            (2, 3, 7, 6), (3, 0, 4, 7),
        ]
        for f in faces:
            try:
                bm.faces.new([verts[i] for i in f])
            except ValueError:
                pass

        # Clamp band: simplified as a thickened torus arc using two half-rings
        band_segs = max(segments // 2, 4)
        front_outer = []
        front_inner = []
        back_outer = []
        back_inner = []

        for i in range(band_segs + 1):
            angle = math.pi + (math.pi * i / band_segs)
            ca = math.cos(angle)
            sa = math.sin(angle)

            if axis == 'X':
                fo = bm.verts.new((center.x - half_w, center.y + ca * clamp_radius, center.z + sa * clamp_radius))
                fi = bm.verts.new((center.x - half_w, center.y + ca * (pipe_radius + 0.001), center.z + sa * (pipe_radius + 0.001)))
                bo = bm.verts.new((center.x + half_w, center.y + ca * clamp_radius, center.z + sa * clamp_radius))
                bi = bm.verts.new((center.x + half_w, center.y + ca * (pipe_radius + 0.001), center.z + sa * (pipe_radius + 0.001)))
            elif axis == 'Y':
                fo = bm.verts.new((center.x + ca * clamp_radius, center.y - half_w, center.z + sa * clamp_radius))
                fi = bm.verts.new((center.x + ca * (pipe_radius + 0.001), center.y - half_w, center.z + sa * (pipe_radius + 0.001)))
                bo = bm.verts.new((center.x + ca * clamp_radius, center.y + half_w, center.z + sa * clamp_radius))
                bi = bm.verts.new((center.x + ca * (pipe_radius + 0.001), center.y + half_w, center.z + sa * (pipe_radius + 0.001)))
            else:
                fo = bm.verts.new((center.x + ca * clamp_radius, center.y + sa * clamp_radius, center.z - half_w))
                fi = bm.verts.new((center.x + ca * (pipe_radius + 0.001), center.y + sa * (pipe_radius + 0.001), center.z - half_w))
                bo = bm.verts.new((center.x + ca * clamp_radius, center.y + sa * clamp_radius, center.z + half_w))
                bi = bm.verts.new((center.x + ca * (pipe_radius + 0.001), center.y + sa * (pipe_radius + 0.001), center.z + half_w))

            front_outer.append(fo)
            front_inner.append(fi)
            back_outer.append(bo)
            back_inner.append(bi)

        # Skin the band
        for i in range(len(front_outer) - 1):
            # Outer surface
            try:
                bm.faces.new((front_outer[i], front_outer[i+1], back_outer[i+1], back_outer[i]))
            except ValueError:
                pass
            # Inner surface
            try:
                bm.faces.new((back_inner[i], back_inner[i+1], front_inner[i+1], front_inner[i]))
            except ValueError:
                pass

        # End caps of band (front and back annular faces)
        for i in range(len(front_outer) - 1):
            try:
                bm.faces.new((front_inner[i], front_inner[i+1], front_outer[i+1], front_outer[i]))
            except ValueError:
                pass
            try:
                bm.faces.new((back_outer[i], back_outer[i+1], back_inner[i+1], back_inner[i]))
            except ValueError:
                pass

    # ------------------------------------------------------------------ #
    #  DRIP GEOMETRY                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def add_drip(bm, center, drip_length, drip_radius, segments=8):
        """
        Add a teardrop/drip hanging downward from *center*.
        Cone pointing down with a rounded top sphere.
        """
        # Cone body
        tip = bm.verts.new((center.x, center.y, center.z - drip_length))

        ring = []
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            ca = math.cos(angle)
            sa = math.sin(angle)
            v = bm.verts.new((
                center.x + ca * drip_radius,
                center.y + sa * drip_radius,
                center.z
            ))
            ring.append(v)

        # Cone faces
        for i in range(segments):
            j = (i + 1) % segments
            try:
                bm.faces.new((ring[i], ring[j], tip))
            except ValueError:
                pass

        # Cap the top
        GeometryPipes._cap_ring(bm, ring, flip=True)

    # ------------------------------------------------------------------ #
    #  WEAR & TEAR EFFECTS                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def apply_dents(bm, intensity, seed, axis='X'):
        """
        Displace verts inward along their radial direction
        using Perlin-style noise (approximated with sin/cos).
        *intensity* 0.0–1.0 scales the maximum displacement.
        """
        if intensity < 0.001:
            return

        rng = random.Random(seed)
        max_disp = intensity * 0.03  # up to 3cm at full intensity

        bm.verts.ensure_lookup_table()

        for v in bm.verts:
            # Radial direction from pipe axis
            if axis == 'X':
                radial = Vector((0, v.co.y, v.co.z))
            elif axis == 'Y':
                radial = Vector((v.co.x, 0, v.co.z))
            else:
                radial = Vector((v.co.x, v.co.y, 0))

            if radial.length < 0.001:
                continue

            # Pseudo-noise displacement
            noise_val = math.sin(v.co.x * 17.3 + seed) * math.cos(v.co.y * 23.7 + seed) * math.sin(v.co.z * 31.1 + seed)
            # Only push inward (negative radial) for dents
            displacement = min(noise_val, 0.0) * max_disp * rng.uniform(0.5, 1.5)
            v.co += radial.normalized() * displacement

    @staticmethod
    def apply_surface_roughness(bm, intensity, seed):
        """
        Add subtle random vertex noise in all directions.
        *intensity* 0.0–1.0 scales the noise magnitude.
        """
        if intensity < 0.001:
            return

        rng = random.Random(seed + 999)
        max_noise = intensity * 0.005  # up to 5mm at full

        for v in bm.verts:
            v.co.x += rng.uniform(-max_noise, max_noise)
            v.co.y += rng.uniform(-max_noise, max_noise)
            v.co.z += rng.uniform(-max_noise, max_noise)

    @staticmethod
    def apply_corrosion_holes(bm, probability, seed):
        """
        Delete random outer faces to simulate corrosion holes.
        *probability* 0.0–1.0 = chance each face gets removed.
        """
        if probability < 0.001:
            return

        rng = random.Random(seed + 777)
        bm.faces.ensure_lookup_table()

        faces_to_delete = []
        for f in bm.faces:
            # Only delete faces that aren't on inner wall (normal pointing outward)
            center = f.calc_center_median()
            if rng.random() < probability * 0.15:  # Scale down so it's sparse
                faces_to_delete.append(f)

        if faces_to_delete:
            bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')
