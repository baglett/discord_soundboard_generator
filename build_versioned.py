#!/usr/bin/env python3
"""
Versioned build script for Discord Soundboard Generator
Automatically handles version incrementing and distribution packaging
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import re

# Configuration
VERSION_FILE = Path('.version')
DEFAULT_VERSION = '1.0.0'
DIST_BASE = Path('distributions')

def print_step(step_name):
    """Print a formatted step message"""
    print(f"\n{'='*60}")
    print(f"  {step_name}")
    print(f"{'='*60}\n")

def parse_version(version_str):
    """Parse version string into major, minor, patch tuple"""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")
    return tuple(map(int, match.groups()))

def version_to_string(major, minor, patch):
    """Convert version tuple to string"""
    return f"{major}.{minor}.{patch}"

def get_current_version():
    """Get the current version from version file or return default"""
    if VERSION_FILE.exists():
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    return DEFAULT_VERSION

def save_version(version_str):
    """Save version to version file"""
    with open(VERSION_FILE, 'w') as f:
        f.write(version_str)

def get_next_version():
    """
    Calculate the next version based on existing distributions.
    If the dist folder exists, increment patch version.
    """
    current = get_current_version()
    major, minor, patch = parse_version(current)

    # Check if distribution with current version exists
    dist_folder_name = f"DiscordSoundboardGenerator_v{current}"
    dist_path = DIST_BASE / dist_folder_name

    if dist_path.exists():
        # Increment patch version
        patch += 1
        new_version = version_to_string(major, minor, patch)
        print(f"Distribution v{current} exists, incrementing to v{new_version}")
        return new_version
    else:
        print(f"Using version v{current}")
        return current

def clean_build_dirs():
    """Remove old build artifacts"""
    print_step("Cleaning old build artifacts")

    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Removing {dir_name}/")
            shutil.rmtree(dir_name)

    print("[OK] Build directories cleaned")

def run_pyinstaller():
    """Run PyInstaller with the spec file"""
    print_step("Running PyInstaller")

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'PyInstaller', 'discord_soundboard.spec', '--clean'],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("[OK] PyInstaller completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] PyInstaller failed with error:")
        print(e.stderr)
        return False

def create_distribution_package(version):
    """Package the built executable into the distributions folder"""
    print_step("Creating distribution package")

    # Create distributions folder if it doesn't exist
    DIST_BASE.mkdir(exist_ok=True)

    # Create versioned folder (no timestamp)
    dist_folder_name = f"DiscordSoundboardGenerator_v{version}"
    dist_folder = DIST_BASE / dist_folder_name

    # Check if it already exists (shouldn't happen if version increment worked)
    if dist_folder.exists():
        print(f"[WARNING] Distribution folder {dist_folder} already exists!")
        print("This shouldn't happen. Removing it and continuing...")
        shutil.rmtree(dist_folder)

    dist_folder.mkdir(exist_ok=True)

    # Copy the built application
    source = Path('dist/DiscordSoundboardGenerator')
    if not source.exists():
        print(f"[ERROR] Build output not found at {source}")
        return False

    print(f"Copying application to {dist_folder}/")
    shutil.copytree(source, dist_folder / 'DiscordSoundboardGenerator')

    # Copy README and other documentation
    files_to_copy = ['README.md', 'sample.env']
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy(file, dist_folder)
            print(f"  Copied {file}")

    # Create a distribution README
    create_distribution_readme(dist_folder, version)

    print(f"\n[OK] Distribution package created: {dist_folder}")
    return True

def create_distribution_readme(dist_folder, version):
    """Create a README specific for the distribution"""
    readme_content = f"""# Discord Soundboard Generator v{version} - Distribution Package

## What's Included

- `DiscordSoundboardGenerator/` - The main application folder containing the executable
- `README.md` - Original project README with full documentation
- `DISTRIBUTION_README.txt` - This file

## Quick Start

