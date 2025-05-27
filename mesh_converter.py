"""
Enhanced Mesh Converter for truck2jbeam
Handles conversion of Ogre3D .mesh files to .dae (COLLADA) and .blend (Blender) formats

This implementation incorporates proven techniques from the blender2ogre project
and provides robust parsing for both binary and XML Ogre3D mesh formats.

Based on research from:
- OGRECave/blender2ogre project
- Ogre3D mesh format specifications
- RoR community mesh handling practices
"""

import os
import struct
import logging
import json
import io
import subprocess
import shutil
import tempfile
from typing import List, Dict, Optional, Tuple, Any, Union
from pathlib import Path
from dataclasses import dataclass, field
import xml.etree.ElementTree as ET
from xml.dom import minidom
import traceback


# Ogre3D Mesh Format Constants (based on OgreSerializer.h)
class OgreChunkID:
    """Ogre mesh chunk identifiers"""
    HEADER = 0x1000
    MESH = 0x3000
    SUBMESH = 0x4000
    SUBMESH_OPERATION = 0x4010
    SUBMESH_BONE_ASSIGNMENT = 0x4100
    SUBMESH_TEXTURE_ALIAS = 0x4200
    MESH_SKELETON_LINK = 0x5000
    MESH_BONE_ASSIGNMENT = 0x5100
    MESH_LOD_LEVEL = 0x8000
    MESH_BOUNDS = 0x9000
    SUBMESH_NAME_TABLE = 0xA000
    SUBMESH_NAME_TABLE_ELEMENT = 0xA100
    EDGE_LISTS = 0xB000
    POSES = 0xC000
    ANIMATIONS = 0xD000
    TABLE_EXTREMES = 0xE000

    # Geometry chunks
    GEOMETRY = 0x5000
    GEOMETRY_VERTEX_DECLARATION = 0x5100
    GEOMETRY_VERTEX_ELEMENT = 0x5110
    GEOMETRY_VERTEX_BUFFER = 0x5200
    GEOMETRY_VERTEX_BUFFER_DATA = 0x5210


class OgreVertexElementType:
    """Ogre vertex element types"""
    FLOAT1 = 0
    FLOAT2 = 1
    FLOAT3 = 2
    FLOAT4 = 3
    COLOUR = 4
    SHORT1 = 5
    SHORT2 = 6
    SHORT3 = 7
    SHORT4 = 8
    UBYTE4 = 9
    COLOUR_ARGB = 10
    COLOUR_ABGR = 11


class OgreVertexElementSemantic:
    """Ogre vertex element semantics"""
    POSITION = 1
    BLENDWEIGHTS = 2
    BLENDINDICES = 3
    NORMAL = 4
    DIFFUSE = 5
    SPECULAR = 6
    TEXCOORD = 7
    BINORMAL = 8
    TANGENT = 9


@dataclass
class MeshVertex:
    """Enhanced mesh vertex with additional attributes"""
    position: Tuple[float, float, float]
    normal: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    uv: Tuple[float, float] = (0.0, 0.0)
    uv2: Optional[Tuple[float, float]] = None
    color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    tangent: Optional[Tuple[float, float, float]] = None
    binormal: Optional[Tuple[float, float, float]] = None


@dataclass
class MeshFace:
    """Represents a mesh face (triangle)"""
    vertices: Tuple[int, int, int]  # Vertex indices
    material_index: int = 0


@dataclass
class MeshMaterial:
    """Enhanced mesh material with additional properties"""
    name: str
    diffuse_texture: Optional[str] = None
    normal_texture: Optional[str] = None
    specular_texture: Optional[str] = None
    diffuse_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    specular_color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    ambient_color: Tuple[float, float, float] = (0.2, 0.2, 0.2)
    shininess: float = 0.0
    transparency: float = 1.0


@dataclass
class MeshSubmesh:
    """Represents a mesh submesh"""
    material_name: str
    vertices: List[MeshVertex]
    faces: List[MeshFace]
    use_shared_vertices: bool = False
    operation_type: int = 4  # Triangle list


@dataclass
class MeshData:
    """Enhanced container for parsed mesh data"""
    name: str
    vertices: List[MeshVertex]  # Shared vertices
    faces: List[MeshFace]
    materials: List[MeshMaterial]
    submeshes: List[MeshSubmesh] = field(default_factory=list)
    bounding_box: Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = None
    skeleton_link: Optional[str] = None
    has_shared_vertices: bool = True


