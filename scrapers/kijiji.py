"""
Scraper for Kijiji (popular in Canada, especially Montreal)
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import json
import re
from scraper_utils import (
    clean_price, clean_address, extract_bedrooms, extract_bathrooms, extract_sqft,
    create_session_with_retries, make_request_with_retry, page_delay
)
import logging

logger = logging.getLogger(__name__)


def extract_json_ld_listings(soup: BeautifulSoup) -> List[Dict]:
    """
    Extract listings from JSON-LD structured data in the page.
    Kijiji embeds listing data in JSON-LD format which is more reliable.
    """
    listings = []
    try:
        # Find JSON-LD script tag
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                # Check if it's an ItemList with apartments
                if isinstance(data, dict) and data.get('@type') == 'ItemList':
                    items = data.get('itemListElement', [])
                    for item in items:
                        if isinstance(item, dict) and 'item' in item:
                            listings.append(item['item'])
            except (json.JSONDecodeError, KeyError):
                continue
    except Exception as e:
        print(f"  Error extracting JSON-LD: {e}")
    
    return listings


def parse_kijiji_json_ld(item_data: Dict, base_url: str) -> Optional[Dict]:
    """
    Parse a listing from JSON-LD structured data.
    This is more reliable than HTML parsing.
    """
    try:
        if item_data.get('@type') != 'SingleFamilyResidence':
            return None
        
        title = item_data.get('name', '')
        if not title:
            return None
        
        url = item_data.get('url', '')
        if url.startswith('/'):
            url = base_url + url
        
        # Extract price from offers
        offers = item_data.get('offers', {})
        price = offers.get('price')
        if price:
            price = int(price)
        else:
            price = None
        
        # Extract address
        address_obj = item_data.get('address', {})
        if isinstance(address_obj, str):
            address = address_obj
        elif isinstance(address_obj, dict):
            address = address_obj.get('address', '')
        else:
            address = "Montreal, QC"
        
        address = clean_address(address)
        
        # Extract bedrooms and bathrooms
        bedrooms = item_data.get('numberOfBedrooms')
        if bedrooms:
            try:
                bedrooms = float(bedrooms)
            except:
                bedrooms = extract_bedrooms(title.lower())
        else:
            bedrooms = extract_bedrooms(title.lower())
        
        bathrooms = item_data.get('numberOfBathroomsTotal')
        if bathrooms:
            try:
                bathrooms = float(bathrooms)
            except:
                bathrooms = extract_bathrooms(title.lower())
        else:
            bathrooms = extract_bathrooms(title.lower())
        
        # Extract square footage
        floor_size = item_data.get('floorSize', {})
        if isinstance(floor_size, dict):
            sqft = floor_size.get('value')
            if sqft:
                try:
                    sqft = int(sqft)
                except:
                    sqft = None
        else:
            sqft = None
        
        if not sqft:
            sqft = extract_sqft(title.lower())
        
        # Extract image
        image = item_data.get('image', '')
        if not image:
            image = "img/property-1.jpg"
        
        # Extract description
        description = item_data.get('description', '')
        
        # Check for furnished, pet-friendly
        desc_lower = (title + " " + description).lower()
        furnished = any(word in desc_lower for word in ['furnished', 'fully furnished', 'furniture', 'meublé', 'meublée', 'meublé'])
        pet_friendly = item_data.get('petsAllowed', False)
        # Convert string to boolean if needed
        if isinstance(pet_friendly, str):
            pet_friendly = pet_friendly.lower() in ['true', '1', 'yes']
        if not pet_friendly:
            pet_friendly = any(word in desc_lower for word in ['pet friendly', 'pets allowed', 'pet-friendly', 'animaux acceptés'])
        
        # Extract amenities from description
        amenities = []
        amenity_keywords = {
            'gym': 'Gym', 'fitness': 'Gym',
            'parking': 'Parking', 'stationnement': 'Parking',
            'laundry': 'Laundry', 'laveuse': 'Laundry', 'laveuse-sécheuse': 'Laundry',
            'dishwasher': 'Dishwasher', 'lave-vaisselle': 'Dishwasher',
            'balcony': 'Balcony', 'balcon': 'Balcony', 'terrace': 'Balcony',
            'pool': 'Pool', 'piscine': 'Pool',
            'concierge': 'Concierge',
            'rooftop': 'Rooftop',
            'lounge': 'Lounge', 'salon': 'Lounge'
        }
        
        for keyword, amenity_name in amenity_keywords.items():
            if keyword in desc_lower and amenity_name not in amenities:
                amenities.append(amenity_name)
        
        # Check for in-unit laundry
        in_unit_laundry = (
            'in-unit laundry' in desc_lower or 
            'in-suite laundry' in desc_lower or
            'laveuse-sécheuse' in desc_lower or
            'laveuse et sécheuse' in desc_lower
        )
        
        apartment = {
            "title": title,
            "price": price,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms or 1.0,
            "sqft": sqft,
            "address": address,
            "city": "Montreal",
            "images": [image] if image else ["img/property-1.jpg"],
            "url": url,
            "source": "kijiji",
            "description": description,
            "amenities": amenities[:5],
            "available_date": None,  # Not in JSON-LD
            "pet_friendly": pet_friendly,
            "furnished": furnished,
            "in_unit_laundry": in_unit_laundry,
            # These will be calculated later
            "lat": None,
            "lng": None,
            "distance_to_work": None,
            "commute_time": None,
            "match_score": 0
        }
        
        return apartment
        
    except Exception as e:
        print(f"  Error parsing JSON-LD listing: {e}")
        return None


def scrape_kijiji(city: str = "montreal", max_pages: int = 5) -> List[Dict]:
    """
    Scrape apartment listings from Kijiji.
    
    Args:
        city: City name (default: "montreal")
        max_pages: Maximum number of pages to scrape (default: 5)
    
    Returns:
        List of apartment dictionaries
    """
    apartments = []
    base_url = "https://www.kijiji.ca"
    
    # Kijiji apartment search URL for Montreal
    search_url = f"{base_url}/b-apartments-condos/ville-de-montreal/c37l1700281"
    
    session = create_session_with_retries()
    
    for page in range(1, max_pages + 1):
        try:
            if page == 1:
                url = search_url
            else:
                url = f"{search_url}?page={page}"
            
            print(f"Scraping Kijiji page {page}...")
            
            response = make_request_with_retry(session, url)
            if not response:
                print(f"  Failed to fetch page {page}")
                break
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Try to extract from JSON-LD first (more reliable)
            json_ld_data = extract_json_ld_listings(soup)
            if json_ld_data:
                print(f"  Found {len(json_ld_data)} listings from JSON-LD")
                for item_data in json_ld_data:
                    try:
                        apt = parse_kijiji_json_ld(item_data, base_url)
                        if apt:
                            apartments.append(apt)
                    except Exception as e:
                        print(f"  Error parsing JSON-LD listing: {e}")
                        continue
            else:
                # Fall back to HTML parsing
                listings = soup.find_all('section', {'data-testid': 'listing-card'}) or \
                          soup.find_all('div', {'data-testid': 'listing-card'})
                
                if not listings:
                    print(f"  No listings found on page {page}")
                    break
                
                print(f"  Found {len(listings)} listings from HTML")
                for listing in listings:
                    try:
                        apt = parse_kijiji_listing(listing, base_url)
                        if apt:
                            apartments.append(apt)
                    except Exception as e:
                        print(f"  Error parsing listing: {e}")
                        continue
            
            # Delay between pages
            if page < max_pages:
                page_delay(5.0, 10.0)
            
        except Exception as e:
            logger.error(f"Error processing page {page}: {e}")
            continue
    
    session.close()
    print(f"Scraped {len(apartments)} apartments from Kijiji")
    return apartments


def parse_kijiji_listing(listing, base_url: str) -> Optional[Dict]:
    """
    Parse a single Kijiji listing.
    
    Args:
        listing: BeautifulSoup element containing listing data
        base_url: Base URL for constructing full URLs
    
    Returns:
        Apartment dictionary or None if parsing fails
    """
    try:
        # Extract title
        title_elem = listing.find('a', class_='title') or \
                    listing.find('h3', class_='title') or \
                    listing.find('a', {'data-testid': 'listing-link'})
        
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        if not title:
            return None
        
        # Extract URL
        url = title_elem.get('href', '')
        if url.startswith('/'):
            url = base_url + url
        
        # Extract price
        price_elem = listing.find('div', class_='price') or \
                    listing.find('span', class_='price')
        price_str = price_elem.get_text(strip=True) if price_elem else ""
        price = clean_price(price_str)
        
        # Extract location
        location_elem = listing.find('div', class_='location') or \
                       listing.find('span', class_='location')
        location = location_elem.get_text(strip=True) if location_elem else ""
        
        # Extract address (may be in location or description)
        address = location if location else "Montreal, QC"
        
        # Extract description
        desc_elem = listing.find('div', class_='description') or \
                   listing.find('p', class_='description')
        description = desc_elem.get_text(strip=True) if desc_elem else ""
        
        # Extract bedrooms, bathrooms, sqft from description or title
        details_text = (title + " " + description).lower()
        
        bedrooms = extract_bedrooms(details_text)
        bathrooms = extract_bathrooms(details_text)
        sqft = extract_sqft(details_text)
        
        # Check for in-unit laundry
        in_unit_laundry = (
            'in-unit laundry' in details_text or 
            'in-suite laundry' in details_text or
            'laveuse-sécheuse' in details_text or
            'laveuse et sécheuse' in details_text
        )
        
        # Extract image
        img_elem = listing.find('img')
        image_url = img_elem.get('src') or img_elem.get('data-src') if img_elem else ""
        if not image_url:
            image_url = "img/property-1.jpg"
        
        # Check for keywords
        desc_lower = description.lower()
        furnished = any(word in desc_lower for word in ['furnished', 'fully furnished', 'furniture', 'meublé', 'meublée'])
        pet_friendly = any(word in desc_lower for word in ['pet friendly', 'pets allowed', 'pet-friendly', 'animaux acceptés'])
        
        # Extract amenities
        amenities = []
        amenity_keywords = {
            'gym': 'Gym',
            'fitness': 'Gym',
            'parking': 'Parking',
            'stationnement': 'Parking',
            'laundry': 'Laundry',
            'laveuse': 'Laundry',
            'dishwasher': 'Dishwasher',
            'lave-vaisselle': 'Dishwasher',
            'balcony': 'Balcony',
            'balcon': 'Balcony',
            'terrace': 'Balcony',
            'pool': 'Pool',
            'piscine': 'Pool',
            'concierge': 'Concierge',
            'rooftop': 'Rooftop',
            'lounge': 'Lounge',
            'salon': 'Lounge'
        }
        
        for keyword, amenity_name in amenity_keywords.items():
            if keyword in desc_lower and amenity_name not in amenities:
                amenities.append(amenity_name)
        
        # Extract available date
        available_date = None
        date_patterns = [
            r'available\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'disponible\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}-\d{2}-\d{2})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, desc_lower)
            if match:
                available_date = match.group(1)
                break
        
        apartment = {
            "title": title,
            "price": price,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms or 1.0,
            "sqft": sqft,
            "address": address,
            "city": "Montreal",
            "images": [image_url],
            "url": url,
            "source": "kijiji",
            "description": description,
            "amenities": amenities[:5],
            "available_date": available_date,
            "pet_friendly": pet_friendly,
            "furnished": furnished,
            "in_unit_laundry": in_unit_laundry,
            # These will be calculated later
            "lat": None,
            "lng": None,
            "distance_to_work": None,
            "commute_time": None,
            "match_score": 0
        }
        
        return apartment
        
    except Exception as e:
        print(f"Error parsing Kijiji listing: {e}")
        return None


if __name__ == "__main__":
    # Test scraper
    print("Testing Kijiji scraper...")
    apartments = scrape_kijiji(city="montreal", max_pages=3)
    
    print(f"\nFound {len(apartments)} apartments")
    if apartments:
        print("\nFirst apartment:")
        print(json.dumps(apartments[0], indent=2))

