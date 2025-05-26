#!/usr/bin/env python3
"""
Example usage of the enhanced truck2jbeam converter

This script demonstrates various ways to use the truck2jbeam converter
programmatically and provides examples of common use cases.
"""

import os
import tempfile
from pathlib import Path

from rig import Rig
from config import get_config, ConversionSettings
import truck2jbeam

# Optional import for download examples
try:
    from ror_downloader import RoRDownloader
    DOWNLOAD_AVAILABLE = True
except ImportError:
    DOWNLOAD_AVAILABLE = False


def create_sample_truck_file() -> str:
    """Create a sample truck file for demonstration"""
    truck_content = """Sample Truck
; This is a simple truck file for demonstration

globals
2000, 1000

nodes
; id,  x,    y,    z,   options
1,     0.0,  0.0,  0.0, l
2,     2.0,  0.0,  0.0, l
3,     1.0,  0.0,  1.0, l
4,     0.0,  1.0,  0.0, l
5,     2.0,  1.0,  0.0, l
6,     1.0,  1.0,  1.0, l

beams
; node1, node2, options
1, 2
1, 3
1, 4
2, 3
2, 5
3, 4
3, 5
3, 6
4, 5
4, 6
5, 6

wheels
; radius, width, rays, n1, n2, snode, braked, propulsed, arm, mass, spring, damp
0.5, 0.3, 12, 1, 4, 9999, 1, 1, 2, 50, 800000, 4000
0.5, 0.3, 12, 2, 5, 9999, 1, 1, 3, 50, 800000, 4000

engine
1000, 3000, 200, 3.5, -3.0, 1.0, 2.5, 4.0

brakes
5000

end
"""

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.truck', delete=False) as f:
        f.write(truck_content)
        return f.name


def example_basic_conversion():
    """Example 1: Basic file conversion"""
    print("Example 1: Basic Conversion")
    print("=" * 40)

    # Create sample file
    truck_file = create_sample_truck_file()

    try:
        # Create rig instance and parse file
        rig = Rig()
        rig.from_file(truck_file)

        # Calculate masses
        rig.calculate_masses()

        # Get statistics
        stats = rig.get_statistics()
        print(f"Loaded truck: {rig.name}")
        print(f"Nodes: {stats['nodes']}")
        print(f"Beams: {stats['beams']}")
        print(f"Wheels: {stats['wheels']}")
        print(f"Total beam length: {stats['total_beam_length']:.2f}")

        # Convert to JBeam
        output_file = truck_file.replace('.truck', '.jbeam')
        rig.to_jbeam(output_file)

        print(f"Converted to: {output_file}")
        print(f"Output file size: {os.path.getsize(output_file)} bytes")

    finally:
        # Cleanup
        if os.path.exists(truck_file):
            os.unlink(truck_file)
        output_file = truck_file.replace('.truck', '.jbeam')
        if os.path.exists(output_file):
            os.unlink(output_file)

    print()


def example_with_validation():
    """Example 2: Conversion with validation"""
    print("Example 2: Conversion with Validation")
    print("=" * 40)

    truck_file = create_sample_truck_file()

    try:
        rig = Rig()
        rig.from_file(truck_file)

        # Validate the rig
        is_valid = rig.validate()
        print(f"Validation result: {'PASS' if is_valid else 'FAIL'}")

        if rig.parse_warnings:
            print(f"Warnings ({len(rig.parse_warnings)}):")
            for warning in rig.parse_warnings:
                print(f"  - {warning}")

        if rig.parse_errors:
            print(f"Errors ({len(rig.parse_errors)}):")
            for error in rig.parse_errors:
                print(f"  - {error}")

        # Calculate masses with validation
        rig.calculate_masses()

        # Show mass distribution
        print("\nNode masses:")
        for node in rig.nodes[:5]:  # Show first 5 nodes
            print(f"  {node.name}: {node.mass:.2f} kg")

        total_mass = sum(n.mass for n in rig.nodes)
        print(f"Total mass: {total_mass:.2f} kg")

    finally:
        if os.path.exists(truck_file):
            os.unlink(truck_file)

    print()


