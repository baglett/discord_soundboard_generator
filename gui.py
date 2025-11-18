"""
Discord Soundboard Generator - GUI Application
Desktop interface for creating and managing Discord soundboard sounds
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
from typing import Optional, Dict, Any
from discord_auth import DiscordAuth
from discord_soundboard import SoundboardManager
from youtube_to_sound import YouTubeToSound
import pygame
import traceback
import time


class CopyableMessageDialog:
    """Custom dialog with copyable text"""

    def __init__(self, parent, title, message, dialog_type="error"):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("600x400")
        self.dialog.minsize(500, 300)

        # Make it modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title with icon
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        icon = "❌" if dialog_type == "error" else "✓" if dialog_type == "success" else "ℹ"
        ttk.Label(title_frame, text=f"{icon} {title}",
                 font=('Arial', 12, 'bold')).pack(side=tk.LEFT)

        # Scrolled text for message (copyable)
        text_widget = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD,
                                                height=15, width=70)
        text_widget.pack(fill=tk.BOTH, expand=True, pady=10)
        text_widget.insert(1.0, message)
        text_widget.config(state=tk.NORMAL)  # Keep it editable for copying

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Copy button
        ttk.Button(button_frame, text="Copy to Clipboard",
                  command=lambda: self.copy_to_clipboard(message)).pack(side=tk.LEFT, padx=(0, 10))

        # Close button
        ttk.Button(button_frame, text="Close",
                  command=self.dialog.destroy).pack(side=tk.LEFT)

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f'+{x}+{y}')

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(text)
        self.dialog.update()  # Keep clipboard content
        messagebox.showinfo("Copied", "Text copied to clipboard!", parent=self.dialog)


class SoundboardGUI:
    """Main GUI application for Discord Soundboard Generator"""

    def __init__(self, root: tk.Tk):
        """Initialize the GUI application"""
        self.root = root
        self.root.title("Discord Soundboard Generator")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # Initialize Discord components
        self.discord = None
        self.soundboard = None
        self.youtube_converter = None
        self.bot_info = None
        self.guilds = []
        self.selected_guild_id = None
        self.default_guild_id = None  # Guild ID from .env file

        # Preview state
        self.preview_audio_path = None
        self.downloaded_audio_path = None
        self.source_mode = tk.StringVar(value="youtube")  # "youtube" or "local"
        self.selected_local_file = None

        # Audio trim slider state (for local files)
        self.audio_duration = 0.0  # Total duration in seconds
        self.trim_start = tk.DoubleVar(value=0.0)
        self.trim_end = tk.DoubleVar(value=5.2)
        self.loaded_audio_path = None  # Track which file is currently loaded

        # YouTube trim slider state (separate from local)
        self.yt_audio_duration = 0.0
        self.yt_trim_start = tk.DoubleVar(value=0.0)
        self.yt_trim_end = tk.DoubleVar(value=5.2)
        self.youtube_video_id = None  # YouTube video ID for preview

        # Setup pygame for audio playback
        pygame.mixer.init()

        # Setup GUI
        self.setup_styles()
        self.create_widgets()

        # Initialize Discord connection
        self.initialize_discord()

    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')

        # Configure colors
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        style.configure('Action.TButton', padding=10)

    def show_error(self, title, message, exception=None):
        """Show error dialog with copyable text"""
        full_message = message
        if exception:
            full_message += f"\n\nException Details:\n{str(exception)}\n\nTraceback:\n{traceback.format_exc()}"
        CopyableMessageDialog(self.root, title, full_message, dialog_type="error")

    def show_success(self, title, message):
        """Show success dialog with copyable text"""
        CopyableMessageDialog(self.root, title, message, dialog_type="success")

    def show_info(self, title, message):
        """Show info dialog with copyable text"""
        CopyableMessageDialog(self.root, title, message, dialog_type="info")

    def safe_remove_file(self, filepath, max_attempts=5, delay=0.3):
        """Safely remove a file with retry logic"""
        if not filepath or not os.path.exists(filepath):
            return True

        for attempt in range(max_attempts):
            try:
                # Stop pygame mixer if it might be using the file
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()

                # Always try to unload to release file handle
                try:
                    pygame.mixer.music.unload()
                except:
                    pass

                # Give Windows time to release the file handle
                time.sleep(delay * (attempt + 1))  # Increase delay with each attempt

                os.remove(filepath)
                return True
            except PermissionError:
                if attempt < max_attempts - 1:
                    time.sleep(delay)
                    continue
                else:
                    return False
            except Exception:
                return False
        return False

    def create_widgets(self):
        """Create all GUI widgets"""
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        self.create_youtube_tab()
        self.create_settings_tab()

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))

    def create_youtube_tab(self):
        """Create YouTube to Sound tab with wizard interface"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Create Sound")

        # Main container with padding
        container = ttk.Frame(tab, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Wizard state
        self.wizard_step = 1  # 1 or 2

        # Create both wizard steps (we'll show/hide them)
        self.wizard_step1_frame = ttk.Frame(container)
        self.wizard_step2_frame = ttk.Frame(container)

        self.create_wizard_step1(self.wizard_step1_frame)
        self.create_wizard_step2(self.wizard_step2_frame)

        # Show step 1 initially
        self.show_wizard_step(1)

    def create_wizard_step1(self, parent):
        """Create wizard step 1: Source selection, URL/file, and sound name"""
        # Header with step indicator
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky=tk.EW)

        ttk.Label(header_frame, text="Step 1 of 2: Select Audio Source",
                  style='Header.TLabel').pack()
        ttk.Label(header_frame, text="Choose your audio source and enter details",
                  font=('Arial', 9), foreground='gray').pack()

        # Source mode selection (YouTube vs Local)
        ttk.Label(container, text="Source:").grid(row=1, column=0, sticky=tk.W, pady=5)
        source_frame = ttk.Frame(container)
        source_frame.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))

        ttk.Radiobutton(source_frame, text="YouTube", variable=self.source_mode,
                       value="youtube", command=self.on_source_mode_changed).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(source_frame, text="Local File", variable=self.source_mode,
                       value="local", command=self.on_source_mode_changed).pack(side=tk.LEFT)

        # YouTube-specific fields (row 2-5)
        self.youtube_frame = ttk.Frame(container)
        self.youtube_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=10)

        # Sound Name (determines temp file name)
        ttk.Label(self.youtube_frame, text="Sound Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.temp_sound_name_entry = ttk.Entry(self.youtube_frame, width=30)
        self.temp_sound_name_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.temp_sound_name_entry.insert(0, "rick_roll")

        # Add helpful hint below sound name field
        hint_sound_name = ttk.Label(self.youtube_frame, text="This will be used for the temporary file name",
                              font=('Arial', 8), foreground='gray')
        hint_sound_name.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=(35, 0), padx=(10, 0))

        # YouTube URL
        ttk.Label(self.youtube_frame, text="YouTube URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.youtube_url_entry = ttk.Entry(self.youtube_frame, width=50)
        self.youtube_url_entry.grid(row=1, column=1, columnspan=2, sticky=tk.EW, pady=5, padx=(10, 0))
        self.youtube_url_entry.insert(0, "https://www.youtube.com/watch?v=xvFZjo5PgG0")

        # Add helpful hint below URL field
        hint_label = ttk.Label(self.youtube_frame, text="Use direct video URL (youtube.com/watch?v=... or youtu.be/...), not search URLs",
                              font=('Arial', 8), foreground='gray')
        hint_label.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=(35, 0), padx=(10, 0))

        # Load Video button
        ttk.Button(self.youtube_frame, text="Load Video Info", command=self.load_youtube_video_info).grid(
            row=2, column=0, columnspan=3, pady=10)

        # YouTube video info display
        self.youtube_info_label = ttk.Label(self.youtube_frame, text="Enter URL and click 'Load Video Info'",
                                           font=('Arial', 9), foreground='gray')
        self.youtube_info_label.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))

        # YouTube Trim Slider Section
        ttk.Separator(self.youtube_frame, orient=tk.HORIZONTAL).grid(
            row=4, column=0, columnspan=3, sticky=tk.EW, pady=(10, 10))

        ttk.Label(self.youtube_frame, text="Audio Trimmer (1.0s - 5.2s max)",
                 font=('Arial', 10, 'bold')).grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(5, 5))

        # YouTube trim sliders frame
        yt_trim_frame = ttk.Frame(self.youtube_frame)
        yt_trim_frame.grid(row=6, column=0, columnspan=3, sticky=tk.EW, pady=5)
        yt_trim_frame.columnconfigure(1, weight=1)

        # Start time slider
        ttk.Label(yt_trim_frame, text="Start:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.yt_start_slider = tk.Scale(yt_trim_frame, from_=0, to=5.2, resolution=0.01,
                                        orient=tk.HORIZONTAL, variable=self.yt_trim_start,
                                        command=self.on_yt_trim_slider_changed, state=tk.DISABLED)
        self.yt_start_slider.grid(row=0, column=1, sticky=tk.EW, padx=5)
        self.yt_start_time_label = ttk.Label(yt_trim_frame, text="0.0s", width=8)
        self.yt_start_time_label.grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        self.yt_start_time_entry_field = ttk.Entry(yt_trim_frame, width=8)
        self.yt_start_time_entry_field.grid(row=0, column=3, sticky=tk.W, padx=(5, 0))
        self.yt_start_time_entry_field.insert(0, "0.0")
        self.yt_start_time_entry_field.bind('<Return>', self.on_yt_trim_entry_changed)
        self.yt_start_time_entry_field.bind('<FocusOut>', self.on_yt_trim_entry_changed)

        # End time slider
        ttk.Label(yt_trim_frame, text="End:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.yt_end_slider = tk.Scale(yt_trim_frame, from_=0, to=5.2, resolution=0.01,
                                      orient=tk.HORIZONTAL, variable=self.yt_trim_end,
                                      command=self.on_yt_trim_slider_changed, state=tk.DISABLED)
        self.yt_end_slider.grid(row=1, column=1, sticky=tk.EW, padx=5)
        self.yt_end_time_label = ttk.Label(yt_trim_frame, text="5.2s", width=8)
        self.yt_end_time_label.grid(row=1, column=2, sticky=tk.W, padx=(5, 0))
        self.yt_end_time_entry_field = ttk.Entry(yt_trim_frame, width=8)
        self.yt_end_time_entry_field.grid(row=1, column=3, sticky=tk.W, padx=(5, 0))
        self.yt_end_time_entry_field.insert(0, "5.2")
        self.yt_end_time_entry_field.bind('<Return>', self.on_yt_trim_entry_changed)
        self.yt_end_time_entry_field.bind('<FocusOut>', self.on_yt_trim_entry_changed)

        # Duration display
        self.yt_duration_label = ttk.Label(yt_trim_frame, text="Duration: 5.2s",
                                          font=('Arial', 9, 'bold'))
        self.yt_duration_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

        # YouTube player button
        self.play_youtube_btn = ttk.Button(self.youtube_frame, text="▶ Preview on YouTube",
                                          command=self.open_youtube_preview, state=tk.DISABLED)
        self.play_youtube_btn.grid(row=7, column=0, columnspan=3, pady=10)

        # Old manual timestamps (kept for compatibility)
        ttk.Separator(self.youtube_frame, orient=tk.HORIZONTAL).grid(
            row=8, column=0, columnspan=3, sticky=tk.EW, pady=(10, 10))

        ttk.Label(self.youtube_frame, text="Or use manual timestamps:").grid(
            row=9, column=0, columnspan=3, sticky=tk.W, pady=(5, 5))

        ttk.Label(self.youtube_frame, text="Start Time (MM:SS):").grid(row=10, column=0, sticky=tk.W, pady=5)
        self.start_time_entry = ttk.Entry(self.youtube_frame, width=20)
        self.start_time_entry.grid(row=10, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.start_time_entry.insert(0, "0:00")

        ttk.Label(self.youtube_frame, text="End Time (MM:SS):").grid(row=11, column=0, sticky=tk.W, pady=5)
        self.end_time_entry = ttk.Entry(self.youtube_frame, width=20)
        self.end_time_entry.grid(row=11, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.end_time_entry.insert(0, "0:07")

        # Local file fields (row 2-5)
        self.local_frame = ttk.Frame(container)
        # Don't grid it yet, will be shown when local mode is selected

        # File selection
        ttk.Label(self.local_frame, text="Audio File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.local_file_entry = ttk.Entry(self.local_frame, width=40, state='readonly')
        self.local_file_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(10, 0))
        ttk.Button(self.local_frame, text="Browse", command=self.browse_local_file).grid(
            row=0, column=2, pady=5, padx=(5, 0))

        # Show sounds folder files
        ttk.Label(self.local_frame, text="Or select from sounds folder:").grid(
            row=1, column=0, columnspan=3, sticky=tk.W, pady=(10, 5))

        sounds_list_frame = ttk.Frame(self.local_frame)
        sounds_list_frame.grid(row=2, column=0, columnspan=3, sticky=tk.NSEW, pady=5)

        scrollbar = ttk.Scrollbar(sounds_list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.sounds_listbox = tk.Listbox(sounds_list_frame, height=5, yscrollcommand=scrollbar.set)
        self.sounds_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.sounds_listbox.yview)
        self.sounds_listbox.bind('<<ListboxSelect>>', self.on_sound_file_selected)

        # Trim Slider Section
        ttk.Separator(self.local_frame, orient=tk.HORIZONTAL).grid(
            row=3, column=0, columnspan=3, sticky=tk.EW, pady=(10, 10))

        ttk.Label(self.local_frame, text="Audio Trimmer (1.0s - 5.2s max)",
                 font=('Arial', 10, 'bold')).grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(5, 5))

        # Audio info display
        self.audio_info_label = ttk.Label(self.local_frame, text="Load an audio file to enable trimmer",
                                         font=('Arial', 9), foreground='gray')
        self.audio_info_label.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))

        # Trim sliders frame
        trim_frame = ttk.Frame(self.local_frame)
        trim_frame.grid(row=6, column=0, columnspan=3, sticky=tk.EW, pady=5)
        trim_frame.columnconfigure(1, weight=1)

        # Start time slider
        ttk.Label(trim_frame, text="Start:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.start_slider = tk.Scale(trim_frame, from_=0, to=5.2, resolution=0.01,
                                     orient=tk.HORIZONTAL, variable=self.trim_start,
                                     command=self.on_trim_slider_changed, state=tk.DISABLED)
        self.start_slider.grid(row=0, column=1, sticky=tk.EW, padx=5)
        self.start_time_label = ttk.Label(trim_frame, text="0.0s", width=8)
        self.start_time_label.grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        self.start_time_entry_field = ttk.Entry(trim_frame, width=8)
        self.start_time_entry_field.grid(row=0, column=3, sticky=tk.W, padx=(5, 0))
        self.start_time_entry_field.insert(0, "0.0")
        self.start_time_entry_field.bind('<Return>', self.on_trim_entry_changed)
        self.start_time_entry_field.bind('<FocusOut>', self.on_trim_entry_changed)

        # End time slider
        ttk.Label(trim_frame, text="End:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.end_slider = tk.Scale(trim_frame, from_=0, to=5.2, resolution=0.01,
                                   orient=tk.HORIZONTAL, variable=self.trim_end,
                                   command=self.on_trim_slider_changed, state=tk.DISABLED)
        self.end_slider.grid(row=1, column=1, sticky=tk.EW, padx=5)
        self.end_time_label = ttk.Label(trim_frame, text="5.2s", width=8)
        self.end_time_label.grid(row=1, column=2, sticky=tk.W, padx=(5, 0))
        self.end_time_entry_field = ttk.Entry(trim_frame, width=8)
        self.end_time_entry_field.grid(row=1, column=3, sticky=tk.W, padx=(5, 0))
        self.end_time_entry_field.insert(0, "5.2")
        self.end_time_entry_field.bind('<Return>', self.on_trim_entry_changed)
        self.end_time_entry_field.bind('<FocusOut>', self.on_trim_entry_changed)

        # Duration display
        self.duration_label = ttk.Label(trim_frame, text="Duration: 5.2s",
                                       font=('Arial', 9, 'bold'))
        self.duration_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

        # Old clipping timestamps for local files (kept for YouTube mode compatibility)
        ttk.Separator(self.local_frame, orient=tk.HORIZONTAL).grid(
            row=7, column=0, columnspan=3, sticky=tk.EW, pady=(10, 10))

        ttk.Label(self.local_frame, text="Or use manual timestamps:").grid(
            row=8, column=0, columnspan=3, sticky=tk.W, pady=(5, 5))

        ttk.Label(self.local_frame, text="Start Time (MM:SS):").grid(row=9, column=0, sticky=tk.W, pady=5)
        self.local_start_time_entry = ttk.Entry(self.local_frame, width=20)
        self.local_start_time_entry.grid(row=9, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.local_start_time_entry.insert(0, "0:00")

        ttk.Label(self.local_frame, text="End Time (MM:SS):").grid(row=10, column=0, sticky=tk.W, pady=5)
        self.local_end_time_entry = ttk.Entry(self.local_frame, width=20)
        self.local_end_time_entry.grid(row=10, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.local_end_time_entry.insert(0, "")

        ttk.Label(self.local_frame, text="Leave end time empty to use entire file",
                 font=('Arial', 8), foreground='gray').grid(row=10, column=1, sticky=tk.W, pady=(35, 0), padx=(10, 0))

        # Preview button
        self.preview_btn = ttk.Button(container, text="Create Preview",
                                      command=self.create_preview, style='Action.TButton')
        self.preview_btn.grid(row=6, column=0, columnspan=3, pady=20)

        # Play preview button (initially disabled)
        self.play_preview_btn = ttk.Button(container, text="Play Preview",
                                           command=self.play_preview, state=tk.DISABLED)
        self.play_preview_btn.grid(row=7, column=0, columnspan=3, pady=5)

        # Separator
        ttk.Separator(container, orient=tk.HORIZONTAL).grid(row=8, column=0, columnspan=3,
                                                             sticky=tk.EW, pady=20)

        # Sound details
        ttk.Label(container, text="Sound Details", style='Header.TLabel').grid(
            row=9, column=0, columnspan=3, pady=(0, 10))

        ttk.Label(container, text="Sound Name:").grid(row=10, column=0, sticky=tk.W, pady=5)
        self.sound_name_entry = ttk.Entry(container, width=30)
        self.sound_name_entry.grid(row=10, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        ttk.Label(container, text="Discord Server:").grid(row=11, column=0, sticky=tk.W, pady=5)
        self.guild_display_label = ttk.Label(container, text="Loading...", font=('Arial', 10))
        self.guild_display_label.grid(row=11, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))

        ttk.Label(container, text="Volume (0.0-1.0):").grid(row=12, column=0, sticky=tk.W, pady=5)
        self.volume_entry = ttk.Entry(container, width=10)
        self.volume_entry.grid(row=12, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.volume_entry.insert(0, "1.0")

        ttk.Label(container, text="Emoji (optional):").grid(row=13, column=0, sticky=tk.W, pady=5)
        self.emoji_entry = ttk.Entry(container, width=10)
        self.emoji_entry.grid(row=13, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        # Create sound button
        self.create_sound_btn = ttk.Button(container, text="Upload to Discord",
                                           command=self.create_sound_from_youtube,
                                           style='Action.TButton', state=tk.DISABLED)
        self.create_sound_btn.grid(row=14, column=0, columnspan=3, pady=20)

        # Configure grid weights
        container.columnconfigure(1, weight=1)

        # Initialize with YouTube mode
        self.on_source_mode_changed()

    def create_bulk_upload_tab(self):
        """Create bulk upload tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Bulk Upload")

        container = ttk.Frame(tab, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(container, text="Bulk Upload Sounds from Directory",
                  style='Header.TLabel').grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Guild selection
        ttk.Label(container, text="Guild:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.bulk_guild_combo = ttk.Combobox(container, width=40, state='readonly')
        self.bulk_guild_combo.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        # Directory selection
        ttk.Label(container, text="Sounds Directory:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.bulk_dir_entry = ttk.Entry(container, width=40)
        self.bulk_dir_entry.grid(row=2, column=1, sticky=tk.EW, pady=5, padx=(10, 0))
        ttk.Button(container, text="Browse", command=self.browse_directory).grid(
            row=2, column=2, pady=5, padx=(5, 0))

        # Volume
        ttk.Label(container, text="Volume (0.0-1.0):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.bulk_volume_entry = ttk.Entry(container, width=10)
        self.bulk_volume_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.bulk_volume_entry.insert(0, "1.0")

        # Upload button
        ttk.Button(container, text="Upload All", command=self.bulk_upload_sounds,
                   style='Action.TButton').grid(row=4, column=0, columnspan=3, pady=20)

        # Progress area
        progress_label_frame = ttk.Frame(container)
        progress_label_frame.grid(row=5, column=0, columnspan=3, sticky=tk.EW, pady=(10, 5))
        ttk.Label(progress_label_frame, text="Progress:").pack(side=tk.LEFT)
        ttk.Button(progress_label_frame, text="Copy Log",
                  command=self.copy_bulk_progress).pack(side=tk.RIGHT)

        self.bulk_progress = scrolledtext.ScrolledText(container, height=15, width=70, state=tk.DISABLED)
        self.bulk_progress.grid(row=6, column=0, columnspan=3, sticky=tk.NSEW, pady=5)

        container.columnconfigure(1, weight=1)
        container.rowconfigure(6, weight=1)

    def create_sounds_list_tab(self):
        """Create sounds list/management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Manage Sounds")

        container = ttk.Frame(tab, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(container, text="Soundboard Sounds",
                  style='Header.TLabel').grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Guild selection
        ttk.Label(container, text="Guild:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.list_guild_combo = ttk.Combobox(container, width=40, state='readonly')
        self.list_guild_combo.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        # Refresh button
        ttk.Button(container, text="Load Sounds", command=self.load_sounds).grid(
            row=2, column=0, columnspan=2, pady=10)

        # Sounds treeview
        tree_frame = ttk.Frame(container)
        tree_frame.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW, pady=10)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Treeview
        self.sounds_tree = ttk.Treeview(tree_frame, columns=('ID', 'Name', 'Emoji', 'Volume'),
                                        show='headings', yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.sounds_tree.yview)

        self.sounds_tree.heading('ID', text='Sound ID')
        self.sounds_tree.heading('Name', text='Name')
        self.sounds_tree.heading('Emoji', text='Emoji')
        self.sounds_tree.heading('Volume', text='Volume')

        self.sounds_tree.column('ID', width=150)
        self.sounds_tree.column('Name', width=250)
        self.sounds_tree.column('Emoji', width=100)
        self.sounds_tree.column('Volume', width=100)

        self.sounds_tree.pack(fill=tk.BOTH, expand=True)

        # Delete button
        ttk.Button(container, text="Delete Selected", command=self.delete_sound,
                   style='Action.TButton').grid(row=4, column=0, columnspan=2, pady=10)

        container.columnconfigure(1, weight=1)
        container.rowconfigure(3, weight=1)

    def create_settings_tab(self):
        """Create settings/info tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Settings & Info")

        container = ttk.Frame(tab, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Bot info
        ttk.Label(container, text="Bot Information", style='Header.TLabel').pack(pady=(0, 10))

        self.bot_info_text = scrolledtext.ScrolledText(container, height=10, width=70, state=tk.DISABLED)
        self.bot_info_text.pack(pady=10, fill=tk.BOTH, expand=True)

        # Refresh button
        ttk.Button(container, text="Refresh Bot Info", command=self.refresh_bot_info).pack(pady=10)

    def initialize_discord(self):
        """Initialize Discord authentication in background thread"""
        def init():
            try:
                self.status_var.set("Connecting to Discord...")

                # Load default guild ID from .env file
                from dotenv import load_dotenv
                load_dotenv()
                self.default_guild_id = os.getenv('DISCORD_GUILD_ID')

                self.discord = DiscordAuth()
                self.soundboard = SoundboardManager(self.discord)
                self.youtube_converter = YouTubeToSound(self.soundboard, output_dir="sounds")

                # Get bot info
                self.bot_info = self.discord.get_bot_info()
                self.guilds = self.discord.get_guilds()

                # Update GUI with guild info
                self.root.after(0, self.update_guild_combos)
                self.root.after(0, lambda: self.status_var.set("Connected to Discord"))
                self.root.after(0, self.refresh_bot_info)

            except Exception as e:
                error_msg = f"Failed to connect to Discord: {str(e)}"
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: self.show_error("Connection Error", error_msg, e))

        thread = threading.Thread(target=init, daemon=True)
        thread.start()

    def update_guild_combos(self):
        """Update guild display with available guilds"""
        print(f"update_guild_combos called. Guilds: {len(self.guilds)}, Default ID: {self.default_guild_id}")

        if self.guilds:
            # Try to find the default guild from .env file
            default_index = 0
            guild_name = "Unknown"
            found_guild = False

            if self.default_guild_id:
                print(f"Looking for guild ID: {self.default_guild_id}")
                for i, guild in enumerate(self.guilds):
                    print(f"Checking guild: {guild['name']} (ID: {guild['id']})")
                    if guild['id'] == self.default_guild_id:
                        default_index = i
                        guild_name = guild['name']
                        self.selected_guild_id = self.default_guild_id
                        found_guild = True
                        print(f"Auto-selected default guild from .env: {guild_name}")
                        break

                if not found_guild:
                    print(f"WARNING: Guild ID {self.default_guild_id} not found in bot's guilds")
                    # Still use the default_guild_id even if not found
                    self.selected_guild_id = self.default_guild_id
                    guild_name = "Unknown"
            else:
                # If no default guild ID in .env, use the first guild
                if self.guilds:
                    self.selected_guild_id = self.guilds[0]['id']
                    guild_name = self.guilds[0]['name']
                    print(f"No default guild in .env, using first guild: {guild_name}")

            # Update the display label in YouTube tab
            if self.selected_guild_id:
                display_text = f"{guild_name} ({self.selected_guild_id})"
                print(f"Setting guild display to: {display_text}")
                try:
                    self.guild_display_label.config(text=display_text)
                    print("Guild display label updated successfully")
                except Exception as e:
                    print(f"ERROR updating guild display label: {e}")
            else:
                print("No guild selected, showing Unknown")
                try:
                    self.guild_display_label.config(text="Unknown")
                except Exception as e:
                    print(f"ERROR updating guild display label: {e}")
        else:
            print("No guilds available")
            self.guild_display_label.config(text="Unknown (no guilds)")

    def on_source_mode_changed(self):
        """Handle source mode radio button change"""
        mode = self.source_mode.get()

        if mode == "youtube":
            # Show YouTube frame, hide local frame
            self.youtube_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=10)
            self.local_frame.grid_forget()
        else:  # local
            # Hide YouTube frame, show local frame
            self.youtube_frame.grid_forget()
            self.local_frame.grid(row=2, column=0, columnspan=3, sticky=tk.NSEW, pady=10)
            # Load sounds from sounds folder
            self.refresh_sounds_list()

    def refresh_sounds_list(self):
        """Refresh the list of MP3 files in the sounds folder"""
        self.sounds_listbox.delete(0, tk.END)

        sounds_dir = Path("sounds")
        if sounds_dir.exists():
            mp3_files = sorted(sounds_dir.glob("*.mp3"))
            for mp3_file in mp3_files:
                self.sounds_listbox.insert(tk.END, mp3_file.name)

    def browse_local_file(self):
        """Browse for a local MP3 file"""
        file_path = filedialog.askopenfilename(
            title="Select MP3 File",
            filetypes=[("MP3 Files", "*.mp3"), ("All Files", "*.*")],
            initialdir=str(Path("sounds").absolute())
        )

        if file_path:
            # Validate it's an MP3
            if not file_path.lower().endswith('.mp3'):
                messagebox.showerror("Invalid File", "Please select an MP3 file.")
                return

            self.selected_local_file = file_path
            self.local_file_entry.config(state='normal')
            self.local_file_entry.delete(0, tk.END)
            self.local_file_entry.insert(0, file_path)
            self.local_file_entry.config(state='readonly')

            # Clear listbox selection
            self.sounds_listbox.selection_clear(0, tk.END)

            # Load audio duration for trim slider
            self.load_audio_duration(file_path)

    def on_sound_file_selected(self, event):
        """Handle selection from sounds folder listbox"""
        selection = self.sounds_listbox.curselection()
        if selection:
            filename = self.sounds_listbox.get(selection[0])
            file_path = str((Path("sounds") / filename).absolute())
            self.selected_local_file = file_path

            self.local_file_entry.config(state='normal')
            self.local_file_entry.delete(0, tk.END)
            self.local_file_entry.insert(0, file_path)
            self.local_file_entry.config(state='readonly')

            # Load audio duration for trim slider
            self.load_audio_duration(file_path)

    def load_audio_duration(self, file_path):
        """Load audio file and get its duration, then setup trim sliders"""
        try:
            from pydub import AudioSegment

            # Load audio file
            audio = AudioSegment.from_file(file_path)
            duration_seconds = len(audio) / 1000.0  # Convert ms to seconds
            self.audio_duration = duration_seconds
            self.loaded_audio_path = file_path

            # Update UI with audio info
            self.audio_info_label.config(
                text=f"Audio loaded: {duration_seconds:.1f}s total duration",
                foreground='green'
            )

            # Configure sliders based on duration
            max_end = min(duration_seconds, 5.2)  # Can't exceed Discord limit or file duration

            # Set slider ranges
            self.start_slider.config(from_=0, to=max_end, state=tk.NORMAL)
            self.end_slider.config(from_=0, to=max_end, state=tk.NORMAL)

            # Enable entry fields
            self.start_time_entry_field.config(state=tk.NORMAL)
            self.end_time_entry_field.config(state=tk.NORMAL)

            # Set initial values (try to select first 5.2s or whole file if shorter)
            self.trim_start.set(0.0)
            self.trim_end.set(max_end)

            # Update labels
            self.update_trim_labels()

        except Exception as e:
            self.audio_info_label.config(
                text=f"Error loading audio: {str(e)}",
                foreground='red'
            )
            self.start_slider.config(state=tk.DISABLED)
            self.end_slider.config(state=tk.DISABLED)
            self.start_time_entry_field.config(state=tk.DISABLED)
            self.end_time_entry_field.config(state=tk.DISABLED)

    def on_trim_slider_changed(self, value=None):
        """Handle trim slider changes - enforce constraints"""
        start = self.trim_start.get()
        end = self.trim_end.get()

        # Minimum duration constraint (1.0 seconds)
        min_duration = 1.0
        # Maximum duration constraint (5.2 seconds)
        max_duration = 5.2

        # Calculate current duration
        duration = end - start

        # If duration is too short, adjust the other slider
        if duration < min_duration:
            # Determine which slider was moved (approximately)
            if value is not None:
                # Try to adjust the other slider to maintain minimum duration
                if abs(float(value) - start) < 0.01:  # Start slider moved
                    new_end = start + min_duration
                    if new_end <= self.audio_duration:
                        self.trim_end.set(new_end)
                    else:
                        # Can't extend end, move start back
                        self.trim_start.set(max(0, end - min_duration))
                else:  # End slider moved
                    new_start = end - min_duration
                    if new_start >= 0:
                        self.trim_start.set(new_start)
                    else:
                        # Can't extend start, move end forward
                        self.trim_end.set(min(self.audio_duration, start + min_duration))

        # If duration is too long, adjust
        elif duration > max_duration:
            if value is not None:
                if abs(float(value) - start) < 0.01:  # Start slider moved
                    # Adjust end to maintain max duration
                    self.trim_end.set(min(start + max_duration, self.audio_duration))
                else:  # End slider moved
                    # Adjust start to maintain max duration
                    self.trim_start.set(max(0, end - max_duration))

        # Ensure start is never after end
        if self.trim_start.get() >= self.trim_end.get():
            if value is not None:
                if abs(float(value) - start) < 0.01:  # Start slider moved
                    self.trim_start.set(max(0, self.trim_end.get() - 0.1))
                else:
                    self.trim_end.set(min(self.audio_duration, self.trim_start.get() + 0.1))

        # Update labels
        self.update_trim_labels()

    def update_trim_labels(self):
        """Update the trim slider time labels and duration display"""
        start = self.trim_start.get()
        end = self.trim_end.get()
        duration = end - start

        self.start_time_label.config(text=f"{start:.2f}s")
        self.end_time_label.config(text=f"{end:.2f}s")
        self.duration_label.config(text=f"Duration: {duration:.2f}s")

        # Update entry fields to match sliders
        self.start_time_entry_field.delete(0, tk.END)
        self.start_time_entry_field.insert(0, f"{start:.2f}")
        self.end_time_entry_field.delete(0, tk.END)
        self.end_time_entry_field.insert(0, f"{end:.2f}")

        # Color code duration based on validity
        if duration < 1.0:
            self.duration_label.config(foreground='red')
        elif duration > 5.2:
            self.duration_label.config(foreground='orange')
        else:
            self.duration_label.config(foreground='green')

    def on_trim_entry_changed(self, event=None):
        """Handle when user types in the trim entry fields"""
        try:
            # Get values from entry fields
            start_text = self.start_time_entry_field.get().strip()
            end_text = self.end_time_entry_field.get().strip()

            # Parse the values
            start_val = float(start_text)
            end_val = float(end_text)

            # Validate ranges
            if start_val < 0:
                start_val = 0
            if end_val > self.audio_duration:
                end_val = self.audio_duration

            # Update the slider variables (this will trigger on_trim_slider_changed)
            self.trim_start.set(start_val)
            self.trim_end.set(end_val)

        except ValueError:
            # Invalid input, revert to slider values
            self.update_trim_labels()

    def load_youtube_video_info(self):
        """Load YouTube video information and setup trim sliders"""
        def load():
            try:
                youtube_url = self.youtube_url_entry.get().strip()
                if not youtube_url:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Please enter a YouTube URL"))
                    return

                self.root.after(0, lambda: self.youtube_info_label.config(
                    text="Loading video info...", foreground='blue'))

                # Get video info
                video_info = self.youtube_converter.get_video_info(youtube_url)
                duration_seconds = video_info['duration']
                title = video_info['title']
                video_id = video_info['video_id']

                # Store video info
                self.yt_audio_duration = duration_seconds
                self.loaded_audio_path = youtube_url
                self.youtube_video_id = video_id

                # Update UI
                def update_ui():
                    self.youtube_info_label.config(
                        text=f"Video: {title} ({duration_seconds:.1f}s total)",
                        foreground='green'
                    )

                    # Configure sliders to show full video duration
                    # The slider range should be the full video, but selection is constrained to 5.2s
                    self.yt_start_slider.config(from_=0, to=duration_seconds, state=tk.NORMAL)
                    self.yt_end_slider.config(from_=0, to=duration_seconds, state=tk.NORMAL)

                    # Enable entry fields
                    self.yt_start_time_entry_field.config(state=tk.NORMAL)
                    self.yt_end_time_entry_field.config(state=tk.NORMAL)

                    # Set initial values - select first 5.2s (or whole video if shorter)
                    initial_end = min(duration_seconds, 5.2)
                    self.yt_trim_start.set(0.0)
                    self.yt_trim_end.set(initial_end)

                    # Update labels
                    self.update_yt_trim_labels()

                    # Enable preview button
                    self.play_youtube_btn.config(state=tk.NORMAL)

                self.root.after(0, update_ui)

            except Exception as e:
                error_msg = f"Failed to load video info: {str(e)}"
                self.root.after(0, lambda: self.youtube_info_label.config(
                    text=error_msg, foreground='red'))
                self.root.after(0, lambda: self.show_error("Video Load Error", error_msg, e))

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def on_yt_trim_slider_changed(self, value=None):
        """Handle YouTube trim slider changes - enforce constraints"""
        start = self.yt_trim_start.get()
        end = self.yt_trim_end.get()

        min_duration = 1.0
        max_duration = 5.2
        duration = end - start

        # If duration is too short, adjust the other slider
        if duration < min_duration:
            if value is not None:
                if abs(float(value) - start) < 0.01:  # Start slider moved
                    new_end = start + min_duration
                    if new_end <= self.yt_audio_duration:
                        self.yt_trim_end.set(new_end)
                    else:
                        self.yt_trim_start.set(max(0, end - min_duration))
                else:  # End slider moved
                    new_start = end - min_duration
                    if new_start >= 0:
                        self.yt_trim_start.set(new_start)
                    else:
                        self.yt_trim_end.set(min(self.yt_audio_duration, start + min_duration))

        # If duration is too long, adjust
        elif duration > max_duration:
            if value is not None:
                if abs(float(value) - start) < 0.01:  # Start slider moved
                    self.yt_trim_end.set(min(start + max_duration, self.yt_audio_duration))
                else:  # End slider moved
                    self.yt_trim_start.set(max(0, end - max_duration))

        # Ensure start is never after end
        if self.yt_trim_start.get() >= self.yt_trim_end.get():
            if value is not None:
                if abs(float(value) - start) < 0.01:  # Start slider moved
                    self.yt_trim_start.set(max(0, self.yt_trim_end.get() - 0.1))
                else:
                    self.yt_trim_end.set(min(self.yt_audio_duration, self.yt_trim_start.get() + 0.1))

        # Update labels
        self.update_yt_trim_labels()

    def update_yt_trim_labels(self):
        """Update the YouTube trim slider time labels and duration display"""
        start = self.yt_trim_start.get()
        end = self.yt_trim_end.get()
        duration = end - start

        self.yt_start_time_label.config(text=f"{start:.2f}s")
        self.yt_end_time_label.config(text=f"{end:.2f}s")
        self.yt_duration_label.config(text=f"Duration: {duration:.2f}s")

        # Update entry fields to match sliders
        self.yt_start_time_entry_field.delete(0, tk.END)
        self.yt_start_time_entry_field.insert(0, f"{start:.2f}")
        self.yt_end_time_entry_field.delete(0, tk.END)
        self.yt_end_time_entry_field.insert(0, f"{end:.2f}")

        # Color code duration based on validity
        if duration < 1.0:
            self.yt_duration_label.config(foreground='red')
        elif duration > 5.2:
            self.yt_duration_label.config(foreground='orange')
        else:
            self.yt_duration_label.config(foreground='green')

    def on_yt_trim_entry_changed(self, event=None):
        """Handle when user types in the YouTube trim entry fields"""
        try:
            # Get values from entry fields
            start_text = self.yt_start_time_entry_field.get().strip()
            end_text = self.yt_end_time_entry_field.get().strip()

            # Parse the values
            start_val = float(start_text)
            end_val = float(end_text)

            # Validate ranges
            if start_val < 0:
                start_val = 0
            if end_val > self.yt_audio_duration:
                end_val = self.yt_audio_duration

            # Update the slider variables (this will trigger on_yt_trim_slider_changed)
            self.yt_trim_start.set(start_val)
            self.yt_trim_end.set(end_val)

        except ValueError:
            # Invalid input, revert to slider values
            self.update_yt_trim_labels()

    def open_youtube_preview(self):
        """Open YouTube video in web browser with start time"""
        if not hasattr(self, 'youtube_video_id') or not self.youtube_video_id:
            messagebox.showerror("Error", "Please load video info first")
            return

        import webbrowser
        start_seconds = int(self.yt_trim_start.get())
        end_seconds = int(self.yt_trim_end.get())

        # YouTube URL with start time parameter
        youtube_url = f"https://www.youtube.com/watch?v={self.youtube_video_id}&t={start_seconds}s"

        webbrowser.open(youtube_url)
        messagebox.showinfo("Preview",
            f"Opening YouTube video at {start_seconds}s in your browser.\n\n"
            f"Listen from {start_seconds}s to {end_seconds}s to preview your clip.")

    def create_preview(self):
        """Create preview from YouTube or local file"""
        mode = self.source_mode.get()

        if mode == "youtube":
            self.create_preview_youtube()
        else:
            self.create_preview_local()

    def create_preview_local(self):
        """Create preview from local MP3 file"""
        def create():
            try:
                if not self.selected_local_file:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Please select an MP3 file"))
                    return

                local_file_path = Path(self.selected_local_file)
                if not local_file_path.exists():
                    self.root.after(0, lambda: messagebox.showerror("Error", "Selected file does not exist"))
                    return

                # Check if manual timestamps are provided, otherwise use trim sliders
                start_time_manual = self.local_start_time_entry.get().strip()
                end_time_manual = self.local_end_time_entry.get().strip()

                # Determine which method to use
                use_manual_timestamps = bool(end_time_manual)  # If end time is filled, use manual

                if use_manual_timestamps:
                    start_time = start_time_manual
                    end_time = end_time_manual
                else:
                    # Use trim slider values (convert seconds to MM:SS format)
                    start_seconds = self.trim_start.get()
                    end_seconds = self.trim_end.get()

                    # Validate duration
                    duration = end_seconds - start_seconds
                    if duration < 1.0:
                        self.root.after(0, lambda: messagebox.showerror("Error",
                            "Duration must be at least 1.0 seconds. Please adjust the trim sliders."))
                        return
                    if duration > 5.2:
                        self.root.after(0, lambda: messagebox.showerror("Error",
                            "Duration cannot exceed 5.2 seconds. Please adjust the trim sliders."))
                        return

                    # Convert to MM:SS format
                    start_time = self.seconds_to_mmss(start_seconds)
                    end_time = self.seconds_to_mmss(end_seconds)

                self.root.after(0, lambda: self.status_var.set("Creating preview from local file..."))
                self.root.after(0, lambda: self.preview_btn.config(state=tk.DISABLED))

                # Stop any playing audio first and release file handles
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()

                try:
                    pygame.mixer.music.unload()
                except:
                    pass

                time.sleep(0.5)

                # Clean up old preview files
                if self.preview_audio_path:
                    self.safe_remove_file(self.preview_audio_path)
                if self.downloaded_audio_path:
                    self.safe_remove_file(self.downloaded_audio_path)

                # Determine output filename
                base_name = local_file_path.stem
                output_filename = f"{base_name}_clip.mp3"
                output_path = Path("sounds") / output_filename

                # Check for file collision
                if output_path.exists():
                    overwrite = messagebox.askyesno(
                        "File Exists",
                        f"The file '{output_filename}' already exists.\n\nDo you want to overwrite it?"
                    )
                    if not overwrite:
                        self.root.after(0, lambda: self.preview_btn.config(state=tk.NORMAL))
                        return

                # Check if we need to clip or just use the file as-is
                if end_time and start_time != "0:00":
                    # Need to clip the audio
                    from pydub import AudioSegment

                    audio = AudioSegment.from_file(str(local_file_path))

                    # Parse timestamps
                    start_ms = self.parse_timestamp(start_time)
                    end_ms = self.parse_timestamp(end_time)

                    if start_ms >= end_ms:
                        self.root.after(0, lambda: messagebox.showerror("Error", "Start time must be before end time"))
                        self.root.after(0, lambda: self.preview_btn.config(state=tk.NORMAL))
                        return

                    # Check if end time exceeds duration
                    duration_ms = len(audio)
                    if end_ms > duration_ms:
                        self.root.after(0, lambda: messagebox.showerror("Error",
                            f"End time ({end_time}) exceeds audio duration ({duration_ms / 1000:.2f} seconds)"))
                        self.root.after(0, lambda: self.preview_btn.config(state=tk.NORMAL))
                        return

                    # Clip the audio
                    clipped = audio[start_ms:end_ms]

                    # Export with quality adjustment to stay under 512KB
                    max_size_bytes = 512 * 1024
                    bitrates = ['128k', '96k', '64k', '48k', '32k']

                    for bitrate in bitrates:
                        clipped.export(str(output_path), format='mp3', bitrate=bitrate, parameters=["-ac", "1"])
                        time.sleep(0.3)

                        file_size = output_path.stat().st_size
                        print(f"Exported at {bitrate} bitrate: {file_size / 1024:.2f} KB")

                        if file_size <= max_size_bytes:
                            break

                    if output_path.stat().st_size > max_size_bytes:
                        self.root.after(0, lambda: messagebox.showerror("Error",
                            "Clipped audio is too large even at lowest quality. Try a shorter clip."))
                        self.root.after(0, lambda: self.preview_btn.config(state=tk.NORMAL))
                        return

                    self.preview_audio_path = str(output_path.absolute())
                else:
                    # No clipping needed, check if file is already under 512KB
                    file_size = local_file_path.stat().st_size
                    if file_size > 512 * 1024:
                        self.root.after(0, lambda: messagebox.showerror("Error",
                            f"File is too large ({file_size / 1024:.2f} KB). Maximum is 512 KB.\n\n"
                            "Please clip the audio or select a smaller file."))
                        self.root.after(0, lambda: self.preview_btn.config(state=tk.NORMAL))
                        return

                    # Copy file to preview location
                    import shutil
                    shutil.copy2(str(local_file_path), str(output_path))
                    self.preview_audio_path = str(output_path.absolute())

                self.downloaded_audio_path = None  # No downloaded file for local mode

                self.root.after(0, lambda: self.status_var.set("Preview created successfully"))
                self.root.after(0, lambda: self.play_preview_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.create_sound_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.preview_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: messagebox.showinfo("Success",
                    "Preview created! Click 'Play Preview' to listen."))

            except Exception as e:
                error_msg = f"Failed to create preview: {str(e)}"
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: self.show_error("Preview Error", error_msg, e))
                self.root.after(0, lambda: self.preview_btn.config(state=tk.NORMAL))

        thread = threading.Thread(target=create, daemon=True)
        thread.start()

    def parse_timestamp(self, timestamp: str) -> int:
        """Parse timestamp string to milliseconds"""
        timestamp = timestamp.strip()

        # Try HH:MM:SS format
        if timestamp.count(':') == 2:
            h, m, s = map(int, timestamp.split(':'))
            return (h * 3600 + m * 60 + s) * 1000
        # Try MM:SS format
        elif timestamp.count(':') == 1:
            m, s = map(int, timestamp.split(':'))
            return (m * 60 + s) * 1000
        # Try seconds only
        else:
            return int(timestamp) * 1000

    def seconds_to_mmss(self, seconds: float) -> str:
        """Convert seconds to MM:SS format"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def create_preview_youtube(self):
        """Create preview of YouTube audio clip"""
        def create():
            try:
                youtube_url = self.youtube_url_entry.get().strip()
                temp_sound_name = self.temp_sound_name_entry.get().strip()

                if not youtube_url:
                    self.root.after(0, lambda: messagebox.showerror("Error", "YouTube URL is required"))
                    return

                # Check if manual timestamps are provided, otherwise use trim sliders
                start_time_manual = self.start_time_entry.get().strip()
                end_time_manual = self.end_time_entry.get().strip()

                # Determine which method to use (prefer manual if both fields are filled)
                use_manual_timestamps = bool(start_time_manual and end_time_manual and (start_time_manual != "0:00" or end_time_manual != "0:07"))

                if use_manual_timestamps:
                    start_time = start_time_manual
                    end_time = end_time_manual
                else:
                    # Use YouTube trim slider values (convert seconds to MM:SS format)
                    start_seconds = self.yt_trim_start.get()
                    end_seconds = self.yt_trim_end.get()

                    # Validate duration
                    duration = end_seconds - start_seconds
                    if duration < 1.0:
                        self.root.after(0, lambda: messagebox.showerror("Error",
                            "Duration must be at least 1.0 seconds. Please adjust the trim sliders."))
                        return
                    if duration > 5.2:
                        self.root.after(0, lambda: messagebox.showerror("Error",
                            "Duration cannot exceed 5.2 seconds. Please adjust the trim sliders."))
                        return

                    # Convert to MM:SS format
                    start_time = self.seconds_to_mmss(start_seconds)
                    end_time = self.seconds_to_mmss(end_seconds)

                # Use temp sound name if provided, otherwise default to "preview"
                preview_name = temp_sound_name if temp_sound_name else "preview"

                self.root.after(0, lambda: self.status_var.set("Creating preview..."))
                self.root.after(0, lambda: self.preview_btn.config(state=tk.DISABLED))

                # Stop any playing audio first and release file handles
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()

                try:
                    pygame.mixer.music.unload()
                except:
                    pass

                time.sleep(0.5)

                # Clean up old preview files with retry (in this background thread)
                if self.preview_audio_path:
                    self.safe_remove_file(self.preview_audio_path)
                if self.downloaded_audio_path:
                    self.safe_remove_file(self.downloaded_audio_path)

                # Create preview
                downloaded, clipped = self.youtube_converter.create_preview_clip(
                    youtube_url=youtube_url,
                    start_time=start_time,
                    end_time=end_time,
                    preview_name=preview_name
                )

                self.downloaded_audio_path = downloaded
                self.preview_audio_path = clipped

                self.root.after(0, lambda: self.status_var.set("Preview created successfully"))
                self.root.after(0, lambda: self.play_preview_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.create_sound_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.preview_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: messagebox.showinfo("Success",
                    "Preview created! Click 'Play Preview' to listen."))

            except Exception as e:
                error_msg = f"Failed to create preview: {str(e)}"
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: self.show_error("Preview Error", error_msg, e))
                self.root.after(0, lambda: self.preview_btn.config(state=tk.NORMAL))

        thread = threading.Thread(target=create, daemon=True)
        thread.start()

    def play_preview(self):
        """Play the preview audio"""
        if not self.preview_audio_path or not os.path.exists(self.preview_audio_path):
            messagebox.showerror("Error", "No preview available. Create a preview first.")
            return

        def play():
            try:
                pygame.mixer.music.load(self.preview_audio_path)
                pygame.mixer.music.play()
                self.root.after(0, lambda: self.status_var.set("Playing preview..."))

                # Wait for playback to finish
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)

                # Unload the music to release the file handle
                pygame.mixer.music.unload()

                self.root.after(0, lambda: self.status_var.set("Preview finished"))
            except Exception as e:
                error_msg = f"Failed to play preview: {str(e)}"
                self.root.after(0, lambda: self.show_error("Playback Error", error_msg, e))
            finally:
                # Ensure file is released even if an error occurs
                try:
                    pygame.mixer.music.unload()
                except:
                    pass

        thread = threading.Thread(target=play, daemon=True)
        thread.start()

    def create_sound_from_youtube(self):
        """Upload the preview to Discord as a soundboard sound"""
        if not self.preview_audio_path or not os.path.exists(self.preview_audio_path):
            messagebox.showerror("Error", "No preview available. Create a preview first.")
            return

        sound_name = self.sound_name_entry.get().strip()
        if not sound_name:
            messagebox.showerror("Error", "Sound name is required")
            return

        if not self.selected_guild_id:
            messagebox.showerror("Error", "Please select a guild")
            return

        try:
            volume = float(self.volume_entry.get())
            if not 0.0 <= volume <= 1.0:
                raise ValueError()
        except:
            messagebox.showerror("Error", "Volume must be between 0.0 and 1.0")
            return

        emoji_name = self.emoji_entry.get().strip() or None

        def upload():
            try:
                # Get guild name for better feedback
                guild_name = "Unknown"
                for guild in self.guilds:
                    if guild['id'] == self.selected_guild_id:
                        guild_name = guild['name']
                        break

                status_msg = f"Uploading '{sound_name}' to {guild_name}..."
                self.root.after(0, lambda: self.status_var.set(status_msg))
                self.root.after(0, lambda: self.create_sound_btn.config(state=tk.DISABLED))

                sound = self.soundboard.create_soundboard_sound(
                    guild_id=self.selected_guild_id,
                    name=sound_name,
                    sound_file_path=self.preview_audio_path,
                    volume=volume,
                    emoji_name=emoji_name
                )

                # Stop any playing audio and release handles
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()

                try:
                    pygame.mixer.music.unload()
                except:
                    pass

                time.sleep(0.5)

                # Clean up preview files safely
                if self.preview_audio_path:
                    self.safe_remove_file(self.preview_audio_path)
                if self.downloaded_audio_path:
                    self.safe_remove_file(self.downloaded_audio_path)

                self.preview_audio_path = None
                self.downloaded_audio_path = None

                # Get guild name for success message
                guild_name = "Unknown"
                for guild in self.guilds:
                    if guild['id'] == self.selected_guild_id:
                        guild_name = guild['name']
                        break

                success_msg = f"Successfully uploaded '{sound_name}' to {guild_name}!"
                self.root.after(0, lambda: self.status_var.set(success_msg))
                self.root.after(0, lambda: messagebox.showinfo("Success", success_msg))
                self.root.after(0, lambda: self.create_sound_btn.config(state=tk.DISABLED))
                self.root.after(0, lambda: self.play_preview_btn.config(state=tk.DISABLED))

                # Clear form
                self.root.after(0, self.clear_youtube_form)

            except Exception as e:
                error_msg = f"Failed to create sound: {str(e)}"
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: self.show_error("Upload Error", error_msg, e))
                self.root.after(0, lambda: self.create_sound_btn.config(state=tk.NORMAL))

        thread = threading.Thread(target=upload, daemon=True)
        thread.start()

    def clear_youtube_form(self):
        """Clear the YouTube form fields"""
        self.temp_sound_name_entry.delete(0, tk.END)
        self.youtube_url_entry.delete(0, tk.END)
        self.sound_name_entry.delete(0, tk.END)
        self.emoji_entry.delete(0, tk.END)
        self.start_time_entry.delete(0, tk.END)
        self.start_time_entry.insert(0, "0:00")
        self.end_time_entry.delete(0, tk.END)
        self.end_time_entry.insert(0, "0:05")

    def browse_directory(self):
        """Browse for sounds directory"""
        directory = filedialog.askdirectory(title="Select Sounds Directory")
        if directory:
            self.bulk_dir_entry.delete(0, tk.END)
            self.bulk_dir_entry.insert(0, directory)

    def bulk_upload_sounds(self):
        """Bulk upload sounds from directory"""
        selection = self.bulk_guild_combo.get()
        if not selection:
            messagebox.showerror("Error", "Please select a guild")
            return

        guild_id = selection.split('(')[-1].rstrip(')')
        directory = self.bulk_dir_entry.get().strip()

        if not directory:
            messagebox.showerror("Error", "Please select a directory")
            return

        try:
            volume = float(self.bulk_volume_entry.get())
            if not 0.0 <= volume <= 1.0:
                raise ValueError()
        except:
            messagebox.showerror("Error", "Volume must be between 0.0 and 1.0")
            return

        def upload():
            try:
                self.root.after(0, lambda: self.log_bulk_progress("Starting bulk upload...\n"))
                self.root.after(0, lambda: self.status_var.set("Uploading sounds..."))

                # Redirect print to progress text
                import io
                from contextlib import redirect_stdout

                output_buffer = io.StringIO()
                with redirect_stdout(output_buffer):
                    created = self.soundboard.bulk_create_sounds(
                        guild_id=guild_id,
                        sounds_directory=directory,
                        volume=volume
                    )

                output_text = output_buffer.getvalue()
                self.root.after(0, lambda: self.log_bulk_progress(output_text))

                success_msg = f"Bulk upload complete: {len(created)} sounds created"
                self.root.after(0, lambda: self.status_var.set(success_msg))
                self.root.after(0, lambda: messagebox.showinfo("Success", success_msg))

            except Exception as e:
                error_msg = f"Bulk upload failed: {str(e)}"
                self.root.after(0, lambda: self.log_bulk_progress(f"\nError: {error_msg}\n"))
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: self.show_error("Bulk Upload Error", error_msg, e))

        thread = threading.Thread(target=upload, daemon=True)
        thread.start()

    def log_bulk_progress(self, message):
        """Log message to bulk progress text area"""
        self.bulk_progress.config(state=tk.NORMAL)
        self.bulk_progress.insert(tk.END, message)
        self.bulk_progress.see(tk.END)
        self.bulk_progress.config(state=tk.DISABLED)

    def copy_bulk_progress(self):
        """Copy bulk progress log to clipboard"""
        text = self.bulk_progress.get(1.0, tk.END)
        if text.strip():
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            messagebox.showinfo("Copied", "Progress log copied to clipboard!")
        else:
            messagebox.showinfo("Empty Log", "Nothing to copy - log is empty.")

    def load_sounds(self):
        """Load sounds from selected guild"""
        selection = self.list_guild_combo.get()
        if not selection:
            messagebox.showerror("Error", "Please select a guild")
            return

        guild_id = selection.split('(')[-1].rstrip(')')

        def load():
            try:
                self.root.after(0, lambda: self.status_var.set("Loading sounds..."))
                sounds = self.soundboard.list_soundboard_sounds(guild_id)

                self.root.after(0, lambda: self.populate_sounds_tree(sounds))
                self.root.after(0, lambda: self.status_var.set(f"Loaded {len(sounds)} sounds"))

            except Exception as e:
                error_msg = f"Failed to load sounds: {str(e)}"
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: self.show_error("Load Error", error_msg, e))

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def populate_sounds_tree(self, sounds):
        """Populate the sounds treeview with data"""
        # Clear existing items
        for item in self.sounds_tree.get_children():
            self.sounds_tree.delete(item)

        # Add sounds
        for sound in sounds:
            emoji = sound.get('emoji_name', '') or ''
            self.sounds_tree.insert('', tk.END, values=(
                sound['sound_id'],
                sound['name'],
                emoji,
                sound['volume']
            ))

    def delete_sound(self):
        """Delete selected sound"""
        selection = self.sounds_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a sound to delete")
            return

        item = self.sounds_tree.item(selection[0])
        sound_id = item['values'][0]
        sound_name = item['values'][1]

        if not messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete '{sound_name}'?"):
            return

        guild_selection = self.list_guild_combo.get()
        guild_id = guild_selection.split('(')[-1].rstrip(')')

        def delete():
            try:
                self.root.after(0, lambda: self.status_var.set("Deleting sound..."))
                self.soundboard.delete_soundboard_sound(guild_id, sound_id)

                self.root.after(0, lambda: self.sounds_tree.delete(selection[0]))
                self.root.after(0, lambda: self.status_var.set(f"Deleted sound: {sound_name}"))
                self.root.after(0, lambda: messagebox.showinfo("Success",
                    f"Successfully deleted '{sound_name}'"))

            except Exception as e:
                error_msg = f"Failed to delete sound: {str(e)}"
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: self.show_error("Delete Error", error_msg, e))

        thread = threading.Thread(target=delete, daemon=True)
        thread.start()

    def refresh_bot_info(self):
        """Refresh bot information display"""
        if not self.bot_info or not self.guilds:
            return

        self.bot_info_text.config(state=tk.NORMAL)
        self.bot_info_text.delete(1.0, tk.END)

        info = f"Bot ID: {self.bot_info['id']}\n"
        info += f"Bot Username: {self.bot_info['username']}\n\n"
        info += f"Guilds ({len(self.guilds)}):\n"
        info += "=" * 50 + "\n"

        for guild in self.guilds:
            info += f"  - {guild['name']}\n"
            info += f"    ID: {guild['id']}\n\n"

        self.bot_info_text.insert(1.0, info)
        self.bot_info_text.config(state=tk.DISABLED)


def main():
    """Main entry point for GUI application"""
    try:
        root = tk.Tk()
        app = SoundboardGUI(root)
        root.mainloop()
    except Exception as e:
        # Create a simple error window with traceback
        error_root = tk.Tk()
        error_root.withdraw()
        error_msg = f"Failed to start application: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        CopyableMessageDialog(error_root, "Application Error", error_msg, dialog_type="error")
        error_root.mainloop()
        sys.exit(1)


if __name__ == "__main__":
    main()
