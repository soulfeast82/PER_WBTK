# World_Building_Toolkit/operators_pipes.py
# Pipe generation operators with wear & tear effects.

import bpy
import bmesh
import math
import random
from mathutils import Vector

from .config import Config
from .utils import Utils
from .operators_walkways import OP_BaseGenerator
from .geometry_pipes import GeometryPipes


# ================================================================== #
#  WEAR PRESET HELPERS                                                 #
# ================================================================== #

def _get_wear_values(preset, scene):
    """
    Return (dent_intensity, roughness, corrosion, num_drips) based on
    the chosen preset, or the manual slider values if preset == 'CUSTOM'.
    """
    if preset == 'CLEAN':
        return 0.0, 0.0, 0.0, 0
    elif preset == 'WEATHERED':
        return 0.3, 0.4, 0.0, 1
    elif preset == 'CORRODED':
        return 0.6, 0.7, 0.3, 2
    elif preset == 'BUSTED':
        return 1.0, 1.0, 0.6, 4
    else:  # CUSTOM
        return (
            getattr(scene, 'wbtk_pipe_dent_intensity', 0.3),
            getattr(scene, 'wbtk_pipe_roughness', 0.4),
            getattr(scene, 'wbtk_pipe_corrosion', 0.0),
            getattr(scene, 'wbtk_pipe_drip_count', 2),
        )


# ================================================================== #
#  OP: STRAIGHT PIPE                                                   #
# ================================================================== #

class OP_GenerateStraightPipe(OP_BaseGenerator):
    bl_idname = "wbtk.generate_straight_pipe"
    bl_label = "Generate Straight Pipe"
    bl_description = "Generate a straight pipe section with optional flanges, clamps, and wear effects"

    def execute(self, context):
        scene = context.scene

        # --- Read properties ---
        length      = getattr(scene, 'wbtk_pipe_length', 4.0)
        radius      = getattr(scene, 'wbtk_pipe_radius', 0.08)
        wall_thick  = getattr(scene, 'wbtk_pipe_wall_thickness', 0.01)
        segments    = getattr(scene, 'wbtk_pipe_segments', 16)
        subdivs     = getattr(scene, 'wbtk_pipe_subdivisions', 8)
        axis        = getattr(scene, 'wbtk_pipe_axis', 'X')

        add_flanges     = getattr(scene, 'wbtk_pipe_add_flanges', True)
        flange_spacing  = getattr(scene, 'wbtk_pipe_flange_spacing', 2.0)
        add_clamps      = getattr(scene, 'wbtk_pipe_add_clamps', True)
        clamp_spacing   = getattr(scene, 'wbtk_pipe_clamp_spacing', 1.5)

        wear_preset = getattr(scene, 'wbtk_pipe_wear_preset', 'WEATHERED')
        wear_seed   = getattr(scene, 'wbtk_pipe_wear_seed', 12345)

        dent_int, roughness, corrosion, drip_count = _get_wear_values(wear_preset, scene)

        # --- Validate ---
        if length <= 0:
            return self.report_warning("Pipe length must be > 0.")
        if radius <= wall_thick:
            return self.report_warning("Pipe radius must be greater than wall thickness.")

        # --- Build mesh ---
        master = Utils.create_master("Pipe_Straight")
        origin = Vector((0, 0, 0))

        # Main pipe body
        bm_pipe = bmesh.new()
        outer_rings, inner_rings = GeometryPipes.create_straight_pipe(
            bm_pipe, origin, length, radius, wall_thick,
            segments, subdivs, axis,
            cap_start=True, cap_end=True
        )

        # Flanges
        if add_flanges and flange_spacing > 0:
            flange_radius = radius * 1.35
            flange_width  = 0.04
            num_flanges = max(int(length / flange_spacing), 0)
            for fi in range(num_flanges + 1):
                t = fi * flange_spacing
                if t > length:
                    break
                if axis == 'X':
                    fc = Vector((t, 0, 0))
                elif axis == 'Y':
                    fc = Vector((0, t, 0))
                else:
                    fc = Vector((0, 0, t))
                GeometryPipes.add_flange(
                    bm_pipe, fc, radius, flange_radius, flange_width,
                    segments, axis
                )

        # Wear effects (applied to all verts in the pipe bmesh)
        GeometryPipes.apply_dents(bm_pipe, dent_int, wear_seed, axis)
        GeometryPipes.apply_surface_roughness(bm_pipe, roughness, wear_seed)

        # Corrosion holes (applied before converting to mesh)
        if corrosion > 0:
            GeometryPipes.apply_corrosion_holes(bm_pipe, corrosion, wear_seed)

        # Drips (random positions along pipe bottom)
        if drip_count > 0:
            rng = random.Random(wear_seed + 555)
            for _ in range(drip_count):
                t = rng.uniform(radius, length - radius)
                drip_len = rng.uniform(0.03, 0.12)
                drip_rad = rng.uniform(0.005, 0.015)
                if axis == 'X':
                    dc = Vector((t, 0, -radius))
                elif axis == 'Y':
                    dc = Vector((0, t, -radius))
                else:
                    dc = Vector((0, -radius, t))
                GeometryPipes.add_drip(bm_pipe, dc, drip_len, drip_rad)

        self.create_and_parent(bm_pipe, "Pipe_Straight_Mesh", origin,
                               Config.MATERIAL_PIPE, master)

        # Clamps (separate mesh for different material)
        if add_clamps and clamp_spacing > 0:
            bm_clamps = bmesh.new()
            clamp_thick = 0.015
            clamp_width = 0.06
            num_clamps = max(int(length / clamp_spacing), 0)
            for ci in range(num_clamps + 1):
                t = ci * clamp_spacing
                if t < radius or t > length - radius:
                    continue
                if axis == 'X':
                    cc = Vector((t, 0, 0))
                elif axis == 'Y':
                    cc = Vector((0, t, 0))
                else:
                    cc = Vector((0, 0, t))
                GeometryPipes.add_clamp(
                    bm_clamps, cc, radius, clamp_thick, clamp_width,
                    segments, axis
                )

            if bm_clamps.verts:
                self.create_and_parent(bm_clamps, "Pipe_Clamps", origin,
                                       Config.MATERIAL_PIPE_CLAMP, master)
            else:
                bm_clamps.free()

        self.report({'INFO'}, f"WBTK: Straight pipe generated ({length:.1f}m, seed {wear_seed})")
        return {'FINISHED'}