1. Navigate to the `DiscordSoundboardGenerator` folder
2. Run `DiscordSoundboardGenerator.exe` (Windows)
3. On first launch, you'll be prompted to enter your Discord credentials:
   - **Bot Token** (Discord API Key)
   - **Application ID** (Discord OAuth2 Application ID)
   - **Guild ID** (Your Discord Server ID)

## Getting Your Discord Credentials

### Bot Token (API Key)
1. Go to https://discord.com/developers/applications
2. Create a new application or select an existing one
3. Go to the "Bot" section
4. Click "Reset Token" and copy the token
5. **IMPORTANT**: Enable these Privileged Gateway Intents:
   - Server Members Intent
   - Message Content Intent

### Application ID
1. On the same page, go to "General Information"
2. Copy the "Application ID"

### Guild ID (Server ID)
1. Open Discord
2. Enable Developer Mode: Settings → Advanced → Developer Mode
3. Right-click your server name and click "Copy Server ID"

### Bot Permissions
Invite your bot to your server with these permissions:
- Manage Guild Expressions (for soundboard management)
- Use Soundboard

**Invite URL Template:**
```
https://discord.com/oauth2/authorize?client_id=YOUR_APPLICATION_ID&scope=bot&permissions=1099511627776
```

## First Run

On first launch:
1. The application will check for FFmpeg (required for audio processing)
2. If FFmpeg is not found, it will offer to download and install it automatically
3. You'll be prompted to enter your Discord credentials
4. Once configured, you can start creating soundboard sounds!

## Features

- **YouTube to Soundboard**: Download and clip audio from YouTube URLs
- **Local File Upload**: Upload your own audio files
- **Audio Trimming**: Precise audio clipping with visual timeline
- **Sound Preview**: Test sounds before uploading
- **Sound Management**: View, play, edit, and delete existing sounds
- **Multi-Guild Support**: Manage sounds across multiple Discord servers

## Configuration

Your settings are saved in `config.json` in the application directory.
This file contains your Discord credentials (stored locally only).

## Troubleshooting

### Application won't start
- Make sure you're running the .exe from within the `DiscordSoundboardGenerator` folder
- Check Windows Defender or antivirus isn't blocking the application

### FFmpeg not found
- Allow the application to auto-install FFmpeg when prompted
- Alternatively, install FFmpeg manually and add it to your system PATH

### Discord API errors
- Verify your bot token is correct
- Ensure your bot has the required permissions
- Check that your bot is invited to the guild (server)

### Audio file too large
- Discord limits soundboard sounds to 512KB
- The application will automatically compress audio if needed
- For best quality, keep clips under 5 seconds

## Version

This is version {version} of the Discord Soundboard Generator.

## Support

For issues, bug reports, or feature requests:
https://github.com/YOUR_USERNAME/discord_soundboard_generator/issues

## License

See the main README.md for license information.
"""

    with open(dist_folder / 'DISTRIBUTION_README.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print(f"  Created DISTRIBUTION_README.txt for v{version}")

def main():
    """Main build process"""
    print("\n" + "="*60)
    print("  Discord Soundboard Generator - Versioned Build")
    print("="*60)

    # Step 1: Determine version
    next_version = get_next_version()
    print(f"\nBuilding version: v{next_version}\n")

    # Step 2: Clean old builds
    clean_build_dirs()

    # Step 3: Run PyInstaller
    if not run_pyinstaller():
        print("\n[ERROR] Build failed!")
        return 1

    # Step 4: Create distribution package
    if not create_distribution_package(next_version):
        print("\n[ERROR] Distribution packaging failed!")
        return 1

    # Step 5: Save the new version
    save_version(next_version)
    print(f"\n[OK] Version saved: v{next_version}")

    print_step("Build Complete!")
    print(f"[OK] Version: v{next_version}")
    print(f"[OK] Location: distributions/DiscordSoundboardGenerator_v{next_version}")
    print("[OK] You can now share this package with other users")

    return 0

if __name__ == '__main__':
    sys.exit(main())
