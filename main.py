"""
Main entry point for Discord Soundboard Generator
Shows startup window with ffmpeg installation progress, then launches GUI
"""

import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

# Import startup window and GUI
from startup_window import StartupWindow, check_ffmpeg_with_progress
from gui_wizard import SoundboardGUI


def main():
    """
    Main function to run the Discord Soundboard Generator GUI
    """
    try:
        # Show startup window with ffmpeg check
        print("Starting Discord Soundboard Generator...")

        startup = StartupWindow()
        startup.run_initialization(check_ffmpeg_with_progress)
        success = startup.show()

        if not success:
            # Show error dialog with instructions
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "FFmpeg Required",
                "FFmpeg is required but could not be installed automatically.\n\n"
                "Please check the startup window for installation instructions,\n"
                "or refer to the README.md file."
            )
            root.destroy()
            print("\nFFmpeg is required but not installed.")
            print("Please install ffmpeg and restart the application.")
            sys.exit(1)

        print("✓ FFmpeg is available")

        # Launch main GUI
        print("Launching Discord Soundboard Generator GUI...")
        root = tk.Tk()
        app = SoundboardGUI(root)
        root.mainloop()

    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

        # Show error dialog if possible
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Application Error",
                f"Failed to start application:\n\n{str(e)}\n\nCheck console for details."
            )
            root.destroy()
        except:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
