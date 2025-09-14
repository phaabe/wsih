#!/usr/bin/env python3

import json
import requests
import sys
import os
from typing import Dict, Any, List

def remove_image_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove image data from the JSON structure while preserving other fields."""
    if isinstance(data, dict):
        cleaned_data = {}
        for key, value in data.items():
            if key == "Cover":
                # Skip Cover field entirely
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

def fetch_and_store_json(url: str, output_file: str = "all-podcasts.json"):
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

        # Remove image data
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
