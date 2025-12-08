"""
Scraper for Rent it Furnished (Montreal)
Target: https://rentitfurnished.com/montreal/listings
Uses Selenium for JavaScript-rendered content
"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time
import json
import re
from scraper_utils import (
    clean_price, clean_address, extract_bedrooms, extract_bathrooms, extract_sqft
)
import logging

logger = logging.getLogger(__name__)


def extract_price_rentit(text):
    """Extract price from text like '$2,100/month' or '$2100'"""
    if not text:
        return None
    match = re.search(r'\$?([\d,]+)', text.replace(',', ''))
    if match:
        try:
            return int(match.group(1))
        except:
            return None
    return None


def extract_bedrooms_rentit(text):
    """Extract bedrooms from text like '2 Bedroom' or '1BR'"""
    if not text:
        return None
    text = text.lower()
    if 'studio' in text:
        return 0
    match = re.search(r'(\d+)\s*(bed|br)', text)
    if match:
        return int(match.group(1))
    return None


def scrape_rentitfurnished(max_pages: int = 1) -> List[Dict]:
    """
    Scrape furnished apartment listings from Rent it Furnished Montreal using Selenium.
    
    Note: This site uses JavaScript rendering, so Selenium is required.
    Only scrapes 1 page (max_pages parameter ignored) due to single-page React app.
    
    Args:
        max_pages: Ignored - always scrapes first page only (default: 1)
    
    Returns:
        List of apartment dictionaries
    """
    apartments = []
    
    print("Setting up Selenium browser...")
    
    # Setup undetected Chrome options
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    
    driver = None
    
    try:
        print("Starting Chrome driver...")
        driver = None
        
        # Strategy 1: Try undetected_chromedriver with auto-version detection
        try:
            driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)
            driver.set_page_load_timeout(60)
            print("  ✓ Chrome started with undetected_chromedriver")
        except Exception as uc_error:
            error_str = str(uc_error)
            print(f"  ⚠️ undetected_chromedriver failed: {error_str[:150]}")
            
            # Strategy 2: Try WebDriverManager as fallback (auto-downloads matching ChromeDriver)
            try:
                print("  Attempting WebDriverManager fallback...")
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.options import Options as ChromeOptions
                
                # Create Chrome options
                chrome_options = ChromeOptions()
                chrome_options.add_argument('--headless=new')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_argument('--window-size=1920,1080')
                
                # Use WebDriverManager to auto-download matching ChromeDriver
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.set_page_load_timeout(60)
                print("  ✓ Chrome started with WebDriverManager")
            except Exception as wdm_error:
                print(f"  ⚠️ WebDriverManager failed: {str(wdm_error)[:150]}")
                
                # Strategy 3: Try forcing undetected_chromedriver to download new version
                try:
                    print("  Attempting to force ChromeDriver download...")
                    import os
                    import shutil
                    # Clear any cached ChromeDriver
                    cache_dir = os.path.expanduser("~/.undetected_chromedriver")
                    if os.path.exists(cache_dir):
                        try:
                            shutil.rmtree(cache_dir)
                            print("  Cleared ChromeDriver cache")
                        except:
                            pass
                    
                    # Try again with fresh download
                    driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)
                    driver.set_page_load_timeout(60)
                    print("  ✓ Chrome started after cache clear")
                except Exception as final_error:
                    print(f"  ✗ All Chrome startup methods failed: {str(final_error)[:150]}")
                    print("  Skipping Rent it Furnished (Chrome/Selenium unavailable)")
                    return []
        
        if not driver:
            print("  ✗ Could not start Chrome driver")
            return []
        
        url = "https://rentitfurnished.com/montreal/listings"
        print(f"Loading {url}...")
        driver.get(url)
        
        # Wait for page to load - try multiple possible selectors
        print("Waiting for listings to load...")
        try:
            # Wait up to 20 seconds for listings to appear
            WebDriverWait(driver, 20).until(
                lambda d: d.find_elements(By.CLASS_NAME, "listing-card") or
                         d.find_elements(By.CLASS_NAME, "property-card") or
                         d.find_elements(By.CLASS_NAME, "rental-listing") or
                         len(d.find_elements(By.TAG_NAME, "article")) > 0
            )
            print("Listings loaded!")
        except:
            print("Timeout waiting for listings. Trying anyway...")
        
        # Extra wait for JavaScript to finish
        time.sleep(5)
        
        # Scroll to load more listings (many React sites use lazy loading)
        print("Scrolling to load more listings...")
        for i in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        # Get page source after JavaScript renders
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Save HTML for debugging
        try:
            with open('debug_html/rentitfurnished_selenium.html', 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            print("Saved HTML to debug_html/rentitfurnished_selenium.html for inspection")
        except:
            pass
        
        # Find listing containers using correct CSS class
        listing_containers = soup.find_all('div', class_=re.compile(r'PropertyCard_property-card__', re.I))
        
        print(f"Found {len(listing_containers)} listings")
        
        if not listing_containers:
            print("\nDEBUG: No listings found with PropertyCard selector.")
            print("HTML structure sample (first 2000 chars):")
            print(soup.prettify()[:2000])
            print("\nPlease inspect debug_html/rentitfurnished_selenium.html to find correct selectors")
            return apartments
        
        for listing in listing_containers[:50]:  # Limit to 50 per page
            try:
                apartment = {}
                
                # Extract title and URL from h2 > a
                title_elem = listing.find('h2', class_=re.compile(r'PropertyCard_property-card--title__', re.I))
                if title_elem:
                    title_link = title_elem.find('a', href=True)
                    if title_link:
                        apartment['title'] = title_link.text.strip()
                        href = title_link.get('href', '')
                        apartment['url'] = f"https://rentitfurnished.com{href}" if href.startswith('/') else href
                    else:
                        apartment['title'] = title_elem.text.strip()
                        apartment['url'] = None
                else:
                    apartment['title'] = None
                    apartment['url'] = None
                
                # Extract price from h3 > a
                price_elem = listing.find('h3', class_=re.compile(r'PropertyCard_property-card--price__', re.I))
                if price_elem:
                    price_link = price_elem.find('a')
                    if price_link:
                        price_text = price_link.text.strip()
                        # Handle format like "$4,350 - Immediately"
                        apartment['price'] = extract_price_rentit(price_text) or clean_price(price_text)
                    else:
                        price_text = price_elem.text.strip()
                        apartment['price'] = extract_price_rentit(price_text) or clean_price(price_text)
                else:
                    apartment['price'] = None
                
                # Extract address
                address_elem = listing.find('div', class_=re.compile(r'PropertyCard_property-card--address__', re.I))
                apartment['address'] = address_elem.text.strip() if address_elem else "Montreal, QC"
                apartment['address'] = clean_address(apartment['address'])
                
                # Extract bedrooms, bathrooms, sqft from subtitle ul > li
                subtitle_elem = listing.find('div', class_=re.compile(r'PropertyCard_property-card--subtitle__', re.I))
                apartment['bedrooms'] = None
                apartment['bathrooms'] = None
                apartment['sqft'] = None
                
                if subtitle_elem:
                    list_items = subtitle_elem.find_all('li')
                    for li in list_items:
                        text = li.text.strip()
                        text_lower = text.lower()
                        # Extract bedrooms
                        if 'bed' in text_lower and apartment['bedrooms'] is None:
                            bed_match = re.search(r'(\d+)\s*beds?', text_lower)
                            if bed_match:
                                apartment['bedrooms'] = int(bed_match.group(1))
                        # Extract bathrooms
                        if 'bath' in text_lower and apartment['bathrooms'] is None:
                            bath_match = re.search(r'([\d.]+)\s*baths?', text_lower)
                            if bath_match:
                                apartment['bathrooms'] = float(bath_match.group(1))
                        # Extract sqft (handle "800 Sqft" format - case insensitive)
                        if apartment['sqft'] is None:
                            # Try multiple patterns for sqft
                            sqft_match = re.search(r'(\d+)\s*sq\.?\s*ft', text_lower)
                            if sqft_match:
                                apartment['sqft'] = int(sqft_match.group(1))
                            else:
                                # Try simpler pattern without space
                                sqft_match = re.search(r'(\d+)\s*sqft', text_lower)
                                if sqft_match:
                                    apartment['sqft'] = int(sqft_match.group(1))
                                else:
                                    # Try just number before "sq" (handles "800 Sqft")
                                    sqft_match = re.search(r'(\d+)\s*sq', text_lower)
                                    if sqft_match:
                                        apartment['sqft'] = int(sqft_match.group(1))
                
                # Set defaults if not found
                if apartment['bedrooms'] is None:
                    apartment['bedrooms'] = extract_bedrooms(apartment['title'] or "")
                if apartment['bathrooms'] is None:
                    apartment['bathrooms'] = 1.0
                if apartment['sqft'] is None:
                    # Try extracting from subtitle text as fallback
                    subtitle_text = subtitle_elem.get_text() if subtitle_elem else ""
                    apartment['sqft'] = extract_sqft(subtitle_text) or extract_sqft(apartment['title'] or "")
                
                # Extract image (first image-gallery-image)
                img_elem = listing.find('img', class_='image-gallery-image')
                if img_elem:
                    img_src = img_elem.get('src') or img_elem.get('data-src') or ''
                    apartment['images'] = [img_src] if img_src else ['img/property-1.jpg']
                else:
                    apartment['images'] = ['img/property-1.jpg']
                
                # Extract description
                desc_elem = listing.find('div', class_=re.compile(r'description', re.I))
                apartment['description'] = desc_elem.text.strip() if desc_elem else ""
                
                # Extract amenities
                amenities = []
                desc_lower = apartment['description'].lower()
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
                
                # Set defaults
                apartment['furnished'] = True  # All listings on this site are furnished
                apartment['source'] = 'rentitfurnished'
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
                
                # Only add if we have minimum data
                if apartment.get('title') or apartment.get('price'):
                    apartments.append(apartment)
                
            except Exception as e:
                logger.warning(f"  Error parsing listing: {e}")
                continue
        
        print(f"Successfully parsed {len(apartments)} apartments from Rent it Furnished")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        # Return empty list on error so other scrapers can continue
        return []
    finally:
        if driver:
            try:
                print("Closing browser...")
                driver.quit()
            except:
                pass  # Ignore errors when closing
    
    return apartments


if __name__ == "__main__":
    # Test scraper
    results = scrape_rentitfurnished(max_pages=1)
    print(f"\nTotal apartments scraped: {len(results)}")
    
    # Print first result
    if results:
        print("\nSample apartment:")
        print(json.dumps(results[0], indent=2))
    else:
        print("\nNo results. Check debug_html/rentitfurnished_selenium.html to inspect HTML structure.")
