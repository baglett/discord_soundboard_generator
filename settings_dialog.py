"""
Settings Dialog for Discord Soundboard Generator
Manages Discord credentials with obfuscation
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict


class SettingsDialog:
    """Settings dialog for managing Discord credentials"""

    def __init__(self, parent, config_manager, on_save_callback=None):
        """
        Initialize settings dialog

        Args:
            parent: Parent window
            config_manager: ConfigManager instance
            on_save_callback: Optional callback function called after successful save
        """
        self.parent = parent
        self.config_manager = config_manager
        self.on_save_callback = on_save_callback
        self.result = None

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("600x400")
        self.dialog.minsize(500, 350)

        # Make it modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Variables for storing visibility state
        self.show_api_key = tk.BooleanVar(value=False)
        self.show_app_id = tk.BooleanVar(value=False)
        self.show_guild_id = tk.BooleanVar(value=False)

        # Variables for credentials
        self.api_key_var = tk.StringVar()
        self.app_id_var = tk.StringVar()
        self.guild_id_var = tk.StringVar()

        # Load current credentials
        credentials = self.config_manager.get_credentials()
        self.api_key_var.set(credentials.get('discord_api_key', ''))
        self.app_id_var.set(credentials.get('discord_application_id', ''))
        self.guild_id_var.set(credentials.get('discord_guild_id', ''))

        self.create_widgets()

    def create_widgets(self):
        """Create dialog widgets"""
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Discord Configuration",
            font=('Segoe UI', 14, 'bold')
        )
        title_label.pack(pady=(0, 20))

        # Credentials frame
        creds_frame = ttk.Frame(main_frame)
        creds_frame.pack(fill=tk.BOTH, expand=True)

        # API Key
        self.create_credential_row(
            creds_frame, 0,
            "Discord Bot Token:",
            self.api_key_var,
            self.show_api_key,
            "Enter your Discord bot token"
        )

        # Application ID
        self.create_credential_row(
            creds_frame, 1,
            "Discord Application ID:",
            self.app_id_var,
            self.show_app_id,
            "Enter your Discord application ID"
        )

        # Guild ID
        self.create_credential_row(
            creds_frame, 2,
            "Discord Guild ID:",
            self.guild_id_var,
            self.show_guild_id,
            "Enter your Discord server (guild) ID"
        )

        # Help text
        help_frame = ttk.Frame(main_frame)
        help_frame.pack(fill=tk.X, pady=(20, 10))

        help_text = ttk.Label(
            help_frame,
            text="💡 Tip: Get your bot token and IDs from Discord Developer Portal",
            foreground='gray',
            font=('Segoe UI', 9)
        )
        help_text.pack()

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Save button
        save_btn = ttk.Button(
            button_frame,
            text="Save",
            command=self.save_settings,
            style='Accent.TButton'
        )
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel
        )
        cancel_btn.pack(side=tk.RIGHT)

        # Handle window close button
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)

    def create_credential_row(self, parent, row, label_text, text_var, show_var, placeholder):
        """
        Create a row with label, obfuscated entry, and show/hide button

        Args:
            parent: Parent frame
            row: Grid row number
            label_text: Label text
            text_var: StringVar for the entry
            show_var: BooleanVar for show/hide state
            placeholder: Placeholder text
        """
        # Container frame for the row
        row_frame = ttk.Frame(parent)
        row_frame.grid(row=row, column=0, sticky=tk.EW, pady=10)
        row_frame.columnconfigure(1, weight=1)

        # Label
        label = ttk.Label(row_frame, text=label_text, width=20, anchor=tk.W)
        label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        # Entry field (obfuscated by default)
        entry = ttk.Entry(row_frame, textvariable=text_var, show='•')
        entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 5))

        # Store entry reference for toggling visibility
        entry_widget = entry

        # Show/Hide button
        def toggle_visibility():
            if show_var.get():
                entry_widget.config(show='')
                toggle_btn.config(text='👁')
            else:
                entry_widget.config(show='•')
                toggle_btn.config(text='👁')

        toggle_btn = ttk.Button(
            row_frame,
            text='👁',
            width=3,
            command=lambda: [show_var.set(not show_var.get()), toggle_visibility()]
        )
        toggle_btn.grid(row=0, column=2, padx=(0, 0))

    def save_settings(self):
        """Save settings and close dialog"""
        # Get values
        api_key = self.api_key_var.get().strip()
        app_id = self.app_id_var.get().strip()
        guild_id = self.guild_id_var.get().strip()

        # Validate
        if not api_key:
            messagebox.showerror("Validation Error", "Discord Bot Token is required", parent=self.dialog)
            return

        if not app_id:
            messagebox.showerror("Validation Error", "Discord Application ID is required", parent=self.dialog)
            return

        if not guild_id:
            messagebox.showerror("Validation Error", "Discord Guild ID is required", parent=self.dialog)
            return

        # Save to config
        success = self.config_manager.save_credentials(api_key, app_id, guild_id)

        if success:
            messagebox.showinfo("Success", "Settings saved successfully!", parent=self.dialog)
            self.result = {
                'discord_api_key': api_key,
                'discord_application_id': app_id,
                'discord_guild_id': guild_id
            }

            # Call callback if provided
            if self.on_save_callback:
                self.on_save_callback(self.result)

            self.dialog.destroy()
        else:
            messagebox.showerror("Error", "Failed to save settings", parent=self.dialog)

    def cancel(self):
        """Cancel and close dialog"""
        self.dialog.destroy()

    def show(self):
        """Show dialog and wait for it to close"""
        self.dialog.wait_window()
        return self.result


def show_settings_dialog(parent, config_manager, on_save_callback=None):
    """
    Show settings dialog

    Args:
        parent: Parent window
        config_manager: ConfigManager instance
        on_save_callback: Optional callback function called after successful save

    Returns:
        Dictionary with saved credentials or None if cancelled
    """
    dialog = SettingsDialog(parent, config_manager, on_save_callback)
    return dialog.show()
