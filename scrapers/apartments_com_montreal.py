"""
Scraper for Apartments.com Montreal (furnished listings)
Target: https://www.apartments.com/montreal-qc/furnished/
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


def scrape_apartments_com_montreal(max_pages: int = 5) -> List[Dict]:
    """
    Scrape furnished apartment listings from Apartments.com Montreal.
    
    Args:
        max_pages: Maximum number of pages to scrape (default: 5)
    
    Returns:
        List of apartment dictionaries
    """
    apartments = []
    base_url = "https://www.apartments.com"
    search_url = f"{base_url}/montreal-qc/furnished/"
    
    session = create_session_with_retries()
    
    for page in range(1, max_pages + 1):
        try:
            if page == 1:
                url = search_url
            else:
                url = f"{search_url}?page={page}"
            
            print(f"  Scraping Apartments.com page {page}...")
            
            response = make_request_with_retry(session, url)
            if not response:
                print(f"  Failed to fetch page {page}")
                break
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Apartments.com structure - try multiple selectors
            listings = []
            selectors = [
                ('article', {'class': 'placard'}),
                ('div', {'class': 'property'}),
                ('li', {'class': 'mortar-wrapper'}),
                ('div', {'data-testid': 'property-card'}),
                ('article', {'class': 'propertyCard'}),
            ]
            
            for tag, attrs in selectors:
                listings = soup.find_all(tag, attrs)
                if listings:
                    print(f"    Found {len(listings)} listings using {tag}")
                    break
            
            if not listings:
                print(f"  No listings found on page {page}")
                # Save HTML for debugging
                with open(f"debug_apartments_com_page{page}.html", 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                break
            
            for listing in listings:
                try:
                    apt = parse_apartments_com_listing(listing, base_url)
                    if apt:
                        apartments.append(apt)
                except Exception as e:
                    logger.warning(f"  Error parsing listing: {e}")
                    continue
            
            # Delay between pages
            if page < max_pages:
                page_delay(5.0, 10.0)
            
        except Exception as e:
            logger.error(f"  Error processing page {page}: {e}")
            continue
    
    session.close()
    print(f"  Scraped {len(apartments)} apartments from Apartments.com")
    return apartments


def parse_apartments_com_listing(listing, base_url: str) -> Optional[Dict]:
    """Parse a single Apartments.com listing."""
    try:
        # Extract title and URL
        title_elem = listing.find('a', class_='placardTitle') or \
                    listing.find('h2') or \
                    listing.find('a', {'data-testid': 'property-link'}) or \
                    listing.find('a', href=True)
        
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        if not title:
            return None
        
        url = title_elem.get('href', '')
        if url.startswith('/'):
            url = base_url + url
        
        # Extract price
        price_elem = listing.find('span', class_='propertyRent') or \
                    listing.find('p', class_='property-pricing') or \
                    listing.find('span', class_='rent')
        price_str = price_elem.get_text(strip=True) if price_elem else ""
        price = clean_price(price_str)
        
        # Extract address
        address_elem = listing.find('div', class_='property-address') or \
                      listing.find('address') or \
                      listing.find('span', class_='propertyAddress')
        address = address_elem.get_text(strip=True) if address_elem else ""
        address = clean_address(address)
        if not address:
            address = "Montreal, QC"
        
        # Extract bedrooms, bathrooms
        details_elem = listing.find('span', class_='propertyBed') or \
                      listing.find('div', class_='property-beds') or \
                      listing.find('span', class_='beds')
        details_text = details_elem.get_text(strip=True) if details_elem else ""
        
        bedrooms = extract_bedrooms(details_text)
        bathrooms = extract_bathrooms(details_text)
        
        # Extract sqft
        sqft_elem = listing.find('span', class_='propertySqft') or \
                   listing.find('span', class_='sqft')
        sqft_text = sqft_elem.get_text(strip=True) if sqft_elem else ""
        sqft = extract_sqft(sqft_text)
        
        # Extract image
        img_elem = listing.find('img')
        image_url = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src') if img_elem else ""
        if not image_url:
            image_url = "img/property-1.jpg"
        
        # Extract description
        desc_elem = listing.find('p', class_='property-description') or \
                   listing.find('div', class_='propertyDescription')
        description = desc_elem.get_text(strip=True) if desc_elem else ""
        
        # Check for furnished (this is the furnished section)
        desc_lower = description.lower()
        furnished = True  # All listings in this section are furnished
        
        # Extract amenities
        amenities = []
        amenities_elem = listing.find('ul', class_='property-amenities') or \
                        listing.find('div', class_='amenities')
        if amenities_elem:
            amenity_items = amenities_elem.find_all('li') or amenities_elem.find_all('span')
            amenities = [item.get_text(strip=True) for item in amenity_items if item.get_text(strip=True)]
        
        # Check for in-unit laundry
        in_unit_laundry = (
            'in-unit laundry' in desc_lower or
            'in-suite laundry' in desc_lower or
            any('laundry' in a.lower() and ('in-unit' in a.lower() or 'in-suite' in a.lower()) for a in amenities)
        )
        
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
            "amenities": amenities[:5],
            "available_date": None,
            "pet_friendly": False,
            "furnished": furnished,
            "in_unit_laundry": in_unit_laundry,
            "lat": None,
            "lng": None,
            "distance_to_work": None,
            "commute_time": None,
            "match_score": 0
        }
        
        return apartment
        
    except Exception as e:
        logger.warning(f"  Error parsing listing: {e}")
        return None


if __name__ == "__main__":
    # Test scraper
    print("Testing Apartments.com Montreal scraper...")
    apartments = scrape_apartments_com_montreal(max_pages=2)
    
    print(f"\nFound {len(apartments)} apartments")
    if apartments:
        print("\nFirst apartment:")
        print(json.dumps(apartments[0], indent=2))

