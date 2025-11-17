"""
Facebook reel audio scraping functionality using yt-dlp.

This module handles:
- Facebook reel URL validation
- Audio extraction from Facebook reels
- Error handling for private posts and rate limits
"""

import os
import re
import yt_dlp
from typing import Dict, Optional, Tuple
from pathlib import Path


class FacebookScraper:
    """Handles Facebook reel audio scraping"""

    def __init__(self, soundboard_manager, ffmpeg_path: str = None):
        """
        Initialize Facebook scraper

        Args:
            soundboard_manager: SoundboardManager instance
            ffmpeg_path: Path to ffmpeg executable
        """
        self.soundboard_manager = soundboard_manager
        self.ffmpeg_path = ffmpeg_path
        self.sounds_dir = Path("sounds")
        self.sounds_dir.mkdir(exist_ok=True)

    def validate_facebook_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if URL is a valid Facebook reel URL

        Args:
            url: URL string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url or not isinstance(url, str):
            return False, "URL cannot be empty"

        url = url.strip()

        # Facebook URL patterns
        facebook_patterns = [
            r'https?://(?:www\.)?facebook\.com/(?:share/(?:v|r)/[A-Za-z0-9]+/?|reel/[0-9]+)',  # Share links and direct reel links
            r'https?://(?:www\.)?facebook\.com/watch/?\?v=[0-9]+',  # Watch links
            r'https?://(?:www\.)?facebook\.com/[^/]+/videos/[0-9]+',  # Profile video links
            r'https?://(?:www\.)?fb\.watch/[A-Za-z0-9_-]+',  # Short links
        ]

        for pattern in facebook_patterns:
            if re.match(pattern, url):
                return True, None

        # Check if it's a Facebook URL but invalid format
        if 'facebook.com' in url or 'fb.watch' in url:
            return False, "URL must be a Facebook reel or video link (facebook.com/share/r/... or facebook.com/reel/...)"

        return False, "URL must be a Facebook reel or video link"

    def detect_url_platform(self, url: str) -> Optional[str]:
        """
        Detect if URL is from YouTube, Instagram, or Facebook

        Args:
            url: URL string to check

        Returns:
            "youtube", "instagram", "facebook", or None if unrecognized
        """
        if not url:
            return None

        url = url.strip().lower()

        # Check Facebook first
        if 'facebook.com' in url or 'fb.watch' in url:
            is_valid, _ = self.validate_facebook_url(url)
            if is_valid:
                return "facebook"

        # Check Instagram
        if 'instagram.com' in url:
            return "instagram"

        # Check YouTube patterns
        youtube_patterns = [
            'youtube.com/watch',
            'youtube.com/v/',
            'youtu.be/',
            'youtube.com/embed/',
        ]

        if any(pattern in url for pattern in youtube_patterns):
            return "youtube"

        return None

    def get_reel_info(self, url: str) -> Dict:
        """
        Get Facebook reel information

        Args:
            url: Facebook reel URL

        Returns:
            Dictionary with reel info:
            {
                'title': str,
                'description': str,
                'duration': float (seconds),
                'thumbnail': str (URL),
                'has_audio': bool
            }

        Raises:
            Exception: If reel is private, rate limited, or other errors
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }

        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg_path)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    raise Exception("Could not extract reel information")

                # Check for audio
                has_audio = False
                formats = info.get('formats', [])
                if formats:
                    has_audio = any(
                        f.get('acodec') and f.get('acodec') != 'none'
                        for f in formats
                    )
                else:
                    # Single URL format, assume it has audio
                    has_audio = True

                return {
                    'title': info.get('title', 'Facebook Reel'),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'has_audio': has_audio,
                    'uploader': info.get('uploader', 'Unknown'),
                }

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e).lower()

            # Check for specific error types
            if 'private' in error_msg or 'login' in error_msg:
                raise Exception("This reel is private. Please try a public reel.")
            elif 'not found' in error_msg or '404' in error_msg:
                raise Exception("Reel not found. Please check the URL.")
            elif 'rate' in error_msg or 'too many' in error_msg or '429' in error_msg:
                raise Exception("Facebook rate limit reached. Please try again in a few minutes.")
            else:
                raise Exception(f"Could not access Facebook reel: {str(e)}")
        except Exception as e:
            if "private" in str(e).lower():
                raise Exception("This reel is private. Please try a public reel.")
            raise

    def download_audio(self, url: str, output_name: str) -> str:
        """
        Download audio from Facebook reel

        Args:
            url: Facebook reel URL
            output_name: Base name for output file (without extension)

        Returns:
            Path to downloaded audio file

        Raises:
            Exception: If download fails
        """
        output_path = str(self.sounds_dir / f"{output_name}_full")

        # Check if already downloaded
        if os.path.exists(f"{output_path}.mp3"):
            print(f"✓ Found existing download: {output_path}.mp3")
            return f"{output_path}.mp3"

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
        }

        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg_path)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"Downloading audio from Facebook reel: {url}")
                ydl.download([url])

            # Verify download
            mp3_path = f"{output_path}.mp3"
            if not os.path.exists(mp3_path):
                raise Exception("Audio file was not created")

            print(f"✓ Downloaded audio: {mp3_path}")
            return mp3_path

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e).lower()

            if 'private' in error_msg or 'login' in error_msg:
                raise Exception("This reel is private. Please try a public reel.")
            elif 'rate' in error_msg or 'too many' in error_msg or '429' in error_msg:
                raise Exception("Facebook rate limit reached. Please try again in a few minutes.")
            else:
                raise Exception(f"Failed to download audio: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to download audio: {str(e)}")

    def download_thumbnail(self, thumbnail_url: str, output_name: str) -> Optional[str]:
        """
        Download thumbnail image for Facebook reel

        Args:
            thumbnail_url: URL of thumbnail image
            output_name: Base name for output file

        Returns:
            Path to downloaded thumbnail, or None if failed
        """
        if not thumbnail_url:
            return None

        import urllib.request

        output_path = self.sounds_dir / f"{output_name}_thumb.jpg"

        # Skip if already downloaded
        if output_path.exists():
            return str(output_path)

        try:
            urllib.request.urlretrieve(thumbnail_url, output_path)
            return str(output_path)
        except Exception as e:
            print(f"Failed to download thumbnail: {e}")
            return None
