# Troubleshooting Guide - Discord Soundboard Generator

This guide addresses common issues when building or running the executable.

## Build Issues

### Missing Module Errors During Build

If PyInstaller fails with errors like:
```
ModuleNotFoundError: No module named 'xyz'
```

**Solution**: Install the missing module and add it to the spec file.

```bash
# Install the module
pip install xyz

# Add to discord_soundboard.spec in the hidden_imports list
hidden_imports = [
    # ... existing imports ...
    'xyz',  # Add the missing module
]

# Rebuild
make build
```

### PyInstaller Version Issues

If you get AST compilation errors:
```
TypeError: required field "value" missing from Constant
```

**Solution**: Upgrade PyInstaller to 6.16.0+

```bash
pip install --upgrade pyinstaller
make build
```

## Runtime Issues (Executable Won't Start)

### Missing pkg_resources Dependencies

**Symptoms:**
```
ModuleNotFoundError: No module named 'jaraco.text'
ModuleNotFoundError: No module named 'platformdirs'
```

**Root Cause**: These are dependencies of `pkg_resources` (setuptools) that PyInstaller doesn't automatically detect.

**Solution**: Already fixed in v1.0.2+. If you encounter new missing modules:

1. Install the missing package:
   ```bash
   pip install package-name
   ```

2. Add to `requirements.txt`:
   ```
   package-name>=version
   ```

3. Add to `discord_soundboard.spec` hidden imports:
   ```python
   hidden_imports = [
       # ... existing imports ...
       'package_name',
   ]
   ```

4. Add to `hook-pkg_resources.py`:
   ```python
   try:
       import package_name
   except ImportError:
       pass
   ```

5. Rebuild:
   ```bash
   make build
   ```

### Complete List of Required Build Dependencies

As of v1.0.2, these packages are required for building:

**Core Dependencies:**
- `python-dotenv==1.0.1`
- `requests==2.31.0`
- `yt-dlp>=2025.10.22`
- `pydub==0.25.1`
- `pygame==2.6.1`
- `audioop-lts==0.2.2`

**Build Dependencies (PyInstaller + pkg_resources):**
- `pyinstaller>=6.16.0`
- `jaraco.text>=4.0.0`
- `jaraco.functools>=4.3.0`
- `jaraco.context>=6.0.0`
- `more-itertools>=10.8.0`
- `platformdirs>=4.0.0`

**Install all at once:**
```bash
make install
# or
pip install -r requirements.txt
```

### Executable Crashes Immediately

**Symptoms**: Executable opens and closes immediately, no error message.

**Diagnosis**: Run from command line to see errors:
```bash
cd distributions/DiscordSoundboardGenerator_vX.X.X/DiscordSoundboardGenerator/
.\DiscordSoundboardGenerator.exe
```

**Common causes and solutions:**

1. **Missing DLLs**: Usually caught by PyInstaller, but if you get DLL errors:
   - Install Visual C++ Redistributables
   - Rebuild with `--collect-all package-name` in spec file

2. **Tkinter issues**: Tkinter should be bundled automatically
   - Verify Tkinter works in your Python: `python -m tkinter`
   - If fails, reinstall Python with Tcl/Tk support

3. **Path issues**: Application expects to run from specific directory
   - Always run from within the `DiscordSoundboardGenerator/` folder
   - Don't move the .exe outside its folder

### FFmpeg Installation Fails

**Symptoms**: Application starts but can't process YouTube videos.

**Solution**:
1. Download FFmpeg manually from https://ffmpeg.org/download.html
2. Extract `ffmpeg.exe` and `ffprobe.exe`
3. Place in a `ffmpeg/` folder next to the executable:
   ```
   DiscordSoundboardGenerator/
   ├── DiscordSoundboardGenerator.exe
   └── ffmpeg/
       ├── ffmpeg.exe
       └── ffprobe.exe
   ```

### Windows SmartScreen Warning

**Symptoms**: "Windows protected your PC" message when running.

**Why**: Unsigned executables trigger SmartScreen.

**Solutions**:
1. **For users**: Click "More info" → "Run anyway"
2. **For developers**:
   - Code sign with a certificate (costs money)
   - Build reputation over time
   - Users can add exception

## Configuration Issues

### Settings Don't Persist

**Symptoms**: Have to re-enter credentials every time.

**Causes**:
1. `config.json` isn't being created
2. Application doesn't have write permissions
3. Application is in a protected folder (like Program Files)

**Solutions**:
1. Check if `config.json` exists in the executable's folder
2. Run as administrator (once) to create the file
3. Move to a user folder (like Documents or Desktop)

### Discord API Errors

**Symptoms**: "Invalid token" or "Permission denied" errors.

**Solutions**:

1. **Invalid Token**:
   - Go to Discord Developer Portal
   - Bot section → Reset Token
   - Copy the NEW token
   - Update in Settings

2. **Permission Denied**:
   - Ensure bot has "Manage Guild Expressions" permission
   - Re-invite bot with correct permissions:
     ```
     https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot&permissions=1099511627776
     ```

3. **Bot not in server**:
   - Verify bot appears in server member list
   - Check bot is online (green status)

## Build System Issues

### "make: command not found"

**Cause**: Make isn't installed.

**Solutions**:

**Windows**:
```bash
# Option 1: Use build.bat instead
build.bat

# Option 2: Use Python directly
python build_versioned.py

# Option 3: Install Make via Chocolatey
choco install make

# Option 4: Use Git Bash (includes Make)
```

**macOS**:
```bash
# Install Xcode Command Line Tools
xcode-select --install
```

**Linux**:
```bash
sudo apt install make  # Debian/Ubuntu
sudo yum install make  # CentOS/RHEL
```

