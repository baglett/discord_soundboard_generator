"""
YouTube to Discord Soundboard Converter
Downloads and clips audio from YouTube videos for Discord soundboard use
"""

import os
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import yt_dlp
from pydub import AudioSegment
from pydub.playback import play
import pygame
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, COMM, TIT2, TPE1
from discord_soundboard import SoundboardManager


class YouTubeToSound:
    """
    Converts YouTube videos to Discord soundboard sounds

    Downloads audio from YouTube, clips it to specified timestamps,
    and uploads to Discord as a soundboard sound.
    """

    def __init__(self, soundboard_manager: SoundboardManager, output_dir: str = "sounds"):
        """
        Initialize the YouTubeToSound converter

        Args:
            soundboard_manager (SoundboardManager): Discord soundboard manager instance
            output_dir (str): Directory to save audio files (default: "sounds")
        """
        self.soundboard = soundboard_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Check for local ffmpeg installation and configure pydub
        local_ffmpeg_dir = Path(__file__).parent / "ffmpeg"
        if local_ffmpeg_dir.exists():
            # Add ffmpeg directory to PATH so pydub can find it
            local_ffmpeg_dir_abs = local_ffmpeg_dir.absolute()
            if str(local_ffmpeg_dir_abs) not in os.environ.get('PATH', ''):
                os.environ['PATH'] = str(local_ffmpeg_dir_abs) + os.pathsep + os.environ.get('PATH', '')
                print(f"Added ffmpeg directory to PATH: {local_ffmpeg_dir_abs}")

            # Set ffmpeg/ffprobe paths for pydub
            ffmpeg_path = local_ffmpeg_dir / "ffmpeg.exe"
            ffprobe_path = local_ffmpeg_dir / "ffprobe.exe"
            if ffmpeg_path.exists():
                AudioSegment.converter = str(ffmpeg_path.absolute())
                print(f"Set AudioSegment.converter to: {AudioSegment.converter}")
            if ffprobe_path.exists():
                AudioSegment.ffprobe = str(ffprobe_path.absolute())
                print(f"Set AudioSegment.ffprobe to: {AudioSegment.ffprobe}")

        # Initialize pygame mixer for audio playback
        pygame.mixer.init()

    def _parse_timestamp(self, timestamp: str) -> int:
        """
        Parse timestamp string to milliseconds

        Supports formats:
        - "MM:SS.mmm" (e.g., "1:30.500" or "1:30")
        - "HH:MM:SS.mmm" (e.g., "1:23:45.123" or "1:23:45")
        - "SS.mmm" (e.g., "90.500" or "90")

        Args:
            timestamp (str): Timestamp string

        Returns:
            int: Timestamp in milliseconds

        Raises:
            ValueError: If timestamp format is invalid
        """
        timestamp = timestamp.strip()

        # Try HH:MM:SS or HH:MM:SS.mmm format
        if timestamp.count(':') == 2:
            match = re.match(r'^(\d+):(\d+):(\d+(?:\.\d+)?)$', timestamp)
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                seconds = float(match.group(3))
                return int((hours * 3600 + minutes * 60 + seconds) * 1000)

        # Try MM:SS or MM:SS.mmm format
        elif timestamp.count(':') == 1:
            match = re.match(r'^(\d+):(\d+(?:\.\d+)?)$', timestamp)
            if match:
                minutes = int(match.group(1))
                seconds = float(match.group(2))
                return int((minutes * 60 + seconds) * 1000)

        # Try seconds only (SS or SS.mmm)
        else:
            match = re.match(r'^(\d+(?:\.\d+)?)$', timestamp)
            if match:
                seconds = float(match.group(1))
                return int(seconds * 1000)

        raise ValueError(f"Invalid timestamp format: {timestamp}. Use MM:SS or HH:MM:SS or SS (decimals supported)")

    def _validate_youtube_url(self, youtube_url: str) -> None:
        """
        Validate that the URL is a direct YouTube video URL, not a search/playlist

        Args:
            youtube_url (str): YouTube URL to validate

        Raises:
            ValueError: If URL is not a valid direct video URL
        """
        # Check for search URLs
        if '/results?' in youtube_url or 'search_query=' in youtube_url:
            raise ValueError(
                "Please provide a direct YouTube video URL, not a search URL.\n"
                "Search URLs look like: youtube.com/results?search_query=...\n"
                "Video URLs look like: youtube.com/watch?v=... or youtu.be/..."
            )

        # Check for playlist URLs (unless it's a specific video in a playlist)
        if '/playlist?' in youtube_url and '&v=' not in youtube_url:
            raise ValueError(
                "Please provide a direct YouTube video URL, not a playlist URL.\n"
                "To use a video from a playlist, use the direct video link instead."
            )

        # Basic validation for YouTube domain
        valid_domains = ['youtube.com', 'youtu.be', 'www.youtube.com', 'm.youtube.com']
        if not any(domain in youtube_url for domain in valid_domains):
            raise ValueError(
                "Please provide a valid YouTube URL.\n"
                "Valid formats: youtube.com/watch?v=..., youtu.be/..., or youtube.com/shorts/..."
            )

    def _add_youtube_metadata(self, mp3_path: str, youtube_url: str, video_title: str = "") -> None:
        """
        Add YouTube URL and video info to MP3 metadata

        Args:
            mp3_path (str): Path to MP3 file
            youtube_url (str): YouTube video URL
            video_title (str): Video title (optional)
        """
        try:
            # Load or create ID3 tag
            try:
                audio = MP3(mp3_path, ID3=ID3)
                audio.add_tags()
            except:
                audio = MP3(mp3_path)

            # Add YouTube URL as a comment
            audio.tags.add(COMM(encoding=3, lang='eng', desc='youtube_url', text=youtube_url))

            # Add video title if provided
            if video_title:
                audio.tags.add(TIT2(encoding=3, text=video_title))

            audio.save()
            print(f"✓ Added YouTube metadata to {mp3_path}")
        except Exception as e:
            print(f"Warning: Failed to add metadata to {mp3_path}: {e}")

    def _get_youtube_url_from_metadata(self, mp3_path: str) -> Optional[str]:
        """
        Extract YouTube URL from MP3 metadata

        Args:
            mp3_path (str): Path to MP3 file

        Returns:
            Optional[str]: YouTube URL if found, None otherwise
        """
        try:
            audio = MP3(mp3_path, ID3=ID3)

            # Look for youtube_url comment
            for frame in audio.tags.getall('COMM'):
                if frame.desc == 'youtube_url':
                    return frame.text[0] if frame.text else None

            return None
        except Exception as e:
            return None

    def find_existing_download(self, youtube_url: str) -> Optional[str]:
        """
        Search for an existing full download of a YouTube video by URL

        Args:
            youtube_url (str): YouTube video URL to search for

        Returns:
            Optional[str]: Path to existing MP3 file if found, None otherwise
        """
        # Search through all MP3 files in output directory
        for mp3_file in self.output_dir.glob("*_full.mp3"):
            stored_url = self._get_youtube_url_from_metadata(str(mp3_file))
            if stored_url and stored_url.strip() == youtube_url.strip():
                print(f"✓ Found existing download: {mp3_file.name}")
                return str(mp3_file.absolute())

        return None

    def get_video_info(self, youtube_url: str) -> Dict[str, Any]:
        """
        Get video information without downloading

        Args:
            youtube_url (str): YouTube video URL

        Returns:
            Dict with 'duration' (in seconds), 'title', 'video_id', etc.

        Raises:
            ValueError: If URL is invalid
            Exception: If info extraction fails
        """
        self._validate_youtube_url(youtube_url)

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)

                if info is None:
                    raise Exception("No video information retrieved")

                return {
                    'duration': info.get('duration', 0),  # Duration in seconds
                    'title': info.get('title', 'Unknown'),
                    'video_id': info.get('id', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', 'Unknown'),
                }

        except Exception as e:
            raise Exception(f"Failed to get video info: {str(e)}")

    def _download_audio(self, youtube_url: str, output_filename: str, check_existing: bool = True) -> str:
        """
        Download audio from YouTube video (or reuse existing download)

        Args:
            youtube_url (str): YouTube video URL (must be a direct video link)
            output_filename (str): Filename for downloaded audio (without extension)
            check_existing (bool): Check for existing downloads first (default: True)

        Returns:
            str: Path to downloaded audio file

        Raises:
            ValueError: If URL is invalid (search URL, playlist, etc.)
            Exception: If download fails
        """
        # Validate URL first
        self._validate_youtube_url(youtube_url)

        # Check for existing download if requested
        if check_existing and "_full" in output_filename:
            existing_path = self.find_existing_download(youtube_url)
            if existing_path:
                print(f"✓ Reusing existing download (no need to re-download)")
                return existing_path

        # Use absolute path for output to avoid path resolution issues
        output_path = str((self.output_dir / output_filename).absolute())

        # Check for local ffmpeg installation first
        local_ffmpeg_dir = Path(__file__).parent / "ffmpeg"

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
            'noplaylist': True,  # Don't download playlists, only single videos
        }

        # If local ffmpeg exists, use it
        if local_ffmpeg_dir.exists():
            ydl_opts['ffmpeg_location'] = str(local_ffmpeg_dir.absolute())

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"Downloading audio from: {youtube_url}")
                info = ydl.extract_info(youtube_url, download=True)

                # Check if download was successful
                if info is None:
                    raise Exception("No video information retrieved. The URL may be invalid or unavailable.")

                video_title = info.get('title', 'Unknown title')
                print(f"Downloaded: {video_title}")

            # yt-dlp adds .mp3 extension
            output_file = f"{output_path}.mp3"
            if not os.path.exists(output_file):
                raise Exception(f"Download completed but output file not found: {output_file}")

            # Give the system a moment to release file handles after yt-dlp finishes
            time.sleep(0.5)

            # Add YouTube URL metadata to the file (for _full versions)
            if "_full" in output_filename:
                self._add_youtube_metadata(output_file, youtube_url, video_title)

            return output_file

        except ValueError as e:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            raise Exception(f"Failed to download YouTube audio: {str(e)}")

    def _clip_audio(
        self,
        audio_path: str,
        start_time: str,
        end_time: str,
        output_filename: str
    ) -> str:
        """
        Clip audio file to specified time range

        Args:
            audio_path (str): Path to input audio file
            start_time (str): Start timestamp (e.g., "1:30")
            end_time (str): End timestamp (e.g., "1:45")
            output_filename (str): Filename for clipped audio

        Returns:
            str: Path to clipped audio file

        Raises:
            ValueError: If timestamps are invalid
        """
        # Parse timestamps to milliseconds
        start_ms = self._parse_timestamp(start_time)
        end_ms = self._parse_timestamp(end_time)

        if start_ms >= end_ms:
            raise ValueError(f"Start time ({start_time}) must be before end time ({end_time})")

        # Load audio file with retry logic for Windows file locking
        print(f"Loading audio file: {audio_path}")
        max_attempts = 5
        audio = None

        for attempt in range(max_attempts):
            try:
                audio = AudioSegment.from_file(audio_path)
                break
            except (PermissionError, OSError) as e:
                print(f"Error attempting to load audio file: {e}")
                print(f"Error type: {type(e).__name__}")
                print(f"File exists: {os.path.exists(audio_path)}")
                print(f"File path: {audio_path}")

                # Check if it's a file locking error (WinError 32)
                if "[WinError 32]" in str(e) or "being used by another process" in str(e) or isinstance(e, PermissionError):
                    if attempt < max_attempts - 1:
                        print(f"File locked, retrying... (attempt {attempt + 1}/{max_attempts})")
                        time.sleep(0.5 * (attempt + 1))  # Progressive delay
                    else:
                        raise ValueError(f"Could not access audio file after {max_attempts} attempts. File may be locked by another process.")
                else:
                    # Different error, re-raise immediately
                    raise

        if audio is None:
            raise ValueError(f"Failed to load audio file: {audio_path}")

        # Check if timestamps are within audio duration
        duration_ms = len(audio)
        if end_ms > duration_ms:
            raise ValueError(
                f"End time ({end_time}) exceeds audio duration "
                f"({duration_ms / 1000:.2f} seconds)"
            )

        # Clip audio
        print(f"Clipping audio from {start_time} to {end_time}")
        clipped = audio[start_ms:end_ms]

        # Calculate clipped duration
        clip_duration = (end_ms - start_ms) / 1000
        print(f"Clip duration: {clip_duration:.2f} seconds")

        # Check if clipped audio is too large for Discord (512kb limit)
        # Reduce quality if necessary
        output_path = str(self.output_dir / output_filename)

        # Try different bitrates to get under 512kb
        max_size_bytes = 512 * 1024  # 512kb
        bitrates = ['128k', '96k', '64k', '48k', '32k']

        for bitrate in bitrates:
            temp_path = output_path
            clipped.export(
                temp_path,
                format='mp3',
                bitrate=bitrate,
                parameters=["-ac", "1"]  # Convert to mono to save space
            )

            # Give the system a moment to release file handles after export
            time.sleep(0.3)

            file_size = os.path.getsize(temp_path)
            print(f"Exported at {bitrate} bitrate: {file_size / 1024:.2f} KB")

            if file_size <= max_size_bytes:
                return temp_path

        # If still too large, raise error
        raise ValueError(
            f"Clipped audio is too large even at lowest quality. "
            f"Try a shorter clip duration (current: {clip_duration:.2f}s)"
        )

    def _play_audio(self, audio_path: str) -> None:
        """
        Play an audio file using pygame mixer

        Args:
            audio_path (str): Path to audio file to play
        """
        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()

            print("\n▶ Playing audio preview... (Press Enter to stop)")

            # Wait for audio to finish or user to press Enter
            while pygame.mixer.music.get_busy():
                # Check if user pressed Enter (non-blocking)
                import msvcrt
                if msvcrt.kbhit():
                    if msvcrt.getch() in [b'\r', b'\n']:
                        pygame.mixer.music.stop()
                        print("⏹ Playback stopped")
                        break
                time.sleep(0.1)
            else:
                print("✓ Playback finished")

        except Exception as e:
            print(f"Error playing audio: {e}")

    def create_preview_clip(
        self,
        youtube_url: str,
        start_time: str,
        end_time: str,
        preview_name: str = "preview"
    ) -> Tuple[str, str]:
        """
        Download YouTube audio and create a preview clip (without uploading to Discord)

        Args:
            youtube_url (str): YouTube video URL
            start_time (str): Start timestamp (e.g., "1:30" or "0:45")
            end_time (str): End timestamp (e.g., "1:45" or "1:00")
            preview_name (str): Name for preview files (default: "preview")

        Returns:
            Tuple[str, str]: (downloaded_file_path, clipped_file_path)

        Raises:
            ValueError: If parameters are invalid
            Exception: If download or clipping fails
        """
        # Create safe filename
        safe_filename = re.sub(r'[^\w\s-]', '', preview_name).strip().replace(' ', '_')

        # Download audio
        temp_download = f"{safe_filename}_full"
        try:
            downloaded_path = self._download_audio(youtube_url, temp_download)
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")

        # Clip audio
        clipped_filename = f"{safe_filename}.mp3"
        try:
            print(f"Clipping: {downloaded_path} -> {clipped_filename}")
            clipped_path = self._clip_audio(
                downloaded_path,
                start_time,
                end_time,
                clipped_filename
            )
            print(f"Clipped path: {clipped_path}")
            return downloaded_path, clipped_path
        except Exception as e:
            print(f"Error during clipping: {str(e)}")
            print(f"Downloaded path: {downloaded_path}")
            print(f"Downloaded path exists: {os.path.exists(downloaded_path)}")
            print(f"Clipped filename: {clipped_filename}")
            # Keep download for future reuse - don't clean up
            raise Exception(f"Clipping failed: {str(e)}\nDownloaded file: {downloaded_path}\nTarget clip file: {clipped_filename}\nDownloaded file exists: {os.path.exists(downloaded_path)}")

    def create_sound_from_youtube(
        self,
        youtube_url: str,
        start_time: str,
        end_time: str,
        sound_name: str,
        guild_id: str,
        volume: float = 1.0,
        emoji_name: Optional[str] = None,
        emoji_id: Optional[str] = None,
        cleanup: bool = True
    ) -> Dict[str, Any]:
        """
        Download YouTube audio, clip it, and create Discord soundboard sound

        Args:
            youtube_url (str): YouTube video URL
            start_time (str): Start timestamp (e.g., "1:30" or "0:45")
            end_time (str): End timestamp (e.g., "1:45" or "1:00")
            sound_name (str): Name for the soundboard sound (2-32 characters)
            guild_id (str): Discord guild ID
            volume (float): Sound volume (0.0 to 1.0), default 1.0
            emoji_name (Optional[str]): Unicode emoji to use
            emoji_id (Optional[str]): Custom emoji ID to use
            cleanup (bool): Delete audio files after upload (default: True)

        Returns:
            Dict[str, Any]: Created soundboard sound object

        Raises:
            ValueError: If parameters are invalid
            Exception: If download, clipping, or upload fails
        """
        # Validate sound name
        if not 2 <= len(sound_name) <= 32:
            raise ValueError("Sound name must be between 2 and 32 characters")

        # Create safe filename
        safe_filename = re.sub(r'[^\w\s-]', '', sound_name).strip().replace(' ', '_')

        # Download audio
        temp_download = f"{safe_filename}_full"
        try:
            downloaded_path = self._download_audio(youtube_url, temp_download)
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")

        # Clip audio
        clipped_filename = f"{safe_filename}_clip.mp3"
        try:
            clipped_path = self._clip_audio(
                downloaded_path,
                start_time,
                end_time,
                clipped_filename
            )
        except Exception as e:
            # Don't cleanup - keep the full download for future reuse
            raise Exception(f"Clipping failed: {str(e)}")
        # Note: We keep the full download for reuse in future iterations

        # Create soundboard sound
        try:
            print(f"\nUploading to Discord as '{sound_name}'...")
            sound = self.soundboard.create_soundboard_sound(
                guild_id=guild_id,
                name=sound_name,
                sound_file_path=clipped_path,
                volume=volume,
                emoji_name=emoji_name,
                emoji_id=emoji_id
            )

            print(f" Successfully created soundboard sound: {sound_name}")
            return sound

        except Exception as e:
            raise Exception(f"Failed to upload to Discord: {str(e)}")

        finally:
            # Cleanup clipped file if requested
            if cleanup and os.path.exists(clipped_path):
                os.remove(clipped_path)
                print(f"Cleaned up clipped file: {clipped_path}")

    def interactive_create_with_preview(self) -> Optional[Dict[str, Any]]:
        """
        Interactive CLI for creating a soundboard sound from YouTube with preview

        Allows users to:
        1. Input YouTube URL and timestamps
        2. Preview the audio clip
        3. Edit timestamps and re-preview
        4. Publish to Discord when satisfied

        Returns:
            Optional[Dict[str, Any]]: Created sound object, or None if cancelled
        """
        print("\n" + "=" * 60)
        print("YouTube to Discord Soundboard Sound Creator (with Preview)")
        print("=" * 60)

        downloaded_path = None
        clipped_path = None
        youtube_url = None
        start_time = None
        end_time = None

        try:
            # Get YouTube URL (only once)
            youtube_url = input("\nYouTube URL: ").strip()
            if not youtube_url:
                print("Error: YouTube URL is required")
                return None

            # Preview loop - edit timestamps and preview until satisfied
            preview_satisfied = False
            first_attempt = True

            while not preview_satisfied:
                # Get timestamps
                if first_attempt:
                    print("\nTimestamp format: MM:SS or HH:MM:SS or SS (seconds)")
                    first_attempt = False
                else:
                    print("\n" + "-" * 60)
                    print("Edit timestamps:")

                start_input = input(f"Start time (current: {start_time or 'none'}): ").strip()
                if start_input:
                    start_time = start_input
                if not start_time:
                    print("Error: Start time is required")
                    continue

                end_input = input(f"End time (current: {end_time or 'none'}): ").strip()
                if end_input:
                    end_time = end_input
                if not end_time:
                    print("Error: End time is required")
                    continue

                # Clean up previous preview files
                if clipped_path and os.path.exists(clipped_path):
                    os.remove(clipped_path)

                # Create preview clip
                try:
                    print("\nCreating preview clip...")
                    downloaded_path, clipped_path = self.create_preview_clip(
                        youtube_url=youtube_url,
                        start_time=start_time,
                        end_time=end_time,
                        preview_name="preview"
                    )
                    print(f"✓ Preview clip created: {clipped_path}")

                    # Play preview
                    play_choice = input("\nPlay preview? (y/n): ").strip().lower()
                    if play_choice == 'y':
                        self._play_audio(clipped_path)

                    # Ask if satisfied
                    print("\n" + "-" * 60)
                    print("Options:")
                    print("  1. Create soundboard sound (publish to Discord)")
                    print("  2. Edit timestamps and try again")
                    print("  3. Cancel")
                    print("-" * 60)

                    choice = input("\nSelect option (1-3): ").strip()

                    if choice == '1':
                        preview_satisfied = True
                    elif choice == '2':
                        continue  # Loop to edit timestamps
                    elif choice == '3':
                        print("Cancelled.")
                        return None
                    else:
                        print("Invalid choice, please try again.")

                except Exception as e:
                    print(f"\n✗ Error: {e}")
                    retry = input("\nTry again with different timestamps? (y/n): ").strip().lower()
                    if retry != 'y':
                        return None

            # User is satisfied - now get Discord details
            print("\n" + "=" * 60)
            print("Sound Details for Discord Upload")
            print("=" * 60)

            sound_name = input("\nSound name (2-32 characters): ").strip()
            if not sound_name:
                print("Error: Sound name is required")
                return None

            guild_id = input("Discord Guild ID: ").strip()
            if not guild_id:
                print("Error: Guild ID is required")
                return None

            # Optional parameters
            volume_input = input("Volume (0.0 to 1.0, default 1.0): ").strip()
            volume = float(volume_input) if volume_input else 1.0

            emoji_name = input("Emoji (optional, e.g., 😎): ").strip()
            if not emoji_name:
                emoji_name = None

            # Final confirmation
            print("\n" + "-" * 60)
            print("Summary:")
            print(f"  YouTube URL: {youtube_url}")
            print(f"  Time range: {start_time} to {end_time}")
            print(f"  Sound name: {sound_name}")
            print(f"  Guild ID: {guild_id}")
            print(f"  Volume: {volume}")
            if emoji_name:
                print(f"  Emoji: {emoji_name}")
            print(f"  Preview file: {clipped_path}")
            print("-" * 60)

            confirm = input("\nPublish to Discord? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Cancelled.")
                return None

            # Upload to Discord using the already-created preview file
            print(f"\nUploading to Discord as '{sound_name}'...")
            sound = self.soundboard.create_soundboard_sound(
                guild_id=guild_id,
                name=sound_name,
                sound_file_path=clipped_path,
                volume=volume,
                emoji_name=emoji_name
            )

            print(f"✓ Successfully created soundboard sound: {sound_name}")
            return sound

        except KeyboardInterrupt:
            print("\n\nCancelled by user.")
            return None
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            # Keep the _full download for reuse, only cleanup preview clips
            if clipped_path and os.path.exists(clipped_path):
                os.remove(clipped_path)
                print(f"Cleaned up preview clip: {clipped_path}")
            # Note: Keeping _full download at: {downloaded_path}

    def interactive_create(self) -> Optional[Dict[str, Any]]:
        """
        Interactive CLI for creating a soundboard sound from YouTube

        Returns:
            Optional[Dict[str, Any]]: Created sound object, or None if cancelled
        """
        print("\n" + "=" * 60)
        print("YouTube to Discord Soundboard Sound Creator")
        print("=" * 60)

        try:
            # Get YouTube URL
            youtube_url = input("\nYouTube URL: ").strip()
            if not youtube_url:
                print("Error: YouTube URL is required")
                return None

            # Get timestamps
            print("\nTimestamp format: MM:SS or HH:MM:SS or SS (seconds)")
            start_time = input("Start time (e.g., 1:30): ").strip()
            if not start_time:
                print("Error: Start time is required")
                return None

            end_time = input("End time (e.g., 1:45): ").strip()
            if not end_time:
                print("Error: End time is required")
                return None

            # Get sound details
            print("\nSound details:")
            sound_name = input("Sound name (2-32 characters): ").strip()
            if not sound_name:
                print("Error: Sound name is required")
                return None

            guild_id = input("Discord Guild ID: ").strip()
            if not guild_id:
                print("Error: Guild ID is required")
                return None

            # Optional parameters
            volume_input = input("Volume (0.0 to 1.0, default 1.0): ").strip()
            volume = float(volume_input) if volume_input else 1.0

            emoji_name = input("Emoji (optional, e.g., 😀): ").strip()
            if not emoji_name:
                emoji_name = None

            # Confirm
            print("\n" + "-" * 60)
            print("Summary:")
            print(f"  YouTube URL: {youtube_url}")
            print(f"  Time range: {start_time} to {end_time}")
            print(f"  Sound name: {sound_name}")
            print(f"  Guild ID: {guild_id}")
            print(f"  Volume: {volume}")
            if emoji_name:
                print(f"  Emoji: {emoji_name}")
            print("-" * 60)

            confirm = input("\nProceed? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Cancelled.")
                return None

            # Create the sound
            sound = self.create_sound_from_youtube(
                youtube_url=youtube_url,
                start_time=start_time,
                end_time=end_time,
                sound_name=sound_name,
                guild_id=guild_id,
                volume=volume,
                emoji_name=emoji_name,
                cleanup=True
            )

            return sound

        except KeyboardInterrupt:
            print("\n\nCancelled by user.")
            return None
        except Exception as e:
            print(f"\n Error: {e}")
            return None
