# section lists
truck_sections = ["globals",
                  "nodes",
                  "nodes2",
                  "beams",
                  "cameras",
                  "cinecam",
                  "engine",
                  "engoption",
                  "engturbo",
                  "brakes",
                  "hydros",
                  "animators",
                  "commands",
                  "commands2",
                  "rotators",
                  "rotators2",
                  "wings",
                  "collisionboxes",
                  "rescuer",
                  "managedmaterials",
                  "contacters",
                  "triggers",
                  "lockgroups",
                  "hooks",
                  "submesh",
                  "slidenodes",
                  "railgroups",
                  "ropes",
                  "fixes",
                  "ties",
                  "ropables",
                  "particles",
                  "rigidifiers",
                  "torquecurve",
                  "cruisecontrol",
                  "axles",
                  "shocks",
                  "shocks2",
                  "flares",
                  "flares2",
                  "materialflarebindings",
                  "props",
                  "flexbodies",
                  "flexbodywheels",
                  "meshwheels2",
                  "meshwheels",
                  "wheels",
                  "wheels2",
                  "airbrakes",
                  "turboprops",
                  "fusedrag",
                  "turbojets",
                  "pistonprops",
                  "screwprops",
                  "description",
                  "rollon",
                  "comment",
                  "soundsources",
                  "minimass",
                  "disabledefaultsounds",
                  "guisettings",
                  "triangles",
                  "quads",
                  "props",
                  "forset"]

truck_inline_sections = ["set_skeleton_settings",
                         "set_beam_defaults",
                         "set_beam_defaults_scale",
                         "set_node_defaults",
                         "enable_advanced_deformation",
                         "end",
                         "guid",
                         "fileformatversion",
                         "author",
                         "fileinfo",
                         "slopebrake",
                         "tractioncontrol",
                         "antilockbrakes",
                         "disable_flexbody_shadow",
                         "flexbody_camera_mode",
                         "prop_camera_mode",
                         "forset"
                         "section",
                         "sectionconfig",
                         "importcommands",
                         "forwardcommands",
                         "forset",
                         "detacher_group"]

# storage classes
class Node:
    def __init__(self, name, xpos, ypos, zpos):
        self.name = name
        self.x = xpos
        self.y = ypos
        self.z = zpos
        self.fixed = False
        self.mass = 10
        self.load_bearer = False
        self.override_mass = False
        self.coupler = False
        self.collision = True
        self.selfCollision = False
        self.frictionCoef = 1.0
        self.group = []

class Beam:
    def __init__(self, nid1, nid2, spring, damp, strength, deform):
        self.id1 = nid1
        self.id2 = nid2
        self.beamSpring = spring
        self.beamDamp = damp
        self.beamStrength = strength
        self.beamDeform = deform
        self.beamShortBound = 1.0
        self.beamLongBound = 1.0
        self.beamPrecompression = 1.0
        self.beamDampRebound = False
        self.beamLimitSpring = spring * 2
        self.beamLimitDamp = damp / 2
        self.type = 'NORMAL'
        self.breakGroup = ''


class Engine:
    def __init__(self, min_rpm, max_rpm, torque, differential, gears):
        self.min_rpm = min_rpm
        self.max_rpm = max_rpm
        self.torque = torque
        self.differential = differential
        self.gears = gears


class Engoption:
    def __init__(self, inertia, type, clutch_force, shift_time, clutch_time, post_shift_time, stall_rpm, idle_rpm, max_idle_mixture, min_idle_mixture):
        self.inertia = inertia
        self.type = type
        self.clutch_force = clutch_force
        self.shift_time = shift_time
        self.clutch_time = clutch_time
        self.post_shift_time = post_shift_time
        self.stall_rpm = stall_rpm
        self.idle_rpm = idle_rpm
        self.max_idle_mixture = max_idle_mixture
        self.min_idle_mixture = min_idle_mixture


class Hydro:
    def __init__(self, nid1, nid2, factor, spring, damp, strength, deform):
        self.id1 = nid1
        self.id2 = nid2
        self.factor = factor
        self.beamSpring = spring
        self.beamDamp = damp
        self.beamStrength = strength
        self.beamDeform = deform


