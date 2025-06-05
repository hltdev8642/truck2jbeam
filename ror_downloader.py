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
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Set
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
    SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

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

        This method uses an efficient sitemap-based approach:
        1. Searches sitemap.xml URLs for query matches
        2. Fetches resource details only for matching URLs
        3. Provides comprehensive coverage without building large indexes
        4. Falls back to client-side filtering if sitemap parsing fails

        Args:
            query: Search query string
            category: Filter by category (optional)
            page: Page number (1-based)
            per_page: Results per page

        Returns:
            Tuple of (resources list, total pages)
        """
        if query:
            # For search queries, use sitemap-based comprehensive search
            return self._search_with_sitemap_index(query, category, page, per_page)
        else:
            # For browsing, use normal pagination
            return self._browse_resources(page, per_page)
    
    def _browse_resources(self, page: int = 1, per_page: int = 20) -> Tuple[List[RoRResource], int]:
        """Browse resources without search (normal pagination)"""
        params = {
            'page': page,
            'order': 'download_count',
            'direction': 'desc'
        }

        try:
            response = self.session.get(self.RESOURCES_URL, params=params, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            resources = self._parse_resource_list(soup)
            total_pages = self._get_total_pages(soup)

            self.logger.info(f"Found {len(resources)} resources on page {page} of {total_pages}")
            return resources, total_pages

        except requests.RequestException as e:
            self.logger.error(f"Error browsing resources: {e}")
            return [], 0

    def _search_with_client_side_filtering(self, query: str, page: int = 1, per_page: int = 20) -> Tuple[List[RoRResource], int]:
        """Search by fetching multiple pages and filtering client-side"""
        self.logger.info(f"Searching for '{query}' using client-side filtering...")

        all_resources = []
        max_pages_to_fetch = 10  # Limit to avoid excessive requests

        # Fetch multiple pages to build a larger dataset for filtering
        for fetch_page in range(1, max_pages_to_fetch + 1):
            try:
                page_resources, total_pages = self._browse_resources(fetch_page, 20)

                if not page_resources:
                    break

                all_resources.extend(page_resources)

                # Stop if we've reached the end
                if fetch_page >= total_pages:
                    break

            except Exception as e:
                self.logger.warning(f"Error fetching page {fetch_page}: {e}")
                break

        # Filter resources based on query
        query_lower = query.lower()
        matching_resources = []

        for resource in all_resources:
            # Check if query matches title, description, or author
            if (query_lower in resource.title.lower() or
                query_lower in resource.description.lower() or
                query_lower in resource.author.lower() or
                query_lower in resource.category.lower()):
                matching_resources.append(resource)

        # Sort by relevance (exact title matches first, then partial matches)
        def relevance_score(resource):
            title_lower = resource.title.lower()
            if query_lower == title_lower:
                return 3  # Exact match
            elif title_lower.startswith(query_lower):
                return 2  # Starts with query
            elif query_lower in title_lower:
                return 1  # Contains query
            else:
                return 0  # Match in description/author/category

        matching_resources.sort(key=relevance_score, reverse=True)

        # Implement pagination on filtered results
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_resources = matching_resources[start_idx:end_idx]

        # Calculate total pages for filtered results
        total_filtered = len(matching_resources)
        total_pages = (total_filtered + per_page - 1) // per_page if total_filtered > 0 else 1

        self.logger.info(f"Found {total_filtered} resources matching '{query}' (showing page {page}/{total_pages})")

        return page_resources, total_pages

    def _search_with_sitemap_index(self, query: str, category: str = "",
                                  page: int = 1, per_page: int = 20) -> Tuple[List[RoRResource], int]:
        """Search by filtering sitemap URLs and fetching only matching resources"""
        self.logger.info(f"Searching for '{query}' using sitemap URL filtering...")

        # Get matching resource IDs from sitemap URLs
        matching_resource_ids = self._search_sitemap_urls(query)

        if not matching_resource_ids:
            self.logger.warning("No matching URLs found in sitemap, falling back to client-side filtering")
            return self._search_with_client_side_filtering(query, page, per_page)

        self.logger.info(f"Found {len(matching_resource_ids)} resources with URLs matching '{query}'")

        # Fetch details only for matching resources
        matching_resources = []
        for resource_id in matching_resource_ids:
            try:
                resource = self.get_resource_details(resource_id)
                if resource:
                    # Additional filtering on resource details if needed
                    query_lower = query.lower()
                    category_lower = category.lower() if category else ""

                    # Check category filter
                    if category_lower and category_lower not in resource.category.lower():
                        continue

                    # Verify the resource actually matches the query (not just URL)
                    if (query_lower in resource.title.lower() or
                        query_lower in resource.description.lower() or
                        query_lower in resource.author.lower() or
                        query_lower in resource.category.lower()):
                        matching_resources.append(resource)

            except Exception as e:
                self.logger.warning(f"Error fetching details for resource {resource_id}: {e}")
                continue

        # Sort by relevance
        def relevance_score(resource):
            title_lower = resource.title.lower()
            query_lower = query.lower()
            if query_lower == title_lower:
                return 4  # Exact match
            elif title_lower.startswith(query_lower):
                return 3  # Starts with query
            elif query_lower in title_lower:
                return 2  # Contains query in title
            elif query_lower in resource.author.lower():
                return 1  # Match in author
            else:
                return 0  # Match in description/category

        matching_resources.sort(key=relevance_score, reverse=True)

        # Implement pagination on filtered results
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_resources = matching_resources[start_idx:end_idx]

        # Calculate total pages for filtered results
        total_filtered = len(matching_resources)
        total_pages = (total_filtered + per_page - 1) // per_page if total_filtered > 0 else 1

        self.logger.info(f"Found {total_filtered} matching resources (showing page {page}/{total_pages})")

        return page_resources, total_pages

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

    def get_sitemap_stats(self) -> Dict[str, Any]:
        """Get statistics about the sitemap"""
        try:
            resource_ids = self._fetch_resource_ids_from_sitemap()
            return {
                'total_resources': len(resource_ids),
                'sitemap_accessible': True,
                'sample_ids': sorted(list(resource_ids))[:10] if resource_ids else []
            }
        except Exception as e:
            return {
                'total_resources': 0,
                'sitemap_accessible': False,
                'error': str(e),
                'sample_ids': []
            }



    def _search_sitemap_urls(self, query: str) -> List[int]:
        """Search sitemap URLs for query and return matching resource IDs"""
        try:
            self.logger.info(f"Searching sitemap URLs for '{query}'")
            response = self.session.get(self.SITEMAP_URL, timeout=30)
            response.raise_for_status()

            # Parse XML
            root = ET.fromstring(response.content)

            # Find URLs that match the query
            matching_resource_ids = []
            query_lower = query.lower()

            # Handle different sitemap formats
            namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            # Look for URL elements with namespaces
            for url_elem in root.findall('.//ns:url', namespaces):
                loc_elem = url_elem.find('ns:loc', namespaces)
                if loc_elem is not None:
                    url = loc_elem.text
                    if url and '/resources/' in url:
                        # Check if query appears in the URL
                        if query_lower in url.lower():
                            resource_id = self._extract_resource_id(url)
                            if resource_id:
                                matching_resource_ids.append(resource_id)

            # If no namespaced elements found, try without namespace
            if not matching_resource_ids:
                for url_elem in root.findall('.//url'):
                    loc_elem = url_elem.find('loc')
                    if loc_elem is not None:
                        url = loc_elem.text
                        if url and '/resources/' in url:
                            # Check if query appears in the URL
                            if query_lower in url.lower():
                                resource_id = self._extract_resource_id(url)
                                if resource_id:
                                    matching_resource_ids.append(resource_id)

            self.logger.info(f"Found {len(matching_resource_ids)} URLs matching '{query}' in sitemap")
            return matching_resource_ids

        except Exception as e:
            self.logger.error(f"Error searching sitemap URLs: {e}")
            return []

    def _fetch_resource_ids_from_sitemap(self) -> Set[int]:
        """Fetch and parse sitemap.xml to extract all resource IDs"""
        try:
            self.logger.info(f"Fetching sitemap from {self.SITEMAP_URL}")
            response = self.session.get(self.SITEMAP_URL, timeout=30)
            response.raise_for_status()

            # Parse XML
            root = ET.fromstring(response.content)

            # Find all URLs in the sitemap
            resource_ids = set()

            # Handle different sitemap formats
            namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            # Look for URL elements
            for url_elem in root.findall('.//ns:url', namespaces):
                loc_elem = url_elem.find('ns:loc', namespaces)
                if loc_elem is not None:
                    url = loc_elem.text
                    if url and '/resources/' in url:
                        resource_id = self._extract_resource_id(url)
                        if resource_id:
                            resource_ids.add(resource_id)

            # If no namespaced elements found, try without namespace
            if not resource_ids:
                for url_elem in root.findall('.//url'):
                    loc_elem = url_elem.find('loc')
                    if loc_elem is not None:
                        url = loc_elem.text
                        if url and '/resources/' in url:
                            resource_id = self._extract_resource_id(url)
                            if resource_id:
                                resource_ids.add(resource_id)

            self.logger.info(f"Extracted {len(resource_ids)} unique resource IDs from sitemap")
            return resource_ids

        except Exception as e:
            self.logger.error(f"Error fetching resource IDs from sitemap: {e}")
            return set()

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
        """Parse individual resource item from XenForo structure"""
        try:
            # Find the title link within structItem-title div
            title_div = item.find('div', class_='structItem-title')
            if not title_div:
                return None

            title_link = title_div.find('a')
            if not title_link:
                return None

            title = title_link.get_text(strip=True)
            resource_url = title_link.get('href', '')

            # Extract version from span.u-muted if present
            version_span = title_div.find('span', class_='u-muted')
            version = version_span.get_text(strip=True) if version_span else ""

            # Extract resource ID from URL
            resource_id = self._extract_resource_id(resource_url)
            if not resource_id:
                return None

            # Extract author information
            author_elem = item.find('a', class_='username')
            author = author_elem.get_text(strip=True) if author_elem else "Unknown"

            # Extract category from structItem-parts
            category = "Unknown"
            parts_list = item.find('ul', class_='structItem-parts')
            if parts_list:
                category_links = parts_list.find_all('a')
                for link in category_links:
                    href = link.get('href', '')
                    if '/resources/categories/' in href:
                        category = link.get_text(strip=True)
                        break

            # Extract description from resourceTagLine
            description = ""
            tagline_div = item.find('div', class_='structItem-resourceTagLine')
            if tagline_div:
                description = tagline_div.get_text(strip=True)

            # Extract download count
            downloads = 0
            downloads_dd = item.find('dl', class_='structItem-metaItem--downloads')
            if downloads_dd:
                dd_elem = downloads_dd.find('dd')
                if dd_elem:
                    try:
                        downloads = int(dd_elem.get_text(strip=True).replace(',', ''))
                    except ValueError:
                        pass

            # Extract rating
            rating = 0.0
            rating_span = item.find('span', class_='ratingStars')
            if rating_span:
                title_attr = rating_span.get('title', '')
                if title_attr:
                    # Extract rating from title like "4.50 star(s)"
                    import re
                    rating_match = re.search(r'(\d+\.?\d*)', title_attr)
                    if rating_match:
                        try:
                            rating = float(rating_match.group(1))
                        except ValueError:
                            pass

            # Extract last update time
            last_update = ""
            update_dd = item.find('dl', class_='structItem-metaItem--lastUpdate')
            if update_dd:
                time_elem = update_dd.find('time')
                if time_elem:
                    last_update = time_elem.get('datetime', '')

            # Create resource object
            return RoRResource(
                id=resource_id,
                title=title,
                author=author,
                category=category,
                description=description,
                download_url=f"{self.BASE_URL}{resource_url}download/",
                preview_url=None,
                rating=rating,
                downloads=downloads,
                last_update=last_update,
                version=version,
                file_size=None,
                tags=[]
            )

        except Exception as e:
            self.logger.warning(f"Error parsing resource item: {e}")
            return None
    
    def _extract_resource_id(self, url: str) -> Optional[int]:
        """Extract resource ID from URL"""
        # Handle URLs like /resources/pluto-sc500.1273/ or /resources/1273/
        match = re.search(r'/resources/[^/]*\.(\d+)/', url)
        if match:
            return int(match.group(1))

        # Fallback for direct ID URLs
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
        """Parse detailed resource information from resource page"""
        try:
            # Extract title from page header
            title_elem = soup.find('h1', class_='p-title-value')
            title = title_elem.get_text(strip=True) if title_elem else f"Resource {resource_id}"

            # Extract author
            author = "Unknown"
            author_elem = soup.find('a', class_='username')
            if author_elem:
                author = author_elem.get_text(strip=True)

            # Extract version
            version = ""
            version_elem = soup.find('span', class_='resourceInfo-version')
            if version_elem:
                version = version_elem.get_text(strip=True)

            # Extract category
            category = "Unknown"
            breadcrumb = soup.find('ul', class_='p-breadcrumbs')
            if breadcrumb:
                category_links = breadcrumb.find_all('a')
                for link in category_links:
                    href = link.get('href', '')
                    if '/resources/categories/' in href:
                        category = link.get_text(strip=True)
                        break

            # Extract description
            description = ""
            desc_elem = soup.find('div', class_='bbWrapper')
            if desc_elem:
                description = desc_elem.get_text(strip=True)[:200]  # Limit length

            # Extract download count
            downloads = 0
            stats_dl = soup.find_all('dl', class_='pairs')
            for dl in stats_dl:
                dt = dl.find('dt')
                if dt and 'downloads' in dt.get_text().lower():
                    dd = dl.find('dd')
                    if dd:
                        try:
                            downloads = int(dd.get_text(strip=True).replace(',', ''))
                        except ValueError:
                            pass
                        break

            return RoRResource(
                id=resource_id,
                title=title,
                author=author,
                category=category,
                description=description,
                download_url=f"{self.RESOURCES_URL}{resource_id}/download/",
                preview_url=None,
                rating=0.0,
                downloads=downloads,
                last_update="",
                version=version,
                file_size=None,
                tags=[]
            )

        except Exception as e:
            self.logger.warning(f"Error parsing resource details: {e}")
            return RoRResource(
                id=resource_id,
                title=f"Resource {resource_id}",
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
                return self._sanitize_filename(filename_match.group(1))

        # Generate filename
        safe_title = self._sanitize_filename(resource.title)
        return f"{safe_title}_{resource.id}.zip"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem"""
        # Remove invalid characters for Windows/Linux/macOS
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Remove control characters and other problematic characters
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '_', filename)

        # Replace multiple spaces/underscores with single underscore
        filename = re.sub(r'[\s_]+', '_', filename)

        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')

        # Ensure filename is not empty
        if not filename:
            filename = "resource"

        # Limit length (leave room for extension)
        if len(filename) > 80:
            filename = filename[:80]

        # Remove trailing underscore
        filename = filename.rstrip('_')

        return filename
    
    def _extract_zip(self, zip_path: Path, resource: RoRResource):
        """Extract zip file to organized directory"""
        safe_title = self._sanitize_filename(resource.title)
        extract_dir = self.download_dir / f"{safe_title}_{resource.id}"
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
