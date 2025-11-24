"""
Scraper for Rent it Furnished (Montreal)
Target: https://rentitfurnished.com/montreal/listings
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


def scrape_rentitfurnished(max_pages: int = 5) -> List[Dict]:
    """
    Scrape furnished apartment listings from Rent it Furnished Montreal.
    
    Args:
        max_pages: Maximum number of pages to scrape (default: 5)
    
    Returns:
        List of apartment dictionaries
    """
    apartments = []
    base_url = "https://rentitfurnished.com"
    search_url = f"{base_url}/montreal/listings"
    
    session = create_session_with_retries()
    
    for page in range(1, max_pages + 1):
        try:
            if page == 1:
                url = search_url
            else:
                url = f"{search_url}?page={page}"
            
            print(f"  Scraping Rent it Furnished page {page}...")
            
            response = make_request_with_retry(session, url)
            if not response:
                print(f"  Failed to fetch page {page}")
                break
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Try multiple selectors for Rent it Furnished
            listings = []
            selectors = [
                ('div', {'class': 'listing'}),
                ('article', {'class': 'property'}),
                ('div', {'class': 'property-card'}),
                ('div', {'class': 'listing-card'}),
            ]
            
            for tag, attrs in selectors:
                listings = soup.find_all(tag, attrs)
                if listings:
                    print(f"    Found {len(listings)} listings using {tag}")
                    break
            
            if not listings:
                # Try finding any divs with listing-like content
                all_divs = soup.find_all('div', class_=True)
                listings = [d for d in all_divs if any(x in str(d.get('class', [])).lower() for x in ['listing', 'property', 'card'])]
                if listings:
                    print(f"    Found {len(listings)} potential listings")
            
            if not listings:
                print(f"  No listings found on page {page}")
                # Save HTML for debugging
                with open(f"debug_rentitfurnished_page{page}.html", 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                break
            
            for listing in listings:
                try:
                    apt = parse_rentitfurnished_listing(listing, base_url)
                    if apt:
                        apartments.append(apt)
                except Exception as e:
                    print(f"  Error parsing listing: {e}")
                    continue
            
            # Delay between pages
            if page < max_pages:
                page_delay(5.0, 10.0)
            
        except Exception as e:
            logger.error(f"  Error processing page {page}: {e}")
            continue
    
    session.close()
    print(f"  Scraped {len(apartments)} apartments from Rent it Furnished")
    return apartments


def parse_rentitfurnished_listing(listing, base_url: str) -> Optional[Dict]:
    """
    Parse a single Rent it Furnished listing.
    
    Args:
        listing: BeautifulSoup element containing listing data
        base_url: Base URL for constructing full URLs
    
    Returns:
        Apartment dictionary or None if parsing fails
    """
    try:
        # Extract title
        title_elem = listing.find('h2') or listing.find('h3') or listing.find('a', class_='title')
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
        price_elem = listing.find('span', class_='price') or listing.find('div', class_='price')
        price_str = price_elem.get_text(strip=True) if price_elem else ""
        price = clean_price(price_str)
        
        # Extract address
        address_elem = listing.find('div', class_='address') or listing.find('span', class_='location')
        address = address_elem.get_text(strip=True) if address_elem else ""
        address = clean_address(address)
        if not address:
            address = "Montreal, QC"
        
        # Extract description
        desc_elem = listing.find('div', class_='description') or listing.find('p', class_='description')
        description = desc_elem.get_text(strip=True) if desc_elem else ""
        
        # Extract bedrooms, bathrooms, sqft from description or title
        details_text = (title + " " + description).lower()
        
        bedrooms = extract_bedrooms(details_text)
        bathrooms = extract_bathrooms(details_text)
        sqft = extract_sqft(details_text)
        
        # Extract image
        img_elem = listing.find('img')
        image_url = img_elem.get('src') or img_elem.get('data-src') if img_elem else ""
        if not image_url:
            image_url = "img/property-1.jpg"
        
        # Rent it Furnished specializes in furnished apartments
        furnished = True  # All listings on this site are furnished
        
        # Check for amenities
        amenities = []
        desc_lower = description.lower()
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
        
        # Check for in-unit laundry
        in_unit_laundry = 'in-unit laundry' in desc_lower or 'in-suite laundry' in desc_lower
        
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
            "source": "rentitfurnished",
            "description": description,
            "amenities": amenities[:5],
            "available_date": available_date,
            "pet_friendly": False,  # Default, may need to check
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
        print(f"  Error parsing Rent it Furnished listing: {e}")
        return None


if __name__ == "__main__":
    # Test scraper
    print("Testing Rent it Furnished scraper...")
    apartments = scrape_rentitfurnished(max_pages=2)
    
    print(f"\nFound {len(apartments)} apartments")
    if apartments:
        print("\nFirst apartment:")
        print(json.dumps(apartments[0], indent=2))

