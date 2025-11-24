"""
Matching algorithm - calculate match scores based on user preferences.
"""
import json
from datetime import datetime
from typing import Dict, Optional
import re


def load_preferences(preferences_file: str = "config/preferences.json") -> dict:
    """Load user preferences."""
    try:
        with open(preferences_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading preferences: {e}")
        return {}


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse date string to datetime object.
    
    Supports various formats:
    - YYYY-MM-DD
    - MM/DD/YYYY
    - MM-DD-YYYY
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # Try ISO format first
    try:
        return datetime.fromisoformat(date_str.replace('/', '-'))
    except:
        pass
    
    # Try other formats
    formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%m-%d-%Y',
        '%d/%m/%Y',
        '%d-%m-%Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    
    return None


def check_must_haves(apartment: Dict, preferences: Dict) -> tuple:
    """
    Check if apartment meets must-have requirements.
    
    Returns:
        Tuple of (meets_all_requirements: bool, missing_requirements: list)
    """
    must_have = preferences.get('must_have', {})
    missing = []
    
    # Check furnished
    if must_have.get('furnished', False):
        if not apartment.get('furnished', False):
            missing.append('furnished')
    
    # Check in-unit laundry
    if must_have.get('in_unit_laundry', False):
        amenities = [a.lower() for a in apartment.get('amenities', [])]
        desc_lower = apartment.get('description', '').lower()
        
        has_laundry = (
            'laundry' in desc_lower and ('in-unit' in desc_lower or 'in suite' in desc_lower or 'in-suite' in desc_lower) or
            'in-unit laundry' in desc_lower or
            'in-suite laundry' in desc_lower or
            any('laundry' in a and ('in-unit' in a or 'in-suite' in a) for a in amenities)
        )
        
        if not has_laundry:
            missing.append('in_unit_laundry')
    
    # Check dishwasher
    if must_have.get('dishwasher', False):
        amenities = [a.lower() for a in apartment.get('amenities', [])]
        desc_lower = apartment.get('description', '').lower()
        
        has_dishwasher = (
            'dishwasher' in desc_lower or
            'dishwasher' in amenities or
            'lave-vaisselle' in desc_lower
        )
        
        if not has_dishwasher:
            missing.append('dishwasher')
    
    # Check modern/renovated (harder to verify, check description)
    if must_have.get('modern_renovated', False):
        desc_lower = apartment.get('description', '').lower()
        title_lower = apartment.get('title', '').lower()
        
        modern_keywords = ['modern', 'renovated', 'updated', 'new', 'contemporary', 'loft', 'condo']
        has_modern = any(keyword in desc_lower or keyword in title_lower for keyword in modern_keywords)
        
        if not has_modern:
            # Not a hard requirement, but note it
            pass
    
    return len(missing) == 0, missing


def calculate_match_score(apartment: Dict, preferences: Dict) -> int:
    """
    Calculate match score (0-100) based on preferences.
    
    Scoring breakdown:
    - Price within budget: 30 points
    - Right # bedrooms: 20 points
    - Close to important locations: 40 points
    - Move-in date match: 10 points
    - Nice-to-have amenities: bonus points
    
    Args:
        apartment: Apartment dictionary
        preferences: User preferences dictionary
    
    Returns:
        Match score (0-100)
    """
    score = 0
    
    # 1. Price score (30 points)
    price = apartment.get('price')
    budget = preferences.get('budget', {})
    min_price = budget.get('min', 0)
    max_price = budget.get('max', float('inf'))
    
    if price:
        if min_price <= price <= max_price:
            # Perfect match: 30 points
            # Bonus if closer to middle of range
            mid_price = (min_price + max_price) / 2
            price_diff = abs(price - mid_price)
            price_range = max_price - min_price
            
            if price_range > 0:
                # Linear scale: closer to middle = higher score
                price_score = 30 * (1 - (price_diff / price_range))
                score += max(0, price_score)
            else:
                score += 30
        elif price < min_price:
            # Below budget - still good, but less points
            score += 15
        else:
            # Above budget - penalty
            over_budget = price - max_price
            if over_budget <= 200:
                score += 10  # Slightly over, small penalty
            # Otherwise 0 points
    
    # 2. Bedroom score (20 points)
    bedrooms = apartment.get('bedrooms')
    bedroom_prefs = preferences.get('bedrooms', {})
    min_bedrooms = bedroom_prefs.get('min', 0)
    max_bedrooms = bedroom_prefs.get('max', float('inf'))
    
    if bedrooms:
        if min_bedrooms <= bedrooms <= max_bedrooms:
            score += 20
        elif bedrooms < min_bedrooms:
            score += 10  # Too small, but still usable
        # Too many bedrooms: 0 points
    
    # 3. Location/distance score (40 points)
    distance_to_work = apartment.get('distance_to_work')
    commute_time = apartment.get('commute_time')
    commute_prefs = preferences.get('commute_preferences', {})
    
    if distance_to_work is not None:
        max_walk_dist = commute_prefs.get('walking_distance_max', 20)
        max_metro_walk = commute_prefs.get('metro_walk_max', 4)
        
        # Walking distance preferred
        if distance_to_work <= max_walk_dist / 2:
            score += 40  # Very close
        elif distance_to_work <= max_walk_dist:
            score += 30  # Within walking distance
        elif distance_to_work <= max_walk_dist * 1.5:
            score += 20  # Close but not walking
        elif distance_to_work <= max_walk_dist * 2:
            score += 10  # Acceptable distance
        # Too far: 0 points
    
    if commute_time is not None:
        # Additional scoring based on commute time
        if commute_time <= 10:
            score += 5  # Bonus for very short commute
        elif commute_time <= 20:
            score += 3  # Bonus for short commute
    
    # 4. Move-in date score (10 points)
    available_date = apartment.get('available_date')
    move_in = preferences.get('move_in_window', {})
    
    if available_date:
        apt_date = parse_date(available_date)
        if apt_date:
            preferred_start = parse_date(move_in.get('preferred_start'))
            preferred_end = parse_date(move_in.get('preferred_end'))
            earliest = parse_date(move_in.get('earliest'))
            latest = parse_date(move_in.get('latest'))
            
            if preferred_start and preferred_end:
                if preferred_start <= apt_date <= preferred_end:
                    score += 10  # Perfect window
                elif earliest and latest and earliest <= apt_date <= latest:
                    score += 5  # Acceptable window
                elif apt_date < earliest:
                    score += 2  # Too early, but workable
                # Too late: 0 points
    
    # 5. Nice-to-have amenities (bonus points, max 10)
    nice_to_have = preferences.get('nice_to_have', [])
    amenities = [a.lower() for a in apartment.get('amenities', [])]
    desc_lower = apartment.get('description', '').lower()
    
    bonus = 0
    for item in nice_to_have:
        if item.lower() in amenities or item.lower() in desc_lower:
            bonus += 1
    
    # Cap bonus at 10 points
    score += min(bonus, 10)
    
    # Check must-haves - if missing critical requirements, reduce score significantly
    meets_requirements, missing = check_must_haves(apartment, preferences)
    if not meets_requirements:
        # Reduce score by 30 points for each missing must-have
        score -= len(missing) * 30
        score = max(0, score)  # Don't go below 0
    
    # Ensure score is between 0 and 100
    return max(0, min(100, int(score)))


def match_apartments(apartments: list, preferences_file: str = "config/preferences.json") -> list:
    """
    Calculate match scores for all apartments and sort by score.
    
    Args:
        apartments: List of apartment dictionaries
        preferences_file: Path to preferences JSON file
    
    Returns:
        List of apartments with match scores, sorted by score (highest first)
    """
    preferences = load_preferences(preferences_file)
    
    if not preferences:
        print("Warning: Could not load preferences, using default scoring")
        return apartments
    
    # Calculate scores
    for apt in apartments:
        apt['match_score'] = calculate_match_score(apt, preferences)
    
    # Sort by match score (highest first)
    apartments.sort(key=lambda x: x.get('match_score', 0), reverse=True)
    
    return apartments


if __name__ == "__main__":
    # Test matcher
    test_apartment = {
        "title": "Modern 1BR Downtown Loft",
        "price": 2000,
        "bedrooms": 1,
        "bathrooms": 1,
        "address": "123 Main St, Montreal, QC",
        "distance_to_work": 1.5,
        "commute_time": 10,
        "furnished": True,
        "amenities": ["Gym", "Laundry", "Dishwasher"],
        "description": "Modern furnished apartment with in-unit laundry and dishwasher",
        "available_date": "2026-02-05"
    }
    
    score = calculate_match_score(test_apartment, load_preferences())
    print(f"Match score: {score}/100")

