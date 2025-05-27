# PowerShell completion for truck2jbeam.py
# Enhanced Rigs of Rods to BeamNG.drive JBeam Converter
#
# Installation:
#   1. Add this to your PowerShell profile:
#      . path\to\truck2jbeam-completion.ps1
#   2. Or run it manually in your session
#
# To find your profile location: $PROFILE
# To create profile if it doesn't exist: New-Item -Path $PROFILE -Type File -Force

# Register argument completer for truck2jbeam.py
Register-ArgumentCompleter -CommandName 'truck2jbeam.py', 'python' -ParameterName 'truck2jbeam.py' -ScriptBlock {
    param($commandName, $parameterName, $wordToComplete, $commandAst, $fakeBoundParameters)

    # Check if we're completing truck2jbeam.py
    $commandLine = $commandAst.ToString()
    if ($commandLine -notmatch 'truck2jbeam\.py') {
        return
    }

    # Define completion options
    $options = @{
        # Basic options
        '--help' = 'Show help message and exit'
        '-h' = 'Show help message and exit'
        '--version' = 'Show version and exit'
        '--output-dir' = 'Output directory for JBeam files'
        '-o' = 'Output directory for JBeam files'
        '--directory' = 'Directory to search for rig files'
        '-d' = 'Directory to search for rig files'
        '--batch' = 'Batch process all files in directory'
        '--backup' = 'Create backup of existing files (default)'
        '--no-backup' = "Don't create backups"
        '--force' = 'Force overwrite existing files'
        '-f' = 'Force overwrite existing files'
        '--verbose' = 'Verbose output'
        '-v' = 'Verbose output'
        '--dry-run' = 'Show what would be done without converting'
        '--author' = 'Set custom author name in output'
        '--template' = 'Apply conversion template'
        '--config' = 'Path to custom configuration file'

        # Enhanced features
        '--process-dae' = 'Process DAE files directory'
        '--dae-output' = 'Output directory for modified DAE files'
        '--no-duplicate-resolution' = 'Disable automatic duplicate mesh name resolution'
        '--strict-validation' = 'Enable strict validation mode'
        '--include-stats' = 'Include conversion statistics in JBeam output'
        '--min-mass' = 'Override minimum node mass'
        '--no-transform-properties' = 'Exclude rotation, translation, and scale properties from flexbodies and props'
        '--convert-meshes' = 'Convert .mesh files to .dae/.blend format'
        '--mesh-output-format' = 'Output format for converted meshes (dae, blend, both)'
        '--mesh-output-dir' = 'Output directory for converted mesh files'

        # Download options
        '--search-ror' = 'Search RoR repository for resources'
        '--download-ids' = 'Download specific resources by ID'
        '--download-search' = 'Search and download resources'
        '--download-dir' = 'Directory for downloads'
        '--category' = 'Filter by category'
        '--auto-convert' = 'Automatically convert downloaded rig files'
        '--no-extract' = "Don't extract downloaded zip files"
        '--search-limit' = 'Limit search results'
    }

    # Template options
    $templates = @('car', 'truck', 'airplane', 'trailer')

    # Category options
    $categories = @('vehicles', 'terrains', 'aircraft', 'boats', 'trailers', 'loads', 'skins', 'tools')

    # RoR file extensions
    $rorExtensions = @('*.truck', '*.trailer', '*.airplane', '*.boat', '*.car', '*.load', '*.train')

    # Get the current word being completed
    $currentWord = $wordToComplete

    # If completing an option
    if ($currentWord.StartsWith('-')) {
        $options.Keys | Where-Object { $_ -like "$currentWord*" } | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new(
                $_,
                $_,
                'ParameterName',
                $options[$_]
            )
        }
        return
    }

    # Check what the previous parameter was for context-specific completion
    $tokens = $commandAst.CommandElements
    $previousToken = $null
    for ($i = 0; $i -lt $tokens.Count; $i++) {
        if ($tokens[$i].ToString() -eq $currentWord -and $i -gt 0) {
            $previousToken = $tokens[$i - 1].ToString()
            break
        }
    }

    # Context-specific completions
    switch ($previousToken) {
        '--template' {
            $templates | Where-Object { $_ -like "$currentWord*" } | ForEach-Object {
                [System.Management.Automation.CompletionResult]::new(
                    $_,
                    $_,
                    'ParameterValue',
                    "Template: $_"
                )
            }
            return
        }

        '--category' {
            $categories | Where-Object { $_ -like "$currentWord*" } | ForEach-Object {
                [System.Management.Automation.CompletionResult]::new(
                    $_,
                    $_,
                    'ParameterValue',
                    "Category: $_"
                )
            }
            return
        }

        { $_ -in @('--output-dir', '-o', '--directory', '-d', '--process-dae', '--dae-output', '--download-dir') } {
            # Complete directories
            Get-ChildItem -Directory -Path "." -Name | Where-Object { $_ -like "$currentWord*" } | ForEach-Object {
                [System.Management.Automation.CompletionResult]::new(
                    $_,
                    $_,
                    'ProviderContainer',
                    "Directory: $_"
                )
            }
            return
        }

        '--config' {
            # Complete JSON files
            Get-ChildItem -File -Path "." -Name -Include "*.json" | Where-Object { $_ -like "$currentWord*" } | ForEach-Object {
                [System.Management.Automation.CompletionResult]::new(
                    $_,
                    $_,
                    'ProviderItem',
                    "Config file: $_"
                )
            }
            return
        }
    }

    # Default: complete RoR files
    foreach ($extension in $rorExtensions) {
        Get-ChildItem -File -Path "." -Name -Include $extension | Where-Object { $_ -like "$currentWord*" } | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new(
                $_,
                $_,
                'ProviderItem',
                "RoR file: $_"
            )
        }
    }
}

# Also register for direct python calls
Register-ArgumentCompleter -CommandName 'python', 'python3', 'py' -ScriptBlock {
    param($commandName, $parameterName, $wordToComplete, $commandAst, $fakeBoundParameters)

    # Check if we're completing truck2jbeam.py as the first argument to python
    $commandLine = $commandAst.ToString()
    if ($commandLine -match 'python.*truck2jbeam\.py') {
        # Delegate to the main completer
        & (Get-Command -Name 'Register-ArgumentCompleter' -Module Microsoft.PowerShell.Core).ScriptBlock `
            'truck2jbeam.py' $parameterName $wordToComplete $commandAst $fakeBoundParameters
    }
}

Write-Host "truck2jbeam.py PowerShell completion loaded successfully!" -ForegroundColor Green
Write-Host "Type 'truck2jbeam.py --<TAB>' or 'python truck2jbeam.py --<TAB>' to see available options." -ForegroundColor Cyan