class InternalCamera:
    def __init__(self, xpos, ypos, zpos, id1, id2, id3, id4, id5, id6, spring, damp):
        self.x = xpos
        self.y = ypos
        self.z = zpos
        self.id1 = id1
        self.id2 = id2
        self.id3 = id3
        self.id4 = id4
        self.id5 = id5
        self.id6 = id6
        self.beamSpring = spring
        self.beamDamp = damp
        self.fov = 60
        self.type = "rorcam"


class Slidenode:
    def __init__(self, node, rail, spring, strength, tolerance):
        self.node = node
        self.rail = rail
        self.spring = spring
        self.strength = strength
        self.tolerance = tolerance


class Rail:
    def __init__(self, name, nodes):
        self.name = name
        self.nodes = nodes


class Refnodes:
    def __init__(self, center, back, left):
        self.center = center
        self.back = back
        self.left = left


class Flexbody:
    """Enhanced flexbody class with additional properties"""
    def __init__(self, refnode, xnode, ynode, offsetX, offsetY, offsetZ, rotX, rotY, rotZ, mesh):
        self.mesh = mesh
        self.refnode = refnode
        self.xnode = xnode
        self.ynode = ynode
        self.offsetX = offsetX
        self.offsetY = offsetY
        self.offsetZ = offsetZ
        self.rotX = rotX
        self.rotY = rotY
        self.rotZ = rotZ

        # Enhanced properties
        self.forset_nodes = []  # Nodes affected by forset
        self.non_flex_materials = []  # Materials that don't deform
        self.shared_skeleton = False  # Whether to share skeleton with other flexbodies
        self.disable_mesh_breaking = False  # Disable mesh breaking
        self.plastic_deform_coef = 0.0  # Plastic deformation coefficient
        self.damage_threshold = 0.0  # Damage threshold
        self.group_name = ""  # Group name for JBeam
        self.scale = [1.0, 1.0, 1.0]  # Scale factors
        self.visibility_mode = "normal"  # "normal", "transparent", "invisible"

    def get_group_name(self):
        """Get the group name for this flexbody"""
        if self.group_name:
            return self.group_name
        # Generate from mesh name
        import re
        name = self.mesh.lower()
        # Remove file extension
        if name.endswith('.mesh'):
            name = name[:-5]
        elif name.endswith('.dae'):
            name = name[:-4]
        # Replace non-alphanumeric characters with underscores
        name = re.sub(r'[^\w_]', '_', name)
        # Remove multiple consecutive underscores
        name = re.sub(r'_+', '_', name)
        # Remove leading/trailing underscores
        name = name.strip('_')
        return name + "_flexbody"

    def get_nodes(self):
        """Get all nodes referenced by this flexbody"""
        nodes = [self.refnode, self.xnode, self.ynode]
        nodes.extend(self.forset_nodes)
        return list(set(nodes))  # Remove duplicates


class Prop:
    """Represents a prop (static mesh) attached to the vehicle"""
    def __init__(self, refnode, xnode, ynode, offsetX, offsetY, offsetZ, rotX, rotY, rotZ, mesh):
        self.mesh = mesh
        self.refnode = refnode
        self.xnode = xnode
        self.ynode = ynode
        self.offsetX = offsetX
        self.offsetY = offsetY
        self.offsetZ = offsetZ
        self.rotX = rotX
        self.rotY = rotY
        self.rotZ = rotZ

        # Prop-specific properties
        self.scale = [1.0, 1.0, 1.0]  # Scale factors
        self.material_override = ""  # Override material
        self.collision_enabled = True  # Whether prop has collision
        self.shadow_enabled = True  # Whether prop casts shadows
        self.group_name = ""  # Group name for JBeam
        self.animation_factor = 0.0  # Animation factor for moving props
        self.animation_mode = "rotation"  # "rotation", "translation", "none"
        self.animation_axis = [0, 0, 1]  # Animation axis

    def get_group_name(self):
        """Get the group name for this prop"""
        if self.group_name:
            return self.group_name
        # Generate from mesh name
        import re
        name = self.mesh.lower()
        # Remove file extension
        if name.endswith('.mesh'):
            name = name[:-5]
        elif name.endswith('.dae'):
            name = name[:-4]
        # Replace non-alphanumeric characters with underscores
        name = re.sub(r'[^\w_]', '_', name)
        # Remove multiple consecutive underscores
        name = re.sub(r'_+', '_', name)
        # Remove leading/trailing underscores
        name = name.strip('_')
        return name + "_prop"

    def get_nodes(self):
        """Get all nodes referenced by this prop"""
        return [self.refnode, self.xnode, self.ynode]


