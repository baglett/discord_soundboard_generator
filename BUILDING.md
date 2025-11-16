# Building the Discord Soundboard Generator

This document explains how to build distributable executables using the automated build system.

## Quick Start

Build a new version:
```bash
make build
```

That's it! The build system will:
1. Automatically determine the next version number
2. Build the executable
3. Package everything into `distributions/DiscordSoundboardGenerator_vX.X.X/`

## Build System Overview

The project uses a Makefile-based build system with automatic version management:

### Version Management

- **Version file**: `.version` tracks the current version
- **Default version**: `1.0.0`
- **Auto-increment**: Patch version increments automatically if distribution exists
- **No timestamps**: Clean semantic versioning only

### Build Flow

```
make build
    ↓
Check if distributions/DiscordSoundboardGenerator_v1.0.X exists
    ↓
    ├─ No  → Use current version (1.0.X)
    └─ Yes → Increment patch (1.0.X+1)
    ↓
Clean build/ and dist/
    ↓
Run PyInstaller with discord_soundboard.spec
    ↓
Package into distributions/DiscordSoundboardGenerator_v1.0.X/
    ↓
Save new version to .version
```

## Available Commands

### `make build`
Build a new distributable executable with automatic version management.

**Output location**: `distributions/DiscordSoundboardGenerator_vX.X.X/`

**What's included:**
- `DiscordSoundboardGenerator/` - Executable and dependencies
  - `DiscordSoundboardGenerator.exe` - Main application
  - `_internal/ffmpeg/` - Bundled FFmpeg binaries (~190MB)
  - `_internal/` - All Python dependencies
- `README.md` - Full documentation
- `sample.env` - Credentials template
- `DISTRIBUTION_README.txt` - End-user quick start

### `make version`
Display the current version number.

```bash
$ make version
1.0.1
```

### `make clean`
Remove build artifacts (`build/` and `dist/` directories).

**Note**: This does NOT remove distributions - those are your release artifacts!

### `make install`
Install all Python dependencies from `requirements.txt`.

```bash
make install
```

Equivalent to:
```bash
pip install -r requirements.txt
```

### `make test`
Run the application directly (without building).

```bash
make test
```

Equivalent to:
```bash
python main.py
```

### `make help`
Display available commands.

## Version Numbering

The build system follows semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR** (1): Breaking changes
- **MINOR** (0): New features, backwards compatible
- **PATCH** (X): Bug fixes and small improvements

Currently, the build system **auto-increments the PATCH version** only.

### Manually Setting Version

To manually change the version, edit `.version`:

```bash
echo "1.1.0" > .version
```

Then run `make build` - it will use `1.1.0` and increment from there.

### Version Examples

```bash
# First build
$ make build
→ Creates: DiscordSoundboardGenerator_v1.0.0

# Second build
$ make build
→ Creates: DiscordSoundboardGenerator_v1.0.1

# Manual version change
$ echo "2.0.0" > .version
$ make build
→ Creates: DiscordSoundboardGenerator_v2.0.0

# Next build
$ make build
→ Creates: DiscordSoundboardGenerator_v2.0.1
```

## Alternative Build Methods

### Windows Batch File

```bash
build.bat
```

Runs `build_versioned.py` directly.

### Direct Python

```bash
python build_versioned.py
```

Same as `make build` but without Make.

### Old Build Script (Non-versioned)

```bash
python build.py
```

Creates timestamped builds (legacy). Not recommended.

## Build Scripts Explained

### `Makefile`
- Main entry point for all build commands
- Cross-platform (requires GNU Make)
- Delegates to Python scripts

### `build_versioned.py`
- Core versioned build logic
- Automatic version detection and increment
- PyInstaller execution
- Distribution packaging

### `build.py`
- Legacy timestamped build script
- Creates `DiscordSoundboardGenerator_v1.0.0_YYYYMMDD_HHMMSS/`
- Kept for backwards compatibility

### `build.bat`
- Windows convenience wrapper
- Calls `build_versioned.py`

### `discord_soundboard.spec`
- PyInstaller configuration
- Defines what gets bundled
- Hidden imports and data files

### `hook-pkg_resources.py`
- PyInstaller runtime hook
- Ensures pkg_resources compatibility
- Pre-imports jaraco dependencies

## Distribution Structure

After `make build`, you'll have:

