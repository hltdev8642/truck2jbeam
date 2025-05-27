# truck2jbeam - Enhanced RoR to BeamNG Converter

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

truck2jbeam is an enhanced converter for Rigs of Rods (RoR) vehicle files to BeamNG.drive JBeam format. This tool converts `.truck`, `.trailer`, `.airplane`, `.boat`, `.car`, `.load`, and `.train` files into BeamNG-compatible `.jbeam` files with comprehensive error handling, validation, and customization options.

### Key Features

- **Enhanced CLI Interface**: Comprehensive command-line options with batch processing
- **RoR Repository Integration**: Download vehicles directly from https://forum.rigsofrods.org/resources/
- **Error Handling & Validation**: Detailed error reporting with line numbers and warnings
- **Configuration System**: Customizable settings and vehicle-specific templates
- **Batch Processing**: Convert multiple files or entire directories
- **Statistics & Reporting**: Detailed conversion reports and vehicle statistics
- **Backup System**: Automatic backup of existing files
- **Template System**: Pre-configured settings for different vehicle types

### 🆕 Enhanced Features (v3.0.0)

- **🔺 Advanced Triangle/Quad Support**: Complete support for RoR triangles and quads with automatic conversion
- **🎨 Enhanced Flexbody/Prop System**: Comprehensive flexbody and prop support with proper node grouping
- **🔧 Duplicate Mesh Resolution**: Automatic detection and resolution of duplicate mesh names
- **📁 DAE File Processing**: Full COLLADA (.dae) file support for mesh extraction and synchronization
- **🎯 Proper BeamNG Grouping**: Critical fix ensuring flexbodies display correctly in BeamNG.drive
- **⚡ Forset Support**: Enhanced forset parsing for proper flexbody node assignment

## Installation

### Requirements
- Python 3.7 or higher
- **Optional for download functionality**: `pip install requests beautifulsoup4`
- **Optional for DAE processing**: `pip install lxml` (recommended for better performance)

### Quick Start
1. Download or clone this repository
2. Ensure Python 3.7+ is installed
3. For download functionality: `pip install -r requirements.txt`
4. Run the converter from command line or drag files onto the script

## Usage

### Basic Usage

```bash
# Convert a single file
python truck2jbeam.py mycar.truck

# Convert multiple files
python truck2jbeam.py *.truck

# Batch convert a directory
python truck2jbeam.py --batch --directory /path/to/rigs

# Specify output directory
python truck2jbeam.py mycar.truck --output-dir ./converted

# Verbose output with statistics
python truck2jbeam.py mycar.truck --verbose

# Dry run (preview what would be converted)
python truck2jbeam.py mycar.truck --dry-run
```

### Download from RoR Repository

```bash
# Search the repository
python truck2jbeam.py --search-ror "monster truck"

# Download specific resources by ID
python truck2jbeam.py --download-ids 123 456 789

# Search and download with auto-conversion
python truck2jbeam.py --download-search "truck" --auto-convert

# Download with custom settings
python truck2jbeam.py --download-search "airplane" --category aircraft --download-dir ./aircraft --auto-convert
```

### Advanced Options

```bash
# Force overwrite existing files
python truck2jbeam.py mycar.truck --force

# Set custom author
python truck2jbeam.py mycar.truck --author "Your Name"

# Disable backups
python truck2jbeam.py mycar.truck --no-backup

# Exclude transform properties for cleaner output
python truck2jbeam.py mycar.truck --no-transform-properties

# Convert .mesh files to .dae format
python truck2jbeam.py mycar.truck --convert-meshes --mesh-output-dir ./converted_meshes

# Convert .mesh files to both .dae and .blend formats
python truck2jbeam.py mycar.truck --convert-meshes --mesh-output-format both

# Get help
python truck2jbeam.py --help
```

### Enhanced Features Usage

#### Triangle and Quad Support
```bash
# Convert files with triangles and quads (automatic)
python truck2jbeam.py vehicle_with_surfaces.truck --verbose

# The converter automatically:
# - Parses triangle and quad sections
# - Converts quads to triangles for BeamNG compatibility
# - Handles collision and visual surface types
# - Preserves material assignments
```

