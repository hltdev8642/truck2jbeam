#!/usr/bin/env python3
"""
Configuration utility for truck2jbeam converter

This script provides a command-line interface for managing truck2jbeam
configuration settings and templates.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from config import get_config, ConversionSettings, TemplateSettings


def list_templates():
    """List all available templates"""
    config = get_config()
    templates = config.list_templates()
    
    print("Available templates:")
    print("=" * 50)
    for name, description in templates.items():
        print(f"  {name:<15} - {description}")
    print()


def show_template(template_name: str):
    """Show details of a specific template"""
    config = get_config()
    template = config.get_template(template_name)
    
    if not template:
        print(f"Template '{template_name}' not found")
        return False
    
    print(f"Template: {template.name}")
    print(f"Description: {template.description}")
    print()
    
    if template.typical_dry_weight:
        print(f"Typical dry weight: {template.typical_dry_weight}")
    if template.typical_load_weight:
        print(f"Typical load weight: {template.typical_load_weight}")
    if template.recommended_minimum_mass:
        print(f"Recommended minimum mass: {template.recommended_minimum_mass}")
    
    print("\nSettings:")
    settings_dict = template.settings.__dict__
    for key, value in settings_dict.items():
        if not key.startswith('_'):
            print(f"  {key}: {value}")
    
    return True


def show_current_config():
    """Show current configuration"""
    config = get_config()
    settings = config.settings
    
    print("Current Configuration:")
    print("=" * 50)
    
    settings_dict = settings.__dict__
    for key, value in settings_dict.items():
        if not key.startswith('_'):
            print(f"  {key}: {value}")
    print()


def create_template():
    """Interactive template creation"""
    print("Creating new template...")
    print("=" * 30)
    
    name = input("Template name: ").strip()
    if not name:
        print("Template name cannot be empty")
        return False
    
    description = input("Description: ").strip()
    if not description:
        description = f"Custom template: {name}"
    
    # Get basic settings
    print("\nBasic Settings (press Enter for default):")
    
    settings = ConversionSettings()
    
    try:
        min_mass = input(f"Minimum mass [{settings.minimum_mass}]: ").strip()
        if min_mass:
            settings.minimum_mass = float(min_mass)
        
        beam_spring = input(f"Default beam spring [{settings.default_beam_spring}]: ").strip()
        if beam_spring:
            settings.default_beam_spring = float(beam_spring)
        
        beam_damp = input(f"Default beam damp [{settings.default_beam_damp}]: ").strip()
        if beam_damp:
            settings.default_beam_damp = float(beam_damp)
        
        author = input(f"Default author [{settings.default_author}]: ").strip()
        if author:
            settings.default_author = author
        
    except ValueError as e:
        print(f"Invalid input: {e}")
        return False
    
    # Optional vehicle-specific settings
    print("\nVehicle-specific settings (optional):")
    
    dry_weight = None
    load_weight = None
    rec_min_mass = None
    
    try:
        dry_weight_input = input("Typical dry weight: ").strip()
        if dry_weight_input:
            dry_weight = float(dry_weight_input)
        
        load_weight_input = input("Typical load weight: ").strip()
        if load_weight_input:
            load_weight = float(load_weight_input)
        
        rec_min_mass_input = input("Recommended minimum mass: ").strip()
        if rec_min_mass_input:
            rec_min_mass = float(rec_min_mass_input)
        
    except ValueError as e:
        print(f"Invalid input: {e}")
        return False
    
    # Create template
    template = TemplateSettings(
        name=name,
        description=description,
        settings=settings,
        typical_dry_weight=dry_weight,
        typical_load_weight=load_weight,
        recommended_minimum_mass=rec_min_mass
    )
    
    # Add to config
    config = get_config()
    config.templates[name] = template
    
    # Save configuration
    if config.save_config():
        print(f"\nTemplate '{name}' created and saved successfully!")
        return True
    else:
        print(f"\nError saving template '{name}'")
        return False


def export_config(output_file: str):
    """Export current configuration to file"""
    config = get_config()
    
    try:
        output_path = Path(output_file)
        if config.save_config(output_path):
            print(f"Configuration exported to {output_path}")
            return True
        else:
            print(f"Error exporting configuration to {output_path}")
            return False
    except Exception as e:
        print(f"Error exporting configuration: {e}")
        return False


def import_config(input_file: str):
    """Import configuration from file"""
    config = get_config()
    
    try:
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"File not found: {input_path}")
            return False
        
        # Backup current config
        backup_path = Path("truck2jbeam_config_backup.json")
        config.save_config(backup_path)
        print(f"Current configuration backed up to {backup_path}")
        
        # Load new config
        config.config_path = input_path
        if config.load_config():
            print(f"Configuration imported from {input_path}")
            return True
        else:
            print(f"Error importing configuration from {input_path}")
            return False
            
    except Exception as e:
        print(f"Error importing configuration: {e}")
        return False


def reset_config():
    """Reset configuration to defaults"""
    response = input("Are you sure you want to reset to default configuration? (y/N): ")
    if response.lower() != 'y':
        print("Reset cancelled")
        return False
    
    config = get_config()
    config.settings = ConversionSettings()
    config._load_default_templates()
    
    if config.save_config():
        print("Configuration reset to defaults")
        return True
    else:
        print("Error resetting configuration")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Manage truck2jbeam configuration and templates",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List templates
    subparsers.add_parser('list', help='List available templates')
    
    # Show template
    show_parser = subparsers.add_parser('show', help='Show template details')
    show_parser.add_argument('template', help='Template name to show')
    
    # Show current config
    subparsers.add_parser('config', help='Show current configuration')
    
    # Create template
    subparsers.add_parser('create', help='Create new template interactively')
    
    # Export config
    export_parser = subparsers.add_parser('export', help='Export configuration to file')
    export_parser.add_argument('file', help='Output file path')
    
    # Import config
    import_parser = subparsers.add_parser('import', help='Import configuration from file')
    import_parser.add_argument('file', help='Input file path')
    
    # Reset config
    subparsers.add_parser('reset', help='Reset configuration to defaults')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load existing configuration
    config = get_config()
    config.load_config()
    
    # Execute command
    if args.command == 'list':
        list_templates()
    elif args.command == 'show':
        if not show_template(args.template):
            sys.exit(1)
    elif args.command == 'config':
        show_current_config()
    elif args.command == 'create':
        if not create_template():
            sys.exit(1)
    elif args.command == 'export':
        if not export_config(args.file):
            sys.exit(1)
    elif args.command == 'import':
        if not import_config(args.file):
            sys.exit(1)
    elif args.command == 'reset':
        if not reset_config():
            sys.exit(1)


if __name__ == "__main__":
    main()
