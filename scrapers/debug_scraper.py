"""
Debug script to inspect actual HTML structure of rental sites
"""
import requests
from bs4 import BeautifulSoup
import os

def debug_site(url, site_name):
    """Inspect HTML structure of a rental site"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-CA,en;q=0.9,fr-CA;q=0.8',
        'Referer': 'https://www.google.com/',
    }
    
    print(f"\n{'='*60}")
    print(f"DEBUGGING: {site_name}")
    print(f"URL: {url}")
    print(f"{'='*60}\n")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"ERROR: Got status {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            return
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Try common listing selectors
        selectors_to_try = [
            ('div.search-item', 'Kijiji search-item'),
            ('div[data-testid*="listing"]', 'Data testid listing'),
            ('article', 'Article tags'),
            ('div.listing', 'Listing class'),
            ('div.property-card', 'Property card'),
            ('div.search-item', 'Search item'),
            ('a[href*="/v"]', 'Kijiji listing links'),
            ('div.info-container', 'Info container'),
        ]
        
        print("Testing selectors:")
        for selector, name in selectors_to_try:
            try:
                elements = soup.select(selector)
                print(f"  {name} ({selector}): Found {len(elements)} elements")
                if elements and len(elements) > 0:
                    first = elements[0]
                    classes = first.get('class', [])
                    print(f"    Classes: {classes}")
                    # Show a snippet
                    text = first.get_text(strip=True)[:100]
                    print(f"    Text preview: {text}...")
            except Exception as e:
                print(f"  {name}: Error - {e}")
        
        # Look for any links that might be listings
        all_links = soup.find_all('a', href=True)
        listing_links = [link for link in all_links if any(x in link.get('href', '') for x in ['/v', '/listing', '/apartment', '/property'])]
        print(f"\nFound {len(listing_links)} potential listing links")
        if listing_links:
            print(f"  Sample link: {listing_links[0].get('href')}")
            parent = listing_links[0].find_parent('div') or listing_links[0].find_parent('article')
            if parent:
                print(f"  Parent tag: {parent.name}, classes: {parent.get('class', [])}")
        
        # Save HTML for inspection
        debug_dir = "debug_html"
        os.makedirs(debug_dir, exist_ok=True)
        filename = f"{debug_dir}/{site_name.lower().replace(' ', '_')}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print(f"\nSaved HTML to: {filename}")
        print("Open this file in a browser to inspect the structure")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Debug each site
    sites = [
        ("https://www.kijiji.ca/b-apartments-condos/ville-de-montreal/c37l1700281", "Kijiji Montreal"),
        ("https://rentitfurnished.com/montreal/listings", "Rent it Furnished"),
    ]
    
    for url, name in sites:
        debug_site(url, name)
        print("\n" + "="*60 + "\n")

