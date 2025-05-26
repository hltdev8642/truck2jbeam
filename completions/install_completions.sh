#!/bin/bash
# Installation script for truck2jbeam.py shell completions
# Supports ZSH and Bash completion installation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect shell
detect_shell() {
    if [ -n "$ZSH_VERSION" ]; then
        echo "zsh"
    elif [ -n "$BASH_VERSION" ]; then
        echo "bash"
    else
        echo "unknown"
    fi
}

# Install ZSH completion
install_zsh_completion() {
    print_info "Installing ZSH completion..."

    # Check if ZSH is available
    if ! command -v zsh &> /dev/null; then
        print_warning "ZSH not found, skipping ZSH completion installation"
        return 1
    fi

    # Create completions directory
    COMPLETION_DIR="$HOME/.zsh/completions"
    mkdir -p "$COMPLETION_DIR"

    # Copy completion file
    if [ -f "_truck2jbeam" ]; then
        cp "_truck2jbeam" "$COMPLETION_DIR/"
        print_success "ZSH completion file copied to $COMPLETION_DIR"
    else
        print_error "ZSH completion file '_truck2jbeam' not found"
        print_error "Make sure you're running this script from the completions directory"
        return 1
    fi

    # Update .zshrc if needed
    ZSHRC="$HOME/.zshrc"
    FPATH_LINE="fpath=(~/.zsh/completions \$fpath)"

    if [ -f "$ZSHRC" ]; then
        if ! grep -q "fpath=(.*\.zsh/completions" "$ZSHRC"; then
            echo "" >> "$ZSHRC"
            echo "# truck2jbeam completion" >> "$ZSHRC"
            echo "$FPATH_LINE" >> "$ZSHRC"
            print_success "Added completion path to $ZSHRC"
        else
            print_info "Completion path already exists in $ZSHRC"
        fi
    else
        echo "$FPATH_LINE" > "$ZSHRC"
        print_success "Created $ZSHRC with completion path"
    fi

    print_info "To activate completions, run: source ~/.zshrc && autoload -U compinit && compinit"
    return 0
}

# Install Bash completion (basic support)
install_bash_completion() {
    print_info "Installing Bash completion..."

    # Check if Bash is available
    if ! command -v bash &> /dev/null; then
        print_warning "Bash not found, skipping Bash completion installation"
        return 1
    fi

    # Create a basic bash completion from ZSH completion
    COMPLETION_DIR="$HOME/.bash_completions"
    mkdir -p "$COMPLETION_DIR"

    # Generate basic bash completion
    cat > "$COMPLETION_DIR/truck2jbeam" << 'EOF'
# Bash completion for truck2jbeam.py
_truck2jbeam_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Basic options
    opts="--help -h --version --output-dir -o --directory -d --batch --backup --no-backup
          --force -f --verbose -v --dry-run --author --template --config --process-dae
          --dae-output --no-duplicate-resolution --strict-validation --include-stats
          --min-mass --search-ror --download-ids --download-search --download-dir
          --category --auto-convert --no-extract --search-limit"

    # Template options
    templates="car truck airplane trailer"

    # Categories
    categories="vehicles terrains aircraft boats trailers loads skins tools"

    case "${prev}" in
        --template)
            COMPREPLY=( $(compgen -W "${templates}" -- ${cur}) )
            return 0
            ;;
        --category)
            COMPREPLY=( $(compgen -W "${categories}" -- ${cur}) )
            return 0
            ;;
        --output-dir|--directory|--process-dae|--dae-output|--download-dir)
            COMPREPLY=( $(compgen -d -- ${cur}) )
            return 0
            ;;
        --config)
            COMPREPLY=( $(compgen -f -X '!*.json' -- ${cur}) )
            return 0
            ;;
    esac

    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi

    # Complete RoR files
    COMPREPLY=( $(compgen -f -X '!*.@(truck|trailer|airplane|boat|car|load)' -- ${cur}) )
}

complete -F _truck2jbeam_completion truck2jbeam.py
EOF

    print_success "Bash completion file created at $COMPLETION_DIR/truck2jbeam"

    # Update .bashrc if needed
    BASHRC="$HOME/.bashrc"
    SOURCE_LINE="source ~/.bash_completions/truck2jbeam"

    if [ -f "$BASHRC" ]; then
        if ! grep -q "source.*\.bash_completions/truck2jbeam" "$BASHRC"; then
            echo "" >> "$BASHRC"
            echo "# truck2jbeam completion" >> "$BASHRC"
            echo "$SOURCE_LINE" >> "$BASHRC"
            print_success "Added completion source to $BASHRC"
        else
            print_info "Completion source already exists in $BASHRC"
        fi
    else
        echo "$SOURCE_LINE" > "$BASHRC"
        print_success "Created $BASHRC with completion source"
    fi

    print_info "To activate completions, run: source ~/.bashrc"
    return 0
}

# Main installation function
main() {
    echo "truck2jbeam.py Shell Completion Installer"
    echo "========================================"

    # Check if we're in the right directory
    if [ ! -f "_truck2jbeam" ]; then
        print_error "Completion files not found. Please run this script from the completions directory."
        print_error "Usage: cd completions && ./install_completions.sh"
        exit 1
    fi

    # Detect current shell
    CURRENT_SHELL=$(detect_shell)
    print_info "Detected shell: $CURRENT_SHELL"

    # Install completions based on available shells and user preference
    if [ "$1" = "--zsh" ] || [ "$1" = "-z" ]; then
        install_zsh_completion
    elif [ "$1" = "--bash" ] || [ "$1" = "-b" ]; then
        install_bash_completion
    elif [ "$1" = "--all" ] || [ "$1" = "-a" ]; then
        install_zsh_completion || true
        install_bash_completion || true
    else
        # Auto-detect and install for current shell
        case "$CURRENT_SHELL" in
            zsh)
                install_zsh_completion
                ;;
            bash)
                install_bash_completion
                ;;
            *)
                print_info "Unknown shell. Installing for both ZSH and Bash..."
                install_zsh_completion || true
                install_bash_completion || true
                ;;
        esac
    fi

    echo ""
    print_success "Installation completed!"
    print_info "Restart your shell or source your shell configuration file to activate completions."

    # Show usage examples
    echo ""
    echo "Test completions with:"
    echo "  truck2jbeam.py --<TAB>"
    echo "  truck2jbeam.py --template <TAB>"
    echo "  truck2jbeam.py <TAB>"
}

# Show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Install shell completions for truck2jbeam.py"
    echo ""
    echo "Options:"
    echo "  -z, --zsh     Install ZSH completion only"
    echo "  -b, --bash    Install Bash completion only"
    echo "  -a, --all     Install completions for all supported shells"
    echo "  -h, --help    Show this help message"
    echo ""
    echo "If no option is specified, installs completion for the current shell."
}

# Parse command line arguments
case "$1" in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
