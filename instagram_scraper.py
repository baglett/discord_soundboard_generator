"""
Instagram audio scraping functionality using yt-dlp.

This module handles:
- Instagram post/reel URL validation
- Carousel (multi-slide) detection and parsing
- Audio extraction from Instagram videos
- Thumbnail extraction for carousel slides
- Error handling for private posts and rate limits
"""

import os
import re
import yt_dlp
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json


class InstagramScraper:
    """Handles Instagram audio scraping and carousel management"""

    def __init__(self, soundboard_manager, ffmpeg_path: str = None):
        """
        Initialize Instagram scraper

        Args:
            soundboard_manager: SoundboardManager instance
            ffmpeg_path: Path to ffmpeg executable
        """
        self.soundboard_manager = soundboard_manager
        self.ffmpeg_path = ffmpeg_path
        self.sounds_dir = Path("sounds")
        self.sounds_dir.mkdir(exist_ok=True)

    def validate_instagram_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if URL is a valid Instagram post/reel URL

        Args:
            url: URL string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url or not isinstance(url, str):
            return False, "URL cannot be empty"

        url = url.strip()

        # Instagram URL patterns
        instagram_patterns = [
            r'https?://(?:www\.)?instagram\.com/p/[A-Za-z0-9_-]+',  # Post
            r'https?://(?:www\.)?instagram\.com/reel/[A-Za-z0-9_-]+',  # Reel
            r'https?://(?:www\.)?instagram\.com/reels?/[A-Za-z0-9_-]+',  # Reels variant
        ]

        for pattern in instagram_patterns:
            if re.match(pattern, url):
                return True, None

        return False, "URL must be an Instagram post or reel (instagram.com/p/... or instagram.com/reel/...)"

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
            return "facebook"

        # Check Instagram
        if 'instagram.com' in url:
            is_valid, _ = self.validate_instagram_url(url)
            if is_valid:
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

    def get_post_info(self, url: str) -> Dict:
        """
        Get Instagram post/reel information including carousel items

        Args:
            url: Instagram post/reel URL

        Returns:
            Dictionary with post info:
            {
                'title': str,
                'description': str,
                'is_carousel': bool,
                'items': List[Dict] with each item containing:
                    {
                        'index': int,
                        'type': 'video' or 'image',
                        'has_audio': bool,
                        'thumbnail': str (path),
                        'url': str (media URL),
                        'duration': float (for videos)
                    }
            }

        Raises:
            Exception: If post is private, rate limited, or other errors
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,  # Get full info
            'skip_download': True,  # Don't download yet, just get info
        }

        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg_path)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    raise Exception("Could not extract post information")

                # Check if it's a carousel (playlist)
                is_carousel = info.get('_type') == 'playlist' or 'entries' in info

                result = {
                    'title': info.get('title', 'Instagram Post'),
                    'description': info.get('description', ''),
                    'is_carousel': is_carousel,
                    'items': []
                }

                if is_carousel:
                    # Multiple items in carousel
                    entries = info.get('entries', [])
                    for idx, entry in enumerate(entries):
                        if entry:  # Skip None entries
                            item_info = self._parse_carousel_item(entry, idx)
                            # Only include items with video (has audio potential)
                            if item_info['type'] == 'video':
                                result['items'].append(item_info)
                else:
                    # Single item (reel or single video post)
                    item_info = self._parse_carousel_item(info, 0)
                    if item_info['type'] == 'video':
                        result['items'].append(item_info)

                # Filter out items without audio
                result['items'] = [item for item in result['items'] if item['has_audio']]

                if not result['items']:
                    raise Exception("No video slides with audio found in this post")

                return result

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e).lower()

            # Check for specific error types
            if 'private' in error_msg or 'login' in error_msg:
                raise Exception("This post is private. Please try a public post.")
            elif 'not found' in error_msg or '404' in error_msg:
                raise Exception("Post not found. Please check the URL.")
            elif 'rate' in error_msg or 'too many' in error_msg or '429' in error_msg:
                raise Exception("Instagram rate limit reached. Please try again in a few minutes.")
            else:
                raise Exception(f"Could not access Instagram post: {str(e)}")
        except Exception as e:
            if "private" in str(e).lower():
                raise Exception("This post is private. Please try a public post.")
            raise

    def _parse_carousel_item(self, entry: Dict, index: int) -> Dict:
        """
        Parse a single carousel item or single post entry

        Args:
            entry: yt-dlp info dict for the item
            index: Item index in carousel

        Returns:
            Dictionary with item info
        """
        # Determine if it's a video or image
        # yt-dlp only extracts videos, so if we have formats, it's a video
        has_formats = 'formats' in entry or 'url' in entry
        is_video = has_formats

        # Check for audio
        has_audio = False
        if is_video:
            # Check if any format has audio
            formats = entry.get('formats', [])
            if formats:
                has_audio = any(
                    f.get('acodec') and f.get('acodec') != 'none'
                    for f in formats
                )
            else:
                # Single URL format, assume it has audio
                has_audio = True

        return {
            'index': index,
            'type': 'video' if is_video else 'image',
            'has_audio': has_audio,
            'thumbnail': entry.get('thumbnail', ''),
            'url': entry.get('url', ''),
            'duration': entry.get('duration', 0),
            'title': entry.get('title', f'Slide {index + 1}')
        }

    def download_audio(self, url: str, output_name: str, carousel_index: Optional[int] = None) -> str:
        """
        Download audio from Instagram post/reel

        Args:
            url: Instagram post/reel URL
            output_name: Base name for output file (without extension)
            carousel_index: If carousel, which item to download (0-indexed)

        Returns:
            Path to downloaded audio file

        Raises:
            Exception: If download fails
        """
        output_path = str(self.sounds_dir / f"{output_name}_full")

        # Check if already downloaded
        if os.path.exists(f"{output_path}.mp3"):
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

        # If carousel, we need to specify which item to download
        if carousel_index is not None:
            ydl_opts['playlist_items'] = str(carousel_index + 1)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Verify download
            mp3_path = f"{output_path}.mp3"
            if not os.path.exists(mp3_path):
                raise Exception("Audio file was not created")

            return mp3_path

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e).lower()

            if 'private' in error_msg or 'login' in error_msg:
                raise Exception("This post is private. Please try a public post.")
            elif 'rate' in error_msg or 'too many' in error_msg or '429' in error_msg:
                raise Exception("Instagram rate limit reached. Please try again in a few minutes.")
            else:
                raise Exception(f"Failed to download audio: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to download audio: {str(e)}")

    def download_thumbnail(self, thumbnail_url: str, output_name: str, index: int) -> Optional[str]:
        """
        Download thumbnail image for carousel item

        Args:
            thumbnail_url: URL of thumbnail image
            output_name: Base name for output file
            index: Carousel item index

        Returns:
            Path to downloaded thumbnail, or None if failed
        """
        if not thumbnail_url:
            return None

        import urllib.request

        output_path = self.sounds_dir / f"{output_name}_thumb_{index}.jpg"

        # Skip if already downloaded
        if output_path.exists():
            return str(output_path)

        try:
            urllib.request.urlretrieve(thumbnail_url, output_path)
            return str(output_path)
        except Exception as e:
            print(f"Failed to download thumbnail: {e}")
            return None