class JBeamInformation:
    def __init__(self):
        self.name = "Untitled"
        self.author = "Insert author information"


class Axle:
    def __init__(self, wid1, wid2, type, state):
        self.wid1 = wid1
        self.wid2 = wid2
        self.type = type
        self.state = state


class Triangle:
    """Represents a triangle surface for collision or visual purposes"""
    def __init__(self, node1: str, node2: str, node3: str, surface_type: str = "collision"):
        self.node1 = node1
        self.node2 = node2
        self.node3 = node3
        self.surface_type = surface_type  # "collision", "visual", "both"
        self.material = "default"
        self.drag_coefficient = 0.0
        self.lift_coefficient = 0.0
        self.options = []  # Additional options like 'c' for collision, 'v' for visual

    def get_nodes(self):
        """Get all nodes in the triangle"""
        return [self.node1, self.node2, self.node3]

    def is_collision(self):
        """Check if this triangle is used for collision"""
        return self.surface_type in ["collision", "both"] or "c" in self.options

    def is_visual(self):
        """Check if this triangle is used for visual purposes"""
        return self.surface_type in ["visual", "both"] or "v" in self.options


class Quad:
    """Represents a quad surface for collision or visual purposes"""
    def __init__(self, node1: str, node2: str, node3: str, node4: str, surface_type: str = "collision"):
        self.node1 = node1
        self.node2 = node2
        self.node3 = node3
        self.node4 = node4
        self.surface_type = surface_type  # "collision", "visual", "both"
        self.material = "default"
        self.drag_coefficient = 0.0
        self.lift_coefficient = 0.0
        self.options = []  # Additional options

    def get_nodes(self):
        """Get all nodes in the quad"""
        return [self.node1, self.node2, self.node3, self.node4]

    def is_collision(self):
        """Check if this quad is used for collision"""
        return self.surface_type in ["collision", "both"] or "c" in self.options

    def is_visual(self):
        """Check if this quad is used for visual purposes"""
        return self.surface_type in ["visual", "both"] or "v" in self.options

    def to_triangles(self):
        """Convert quad to two triangles"""
        # Split quad into two triangles: (1,2,3) and (1,3,4)
        tri1 = Triangle(self.node1, self.node2, self.node3, self.surface_type)
        tri1.material = self.material
        tri1.drag_coefficient = self.drag_coefficient
        tri1.lift_coefficient = self.lift_coefficient
        tri1.options = self.options.copy()

        tri2 = Triangle(self.node1, self.node3, self.node4, self.surface_type)
        tri2.material = self.material
        tri2.drag_coefficient = self.drag_coefficient
        tri2.lift_coefficient = self.lift_coefficient
        tri2.options = self.options.copy()

        return [tri1, tri2]

class WheelTypeA:
    def __init__(self, radius, width, num_rays, nid1, nid2, snode, braketype, drivetype, armnode, mass, spring, damp):
        self.radius = radius
        self.width = width
        self.num_rays = num_rays
        self.nid1 = nid1
        self.nid2 = nid2
        self.snode = snode
        self.braketype = braketype
        self.drivetype = drivetype
        self.armnode = armnode
        self.mass = mass
        self.spring = spring
        self.damp = damp
        self.type = "wheels"


class WheelTypeB:
    def __init__(self, tire_radius, hub_radius, width, num_rays, nid1, nid2, snode, braketype, drivetype, armnode, mass, tire_spring, tire_damp, hub_spring, hub_damp):
        self.tire_radius = tire_radius
        self.hub_radius = hub_radius
        self.width = width
        self.num_rays = num_rays
        self.nid1 = nid1
        self.nid2 = nid2
        self.snode = snode
        self.braketype = braketype
        self.drivetype = drivetype
        self.armnode = armnode
        self.mass = mass
        self.tire_spring = tire_spring
        self.tire_damp = tire_damp
        self.hub_spring = hub_spring
        self.hub_damp = hub_damp
        self.type = "wheels.advanced"
        self.subtype = "None"