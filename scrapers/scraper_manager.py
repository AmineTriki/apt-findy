"""
Scraper manager - orchestrates all scrapers and combines results.
"""
import json
import sys
import argparse
from datetime import datetime
from typing import List, Dict
import os

# Import Montreal-specific scrapers
try:
    from kijiji import scrape_kijiji
except ImportError:
    scrape_kijiji = None

try:
    from apartments_com_montreal import scrape_apartments_com_montreal
except ImportError:
    scrape_apartments_com_montreal = None

try:
    from rentitfurnished import scrape_rentitfurnished
except ImportError:
    scrape_rentitfurnished = None

try:
    from sublet_com import scrape_sublet_com
except ImportError:
    scrape_sublet_com = None

try:
    from rentals_ca import scrape_rentals_ca
except ImportError:
    scrape_rentals_ca = None

try:
    from padmapper import scrape_padmapper
except ImportError:
    scrape_padmapper = None

# Note: Airbnb monthly removed - requires Selenium, low priority

# Import geocoding, distance, and matching modules
try:
    from geocoder import Geocoder, load_preferences
except ImportError:
    Geocoder = None
    load_preferences = None

try:
    from distance_calculator import calculate_distances
except ImportError:
    calculate_distances = None

try:
    from matcher import match_apartments
except ImportError:
    match_apartments = None


def remove_duplicates(apartments: List[Dict]) -> List[Dict]:
    """
    Remove duplicate apartments based on URL or address.
    
    Args:
        apartments: List of apartment dictionaries
    
    Returns:
        List with duplicates removed
    """
    seen_urls = set()
    seen_addresses = set()
    unique_apartments = []
    
    for apt in apartments:
        # Skip if no URL or address
        if not apt.get('url') and not apt.get('address'):
            continue
        
        # Check for duplicate URL
        if apt.get('url'):
            if apt['url'] in seen_urls:
                continue
            seen_urls.add(apt['url'])
        
        # Check for duplicate address (normalized)
        if apt.get('address'):
            address_key = apt['address'].lower().strip()
            if address_key in seen_addresses:
                continue
            seen_addresses.add(address_key)
        
        unique_apartments.append(apt)
    
    return unique_apartments


def assign_ids(apartments: List[Dict]) -> List[Dict]:
    """
    Assign unique IDs to apartments.
    
    Args:
        apartments: List of apartment dictionaries
    
    Returns:
        List with IDs assigned
    """
    for idx, apt in enumerate(apartments, start=1):
        apt['id'] = idx
    return apartments


