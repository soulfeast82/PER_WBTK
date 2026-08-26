# World_Building_Toolkit/operators_props.py

import bpy
import bmesh
import random
import math
from mathutils import Vector

# Import local modules
from .config import Config
from .utils import Utils
# Import Base Class
from .operators_walkways import OP_BaseGenerator
# GeometryBuildings likely not needed for these props
# from .geometry_buildings import GeometryBuildings

# === Prop Operators ===

class OP_GenerateCrate(OP_BaseGenerator):
    bl_idname = "wbtk.generate_crate" # Use wbtk prefix
    bl_label = "Generate Crate"
    bl_description = "Generate a modular crate with optional inset panels"
    # bl_options = {'REGISTER', 'UNDO'} # Inherited

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        width = scene.wbtk_crate_width
        depth = scene.wbtk_crate_depth
        height = scene.wbtk_crate_height
        inset_amount = scene.wbtk_crate_inset_amount
        add_insets = scene.wbtk_crate_add_insets

        master = Utils.create_master("Crate")
        bm = bmesh.new()

        # Create base cube vertices
        v = [ Vector((0, 0, 0)), Vector((width, 0, 0)), Vector((width, depth, 0)), Vector((0, depth, 0)),
              Vector((0, 0, height)), Vector((width, 0, height)), Vector((width, depth, height)), Vector((0, depth, height)) ]
        verts = [bm.verts.new(coord) for coord in v]

        # Create faces
        try:
            bm.faces.new((verts[0], verts[1], verts[2], verts[3])) # Bottom -Y
            bm.faces.new((verts[7], verts[6], verts[5], verts[4])) # Top +Y (Reversed order for normal)
            bm.faces.new((verts[0], verts[1], verts[5], verts[4])) # Front +X
            bm.faces.new((verts[1], verts[2], verts[6], verts[5])) # Right +Y
            bm.faces.new((verts[3], verts[2], verts[6], verts[7])) # Back -X (Reversed order for normal)
            bm.faces.new((verts[0], verts[3], verts[7], verts[4])) # Left -Y (Reversed order for normal)
        except ValueError: pass # Ignore potential degenerate faces

        # Inset side faces (excluding top and bottom)
        if add_insets and inset_amount > 0.001:
            # Select side faces (normals are primarily X or Y)
            side_faces = [f for f in bm.faces if abs(f.normal.z) < 0.5]
            if side_faces:
                try:
                    # Inset faces individually
                    inset_result = bmesh.ops.inset_individual(bm, faces=side_faces, thickness=inset_amount, use_even_offset=True)
                    # Push each inset face inward along ITS OWN normal
                    for face in inset_result['faces']:
                        face_normal = face.normal.copy()
                        push_vec = face_normal * (-inset_amount * 0.5)
                        bmesh.ops.translate(bm, verts=list(face.verts), vec=push_vec)
                except Exception as e:
                    print(f"Warning: Crate inset/extrude failed: {e}")


        # Use create_and_parent helper
        # Use a generic wood material for crates, defined in Config
        self.create_and_parent(bm, "Crate", Vector((0,0,0)), Config.MATERIAL_PROP_WOOD, master)

        return {'FINISHED'}