#### Flexbody and Prop Processing
```bash
# Convert with enhanced flexbody support (automatic)
python truck2jbeam.py detailed_vehicle.truck

# Features include:
# - Proper node grouping for BeamNG visibility
# - Forset parsing and node assignment
# - Duplicate mesh name resolution
# - Enhanced material and scaling support
```

#### DAE File Processing
```bash
# Process DAE files alongside conversion
python truck2jbeam.py vehicle.truck --process-dae ./meshes --dae-output ./modified_meshes

# Extract mesh names from DAE files
python -c "from rig import Rig; r = Rig(); print(r.extract_dae_mesh_names('./meshes'))"

# Synchronize DAE files with JBeam output
python -c "from rig import Rig; r = Rig(); r.from_file('vehicle.truck'); r.process_dae_files('./meshes', './output')"
```

#### Mesh File Conversion
```bash
# Convert .mesh files to .dae format (default)
python truck2jbeam.py vehicle.truck --convert-meshes

# Convert to specific format
python truck2jbeam.py vehicle.truck --convert-meshes --mesh-output-format dae
python truck2jbeam.py vehicle.truck --convert-meshes --mesh-output-format blend
python truck2jbeam.py vehicle.truck --convert-meshes --mesh-output-format both

# Specify output directory for converted meshes
python truck2jbeam.py vehicle.truck --convert-meshes --mesh-output-dir ./converted_meshes

# Convert with coordinate transformation disabled
python truck2jbeam.py vehicle.truck --convert-meshes --no-transform-properties

# Features include:
# - Automatic .mesh file detection from flexbodies and props
# - Coordinate system conversion (RoR to BeamNG)
# - Mesh name synchronization with JBeam output
# - Duplicate mesh name resolution
# - Support for both .dae (COLLADA) and .blend (Blender) output
```

### Configuration Management

```bash
# List available templates
python truck2jbeam_config.py list

# Show template details
python truck2jbeam_config.py show car

# Show current configuration
python truck2jbeam_config.py config

# Create custom template
python truck2jbeam_config.py create

# Export configuration
python truck2jbeam_config.py export my_config.json

# Import configuration
python truck2jbeam_config.py import my_config.json

# Reset to defaults
python truck2jbeam_config.py reset
```

### Dedicated Download CLI

For advanced download management, use the dedicated download CLI:

```bash
# Search for resources
python ror_download_cli.py search "monster truck"

# Download specific resources
python ror_download_cli.py download --ids 123 456

# Download by search query
python ror_download_cli.py download --search "truck" --auto-confirm

# Show popular resources
python ror_download_cli.py popular --limit 10

# Show recent resources
python ror_download_cli.py recent --limit 5

# Get resource details
python ror_download_cli.py info 123

# View download history
python ror_download_cli.py history --limit 20
```

## Enhanced Features Details

### 🔺 Advanced Triangle and Quad Support

The converter now provides comprehensive support for RoR triangle and quad surfaces:

#### Features
- **Complete Triangle Support**: Parses all RoR triangle formats including collision, visual, and mixed types
- **Quad to Triangle Conversion**: Automatically converts quads to triangles for BeamNG compatibility
- **Material Preservation**: Maintains material assignments and surface properties
- **Options Support**: Handles RoR triangle options ('c' for collision, 'v' for visual)
- **Drag/Lift Coefficients**: Supports aerodynamic properties

#### Example RoR Input
```
triangles
1, 2, 3, c
4, 5, 6, v, custom_material
```

#### Generated JBeam Output
```json
"triangles": [
    ["n1:", "n2:", "n3:", "group"],
    ["node1", "node2", "node3", "collision_triangles"],
    ["node4", "node5", "node6", "visual_triangles"]
]
```

### 🎨 Enhanced Flexbody and Prop System

Critical improvements for proper BeamNG.drive compatibility:

