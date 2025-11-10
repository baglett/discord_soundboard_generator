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

        # Preview state
        self.preview_audio_path = None
        self.downloaded_audio_path = None

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
        self.create_bulk_upload_tab()
        self.create_sounds_list_tab()
        self.create_settings_tab()

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))

    def create_youtube_tab(self):
        """Create YouTube to Sound tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="YouTube to Sound")

        # Main container with padding
        container = ttk.Frame(tab, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(container, text="Create Soundboard Sound from YouTube",
                  style='Header.TLabel').grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Sound Name (determines temp file name)
        ttk.Label(container, text="Sound Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.temp_sound_name_entry = ttk.Entry(container, width=30)
        self.temp_sound_name_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.temp_sound_name_entry.insert(0, "rick_roll")

        # Add helpful hint below sound name field
        hint_sound_name = ttk.Label(container, text="This will be used for the temporary file name",
                              font=('Arial', 8), foreground='gray')
        hint_sound_name.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=(35, 0), padx=(10, 0))

        # YouTube URL
        ttk.Label(container, text="YouTube URL:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.youtube_url_entry = ttk.Entry(container, width=50)
        self.youtube_url_entry.grid(row=2, column=1, columnspan=2, sticky=tk.EW, pady=5, padx=(10, 0))
        self.youtube_url_entry.insert(0, "https://www.youtube.com/watch?v=xvFZjo5PgG0")

        # Add helpful hint below URL field
        hint_label = ttk.Label(container, text="⚠ Use direct video URL (youtube.com/watch?v=... or youtu.be/...), not search URLs",
                              font=('Arial', 8), foreground='gray')
        hint_label.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=(35, 0), padx=(10, 0))

        # Timestamps
        ttk.Label(container, text="Start Time (MM:SS):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.start_time_entry = ttk.Entry(container, width=20)
        self.start_time_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.start_time_entry.insert(0, "0:00")

        ttk.Label(container, text="End Time (MM:SS):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.end_time_entry = ttk.Entry(container, width=20)
        self.end_time_entry.grid(row=4, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.end_time_entry.insert(0, "0:07")

        # Preview button
        self.preview_btn = ttk.Button(container, text="Create Preview",
                                      command=self.create_preview, style='Action.TButton')
        self.preview_btn.grid(row=5, column=0, columnspan=3, pady=20)

        # Play preview button (initially disabled)
        self.play_preview_btn = ttk.Button(container, text="Play Preview",
                                           command=self.play_preview, state=tk.DISABLED)
        self.play_preview_btn.grid(row=6, column=0, columnspan=3, pady=5)

        # Separator
        ttk.Separator(container, orient=tk.HORIZONTAL).grid(row=7, column=0, columnspan=3,
                                                             sticky=tk.EW, pady=20)

        # Sound details
        ttk.Label(container, text="Sound Details", style='Header.TLabel').grid(
            row=8, column=0, columnspan=3, pady=(0, 10))

        ttk.Label(container, text="Sound Name:").grid(row=9, column=0, sticky=tk.W, pady=5)
        self.sound_name_entry = ttk.Entry(container, width=30)
        self.sound_name_entry.grid(row=9, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        ttk.Label(container, text="Guild:").grid(row=10, column=0, sticky=tk.W, pady=5)
        self.guild_combo = ttk.Combobox(container, width=30, state='readonly')
        self.guild_combo.grid(row=10, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.guild_combo.bind('<<ComboboxSelected>>', self.on_guild_selected)

        ttk.Label(container, text="Volume (0.0-1.0):").grid(row=11, column=0, sticky=tk.W, pady=5)
        self.volume_entry = ttk.Entry(container, width=10)
        self.volume_entry.grid(row=11, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.volume_entry.insert(0, "1.0")

        ttk.Label(container, text="Emoji (optional):").grid(row=12, column=0, sticky=tk.W, pady=5)
        self.emoji_entry = ttk.Entry(container, width=10)
        self.emoji_entry.grid(row=12, column=1, sticky=tk.W, pady=5, padx=(10, 0))

        # Create sound button
        self.create_sound_btn = ttk.Button(container, text="Upload to Discord",
                                           command=self.create_sound_from_youtube,
                                           style='Action.TButton', state=tk.DISABLED)
        self.create_sound_btn.grid(row=13, column=0, columnspan=3, pady=20)

        # Configure grid weights
        container.columnconfigure(1, weight=1)

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
        """Update all guild combo boxes with available guilds"""
        guild_names = [f"{g['name']} ({g['id']})" for g in self.guilds]

        self.guild_combo['values'] = guild_names
        self.bulk_guild_combo['values'] = guild_names
        self.list_guild_combo['values'] = guild_names

        if guild_names:
            self.guild_combo.current(0)
            self.bulk_guild_combo.current(0)
            self.list_guild_combo.current(0)
            self.on_guild_selected()

    def on_guild_selected(self, event=None):
        """Handle guild selection"""
        selection = self.guild_combo.get()
        if selection:
            # Extract guild ID from selection (format: "Name (ID)")
            guild_id = selection.split('(')[-1].rstrip(')')
            self.selected_guild_id = guild_id

    def create_preview(self):
        """Create preview of YouTube audio clip"""
        def create():
            try:
                youtube_url = self.youtube_url_entry.get().strip()
                start_time = self.start_time_entry.get().strip()
                end_time = self.end_time_entry.get().strip()
                temp_sound_name = self.temp_sound_name_entry.get().strip()

                if not youtube_url:
                    self.root.after(0, lambda: messagebox.showerror("Error", "YouTube URL is required"))
                    return

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
                self.root.after(0, lambda: self.status_var.set("Uploading to Discord..."))
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

                success_msg = f"Successfully created soundboard sound: {sound_name}"
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