class OP_GenerateBarrel(OP_BaseGenerator):
    bl_idname = "wbtk.generate_barrel" # Use wbtk prefix
    bl_label = "Generate Barrel (Basic)"
    bl_description = "Generate a basic barrel with simple ribs (Use Metal Barrel for better results)"
    # bl_options = {'REGISTER', 'UNDO'} # Inherited

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        radius = scene.wbtk_barrel_radius
        height = scene.wbtk_barrel_height
        segments = scene.wbtk_barrel_sides
        rib_count = scene.wbtk_barrel_ribs
        rib_width = scene.wbtk_barrel_rib_width # Note: Width property wasn't actually used in original bevel
        rib_extrude = scene.wbtk_barrel_rib_extrude

        master = Utils.create_master("Barrel_Basic")

        # Create Cylinder Primitive using bpy.ops
        # This is less ideal than pure bmesh but matches the original code
        try:
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=segments, radius=radius, depth=height, location=(0, 0, height/2.0), # Center origin
                end_fill_type='NGON', calc_uvs=True )
            barrel_obj = context.active_object
            if not barrel_obj: raise RuntimeError("Cylinder creation failed.")
            barrel_obj.name = "Barrel_Basic_Mesh"
        except Exception as e:
            return self.report_error(f"Failed to create base cylinder: {e}")

        # --- Modify with BMesh ---
        bm = bmesh.new()
        bm.from_mesh(barrel_obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        # Add horizontal loops for ribs (more reliable than finding existing edges)
        if rib_count > 0:
            # Select vertical edges only
            vertical_edges = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > height * 0.9]
            if vertical_edges:
                try:
                    bmesh.ops.subdivide_edges(bm, edges=vertical_edges, cuts=rib_count + 1)
                except Exception as e:
                    print(f"Warning: Barrel loop cut failed: {e}")

        # Find horizontal edge loops near rib positions to bevel
        rib_edges_to_bevel = []
        if rib_count > 0:
            step = height / (rib_count + 1)
            for edge in bm.edges:
                if not edge.is_boundary and abs(edge.verts[0].co.z - edge.verts[1].co.z) < 0.01: # Horizontal edge
                    mid_z = (edge.verts[0].co.z + edge.verts[1].co.z) * 0.5
                    for i in range(1, rib_count + 1):
                        target_z = -height / 2 + i * step # Target Z relative to bottom at -h/2
                        if abs(mid_z - target_z) < step * 0.1: # Tolerance based on spacing
                            rib_edges_to_bevel.append(edge)
                            break # Found loop for this edge

        # Bevel the selected rib edges
        if rib_edges_to_bevel:
            try:
                bmesh.ops.bevel( bm, geom=rib_edges_to_bevel, offset=rib_extrude * 0.5, # Bevel amount
                                 offset_type='OFFSET', segments=2, profile=0.5, affect='EDGES')
            except Exception as e:
                print(f"Warning: Barrel rib bevel failed: {e}")

        # --- Slight Bulge (Optional) ---
        # Original bulge logic - keep if desired
        for v in bm.verts:
            z_norm = (v.co.z + height / 2.0) / height # Normalize Z from 0 to 1
            bulge_factor = 1.0 + (math.sin(z_norm * math.pi) * 0.05) # Gentle sine bulge
            v.co.xy *= bulge_factor # Scale X and Y

        # --- Update Mesh and Finalize ---
        bm.to_mesh(barrel_obj.data)
        bm.free()
        barrel_obj.data.update()

        # Add material using Utils
        mat = Utils.get_or_create_material(Config.MATERIAL_PROP_WOOD) # Wood for basic barrel?
        if mat and len(barrel_obj.data.materials) == 0:
            barrel_obj.data.materials.append(mat)
        elif mat:
            barrel_obj.data.materials[0] = mat

        # Parent to master
        barrel_obj.parent = master
        # Add collider
        Utils.add_ucx_collider(barrel_obj, master)
        # Ensure object is placed at world origin (cylinder was created centered)
        barrel_obj.location = (0,0,0)


        return {'FINISHED'}


