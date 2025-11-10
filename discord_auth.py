"""
Discord Authentication Module
Provides a reusable class for authenticating with the Discord API
"""

import os
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv


class DiscordAuth:
    """
    Reusable Discord API authentication class

    Supports bot token authentication and provides methods to interact
    with the Discord API.
    """

    BASE_URL = "https://discord.com/api/v10"

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the DiscordAuth class

        Args:
            token (Optional[str]): Discord bot token. If not provided,
                                  will attempt to load from DISCORD_API_KEY env variable
        """
        load_dotenv()

        self.token = token or os.getenv('DISCORD_API_KEY')

        if not self.token:
            raise ValueError(
                "Discord API token is required. "
                "Provide it as an argument or set DISCORD_API_KEY in .env file"
            )

        self.headers = {
            'Authorization': f'Bot {self.token}',
            'Content-Type': 'application/json'
        }

        self._validate_token()

    def _validate_token(self) -> None:
        """
        Validate the Discord bot token by attempting to fetch bot user info

        Raises:
            ValueError: If the token is invalid
            requests.RequestException: If there's a network error
        """
        try:
            response = self.get('/users/@me')
            if response.status_code == 401:
                raise ValueError("Invalid Discord API token")
            response.raise_for_status()
            bot_info = response.json()
            print(f"Successfully authenticated as: {bot_info.get('username', 'Unknown')}#{bot_info.get('discriminator', '0000')}")
        except requests.RequestException as e:
            raise ValueError(f"Failed to validate token: {str(e)}")

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make a GET request to the Discord API

        Args:
            endpoint (str): API endpoint (e.g., '/users/@me')
            params (Optional[Dict[str, Any]]): Query parameters

        Returns:
            requests.Response: Response object
        """
        url = f"{self.BASE_URL}{endpoint}"
        return requests.get(url, headers=self.headers, params=params)

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make a POST request to the Discord API

        Args:
            endpoint (str): API endpoint
            data (Optional[Dict[str, Any]]): JSON payload

        Returns:
            requests.Response: Response object
        """
        url = f"{self.BASE_URL}{endpoint}"
        return requests.post(url, headers=self.headers, json=data)

    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make a PUT request to the Discord API

        Args:
            endpoint (str): API endpoint
            data (Optional[Dict[str, Any]]): JSON payload

        Returns:
            requests.Response: Response object
        """
        url = f"{self.BASE_URL}{endpoint}"
        return requests.put(url, headers=self.headers, json=data)

    def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make a PATCH request to the Discord API

        Args:
            endpoint (str): API endpoint
            data (Optional[Dict[str, Any]]): JSON payload

        Returns:
            requests.Response: Response object
        """
        url = f"{self.BASE_URL}{endpoint}"
        return requests.patch(url, headers=self.headers, json=data)

    def delete(self, endpoint: str) -> requests.Response:
        """
        Make a DELETE request to the Discord API

        Args:
            endpoint (str): API endpoint

        Returns:
            requests.Response: Response object
        """
        url = f"{self.BASE_URL}{endpoint}"
        return requests.delete(url, headers=self.headers)

    def get_bot_info(self) -> Dict[str, Any]:
        """
        Get information about the authenticated bot

        Returns:
            Dict[str, Any]: Bot user information
        """
        response = self.get('/users/@me')
        response.raise_for_status()
        return response.json()

    def get_guilds(self) -> list[Dict[str, Any]]:
        """
        Get list of guilds the bot is in

        Returns:
            list[Dict[str, Any]]: List of guild objects
        """
        response = self.get('/users/@me/guilds')
        response.raise_for_status()
        return response.json()
