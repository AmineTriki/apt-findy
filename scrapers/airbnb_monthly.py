"""
Scraper for Airbnb Monthly Rentals (Montreal)
Target: https://www.airbnb.ca/s/Montreal--QC/homes (filter 30+ days)
Note: Airbnb uses heavy JavaScript, may need Selenium for full functionality
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import json
import re
from scraper_utils import delay, clean_price, clean_address, extract_bedrooms, extract_bathrooms, extract_sqft


def scrape_airbnb_monthly(max_pages: int = 3) -> List[Dict]:
    """
    Scrape monthly rental listings from Airbnb Montreal.
    
    Note: Airbnb heavily uses JavaScript, so this basic scraper may have limited results.
    For full functionality, consider using Selenium.
    
    Args:
        max_pages: Maximum number of pages to scrape (default: 3)
    
    Returns:
        List of apartment dictionaries
    """
    apartments = []
    base_url = "https://www.airbnb.ca"
    # Airbnb search URL with monthly filter (30+ days)
    search_url = f"{base_url}/s/Montreal--QC/homes?refinement_paths%5B%5D=%2Fhomes&search_type=filter_change&tab_id=home_tab&flexible_trip_lengths%5B%5D=monthly&monthly_start_date=2026-01-01&monthly_end_date=2026-02-15"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-CA,en;q=0.9,fr-CA;q=0.8,fr;q=0.7',
    }
    
    for page in range(1, max_pages + 1):
        try:
            if page == 1:
                url = search_url
            else:
                # Airbnb pagination
                url = f"{search_url}&items_offset={page * 20}"
            
            print(f"  Scraping page {page}...")
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Airbnb uses various class names - may need to inspect actual HTML
            listings = soup.find_all('div', {'data-testid': 'card-container'}) or \
                      soup.find_all('div', class_='_1e4zi4s') or \
                      soup.find_all('div', class_='c1l1h97y')
            
            if not listings:
                print(f"  No listings found on page {page} (Airbnb may require JavaScript)")
                # Airbnb likely requires JavaScript, so break early
                break
            
            for listing in listings:
                try:
                    apt = parse_airbnb_listing(listing, base_url)
                    if apt:
                        apartments.append(apt)
                except Exception as e:
                    print(f"  Error parsing listing: {e}")
                    continue
            
            delay(3.0)  # Be careful with Airbnb
            
        except requests.RequestException as e:
            print(f"  Error fetching page {page}: {e}")
            continue
        except Exception as e:
            print(f"  Error processing page {page}: {e}")
            continue
    
    print(f"  Scraped {len(apartments)} apartments from Airbnb Monthly")
    if len(apartments) == 0:
        print("  Note: Airbnb uses heavy JavaScript. Consider using Selenium for better results.")
    return apartments


def parse_airbnb_listing(listing, base_url: str) -> Optional[Dict]:
    """
    Parse a single Airbnb listing.
    
    Args:
        listing: BeautifulSoup element containing listing data
        base_url: Base URL for constructing full URLs
    
    Returns:
        Apartment dictionary or None if parsing fails
    """
    try:
        # Extract title
        title_elem = listing.find('div', {'data-testid': 'listing-card-title'}) or \
                    listing.find('span', class_='_1y6fhhr') or \
                    listing.find('div', class_='title')
        
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
        
        # Extract price - Airbnb shows monthly price for monthly rentals
        price_elem = listing.find('span', {'data-testid': 'price'}) or \
                    listing.find('span', class_='_1y6fhhr')
        price_str = price_elem.get_text(strip=True) if price_elem else ""
        price = clean_price(price_str)
        
        # Extract address (may be limited without JavaScript)
        address = "Montreal, QC"  # Default, Airbnb may not show full address in listing
        
        # Extract bedrooms, bathrooms from title or description
        details_text = title.lower()
        bedrooms = extract_bedrooms(details_text)
        bathrooms = extract_bathrooms(details_text)
        sqft = extract_sqft(details_text)
        
        # Extract image
        img_elem = listing.find('img')
        image_url = img_elem.get('src') or img_elem.get('data-src') if img_elem else ""
        if not image_url:
            image_url = "img/property-1.jpg"
        
        # Airbnb monthly rentals are typically furnished
        furnished = True  # Most Airbnb monthly rentals are furnished
        
        # Default amenities (Airbnb listings typically have these)
        amenities = ['Furnished', 'WiFi', 'Kitchen']
        
        # Extract available date (may be in URL or description)
        available_date = None
        
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
            "source": "airbnb_monthly",
            "description": f"Airbnb monthly rental: {title}",
            "amenities": amenities,
            "available_date": available_date,
            "pet_friendly": False,  # Default
            "furnished": furnished,
            "in_unit_laundry": False,  # Default, may need to check
            # These will be calculated later
            "lat": None,
            "lng": None,
            "distance_to_work": None,
            "commute_time": None,
            "match_score": 0
        }
        
        return apartment
        
    except Exception as e:
        print(f"  Error parsing Airbnb listing: {e}")
        return None


if __name__ == "__main__":
    # Test scraper
    print("Testing Airbnb Monthly scraper...")
    print("Note: Airbnb uses heavy JavaScript, results may be limited")
    apartments = scrape_airbnb_monthly(max_pages=2)
    
    print(f"\nFound {len(apartments)} apartments")
    if apartments:
        print("\nFirst apartment:")
        print(json.dumps(apartments[0], indent=2))

