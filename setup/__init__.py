"""
Setup utilities for Discord Soundboard Generator
"""

from .ffmpeg_installer import check_and_install_ffmpeg, FFmpegInstaller

__all__ = ['check_and_install_ffmpeg', 'FFmpegInstaller']
