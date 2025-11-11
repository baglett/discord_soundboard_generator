# Build Guide - Discord Soundboard Generator

This guide provides detailed instructions for building distributable executables of the Discord Soundboard Generator application.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Build Process Details](#build-process-details)
5. [Customization](#customization)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Topics](#advanced-topics)

## Overview

The Discord Soundboard Generator can be packaged into a standalone executable that:
- Runs without requiring Python installation
- Includes all dependencies
- Prompts users for credentials on first launch
- Auto-installs FFmpeg if needed
- Creates a self-contained distribution package

## Prerequisites

### Software Requirements

1. **Python 3.13.3+** - Installed and in PATH
2. **Git** - For version control
3. **All project dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Disk Space

- ~500 MB for build process
- ~100 MB for final distribution package

### Supported Platforms

- **Windows 10/11** - Fully supported (tested)
- **macOS** - Should work (requires testing)
- **Linux** - Requires modifications to spec file

## Quick Start

### Windows

```bash
# Option 1: Use the batch file
build.bat

# Option 2: Use Python directly
python build.py
```

### macOS/Linux

```bash
python build.py
```

### Output

The build process creates:
```
distributions/
└── DiscordSoundboardGenerator_v1.0.0_YYYYMMDD_HHMMSS/
    ├── DiscordSoundboardGenerator/          # The executable application
    ├── README.md                            # Full documentation
    ├── sample.env                           # Credentials template
    └── DISTRIBUTION_README.txt              # Quick start guide
```

## Build Process Details

### Step 1: Cleanup

Removes old build artifacts:
- `build/` - Temporary build files
- `dist/` - Previous distributions

### Step 2: PyInstaller Execution

Runs PyInstaller with the custom spec file:
```bash
pyinstaller discord_soundboard.spec --clean
```

**What gets bundled:**
- All Python source files
- setup/ directory (FFmpeg installer)
- sounds/ directory (template)
- All Python dependencies
- Required DLLs and binaries

**What's excluded:**
- Development tools (pytest, black, etc.)
- Unnecessary packages (matplotlib, numpy, pandas)
- Documentation files
- Git metadata

### Step 3: Distribution Packaging

Creates a timestamped folder with:
1. The built application
2. Documentation files
3. End-user instructions

## Customization

### Changing the Application Icon

1. Create or obtain an `.ico` file (Windows) or `.icns` file (macOS)
2. Place it in the project root
3. Edit `discord_soundboard.spec`:

```python
exe = EXE(
    # ...
    icon='myicon.ico',  # Add this line
    # ...
)
```

4. Rebuild:
```bash
python build.py
```

### Modifying the Version Number

Edit `build.py` line 68:
```python
version = "v1.0.0"  # Change this
```

### Adding Additional Files

To include extra files in the distribution, edit `discord_soundboard.spec`:

```python
# Add to the datas list
datas = [
    ('setup', 'setup'),
    ('sounds', 'sounds'),
    ('path/to/your/file.txt', '.'),  # Add this
]
```

### Changing the Executable Name

Edit `discord_soundboard.spec`:
```python
exe = EXE(
    # ...
    name='MyCustomName',  # Change this
    # ...
)
```

### Creating a Single-File Executable

**Warning:** Single-file executables are slower to start and may trigger antivirus false positives.

Edit `discord_soundboard.spec`:
```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # Move these
    a.zipfiles,      # Move these
    a.datas,         # Move these
    [],
    exclude_binaries=False,  # Change this
    # ...
)

# Remove or comment out the COLLECT block
```

## Testing

### Test the Built Executable

1. **Navigate to the distribution folder:**
   ```bash
   cd distributions/DiscordSoundboardGenerator_v1.0.0_TIMESTAMP/DiscordSoundboardGenerator/
   ```

2. **Run the executable:**
   ```bash
   DiscordSoundboardGenerator.exe
   ```

3. **Test scenarios:**
   - First launch (no credentials)
   - FFmpeg auto-install (delete ffmpeg/ folder first)
   - Create a sound from YouTube
   - Upload a local file
   - Manage existing sounds
   - Settings persistence

### Test on a Clean System

For best results, test on a computer without Python installed:
1. Copy the entire `DiscordSoundboardGenerator/` folder
2. Run the executable
3. Verify all features work

## Troubleshooting

### Build Fails - "PyInstaller not found"

**Solution:**
```bash
pip install pyinstaller==6.11.1
```

### Build Fails - Missing Module

**Solution:** Add the module to `hidden_imports` in `discord_soundboard.spec`:
```python
hidden_imports = [
    'pygame',
    'pydub',
    'your_missing_module',  # Add here
]
```

### Executable Crashes on Startup

**Diagnosis:**
```bash
# Run with debug mode
DiscordSoundboardGenerator.exe --debug
```

**Common causes:**
1. Missing hidden imports
2. Missing data files
3. Antivirus interference

**Solutions:**
1. Check console output for import errors
2. Add missing imports to spec file
3. Temporarily disable antivirus for testing

### Executable Won't Run - "Windows Protected Your PC"

This is Windows SmartScreen. To bypass:
1. Click "More info"
2. Click "Run anyway"

**For distribution:**
- Code signing certificate required to avoid this warning
- Alternatively, users can add an exception

### Large Executable Size

**Normal size:** 80-150 MB (includes Python, dependencies, and libraries)

**To reduce size:**
1. Exclude unnecessary packages in spec file
2. Use UPX compression (already enabled)
3. Audit dependencies for bloat

### Antivirus False Positives

PyInstaller executables are often flagged as suspicious.

**Solutions:**
1. Submit to antivirus vendors for whitelisting
2. Code signing (requires certificate)
3. Build on a clean system
4. Use virtualization for testing

## Advanced Topics

### Building for Different Python Versions

```bash
# Use a specific Python version
py -3.13 -m PyInstaller discord_soundboard.spec
```

### Cross-Platform Builds

**Important:** PyInstaller creates executables for the platform it runs on.

To build for multiple platforms:
1. Build on Windows → Windows .exe
2. Build on macOS → macOS app
3. Build on Linux → Linux binary

**Cannot cross-compile** - must build on each target platform.

### Continuous Integration (CI/CD)

Example GitHub Actions workflow:

```yaml
name: Build Executable

on:
  push:
    tags:
      - 'v*'

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: python build.py
      - uses: actions/upload-artifact@v3
        with:
          name: windows-build
          path: distributions/
```

### Code Signing (Windows)

To avoid SmartScreen warnings:

1. Obtain a code signing certificate
2. Install certificate
3. Sign the executable:
   ```bash
   signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com DiscordSoundboardGenerator.exe
   ```

### Creating an Installer

Use tools like:
- **Inno Setup** (Windows)
- **NSIS** (Windows)
- **create-dmg** (macOS)

Example Inno Setup script:
```iss
[Setup]
AppName=Discord Soundboard Generator
AppVersion=1.0.0
DefaultDirName={pf}\DiscordSoundboardGenerator
OutputDir=installers

[Files]
Source: "dist\DiscordSoundboardGenerator\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{commondesktop}\Discord Soundboard Generator"; Filename: "{app}\DiscordSoundboardGenerator.exe"
```

### Debugging the Built Executable

Enable console mode temporarily:

```python
# In discord_soundboard.spec
exe = EXE(
    # ...
    console=True,  # Change to True for debugging
    # ...
)
```

This shows console output for debugging.

## Build Checklist

Before distributing:

- [ ] Test executable on clean system (no Python)
- [ ] Verify FFmpeg auto-install works
- [ ] Test credentials entry and persistence
- [ ] Test all major features (YouTube, local upload, management)
- [ ] Check file size is reasonable (<200 MB)
- [ ] Verify documentation is included
- [ ] Test on different Windows versions (if possible)
- [ ] Scan with antivirus to check for false positives
- [ ] Create release notes
- [ ] Tag the Git commit with version number

## Support

For build issues:
1. Check this guide
2. Review PyInstaller documentation: https://pyinstaller.org/
3. Open an issue on GitHub with:
   - Your OS and Python version
   - Full build output
   - Error messages

## References

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [PyInstaller Spec Files](https://pyinstaller.org/en/stable/spec-files.html)
- [PyInstaller Hooks](https://pyinstaller.org/en/stable/hooks.html)
- [Code Signing Guide](https://docs.microsoft.com/en-us/windows/win32/seccrypto/cryptography-tools)
