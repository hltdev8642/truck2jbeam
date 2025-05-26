#!/usr/bin/env python3
"""
Test suite for truck2jbeam converter

This module contains comprehensive tests for the truck2jbeam conversion
functionality, including unit tests and integration tests.
"""

import unittest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import modules to test
from rig import Rig, RigParseError, vector_distance, vector_length
from rig_common import Node, Beam, Engine, Triangle, Quad, Flexbody, Prop
import rig_parser as parser
from config import ConversionSettings, ConfigManager


class TestVectorFunctions(unittest.TestCase):
    """Test vector calculation functions"""

    def test_vector_distance(self):
        """Test vector distance calculation"""
        # Test basic distance
        dist = vector_distance(0, 0, 0, 3, 4, 0)
        self.assertEqual(dist, 25)  # 3^2 + 4^2 = 25

        # Test 3D distance
        dist = vector_distance(0, 0, 0, 1, 1, 1)
        self.assertEqual(dist, 3)  # 1^2 + 1^2 + 1^2 = 3

        # Test negative coordinates
        dist = vector_distance(-1, -1, -1, 1, 1, 1)
        self.assertEqual(dist, 12)  # 2^2 + 2^2 + 2^2 = 12

    def test_vector_length(self):
        """Test vector length calculation"""
        # Test basic length
        length = vector_length(0, 0, 0, 3, 4, 0)
        self.assertEqual(length, 5.0)  # sqrt(25) = 5

        # Test 3D length
        length = vector_length(0, 0, 0, 1, 1, 1)
        self.assertAlmostEqual(length, 1.732, places=3)  # sqrt(3)


class TestRigClass(unittest.TestCase):
    """Test Rig class functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.rig = Rig()

    def test_initialization(self):
        """Test Rig initialization"""
        self.assertEqual(self.rig.name, "Untitled Rig Class")
        self.assertEqual(len(self.rig.nodes), 0)
        self.assertEqual(len(self.rig.beams), 0)
        self.assertEqual(self.rig.dry_weight, 10000)
        self.assertEqual(self.rig.load_weight, 10000)
        self.assertEqual(self.rig.minimass, 50)

    def test_add_warning(self):
        """Test warning addition"""
        self.rig.add_warning("Test warning", 10)
        self.assertEqual(len(self.rig.parse_warnings), 1)
        self.assertIn("Line 10", self.rig.parse_warnings[0])

    def test_add_error(self):
        """Test error addition"""
        self.rig.add_error("Test error", 5)
        self.assertEqual(len(self.rig.parse_errors), 1)
        self.assertIn("Line 5", self.rig.parse_errors[0])

    def test_validation_empty_rig(self):
        """Test validation of empty rig"""
        is_valid = self.rig.validate()
        self.assertFalse(is_valid)
        self.assertGreater(len(self.rig.parse_errors), 0)

    def test_validation_with_nodes_and_beams(self):
        """Test validation with basic components"""
        # Add some test nodes
        node1 = Node("node1", 0, 0, 0)
        node2 = Node("node2", 1, 0, 0)
        self.rig.nodes = [node1, node2]

        # Add a test beam
        beam1 = Beam("node1", "node2", 9000000, 12000, 1000000, 400000)
        self.rig.beams = [beam1]

        is_valid = self.rig.validate()
        self.assertTrue(is_valid)

    def test_validation_orphaned_beams(self):
        """Test validation with orphaned beams"""
        # Add nodes
        node1 = Node("node1", 0, 0, 0)
        self.rig.nodes = [node1]

        # Add beam referencing non-existent node
        beam1 = Beam("node1", "node999", 9000000, 12000, 1000000, 400000)
        self.rig.beams = [beam1]

        self.rig.validate()
        self.assertGreater(len(self.rig.parse_warnings), 0)

    def test_get_statistics(self):
        """Test statistics generation"""
        # Add test data
        node1 = Node("node1", 0, 0, 0)
        node2 = Node("node2", 1, 0, 0)
        self.rig.nodes = [node1, node2]

        beam1 = Beam("node1", "node2", 9000000, 12000, 1000000, 400000)
        self.rig.beams = [beam1]

        stats = self.rig.get_statistics()

        self.assertEqual(stats['nodes'], 2)
        self.assertEqual(stats['beams'], 1)
        self.assertEqual(stats['dry_weight'], 10000)
        self.assertGreater(stats['total_beam_length'], 0)

    def test_calculate_masses_empty(self):
        """Test mass calculation with no nodes"""
        self.rig.calculate_masses()
        self.assertGreater(len(self.rig.parse_errors), 0)

    def test_calculate_masses_basic(self):
        """Test basic mass calculation"""
        # Add load-bearing nodes
        node1 = Node("node1", 0, 0, 0)
        node1.load_bearer = True
        node2 = Node("node2", 1, 0, 0)
        node2.load_bearer = True
        self.rig.nodes = [node1, node2]

        # Add beam
        beam1 = Beam("node1", "node2", 9000000, 12000, 1000000, 400000)
        self.rig.beams = [beam1]

        self.rig.calculate_masses()

        # Check that masses were calculated
        self.assertGreater(node1.mass, 0)
        self.assertGreater(node2.mass, 0)
        self.assertGreaterEqual(node1.mass, self.rig.minimass)
        self.assertGreaterEqual(node2.mass, self.rig.minimass)


class TestRigParser(unittest.TestCase):
    """Test rig parser functions"""

    def test_parse_node_name(self):
        """Test node name parsing"""
        # Test numeric node
        self.assertEqual(parser.ParseNodeName("123"), "node123")

        # Test named node
        self.assertEqual(parser.ParseNodeName("frontwheel"), "frontwheel")

    def test_parse_group_name(self):
        """Test group name parsing"""
        self.assertEqual(parser.ParseGroupName("wheel.mesh"), "wheel")
        self.assertEqual(parser.ParseGroupName("body.dae"), "body")
        self.assertEqual(parser.ParseGroupName("car-body.mesh"), "car_body")
        self.assertEqual(parser.ParseGroupName("test123"), "test123")

    def test_prepare_line(self):
        """Test line preparation"""
        # Test comment line
        self.assertIsNone(parser.PrepareLine("; this is a comment"))

        # Test empty line
        self.assertIsNone(parser.PrepareLine(""))

        # Test normal line
        components = parser.PrepareLine("nodes")
        self.assertEqual(components, ["nodes"])

        # Test line with data
        components = parser.PrepareLine("1, 0.0, 0.0, 0.0")
        self.assertEqual(len(components), 4)


class TestFileOperations(unittest.TestCase):
    """Test file operations"""

    def test_parse_invalid_file(self):
        """Test parsing non-existent file"""
        rig = Rig()

        with self.assertRaises(RigParseError):
            rig.from_file("nonexistent.truck")

    def test_parse_empty_file(self):
        """Test parsing empty file"""
        rig = Rig()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.truck', delete=False) as f:
            temp_path = f.name

        try:
            with self.assertRaises(RigParseError):
                rig.from_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_parse_minimal_truck(self):
        """Test parsing minimal valid truck file"""
        truck_content = """Test Truck
