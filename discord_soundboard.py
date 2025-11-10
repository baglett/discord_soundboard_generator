"""
Discord Soundboard Manager
Handles creation and management of soundboard sounds via Discord API
"""

import os
import base64
from typing import Optional, Dict, Any
from pathlib import Path
from discord_auth import DiscordAuth


class SoundboardManager:
    """
    Manages Discord soundboard sounds

    Provides methods to create, list, update, and delete soundboard sounds
    for a Discord guild (server).
    """

    def __init__(self, discord_auth: DiscordAuth):
        """
        Initialize the SoundboardManager

        Args:
            discord_auth (DiscordAuth): Authenticated Discord API instance
        """
        self.discord = discord_auth

    def create_soundboard_sound(
        self,
        guild_id: str,
        name: str,
        sound_file_path: str,
        volume: float = 1.0,
        emoji_id: Optional[str] = None,
        emoji_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new soundboard sound in a guild

        Args:
            guild_id (str): The Discord guild (server) ID
            name (str): Name of the soundboard sound (2-32 characters)
            sound_file_path (str): Path to the audio file (mp3 or ogg, max 512kb)
            volume (float): Volume of the sound (0.0 to 1.0), default 1.0
            emoji_id (Optional[str]): Custom emoji ID to use
            emoji_name (Optional[str]): Unicode emoji name to use

        Returns:
            Dict[str, Any]: Created soundboard sound object

        Raises:
            ValueError: If file doesn't exist, is too large, or invalid parameters
            requests.RequestException: If the API request fails
        """
        # Validate name
        if not 2 <= len(name) <= 32:
            raise ValueError("Sound name must be between 2 and 32 characters")

        # Validate volume
        if not 0.0 <= volume <= 1.0:
            raise ValueError("Volume must be between 0.0 and 1.0")

        # Validate file exists
        sound_path = Path(sound_file_path)
        if not sound_path.exists():
            raise ValueError(f"Sound file not found: {sound_file_path}")

        # Check file size (Discord limit is 512kb)
        file_size = sound_path.stat().st_size
        max_size = 512 * 1024  # 512kb in bytes
        if file_size > max_size:
            raise ValueError(f"File size ({file_size} bytes) exceeds Discord limit of {max_size} bytes (512kb)")

        # Validate file format
        allowed_extensions = {'.mp3', '.ogg'}
        if sound_path.suffix.lower() not in allowed_extensions:
            raise ValueError(f"File must be mp3 or ogg format. Got: {sound_path.suffix}")

        # Read and encode the audio file
        with open(sound_file_path, 'rb') as f:
            audio_data = f.read()

        # Encode to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        # Determine MIME type
        mime_type = 'audio/mpeg' if sound_path.suffix.lower() == '.mp3' else 'audio/ogg'

        # Prepare request payload
        payload = {
            'name': name,
            'sound': f'data:{mime_type};base64,{audio_base64}',
            'volume': volume
        }

        # Add emoji if provided
        if emoji_id:
            payload['emoji_id'] = emoji_id
        elif emoji_name:
            payload['emoji_name'] = emoji_name

        # Make API request
        endpoint = f'/guilds/{guild_id}/soundboard-sounds'
        response = self.discord.post(endpoint, data=payload)

        if response.status_code == 400:
            error_data = response.json()
            raise ValueError(f"Invalid request: {error_data.get('message', 'Unknown error')}")
        elif response.status_code == 403:
            raise PermissionError("Bot lacks permission to create soundboard sounds in this guild")
        elif response.status_code == 404:
            raise ValueError(f"Guild not found: {guild_id}")

        response.raise_for_status()
        sound_data = response.json()

        print(f" Created soundboard sound: {name} (ID: {sound_data.get('sound_id', 'Unknown')})")
        return sound_data

    def list_soundboard_sounds(self, guild_id: str) -> list[Dict[str, Any]]:
        """
        List all soundboard sounds in a guild

        Args:
            guild_id (str): The Discord guild (server) ID

        Returns:
            list[Dict[str, Any]]: List of soundboard sound objects
        """
        endpoint = f'/guilds/{guild_id}/soundboard-sounds'
        response = self.discord.get(endpoint)

        if response.status_code == 404:
            raise ValueError(f"Guild not found: {guild_id}")

        response.raise_for_status()
        return response.json()

    def get_soundboard_sound(self, guild_id: str, sound_id: str) -> Dict[str, Any]:
        """
        Get a specific soundboard sound

        Args:
            guild_id (str): The Discord guild (server) ID
            sound_id (str): The soundboard sound ID

        Returns:
            Dict[str, Any]: Soundboard sound object
        """
        sounds = self.list_soundboard_sounds(guild_id)
        for sound in sounds:
            if sound.get('sound_id') == sound_id:
                return sound

        raise ValueError(f"Soundboard sound not found: {sound_id}")

    def update_soundboard_sound(
        self,
        guild_id: str,
        sound_id: str,
        name: Optional[str] = None,
        volume: Optional[float] = None,
        emoji_id: Optional[str] = None,
        emoji_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing soundboard sound

        Args:
            guild_id (str): The Discord guild (server) ID
            sound_id (str): The soundboard sound ID
            name (Optional[str]): New name (2-32 characters)
            volume (Optional[float]): New volume (0.0 to 1.0)
            emoji_id (Optional[str]): New custom emoji ID
            emoji_name (Optional[str]): New unicode emoji name

        Returns:
            Dict[str, Any]: Updated soundboard sound object
        """
        payload = {}

        if name is not None:
            if not 2 <= len(name) <= 32:
                raise ValueError("Sound name must be between 2 and 32 characters")
            payload['name'] = name

        if volume is not None:
            if not 0.0 <= volume <= 1.0:
                raise ValueError("Volume must be between 0.0 and 1.0")
            payload['volume'] = volume

        if emoji_id is not None:
            payload['emoji_id'] = emoji_id
        elif emoji_name is not None:
            payload['emoji_name'] = emoji_name

        if not payload:
            raise ValueError("At least one field must be provided to update")

        endpoint = f'/guilds/{guild_id}/soundboard-sounds/{sound_id}'
        response = self.discord.patch(endpoint, data=payload)

        if response.status_code == 404:
            raise ValueError(f"Soundboard sound or guild not found")

        response.raise_for_status()
        sound_data = response.json()

        print(f" Updated soundboard sound: {sound_data.get('name', sound_id)}")
        return sound_data

    def delete_soundboard_sound(self, guild_id: str, sound_id: str) -> None:
        """
        Delete a soundboard sound from a guild

        Args:
            guild_id (str): The Discord guild (server) ID
            sound_id (str): The soundboard sound ID
        """
        endpoint = f'/guilds/{guild_id}/soundboard-sounds/{sound_id}'
        response = self.discord.delete(endpoint)

        if response.status_code == 404:
            raise ValueError(f"Soundboard sound or guild not found")

        response.raise_for_status()
        print(f" Deleted soundboard sound: {sound_id}")

    def bulk_create_sounds(
        self,
        guild_id: str,
        sounds_directory: str,
        volume: float = 1.0,
        name_from_filename: bool = True
    ) -> list[Dict[str, Any]]:
        """
        Create multiple soundboard sounds from a directory

        Args:
            guild_id (str): The Discord guild (server) ID
            sounds_directory (str): Path to directory containing audio files
            volume (float): Default volume for all sounds (0.0 to 1.0)
            name_from_filename (bool): Use filename (without extension) as sound name

        Returns:
            list[Dict[str, Any]]: List of created soundboard sound objects
        """
        sounds_path = Path(sounds_directory)
        if not sounds_path.exists() or not sounds_path.is_dir():
            raise ValueError(f"Directory not found: {sounds_directory}")

        created_sounds = []
        failed_sounds = []

        # Find all audio files
        audio_files = list(sounds_path.glob('*.mp3')) + list(sounds_path.glob('*.ogg'))

        if not audio_files:
            print(f"No audio files found in {sounds_directory}")
            return []

        print(f"\nFound {len(audio_files)} audio file(s) to upload...")

        for audio_file in audio_files:
            try:
                # Generate name from filename
                sound_name = audio_file.stem if name_from_filename else audio_file.name

                # Ensure name is within limits
                if len(sound_name) > 32:
                    sound_name = sound_name[:32]
                elif len(sound_name) < 2:
                    sound_name = f"sound_{audio_file.stem}"

                # Create the sound
                sound = self.create_soundboard_sound(
                    guild_id=guild_id,
                    name=sound_name,
                    sound_file_path=str(audio_file),
                    volume=volume
                )
                created_sounds.append(sound)

            except Exception as e:
                failed_sounds.append((audio_file.name, str(e)))
                print(f" Failed to create {audio_file.name}: {e}")

        # Summary
        print(f"\n{'='*60}")
        print(f"Successfully created: {len(created_sounds)}/{len(audio_files)} sounds")
        if failed_sounds:
            print(f"Failed: {len(failed_sounds)}")
            for filename, error in failed_sounds:
                print(f"  - {filename}: {error}")

        return created_sounds
