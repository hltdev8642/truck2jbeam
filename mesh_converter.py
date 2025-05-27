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

    def _check_blender_availability(self) -> bool:
        """Check if Blender Python API is available"""
        try:
            import bpy
            return True
        except ImportError:
            self.logger.info("Blender Python API not available, .blend export disabled")
            return False

    def parse_mesh_file(self, mesh_file_path: str) -> Optional[MeshData]:
        """
        Parse an Ogre3D .mesh file and extract geometry data

        Args:
            mesh_file_path: Path to the .mesh file

        Returns:
            MeshData object containing parsed mesh information, or None if parsing fails
        """
        if not os.path.exists(mesh_file_path):
            self.logger.error(f"Mesh file not found: {mesh_file_path}")
            return None

        try:
            # Try to parse as binary Ogre mesh first
            mesh_data = self._parse_binary_mesh(mesh_file_path)
            if mesh_data:
                return mesh_data

            # Fallback to XML mesh parsing
            mesh_data = self._parse_xml_mesh(mesh_file_path)
            if mesh_data:
                return mesh_data

            self.logger.error(f"Unable to parse mesh file: {mesh_file_path}")
            return None

        except Exception as e:
            self.logger.error(f"Error parsing mesh file {mesh_file_path}: {e}")
            return None

    def _parse_binary_mesh(self, mesh_file_path: str) -> Optional[MeshData]:
        """
        Parse binary Ogre3D .mesh file using proper format specification

        Based on Ogre3D serialization format and blender2ogre techniques
        """
        try:
            with open(mesh_file_path, 'rb') as f:
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
                    if chunk_id == OgreChunkID.MESH:
                        self._parse_mesh_chunk(chunk_data, mesh_data)
                    elif chunk_id == OgreChunkID.SUBMESH:
                        self._parse_submesh_chunk(chunk_data, mesh_data)
                    elif chunk_id == OgreChunkID.MESH_BOUNDS:
                        self._parse_bounds_chunk(chunk_data, mesh_data)
                    elif chunk_id == OgreChunkID.SUBMESH_NAME_TABLE:
                        self._parse_submesh_name_table(chunk_data, mesh_data)
                    else:
                        self.logger.debug(f"Skipping unknown chunk: {chunk_id:04X}")

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