class OP_GenerateMetalBarrel(OP_BaseGenerator):
    bl_idname = "wbtk.generate_metal_barrel" # Use wbtk prefix
    bl_label = "Generate Metal Barrel"
    bl_description = "Generate a metal barrel with cleaner ribs and UVs"
    # bl_options = {'REGISTER', 'UNDO'} # Inherited

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        radius = scene.wbtk_barrel_radius
        height = scene.wbtk_barrel_height
        segments = scene.wbtk_barrel_sides
        # Fixed rib parameters for metal barrel style
        rib_count = 4
        rib_extrude_bevel = 0.015 # Bevel amount for cleaner ribs
        rib_scale_out = 1.02 # How much rib verts are scaled out

        master = Utils.create_master("MetalBarrel")

        # --- Create Cylinder using bpy.ops ---
        try:
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=segments, radius=radius, depth=height, location=(0, 0, height/2.0),
                end_fill_type='NGON', calc_uvs=True)
            barrel_obj = context.active_object
            if not barrel_obj: raise RuntimeError("Cylinder creation failed.")
            barrel_obj.name = "MetalBarrel_Mesh"
        except Exception as e:
            return self.report_error(f"Failed to create base cylinder: {e}")

        # --- Add Loop Cuts using bpy.ops in Edit Mode ---
        try:
            bpy.context.view_layer.objects.active = barrel_obj
            bpy.ops.object.mode_set(mode='EDIT')
            # Use loopcut operator directly
            bpy.ops.mesh.loopcut_slide(MESH_OT_loopcut={"number_cuts": rib_count*2 + 2, "smoothness": 0, "falloff":'INVERSE_SQUARE', "edge_index":2, "mesh_select_mode_init":(True, False, False)}, TRANSFORM_OT_edge_slide={"value":0})
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception as e:
            print(f"Warning: Barrel loop cut failed: {e}")
            # Ensure exit edit mode
            if barrel_obj.mode == 'EDIT': bpy.ops.object.mode_set(mode='OBJECT')


        # --- Modify with BMesh ---
        bm = bmesh.new(); bm.from_mesh(barrel_obj.data)
        bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()

        # Find horizontal edge loops to act as centers for bevelled ribs
        rib_center_edges = []
        step = height / (rib_count + 1)
        z_coords_found = set() # Avoid duplicates if loops overlap slightly

        for edge in bm.edges:
            if not edge.is_boundary and abs(edge.verts[0].co.z - edge.verts[1].co.z) < 0.01:
                mid_z = (edge.verts[0].co.z + edge.verts[1].co.z) * 0.5
                for i in range(1, rib_count + 1):
                    target_z = -height / 2.0 + i * step
                    if abs(mid_z - target_z) < step * 0.1: # Tolerance
                        # Check if we already added a loop very close to this Z
                        is_duplicate = False
                        for found_z in z_coords_found:
                            if abs(mid_z - found_z) < 0.001:
                                is_duplicate = True; break
                        if not is_duplicate:
                            rib_center_edges.append(edge)
                            z_coords_found.add(mid_z)
                        break # Move to next edge once a loop is found for it


        # Bevel the rib center edges
        if rib_center_edges:
            try:
                bevel_result = bmesh.ops.bevel(bm, geom=rib_center_edges, offset=rib_extrude_bevel,
                                               offset_type='OFFSET', segments=4, profile=0.6, affect='EDGES')
                # Slightly scale out the vertices created by the bevel for a more pronounced rib
                # Need to carefully select only the vertices pushed outwards by the bevel
                verts_to_scale = set()
                if 'edges' in bevel_result: # Edges created between the new loops
                    for e in bevel_result['edges']:
                        verts_to_scale.update(e.verts)
                # Filter verts_to_scale to only include those further from Z-axis
                # This is complex, alternative: scale ALL bevel verts slightly?
                center_xy = Vector((0,0))
                for v in list(verts_to_scale): # Iterate over copy
                    if (v.co.xy - center_xy).length < radius * 0.99: # If vertex is too close to center, don't scale
                        verts_to_scale.remove(v)

                # Apply scaling
                if verts_to_scale:
                    bmesh.ops.scale(bm, verts=list(verts_to_scale), vec=(rib_scale_out, rib_scale_out, 1.0))

            except Exception as e:
                print(f"Warning: Metal barrel rib bevel/scale failed: {e}")

        # --- Update Mesh, UVs, Shading, Material ---
        bm.to_mesh(barrel_obj.data); bm.free(); barrel_obj.data.update()

        # UV Unwrap using Utils helper within bm_to_obj is preferred, but if done here:
        # try:
        #     Utils.smart_uv_unwrap(barrel_obj) # Assuming helper exists
        # except Exception as e: print(f"Warning: Metal Barrel UV unwrap failed: {e}")

        # Auto Smooth (Blender 5.0 compatible)
        if hasattr(barrel_obj.data, 'set_sharp_from_angle'):
            barrel_obj.data.set_sharp_from_angle(angle=math.radians(60))
        barrel_obj.data.polygons.foreach_set("use_smooth", [True] * len(barrel_obj.data.polygons))
        barrel_obj.data.update()

        # Assign Material
        mat = Utils.get_or_create_material(Config.MATERIAL_PROP_METAL)
        if mat and len(barrel_obj.data.materials) == 0: barrel_obj.data.materials.append(mat)
        elif mat: barrel_obj.data.materials[0] = mat

        # --- Randomization ---
        # Apply random scale/rotation before parenting
        if random.random() < 0.8: barrel_obj.scale.z *= random.uniform(0.95, 1.05)
        if random.random() < 0.2: # Broken barrel effect
            barrel_obj.scale.x *= random.uniform(0.85, 1.05)
            barrel_obj.scale.y *= random.uniform(0.85, 1.05)
            barrel_obj.rotation_euler.x += random.uniform(math.radians(-5), math.radians(5))
            barrel_obj.rotation_euler.y += random.uniform(math.radians(-5), math.radians(5))

        # --- Finalize ---
        barrel_obj.parent = master
        Utils.add_ucx_collider(barrel_obj, master)
        barrel_obj.location = (0,0,0) # Reset location after potential centering adjustments

        return {'FINISHED'}


