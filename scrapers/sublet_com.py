"""
Scraper for Sublet.com Montreal
Target: https://www.sublet.com/apartments-for-rent/montreal/
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


def scrape_sublet_com(max_pages: int = 5) -> List[Dict]:
    """
    Scrape apartment listings from Sublet.com Montreal.
    
    Args:
        max_pages: Maximum number of pages to scrape (default: 5)
    
    Returns:
        List of apartment dictionaries
    """
    apartments = []
    base_url = "https://www.sublet.com"
    search_url = f"{base_url}/apartments-for-rent/montreal/"
    
    session = create_session_with_retries()
    
    for page in range(1, max_pages + 1):
        try:
            if page == 1:
                url = search_url
            else:
                url = f"{search_url}?page={page}"
            
            print(f"  Scraping Sublet.com page {page}...")
            
            response = make_request_with_retry(session, url)
            if not response:
                print(f"  Failed to fetch page {page}")
                break
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Sublet.com structure - uses rental-item class
            listings = soup.find_all('div', class_='rental-item')
            
            if listings:
                print(f"    Found {len(listings)} listings using rental-item")
            
            if not listings:
                print(f"  No listings found on page {page}")
                # Save HTML for debugging
                with open(f"debug_sublet_page{page}.html", 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                break
            
            for listing in listings:
                try:
                    apt = parse_sublet_listing(listing, base_url)
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
    print(f"  Scraped {len(apartments)} apartments from Sublet.com")
    return apartments


def parse_sublet_listing(listing, base_url: str) -> Optional[Dict]:
    """Parse a single Sublet.com listing."""
    try:
        # Extract URL from data-href attribute
        url = listing.get('data-href', '')
        if not url:
            url_elem = listing.find('a', href=True)
            if url_elem:
                url = url_elem.get('href', '')
        
        if not url:
            return None
        
        if url.startswith('/'):
            url = base_url + url
        
        # Extract title from supply-details-listing
        title = "Apartment in Montreal"
        title_elem = listing.find('div', class_='supply-details-listing')
        if title_elem:
            title_link = title_elem.find('a', class_='supply-details-link')
            if title_link:
                title = title_link.get_text(strip=True)
            else:
                # Try to get text from the div
                title = title_elem.get_text(strip=True)
        
        if not title or title == "":
            return None
        
        # Extract price - format is: <span class="js-currency">$</span>2101/month
        price = None
        price_elem = listing.find('div', class_='supply-details-listing')
        if price_elem:
            # Look for currency span followed by price text
            currency_span = price_elem.find('span', class_='js-currency')
            if currency_span:
                # Get the parent div and extract all text
                parent_div = currency_span.find_parent('div', class_='font14')
                if parent_div:
                    price_text = parent_div.get_text(strip=True)
                    # Extract price pattern like "$2101/month" or "2101/month" - match full number
                    price_match = re.search(r'[\$]?\s*(\d{3,5})/month', price_text)
                    if price_match:
                        price_str = price_match.group(1)
                        price = int(price_str) if price_str.isdigit() else None
        
        # If still no price, try finding any amount in the listing text
        if not price:
            all_text = listing.get_text()
            price_match = re.search(r'[\$]?\s*(\d{3,5})/month', all_text)
            if price_match:
                price_str = price_match.group(1)
                price = int(price_str) if price_str.isdigit() else None
        
        # Extract address - may be in data attributes or text
        address = listing.get('data-city', '') + ", " + listing.get('data-state', '')
        if address == ", ":
            address_elem = listing.find('div', class_='address') or listing.find('span', class_='location')
            address = address_elem.get_text(strip=True) if address_elem else ""
        
        address = clean_address(address)
        if not address or address == ", ":
            address = "Montreal, QC"
        
        # Extract description
        desc_elem = listing.find('div', class_='description')
        description = desc_elem.get_text(strip=True) if desc_elem else ""
        
        # Extract bedrooms and bathrooms from details section
        bedrooms = None
        bathrooms = None
        details_section = listing.find('div', class_='details-section')
        if details_section:
            # Look for bed icon and text - format: "1 Room" or "2 Rooms"
            bed_spans = details_section.find_all('span', title=re.compile(r'Bed', re.I))
            for bed_span in bed_spans:
                bed_text = bed_span.get_text(strip=True)
                # Extract number from "1 Room" or "2 Rooms"
                room_match = re.search(r'(\d+)\s*Room', bed_text, re.I)
                if room_match:
                    bedrooms = int(room_match.group(1))
                    break
                # Try extract_bedrooms as fallback
                if not bedrooms:
                    bedrooms = extract_bedrooms(bed_text)
            
            # Look for bath icon and text
            bath_spans = details_section.find_all('span', title=re.compile(r'bath', re.I))
            for bath_span in bath_spans:
                bath_text = bath_span.get_text(strip=True)
                bathrooms = extract_bathrooms(bath_text)
                if bathrooms:
                    break
        
        # Fallback to text extraction if not found
        if not bedrooms or not bathrooms:
            details_text = (title + " " + description).lower()
            if not bedrooms:
                bedrooms = extract_bedrooms(details_text)
            if not bathrooms:
                bathrooms = extract_bathrooms(details_text)
        
        sqft = extract_sqft((title + " " + description).lower())
        
        # Extract image from carousel
        image_url = "img/property-1.jpg"
        carousel_item = listing.find('div', class_='carousel-item')
        if carousel_item:
            image_url = carousel_item.get('data-bgimage', '')
            if not image_url:
                # Try style attribute
                style = carousel_item.get('style', '')
                bg_match = re.search(r'background-image:\s*url\([\'"]?([^\'"]+)[\'"]?\)', style)
                if bg_match:
                    image_url = bg_match.group(1)
        
        # Prepare text for searching
        desc_lower = (title + " " + description).lower()
        
        # Check for furnished - look for "Furnished Rental" text
        furnished = False
        details_section = listing.find('div', class_='details-section')
        if details_section:
            furnished_text = details_section.get_text()
            if 'furnished' in furnished_text.lower():
                furnished = True
        
        # Fallback to text search
        if not furnished:
            furnished = any(word in desc_lower for word in ['furnished', 'fully furnished', 'furniture', 'meublé'])
        
        # Extract amenities
        amenities = []
        amenity_keywords = {
            'gym': 'Gym', 'fitness': 'Gym',
            'parking': 'Parking',
            'laundry': 'Laundry',
            'dishwasher': 'Dishwasher',
            'balcony': 'Balcony', 'terrace': 'Balcony',
            'pool': 'Pool',
        }
        
        for keyword, amenity_name in amenity_keywords.items():
            if keyword in desc_lower and amenity_name not in amenities:
                amenities.append(amenity_name)
        
        # Check for in-unit laundry
        in_unit_laundry = (
            'in-unit laundry' in desc_lower or
            'in-suite laundry' in desc_lower
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
            "source": "sublet.com",
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
    print("Testing Sublet.com scraper...")
    apartments = scrape_sublet_com(max_pages=2)
    
    print(f"\nFound {len(apartments)} apartments")
    if apartments:
        print("\nFirst apartment:")
        print(json.dumps(apartments[0], indent=2))

