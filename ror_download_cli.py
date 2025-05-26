#!/usr/bin/env python3
"""
Command-line interface for Rigs of Rods repository downloader

This script provides a CLI for browsing, searching, and downloading
vehicle files from the Rigs of Rods repository.
"""

import argparse
import sys
import os
import json
import time
from pathlib import Path
from typing import List, Optional

from ror_downloader import RoRDownloader, RoRResource


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.0f}m {seconds%60:.0f}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours:.0f}h {minutes:.0f}m"


def print_resource_table(resources: List[RoRResource], show_details: bool = False):
    """Print resources in a formatted table"""
    if not resources:
        print("No resources found.")
        return
    
    print(f"\n{'ID':<8} {'Title':<40} {'Author':<20} {'Category':<15}")
    print("-" * 85)
    
    for resource in resources:
        title = resource.title[:37] + "..." if len(resource.title) > 40 else resource.title
        author = resource.author[:17] + "..." if len(resource.author) > 20 else resource.author
        category = resource.category[:12] + "..." if len(resource.category) > 15 else resource.category
        
        print(f"{resource.id:<8} {title:<40} {author:<20} {category:<15}")
        
        if show_details and resource.description:
            desc = resource.description[:100] + "..." if len(resource.description) > 100 else resource.description
            print(f"         {desc}")
    
    print()


def print_resource_details(resource: RoRResource):
    """Print detailed information about a resource"""
    print(f"\nResource Details:")
    print(f"{'='*50}")
    print(f"ID: {resource.id}")
    print(f"Title: {resource.title}")
    print(f"Author: {resource.author}")
    print(f"Category: {resource.category}")
    print(f"Version: {resource.version}")
    print(f"Downloads: {resource.downloads}")
    print(f"Rating: {resource.rating}/5.0")
    print(f"Last Update: {resource.last_update}")
    
    if resource.file_size:
        print(f"File Size: {resource.file_size}")
    
    if resource.tags:
        print(f"Tags: {', '.join(resource.tags)}")
    
    if resource.description:
        print(f"\nDescription:")
        print(f"{resource.description}")
    
    print()


def search_command(args):
    """Handle search command"""
    downloader = RoRDownloader(download_dir=args.download_dir)
    
    print(f"Searching for: '{args.query}'")
    if args.category:
        print(f"Category filter: {args.category}")
    
    resources, total_pages = downloader.search_resources(
        query=args.query,
        category=args.category,
        page=args.page,
        per_page=args.limit
    )
    
    if resources:
        print(f"\nFound {len(resources)} resources (page {args.page} of {total_pages})")
        print_resource_table(resources, show_details=args.details)
        
        if args.page < total_pages:
            print(f"Use --page {args.page + 1} to see more results")
    else:
        print("No resources found matching your criteria.")


def download_command(args):
    """Handle download command"""
    downloader = RoRDownloader(download_dir=args.download_dir)
    
    if args.resource_ids:
        # Download specific resources by ID
        for resource_id in args.resource_ids:
            print(f"Getting details for resource {resource_id}...")
            resource = downloader.get_resource_details(resource_id)
            
            if not resource:
                print(f"Resource {resource_id} not found or inaccessible")
                continue
            
            print(f"Downloading: {resource.title}")
            
            if args.dry_run:
                print(f"[DRY RUN] Would download {resource.title} to {args.download_dir}")
                continue
            
            success = downloader.download_resource(resource, extract=args.extract)
            
            if success:
                print(f"✓ Successfully downloaded {resource.title}")
            else:
                print(f"✗ Failed to download {resource.title}")
    
    elif args.search_query:
        # Search and download
        print(f"Searching for '{args.search_query}' to download...")
        resources, _ = downloader.search_resources(
            query=args.search_query,
            category=args.category,
            per_page=args.limit
        )
        
        if not resources:
            print("No resources found matching search criteria")
            return
        
        print(f"Found {len(resources)} resources:")
        print_resource_table(resources)
        
        if not args.auto_confirm:
            response = input(f"Download all {len(resources)} resources? (y/N): ")
            if response.lower() != 'y':
                print("Download cancelled")
                return
        
        for resource in resources:
            if args.dry_run:
                print(f"[DRY RUN] Would download {resource.title}")
                continue
            
            print(f"Downloading: {resource.title}")
            success = downloader.download_resource(resource, extract=args.extract)
            
            if success:
                print(f"✓ Successfully downloaded {resource.title}")
            else:
                print(f"✗ Failed to download {resource.title}")
    
    else:
        print("No resource IDs or search query specified")