class OP_GenerateVendorStall(OP_BaseGenerator):
    bl_idname = "wbtk.generate_vendor_stall" # Use wbtk prefix
    bl_label = "Generate Vendor Stall"
    bl_description = "Generate a modular vendor stall with poles and angled roof"
    # bl_options = {'REGISTER', 'UNDO'} # Inherited

    # Keep pole generation as a helper specific to this operator for now
    def _add_pole(self, bm, base_pos_tuple, pole_height, pole_thickness=0.05):
        """ Helper to add a simple square pole to the BMesh. """
        x, y, z = base_pos_tuple
        pt = pole_thickness / 2.0
        v = [ Vector((x - pt, y - pt, z)), Vector((x + pt, y - pt, z)),
              Vector((x + pt, y + pt, z)), Vector((x - pt, y + pt, z)),
              Vector((x - pt, y - pt, z + pole_height)), Vector((x + pt, y - pt, z + pole_height)),
              Vector((x + pt, y + pt, z + pole_height)), Vector((x - pt, y + pt, z + pole_height)) ]
        verts = [bm.verts.new(coord) for coord in v]
        try: # Add faces
            bm.faces.new((verts[0], verts[1], verts[2], verts[3]))
            bm.faces.new((verts[7], verts[6], verts[5], verts[4]))
            bm.faces.new((verts[0], verts[1], verts[5], verts[4]))
            bm.faces.new((verts[1], verts[2], verts[6], verts[5]))
            bm.faces.new((verts[2], verts[3], verts[7], verts[6]))
            bm.faces.new((verts[3], verts[0], verts[4], verts[7]))
        except ValueError: pass

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        width = scene.wbtk_stall_width
        depth = scene.wbtk_stall_depth
        height = scene.wbtk_stall_height # Back post height
        add_table = scene.wbtk_stall_add_table
        slope_amount = scene.wbtk_stall_slope_amount

        master = Utils.create_master("VendorStall")
        origin = Vector((0,0,0)) # Generate relative to origin

        # --- Poles ---
        bm_poles = bmesh.new()
        pole_thickness = 0.05 # Make configurable?
        self._add_pole(bm_poles, (0, 0, 0), height, pole_thickness)                         # Back Left
        self._add_pole(bm_poles, (width, 0, 0), height, pole_thickness)                     # Back Right
        self._add_pole(bm_poles, (width, depth, 0), height - slope_amount, pole_thickness)  # Front Right
        self._add_pole(bm_poles, (0, depth, 0), height - slope_amount, pole_thickness)      # Front Left
        self.create_and_parent(bm_poles, "Stall_Poles", origin, Config.MATERIAL_PROP_WOOD, master)

        # --- Roof Tarp ---
        bm_roof = bmesh.new()
        v0 = bm_roof.verts.new((0, 0, height))
        v1 = bm_roof.verts.new((width, 0, height))
        v2 = bm_roof.verts.new((width, depth, height - slope_amount))
        v3 = bm_roof.verts.new((0, depth, height - slope_amount))
        try: bm_roof.faces.new((v0, v1, v2, v3))
        except ValueError: pass
        self.create_and_parent(bm_roof, "Stall_Tarp", origin, Config.MATERIAL_PROP_WOOD, master) # Wood or Fabric?

        # --- Optional Table ---
        if add_table:
            bm_table = bmesh.new()
            table_height = min(height - slope_amount, height) * 0.5 # Place table halfway up shortest posts
            table_thickness = 0.05
            # Create simple box for table
            v_t = [ Vector((0, 0, table_height)), Vector((width, 0, table_height)),
                    Vector((width, depth, table_height)), Vector((0, depth, table_height)),
                    Vector((0, 0, table_height+table_thickness)), Vector((width, 0, table_height+table_thickness)),
                    Vector((width, depth, table_height+table_thickness)), Vector((0, depth, table_height+table_thickness))]
            verts_t = [bm_table.verts.new(coord) for coord in v_t]
            try: # Add faces
                bm_table.faces.new((verts_t[0], verts_t[1], verts_t[2], verts_t[3]))
                bm_table.faces.new((verts_t[7], verts_t[6], verts_t[5], verts_t[4]))
                bm_table.faces.new((verts_t[0], verts_t[1], verts_t[5], verts_t[4]))
                bm_table.faces.new((verts_t[1], verts_t[2], verts_t[6], verts_t[5]))
                bm_table.faces.new((verts_t[2], verts_t[3], verts_t[7], verts_t[6]))
                bm_table.faces.new((verts_t[3], verts_t[0], verts_t[4], verts_t[7]))
            except ValueError: pass
            self.create_and_parent(bm_table, "Stall_Table", origin, Config.MATERIAL_PROP_WOOD, master)

        return {'FINISHED'}


