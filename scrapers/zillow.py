"""
Scraper for Zillow (rentals)
Note: Zillow uses heavy JavaScript, may need Selenium for full functionality
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import json
import re
from scraper_utils import delay, clean_price, clean_address, extract_bedrooms, extract_bathrooms, extract_sqft


def scrape_zillow(city: str = "Montreal", state: str = "QC", max_pages: int = 3) -> List[Dict]:
    """
    Scrape rental listings from Zillow.
    
    Note: Zillow heavily uses JavaScript, so this basic scraper may have limited results.
    For full functionality, consider using Selenium.
    
    Args:
        city: City name (default: "Montreal")
        state: State/province code (default: "QC")
        max_pages: Maximum number of pages to scrape (default: 3)
    
    Returns:
        List of apartment dictionaries
    """
    apartments = []
    base_url = "https://www.zillow.com"
    
    # Zillow rental search URL
    # Note: Zillow's URL structure may vary
    search_url = f"{base_url}/homes/{city}-{state}_rb/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    for page in range(1, max_pages + 1):
        try:
            if page == 1:
                url = search_url
            else:
                url = f"{search_url}{page}_p/"
            
            print(f"Scraping Zillow page {page}...")
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Zillow uses various class names for listings
            listings = soup.find_all('article', {'data-test': 'property-card'}) or \
                      soup.find_all('div', class_='property-card') or \
                      soup.find_all('li', class_='ListItem-c11n-8-84-3__sc-10e22w8-0')
            
            if not listings:
                print(f"No listings found on page {page}")
                # Zillow may require JavaScript, so break early
                break
            
            for listing in listings:
                try:
                    apt = parse_zillow_listing(listing, base_url)
                    if apt:
                        apartments.append(apt)
                except Exception as e:
                    print(f"Error parsing listing: {e}")
                    continue
            
            delay(3.0)  # Be careful with Zillow
            
        except requests.RequestException as e:
            print(f"Error fetching page {page}: {e}")
            continue
        except Exception as e:
            print(f"Error processing page {page}: {e}")
            continue
    
    print(f"Scraped {len(apartments)} apartments from Zillow")
    return apartments


def parse_zillow_listing(listing, base_url: str) -> Optional[Dict]:
    """
    Parse a single Zillow listing.
    
    Args:
        listing: BeautifulSoup element containing listing data
        base_url: Base URL for constructing full URLs
    
    Returns:
        Apartment dictionary or None if parsing fails
    """
    try:
        # Extract title/address
        title_elem = listing.find('a', {'data-test': 'property-card-link'}) or \
                    listing.find('a', class_='property-card-link') or \
                    listing.find('h3')
        
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
        price_elem = listing.find('span', {'data-test': 'property-card-price'}) or \
                    listing.find('span', class_='PropertyCardWrapper__StyledPriceLine')
        
        price_str = price_elem.get_text(strip=True) if price_elem else ""
        price = clean_price(price_str)
        
        # Extract address
        address_elem = listing.find('address') or listing.find('div', class_='property-address')
        address = address_elem.get_text(strip=True) if address_elem else title
        address = clean_address(address)
        
        # Extract bedrooms, bathrooms, sqft
        details_elem = listing.find('ul', class_='PropertyCardWrapper__StyledPropertyCardDetails') or \
                      listing.find('div', class_='property-details')
        
        details_text = details_elem.get_text(strip=True) if details_elem else ""
        
        bedrooms = extract_bedrooms(details_text)
        bathrooms = extract_bathrooms(details_text)
        sqft = extract_sqft(details_text)
        
        # Extract image
        img_elem = listing.find('img')
        image_url = img_elem.get('src') or img_elem.get('data-src') if img_elem else ""
        if not image_url:
            image_url = "img/property-1.jpg"
        
        # Extract description (may not be available without visiting detail page)
        description = ""
        
        # Check for amenities in description or details
        amenities = []
        desc_lower = (details_text + " " + description).lower()
        
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
        
        # Default assumptions (Zillow may not show these in listing preview)
        furnished = False
        pet_friendly = False
        
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
            "source": "zillow",
            "description": description,
            "amenities": amenities[:5],
            "available_date": None,
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
        print(f"Error parsing Zillow listing: {e}")
        return None


if __name__ == "__main__":
    # Test scraper
    print("Testing Zillow scraper...")
    print("Note: Zillow uses heavy JavaScript, results may be limited")
    apartments = scrape_zillow(city="Montreal", state="QC", max_pages=2)
    
    print(f"\nFound {len(apartments)} apartments")
    if apartments:
        print("\nFirst apartment:")
        print(json.dumps(apartments[0], indent=2))