# ================================================================== #
#  OP: PIPE RUN (STRAIGHT + ELBOW + STRAIGHT)                         #
# ================================================================== #

class OP_GeneratePipeRun(OP_BaseGenerator):
    bl_idname = "wbtk.generate_pipe_run"
    bl_label = "Generate Pipe Run"
    bl_description = "Generate an L-shaped pipe run: straight section → 90° elbow → straight section"

    def execute(self, context):
        scene = context.scene

        length1     = getattr(scene, 'wbtk_pipe_run_leg1', 3.0)
        length2     = getattr(scene, 'wbtk_pipe_run_leg2', 2.0)
        radius      = getattr(scene, 'wbtk_pipe_radius', 0.08)
        wall_thick  = getattr(scene, 'wbtk_pipe_wall_thickness', 0.01)
        segments    = getattr(scene, 'wbtk_pipe_segments', 16)
        subdivs     = getattr(scene, 'wbtk_pipe_subdivisions', 8)
        bend_plane  = getattr(scene, 'wbtk_pipe_run_bend_plane', 'XZ')
        bend_radius = getattr(scene, 'wbtk_pipe_run_bend_radius', 0.2)

        wear_preset = getattr(scene, 'wbtk_pipe_wear_preset', 'WEATHERED')
        wear_seed   = getattr(scene, 'wbtk_pipe_wear_seed', 12345)
        dent_int, roughness, corrosion, drip_count = _get_wear_values(wear_preset, scene)

        add_flanges    = getattr(scene, 'wbtk_pipe_add_flanges', True)
        flange_spacing = getattr(scene, 'wbtk_pipe_flange_spacing', 2.0)

        if radius <= wall_thick:
            return self.report_warning("Pipe radius must be greater than wall thickness.")

        master = Utils.create_master("Pipe_Run")
        origin = Vector((0, 0, 0))

        bm = bmesh.new()

        # --- Leg 1: along X ---
        if length1 > 0:
            GeometryPipes.create_straight_pipe(
                bm, origin, length1, radius, wall_thick,
                segments, subdivs, 'X',
                cap_start=True, cap_end=False
            )

        # --- Elbow ---
        if bend_plane == 'XY':
            elbow_origin = Vector((length1, -bend_radius, 0))
            second_axis = 'Y'
        elif bend_plane == 'XZ':
            elbow_origin = Vector((length1, 0, -bend_radius))
            second_axis = 'Z'
        else:  # YZ
            elbow_origin = Vector((length1, 0, -bend_radius))
            second_axis = 'Z'

        bend_segs = max(segments // 2, 6)
        GeometryPipes.create_elbow(
            bm, elbow_origin, radius, wall_thick, segments,
            bend_radius, bend_segs, bend_plane, start_angle=0.0
        )

        # --- Leg 2: along second axis ---
        if length2 > 0:
            if bend_plane == 'XY':
                leg2_origin = Vector((length1 + bend_radius, -bend_radius + bend_radius, 0))
                # After 90° bend in XY: now running along +Y
                leg2_origin = Vector((length1 + bend_radius, 0, 0))
            elif bend_plane == 'XZ':
                leg2_origin = Vector((length1 + bend_radius, 0, 0))
            else:
                leg2_origin = Vector((length1 + bend_radius, 0, 0))

            GeometryPipes.create_straight_pipe(
                bm, leg2_origin, length2, radius, wall_thick,
                segments, subdivs, second_axis,
                cap_start=False, cap_end=True
            )

        # Flanges at connection points
        if add_flanges:
            flange_radius = radius * 1.35
            flange_width = 0.04
            # Flange at pipe start
            GeometryPipes.add_flange(bm, origin, radius, flange_radius,
                                     flange_width, segments, 'X')
            # Flange before elbow
            if length1 > 0:
                fc = Vector((length1, 0, 0))
                GeometryPipes.add_flange(bm, fc, radius, flange_radius,
                                         flange_width, segments, 'X')

        # Wear
        GeometryPipes.apply_dents(bm, dent_int, wear_seed, 'X')
        GeometryPipes.apply_surface_roughness(bm, roughness, wear_seed)
        if corrosion > 0:
            GeometryPipes.apply_corrosion_holes(bm, corrosion, wear_seed)

        # Drips
        if drip_count > 0:
            rng = random.Random(wear_seed + 333)
            total_len = length1 + length2
            for _ in range(drip_count):
                t = rng.uniform(0, length1)
                drip_len = rng.uniform(0.03, 0.12)
                drip_rad = rng.uniform(0.005, 0.015)
                dc = Vector((t, 0, -radius))
                GeometryPipes.add_drip(bm, dc, drip_len, drip_rad)

        self.create_and_parent(bm, "PipeRun_Mesh", origin,
                               Config.MATERIAL_PIPE, master)

        self.report({'INFO'}, f"WBTK: Pipe run generated (L1={length1:.1f}m, L2={length2:.1f}m)")
        return {'FINISHED'}


# ================================================================== #
#  OP: PIPE BUNDLE                                                     #
# ================================================================== #

class OP_GeneratePipeBundle(OP_BaseGenerator):
    bl_idname = "wbtk.generate_pipe_bundle"
    bl_label = "Generate Pipe Bundle"
    bl_description = "Generate a cluster of parallel pipes with random size variation and shared wear"

    def execute(self, context):
        scene = context.scene

        bundle_count = getattr(scene, 'wbtk_pipe_bundle_count', 3)
        length       = getattr(scene, 'wbtk_pipe_length', 4.0)
        radius       = getattr(scene, 'wbtk_pipe_radius', 0.08)
        wall_thick   = getattr(scene, 'wbtk_pipe_wall_thickness', 0.01)
        segments     = getattr(scene, 'wbtk_pipe_segments', 16)
        subdivs      = getattr(scene, 'wbtk_pipe_subdivisions', 8)
        axis         = getattr(scene, 'wbtk_pipe_axis', 'X')
        bundle_spread = getattr(scene, 'wbtk_pipe_bundle_spread', 0.3)

        wear_preset = getattr(scene, 'wbtk_pipe_wear_preset', 'WEATHERED')
        wear_seed   = getattr(scene, 'wbtk_pipe_wear_seed', 12345)
        dent_int, roughness, corrosion, drip_count = _get_wear_values(wear_preset, scene)

        add_flanges    = getattr(scene, 'wbtk_pipe_add_flanges', True)
        flange_spacing = getattr(scene, 'wbtk_pipe_flange_spacing', 2.0)

        if bundle_count < 1:
            return self.report_warning("Bundle count must be >= 1.")

        master = Utils.create_master("Pipe_Bundle")
        rng = random.Random(wear_seed + 42)

        for p_idx in range(bundle_count):
            # Random offset perpendicular to pipe axis
            if axis == 'X':
                off_y = rng.uniform(-bundle_spread, bundle_spread)
                off_z = rng.uniform(-bundle_spread * 0.5, bundle_spread * 0.5)
                p_origin = Vector((0, off_y, off_z))
            elif axis == 'Y':
                off_x = rng.uniform(-bundle_spread, bundle_spread)
                off_z = rng.uniform(-bundle_spread * 0.5, bundle_spread * 0.5)
                p_origin = Vector((off_x, 0, off_z))
            else:
                off_x = rng.uniform(-bundle_spread, bundle_spread)
                off_y = rng.uniform(-bundle_spread * 0.5, bundle_spread * 0.5)
                p_origin = Vector((off_x, off_y, 0))

            # Slight radius variation per pipe
            p_radius = radius * rng.uniform(0.7, 1.0)
            p_wall = min(wall_thick, p_radius * 0.4)

            bm = bmesh.new()

            GeometryPipes.create_straight_pipe(
                bm, p_origin, length, p_radius, p_wall,
                segments, subdivs, axis,
                cap_start=True, cap_end=True
            )

            # Flanges
            if add_flanges and flange_spacing > 0:
                flange_radius = p_radius * 1.35
                flange_width = 0.04
                num_flanges = max(int(length / flange_spacing), 0)
                for fi in range(num_flanges + 1):
                    t = fi * flange_spacing
                    if t > length:
                        break
                    if axis == 'X':
                        fc = Vector((p_origin.x + t, p_origin.y, p_origin.z))
                    elif axis == 'Y':
                        fc = Vector((p_origin.x, p_origin.y + t, p_origin.z))
                    else:
                        fc = Vector((p_origin.x, p_origin.y, p_origin.z + t))
                    GeometryPipes.add_flange(bm, fc, p_radius, flange_radius,
                                             flange_width, segments, axis)

            # Per-pipe wear with offset seed
            pipe_seed = wear_seed + p_idx * 137
            GeometryPipes.apply_dents(bm, dent_int, pipe_seed, axis)
            GeometryPipes.apply_surface_roughness(bm, roughness, pipe_seed)
            if corrosion > 0:
                GeometryPipes.apply_corrosion_holes(bm, corrosion, pipe_seed)

            # Drips
            if drip_count > 0:
                drng = random.Random(pipe_seed + 555)
                for _ in range(max(drip_count // bundle_count, 1)):
                    t = drng.uniform(p_radius, length - p_radius)
                    drip_len = drng.uniform(0.03, 0.12)
                    drip_rad = drng.uniform(0.005, 0.015)
                    if axis == 'X':
                        dc = Vector((t + p_origin.x, p_origin.y, p_origin.z - p_radius))
                    elif axis == 'Y':
                        dc = Vector((p_origin.x, t + p_origin.y, p_origin.z - p_radius))
                    else:
                        dc = Vector((p_origin.x, p_origin.y - p_radius, t + p_origin.z))
                    GeometryPipes.add_drip(bm, dc, drip_len, drip_rad)

            self.create_and_parent(bm, f"Bundle_Pipe_{p_idx:02d}", Vector((0, 0, 0)),
                                   Config.MATERIAL_PIPE, master)

        self.report({'INFO'}, f"WBTK: Pipe bundle ({bundle_count} pipes, seed {wear_seed})")
        return {'FINISHED'}


# ================================================================== #
#  OP: RANDOMIZE SEED (one-click re-roll for wear patterns)            #
# ================================================================== #

class OP_RandomizePipeSeed(OP_BaseGenerator):
    bl_idname = "wbtk.randomize_pipe_seed"
    bl_label = "Randomize Pipe Seed"
    bl_description = "Roll a new random seed for pipe wear patterns"

    def execute(self, context):
        context.scene.wbtk_pipe_wear_seed = random.randint(1, 99999)
        self.report({'INFO'}, f"WBTK: New pipe seed = {getattr(context.scene, 'wbtk_pipe_wear_seed', 12345)}")
        return {'FINISHED'}


# ================================================================== #
#  REGISTRATION                                                        #
# ================================================================== #

_classes_to_register = (
    OP_GenerateStraightPipe,
    OP_GeneratePipeRun,
    OP_GeneratePipeBundle,
    OP_RandomizePipeSeed,
)
