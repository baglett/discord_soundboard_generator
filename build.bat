@echo off
REM Build script for Discord Soundboard Generator (Windows)
REM This script runs the Python build script

echo Building Discord Soundboard Generator...
echo.

python build_versioned.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build successful!
    echo Check the 'distributions' folder for your executable.
) else (
    echo.
    echo Build failed! Check the error messages above.
)

echo.
pause