nodes
1, 0.0, 0.0, 0.0, l
2, 1.0, 0.0, 0.0, l

beams
1, 2

globals
1000, 500

end
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.truck', delete=False) as f:
            f.write(truck_content)
            temp_path = f.name

        try:
            rig = Rig()
            rig.from_file(temp_path)

            self.assertEqual(rig.name, "Test Truck")
            self.assertEqual(len(rig.nodes), 2)
            self.assertEqual(len(rig.beams), 1)
            self.assertEqual(rig.dry_weight, 1000)
            self.assertEqual(rig.load_weight, 500)

        finally:
            os.unlink(temp_path)


class TestTriangleQuadSupport(unittest.TestCase):
    """Test triangle and quad functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.rig = Rig()

        # Add test nodes
        self.node1 = Node("node1", 0, 0, 0)
        self.node2 = Node("node2", 1, 0, 0)
        self.node3 = Node("node3", 0, 1, 0)
        self.node4 = Node("node4", 1, 1, 0)
        self.rig.nodes = [self.node1, self.node2, self.node3, self.node4]

    def test_triangle_creation(self):
        """Test Triangle object creation"""
        triangle = Triangle("node1", "node2", "node3", "collision")

        self.assertEqual(triangle.node1, "node1")
        self.assertEqual(triangle.node2, "node2")
        self.assertEqual(triangle.node3, "node3")
        self.assertEqual(triangle.surface_type, "collision")
        self.assertTrue(triangle.is_collision())
        self.assertFalse(triangle.is_visual())

    def test_triangle_visual_type(self):
        """Test Triangle with visual surface type"""
        triangle = Triangle("node1", "node2", "node3", "visual")

        self.assertEqual(triangle.surface_type, "visual")
        self.assertFalse(triangle.is_collision())
        self.assertTrue(triangle.is_visual())

    def test_triangle_both_type(self):
        """Test Triangle with both collision and visual"""
        triangle = Triangle("node1", "node2", "node3", "both")

        self.assertEqual(triangle.surface_type, "both")
        self.assertTrue(triangle.is_collision())
        self.assertTrue(triangle.is_visual())

    def test_triangle_get_nodes(self):
        """Test Triangle get_nodes method"""
        triangle = Triangle("node1", "node2", "node3")
        nodes = triangle.get_nodes()

        self.assertEqual(len(nodes), 3)
        self.assertIn("node1", nodes)
        self.assertIn("node2", nodes)
        self.assertIn("node3", nodes)

    def test_quad_creation(self):
        """Test Quad object creation"""
        quad = Quad("node1", "node2", "node3", "node4", "collision")

        self.assertEqual(quad.node1, "node1")
        self.assertEqual(quad.node2, "node2")
        self.assertEqual(quad.node3, "node3")
        self.assertEqual(quad.node4, "node4")
        self.assertEqual(quad.surface_type, "collision")
        self.assertTrue(quad.is_collision())

    def test_quad_get_nodes(self):
        """Test Quad get_nodes method"""
        quad = Quad("node1", "node2", "node3", "node4")
        nodes = quad.get_nodes()

        self.assertEqual(len(nodes), 4)
        self.assertIn("node1", nodes)
        self.assertIn("node2", nodes)
        self.assertIn("node3", nodes)
        self.assertIn("node4", nodes)

    def test_quad_to_triangles(self):
        """Test Quad conversion to triangles"""
        quad = Quad("node1", "node2", "node3", "node4", "collision")
        quad.material = "metal"
        quad.drag_coefficient = 0.5

        triangles = quad.to_triangles()

        self.assertEqual(len(triangles), 2)

        # Check first triangle (1,2,3)
        tri1 = triangles[0]
        self.assertEqual(tri1.node1, "node1")
        self.assertEqual(tri1.node2, "node2")
        self.assertEqual(tri1.node3, "node3")
        self.assertEqual(tri1.material, "metal")
        self.assertEqual(tri1.drag_coefficient, 0.5)

        # Check second triangle (1,3,4)
        tri2 = triangles[1]
        self.assertEqual(tri2.node1, "node1")
        self.assertEqual(tri2.node2, "node3")
        self.assertEqual(tri2.node3, "node4")
        self.assertEqual(tri2.material, "metal")
        self.assertEqual(tri2.drag_coefficient, 0.5)

    def test_parse_triangle(self):
        """Test triangle parsing"""
        components = ["node1", "node2", "node3", "c", "0.5"]
        triangle = parser.ParseTriangle(components)

        self.assertEqual(triangle.node1, "node1")
        self.assertEqual(triangle.node2, "node2")
        self.assertEqual(triangle.node3, "node3")
        self.assertEqual(triangle.surface_type, "collision")
        self.assertIn('c', triangle.options)
        self.assertEqual(triangle.drag_coefficient, 0.5)

    def test_parse_quad(self):
        """Test quad parsing"""
        components = ["node1", "node2", "node3", "node4", "cv", "metal", "0.3"]
        quad = parser.ParseQuad(components)

        self.assertEqual(quad.node1, "node1")
        self.assertEqual(quad.node2, "node2")
        self.assertEqual(quad.node3, "node3")
        self.assertEqual(quad.node4, "node4")
        self.assertEqual(quad.surface_type, "both")  # 'c' and 'v' options
        self.assertIn('c', quad.options)
        self.assertIn('v', quad.options)
        self.assertEqual(quad.material, "metal")
        self.assertEqual(quad.lift_coefficient, 0.3)

    def test_parse_submesh_triangle(self):
        """Test submesh triangle parsing"""
        components = ["node1", "node2", "node3", "c"]
        triangle = parser.ParseSubmeshTriangle(components)

        self.assertEqual(triangle.node1, "node1")
        self.assertEqual(triangle.node2, "node2")
        self.assertEqual(triangle.node3, "node3")
        self.assertEqual(triangle.surface_type, "collision")
        self.assertIn('c', triangle.options)

    def test_rig_triangle_validation(self):
        """Test triangle validation in rig"""
        # Add valid triangle
        triangle = Triangle("node1", "node2", "node3")
        self.rig.triangles = [triangle]

        # Add invalid triangle
        invalid_triangle = Triangle("node1", "node2", "node999")
        self.rig.triangles.append(invalid_triangle)

        self.rig.validate()

        # Should have warning about invalid node
        self.assertGreater(len(self.rig.parse_warnings), 0)
        warning_found = any("node999" in warning for warning in self.rig.parse_warnings)
        self.assertTrue(warning_found)

    def test_rig_quad_validation(self):
        """Test quad validation in rig"""
        # Add valid quad
        quad = Quad("node1", "node2", "node3", "node4")
        self.rig.quads = [quad]

        # Add invalid quad
        invalid_quad = Quad("node1", "node2", "node3", "node999")
        self.rig.quads.append(invalid_quad)

        self.rig.validate()

        # Should have warning about invalid node
        self.assertGreater(len(self.rig.parse_warnings), 0)
        warning_found = any("node999" in warning for warning in self.rig.parse_warnings)
        self.assertTrue(warning_found)

    def test_rig_statistics_with_triangles_quads(self):
        """Test statistics include triangles and quads"""
        triangle = Triangle("node1", "node2", "node3")
        quad = Quad("node1", "node2", "node3", "node4")

        self.rig.triangles = [triangle]
        self.rig.quads = [quad]
        self.rig.legacy_triangles = [["node1", "node2", "node3"]]

        stats = self.rig.get_statistics()

        self.assertEqual(stats['triangles'], 1)
        self.assertEqual(stats['quads'], 1)
        self.assertEqual(stats['legacy_triangles'], 1)


class TestTriangleQuadParsing(unittest.TestCase):
    """Test triangle and quad parsing in rig files"""

    def test_parse_triangle_section(self):
        """Test parsing triangle section"""
        truck_content = """Test Truck
