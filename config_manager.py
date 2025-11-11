"""
Configuration Manager for Discord Soundboard Generator
Manages loading and saving of application settings
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv


class ConfigManager:
    """Manages application configuration from .env and local config file"""

    CONFIG_FILE = "config.json"

    def __init__(self):
        self.config_path = Path(self.CONFIG_FILE)
        self.config = {}
        self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from .env and config.json
        Priority: .env > config.json

        Returns:
            Dict with configuration values
        """
        # Load from .env first (for local development)
        load_dotenv()

        # Load from config.json if it exists
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config.json: {e}")
                self.config = {}
        else:
            self.config = {}

        # Override with .env values if present (development priority)
        env_api_key = os.getenv('DISCORD_API_KEY')
        env_app_id = os.getenv('DISCORD_APPLICATION_ID')
        env_guild_id = os.getenv('DISCORD_GUILD_ID')

        if env_api_key:
            self.config['discord_api_key'] = env_api_key
        if env_app_id:
            self.config['discord_application_id'] = env_app_id
        if env_guild_id:
            self.config['discord_guild_id'] = env_guild_id

        return self.config

    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration to config.json

        Args:
            config: Dictionary with configuration values

        Returns:
            True if successful, False otherwise
        """
        try:
            self.config = config
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
            return True
        except IOError as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value"""
        self.config[key] = value

    def has_credentials(self) -> bool:
        """Check if all required Discord credentials are present"""
        return bool(
            self.config.get('discord_api_key') and
            self.config.get('discord_application_id') and
            self.config.get('discord_guild_id')
        )

    def get_credentials(self) -> Dict[str, str]:
        """Get all Discord credentials"""
        return {
            'discord_api_key': self.config.get('discord_api_key', ''),
            'discord_application_id': self.config.get('discord_application_id', ''),
            'discord_guild_id': self.config.get('discord_guild_id', '')
        }

    def save_credentials(self, api_key: str, app_id: str, guild_id: str) -> bool:
        """
        Save Discord credentials to config file

        Args:
            api_key: Discord bot token
            app_id: Discord application ID
            guild_id: Discord guild (server) ID

        Returns:
            True if successful, False otherwise
        """
        self.config['discord_api_key'] = api_key
        self.config['discord_application_id'] = app_id
        self.config['discord_guild_id'] = guild_id
        return self.save_config(self.config)
