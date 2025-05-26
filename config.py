#!/usr/bin/env python3
"""
Configuration management for truck2jbeam converter

This module handles configuration loading, validation, and default settings
for the truck2jbeam conversion process.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging


@dataclass
class ConversionSettings:
    """Settings for the conversion process"""
    # Output settings
    indent_size: int = 4
    use_tabs: bool = False
    pretty_print: bool = True
    
    # Mass calculation settings
    minimum_mass: float = 50.0
    mass_calculation_method: str = "ror_standard"  # "ror_standard", "uniform", "custom"
    
    # Beam settings
    default_beam_spring: float = 9000000
    default_beam_damp: float = 12000
    default_beam_deform: float = 400000
    default_beam_strength: float = 1000000
    
    # Node settings
    default_friction: float = 1.0
    default_load_weight: float = 0.0
    
    # JBeam output settings
    slot_type: str = "main"
    default_author: str = "truck2jbeam converter"
    include_statistics: bool = False
    
    # Validation settings
    strict_validation: bool = False
    warn_on_missing_nodes: bool = True
    warn_on_duplicate_positions: bool = True
    
    # Material mappings
    material_mappings: Dict[str, str] = None
    
    def __post_init__(self):
        if self.material_mappings is None:
            self.material_mappings = {
                "default": "NM_METAL",
                "rubber": "NM_RUBBER",
                "plastic": "NM_PLASTIC",
                "glass": "NM_GLASS"
            }


@dataclass
class TemplateSettings:
    """Template-specific settings for different vehicle types"""
    name: str
    description: str
    settings: ConversionSettings
    
    # Vehicle-specific overrides
    typical_dry_weight: Optional[float] = None
    typical_load_weight: Optional[float] = None
    recommended_minimum_mass: Optional[float] = None


class ConfigManager:
    """Manages configuration loading and saving"""
    
    DEFAULT_CONFIG_NAME = "truck2jbeam_config.json"
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_path = self._find_config_file()
        self.settings = ConversionSettings()
        self.templates: Dict[str, TemplateSettings] = {}
        self._load_default_templates()
    
    def _find_config_file(self) -> Optional[Path]:
        """Find configuration file in standard locations"""
        search_paths = [
            Path.cwd() / self.DEFAULT_CONFIG_NAME,
            Path.home() / ".config" / "truck2jbeam" / self.DEFAULT_CONFIG_NAME,
            Path(__file__).parent / self.DEFAULT_CONFIG_NAME
        ]
        
        for path in search_paths:
            if path.exists():
                return path
        
        return None
    
    def _load_default_templates(self):
        """Load default templates for common vehicle types"""
        # Car template
        car_settings = ConversionSettings()
        car_settings.minimum_mass = 25.0
        self.templates["car"] = TemplateSettings(
            name="car",
            description="Standard passenger car",
            settings=car_settings,
            typical_dry_weight=1500,
            typical_load_weight=500,
            recommended_minimum_mass=25.0
        )
        
        # Truck template
        truck_settings = ConversionSettings()
        truck_settings.minimum_mass = 100.0
        self.templates["truck"] = TemplateSettings(
            name="truck",
            description="Heavy truck/lorry",
            settings=truck_settings,
            typical_dry_weight=8000,
            typical_load_weight=20000,
            recommended_minimum_mass=100.0
        )
        
        # Airplane template
        airplane_settings = ConversionSettings()
        airplane_settings.minimum_mass = 10.0
        airplane_settings.default_beam_spring = 15000000
        self.templates["airplane"] = TemplateSettings(
            name="airplane",
            description="Aircraft",
            settings=airplane_settings,
            typical_dry_weight=2000,
            typical_load_weight=1000,
            recommended_minimum_mass=10.0
        )
        
        # Trailer template
        trailer_settings = ConversionSettings()
        trailer_settings.minimum_mass = 75.0
        self.templates["trailer"] = TemplateSettings(
            name="trailer",
            description="Trailer/semi-trailer",
            settings=trailer_settings,
            typical_dry_weight=5000,
            typical_load_weight=25000,
            recommended_minimum_mass=75.0
        )
    
    def load_config(self) -> bool:
        """Load configuration from file"""
        if not self.config_path or not self.config_path.exists():
            self.logger.info("No configuration file found, using defaults")
            return False
        
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            
            # Load main settings
            if 'settings' in config_data:
                settings_dict = config_data['settings']
                # Update settings with loaded values
                for key, value in settings_dict.items():
                    if hasattr(self.settings, key):
                        setattr(self.settings, key, value)
            
            # Load custom templates
            if 'templates' in config_data:
                for template_name, template_data in config_data['templates'].items():
                    if template_name not in self.templates:
                        # Create custom template
                        template_settings = ConversionSettings()
                        if 'settings' in template_data:
                            for key, value in template_data['settings'].items():
                                if hasattr(template_settings, key):
                                    setattr(template_settings, key, value)
                        
                        self.templates[template_name] = TemplateSettings(
                            name=template_name,
                            description=template_data.get('description', 'Custom template'),
                            settings=template_settings,
                            typical_dry_weight=template_data.get('typical_dry_weight'),
                            typical_load_weight=template_data.get('typical_load_weight'),
                            recommended_minimum_mass=template_data.get('recommended_minimum_mass')
                        )
            
            self.logger.info(f"Loaded configuration from {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return False
    
    def save_config(self, path: Optional[Path] = None) -> bool:
        """Save current configuration to file"""
        save_path = path or self.config_path or Path.cwd() / self.DEFAULT_CONFIG_NAME
        
        try:
            config_data = {
                'settings': asdict(self.settings),
                'templates': {}
            }
            
            # Save custom templates (skip built-in ones)
            builtin_templates = {'car', 'truck', 'airplane', 'trailer'}
            for name, template in self.templates.items():
                if name not in builtin_templates:
                    config_data['templates'][name] = {
                        'description': template.description,
                        'settings': asdict(template.settings),
                        'typical_dry_weight': template.typical_dry_weight,
                        'typical_load_weight': template.typical_load_weight,
                        'recommended_minimum_mass': template.recommended_minimum_mass
                    }
            
            # Create directory if needed
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            self.logger.info(f"Saved configuration to {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def get_template(self, name: str) -> Optional[TemplateSettings]:
        """Get template by name"""
        return self.templates.get(name)
    
    def list_templates(self) -> Dict[str, str]:
        """Get list of available templates with descriptions"""
        return {name: template.description for name, template in self.templates.items()}
    
    def apply_template(self, template_name: str) -> bool:
        """Apply a template to current settings"""
        template = self.get_template(template_name)
        if not template:
            return False
        
        self.settings = template.settings
        self.logger.info(f"Applied template: {template_name}")
        return True


# Global config manager instance
config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """Get the global configuration manager"""
    return config_manager


def load_config() -> bool:
    """Load configuration from file"""
    return config_manager.load_config()


def get_settings() -> ConversionSettings:
    """Get current conversion settings"""
    return config_manager.settings