class OP_GenerateNeonSign(OP_BaseGenerator):
    bl_idname = "wbtk.generate_neon_sign" # Use wbtk prefix
    bl_label = "Generate Neon Sign"
    bl_description = "Generate a basic neon sign backplate"
    # bl_options = {'REGISTER', 'UNDO'} # Inherited

    def execute(self, context):
        scene = context.scene
        # Use wbtk_ prefixes
        width = scene.wbtk_sign_width
        height = scene.wbtk_sign_height
        # Frame thickness not used in original simple plane logic, maybe add later?
        # frame_thickness = scene.wbtk_sign_frame_thickness

        master = Utils.create_master("NeonSign")
        bm = bmesh.new()

        # Create simple plane centered at origin
        half_w = width / 2.0
        half_h = height / 2.0
        v0 = bm.verts.new((-half_w, 0, -half_h))
        v1 = bm.verts.new(( half_w, 0, -half_h))
        v2 = bm.verts.new(( half_w, 0,  half_h))
        v3 = bm.verts.new((-half_w, 0,  half_h))
        try: bm.faces.new((v0, v1, v2, v3))
        except ValueError: pass

        self.create_and_parent(bm, "NeonSign_Backplate", Vector((0,0,0)), Config.MATERIAL_NEON_SIGN, master)

        return {'FINISHED'}


