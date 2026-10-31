# Location-Based Internet Search Setup Guide

This guide explains how to enable location-based internet search in your Gemini-powered Gmail/Calendar app.

## Overview

The app can now:
1. **Extract location** from your prompts (e.g., "Find coffee shops in Los Angeles")
2. **Convert locations to coordinates** (latitude/longitude)
3. **Use Google Search and Google Maps tools** with location context for more relevant results

## How It Works

### 1. Location Extraction

The app automatically detects location mentions in your prompts using patterns like:
- "in [location]" - e.g., "Find restaurants in San Francisco"
- "near [location]" - e.g., "What's the weather near me"
- "at [location]" - e.g., "Find hotels at the airport"
- "from [location]" - e.g., "Search news from New York"
- "location: [location]" - e.g., "location: Los Angeles"

### 2. Geocoding (Location → Coordinates)

Currently uses a simple hardcoded list of common cities. For production use, you should:

**Option A: Use Google Geocoding API (Recommended)**

1. Get a Google Maps API key:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable "Geocoding API"
   - Create an API key

2. Install the library:
   ```bash
   pip install googlemaps
   ```

3. Update `scheduling_agent.py`:
   ```python
   from location_helper import get_location_coordinates
   import os
   
   # In run_agent function:
   location_coords = get_location_coordinates(
       user_prompt, 
       use_google_api=True,
       api_key=os.getenv('GOOGLE_MAPS_API_KEY')
   )
   ```

4. Set your API key:
   ```bash
   export GOOGLE_MAPS_API_KEY="your-api-key-here"
   ```

**Option B: Use a different geocoding service**

You can modify `location_helper.py` to use other services like:
- OpenStreetMap Nominatim (free, no API key needed)
- Mapbox Geocoding API
- Here Geocoding API

### 3. Google Search & Google Maps Tools

The app attempts to enable Gemini's built-in Google Search and Google Maps tools. These tools allow Gemini to:

- **Google Search**: Search the web with location context
- **Google Maps**: Find local businesses, places, and get location-specific information

## Current Implementation Status

The code structure is in place, but you may need to:

1. **Verify Gemini API supports these tools**: Check the latest Gemini API documentation for the exact tool names and configuration.

2. **Enable tools in your API settings**: Some tools may need to be enabled in your Google Cloud project settings.

3. **Check API structure**: The exact API structure may vary. If you get errors, check:
   - `types.GoogleSearch()` vs `types.google_search()`
   - `types.GoogleMaps()` vs `types.google_maps()`
   - Tool configuration structure

## Testing

Try prompts like:
- "Find the best pizza restaurants in Los Angeles"
- "What's the weather like in New York?"
- "Search for coffee shops near San Francisco"
- "Find hotels in Chicago"

The app will:
1. Extract the location (Los Angeles, New York, San Francisco, Chicago)
2. Convert to coordinates
3. Use those coordinates to provide location-relevant search results

## Troubleshooting

### Location not detected
- Make sure you include location keywords like "in", "near", "at"
- Try being more explicit: "location: [city name]"

### Coordinates not found
- The hardcoded list only includes major cities
- For other locations, enable Google Geocoding API (see Option A above)

### Google Search/Maps tools not working
- Check Gemini API documentation for correct tool names
- Verify tools are enabled in your Google Cloud project
- Check API error messages for specific issues

## Example Usage

```python
# In your prompt:
"Find Italian restaurants in Boston"

# The app will:
# 1. Extract "Boston" as location
# 2. Convert to coordinates (42.3601, -71.0589)
# 3. Pass coordinates to Google Search/Google Maps tools
# 4. Get location-relevant restaurant results
```

## Next Steps

1. Test with common city names (they're in the hardcoded list)
2. Set up Google Geocoding API for accurate location conversion
3. Verify Gemini API tool configuration matches your API version
4. Test with various location-based queries

For more information, see:
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [Google Geocoding API](https://developers.google.com/maps/documentation/geocoding)
- [Google Maps Platform](https://developers.google.com/maps)

