"""
Geocoding utilities - convert addresses to lat/lng coordinates.
"""
import json
import os
from typing import Optional, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time


class Geocoder:
    """
    Geocoder with caching to avoid repeated API calls.
    """
    
    def __init__(self, cache_file: str = "data/geocache.json"):
        """
        Initialize geocoder with cache.
        
        Args:
            cache_file: Path to cache file for storing geocoded addresses
        """
        self.geolocator = Nominatim(user_agent="apt-findy-scraper")
        self.cache_file = cache_file
        self.cache = self._load_cache()
    
    def _load_cache(self) -> dict:
        """Load geocoding cache from file."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading cache: {e}")
                return {}
        return {}
    
    def _save_cache(self) -> None:
        """Save geocoding cache to file."""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def geocode(self, address: str, retries: int = 3) -> Optional[Tuple[float, float]]:
        """
        Geocode an address to (lat, lng).
        
        Args:
            address: Address string to geocode
            retries: Number of retry attempts
        
        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        if not address:
            return None
        
        # Normalize address for cache key
        cache_key = address.lower().strip()
        
        # Check cache first
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            return (cached['lat'], cached['lng'])
        
        # Geocode with retries
        for attempt in range(retries):
            try:
                time.sleep(1)  # Rate limiting for Nominatim (1 request per second)
                location = self.geolocator.geocode(address, timeout=10)
                
                if location:
                    lat, lng = location.latitude, location.longitude
                    
                    # Save to cache
                    self.cache[cache_key] = {
                        'lat': lat,
                        'lng': lng,
                        'address': address
                    }
                    self._save_cache()
                    
                    return (lat, lng)
                else:
                    print(f"Could not geocode: {address}")
                    return None
                    
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                if attempt < retries - 1:
                    print(f"Geocoding error (attempt {attempt + 1}/{retries}): {e}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"Failed to geocode after {retries} attempts: {address}")
                    return None
            except Exception as e:
                print(f"Unexpected error geocoding {address}: {e}")
                return None
        
        return None
    
    def geocode_batch(self, addresses: list) -> dict:
        """
        Geocode multiple addresses.
        
        Args:
            addresses: List of address strings
        
        Returns:
            Dictionary mapping addresses to (lat, lng) tuples
        """
        results = {}
        for address in addresses:
            if address:
                coords = self.geocode(address)
                results[address] = coords
        return results


def load_preferences(preferences_file: str = "config/preferences.json") -> dict:
    """
    Load user preferences from JSON file.
    
    Args:
        preferences_file: Path to preferences JSON file
    
    Returns:
        Preferences dictionary
    """
    try:
        with open(preferences_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Preferences file not found: {preferences_file}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing preferences file: {e}")
        return {}


if __name__ == "__main__":
    # Test geocoder
    geocoder = Geocoder()
    
    # Test with work address
    test_address = "1190 Avenue des Canadiens-de-Montréal, Montréal, QC"
    print(f"Geocoding: {test_address}")
    coords = geocoder.geocode(test_address)
    if coords:
        print(f"Result: {coords}")
    else:
        print("Geocoding failed")