class OP_GenerateBarrelPyramid(OP_BaseGenerator):
    bl_idname = "wbtk.generate_barrel_pyramid"
    bl_label = "Generate Barrel Pyramid"
    bl_description = "Generate a stacked pyramid of metal barrels"

    base_count: bpy.props.IntProperty(name="Base Count", default=3, min=1, max=10)
    spacing_factor: bpy.props.FloatProperty(name="Spacing Factor", default=1.0, min=0.5, max=2.0,
        description="Multiplier for barrel diameter spacing")

    def execute(self, context):
        base_count = self.base_count
        spacing_factor = self.spacing_factor

        barrel_radius = getattr(context.scene, 'wbtk_barrel_radius', 0.25)
        barrel_height = getattr(context.scene, 'wbtk_barrel_height', 0.8)
        segments = getattr(context.scene, 'wbtk_barrel_sides', 16)
        spacing = barrel_radius * 2.0 * spacing_factor

        pyramid_master = Utils.create_master(f"BarrelPyramid_{base_count}")

        # --- Build ONE template barrel as pure BMesh (no bpy.ops calls) ---
        template_bm = bmesh.new()

        # Cylinder body
        top_ring = []
        bot_ring = []
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            ca = math.cos(angle)
            sa = math.sin(angle)
            # Gentle barrel bulge via sine
            for z_frac, ring_list in [(0.0, bot_ring), (1.0, top_ring)]:
                z = z_frac * barrel_height
                bulge = 1.0 + math.sin(z_frac * math.pi) * 0.04
                ring_list.append(template_bm.verts.new((
                    ca * barrel_radius * bulge,
                    sa * barrel_radius * bulge,
                    z
                )))

        # Side faces
        for i in range(segments):
            j = (i + 1) % segments
            try:
                template_bm.faces.new((bot_ring[i], bot_ring[j], top_ring[j], top_ring[i]))
            except ValueError:
                pass

        # Cap faces
        try:
            template_bm.faces.new(list(reversed(bot_ring)))
        except ValueError:
            pass
        try:
            template_bm.faces.new(top_ring)
        except ValueError:
            pass

        # Add 3 rib loops via subdivide + scale
        rib_edges = [e for e in template_bm.edges
                     if abs(e.verts[0].co.z - e.verts[1].co.z) > barrel_height * 0.8]
        if rib_edges:
            try:
                bmesh.ops.subdivide_edges(template_bm, edges=rib_edges, cuts=4)
            except Exception:
                pass

        # Scale rib-height verts outward slightly
        template_bm.verts.ensure_lookup_table()
        rib_positions = [barrel_height * f for f in [0.25, 0.5, 0.75]]
        for v in template_bm.verts:
            for rz in rib_positions:
                if abs(v.co.z - rz) < barrel_height * 0.03:
                    radial_len = Vector((v.co.x, v.co.y, 0)).length
                    if radial_len > 0.01:
                        scale = 1.03
                        v.co.x *= scale
                        v.co.y *= scale
                    break

        # Convert template to mesh data
        template_mesh = bpy.data.meshes.new("BarrelPyramid_TemplateMesh")
        template_bm.to_mesh(template_mesh)
        template_bm.free()
        template_mesh.update()

        # Assign material
        mat = Utils.get_or_create_material(Config.MATERIAL_PROP_METAL)
        if mat:
            template_mesh.materials.append(mat)

        # --- Place barrels by duplicating the mesh data ---
        barrel_idx = 0
        for level_num in range(base_count):
            level_size = base_count - level_num
            level_offset_x = level_num * spacing / 2.0
            level_offset_y = level_num * spacing / 2.0
            level_z = level_num * barrel_height * 0.9

            for x_idx in range(level_size):
                for y_idx in range(level_size):
                    # Create object using shared mesh data (instancing)
                    barrel_obj = bpy.data.objects.new(
                        f"Barrel_{barrel_idx:03d}", template_mesh.copy()
                    )

                    barrel_obj.location = (
                        level_offset_x + x_idx * spacing,
                        level_offset_y + y_idx * spacing,
                        level_z
                    )

                    # Slight random variation
                    barrel_obj.rotation_euler.z = random.uniform(0, math.pi * 2)
                    barrel_obj.scale.z *= random.uniform(0.95, 1.05)
                    if random.random() < 0.15:
                        barrel_obj.rotation_euler.x += random.uniform(
                            math.radians(-3), math.radians(3))

                    barrel_obj.parent = pyramid_master
                    Utils.link_to_collection(barrel_obj, Config.TARGET_COLLECTION)

                    barrel_idx += 1

        # Clean up template mesh if no users
        if template_mesh.users == 0:
            bpy.data.meshes.remove(template_mesh)

        # Select pyramid master
        bpy.ops.object.select_all(action='DESELECT')
        pyramid_master.select_set(True)
        context.view_layer.objects.active = pyramid_master

        self.report({'INFO'}, f"WBTK: Barrel pyramid — {barrel_idx} barrels placed")
        return {'FINISHED'}


# --- List of Operator Classes to Register from THIS file ---
_classes_to_register = (
    OP_GenerateCrate,
    OP_GenerateBarrel,
    OP_GenerateMetalBarrel,
    OP_GenerateVendorStall,
    OP_GenerateNeonSign,
    OP_GenerateBarrelPyramid,
)