def example_with_configuration():
    """Example 3: Using configuration and templates"""
    print("Example 3: Configuration and Templates")
    print("=" * 40)

    # Get configuration manager
    config = get_config()

    # Show available templates
    templates = config.list_templates()
    print("Available templates:")
    for name, description in templates.items():
        print(f"  {name}: {description}")

    # Apply car template
    print("\nApplying car template...")
    config.apply_template("car")

    # Show current settings
    settings = config.settings
    print(f"Minimum mass: {settings.minimum_mass}")
    print(f"Default author: {settings.default_author}")
    print(f"Pretty print: {settings.pretty_print}")

    # Create custom settings
    custom_settings = ConversionSettings()
    custom_settings.minimum_mass = 15.0
    custom_settings.default_author = "Example User"
    custom_settings.pretty_print = True

    print(f"\nCustom settings:")
    print(f"Minimum mass: {custom_settings.minimum_mass}")
    print(f"Default author: {custom_settings.default_author}")

    print()


def example_error_handling():
    """Example 4: Error handling"""
    print("Example 4: Error Handling")
    print("=" * 40)

    # Create a truck file with errors
    bad_truck_content = """Bad Truck
nodes
1, 0.0, 0.0, 0.0, l
2, 1.0, 0.0, 0.0, l

beams
1, 2
1, 999  ; This beam references a non-existent node
2, 888  ; This one too

globals
-100, -50  ; Negative weights

end
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.truck', delete=False) as f:
        f.write(bad_truck_content)
        truck_file = f.name

    try:
        rig = Rig()
        rig.from_file(truck_file)

        # Validation will catch the errors
        is_valid = rig.validate()
        print(f"Validation result: {'PASS' if is_valid else 'FAIL'}")

        print(f"\nFound {len(rig.parse_warnings)} warnings:")
        for warning in rig.parse_warnings:
            print(f"  - {warning}")

        print(f"\nFound {len(rig.parse_errors)} errors:")
        for error in rig.parse_errors:
            print(f"  - {error}")

        # Try to calculate masses anyway
        rig.calculate_masses()

        # Show statistics
        stats = rig.get_statistics()
        print(f"\nStatistics:")
        print(f"  Nodes: {stats['nodes']}")
        print(f"  Beams: {stats['beams']}")
        print(f"  Warnings: {stats['warnings']}")
        print(f"  Errors: {stats['errors']}")

    finally:
        if os.path.exists(truck_file):
            os.unlink(truck_file)

    print()


def example_batch_processing():
    """Example 5: Batch processing simulation"""
    print("Example 5: Batch Processing Simulation")
    print("=" * 40)

    # Create multiple sample files
    temp_dir = tempfile.mkdtemp()
    truck_files = []

    try:
        # Create 3 sample truck files
        for i in range(3):
            content = f"""Sample Truck {i+1}
globals
{1000 + i*500}, {500 + i*200}

nodes
1, 0.0, 0.0, 0.0, l
2, {1.0 + i*0.5}, 0.0, 0.0, l

beams
1, 2

