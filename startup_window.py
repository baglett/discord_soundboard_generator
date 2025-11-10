"""
Startup Window for Discord Soundboard Generator
Shows initialization progress including ffmpeg installation
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from pathlib import Path
import sys


class StartupWindow:
    """Splash screen showing initialization progress"""

    def __init__(self):
        """Initialize the startup window"""
        self.root = tk.Tk()
        self.root.title("Discord Soundboard Generator - Starting")
        self.root.geometry("600x300")
        self.root.resizable(False, False)

        # Center window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.root.winfo_screenheight() // 2) - (300 // 2)
        self.root.geometry(f'+{x}+{y}')

        # Remove window decorations for splash effect
        self.root.overrideredirect(True)

        # Main frame with border
        main_frame = tk.Frame(self.root, relief=tk.RAISED, borderwidth=2, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = tk.Frame(main_frame, bg='#5865F2', height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        tk.Label(
            header_frame,
            text="Discord Soundboard Generator",
            font=('Arial', 18, 'bold'),
            bg='#5865F2',
            fg='white'
        ).pack(pady=25)

        # Content frame
        content_frame = tk.Frame(main_frame, bg='white', padx=40, pady=20)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Status label
        self.status_label = tk.Label(
            content_frame,
            text="Initializing...",
            font=('Arial', 11),
            bg='white',
            fg='#333333'
        )
        self.status_label.pack(pady=(10, 5))

        # Progress bar
        self.progress = ttk.Progressbar(
            content_frame,
            mode='indeterminate',
            length=400
        )
        self.progress.pack(pady=10)
        self.progress.start(10)

        # Details text (scrollable)
        details_frame = tk.Frame(content_frame, bg='white')
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        scrollbar = tk.Scrollbar(details_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.details_text = tk.Text(
            details_frame,
            height=6,
            width=60,
            font=('Courier', 9),
            bg='#f5f5f5',
            fg='#666666',
            relief=tk.FLAT,
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD
        )
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.details_text.yview)

        # Status variables
        self.initialization_complete = False
        self.initialization_success = False
        self.error_message = None

    def update_status(self, message: str, add_to_details: bool = True):
        """
        Update the status message

        Args:
            message: Status message to display
            add_to_details: Whether to add to the details log
        """
        self.status_label.config(text=message)

        if add_to_details:
            self.details_text.insert(tk.END, f"{message}\n")
            self.details_text.see(tk.END)
            self.root.update()

    def set_progress_determinate(self, value: float):
        """
        Set progress bar to determinate mode with a specific value

        Args:
            value: Progress value (0-100)
        """
        self.progress.stop()
        self.progress.config(mode='determinate', maximum=100, value=value)

    def complete_initialization(self, success: bool, error_message: str = None):
        """
        Mark initialization as complete

        Args:
            success: Whether initialization was successful
            error_message: Error message if initialization failed
        """
        self.initialization_complete = True
        self.initialization_success = success
        self.error_message = error_message

        if success:
            self.progress.stop()
            self.set_progress_determinate(100)
            self.update_status("✓ Initialization complete!", add_to_details=True)
            # Close after a brief delay
            self.root.after(500, self.root.destroy)
        else:
            self.progress.stop()
            self.update_status("✗ Initialization failed", add_to_details=True)

    def run_initialization(self, init_function):
        """
        Run initialization function in a background thread

        Args:
            init_function: Function to run for initialization (should accept progress_callback)
        """
        def init_thread():
            try:
                # Run the initialization function with our progress callback
                success = init_function(self.update_status)
                self.root.after(0, lambda: self.complete_initialization(success))
            except Exception as e:
                error_msg = f"Initialization error: {str(e)}"
                self.root.after(0, lambda: self.complete_initialization(False, error_msg))

        thread = threading.Thread(target=init_thread, daemon=True)
        thread.start()

    def show(self) -> bool:
        """
        Show the startup window and wait for completion

        Returns:
            bool: True if initialization successful, False otherwise
        """
        self.root.mainloop()
        return self.initialization_success


def check_ffmpeg_with_progress(progress_callback) -> bool:
    """
    Check for ffmpeg and install if needed, reporting progress

    Args:
        progress_callback: Function to call with progress updates

    Returns:
        bool: True if ffmpeg is available, False otherwise
    """
    from pathlib import Path
    import sys

    # Add setup to path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root / "setup"))

    from ffmpeg_installer import FFmpegInstaller

    progress_callback("Checking for ffmpeg installation...")

    installer = FFmpegInstaller(project_root)

    # If already installed, return True
    if installer.is_ffmpeg_installed():
        progress_callback("FFmpeg already installed")
        return True

    # FFmpeg not found - ask user for permission to download
    progress_callback("FFmpeg not found.")

    # Create a temporary root window for the messagebox
    temp_root = tk.Tk()
    temp_root.withdraw()  # Hide the window
    temp_root.attributes('-topmost', True)  # Keep dialog on top

    user_confirmed = messagebox.askyesno(
        "Download FFmpeg?",
        "FFmpeg is required to convert audio files for Discord.\n\n"
        "Would you like to download and install it automatically?\n\n"
        "(Download size: ~80-100 MB)",
        icon='question'
    )

    temp_root.destroy()

    if not user_confirmed:
        progress_callback("User declined automatic installation.")
        instructions = installer.show_manual_install_instructions()
        progress_callback("\n" + instructions)
        return False

    progress_callback("User approved download. Installing FFmpeg...")
    success = installer.install(progress_callback)

    if not success:
        # Show manual installation instructions
        instructions = installer.show_manual_install_instructions()
        progress_callback("\n" + instructions)

    return success


if __name__ == "__main__":
    """Test the startup window"""
    import time

    def test_init(progress_callback):
        """Test initialization function"""
        progress_callback("Testing startup window...")
        time.sleep(1)
        progress_callback("Checking dependencies...")
        time.sleep(1)
        progress_callback("Loading configuration...")
        time.sleep(1)
        progress_callback("Connecting to services...")
        time.sleep(1)
        return True

    window = StartupWindow()
    window.run_initialization(test_init)
    success = window.show()

    if success:
        print("Initialization successful!")
    else:
        print("Initialization failed!")
