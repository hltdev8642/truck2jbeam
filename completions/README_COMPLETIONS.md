# Shell Completions for truck2jbeam.py

This directory contains shell completion scripts for the `truck2jbeam.py` command, providing intelligent auto-completion for command-line options, file names, and parameter values.

## Files

- **`_truck2jbeam`** - ZSH completion script
- **`truck2jbeam-completion.ps1`** - PowerShell completion script
- **`COMPLETION_SETUP.md`** - Detailed installation and usage instructions
- **`test_completions.py`** - Test script to validate completion files

## Quick Setup

### ZSH (Linux/macOS)

```bash
# Copy completion file
mkdir -p ~/.zsh/completions
cp _truck2jbeam ~/.zsh/completions/

# Add to your ~/.zshrc
echo 'fpath=(~/.zsh/completions $fpath)' >> ~/.zshrc

# Reload
source ~/.zshrc && autoload -U compinit && compinit
```

### PowerShell (Windows/Cross-platform)

```powershell
# Add to your PowerShell profile
Add-Content -Path $PROFILE -Value ". path\to\completions\truck2jbeam-completion.ps1"

# Reload profile
. $PROFILE
```

## Features

### Smart Completion

Both completion systems provide intelligent suggestions for:

- **Command Options**: All available flags and parameters
- **File Types**: RoR files (*.truck, *.trailer, *.airplane, *.train, etc.)
- **Templates**: car, truck, airplane, trailer
- **Categories**: vehicles, terrains, aircraft, boats, etc.
- **Directories**: For output paths and DAE processing
- **Config Files**: JSON configuration files

### Context-Aware Suggestions

The completions understand context and provide relevant suggestions:

```bash
# Template completion
truck2jbeam.py --template <TAB>
# Shows: car, truck, airplane, trailer

# File completion
truck2jbeam.py <TAB>
# Shows: *.truck, *.trailer, *.airplane, *.boat, *.car, *.load, *.train files

# Directory completion
truck2jbeam.py --output-dir <TAB>
# Shows: available directories

# Category completion
truck2jbeam.py --category <TAB>
# Shows: vehicles, terrains, aircraft, boats, trailers, loads, skins, tools
```

## Supported Options

### Basic Options
- `--help`, `-h` - Show help
- `--version` - Show version
- `--output-dir`, `-o` - Output directory
- `--directory`, `-d` - Search directory
- `--batch` - Batch processing
- `--backup` / `--no-backup` - Backup control
- `--force`, `-f` - Force overwrite
- `--verbose`, `-v` - Verbose output
- `--dry-run` - Preview mode
- `--author` - Custom author

### Enhanced Features
- `--template` - Apply template (car, truck, airplane, trailer)
- `--config` - Configuration file
- `--process-dae` - DAE processing directory
- `--dae-output` - DAE output directory
- `--no-duplicate-resolution` - Disable duplicate resolution
- `--strict-validation` - Strict validation mode
- `--include-stats` - Include statistics
- `--min-mass` - Minimum mass override
- `--no-transform-properties` - Exclude rotation, translation, and scale properties
- `--convert-meshes` - Convert .mesh files to .dae/.blend format
- `--mesh-output-format` - Output format for converted meshes
- `--mesh-output-dir` - Output directory for converted mesh files

### Download Options
- `--search-ror` - Search RoR repository
- `--download-ids` - Download by IDs
- `--download-search` - Download by search
- `--download-dir` - Download directory
- `--category` - Filter category
- `--auto-convert` - Auto-convert downloads
- `--no-extract` - Don't extract archives
- `--search-limit` - Search result limit

## Testing

Run the test script to verify completions:

```bash
python test_completions.py
```

## Manual Testing

### ZSH
```bash
# Test basic completion
truck2jbeam.py --<TAB><TAB>

# Test template completion
truck2jbeam.py --template <TAB>

# Test file completion
truck2jbeam.py <TAB>
```

### PowerShell
```powershell
# Test basic completion
truck2jbeam.py --<TAB>

# Test template completion
truck2jbeam.py --template <TAB>

# Test file completion
truck2jbeam.py <TAB>
```

## Troubleshooting

### ZSH Issues
- Ensure `compinit` is called after adding to `fpath`
- Clear completion cache: `rm ~/.zcompdump*`
- Check file permissions on completion script

### PowerShell Issues
- Set execution policy: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Verify profile path: `$PROFILE`
- Restart PowerShell after profile changes

## Contributing

When adding new options to `truck2jbeam.py`:

1. Update both completion files
2. Add appropriate completion logic for new parameter types
3. Update this documentation
4. Run the test script to verify completions

## License

These completion scripts are part of the truck2jbeam project and follow the same MIT license.