nodes
1, 0.0, 0.0, 0.0, l
2, 1.0, 0.0, 0.0, l
3, 0.0, 1.0, 0.0, l

triangles
1, 2, 3, c, 0.5
2, 3, 1, v

end
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.truck', delete=False) as f:
            f.write(truck_content)
            temp_path = f.name

        try:
            rig = Rig()
            rig.from_file(temp_path)

            self.assertEqual(len(rig.triangles), 2)

            # Check first triangle
            tri1 = rig.triangles[0]
            self.assertEqual(tri1.node1, "node1")
            self.assertEqual(tri1.node2, "node2")
            self.assertEqual(tri1.node3, "node3")
            self.assertEqual(tri1.surface_type, "collision")
            self.assertEqual(tri1.drag_coefficient, 0.5)

            # Check second triangle
            tri2 = rig.triangles[1]
            self.assertEqual(tri2.node1, "node2")
            self.assertEqual(tri2.node2, "node3")
            self.assertEqual(tri2.node3, "node1")
            self.assertEqual(tri2.surface_type, "visual")

        finally:
            os.unlink(temp_path)

    def test_parse_quad_section(self):
        """Test parsing quad section"""
        truck_content = """Test Truck
nodes
1, 0.0, 0.0, 0.0, l
2, 1.0, 0.0, 0.0, l
3, 1.0, 1.0, 0.0, l
4, 0.0, 1.0, 0.0, l

quads
1, 2, 3, 4, c, 0.3
2, 3, 4, 1, cv, metal

end
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.truck', delete=False) as f:
            f.write(truck_content)
            temp_path = f.name

        try:
            rig = Rig()
            rig.from_file(temp_path)

            self.assertEqual(len(rig.quads), 2)

            # Check first quad
            quad1 = rig.quads[0]
            self.assertEqual(quad1.node1, "node1")
            self.assertEqual(quad1.node2, "node2")
            self.assertEqual(quad1.node3, "node3")
            self.assertEqual(quad1.node4, "node4")
            self.assertEqual(quad1.surface_type, "collision")
            self.assertEqual(quad1.drag_coefficient, 0.3)

            # Check second quad
            quad2 = rig.quads[1]
            self.assertEqual(quad2.surface_type, "both")
            self.assertEqual(quad2.material, "metal")

        finally:
            os.unlink(temp_path)


class TestFlexbodyPropSupport(unittest.TestCase):
    """Test flexbody and prop functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.rig = Rig()

        # Add test nodes
        self.node1 = Node("node1", 0, 0, 0)
        self.node2 = Node("node2", 1, 0, 0)
        self.node3 = Node("node3", 0, 1, 0)
        self.rig.nodes = [self.node1, self.node2, self.node3]

    def test_flexbody_creation(self):
        """Test Flexbody object creation"""
        flexbody = Flexbody("node1", "node2", "node3", 0.1, 0.2, 0.3, 10, 20, 30, "test.mesh")

        self.assertEqual(flexbody.refnode, "node1")
        self.assertEqual(flexbody.xnode, "node2")
        self.assertEqual(flexbody.ynode, "node3")
        self.assertEqual(flexbody.offsetX, 0.1)
        self.assertEqual(flexbody.offsetY, 0.2)
        self.assertEqual(flexbody.offsetZ, 0.3)
        self.assertEqual(flexbody.rotX, 10)
        self.assertEqual(flexbody.rotY, 20)
        self.assertEqual(flexbody.rotZ, 30)
        self.assertEqual(flexbody.mesh, "test.mesh")

    def test_flexbody_enhanced_properties(self):
        """Test enhanced flexbody properties"""
        flexbody = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "test.mesh")

        # Test default values
        self.assertEqual(flexbody.scale, [1.0, 1.0, 1.0])
        self.assertEqual(flexbody.forset_nodes, [])
        self.assertEqual(flexbody.non_flex_materials, [])
        self.assertFalse(flexbody.disable_mesh_breaking)
        self.assertEqual(flexbody.plastic_deform_coef, 0.0)

        # Test setting properties
        flexbody.scale = [2.0, 1.5, 1.0]
        flexbody.disable_mesh_breaking = True
        flexbody.plastic_deform_coef = 0.5

        self.assertEqual(flexbody.scale, [2.0, 1.5, 1.0])
        self.assertTrue(flexbody.disable_mesh_breaking)
        self.assertEqual(flexbody.plastic_deform_coef, 0.5)

    def test_flexbody_group_name(self):
        """Test flexbody group name generation"""
        flexbody = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "car_body.mesh")

        group_name = flexbody.get_group_name()
        self.assertEqual(group_name, "car_body_flexbody")

        # Test with custom group name
        flexbody.group_name = "custom_body"
        self.assertEqual(flexbody.get_group_name(), "custom_body")

    def test_flexbody_get_nodes(self):
        """Test flexbody get_nodes method"""
        flexbody = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "test.mesh")
        flexbody.forset_nodes = ["node4", "node5"]

        nodes = flexbody.get_nodes()
        self.assertEqual(len(nodes), 5)
        self.assertIn("node1", nodes)
        self.assertIn("node2", nodes)
        self.assertIn("node3", nodes)
        self.assertIn("node4", nodes)
        self.assertIn("node5", nodes)

    def test_prop_creation(self):
        """Test Prop object creation"""
        prop = Prop("node1", "node2", "node3", 0.1, 0.2, 0.3, 10, 20, 30, "wheel.mesh")

        self.assertEqual(prop.refnode, "node1")
        self.assertEqual(prop.xnode, "node2")
        self.assertEqual(prop.ynode, "node3")
        self.assertEqual(prop.offsetX, 0.1)
        self.assertEqual(prop.offsetY, 0.2)
        self.assertEqual(prop.offsetZ, 0.3)
        self.assertEqual(prop.rotX, 10)
        self.assertEqual(prop.rotY, 20)
        self.assertEqual(prop.rotZ, 30)
        self.assertEqual(prop.mesh, "wheel.mesh")

    def test_prop_enhanced_properties(self):
        """Test enhanced prop properties"""
        prop = Prop("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "wheel.mesh")

        # Test default values
        self.assertEqual(prop.scale, [1.0, 1.0, 1.0])
        self.assertTrue(prop.collision_enabled)
        self.assertTrue(prop.shadow_enabled)
        self.assertEqual(prop.animation_factor, 0.0)
        self.assertEqual(prop.animation_mode, "rotation")
        self.assertEqual(prop.animation_axis, [0, 0, 1])

        # Test setting properties
        prop.scale = [0.8, 0.8, 0.8]
        prop.collision_enabled = False
        prop.animation_factor = 45.0
        prop.animation_mode = "translation"
        prop.animation_axis = [1, 0, 0]

        self.assertEqual(prop.scale, [0.8, 0.8, 0.8])
        self.assertFalse(prop.collision_enabled)
        self.assertEqual(prop.animation_factor, 45.0)
        self.assertEqual(prop.animation_mode, "translation")
        self.assertEqual(prop.animation_axis, [1, 0, 0])

    def test_prop_group_name(self):
        """Test prop group name generation"""
        prop = Prop("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "steering_wheel.mesh")

        group_name = prop.get_group_name()
        self.assertEqual(group_name, "steering_wheel_prop")

        # Test with custom group name
        prop.group_name = "custom_wheel"
        self.assertEqual(prop.get_group_name(), "custom_wheel")

    def test_prop_get_nodes(self):
        """Test prop get_nodes method"""
        prop = Prop("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "test.mesh")

        nodes = prop.get_nodes()
        self.assertEqual(len(nodes), 3)
        self.assertIn("node1", nodes)
        self.assertIn("node2", nodes)
        self.assertIn("node3", nodes)

    def test_parse_flexbody(self):
        """Test flexbody parsing"""
        components = ["node1", "node2", "node3", "0.1", "0.2", "0.3", "10", "20", "30", "car.mesh", "2.0", "1.5", "1.0"]
        flexbody = parser.ParseFlexbody(components)

        self.assertEqual(flexbody.refnode, "node1")
        self.assertEqual(flexbody.xnode, "node2")
        self.assertEqual(flexbody.ynode, "node3")
        self.assertEqual(flexbody.offsetX, 0.3)  # Note: RoR coordinate mapping
        self.assertEqual(flexbody.offsetY, 0.1)
        self.assertEqual(flexbody.offsetZ, 0.2)
        self.assertEqual(flexbody.rotX, 30)
        self.assertEqual(flexbody.rotY, 10)
        self.assertEqual(flexbody.rotZ, 20)
        self.assertEqual(flexbody.mesh, "car.mesh")
        self.assertEqual(flexbody.scale, [2.0, 1.5, 1.0])

    def test_parse_prop(self):
        """Test prop parsing"""
        components = ["node1", "node2", "node3", "0.1", "0.2", "0.3", "10", "20", "30", "wheel.mesh", "0.8", "0.8", "0.8", "45.0", "rotation"]
        prop = parser.ParseProp(components)

        self.assertEqual(prop.refnode, "node1")
        self.assertEqual(prop.xnode, "node2")
        self.assertEqual(prop.ynode, "node3")
        self.assertEqual(prop.mesh, "wheel.mesh")
        self.assertEqual(prop.scale, [0.8, 0.8, 0.8])
        self.assertEqual(prop.animation_factor, 45.0)
        self.assertEqual(prop.animation_mode, "rotation")

    def test_rig_flexbody_validation(self):
        """Test flexbody validation in rig"""
        # Add valid flexbody
        flexbody = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "valid.mesh")
        self.rig.flexbodies = [flexbody]

        # Add invalid flexbody
        invalid_flexbody = Flexbody("node1", "node2", "node999", 0, 0, 0, 0, 0, 0, "invalid.txt")
        invalid_flexbody.scale = [-1.0, 1.0, 1.0]  # Invalid scale
        self.rig.flexbodies.append(invalid_flexbody)

        self.rig.validate()

        # Should have warnings about invalid node, unusual format, and invalid scale
        self.assertGreater(len(self.rig.parse_warnings), 0)
        warning_messages = ' '.join(self.rig.parse_warnings)
        self.assertIn("node999", warning_messages)
        self.assertIn("unusual mesh format", warning_messages)
        self.assertIn("invalid scale", warning_messages)

    def test_rig_prop_validation(self):
        """Test prop validation in rig"""
        # Add valid prop
        prop = Prop("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "valid.mesh")
        self.rig.props = [prop]

        # Add invalid prop
        invalid_prop = Prop("node1", "node2", "node999", 0, 0, 0, 0, 0, 0, "invalid.txt")
        invalid_prop.scale = [0.0, 1.0, 1.0]  # Invalid scale
        invalid_prop.animation_factor = 1.0
        invalid_prop.animation_mode = "invalid_mode"  # Invalid animation mode
        self.rig.props.append(invalid_prop)

        self.rig.validate()

        # Should have warnings about invalid node, unusual format, invalid scale, and invalid animation mode
        self.assertGreater(len(self.rig.parse_warnings), 0)
        warning_messages = ' '.join(self.rig.parse_warnings)
        self.assertIn("node999", warning_messages)
        self.assertIn("unusual mesh format", warning_messages)
        self.assertIn("invalid scale", warning_messages)
        self.assertIn("invalid animation mode", warning_messages)

    def test_rig_statistics_with_flexbodies_props(self):
        """Test statistics include flexbodies and props"""
        flexbody = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "car.mesh")
        prop = Prop("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "wheel.mesh")

        self.rig.flexbodies = [flexbody]
        self.rig.props = [prop]

        stats = self.rig.get_statistics()

        self.assertEqual(stats['flexbodies'], 1)
        self.assertEqual(stats['props'], 1)

    def test_flexbody_group_assignment(self):
        """Test that flexbody nodes are properly assigned to groups"""
        # Create flexbody
        flexbody = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "car_body.mesh")
        flexbody.forset_nodes = ["node4"]  # Manually add a forset node
        self.rig.flexbodies = [flexbody]

        # Add a fourth node for forset
        node4 = Node("node4", 0.5, 0.5, 0.5)
        self.rig.nodes.append(node4)

        # Run the group assignment
        self.rig._assign_flexbody_groups()

        # Check that reference nodes are assigned to the flexbody group
        expected_group = "car_body_flexbody"

        node1 = next(n for n in self.rig.nodes if n.name == "node1")
        node2 = next(n for n in self.rig.nodes if n.name == "node2")
        node3 = next(n for n in self.rig.nodes if n.name == "node3")
        node4 = next(n for n in self.rig.nodes if n.name == "node4")

        self.assertIn(expected_group, node1.group)
        self.assertIn(expected_group, node2.group)
        self.assertIn(expected_group, node3.group)
        self.assertIn(expected_group, node4.group)  # forset node

    def test_prop_group_assignment(self):
        """Test that prop nodes are properly assigned to groups"""
        # Create prop
        prop = Prop("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "steering_wheel.mesh")
        self.rig.props = [prop]

        # Run the group assignment
        self.rig._assign_flexbody_groups()

        # Check that reference nodes are assigned to the prop group
        expected_group = "steering_wheel_prop"

        node1 = next(n for n in self.rig.nodes if n.name == "node1")
        node2 = next(n for n in self.rig.nodes if n.name == "node2")
        node3 = next(n for n in self.rig.nodes if n.name == "node3")

        self.assertIn(expected_group, node1.group)
        self.assertIn(expected_group, node2.group)
        self.assertIn(expected_group, node3.group)

    def test_automatic_flexbody_node_detection(self):
        """Test automatic detection of flexbody nodes based on proximity"""
        # Create a flexbody without forset nodes
        flexbody = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "body.mesh")
        self.rig.flexbodies = [flexbody]

        # Add more nodes in the vicinity
        node4 = Node("node4", 0.5, 0.5, 0.5)  # Close to the reference nodes
        node5 = Node("node5", 10.0, 10.0, 10.0)  # Far from reference nodes
        self.rig.nodes.extend([node4, node5])

        # Run the group assignment
        self.rig._assign_flexbody_groups()

        expected_group = "body_flexbody"

        # Close node should be included
        node4 = next(n for n in self.rig.nodes if n.name == "node4")
        self.assertIn(expected_group, node4.group)

        # Far node should not be included (depending on the algorithm)
        node5 = next(n for n in self.rig.nodes if n.name == "node5")
        # This might or might not be included depending on the search radius

    def test_duplicate_mesh_name_resolution(self):
        """Test resolution of duplicate mesh names in flexbodies and props"""
        # Create multiple flexbodies and props with duplicate mesh names
        flexbody1 = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "wheel.mesh")
        flexbody2 = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "wheel.mesh")  # Duplicate
        flexbody3 = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "body.mesh")   # Unique

        prop1 = Prop("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "wheel.mesh")  # Duplicate with flexbodies
        prop2 = Prop("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "antenna.mesh")  # Unique
        prop3 = Prop("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "antenna.mesh")  # Duplicate

        self.rig.flexbodies = [flexbody1, flexbody2, flexbody3]
        self.rig.props = [prop1, prop2, prop3]

        # Store original mesh names for comparison
        original_meshes = [
            flexbody1.mesh, flexbody2.mesh, flexbody3.mesh,
            prop1.mesh, prop2.mesh, prop3.mesh
        ]

        # Run duplicate resolution
        self.rig._resolve_duplicate_mesh_names()

        # Check that duplicates were renamed
        final_meshes = [
            flexbody1.mesh, flexbody2.mesh, flexbody3.mesh,
            prop1.mesh, prop2.mesh, prop3.mesh
        ]

        # All mesh names should now be unique
        self.assertEqual(len(set(final_meshes)), len(final_meshes))

        # Check specific renaming patterns
        wheel_meshes = [m for m in final_meshes if m.startswith("wheel")]
        antenna_meshes = [m for m in final_meshes if m.startswith("antenna")]

        # Should have 3 wheel variants and 2 antenna variants
        self.assertEqual(len(wheel_meshes), 3)
        self.assertEqual(len(antenna_meshes), 2)

        # Check that unique mesh names weren't changed
        self.assertEqual(flexbody3.mesh, "body.mesh")

        # Check that renamed meshes follow the pattern
        self.assertIn("wheel_001.mesh", final_meshes)
        self.assertIn("wheel_002.mesh", final_meshes)
        self.assertIn("wheel_003.mesh", final_meshes)
        self.assertIn("antenna_001.mesh", final_meshes)
        self.assertIn("antenna_002.mesh", final_meshes)

    def test_generate_unique_mesh_name(self):
        """Test unique mesh name generation"""
        # Test with .mesh extension
        result1 = self.rig._generate_unique_mesh_name("wheel.mesh", 0)
        self.assertEqual(result1, "wheel_001.mesh")

        result2 = self.rig._generate_unique_mesh_name("wheel.mesh", 1)
        self.assertEqual(result2, "wheel_002.mesh")

        result3 = self.rig._generate_unique_mesh_name("wheel.mesh", 9)
        self.assertEqual(result3, "wheel_010.mesh")

        # Test with .dae extension
        result4 = self.rig._generate_unique_mesh_name("body.dae", 0)
        self.assertEqual(result4, "body_001.dae")

        # Test with no extension
        result5 = self.rig._generate_unique_mesh_name("antenna", 2)
        self.assertEqual(result5, "antenna_003")

        # Test with complex filename
        result6 = self.rig._generate_unique_mesh_name("car-body_v2.mesh", 0)
        self.assertEqual(result6, "car-body_v2_001.mesh")

    def test_duplicate_resolution_case_insensitive(self):
        """Test that duplicate resolution is case-insensitive"""
        flexbody1 = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "Wheel.mesh")
        flexbody2 = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "wheel.mesh")
        flexbody3 = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "WHEEL.MESH")

        self.rig.flexbodies = [flexbody1, flexbody2, flexbody3]

        # Run duplicate resolution
        self.rig._resolve_duplicate_mesh_names()

        # All should be renamed since they're considered duplicates (case-insensitive)
        final_meshes = [flexbody1.mesh, flexbody2.mesh, flexbody3.mesh]

        # All mesh names should be unique
        self.assertEqual(len(set(final_meshes)), 3)

        # Should follow the naming pattern
        self.assertIn("Wheel_001.mesh", final_meshes)
        self.assertIn("wheel_002.mesh", final_meshes)
        self.assertIn("WHEEL_003.MESH", final_meshes)