end
"""
            truck_file = os.path.join(temp_dir, f"truck_{i+1}.truck")
            with open(truck_file, 'w') as f:
                f.write(content)
            truck_files.append(truck_file)

        print(f"Created {len(truck_files)} sample truck files")

        # Process each file
        results = []
        for truck_file in truck_files:
            try:
                rig = Rig()
                rig.from_file(truck_file)
                rig.calculate_masses()

                # Validate
                is_valid = rig.validate()

                # Get statistics
                stats = rig.get_statistics()

                results.append({
                    'file': os.path.basename(truck_file),
                    'name': rig.name,
                    'valid': is_valid,
                    'nodes': stats['nodes'],
                    'beams': stats['beams'],
                    'warnings': stats['warnings'],
                    'errors': stats['errors']
                })

                print(f"  ✓ Processed {os.path.basename(truck_file)}")

            except Exception as e:
                print(f"  ✗ Failed to process {os.path.basename(truck_file)}: {e}")

        # Summary
        print(f"\nBatch Processing Summary:")
        print(f"Files processed: {len(results)}")
        valid_files = sum(1 for r in results if r['valid'])
        print(f"Valid files: {valid_files}")
        total_warnings = sum(r['warnings'] for r in results)
        total_errors = sum(r['errors'] for r in results)
        print(f"Total warnings: {total_warnings}")
        print(f"Total errors: {total_errors}")

    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)

    print()


def example_download_functionality():
    """Example 6: Download functionality (if available)"""
    print("Example 6: Download Functionality")
    print("=" * 40)

    if not DOWNLOAD_AVAILABLE:
        print("Download functionality not available.")
        print("To enable downloads, install required dependencies:")
        print("  pip install requests beautifulsoup4")
        print()
        return

    try:
        # Create downloader instance
        downloader = RoRDownloader(download_dir="./example_downloads")

        print("Testing RoR repository connection...")

        # Search for resources
        print("Searching for 'truck' resources...")
        resources, total_pages = downloader.search_resources(query="truck", per_page=5)

        if resources:
            print(f"Found {len(resources)} resources:")
            for i, resource in enumerate(resources, 1):
                print(f"  {i}. {resource.title} by {resource.author}")

            print(f"\nTotal pages available: {total_pages}")

            # Get details for first resource
            if resources:
                first_resource = resources[0]
                print(f"\nGetting details for: {first_resource.title}")
                detailed_resource = downloader.get_resource_details(first_resource.id)

                if detailed_resource:
                    print(f"  ID: {detailed_resource.id}")
                    print(f"  Title: {detailed_resource.title}")
                    print(f"  Author: {detailed_resource.author}")
                    print(f"  Category: {detailed_resource.category}")

                    # Simulate download (dry run)
                    print(f"\n[SIMULATION] Would download: {detailed_resource.title}")
                    print(f"[SIMULATION] Download URL: {detailed_resource.download_url}")
                else:
                    print("  Could not get detailed information")
        else:
            print("No resources found or connection failed")

        # Show download history (will be empty for this example)
        history = downloader.get_download_history()
        print(f"\nDownload history: {len(history)} items")

    except Exception as e:
        print(f"Error testing download functionality: {e}")
        print("This might be due to network issues or changes in the RoR website structure")

    print()


def main():
    """Run all examples"""
    print("truck2jbeam Enhanced Converter - Usage Examples")
    print("=" * 60)
    print()

    # Run examples
    example_basic_conversion()
    example_with_validation()
    example_with_configuration()
    example_error_handling()
    example_batch_processing()
    example_download_functionality()
    example_enhanced_features()  # New enhanced features example

    print("All examples completed!")
    print("\nFor more information, see:")
    print("  - README.md for comprehensive documentation")
    print("  - python truck2jbeam.py --help for CLI options")
    print("  - python truck2jbeam_config.py --help for configuration")
    print("  - python test_truck2jbeam.py to run tests")


def example_enhanced_features():
    """Example: Enhanced triangles/quads and flexbodies/props support"""
    print("\n" + "="*60)
    print("ENHANCED FEATURES EXAMPLE")
    print("="*60)

    # Create a sample truck file with enhanced features
    enhanced_truck_content = """Enhanced Demo Truck
globals
5000, 2000

nodes
1, 0.0, 0.0, 0.0, l
2, 2.0, 0.0, 0.0, l
3, 2.0, 2.0, 0.0, l
4, 0.0, 2.0, 0.0, l
5, 1.0, 1.0, 1.0, l
6, 1.0, 1.0, -0.5, l

beams
1, 2
2, 3
3, 4
4, 1
1, 5
2, 5
3, 5
4, 5
5, 6

triangles
1, 2, 5, c, 0.3
2, 3, 5, v
3, 4, 5, cv, metal, 0.5

quads
1, 2, 3, 4, c, 0.2
1, 4, 5, 2, v, glass

