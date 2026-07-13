from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium_stealth import stealth
from datetime import datetime, timezone
import time
import os

# Initialize browser globally with selenium-stealth
chrome_options = ChromeOptions()

# Check for local testing (non-headless)
if os.getenv('FUNDA_LOCAL_TEST') == '1':
    print("INFO: Running in local test mode (non-headless)")
else:
    chrome_options.add_argument('--headless')

chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920x1080')
chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
chrome_options.binary_location = "/usr/bin/google-chrome-stable" if os.path.exists("/usr/bin/google-chrome-stable") else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

browser = None
try:
    browser = webdriver.Chrome(options=chrome_options)

    # Apply selenium-stealth to bypass bot detection with Dutch language priority
    stealth(browser,
        languages=["nl-NL", "nl", "en-US", "en"],
        vendor="Google Inc.",
        platform="MacIntel",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        run_on_insecure_origins=True,
    )

    print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Global selenium-stealth browser initialized in hunter.py.")
except Exception as e:
    try: timestamp = datetime.now(timezone.utc).isoformat()
    except: timestamp = "TIMESTAMP_ERROR"
    print(f"CRITICAL_ERROR: [{timestamp}] Failed to initialize global selenium-stealth browser in hunter.py: {e}")

class Prey:
    # UPDATED: Added m2=None to the constructor
    def __init__(self, name, price, link, agency, website, m2=None):
        self.name = name
        self.price = price
        self.link = link
        self.agency = agency
        self.website = website
        self.m2 = m2 # NEW: Added the m2 attribute
        self.city_scraped_for = None # Main script will set this

    def __str__(self):
        return f"{self.website}: {self.name} ({self.city_scraped_for}) - {self.price} EUR - {self.link}"

class Hunter:
    def __init__(self, name, url=None):
        self.name = name
        self.url = url
        self.current_city_name = None

    def start(self):
        pass

    def stop(self):
        pass

    def hunt(self):
        if not self.url:
            print(f"WARNING: [{datetime.now(timezone.utc).isoformat()}] No URL set for hunter {self.name}. Skipping hunt.")
            return []
        if browser is None:
            print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Global browser not initialized for hunter {self.name}. Skipping hunt.")
            return []

        browser.get(self.url)
        time.sleep(1)
        return self.process()

    def process(self):
        raise NotImplementedError(f"Process method not implemented for {self.name}")

    def supported_cities(self):
        raise NotImplementedError(f"supported_cities() not implemented for {self.name}")

    def set_city(self, city_name_key_from_map):
        cities = self.supported_cities()
        if city_name_key_from_map in cities:
            self.url = cities[city_name_key_from_map]
            self.current_city_name = city_name_key_from_map
        else:
            raise ValueError(f"{self.name}: City key '{city_name_key_from_map}' not found in its own supported_cities map.")