### Version Not Incrementing

**Expected**: Each build increments version (1.0.0 → 1.0.1 → 1.0.2)

**If it doesn't increment**:

1. Check if distribution folder exists:
   ```bash
   ls distributions/
   ```

2. Check `.version` file:
   ```bash
   cat .version
   ```

3. Manually set version if needed:
   ```bash
   echo "1.1.0" > .version
   make build
   ```

### Build Takes Too Long

**Normal build time**: 1-3 minutes (first build), 30-60 seconds (subsequent builds)

**If longer**:
1. PyInstaller caches modules - delete cache:
   ```bash
   make clean
   rm -rf ~/.pyinstaller/  # or C:\Users\YourName\.pyinstaller
   make build
   ```

2. Antivirus scanning: Add exclusions for:
   - Project directory
   - Python directory
   - Temp folder

## Python Environment Issues

### Wrong Python Version

**Required**: Python 3.13.3+

**Check version**:
```bash
python --version
```

**If wrong version**:
1. Install Python 3.13.3+ from python.org
2. Use specific Python version:
   ```bash
   py -3.13 -m pip install -r requirements.txt
   py -3.13 build_versioned.py
   ```

### Virtual Environment Issues

**Recommended**: Use a virtual environment to avoid conflicts.

```bash
# Create venv
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Build
make build
```

### Dependencies Conflict

**Symptoms**: "Requirement already satisfied but..." errors

**Solution**: Clean install

```bash
# Create fresh virtual environment
python -m venv venv_clean
venv_clean\Scripts\activate  # Windows
# or: source venv_clean/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Build
make build
```

## Distribution Issues

### Executable Too Large

**Normal size**: 8-12 MB (compressed), 40-60 MB (extracted)

**Includes**:
- Python interpreter (~5 MB)
- Tkinter (~3 MB)
- yt-dlp (~2 MB)
- pygame (~2 MB)
- Other dependencies

**To reduce size** (advanced):
1. Exclude unused packages in spec file
2. Use UPX compression (already enabled)
3. Remove debug symbols
4. Single-file executable (but slower startup)

Not recommended unless size is critical.

### Can't Share - File Too Big for Email

**Solutions**:
1. **Zip the folder**: Reduces size 50-70%
   ```bash
   cd distributions
   zip -r DiscordSoundboardGenerator_v1.0.2.zip DiscordSoundboardGenerator_v1.0.2/
   ```

2. **Use cloud storage**:
   - Google Drive
   - Dropbox
   - OneDrive
   - GitHub Releases (recommended for open source)

3. **Use GitHub Releases**:
   ```bash
   gh release create v1.0.2 \
     distributions/DiscordSoundboardGenerator_v1.0.2.zip \
     --title "Discord Soundboard Generator v1.0.2"
   ```

## Antivirus / Security Issues

### False Positive Detection

**Common**: PyInstaller executables often flagged as suspicious.

**Why**:
- Self-extracting behavior looks like malware
- Unsigned executable
- New/unknown file

**Solutions**:

1. **For developers**:
   - Code sign the executable (requires certificate, ~$100/year)
   - Submit to antivirus vendors for whitelisting
   - Build reputation over time

2. **For users**:
   - Add exception in antivirus
   - Check hash/signature from trusted source
   - Run in sandbox first if concerned

3. **Verify it's not actual malware**:
   - Build from source yourself
   - Check GitHub repository
   - Scan with multiple antivirus tools
   - Verify digital signature (if available)

## Still Having Issues?

### Diagnostic Information to Collect

When reporting issues, include:

1. **Python version**: `python --version`
2. **PyInstaller version**: `pip show pyinstaller`
3. **OS and version**: Windows 10/11, macOS version, Linux distro
4. **Full error message**: Copy entire traceback
5. **Build output**: Save output from `make build`
6. **What you've tried**: List troubleshooting steps attempted

### Getting Help

1. **Check documentation**:
   - `README.md` - Application usage
   - `BUILDING.md` - Build system details
   - This file - Troubleshooting

2. **Search issues**: Check if someone else had the same problem
   - GitHub Issues
   - PyInstaller issues
   - Stack Overflow

3. **Ask for help**:
   - Open a GitHub issue
   - Include diagnostic information
   - Describe what you expected vs what happened

### Emergency Workaround - Run Without Building

If you can't get the build to work, users can run the Python script directly:

```bash
# Install Python 3.13.3+
# Install dependencies
pip install -r requirements.txt

# Run directly
python main.py
```

Not ideal for distribution, but works in a pinch.

## Quick Reference

### Most Common Issues

1. **"No module named 'platformdirs'"** → Upgrade to v1.0.2+
2. **"make: command not found"** → Use `build.bat` or `python build_versioned.py`
3. **Windows SmartScreen** → Click "More info" → "Run anyway"
4. **FFmpeg fails** → Download manually to `ffmpeg/` folder
5. **Settings don't save** → Run as admin once or move to user folder

### Quick Fixes

```bash
# Fresh build from scratch
make clean
pip install -r requirements.txt
make build

# Test the executable
cd distributions/DiscordSoundboardGenerator_v1.0.X/DiscordSoundboardGenerator/
.\DiscordSoundboardGenerator.exe

# Check for errors
# (Run from command line to see error messages)
```

## Summary

Most issues are related to:
1. Missing Python packages (solution: `make install`)
2. PyInstaller compatibility (solution: upgrade to 6.16.0+)
3. pkg_resources dependencies (solution: already fixed in v1.0.2+)
4. Windows security warnings (solution: user adds exception)

The build system is designed to handle most cases automatically. If you encounter new issues, they're likely environment-specific and can be resolved by following the steps above.
