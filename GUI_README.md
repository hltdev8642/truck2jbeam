# RoR Downloader & truck2jbeam Converter GUI

A comprehensive graphical user interface for discovering, downloading, and converting Rigs of Rods resources to BeamNG.drive JBeam format.

## Features

### 🔍 **Search Interface**
- **Efficient Sitemap-Based Search**: Searches through all 935+ RoR resources using sitemap URL filtering
- **Real-Time Results**: Fast search results in ~0.5 seconds
- **Category Filtering**: Filter by vehicle type (Cars, Trucks, Buses, etc.)
- **Configurable Limits**: Set result limits from 5-100 resources

### 📊 **Resource Browser**
- **Table View**: Display resources with ID, title, author, category, and download status
- **Multi-Selection**: Select multiple resources for batch downloading
- **Detailed Information**: View comprehensive resource details in popup dialogs
- **Status Tracking**: See which resources are already downloaded

### ⬇️ **Download Management**
- **Download Queue**: Visual queue showing download progress and status
- **Progress Tracking**: Real-time progress indicators for each download
- **Pause/Resume**: Control downloads with pause and resume functionality
- **Concurrent Downloads**: Configurable number of simultaneous downloads
- **Auto-Extraction**: Automatic extraction of downloaded ZIP files

### 🔄 **Conversion Pipeline**
- **Integrated truck2jbeam**: Built-in conversion from RoR to BeamNG JBeam format
- **Mesh Conversion**: Convert .mesh files to .dae or .blend formats
- **Configurable Settings**: Choose output formats and conversion parameters
- **Progress Monitoring**: Visual progress indicators during conversion
- **Error Handling**: Comprehensive error reporting and recovery

### 📁 **File Management**
- **File Browser**: Easy selection of input RoR files
- **Directory Management**: Configure download and output directories
- **Quick Access**: Buttons to open folders in file explorer
- **Batch Processing**: Convert multiple files at once

### ⚙️ **Settings Panel**
- **Download Configuration**: Set download directory and concurrent limits
- **Conversion Settings**: Configure mesh output formats and conversion options
- **User Preferences**: Customize application behavior
- **Persistent Settings**: Settings saved between application sessions

### 📝 **Status & Logging**
- **Status Bar**: Real-time status updates
- **Logging Panel**: Comprehensive log of all operations
- **Error Reporting**: Clear error messages and troubleshooting information
- **Collapsible Interface**: Hide/show log panel as needed

## Installation

### Prerequisites
- Python 3.7 or higher
- tkinter (usually included with Python)

### Required Dependencies
```bash
pip install requests beautifulsoup4
```

### Optional Dependencies (for mesh conversion)
```bash
# For enhanced mesh processing
pip install numpy
```

## Usage

### Starting the GUI
```bash
python ror_gui.py
```

Or use the demo launcher:
```bash
python demo_gui.py
```

### Basic Workflow

1. **Search for Resources**
   - Enter search terms in the search box
   - Select category filter if desired
   - Click "Search" or press Enter
   - Browse results in the table

2. **Download Resources**
   - Select desired resources from search results
   - Click "Download Selected"
   - Monitor progress in the download queue
   - Use pause/resume controls as needed

3. **Convert to JBeam**
   - Select input RoR file using "Browse..." button
   - Choose output directory
   - Configure conversion options (mesh format, etc.)
   - Click "Convert to JBeam"
   - Monitor conversion progress

### Keyboard Shortcuts
- **Ctrl+O**: Open RoR file for conversion
- **Ctrl+F**: Focus search box
- **F5**: Perform search
- **Ctrl+Q**: Quit application

## Configuration

### Settings Dialog
Access via **File → Settings** to configure:

- **Download Directory**: Where downloaded files are saved
- **Max Concurrent Downloads**: Number of simultaneous downloads (1-10)
- **Auto-Extract**: Automatically extract downloaded ZIP files
- **Default Mesh Format**: DAE or Blend format for mesh conversion
- **Convert Meshes by Default**: Enable mesh conversion by default

### File Locations
- **Settings**: `ror_gui_settings.json` (in application directory)
- **Downloads**: Configurable via settings (default: `./downloads`)
- **Output**: Configurable via conversion panel (default: `./output`)

## Technical Details

### Architecture
- **Frontend**: tkinter with ttk styling
- **Backend**: Integration with existing `ror_downloader.py` and `truck2jbeam.py`
- **Threading**: Background operations for search, download, and conversion
- **Error Handling**: Comprehensive exception handling with user feedback

### Performance
- **Search Speed**: ~0.5 seconds for sitemap-based searches
- **Memory Usage**: Efficient resource management with minimal memory footprint
- **Responsiveness**: Non-blocking UI with background processing

### Compatibility
- **Operating Systems**: Windows, macOS, Linux
- **Python Versions**: 3.7+
- **Screen Sizes**: Responsive layout with minimum 800x600 resolution

## Troubleshooting

### Common Issues

**GUI won't start**
- Check Python version: `python --version`
- Install dependencies: `pip install requests beautifulsoup4`
- Check tkinter availability: `python -c "import tkinter"`

**Search not working**
- Check internet connection
- Verify sitemap accessibility via **Tools → Refresh Sitemap Stats**
- Check firewall/proxy settings

**Downloads failing**
- Check download directory permissions
- Verify available disk space
- Check internet connection stability

**Conversion errors**
- Ensure input file is a valid RoR format
- Check output directory permissions
- Verify mesh conversion dependencies

### Getting Help
- Check the log panel for detailed error messages
- Use **Help → About** for version information
- Visit the GitHub repository for issues and updates

## Development

### Project Structure
```
ror_gui.py              # Main GUI application
ror_downloader.py       # Resource discovery and download
truck2jbeam.py         # RoR to JBeam conversion
demo_gui.py            # GUI demonstration script
ror_gui_settings.json  # User settings (created on first run)
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is part of the truck2jbeam converter system. See the main repository for license information.

## Acknowledgments

- **Rigs of Rods Community**: For the amazing vehicle resources
- **BeamNG.drive**: For the excellent physics simulation platform
- **Python Community**: For the excellent GUI and web scraping libraries
