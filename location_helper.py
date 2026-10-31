# --- location_helper.py ---
"""
Helper functions for extracting location from prompts and converting to coordinates
"""

import re
from typing import Optional, Tuple, Dict

def extract_location_from_prompt(prompt: str) -> Optional[str]:
    """
    Extract location information from user prompt.
    Looks for patterns like "in [location]", "near [location]", "at [location]", etc.
    """
    # Common location patterns
    patterns = [
        r'\bin\s+([A-Z][a-zA-Z\s,]+?)(?:\s|$|,|\.|!|\?)',  # "in Los Angeles"
        r'\bnear\s+([A-Z][a-zA-Z\s,]+?)(?:\s|$|,|\.|!|\?)',  # "near me" or "near downtown"
        r'\bat\s+([A-Z][a-zA-Z\s,]+?)(?:\s|$|,|\.|!|\?)',  # "at the office"
        r'\bfrom\s+([A-Z][a-zA-Z\s,]+?)(?:\s|$|,|\.|!|\?)',  # "from New York"
        r'\blocation[:\s]+([A-Z][a-zA-Z\s,]+?)(?:\s|$|,|\.|!|\?)',  # "location: San Francisco"
        r'\baddress[:\s]+([A-Z][a-zA-Z\s,]+?)(?:\s|$|,|\.|!|\?)',  # "address: 123 Main St"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            # Clean up common trailing words
            location = re.sub(r'\s+(and|or|the|a|an)\s*$', '', location, flags=re.IGNORECASE)
            if len(location) > 2:  # Valid location
                return location
    
    # Check for explicit location mentions (capitalized city/place names)
    # This is a simple heuristic - could be improved
    capitalized_words = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', prompt)
    # Filter out common non-location capitalized words
    exclude_words = {'Gmail', 'Calendar', 'Email', 'Meeting', 'Tuesday', 'Wednesday', 
                     'Thursday', 'Friday', 'Saturday', 'Sunday', 'Monday', 'January',
                     'February', 'March', 'April', 'May', 'June', 'July', 'August',
                     'September', 'October', 'November', 'December'}
    
    for word in capitalized_words:
        if word not in exclude_words and len(word) > 3:
            # Could be a location
            return word
    
    return None


def geocode_location(location: str, use_google_api: bool = False, api_key: str = None) -> Optional[Tuple[float, float]]:
    """
    Convert location string to latitude/longitude coordinates.
    
    Args:
        location: Location string (e.g., "Los Angeles", "New York, NY")
        use_google_api: If True, use Google Geocoding API (requires api_key)
        api_key: Google Maps API key (required if use_google_api=True)
    
    Returns (latitude, longitude) or None if not found.
    
    For production use, set use_google_api=True and provide your Google Maps API key.
    Get your API key from: https://console.cloud.google.com/google/maps-apis
    """
    # Use Google Geocoding API if enabled
    if use_google_api and api_key:
        try:
            import googlemaps
            gmaps = googlemaps.Client(key=api_key)
            geocode_result = gmaps.geocode(location)
            if geocode_result:
                lat = geocode_result[0]['geometry']['location']['lat']
                lng = geocode_result[0]['geometry']['location']['lng']
                return (lat, lng)
        except ImportError:
            print("⚠ googlemaps library not installed. Install with: pip install googlemaps")
        except Exception as e:
            print(f"⚠ Geocoding API error: {e}")
    
    # Fallback: Simple hardcoded locations for common places (for demo purposes)
    # In production, use Google Geocoding API: https://developers.google.com/maps/documentation/geocoding
    common_locations = {
        'los angeles': (34.0522, -118.2437),
        'la': (34.0522, -118.2437),
        'new york': (40.7128, -74.0060),
        'nyc': (40.7128, -74.0060),
        'san francisco': (37.7749, -122.4194),
        'sf': (37.7749, -122.4194),
        'chicago': (41.8781, -87.6298),
        'houston': (29.7604, -95.3698),
        'phoenix': (33.4484, -112.0740),
        'philadelphia': (39.9526, -75.1652),
        'san antonio': (29.4241, -98.4936),
        'san diego': (32.7157, -117.1611),
        'dallas': (32.7767, -96.7970),
        'san jose': (37.3382, -121.8863),
        'austin': (30.2672, -97.7431),
        'london': (51.5074, -0.1278),
        'paris': (48.8566, 2.3522),
        'tokyo': (35.6762, 139.6503),
        'sydney': (-33.8688, 151.2093),
        'toronto': (43.6532, -79.3832),
    }
    
    location_lower = location.lower().strip()
    
    # Check exact match
    if location_lower in common_locations:
        return common_locations[location_lower]
    
    # Check partial match
    for key, coords in common_locations.items():
        if key in location_lower or location_lower in key:
            return coords
    
    # If not found, return None
    # In production, you would call Google Geocoding API here
    return None


def get_location_coordinates(prompt: str, use_google_api: bool = False, api_key: str = None) -> Optional[Dict[str, float]]:
    """
    Extract location from prompt and return coordinates if found.
    
    Args:
        prompt: User's prompt text
        use_google_api: If True, use Google Geocoding API for accurate results
        api_key: Google Maps API key (required if use_google_api=True)
    
    Returns dict with 'latitude' and 'longitude' or None.
    """
    location = extract_location_from_prompt(prompt)
    
    if not location:
        return None
    
    coords = geocode_location(location, use_google_api=use_google_api, api_key=api_key)
    
    if coords:
        return {
            'latitude': coords[0],
            'longitude': coords[1]
        }
    
    return None