```
distributions/
├── .gitkeep
├── DiscordSoundboardGenerator_v1.0.0/
│   ├── DiscordSoundboardGenerator/
│   │   ├── DiscordSoundboardGenerator.exe  (10 MB)
│   │   ├── _internal/                      (Dependencies)
│   │   ├── setup/                          (FFmpeg installer)
│   │   └── sounds/                         (Empty template)
│   ├── README.md
│   ├── sample.env
│   └── DISTRIBUTION_README.txt
│
└── DiscordSoundboardGenerator_v1.0.1/
    └── (Same structure)
```

## Sharing Distributions

To distribute to end users:

1. **Zip the version folder**:
   ```bash
   cd distributions
   zip -r DiscordSoundboardGenerator_v1.0.1.zip DiscordSoundboardGenerator_v1.0.1/
   ```

2. **Upload to GitHub Releases**:
   ```bash
   gh release create v1.0.1 \
     distributions/DiscordSoundboardGenerator_v1.0.1.zip \
     --title "Discord Soundboard Generator v1.0.1" \
     --notes "Release notes here"
   ```

3. **Share the zip file** - Users extract and run the .exe

## Requirements

### Build Requirements

- Python 3.13.3+
- PyInstaller 6.16.0+
- All dependencies from `requirements.txt`

Install with:
```bash
make install
```

### System Requirements

- **Windows**: Fully supported, tested on Windows 10/11
- **macOS**: Should work (untested)
- **Linux**: Requires make adjustments

### Make Requirement

- **Windows**: Install via Git Bash, WSL, or Chocolatey
- **macOS**: Included with Xcode Command Line Tools
- **Linux**: `sudo apt install make`

## Troubleshooting

### Build fails with "jaraco.text not found"

Install the missing dependencies:
```bash
pip install jaraco.text jaraco.functools jaraco.context more-itertools
```

Or just:
```bash
make install
```

### "make: command not found"

Make is not installed. Use alternative methods:
```bash
# Windows
build.bat

# Or Python directly
python build_versioned.py
```

### Version doesn't increment

Check if the distribution folder exists:
```bash
ls distributions/
```

If it doesn't exist, the version won't increment. This is expected behavior.

### Build is slow

PyInstaller builds take 1-3 minutes. This is normal.

Subsequent builds use cached modules, so they're faster.

### Executable is large (~240 MB)

Normal. The distribution includes:
- Python interpreter (~5 MB)
- All dependencies (pygame, yt-dlp, requests, etc.) (~40 MB)
- Tkinter GUI framework (~5 MB)
- **FFmpeg binaries (~190 MB)** - Pre-bundled for immediate use
- Total: ~243 MB uncompressed, ~80 MB when zipped

### Antivirus flags the executable

Common false positive with PyInstaller. Solutions:
1. Add exception in antivirus
2. Code sign the executable (requires certificate)
3. Submit to antivirus vendors for whitelisting

## Advanced Usage

### Building for Different Platforms

Build on each target platform:

```bash
# On Windows
make build  # Creates .exe

# On macOS
make build  # Creates .app

# On Linux
make build  # Creates binary
```

Cannot cross-compile - must build on the target OS.

### Customizing the Build

Edit `discord_soundboard.spec`:

```python
# Change executable name
exe = EXE(
    ...
    name='MyCustomName',  # Default: DiscordSoundboardGenerator
    ...
)

# Add an icon
exe = EXE(
    ...
    icon='myicon.ico',  # Add your icon file
    ...
)

# Create single-file executable (slower startup)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,  # Include these
    a.zipfiles,  # Include these
    a.datas,     # Include these
    [],
    exclude_binaries=False,  # Change to False
    ...
)
```

After editing, run:
```bash
make build
```

### Adding Files to Distribution

Edit `build_versioned.py`, function `create_distribution_package()`:

```python
# Copy additional files
files_to_copy = ['README.md', 'sample.env', 'LICENSE', 'myfile.txt']
```

## CI/CD Integration

### GitHub Actions Example

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
      - run: make install
      - run: make build
      - uses: actions/upload-artifact@v3
        with:
          name: windows-executable
          path: distributions/DiscordSoundboardGenerator_v*/
```

## Best Practices

1. **Test before distributing**: Always test the executable on a clean system
2. **Version control**: Commit the `.version` file to Git
3. **Release notes**: Document changes for each version
4. **Clean builds**: Run `make clean` before important releases
5. **Archive old versions**: Keep previous distributions for rollback

## Getting Help

- Run `make help` for available commands
- Check `BUILD.md` (this file) for documentation
- See `README.md` for application documentation
- Open an issue on GitHub for build problems

## Summary

```bash
# Most common workflow:
make install    # Install dependencies (first time only)
make build      # Build new version
make version    # Check what version was built
```

That's it! The build system handles everything else automatically.
