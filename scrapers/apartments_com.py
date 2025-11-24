"""
Scraper for Apartments.com
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import json
import re
from scraper_utils import delay, clean_price, clean_address, extract_bedrooms, extract_bathrooms, extract_sqft


def scrape_apartments_com(city: str = "Montreal", max_pages: int = 5) -> List[Dict]:
    """
    Scrape apartment listings from Apartments.com.
    
    Args:
        city: City name to search (default: "Montreal")
        max_pages: Maximum number of pages to scrape (default: 5)
    
    Returns:
        List of apartment dictionaries
    """
    apartments = []
    base_url = "https://www.apartments.com"
    
    # Construct search URL for Montreal
    # Note: Apartments.com uses query parameters for search
    search_url = f"{base_url}/montreal-qc/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    for page in range(1, max_pages + 1):
        try:
            # Construct page URL
            if page == 1:
                url = search_url
            else:
                url = f"{search_url}?page={page}"
            
            print(f"Scraping Apartments.com page {page}...")
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Find apartment listings
            # Note: Apartments.com structure may vary, this is a general approach
            listings = soup.find_all('article', class_='placard') or soup.find_all('div', class_='property')
            
            if not listings:
                # Try alternative selectors
                listings = soup.find_all('li', class_='mortar-wrapper')
            
            if not listings:
                print(f"No listings found on page {page}")
                break
            
            for listing in listings:
                try:
                    apt = parse_listing(listing, base_url)
                    if apt:
                        apartments.append(apt)
                except Exception as e:
                    print(f"Error parsing listing: {e}")
                    continue
            
            # Delay between pages
            delay(2.5)
            
        except requests.RequestException as e:
            print(f"Error fetching page {page}: {e}")
            continue
        except Exception as e:
            print(f"Error processing page {page}: {e}")
            continue
    
    print(f"Scraped {len(apartments)} apartments from Apartments.com")
    return apartments


def parse_listing(listing, base_url: str) -> Optional[Dict]:
    """
    Parse a single listing element into apartment dictionary.
    
    Args:
        listing: BeautifulSoup element containing listing data
        base_url: Base URL for constructing full URLs
    
    Returns:
        Apartment dictionary or None if parsing fails
    """
    try:
        # Extract title
        title_elem = listing.find('a', class_='placardTitle') or listing.find('h2') or listing.find('a', class_='property-link')
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        if not title:
            return None
        
        # Extract URL
        url_elem = listing.find('a', href=True)
        if url_elem:
            url = url_elem['href']
            if url.startswith('/'):
                url = base_url + url
        else:
            url = ""
        
        # Extract price
        price_elem = listing.find('span', class_='propertyRent') or listing.find('p', class_='property-pricing')
        if not price_elem:
            price_elem = listing.find('span', string=re.compile(r'\$'))
        
        price_str = price_elem.get_text(strip=True) if price_elem else ""
        price = clean_price(price_str)
        
        # Extract address
        address_elem = listing.find('div', class_='property-address') or listing.find('address')
        if not address_elem:
            address_elem = listing.find('span', class_='propertyAddress')
        
        address = address_elem.get_text(strip=True) if address_elem else ""
        address = clean_address(address)
        
        # Extract bedrooms and bathrooms
        details_elem = listing.find('span', class_='propertyBed') or listing.find('div', class_='property-beds')
        details_text = details_elem.get_text(strip=True) if details_elem else ""
        
        bedrooms = extract_bedrooms(details_text)
        bathrooms = extract_bathrooms(details_text)
        
        # Extract square footage
        sqft_elem = listing.find('span', class_='propertySqft') or listing.find('div', class_='property-sqft')
        sqft_text = sqft_elem.get_text(strip=True) if sqft_elem else ""
        sqft = extract_sqft(sqft_text)
        
        # Extract image
        img_elem = listing.find('img')
        image_url = img_elem.get('src') or img_elem.get('data-src') if img_elem else ""
        if not image_url:
            image_url = "img/property-1.jpg"  # Default placeholder
        
        # Extract description
        desc_elem = listing.find('p', class_='property-description') or listing.find('div', class_='propertyDescription')
        description = desc_elem.get_text(strip=True) if desc_elem else ""
        
        # Extract amenities (if available)
        amenities = []
        amenities_elem = listing.find('ul', class_='property-amenities') or listing.find('div', class_='amenities')
        if amenities_elem:
            amenity_items = amenities_elem.find_all('li') or amenities_elem.find_all('span')
            amenities = [item.get_text(strip=True) for item in amenity_items if item.get_text(strip=True)]
        
        # Check for furnished, pet-friendly, etc. from description
        desc_lower = description.lower()
        furnished = any(word in desc_lower for word in ['furnished', 'fully furnished', 'furniture included'])
        pet_friendly = any(word in desc_lower for word in ['pet friendly', 'pets allowed', 'pet-friendly'])
        
        # Extract available date if mentioned
        available_date = None
        date_patterns = [
            r'available\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'available\s+(\w+\s+\d{1,2},?\s+\d{4})',
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
            "source": "apartments.com",
            "description": description,
            "amenities": amenities[:5],  # Limit to 5 amenities
            "available_date": available_date,
            "pet_friendly": pet_friendly,
            "furnished": furnished,
            # These will be calculated later by matcher
            "lat": None,
            "lng": None,
            "distance_to_work": None,
            "commute_time": None,
            "match_score": 0
        }
        
        return apartment
        
    except Exception as e:
        print(f"Error parsing listing: {e}")
        return None


if __name__ == "__main__":
    # Test scraper
    print("Testing Apartments.com scraper...")
    apartments = scrape_apartments_com(city="Montreal", max_pages=3)
    
    print(f"\nFound {len(apartments)} apartments")
    if apartments:
        print("\nFirst apartment:")
        print(json.dumps(apartments[0], indent=2))

