from rig_common import truck_sections, truck_inline_sections, Axle
import rig_parser as parser
import rig_torquecurves as curves
import logging
import math
import json
import os
from typing import List, Optional, Dict, Any, Tuple
from dae_processor import DAEProcessor


def vector_distance(x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> float:
    """Calculate squared distance between two 3D points"""
    nx = x2 - x1
    ny = y2 - y1
    nz = z2 - z1
    return nx * nx + ny * ny + nz * nz


def vector_length(x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> float:
    """Calculate actual distance between two 3D points"""
    return math.sqrt(vector_distance(x1, y1, z1, x2, y2, z2))

class RigParseError(Exception):
    """Custom exception for rig parsing errors"""
    def __init__(self, message: str, line_number: Optional[int] = None, line_content: Optional[str] = None):
        self.line_number = line_number
        self.line_content = line_content
        if line_number:
            message = f"Line {line_number}: {message}"
        if line_content:
            message += f" ('{line_content.strip()}')"
        super().__init__(message)


class Rig:
    """Enhanced Rig class with better error handling and validation"""

    def __init__(self):
        self.name: str = "Untitled Rig Class"
        self.authors: List[str] = []
        self.nodes: List[Any] = []
        self.beams: List[Any] = []
        self.hydros: List[Any] = []
        self.internal_cameras: List[Any] = []
        self.rails: List[Any] = []
        self.slidenodes: List[Any] = []
        self.wheels: List[Any] = []
        self.flexbodies: List[Any] = []
        self.props: List[Any] = []  # New prop support
        self.axles: List[Axle] = []
        self.brakes: List[float] = []
        self.torquecurve: Optional[List[List[float]]] = None
        self.engine: Optional[Any] = None
        self.engoption: Optional[Any] = None
        self.refnodes: Optional[Any] = None
        self.minimass: float = 50
        self.dry_weight: float = 10000
        self.load_weight: float = 10000
        self.triangles: List[Any] = []  # Now supports Triangle objects
        self.quads: List[Any] = []  # New quad support
        self.legacy_triangles: List[List[str]] = []  # Legacy triangle format from submesh
        self.rollon: bool = False
        self.type: str = 'truck'

        # Statistics and validation
        self.parse_warnings: List[str] = []
        self.parse_errors: List[str] = []
        self.logger = logging.getLogger(__name__)

        # DAE processor for mesh name handling
        self.dae_processor = DAEProcessor()

        # Flag to exclude transform properties from JBeam output
        self.no_transform_properties = False

    def add_warning(self, message: str, line_number: Optional[int] = None):
        """Add a parsing warning"""
        warning = f"Line {line_number}: {message}" if line_number else message
        self.parse_warnings.append(warning)
        self.logger.warning(warning)

    def add_error(self, message: str, line_number: Optional[int] = None):
        """Add a parsing error"""
        error = f"Line {line_number}: {message}" if line_number else message
        self.parse_errors.append(error)
        self.logger.error(error)

    def validate(self) -> bool:
        """Validate the rig data for common issues"""
        is_valid = True

        # Check for minimum required components
        if not self.nodes:
            self.add_error("No nodes found - vehicle needs nodes to function")
            is_valid = False

        if not self.beams:
            self.add_error("No beams found - vehicle needs beams for structure")
            is_valid = False

        # Check for orphaned beams (beams referencing non-existent nodes)
        node_names = {node.name for node in self.nodes}
        for beam in self.beams:
            if beam.id1 not in node_names:
                self.add_warning(f"Beam references non-existent node: {beam.id1}")
            if beam.id2 not in node_names:
                self.add_warning(f"Beam references non-existent node: {beam.id2}")

        # Check for duplicate nodes
        node_positions = {}
        for node in self.nodes:
            pos_key = (round(node.x, 3), round(node.y, 3), round(node.z, 3))
            if pos_key in node_positions:
                self.add_warning(f"Nodes {node.name} and {node_positions[pos_key]} have identical positions")
            else:
                node_positions[pos_key] = node.name

        # Check for reasonable mass values
        if self.dry_weight <= 0:
            self.add_warning(f"Dry weight is {self.dry_weight}, should be positive")

        if self.load_weight <= 0:
            self.add_warning(f"Load weight is {self.load_weight}, should be positive")

        # Check engine configuration
        if self.engine and not self.torquecurve:
            self.add_warning("Engine defined but no torque curve found")

        # Validate triangles and quads
        self._validate_surfaces()

        # Validate flexbodies and props
        self._validate_visual_elements()

        return is_valid

    def _validate_surfaces(self):
        """Validate triangles and quads"""
        node_names = {node.name for node in self.nodes}

        # Validate triangles
        for i, triangle in enumerate(self.triangles):
            if hasattr(triangle, 'get_nodes'):  # New Triangle object
                for node_name in triangle.get_nodes():
                    if node_name not in node_names:
                        self.add_warning(f"Triangle {i} references non-existent node: {node_name}")
            else:  # Legacy format
                for node_name in triangle:
                    if node_name not in node_names:
                        self.add_warning(f"Legacy triangle {i} references non-existent node: {node_name}")

        # Validate quads
        for i, quad in enumerate(self.quads):
            if hasattr(quad, 'get_nodes'):  # Quad object
                for node_name in quad.get_nodes():
                    if node_name not in node_names:
                        self.add_warning(f"Quad {i} references non-existent node: {node_name}")

        # Validate legacy triangles
        for i, triangle in enumerate(self.legacy_triangles):
            for node_name in triangle:
                if node_name not in node_names:
                    self.add_warning(f"Legacy submesh triangle {i} references non-existent node: {node_name}")

    def _validate_visual_elements(self):
        """Validate flexbodies and props"""
        node_names = {node.name for node in self.nodes}

        # Validate flexbodies
        for i, flexbody in enumerate(self.flexbodies):
            if hasattr(flexbody, 'get_nodes'):  # Enhanced Flexbody object
                for node_name in flexbody.get_nodes():
                    if node_name not in node_names:
                        self.add_warning(f"Flexbody {i} ({flexbody.mesh}) references non-existent node: {node_name}")

                # Check mesh file extension
                if not (flexbody.mesh.endswith('.mesh') or flexbody.mesh.endswith('.dae')):
                    self.add_warning(f"Flexbody {i} has unusual mesh format: {flexbody.mesh}")

                # Check for reasonable scale values
                if hasattr(flexbody, 'scale'):
                    for j, scale_val in enumerate(flexbody.scale):
                        if scale_val <= 0:
                            self.add_warning(f"Flexbody {i} has invalid scale value: {scale_val}")
                        elif scale_val > 10:
                            self.add_warning(f"Flexbody {i} has very large scale value: {scale_val}")
            else:  # Legacy flexbody
                for node_name in [flexbody.refnode, flexbody.xnode, flexbody.ynode]:
                    if node_name not in node_names:
                        self.add_warning(f"Legacy flexbody {i} ({flexbody.mesh}) references non-existent node: {node_name}")

        # Validate props
        for i, prop in enumerate(self.props):
            if hasattr(prop, 'get_nodes'):  # Prop object
                for node_name in prop.get_nodes():
                    if node_name not in node_names:
                        self.add_warning(f"Prop {i} ({prop.mesh}) references non-existent node: {node_name}")

                # Check mesh file extension
                if not (prop.mesh.endswith('.mesh') or prop.mesh.endswith('.dae')):
                    self.add_warning(f"Prop {i} has unusual mesh format: {prop.mesh}")

                # Check for reasonable scale values
                if hasattr(prop, 'scale'):
                    for j, scale_val in enumerate(prop.scale):
                        if scale_val <= 0:
                            self.add_warning(f"Prop {i} has invalid scale value: {scale_val}")
                        elif scale_val > 10:
                            self.add_warning(f"Prop {i} has very large scale value: {scale_val}")

                # Check animation parameters
                if hasattr(prop, 'animation_factor') and prop.animation_factor != 0:
                    if prop.animation_mode not in ["rotation", "translation", "none"]:
                        self.add_warning(f"Prop {i} has invalid animation mode: {prop.animation_mode}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the rig"""
        stats = {
            'nodes': len(self.nodes),
            'beams': len(self.beams),
            'wheels': len(self.wheels),
            'hydros': len(self.hydros),
            'flexbodies': len(self.flexbodies),
            'props': len(self.props),
            'cameras': len(self.internal_cameras),
            'rails': len(self.rails),
            'slidenodes': len(self.slidenodes),
            'triangles': len(self.triangles),
            'quads': len(self.quads),
            'legacy_triangles': len(self.legacy_triangles),
            'axles': len(self.axles),
            'dry_weight': self.dry_weight,
            'load_weight': self.load_weight,
            'has_engine': self.engine is not None,
            'has_torquecurve': self.torquecurve is not None,
            'warnings': len(self.parse_warnings),
            'errors': len(self.parse_errors)
        }

        # Calculate total beam length
        total_beam_length = 0
        for beam in self.beams:
            node1 = next((n for n in self.nodes if n.name == beam.id1), None)
            node2 = next((n for n in self.nodes if n.name == beam.id2), None)
            if node1 and node2:
                total_beam_length += vector_length(node1.x, node1.y, node1.z, node2.x, node2.y, node2.z)

        stats['total_beam_length'] = total_beam_length

        return stats

    def calculate_masses(self):
        """
        Calculate node masses based on RoR algorithm
        Python version of https://github.com/RigsOfRods/rigs-of-rods/blob/master/source/main/physics/Beam.cpp#L814
        """
        if not self.nodes:
            self.add_error("Cannot calculate masses: no nodes found")
            return

        numnodes = 0
        numloadnodes = 0
        for n in self.nodes:
            if n.load_bearer:
                numloadnodes += 1
            else:
                numnodes += 1

        self.logger.debug(f"Found {numloadnodes} load-bearing nodes, {numnodes} regular nodes")

        # Initialize node masses
        for n in self.nodes:
            if not n.load_bearer:
                n.mass = 0
            elif n.override_mass == False:
                if numloadnodes > 0:
                    n.mass = self.load_weight / numloadnodes
                else:
                    n.mass = self.minimass
                    self.add_warning("No load-bearing nodes found, using minimum mass")
            elif n.override_mass != False:
                n.mass = n.override_mass

        # Calculate average linear density from beam lengths
        avg_lin_dens = 0.0
        valid_beams = 0

        for b in self.beams:
            if b.type != 'VIRTUAL':
                node1 = next((x for x in self.nodes if x.name == b.id1), None)
                node2 = next((x for x in self.nodes if x.name == b.id2), None)

                if node1 is not None and node2 is not None:
                    beam_length = vector_distance(node1.x, node1.y, node1.z, node2.x, node2.y, node2.z)
                    avg_lin_dens += beam_length
                    valid_beams += 1
                else:
                    self.add_warning(f"Beam references missing nodes: {b.id1}, {b.id2}")

        if avg_lin_dens == 0:
            self.add_error("Cannot calculate masses: no valid beams found")
            return

        self.logger.debug(f"Calculated linear density from {valid_beams} beams")

        # Distribute dry weight based on beam lengths
        for b in self.beams:
            if b.type != 'VIRTUAL':
                node1 = next((x for x in self.nodes if x.name == b.id1), None)
                node2 = next((x for x in self.nodes if x.name == b.id2), None)

                if node1 is not None and node2 is not None:
                    beam_length = vector_distance(node1.x, node1.y, node1.z, node2.x, node2.y, node2.z)
                    half_mass = beam_length * self.dry_weight / avg_lin_dens / 2

                    node1.mass += half_mass
                    node2.mass += half_mass

        # Ensure minimum mass
        nodes_adjusted = 0
        for n in self.nodes:
            if n.mass < self.minimass:
                n.mass = self.minimass
                nodes_adjusted += 1

        if nodes_adjusted > 0:
            self.logger.debug(f"Adjusted {nodes_adjusted} nodes to minimum mass of {self.minimass}")

        # Calculate total mass for validation
        total_mass = sum(n.mass for n in self.nodes)
        expected_mass = self.dry_weight + self.load_weight
        mass_difference = abs(total_mass - expected_mass)

        if mass_difference > expected_mass * 0.1:  # More than 10% difference
            self.add_warning(f"Total calculated mass ({total_mass:.1f}) differs significantly from expected ({expected_mass:.1f})")

        self.logger.debug(f"Mass calculation complete. Total mass: {total_mass:.1f}")




    def from_file(self, filename: str):
        """
        Parse a RoR rig file with enhanced error handling

        Args:
            filename: Path to the rig file to parse

        Raises:
            RigParseError: If critical parsing errors occur
            FileNotFoundError: If the file doesn't exist
            PermissionError: If the file can't be read
        """
        self.logger.info(f"Parsing rig file: {filename}")

        # Read file with error handling
        try:
            with open(filename, 'r', encoding='utf-8', errors='replace') as f:
                trucklines = f.readlines()
        except FileNotFoundError:
            raise RigParseError(f"File not found: {filename}")
        except PermissionError:
            raise RigParseError(f"Permission denied reading file: {filename}")
        except Exception as e:
            raise RigParseError(f"Error reading file {filename}: {e}")

        if not trucklines:
            raise RigParseError("File is empty")

        self.logger.debug(f"Read {len(trucklines)} lines from file")

        # Initialize parsing state
        last_beamspring = 9000000
        last_beamdamp = 12000
        last_beamdeform = 400000
        last_beamstrength = 1000000

        springscale = 1
        dampscale = 1
        deformscale = 1
        strengthscale = 1

        cur_detach_group = 0

        last_loadweight = 0.0
        last_friction = 1.0

        # Parse the rig file
        current_section = None
        lines_parsed = 0

        for line_number, line in enumerate(trucklines, 1):
            try:
                # First line is the title
                if lines_parsed == 0:
                    self.name = line.replace("\n", "").strip()
                    if not self.name:
                        self.name = "Untitled Rig"
                        self.add_warning("Empty title line, using default name", line_number)
                    lines_parsed += 1
                    continue

                # Parse line components
                line_cmps = parser.PrepareLine(line)

                # Skip invalid/empty lines
                if line_cmps is None:
                    continue

                num_components = len(line_cmps)

                if num_components == 0:
                    continue

                # Handle inline sections
                if line_cmps[0] in truck_inline_sections:
                    section_name = line_cmps[0]

                    try:
                        if section_name == "set_beam_defaults" and num_components >= 5:
                            last_beamspring, last_beamdamp, last_beamdeform, last_beamstrength = parser.ParseSetBeamDefaults(line_cmps)
                        elif section_name == "set_beam_defaults_scale" and num_components >= 5:
                            springscale, dampscale, deformscale, strengthscale = parser.ParseSetBeamDefaults(line_cmps)
                        elif section_name == "set_node_defaults" and num_components >= 5:
                            defaults = parser.ParseSetNodeDefaults(line_cmps)
                            last_loadweight = defaults[0]
                            last_friction = defaults[1]
                        elif section_name == "detacher_group":
                            if num_components >= 2:
                                cur_detach_group = int(line_cmps[1])
                            else:
                                self.add_warning("detacher_group missing group ID", line_number)
                        elif section_name == "rollon":
                            self.rollon = True
                        elif section_name == "author":
                            if num_components >= 2:
                                author_data = line_cmps[1].strip().split()
                                if len(author_data) >= 3:
                                    self.authors.append(author_data[2].replace("_", " "))
                                else:
                                    self.add_warning("Invalid author format", line_number)
                            else:
                                self.add_warning("author missing data", line_number)
                        elif section_name == "forset" and len(self.flexbodies) > 0:
                            forset = parser.ParseForset(line_cmps)
                            # Get the last flexbody (forset applies to the most recently defined flexbody)
                            last_flexbody = self.flexbodies[-1]

                            # Store forset nodes in the flexbody for later group assignment
                            if not hasattr(last_flexbody, 'forset_nodes'):
                                last_flexbody.forset_nodes = []

                            for ranges in forset:
                                for cr in range(ranges[0], ranges[1] + 1):
                                    if cr >= len(self.nodes):
                                        self.add_warning(f"forset references invalid node index {cr}", line_number)
                                        break
                                    else:
                                        # Add node name to flexbody's forset list
                                        node_name = self.nodes[cr].name
                                        if node_name not in last_flexbody.forset_nodes:
                                            last_flexbody.forset_nodes.append(node_name)
                        elif section_name == "end":
                            # Stop parsing
                            break
                    except (ValueError, IndexError) as e:
                        self.add_error(f"Error parsing {section_name}: {e}", line_number)

                    continue

                # Handle new sections
                if line_cmps[0] in truck_sections:
                    current_section = line_cmps[0]
                    continue

                # Parse section content
                if (current_section == "nodes" or current_section == "nodes2") and num_components >= 4:
                    node_object = parser.ParseNode(line_cmps)

                    # apply set_node_defaults
                    node_object.frictionCoef = last_friction
                    if last_loadweight > 0:
                        node_object.override_mass = last_loadweight

                    self.nodes.append(node_object)
                elif current_section == "beams" and num_components >= 2:
                    beam_object = parser.ParseBeam(line_cmps, last_beamspring * springscale, last_beamdamp * dampscale, last_beamstrength * strengthscale, last_beamdeform * deformscale)
                    parser.SetBeamBreakgroup(beam_object, cur_detach_group)
                    self.beams.append(beam_object)
                elif current_section == "hydros" and num_components >= 3:
                    self.hydros.append(parser.ParseHydro(line_cmps, last_beamspring, last_beamdamp, last_beamstrength * strengthscale, last_beamdeform * deformscale))
                elif current_section == "globals" and num_components >= 2:
                    self.dry_weight = float(line_cmps[0])
                    self.load_weight = float(line_cmps[1])
                elif current_section == "railgroups" and num_components >= 2:
                    self.rails.append(parser.ParseRailgroup(line_cmps))
                elif current_section == "slidenodes" and num_components >= 2:
                    slidenode, rail = parser.ParseSlidenode(line_cmps)

                    if not isinstance(rail, str):
                        # this is a Railgroup object, add it to self
                        self.rails.append(rail)

                    self.slidenodes.append(slidenode)
                elif current_section == "fixes" and num_components >= 1:
                    # set node(s) to fixed
                    nid = line_cmps[0]
                    if nid.isdigit():
                        nid = "node" + nid

                    node = next((x for x in self.nodes if x.name == nid), None)
                    if node:
                        node.fixed = True
                    else:
                        self.add_warning(f"Cannot fix unknown node: {nid}", line_number)
                elif current_section == "triangles" and num_components >= 3:
                    # Parse new triangle format
                    try:
                        triangle = parser.ParseTriangle(line_cmps)
                        self.triangles.append(triangle)
                    except ValueError as e:
                        self.add_error(f"Error parsing triangle: {e}", line_number)
                elif current_section == "quads" and num_components >= 4:
                    # Parse quad format
                    try:
                        quad = parser.ParseQuad(line_cmps)
                        self.quads.append(quad)
                    except ValueError as e:
                        self.add_error(f"Error parsing quad: {e}", line_number)
                elif current_section == "submesh" and num_components >= 4:
                    # Parse legacy submesh triangles
                    if 'c' in line_cmps[3]:
                        # collision triangle
                        try:
                            triangle = parser.ParseSubmeshTriangle(line_cmps)
                            self.legacy_triangles.append([triangle.node1, triangle.node2, triangle.node3])
                        except ValueError as e:
                            self.add_error(f"Error parsing submesh triangle: {e}", line_number)
                elif current_section == "flexbodies" and num_components >= 10:
                    # Parse flexbody
                    try:
                        flexbody = parser.ParseFlexbody(line_cmps)
                        self.flexbodies.append(flexbody)
                    except ValueError as e:
                        self.add_error(f"Error parsing flexbody: {e}", line_number)
                elif current_section == "props" and num_components >= 10:
                    # Parse prop
                    try:
                        prop = parser.ParseProp(line_cmps)
                        self.props.append(prop)
                    except ValueError as e:
                        self.add_error(f"Error parsing prop: {e}", line_number)
                elif current_section == "forset" and len(self.flexbodies) > 0:
                    # Parse forset for the last flexbody
                    try:
                        # Add the section name back for ParseForset
                        forset_components = ['forset'] + line_cmps
                        forset = parser.ParseForset(forset_components)
                        last_flexbody = self.flexbodies[-1]

                        # Store forset nodes in the flexbody for later group assignment
                        if not hasattr(last_flexbody, 'forset_nodes'):
                            last_flexbody.forset_nodes = []

                        for ranges in forset:
                            for cr in range(ranges[0], ranges[1] + 1):
                                if cr >= len(self.nodes):
                                    self.add_warning(f"forset references invalid node index {cr}", line_number)
                                    break
                                else:
                                    # Add node name to flexbody's forset list
                                    node_name = self.nodes[cr].name
                                    if node_name not in last_flexbody.forset_nodes:
                                        last_flexbody.forset_nodes.append(node_name)
                    except ValueError as e:
                        self.add_error(f"Error parsing forset: {e}", line_number)

                # Add more section parsing here if needed...
                # For now, skip unsupported sections with a warning
                elif current_section and num_components > 0:
                    # This is content for a section we don't fully support yet
                    pass

                lines_parsed += 1

            except Exception as e:
                self.add_error(f"Error parsing line: {e}", line_number)
                lines_parsed += 1
                continue

        # Final validation and cleanup
        if self.torquecurve is None and self.engine is not None:
            self.torquecurve = curves.get_curve("default")

        self.logger.info(f"Parsing complete. Processed {lines_parsed} lines.")

        # Run validation
        self.validate()

    def _assign_flexbody_groups(self):
        """Assign nodes to their corresponding flexbody groups for proper visibility in BeamNG"""
        # First, resolve duplicate mesh names
        self._resolve_duplicate_mesh_names()

        # Create a mapping of node names to node objects for quick lookup
        node_map = {node.name: node for node in self.nodes}

        # Process each flexbody
        for flexbody in self.flexbodies:
            if hasattr(flexbody, 'get_group_name'):
                group_name = flexbody.get_group_name()

                # Get all nodes that should be part of this flexbody
                flexbody_nodes = []

                # Add reference nodes (always part of flexbody)
                ref_nodes = [flexbody.refnode, flexbody.xnode, flexbody.ynode]
                for node_name in ref_nodes:
                    if node_name in node_map:
                        flexbody_nodes.append(node_name)

                # Add forset nodes if they exist
                if hasattr(flexbody, 'forset_nodes'):
                    flexbody_nodes.extend(flexbody.forset_nodes)

                # If no forset nodes are specified, we need to intelligently assign nodes
                # This is crucial for proper flexbody visibility in BeamNG
                if not hasattr(flexbody, 'forset_nodes') or not flexbody.forset_nodes:
                    # Find nodes that are likely part of this flexbody based on proximity and connectivity
                    flexbody_nodes.extend(self._find_flexbody_nodes(flexbody, node_map))

                # Assign the group to all flexbody nodes
                for node_name in set(flexbody_nodes):  # Remove duplicates
                    if node_name in node_map:
                        node = node_map[node_name]
                        if group_name not in node.group:
                            node.group.append(group_name)

        # Process props similarly
        for prop in self.props:
            if hasattr(prop, 'get_group_name'):
                group_name = prop.get_group_name()

                # Props typically only affect their reference nodes
                ref_nodes = [prop.refnode, prop.xnode, prop.ynode]
                for node_name in ref_nodes:
                    if node_name in node_map:
                        node = node_map[node_name]
                        if group_name not in node.group:
                            node.group.append(group_name)

    def _find_flexbody_nodes(self, flexbody, node_map):
        """Find nodes that should be part of a flexbody based on connectivity and proximity"""
        import math

        # Get reference node positions
        ref_node = node_map.get(flexbody.refnode)
        x_node = node_map.get(flexbody.xnode)
        y_node = node_map.get(flexbody.ynode)

        if not all([ref_node, x_node, y_node]):
            return []

        # Calculate the center and approximate size of the flexbody
        center_x = (ref_node.x + x_node.x + y_node.x) / 3
        center_y = (ref_node.y + x_node.y + y_node.y) / 3
        center_z = (ref_node.z + x_node.z + y_node.z) / 3

        # Calculate approximate radius based on reference nodes
        max_dist = 0
        for node in [ref_node, x_node, y_node]:
            dist = math.sqrt((node.x - center_x)**2 + (node.y - center_y)**2 + (node.z - center_z)**2)
            max_dist = max(max_dist, dist)

        # Expand radius to include nearby nodes (flexbodies often cover larger areas)
        search_radius = max_dist * 2.0  # Adjust multiplier as needed

        # Find nodes within the search radius
        candidate_nodes = []
        for node in self.nodes:
            dist = math.sqrt((node.x - center_x)**2 + (node.y - center_y)**2 + (node.z - center_z)**2)
            if dist <= search_radius:
                candidate_nodes.append(node.name)

        # Filter out nodes that are already assigned to other flexbodies
        # (to avoid conflicts, though BeamNG can handle nodes in multiple groups)
        flexbody_nodes = []
        for node_name in candidate_nodes:
            node = node_map[node_name]
            # Include nodes that aren't heavily grouped already
            if len(node.group) < 2:  # Allow some overlap but prefer ungrouped nodes
                flexbody_nodes.append(node_name)

        # If we found too few nodes, be more inclusive
        if len(flexbody_nodes) < 10:  # Minimum reasonable number for a flexbody
            flexbody_nodes = candidate_nodes

        return flexbody_nodes

    def _resolve_duplicate_mesh_names(self):
        """Resolve duplicate mesh names in flexbodies and props by adding sequential suffixes"""
        # Track mesh name usage across both flexbodies and props
        mesh_usage = {}

        # First pass: collect all mesh names and count usage
        all_visual_elements = []

        # Add flexbodies
        for flexbody in self.flexbodies:
            all_visual_elements.append(('flexbody', flexbody))
            mesh_name = flexbody.mesh.lower()
            mesh_usage[mesh_name] = mesh_usage.get(mesh_name, 0) + 1

        # Add props
        for prop in self.props:
            all_visual_elements.append(('prop', prop))
            mesh_name = prop.mesh.lower()
            mesh_usage[mesh_name] = mesh_usage.get(mesh_name, 0) + 1

        # Second pass: rename duplicates
        mesh_counters = {}

        for element_type, element in all_visual_elements:
            original_mesh = element.mesh
            mesh_name_lower = original_mesh.lower()

            # If this mesh name appears multiple times, we need to rename
            if mesh_usage[mesh_name_lower] > 1:
                # Initialize counter for this mesh name if not exists
                if mesh_name_lower not in mesh_counters:
                    mesh_counters[mesh_name_lower] = 0

                # Generate new unique mesh name
                counter = mesh_counters[mesh_name_lower]
                mesh_counters[mesh_name_lower] += 1

                # Create new mesh name with suffix
                new_mesh_name = self._generate_unique_mesh_name(original_mesh, counter)

                # Update the element's mesh name
                element.mesh = new_mesh_name

                # Log the change
                self.logger.info(f"Renamed duplicate mesh: {original_mesh} -> {new_mesh_name}")

    def _generate_unique_mesh_name(self, original_mesh, counter):
        """Generate a unique mesh name by adding a sequential suffix"""
        import os

        # Split filename and extension
        name, ext = os.path.splitext(original_mesh)

        # Generate suffix based on counter
        if counter == 0:
            suffix = "_001"
        elif counter == 1:
            suffix = "_002"
        elif counter == 2:
            suffix = "_003"
        else:
            suffix = f"_{counter+1:03d}"

        # Return new name with suffix
        return f"{name}{suffix}{ext}"

    def extract_dae_mesh_names(self, dae_directory: str) -> Dict[str, List[str]]:
        """
        Extract mesh names from all DAE files in a directory

        Args:
            dae_directory: Directory containing DAE files

        Returns:
            Dictionary mapping DAE file paths to lists of mesh names
        """
        return self.dae_processor.extract_mesh_names_from_directory(dae_directory)

    def process_dae_files(self, dae_directory: str, output_directory: Optional[str] = None) -> bool:
        """
        Process DAE files to match JBeam group names

        Args:
            dae_directory: Directory containing DAE files to process
            output_directory: Directory for modified DAE files (if None, modifies in place)

        Returns:
            True if successful, False otherwise
        """
        return self.dae_processor.process_dae_files_for_rig(self, dae_directory, output_directory)

    def sync_dae_with_jbeam(self, dae_file_path: str, output_path: Optional[str] = None) -> bool:
        """
        Synchronize a single DAE file with JBeam mesh names

        IMPORTANT: This modifies DAE mesh names to match the "mesh" property values in JBeam output,
        NOT the group names. This ensures DAE files work correctly with the generated JBeam.

        Args:
            dae_file_path: Path to the DAE file to process
            output_path: Path for the modified DAE file (if None, overwrites original)

        Returns:
            True if successful, False otherwise
        """
        # Generate mesh mapping from current flexbodies and props
        mesh_mapping = self.dae_processor.generate_mesh_mapping(self.flexbodies, self.props)

        if not mesh_mapping:
            self.logger.info("No mesh mapping available for DAE synchronization")
            return True

        return self.dae_processor.modify_mesh_names(dae_file_path, mesh_mapping, output_path)

    def to_jbeam(self, filename):
      # sort beams by something so the jbeam doesn't look like a total mess
      self.beams.sort(key=lambda x: x.beamSpring, reverse=True)

      # Assign nodes to flexbody groups before writing
      self._assign_flexbody_groups()

      # open file and write it
      f = open(filename, 'w')
      f.write("{\n\t\"truck2jbeam\":{\n\t\t\"slotType\": \"main\",\n\n\t\t\"information\":{\n\t\t\t\"name\": \"" + self.name + "\",\n\t\t\t\"authors\": \"insert your name here\"\n\t\t}\n\n")

      # write refnodes
      if self.refnodes is not None:
        f.write("\t\t\"refNodes\":[\n\t\t\t[\"ref:\", \"back:\", \"left:\", \"up:\"],\n")
        f.write("\t\t\t[\"" + self.refnodes.center + "\", \"" + self.refnodes.back + "\", \"" + self.refnodes.left + "\", \"" + self.refnodes.center + "\"]\n")
        f.write("\t\t],\n\n")

      # write torquecurve
      if self.torquecurve is not None:
        f.write("\t\t\"enginetorque\":[\n\t\t\t[\"rpm\", \"torque\"],\n")

        # write curve, and multiply torque
        for t in self.torquecurve:
          f.write("\t\t\t[" + str(t[0]) + ", " + str(t[1] * self.engine.torque) + "],\n")

        f.write("\t\t],\n\n")

      # write engine
      if self.engine is not None:
        f.write("\t\t\"engine\":{\n")

        # idle/max RPM
        if self.engoption is None:
          f.write("\t\t\t\"idleRPM\":800,\n")
        else:
          f.write("\t\t\t\"idleRPM\":" + str(self.engoption.idle_rpm) + ",\n")

        f.write("\t\t\t\"maxRPM\":" + str(self.engine.max_rpm * 1.25) + ",\n")

        # shift RPMs
        f.write("\t\t\t\"shiftDownRPM\":" + str(self.engine.min_rpm) + ",\n")
        f.write("\t\t\t\"shiftUpRPM\":" + str(self.engine.max_rpm) + ",\n")

        # diff
        f.write("\t\t\t\"differential\":" + str(self.engine.differential) + ",\n")

        # inertia
        if self.engoption is None:
          f.write("\t\t\t\"inertia\":10,\n")
        else:
          f.write("\t\t\t\"inertia\":" + str(self.engoption.inertia) + ",\n")

        # ratios
        f.write("\t\t\t\"gears\":[")
        for g in self.engine.gears:
          f.write(str(g) + ", ")

        # seek before ratios last comma/spce
        f.seek(f.tell() - 2)
        f.write("],\n")

        # rest of engoption stuff
        if self.engoption is not None:
          f.write("\t\t\t\"clutchTorque\":" + str(self.engoption.clutch_force) + ",\n")
          f.write("\t\t\t\"clutchDuration\":" + str(self.engoption.clutch_time) + ",\n")

        f.write("\t\t}\n\n")


      # write cameras
      if len(self.internal_cameras) > 0:
        last_beam_spring = -1.0
        last_beam_damp = -1.0

        #     "camerasInternal":[
        #
        f.write("\t\t\"camerasInternal\":[\n\t\t\t[\"type\", \"x\", \"y\", \"z\", \"fov\", \"id1:\", \"id2:\", \"id3:\", \"id4:\", \"id5:\", \"id6:\"],\n\t\t\t{\"nodeWeight\": 20},\n")
        for c in self.internal_cameras:
            if c.beamSpring != last_beam_spring:
                last_beam_spring = c.beamSpring
                f.write("\t\t\t{\"beamSpring\":" + str(c.beamSpring) + "}\n")
            if c.beamDamp != last_beam_damp:
                last_beam_damp = c.beamDamp
                f.write("\t\t\t{\"beamDamp\":" + str(c.beamDamp) + "}\n")

            # write camera line
            f.write("\t\t\t[\"" + c.type + "\", " + str(c.x) + ", " + str(c.y) + ", " + str(c.z) + ", " + str(c.fov) + ", \"" + c.id1 + "\", \"" + c.id2 + "\", \"" + c.id3 + "\", \"" + c.id4 + "\", \"" + c.id5 + "\", \"" + c.id6 + "\"],\n")

        f.write("\t\t],\n\n")

      # write flexbodies (enhanced format)
      if len(self.flexbodies) > 0:
        f.write("\t\t\"flexbodies\":[\n\t\t\t[\"mesh\", \"[group]:\", \"nonFlexMaterials\"],\n")
        for fb in self.flexbodies:
          # Find reference nodes
          refnode = next((x for x in self.nodes if x.name == fb.refnode), None)
          xnode = next((x for x in self.nodes if x.name == fb.xnode), None)
          ynode = next((x for x in self.nodes if x.name == fb.ynode), None)

          if refnode is None or xnode is None or ynode is None:
            self.logger.warning(f"Can't find nodes for flexbody {fb.mesh}. Possibly forset on tires?")
            continue

          # Calculate position with coordinate system conversion
          # RoR coordinate system: X=right, Y=up, Z=forward
          # BeamNG coordinate system: X=right, Y=forward, Z=up
          # Apply coordinate system conversion to offset values
          real_x_offset = fb.offsetX   # X-axis stays the same (right)
          real_y_offset = fb.offsetZ   # RoR Z-offset (forward) becomes BeamNG Y-offset (forward)
          real_z_offset = fb.offsetY   # RoR Y-offset (up) becomes BeamNG Z-offset (up)

          # Convert RoR rotation to BeamNG rotation
          # Both RoR and BeamNG use degrees for rotations
          # RoR coordinate system: X=right, Y=up, Z=forward
          # BeamNG coordinate system: X=right, Y=forward, Z=up
          # Need to apply coordinate system conversion only

          # Apply coordinate system conversion (keep in degrees)
          # RoR rotations are applied in RoR's coordinate system, need to map to BeamNG's system
          real_x_rotation = fb.rotX   # Roll around X-axis (same in both systems)
          real_y_rotation = fb.rotZ   # Pitch: RoR Z-rotation becomes BeamNG Y-rotation
          real_z_rotation = fb.rotY   # Yaw: RoR Y-rotation becomes BeamNG Z-rotation

          # Get group name
          group_name = fb.get_group_name() if hasattr(fb, 'get_group_name') else parser.ParseGroupName(fb.mesh)

          # Get scale
          scale_x, scale_y, scale_z = (1, 1, 1)
          if hasattr(fb, 'scale'):
            scale_x, scale_y, scale_z = fb.scale

          # Get non-flex materials
          non_flex_materials = []
          if hasattr(fb, 'non_flex_materials'):
            non_flex_materials = fb.non_flex_materials

          # Write flexbody entry (use mesh name, not group name)
          mesh_name = fb.mesh
          if mesh_name.endswith('.mesh'):
              mesh_name = mesh_name[:-5]
          elif mesh_name.endswith('.dae'):
              mesh_name = mesh_name[:-4]

          f.write(f"\t\t\t[\"{mesh_name}\", [\"{group_name}\"], {json.dumps(non_flex_materials)}")

          # Add transform properties only if not disabled
          if not self.no_transform_properties:
            f.write(f", {{\"pos\":{{\"x\":{real_x_offset}, \"y\":{real_y_offset}, \"z\":{real_z_offset}}}, ")
            f.write(f"\"rot\":{{\"x\":{real_x_rotation}, \"y\":{real_y_rotation}, \"z\":{real_z_rotation}}}, ")
            f.write(f"\"scale\":{{\"x\":{scale_x}, \"y\":{scale_y}, \"z\":{scale_z}}}")

            # Add enhanced properties
            if hasattr(fb, 'disable_mesh_breaking') and fb.disable_mesh_breaking:
              f.write(f", \"disableMeshBreaking\":true")
            if hasattr(fb, 'plastic_deform_coef') and fb.plastic_deform_coef > 0:
              f.write(f", \"plasticDeformCoef\":{fb.plastic_deform_coef}")
            if hasattr(fb, 'damage_threshold') and fb.damage_threshold > 0:
              f.write(f", \"damageThreshold\":{fb.damage_threshold}")

            f.write("}")
          else:
            # Add enhanced properties without transform properties
            enhanced_props = []
            if hasattr(fb, 'disable_mesh_breaking') and fb.disable_mesh_breaking:
              enhanced_props.append(f"\"disableMeshBreaking\":true")
            if hasattr(fb, 'plastic_deform_coef') and fb.plastic_deform_coef > 0:
              enhanced_props.append(f"\"plasticDeformCoef\":{fb.plastic_deform_coef}")
            if hasattr(fb, 'damage_threshold') and fb.damage_threshold > 0:
              enhanced_props.append(f"\"damageThreshold\":{fb.damage_threshold}")

            if enhanced_props:
              f.write(f", {{{', '.join(enhanced_props)}}}")

          f.write("],\n")
        f.write("\t\t],\n\n")

      # write props (corrected BeamNG format)
      if len(self.props) > 0:
        f.write("\t\t\"props\":[\n\t\t\t[\"func\", \"mesh\", \"idRef:\", \"idX:\", \"idY:\", \"baseRotation\", \"rotation\", \"translation\", \"min\", \"max\", \"offset\", \"multiplier\"],\n")
        for prop in self.props:
          # Find reference nodes
          refnode = next((x for x in self.nodes if x.name == prop.refnode), None)
          xnode = next((x for x in self.nodes if x.name == prop.xnode), None)
          ynode = next((x for x in self.nodes if x.name == prop.ynode), None)

          if refnode is None or xnode is None or ynode is None:
            self.logger.warning(f"Can't find nodes for prop {prop.mesh}")
            continue

          # Get group name
          group_name = prop.get_group_name() if hasattr(prop, 'get_group_name') else parser.ParseGroupName(prop.mesh)

          # Convert RoR rotation to BeamNG rotation for props
          # Apply the same coordinate system conversion as flexbodies
          # Both RoR and BeamNG use degrees for rotations

          # Apply coordinate system conversion (keep in degrees)
          prop_x_rotation = prop.rotX   # Roll around X-axis (same in both systems)
          prop_y_rotation = prop.rotZ   # Pitch: RoR Z-rotation becomes BeamNG Y-rotation
          prop_z_rotation = prop.rotY   # Yaw: RoR Y-rotation becomes BeamNG Z-rotation

          # Calculate base rotation from converted values (BeamNG uses dictionary format)
          base_rotation = {"x": prop_x_rotation, "y": prop_y_rotation, "z": prop_z_rotation}

          # Set up animation parameters (BeamNG uses dictionary format)
          rotation = {"x": 0, "y": 0, "z": 0}
          translation = {"x": 0, "y": 0, "z": 0}
          min_val = 0
          max_val = 0
          offset = 0
          multiplier = 1

          if hasattr(prop, 'animation_factor') and prop.animation_factor != 0:
            if hasattr(prop, 'animation_mode'):
              if prop.animation_mode == "rotation":
                if hasattr(prop, 'animation_axis'):
                  rotation = {"x": prop.animation_axis[0], "y": prop.animation_axis[1], "z": prop.animation_axis[2]}
                multiplier = prop.animation_factor
                min_val = -180
                max_val = 180
              elif prop.animation_mode == "translation":
                if hasattr(prop, 'animation_axis'):
                  translation = {"x": prop.animation_axis[0], "y": prop.animation_axis[1], "z": prop.animation_axis[2]}
                multiplier = prop.animation_factor
                min_val = -1
                max_val = 1

          # Get mesh name (without extension)
          mesh_name = prop.mesh
          if mesh_name.endswith('.mesh'):
              mesh_name = mesh_name[:-5]
          elif mesh_name.endswith('.dae'):
              mesh_name = mesh_name[:-4]

          # Default function for non-animated props (BeamNG format)
          func = "nop"  # BeamNG function that always returns 0 for static props

          # Write prop entry in correct BeamNG format
          f.write(f"\t\t\t[\"{func}\", \"{mesh_name}\", \"{prop.refnode}\", \"{prop.xnode}\", \"{prop.ynode}\"")

          # Add transform properties only if not disabled
          if not self.no_transform_properties:
            f.write(f", {json.dumps(base_rotation)}, {json.dumps(rotation)}, {json.dumps(translation)}, ")
            f.write(f"{min_val}, {max_val}, {offset}, {multiplier}")

          f.write("],\n")
        f.write("\t\t],\n\n")

      # write nodes
      if len(self.nodes) > 0:
        last_node_mass = -1.0
        last_node_friction = 1.0
        last_selfcollision = False
        last_groups = []
        f.write("\t\t\"nodes\":[\n\t\t\t[\"id\", \"posX\", \"posY\", \"posZ\"],\n")
        for n in self.nodes:
            if n.mass != last_node_mass:
                f.write("\t\t\t{\"nodeWeight\": " + str(n.mass) + "},\n")
                last_node_mass = n.mass
            if n.frictionCoef != last_node_friction:
                f.write("\t\t\t{\"frictionCoef\": " + str(n.frictionCoef) + "},\n")
                last_node_friction = n.frictionCoef
            if n.selfCollision != last_selfcollision:
                f.write("\t\t\t{\"selfCollision\": " + str(n.selfCollision).lower() + "},\n")
                last_selfcollision = n.selfCollision
            if n.group != last_groups:
                if len(n.group) > 0:
                  f.write("\t\t\t{\"group\": [")
                  for g in n.group:
                    f.write("\"" + g + "\", ")
                  f.seek(f.tell() - 2, 0)
                  f.write("]},\n")
                else:
                  f.write("\t\t\t{\"group\": \"\"},\n")

                last_groups = n.group

            # write node line
            f.write("\t\t\t[\"" + n.name + "\", " + str(n.x) + ", " + str(n.y) + ", " + str(n.z))

            # write inline stuff
            if n.coupler:
                f.write(", {\"couplerTag\":\"fifthwheel\"}")

            f.write("],\n")
        f.write("\t\t],\n\n")

      # write beams
      if len(self.beams) > 0:
        last_beam_spring = -1.0
        last_beam_damp = -1.0
        last_beam_deform = -1.0
        last_beam_strength = -1.0
        last_beam_shortbound = -1.0
        last_beam_longbound = -1.0
        last_beam_precomp = -1.0
        last_beam_type = 'NONEXISTANT'
        last_beam_damprebound = False
        last_breakgroup = ''

        f.write("\t\t\"beams\":[\n\t\t\t[\"id1:\", \"id2:\"],\n")
        for b in self.beams:
            # write vars if changed
            if b.beamDampRebound != last_beam_damprebound:
                last_beam_damprebound = b.beamDampRebound
                f.write("\t\t\t{\"beamDampRebound\":" + str(b.beamDampRebound).lower() + "},\n")
            if b.type != last_beam_type:
                last_beam_type = b.type
                f.write("\t\t\t{\"beamType\":\"|" + b.type + "\"},\n")
            if b.beamSpring != last_beam_spring:
                last_beam_spring = b.beamSpring
                f.write("\t\t\t{\"beamSpring\":" + str(b.beamSpring) + "}\n")
            if b.beamDamp != last_beam_damp:
                last_beam_damp = b.beamDamp
                f.write("\t\t\t{\"beamDamp\":" + str(b.beamDamp) + "}\n")
            if b.beamDeform != last_beam_deform:
                last_beam_deform = b.beamDeform
                f.write("\t\t\t{\"beamDeform\":" + str(b.beamDeform) + "}\n")
            if b.beamStrength != last_beam_strength:
                last_beam_strength = b.beamStrength
                f.write("\t\t\t{\"beamStrength\":" + str(b.beamStrength) + "}\n")
            if b.beamShortBound != last_beam_shortbound:
                last_beam_shortbound = b.beamShortBound
                f.write("\t\t\t{\"beamShortBound\":" + str(b.beamShortBound) + "}\n")
            if b.beamLongBound != last_beam_longbound:
                last_beam_longbound = b.beamLongBound
                f.write("\t\t\t{\"beamLongBound\":" + str(b.beamLongBound) + "}\n")
            if b.beamPrecompression != last_beam_precomp:
                last_beam_precomp = b.beamPrecompression
                f.write("\t\t\t{\"beamPrecompression\":" + str(b.beamPrecompression) + "}\n")
            if b.breakGroup != last_breakgroup:
                last_breakgroup = b.breakGroup
                f.write("\t\t\t{\"breakGroup\":\"" + b.breakGroup + "\"}\n")
            # write beam line
            f.write("\t\t\t[\"" + b.id1 + "\", \"" + b.id2 + "\"],\n")

        f.write("\t\t],\n\n")

      # write rails (name, nodes are params)
      if len(self.rails) > 0:
        f.write("\t\t\"rails\":{\n")
        for r in self.rails:
          # start write rail line
          f.write("\t\t\t\"" + r.name + "\":{\"links:\":[")
          for n in r.nodes:
            f.write("\"" + n + "\", ")

          # seek before last comma, and overwrite it
          f.seek(f.tell() - 2, 0)

          # finish writing rail line
          f.write("], \"looped\":false, \"capped\":true}\n")

        f.write("\t\t}\n\n")

      # write slidenodes
      if len(self.slidenodes) > 0:
        f.write("\t\t\"slidenodes\":[\n\t\t\t[\"id:\", \"railName\", \"attached\", \"fixToRail\", \"tolerance\", \"spring\", \"strength\", \"capStrength\"],\n")
        for s in self.slidenodes:
          # write slidenode line
          f.write("\t\t\t[\"" + s.node + "\", \"" + s.rail + "\", true, true, " + str(s.tolerance) + ", " + str(s.spring) + ", " + str(s.strength).replace("inf", "100000000") + ", 345435],\n")
        f.write("\t\t],\n\n")

      # write diffs
      if len(self.axles) > 0:
        f.write("\t\t\"differentials\":[\n\t\t\t[\"wheelName1\", \"wheelName2\", \"type\", \"state\", \"closedTorque\", \"engineTorqueCoef\"],\n")
        for a in self.axles:
          f.write("\t\t\t[\"" + a.wid1 + "\", \"" + a.wid2 + "\", \"" + a.type + "\", \"" + a.state + "\", 10000, 1],\n")
        f.write("\t\t],\n\n")

      # write triangles (enhanced format)
      all_triangles = []

      # Add new Triangle objects
      for triangle in self.triangles:
          if hasattr(triangle, 'get_nodes'):  # New Triangle object
              all_triangles.append(triangle)
          else:  # Legacy format
              from rig_common import Triangle
              legacy_tri = Triangle(triangle[0], triangle[1], triangle[2], "collision")
              all_triangles.append(legacy_tri)

      # Add triangles from legacy submesh
      for triangle in self.legacy_triangles:
          from rig_common import Triangle
          legacy_tri = Triangle(triangle[0], triangle[1], triangle[2], "collision")
          all_triangles.append(legacy_tri)

      # Add triangles from converted quads
      for quad in self.quads:
          if hasattr(quad, 'to_triangles'):
              all_triangles.extend(quad.to_triangles())

      if all_triangles:
          # Separate collision and visual triangles
          collision_triangles = [t for t in all_triangles if t.is_collision()]
          visual_triangles = [t for t in all_triangles if t.is_visual() and not t.is_collision()]

          # Write collision triangles
          if collision_triangles:
              f.write("\t\t\"triangles\":[\n\t\t\t[\"id1:\", \"id2:\", \"id3:\"],\n")

              # Group by material and drag coefficient for optimization
              current_material = None
              current_drag = None

              for triangle in collision_triangles:
                  # Write material/drag coefficient changes
                  if triangle.material != current_material:
                      current_material = triangle.material
                      f.write(f"\t\t\t{{\"material\":\"|{current_material}\"}},\n")

                  if triangle.drag_coefficient != current_drag:
                      current_drag = triangle.drag_coefficient
                      f.write(f"\t\t\t{{\"dragCoef\":{current_drag}}},\n")

                  # Write triangle
                  f.write(f"\t\t\t[\"{triangle.node1}\", \"{triangle.node2}\", \"{triangle.node3}\"],\n")

              f.write("\t\t],\n\n")

          # Write visual triangles if any (for future BeamNG support)
          if visual_triangles:
              f.write("\t\t\"visualTriangles\":[\n\t\t\t[\"id1:\", \"id2:\", \"id3:\"],\n")

              current_material = None
              for triangle in visual_triangles:
                  if triangle.material != current_material:
                      current_material = triangle.material
                      f.write(f"\t\t\t{{\"material\":\"|{current_material}\"}},\n")

                  f.write(f"\t\t\t[\"{triangle.node1}\", \"{triangle.node2}\", \"{triangle.node3}\"],\n")

              f.write("\t\t],\n\n")

      # write wheels
      if len(self.wheels) > 0:
        last_wheel_spring = -1.0
        last_wheel_damp = -1.0
        last_tire_damp = -1.0
        last_tire_spring = -1.0
        last_numrays = -1
        last_width = -1
        last_hub_radius = -1
        last_radius = -1
        last_propulsed = 0
        last_mass = 0
        last_wheel_type = "NONE"

        c_wheel_idx = 0

        wrote_advanced_wheel = False

        f.write("\t\t\"pressureWheels\":[\n\t\t\t[\"name\",\"hubGroup\",\"group\",\"node1:\",\"node2:\",\"nodeS\",\"nodeArm:\",\"wheelDir\"],\n")
        if len(self.brakes) > 0:
          f.write("\t\t\t{\"brakeTorque\":" + str(self.brakes[0]) + ", \"parkingTorque\":" + str(self.brakes[1]) + "},\n")

        if self.rollon:
          f.write("\t\t\t{\"selfCollision\":true}\n")

        for w in self.wheels:
          # write global vars if changed
          if last_wheel_type != w.type:
            last_wheel_type = w.type
            if w.type == "wheels":
              f.write("\t\t\t{\"hasTire\":false},\n")
              f.write("\t\t\t{\"hubNodeMaterial\":\"|NM_RUBBER\"},\n")
            else:
              f.write("\t\t\t{\"hasTire\":true},\n")
              f.write("\t\t\t{\"hubNodeMaterial\":\"|NM_METAL\"},\n")

          if w.drivetype > 0 and last_propulsed == 0 and len(self.axles) == 0:
            last_propulsed = 1
            f.write("\t\t\t{\"propulsed\":" + str(last_propulsed) + "}\n")
          elif w.drivetype == 0 and last_propulsed == 1 and len(self.axles) == 0:
            last_propulsed = 0
            f.write("\t\t\t{\"propulsed\":" + str(last_propulsed) + "}\n")
          if w.width != last_width:
            last_width = w.width
            f.write("\t\t\t{\"hubWidth\":" + str(w.width) + "}\n")
            f.write("\t\t\t{\"tireWidth\":" + str(w.width) + "}\n")
          if w.num_rays != last_numrays:
            last_numrays = w.num_rays
            f.write("\t\t\t{\"numRays\":" + str(w.num_rays) + "}\n")
          if w.mass != last_mass:
            last_mass = w.mass
            if w.type == "wheels":
              f.write("\t\t\t{\"hubNodeWeight\":" + str(w.mass / (w.num_rays  * 2)) + "}\n")
            else:
              f.write("\t\t\t{\"nodeWeight\":" + str(w.mass / (w.num_rays  * 4)) + "}\n")
              f.write("\t\t\t{\"hubNodeWeight\":" + str(w.mass / (w.num_rays  * 4)) + "}\n")

          # basic wheels
          if w.type == "wheels":
            if w.spring != last_wheel_spring:
              last_wheel_spring = w.spring
              f.write("\t\t\t{\"beamSpring\":" + str(w.spring) + "}\n")
            if w.damp != last_wheel_damp:
              last_wheel_damp = w.damp
              f.write("\t\t\t{\"beamDamp\":" + str(w.damp) + "}\n")
            if w.radius != last_hub_radius:
              last_hub_radius = w.radius
              f.write("\t\t\t{\"hubRadius\":" + str(w.radius) + "}\n")


          # advanced wheels
          if w.type == "wheels.advanced":
            # first things first, 'global' stuff
            if not wrote_advanced_wheel:
              wrote_advanced_wheel = True
              f.write("\t\t\t{\"disableMeshBreaking\":true}\n")
              f.write("\t\t\t{\"disableHubMeshBreaking\":false}\n")
              f.write("\t\t\t{\"enableTireReinfBeams\":true}\n")
              f.write("\t\t\t{\"pressurePSI\":30}\n")

            if w.hub_spring != last_wheel_spring:
              last_wheel_spring = w.hub_spring
              f.write("\t\t\t{\"beamSpring\":" + str(w.hub_spring) + "}\n")
            if w.hub_damp != last_wheel_damp:
              last_wheel_damp = w.hub_damp
              f.write("\t\t\t{\"beamDamp\":" + str(w.hub_damp) + "}\n")
            if w.tire_damp != last_tire_damp:
              last_tire_damp = w.tire_damp
              f.write("\t\t\t{\"wheelSideBeamDamp\":" + str(w.tire_damp) + "}\n")
              f.write("\t\t\t{\"wheelSideBeamDampExpansion\":" + str(w.tire_damp) + "}\n")
              f.write("\t\t\t{\"wheelReinfBeamDamp\":" + str(w.tire_damp) + "}\n")
              f.write("\t\t\t{\"wheelTreadBeamDamp\":" + str(w.tire_damp) + "}\n")
              f.write("\t\t\t{\"wheelPeripheryBeamDamp\":" + str(w.tire_damp) + "}\n")
            if w.tire_spring != last_tire_spring:
              last_tire_spring = w.tire_spring
              f.write("\t\t\t{\"wheelSideBeamSpringExpansion\":" + str(w.tire_spring) + "}\n")
              f.write("\t\t\t{\"wheelReinfBeamSpring\":" + str(w.tire_spring) + "}\n")
              f.write("\t\t\t{\"wheelTreadBeamSpring\":" + str(w.tire_spring) + "}\n")
              f.write("\t\t\t{\"wheelPeripheryBeamSpring\":" + str(w.tire_spring) + "}\n")
            if w.tire_radius != last_radius:
              last_radius = w.tire_radius
              f.write("\t\t\t{\"radius\":" + str(w.tire_radius) + "}\n")

          # write wheel line
          snode = "\"" + w.snode + "\"" if w.snode != "node9999" else 9999
          drivetype = -1 if w.drivetype == 2 else w.drivetype
          f.write("\t\t\t[\"rorwheel" + str(c_wheel_idx) + "\", \"none\", \"none\", \"" + w.nid1 + "\", \"" + w.nid2 + "\", "  + str(snode) + ", \"" + w.armnode + "\", " + str(drivetype) + "],\n\n")

          #increment wheel ID
          c_wheel_idx += 1
        f.write("\t\t],\n\n")


      # write hydros
      if len(self.hydros) > 0:
        last_beam_spring = -1.0
        last_beam_damp = -1.0
        last_beam_deform = -1.0
        last_beam_strength = -1.0

        f.write("\t\t\"hydros\":[\n\t\t\t[\"id1:\", \"id2:\"],\n")
        for h in self.hydros:
            # write vars if changed
            if h.beamSpring != last_beam_spring:
                last_beam_spring = h.beamSpring
                f.write("\t\t\t{\"beamSpring\":" + str(h.beamSpring) + "}\n")
            if h.beamDamp != last_beam_damp:
                last_beam_damp = h.beamDamp
                f.write("\t\t\t{\"beamDamp\":" + str(h.beamDamp) + "}\n")
            if h.beamDeform != last_beam_deform:
                last_beam_deform = h.beamDeform
                f.write("\t\t\t{\"beamDeform\":" + str(h.beamDeform) + "}\n")
            if h.beamStrength != last_beam_strength:
                last_beam_strength = h.beamStrength
                f.write("\t\t\t{\"beamStrength\":" + str(h.beamStrength) + "}\n")

            # write hydro line
            f.write("\t\t\t[\"" + h.id1 + "\", \"" + h.id2 + "\", {\"inputSource\": \"steering\", \"inputFactor\": " + str(h.factor) + ", \"inRate\": 0.25, \"outRate\": 0.25}],\n")

        f.write("\t\t],\n")


      f.write("\t}\n}")
      f.close()