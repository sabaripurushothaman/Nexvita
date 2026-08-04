import math
import requests
import os
from typing import Dict, Optional, Tuple

def get_user_location() -> Optional[Dict]:
    """
    Get the user's current location using IP geolocation.
    In a real mobile app, this would use the device's GPS.
    """
    try:
        # Using a free IP geolocation service
        # In production, you might use a more reliable service or the device's GPS
        response = requests.get('http://ip-api.com/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                return {
                    'latitude': data['lat'],
                    'longitude': data['lon'],
                    'city': data['city'],
                    'region': data['regionName'],
                    'country': data['country'],
                    'ip': data['query']
                }
    except Exception as e:
        # Log the error in a real application
        pass
    return None

def get_location_from_ip(ip_address: str) -> Optional[Dict]:
    """Get location information from an IP address."""
    try:
        response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                return {
                    'latitude': data['lat'],
                    'longitude': data['lon'],
                    'city': data['city'],
                    'region': data['regionName'],
                    'country': data['country'],
                    'ip': data['query']
                }
    except Exception:
        pass
    return None

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

# Alias for backward compatibility
get_distance = calculate_distance

def get_address_from_coordinates(latitude: float, longitude: float) -> Optional[Dict]:
    """
    Get address information from latitude and longitude using reverse geocoding.
    Uses Nominatim (OpenStreetMap) - in production you might want to use a service
    with better rate limits and terms of service.
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=18&addressdetails=1"
        headers = {'User-Agent': 'NexVitaHealthApp/1.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            address = data.get('address', {})
            return {
                'formatted': data.get('display_name', ''),
                'road': address.get('road', ''),
                'house_number': address.get('house_number', ''),
                'city': address.get('city', address.get('town', address.get('village', ''))),
                'state': address.get('state', ''),
                'postcode': address.get('postcode', ''),
                'country': address.get('country', ''),
                'latitude': latitude,
                'longitude': longitude
            }
    except Exception:
        pass
    return None

def get_coordinates_from_address(address: str) -> Optional[Dict]:
    """
    Get latitude and longitude from an address using geocoding.
    Uses Nominatim (OpenStreetMap).
    """
    try:
        # URL encode the address
        import urllib.parse
        encoded_address = urllib.parse.quote(address)
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={encoded_address}&limit=1"
        headers = {'User-Agent': 'NexVitaHealthApp/1.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                item = data[0]
                return {
                    'latitude': float(item['lat']),
                    'longitude': float(item['lon']),
                    'display_name': item.get('display_name', ''),
                    'address': {
                        'road': item.get('address', {}).get('road', ''),
                        'city': item.get('address', {}).get('city', ''),
                        'state': item.get('address', {}).get('state', ''),
                        'country': item.get('address', {}).get('country', '')
                    }
                }
    except Exception:
        pass
    return None

def is_point_in_radius(lat1: float, lon1: float, lat2: float, lon2: float, radius_km: float) -> bool:
    """Check if a point is within a given radius of another point."""
    distance = calculate_distance(lat1, lon1, lat2, lon2)
    return distance <= radius_km

def format_coordinates(latitude: float, longitude: float) -> str:
    """Format coordinates as a string."""
    return f"{latitude:.6f}, {longitude:.6f}"

def get_distance_human_readable(distance_km: float) -> str:
    """Convert distance in kilometers to a human-readable string."""
    if distance_km < 1:
        return f"{distance_km * 1000:.0f} meters"
    elif distance_km < 1000:
        return f"{distance_km:.1f} km"
    else:
        return f"{distance_km / 1000:.1f} miles"

# Constants for common locations (useful for testing or defaults)
DEFAULT_LOCATIONS = {
    'new_york': {'latitude': 40.7128, 'longitude': -74.0060, 'city': 'New York', 'country': 'USA'},
    'london': {'latitude': 51.5074, 'longitude': -0.1278, 'city': 'London', 'country': 'UK'},
    'tokyo': {'latitude': 35.6762, 'longitude': 139.6503, 'city': 'Tokyo', 'country': 'Japan'},
    'sydney': {'latitude': -33.8688, 'longitude': 151.2093, 'city': 'Sydney', 'country': 'Australia'}
}

def get_default_location(key: str = 'new_york') -> Optional[Dict]:
    """Get a default location for testing or fallback."""
    return DEFAULT_LOCATIONS.get(key.lower())

# For offline use or when APIs are not available
def get_mock_location() -> Dict:
    """Return a mock location for development/testing."""
    return {
        'latitude': 40.7128,
        'longitude': -74.0060,
        'city': 'New York',
        'region': 'New York',
        'country': 'USA',
        'ip': '127.0.0.1'
    }