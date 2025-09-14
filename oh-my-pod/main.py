#!/usr/bin/env python3

import json
import requests
import sys
import os
from urllib.parse import urlparse
from typing import Dict, Any, List

def remove_image_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove image data from the JSON structure while preserving other fields."""
    if isinstance(data, dict):
        cleaned_data = {}
        for key, value in data.items():
            if key in ["Cover", "id", "createdTime"]:
                # Skip Cover, id, and createdTime fields entirely
                continue
            elif key == "CoverPath":
                # Preserve CoverPath field
                cleaned_data[key] = value
                continue
            elif isinstance(value, dict):
                cleaned_data[key] = remove_image_data(value)
            elif isinstance(value, list):
                cleaned_data[key] = [remove_image_data(item) if isinstance(item, dict) else item for item in value]
            else:
                cleaned_data[key] = value
        return cleaned_data
    elif isinstance(data, list):
        return [remove_image_data(item) if isinstance(item, dict) else item for item in data]
    else:
        return data

def download_cover_image(cover_url: str, podcast_name: str, cover_dir: str = "cover") -> str:
    """Download cover image and return the local file path."""
    try:
        # Create cover directory if it doesn't exist
        os.makedirs(cover_dir, exist_ok=True)

        # Get file extension from URL
        parsed_url = urlparse(cover_url)
        file_ext = os.path.splitext(parsed_url.path)[1] or '.jpg'

        # Create safe filename from podcast name
        safe_name = "".join(c for c in podcast_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        filename = f"{safe_name}{file_ext}"
        filepath = os.path.join("oh-my-pod", cover_dir, filename)

        # Download the image
        response = requests.get(cover_url, timeout=30)
        response.raise_for_status()

        # Save the image
        with open(filepath, 'wb') as f:
            f.write(response.content)

        print(f"Downloaded cover: {filepath}")
        return filepath

    except Exception as e:
        print(f"Error downloading cover for {podcast_name}: {e}", file=sys.stderr)
        return ""

def fetch_and_store_json(url: str, output_file: str = "oh-my-pod/podcasts.json"):
    """Fetch JSON from URL and store it without image data."""
    try:
        # Prepare headers for Airtable API
        headers = {}
        bearer_token = os.environ.get('BEARER_TOKEN')
        if bearer_token:
            headers['Authorization'] = f'Bearer {bearer_token}'

        # Fetch JSON data
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Parse JSON
        data = response.json()

        # Process records to download covers and add local paths
        if 'records' in data:
            for record in data['records']:
                if 'fields' in record and 'Cover' in record['fields']:
                    cover_data = record['fields']['Cover']
                    if isinstance(cover_data, list) and len(cover_data) > 0:
                        # Find the 'large' image or fallback to first image
                        cover_image = None
                        for img in cover_data:
                            if 'thumbnails' in img and 'large' in img['thumbnails']:
                                cover_image = img['thumbnails']['large']
                                break

                        if not cover_image and 'url' in cover_data[0]:
                            cover_image = cover_data[0]

                        if cover_image and 'url' in cover_image:
                            # Get podcast name for filename
                            podcast_name = record['fields'].get('Name', f"podcast_{record.get('id', 'unknown')}")

                            # Download cover and get local path
                            local_path = download_cover_image(cover_image['url'], podcast_name)

                            # Add local cover path to the record
                            if local_path:
                                # Store full path for HTML usage from parent directory
                                record['fields']['CoverPath'] = local_path

        # Remove image data but preserve CoverPath
        cleaned_data = remove_image_data(data)

        # Write to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

        print(f"Successfully fetched and stored JSON data to {output_file}")
        print(f"Removed image data from {len(cleaned_data.get('records', []))} records")

    except requests.RequestException as e:
        print(f"Error fetching data from URL: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Use the Airtable API endpoint from the original comment
    url = "https://api.airtable.com/v0/appFIFZakjlm1Zi3z/podcasts"

    # Allow override via command line argument
    if len(sys.argv) > 1:
        url = sys.argv[1]

    # Check if bearer token is provided
    if not os.environ.get('BEARER_TOKEN'):
        print("Warning: BEARER_TOKEN environment variable not set. Request may fail if authentication is required.", file=sys.stderr)

    fetch_and_store_json(url)