#### Key Improvements
- **Proper Node Grouping**: Ensures flexbodies are visible in BeamNG.drive
- **Forset Integration**: Processes forset commands for correct node assignment
- **Enhanced Properties**: Support for scaling, materials, and animation
- **Automatic Group Assignment**: Intelligently assigns nodes to flexbody groups

#### The Critical Fix
Previous versions had flexbodies that were invisible in BeamNG.drive due to improper node grouping. This version fixes this by:
1. Automatically assigning reference nodes to flexbody groups
2. Processing forset commands to include additional nodes
3. Ensuring all flexbody nodes are properly grouped before JBeam output

### 🔧 Duplicate Mesh Resolution

Automatically handles duplicate mesh names that are common in RoR files:

#### Features
- **Cross-Type Detection**: Detects duplicates across flexbodies and props
- **Sequential Renaming**: Uses pattern `mesh_001.ext`, `mesh_002.ext`, etc.
- **Case-Insensitive**: Treats "Wheel.mesh" and "wheel.mesh" as duplicates
- **Extension Preservation**: Maintains .mesh and .dae file extensions

#### Example
```
Input:  wheel.mesh, wheel.mesh, wheel.mesh
Output: wheel_001.mesh, wheel_002.mesh, wheel_003.mesh
```

### 📁 DAE File Processing

Comprehensive COLLADA (.dae) file support for mesh synchronization:

#### Capabilities
- **Mesh Name Extraction**: Extracts all mesh names from DAE files
- **Bidirectional Sync**: Synchronizes DAE files with JBeam group names
- **Namespace Support**: Proper COLLADA XML namespace handling
- **Batch Processing**: Processes entire directories of DAE files

#### Workflow
1. **Extract**: Read mesh names from DAE files for validation
2. **Resolve**: Apply duplicate mesh name resolution
3. **Synchronize**: Update DAE files to match JBeam group names
4. **Validate**: Ensure consistency between DAE and JBeam files

### 🔄 Enhanced Mesh File Conversion

Advanced .mesh to .dae/.blend conversion with robust Ogre3D parsing and full BeamNG.drive integration:

#### 🔧 Robust Parsing Engine
- **Binary Mesh Support**: Proper Ogre3D chunk-based parsing following official specification
- **XML Mesh Support**: Complete XML schema support with shared/submesh geometry
- **Header Validation**: Version checking, endianness detection, and format verification
- **Error Recovery**: Graceful handling of malformed files with fallback mesh generation
- **Performance Optimized**: Memory-efficient streaming for large mesh files

#### 🎯 Enhanced Format Support
- **Binary Ogre Mesh**: Chunk parsing (header 0x1000, submesh 0x4000, bounds 0x9000)
- **XML Ogre Mesh**: Shared geometry, submesh-specific vertices, multiple UV sets
- **Advanced Attributes**: Vertex colors, tangents, binormals, skeleton links
- **Material Extraction**: Proper material name parsing and mapping
- **Bounding Boxes**: Automatic bounds detection and preservation

#### 🌐 Accurate Coordinate Transformation
- **RoR System**: X=right, Y=forward, Z=up
- **BeamNG System**: X=right, Y=up, Z=forward
- **Transformation**: X→X, Y→Z, Z→Y (consistent with flexbodies/props)
- **Geometry Preservation**: Maintains mesh proportions and orientation
- **Y-Up Compliance**: Proper COLLADA Y-up axis for BeamNG compatibility

#### 🔗 Seamless Integration
- **JBeam Workflow**: Integrated with existing conversion process
- **Name Synchronization**: Mesh object names match JBeam flexbody/prop references
- **Duplicate Resolution**: Applies same mesh name resolution as JBeam output
- **Transform Consistency**: Respects `--no-transform-properties` flag
- **Batch Processing**: Converts all referenced .mesh files automatically

#### 📤 Multi-Format Output
- **.dae (COLLADA)**: Industry-standard 3D format, BeamNG.drive compatible
- **.blend (Blender)**: Direct Blender import with materials and node setup
- **Both Formats**: Generate both simultaneously for maximum compatibility
- **Quality Assurance**: Validation and integrity checking for all outputs

