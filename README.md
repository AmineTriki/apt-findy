# Apt-Findy 🏠

Automated apartment finder that scrapes rental sites and matches apartments to your preferences.

## Features

- **Multi-source scraping**: Scrapes apartments from multiple rental websites (Apartments.com, Craigslist, Zillow, Kijiji)
- **Smart matching**: Calculates match scores based on your budget, location preferences, must-have features, and move-in dates
- **Beautiful web interface**: Modern, responsive UI to browse and filter apartments
- **Automated updates**: Runs automatically via GitHub Actions (coming in Week 2)
- **100% free**: Uses free services (GitHub Actions, GitHub Pages, Nominatim geocoding)

## Status

✅ **Week 1 Complete**: Core scraping, matching, and web interface working

## Project Structure

```
apt-findy/
├── scrapers/          # Python scrapers for rental websites
│   ├── apartments_com.py
│   ├── craigslist.py
│   ├── zillow.py
│   ├── kijiji.py
│   ├── scraper_manager.py
│   ├── geocoder.py
│   ├── distance_calculator.py
│   ├── matcher.py
│   └── scraper_utils.py
├── config/
│   └── preferences.json    # Your search preferences
├── website/           # Web interface
│   ├── apartments.json      # Generated apartment data
│   ├── apartments.js
│   └── property-list.html
└── data/
    └── geocache.json        # Cached geocoding results
```

## Setup

### Prerequisites

- Python 3.11+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/AmineTriki/apt-findy.git
cd apt-findy
```

2. Install Python dependencies:
```bash
pip install -r scrapers/requirements.txt
```

3. Configure your preferences:
   - Edit `config/preferences.json` with your city, budget, locations, and requirements

4. Run the scraper:
```bash
python scrapers/scraper_manager.py --city Montreal --pages 3
```

5. View results:
   - Open `website/property-list.html` in a web browser
   - Or serve the website locally with a simple HTTP server:
     ```bash
     cd website
     python -m http.server 8000
     ```
     Then visit `http://localhost:8000/property-list.html`

## How It Works

1. **Scraping**: The scraper manager runs multiple scrapers in parallel, collecting apartment listings from various sources
2. **Geocoding**: Addresses are converted to lat/lng coordinates using Nominatim (free geocoding service)
3. **Distance Calculation**: Distances and commute times are calculated to your important locations (work, friends, etc.)
4. **Matching**: Each apartment gets a match score (0-100) based on:
   - Price within budget (30 points)
   - Right number of bedrooms (20 points)
   - Proximity to important locations (40 points)
   - Move-in date match (10 points)
   - Nice-to-have amenities (bonus points)
5. **Display**: Apartments are sorted by match score and displayed in the web interface

## Customization

### For Your City

1. Update `config/preferences.json` with your city and locations
2. Modify scraper URLs in the scraper files if needed for your city
3. Run the scraper with your city name:
   ```bash
   python scrapers/scraper_manager.py --city "YourCity"
   ```

### Adding New Scrapers

1. Create a new file in `scrapers/` (e.g., `new_site.py`)
2. Implement a `scrape_new_site()` function that returns a list of apartment dictionaries
3. Add the scraper to `scraper_manager.py`:
   ```python
   from new_site import scrape_new_site
   # ... in run_all_scrapers():
   apts = scrape_new_site(city=city, max_pages=max_pages)
   ```

## Current Limitations

- Some websites use heavy JavaScript and may require Selenium for full functionality
- Geocoding is rate-limited (1 request per second) to respect Nominatim's usage policy
- Scrapers may need updates if website structures change

## Next Steps (Week 2)

- [ ] Set up GitHub Actions for automated scraping every 30 minutes
- [ ] Deploy website to GitHub Pages
- [ ] Add email notifications for new high-match apartments
- [ ] Add filtering and sorting to web interface
- [ ] Add map view with apartment locations

## License

See LICENSE file for details.