"""
FFmpeg Auto-Installer
Downloads and installs ffmpeg locally for the Discord Soundboard Generator
"""

import os
import sys
import zipfile
import urllib.request
import platform
from pathlib import Path


class FFmpegInstaller:
    """Downloads and installs ffmpeg for the current platform"""

    # FFmpeg download URLs for different platforms
    FFMPEG_URLS = {
        'Windows': 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',
        'Darwin': 'https://evermeet.cx/ffmpeg/ffmpeg-6.1.zip',  # macOS
        'Linux': None  # Linux users should install via package manager
    }

    def __init__(self, project_root: Path):
        """
        Initialize the FFmpeg installer

        Args:
            project_root: Path to the project root directory
        """
        self.project_root = project_root
        self.ffmpeg_dir = project_root / "ffmpeg"
        self.platform = platform.system()

    def is_ffmpeg_installed(self) -> bool:
        """
        Check if ffmpeg is already installed locally

        Returns:
            bool: True if ffmpeg exists in local ffmpeg directory
        """
        if not self.ffmpeg_dir.exists():
            return False

        # Check for required binaries based on platform
        if self.platform == 'Windows':
            return (self.ffmpeg_dir / "ffmpeg.exe").exists() and \
                   (self.ffmpeg_dir / "ffprobe.exe").exists()
        else:
            return (self.ffmpeg_dir / "ffmpeg").exists() and \
                   (self.ffmpeg_dir / "ffprobe").exists()

    def install(self, progress_callback=None) -> bool:
        """
        Download and install ffmpeg

        Args:
            progress_callback: Optional callback function for progress updates

        Returns:
            bool: True if installation successful, False otherwise
        """
        if self.is_ffmpeg_installed():
            if progress_callback:
                progress_callback("FFmpeg already installed")
            return True

        if self.platform not in self.FFMPEG_URLS or self.FFMPEG_URLS[self.platform] is None:
            if progress_callback:
                progress_callback(f"Auto-install not supported for {self.platform}")
            return False

        try:
            # Create ffmpeg directory
            self.ffmpeg_dir.mkdir(exist_ok=True)

            download_url = self.FFMPEG_URLS[self.platform]

            if progress_callback:
                progress_callback("Downloading FFmpeg...")

            # Download zip file
            zip_path = self.ffmpeg_dir / "ffmpeg_temp.zip"

            def download_progress(block_num, block_size, total_size):
                if progress_callback:
                    downloaded = block_num * block_size
                    percent = min(100, (downloaded / total_size) * 100)
                    progress_callback(f"Downloading: {percent:.1f}%")

            urllib.request.urlretrieve(download_url, zip_path, download_progress)

            if progress_callback:
                progress_callback("Extracting FFmpeg...")

            # Extract zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.ffmpeg_dir / "temp")

            # Find and move ffmpeg/ffprobe to ffmpeg directory
            temp_dir = self.ffmpeg_dir / "temp"
            if self.platform == 'Windows':
                self._extract_windows_binaries(temp_dir)
            else:
                self._extract_unix_binaries(temp_dir)

            # Clean up
            if progress_callback:
                progress_callback("Cleaning up...")

            zip_path.unlink()
            self._remove_directory(temp_dir)

            if progress_callback:
                progress_callback("FFmpeg installation complete!")

            return True

        except Exception as e:
            if progress_callback:
                progress_callback(f"Installation failed: {str(e)}")
            return False

    def _extract_windows_binaries(self, temp_dir: Path):
        """Extract ffmpeg and ffprobe from Windows zip structure"""
        # Windows builds typically have structure: ffmpeg-xxx/bin/ffmpeg.exe
        for root, dirs, files in os.walk(temp_dir):
            root_path = Path(root)
            for file in files:
                if file in ['ffmpeg.exe', 'ffprobe.exe']:
                    source = root_path / file
                    dest = self.ffmpeg_dir / file
                    source.rename(dest)

    def _extract_unix_binaries(self, temp_dir: Path):
        """Extract ffmpeg and ffprobe from Unix/Mac zip structure"""
        for root, dirs, files in os.walk(temp_dir):
            root_path = Path(root)
            for file in files:
                if file in ['ffmpeg', 'ffprobe']:
                    source = root_path / file
                    dest = self.ffmpeg_dir / file
                    source.rename(dest)
                    # Make executable
                    dest.chmod(0o755)

    def _remove_directory(self, directory: Path):
        """Recursively remove a directory"""
        if not directory.exists():
            return

        for item in directory.iterdir():
            if item.is_dir():
                self._remove_directory(item)
            else:
                item.unlink()
        directory.rmdir()

    def show_manual_install_instructions(self):
        """Show instructions for manual installation"""
        if self.platform == 'Linux':
            return """
FFmpeg Auto-Install Not Available for Linux

Please install FFmpeg using your package manager:

Ubuntu/Debian:
  sudo apt update
  sudo apt install ffmpeg

Fedora:
  sudo dnf install ffmpeg

Arch Linux:
  sudo pacman -S ffmpeg

After installation, restart the application.
"""
        elif self.platform == 'Windows':
            return """
FFmpeg Auto-Install Failed

Please install FFmpeg manually:

1. Download FFmpeg from: https://ffmpeg.org/download.html
2. Extract ffmpeg.exe and ffprobe.exe
3. Place them in: {0}
4. Restart the application

Or install system-wide and add to PATH.
""".format(self.ffmpeg_dir)

        elif self.platform == 'Darwin':  # macOS
            return """
FFmpeg Auto-Install Failed

Please install FFmpeg manually:

Using Homebrew (recommended):
  brew install ffmpeg

Or download from: https://ffmpeg.org/download.html
And place binaries in: {0}

After installation, restart the application.
""".format(self.ffmpeg_dir)

        return "Please install FFmpeg manually for your platform."


def check_and_install_ffmpeg(project_root: Path = None, progress_callback=None) -> bool:
    """
    Check if ffmpeg is installed and install if missing

    Args:
        project_root: Path to project root (defaults to parent of this file)
        progress_callback: Optional callback for progress updates

    Returns:
        bool: True if ffmpeg is available, False otherwise
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent

    installer = FFmpegInstaller(project_root)

    if installer.is_ffmpeg_installed():
        if progress_callback:
            progress_callback("FFmpeg already installed")
        return True

    if progress_callback:
        progress_callback("FFmpeg not found. Attempting to install...")

    success = installer.install(progress_callback)

    if not success:
        if progress_callback:
            progress_callback(installer.show_manual_install_instructions())

    return success


if __name__ == "__main__":
    """Run installer standalone"""
    def print_progress(message):
        print(message)

    project_root = Path(__file__).parent.parent
    success = check_and_install_ffmpeg(project_root, print_progress)

    if success:
        print("\n✓ FFmpeg is ready!")
        sys.exit(0)
    else:
        print("\n✗ FFmpeg installation failed")
        sys.exit(1)
