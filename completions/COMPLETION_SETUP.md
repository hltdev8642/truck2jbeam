# Shell Completion Setup for truck2jbeam.py

This document provides instructions for setting up auto-completion for the `truck2jbeam.py` command in ZSH and PowerShell.

## ZSH Completion

### Installation

#### Option 1: User-specific installation (Recommended)

1. Create a completions directory in your home folder:
   ```bash
   mkdir -p ~/.zsh/completions
   ```

2. Copy the completion file:
   ```bash
   cp completions/_truck2jbeam ~/.zsh/completions/
   ```

3. Add the completions directory to your `fpath` in `~/.zshrc`:
   ```bash
   echo 'fpath=(~/.zsh/completions $fpath)' >> ~/.zshrc
   ```

4. Reload your shell configuration:
   ```bash
   source ~/.zshrc
   autoload -U compinit && compinit
   ```

#### Option 2: System-wide installation

1. Copy the completion file to the system completions directory:
   ```bash
   sudo cp completions/_truck2jbeam /usr/share/zsh/site-functions/
   ```

2. Reload completions:
   ```bash
   autoload -U compinit && compinit
   ```

### Usage

Once installed, you can use tab completion with `truck2jbeam.py`:

```bash
# Complete command options
truck2jbeam.py --<TAB>

# Complete template names
truck2jbeam.py --template <TAB>

# Complete file names (RoR files)
truck2jbeam.py <TAB>

# Complete directory paths
truck2jbeam.py --output-dir <TAB>
```

### Features

- **Command Options**: Complete all available command-line options
- **Template Names**: Complete template names (car, truck, airplane, trailer)
- **File Completion**: Complete RoR files (*.truck, *.trailer, *.airplane, etc.)
- **Directory Completion**: Complete directory paths for relevant options
- **Category Completion**: Complete RoR repository categories
- **Context-Aware**: Provides appropriate completions based on the current option

## PowerShell Completion

### Installation

#### Option 1: Add to PowerShell Profile (Recommended)

1. Check if you have a PowerShell profile:
   ```powershell
   Test-Path $PROFILE
   ```

2. If the profile doesn't exist, create it:
   ```powershell
   New-Item -Path $PROFILE -Type File -Force
   ```

3. Add the completion script to your profile:
   ```powershell
   Add-Content -Path $PROFILE -Value ". path\to\completions\truck2jbeam-completion.ps1"
   ```

   Replace `path\to\` with the actual path to the truck2jbeam directory.

4. Reload your PowerShell profile:
   ```powershell
   . $PROFILE
   ```

#### Option 2: Manual loading

Run the completion script manually in your PowerShell session:
```powershell
. .\completions\truck2jbeam-completion.ps1
```

### Usage

Once loaded, you can use tab completion with `truck2jbeam.py`:

```powershell
# Complete command options
truck2jbeam.py --<TAB>

# Complete template names
truck2jbeam.py --template <TAB>

# Complete file names (RoR files)
truck2jbeam.py <TAB>

# Complete directory paths
truck2jbeam.py --output-dir <TAB>

# Also works with python command
python truck2jbeam.py --<TAB>
```

### Features

- **Command Options**: Complete all available command-line options with descriptions
- **Template Names**: Complete template names (car, truck, airplane, trailer)
- **File Completion**: Complete RoR files and JSON config files
- **Directory Completion**: Complete directory paths for relevant options
- **Category Completion**: Complete RoR repository categories
- **Python Integration**: Works with `python truck2jbeam.py` commands
- **Rich Descriptions**: Shows helpful descriptions for each completion option

## Completion Features

Both completion systems provide:

### Basic Options
- `--help`, `-h`: Show help message
- `--version`: Show version information
- `--output-dir`, `-o`: Output directory completion
- `--directory`, `-d`: Search directory completion
- `--verbose`, `-v`: Verbose output
- `--dry-run`: Preview mode
- `--force`, `-f`: Force overwrite

### Enhanced Features
- `--template`: Template completion (car, truck, airplane, trailer)
- `--config`: JSON configuration file completion
- `--process-dae`: DAE directory completion
- `--dae-output`: DAE output directory completion
- `--min-mass`: Minimum mass override
- `--strict-validation`: Strict validation mode
- `--include-stats`: Include statistics

### Download Options
- `--search-ror`: Search RoR repository
- `--download-ids`: Download by resource IDs
- `--download-search`: Download by search query
- `--download-dir`: Download directory completion
- `--category`: Category completion (vehicles, terrains, aircraft, etc.)
- `--auto-convert`: Auto-convert downloads
- `--search-limit`: Search result limit

### File Completion
Automatically completes RoR files with extensions:
- `*.truck`
- `*.trailer`
- `*.airplane`
- `*.boat`
- `*.car`
- `*.load`

## Troubleshooting

### ZSH Issues

1. **Completions not working**: Ensure `compinit` is called after adding to `fpath`
2. **Permission issues**: Make sure the completion file is readable
3. **Cache issues**: Clear completion cache with `rm ~/.zcompdump*` and restart shell

### PowerShell Issues

1. **Execution policy**: You may need to set execution policy:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

2. **Module not found**: Ensure the completion script path is correct in your profile

3. **Completions not showing**: Restart PowerShell after adding to profile

## Testing

Test the completions by typing:

### ZSH
```bash
truck2jbeam.py --<TAB><TAB>
```

### PowerShell
```powershell
truck2jbeam.py --<TAB>
```

You should see a list of available options with descriptions.
