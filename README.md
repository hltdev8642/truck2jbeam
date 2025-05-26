# truck2jbeam - Enhanced RoR to BeamNG Converter

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

truck2jbeam is an enhanced converter for Rigs of Rods (RoR) vehicle files to BeamNG.drive JBeam format. This tool converts `.truck`, `.trailer`, `.airplane`, `.boat`, `.car`, and `.load` files into BeamNG-compatible `.jbeam` files with comprehensive error handling, validation, and customization options.

### Key Features

- **Enhanced CLI Interface**: Comprehensive command-line options with batch processing
- **RoR Repository Integration**: Download vehicles directly from https://forum.rigsofrods.org/resources/
- **Error Handling & Validation**: Detailed error reporting with line numbers and warnings
- **Configuration System**: Customizable settings and vehicle-specific templates
- **Batch Processing**: Convert multiple files or entire directories
- **Statistics & Reporting**: Detailed conversion reports and vehicle statistics
- **Backup System**: Automatic backup of existing files
- **Template System**: Pre-configured settings for different vehicle types

## Installation

### Requirements
- Python 3.7 or higher
- **Optional for download functionality**: `pip install requests beautifulsoup4`

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

# Get help
python truck2jbeam.py --help
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
- `flexbodies` - 3D mesh bodies
- `submesh` - Collision triangles
- `cinecam` - Internal cameras
- `slidenodes` / `railgroups` - Sliding mechanisms
- `contacters` - Collision nodes

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

## Error Handling & Validation

### Validation Checks
- Missing required components (nodes, beams)
- Orphaned beams (referencing non-existent nodes)
- Duplicate node positions
- Invalid mass values
- Engine configuration consistency

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

## Output Format

The converter generates BeamNG.drive compatible JBeam files with:
- Proper JSON structure and formatting
- Optimized beam ordering for readability
- Comprehensive metadata and statistics
- Material and group assignments
- Camera and visual element support

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

## Special Thanks

- [Goosah](http://www.beamng.com/members/goosah.19311/) for helping with tire mechanics
- The Rigs of Rods community for documentation and examples
- BeamNG.drive developers for JBeam format specification
