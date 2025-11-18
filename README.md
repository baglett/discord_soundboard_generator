# Discord Soundboard Generator

A Python tool to create and manage soundboard sounds on Discord using the Discord API.

## Features

- Create individual soundboard sounds from YouTube, Instagram, Facebook, or local files
- Extract audio from YouTube videos with custom trim ranges
- Extract audio from Instagram posts and reels (including multi-slide carousel posts)
- Extract audio from Facebook reels
- Automatic audio detection and slide filtering for Instagram carousels
- Interactive GUI wizard for easy sound creation
- Bulk upload sounds from a directory
- List all soundboard sounds in a guild
- Update existing soundboard sounds
- Delete soundboard sounds
- Reusable Discord authentication class

## Requirements

- Python 3.13.3 or higher
- Discord bot with appropriate permissions
- Audio files in MP3 or OGG format (max 512kb each)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd discord_soundboard_generator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install ffmpeg (required for YouTube audio processing):

**Option A: Local installation (recommended)**
- Download ffmpeg from https://ffmpeg.org/download.html
- Extract `ffmpeg.exe` and `ffprobe.exe` to a `ffmpeg/` folder in the project root
- The application will automatically detect and use the local ffmpeg

**Option B: System-wide installation**
- Download and install ffmpeg to your system PATH
- The application will use the system ffmpeg if no local installation is found

4. Configure Discord credentials:

**Option A: Use the GUI Settings (Recommended)**
- Launch the application with `python main.py`
- On first run, you'll be prompted to configure Discord settings
- Enter your bot token, application ID, and guild ID in the settings dialog
- Settings are saved to `config.json` (automatically created)

**Option B: Use .env file (For development)**
- Copy `sample.env` to `.env`
- Edit `.env` and add your credentials:
```env
DISCORD_API_KEY=your_bot_token_here
DISCORD_APPLICATION_ID=your_application_id_here
DISCORD_GUILD_ID=your_server_id_here
```

**Note**: The application prioritizes `.env` over `config.json` for local development.

## Getting Your Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application or select an existing one
3. Go to the "Bot" section
4. Click "Reset Token" to get your bot token
5. Copy the token to your `.env` file

## Required Bot Permissions

Your Discord bot needs the following permissions:
- **Create Expressions** - To create soundboard sounds
- **Manage Expressions** - To update/delete soundboard sounds

Invite your bot with this permission integer: `274877925376` or use the OAuth2 URL Generator in the Discord Developer Portal.

## Usage

### Launching the Application

Run the main script:
```bash
python main.py
```

**Startup Process:**
1. A **startup window** appears showing initialization progress
2. The application automatically checks for ffmpeg installation
3. Progress updates are displayed in real-time:
   - "Checking for ffmpeg installation..."
   - "Downloading FFmpeg..." (if needed)
   - "Extracting FFmpeg..." (if downloading)
   - "FFmpeg installation complete!" or "FFmpeg already installed"
4. Once initialization is complete, the main GUI launches automatically

**First Run (no ffmpeg):**
- FFmpeg will be automatically downloaded and installed (Windows/macOS)
- Progress is shown in the startup window
- Linux users will see instructions to install via package manager
- Typical download/install takes 30-60 seconds

**Subsequent Runs:**
- Startup window appears briefly
- FFmpeg check completes instantly (already installed)
- Main GUI launches immediately

### Using the GUI

The GUI provides an intuitive interface with multiple tabs:

**Create Sound Wizard Tab:**
1. **Step 1: Source Selection**
   - Choose between "YouTube / Instagram / Facebook" or "Local File"
   - For online sources:
     - Paste a YouTube video URL (youtube.com/watch?v=... or youtu.be/...)
     - OR paste an Instagram post/reel URL (instagram.com/p/... or instagram.com/reel/...)
     - OR paste a Facebook reel URL (facebook.com/share/r/... or facebook.com/reel/...)
     - The app automatically detects which platform you're using
   - For local files:
     - Browse and select an MP3 file from your computer
   - Enter a Discord sound name
   - Click "Next" to proceed

2. **Step 2: Preview & Trim**
   - **For YouTube/Instagram/Facebook**: Audio is automatically downloaded
   - **For Instagram carousels**: Select which slide to use (only slides with audio are shown)
   - Use the trim sliders to select a 1.0s - 5.2s audio clip
   - Click "Generate Preview" to create the clip
   - Click "▶ Play Preview" to listen before publishing
   - Click "Publish to Discord" when ready