def save_apartments(apartments: List[Dict], output_path: str = "website/apartments.json") -> None:
    """
    Save apartments to JSON file.
    
    Args:
        apartments: List of apartment dictionaries
        output_path: Path to output JSON file
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Prepare output data
    output_data = {
        "apartments": apartments,
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "total_count": len(apartments)
    }
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved {len(apartments)} apartments to {output_path}")


def run_all_scrapers(city: str = "Montreal", max_pages_per_scraper: int = 3) -> List[Dict]:
    """
    Run all available scrapers and combine results.
    
    Args:
        city: City name to search
        max_pages_per_scraper: Maximum pages per scraper
    
    Returns:
        Combined list of all apartments
    """
    all_apartments = []
    
    print("=" * 60)
    print("Starting Montreal apartment scraping...")
    print("=" * 60)
    
    scraper_num = 1
    total_scrapers = 6
    
    # Run Kijiji scraper (Priority 1 - TIER 1)
    if scrape_kijiji:
        try:
            print(f"\n[{scraper_num}/{total_scrapers}] Scraping Kijiji Montreal...")
            apts = scrape_kijiji(city="montreal", max_pages=max_pages_per_scraper)
            all_apartments.extend(apts)
            print(f"✓ Found {len(apts)} apartments from Kijiji")
        except Exception as e:
            print(f"✗ Error scraping Kijiji: {e}")
    else:
        print(f"[{scraper_num}/{total_scrapers}] Kijiji scraper not available")
    scraper_num += 1
    
    # Run Apartments.com Montreal scraper (Priority 2 - TIER 1)
    if scrape_apartments_com_montreal:
        try:
            print(f"\n[{scraper_num}/{total_scrapers}] Scraping Apartments.com Montreal...")
            apts = scrape_apartments_com_montreal(max_pages=max_pages_per_scraper)
            all_apartments.extend(apts)
            print(f"✓ Found {len(apts)} apartments from Apartments.com")
        except Exception as e:
            print(f"✗ Error scraping Apartments.com: {e}")
    else:
        print(f"[{scraper_num}/{total_scrapers}] Apartments.com scraper not available")
    scraper_num += 1
    
    # Run Rent it Furnished scraper (Priority 3 - TIER 1)
    if scrape_rentitfurnished:
        try:
            print(f"\n[{scraper_num}/{total_scrapers}] Scraping Rent it Furnished...")
            apts = scrape_rentitfurnished(max_pages=max_pages_per_scraper)
            all_apartments.extend(apts)
            print(f"✓ Found {len(apts)} apartments from Rent it Furnished")
        except Exception as e:
            print(f"✗ Error scraping Rent it Furnished: {e}")
    else:
        print(f"[{scraper_num}/{total_scrapers}] Rent it Furnished scraper not available")
    scraper_num += 1
    
    # Run Sublet.com scraper (Priority 4 - TIER 2)
    if scrape_sublet_com:
        try:
            print(f"\n[{scraper_num}/{total_scrapers}] Scraping Sublet.com...")
            apts = scrape_sublet_com(max_pages=max_pages_per_scraper)
            all_apartments.extend(apts)
            print(f"✓ Found {len(apts)} apartments from Sublet.com")
        except Exception as e:
            print(f"✗ Error scraping Sublet.com: {e}")
    else:
        print(f"[{scraper_num}/{total_scrapers}] Sublet.com scraper not available")
    scraper_num += 1
    
    # Run Rentals.ca scraper (Priority 5 - TIER 2)
    if scrape_rentals_ca:
        try:
            print(f"\n[{scraper_num}/{total_scrapers}] Scraping Rentals.ca...")
            apts = scrape_rentals_ca(max_pages=max_pages_per_scraper)
            all_apartments.extend(apts)
            print(f"✓ Found {len(apts)} apartments from Rentals.ca")
        except Exception as e:
            print(f"✗ Error scraping Rentals.ca: {e}")
    else:
        print(f"[{scraper_num}/{total_scrapers}] Rentals.ca scraper not available")
    scraper_num += 1
    
    # Run PadMapper scraper (Priority 6 - TIER 3)
    if scrape_padmapper:
        try:
            print(f"\n[{scraper_num}/{total_scrapers}] Scraping PadMapper...")
            apts = scrape_padmapper(max_pages=max_pages_per_scraper)
            all_apartments.extend(apts)
            print(f"✓ Found {len(apts)} apartments from PadMapper")
        except Exception as e:
            print(f"✗ Error scraping PadMapper: {e}")
    else:
        print(f"[{scraper_num}/{total_scrapers}] PadMapper scraper not available")
    
    print("\n" + "=" * 60)
    print(f"Total apartments found: {len(all_apartments)}")
    print("=" * 60)
    
    # Remove duplicates
    print("\nRemoving duplicates...")
    unique_apartments = remove_duplicates(all_apartments)
    print(f"After removing duplicates: {len(unique_apartments)} apartments")
    
    # Assign IDs
    unique_apartments = assign_ids(unique_apartments)
    
    return unique_apartments


def geocode_apartments(apartments: List[Dict], preferences_file: str = "config/preferences.json") -> List[Dict]:
    """
    Geocode all apartment addresses.
    
    Args:
        apartments: List of apartment dictionaries
        preferences_file: Path to preferences file
    
    Returns:
        List of apartments with lat/lng coordinates
    """
    if not Geocoder:
        print("Geocoder not available, skipping geocoding")
        return apartments
    
    print("\n" + "=" * 60)
    print("Geocoding apartment addresses...")
    print("=" * 60)
    
    geocoder = Geocoder()
    
    geocoded_count = 0
    for apt in apartments:
        address = apt.get('address')
        if address and not apt.get('lat'):
            coords = geocoder.geocode(address)
            if coords:
                apt['lat'], apt['lng'] = coords
                geocoded_count += 1
                if geocoded_count % 10 == 0:
                    print(f"Geocoded {geocoded_count} apartments...")
    
    print(f"✓ Geocoded {geocoded_count} apartments")
    return apartments


def calculate_apartment_distances(apartments: List[Dict], preferences_file: str = "config/preferences.json") -> List[Dict]:
    """
    Calculate distances from apartments to important locations.
    
    Args:
        apartments: List of apartment dictionaries
        preferences_file: Path to preferences file
    
    Returns:
        List of apartments with distance information
    """
    if not calculate_distances or not load_preferences:
        print("Distance calculator not available, skipping distance calculation")
        return apartments
    
    preferences = load_preferences(preferences_file)
    if not preferences:
        print("Could not load preferences, skipping distance calculation")
        return apartments
    
    print("\n" + "=" * 60)
    print("Calculating distances to important locations...")
    print("=" * 60)
    
    # Prepare locations for distance calculation
    locations = []
    
    # Add work location
    work_address = preferences.get('work_address')
    if work_address:
        geocoder = Geocoder() if Geocoder else None
        if geocoder:
            # Try full address first, then simplified version
            work_coords = geocoder.geocode(work_address)
            if not work_coords:
                # Try without suite number
                simplified_address = work_address.replace('Suite 500,', '').replace('Suite 500', '')
                work_coords = geocoder.geocode(simplified_address)
            if not work_coords:
                # Try just the street address
                street_only = "1190 Avenue des Canadiens-de-Montréal, Montréal, QC"
                work_coords = geocoder.geocode(street_only)
            if work_coords:
                locations.append({
                    'name': 'Work',
                    'lat': work_coords[0],
                    'lng': work_coords[1]
                })
            else:
                print(f"Warning: Could not geocode work address: {work_address}")
    
    # Add important locations
    important_locations = preferences.get('important_locations', [])
    for loc in important_locations:
        loc_address = loc.get('address')
        if loc_address:
            geocoder = Geocoder() if Geocoder else None
            if geocoder:
                loc_coords = geocoder.geocode(loc_address)
                if loc_coords:
                    locations.append({
                        'name': loc.get('name', 'Location'),
                        'lat': loc_coords[0],
                        'lng': loc_coords[1]
                    })
                else:
                    print(f"Warning: Could not geocode location: {loc_address}")
    
    if not locations:
        print("No locations found for distance calculation")
        return apartments
    
    # Calculate distances for each apartment
    commute_prefs = preferences.get('commute_preferences', {})
    transport_mode = commute_prefs.get('transport_mode', 'mixed')
    
    calculated_count = 0
    for apt in apartments:
        if apt.get('lat') and apt.get('lng'):
            dist_info = calculate_distances(
                apt['lat'],
                apt['lng'],
                locations,
                transport_mode
            )
            
            if dist_info.get('distance_km') is not None:
                apt['distance_to_work'] = dist_info['distance_km']
                apt['commute_time'] = dist_info.get('time_minutes', 0)
                calculated_count += 1
    
    print(f"✓ Calculated distances for {calculated_count} apartments")
    return apartments


def score_apartments(apartments: List[Dict], preferences_file: str = "config/preferences.json") -> List[Dict]:
    """
    Calculate match scores and sort apartments.
    
    Args:
        apartments: List of apartment dictionaries
        preferences_file: Path to preferences file
    
    Returns:
        List of apartments sorted by match score
    """
    if not match_apartments:
        print("Matcher not available, skipping scoring")
        return apartments
    
    print("\n" + "=" * 60)
    print("Calculating match scores...")
    print("=" * 60)
    
    scored_apartments = match_apartments(apartments, preferences_file)
    
    # Show top matches
    top_matches = [apt for apt in scored_apartments[:5] if apt.get('match_score', 0) > 0]
    if top_matches:
        print(f"\nTop matches:")
        for apt in top_matches:
            print(f"  - {apt.get('title', 'N/A')}: {apt.get('match_score', 0)}%")
    
    print(f"✓ Scored {len(scored_apartments)} apartments")
    return scored_apartments


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Scrape apartments from multiple sources')
    parser.add_argument('--city', type=str, default='Montreal', help='City to search (default: Montreal)')
    parser.add_argument('--pages', type=int, default=3, help='Max pages per scraper (default: 3)')
    parser.add_argument('--output', type=str, default='website/apartments.json', help='Output JSON file path')
    
    args = parser.parse_args()
    
    # Run all scrapers
    apartments = run_all_scrapers(city=args.city, max_pages_per_scraper=args.pages)
    
    # Geocode addresses
    apartments = geocode_apartments(apartments)
    
    # Calculate distances
    apartments = calculate_apartment_distances(apartments)
    
    # Calculate match scores and sort
    apartments = score_apartments(apartments)
    
    # Save results
    save_apartments(apartments, output_path=args.output)
    
    print("\n" + "=" * 60)
    print(f"✓ Scraping complete! Found {len(apartments)} unique apartments.")
    print(f"✓ Results saved to {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()

