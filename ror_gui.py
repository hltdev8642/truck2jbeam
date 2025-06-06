#!/usr/bin/env python3
"""
RoR Downloader & truck2jbeam Converter GUI
A comprehensive graphical interface for RoR resource discovery, downloading, and BeamNG conversion
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import webbrowser

# Import our existing modules
from ror_downloader import RoRDownloader, RoRResource
from truck2jbeam import convert_single_file, ConversionConfig

class RoRGUI:
    """Main GUI application class"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RoR Downloader & truck2jbeam Converter")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Application state
        self.downloader = None
        self.download_queue = queue.Queue()
        self.search_results: List[RoRResource] = []
        self.selected_resources: List[RoRResource] = []
        self.settings = self.load_settings()
        
        # GUI components
        self.setup_styles()
        self.create_menu()
        self.create_main_interface()
        self.setup_logging()
        
        # Initialize downloader
        self.initialize_downloader()
        
        # Start background tasks
        self.start_background_tasks()
        
        # Bind events
        self.setup_keyboard_shortcuts()
    
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        
        # Configure treeview for better appearance
        style.configure("Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=('TkDefaultFont', 9, 'bold'))
        
        # Configure progress bar
        style.configure("TProgressbar", thickness=20)
    
    def create_menu(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open RoR File...", command=self.open_ror_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Open Download Folder", command=self.open_download_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Settings...", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Refresh Sitemap Stats", command=self.refresh_sitemap_stats)
        tools_menu.add_command(label="Clear Download History", command=self.clear_download_history)
        tools_menu.add_command(label="Convert Local Files...", command=self.convert_local_files)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="GitHub Repository", command=lambda: webbrowser.open("https://github.com/hltdev8642/truck2jbeam"))
    
    def create_main_interface(self):
        """Create the main interface layout"""
        # Create main paned window
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Search and Results
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=2)
        
        # Right panel - Downloads and Conversion
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)
        
        # Create left panel components
        self.create_search_panel(left_frame)
        self.create_results_panel(left_frame)
        
        # Create right panel components
        self.create_download_panel(right_frame)
        self.create_conversion_panel(right_frame)
        
        # Create bottom status panel
        self.create_status_panel()
    
    def create_search_panel(self, parent):
        """Create search interface panel"""
        search_frame = ttk.LabelFrame(parent, text="Search RoR Resources", padding=10)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Search input
        search_input_frame = ttk.Frame(search_frame)
        search_input_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_input_frame, text="Search:").pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_input_frame, textvariable=self.search_var, font=('TkDefaultFont', 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.search_entry.bind('<Return>', self.perform_search)
        
        # Search controls
        controls_frame = ttk.Frame(search_frame)
        controls_frame.pack(fill=tk.X)
        
        self.search_button = ttk.Button(controls_frame, text="Search", command=self.perform_search)
        self.search_button.pack(side=tk.LEFT)
        
        self.clear_button = ttk.Button(controls_frame, text="Clear", command=self.clear_search)
        self.clear_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Search status
        self.search_status_var = tk.StringVar(value="Ready to search")
        self.search_status_label = ttk.Label(controls_frame, textvariable=self.search_status_var, foreground="gray")
        self.search_status_label.pack(side=tk.RIGHT)
        
        # Search options
        options_frame = ttk.Frame(search_frame)
        options_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(options_frame, text="Category:").pack(side=tk.LEFT)
        
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(options_frame, textvariable=self.category_var, 
                                          values=["All", "Cars & Light Trucks", "Trucks", "Buses", "Boats", "Aircraft", "Trailers"],
                                          state="readonly", width=20)
        self.category_combo.set("All")
        self.category_combo.pack(side=tk.LEFT, padx=(5, 0))
        
        # Results limit
        ttk.Label(options_frame, text="Limit:").pack(side=tk.LEFT, padx=(20, 0))
        
        self.limit_var = tk.StringVar(value="20")
        self.limit_spin = ttk.Spinbox(options_frame, from_=5, to=100, textvariable=self.limit_var, width=10)
        self.limit_spin.pack(side=tk.LEFT, padx=(5, 0))
    
    def create_results_panel(self, parent):
        """Create search results panel"""
        results_frame = ttk.LabelFrame(parent, text="Search Results", padding=5)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Results treeview
        columns = ("ID", "Title", "Author", "Category", "Status")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        self.results_tree.heading("ID", text="ID")
        self.results_tree.heading("Title", text="Title")
        self.results_tree.heading("Author", text="Author")
        self.results_tree.heading("Category", text="Category")
        self.results_tree.heading("Status", text="Status")
        
        self.results_tree.column("ID", width=60, minwidth=50)
        self.results_tree.column("Title", width=300, minwidth=200)
        self.results_tree.column("Author", width=150, minwidth=100)
        self.results_tree.column("Category", width=120, minwidth=100)
        self.results_tree.column("Status", width=80, minwidth=70)
        
        # Scrollbars for treeview
        tree_scroll_y = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        tree_scroll_x = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        # Pack treeview and scrollbars
        self.results_tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")
        
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)
        
        # Results controls
        results_controls = ttk.Frame(results_frame)
        results_controls.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        
        self.download_selected_button = ttk.Button(results_controls, text="Download Selected", 
                                                  command=self.download_selected, state=tk.DISABLED)
        self.download_selected_button.pack(side=tk.LEFT)
        
        self.select_all_button = ttk.Button(results_controls, text="Select All", command=self.select_all_results)
        self.select_all_button.pack(side=tk.LEFT, padx=(5, 0))
        
        self.view_details_button = ttk.Button(results_controls, text="View Details", 
                                             command=self.view_resource_details, state=tk.DISABLED)
        self.view_details_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Results info
        self.results_info_var = tk.StringVar(value="No search performed")
        self.results_info_label = ttk.Label(results_controls, textvariable=self.results_info_var, foreground="gray")
        self.results_info_label.pack(side=tk.RIGHT)
        
        # Bind treeview events
        self.results_tree.bind("<<TreeviewSelect>>", self.on_result_selection)
        self.results_tree.bind("<Double-1>", self.on_result_double_click)
    
    def load_settings(self) -> Dict[str, Any]:
        """Load application settings"""
        settings_file = Path("ror_gui_settings.json")
        default_settings = {
            "download_dir": "./downloads",
            "output_dir": "./output",
            "convert_meshes": True,
            "mesh_output_format": "dae",
            "auto_extract": True,
            "max_concurrent_downloads": 3,
            "window_geometry": "1200x800"
        }
        
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                # Merge with defaults for any missing keys
                for key, value in default_settings.items():
                    if key not in settings:
                        settings[key] = value
                return settings
            except Exception as e:
                print(f"Error loading settings: {e}")
        
        return default_settings
    
    def save_settings(self):
        """Save application settings"""
        try:
            settings_file = Path("ror_gui_settings.json")
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def initialize_downloader(self):
        """Initialize the RoR downloader"""
        try:
            self.downloader = RoRDownloader(
                download_dir=self.settings["download_dir"],
                max_workers=self.settings["max_concurrent_downloads"]
            )
            self.log_message("RoR Downloader initialized successfully")
        except Exception as e:
            self.log_message(f"Error initializing downloader: {e}", "ERROR")
            messagebox.showerror("Initialization Error", f"Failed to initialize RoR downloader:\n{e}")

    def create_download_panel(self, parent):
        """Create download management panel"""
        download_frame = ttk.LabelFrame(parent, text="Download Queue", padding=5)
        download_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Download queue treeview
        queue_columns = ("Title", "Progress", "Status")
        self.download_tree = ttk.Treeview(download_frame, columns=queue_columns, show="headings", height=8)

        self.download_tree.heading("Title", text="Title")
        self.download_tree.heading("Progress", text="Progress")
        self.download_tree.heading("Status", text="Status")

        self.download_tree.column("Title", width=200, minwidth=150)
        self.download_tree.column("Progress", width=80, minwidth=60)
        self.download_tree.column("Status", width=100, minwidth=80)

        # Download queue scrollbar
        download_scroll = ttk.Scrollbar(download_frame, orient=tk.VERTICAL, command=self.download_tree.yview)
        self.download_tree.configure(yscrollcommand=download_scroll.set)

        self.download_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        download_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Download controls
        download_controls = ttk.Frame(download_frame)
        download_controls.pack(fill=tk.X, pady=(5, 0))

        self.pause_button = ttk.Button(download_controls, text="Pause", command=self.pause_downloads, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT)

        self.resume_button = ttk.Button(download_controls, text="Resume", command=self.resume_downloads, state=tk.DISABLED)
        self.resume_button.pack(side=tk.LEFT, padx=(5, 0))

        self.clear_completed_button = ttk.Button(download_controls, text="Clear Completed", command=self.clear_completed_downloads)
        self.clear_completed_button.pack(side=tk.LEFT, padx=(5, 0))

        # Download progress
        self.overall_progress_var = tk.StringVar(value="No active downloads")
        self.overall_progress_label = ttk.Label(download_controls, textvariable=self.overall_progress_var, foreground="gray")
        self.overall_progress_label.pack(side=tk.RIGHT)

    def create_conversion_panel(self, parent):
        """Create conversion settings panel"""
        conversion_frame = ttk.LabelFrame(parent, text="truck2jbeam Conversion", padding=10)
        conversion_frame.pack(fill=tk.X, padx=5, pady=5)

        # Input file selection
        input_frame = ttk.Frame(conversion_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(input_frame, text="Input File:").pack(anchor=tk.W)

        input_select_frame = ttk.Frame(input_frame)
        input_select_frame.pack(fill=tk.X, pady=(2, 0))

        self.input_file_var = tk.StringVar()
        self.input_file_entry = ttk.Entry(input_select_frame, textvariable=self.input_file_var, state="readonly")
        self.input_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.browse_input_button = ttk.Button(input_select_frame, text="Browse...", command=self.browse_input_file)
        self.browse_input_button.pack(side=tk.RIGHT, padx=(5, 0))

        # Output directory selection
        output_frame = ttk.Frame(conversion_frame)
        output_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(output_frame, text="Output Directory:").pack(anchor=tk.W)

        output_select_frame = ttk.Frame(output_frame)
        output_select_frame.pack(fill=tk.X, pady=(2, 0))

        self.output_dir_var = tk.StringVar(value=self.settings["output_dir"])
        self.output_dir_entry = ttk.Entry(output_select_frame, textvariable=self.output_dir_var, state="readonly")
        self.output_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.browse_output_button = ttk.Button(output_select_frame, text="Browse...", command=self.browse_output_dir)
        self.browse_output_button.pack(side=tk.RIGHT, padx=(5, 0))

        # Conversion options
        options_frame = ttk.LabelFrame(conversion_frame, text="Conversion Options", padding=5)
        options_frame.pack(fill=tk.X, pady=(0, 10))

        # Mesh conversion
        self.convert_meshes_var = tk.BooleanVar(value=self.settings["convert_meshes"])
        self.convert_meshes_check = ttk.Checkbutton(options_frame, text="Convert meshes", variable=self.convert_meshes_var)
        self.convert_meshes_check.pack(anchor=tk.W)

        # Mesh output format
        mesh_format_frame = ttk.Frame(options_frame)
        mesh_format_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(mesh_format_frame, text="Mesh format:").pack(side=tk.LEFT)

        self.mesh_format_var = tk.StringVar(value=self.settings["mesh_output_format"])
        self.mesh_format_combo = ttk.Combobox(mesh_format_frame, textvariable=self.mesh_format_var,
                                             values=["dae", "blend"], state="readonly", width=10)
        self.mesh_format_combo.pack(side=tk.LEFT, padx=(5, 0))

        # Conversion controls
        convert_controls = ttk.Frame(conversion_frame)
        convert_controls.pack(fill=tk.X)

        self.convert_button = ttk.Button(convert_controls, text="Convert to JBeam",
                                        command=self.start_conversion, state=tk.DISABLED)
        self.convert_button.pack(side=tk.LEFT)

        self.open_output_button = ttk.Button(convert_controls, text="Open Output Folder", command=self.open_output_folder)
        self.open_output_button.pack(side=tk.LEFT, padx=(5, 0))

        # Conversion progress
        self.conversion_progress = ttk.Progressbar(convert_controls, mode='indeterminate')
        self.conversion_progress.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))

        # Update convert button state when input file changes
        self.input_file_var.trace('w', self.update_convert_button_state)

    def create_status_panel(self):
        """Create status bar and logging panel"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # Logging panel (collapsible)
        self.log_frame = ttk.LabelFrame(self.root, text="Log Messages", padding=5)

        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=8, wrap=tk.WORD, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Log controls
        log_controls = ttk.Frame(self.log_frame)
        log_controls.pack(fill=tk.X, pady=(5, 0))

        self.clear_log_button = ttk.Button(log_controls, text="Clear Log", command=self.clear_log)
        self.clear_log_button.pack(side=tk.LEFT)

        self.toggle_log_button = ttk.Button(self.root, text="Show Log", command=self.toggle_log_panel)
        self.toggle_log_button.pack(side=tk.BOTTOM, anchor=tk.E, padx=5, pady=2)

        self.log_visible = False

    def setup_logging(self):
        """Setup logging to display in GUI"""
        # Create custom log handler
        self.log_handler = GUILogHandler(self.log_message)
        self.log_handler.setLevel(logging.INFO)

        # Add handler to root logger
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind('<Control-o>', lambda e: self.open_ror_file())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<F5>', lambda e: self.perform_search())
        self.root.bind('<Control-f>', lambda e: self.search_entry.focus_set())

    def start_background_tasks(self):
        """Start background tasks"""
        # Start download queue processor
        self.root.after(100, self.process_download_queue)

        # Start status updater
        self.root.after(1000, self.update_status)

    # Search functionality
    def perform_search(self, event=None):
        """Perform search for RoR resources"""
        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("Search", "Please enter a search query")
            return

        # Disable search controls
        self.search_button.config(state=tk.DISABLED)
        self.search_status_var.set("Searching...")

        # Start search in background thread
        search_thread = threading.Thread(target=self._search_worker, args=(query,))
        search_thread.daemon = True
        search_thread.start()

    def _search_worker(self, query):
        """Background worker for search"""
        try:
            category = self.category_var.get()
            if category == "All":
                category = ""

            limit = int(self.limit_var.get())

            # Perform search
            resources, total_pages = self.downloader.search_resources(
                query=query,
                category=category,
                page=1,
                per_page=limit
            )

            # Update GUI in main thread
            self.root.after(0, self._update_search_results, resources, total_pages, query)

        except Exception as e:
            self.root.after(0, self._search_error, str(e))

    def _update_search_results(self, resources, total_pages, query):
        """Update search results in GUI"""
        self.search_results = resources

        # Clear existing results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        # Add new results
        for resource in resources:
            status = "Downloaded" if self._is_downloaded(resource) else "Available"
            self.results_tree.insert("", tk.END, values=(
                resource.id,
                resource.title,
                resource.author,
                resource.category,
                status
            ))

        # Update status
        self.search_button.config(state=tk.NORMAL)
        self.search_status_var.set(f"Found {len(resources)} results")
        self.results_info_var.set(f"Showing {len(resources)} results for '{query}'")

        self.log_message(f"Search completed: {len(resources)} results for '{query}'")

    def _search_error(self, error_msg):
        """Handle search error"""
        self.search_button.config(state=tk.NORMAL)
        self.search_status_var.set("Search failed")
        self.log_message(f"Search error: {error_msg}", "ERROR")
        messagebox.showerror("Search Error", f"Search failed:\n{error_msg}")

    def clear_search(self):
        """Clear search results"""
        self.search_var.set("")
        self.search_results = []

        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        self.search_status_var.set("Ready to search")
        self.results_info_var.set("No search performed")

    def on_result_selection(self, event):
        """Handle result selection"""
        selection = self.results_tree.selection()
        if selection:
            self.download_selected_button.config(state=tk.NORMAL)
            self.view_details_button.config(state=tk.NORMAL)
        else:
            self.download_selected_button.config(state=tk.DISABLED)
            self.view_details_button.config(state=tk.DISABLED)

    def on_result_double_click(self, event):
        """Handle double-click on result"""
        self.view_resource_details()

    def select_all_results(self):
        """Select all search results"""
        for item in self.results_tree.get_children():
            self.results_tree.selection_add(item)

    # Download functionality
    def download_selected(self):
        """Download selected resources"""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("Download", "Please select resources to download")
            return

        selected_resources = []
        for item in selection:
            values = self.results_tree.item(item, "values")
            resource_id = int(values[0])

            # Find the resource object
            for resource in self.search_results:
                if resource.id == resource_id:
                    selected_resources.append(resource)
                    break

        # Add to download queue
        for resource in selected_resources:
            self._add_to_download_queue(resource)

        self.log_message(f"Added {len(selected_resources)} resources to download queue")

    def _add_to_download_queue(self, resource):
        """Add resource to download queue"""
        # Add to treeview
        self.download_tree.insert("", tk.END, values=(
            resource.title,
            "0%",
            "Queued"
        ))

        # Add to queue for processing
        self.download_queue.put(resource)

        # Enable download controls
        self.pause_button.config(state=tk.NORMAL)

    def process_download_queue(self):
        """Process download queue"""
        # This would be implemented to handle actual downloads
        # For now, just schedule next check
        self.root.after(100, self.process_download_queue)

    def pause_downloads(self):
        """Pause all downloads"""
        # Implementation would pause active downloads
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.NORMAL)
        self.log_message("Downloads paused")

    def resume_downloads(self):
        """Resume downloads"""
        # Implementation would resume paused downloads
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)
        self.log_message("Downloads resumed")

    def clear_completed_downloads(self):
        """Clear completed downloads from queue"""
        # Remove completed items from download tree
        for item in self.download_tree.get_children():
            values = self.download_tree.item(item, "values")
            if values[2] in ["Completed", "Failed"]:
                self.download_tree.delete(item)

    # Conversion functionality
    def browse_input_file(self):
        """Browse for input RoR file"""
        filetypes = [
            ("RoR Files", "*.truck *.trailer *.car *.boat *.airplane *.load *.train"),
            ("All Files", "*.*")
        ]

        filename = filedialog.askopenfilename(
            title="Select RoR File",
            filetypes=filetypes,
            initialdir=self.settings["download_dir"]
        )

        if filename:
            self.input_file_var.set(filename)

    def browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.settings["output_dir"]
        )

        if directory:
            self.output_dir_var.set(directory)
            self.settings["output_dir"] = directory
            self.save_settings()

    def update_convert_button_state(self, *args):
        """Update convert button state based on input file"""
        if self.input_file_var.get():
            self.convert_button.config(state=tk.NORMAL)
        else:
            self.convert_button.config(state=tk.DISABLED)

    def start_conversion(self):
        """Start conversion process"""
        input_file = self.input_file_var.get()
        output_dir = self.output_dir_var.get()

        if not input_file or not os.path.exists(input_file):
            messagebox.showerror("Conversion Error", "Please select a valid input file")
            return

        if not output_dir:
            messagebox.showerror("Conversion Error", "Please select an output directory")
            return

        # Disable convert button and show progress
        self.convert_button.config(state=tk.DISABLED)
        self.conversion_progress.start()

        # Start conversion in background thread
        conversion_thread = threading.Thread(target=self._conversion_worker, args=(input_file, output_dir))
        conversion_thread.daemon = True
        conversion_thread.start()

    def _conversion_worker(self, input_file, output_dir):
        """Background worker for conversion"""
        try:
            # Create conversion config
            config = ConversionConfig(
                output_dir=output_dir,
                convert_meshes=self.convert_meshes_var.get(),
                mesh_output_format=self.mesh_format_var.get(),
                mesh_output_dir=os.path.join(output_dir, 'meshes'),
                exclude_rotation_translation_scale=False,
                verbose=True
            )

            # Create logger
            import logging
            logger = logging.getLogger(__name__)

            # Perform conversion
            result = convert_single_file(input_file, config, logger)

            # Update GUI in main thread
            self.root.after(0, self._conversion_complete, result, input_file)

        except Exception as e:
            self.root.after(0, self._conversion_error, str(e))

    def _conversion_complete(self, result, input_file):
        """Handle conversion completion"""
        self.convert_button.config(state=tk.NORMAL)
        self.conversion_progress.stop()

        filename = os.path.basename(input_file)
        self.log_message(f"Conversion completed: {filename}")

        messagebox.showinfo("Conversion Complete",
                           f"Successfully converted {filename} to JBeam format.\n"
                           f"Output saved to: {self.output_dir_var.get()}")

    def _conversion_error(self, error_msg):
        """Handle conversion error"""
        self.convert_button.config(state=tk.NORMAL)
        self.conversion_progress.stop()

        self.log_message(f"Conversion error: {error_msg}", "ERROR")
        messagebox.showerror("Conversion Error", f"Conversion failed:\n{error_msg}")

    # File management
    def open_ror_file(self):
        """Open RoR file for conversion"""
        self.browse_input_file()

    def open_download_folder(self):
        """Open download folder in file explorer"""
        download_dir = self.settings["download_dir"]
        if os.path.exists(download_dir):
            if os.name == 'nt':  # Windows
                os.startfile(download_dir)
            elif os.name == 'posix':  # macOS and Linux
                os.system(f'open "{download_dir}"' if sys.platform == 'darwin' else f'xdg-open "{download_dir}"')
        else:
            messagebox.showwarning("Folder Not Found", f"Download folder does not exist:\n{download_dir}")

    def open_output_folder(self):
        """Open output folder in file explorer"""
        output_dir = self.output_dir_var.get()
        if os.path.exists(output_dir):
            if os.name == 'nt':  # Windows
                os.startfile(output_dir)
            elif os.name == 'posix':  # macOS and Linux
                os.system(f'open "{output_dir}"' if sys.platform == 'darwin' else f'xdg-open "{output_dir}"')
        else:
            messagebox.showwarning("Folder Not Found", f"Output folder does not exist:\n{output_dir}")

    def convert_local_files(self):
        """Convert local RoR files"""
        filetypes = [
            ("RoR Files", "*.truck *.trailer *.car *.boat *.airplane *.load *.train"),
            ("All Files", "*.*")
        ]

        filenames = filedialog.askopenfilenames(
            title="Select RoR Files to Convert",
            filetypes=filetypes,
            initialdir=self.settings["download_dir"]
        )

        if filenames:
            # Process multiple files
            for filename in filenames:
                self.input_file_var.set(filename)
                self.start_conversion()

    # Utility methods
    def _is_downloaded(self, resource):
        """Check if resource is already downloaded"""
        # This would check the download history
        return False  # Placeholder

    def view_resource_details(self):
        """View detailed information about selected resource"""
        selection = self.results_tree.selection()
        if not selection:
            return

        values = self.results_tree.item(selection[0], "values")
        resource_id = int(values[0])

        # Find the resource object
        resource = None
        for r in self.search_results:
            if r.id == resource_id:
                resource = r
                break

        if resource:
            self._show_resource_details_dialog(resource)

    def _show_resource_details_dialog(self, resource):
        """Show resource details in a dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Resource Details - {resource.title}")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Create details display
        details_text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, padx=10, pady=10)
        details_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Format resource details
        details = f"""Title: {resource.title}
Author: {resource.author}
Category: {resource.category}
ID: {resource.id}
Description: {resource.description}
Download Count: {resource.download_count}
Rating: {resource.rating}
Version: {resource.version}
File Size: {resource.file_size}
"""

        details_text.insert(tk.END, details)
        details_text.config(state=tk.DISABLED)

        # Close button
        close_button = ttk.Button(dialog, text="Close", command=dialog.destroy)
        close_button.pack(pady=10)

    # Settings and configuration
    def show_settings(self):
        """Show settings dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Create settings notebook
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # General settings tab
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")

        # Download directory
        ttk.Label(general_frame, text="Download Directory:").pack(anchor=tk.W, pady=(10, 0))

        download_dir_frame = ttk.Frame(general_frame)
        download_dir_frame.pack(fill=tk.X, pady=(5, 10))

        download_dir_var = tk.StringVar(value=self.settings["download_dir"])
        download_dir_entry = ttk.Entry(download_dir_frame, textvariable=download_dir_var, state="readonly")
        download_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def browse_download_dir():
            directory = filedialog.askdirectory(title="Select Download Directory",
                                              initialdir=self.settings["download_dir"])
            if directory:
                download_dir_var.set(directory)

        ttk.Button(download_dir_frame, text="Browse...", command=browse_download_dir).pack(side=tk.RIGHT, padx=(5, 0))

        # Max concurrent downloads
        ttk.Label(general_frame, text="Max Concurrent Downloads:").pack(anchor=tk.W, pady=(0, 5))

        max_downloads_var = tk.StringVar(value=str(self.settings["max_concurrent_downloads"]))
        max_downloads_spin = ttk.Spinbox(general_frame, from_=1, to=10, textvariable=max_downloads_var, width=10)
        max_downloads_spin.pack(anchor=tk.W)

        # Auto extract
        auto_extract_var = tk.BooleanVar(value=self.settings["auto_extract"])
        ttk.Checkbutton(general_frame, text="Auto-extract downloaded files", variable=auto_extract_var).pack(anchor=tk.W, pady=(10, 0))

        # Conversion settings tab
        conversion_frame = ttk.Frame(notebook)
        notebook.add(conversion_frame, text="Conversion")

        # Default mesh format
        ttk.Label(conversion_frame, text="Default Mesh Output Format:").pack(anchor=tk.W, pady=(10, 5))

        mesh_format_var = tk.StringVar(value=self.settings["mesh_output_format"])
        mesh_format_combo = ttk.Combobox(conversion_frame, textvariable=mesh_format_var,
                                        values=["dae", "blend"], state="readonly", width=15)
        mesh_format_combo.pack(anchor=tk.W)

        # Convert meshes by default
        convert_meshes_var = tk.BooleanVar(value=self.settings["convert_meshes"])
        ttk.Checkbutton(conversion_frame, text="Convert meshes by default", variable=convert_meshes_var).pack(anchor=tk.W, pady=(10, 0))

        # Dialog buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        def save_settings():
            self.settings["download_dir"] = download_dir_var.get()
            self.settings["max_concurrent_downloads"] = int(max_downloads_var.get())
            self.settings["auto_extract"] = auto_extract_var.get()
            self.settings["mesh_output_format"] = mesh_format_var.get()
            self.settings["convert_meshes"] = convert_meshes_var.get()

            self.save_settings()

            # Update GUI
            self.mesh_format_var.set(mesh_format_var.get())
            self.convert_meshes_var.set(convert_meshes_var.get())

            dialog.destroy()
            messagebox.showinfo("Settings", "Settings saved successfully")

        ttk.Button(button_frame, text="Save", command=save_settings).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=(0, 5))

    def refresh_sitemap_stats(self):
        """Refresh sitemap statistics"""
        if not self.downloader:
            return

        def worker():
            try:
                stats = self.downloader.get_sitemap_stats()
                self.root.after(0, lambda: self._show_sitemap_stats(stats))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Sitemap Error", f"Failed to get sitemap stats:\n{e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _show_sitemap_stats(self, stats):
        """Show sitemap statistics dialog"""
        if stats['sitemap_accessible']:
            message = f"Sitemap accessible\nTotal resources: {stats['total_resources']:,}"
        else:
            message = f"Sitemap not accessible\nError: {stats.get('error', 'Unknown error')}"

        messagebox.showinfo("Sitemap Statistics", message)

    def clear_download_history(self):
        """Clear download history"""
        if messagebox.askyesno("Clear History", "Are you sure you want to clear the download history?"):
            # Implementation would clear the download history
            self.log_message("Download history cleared")

    # Logging functionality
    def log_message(self, message, level="INFO"):
        """Add message to log"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"

        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)

        # Update status bar
        self.status_var.set(message)

    def clear_log(self):
        """Clear log messages"""
        self.log_text.delete(1.0, tk.END)

    def toggle_log_panel(self):
        """Toggle log panel visibility"""
        if self.log_visible:
            self.log_frame.pack_forget()
            self.toggle_log_button.config(text="Show Log")
            self.log_visible = False
        else:
            self.log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, before=self.toggle_log_button)
            self.toggle_log_button.config(text="Hide Log")
            self.log_visible = True

    def update_status(self):
        """Update application status"""
        # This would update various status indicators
        self.root.after(1000, self.update_status)

    # Dialog methods
    def show_about(self):
        """Show about dialog"""
        about_text = """RoR Downloader & truck2jbeam Converter

A comprehensive tool for discovering, downloading, and converting
Rigs of Rods resources to BeamNG.drive JBeam format.

Features:
• Efficient sitemap-based resource discovery
• Download management with progress tracking
• Automatic mesh conversion to DAE/Blend formats
• Comprehensive JBeam output with flexbodies and props

Version: 1.0
GitHub: https://github.com/hltdev8642/truck2jbeam
"""
        messagebox.showinfo("About", about_text)

    def run(self):
        """Run the GUI application"""
        try:
            self.root.mainloop()
        finally:
            self.save_settings()


class GUILogHandler(logging.Handler):
    """Custom log handler for GUI display"""

    def __init__(self, log_func):
        super().__init__()
        self.log_func = log_func

    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname
            self.log_func(msg, level)
        except Exception:
            pass


def main():
    """Main entry point"""
    try:
        app = RoRGUI()
        app.run()
    except Exception as e:
        print(f"Error starting GUI: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
