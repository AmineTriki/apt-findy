"""
Utility functions for apartment scrapers.
"""
import re
import time
import random
import logging
from typing import Optional, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User agent pool for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
]

def get_random_user_agent() -> str:
    """Get a random user agent from the pool."""
    return random.choice(USER_AGENTS)

def random_delay(min_seconds: float = 2.0, max_seconds: float = 5.0) -> None:
    """
    Add a random delay between requests to mimic human behavior.
    
    Args:
        min_seconds: Minimum delay in seconds (default: 2.0)
        max_seconds: Maximum delay in seconds (default: 5.0)
    """
    delay_time = random.uniform(min_seconds, max_seconds)
    time.sleep(delay_time)

def page_delay(min_seconds: float = 5.0, max_seconds: float = 10.0) -> None:
    """
    Add a longer random delay between pages.
    
    Args:
        min_seconds: Minimum delay in seconds (default: 5.0)
        max_seconds: Maximum delay in seconds (default: 10.0)
    """
    delay_time = random.uniform(min_seconds, max_seconds)
    time.sleep(delay_time)

def create_session_with_retries() -> requests.Session:
    """
    Create a requests session with retry logic and proper headers.
    
    Returns:
        Configured requests.Session object
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set default headers
    session.headers.update({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-CA,en;q=0.9,fr-CA;q=0.8,fr;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    })
    
    return session

def make_request_with_retry(
    session: requests.Session,
    url: str,
    max_retries: int = 3,
    retry_delay: int = 60
) -> Optional[requests.Response]:
    """
    Make a request with retry logic and error handling.
    
    Args:
        session: requests.Session object
        url: URL to request
        max_retries: Maximum number of retries (default: 3)
        retry_delay: Delay in seconds if blocked (default: 60)
    
    Returns:
        Response object or None if all retries failed
    """
    # Rotate user agent
    session.headers['User-Agent'] = get_random_user_agent()
    
    for attempt in range(max_retries):
        try:
            # Random delay before request
            random_delay(2.0, 5.0)
            
            response = session.get(url, timeout=15)
            
            # Check for rate limiting
            if response.status_code == 429:
                logger.warning(f"Rate limited (429) on attempt {attempt + 1}. Waiting {retry_delay}s...")
                time.sleep(retry_delay)
                continue
            
            # Check for server errors
            if response.status_code in [503, 502, 504]:
                logger.warning(f"Server error ({response.status_code}) on attempt {attempt + 1}. Retrying...")
                time.sleep(retry_delay // 2)
                continue
            
            # Check for blocking (403, 406)
            if response.status_code in [403, 406]:
                logger.warning(f"Blocked ({response.status_code}) on attempt {attempt + 1}. Waiting {retry_delay}s...")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Permanently blocked from {url}")
                    return None
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                # Exponential backoff
                wait_time = retry_delay * (2 ** attempt)
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                logger.error(f"All retries failed for {url}")
                return None
    
    return None


def delay(seconds: float = 2.0) -> None:
    """
    Add a delay between requests to avoid being blocked.
    DEPRECATED: Use random_delay() instead for better human-like behavior.
    
    Args:
        seconds: Number of seconds to delay (default: 2.0)
    """
    time.sleep(seconds)


def clean_price(price_str: str) -> Optional[int]:
    """
    Extract numeric price from various formats.
    
    Examples:
        "$1,200/mo" -> 1200
        "$1,200/month" -> 1200
        "1200" -> 1200
        "$1,200" -> 1200
    
    Args:
        price_str: Price string in various formats
    
    Returns:
        Price as integer, or None if cannot parse
    """
    if not price_str:
        return None
    
    # Remove common text
    price_str = price_str.lower()
    price_str = price_str.replace('/mo', '').replace('/month', '').replace('per month', '')
    price_str = price_str.replace('$', '').replace(',', '').strip()
    
    # Extract first number found
    match = re.search(r'\d+', price_str)
    if match:
        try:
            return int(match.group())
        except ValueError:
            return None
    return None


def clean_address(address: str) -> str:
    """
    Normalize address string.
    
    Args:
        address: Raw address string
    
    Returns:
        Cleaned address string
    """
    if not address:
        return ""
    
    # Remove extra whitespace
    address = ' '.join(address.split())
    
    # Ensure proper formatting
    address = address.strip()
    
    return address


def extract_bedrooms(text: str) -> Optional[int]:
    """
    Extract number of bedrooms from text.
    
    Examples:
        "2 Bed" -> 2
        "2BR" -> 2
        "2 bedrooms" -> 2
    
    Args:
        text: Text containing bedroom information
    
    Returns:
        Number of bedrooms, or None if not found
    """
    if not text:
        return None
    
    text = text.lower()
    
    # Look for patterns like "2 bed", "2br", "2 bedrooms"
    patterns = [
        r'(\d+)\s*bed',
        r'(\d+)\s*br',
        r'(\d+)\s*bedroom'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    
    return None


def extract_bathrooms(text: str) -> Optional[float]:
    """
    Extract number of bathrooms from text.
    
    Examples:
        "1 Bath" -> 1.0
        "1.5 Bath" -> 1.5
        "2BA" -> 2.0
    
    Args:
        text: Text containing bathroom information
    
    Returns:
        Number of bathrooms, or None if not found
    """
    if not text:
        return None
    
    text = text.lower()
    
    # Look for patterns like "1 bath", "1.5 bath", "2ba"
    patterns = [
        r'(\d+\.?\d*)\s*bath',
        r'(\d+\.?\d*)\s*ba',
        r'(\d+\.?\d*)\s*bathroom'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return None


def extract_sqft(text: str) -> Optional[int]:
    """
    Extract square footage from text.
    
    Examples:
        "950 sqft" -> 950
        "950 sq ft" -> 950
        "950sf" -> 950
    
    Args:
        text: Text containing square footage information
    
    Returns:
        Square footage as integer, or None if not found
    """
    if not text:
        return None
    
    text = text.lower()
    
    # Look for patterns like "950 sqft", "950 sq ft", "950sf"
    patterns = [
        r'(\d+)\s*sq\s*ft',
        r'(\d+)\s*sqft',
        r'(\d+)\s*sf'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    
    return None

