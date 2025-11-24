"""
Distance calculation utilities.
"""
import math
from typing import Optional, Tuple, List, Dict


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth (in km).
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
    
    Returns:
        Distance in kilometers
    """
    # Radius of Earth in kilometers
    R = 6371.0
    
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    distance = R * c
    return distance


def walking_time(distance_km: float, walking_speed_kmh: float = 5.0) -> float:
    """
    Calculate walking time in minutes.
    
    Args:
        distance_km: Distance in kilometers
        walking_speed_kmh: Walking speed in km/h (default: 5.0 km/h)
    
    Returns:
        Time in minutes
    """
    if distance_km <= 0:
        return 0.0
    
    # Account for walking paths being longer than straight-line distance
    # Multiply by 1.3 to account for city blocks, paths, etc.
    actual_distance = distance_km * 1.3
    
    time_hours = actual_distance / walking_speed_kmh
    time_minutes = time_hours * 60
    
    return round(time_minutes, 1)


def driving_time(distance_km: float, avg_speed_kmh: float = 30.0) -> float:
    """
    Calculate driving time in minutes (approximation for city driving).
    
    Args:
        distance_km: Distance in kilometers
        avg_speed_kmh: Average speed in km/h (default: 30 km/h for city)
    
    Returns:
        Time in minutes
    """
    if distance_km <= 0:
        return 0.0
    
    # Account for driving paths being longer than straight-line distance
    actual_distance = distance_km * 1.4
    
    time_hours = actual_distance / avg_speed_kmh
    time_minutes = time_hours * 60
    
    return round(time_minutes, 1)


def transit_time(distance_km: float) -> float:
    """
    Calculate transit time in minutes (approximation).
    
    Args:
        distance_km: Distance in kilometers
    
    Returns:
        Time in minutes
    """
    if distance_km <= 0:
        return 0.0
    
    # Rough approximation: 2 minutes per km for transit (including wait time)
    # Plus 5 minutes for walking to/from stations
    base_time = distance_km * 2 + 5
    
    return round(base_time, 1)


def calculate_distances(
    apt_lat: Optional[float],
    apt_lng: Optional[float],
    locations: List[Dict[str, any]],
    transport_mode: str = "mixed"
) -> Dict[str, float]:
    """
    Calculate distances from apartment to multiple locations.
    
    Args:
        apt_lat: Apartment latitude
        apt_lng: Apartment longitude
        locations: List of location dictionaries with 'lat' and 'lng' keys
        transport_mode: Transport mode ('walking', 'driving', 'transit', 'mixed')
    
    Returns:
        Dictionary with distance and time information
    """
    if apt_lat is None or apt_lng is None:
        return {
            "distance_km": None,
            "time_minutes": None
        }
    
    # Calculate distance to each location and find minimum
    min_distance = float('inf')
    closest_location = None
    
    for location in locations:
        if location.get('lat') and location.get('lng'):
            dist = haversine_distance(
                apt_lat, apt_lng,
                location['lat'], location['lng']
            )
            if dist < min_distance:
                min_distance = dist
                closest_location = location
    
    if min_distance == float('inf'):
        return {
            "distance_km": None,
            "time_minutes": None
        }
    
    # Calculate time based on transport mode
    if transport_mode == "walking":
        time_min = walking_time(min_distance)
    elif transport_mode == "driving":
        time_min = driving_time(min_distance)
    elif transport_mode == "transit":
        time_min = transit_time(min_distance)
    else:  # mixed - use walking for short distances, transit for longer
        if min_distance <= 2.0:  # Within 2km, walking is reasonable
            time_min = walking_time(min_distance)
        else:
            time_min = transit_time(min_distance)
    
    return {
        "distance_km": round(min_distance, 2),
        "time_minutes": time_min,
        "closest_location": closest_location.get('name') if closest_location else None
    }


if __name__ == "__main__":
    # Test distance calculation
    # Montreal coordinates
    montreal_lat, montreal_lng = 45.5017, -73.5673
    # Work location (approximate)
    work_lat, work_lng = 45.4969, -73.5694
    
    distance = haversine_distance(montreal_lat, montreal_lng, work_lat, work_lng)
    print(f"Distance: {distance:.2f} km")
    print(f"Walking time: {walking_time(distance):.1f} minutes")