flexbodies
1, 2, 4, 0.0, 0.0, 0.5, 0, 0, 0, car_body.mesh, 1.0, 1.0, 1.0
5, 6, 1, 0.0, 0.0, 0.0, 0, 0, 0, engine_block.mesh, 0.8, 0.8, 0.8
1, 2, 3, 0.0, 0.0, 0.3, 0, 0, 0, wheel.mesh, 0.9, 0.9, 0.9
2, 3, 4, 0.0, 0.0, 0.3, 0, 0, 0, wheel.mesh, 0.9, 0.9, 0.9

props
1, 2, 4, 0.0, 0.0, 1.0, 0, 0, 0, steering_wheel.mesh, 0.5, 0.5, 0.5, 45.0, rotation
5, 6, 1, 0.0, 0.0, 0.2, 0, 0, 0, radiator_fan.mesh, 1.0, 1.0, 1.0, 360.0, rotation
1, 2, 3, 0.0, 0.0, 0.8, 0, 0, 0, wheel.mesh, 0.7, 0.7, 0.7, 180.0, rotation
3, 4, 5, 0.0, 0.0, 0.8, 0, 0, 0, antenna.mesh, 0.3, 0.3, 0.3
4, 5, 6, 0.0, 0.0, 0.8, 0, 0, 0, antenna.mesh, 0.3, 0.3, 0.3

