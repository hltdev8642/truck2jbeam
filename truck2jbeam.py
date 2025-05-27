#!/usr/bin/env python3
"""
truck2jbeam - Enhanced Rigs of Rods to BeamNG.drive JBeam Converter

This script converts Rigs of Rods vehicle files (.truck, .trailer, .airplane, .train, etc.)
to BeamNG.drive JBeam format with enhanced features and error handling.

Author: Enhanced by AI Assistant
License: MIT
"""

import sys
import os
import argparse
import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from rig import Rig

# Optional import for download functionality
try:
    from ror_downloader import RoRDownloader
    DOWNLOAD_AVAILABLE = True
except ImportError:
    DOWNLOAD_AVAILABLE = False

# Optional import for configuration management
try:
    from config import get_config, load_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


@dataclass
class ConversionConfig:
    """Configuration for conversion process"""
    output_dir: Optional[str] = None
    backup: bool = True
    verbose: bool = False
    dry_run: bool = False
    force_overwrite: bool = False
    custom_author: Optional[str] = None
    template: Optional[str] = None
    config_file: Optional[str] = None
    batch_mode: bool = False
    # Enhanced features settings
    process_dae: Optional[str] = None
    dae_output: Optional[str] = None
    no_duplicate_resolution: bool = False
    strict_validation: bool = False
    include_stats: bool = False
    min_mass: Optional[float] = None
    no_transform_properties: bool = False
    convert_meshes: bool = False
    mesh_output_format: str = 'dae'
    mesh_output_dir: Optional[str] = None
    # Download-related settings
    download_dir: str = "./downloads"
    auto_extract: bool = True
    auto_convert: bool = False


class ConversionStats:
    """Track conversion statistics"""
    def __init__(self):
        self.files_processed = 0
        self.files_successful = 0
        self.files_failed = 0
        self.start_time = time.time()
        self.errors: List[str] = []

    def add_success(self):
        self.files_successful += 1
        self.files_processed += 1

    def add_failure(self, error: str):
        self.files_failed += 1
        self.files_processed += 1
        self.errors.append(error)

    def get_duration(self) -> float:
        return time.time() - self.start_time

    def print_summary(self):
        duration = self.get_duration()
        print(f"\n{'='*50}")
        print(f"CONVERSION SUMMARY")
        print(f"{'='*50}")
        print(f"Files processed: {self.files_processed}")
        print(f"Successful: {self.files_successful}")
        print(f"Failed: {self.files_failed}")
        print(f"Duration: {duration:.2f} seconds")

        if self.errors:
            print(f"\nErrors encountered:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    return logging.getLogger(__name__)


def validate_input_file(filepath: str) -> bool:
    """Validate input file exists and has correct extension"""
    if not os.path.isfile(filepath):
        return False

    valid_extensions = {'.truck', '.trailer', '.airplane', '.boat', '.car', '.load', '.train'}
    ext = os.path.splitext(filepath)[1].lower()
    return ext in valid_extensions


def get_output_path(input_path: str, config: ConversionConfig) -> str:
    """Generate output path based on configuration"""
    input_file = Path(input_path)
    output_name = input_file.stem + '.jbeam'

    if config.output_dir:
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir / output_name)
    else:
        return str(input_file.parent / output_name)


def create_backup(filepath: str) -> bool:
    """Create backup of existing file"""
    if not os.path.exists(filepath):
        return True

    backup_path = filepath + '.backup'
    try:
        import shutil
        shutil.copy2(filepath, backup_path)
        return True
    except Exception as e:
        logging.error(f"Failed to create backup: {e}")
        return False


