# PowerShell installation script for truck2jbeam.py completions
# Enhanced Rigs of Rods to BeamNG.drive JBeam Converter

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$AllUsers,
    [switch]$CurrentUser,
    [switch]$Help
)

# Colors for output
$Colors = @{
    Info = 'Cyan'
    Success = 'Green'
    Warning = 'Yellow'
    Error = 'Red'
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Type = 'Info'
    )
    Write-Host "[$Type] $Message" -ForegroundColor $Colors[$Type]
}

function Show-Help {
    Write-Host "truck2jbeam.py PowerShell Completion Installer" -ForegroundColor Blue
    Write-Host "=============================================" -ForegroundColor Blue
    Write-Host ""
    Write-Host "SYNOPSIS"
    Write-Host "    Install PowerShell completion for truck2jbeam.py"
    Write-Host ""
    Write-Host "SYNTAX"
    Write-Host "    .\Install-Completions.ps1 [-Force] [-AllUsers] [-CurrentUser] [-Help]"
    Write-Host ""
    Write-Host "PARAMETERS"
    Write-Host "    -Force        Overwrite existing completion installation"
    Write-Host "    -AllUsers     Install for all users (requires admin privileges)"
    Write-Host "    -CurrentUser  Install for current user only (default)"
    Write-Host "    -Help         Show this help message"
    Write-Host ""
    Write-Host "EXAMPLES"
    Write-Host "    .\Install-Completions.ps1"
    Write-Host "        Install completion for current user"
    Write-Host ""
    Write-Host "    .\Install-Completions.ps1 -Force"
    Write-Host "        Force reinstall completion for current user"
    Write-Host ""
    Write-Host "    .\Install-Completions.ps1 -AllUsers"
    Write-Host "        Install completion for all users (requires admin)"
}

function Test-AdminPrivileges {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-Completion {
    param(
        [bool]$ForAllUsers = $false
    )

    Write-ColorOutput "Installing PowerShell completion for truck2jbeam.py..." "Info"

    # Check if completion file exists
    $completionFile = "truck2jbeam-completion.ps1"
    if (-not (Test-Path $completionFile)) {
        Write-ColorOutput "Completion file '$completionFile' not found!" "Error"
        Write-ColorOutput "Please run this script from the truck2jbeam directory." "Error"
        return $false
    }

    # Determine profile path
    if ($ForAllUsers) {
        if (-not (Test-AdminPrivileges)) {
            Write-ColorOutput "Administrator privileges required for all-users installation!" "Error"
            return $false
        }
        $profilePath = $PROFILE.AllUsersAllHosts
        Write-ColorOutput "Installing for all users..." "Info"
    } else {
        $profilePath = $PROFILE.CurrentUserAllHosts
        Write-ColorOutput "Installing for current user..." "Info"
    }

    Write-ColorOutput "Profile path: $profilePath" "Info"

    # Create profile directory if it doesn't exist
    $profileDir = Split-Path $profilePath -Parent
    if (-not (Test-Path $profileDir)) {
        try {
            New-Item -Path $profileDir -ItemType Directory -Force | Out-Null
            Write-ColorOutput "Created profile directory: $profileDir" "Success"
        } catch {
            Write-ColorOutput "Failed to create profile directory: $($_.Exception.Message)" "Error"
            return $false
        }
    }

    # Create profile file if it doesn't exist
    if (-not (Test-Path $profilePath)) {
        try {
            New-Item -Path $profilePath -ItemType File -Force | Out-Null
            Write-ColorOutput "Created profile file: $profilePath" "Success"
        } catch {
            Write-ColorOutput "Failed to create profile file: $($_.Exception.Message)" "Error"
            return $false
        }
    }

    # Get absolute path to completion script
    $completionScriptPath = (Resolve-Path $completionFile).Path
    $sourceCommand = ". `"$completionScriptPath`""

    # Check if completion is already installed
    $profileContent = Get-Content $profilePath -ErrorAction SilentlyContinue
    $alreadyInstalled = $profileContent | Where-Object { $_ -match "truck2jbeam-completion\.ps1" }

    if ($alreadyInstalled -and -not $Force) {
        Write-ColorOutput "Completion already installed in profile!" "Warning"
        Write-ColorOutput "Use -Force to reinstall." "Info"
        return $true
    }

    # Remove existing installation if forcing
    if ($Force -and $alreadyInstalled) {
        Write-ColorOutput "Removing existing completion installation..." "Info"
        $newContent = $profileContent | Where-Object { $_ -notmatch "truck2jbeam-completion\.ps1" -and $_ -notmatch "truck2jbeam\.py.*completion" }
        Set-Content -Path $profilePath -Value $newContent
    }

    # Add completion to profile
    try {
        Add-Content -Path $profilePath -Value ""
        Add-Content -Path $profilePath -Value "# truck2jbeam.py completion"
        Add-Content -Path $profilePath -Value $sourceCommand
        Write-ColorOutput "Added completion to PowerShell profile!" "Success"
    } catch {
        Write-ColorOutput "Failed to add completion to profile: $($_.Exception.Message)" "Error"
        return $false
    }

    return $true
}

function Test-Completion {
    Write-ColorOutput "Testing completion installation..." "Info"

    try {
        # Source the completion script
        . ".\truck2jbeam-completion.ps1"
        Write-ColorOutput "Completion script loaded successfully!" "Success"

        Write-ColorOutput "Test the completion by typing:" "Info"
        Write-ColorOutput "  truck2jbeam.py --<TAB>" "Info"
        Write-ColorOutput "  python truck2jbeam.py --<TAB>" "Info"

        return $true
    } catch {
        Write-ColorOutput "Failed to load completion script: $($_.Exception.Message)" "Error"
        return $false
    }
}

function Main {
    if ($Help) {
        Show-Help
        return
    }

    Write-Host "truck2jbeam.py PowerShell Completion Installer" -ForegroundColor Blue
    Write-Host "=============================================" -ForegroundColor Blue
    Write-Host ""

    # Check if we're in the right directory
    if (-not (Test-Path "truck2jbeam-completion.ps1")) {
        Write-ColorOutput "Completion files not found!" "Error"
        Write-ColorOutput "Please run this script from the completions directory." "Error"
        Write-ColorOutput "Usage: cd completions; .\Install-Completions.ps1" "Error"
        exit 1
    }

    # Determine installation scope
    $installForAllUsers = $AllUsers -and -not $CurrentUser

    if ($AllUsers -and $CurrentUser) {
        Write-ColorOutput "Cannot specify both -AllUsers and -CurrentUser!" "Error"
        exit 1
    }

    # Install completion
    $success = Install-Completion -ForAllUsers $installForAllUsers

    if ($success) {
        Write-ColorOutput "Installation completed successfully!" "Success"
        Write-Host ""
        Write-ColorOutput "To activate completions immediately, restart PowerShell or run:" "Info"
        Write-ColorOutput "  . `$PROFILE" "Info"
        Write-Host ""

        # Test completion in current session
        Test-Completion
    } else {
        Write-ColorOutput "Installation failed!" "Error"
        exit 1
    }
}

# Run main function
Main