class TestFlexbodyPropParsing(unittest.TestCase):
    """Test flexbody and prop parsing in rig files"""

    def test_parse_flexbody_section(self):
        """Test parsing flexbody section"""
        truck_content = """Test Truck
nodes
1, 0.0, 0.0, 0.0, l
2, 1.0, 0.0, 0.0, l
3, 0.0, 1.0, 0.0, l

flexbodies
1, 2, 3, 0.1, 0.2, 0.3, 10, 20, 30, car_body.mesh, 2.0, 1.5, 1.0

end
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.truck', delete=False) as f:
            f.write(truck_content)
            temp_path = f.name

        try:
            rig = Rig()
            rig.from_file(temp_path)

            self.assertEqual(len(rig.flexbodies), 1)

            # Check flexbody
            fb = rig.flexbodies[0]
            self.assertEqual(fb.refnode, "node1")
            self.assertEqual(fb.xnode, "node2")
            self.assertEqual(fb.ynode, "node3")
            self.assertEqual(fb.mesh, "car_body.mesh")
            self.assertEqual(fb.scale, [2.0, 1.5, 1.0])

        finally:
            os.unlink(temp_path)

    def test_parse_prop_section(self):
        """Test parsing prop section"""
        truck_content = """Test Truck
nodes
1, 0.0, 0.0, 0.0, l
2, 1.0, 0.0, 0.0, l
3, 0.0, 1.0, 0.0, l