def convert_single_file(input_path: str, config: ConversionConfig, logger: logging.Logger) -> bool:
    """Convert a single RoR file to JBeam"""
    try:
        # Validate input
        if not validate_input_file(input_path):
            raise ValueError(f"Invalid input file: {input_path}")

        # Get output path
        output_path = get_output_path(input_path, config)

        # Check if output exists and handle accordingly
        if os.path.exists(output_path) and not config.force_overwrite:
            if not config.dry_run:
                response = input(f"Output file {output_path} exists. Overwrite? (y/N): ")
                if response.lower() != 'y':
                    logger.info(f"Skipping {input_path}")
                    return True

        # Create backup if needed
        if config.backup and os.path.exists(output_path) and not config.dry_run:
            if not create_backup(output_path):
                logger.warning(f"Could not create backup for {output_path}")

        if config.dry_run:
            logger.info(f"[DRY RUN] Would convert {input_path} -> {output_path}")
            return True

        # Perform conversion
        logger.info(f"Converting {input_path}...")

        rig = Rig()
        rig.type = os.path.splitext(input_path)[1][1:].lower()

        # Load configuration if specified
        if CONFIG_AVAILABLE and config.config_file:
            try:
                config_manager = get_config()
                config_manager.config_path = Path(config.config_file)
                config_manager.load_config()
                logger.debug(f"Loaded configuration from {config.config_file}")
            except Exception as e:
                logger.warning(f"Failed to load configuration: {e}")

        # Apply template if specified
        if CONFIG_AVAILABLE and config.template:
            try:
                config_manager = get_config()
                if config_manager.apply_template(config.template):
                    logger.debug(f"Applied template: {config.template}")
                else:
                    logger.warning(f"Template not found: {config.template}")
            except Exception as e:
                logger.warning(f"Failed to apply template: {e}")

        # Apply custom author if specified
        if config.custom_author:
            rig.authors = [config.custom_author]

        # Apply enhanced configuration options
        if config.min_mass is not None:
            # This would require modifying the Rig class to accept minimum mass override
            logger.debug(f"Setting minimum mass to {config.min_mass}")

        # Set transform properties flag
        if config.no_transform_properties:
            rig.no_transform_properties = True
            logger.debug("Transform properties (rotation, translation, scale) will be excluded from output")

        logger.debug(f"Parsing {rig.type} file...")
        rig.from_file(input_path)

        logger.debug("Calculating node masses...")
        rig.calculate_masses()

        # Process DAE files if requested
        if config.process_dae:
            logger.info(f"Processing DAE files from {config.process_dae}...")
            try:
                success = rig.process_dae_files(config.process_dae, config.dae_output)
                if success:
                    logger.info("DAE files processed successfully")
                else:
                    logger.warning("DAE file processing failed")
            except Exception as e:
                logger.warning(f"DAE processing error: {e}")

        # Convert mesh files if requested
        if config.convert_meshes:
            mesh_dir = config.mesh_output_dir or os.path.dirname(input_path)
            output_dir = config.mesh_output_dir or os.path.join(os.path.dirname(output_path), "meshes")

            logger.info(f"Converting .mesh files to {config.mesh_output_format} format...")
            try:
                # Apply coordinate transformation unless disabled by no_transform_properties
                coordinate_transform = not config.no_transform_properties

                success = rig.convert_mesh_files(
                    mesh_dir, output_dir, config.mesh_output_format, coordinate_transform
                )
                if success:
                    logger.info(f"Mesh files converted successfully to {output_dir}")
                else:
                    logger.warning("Mesh file conversion failed")
            except Exception as e:
                logger.warning(f"Mesh conversion error: {e}")

        logger.debug(f"Writing JBeam to {output_path}...")
        rig.to_jbeam(output_path)

        logger.info(f"Successfully converted {input_path} -> {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to convert {input_path}: {e}")
        return False


def find_rig_files(directory: str) -> List[str]:
    """Find all RoR rig files in directory"""
    valid_extensions = {'.truck', '.trailer', '.airplane', '.boat', '.car', '.load', '.train'}
    rig_files = []

    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in valid_extensions):
                rig_files.append(os.path.join(root, file))

    return rig_files


