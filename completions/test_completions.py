#!/usr/bin/env python3
"""
Test script for shell completions
Validates that completion files contain all necessary options
"""

import re
import sys
from pathlib import Path

def extract_options_from_truck2jbeam():
    """Extract all command-line options from truck2jbeam.py"""
    truck2jbeam_path = Path("../truck2jbeam.py")
    if not truck2jbeam_path.exists():
        print("Error: truck2jbeam.py not found in parent directory")
        print("Please run this script from the completions directory")
        return set()

    options = set()
    with open(truck2jbeam_path, 'r') as f:
        content = f.read()

    # Find all add_argument calls
    arg_pattern = r"add_argument\(['\"]([^'\"]+)['\"]"
    matches = re.findall(arg_pattern, content)

    for match in matches:
        if match.startswith('-'):
            options.add(match)

    # Also look for short options
    short_pattern = r"add_argument\(['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]"
    short_matches = re.findall(short_pattern, content)

    for short, long_opt in short_matches:
        if short.startswith('-'):
            options.add(short)
        if long_opt.startswith('-'):
            options.add(long_opt)

    return options

def test_zsh_completion():
    """Test ZSH completion file"""
    print("Testing ZSH completion file...")

    zsh_file = Path("_truck2jbeam")
    if not zsh_file.exists():
        print("Error: _truck2jbeam not found")
        return False

    with open(zsh_file, 'r') as f:
        content = f.read()

    # Extract options from ZSH completion
    zsh_options = set()
    option_pattern = r"'([^']*--[^']*)'|'([^']*-[^']*)'|\(([^)]*--[^)]*)\)|\(([^)]*-[^)]*)\)"
    matches = re.findall(option_pattern, content)

    for match in matches:
        for group in match:
            if group and group.startswith('-'):
                # Clean up the option (remove descriptions, etc.)
                clean_option = group.split('[')[0].split(')')[0].strip()
                if clean_option.startswith('-'):
                    zsh_options.add(clean_option)

    print(f"Found {len(zsh_options)} options in ZSH completion")
    return zsh_options

def test_powershell_completion():
    """Test PowerShell completion file"""
    print("Testing PowerShell completion file...")

    ps_file = Path("truck2jbeam-completion.ps1")
    if not ps_file.exists():
        print("Error: truck2jbeam-completion.ps1 not found")
        return False

    with open(ps_file, 'r') as f:
        content = f.read()

    # Extract options from PowerShell completion
    ps_options = set()
    option_pattern = r"'([^']*--[^']*)'|'([^']*-[^']*)'|\"([^\"]*--[^\"]*)\"|\"([^\"]*-[^\"]*)\""
    matches = re.findall(option_pattern, content)

    for match in matches:
        for group in match:
            if group and group.startswith('-'):
                ps_options.add(group)

    print(f"Found {len(ps_options)} options in PowerShell completion")
    return ps_options

def main():
    """Main test function"""
    print("Testing shell completion files for truck2jbeam.py")
    print("=" * 50)

    # Get expected options from truck2jbeam.py
    expected_options = extract_options_from_truck2jbeam()
    print(f"Expected options from truck2jbeam.py: {len(expected_options)}")

    if not expected_options:
        print("Could not extract options from truck2jbeam.py")
        return 1

    # Test ZSH completion
    zsh_options = test_zsh_completion()
    if zsh_options:
        missing_zsh = expected_options - zsh_options
        extra_zsh = zsh_options - expected_options

        if missing_zsh:
            print(f"Missing from ZSH completion: {sorted(missing_zsh)}")
        if extra_zsh:
            print(f"Extra in ZSH completion: {sorted(extra_zsh)}")

        if not missing_zsh and not extra_zsh:
            print("✓ ZSH completion is complete and accurate")
        else:
            print("⚠ ZSH completion has discrepancies")

    print()

    # Test PowerShell completion
    ps_options = test_powershell_completion()
    if ps_options:
        missing_ps = expected_options - ps_options
        extra_ps = ps_options - expected_options

        if missing_ps:
            print(f"Missing from PowerShell completion: {sorted(missing_ps)}")
        if extra_ps:
            print(f"Extra in PowerShell completion: {sorted(extra_ps)}")

        if not missing_ps and not extra_ps:
            print("✓ PowerShell completion is complete and accurate")
        else:
            print("⚠ PowerShell completion has discrepancies")

    print()
    print("Test completed!")

    # Print some expected options for verification
    print(f"\nSample expected options: {sorted(list(expected_options))[:10]}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