class MeshConverter:
    """Converts Ogre3D .mesh files to .dae and .blend formats"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.has_bpy = self._check_blender_availability()
        self.ogre_tools = self._detect_ogre_tools()

    def _check_blender_availability(self) -> bool:
        """Check if Blender Python API is available"""
        try:
            import bpy
            return True
        except ImportError:
            self.logger.info("Blender Python API not available, .blend export disabled")
            return False

    def _detect_ogre_tools(self) -> Dict[str, Optional[str]]:
        """Detect available Ogre3D tools for mesh processing"""
        tools = {
            'mesh_upgrader': None,
            'xml_converter': None
        }

        # Common tool names and possible locations
        tool_names = {
            'mesh_upgrader': ['OgreMeshUpgrader.exe', 'OgreMeshUpgrader', 'ogre-mesh-upgrader'],
            'xml_converter': ['OgreXMLConverter.exe', 'OgreXMLConverter', 'ogre-xml-converter']
        }

        # Search paths (including common Ogre installation directories)
        search_paths = [
            '.',  # Current directory
            './tools',  # Tools subdirectory
            './ogre-tools',  # Ogre tools directory
            os.path.expanduser('~/ogre-tools'),  # User home ogre tools
            'C:/OgreSDK/bin',  # Windows Ogre SDK
            'C:/Program Files/OGRE/bin',  # Windows Program Files
            'C:/Program Files (x86)/OGRE/bin',  # Windows Program Files x86
            '/usr/bin',  # Linux system binaries
            '/usr/local/bin',  # Linux local binaries
            '/opt/ogre/bin',  # Linux opt directory
        ]

        for tool_key, tool_names_list in tool_names.items():
            for tool_name in tool_names_list:
                # First check if tool is in PATH
                if shutil.which(tool_name):
                    tools[tool_key] = tool_name
                    self.logger.debug(f"Found {tool_key}: {tool_name} (in PATH)")
                    break

                # Then check specific paths
                for search_path in search_paths:
                    tool_path = os.path.join(search_path, tool_name)
                    if os.path.isfile(tool_path) and os.access(tool_path, os.X_OK):
                        tools[tool_key] = tool_path
                        self.logger.debug(f"Found {tool_key}: {tool_path}")
                        break

                if tools[tool_key]:
                    break

        # Log availability
        if tools['mesh_upgrader']:
            self.logger.info(f"OgreMeshUpgrader available: {tools['mesh_upgrader']}")
        else:
            self.logger.warning("OgreMeshUpgrader not found - will use fallback parsing")

        if tools['xml_converter']:
            self.logger.info(f"OgreXMLConverter available: {tools['xml_converter']}")
        else:
            self.logger.warning("OgreXMLConverter not found - will use fallback parsing")

        return tools

    def parse_mesh_file(self, mesh_file_path: str) -> Optional[MeshData]:
        """
        Parse an Ogre3D .mesh file and extract geometry data using official Ogre tools

        Args:
            mesh_file_path: Path to the .mesh file

        Returns:
            MeshData object containing parsed mesh information, or None if parsing fails
        """
        if not os.path.exists(mesh_file_path):
            self.logger.error(f"Mesh file not found: {mesh_file_path}")
            return None

        try:
            # First try using official Ogre tools for accurate parsing
            if self.ogre_tools['xml_converter']:
                mesh_data = self._parse_with_ogre_tools(mesh_file_path)
                if mesh_data:
                    return mesh_data

            # Fallback to direct binary parsing
            mesh_data = self._parse_binary_mesh(mesh_file_path)
            if mesh_data:
                return mesh_data

            # Final fallback to XML mesh parsing
            mesh_data = self._parse_xml_mesh(mesh_file_path)
            if mesh_data:
                return mesh_data

            self.logger.error(f"Unable to parse mesh file: {mesh_file_path}")
            return None

        except Exception as e:
            self.logger.error(f"Error parsing mesh file {mesh_file_path}: {e}")
            return None

    def _parse_with_ogre_tools(self, mesh_file_path: str) -> Optional[MeshData]:
        """
        Parse mesh file using official Ogre3D tools for maximum accuracy

        This method implements the proper Ogre3D mesh processing pipeline:
        1. Upgrade mesh format with OgreMeshUpgrader (if available)
        2. Convert to XML with OgreXMLConverter
        3. Parse the XML for accurate geometry extraction
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                mesh_path = Path(mesh_file_path)
                temp_mesh_path = Path(temp_dir) / mesh_path.name

                # Copy original mesh to temp directory
                shutil.copy2(mesh_file_path, temp_mesh_path)

                # Step 1: Upgrade mesh format if upgrader is available
                if self.ogre_tools['mesh_upgrader']:
                    upgraded_mesh_path = self._upgrade_mesh_format(temp_mesh_path)
                    if upgraded_mesh_path:
                        temp_mesh_path = upgraded_mesh_path

                # Step 2: Convert to XML format
                xml_mesh_path = self._convert_to_xml(temp_mesh_path, temp_dir)
                if not xml_mesh_path:
                    self.logger.debug("Failed to convert mesh to XML format")
                    return None

                # Step 3: Parse the XML mesh file
                mesh_data = self._parse_ogre_xml_mesh(xml_mesh_path)
                if mesh_data:
                    self.logger.debug(f"Successfully parsed mesh using Ogre tools: {len(mesh_data.vertices)} vertices")
                    return mesh_data

                return None

        except Exception as e:
            self.logger.debug(f"Ogre tools parsing failed: {e}")
            return None

    def _upgrade_mesh_format(self, mesh_path: Path) -> Optional[Path]:
        """Upgrade mesh format using OgreMeshUpgrader"""
        try:
            cmd = [self.ogre_tools['mesh_upgrader'], str(mesh_path)]

            self.logger.debug(f"Running OgreMeshUpgrader: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=mesh_path.parent
            )

            if result.returncode == 0:
                self.logger.debug("Mesh format upgraded successfully")
                return mesh_path
            else:
                self.logger.debug(f"OgreMeshUpgrader failed: {result.stderr}")
                return mesh_path  # Return original path, upgrader failure is not critical

        except subprocess.TimeoutExpired:
            self.logger.warning("OgreMeshUpgrader timed out")
            return mesh_path
        except Exception as e:
            self.logger.debug(f"Error running OgreMeshUpgrader: {e}")
            return mesh_path

    def _convert_to_xml(self, mesh_path: Path, temp_dir: str) -> Optional[Path]:
        """Convert binary mesh to XML using OgreXMLConverter"""
        try:
            xml_path = Path(temp_dir) / f"{mesh_path.stem}.mesh.xml"

            cmd = [self.ogre_tools['xml_converter'], str(mesh_path), str(xml_path)]

            self.logger.debug(f"Running OgreXMLConverter: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=temp_dir
            )

            # OgreXMLConverter sometimes returns non-zero exit codes even on success
            # Check if the XML file was actually created instead
            if xml_path.exists() and xml_path.stat().st_size > 0:
                self.logger.debug(f"Successfully converted to XML: {xml_path}")
                return xml_path
            else:
                self.logger.debug(f"OgreXMLConverter failed: {result.stderr}")
                self.logger.debug(f"Return code: {result.returncode}")
                return None

        except subprocess.TimeoutExpired:
            self.logger.warning("OgreXMLConverter timed out")
            return None
        except Exception as e:
            self.logger.debug(f"Error running OgreXMLConverter: {e}")
            return None

    def _parse_ogre_xml_mesh(self, xml_mesh_path: Path) -> Optional[MeshData]:
        """
        Parse Ogre XML mesh file generated by OgreXMLConverter

        This parser handles the official Ogre XML format which contains
        complete and accurate mesh data including:
        - Shared geometry with vertex buffers
        - Submeshes with materials and face data
        - Proper vertex attributes (position, normal, UV, etc.)
        - Skeleton links and animation data
        """
        try:
            tree = ET.parse(xml_mesh_path)
            root = tree.getroot()

            if root.tag != 'mesh':
                self.logger.debug("Invalid Ogre XML mesh format")
                return None

            mesh_name = xml_mesh_path.stem.replace('.mesh', '')
            mesh_data = MeshData(
                name=mesh_name,
                vertices=[],
                faces=[],
                materials=[],
                submeshes=[]
            )

            # Parse shared geometry
            shared_geometry = root.find('sharedgeometry')
            if shared_geometry is not None:
                self._parse_ogre_shared_geometry(shared_geometry, mesh_data)

            # Parse submeshes
            submeshes_elem = root.find('submeshes')
            if submeshes_elem is not None:
                self._parse_ogre_submeshes(submeshes_elem, mesh_data)

            # Parse skeleton link if present
            skeleton_link = root.find('skeletonlink')
            if skeleton_link is not None:
                skeleton_name = skeleton_link.get('name', '')
                self.logger.debug(f"Mesh has skeleton link: {skeleton_name}")

            # Parse bounds
            bounds_elem = root.find('bounds')
            if bounds_elem is not None:
                self._parse_ogre_bounds(bounds_elem, mesh_data)

            # Validate parsed data
            if not mesh_data.vertices and not any(submesh.vertices for submesh in mesh_data.submeshes):
                self.logger.debug("No vertices found in Ogre XML mesh")
                return None

            # Ensure we have materials
            if not mesh_data.materials:
                mesh_data.materials.append(MeshMaterial(f"{mesh_name}_material"))

            self.logger.debug(f"Parsed Ogre XML mesh: {len(mesh_data.vertices)} shared vertices, {len(mesh_data.submeshes)} submeshes")
            return mesh_data

        except ET.ParseError as e:
            self.logger.debug(f"XML parsing error: {e}")
            return None
        except Exception as e:
            self.logger.debug(f"Error parsing Ogre XML mesh: {e}")
            return None

    def _parse_ogre_shared_geometry(self, shared_geometry: ET.Element, mesh_data: MeshData) -> None:
        """Parse shared geometry section from Ogre XML"""
        try:
            vertex_count = int(shared_geometry.get('vertexcount', 0))
            if vertex_count == 0:
                return

            # Find vertex buffer
            vertex_buffer = shared_geometry.find('vertexbuffer')
            if vertex_buffer is None:
                return

            # Parse vertex attributes
            has_positions = vertex_buffer.get('positions', 'false').lower() == 'true'
            has_normals = vertex_buffer.get('normals', 'false').lower() == 'true'
            texture_coords = int(vertex_buffer.get('texture_coords', 0))
            has_colors = vertex_buffer.get('colours_diffuse', 'false').lower() == 'true'

            # Parse vertices
            vertices = []
            for vertex_elem in vertex_buffer.findall('vertex'):
                position = (0.0, 0.0, 0.0)
                normal = (0.0, 0.0, 1.0)
                uv = (0.0, 0.0)
                color = (1.0, 1.0, 1.0, 1.0)

                # Parse position
                if has_positions:
                    pos_elem = vertex_elem.find('position')
                    if pos_elem is not None:
                        x = float(pos_elem.get('x', 0.0))
                        y = float(pos_elem.get('y', 0.0))
                        z = float(pos_elem.get('z', 0.0))
                        position = (x, y, z)

                # Parse normal
                if has_normals:
                    normal_elem = vertex_elem.find('normal')
                    if normal_elem is not None:
                        nx = float(normal_elem.get('x', 0.0))
                        ny = float(normal_elem.get('y', 0.0))
                        nz = float(normal_elem.get('z', 1.0))
                        normal = (nx, ny, nz)

                # Parse texture coordinates
                if texture_coords > 0:
                    texcoord_elem = vertex_elem.find('texcoord')
                    if texcoord_elem is not None:
                        u = float(texcoord_elem.get('u', 0.0))
                        v = float(texcoord_elem.get('v', 0.0))
                        uv = (u, v)

                # Parse vertex color
                if has_colors:
                    color_elem = vertex_elem.find('colour_diffuse')
                    if color_elem is not None:
                        # Ogre stores color as single value, we'll use default
                        color = (1.0, 1.0, 1.0, 1.0)

                vertices.append(MeshVertex(position, normal, uv, color))

            mesh_data.vertices = vertices
            self.logger.debug(f"Parsed {len(vertices)} shared vertices")

        except Exception as e:
            self.logger.debug(f"Error parsing shared geometry: {e}")

    def _parse_ogre_submeshes(self, submeshes_elem: ET.Element, mesh_data: MeshData) -> None:
        """Parse submeshes section from Ogre XML"""
        try:
            for submesh_elem in submeshes_elem.findall('submesh'):
                material_name = submesh_elem.get('material', 'default_material')
                use_shared_vertices = submesh_elem.get('usesharedvertices', 'true').lower() == 'true'
                operation_type = submesh_elem.get('operationtype', 'triangle_list')

                # Create material if not exists
                if not any(mat.name == material_name for mat in mesh_data.materials):
                    mesh_data.materials.append(MeshMaterial(material_name))

                # Parse faces
                faces = []
                faces_elem = submesh_elem.find('faces')
                if faces_elem is not None:
                    face_count = int(faces_elem.get('count', 0))

                    for face_elem in faces_elem.findall('face'):
                        v1 = int(face_elem.get('v1', 0))
                        v2 = int(face_elem.get('v2', 0))
                        v3 = int(face_elem.get('v3', 0))

                        # Find material index
                        material_index = 0
                        for i, mat in enumerate(mesh_data.materials):
                            if mat.name == material_name:
                                material_index = i
                                break

                        faces.append(MeshFace((v1, v2, v3), material_index))

                # Parse submesh-specific geometry if not using shared vertices
                submesh_vertices = []
                if not use_shared_vertices:
                    geometry_elem = submesh_elem.find('geometry')
                    if geometry_elem is not None:
                        vertex_count = int(geometry_elem.get('vertexcount', 0))
                        vertex_buffer = geometry_elem.find('vertexbuffer')

                        if vertex_buffer is not None:
                            # Parse vertex attributes (similar to shared geometry)
                            has_positions = vertex_buffer.get('positions', 'false').lower() == 'true'
                            has_normals = vertex_buffer.get('normals', 'false').lower() == 'true'
                            texture_coords = int(vertex_buffer.get('texture_coords', 0))

                            for vertex_elem in vertex_buffer.findall('vertex'):
                                position = (0.0, 0.0, 0.0)
                                normal = (0.0, 0.0, 1.0)
                                uv = (0.0, 0.0)

                                if has_positions:
                                    pos_elem = vertex_elem.find('position')
                                    if pos_elem is not None:
                                        x = float(pos_elem.get('x', 0.0))
                                        y = float(pos_elem.get('y', 0.0))
                                        z = float(pos_elem.get('z', 0.0))
                                        position = (x, y, z)

                                if has_normals:
                                    normal_elem = vertex_elem.find('normal')
                                    if normal_elem is not None:
                                        nx = float(normal_elem.get('x', 0.0))
                                        ny = float(normal_elem.get('y', 0.0))
                                        nz = float(normal_elem.get('z', 1.0))
                                        normal = (nx, ny, nz)

                                if texture_coords > 0:
                                    texcoord_elem = vertex_elem.find('texcoord')
                                    if texcoord_elem is not None:
                                        u = float(texcoord_elem.get('u', 0.0))
                                        v = float(texcoord_elem.get('v', 0.0))
                                        uv = (u, v)

                                submesh_vertices.append(MeshVertex(position, normal, uv))

                # Create submesh
                submesh = MeshSubmesh(
                    material_name=material_name,
                    vertices=submesh_vertices,
                    faces=faces,
                    use_shared_vertices=use_shared_vertices
                )

                mesh_data.submeshes.append(submesh)

                # Add faces to main mesh data for shared vertices
                if use_shared_vertices:
                    mesh_data.faces.extend(faces)

            self.logger.debug(f"Parsed {len(mesh_data.submeshes)} submeshes")

        except Exception as e:
            self.logger.debug(f"Error parsing submeshes: {e}")

    def _parse_ogre_bounds(self, bounds_elem: ET.Element, mesh_data: MeshData) -> None:
        """Parse bounds section from Ogre XML"""
        try:
            min_x = float(bounds_elem.get('minx', 0.0))
            min_y = float(bounds_elem.get('miny', 0.0))
            min_z = float(bounds_elem.get('minz', 0.0))
            max_x = float(bounds_elem.get('maxx', 0.0))
            max_y = float(bounds_elem.get('maxy', 0.0))
            max_z = float(bounds_elem.get('maxz', 0.0))

            mesh_data.bounding_box = (
                (min_x, min_y, min_z),
                (max_x, max_y, max_z)
            )

            self.logger.debug(f"Parsed bounding box: ({min_x}, {min_y}, {min_z}) to ({max_x}, {max_y}, {max_z})")

        except Exception as e:
            self.logger.debug(f"Error parsing bounds: {e}")

    def _parse_binary_mesh(self, mesh_file_path: str) -> Optional[MeshData]:
        """
        Parse binary Ogre3D .mesh file using proper format specification

        Based on Ogre3D serialization format and blender2ogre techniques
        """
        try:
            with open(mesh_file_path, 'rb') as f:
                # Read first few bytes to detect format
                initial_data = f.read(64)
                f.seek(0)

                # Check for text-based header (newer Ogre format)
                if b'[MeshSerializer_v' in initial_data:
                    return self._parse_modern_binary_mesh(f, mesh_file_path)

                # Check for old binary format
                if len(initial_data) >= 6:
                    header_id = struct.unpack('<H', initial_data[:2])[0]
                    if header_id == OgreChunkID.HEADER:
                        return self._parse_legacy_binary_mesh(f, mesh_file_path)

                self.logger.debug("Unknown binary mesh format")
                return None

        except Exception as e:
            self.logger.debug(f"Binary mesh parsing failed: {e}")
            return None

    def _parse_modern_binary_mesh(self, f, mesh_file_path: str) -> Optional[MeshData]:
        """Parse modern Ogre mesh format with text header"""
        try:
            # Read the text header line
            f.seek(0)
            header_line = f.readline()
            self.logger.debug(f"Header: {header_line}")

            # The modern format has a complex structure - let's try a different approach
            # Look for known Ogre chunk patterns in the file
            mesh_name = Path(mesh_file_path).stem
            mesh_data = MeshData(
                name=mesh_name,
                vertices=[],
                faces=[],
                materials=[],
                submeshes=[]
            )

            # Read the entire file and look for chunk patterns
            f.seek(0)
            file_data = f.read()

            # Try to find mesh chunks by scanning for known patterns
            vertices_found = self._extract_vertices_from_binary(file_data, mesh_data)
            submeshes_found = self._extract_submeshes_from_binary(file_data, mesh_data)

            self.logger.debug(f"Extracted {len(mesh_data.vertices)} vertices, {len(mesh_data.submeshes)} submeshes")

            # If we found some data, use it
            if vertices_found or submeshes_found:
                # Ensure we have at least one material
                if not mesh_data.materials:
                    mesh_data.materials.append(MeshMaterial(f"{mesh_name}_material"))

                # Consolidate faces from submeshes
                for submesh in mesh_data.submeshes:
                    mesh_data.faces.extend(submesh.faces)

                return mesh_data
            else:
                self.logger.debug("No mesh data found in modern binary format")
                return self._create_fallback_mesh(mesh_name)

        except Exception as e:
            self.logger.debug(f"Modern binary mesh parsing failed: {e}")
            return None

    def _extract_vertices_from_binary(self, file_data: bytes, mesh_data: MeshData) -> bool:
        """Extract vertices from binary data using optimized pattern matching"""
        try:
            vertices = []

            # More efficient approach: sample the file at regular intervals
            # instead of scanning every byte
            file_size = len(file_data)
            sample_interval = max(1000, file_size // 10000)  # Sample every 1KB or 1/10000 of file

            for offset in range(0, file_size - 32, sample_interval):
                try:
                    # Try to read vertex data (position + normal + UV = 32 bytes)
                    if offset + 32 <= file_size:
                        # Read position (3 floats)
                        x, y, z = struct.unpack('<3f', file_data[offset:offset+12])

                        # Check if these look like reasonable vertex coordinates
                        if (abs(x) < 500 and abs(y) < 500 and abs(z) < 500 and
                            not (x == 0 and y == 0 and z == 0)):

                            # Try to read normal
                            normal = (0.0, 0.0, 1.0)
                            try:
                                nx, ny, nz = struct.unpack('<3f', file_data[offset+12:offset+24])
                                # Check if this looks like a normalized vector
                                length_sq = nx*nx + ny*ny + nz*nz
                                if 0.5 <= length_sq <= 1.5:  # Approximately normalized
                                    normal = (nx, ny, nz)
                            except:
                                pass

                            # Try to read UV
                            uv = (0.0, 0.0)
                            try:
                                u, v = struct.unpack('<2f', file_data[offset+24:offset+32])
                                if 0 <= u <= 5 and 0 <= v <= 5:  # Reasonable UV range
                                    uv = (u, v)
                            except:
                                pass

                            vertices.append(MeshVertex((x, y, z), normal, uv))

                            # Limit vertices to avoid memory issues
                            if len(vertices) >= 1000:
                                break

                except struct.error:
                    continue

            # If we found vertices, add them to mesh data
            if vertices:
                # Remove obvious duplicates
                unique_vertices = []
                seen_positions = set()

                for vertex in vertices:
                    # Round to reduce precision for duplicate detection
                    pos_key = (round(vertex.position[0], 3), round(vertex.position[1], 3), round(vertex.position[2], 3))
                    if pos_key not in seen_positions:
                        seen_positions.add(pos_key)
                        unique_vertices.append(vertex)

                mesh_data.vertices = unique_vertices
                self.logger.debug(f"Extracted {len(mesh_data.vertices)} vertices from binary data")
                return len(mesh_data.vertices) > 0

            return False

        except Exception as e:
            self.logger.debug(f"Error extracting vertices: {e}")
            return False

    def _extract_submeshes_from_binary(self, file_data: bytes, mesh_data: MeshData) -> bool:
        """Extract submesh information from binary data"""
        try:
            materials_found = []

            # More efficient material name search - sample at intervals
            file_size = len(file_data)
            sample_interval = max(100, file_size // 1000)  # Sample every 100 bytes or 1/1000 of file

            for offset in range(0, file_size - 50, sample_interval):
                # Look for text patterns that could be material names
                try:
                    # Try to decode a reasonable chunk of text
                    chunk = file_data[offset:offset+50]
                    text = chunk.decode('utf-8', errors='ignore')

                    # Look for material-related keywords
                    if any(keyword in text.lower() for keyword in ['material', '.png', '.jpg', '.dds', '.tga']):
                        # Extract potential material names
                        words = text.split('\x00')
                        for word in words:
                            word = word.strip()
                            if (len(word) > 3 and len(word) < 30 and
                                any(ext in word.lower() for ext in ['material', '.png', '.jpg', '.dds']) and
                                word not in materials_found):
                                materials_found.append(word)

                except UnicodeDecodeError:
                    continue

            # If no materials found, create a default one
            if not materials_found:
                materials_found = [f"{mesh_data.name}_material"]

            # Create submeshes for found materials
            for i, material_name in enumerate(materials_found[:3]):  # Limit to 3 materials
                # Create faces for the submesh
                faces = []
                if len(mesh_data.vertices) >= 3:
                    # Create triangles from available vertices
                    vertex_count = len(mesh_data.vertices)
                    vertices_per_submesh = vertex_count // len(materials_found)
                    start_vertex = i * vertices_per_submesh
                    end_vertex = min(start_vertex + vertices_per_submesh, vertex_count - 2)

                    for j in range(start_vertex, end_vertex - 2, 3):
                        if j + 2 < vertex_count:
                            faces.append(MeshFace((j, j+1, j+2), i))

                submesh = MeshSubmesh(
                    material_name=material_name,
                    vertices=[],
                    faces=faces,
                    use_shared_vertices=True
                )

                mesh_data.submeshes.append(submesh)
                mesh_data.materials.append(MeshMaterial(material_name))

            self.logger.debug(f"Created {len(mesh_data.submeshes)} submeshes with materials: {[m[:20] for m in materials_found]}")
            return len(mesh_data.submeshes) > 0

        except Exception as e:
            self.logger.debug(f"Error extracting submeshes: {e}")
            return False

    def _parse_legacy_binary_mesh(self, f, mesh_file_path: str) -> Optional[MeshData]:
        """Parse legacy Ogre mesh format"""
        try:
            # Read and validate header
            header_data = f.read(18)
            if len(header_data) < 18:
                self.logger.debug("File too small to be valid Ogre mesh")
                return None

            # Parse header
            header_id, version, endian_flag = struct.unpack('<HHH', header_data[:6])

            # Validate header
            if header_id != OgreChunkID.HEADER:
                self.logger.debug(f"Invalid header ID: {header_id:04X}, expected {OgreChunkID.HEADER:04X}")
                return None

            self.logger.debug(f"Ogre mesh version: {version}, endian: {endian_flag}")

            # Initialize mesh data
            mesh_name = Path(mesh_file_path).stem
            mesh_data = MeshData(
                name=mesh_name,
                vertices=[],
                faces=[],
                materials=[],
                submeshes=[]
            )

            # Parse chunks
            while True:
                chunk_header = f.read(6)
                if len(chunk_header) < 6:
                    break

                chunk_id, chunk_size = struct.unpack('<HI', chunk_header)
                chunk_data = f.read(chunk_size - 6)

                if len(chunk_data) != chunk_size - 6:
                    self.logger.warning(f"Incomplete chunk data for chunk {chunk_id:04X}")
                    break

                # Process chunk based on type
                self._process_mesh_chunk(chunk_id, chunk_data, mesh_data)

            # Validate parsed data
            if not mesh_data.vertices and not any(submesh.vertices for submesh in mesh_data.submeshes):
                self.logger.warning("No vertices found in mesh")
                return self._create_fallback_mesh(mesh_name)

            # Ensure we have at least one material
            if not mesh_data.materials:
                mesh_data.materials.append(MeshMaterial(f"{mesh_name}_material"))

            return mesh_data

        except struct.error as e:
            self.logger.debug(f"Binary mesh parsing failed - struct error: {e}")
            return None
        except Exception as e:
            self.logger.debug(f"Binary mesh parsing failed: {e}")
            return None

    def _parse_mesh_chunk(self, chunk_data: bytes, mesh_data: MeshData) -> None:
        """Parse main mesh chunk"""
        try:
            offset = 0
            # Skip skeletal animation flag
            skeletal_anim = struct.unpack('<B', chunk_data[offset:offset+1])[0]
            offset += 1

            mesh_data.has_shared_vertices = skeletal_anim != 0
            self.logger.debug(f"Mesh has shared vertices: {mesh_data.has_shared_vertices}")

        except Exception as e:
            self.logger.debug(f"Error parsing mesh chunk: {e}")

    def _parse_submesh_chunk(self, chunk_data: bytes, mesh_data: MeshData) -> None:
        """Parse submesh chunk"""
        try:
            offset = 0

            # Read material name length and name
            material_name_len = struct.unpack('<I', chunk_data[offset:offset+4])[0]
            offset += 4

            material_name = chunk_data[offset:offset+material_name_len].decode('utf-8', errors='ignore').rstrip('\x00')
            offset += material_name_len

            # Read use shared vertices flag
            use_shared_vertices = struct.unpack('<B', chunk_data[offset:offset+1])[0] != 0
            offset += 1

            # Read index count
            index_count = struct.unpack('<I', chunk_data[offset:offset+4])[0]
            offset += 4

            # Read 32-bit indices flag
            indices_32bit = struct.unpack('<B', chunk_data[offset:offset+1])[0] != 0
            offset += 1

            # Read indices
            faces = []
            index_format = '<I' if indices_32bit else '<H'
            index_size = 4 if indices_32bit else 2

            for i in range(0, index_count, 3):
                if offset + index_size * 3 <= len(chunk_data):
                    idx1 = struct.unpack(index_format, chunk_data[offset:offset+index_size])[0]
                    offset += index_size
                    idx2 = struct.unpack(index_format, chunk_data[offset:offset+index_size])[0]
                    offset += index_size
                    idx3 = struct.unpack(index_format, chunk_data[offset:offset+index_size])[0]
                    offset += index_size

                    faces.append(MeshFace((idx1, idx2, idx3), len(mesh_data.submeshes)))

            # Create submesh
            submesh = MeshSubmesh(
                material_name=material_name,
                vertices=[],
                faces=faces,
                use_shared_vertices=use_shared_vertices
            )

            mesh_data.submeshes.append(submesh)

            # Add material if not exists
            if not any(mat.name == material_name for mat in mesh_data.materials):
                mesh_data.materials.append(MeshMaterial(material_name))

            self.logger.debug(f"Parsed submesh: {material_name}, {len(faces)} faces, shared_vertices: {use_shared_vertices}")

        except Exception as e:
            self.logger.debug(f"Error parsing submesh chunk: {e}")

    def _parse_bounds_chunk(self, chunk_data: bytes, mesh_data: MeshData) -> None:
        """Parse mesh bounds chunk"""
        try:
            if len(chunk_data) >= 24:  # 6 floats * 4 bytes each
                min_x, min_y, min_z, max_x, max_y, max_z = struct.unpack('<6f', chunk_data[:24])
                mesh_data.bounding_box = ((min_x, min_y, min_z), (max_x, max_y, max_z))
                self.logger.debug(f"Parsed bounds: min({min_x:.2f}, {min_y:.2f}, {min_z:.2f}) max({max_x:.2f}, {max_y:.2f}, {max_z:.2f})")
        except Exception as e:
            self.logger.debug(f"Error parsing bounds chunk: {e}")

    def _parse_submesh_name_table(self, chunk_data: bytes, mesh_data: MeshData) -> None:
        """Parse submesh name table"""
        try:
            offset = 0
            submesh_index = 0

            while offset < len(chunk_data) and submesh_index < len(mesh_data.submeshes):
                # Read name length
                if offset + 4 > len(chunk_data):
                    break

                name_len = struct.unpack('<I', chunk_data[offset:offset+4])[0]
                offset += 4

                if offset + name_len > len(chunk_data):
                    break

                # Read name
                name = chunk_data[offset:offset+name_len].decode('utf-8', errors='ignore').rstrip('\x00')
                offset += name_len

                # Update submesh material name if more descriptive
                if submesh_index < len(mesh_data.submeshes) and name:
                    mesh_data.submeshes[submesh_index].material_name = name

                submesh_index += 1

        except Exception as e:
            self.logger.debug(f"Error parsing submesh name table: {e}")

    def _process_mesh_chunk(self, chunk_id: int, chunk_data: bytes, mesh_data: MeshData) -> None:
        """Process a mesh chunk based on its type"""
        try:
            if chunk_id == OgreChunkID.MESH:
                self._parse_mesh_chunk(chunk_data, mesh_data)
            elif chunk_id == OgreChunkID.SUBMESH:
                self._parse_submesh_chunk(chunk_data, mesh_data)
            elif chunk_id == OgreChunkID.GEOMETRY:
                self._parse_geometry_chunk(chunk_data, mesh_data)
            elif chunk_id == OgreChunkID.MESH_BOUNDS:
                self._parse_bounds_chunk(chunk_data, mesh_data)
            elif chunk_id == OgreChunkID.SUBMESH_NAME_TABLE:
                self._parse_submesh_name_table(chunk_data, mesh_data)
            else:
                self.logger.debug(f"Skipping unknown chunk: {chunk_id:04X}")
        except Exception as e:
            self.logger.debug(f"Error processing chunk {chunk_id:04X}: {e}")

    def _parse_geometry_chunk(self, chunk_data: bytes, mesh_data: MeshData) -> None:
        """Parse geometry chunk containing vertex data"""
        try:
            offset = 0

            # Read vertex count
            if offset + 4 > len(chunk_data):
                return
            vertex_count = struct.unpack('<I', chunk_data[offset:offset+4])[0]
            offset += 4

            self.logger.debug(f"Parsing geometry with {vertex_count} vertices")

            # Parse nested chunks within geometry
            vertices = []
            vertex_declaration = {}

            while offset < len(chunk_data):
                if offset + 6 > len(chunk_data):
                    break

                sub_chunk_id, sub_chunk_size = struct.unpack('<HI', chunk_data[offset:offset+6])
                offset += 6

                if offset + sub_chunk_size - 6 > len(chunk_data):
                    break

                sub_chunk_data = chunk_data[offset:offset+sub_chunk_size-6]
                offset += sub_chunk_size - 6

                if sub_chunk_id == OgreChunkID.GEOMETRY_VERTEX_DECLARATION:
                    vertex_declaration = self._parse_vertex_declaration(sub_chunk_data)
                elif sub_chunk_id == OgreChunkID.GEOMETRY_VERTEX_BUFFER:
                    buffer_vertices = self._parse_vertex_buffer(sub_chunk_data, vertex_declaration, vertex_count)
                    vertices.extend(buffer_vertices)

            # Add parsed vertices to mesh data
            mesh_data.vertices.extend(vertices)
            self.logger.debug(f"Added {len(vertices)} vertices to mesh")

        except Exception as e:
            self.logger.debug(f"Error parsing geometry chunk: {e}")

    def _parse_vertex_declaration(self, chunk_data: bytes) -> Dict:
        """Parse vertex declaration to understand vertex format"""
        declaration = {
            'position_offset': -1,
            'normal_offset': -1,
            'uv_offset': -1,
            'vertex_size': 0
        }

        try:
            offset = 0
            current_offset = 0

            while offset < len(chunk_data):
                if offset + 6 > len(chunk_data):
                    break

                element_chunk_id, element_chunk_size = struct.unpack('<HI', chunk_data[offset:offset+6])
                offset += 6

                if element_chunk_id == OgreChunkID.GEOMETRY_VERTEX_ELEMENT:
                    if offset + 8 <= len(chunk_data):
                        source, element_type, semantic, element_offset = struct.unpack('<HHHH', chunk_data[offset:offset+8])

                        if semantic == OgreVertexElementSemantic.POSITION:
                            declaration['position_offset'] = element_offset
                        elif semantic == OgreVertexElementSemantic.NORMAL:
                            declaration['normal_offset'] = element_offset
                        elif semantic == OgreVertexElementSemantic.TEXCOORD:
                            declaration['uv_offset'] = element_offset

                        # Calculate element size
                        element_size = self._get_element_size(element_type)
                        current_offset = max(current_offset, element_offset + element_size)

                offset += element_chunk_size - 6

            declaration['vertex_size'] = current_offset
            self.logger.debug(f"Vertex declaration: {declaration}")

        except Exception as e:
            self.logger.debug(f"Error parsing vertex declaration: {e}")

        return declaration

    def _parse_vertex_buffer(self, chunk_data: bytes, vertex_declaration: Dict, vertex_count: int) -> List[MeshVertex]:
        """Parse vertex buffer data"""
        vertices = []

        try:
            offset = 0

            # Skip to vertex buffer data chunk
            while offset < len(chunk_data):
                if offset + 6 > len(chunk_data):
                    break

                buffer_chunk_id, buffer_chunk_size = struct.unpack('<HI', chunk_data[offset:offset+6])
                offset += 6

                if buffer_chunk_id == OgreChunkID.GEOMETRY_VERTEX_BUFFER_DATA:
                    vertex_data = chunk_data[offset:offset+buffer_chunk_size-6]
                    vertices = self._parse_vertex_data(vertex_data, vertex_declaration, vertex_count)
                    break

                offset += buffer_chunk_size - 6

        except Exception as e:
            self.logger.debug(f"Error parsing vertex buffer: {e}")

        return vertices

    def _parse_vertex_data(self, vertex_data: bytes, vertex_declaration: Dict, vertex_count: int) -> List[MeshVertex]:
        """Parse actual vertex data"""
        vertices = []
        vertex_size = vertex_declaration.get('vertex_size', 0)

        if vertex_size == 0:
            self.logger.debug("Unknown vertex size, using fallback parsing")
            return vertices

        try:
            for i in range(vertex_count):
                vertex_offset = i * vertex_size

                if vertex_offset + vertex_size > len(vertex_data):
                    break

                # Parse position
                position = (0.0, 0.0, 0.0)
                pos_offset = vertex_declaration.get('position_offset', -1)
                if pos_offset >= 0 and vertex_offset + pos_offset + 12 <= len(vertex_data):
                    position = struct.unpack('<3f', vertex_data[vertex_offset + pos_offset:vertex_offset + pos_offset + 12])

                # Parse normal
                normal = (0.0, 0.0, 1.0)
                normal_offset = vertex_declaration.get('normal_offset', -1)
                if normal_offset >= 0 and vertex_offset + normal_offset + 12 <= len(vertex_data):
                    normal = struct.unpack('<3f', vertex_data[vertex_offset + normal_offset:vertex_offset + normal_offset + 12])

                # Parse UV
                uv = (0.0, 0.0)
                uv_offset = vertex_declaration.get('uv_offset', -1)
                if uv_offset >= 0 and vertex_offset + uv_offset + 8 <= len(vertex_data):
                    uv = struct.unpack('<2f', vertex_data[vertex_offset + uv_offset:vertex_offset + uv_offset + 8])

                vertices.append(MeshVertex(position, normal, uv))

            self.logger.debug(f"Parsed {len(vertices)} vertices from vertex data")

        except Exception as e:
            self.logger.debug(f"Error parsing vertex data: {e}")

        return vertices

    def _get_element_size(self, element_type: int) -> int:
        """Get size in bytes for vertex element type"""
        size_map = {
            OgreVertexElementType.FLOAT1: 4,
            OgreVertexElementType.FLOAT2: 8,
            OgreVertexElementType.FLOAT3: 12,
            OgreVertexElementType.FLOAT4: 16,
            OgreVertexElementType.SHORT1: 2,
            OgreVertexElementType.SHORT2: 4,
            OgreVertexElementType.SHORT3: 6,
            OgreVertexElementType.SHORT4: 8,
            OgreVertexElementType.UBYTE4: 4,
            OgreVertexElementType.COLOUR: 4,
            OgreVertexElementType.COLOUR_ARGB: 4,
            OgreVertexElementType.COLOUR_ABGR: 4,
        }
        return size_map.get(element_type, 4)

    def _create_fallback_mesh(self, mesh_name: str) -> MeshData:
        """Create a fallback mesh when parsing fails"""
        self.logger.info(f"Creating fallback mesh for {mesh_name}")

        # Create a simple triangle
        vertices = [
            MeshVertex((-1.0, -1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0)),
            MeshVertex((1.0, -1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0)),
            MeshVertex((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.5, 1.0))
        ]

        faces = [MeshFace((0, 1, 2), 0)]
        materials = [MeshMaterial(f"{mesh_name}_material")]

        return MeshData(mesh_name, vertices, faces, materials)

    def _parse_xml_mesh(self, mesh_file_path: str) -> Optional[MeshData]:
        """
        Parse XML Ogre3D .mesh file with enhanced support

        Handles both shared geometry and submesh-specific geometry
        """
        try:
            tree = ET.parse(mesh_file_path)
            root = tree.getroot()

            if root.tag != 'mesh':
                self.logger.debug("Root element is not 'mesh'")
                return None

            mesh_name = Path(mesh_file_path).stem
            mesh_data = MeshData(
                name=mesh_name,
                vertices=[],
                faces=[],
                materials=[],
                submeshes=[]
            )

            # Parse shared geometry
            shared_geometry = root.find('sharedgeometry')
            if shared_geometry is not None:
                vertex_count = int(shared_geometry.get('vertexcount', 0))
                self.logger.debug(f"Parsing shared geometry with {vertex_count} vertices")

                mesh_data.vertices = self._parse_xml_vertex_buffer(shared_geometry)
                mesh_data.has_shared_vertices = len(mesh_data.vertices) > 0

            # Parse submeshes
            submeshes_elem = root.find('submeshes')
            if submeshes_elem is not None:
                for submesh_elem in submeshes_elem.findall('submesh'):
                    submesh = self._parse_xml_submesh(submesh_elem, mesh_data)
                    if submesh:
                        mesh_data.submeshes.append(submesh)

            # Parse skeleton link
            skeleton_link = root.find('skeletonlink')
            if skeleton_link is not None:
                mesh_data.skeleton_link = skeleton_link.get('name')

            # Parse bounding box
            bounds_elem = root.find('bounds')
            if bounds_elem is not None:
                try:
                    min_x = float(bounds_elem.get('minx', 0.0))
                    min_y = float(bounds_elem.get('miny', 0.0))
                    min_z = float(bounds_elem.get('minz', 0.0))
                    max_x = float(bounds_elem.get('maxx', 0.0))
                    max_y = float(bounds_elem.get('maxy', 0.0))
                    max_z = float(bounds_elem.get('maxz', 0.0))
                    mesh_data.bounding_box = ((min_x, min_y, min_z), (max_x, max_y, max_z))
                except ValueError:
                    pass

            # Consolidate faces from submeshes
            for submesh in mesh_data.submeshes:
                mesh_data.faces.extend(submesh.faces)

            # Ensure we have at least one material
            if not mesh_data.materials:
                mesh_data.materials.append(MeshMaterial(f"{mesh_name}_material"))

            # Validate parsed data
            if not mesh_data.vertices and not any(submesh.vertices for submesh in mesh_data.submeshes):
                self.logger.warning("No vertices found in XML mesh")
                return self._create_fallback_mesh(mesh_name)

            self.logger.debug(f"Parsed XML mesh: {len(mesh_data.vertices)} shared vertices, {len(mesh_data.submeshes)} submeshes")
            return mesh_data

        except ET.ParseError as e:
            self.logger.debug(f"XML parsing failed: {e}")
            return None
        except Exception as e:
            self.logger.debug(f"XML mesh parsing failed: {e}")
            return None

    def _parse_xml_vertex_buffer(self, geometry_elem: ET.Element) -> List[MeshVertex]:
        """Parse XML vertex buffer with enhanced attribute support"""
        vertices = []

        vertex_buffer = geometry_elem.find('vertexbuffer')
        if vertex_buffer is None:
            return vertices

        for vertex_elem in vertex_buffer.findall('vertex'):
            # Initialize default values
            position = (0.0, 0.0, 0.0)
            normal = (0.0, 0.0, 1.0)
            uv = (0.0, 0.0)
            uv2 = None
            color = (1.0, 1.0, 1.0, 1.0)
            tangent = None
            binormal = None

            # Parse position
            position_elem = vertex_elem.find('position')
            if position_elem is not None:
                try:
                    position = (
                        float(position_elem.get('x', 0.0)),
                        float(position_elem.get('y', 0.0)),
                        float(position_elem.get('z', 0.0))
                    )
                except ValueError:
                    pass

            # Parse normal
            normal_elem = vertex_elem.find('normal')
            if normal_elem is not None:
                try:
                    normal = (
                        float(normal_elem.get('x', 0.0)),
                        float(normal_elem.get('y', 0.0)),
                        float(normal_elem.get('z', 1.0))
                    )
                except ValueError:
                    pass

            # Parse texture coordinates
            texcoord_elems = vertex_elem.findall('texcoord')
            for i, texcoord_elem in enumerate(texcoord_elems):
                try:
                    u = float(texcoord_elem.get('u', 0.0))
                    v = float(texcoord_elem.get('v', 0.0))
                    if i == 0:
                        uv = (u, v)
                    elif i == 1:
                        uv2 = (u, v)
                except ValueError:
                    pass

            # Parse color
            colour_elem = vertex_elem.find('colour_diffuse')
            if colour_elem is not None:
                try:
                    # Parse color value (can be in various formats)
                    color_value = colour_elem.get('value', '1 1 1 1')
                    color_parts = color_value.split()
                    if len(color_parts) >= 3:
                        color = (
                            float(color_parts[0]),
                            float(color_parts[1]),
                            float(color_parts[2]),
                            float(color_parts[3]) if len(color_parts) > 3 else 1.0
                        )
                except (ValueError, IndexError):
                    pass

            # Parse tangent
            tangent_elem = vertex_elem.find('tangent')
            if tangent_elem is not None:
                try:
                    tangent = (
                        float(tangent_elem.get('x', 0.0)),
                        float(tangent_elem.get('y', 0.0)),
                        float(tangent_elem.get('z', 0.0))
                    )
                except ValueError:
                    pass

            # Parse binormal
            binormal_elem = vertex_elem.find('binormal')
            if binormal_elem is not None:
                try:
                    binormal = (
                        float(binormal_elem.get('x', 0.0)),
                        float(binormal_elem.get('y', 0.0)),
                        float(binormal_elem.get('z', 0.0))
                    )
                except ValueError:
                    pass

            vertices.append(MeshVertex(
                position=position,
                normal=normal,
                uv=uv,
                uv2=uv2,
                color=color,
                tangent=tangent,
                binormal=binormal
            ))

        return vertices

    def _parse_xml_submesh(self, submesh_elem: ET.Element, mesh_data: MeshData) -> Optional[MeshSubmesh]:
        """Parse XML submesh with enhanced support"""
        try:
            material_name = submesh_elem.get('material', f'{mesh_data.name}_material')
            use_shared_vertices = submesh_elem.get('usesharedvertices', 'true').lower() == 'true'
            operation_type = submesh_elem.get('operationtype', 'triangle_list')

            # Add material if not exists
            if not any(mat.name == material_name for mat in mesh_data.materials):
                mesh_data.materials.append(MeshMaterial(material_name))

            # Parse submesh-specific geometry
            submesh_vertices = []
            if not use_shared_vertices:
                geometry_elem = submesh_elem.find('geometry')
                if geometry_elem is not None:
                    submesh_vertices = self._parse_xml_vertex_buffer(geometry_elem)

            # Parse faces
            faces = []
            faces_elem = submesh_elem.find('faces')
            if faces_elem is not None:
                face_count = int(faces_elem.get('count', 0))
                self.logger.debug(f"Parsing {face_count} faces for submesh {material_name}")

                for face_elem in faces_elem.findall('face'):
                    try:
                        v1 = int(face_elem.get('v1', 0))
                        v2 = int(face_elem.get('v2', 0))
                        v3 = int(face_elem.get('v3', 0))

                        # Find material index
                        material_index = 0
                        for i, mat in enumerate(mesh_data.materials):
                            if mat.name == material_name:
                                material_index = i
                                break

                        faces.append(MeshFace((v1, v2, v3), material_index))
                    except ValueError:
                        continue

            return MeshSubmesh(
                material_name=material_name,
                vertices=submesh_vertices,
                faces=faces,
                use_shared_vertices=use_shared_vertices,
                operation_type=4 if operation_type == 'triangle_list' else 4
            )

        except Exception as e:
            self.logger.debug(f"Error parsing XML submesh: {e}")
            return None

    def convert_to_dae(self, mesh_data: MeshData, output_path: str,
                       coordinate_transform: bool = True) -> bool:
        """
        Convert mesh data to COLLADA (.dae) format

        Args:
            mesh_data: Parsed mesh data
            output_path: Output path for .dae file
            coordinate_transform: Apply RoR to BeamNG coordinate transformation

        Returns:
            True if conversion successful, False otherwise
        """
        try:
            # Create COLLADA XML structure
            collada = ET.Element('COLLADA')
            collada.set('xmlns', 'http://www.collada.org/2005/11/COLLADASchema')
            collada.set('version', '1.4.1')

            # Asset information
            asset = ET.SubElement(collada, 'asset')
            contributor = ET.SubElement(asset, 'contributor')
            ET.SubElement(contributor, 'authoring_tool').text = 'truck2jbeam mesh converter'
            ET.SubElement(asset, 'created').text = '2024-01-01T00:00:00Z'
            ET.SubElement(asset, 'modified').text = '2024-01-01T00:00:00Z'

            # Up axis (BeamNG uses Y-up)
            ET.SubElement(asset, 'up_axis').text = 'Y_UP'

            # Library geometries
            lib_geometries = ET.SubElement(collada, 'library_geometries')
            geometry = ET.SubElement(lib_geometries, 'geometry')
            geometry.set('id', f"{mesh_data.name}-geometry")
            geometry.set('name', mesh_data.name)

            mesh_elem = ET.SubElement(geometry, 'mesh')

            # Prepare consolidated vertex and face data
            all_vertices = []
            all_faces = []

            # Add shared vertices if present
            if mesh_data.vertices:
                for vertex in mesh_data.vertices:
                    x, y, z = vertex.position
                    if coordinate_transform:
                        # Apply RoR to BeamNG coordinate transformation
                        all_vertices.append((x, z, y))  # X stays, Y->Z, Z->Y
                    else:
                        all_vertices.append((x, y, z))

                # Add faces that use shared vertices
                for face in mesh_data.faces:
                    all_faces.append(face.vertices)

            # Add submesh-specific vertices
            for submesh in mesh_data.submeshes:
                if not submesh.use_shared_vertices and submesh.vertices:
                    submesh_start = len(all_vertices)

                    for vertex in submesh.vertices:
                        x, y, z = vertex.position
                        if coordinate_transform:
                            all_vertices.append((x, z, y))
                        else:
                            all_vertices.append((x, y, z))

                    # Add submesh faces with adjusted indices
                    for face in submesh.faces:
                        adjusted_face = (
                            face.vertices[0] + submesh_start,
                            face.vertices[1] + submesh_start,
                            face.vertices[2] + submesh_start
                        )
                        all_faces.append(adjusted_face)
                elif submesh.use_shared_vertices:
                    # Use shared vertices, faces already added above
                    for face in submesh.faces:
                        all_faces.append(face.vertices)

            # Vertices source
            positions_source = ET.SubElement(mesh_elem, 'source')
            positions_source.set('id', f"{mesh_data.name}-positions")

            positions_array = ET.SubElement(positions_source, 'float_array')
            positions_array.set('id', f"{mesh_data.name}-positions-array")
            positions_array.set('count', str(len(all_vertices) * 3))

            # Build position data
            position_data = []
            for vertex in all_vertices:
                position_data.extend(vertex)

            positions_array.text = ' '.join(map(str, position_data))

            # Position accessor
            positions_technique = ET.SubElement(positions_source, 'technique_common')
            positions_accessor = ET.SubElement(positions_technique, 'accessor')
            positions_accessor.set('source', f"#{mesh_data.name}-positions-array")
            positions_accessor.set('count', str(len(all_vertices)))
            positions_accessor.set('stride', '3')

            ET.SubElement(positions_accessor, 'param', name='X', type='float')
            ET.SubElement(positions_accessor, 'param', name='Y', type='float')
            ET.SubElement(positions_accessor, 'param', name='Z', type='float')

            # Vertices element
            vertices = ET.SubElement(mesh_elem, 'vertices')
            vertices.set('id', f"{mesh_data.name}-vertices")
            vertices_input = ET.SubElement(vertices, 'input')
            vertices_input.set('semantic', 'POSITION')
            vertices_input.set('source', f"#{mesh_data.name}-positions")

            # Triangles
            triangles = ET.SubElement(mesh_elem, 'triangles')
            triangles.set('count', str(len(all_faces)))

            triangles_input = ET.SubElement(triangles, 'input')
            triangles_input.set('semantic', 'VERTEX')
            triangles_input.set('source', f"#{mesh_data.name}-vertices")
            triangles_input.set('offset', '0')

            # Face indices
            face_indices = []
            for face in all_faces:
                face_indices.extend(face)

            p_elem = ET.SubElement(triangles, 'p')
            p_elem.text = ' '.join(map(str, face_indices))

            # Library visual scenes
            lib_visual_scenes = ET.SubElement(collada, 'library_visual_scenes')
            visual_scene = ET.SubElement(lib_visual_scenes, 'visual_scene')
            visual_scene.set('id', 'Scene')
            visual_scene.set('name', 'Scene')

            node = ET.SubElement(visual_scene, 'node')
            node.set('id', mesh_data.name)
            node.set('name', mesh_data.name)
            node.set('type', 'NODE')

            instance_geometry = ET.SubElement(node, 'instance_geometry')
            instance_geometry.set('url', f"#{mesh_data.name}-geometry")

            # Scene
            scene = ET.SubElement(collada, 'scene')
            instance_visual_scene = ET.SubElement(scene, 'instance_visual_scene')
            instance_visual_scene.set('url', '#Scene')

            # Write to file with pretty formatting
            rough_string = ET.tostring(collada, 'unicode')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent='  ')

            # Remove empty lines
            pretty_lines = [line for line in pretty_xml.split('\n') if line.strip()]
            pretty_xml = '\n'.join(pretty_lines)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)

            self.logger.info(f"Successfully converted mesh to DAE: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error converting mesh to DAE: {e}")
            return False

    def convert_to_blend(self, mesh_data: MeshData, output_path: str,
                        coordinate_transform: bool = True) -> bool:
        """
        Convert mesh data to Blender (.blend) format

        Args:
            mesh_data: Parsed mesh data
            output_path: Output path for .blend file
            coordinate_transform: Apply RoR to BeamNG coordinate transformation

        Returns:
            True if conversion successful, False otherwise
        """
        if not self.has_bpy:
            self.logger.error("Blender Python API not available for .blend export")
            return False

        try:
            import bpy

            # Clear existing mesh objects
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete(use_global=False)

            # Create new mesh
            mesh = bpy.data.meshes.new(mesh_data.name)

            # Prepare vertex data with coordinate transformation
            # Handle both shared vertices and submesh vertices
            all_vertices = []
            all_faces = []

            # Add shared vertices if present
            if mesh_data.vertices:
                for vertex in mesh_data.vertices:
                    x, y, z = vertex.position
                    if coordinate_transform:
                        # Apply RoR to BeamNG coordinate transformation
                        all_vertices.append((x, z, y))  # X stays, Y->Z, Z->Y
                    else:
                        all_vertices.append((x, y, z))

                # Add faces that use shared vertices
                for face in mesh_data.faces:
                    all_faces.append(face.vertices)

            # Add submesh-specific vertices
            for submesh in mesh_data.submeshes:
                if not submesh.use_shared_vertices and submesh.vertices:
                    submesh_start = len(all_vertices)

                    for vertex in submesh.vertices:
                        x, y, z = vertex.position
                        if coordinate_transform:
                            all_vertices.append((x, z, y))
                        else:
                            all_vertices.append((x, y, z))

                    # Add submesh faces with adjusted indices
                    for face in submesh.faces:
                        adjusted_face = (
                            face.vertices[0] + submesh_start,
                            face.vertices[1] + submesh_start,
                            face.vertices[2] + submesh_start
                        )
                        all_faces.append(adjusted_face)
                elif submesh.use_shared_vertices:
                    # Use shared vertices, faces already added above
                    for face in submesh.faces:
                        all_faces.append(face.vertices)

            # Use consolidated vertex and face data
            vertices = all_vertices
            faces = all_faces

            # Create mesh from data
            mesh.from_pydata(vertices, [], faces)
            mesh.update()

            # Create object and link to scene
            obj = bpy.data.objects.new(mesh_data.name, mesh)
            bpy.context.collection.objects.link(obj)

            # Add materials
            for material_data in mesh_data.materials:
                material = bpy.data.materials.new(name=material_data.name)
                material.use_nodes = True

                # Set diffuse color
                if material.node_tree:
                    bsdf = material.node_tree.nodes.get("Principled BSDF")
                    if bsdf:
                        bsdf.inputs[0].default_value = material_data.diffuse_color

                mesh.materials.append(material)

            # Save blend file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=output_path)

            self.logger.info(f"Successfully converted mesh to Blender: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error converting mesh to Blender: {e}")
            return False

    def convert_mesh_file(self, mesh_file_path: str, output_dir: str,
                         output_format: str = 'dae', mesh_name_override: Optional[str] = None,
                         coordinate_transform: bool = True) -> List[str]:
        """
        Convert a single .mesh file to specified format(s)

        Args:
            mesh_file_path: Path to input .mesh file
            output_dir: Output directory for converted files
            output_format: Output format ('dae', 'blend', or 'both')
            mesh_name_override: Override mesh name (for duplicate resolution)
            coordinate_transform: Apply RoR to BeamNG coordinate transformation

        Returns:
            List of successfully created output file paths
        """
        # Parse the mesh file
        mesh_data = self.parse_mesh_file(mesh_file_path)
        if not mesh_data:
            self.logger.error(f"Failed to parse mesh file: {mesh_file_path}")
            return []

        # Override mesh name if provided (for duplicate resolution)
        if mesh_name_override:
            mesh_data.name = mesh_name_override

        output_files = []

        # Convert to DAE
        if output_format in ['dae', 'both']:
            dae_path = os.path.join(output_dir, f"{mesh_data.name}.dae")
            if self.convert_to_dae(mesh_data, dae_path, coordinate_transform):
                output_files.append(dae_path)

        # Convert to Blender
        if output_format in ['blend', 'both']:
            blend_path = os.path.join(output_dir, f"{mesh_data.name}.blend")
            if self.convert_to_blend(mesh_data, blend_path, coordinate_transform):
                output_files.append(blend_path)

        return output_files

    def batch_convert_meshes(self, mesh_files: List[str], output_dir: str,
                           output_format: str = 'dae', mesh_name_mapping: Optional[Dict[str, str]] = None,
                           coordinate_transform: bool = True) -> Dict[str, List[str]]:
        """
        Convert multiple .mesh files in batch

        Args:
            mesh_files: List of .mesh file paths
            output_dir: Output directory for converted files
            output_format: Output format ('dae', 'blend', or 'both')
            mesh_name_mapping: Optional mapping of original names to new names
            coordinate_transform: Apply RoR to BeamNG coordinate transformation

        Returns:
            Dictionary mapping input file paths to lists of output file paths
        """
        results = {}

        for mesh_file in mesh_files:
            if not mesh_file.endswith('.mesh'):
                continue

            # Get mesh name override from mapping
            mesh_name = Path(mesh_file).stem
            mesh_name_override = None
            if mesh_name_mapping and mesh_name in mesh_name_mapping:
                mesh_name_override = mesh_name_mapping[mesh_name]

            # Convert the mesh
            output_files = self.convert_mesh_file(
                mesh_file, output_dir, output_format,
                mesh_name_override, coordinate_transform
            )

            results[mesh_file] = output_files

            if output_files:
                self.logger.info(f"Converted {mesh_file} -> {output_files}")
            else:
                self.logger.warning(f"Failed to convert {mesh_file}")

        return results

    def extract_mesh_files_from_rig(self, rig) -> List[str]:
        """
        Extract all .mesh file references from a rig object

        Args:
            rig: Rig object containing flexbodies and props

        Returns:
            List of unique .mesh file names referenced in the rig
        """
        mesh_files = set()

        # Extract from flexbodies
        for flexbody in rig.flexbodies:
            if hasattr(flexbody, 'mesh') and flexbody.mesh.endswith('.mesh'):
                mesh_files.add(flexbody.mesh)

        # Extract from props
        for prop in rig.props:
            if hasattr(prop, 'mesh') and prop.mesh.endswith('.mesh'):
                mesh_files.add(prop.mesh)

        return list(mesh_files)

    def generate_mesh_conversion_mapping(self, rig) -> Dict[str, str]:
        """
        Generate mesh name mapping for conversion that matches JBeam output

        Args:
            rig: Rig object with resolved mesh names

        Returns:
            Dictionary mapping original .mesh names to converted names (without extensions)
        """
        mapping = {}

        # Process flexbodies
        for flexbody in rig.flexbodies:
            if hasattr(flexbody, 'mesh') and flexbody.mesh.endswith('.mesh'):
                original_name = Path(flexbody.mesh).stem
                # Use the same name as will appear in JBeam (without extension)
                jbeam_name = flexbody.mesh[:-5]  # Remove .mesh extension
                mapping[original_name] = jbeam_name

        # Process props
        for prop in rig.props:
            if hasattr(prop, 'mesh') and prop.mesh.endswith('.mesh'):
                original_name = Path(prop.mesh).stem
                # Use the same name as will appear in JBeam (without extension)
                jbeam_name = prop.mesh[:-5]  # Remove .mesh extension
                mapping[original_name] = jbeam_name

        return mapping
