#!/usr/bin/env python3
"""
Rigs of Rods Repository Downloader

This module provides functionality to browse, search, and download vehicle files
from the official Rigs of Rods repository at https://forum.rigsofrods.org/resources/
"""

import requests
import re
import os
import json
import time
import zipfile
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import threading
from queue import Queue


@dataclass
class RoRResource:
    """Represents a Rigs of Rods resource"""
    id: int
    title: str
    author: str
    category: str
    description: str
    download_url: str
    preview_url: Optional[str]
    rating: float
    downloads: int
    last_update: str
    version: str
    file_size: Optional[str]
    tags: List[str]
    
    def __str__(self):
        return f"{self.title} by {self.author} ({self.category})"


@dataclass
class DownloadProgress:
    """Track download progress"""
    resource_id: int
    filename: str
    total_size: int
    downloaded: int
    speed: float
    eta: float
    status: str  # 'downloading', 'completed', 'failed', 'paused'


class RoRDownloader:
    """Main downloader class for Rigs of Rods resources"""
    
    BASE_URL = "https://forum.rigsofrods.org"
    RESOURCES_URL = f"{BASE_URL}/resources/"
    
    def __init__(self, download_dir: str = "./downloads", max_workers: int = 3):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'truck2jbeam-downloader/1.0 (https://github.com/Dummiesman/truck2jbeam)'
        })
        self.logger = logging.getLogger(__name__)
        
        # Download management
        self.download_queue = Queue()
        self.active_downloads: Dict[int, DownloadProgress] = {}
        self.download_history: List[Dict] = []
        
        # Load download history
        self._load_history()
    
    def _load_history(self):
        """Load download history from file"""
        history_file = self.download_dir / "download_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    self.download_history = json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load download history: {e}")
    
    def _save_history(self):
        """Save download history to file"""
        history_file = self.download_dir / "download_history.json"
        try:
            with open(history_file, 'w') as f:
                json.dump(self.download_history, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Could not save download history: {e}")
    
    def search_resources(self, query: str = "", category: str = "", 
                        page: int = 1, per_page: int = 20) -> Tuple[List[RoRResource], int]:
        """
        Search for resources in the RoR repository
        
        Args:
            query: Search query string
            category: Filter by category (vehicles, terrains, etc.)
            page: Page number (1-based)
            per_page: Results per page
            
        Returns:
            Tuple of (resources list, total pages)
        """
        self.logger.info(f"Searching resources: query='{query}', category='{category}', page={page}")
        
        params = {
            'page': page,
            'order': 'download_count',
            'direction': 'desc'
        }
        
        if query:
            params['keywords'] = query
        
        if category:
            params['category_id'] = self._get_category_id(category)
        
        try:
            response = self.session.get(self.RESOURCES_URL, params=params, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            resources = self._parse_resource_list(soup)
            total_pages = self._get_total_pages(soup)
            
            self.logger.info(f"Found {len(resources)} resources on page {page} of {total_pages}")
            return resources, total_pages
            
        except requests.RequestException as e:
            self.logger.error(f"Error searching resources: {e}")
            return [], 0
    
    def get_resource_details(self, resource_id: int) -> Optional[RoRResource]:
        """Get detailed information about a specific resource"""
        url = f"{self.RESOURCES_URL}{resource_id}/"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return self._parse_resource_details(soup, resource_id)
            
        except requests.RequestException as e:
            self.logger.error(f"Error getting resource details for {resource_id}: {e}")
            return None
    
    def download_resource(self, resource: RoRResource, extract: bool = True) -> bool:
        """
        Download a resource
        
        Args:
            resource: RoRResource to download
            extract: Whether to extract zip files automatically
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Starting download: {resource.title}")
        
        # Create progress tracker
        progress = DownloadProgress(
            resource_id=resource.id,
            filename=f"{resource.title}.zip",
            total_size=0,
            downloaded=0,
            speed=0.0,
            eta=0.0,
            status='downloading'
        )
        
        self.active_downloads[resource.id] = progress
        
        try:
            # Get download URL
            download_url = self._get_download_url(resource)
            if not download_url:
                progress.status = 'failed'
                return False
            
            # Download file
            response = self.session.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get file size
            total_size = int(response.headers.get('content-length', 0))
            progress.total_size = total_size
            
            # Determine filename
            filename = self._get_filename_from_response(response, resource)
            filepath = self.download_dir / filename
            progress.filename = filename
            
            # Download with progress tracking
            start_time = time.time()
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress.downloaded = downloaded
                        
                        # Calculate speed and ETA
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            progress.speed = downloaded / elapsed
                            if progress.speed > 0:
                                progress.eta = (total_size - downloaded) / progress.speed
            
            progress.status = 'completed'
            
            # Extract if requested and it's a zip file
            if extract and filepath.suffix.lower() == '.zip':
                self._extract_zip(filepath, resource)
            
            # Add to history
            self._add_to_history(resource, str(filepath))
            
            self.logger.info(f"Download completed: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Download failed for {resource.title}: {e}")
            progress.status = 'failed'
            return False
        
        finally:
            # Clean up active downloads
            if resource.id in self.active_downloads:
                del self.active_downloads[resource.id]
    
    def get_popular_resources(self, limit: int = 50) -> List[RoRResource]:
        """Get most popular resources"""
        resources, _ = self.search_resources(per_page=limit)
        return resources
    
    def get_recent_resources(self, limit: int = 20) -> List[RoRResource]:
        """Get recently updated resources"""
        params = {
            'order': 'last_update',
            'direction': 'desc',
            'page': 1
        }
        
        try:
            response = self.session.get(self.RESOURCES_URL, params=params, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            resources = self._parse_resource_list(soup)
            return resources[:limit]
            
        except requests.RequestException as e:
            self.logger.error(f"Error getting recent resources: {e}")
            return []
    
    def get_download_progress(self, resource_id: int) -> Optional[DownloadProgress]:
        """Get download progress for a resource"""
        return self.active_downloads.get(resource_id)
    
    def get_download_history(self) -> List[Dict]:
        """Get download history"""
        return self.download_history.copy()
    
    def _parse_resource_list(self, soup: BeautifulSoup) -> List[RoRResource]:
        """Parse resource list from HTML"""
        resources = []
        
        # Find resource items (this will need to be adjusted based on actual HTML structure)
        resource_items = soup.find_all('div', class_='structItem')
        
        for item in resource_items:
            try:
                resource = self._parse_resource_item(item)
                if resource:
                    resources.append(resource)
            except Exception as e:
                self.logger.warning(f"Error parsing resource item: {e}")
                continue
        
        return resources
    
    def _parse_resource_item(self, item) -> Optional[RoRResource]:
        """Parse individual resource item"""
        # This is a simplified parser - actual implementation would need
        # to be adjusted based on the real HTML structure
        try:
            title_elem = item.find('a', class_='structItem-title')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            resource_url = title_elem.get('href', '')
            
            # Extract resource ID from URL
            resource_id = self._extract_resource_id(resource_url)
            if not resource_id:
                return None
            
            # Extract other information
            author_elem = item.find('a', class_='username')
            author = author_elem.get_text(strip=True) if author_elem else "Unknown"
            
            # Create basic resource object
            return RoRResource(
                id=resource_id,
                title=title,
                author=author,
                category="Unknown",
                description="",
                download_url=f"{self.BASE_URL}{resource_url}download/",
                preview_url=None,
                rating=0.0,
                downloads=0,
                last_update="",
                version="",
                file_size=None,
                tags=[]
            )
            
        except Exception as e:
            self.logger.warning(f"Error parsing resource item: {e}")
            return None
    
    def _extract_resource_id(self, url: str) -> Optional[int]:
        """Extract resource ID from URL"""
        match = re.search(r'/resources/(\d+)/', url)
        return int(match.group(1)) if match else None
    
    def _get_category_id(self, category: str) -> str:
        """Get category ID for filtering"""
        # This would need to be implemented based on actual category IDs
        category_map = {
            'vehicles': '1',
            'terrains': '2',
            'aircraft': '3',
            'boats': '4'
        }
        return category_map.get(category.lower(), '')
    
    def _get_total_pages(self, soup: BeautifulSoup) -> int:
        """Extract total pages from pagination"""
        # Simplified implementation
        pagination = soup.find('nav', class_='pageNav')
        if pagination:
            page_links = pagination.find_all('a')
            if page_links:
                try:
                    return int(page_links[-2].get_text(strip=True))
                except (ValueError, IndexError):
                    pass
        return 1
    
    def _parse_resource_details(self, soup: BeautifulSoup, resource_id: int) -> Optional[RoRResource]:
        """Parse detailed resource information"""
        # This would need detailed implementation based on actual page structure
        # For now, return a basic resource
        title_elem = soup.find('h1', class_='p-title-value')
        title = title_elem.get_text(strip=True) if title_elem else f"Resource {resource_id}"
        
        return RoRResource(
            id=resource_id,
            title=title,
            author="Unknown",
            category="Unknown",
            description="",
            download_url=f"{self.RESOURCES_URL}{resource_id}/download/",
            preview_url=None,
            rating=0.0,
            downloads=0,
            last_update="",
            version="",
            file_size=None,
            tags=[]
        )
    
    def _get_download_url(self, resource: RoRResource) -> Optional[str]:
        """Get actual download URL for resource"""
        return resource.download_url
    
    def _get_filename_from_response(self, response: requests.Response, resource: RoRResource) -> str:
        """Extract filename from response headers or generate one"""
        content_disposition = response.headers.get('content-disposition', '')
        if content_disposition:
            filename_match = re.search(r'filename="([^"]+)"', content_disposition)
            if filename_match:
                return filename_match.group(1)
        
        # Generate filename
        safe_title = re.sub(r'[^\w\-_\.]', '_', resource.title)
        return f"{safe_title}_{resource.id}.zip"
    
    def _extract_zip(self, zip_path: Path, resource: RoRResource):
        """Extract zip file to organized directory"""
        extract_dir = self.download_dir / f"{resource.title}_{resource.id}"
        extract_dir.mkdir(exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            self.logger.info(f"Extracted {zip_path.name} to {extract_dir}")
        except Exception as e:
            self.logger.error(f"Error extracting {zip_path.name}: {e}")
    
    def _add_to_history(self, resource: RoRResource, filepath: str):
        """Add download to history"""
        history_entry = {
            'timestamp': time.time(),
            'resource': asdict(resource),
            'filepath': filepath,
            'success': True
        }
        self.download_history.append(history_entry)
        self._save_history()