end
"""

    # Write sample file
    sample_file = "enhanced_demo.truck"
    with open(sample_file, 'w') as f:
        f.write(enhanced_truck_content)

    try:
        print(f"Parsing enhanced truck file: {sample_file}")
        rig = Rig()
        rig.from_file(sample_file)

        # Show enhanced statistics
        stats = rig.get_statistics()
        print(f"\nEnhanced Vehicle Statistics:")
        print(f"  - Nodes: {stats['nodes']}")
        print(f"  - Beams: {stats['beams']}")
        print(f"  - Triangles: {stats['triangles']}")
        print(f"  - Quads: {stats['quads']}")
        print(f"  - Flexbodies: {stats['flexbodies']}")
        print(f"  - Props: {stats['props']}")
        print(f"  - Warnings: {stats['warnings']}")
        print(f"  - Errors: {stats['errors']}")

        # Show original mesh names before duplicate resolution
        print(f"\nOriginal Mesh Names (before duplicate resolution):")
        original_flexbody_meshes = []
        original_prop_meshes = []

        # Collect original mesh names (before resolution)
        for flexbody in rig.flexbodies:
            original_flexbody_meshes.append(flexbody.mesh)
        for prop in rig.props:
            original_prop_meshes.append(prop.mesh)

        print(f"  Flexbody meshes: {original_flexbody_meshes}")
        print(f"  Prop meshes: {original_prop_meshes}")

        # Check for duplicates
        all_original_meshes = original_flexbody_meshes + original_prop_meshes
        duplicates = [mesh for mesh in set(all_original_meshes) if all_original_meshes.count(mesh) > 1]
        if duplicates:
            print(f"  Duplicate meshes detected: {duplicates}")
        else:
            print(f"  No duplicate meshes found")

        # Show triangle details
        print(f"\nTriangle Details:")
        for i, triangle in enumerate(rig.triangles):
            if hasattr(triangle, 'surface_type'):
                print(f"  Triangle {i+1}: {triangle.surface_type} surface")
                print(f"    Nodes: {triangle.get_nodes()}")
                print(f"    Material: {triangle.material}")
                print(f"    Drag coefficient: {triangle.drag_coefficient}")

        # Show quad details
        print(f"\nQuad Details:")
        for i, quad in enumerate(rig.quads):
            if hasattr(quad, 'surface_type'):
                print(f"  Quad {i+1}: {quad.surface_type} surface")
                print(f"    Nodes: {quad.get_nodes()}")
                print(f"    Material: {quad.material}")
                print(f"    Will be converted to {len(quad.to_triangles())} triangles")

        # Show flexbody details
        print(f"\nFlexbody Details:")
        for i, flexbody in enumerate(rig.flexbodies):
            if hasattr(flexbody, 'get_group_name'):
                print(f"  Flexbody {i+1}: {flexbody.mesh}")
                print(f"    Group name: {flexbody.get_group_name()}")
                print(f"    Scale: {flexbody.scale}")
                print(f"    Reference nodes: {flexbody.get_nodes()}")

        # Show prop details
        print(f"\nProp Details:")
        for i, prop in enumerate(rig.props):
            if hasattr(prop, 'get_group_name'):
                print(f"  Prop {i+1}: {prop.mesh}")
                print(f"    Group name: {prop.get_group_name()}")
                print(f"    Scale: {prop.scale}")
                print(f"    Animation: {prop.animation_mode} factor {prop.animation_factor}")
                print(f"    Reference nodes: {prop.get_nodes()}")

        # Validate the rig
        print(f"\nValidating rig...")
        is_valid = rig.validate()
        print(f"Validation result: {'PASSED' if is_valid else 'FAILED'}")

        if rig.parse_warnings:
            print(f"Warnings:")
            for warning in rig.parse_warnings:
                print(f"  - {warning}")

        if rig.parse_errors:
            print(f"Errors:")
            for error in rig.parse_errors:
                print(f"  - {error}")

        # Convert to JBeam (this will trigger duplicate resolution)
        output_file = "enhanced_demo.jbeam"
        print(f"\nConverting to JBeam: {output_file}")
        rig.to_jbeam(output_file)

        # Show mesh names after duplicate resolution
        print(f"\nMesh Names After Duplicate Resolution:")
        final_flexbody_meshes = [flexbody.mesh for flexbody in rig.flexbodies]
        final_prop_meshes = [prop.mesh for prop in rig.props]

        print(f"  Flexbody meshes: {final_flexbody_meshes}")
        print(f"  Prop meshes: {final_prop_meshes}")

        # Verify all mesh names are now unique
        all_final_meshes = final_flexbody_meshes + final_prop_meshes
        if len(set(all_final_meshes)) == len(all_final_meshes):
            print(f"  ✅ All mesh names are now unique!")
        else:
            print(f"  ❌ Still have duplicate mesh names")

        # Show renamed meshes
        renamed_count = 0
        for i, (original, final) in enumerate(zip(all_original_meshes, all_final_meshes)):
            if original != final:
                print(f"  Renamed: {original} -> {final}")
                renamed_count += 1

        if renamed_count == 0:
            print(f"  No meshes were renamed (no duplicates found)")
        else:
            print(f"  Total meshes renamed: {renamed_count}")

        # Show JBeam file size and structure
        import os
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"Generated JBeam file: {file_size} bytes")

            # Count sections in JBeam file
            with open(output_file, 'r') as f:
                content = f.read()
                sections = []
                if '"nodes":' in content:
                    sections.append("nodes")
                if '"beams":' in content:
                    sections.append("beams")
                if '"triangles":' in content:
                    sections.append("triangles")
                if '"flexbodies":' in content:
                    sections.append("flexbodies")
                if '"props":' in content:
                    sections.append("props")

                print(f"JBeam sections generated: {', '.join(sections)}")

        print(f"\nEnhanced features demonstration completed successfully!")

    except Exception as e:
        print(f"Enhanced features example failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up
        import os
        for file in [sample_file, "enhanced_demo.jbeam"]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass


def example_dae_processing():
    """Demonstrate DAE file processing capabilities"""
    print("\n" + "="*60)
    print("DAE PROCESSING EXAMPLE")
    print("="*60)

    try:
        from rig import Rig
        import tempfile
        import os

        # Create a sample DAE file
        sample_dae_content = '''<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <library_geometries>
    <geometry id="wheel" name="wheel_mesh">
      <mesh>
        <source id="wheel-positions">
          <float_array id="wheel-positions-array" count="24">
            1.0 1.0 1.0 -1.0 1.0 1.0 -1.0 -1.0 1.0 1.0 -1.0 1.0
            1.0 1.0 -1.0 -1.0 1.0 -1.0 -1.0 -1.0 -1.0 1.0 -1.0 -1.0
          </float_array>
        </source>
        <vertices id="wheel-vertices">
          <input semantic="POSITION" source="#wheel-positions"/>
        </vertices>
        <triangles count="12">
          <input semantic="VERTEX" source="#wheel-vertices" offset="0"/>
          <p>0 1 2 2 3 0 4 7 6 6 5 4 0 4 5 5 1 0 2 6 7 7 3 2 0 3 7 7 4 0 1 5 6 6 2 1</p>
        </triangles>
      </mesh>
    </geometry>
    <geometry id="antenna" name="antenna_mesh">
      <mesh>
        <source id="antenna-positions">
          <float_array id="antenna-positions-array" count="12">
            0.1 0.1 2.0 -0.1 0.1 2.0 -0.1 -0.1 2.0 0.1 -0.1 2.0
          </float_array>
        </source>
        <vertices id="antenna-vertices">
          <input semantic="POSITION" source="#antenna-positions"/>
        </vertices>
        <triangles count="2">
          <input semantic="VERTEX" source="#antenna-vertices" offset="0"/>
          <p>0 1 2 2 3 0</p>
        </triangles>
      </mesh>
    </geometry>
  </library_geometries>
  <library_visual_scenes>
    <visual_scene id="Scene" name="Scene">
      <node id="wheel_node" name="wheel_node" type="NODE">
        <translate sid="location">0 0 0</translate>
        <rotate sid="rotationZ">0 0 1 0</rotate>
        <rotate sid="rotationY">0 1 0 0</rotate>
        <rotate sid="rotationX">1 0 0 0</rotate>
        <scale sid="scale">1 1 1</scale>
        <instance_geometry url="#wheel"/>
      </node>
      <node id="antenna_node" name="antenna_node" type="NODE">
        <translate sid="location">0 0 2</translate>
        <rotate sid="rotationZ">0 0 1 0</rotate>
        <rotate sid="rotationY">0 1 0 0</rotate>
        <rotate sid="rotationX">1 0 0 0</rotate>
        <scale sid="scale">1 1 1</scale>
        <instance_geometry url="#antenna"/>
      </node>
    </visual_scene>
  </library_visual_scenes>
  <scene>
    <instance_visual_scene url="#Scene"/>
  </scene>
</COLLADA>'''

        # Create a temporary directory for DAE files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample DAE file
            dae_file_path = os.path.join(temp_dir, "vehicle_parts.dae")
            with open(dae_file_path, 'w', encoding='utf-8') as f:
                f.write(sample_dae_content)

            print(f"Created sample DAE file: {dae_file_path}")

            # Create a rig with flexbodies and props that reference DAE meshes
            rig = Rig()
            rig.name = "DAE Processing Demo"

            # Add some nodes
            from rig_common import Node, Flexbody, Prop
            rig.nodes = [
                Node("node1", 0.0, 0.0, 0.0),
                Node("node2", 1.0, 0.0, 0.0),
                Node("node3", 0.0, 1.0, 0.0),
                Node("node4", 0.5, 0.5, 0.5)
            ]

            # Add flexbodies and props that reference the DAE meshes
            flexbody1 = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "wheel.dae")
            flexbody2 = Flexbody("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "wheel.dae")  # Duplicate

            prop1 = Prop("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "antenna.dae")
            prop2 = Prop("node1", "node2", "node3", 0, 0, 0, 0, 0, 0, "antenna.dae")  # Duplicate

            rig.flexbodies = [flexbody1, flexbody2]
            rig.props = [prop1, prop2]

            print(f"\nRig Configuration:")
            print(f"  - Flexbodies: {len(rig.flexbodies)}")
            print(f"  - Props: {len(rig.props)}")

            # Extract mesh names from DAE file
            print(f"\nExtracting mesh names from DAE file...")
            mesh_names = rig.dae_processor.extract_mesh_names(dae_file_path)
            print(f"Found mesh names: {mesh_names}")

            # Extract mesh names from directory
            print(f"\nExtracting mesh names from directory...")
            mesh_names_by_file = rig.extract_dae_mesh_names(temp_dir)
            print(f"Mesh names by file:")
            for file_path, names in mesh_names_by_file.items():
                print(f"  {os.path.basename(file_path)}: {names}")

            # Resolve duplicate mesh names in rig
            print(f"\nResolving duplicate mesh names...")
            original_meshes = [fb.mesh for fb in rig.flexbodies] + [p.mesh for p in rig.props]
            print(f"Original mesh names: {original_meshes}")

            # This will trigger duplicate resolution
            rig._resolve_duplicate_mesh_names()

            final_meshes = [fb.mesh for fb in rig.flexbodies] + [p.mesh for p in rig.props]
            print(f"Resolved mesh names: {final_meshes}")

            # Generate mesh mapping for DAE synchronization
            print(f"\nGenerating mesh mapping for DAE synchronization...")
            mesh_mapping = rig.dae_processor.generate_mesh_mapping(rig.flexbodies, rig.props)
            print(f"Mesh mapping:")
            for old_name, new_name in mesh_mapping.items():
                print(f"  {old_name} -> {new_name}")

            # Create output directory for modified DAE files
            output_dir = os.path.join(temp_dir, "modified")
            os.makedirs(output_dir, exist_ok=True)

            # Process DAE files to match JBeam group names
            print(f"\nProcessing DAE files to match JBeam group names...")
            success = rig.process_dae_files(temp_dir, output_dir)
            print(f"DAE processing result: {'SUCCESS' if success else 'FAILED'}")

            # Check the modified DAE file
            modified_dae_path = os.path.join(output_dir, "vehicle_parts.dae")
            if os.path.exists(modified_dae_path):
                print(f"\nModified DAE file created: {modified_dae_path}")

                # Read and show a snippet of the modified content
                with open(modified_dae_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                print(f"Modified DAE content preview:")
                lines = content.split('\n')
                for i, line in enumerate(lines[:30]):  # Show first 30 lines
                    if 'geometry' in line or 'node' in line or 'instance_geometry' in line:
                        print(f"  Line {i+1}: {line.strip()}")

                # Check for expected modifications
                expected_modifications = ['wheel_001', 'wheel_002', 'antenna_001', 'antenna_002']
                found_modifications = []
                for mod in expected_modifications:
                    if mod in content:
                        found_modifications.append(mod)

                print(f"\nExpected modifications found: {found_modifications}")
                print(f"All modifications applied: {len(found_modifications) == len(expected_modifications)}")

            # Generate JBeam file to show final result
            print(f"\nGenerating JBeam file...")
            jbeam_file = os.path.join(temp_dir, "dae_demo.jbeam")
            rig.to_jbeam(jbeam_file)

            if os.path.exists(jbeam_file):
                with open(jbeam_file, 'r', encoding='utf-8') as f:
                    jbeam_content = f.read()

                print(f"JBeam file generated: {jbeam_file}")
                print(f"JBeam file size: {len(jbeam_content)} bytes")

                # Show flexbodies and props sections
                if '"flexbodies":' in jbeam_content:
                    print(f"\nJBeam flexbodies section contains unique mesh names:")
                    lines = jbeam_content.split('\n')
                    in_flexbodies = False
                    for line in lines:
                        if '"flexbodies":' in line:
                            in_flexbodies = True
                        elif in_flexbodies and '],' in line and not line.strip().startswith('['):
                            break
                        elif in_flexbodies and line.strip().startswith('["'):
                            print(f"  {line.strip()}")

                if '"props":' in jbeam_content:
                    print(f"\nJBeam props section contains unique mesh names:")
                    lines = jbeam_content.split('\n')
                    in_props = False
                    for line in lines:
                        if '"props":' in line:
                            in_props = True
                        elif in_props and '],' in line and not line.strip().startswith('['):
                            break
                        elif in_props and line.strip().startswith('["'):
                            print(f"  {line.strip()}")

        print(f"\nDAE processing demonstration completed successfully!")
        print(f"Key features demonstrated:")
        print(f"  ✅ DAE mesh name extraction")
        print(f"  ✅ Duplicate mesh name resolution")
        print(f"  ✅ Mesh mapping generation")
        print(f"  ✅ DAE file modification")
        print(f"  ✅ JBeam synchronization")

    except Exception as e:
        print(f"Error in DAE processing example: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
