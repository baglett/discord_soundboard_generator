"""
Main entry point for Discord Soundboard Generator
"""

import os
import sys
from discord_auth import DiscordAuth
from discord_soundboard import SoundboardManager
from youtube_to_sound import YouTubeToSound


def print_menu():
    """Print the main menu"""
    print("\n" + "=" * 60)
    print("Discord Soundboard Generator - Main Menu")
    print("=" * 60)
    print("1. Create sound from YouTube video")
    print("2. List soundboard sounds in a guild")
    print("3. Bulk upload sounds from directory")
    print("4. Delete a soundboard sound")
    print("5. Show bot info")
    print("0. Exit")
    print("=" * 60)


def show_bot_info(discord):
    """Display bot information and guilds"""
    bot_info = discord.get_bot_info()
    print(f"\nBot ID: {bot_info['id']}")
    print(f"Bot Username: {bot_info['username']}")

    guilds = discord.get_guilds()
    print(f"\nBot is in {len(guilds)} guild(s):")
    for guild in guilds:
        print(f"  - {guild['name']} (ID: {guild['id']})")


def list_sounds(soundboard):
    """List all soundboard sounds in a guild"""
    guild_id = input("\nEnter Discord Guild ID: ").strip()
    if not guild_id:
        print("Error: Guild ID is required")
        return

    try:
        sounds = soundboard.list_soundboard_sounds(guild_id)
        print(f"\nFound {len(sounds)} soundboard sound(s):")
        for sound in sounds:
            emoji = sound.get('emoji_name', '') or ''
            print(f"  {emoji} {sound['name']} (ID: {sound['sound_id']}, Volume: {sound['volume']})")
    except Exception as e:
        print(f"Error: {e}")


def bulk_upload_sounds(soundboard):
    """Bulk upload sounds from a directory"""
    guild_id = input("\nEnter Discord Guild ID: ").strip()
    if not guild_id:
        print("Error: Guild ID is required")
        return

    directory = input("Enter path to sounds directory: ").strip()
    if not directory:
        print("Error: Directory path is required")
        return

    volume_input = input("Volume (0.0 to 1.0, default 1.0): ").strip()
    volume = float(volume_input) if volume_input else 1.0

    try:
        created = soundboard.bulk_create_sounds(
            guild_id=guild_id,
            sounds_directory=directory,
            volume=volume
        )
        print(f"\n✓ Bulk upload complete: {len(created)} sounds created")
    except Exception as e:
        print(f"Error: {e}")


def delete_sound(soundboard):
    """Delete a soundboard sound"""
    guild_id = input("\nEnter Discord Guild ID: ").strip()
    if not guild_id:
        print("Error: Guild ID is required")
        return

    sound_id = input("Enter Sound ID to delete: ").strip()
    if not sound_id:
        print("Error: Sound ID is required")
        return

    confirm = input(f"Are you sure you want to delete sound {sound_id}? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return

    try:
        soundboard.delete_soundboard_sound(guild_id, sound_id)
        print(f"✓ Successfully deleted sound: {sound_id}")
    except Exception as e:
        print(f"Error: {e}")


def main():
    """
    Main function to run the Discord Soundboard Generator
    """
    try:
        # Initialize Discord authentication
        print("Initializing Discord authentication...")
        discord = DiscordAuth()

        # Initialize managers
        soundboard = SoundboardManager(discord)
        youtube_converter = YouTubeToSound(soundboard, output_dir="sounds")

        print("\n✓ Authentication successful!")

        # Main menu loop
        while True:
            print_menu()
            choice = input("\nSelect an option: ").strip()

            if choice == "1":
                # Create sound from YouTube with preview
                youtube_converter.interactive_create_with_preview()

            elif choice == "2":
                # List sounds
                list_sounds(soundboard)

            elif choice == "3":
                # Bulk upload
                bulk_upload_sounds(soundboard)

            elif choice == "4":
                # Delete sound
                delete_sound(soundboard)

            elif choice == "5":
                # Show bot info
                show_bot_info(discord)

            elif choice == "0":
                # Exit
                print("\nGoodbye!")
                sys.exit(0)

            else:
                print("\n✗ Invalid option. Please try again.")

    except ValueError as e:
        print(f"\nAuthentication Error: {e}")
        print("\nPlease ensure you have:")
        print("1. Created a .env file (you can copy sample.env)")
        print("2. Added your Discord bot token to DISCORD_API_KEY in .env")
        print("3. Added your Discord guild ID to DISCORD_GUILD_ID in .env (optional)")
        sys.exit(1)

    except PermissionError as e:
        print(f"\nPermission Error: {e}")
        print("\nMake sure your bot has the following permissions:")
        print("- Create Expressions (for soundboard sounds)")
        print("- Manage Expressions (to modify/delete sounds)")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