props
1, 2, 3, 0.1, 0.2, 0.3, 10, 20, 30, steering_wheel.mesh, 0.8, 0.8, 0.8, 45.0, rotation

end
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.truck', delete=False) as f:
            f.write(truck_content)
            temp_path = f.name

        try:
            rig = Rig()
            rig.from_file(temp_path)

            self.assertEqual(len(rig.props), 1)

            # Check prop
            prop = rig.props[0]
            self.assertEqual(prop.refnode, "node1")
            self.assertEqual(prop.xnode, "node2")
            self.assertEqual(prop.ynode, "node3")
            self.assertEqual(prop.mesh, "steering_wheel.mesh")
            self.assertEqual(prop.scale, [0.8, 0.8, 0.8])
            self.assertEqual(prop.animation_factor, 45.0)
            self.assertEqual(prop.animation_mode, "rotation")

        finally:
            os.unlink(temp_path)

    def test_parse_flexbody_with_forset(self):
        """Test parsing flexbody with forset for proper node grouping"""
        truck_content = """Test Truck
nodes
1, 0.0, 0.0, 0.0, l
2, 1.0, 0.0, 0.0, l
3, 0.0, 1.0, 0.0, l
4, 0.5, 0.5, 0.5, l
5, 0.3, 0.3, 0.3, l

flexbodies
1, 2, 3, 0.0, 0.0, 0.5, 0, 0, 0, car_body.mesh, 1.0, 1.0, 1.0
forset 3-4

end
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.truck', delete=False) as f:
            f.write(truck_content)
            temp_path = f.name

        try:
            rig = Rig()
            rig.from_file(temp_path)

            self.assertEqual(len(rig.flexbodies), 1)

            # Check flexbody has forset nodes
            flexbody = rig.flexbodies[0]
            self.assertTrue(hasattr(flexbody, 'forset_nodes'))
            self.assertIn("node4", flexbody.forset_nodes)
            self.assertIn("node5", flexbody.forset_nodes)

            # Test JBeam output with proper grouping
            output_file = "test_flexbody_forset.jbeam"
            rig.to_jbeam(output_file)

            # Verify nodes are properly grouped
            expected_group = "car_body_flexbody"

            # Check that forset nodes are assigned to the flexbody group
            node4 = next(n for n in rig.nodes if n.name == "node4")
            node5 = next(n for n in rig.nodes if n.name == "node5")

            self.assertIn(expected_group, node4.group)
            self.assertIn(expected_group, node5.group)

            # Verify JBeam file contains proper grouping
            with open(output_file, 'r') as f:
                content = f.read()
                self.assertIn('"flexbodies":', content)
                self.assertIn(expected_group, content)

            # Clean up
            os.unlink(output_file)

        finally:
            os.unlink(temp_path)

    def test_parse_truck_with_duplicate_meshes(self):
        """Test parsing truck file with duplicate mesh names and proper resolution"""
        truck_content = """Test Truck with Duplicates