def popular_command(args):
    """Handle popular command"""
    downloader = RoRDownloader(download_dir=args.download_dir)
    
    print(f"Getting {args.limit} most popular resources...")
    resources = downloader.get_popular_resources(limit=args.limit)
    
    if resources:
        print(f"\nMost Popular Resources:")
        print_resource_table(resources, show_details=args.details)
    else:
        print("Could not retrieve popular resources")


def recent_command(args):
    """Handle recent command"""
    downloader = RoRDownloader(download_dir=args.download_dir)
    
    print(f"Getting {args.limit} most recent resources...")
    resources = downloader.get_recent_resources(limit=args.limit)
    
    if resources:
        print(f"\nMost Recent Resources:")
        print_resource_table(resources, show_details=args.details)
    else:
        print("Could not retrieve recent resources")


def info_command(args):
    """Handle info command"""
    downloader = RoRDownloader(download_dir=args.download_dir)
    
    resource = downloader.get_resource_details(args.resource_id)
    
    if resource:
        print_resource_details(resource)
    else:
        print(f"Resource {args.resource_id} not found or inaccessible")


def history_command(args):
    """Handle history command"""
    downloader = RoRDownloader(download_dir=args.download_dir)
    
    history = downloader.get_download_history()
    
    if not history:
        print("No download history found")
        return
    
    print(f"\nDownload History ({len(history)} items):")
    print(f"{'Date':<20} {'Title':<40} {'Status':<10}")
    print("-" * 72)
    
    for entry in reversed(history[-args.limit:]):  # Show most recent first
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(entry['timestamp']))
        title = entry['resource']['title'][:37] + "..." if len(entry['resource']['title']) > 40 else entry['resource']['title']
        status = "Success" if entry['success'] else "Failed"
        
        print(f"{timestamp:<20} {title:<40} {status:<10}")
    
    print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Download and manage Rigs of Rods repository resources",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--download-dir', default='./downloads',
                       help='Directory to save downloads (default: ./downloads)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for resources')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--category', help='Filter by category')
    search_parser.add_argument('--page', type=int, default=1, help='Page number (default: 1)')
    search_parser.add_argument('--limit', type=int, default=20, help='Results per page (default: 20)')
    search_parser.add_argument('--details', action='store_true', help='Show detailed information')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download resources')
    download_group = download_parser.add_mutually_exclusive_group(required=True)
    download_group.add_argument('--ids', type=int, nargs='+', dest='resource_ids',
                               help='Resource IDs to download')
    download_group.add_argument('--search', dest='search_query',
                               help='Search query for resources to download')
    download_parser.add_argument('--category', help='Filter by category (for search)')
    download_parser.add_argument('--limit', type=int, default=10,
                                help='Max results to download (for search, default: 10)')
    download_parser.add_argument('--extract', action='store_true', default=True,
                                help='Extract zip files (default: True)')
    download_parser.add_argument('--no-extract', dest='extract', action='store_false',
                                help='Don\'t extract zip files')
    download_parser.add_argument('--dry-run', action='store_true',
                                help='Show what would be downloaded without downloading')
    download_parser.add_argument('--auto-confirm', action='store_true',
                                help='Don\'t ask for confirmation when downloading multiple files')
    
    # Popular command
    popular_parser = subparsers.add_parser('popular', help='Show popular resources')
    popular_parser.add_argument('--limit', type=int, default=20,
                               help='Number of resources to show (default: 20)')
    popular_parser.add_argument('--details', action='store_true', help='Show detailed information')
    
    # Recent command
    recent_parser = subparsers.add_parser('recent', help='Show recent resources')
    recent_parser.add_argument('--limit', type=int, default=20,
                              help='Number of resources to show (default: 20)')
    recent_parser.add_argument('--details', action='store_true', help='Show detailed information')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show detailed resource information')
    info_parser.add_argument('resource_id', type=int, help='Resource ID')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show download history')
    history_parser.add_argument('--limit', type=int, default=50,
                               help='Number of entries to show (default: 50)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    try:
        if args.command == 'search':
            search_command(args)
        elif args.command == 'download':
            download_command(args)
        elif args.command == 'popular':
            popular_command(args)
        elif args.command == 'recent':
            recent_command(args)
        elif args.command == 'info':
            info_command(args)
        elif args.command == 'history':
            history_command(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
