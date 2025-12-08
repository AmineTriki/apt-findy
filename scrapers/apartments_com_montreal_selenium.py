"""
Scraper for Apartments.com Montreal (furnished listings) using Selenium
Target: https://www.apartments.com/montreal-qc/furnished/
Uses Selenium to handle JavaScript-rendered content
"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import json
import re
import time
import random
import logging
from scraper_utils import clean_price, clean_address, extract_bedrooms, extract_bathrooms, extract_sqft

logger = logging.getLogger(__name__)


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


def scrape_apartments_com_montreal(max_pages: int = 2) -> List[Dict]:
    """
    Scrape Apartments.com Montreal furnished listings using Selenium.
    This site is JavaScript-rendered, so Selenium is required.
    
    Args:
        max_pages: Maximum number of pages to scrape (default: 2)
    
    Returns:
        List of apartment dictionaries
    """
    apartments = []
    
    print(f"Scraping Apartments.com Montreal (furnished) with Selenium...")
    
    # Setup Chrome options
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = None
    
    try:
        print("Starting Chrome driver...")
        driver = None
        
        # Strategy 1: Try undetected_chromedriver
        try:
            driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)
            driver.set_page_load_timeout(90)
            print("  ✓ Chrome started with undetected_chromedriver")
        except Exception as uc_error:
            error_str = str(uc_error)
            print(f"  ⚠️ undetected_chromedriver failed: {error_str[:150]}")
            
            # Strategy 2: Try WebDriverManager as fallback
            try:
                print("  Attempting WebDriverManager fallback...")
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.options import Options as ChromeOptions
                
                chrome_options = ChromeOptions()
                chrome_options.add_argument('--headless=new')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_argument('--window-size=1920,1080')
                
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.set_page_load_timeout(90)
                print("  ✓ Chrome started with WebDriverManager")
            except Exception as wdm_error:
                print(f"  ⚠️ WebDriverManager failed: {str(wdm_error)[:150]}")
                print("  Skipping Apartments.com (Chrome/Selenium unavailable)")
                return []
        
        if not driver:
            return []
        
        base_url = "https://www.apartments.com/montreal-qc/furnished/"
        
        for page in range(1, max_pages + 1):
            try:
                if page == 1:
                    url = base_url
                else:
                    url = f"{base_url}{page}/"
                
                print(f"  Loading page {page}...")
                driver.get(url)
                
                # Wait for listings to load - try multiple strategies
                print("  Waiting for listings to load...")
                try:
                    # Wait for any listing-like elements
                    WebDriverWait(driver, 30).until(
                        lambda d: (
                            d.find_elements(By.CSS_SELECTOR, "article.placard") or
                            d.find_elements(By.CSS_SELECTOR, "li.mortar-wrapper") or
                            d.find_elements(By.CSS_SELECTOR, "[data-listingid]") or
                            d.find_elements(By.CSS_SELECTOR, ".propertyCard") or
                            d.find_elements(By.CSS_SELECTOR, ".listingCard") or
                            len(d.find_elements(By.TAG_NAME, "article")) > 0
                        )
                    )
                    print("  Listings loaded!")
                except:
                    print("  Timeout waiting for listings, trying anyway...")
                
                # Extra wait for JavaScript to finish
                time.sleep(5)
                
                # Scroll multiple times to trigger lazy loading
                for i in range(3):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(1)
                
                # Get page source after JavaScript renders
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find listings - try multiple selectors
                listings = soup.find_all('article', class_='placard')
                if not listings:
                    listings = soup.find_all('li', class_='mortar-wrapper')
                if not listings:
                    listings = soup.find_all('div', attrs={'data-listingid': True})
                if not listings:
                    # Try more generic selectors
                    listings = soup.find_all('article')
                if not listings:
                    listings = soup.find_all('div', class_=re.compile(r'property|listing|placard', re.I))
                if not listings:
                    # Last resort: look for any div with address-like content
                    listings = soup.find_all('div', string=re.compile(r'\d+\s+\w+.*(st|street|ave|avenue|blvd|boulevard)', re.I))
                
                print(f"  Found {len(listings)} listings on page {page}")
                
                if not listings:
                    if page == 1:
                        # Save debug HTML on first page
                        try:
                            import os
                            os.makedirs('debug_html', exist_ok=True)
                            with open('debug_html/apartments_com_selenium.html', 'w', encoding='utf-8') as f:
                                f.write(soup.prettify())
                            print("  Saved HTML to debug_html/apartments_com_selenium.html")
                        except:
                            pass
                    break
                
                for idx, listing in enumerate(listings):
                    try:
                        apartment = {}
                        
                        # Extract title
                        title_elem = (
                            listing.find('span', class_='js-placardTitle') or
                            listing.find('a', class_='property-link') or
                            listing.find('div', class_='property-title') or
                            listing.find('h2') or
                            listing.find('h3')
                        )
                        apartment['title'] = title_elem.text.strip() if title_elem else None
                        
                        # Extract URL
                        link_elem = listing.find('a', class_='property-link') or listing.find('a', href=True)
                        if link_elem and link_elem.get('href'):
                            href = link_elem['href']
                            apartment['url'] = f"https://www.apartments.com{href}" if href.startswith('/') else href
                        else:
                            apartment['url'] = None
                        
                        # Extract price - try multiple selectors
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
                        # Also search in all text
                        if not price_text:
                            all_text = listing.get_text()
                            price_match = re.search(r'\$[\d,]+', all_text)
                            if price_match:
                                price_text = price_match.group()
                        apartment['price'] = extract_price_apartments_com(price_text) or clean_price(price_text)
                        
                        # Extract bedrooms/bathrooms
                        details_elem = (
                            listing.find('p', class_='property-beds') or
                            listing.find('span', class_='detailsTextWrapper') or
                            listing.find('p', class_='bed-range') or
                            listing.find('span', class_=re.compile(r'bed', re.I)) or
                            listing.find('div', class_=re.compile(r'bed', re.I))
                        )
                        details_text = details_elem.text.strip() if details_elem else ""
                        if not details_text:
                            all_text = listing.get_text()
                            details_text = all_text
                        
                        apartment['bedrooms'] = extract_bedrooms_apartments_com(details_text) or extract_bedrooms(details_text) or extract_bedrooms(apartment.get('title', ''))
                        apartment['bathrooms'] = extract_bathrooms_apartments_com(details_text) or extract_bathrooms(details_text) or extract_bathrooms(apartment.get('title', '')) or 1.0
                        
                        # Extract address
                        address_elem = (
                            listing.find('div', class_='property-address') or
                            listing.find('span', class_='property-address') or
                            listing.find('p', class_='property-address')
                        )
                        apartment['address'] = address_elem.text.strip() if address_elem else None
                        
                        if apartment['address'] and 'montreal' not in apartment['address'].lower():
                            apartment['address'] = f"{apartment['address']}, Montreal, QC"
                        
                        apartment['address'] = clean_address(apartment['address'] or "Montreal, QC")
                        
                        # Extract image
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
                    delay = random.uniform(5, 10)
                    print(f"  Waiting {delay:.1f}s before next page...")
                    time.sleep(delay)
            
            except Exception as e:
                logger.error(f"  Error on page {page}: {e}")
                continue
        
        print(f"\n✓ Scraped {len(apartments)} apartments from Apartments.com")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            try:
                print("Closing browser...")
                driver.quit()
            except:
                pass
    
    return apartments


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


if __name__ == "__main__":
    results = scrape_apartments_com_montreal(max_pages=2)
    print(f"\nTotal apartments scraped: {len(results)}")
    
    if results:
        print("\nSample apartment:")
        print(json.dumps(results[0], indent=2))
    else:
        print("\nNo results.")