nodes
1, 0.0, 0.0, 0.0, l
2, 1.0, 0.0, 0.0, l
3, 0.0, 1.0, 0.0, l
4, 0.5, 0.5, 0.5, l

flexbodies
1, 2, 3, 0.0, 0.0, 0.5, 0, 0, 0, wheel.mesh, 1.0, 1.0, 1.0
1, 2, 3, 0.0, 0.0, 0.5, 0, 0, 0, wheel.mesh, 1.0, 1.0, 1.0
1, 2, 3, 0.0, 0.0, 0.5, 0, 0, 0, body.mesh, 1.0, 1.0, 1.0

props
1, 2, 3, 0.0, 0.0, 1.0, 0, 0, 0, wheel.mesh, 0.5, 0.5, 0.5
1, 2, 3, 0.0, 0.0, 1.0, 0, 0, 0, antenna.mesh, 0.5, 0.5, 0.5
1, 2, 3, 0.0, 0.0, 1.0, 0, 0, 0, antenna.mesh, 0.5, 0.5, 0.5

end
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.truck', delete=False) as f:
            f.write(truck_content)
            temp_path = f.name

        try:
            rig = Rig()
            rig.from_file(temp_path)

            # Should have parsed all elements
            self.assertEqual(len(rig.flexbodies), 3)
            self.assertEqual(len(rig.props), 3)

            # Test JBeam output with duplicate resolution
            output_file = "test_duplicate_meshes.jbeam"
            rig.to_jbeam(output_file)

            # Collect all mesh names after processing
            all_meshes = [fb.mesh for fb in rig.flexbodies] + [p.mesh for p in rig.props]

            # All mesh names should be unique
            self.assertEqual(len(set(all_meshes)), len(all_meshes))

            # Check that we have the expected renamed meshes
            wheel_meshes = [m for m in all_meshes if m.startswith("wheel")]
            antenna_meshes = [m for m in all_meshes if m.startswith("antenna")]
            body_meshes = [m for m in all_meshes if m.startswith("body")]

            self.assertEqual(len(wheel_meshes), 3)  # 2 flexbodies + 1 prop
            self.assertEqual(len(antenna_meshes), 2)  # 2 props
            self.assertEqual(len(body_meshes), 1)  # 1 flexbody (unique, not renamed)

            # Verify JBeam file contains unique mesh references
            with open(output_file, 'r') as f:
                content = f.read()
                self.assertIn('"flexbodies":', content)
                self.assertIn('"props":', content)

                # Should contain renamed mesh references
                self.assertIn("wheel_001", content)
                self.assertIn("wheel_002", content)
                self.assertIn("wheel_003", content)
                self.assertIn("antenna_001", content)
                self.assertIn("antenna_002", content)
                self.assertIn("body", content)  # Should be unchanged

            # Clean up
            os.unlink(output_file)

        finally:
            os.unlink(temp_path)