#### 🛡️ Enhanced Error Handling
- **Malformed File Detection**: Comprehensive validation and error reporting
- **Graceful Degradation**: Partial parsing with warnings for recoverable errors
- **Fallback Meshes**: Automatic generation of placeholder geometry when parsing fails
- **Detailed Logging**: Comprehensive diagnostic information and progress reporting

## Supported RoR Sections

### Core Sections
- `globals` - Vehicle mass and weight settings
- `nodes` / `nodes2` - Vehicle structure nodes
- `beams` - Structural beams connecting nodes
- `fixes` - Fixed/immovable nodes

### Advanced Sections
- `shocks` / `shocks2` - Shock absorbers and dampers
- `hydros` - Hydraulic actuators
- `wheels` / `wheels2` / `meshwheels` / `meshwheels2` / `flexbodywheels` - Wheel definitions
- `engine` / `engoption` / `torquecurve` - Engine and drivetrain
- `brakes` / `axles` - Braking and differential systems

### Visual & Interaction
- `flexbodies` - 3D mesh bodies with enhanced node grouping and forset support
- `props` - Static mesh attachments with animation and collision control
- `triangles` - Collision and visual surface triangles with material support
- `quads` - Quad surfaces (automatically converted to triangles)
- `submesh` - Legacy collision triangles
- `cinecam` - Internal cameras
- `slidenodes` / `railgroups` - Sliding mechanisms
- `contacters` - Collision nodes
- `forset` - Node sets for flexbody assignment

### Configuration
- `set_beam_defaults` / `set_beam_defaults_scale` - Beam property defaults
- `set_node_defaults` - Node property defaults
- `minimass` - Minimum node mass
- `rollon` - Self-collision enabling
- `author` - Author information

## Templates

The converter includes pre-configured templates for common vehicle types:

### Available Templates
- **car**: Standard passenger car (min mass: 25kg)
- **truck**: Heavy truck/lorry (min mass: 100kg)
- **airplane**: Aircraft (min mass: 10kg, higher beam spring)
- **trailer**: Trailer/semi-trailer (min mass: 75kg)

### Using Templates
Templates are automatically applied based on file extension, or can be manually specified through configuration.

## Configuration

### Configuration File
The converter uses `truck2jbeam_config.json` for persistent settings. The file is searched in:
1. Current working directory
2. `~/.config/truck2jbeam/`
3. Script directory

### Key Settings
- `minimum_mass`: Minimum node mass (default: 50.0)
- `default_author`: Default author name
- `pretty_print`: Format output JSON nicely
- `strict_validation`: Enable strict validation mode
- `material_mappings`: Custom material name mappings
- `resolve_duplicate_meshes`: Automatically resolve duplicate mesh names (default: true)
- `process_dae_files`: Enable DAE file processing (default: false)
- `dae_output_directory`: Directory for modified DAE files

## Error Handling & Validation

### Validation Checks
- Missing required components (nodes, beams)
- Orphaned beams (referencing non-existent nodes)
- Duplicate node positions
- Invalid mass values
- Engine configuration consistency
- Triangle and quad surface validation
- Flexbody and prop reference validation
- Mesh name conflict detection
- DAE file existence and structure validation
- Forset node reference validation

### Error Reporting
- Line-by-line error reporting with context
- Warning vs. error classification
- Detailed statistics and summaries
- Recovery suggestions

## Testing

Run the comprehensive test suite:

```bash
python test_truck2jbeam.py
```

The test suite includes:
- Unit tests for core functions
- Integration tests for file operations
- Configuration management tests
- Error handling validation
- Performance benchmarks
- Triangle and quad processing tests
- Flexbody and prop functionality tests
- Duplicate mesh resolution tests
- DAE file processing tests
- Forset parsing and validation tests

## Output Format

The converter generates BeamNG.drive compatible JBeam files with:
- Proper JSON structure and formatting
- Optimized beam ordering for readability
- Comprehensive metadata and statistics
- Material and group assignments
- Camera and visual element support
- Enhanced triangle and quad surface definitions
- Proper flexbody and prop grouping for BeamNG visibility
- Unique mesh name resolution
- DAE file synchronization support

