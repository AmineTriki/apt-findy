"""
Scraper for Craigslist
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import json
import re
from scraper_utils import delay, clean_price, clean_address, extract_bedrooms, extract_bathrooms, extract_sqft


def scrape_craigslist(city: str = "montreal", max_pages: int = 5) -> List[Dict]:
    """
    Scrape apartment listings from Craigslist.
    
    Args:
        city: City name (default: "montreal")
        max_pages: Maximum number of pages to scrape (default: 5)
    
    Returns:
        List of apartment dictionaries
    """
    apartments = []
    base_url = f"https://{city}.craigslist.org"
    
    # Craigslist apartment search URL
    search_url = f"{base_url}/search/apa"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    for page in range(max_pages):
        try:
            # Craigslist uses 's=' parameter for pagination (120 results per page)
            offset = page * 120
            url = f"{search_url}?s={offset}"
            
            print(f"Scraping Craigslist page {page + 1}...")
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Find listings - Craigslist uses class 'result-row'
            listings = soup.find_all('li', class_='result-row')
            
            if not listings:
                print(f"No listings found on page {page + 1}")
                break
            
            for listing in listings:
                try:
                    apt = parse_craigslist_listing(listing, base_url)
                    if apt:
                        apartments.append(apt)
                except Exception as e:
                    print(f"Error parsing listing: {e}")
                    continue
            
            # Delay between pages
            delay(3.0)  # Be more careful with Craigslist
            
        except requests.RequestException as e:
            print(f"Error fetching page {page + 1}: {e}")
            continue
        except Exception as e:
            print(f"Error processing page {page + 1}: {e}")
            continue
    
    print(f"Scraped {len(apartments)} apartments from Craigslist")
    return apartments


def parse_craigslist_listing(listing, base_url: str) -> Optional[Dict]:
    """
    Parse a single Craigslist listing.
    
    Args:
        listing: BeautifulSoup element containing listing data
        base_url: Base URL for constructing full URLs
    
    Returns:
        Apartment dictionary or None if parsing fails
    """
    try:
        # Extract title and URL
        title_elem = listing.find('a', class_='result-title')
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        url = title_elem.get('href', '')
        if url.startswith('/'):
            url = base_url + url
        
        # Extract price
        price_elem = listing.find('span', class_='result-price')
        price_str = price_elem.get_text(strip=True) if price_elem else ""
        price = clean_price(price_str)
        
        # Extract location/neighborhood
        location_elem = listing.find('span', class_='result-hood')
        location = location_elem.get_text(strip=True) if location_elem else ""
        
        # Extract housing info (bedrooms, bathrooms, sqft)
        housing_elem = listing.find('span', class_='housing')
        housing_text = housing_elem.get_text(strip=True) if housing_elem else ""
        
        bedrooms = extract_bedrooms(housing_text)
        bathrooms = extract_bathrooms(housing_text)
        sqft = extract_sqft(housing_text)
        
        # Extract full address from post body (would need to visit individual page)
        # For now, use location/neighborhood
        address = location if location else "Montreal, QC"
        
        # Extract image
        img_elem = listing.find('img', class_='swipe')
        image_url = img_elem.get('src') if img_elem else ""
        if not image_url:
            image_url = "img/property-1.jpg"  # Default placeholder
        
        # Extract description snippet
        desc_elem = listing.find('span', class_='result-body')
        description = desc_elem.get_text(strip=True) if desc_elem else ""
        
        # Check for keywords in description
        desc_lower = description.lower()
        furnished = any(word in desc_lower for word in ['furnished', 'fully furnished', 'furniture'])
        pet_friendly = any(word in desc_lower for word in ['pet friendly', 'pets allowed', 'pet-friendly', 'cats ok', 'dogs ok'])
        
        # Extract amenities from description
        amenities = []
        amenity_keywords = {
            'gym': 'Gym',
            'fitness': 'Gym',
            'parking': 'Parking',
            'laundry': 'Laundry',
            'dishwasher': 'Dishwasher',
            'balcony': 'Balcony',
            'terrace': 'Balcony',
            'pool': 'Pool',
            'concierge': 'Concierge',
            'rooftop': 'Rooftop',
            'lounge': 'Lounge'
        }
        
        for keyword, amenity_name in amenity_keywords.items():
            if keyword in desc_lower and amenity_name not in amenities:
                amenities.append(amenity_name)
        
        # Extract available date
        available_date = None
        date_patterns = [
            r'available\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'avail\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}-\d{2}-\d{2})',  # ISO format
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
            "source": "craigslist",
            "description": description,
            "amenities": amenities[:5],
            "available_date": available_date,
            "pet_friendly": pet_friendly,
            "furnished": furnished,
            # These will be calculated later
            "lat": None,
            "lng": None,
            "distance_to_work": None,
            "commute_time": None,
            "match_score": 0
        }
        
        return apartment
        
    except Exception as e:
        print(f"Error parsing Craigslist listing: {e}")
        return None


if __name__ == "__main__":
    # Test scraper
    print("Testing Craigslist scraper...")
    apartments = scrape_craigslist(city="montreal", max_pages=3)
    
    print(f"\nFound {len(apartments)} apartments")
    if apartments:
        print("\nFirst apartment:")
        print(json.dumps(apartments[0], indent=2))