class TestDAEProcessor(unittest.TestCase):
    """Test DAE file processing functionality"""

    def setUp(self):
        """Set up test fixtures"""
        from dae_processor import DAEProcessor
        self.dae_processor = DAEProcessor()

    def test_dae_processor_initialization(self):
        """Test DAE processor initialization"""
        self.assertIsNotNone(self.dae_processor)
        self.assertIsInstance(self.dae_processor.has_lxml, bool)

    def test_extract_mesh_names_basic(self):
        """Test basic mesh name extraction from DAE content"""
        # Create a simple DAE file content
        dae_content = '''<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <library_geometries>
    <geometry id="wheel_mesh" name="wheel">
      <mesh>
        <source id="wheel_mesh-positions">
          <float_array id="wheel_mesh-positions-array" count="24">
            1.0 1.0 1.0 -1.0 1.0 1.0 -1.0 -1.0 1.0 1.0 -1.0 1.0
          </float_array>
        </source>
      </mesh>
    </geometry>
    <geometry id="body_mesh" name="car_body">
      <mesh>
        <source id="body_mesh-positions">
          <float_array id="body_mesh-positions-array" count="12">
            2.0 2.0 2.0 -2.0 2.0 2.0
          </float_array>
        </source>
      </mesh>
    </geometry>
  </library_geometries>
  <library_visual_scenes>
    <visual_scene id="Scene" name="Scene">
      <node id="wheel_node" name="wheel_node" type="NODE">
        <instance_geometry url="#wheel_mesh"/>
      </node>
      <node id="body_node" name="body_node" type="NODE">
        <instance_geometry url="#body_mesh"/>
      </node>
    </visual_scene>
  </library_visual_scenes>
</COLLADA>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.dae', delete=False) as f:
            f.write(dae_content)
            temp_path = f.name

        try:
            mesh_names = self.dae_processor.extract_mesh_names(temp_path)

            # Should extract geometry IDs, names, node IDs, and instance references
            expected_names = {'wheel_mesh', 'wheel', 'body_mesh', 'car_body', 'wheel_node', 'body_node'}
            found_names = set(mesh_names)

            # Check that we found the expected mesh names
            self.assertTrue(expected_names.issubset(found_names),
                          f"Expected {expected_names} to be subset of {found_names}")

        finally:
            os.unlink(temp_path)

    def test_modify_mesh_names_basic(self):
        """Test basic mesh name modification in DAE files"""
        # Create a simple DAE file
        dae_content = '''<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <library_geometries>
    <geometry id="wheel" name="wheel">
      <mesh>
        <source id="wheel-positions">
          <float_array id="wheel-positions-array" count="24">
            1.0 1.0 1.0 -1.0 1.0 1.0
          </float_array>
        </source>
      </mesh>
    </geometry>
  </library_geometries>
  <library_visual_scenes>
    <visual_scene id="Scene" name="Scene">
      <node id="wheel_node" name="wheel_node" type="NODE">
        <instance_geometry url="#wheel"/>
      </node>
    </visual_scene>
  </library_visual_scenes>