def download_and_convert(resource_ids: List[int], search_query: str, config: ConversionConfig, logger: logging.Logger) -> bool:
    """Download resources from RoR repository and optionally convert them"""
    if not DOWNLOAD_AVAILABLE:
        logger.error("Download functionality not available. Please install required dependencies:")
        logger.error("pip install requests beautifulsoup4")
        return False

    downloader = RoRDownloader(download_dir=config.download_dir)
    downloaded_files = []

    # Download by resource IDs
    if resource_ids:
        for resource_id in resource_ids:
            logger.info(f"Getting details for resource {resource_id}...")
            resource = downloader.get_resource_details(resource_id)

            if not resource:
                logger.error(f"Resource {resource_id} not found or inaccessible")
                continue

            logger.info(f"Downloading: {resource.title}")

            if config.dry_run:
                logger.info(f"[DRY RUN] Would download {resource.title}")
                continue

            success = downloader.download_resource(resource, extract=config.auto_extract)

            if success:
                logger.info(f"✓ Successfully downloaded {resource.title}")
                if config.auto_extract:
                    # Find extracted files
                    extract_dir = Path(config.download_dir) / f"{resource.title}_{resource.id}"
                    if extract_dir.exists():
                        downloaded_files.extend(find_rig_files(str(extract_dir)))
            else:
                logger.error(f"✗ Failed to download {resource.title}")

    # Download by search query
    elif search_query:
        logger.info(f"Searching for '{search_query}' to download...")
        resources, _ = downloader.search_resources(query=search_query, per_page=10)

        if not resources:
            logger.warning("No resources found matching search criteria")
            return False

        logger.info(f"Found {len(resources)} resources")

        for resource in resources:
            if config.dry_run:
                logger.info(f"[DRY RUN] Would download {resource.title}")
                continue

            logger.info(f"Downloading: {resource.title}")
            success = downloader.download_resource(resource, extract=config.auto_extract)

            if success:
                logger.info(f"✓ Successfully downloaded {resource.title}")
                if config.auto_extract:
                    # Find extracted files
                    extract_dir = Path(config.download_dir) / f"{resource.title}_{resource.id}"
                    if extract_dir.exists():
                        downloaded_files.extend(find_rig_files(str(extract_dir)))
            else:
                logger.error(f"✗ Failed to download {resource.title}")

    # Auto-convert downloaded files if requested
    if config.auto_convert and downloaded_files and not config.dry_run:
        logger.info(f"Auto-converting {len(downloaded_files)} downloaded rig files...")

        conversion_stats = ConversionStats()
        for filepath in downloaded_files:
            logger.info(f"Converting {os.path.basename(filepath)}")
            if convert_single_file(filepath, config, logger):
                conversion_stats.add_success()
            else:
                conversion_stats.add_failure(f"Failed to convert {filepath}")

        if config.verbose:
            conversion_stats.print_summary()

    return True


def search_ror_resources(query: str, category: str, limit: int, logger: logging.Logger) -> bool:
    """Search RoR repository and display results"""
    if not DOWNLOAD_AVAILABLE:
        logger.error("Download functionality not available. Please install required dependencies:")
        logger.error("pip install requests beautifulsoup4")
        return False

    downloader = RoRDownloader()

    logger.info(f"Searching for: '{query}'")
    if category:
        logger.info(f"Category filter: {category}")

    resources, total_pages = downloader.search_resources(
        query=query,
        category=category,
        per_page=limit
    )

    if resources:
        print(f"\nFound {len(resources)} resources:")
        print(f"{'ID':<8} {'Title':<40} {'Author':<20}")
        print("-" * 70)

        for resource in resources:
            title = resource.title[:37] + "..." if len(resource.title) > 40 else resource.title
            author = resource.author[:17] + "..." if len(resource.author) > 20 else resource.author
            print(f"{resource.id:<8} {title:<40} {author:<20}")

        print(f"\nTo download a resource, use: --download-ids {' '.join(str(r.id) for r in resources[:5])}")
        print(f"Or download by search: --download-search '{query}'")
    else:
        logger.warning("No resources found matching your criteria")

    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Convert Rigs of Rods vehicle files to BeamNG.drive JBeam format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s mycar.truck                    # Convert single file
  %(prog)s *.truck                        # Convert multiple files
  %(prog)s -d /path/to/rigs --batch       # Batch convert directory
  %(prog)s mycar.truck -o ./output        # Specify output directory
  %(prog)s mycar.truck --dry-run          # Preview conversion
  %(prog)s mycar.truck -v                 # Verbose output

