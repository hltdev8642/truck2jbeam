"""
DAE File Processor for truck2jbeam
Handles parsing and modification of COLLADA (.dae) files for mesh name extraction and synchronization
"""

import os
import re
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class DAEProcessor:
    """Handles DAE file processing for mesh name extraction and modification"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.has_lxml = self._check_lxml_availability()

    def _check_lxml_availability(self) -> bool:
        """Check if lxml is available for XML processing"""
        try:
            import lxml.etree as ET
            return True
        except ImportError:
            self.logger.warning("lxml not available, falling back to basic XML processing")
            return False

    def extract_mesh_names(self, dae_file_path: str) -> List[str]:
        """
        Extract mesh names from a DAE file

        Args:
            dae_file_path: Path to the DAE file

        Returns:
            List of mesh names found in the DAE file
        """
        if not os.path.exists(dae_file_path):
            self.logger.error(f"DAE file not found: {dae_file_path}")
            return []

        try:
            if self.has_lxml:
                return self._extract_mesh_names_lxml(dae_file_path)
            else:
                return self._extract_mesh_names_basic(dae_file_path)
        except Exception as e:
            self.logger.error(f"Error extracting mesh names from {dae_file_path}: {e}")
            return []

    def _extract_mesh_names_lxml(self, dae_file_path: str) -> List[str]:
        """Extract mesh names using lxml (preferred method)"""
        try:
            from lxml import etree as ET
        except ImportError:
            return self._extract_mesh_names_basic(dae_file_path)

        mesh_names = []

        try:
            # Parse the DAE file
            tree = ET.parse(dae_file_path)
            root = tree.getroot()

            # Define COLLADA namespace
            namespaces = {
                'collada': 'http://www.collada.org/2005/11/COLLADASchema'
            }

            # Extract mesh names from geometry elements
            geometries = root.xpath('//collada:geometry', namespaces=namespaces)
            for geometry in geometries:
                mesh_id = geometry.get('id')
                mesh_name = geometry.get('name')

                if mesh_id:
                    mesh_names.append(mesh_id)
                elif mesh_name:
                    mesh_names.append(mesh_name)

            # Extract mesh names from node elements
            nodes = root.xpath('//collada:node', namespaces=namespaces)
            for node in nodes:
                node_id = node.get('id')
                node_name = node.get('name')

                if node_id and node_id not in mesh_names:
                    mesh_names.append(node_id)
                elif node_name and node_name not in mesh_names:
                    mesh_names.append(node_name)

            # Extract mesh names from instance_geometry elements
            instance_geometries = root.xpath('//collada:instance_geometry', namespaces=namespaces)
            for instance in instance_geometries:
                url = instance.get('url')
                if url and url.startswith('#'):
                    mesh_name = url[1:]  # Remove the '#' prefix
                    if mesh_name not in mesh_names:
                        mesh_names.append(mesh_name)

        except Exception as e:
            self.logger.error(f"Error parsing DAE file with lxml: {e}")
            return self._extract_mesh_names_basic(dae_file_path)

        return list(set(mesh_names))  # Remove duplicates

    def _extract_mesh_names_basic(self, dae_file_path: str) -> List[str]:
        """Extract mesh names using basic text parsing (fallback method)"""
        mesh_names = []

        try:
            with open(dae_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract geometry IDs
            geometry_pattern = r'<geometry\s+id="([^"]+)"'
            geometry_matches = re.findall(geometry_pattern, content, re.IGNORECASE)
            mesh_names.extend(geometry_matches)

            # Extract geometry names
            geometry_name_pattern = r'<geometry\s+[^>]*name="([^"]+)"'
            geometry_name_matches = re.findall(geometry_name_pattern, content, re.IGNORECASE)
            mesh_names.extend(geometry_name_matches)

            # Extract node IDs
            node_pattern = r'<node\s+id="([^"]+)"'
            node_matches = re.findall(node_pattern, content, re.IGNORECASE)
            mesh_names.extend(node_matches)

            # Extract node names
            node_name_pattern = r'<node\s+[^>]*name="([^"]+)"'
            node_name_matches = re.findall(node_name_pattern, content, re.IGNORECASE)
            mesh_names.extend(node_name_matches)

            # Extract instance_geometry URLs
            instance_pattern = r'<instance_geometry\s+url="#([^"]+)"'
            instance_matches = re.findall(instance_pattern, content, re.IGNORECASE)
            mesh_names.extend(instance_matches)

        except Exception as e:
            self.logger.error(f"Error reading DAE file: {e}")

        return list(set(mesh_names))  # Remove duplicates

    def modify_mesh_names(self, dae_file_path: str, mesh_mapping: Dict[str, str],
                         output_path: Optional[str] = None) -> bool:
        """
        Modify mesh names in a DAE file to match JBeam group names

        Args:
            dae_file_path: Path to the input DAE file
            mesh_mapping: Dictionary mapping old mesh names to new names
            output_path: Path for the modified DAE file (if None, overwrites original)

        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(dae_file_path):
            self.logger.error(f"DAE file not found: {dae_file_path}")
            return False

        if not mesh_mapping:
            self.logger.warning("No mesh mapping provided")
            return True

        try:
            if self.has_lxml:
                return self._modify_mesh_names_lxml(dae_file_path, mesh_mapping, output_path)
            else:
                return self._modify_mesh_names_basic(dae_file_path, mesh_mapping, output_path)
        except Exception as e:
            self.logger.error(f"Error modifying mesh names in {dae_file_path}: {e}")
            return False

    def _modify_mesh_names_lxml(self, dae_file_path: str, mesh_mapping: Dict[str, str],
                               output_path: Optional[str] = None) -> bool:
        """Modify mesh names using lxml (preferred method)"""
        try:
            from lxml import etree as ET
        except ImportError:
            return self._modify_mesh_names_basic(dae_file_path, mesh_mapping, output_path)

        try:
            # Parse the DAE file
            tree = ET.parse(dae_file_path)
            root = tree.getroot()

            # Define COLLADA namespace
            namespaces = {
                'collada': 'http://www.collada.org/2005/11/COLLADASchema'
            }

            modifications_made = 0

            # Modify geometry elements
            geometries = root.xpath('//collada:geometry', namespaces=namespaces)
            for geometry in geometries:
                old_id = geometry.get('id')
                old_name = geometry.get('name')

                if old_id and old_id in mesh_mapping:
                    geometry.set('id', mesh_mapping[old_id])
                    modifications_made += 1
                    self.logger.info(f"Modified geometry id: {old_id} -> {mesh_mapping[old_id]}")

                if old_name and old_name in mesh_mapping:
                    geometry.set('name', mesh_mapping[old_name])
                    modifications_made += 1
                    self.logger.info(f"Modified geometry name: {old_name} -> {mesh_mapping[old_name]}")

            # Modify node elements
            nodes = root.xpath('//collada:node', namespaces=namespaces)
            for node in nodes:
                old_id = node.get('id')
                old_name = node.get('name')

                if old_id and old_id in mesh_mapping:
                    node.set('id', mesh_mapping[old_id])
                    modifications_made += 1
                    self.logger.info(f"Modified node id: {old_id} -> {mesh_mapping[old_id]}")

                if old_name and old_name in mesh_mapping:
                    node.set('name', mesh_mapping[old_name])
                    modifications_made += 1
                    self.logger.info(f"Modified node name: {old_name} -> {mesh_mapping[old_name]}")

            # Modify instance_geometry elements
            instance_geometries = root.xpath('//collada:instance_geometry', namespaces=namespaces)
            for instance in instance_geometries:
                url = instance.get('url')
                if url and url.startswith('#'):
                    old_ref = url[1:]  # Remove the '#' prefix
                    if old_ref in mesh_mapping:
                        instance.set('url', f"#{mesh_mapping[old_ref]}")
                        modifications_made += 1
                        self.logger.info(f"Modified instance_geometry url: #{old_ref} -> #{mesh_mapping[old_ref]}")

            # Write the modified DAE file
            output_file = output_path if output_path else dae_file_path
            tree.write(output_file, encoding='utf-8', xml_declaration=True, pretty_print=True)

            self.logger.info(f"Successfully modified DAE file with {modifications_made} changes: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error modifying DAE file with lxml: {e}")
            return self._modify_mesh_names_basic(dae_file_path, mesh_mapping, output_path)

    def _modify_mesh_names_basic(self, dae_file_path: str, mesh_mapping: Dict[str, str],
                                output_path: Optional[str] = None) -> bool:
        """Modify mesh names using basic text replacement (fallback method)"""
        try:
            with open(dae_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            modifications_made = 0

            for old_name, new_name in mesh_mapping.items():
                # Escape special regex characters
                escaped_old_name = re.escape(old_name)

                # Replace geometry id attributes
                geometry_id_pattern = f'(<geometry\\s+id=")({escaped_old_name})(")'
                if re.search(geometry_id_pattern, content, re.IGNORECASE):
                    content = re.sub(geometry_id_pattern, f'\\1{new_name}\\3', content, flags=re.IGNORECASE)
                    modifications_made += 1
                    self.logger.info(f"Modified geometry id: {old_name} -> {new_name}")

                # Replace geometry name attributes
                geometry_name_pattern = f'(<geometry\\s+[^>]*name=")({escaped_old_name})(")'
                if re.search(geometry_name_pattern, content, re.IGNORECASE):
                    content = re.sub(geometry_name_pattern, f'\\1{new_name}\\3', content, flags=re.IGNORECASE)
                    modifications_made += 1
                    self.logger.info(f"Modified geometry name: {old_name} -> {new_name}")

                # Replace node id attributes
                node_id_pattern = f'(<node\\s+id=")({escaped_old_name})(")'
                if re.search(node_id_pattern, content, re.IGNORECASE):
                    content = re.sub(node_id_pattern, f'\\1{new_name}\\3', content, flags=re.IGNORECASE)
                    modifications_made += 1
                    self.logger.info(f"Modified node id: {old_name} -> {new_name}")

                # Replace node name attributes
                node_name_pattern = f'(<node\\s+[^>]*name=")({escaped_old_name})(")'
                if re.search(node_name_pattern, content, re.IGNORECASE):
                    content = re.sub(node_name_pattern, f'\\1{new_name}\\3', content, flags=re.IGNORECASE)
                    modifications_made += 1
                    self.logger.info(f"Modified node name: {old_name} -> {new_name}")

                # Replace instance_geometry url references
                instance_pattern = f'(<instance_geometry\\s+url="#)({escaped_old_name})(")'
                if re.search(instance_pattern, content, re.IGNORECASE):
                    content = re.sub(instance_pattern, f'\\1{new_name}\\3', content, flags=re.IGNORECASE)
                    modifications_made += 1
                    self.logger.info(f"Modified instance_geometry url: #{old_name} -> #{new_name}")

            # Write the modified content
            if content != original_content:
                output_file = output_path if output_path else dae_file_path
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.logger.info(f"Successfully modified DAE file with {modifications_made} changes: {output_file}")
                return True
            else:
                self.logger.info("No modifications needed for DAE file")
                return True

        except Exception as e:
            self.logger.error(f"Error modifying DAE file with basic method: {e}")
            return False

    def generate_mesh_mapping(self, flexbodies: List, props: List) -> Dict[str, str]:
        """
        Generate mesh name mapping from flexbodies and props to their group names

        Args:
            flexbodies: List of flexbody objects
            props: List of prop objects

        Returns:
            Dictionary mapping original mesh names to group names
        """
        mesh_mapping = {}

        # Process flexbodies
        for flexbody in flexbodies:
            if hasattr(flexbody, 'mesh') and hasattr(flexbody, 'get_group_name'):
                original_mesh = flexbody.mesh
                group_name = flexbody.get_group_name()

                # Remove file extension for mapping
                mesh_base_name = original_mesh
                if mesh_base_name.endswith('.dae'):
                    mesh_base_name = mesh_base_name[:-4]
                elif mesh_base_name.endswith('.mesh'):
                    mesh_base_name = mesh_base_name[:-5]

                mesh_mapping[mesh_base_name] = group_name
                mesh_mapping[original_mesh] = group_name  # Also map full name

        # Process props
        for prop in props:
            if hasattr(prop, 'mesh') and hasattr(prop, 'get_group_name'):
                original_mesh = prop.mesh
                group_name = prop.get_group_name()

                # Remove file extension for mapping
                mesh_base_name = original_mesh
                if mesh_base_name.endswith('.dae'):
                    mesh_base_name = mesh_base_name[:-4]
                elif mesh_base_name.endswith('.mesh'):
                    mesh_base_name = mesh_base_name[:-5]

                mesh_mapping[mesh_base_name] = group_name
                mesh_mapping[original_mesh] = group_name  # Also map full name

        return mesh_mapping

    def process_dae_files_for_rig(self, rig, dae_directory: str, output_directory: Optional[str] = None) -> bool:
        """
        Process all DAE files for a rig, modifying mesh names to match JBeam groups

        Args:
            rig: Rig object containing flexbodies and props
            dae_directory: Directory containing DAE files
            output_directory: Directory for modified DAE files (if None, modifies in place)

        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(dae_directory):
            self.logger.error(f"DAE directory not found: {dae_directory}")
            return False

        # Generate mesh mapping
        mesh_mapping = self.generate_mesh_mapping(rig.flexbodies, rig.props)

        if not mesh_mapping:
            self.logger.info("No mesh mapping generated, no DAE files to process")
            return True

        # Find all DAE files in the directory
        dae_files = []
        for root, dirs, files in os.walk(dae_directory):
            for file in files:
                if file.lower().endswith('.dae'):
                    dae_files.append(os.path.join(root, file))

        if not dae_files:
            self.logger.warning(f"No DAE files found in directory: {dae_directory}")
            return True

        success_count = 0

        for dae_file in dae_files:
            try:
                # Determine output path
                if output_directory:
                    os.makedirs(output_directory, exist_ok=True)
                    relative_path = os.path.relpath(dae_file, dae_directory)
                    output_path = os.path.join(output_directory, relative_path)
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                else:
                    output_path = None

                # Process the DAE file
                if self.modify_mesh_names(dae_file, mesh_mapping, output_path):
                    success_count += 1
                    self.logger.info(f"Successfully processed DAE file: {dae_file}")
                else:
                    self.logger.error(f"Failed to process DAE file: {dae_file}")

            except Exception as e:
                self.logger.error(f"Error processing DAE file {dae_file}: {e}")

        self.logger.info(f"Successfully processed {success_count}/{len(dae_files)} DAE files")
        return success_count == len(dae_files)

    def extract_mesh_names_from_directory(self, dae_directory: str) -> Dict[str, List[str]]:
        """
        Extract mesh names from all DAE files in a directory

        Args:
            dae_directory: Directory containing DAE files

        Returns:
            Dictionary mapping DAE file paths to lists of mesh names
        """
        if not os.path.exists(dae_directory):
            self.logger.error(f"DAE directory not found: {dae_directory}")
            return {}

        mesh_names_by_file = {}

        # Find all DAE files in the directory
        for root, _, files in os.walk(dae_directory):
            for file in files:
                if file.lower().endswith('.dae'):
                    dae_file_path = os.path.join(root, file)
                    mesh_names = self.extract_mesh_names(dae_file_path)
                    if mesh_names:
                        mesh_names_by_file[dae_file_path] = mesh_names

        return mesh_names_by_file
