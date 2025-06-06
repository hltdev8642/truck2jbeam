#!/usr/bin/env python3
"""
Demo script for the RoR GUI application
"""

import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os

def check_dependencies():
    """Check if required dependencies are available"""
    try:
        import requests
        import bs4
        return True
    except ImportError:
        return False

def show_gui_features():
    """Show GUI features information"""
    features_text = """🚀 RoR Downloader & truck2jbeam Converter GUI

Key Features:

🔍 SEARCH INTERFACE
• Efficient sitemap-based resource discovery
• Real-time search through 935+ RoR resources
• Category filtering and result limits
• Fast URL filtering (~0.5s search times)

📊 RESOURCE BROWSER
• Table view with ID, title, author, category
• Download status tracking
• Multi-select capabilities
• Detailed resource information dialogs

⬇️ DOWNLOAD MANAGEMENT
• Download queue with progress indicators
• Pause/resume functionality
• Concurrent download management
• Auto-extraction options

🔄 CONVERSION PIPELINE
• Integrated truck2jbeam conversion
• Mesh conversion to DAE/Blend formats
• Configurable output settings
• Progress tracking and error handling

📁 FILE MANAGEMENT
• File browser for input selection
• Output directory management
• Quick folder access buttons
• Drag-and-drop support (planned)

⚙️ SETTINGS PANEL
• Download directory configuration
• Conversion parameter settings
• Mesh output format selection
• User preference management

📝 STATUS & LOGGING
• Real-time operation status
• Comprehensive logging panel
• Error reporting and completion messages
• Collapsible log view

🎯 KEYBOARD SHORTCUTS
• Ctrl+O: Open RoR file
• Ctrl+F: Focus search
• F5: Perform search
• Ctrl+Q: Quit application

🖥️ RESPONSIVE DESIGN
• Resizable panels and windows
• Cross-platform compatibility
• Tooltips and help text
• Modern tkinter interface
"""
    
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    messagebox.showinfo("RoR GUI Features", features_text)
    root.destroy()

def launch_gui():
    """Launch the GUI application"""
    if not check_dependencies():
        root = tk.Tk()
        root.withdraw()
        
        install_deps = messagebox.askyesno(
            "Missing Dependencies",
            "Required dependencies are missing.\n\n"
            "Would you like to install them now?\n"
            "(This will run: pip install requests beautifulsoup4)"
        )
        
        if install_deps:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4"])
                messagebox.showinfo("Success", "Dependencies installed successfully!\nLaunching GUI...")
            except subprocess.CalledProcessError as e:
                messagebox.showerror("Installation Failed", f"Failed to install dependencies:\n{e}")
                root.destroy()
                return
        else:
            root.destroy()
            return
        
        root.destroy()
    
    # Launch the GUI
    try:
        subprocess.Popen([sys.executable, "ror_gui.py"])
        print("✅ RoR GUI launched successfully!")
        print("   Check your taskbar for the application window.")
    except Exception as e:
        print(f"❌ Failed to launch GUI: {e}")

def main():
    """Main demo function"""
    print("🎮 RoR Downloader & truck2jbeam Converter GUI Demo")
    print("=" * 60)
    
    while True:
        print("\nChoose an option:")
        print("1. Show GUI Features")
        print("2. Launch GUI Application")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            show_gui_features()
        elif choice == "2":
            launch_gui()
            break
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()
