"""
Scraper for Apartments.com Montreal (furnished listings)
Target: https://www.apartments.com/montreal-qc/furnished/
Fixed timeout issues with longer delays and better headers
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import json
import re
import time
import random
from scraper_utils import clean_price, clean_address, extract_bedrooms, extract_bathrooms, extract_sqft
import logging

logger = logging.getLogger(__name__)


def get_headers():
    """Return realistic browser headers"""
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }


def extract_price_apartments_com(text):
    """Extract first price number from text like '$1,299 - $2,839' or '$1,500'"""
    if not text:
        return None
    match = re.search(r'\$?([\d,]+)', text.replace(',', ''))
    if match:
        try:
            return int(match.group(1))
        except:
            return None
    return None


def extract_bedrooms_apartments_com(text):
    """Extract bedroom count from 'Studio', '1 Bed', '2 Beds', etc."""
    if not text:
        return None
    text = text.lower()
    if 'studio' in text:
        return 0
    match = re.search(r'(\d+)\s*bed', text)
    if match:
        return int(match.group(1))
    return None


def extract_bathrooms_apartments_com(text):
    """Extract bathroom count from '1 Bath', '1.5 Baths', etc."""
    if not text:
        return None
    match = re.search(r'([\d.]+)\s*bath', text.lower())
    if match:
        return float(match.group(1))
    return None


def scrape_apartments_com_montreal(max_pages: int = 2) -> List[Dict]:
    """
    Scrape Apartments.com Montreal furnished listings
    Limited to 2 pages to avoid timeouts
    
    Args:
        max_pages: Maximum number of pages to scrape (default: 2)
    
    Returns:
        List of apartment dictionaries
    """
    apartments = []
    session = requests.Session()
    
    base_url = "https://www.apartments.com/montreal-qc/furnished/"
    
    print(f"Scraping Apartments.com Montreal (furnished)...")
    print("NOTE: Using longer timeouts and delays to avoid blocking")
    
    for page in range(1, max_pages + 1):
        try:
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}{page}/"
            
            print(f"  Fetching page {page}... (may take 30-60 seconds)")
            
            response = session.get(
                url, 
                headers=get_headers(),
                timeout=45,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                print(f"  Failed with status {response.status_code}")
                if response.status_code == 403:
                    print("  Site is blocking us. Try again later or use Selenium.")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple selectors for listings
            listings = soup.find_all('article', class_='placard')
            if not listings:
                listings = soup.find_all('li', class_='mortar-wrapper')
            if not listings:
                listings = soup.find_all('div', attrs={'data-listingid': True})
            if not listings:
                # Try finding any article or listing-like elements
                listings = soup.find_all('article') or soup.find_all('li', class_=re.compile(r'listing|property|placard', re.I))
            
            print(f"  Found {len(listings)} listings on page {page}")
            
            if not listings:
                print("  No listings found. Site may be blocking or structure changed.")
                # Save debug HTML
                try:
                    import os
                    os.makedirs('debug_html', exist_ok=True)
                    with open('debug_html/apartments_com_debug.html', 'w', encoding='utf-8') as f:
                        f.write(soup.prettify())
                    print("  Saved HTML to debug_html/apartments_com_debug.html for inspection")
                except Exception as e:
                    logger.warning(f"  Could not save debug HTML: {e}")
                # Check if page loaded correctly
                if len(soup.get_text()) < 1000:
                    print("  ⚠️ Page content seems empty - likely blocked or JavaScript-rendered")
                    print("  Skipping Apartments.com (requires Selenium)")
                    return apartments
                break
            
            for idx, listing in enumerate(listings):
                try:
                    apartment = {}
                    
                    title_elem = (
                        listing.find('span', class_='js-placardTitle') or
                        listing.find('a', class_='property-link') or
                        listing.find('div', class_='property-title')
                    )
                    apartment['title'] = title_elem.text.strip() if title_elem else None
                    
                    link_elem = listing.find('a', class_='property-link') or listing.find('a', href=True)
                    if link_elem and link_elem.get('href'):
                        href = link_elem['href']
                        apartment['url'] = f"https://www.apartments.com{href}" if href.startswith('/') else href
                    else:
                        apartment['url'] = None
                    
                    # Try multiple selectors for price
                    price_elem = (
                        listing.find('p', class_='property-pricing') or
                        listing.find('span', class_='rentInfoDetail') or
                        listing.find('p', class_='price-range') or
                        listing.find('span', class_='priceRange') or
                        listing.find('p', attrs={'data-tid': 'property-pricing'}) or
                        listing.find('span', class_=re.compile(r'price|rent', re.I)) or
                        listing.find('div', class_=re.compile(r'price|rent', re.I))
                    )
                    price_text = price_elem.text.strip() if price_elem else None
                    # Also search in all text if not found
                    if not price_text:
                        all_text = listing.get_text()
                        price_match = re.search(r'\$[\d,]+', all_text)
                        if price_match:
                            price_text = price_match.group()
                    apartment['price'] = extract_price_apartments_com(price_text) or clean_price(price_text)
                    
                    # Try multiple selectors for bedrooms/bathrooms
                    details_elem = (
                        listing.find('p', class_='property-beds') or
                        listing.find('span', class_='detailsTextWrapper') or
                        listing.find('p', class_='bed-range') or
                        listing.find('span', class_=re.compile(r'bed', re.I)) or
                        listing.find('div', class_=re.compile(r'bed', re.I))
                    )
                    details_text = details_elem.text.strip() if details_elem else ""
                    # Also try extracting from title and all text
                    if not details_text or (not apartment.get('bedrooms') and not apartment.get('bathrooms')):
                        all_text = listing.get_text()
                        details_text = details_text + " " + all_text
                    
                    apartment['bedrooms'] = extract_bedrooms_apartments_com(details_text) or extract_bedrooms(details_text) or extract_bedrooms(apartment.get('title', ''))
                    apartment['bathrooms'] = extract_bathrooms_apartments_com(details_text) or extract_bathrooms(details_text) or extract_bathrooms(apartment.get('title', '')) or 1.0
                    
                    address_elem = (
                        listing.find('div', class_='property-address') or
                        listing.find('span', class_='property-address') or
                        listing.find('p', class_='property-address')
                    )
                    apartment['address'] = address_elem.text.strip() if address_elem else None
                    
                    if apartment['address'] and 'montreal' not in apartment['address'].lower():
                        apartment['address'] = f"{apartment['address']}, Montreal, QC"
                    
                    apartment['address'] = clean_address(apartment['address'] or "Montreal, QC")
                    
                    img_elem = listing.find('img', class_='img-responsive') or listing.find('img')
                    if img_elem:
                        img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy')
                        apartment['images'] = [img_src] if img_src else ['img/property-1.jpg']
                    else:
                        apartment['images'] = ['img/property-1.jpg']
                    
                    # Extract description
                    desc_elem = listing.find('p', class_='property-description')
                    apartment['description'] = desc_elem.text.strip() if desc_elem else ""
                    
                    # Extract amenities
                    amenities = []
                    amenities_elem = listing.find('ul', class_='property-amenities')
                    if amenities_elem:
                        amenity_items = amenities_elem.find_all('li')
                        amenities = [item.get_text(strip=True) for item in amenity_items if item.get_text(strip=True)]
                    
                    # Check for in-unit laundry
                    desc_lower = apartment['description'].lower()
                    in_unit_laundry = (
                        'in-unit laundry' in desc_lower or
                        'in-suite laundry' in desc_lower or
                        any('laundry' in a.lower() and ('in-unit' in a.lower() or 'in-suite' in a.lower()) for a in amenities)
                    )
                    
                    apartment['furnished'] = True
                    apartment['source'] = 'apartments.com'
                    apartment['city'] = 'Montreal'
                    apartment['sqft'] = extract_sqft(apartment['description'])
                    apartment['amenities'] = amenities[:5]
                    apartment['available_date'] = None
                    apartment['pet_friendly'] = False
                    apartment['in_unit_laundry'] = in_unit_laundry
                    apartment['lat'] = None
                    apartment['lng'] = None
                    apartment['distance_to_work'] = None
                    apartment['commute_time'] = None
                    apartment['match_score'] = 0
                    
                    if apartment.get('title') and apartment.get('url'):
                        apartments.append(apartment)
                        if idx < 3:
                            print(f"    ✓ {apartment['title'][:50]}... - ${apartment.get('price', 'N/A')}")
                    
                except Exception as e:
                    logger.warning(f"    Error parsing listing: {e}")
                    continue
            
            if page < max_pages:
                delay = random.uniform(8, 15)
                print(f"  Waiting {delay:.1f}s before next page...")
                time.sleep(delay)
            
        except requests.Timeout:
            print(f"  ⚠️ Timeout on page {page}. Site is too slow or blocking.")
            print(f"  Collected {len(apartments)} apartments so far. Skipping Apartments.com.")
            # Don't break - continue to next scraper
            return apartments
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️ Request error on page {page}: {e}")
            print(f"  Collected {len(apartments)} apartments so far. Skipping Apartments.com.")
            return apartments
        except Exception as e:
            logger.error(f"  Error on page {page}: {e}")
            # Continue to try next page, but if it's a critical error, return what we have
            if "blocked" in str(e).lower() or "403" in str(e) or "406" in str(e):
                print(f"  Site appears to be blocking us. Skipping Apartments.com.")
                return apartments
            continue
    
    session.close()
    print(f"\n✓ Scraped {len(apartments)} apartments from Apartments.com")
    return apartments


if __name__ == "__main__":
    results = scrape_apartments_com_montreal(max_pages=2)
    print(f"\nTotal apartments scraped: {len(results)}")
    
    if results:
        print("\nSample apartment:")
        print(json.dumps(results[0], indent=2))
    else:
        print("\nNo results. Check debug_html/apartments_com_debug.html if it was created.")