**Instagram Features:**
- Automatically detects Instagram posts and reels
- For carousel posts (multiple slides):
  - Shows thumbnails of each slide
  - Filters out slides without audio
  - Displays duration for each slide
  - Select which slide to extract audio from
- Error handling for:
  - Private posts (prompts to use public posts)
  - Rate limits (asks to retry later)
  - Posts without audio

**Facebook Features:**
- Automatically detects Facebook reels and videos
- Supports multiple URL formats:
  - Share links: facebook.com/share/r/...
  - Direct reel links: facebook.com/reel/...
  - Watch links: facebook.com/watch/?v=...
  - Short links: fb.watch/...
- Error handling for:
  - Private reels (prompts to use public reels)
  - Rate limits (asks to retry later)
  - Videos without audio

**YouTube to Sound Tab (Legacy):**
1. Enter a sound name for the temporary file
2. Paste a YouTube video URL
3. Set start and end timestamps (MM:SS format)
4. Click "Create Preview" to download and clip the audio
5. Click "Play Preview" to listen before uploading
6. Fill in the Discord sound details (name, guild, volume, emoji)
7. Click "Upload to Discord" to publish the sound

**Bulk Upload Tab:**
- Select a guild
- Choose a directory containing MP3/OGG files
- Set volume
- Click "Upload All" to bulk upload

**Manage Sounds Tab:**
- Select a guild
- Click "Load Sounds" to view all soundboard sounds
- Select a sound and click "Delete Selected" to remove it

**Settings & Info Tab:**
- **Configure Discord Settings**: Click the "⚙ Configure Discord Settings" button to manage credentials
  - Discord Bot Token (obfuscated by default)
  - Discord Application ID (obfuscated by default)
  - Discord Guild ID (obfuscated by default)
  - Click the eye icon (👁) to show/hide values
  - Settings are saved to `config.json`
- View bot information and connected guilds
- Refresh bot information

### Programmatic Usage (Advanced)

You can also use the library programmatically:

```python
from discord_auth import DiscordAuth
from discord_soundboard import SoundboardManager

# Initialize
discord = DiscordAuth()
soundboard = SoundboardManager(discord)

# Create a sound
sound = soundboard.create_soundboard_sound(
    guild_id="YOUR_GUILD_ID",
    name="Epic Sound",
    sound_file_path="path/to/sound.mp3",
    volume=1.0,
    emoji_name="😎"
)
print(f"Created: {sound['name']}")
```

### Bulk Upload from Directory

```python
# Upload all MP3/OGG files from a directory
created_sounds = soundboard.bulk_create_sounds(
    guild_id="YOUR_GUILD_ID",
    sounds_directory="path/to/sounds/folder",
    volume=0.8,
    name_from_filename=True
)
print(f"Uploaded {len(created_sounds)} sounds!")
```

### List All Soundboard Sounds

```python
sounds = soundboard.list_soundboard_sounds(guild_id="YOUR_GUILD_ID")
for sound in sounds:
    print(f"- {sound['name']} (ID: {sound['sound_id']}, Volume: {sound['volume']})")
```

### Update a Soundboard Sound

```python
updated = soundboard.update_soundboard_sound(
    guild_id="YOUR_GUILD_ID",
    sound_id="SOUND_ID",
    name="New Name",
    volume=0.5,
    emoji_name="<�"
)
```

### Delete a Soundboard Sound

```python
soundboard.delete_soundboard_sound(
    guild_id="YOUR_GUILD_ID",
    sound_id="SOUND_ID"
)
```

## Audio File Requirements

- **Formats**: MP3 or OGG
- **Max Size**: 512kb per file
- **Name Length**: 2-32 characters
- **Volume**: 0.0 to 1.0

## File Structure