## Troubleshooting

### Common Issues

**File not found errors**
- Ensure file paths are correct
- Check file permissions
- Verify file extensions are supported

**Parsing errors**
- Check RoR file syntax
- Look for unsupported sections
- Verify node/beam references

**Mass calculation warnings**
- Review `globals` section values
- Check for missing load-bearing nodes
- Adjust minimum mass settings

**Output validation failures**
- Enable verbose mode for details
- Check for orphaned references
- Verify required sections exist

**Flexbodies not visible in BeamNG**
- Ensure proper node grouping is enabled
- Check forset parsing and node assignment
- Verify mesh files exist and are properly named
- Review duplicate mesh name resolution

**DAE file processing issues**
- Install lxml for better performance: `pip install lxml`
- Check DAE file structure and validity
- Verify mesh name mappings are correct
- Ensure output directory permissions

### Getting Help
1. Run with `--verbose` for detailed output
2. Check the test suite for examples
3. Review configuration templates
4. Examine error messages and line numbers

## Contributing

Contributions are welcome! Please:
1. Run the test suite before submitting
2. Follow existing code style
3. Add tests for new features
4. Update documentation as needed

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### Version 3.0.0 (Latest)
- **🔺 Advanced Triangle/Quad Support**: Complete RoR triangle and quad parsing with automatic conversion
- **🎨 Enhanced Flexbody/Prop System**: Comprehensive flexbody and prop support with proper BeamNG node grouping
- **🔧 Duplicate Mesh Resolution**: Automatic detection and sequential renaming of duplicate mesh names
- **📁 DAE File Processing**: Full COLLADA (.dae) file support for mesh extraction and synchronization
- **🎯 Critical BeamNG Fix**: Proper node grouping ensuring flexbodies display correctly in-game
- **⚡ Forset Support**: Enhanced forset parsing for proper flexbody node assignment
- **🎛️ Clean Output Option**: `--no-transform-properties` flag for simplified JBeam output
- **📐 Props Format Fix**: Corrected props format to match BeamNG documentation exactly
- **🔄 Enhanced Mesh Conversion**: Robust Ogre3D parsing with proven blender2ogre techniques
- **🎯 Advanced Mesh Support**: Binary/XML parsing, error recovery, and seamless JBeam integration
- **🧪 Comprehensive Testing**: Extensive test coverage for all new features
- **📚 Enhanced Documentation**: Complete documentation of all features and capabilities

### Version 2.0.0
- Complete rewrite with enhanced error handling
- Added configuration system and templates
- Implemented batch processing
- Added comprehensive test suite
- Improved CLI interface with argparse
- Added validation and statistics
- Enhanced JBeam output quality

### Version 1.0.0
- Initial release
- Basic RoR to JBeam conversion
- Support for core RoR sections

## Examples and Demonstrations

### Running Examples
```bash
# Test enhanced features (triangles, quads, flexbodies, props, duplicate resolution)
python -c "from example_usage import example_enhanced_features; example_enhanced_features()"

# Test DAE file processing capabilities
python -c "from example_usage import example_dae_processing; example_dae_processing()"

# Run basic usage examples
python example_usage.py
```

### Example Output
The enhanced converter produces high-quality JBeam files with:
- ✅ **Perfect BeamNG Compatibility**: All visual elements display correctly
- ✅ **Unique Mesh Names**: No conflicts or duplicate entries
- ✅ **Proper Node Grouping**: Flexbodies are visible and functional
- ✅ **Complete Surface Support**: Triangles and quads with materials
- ✅ **DAE Synchronization**: Mesh files match JBeam definitions

## Special Thanks

- [Goosah](http://www.beamng.com/members/goosah.19311/) for helping with tire mechanics
- The Rigs of Rods community for documentation and examples
- BeamNG.drive developers for JBeam format specification
- Contributors who reported issues with flexbody visibility and mesh naming
