@echo off
REM truck2jbeam Windows Batch Converter
REM Drag and drop truck files onto this batch file to convert them

setlocal enabledelayedexpansion

echo truck2jbeam Enhanced Converter
echo ================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://python.org
    pause
    exit /b 1
)

REM Check if any files were dropped
if "%~1"=="" (
    echo No files provided. 
    echo.
    echo Usage: Drag and drop .truck, .trailer, .airplane, .boat, .car, or .load files onto this batch file
    echo.
    echo Alternatively, you can run from command line:
    echo   python truck2jbeam.py myfile.truck
    echo.
    pause
    exit /b 1
)

REM Process each dropped file
set /a count=0
set /a success=0
set /a failed=0

:loop
if "%~1"=="" goto summary

set /a count+=1
set "file=%~1"
echo [!count!] Processing: !file!

REM Check if file exists
if not exist "!file!" (
    echo   ERROR: File not found
    set /a failed+=1
    goto next
)

REM Check file extension
set "ext=%~x1"
if /i "!ext!"==".truck" goto convert
if /i "!ext!"==".trailer" goto convert
if /i "!ext!"==".airplane" goto convert
if /i "!ext!"==".boat" goto convert
if /i "!ext!"==".car" goto convert
if /i "!ext!"==".load" goto convert

echo   WARNING: Unsupported file extension: !ext!
echo   Supported: .truck, .trailer, .airplane, .boat, .car, .load
set /a failed+=1
goto next

:convert
REM Run the converter
python truck2jbeam.py "!file!" --verbose
if errorlevel 1 (
    echo   ERROR: Conversion failed
    set /a failed+=1
) else (
    echo   SUCCESS: Converted successfully
    set /a success+=1
)

:next
shift
echo.
goto loop

:summary
echo ================================
echo Conversion Summary
echo ================================
echo Files processed: !count!
echo Successful: !success!
echo Failed: !failed!
echo.

if !failed! gtr 0 (
    echo Some conversions failed. Check the output above for details.
    echo.
    echo Common issues:
    echo - Invalid file format or syntax
    echo - Missing required sections (nodes, beams)
    echo - File permission issues
    echo.
    echo For detailed help, run: python truck2jbeam.py --help
)

if !success! gtr 0 (
    echo Successfully converted files can be found in the same directory as the source files.
    echo Look for .jbeam files with the same name as your input files.
)

echo.
pause