```
discord_soundboard_generator/
├── main.py                          [IN-USE] - Main entry point; launches startup window, checks FFmpeg, then opens GUI
├── gui_wizard.py                    [IN-USE] - Modern wizard-style GUI with tabbed interface for creating/managing sounds
├── gui.py                           [IN-USE] - Legacy GUI implementation (kept for backward compatibility)
├── startup_window.py                [IN-USE] - Startup splash screen with progress updates during initialization
├── discord_auth.py                  [IN-USE] - Discord API authentication and HTTP request wrapper class
├── discord_soundboard.py            [IN-USE] - Core soundboard management (create/list/update/delete sounds)
├── youtube_to_sound.py              [IN-USE] - YouTube audio downloader and clipper using yt-dlp
├── instagram_scraper.py             [IN-USE] - Instagram post/reel audio scraper with carousel support
├── facebook_scraper.py              [IN-USE] - Facebook reel audio scraper and downloader
├── config_manager.py                [IN-USE] - Configuration management for Discord credentials (.env and config.json)
├── settings_dialog.py               [IN-USE] - GUI settings dialog for managing Discord credentials
├── emoji_picker.py                  [IN-USE] - Searchable emoji picker component for Discord-compatible emojis
├── build.py                         [IN-USE] - Build script for creating distributable .exe (basic version)
├── build_versioned.py               [IN-USE] - Advanced versioned build script with auto-incrementing version numbers
├── discord_soundboard.spec          [IN-USE] - PyInstaller specification for bundling the application
├── Makefile                         [IN-USE] - Cross-platform build automation (build, clean, install, release)
├── requirements.txt                 [IN-USE] - Python package dependencies
├── sample.env                       [IN-USE] - Template for environment variables
├── README.md                        [IN-USE] - This file; comprehensive project documentation
├── .gitignore                       [IN-USE] - Git ignore rules for sensitive files and build artifacts
├── hook-pkg_resources.py            [IN-USE] - PyInstaller runtime hook for pkg_resources compatibility
├── test_facebook.py                 [IN-USE] - Test suite for Facebook scraper functionality
│
├── setup/                           [IN-USE] - Setup and installation utilities
│   ├── __init__.py                  [IN-USE] - Package initialization
│   └── ffmpeg_installer.py          [IN-USE] - Auto-downloads and installs FFmpeg for Windows/macOS
│
├── sounds/                          [IN-USE] - Directory for storing downloaded audio files (created at runtime)
│   └── (audio files stored here during operation)
│
├── distributions/                   [NOT CREATED YET] - Generated by build scripts; contains versioned .exe packages
│   └── DiscordSoundboardGenerator_vX.X.X/
│       ├── DiscordSoundboardGenerator/
│       │   └── DiscordSoundboardGenerator.exe
│       ├── README.md
│       ├── sample.env
│       └── DISTRIBUTION_README.txt
│
├── ffmpeg/                          [NOT CREATED YET] - Created by FFmpeg installer; contains ffmpeg binaries
│   ├── ffmpeg.exe                   [AUTO-INSTALLED] - FFmpeg binary for audio processing
│   └── ffprobe.exe                  [AUTO-INSTALLED] - FFprobe binary for media information
│
├── build/                           [NOT-USED] - Temporary PyInstaller build artifacts (auto-generated, git-ignored)
├── dist/                            [NOT-USED] - PyInstaller output directory (auto-generated, git-ignored)
├── .env                             [NOT-USED] - User-created environment variables file (git-ignored, optional)
├── config.json                      [NOT-USED] - User configuration file (auto-created by app, git-ignored)
└── .version                         [NOT-USED] - Version tracking file for build system (auto-generated)
```

### File Status Legend
- **IN-USE**: File is actively used by the application
- **NOT CREATED YET**: Directory/file is created during build process or first run
- **AUTO-INSTALLED**: File is automatically downloaded/created by the application
- **NOT-USED**: Temporary, generated, or optional user-created files
discord_soundboard_generator/
   discord_auth.py          # Discord API authentication class
   discord_soundboard.py    # Soundboard management class
   main.py                  # Main entry point
   requirements.txt         # Python dependencies
   sample.env              # Environment variable template
   .env                    # Your actual environment variables (git-ignored)
   README.md               # This file
