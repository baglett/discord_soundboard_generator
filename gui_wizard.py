"""
Discord Soundboard Generator - GUI Application with Wizard Interface
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
from config_manager import ConfigManager
from settings_dialog import show_settings_dialog
from emoji_picker import show_emoji_picker
import pygame
import traceback
import time

# Try to import tkinterweb for embedded YouTube player
try:
    from tkinterweb import HtmlFrame
    TKINTERWEB_AVAILABLE = True
except ImportError:
    TKINTERWEB_AVAILABLE = False
    print("Warning: tkinterweb not available. YouTube player will be limited.")


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
    """Main GUI application for Discord Soundboard Generator with Wizard Interface"""

    def __init__(self, root: tk.Tk):
        """Initialize the GUI application"""
        self.root = root
        self.root.title("Discord Soundboard Generator")
        self.root.geometry("900x750")
        self.root.minsize(750, 600)

        # Initialize config manager
        self.config_manager = ConfigManager()

        # Initialize Discord components
        self.discord = None
        self.soundboard = None
        self.youtube_converter = None
        self.bot_info = None
        self.guilds = []
        self.selected_guild_id = None
        self.default_guild_id = None  # Guild ID from config

        # Wizard state
        self.wizard_step = 1  # Current step (1 or 2)

        # Audio state
        self.preview_audio_path = None
        self.downloaded_audio_path = None
        self.source_mode = tk.StringVar(value="online")  # "online" (YouTube/Instagram) or "local"
        self.selected_local_file = None
        self.detected_platform = None  # "youtube" or "instagram"
        self.instagram_carousel_items = []  # For multi-slide Instagram posts
        self.selected_carousel_index = None  # Which slide user selected

        # Audio trim slider state (unified for both YouTube and local)
        self.audio_duration = 0.0  # Total duration in seconds
        self.trim_start = tk.DoubleVar(value=0.0)
        self.trim_end = tk.DoubleVar(value=5.2)
        self.loaded_audio_path = None  # Track which file is currently loaded
        self.youtube_video_id = None  # YouTube video ID for preview

        # Setup pygame for audio playback
        pygame.mixer.init()

        # Setup GUI
        self.setup_styles()
        self.create_widgets()

        # Check for credentials and prompt if missing
        self.check_credentials_and_initialize()

    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')

        # Configure colors
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Subheader.TLabel', font=('Arial', 10))
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
        self.create_wizard_tab()
        self.create_sound_management_tab()
        self.create_settings_tab()

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))

    def create_wizard_tab(self):
        """Create the wizard-based sound creation tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Create Sound")

        # Create canvas for scrolling
        canvas = tk.Canvas(tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)

        # Main container with padding
        container = ttk.Frame(canvas, padding=20)

        # Configure canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.create_window((0, 0), window=container, anchor="nw")

        # Pack canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Update scroll region when container changes size
        def on_container_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        container.bind("<Configure>", on_container_configure)

        # Update canvas window width when canvas is resized
        def on_canvas_configure(event):
            canvas.itemconfig(canvas.find_withtag("all")[0], width=event.width)

        canvas.bind("<Configure>", on_canvas_configure)

        # Bind mousewheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        # Only bind mousewheel when mouse is over the canvas
        def bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", on_mousewheel)

        def unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", bind_mousewheel)
        canvas.bind("<Leave>", unbind_mousewheel)

        # Store canvas reference for cleanup
        self.wizard_canvas = canvas

        # Create wizard step frames (we'll show/hide them)
        self.wizard_step1_frame = ttk.Frame(container)
        self.wizard_step2_frame = ttk.Frame(container)

        # Build wizard steps
        self.create_wizard_step1()
        self.create_wizard_step2()

        # Show step 1 initially
        self.show_wizard_step(1)

    def create_wizard_step1(self):
        """
        Create wizard step 1: Source selection, URL/file input, and sound name
        """
        parent = self.wizard_step1_frame

        # Header with step indicator
        header_frame = ttk.Frame(parent)
        header_frame.pack(pady=(0, 20), fill=tk.X)

        ttk.Label(header_frame, text="Step 1 of 2: Select Audio Source",
                  style='Header.TLabel').pack()
        ttk.Label(header_frame, text="Choose your audio source and enter details",
                  font=('Arial', 9), foreground='gray').pack()

        # Content frame
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True)

        row = 0

        # Source mode selection (YouTube/Instagram vs Local)
        ttk.Label(content, text="Source:").grid(row=row, column=0, sticky=tk.W, pady=5)
        source_frame = ttk.Frame(content)
        source_frame.grid(row=row, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))

        ttk.Radiobutton(source_frame, text="YouTube / Instagram", variable=self.source_mode,
                       value="online", command=self.on_step1_source_changed).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(source_frame, text="Local File", variable=self.source_mode,
                       value="local", command=self.on_step1_source_changed).pack(side=tk.LEFT)

        row += 1

        # Online source-specific fields (YouTube/Instagram)
        self.step1_youtube_frame = ttk.Frame(content)
        self.step1_youtube_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=10)

        ttk.Label(self.step1_youtube_frame, text="Video URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.step1_youtube_url_entry = ttk.Entry(self.step1_youtube_frame, width=50)
        self.step1_youtube_url_entry.grid(row=0, column=1, columnspan=2, sticky=tk.EW, pady=5, padx=(10, 0))
        self.step1_youtube_url_entry.insert(0, "https://www.youtube.com/watch?v=xvFZjo5PgG0")

        hint_label = ttk.Label(self.step1_youtube_frame, text="Paste YouTube or Instagram URL (video, reel, or post)",
                              font=('Arial', 8), foreground='gray')
        hint_label.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=(35, 0), padx=(10, 0))

        # Local file fields
        self.step1_local_frame = ttk.Frame(content)
        # Don't grid it yet, will be shown when local mode is selected

        ttk.Label(self.step1_local_frame, text="Audio File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.step1_local_file_entry = ttk.Entry(self.step1_local_frame, width=40, state='readonly')
        self.step1_local_file_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(10, 0))
        ttk.Button(self.step1_local_frame, text="Browse", command=self.step1_browse_local_file).grid(
            row=0, column=2, pady=5, padx=(5, 0))

        # Show sounds folder files
        ttk.Label(self.step1_local_frame, text="Or select from sounds folder:").grid(
            row=1, column=0, columnspan=3, sticky=tk.W, pady=(10, 5))

        sounds_list_frame = ttk.Frame(self.step1_local_frame)
        sounds_list_frame.grid(row=2, column=0, columnspan=3, sticky=tk.NSEW, pady=5)

        scrollbar = ttk.Scrollbar(sounds_list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.step1_sounds_listbox = tk.Listbox(sounds_list_frame, height=5, yscrollcommand=scrollbar.set)
        self.step1_sounds_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.step1_sounds_listbox.yview)
        self.step1_sounds_listbox.bind('<<ListboxSelect>>', self.step1_on_sound_file_selected)

        row += 1

        # Separator
        ttk.Separator(content, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=3,
                                                           sticky=tk.EW, pady=20)

        row += 1

        # Discord Sound Name
        ttk.Label(content, text="Discord Sound Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.step1_sound_name_entry = ttk.Entry(content, width=30)
        self.step1_sound_name_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        ttk.Label(content, text="The name that will appear in Discord",
                 font=('Arial', 8), foreground='gray').grid(row=row, column=1, sticky=tk.W, pady=(35, 0), padx=(10, 0))

        row += 1

        # Configure grid weights
        content.columnconfigure(1, weight=1)

        # Navigation buttons
        nav_frame = ttk.Frame(parent)
        nav_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))

        ttk.Button(nav_frame, text="Next →", command=self.wizard_go_to_step2,
                  style='Action.TButton').pack(side=tk.RIGHT)

        # Initialize with YouTube mode
        self.on_step1_source_changed()

    def create_wizard_step2(self):
        """
        Create wizard step 2: Load audio, trim slider, preview, and publish
        """
        parent = self.wizard_step2_frame

        # Header with step indicator
        header_frame = ttk.Frame(parent)
        header_frame.pack(pady=(0, 20), fill=tk.X)

        ttk.Label(header_frame, text="Step 2 of 2: Preview & Publish",
                  style='Header.TLabel').pack()
        ttk.Label(header_frame, text="Select the 5.2s audio range and publish to Discord",
                  font=('Arial', 9), foreground='gray').pack()

        # Content frame
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True)

        row = 0

        # Audio info display
        self.step2_audio_info_label = ttk.Label(content, text="Click 'Next' from Step 1 to load audio",
                                               font=('Arial', 10), foreground='gray')
        self.step2_audio_info_label.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 15))

        row += 1

        # YouTube Video Info Frame (only shown for YouTube mode)
        self.step2_youtube_video_frame = ttk.LabelFrame(content, text="YouTube Video", padding=15)
        # Don't grid it yet, will be shown when YouTube video is loaded

        # Video thumbnail and info
        video_info_container = ttk.Frame(self.step2_youtube_video_frame)
        video_info_container.pack(fill=tk.BOTH, expand=True)

        self.step2_youtube_title_label = ttk.Label(video_info_container,
                                                    text="Video Title",
                                                    font=('Arial', 12, 'bold'),
                                                    wraplength=500)
        self.step2_youtube_title_label.pack(pady=(0, 10), fill=tk.X)

        self.step2_youtube_duration_label = ttk.Label(video_info_container,
                                                       text="Duration: --",
                                                       font=('Arial', 10))
        self.step2_youtube_duration_label.pack(pady=(0, 15))

        # Helpful message
        ttk.Label(video_info_container,
                 text="💡 Watch the video in your browser to find the perfect timestamp for your clip",
                 font=('Arial', 9),
                 foreground='#0066cc',
                 wraplength=500).pack(pady=(0, 15), fill=tk.X)

        # Browser button
        button_frame = ttk.Frame(video_info_container)
        button_frame.pack()

        self.step2_youtube_browser_btn = ttk.Button(button_frame,
                                                     text="▶ Open Video in Browser",
                                                     command=self.step2_youtube_open_browser,
                                                     style='Action.TButton')
        self.step2_youtube_browser_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(button_frame,
                 text="(Opens at your current trim start position)",
                 font=('Arial', 8),
                 foreground='gray').pack(side=tk.LEFT, padx=5)

        # Instagram Carousel Frame (only shown for Instagram carousels)
        self.step2_instagram_carousel_frame = ttk.LabelFrame(content, text="Select Carousel Slide", padding=15)
        # Don't grid it yet, will be shown when Instagram carousel is detected

        carousel_info_container = ttk.Frame(self.step2_instagram_carousel_frame)
        carousel_info_container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(carousel_info_container,
                 text="This post has multiple slides. Select which one to use:",
                 font=('Arial', 10)).pack(pady=(0, 10))

        # Scrollable frame for carousel items
        carousel_canvas = tk.Canvas(carousel_info_container, height=150, highlightthickness=0)
        carousel_scrollbar = ttk.Scrollbar(carousel_info_container, orient="horizontal", command=carousel_canvas.xview)
        self.step2_carousel_items_frame = ttk.Frame(carousel_canvas)

        carousel_canvas.configure(xscrollcommand=carousel_scrollbar.set)
        carousel_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        carousel_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        carousel_canvas.create_window((0, 0), window=self.step2_carousel_items_frame, anchor="nw")

        self.step2_carousel_items_frame.bind("<Configure>",
            lambda e: carousel_canvas.configure(scrollregion=carousel_canvas.bbox("all")))

        row += 1

        # Trim Slider Section
        ttk.Label(content, text="Audio Trimmer (1.0s - 5.2s max)",
                 font=('Arial', 10, 'bold')).grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(5, 5))

        row += 1

        # Trim sliders frame
        trim_frame = ttk.Frame(content)
        trim_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=5)
        trim_frame.columnconfigure(1, weight=1)

        # Start time slider
        ttk.Label(trim_frame, text="Start:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.step2_start_slider = tk.Scale(trim_frame, from_=0, to=5.2, resolution=0.1,
                                          orient=tk.HORIZONTAL, variable=self.trim_start,
                                          command=self.step2_on_trim_slider_changed, state=tk.DISABLED)
        self.step2_start_slider.grid(row=0, column=1, sticky=tk.EW, padx=5)
        self.step2_start_time_label = ttk.Label(trim_frame, text="0.0s", width=8)
        self.step2_start_time_label.grid(row=0, column=2, sticky=tk.W, padx=(5, 0))

        # End time slider
        ttk.Label(trim_frame, text="End:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.step2_end_slider = tk.Scale(trim_frame, from_=0, to=5.2, resolution=0.1,
                                        orient=tk.HORIZONTAL, variable=self.trim_end,
                                        command=self.step2_on_trim_slider_changed, state=tk.DISABLED)
        self.step2_end_slider.grid(row=1, column=1, sticky=tk.EW, padx=5)
        self.step2_end_time_label = ttk.Label(trim_frame, text="5.2s", width=8)
        self.step2_end_time_label.grid(row=1, column=2, sticky=tk.W, padx=(5, 0))

        # Duration display
        self.step2_duration_label = ttk.Label(trim_frame, text="Duration: 5.2s",
                                             font=('Arial', 9, 'bold'))
        self.step2_duration_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

        row += 1

        # Preview playback buttons
        preview_frame = ttk.Frame(content)
        preview_frame.grid(row=row, column=0, columnspan=3, pady=20)

        self.step2_generate_preview_btn = ttk.Button(preview_frame, text="Generate Preview Clip",
                                                     command=self.step2_generate_preview, state=tk.DISABLED)
        self.step2_generate_preview_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.step2_play_preview_btn = ttk.Button(preview_frame, text="▶ Play Preview",
                                                 command=self.step2_play_preview, state=tk.DISABLED)
        self.step2_play_preview_btn.pack(side=tk.LEFT)

        row += 1

        # Separator
        ttk.Separator(content, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=3,
                                                           sticky=tk.EW, pady=20)

        row += 1

        # Additional settings
        ttk.Label(content, text="Additional Settings", style='Subheader.TLabel').grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        row += 1

        ttk.Label(content, text="Discord Server:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.step2_guild_display_label = ttk.Label(content, text="Loading...", font=('Arial', 10))
        self.step2_guild_display_label.grid(row=row, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))

        row += 1

        ttk.Label(content, text="Volume (0.0-1.0):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.step2_volume_entry = ttk.Entry(content, width=10)
        self.step2_volume_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.step2_volume_entry.insert(0, "1.0")

        row += 1

        # Emoji picker
        ttk.Label(content, text="Emoji (optional):").grid(row=row, column=0, sticky=tk.W, pady=5)

        emoji_frame = ttk.Frame(content)
        emoji_frame.grid(row=row, column=1, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))

        self.step2_selected_emoji = tk.StringVar(value="")
        self.step2_emoji_display = ttk.Label(emoji_frame, textvariable=self.step2_selected_emoji,
                                             font=('Segoe UI Emoji', 20), width=3)
        self.step2_emoji_display.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(emoji_frame, text="Pick Emoji",
                  command=self.step2_pick_emoji).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(emoji_frame, text="Clear",
                  command=lambda: self.step2_selected_emoji.set("")).pack(side=tk.LEFT)

        row += 1

        # Configure grid weights
        content.columnconfigure(1, weight=1)

        # Navigation buttons
        nav_frame = ttk.Frame(parent)
        nav_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))

        ttk.Button(nav_frame, text="← Back", command=self.wizard_go_to_step1).pack(side=tk.LEFT)

        self.step2_publish_btn = ttk.Button(nav_frame, text="Publish Sound to Discord",
                                           command=self.step2_publish_sound,
                                           style='Action.TButton', state=tk.DISABLED)
        self.step2_publish_btn.pack(side=tk.RIGHT)

    def show_wizard_step(self, step):
        """Show the specified wizard step and hide others"""
        self.wizard_step = step

        if step == 1:
            self.wizard_step1_frame.pack(fill=tk.BOTH, expand=True)
            self.wizard_step2_frame.pack_forget()
        elif step == 2:
            self.wizard_step1_frame.pack_forget()
            self.wizard_step2_frame.pack(fill=tk.BOTH, expand=True)

        # Reset scroll position to top
        if hasattr(self, 'wizard_canvas'):
            self.wizard_canvas.yview_moveto(0)

    def on_step1_source_changed(self):
        """Handle source mode radio button change in step 1"""
        mode = self.source_mode.get()

        if mode == "online":
            # Show online source frame (YouTube/Instagram), hide local frame
            self.step1_youtube_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=10)
            self.step1_local_frame.grid_forget()
        else:  # local
            # Hide online source frame, show local frame
            self.step1_youtube_frame.grid_forget()
            self.step1_local_frame.grid(row=1, column=0, columnspan=3, sticky=tk.NSEW, pady=10)
            # Load sounds from sounds folder
            self.step1_refresh_sounds_list()

    def step1_refresh_sounds_list(self):
        """Refresh the list of MP3 files in the sounds folder"""
        self.step1_sounds_listbox.delete(0, tk.END)

        sounds_dir = Path("sounds")
        if sounds_dir.exists():
            mp3_files = sorted(sounds_dir.glob("*.mp3"))
            for mp3_file in mp3_files:
                self.step1_sounds_listbox.insert(tk.END, mp3_file.name)

    def step1_browse_local_file(self):
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
            self.step1_local_file_entry.config(state='normal')
            self.step1_local_file_entry.delete(0, tk.END)
            self.step1_local_file_entry.insert(0, file_path)
            self.step1_local_file_entry.config(state='readonly')

            # Clear listbox selection
            self.step1_sounds_listbox.selection_clear(0, tk.END)

    def step1_on_sound_file_selected(self, event):
        """Handle selection from sounds folder listbox"""
        selection = self.step1_sounds_listbox.curselection()
        if selection:
            filename = self.step1_sounds_listbox.get(selection[0])
            file_path = str((Path("sounds") / filename).absolute())
            self.selected_local_file = file_path

            self.step1_local_file_entry.config(state='normal')
            self.step1_local_file_entry.delete(0, tk.END)
            self.step1_local_file_entry.insert(0, file_path)
            self.step1_local_file_entry.config(state='readonly')

    def wizard_go_to_step2(self):
        """Navigate to step 2 and load audio data"""
        # Validate step 1 inputs
        mode = self.source_mode.get()
        sound_name = self.step1_sound_name_entry.get().strip()

        if not sound_name:
            messagebox.showerror("Error", "Please enter a Discord Sound Name")
            return

        if mode == "online":
            online_url = self.step1_youtube_url_entry.get().strip()
            if not online_url:
                messagebox.showerror("Error", "Please enter a video URL")
                return

            # Detect platform (YouTube or Instagram)
            from instagram_scraper import InstagramScraper
            instagram_scraper = InstagramScraper(None)  # Only need for URL detection
            self.detected_platform = instagram_scraper.detect_url_platform(online_url)

            if not self.detected_platform:
                messagebox.showerror("Error",
                    "URL not recognized. Please enter a valid YouTube or Instagram URL.\n\n" +
                    "YouTube: youtube.com/watch?v=... or youtu.be/...\n" +
                    "Instagram: instagram.com/p/... or instagram.com/reel/...")
                return
        else:  # local
            if not self.selected_local_file:
                messagebox.showerror("Error", "Please select an audio file")
                return

        # Go to step 2
        self.show_wizard_step(2)

        # Load audio data in background
        self.step2_load_audio_data()

    def wizard_go_to_step1(self):
        """Navigate back to step 1"""
        # Hide YouTube video info when going back
        self.step2_youtube_video_frame.grid_forget()
        self.show_wizard_step(1)

    def step2_load_audio_data(self):
        """Load audio data for step 2 (online or local file)"""
        mode = self.source_mode.get()

        if mode == "online":
            # Route based on detected platform
            if self.detected_platform == "youtube":
                self.step2_load_youtube_info()
            elif self.detected_platform == "instagram":
                self.step2_load_instagram_info()
        else:
            self.step2_load_local_audio_info()

    def step2_load_youtube_info(self):
        """Load YouTube video information and setup trim sliders"""
        def load():
            try:
                youtube_url = self.step1_youtube_url_entry.get().strip()
                sound_name = self.step1_sound_name_entry.get().strip()

                self.root.after(0, lambda: self.step2_audio_info_label.config(
                    text="Loading YouTube video info...", foreground='blue'))

                # Get video info
                video_info = self.youtube_converter.get_video_info(youtube_url)
                title = video_info['title']
                video_id = video_info['video_id']

                # Store video info
                self.loaded_audio_path = youtube_url
                self.youtube_video_id = video_id

                # Download or find existing audio to get ACTUAL duration
                self.root.after(0, lambda: self.step2_audio_info_label.config(
                    text="Downloading/loading audio file...", foreground='blue'))

                # Create safe filename
                import re
                safe_filename = re.sub(r'[^\w\s-]', '', sound_name).strip().replace(' ', '_')
                temp_download = f"{safe_filename}_full"

                # Download audio (or reuse existing)
                downloaded_path = self.youtube_converter._download_audio(youtube_url, temp_download, check_existing=True)

                # Get actual duration from audio file
                from pydub import AudioSegment
                audio = AudioSegment.from_file(downloaded_path)
                actual_duration_seconds = len(audio) / 1000.0  # Convert ms to seconds

                # Store the actual duration and downloaded path
                self.audio_duration = actual_duration_seconds
                self.downloaded_audio_path = downloaded_path

                # Update UI
                def update_ui():
                    self.step2_audio_info_label.config(
                        text=f"✓ Audio loaded ({actual_duration_seconds:.2f}s total)",
                        foreground='green'
                    )

                    # Show YouTube video info
                    self.step2_show_youtube_video_info(video_id, title, actual_duration_seconds)

                    # Configure sliders with ACTUAL duration
                    self.step2_start_slider.config(from_=0, to=actual_duration_seconds, state=tk.NORMAL)
                    self.step2_end_slider.config(from_=0, to=actual_duration_seconds, state=tk.NORMAL)

                    # Set initial values
                    initial_end = min(actual_duration_seconds, 5.2)
                    self.trim_start.set(0.0)
                    self.trim_end.set(initial_end)

                    # Update labels
                    self.step2_update_trim_labels()

                    # Enable generate preview button
                    self.step2_generate_preview_btn.config(state=tk.NORMAL)

                self.root.after(0, update_ui)

            except Exception as e:
                error_msg = f"Failed to load video info: {str(e)}"
                error_obj = e  # Capture in local scope
                self.root.after(0, lambda: self.step2_audio_info_label.config(
                    text=error_msg, foreground='red'))
                self.root.after(0, lambda err=error_obj: self.show_error("Video Load Error", error_msg, err))

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def step2_show_youtube_video_info(self, video_id, title, duration):
        """Show YouTube video info card"""
        # Show the video info frame
        self.step2_youtube_video_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=(0, 15))

        # Update labels
        self.step2_youtube_title_label.config(text=title)
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        self.step2_youtube_duration_label.config(text=f"Duration: {minutes}:{seconds:02d}")

    def step2_youtube_open_browser(self):
        """Open the YouTube video in the default browser"""
        if not hasattr(self, 'youtube_video_id') or not self.youtube_video_id:
            messagebox.showerror("Error", "No video loaded")
            return

        import webbrowser
        start_seconds = int(self.trim_start.get())
        youtube_url = f"https://www.youtube.com/watch?v={self.youtube_video_id}&t={start_seconds}s"
        webbrowser.open(youtube_url)

    def step2_load_instagram_info(self):
        """Load Instagram post/reel information and setup carousel selector"""
        def load():
            try:
                from instagram_scraper import InstagramScraper
                from pydub import AudioSegment
                import re

                instagram_url = self.step1_youtube_url_entry.get().strip()
                sound_name = self.step1_sound_name_entry.get().strip()

                self.root.after(0, lambda: self.step2_audio_info_label.config(
                    text="Loading Instagram post info...", foreground='blue'))

                # Initialize Instagram scraper
                ffmpeg_path = self.youtube_converter.ffmpeg_path if hasattr(self.youtube_converter, 'ffmpeg_path') else None
                instagram_scraper = InstagramScraper(self.soundboard, ffmpeg_path)

                # Get post info (includes carousel detection)
                post_info = instagram_scraper.get_post_info(instagram_url)
                self.instagram_carousel_items = post_info['items']

                # If carousel with multiple items, show selector
                if post_info['is_carousel'] and len(self.instagram_carousel_items) > 1:
                    self.root.after(0, lambda: self.step2_audio_info_label.config(
                        text=f"Found {len(self.instagram_carousel_items)} slides with audio. Select one below.",
                        foreground='blue'))

                    # Show carousel selector
                    self.root.after(0, lambda: self.step2_show_instagram_carousel(instagram_url, sound_name))
                else:
                    # Single item, download directly
                    if not self.instagram_carousel_items:
                        raise Exception("No video with audio found in this post")

                    self.selected_carousel_index = 0

                    # Schedule download in a separate thread
                    def download_single():
                        self.step2_download_instagram_audio(instagram_url, sound_name, 0)

                    download_thread = threading.Thread(target=download_single, daemon=True)
                    self.root.after(0, download_thread.start)

            except Exception as e:
                error_msg = f"Failed to load Instagram post: {str(e)}"
                error_obj = e  # Capture in local scope
                self.root.after(0, lambda: self.step2_audio_info_label.config(
                    text=error_msg, foreground='red'))
                self.root.after(0, lambda err=error_obj: self.show_error("Instagram Load Error", error_msg, err))

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def step2_show_instagram_carousel(self, instagram_url, sound_name):
        """Display carousel item selector with thumbnails"""
        from PIL import Image, ImageTk
        import urllib.request
        from io import BytesIO

        # Show carousel frame
        self.step2_instagram_carousel_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=(0, 15))

        # Clear existing items
        for widget in self.step2_carousel_items_frame.winfo_children():
            widget.destroy()

        # Create thumbnail buttons for each item
        for idx, item in enumerate(self.instagram_carousel_items):
            item_frame = ttk.Frame(self.step2_carousel_items_frame, padding=5)
            item_frame.pack(side=tk.LEFT, padx=5)

            # Try to load thumbnail
            thumbnail_label = None
            if item['thumbnail']:
                try:
                    # Download thumbnail
                    with urllib.request.urlopen(item['thumbnail']) as response:
                        img_data = response.read()
                    img = Image.open(BytesIO(img_data))

                    # Resize to reasonable thumbnail size
                    img.thumbnail((120, 120))
                    photo = ImageTk.PhotoImage(img)

                    thumbnail_label = ttk.Label(item_frame, image=photo, relief=tk.RAISED, borderwidth=2)
                    thumbnail_label.image = photo  # Keep reference
                    thumbnail_label.pack()
                except Exception as e:
                    print(f"Failed to load thumbnail {idx}: {e}")

            # Item info
            duration_text = f"{item['duration']:.1f}s" if item.get('duration') else "N/A"
            info_text = f"Slide {idx + 1}\n{duration_text}"

            ttk.Label(item_frame, text=info_text, font=('Arial', 9), justify=tk.CENTER).pack(pady=(5, 0))

            # Select button
            select_btn = ttk.Button(item_frame, text="Select",
                                   command=lambda i=idx: self.step2_select_carousel_item(instagram_url, sound_name, i))
            select_btn.pack(pady=(5, 0))

    def step2_select_carousel_item(self, instagram_url, sound_name, index):
        """User selected a carousel item"""
        self.selected_carousel_index = index

        # Hide carousel selector
        self.step2_instagram_carousel_frame.grid_forget()

        # Download audio for selected item
        self.step2_audio_info_label.config(
            text=f"Loading audio from slide {index + 1}...", foreground='blue')

        # Download in background thread
        thread = threading.Thread(
            target=lambda: self.step2_download_instagram_audio(instagram_url, sound_name, index),
            daemon=True)
        thread.start()

    def step2_download_instagram_audio(self, instagram_url, sound_name, carousel_index):
        """Download Instagram audio and setup trim sliders"""
        try:
            from instagram_scraper import InstagramScraper
            from pydub import AudioSegment
            import re

            # Initialize scraper
            ffmpeg_path = self.youtube_converter.ffmpeg_path if hasattr(self.youtube_converter, 'ffmpeg_path') else None
            instagram_scraper = InstagramScraper(self.soundboard, ffmpeg_path)

            # Create safe filename
            safe_filename = re.sub(r'[^\w\s-]', '', sound_name).strip().replace(' ', '_')

            # Download audio
            self.root.after(0, lambda: self.step2_audio_info_label.config(
                text="Downloading audio...", foreground='blue'))

            downloaded_path = instagram_scraper.download_audio(
                instagram_url,
                safe_filename,
                carousel_index if len(self.instagram_carousel_items) > 1 else None
            )

            # Store path
            self.downloaded_audio_path = downloaded_path
            self.loaded_audio_path = downloaded_path

            # Get actual duration
            audio = AudioSegment.from_file(downloaded_path)
            actual_duration_seconds = len(audio) / 1000.0
            self.audio_duration = actual_duration_seconds

            def update_ui():
                # Update info label
                self.step2_audio_info_label.config(
                    text=f"✓ Audio loaded from Instagram ({actual_duration_seconds:.2f}s total)",
                    foreground='green'
                )

                # Configure sliders
                self.step2_start_slider.config(from_=0, to=actual_duration_seconds, state=tk.NORMAL)
                self.step2_end_slider.config(from_=0, to=actual_duration_seconds, state=tk.NORMAL)

                # Set initial values
                initial_end = min(actual_duration_seconds, 5.2)
                self.trim_start.set(0.0)
                self.trim_end.set(initial_end)

                # Update labels
                self.step2_update_trim_labels()

                # Enable generate preview button
                self.step2_generate_preview_btn.config(state=tk.NORMAL)

            self.root.after(0, update_ui)

        except Exception as e:
            error_msg = f"Failed to download Instagram audio: {str(e)}"
            error_obj = e  # Capture in local scope
            self.root.after(0, lambda: self.step2_audio_info_label.config(
                text=error_msg, foreground='red'))
            self.root.after(0, lambda err=error_obj: self.show_error("Instagram Download Error", error_msg, err))

    def step2_load_local_audio_info(self):
        """Load local audio file information and setup trim sliders"""
        try:
            file_path = self.selected_local_file

            from pydub import AudioSegment

            # Load audio file
            audio = AudioSegment.from_file(file_path)
            duration_seconds = len(audio) / 1000.0  # Convert ms to seconds
            self.audio_duration = duration_seconds
            self.loaded_audio_path = file_path

            # Update UI with audio info
            self.step2_audio_info_label.config(
                text=f"Audio loaded: {Path(file_path).name} ({duration_seconds:.1f}s total)",
                foreground='green'
            )

            # Configure sliders based on duration
            max_end = min(duration_seconds, 5.2)

            # Set slider ranges
            self.step2_start_slider.config(from_=0, to=max_end, state=tk.NORMAL)
            self.step2_end_slider.config(from_=0, to=max_end, state=tk.NORMAL)

            # Set initial values
            self.trim_start.set(0.0)
            self.trim_end.set(max_end)

            # Update labels
            self.step2_update_trim_labels()

            # Enable generate preview button
            self.step2_generate_preview_btn.config(state=tk.NORMAL)

        except Exception as e:
            self.step2_audio_info_label.config(
                text=f"Error loading audio: {str(e)}",
                foreground='red'
            )
            self.step2_start_slider.config(state=tk.DISABLED)
            self.step2_end_slider.config(state=tk.DISABLED)

    def step2_on_trim_slider_changed(self, value=None):
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
            if value is not None:
                if abs(float(value) - start) < 0.01:  # Start slider moved
                    new_end = start + min_duration
                    if new_end <= self.audio_duration:
                        self.trim_end.set(new_end)
                    else:
                        self.trim_start.set(max(0, end - min_duration))
                else:  # End slider moved
                    new_start = end - min_duration
                    if new_start >= 0:
                        self.trim_start.set(new_start)
                    else:
                        self.trim_end.set(min(self.audio_duration, start + min_duration))

        # If duration is too long, adjust
        elif duration > max_duration:
            if value is not None:
                if abs(float(value) - start) < 0.01:  # Start slider moved
                    self.trim_end.set(min(start + max_duration, self.audio_duration))
                else:  # End slider moved
                    self.trim_start.set(max(0, end - max_duration))

        # Ensure start is never after end
        if self.trim_start.get() >= self.trim_end.get():
            if value is not None:
                if abs(float(value) - start) < 0.01:  # Start slider moved
                    self.trim_start.set(max(0, self.trim_end.get() - 0.1))
                else:
                    self.trim_end.set(min(self.audio_duration, self.trim_start.get() + 0.1))

        # Update labels
        self.step2_update_trim_labels()

    def step2_update_trim_labels(self):
        """Update the trim slider time labels and duration display"""
        start = self.trim_start.get()
        end = self.trim_end.get()
        duration = end - start

        self.step2_start_time_label.config(text=f"{start:.1f}s")
        self.step2_end_time_label.config(text=f"{end:.1f}s")
        self.step2_duration_label.config(text=f"Duration: {duration:.1f}s")

        # Color code duration based on validity
        if duration < 1.0:
            self.step2_duration_label.config(foreground='red')
        elif duration > 5.2:
            self.step2_duration_label.config(foreground='orange')
        else:
            self.step2_duration_label.config(foreground='green')

    def step2_generate_preview(self):
        """Generate preview clip based on trim slider selection"""
        mode = self.source_mode.get()

        if mode == "online":
            self.step2_generate_preview_youtube()  # Works for both YouTube and Instagram
        else:
            self.step2_generate_preview_local()

    def step2_generate_preview_youtube(self):
        """Generate preview from YouTube (using already-downloaded audio)"""
        def create():
            try:
                sound_name = self.step1_sound_name_entry.get().strip()

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

                self.root.after(0, lambda: self.status_var.set("Creating preview..."))
                self.root.after(0, lambda: self.step2_generate_preview_btn.config(state=tk.DISABLED))

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

                # Use the already-downloaded audio file to create preview
                # (downloaded in step2_load_youtube_info)
                if not self.downloaded_audio_path or not os.path.exists(self.downloaded_audio_path):
                    raise Exception("Audio file not found. Please go back and reload.")

                # Create safe filename for preview
                import re
                safe_filename = re.sub(r'[^\w\s-]', '', sound_name).strip().replace(' ', '_')
                clipped_filename = f"{safe_filename}.mp3"

                # Clip the audio
                clipped = self.youtube_converter._clip_audio(
                    self.downloaded_audio_path,
                    start_time,
                    end_time,
                    clipped_filename
                )

                self.preview_audio_path = clipped

                self.root.after(0, lambda: self.status_var.set("Preview created successfully"))
                self.root.after(0, lambda: self.step2_play_preview_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.step2_publish_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.step2_generate_preview_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: messagebox.showinfo("Success",
                    "Preview created! Click 'Play Preview' to listen."))

            except Exception as e:
                error_msg = f"Failed to create preview: {str(e)}"
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: self.show_error("Preview Error", error_msg, e))
                self.root.after(0, lambda: self.step2_generate_preview_btn.config(state=tk.NORMAL))

        thread = threading.Thread(target=create, daemon=True)
        thread.start()

    def step2_generate_preview_local(self):
        """Generate preview from local file"""
        def create():
            try:
                local_file_path = Path(self.selected_local_file)
                sound_name = self.step1_sound_name_entry.get().strip()

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

                self.root.after(0, lambda: self.status_var.set("Creating preview from local file..."))
                self.root.after(0, lambda: self.step2_generate_preview_btn.config(state=tk.DISABLED))

                # Stop any playing audio first
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
                output_filename = f"{sound_name}_clip.mp3"
                output_path = Path("sounds") / output_filename

                # Clip the audio
                from pydub import AudioSegment

                audio = AudioSegment.from_file(str(local_file_path))

                # Convert seconds to milliseconds
                start_ms = int(start_seconds * 1000)
                end_ms = int(end_seconds * 1000)

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
                    self.root.after(0, lambda: self.step2_generate_preview_btn.config(state=tk.NORMAL))
                    return

                self.preview_audio_path = str(output_path.absolute())
                self.downloaded_audio_path = None  # No downloaded file for local mode

                self.root.after(0, lambda: self.status_var.set("Preview created successfully"))
                self.root.after(0, lambda: self.step2_play_preview_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.step2_publish_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.step2_generate_preview_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: messagebox.showinfo("Success",
                    "Preview created! Click 'Play Preview' to listen."))

            except Exception as e:
                error_msg = f"Failed to create preview: {str(e)}"
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: self.show_error("Preview Error", error_msg, e))
                self.root.after(0, lambda: self.step2_generate_preview_btn.config(state=tk.NORMAL))

        thread = threading.Thread(target=create, daemon=True)
        thread.start()

    def step2_play_preview(self):
        """Play the preview audio"""
        if not self.preview_audio_path or not os.path.exists(self.preview_audio_path):
            messagebox.showerror("Error", "No preview available. Generate a preview first.")
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

    def step2_pick_emoji(self):
        """Open emoji picker dialog"""
        def on_emoji_selected(emoji):
            if emoji:
                self.step2_selected_emoji.set(emoji)

        show_emoji_picker(self.root, on_emoji_selected)

    def step2_publish_sound(self):
        """Publish the sound to Discord"""
        if not self.preview_audio_path or not os.path.exists(self.preview_audio_path):
            messagebox.showerror("Error", "No preview available. Generate a preview first.")
            return

        sound_name = self.step1_sound_name_entry.get().strip()
        if not sound_name:
            messagebox.showerror("Error", "Sound name is required")
            return

        if not self.selected_guild_id:
            messagebox.showerror("Error", "No Discord server selected")
            return

        try:
            volume = float(self.step2_volume_entry.get())
            if not 0.0 <= volume <= 1.0:
                raise ValueError()
        except:
            messagebox.showerror("Error", "Volume must be between 0.0 and 1.0")
            return

        emoji_name = self.step2_selected_emoji.get().strip() or None

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
                self.root.after(0, lambda: self.step2_publish_btn.config(state=tk.DISABLED))

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

                success_msg = f"Successfully uploaded '{sound_name}' to {guild_name}!"
                self.root.after(0, lambda: self.status_var.set(success_msg))
                self.root.after(0, lambda: messagebox.showinfo("Success", success_msg))

                # Reset wizard to step 1
                self.root.after(0, self.wizard_reset)

            except Exception as e:
                error_msg = f"Failed to publish sound: {str(e)}"
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: self.show_error("Upload Error", error_msg, e))
                self.root.after(0, lambda: self.step2_publish_btn.config(state=tk.NORMAL))

        thread = threading.Thread(target=upload, daemon=True)
        thread.start()

    def wizard_reset(self):
        """Reset the wizard to step 1 and clear form"""
        # Clear step 1 fields
        self.step1_youtube_url_entry.delete(0, tk.END)
        self.step1_sound_name_entry.delete(0, tk.END)
        self.step1_local_file_entry.config(state='normal')
        self.step1_local_file_entry.delete(0, tk.END)
        self.step1_local_file_entry.config(state='readonly')
        self.selected_local_file = None

        # Clear step 2 fields
        self.step2_selected_emoji.set("")
        self.step2_volume_entry.delete(0, tk.END)
        self.step2_volume_entry.insert(0, "1.0")

        # Reset sliders
        self.trim_start.set(0.0)
        self.trim_end.set(5.2)

        # Disable step 2 buttons
        self.step2_generate_preview_btn.config(state=tk.DISABLED)
        self.step2_play_preview_btn.config(state=tk.DISABLED)
        self.step2_publish_btn.config(state=tk.DISABLED)
        self.step2_start_slider.config(state=tk.DISABLED)
        self.step2_end_slider.config(state=tk.DISABLED)

        # Hide YouTube video info
        self.step2_youtube_video_frame.grid_forget()

        # Go back to step 1
        self.show_wizard_step(1)

    def seconds_to_mmss(self, seconds: float) -> str:
        """Convert seconds to MM:SS.milliseconds format"""
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:06.3f}"

    def create_sound_management_tab(self):
        """Create sound management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Manage Sounds")

        container = ttk.Frame(tab, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(container, text="Soundboard Management",
                  style='Header.TLabel').pack(pady=(0, 20))

        # Server info frame
        info_frame = ttk.LabelFrame(container, text="Server Information", padding=15)
        info_frame.pack(fill=tk.X, pady=(0, 20))

        # Guild name
        guild_frame = ttk.Frame(info_frame)
        guild_frame.pack(fill=tk.X, pady=5)
        ttk.Label(guild_frame, text="Server:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.mgmt_guild_name_label = ttk.Label(guild_frame, text="Loading...", font=('Arial', 10))
        self.mgmt_guild_name_label.pack(side=tk.LEFT, padx=(10, 0))

        # Tier information
        tier_frame = ttk.Frame(info_frame)
        tier_frame.pack(fill=tk.X, pady=5)
        ttk.Label(tier_frame, text="Boost Tier:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.mgmt_tier_label = ttk.Label(tier_frame, text="--", font=('Arial', 10))
        self.mgmt_tier_label.pack(side=tk.LEFT, padx=(10, 0))

        # Boosts count
        boosts_frame = ttk.Frame(info_frame)
        boosts_frame.pack(fill=tk.X, pady=5)
        ttk.Label(boosts_frame, text="Server Boosts:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.mgmt_boosts_label = ttk.Label(boosts_frame, text="--", font=('Arial', 10))
        self.mgmt_boosts_label.pack(side=tk.LEFT, padx=(10, 0))

        # Separator
        ttk.Separator(info_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Slot usage
        slots_frame = ttk.Frame(info_frame)
        slots_frame.pack(fill=tk.X, pady=5)
        ttk.Label(slots_frame, text="Soundboard Slots:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.mgmt_slots_label = ttk.Label(slots_frame, text="-- / --", font=('Arial', 10))
        self.mgmt_slots_label.pack(side=tk.LEFT, padx=(10, 0))

        # Available slots (highlighted)
        available_frame = ttk.Frame(info_frame)
        available_frame.pack(fill=tk.X, pady=5)
        ttk.Label(available_frame, text="Available Slots:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.mgmt_available_label = ttk.Label(available_frame, text="--",
                                              font=('Arial', 11, 'bold'), foreground='green')
        self.mgmt_available_label.pack(side=tk.LEFT, padx=(10, 0))

        # Refresh button
        ttk.Button(container, text="Refresh Server Info",
                  command=self.refresh_sound_management_info,
                  style='Action.TButton').pack(pady=10)

        # Sounds list frame
        sounds_frame = ttk.LabelFrame(container, text="Soundboard Sounds", padding=15)
        sounds_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Search/filter bar
        search_frame = ttk.Frame(sounds_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.mgmt_search_var = tk.StringVar()
        self.mgmt_search_var.trace('w', lambda *args: self.filter_sounds_list())
        self.mgmt_search_entry = ttk.Entry(search_frame, textvariable=self.mgmt_search_var, width=30)
        self.mgmt_search_entry.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(search_frame, text="Refresh List", command=self.load_sounds_list).pack(side=tk.LEFT)

        # Treeview for sounds
        tree_container = ttk.Frame(sounds_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        hsb = ttk.Scrollbar(tree_container, orient="horizontal")
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview columns: Sound ID, Name, Emoji, Volume, Creator, Available
        columns = ('sound_id', 'name', 'emoji', 'volume', 'creator', 'available')
        self.mgmt_sounds_tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show='headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        vsb.config(command=self.mgmt_sounds_tree.yview)
        hsb.config(command=self.mgmt_sounds_tree.xview)

        # Configure columns
        self.mgmt_sounds_tree.heading('sound_id', text='Sound ID')
        self.mgmt_sounds_tree.heading('name', text='Name')
        self.mgmt_sounds_tree.heading('emoji', text='Emoji')
        self.mgmt_sounds_tree.heading('volume', text='Volume')
        self.mgmt_sounds_tree.heading('creator', text='Creator')
        self.mgmt_sounds_tree.heading('available', text='Available')

        self.mgmt_sounds_tree.column('sound_id', width=150, anchor='w')
        self.mgmt_sounds_tree.column('name', width=200, anchor='w')
        self.mgmt_sounds_tree.column('emoji', width=60, anchor='center')
        self.mgmt_sounds_tree.column('volume', width=80, anchor='center')
        self.mgmt_sounds_tree.column('creator', width=150, anchor='w')
        self.mgmt_sounds_tree.column('available', width=80, anchor='center')

        self.mgmt_sounds_tree.pack(fill=tk.BOTH, expand=True)

        # Store all sounds data for filtering
        self.mgmt_all_sounds = []

        # Context menu for right-click (future: delete, edit, etc.)
        # self.mgmt_sounds_tree.bind('<Button-3>', self.show_sound_context_menu)

    def load_sounds_list(self):
        """Load the list of soundboard sounds"""
        if not self.selected_guild_id:
            return

        def load():
            try:
                self.root.after(0, lambda: self.status_var.set("Loading sounds..."))

                # Get sounds
                sounds = self.soundboard.list_soundboard_sounds(self.selected_guild_id)

                # Update UI
                def update_ui():
                    self.mgmt_all_sounds = sounds
                    self.populate_sounds_tree(sounds)
                    self.status_var.set(f"Loaded {len(sounds)} sounds")

                self.root.after(0, update_ui)

            except Exception as e:
                error_msg = f"Failed to load sounds: {str(e)}"
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: self.show_error("Load Error", error_msg, e))

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def populate_sounds_tree(self, sounds):
        """Populate the sounds treeview with sound data"""
        # Clear existing items
        for item in self.mgmt_sounds_tree.get_children():
            self.mgmt_sounds_tree.delete(item)

        # Add sounds
        for sound in sounds:
            sound_id = sound.get('sound_id', 'Unknown')
            name = sound.get('name', 'Unknown')
            emoji = sound.get('emoji_name', '') or sound.get('emoji_id', '') or ''
            volume = sound.get('volume', 0.0)
            volume_str = f"{volume:.2f}" if volume else "0.00"

            # Get creator name
            user = sound.get('user', {})
            creator = user.get('global_name') or user.get('username', 'Unknown')

            available = 'Yes' if sound.get('available', True) else 'No'

            self.mgmt_sounds_tree.insert('', tk.END, values=(
                sound_id,
                name,
                emoji,
                volume_str,
                creator,
                available
            ))

    def filter_sounds_list(self):
        """Filter the sounds list based on search input"""
        search_term = self.mgmt_search_var.get().lower()

        if not search_term:
            # No filter, show all
            self.populate_sounds_tree(self.mgmt_all_sounds)
            return

        # Filter sounds by name, emoji, or creator
        filtered_sounds = []
        for sound in self.mgmt_all_sounds:
            name = sound.get('name', '').lower()
            emoji = sound.get('emoji_name', '').lower()
            user = sound.get('user', {})
            creator = (user.get('global_name') or user.get('username', '')).lower()

            if search_term in name or search_term in emoji or search_term in creator:
                filtered_sounds.append(sound)

        self.populate_sounds_tree(filtered_sounds)

    def refresh_sound_management_info(self):
        """Refresh sound management info display"""
        if not self.selected_guild_id:
            messagebox.showerror("Error", "No Discord server selected")
            return

        def load():
            try:
                self.root.after(0, lambda: self.status_var.set("Loading server info..."))

                # Get soundboard info
                info = self.soundboard.get_guild_soundboard_info(self.selected_guild_id)

                # Update UI
                def update_ui():
                    self.mgmt_guild_name_label.config(text=info['guild_name'])

                    tier = info['premium_tier']
                    tier_text = f"Tier {tier}"
                    if tier == 0:
                        tier_text += " (No Boost)"
                    self.mgmt_tier_label.config(text=tier_text)

                    self.mgmt_boosts_label.config(text=str(info['premium_subscription_count']))

                    slots_text = f"{info['current_sounds_count']} / {info['max_soundboard_slots']}"
                    self.mgmt_slots_label.config(text=slots_text)

                    available = info['available_slots']
                    self.mgmt_available_label.config(text=str(available))

                    # Color code available slots
                    if available <= 0:
                        self.mgmt_available_label.config(foreground='red')
                    elif available <= 5:
                        self.mgmt_available_label.config(foreground='orange')
                    else:
                        self.mgmt_available_label.config(foreground='green')

                    self.status_var.set("Server info loaded")

                self.root.after(0, update_ui)

            except Exception as e:
                error_msg = f"Failed to load server info: {str(e)}"
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: self.show_error("Load Error", error_msg, e))

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def create_settings_tab(self):
        """Create settings/info tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Settings & Info")

        container = ttk.Frame(tab, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Discord Settings Section
        settings_frame = ttk.LabelFrame(container, text="Discord Settings", padding=15)
        settings_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(settings_frame, text="Configure your Discord bot credentials and server settings.",
                  foreground='gray', font=('Segoe UI', 9)).pack(pady=(0, 10))

        ttk.Button(settings_frame, text="⚙ Configure Discord Settings",
                  command=self.open_settings_dialog, style='Action.TButton').pack()

        # Bot info
        ttk.Label(container, text="Bot Information", style='Header.TLabel').pack(pady=(10, 10))

        self.bot_info_text = scrolledtext.ScrolledText(container, height=10, width=70, state=tk.DISABLED)
        self.bot_info_text.pack(pady=10, fill=tk.BOTH, expand=True)

        # Refresh button
        ttk.Button(container, text="Refresh Bot Info", command=self.refresh_bot_info).pack(pady=10)

    def open_settings_dialog(self):
        """Open the settings dialog"""
        def on_save(credentials):
            """Callback after settings are saved"""
            # Reinitialize Discord with new credentials
            messagebox.showinfo("Settings Saved",
                              "Discord credentials updated. Reconnecting to Discord...",
                              parent=self.root)
            self.initialize_discord()

        show_settings_dialog(self.root, self.config_manager, on_save_callback=on_save)

    def check_credentials_and_initialize(self):
        """Check if credentials exist, prompt if missing, then initialize Discord"""
        if not self.config_manager.has_credentials():
            # Show a message and open settings dialog
            response = messagebox.askyesno(
                "Discord Configuration Required",
                "Discord credentials are not configured.\n\n"
                "Would you like to configure them now?",
                icon='warning'
            )

            if response:
                def on_save(credentials):
                    """Callback after first-time settings are saved"""
                    messagebox.showinfo("Setup Complete",
                                      "Discord credentials saved. Connecting to Discord...",
                                      parent=self.root)
                    self.initialize_discord()

                show_settings_dialog(self.root, self.config_manager, on_save_callback=on_save)
            else:
                messagebox.showwarning("Warning",
                                     "The application requires Discord credentials to function.\n"
                                     "You can configure them later in Settings & Info tab.")
        else:
            # Credentials exist, initialize normally
            self.initialize_discord()

    def initialize_discord(self):
        """Initialize Discord authentication in background thread"""
        def init():
            try:
                self.status_var.set("Connecting to Discord...")

                # Load guild ID from config
                self.default_guild_id = self.config_manager.get('discord_guild_id')

                # Get credentials from config
                credentials = self.config_manager.get_credentials()
                api_key = credentials.get('discord_api_key')
                app_id = credentials.get('discord_application_id')

                # Set environment variables for DiscordAuth to use
                os.environ['DISCORD_API_KEY'] = api_key
                if app_id:
                    os.environ['DISCORD_APPLICATION_ID'] = app_id

                self.discord = DiscordAuth()
                self.soundboard = SoundboardManager(self.discord)
                self.youtube_converter = YouTubeToSound(self.soundboard, output_dir="sounds")

                # Get bot info
                self.bot_info = self.discord.get_bot_info()
                self.guilds = self.discord.get_guilds()

                # Update GUI with guild info
                self.root.after(0, self.update_guild_info)
                self.root.after(0, lambda: self.status_var.set("Connected to Discord"))
                self.root.after(0, self.refresh_bot_info)

                # Auto-load sound management info
                self.root.after(0, self.refresh_sound_management_info)

                # Auto-load sounds list
                self.root.after(0, self.load_sounds_list)

            except Exception as e:
                error_msg = f"Failed to connect to Discord: {str(e)}"
                self.root.after(0, lambda: self.status_var.set(error_msg))
                self.root.after(0, lambda: self.show_error("Connection Error", error_msg, e))

        thread = threading.Thread(target=init, daemon=True)
        thread.start()

    def update_guild_info(self):
        """Update guild display with available guilds"""
        if self.guilds:
            # Try to find the default guild from .env file
            guild_name = "Unknown"
            found_guild = False

            if self.default_guild_id:
                for guild in self.guilds:
                    if guild['id'] == self.default_guild_id:
                        guild_name = guild['name']
                        self.selected_guild_id = self.default_guild_id
                        found_guild = True
                        break

                if not found_guild:
                    # Still use the default_guild_id even if not found
                    self.selected_guild_id = self.default_guild_id
                    guild_name = "Unknown"
            else:
                # If no default guild ID in .env, use the first guild
                if self.guilds:
                    self.selected_guild_id = self.guilds[0]['id']
                    guild_name = self.guilds[0]['name']

            # Update the display label in step 2
            if self.selected_guild_id:
                display_text = f"{guild_name} ({self.selected_guild_id})"
                self.step2_guild_display_label.config(text=display_text)
            else:
                self.step2_guild_display_label.config(text="Unknown")
        else:
            self.step2_guild_display_label.config(text="Unknown (no guilds)")

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