Enhanced Features:
  %(prog)s mycar.truck --template truck   # Apply truck template settings
  %(prog)s mycar.truck --process-dae ./meshes --dae-output ./modified  # Process DAE files
  %(prog)s mycar.truck --strict-validation --include-stats  # Strict mode with statistics
  %(prog)s mycar.truck --min-mass 25.0    # Override minimum node mass
  %(prog)s mycar.truck --no-duplicate-resolution  # Disable duplicate mesh resolution

Download Examples (requires: pip install requests beautifulsoup4):
  %(prog)s --search-ror "truck"           # Search RoR repository
  %(prog)s --download-ids 123 456         # Download specific resources
  %(prog)s --download-search "monster truck" --auto-convert  # Download and convert

Configuration:
  Use truck2jbeam_config.py for advanced configuration management
  %(prog)s --config ./my_config.json      # Use custom configuration file
        """
    )

    parser.add_argument('files', nargs='*', help='RoR rig files to convert (.truck, .trailer, .airplane, .boat, .car, .load, .train)')
    parser.add_argument('-o', '--output-dir', help='Output directory for JBeam files')
    parser.add_argument('-d', '--directory', help='Directory to search for rig files')
    parser.add_argument('--batch', action='store_true', help='Batch process all files in directory')
    parser.add_argument('--backup', action='store_true', default=True, help='Create backup of existing files')
    parser.add_argument('--no-backup', dest='backup', action='store_false', help='Don\'t create backups')
    parser.add_argument('-f', '--force', action='store_true', help='Force overwrite existing files')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without actually converting')
    parser.add_argument('--author', help='Set custom author name in output')
    parser.add_argument('--template', help='Apply conversion template (car, truck, airplane, trailer)')
    parser.add_argument('--config', help='Path to custom configuration file')
    parser.add_argument('--version', action='version', version='truck2jbeam 3.0.0')

    # Enhanced features arguments
    enhanced_group = parser.add_argument_group('enhanced features', 'Advanced conversion options')
    enhanced_group.add_argument('--process-dae', metavar='DIR',
                               help='Process DAE files in directory to match JBeam group names')
    enhanced_group.add_argument('--dae-output', metavar='DIR',
                               help='Output directory for modified DAE files (default: modify in place)')
    enhanced_group.add_argument('--no-duplicate-resolution', action='store_true',
                               help='Disable automatic duplicate mesh name resolution')
    enhanced_group.add_argument('--strict-validation', action='store_true',
                               help='Enable strict validation mode with detailed error checking')
    enhanced_group.add_argument('--include-stats', action='store_true',
                               help='Include conversion statistics in JBeam output')
    enhanced_group.add_argument('--min-mass', type=float, metavar='MASS',
                               help='Override minimum node mass (default: 50.0)')
    enhanced_group.add_argument('--no-transform-properties', action='store_true',
                               help='Exclude rotation, translation, and scale properties from flexbodies and props')
    enhanced_group.add_argument('--convert-meshes', action='store_true',
                               help='Convert .mesh files to .dae/.blend format')
    enhanced_group.add_argument('--mesh-output-format', choices=['dae', 'blend', 'both'], default='dae',
                               help='Output format for converted meshes (default: dae)')
    enhanced_group.add_argument('--mesh-output-dir', metavar='DIR',
                               help='Output directory for converted mesh files')

    # Download-related arguments
    if DOWNLOAD_AVAILABLE:
        download_group = parser.add_argument_group('download options', 'Download resources from RoR repository')
        download_group.add_argument('--search-ror', metavar='QUERY',
                                   help='Search RoR repository for resources')
        download_group.add_argument('--download-ids', type=int, nargs='+', metavar='ID',
                                   help='Download specific resources by ID')
        download_group.add_argument('--download-search', metavar='QUERY',
                                   help='Search and download resources')
        download_group.add_argument('--download-dir', default='./downloads',
                                   help='Directory for downloads (default: ./downloads)')
        download_group.add_argument('--category', help='Filter by category (vehicles, terrains, etc.)')
        download_group.add_argument('--auto-convert', action='store_true',
                                   help='Automatically convert downloaded rig files')
        download_group.add_argument('--no-extract', dest='auto_extract', action='store_false', default=True,
                                   help='Don\'t extract downloaded zip files')
        download_group.add_argument('--search-limit', type=int, default=20,
                                   help='Limit search results (default: 20)')

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.verbose)

    # Create configuration
    config = ConversionConfig(
        output_dir=args.output_dir,
        backup=args.backup,
        verbose=args.verbose,
        dry_run=args.dry_run,
        force_overwrite=args.force,
        custom_author=args.author,
        template=getattr(args, 'template', None),
        config_file=getattr(args, 'config', None),
        batch_mode=args.batch,
        # Enhanced features
        process_dae=getattr(args, 'process_dae', None),
        dae_output=getattr(args, 'dae_output', None),
        no_duplicate_resolution=getattr(args, 'no_duplicate_resolution', False),
        strict_validation=getattr(args, 'strict_validation', False),
        include_stats=getattr(args, 'include_stats', False),
        min_mass=getattr(args, 'min_mass', None),
        no_transform_properties=getattr(args, 'no_transform_properties', False),
        convert_meshes=getattr(args, 'convert_meshes', False),
        mesh_output_format=getattr(args, 'mesh_output_format', 'dae'),
        mesh_output_dir=getattr(args, 'mesh_output_dir', None),
        # Download settings
        download_dir=getattr(args, 'download_dir', './downloads'),
        auto_extract=getattr(args, 'auto_extract', True),
        auto_convert=getattr(args, 'auto_convert', False)
    )

    # Handle download functionality first
    if DOWNLOAD_AVAILABLE and hasattr(args, 'search_ror') and args.search_ror:
        # Search RoR repository
        search_ror_resources(args.search_ror, getattr(args, 'category', ''),
                           getattr(args, 'search_limit', 20), logger)
        return

    if DOWNLOAD_AVAILABLE and (getattr(args, 'download_ids', None) or getattr(args, 'download_search', None)):
        # Download from RoR repository
        success = download_and_convert(
            getattr(args, 'download_ids', []),
            getattr(args, 'download_search', ''),
            config, logger
        )
        if not success:
            sys.exit(1)

        # If auto-convert is disabled, exit after download
        if not config.auto_convert:
            return

    # Collect files to process
    files_to_process = []

    if args.directory or args.batch:
        search_dir = args.directory or '.'
        if not os.path.isdir(search_dir):
            logger.error(f"Directory not found: {search_dir}")
            sys.exit(1)
        files_to_process.extend(find_rig_files(search_dir))
        logger.info(f"Found {len(files_to_process)} rig files in {search_dir}")

    if args.files:
        for file_pattern in args.files:
            if '*' in file_pattern or '?' in file_pattern:
                import glob
                files_to_process.extend(glob.glob(file_pattern))
            else:
                files_to_process.append(file_pattern)

    # If no files specified, show help
    if not files_to_process:
        parser.print_help()
        sys.exit(1)

    # Remove duplicates and validate
    files_to_process = list(set(files_to_process))
    valid_files = [f for f in files_to_process if validate_input_file(f)]

    if not valid_files:
        logger.error("No valid rig files found to process")
        sys.exit(1)

    if len(valid_files) != len(files_to_process):
        invalid_count = len(files_to_process) - len(valid_files)
        logger.warning(f"Skipping {invalid_count} invalid files")

    # Process files
    stats = ConversionStats()

    logger.info(f"Processing {len(valid_files)} files...")

    for i, filepath in enumerate(valid_files, 1):
        if len(valid_files) > 1:
            logger.info(f"[{i}/{len(valid_files)}] Processing {os.path.basename(filepath)}")

        if convert_single_file(filepath, config, logger):
            stats.add_success()
        else:
            stats.add_failure(f"Failed to convert {filepath}")

    # Print summary
    if len(valid_files) > 1 or config.verbose:
        stats.print_summary()

    # Exit with appropriate code
    sys.exit(0 if stats.files_failed == 0 else 1)


if __name__ == "__main__":
    main()