```

## API Reference

### DiscordAuth Class

```python
DiscordAuth(token: Optional[str] = None)
```

Methods:
- `get(endpoint, params)` - Make GET request
- `post(endpoint, data)` - Make POST request
- `put(endpoint, data)` - Make PUT request
- `patch(endpoint, data)` - Make PATCH request
- `delete(endpoint)` - Make DELETE request
- `get_bot_info()` - Get bot information
- `get_guilds()` - Get list of guilds

### SoundboardManager Class

```python
SoundboardManager(discord_auth: DiscordAuth)
```

Methods:
- `create_soundboard_sound(guild_id, name, sound_file_path, volume, emoji_id, emoji_name)` - Create a sound
- `list_soundboard_sounds(guild_id)` - List all sounds
- `get_soundboard_sound(guild_id, sound_id)` - Get specific sound
- `update_soundboard_sound(guild_id, sound_id, name, volume, emoji_id, emoji_name)` - Update a sound
- `delete_soundboard_sound(guild_id, sound_id)` - Delete a sound
- `bulk_create_sounds(guild_id, sounds_directory, volume, name_from_filename)` - Bulk upload

## Error Handling

The library raises specific exceptions:
- `ValueError` - Invalid parameters or missing files
- `PermissionError` - Bot lacks required permissions
- `requests.RequestException` - API request failures

## Common Issues

### "Invalid Discord API token"
- Make sure you copied the token correctly
- Ensure there are no extra spaces in your `.env` file
- Try resetting your bot token in the Developer Portal

### "Bot lacks permission to create soundboard sounds"
- Reinvite your bot with the "Create Expressions" permission
- Check that the bot has the permission in your specific server

### "File size exceeds Discord limit"
- Audio files must be under 512kb
- Use audio compression tools to reduce file size
- Consider converting to OGG format for better compression

## Building Distributable Executable

You can build a standalone executable for distribution to users who don't have Python installed.

### Prerequisites

1. Install PyInstaller (included in requirements.txt):
```bash
pip install -r requirements.txt
```

### Build Process

**Using Make (Recommended):**
```bash
make build
```

**Alternative methods:**

Windows:
```bash
build.bat
```

Python directly:
```bash
python build_versioned.py
```

### What Happens During Build

1. **Version Check**: Determines the next version number automatically
2. **Cleanup**: Removes old build artifacts from `build/` and `dist/`
3. **PyInstaller**: Bundles the application with all dependencies
4. **Packaging**: Creates a versioned distribution package in `distributions/` folder
5. **Documentation**: Includes README and setup instructions

### Version Management

The build system automatically manages versions:
- First build creates `v1.0.0`
- Subsequent builds increment patch version: `v1.0.1`, `v1.0.2`, etc.
- Version is stored in `.version` file
- No timestamps - clean version numbers only

Check current version:
```bash
make version
```

### Distribution Package Contents

After building, you'll find in `distributions/`:
```
DiscordSoundboardGenerator_v1.0.X/
├── DiscordSoundboardGenerator/     # The executable application
│   ├── DiscordSoundboardGenerator.exe
│   ├── All bundled dependencies
│   └── sounds/                     # Empty template folder
├── README.md                       # Original README
├── sample.env                      # Credentials template
└── DISTRIBUTION_README.txt         # End-user instructions
```

Where `X` is automatically incremented for each build.

### Distributing to Users

Users can:
1. Download and extract the package
2. Run `DiscordSoundboardGenerator.exe`
3. Enter their Discord credentials on first launch
4. Start creating soundboard sounds immediately

**No Python installation required!**
**FFmpeg is bundled - no additional downloads needed!**

### Build Configuration

The build process is controlled by:
- `discord_soundboard.spec` - PyInstaller specification file
- `build.py` - Automated build script
- `build.bat` - Windows convenience wrapper

To customize the build (e.g., add an icon), edit `discord_soundboard.spec`:
```python
exe = EXE(
    ...
    icon='icon.ico',  # Add your icon here
    ...
)
```

### Troubleshooting Build Issues

**"PyInstaller not found"**
- Run: `pip install pyinstaller`

**"Build succeeds but exe won't run"**
- Check antivirus settings (may block the executable)
- Try running from the `dist/DiscordSoundboardGenerator/` folder
- Check for missing dependencies in the spec file

**"Application crashes on startup"**
- Ensure all hidden imports are listed in the spec file
- Test with `--debug=all` flag for detailed error messages

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

MIT License - See LICENSE file for details

## Configuration Files

- **config.json**: Stores Discord credentials (created automatically by the app)
  - Contains: discord_api_key, discord_application_id, discord_guild_id
  - Git-ignored for security
  - Managed through the GUI settings dialog

- **.env**: Optional environment file for development
  - Takes priority over config.json
  - Useful for local development and testing
  - Git-ignored for security
