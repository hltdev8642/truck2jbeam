# Shell Completions for truck2jbeam.py

This project includes comprehensive shell completion support for the `truck2jbeam.py` command, providing intelligent auto-completion for all command-line options, file types, and parameter values.

## 📁 Location

All completion files are located in the **`completions/`** directory:

```
completions/
├── _truck2jbeam                    # ZSH completion script
├── truck2jbeam-completion.ps1      # PowerShell completion script
├── install_completions.sh          # Linux/macOS installation script
├── Install-Completions.ps1         # Windows installation script
├── COMPLETION_SETUP.md             # Detailed setup instructions
├── README_COMPLETIONS.md           # Quick reference guide
├── COMPLETION_FILES_SUMMARY.md     # Comprehensive overview
└── test_completions.py             # Validation script
```

## 🚀 Quick Installation

### ZSH (Linux/macOS)
```bash
cd completions
./install_completions.sh
```

### PowerShell (Windows/Cross-platform)
```powershell
cd completions
.\Install-Completions.ps1
```

## ✨ Features

- **30+ Command Options**: Complete all available flags and parameters
- **Smart File Completion**: Only shows RoR files (*.truck, *.trailer, etc.)
- **Template Completion**: car, truck, airplane, trailer
- **Category Completion**: vehicles, terrains, aircraft, boats, etc.
- **Directory Completion**: Intelligent path completion
- **Context-Aware**: Provides relevant suggestions based on current option

## 📖 Documentation

For detailed installation instructions, troubleshooting, and usage examples, see:

- **[COMPLETION_SETUP.md](completions/COMPLETION_SETUP.md)** - Step-by-step installation guide
- **[README_COMPLETIONS.md](completions/README_COMPLETIONS.md)** - Quick reference and features
- **[COMPLETION_FILES_SUMMARY.md](completions/COMPLETION_FILES_SUMMARY.md)** - Comprehensive overview

## 🧪 Testing

Test the completion installation:

```bash
cd completions
python test_completions.py
```

## 💡 Usage Examples

Once installed, you can use tab completion:

```bash
# Complete command options
truck2jbeam.py --<TAB>

# Complete template names
truck2jbeam.py --template <TAB>

# Complete RoR files
truck2jbeam.py <TAB>

# Complete directories
truck2jbeam.py --output-dir <TAB>
```

## 🔧 Supported Shells

- ✅ **ZSH**: Full feature support (Linux, macOS, Windows WSL)
- ✅ **PowerShell**: Full feature support (Windows, Linux, macOS)
- ✅ **Bash**: Basic support via generated completion

## 📋 Requirements

- **ZSH**: Version 5.0 or later
- **PowerShell**: Version 5.1 or later (including PowerShell Core 6.0+)
- **Bash**: Version 4.0 or later (basic support)

Transform your truck2jbeam.py command-line experience with intelligent auto-completion!