</COLLADA>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.dae', delete=False) as f:
            f.write(dae_content)
            temp_path = f.name

        try:
            # Define mesh mapping
            mesh_mapping = {
                'wheel': 'wheel_flexbody',
                'wheel_node': 'wheel_node_group'
            }

            # Create output file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.dae', delete=False) as f:
                output_path = f.name

            try:
                # Modify mesh names
                success = self.dae_processor.modify_mesh_names(temp_path, mesh_mapping, output_path)
                self.assertTrue(success)

                # Read the modified file
                with open(output_path, 'r', encoding='utf-8') as f:
                    modified_content = f.read()

                # Check that mesh names were modified
                self.assertIn('id="wheel_flexbody"', modified_content)
                self.assertIn('name="wheel_flexbody"', modified_content)
                self.assertIn('id="wheel_node_group"', modified_content)
                self.assertIn('url="#wheel_flexbody"', modified_content)

                # Check that old names are gone
                self.assertNotIn('id="wheel"', modified_content)
                self.assertNotIn('url="#wheel"', modified_content)

            finally:
                os.unlink(output_path)

        finally:
            os.unlink(temp_path)

    def test_generate_mesh_mapping(self):
        """Test mesh mapping generation from flexbodies and props"""
        from rig_common import Flexbody, Prop

        # Create test flexbodies and props
        flexbody1 = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "wheel.dae")
        flexbody2 = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "body.mesh")

        prop1 = Prop("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "antenna.dae")
        prop2 = Prop("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "mirror.mesh")

        flexbodies = [flexbody1, flexbody2]
        props = [prop1, prop2]

        # Generate mesh mapping
        mesh_mapping = self.dae_processor.generate_mesh_mapping(flexbodies, props)

        # Check that mapping includes both base names and full names
        expected_mappings = {
            'wheel': 'wheel_flexbody',
            'wheel.dae': 'wheel_flexbody',
            'body': 'body_flexbody',
            'body.mesh': 'body_flexbody',
            'antenna': 'antenna_prop',
            'antenna.dae': 'antenna_prop',
            'mirror': 'mirror_prop',
            'mirror.mesh': 'mirror_prop'
        }

        for key, expected_value in expected_mappings.items():
            self.assertIn(key, mesh_mapping)
            self.assertEqual(mesh_mapping[key], expected_value)

    def test_extract_mesh_names_from_directory(self):
        """Test extracting mesh names from a directory of DAE files"""
        # Create a temporary directory with DAE files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create first DAE file
            dae1_content = '''<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <library_geometries>
    <geometry id="wheel1" name="front_wheel">
      <mesh></mesh>
    </geometry>
  </library_geometries>
</COLLADA>'''

            dae1_path = os.path.join(temp_dir, "wheel.dae")
            with open(dae1_path, 'w', encoding='utf-8') as f:
                f.write(dae1_content)

            # Create second DAE file
            dae2_content = '''<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <library_geometries>
    <geometry id="body1" name="car_body">
      <mesh></mesh>
    </geometry>
  </library_geometries>
</COLLADA>'''

            dae2_path = os.path.join(temp_dir, "body.dae")
            with open(dae2_path, 'w', encoding='utf-8') as f:
                f.write(dae2_content)

            # Extract mesh names from directory
            mesh_names_by_file = self.dae_processor.extract_mesh_names_from_directory(temp_dir)

            # Check results
            self.assertEqual(len(mesh_names_by_file), 2)

            # Check that both files are included
            dae_files = list(mesh_names_by_file.keys())
            self.assertTrue(any(f.endswith('wheel.dae') for f in dae_files))
            self.assertTrue(any(f.endswith('body.dae') for f in dae_files))

            # Check mesh names
            all_mesh_names = []
            for mesh_names in mesh_names_by_file.values():
                all_mesh_names.extend(mesh_names)

            expected_names = {'wheel1', 'front_wheel', 'body1', 'car_body'}
            found_names = set(all_mesh_names)
            self.assertTrue(expected_names.issubset(found_names))


class TestConfigManager(unittest.TestCase):
    """Test configuration management"""

    def setUp(self):
        """Set up test fixtures"""
        self.config_manager = ConfigManager()

    def test_default_settings(self):
        """Test default settings"""
        settings = self.config_manager.settings
        self.assertEqual(settings.minimum_mass, 50.0)
        self.assertEqual(settings.default_author, "truck2jbeam converter")
        self.assertTrue(settings.pretty_print)

    def test_default_templates(self):
        """Test default templates"""
        templates = self.config_manager.list_templates()
        self.assertIn("car", templates)
        self.assertIn("truck", templates)
        self.assertIn("airplane", templates)
        self.assertIn("trailer", templates)

    def test_get_template(self):
        """Test template retrieval"""
        car_template = self.config_manager.get_template("car")
        self.assertIsNotNone(car_template)
        self.assertEqual(car_template.name, "car")
        self.assertEqual(car_template.settings.minimum_mass, 25.0)

    def test_apply_template(self):
        """Test template application"""
        original_mass = self.config_manager.settings.minimum_mass

        success = self.config_manager.apply_template("car")
        self.assertTrue(success)
        self.assertNotEqual(self.config_manager.settings.minimum_mass, original_mass)
        self.assertEqual(self.config_manager.settings.minimum_mass, 25.0)

    def test_save_load_config(self):
        """Test configuration save/load"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Modify settings
            self.config_manager.settings.minimum_mass = 123.45
            self.config_manager.settings.default_author = "Test Author"

            # Save config
            success = self.config_manager.save_config(temp_path)
            self.assertTrue(success)
            self.assertTrue(temp_path.exists())

            # Create new config manager and load
            new_config = ConfigManager()
            new_config.config_path = temp_path
            success = new_config.load_config()
            self.assertTrue(success)

            # Verify settings were loaded
            self.assertEqual(new_config.settings.minimum_mass, 123.45)
            self.assertEqual(new_config.settings.default_author, "Test Author")

        finally:
            if temp_path.exists():
                temp_path.unlink()


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestVectorFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestRigClass))
    suite.addTests(loader.loadTestsFromTestCase(TestRigParser))
    suite.addTests(loader.loadTestsFromTestCase(TestFileOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestTriangleQuadSupport))
    suite.addTests(loader.loadTestsFromTestCase(TestTriangleQuadParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestFlexbodyPropSupport))
    suite.addTests(loader.loadTestsFromTestCase(TestFlexbodyPropParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestDAEProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
