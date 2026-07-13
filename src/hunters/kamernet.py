# src/hunters/kamernet.py

from .hunter import browser, Prey, Hunter
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import os
from datetime import datetime, timezone
import time

class Kamernet(Hunter):
    def __init__(self):
        super().__init__(name='Kamernet', url=None)

    def process(self):
        preys = []
        if browser is None:
            print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Kamernet: Global browser not available for {self.url}.")
            return preys

        # Use /app/debug_files in Docker, else local debug_files so local runs don't fail
        debug_dir = "/app/debug_files" if os.path.exists("/app") and os.access("/app", os.W_OK) else os.path.join(os.getcwd(), "debug_files")
        if not os.path.exists(debug_dir):
            try:
                os.makedirs(debug_dir, exist_ok=True)
            except OSError:
                debug_dir = os.path.join(os.path.dirname(__file__), "..", "..", "debug_files")
                os.makedirs(debug_dir, exist_ok=True)
        
        error_occurred = False
        
        try:
            wait = WebDriverWait(browser, 15)
            print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Kamernet processing URL: {self.url}")

            # --- NEW STEP 1: Handle the cookie banner ---
            try:
                # Wait a few seconds for the cookie banner to appear and become clickable
                cookie_button = WebDriverWait(browser, 5).until(
                    EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
                )
                cookie_button.click()
                print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Kamernet: Clicked the cookie accept button.")
                time.sleep(1) # Give the banner a moment to disappear
            except:
                # If the banner doesn't appear (e.g., cookie already set), just continue
                print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Kamernet: Cookie banner not found or already accepted.")
                pass

            # --- NEW STEP 2: Use the CORRECT, updated selectors ---
            # Wait for the main listings container
            listings_container = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div[class*='SearchResultGrid_root__']")))
            
            # Find all individual apartment cards within the container
            listing_elements = listings_container.find_elements(By.CSS_SELECTOR, "a[class*='SearchResultCard_root__']")
            
            print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Kamernet: Found {len(listing_elements)} potential listings for {self.current_city_name}.")

            for item in listing_elements:
                try:
                    link = item.get_attribute('href')
                    content_block = item.find_element(By.CSS_SELECTOR, "div[class*='SearchResultCard_content__']")
                    
                    # Name is the first span with this class
                    name = content_block.find_element(By.CSS_SELECTOR, "span[class*='CommonStyles_whiteSpaceNoWrap__']").text.strip()
                    
                    price_text = content_block.find_element(By.CSS_SELECTOR, "span[class*='MuiTypography-h5']").text
                    price = re.sub(r'[^\d]', '', price_text)

                    m2 = None
                    all_details = content_block.find_elements(By.TAG_NAME, 'p')
                    for detail in all_details:
                        if 'm²' in detail.text:
                            m2_text = detail.text
                            m2 = int(re.sub(r'[^\d]', '', m2_text))
                            break
                    
                    agency = 'No Agency'
                    
                    if name and link and price and int(price) > 0:
                        p = Prey(name=name, price=price, link=link, agency=agency, website=self.name, m2=m2)
                        p.city_scraped_for = self._city_from_listing_url(link) or self.current_city_name
                        preys.append(p)

                except Exception:
                    pass
            
        except Exception as e_process:
            error_occurred = True
            print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Kamernet main processing error for {self.url}: {e_process}")
            
        finally:
            if error_occurred:
                timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                screenshot_path = os.path.join(debug_dir, f'kamernet_error_{timestamp}.png')
                html_path = os.path.join(debug_dir, f'kamernet_error_{timestamp}.html')

                print(f"DEBUG: Saving screenshot to {screenshot_path}")
                browser.save_screenshot(screenshot_path)
                
                print(f"DEBUG: Saving page source to {html_path}")
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(browser.page_source)
        
        return preys

    _SLUG_TO_CITY = {"den-haag": "The Hague"}

    @classmethod
    def _city_from_listing_url(cls, link):
        """Actual city from Kamernet listing URL: .../room-{city}/... or .../apartment-{city}/..."""
        if not link:
            return None
        parts = link.rstrip("/").split("/")
        for p in parts:
            if p.startswith("room-"):
                slug = p.replace("room-", "").lower()
                return cls._SLUG_TO_CITY.get(slug) or slug.replace("-", " ").title()
            if p.startswith("apartment-"):
                slug = p.replace("apartment-", "").lower()
                return cls._SLUG_TO_CITY.get(slug) or slug.replace("-", " ").title()
        return None

    def supported_cities(self):
        return {
            'Amsterdam': 'https://kamernet.nl/en/for-rent/properties-amsterdam',
            'Groningen': 'https://kamernet.nl/en/for-rent/properties-groningen',
            'Maastricht': 'https://kamernet.nl/en/for-rent/properties-maastricht',
            'Rotterdam': 'https://kamernet.nl/en/for-rent/properties-rotterdam',
            'Leiden': 'https://kamernet.nl/en/for-rent/properties-leiden',
            'Delft': 'https://kamernet.nl/en/for-rent/properties-delft',
            'Utrecht': 'https://kamernet.nl/en/for-rent/properties-utrecht',
            'Eindhoven': 'https://kamernet.nl/en/for-rent/properties-eindhoven',
            'Tilburg': 'https://kamernet.nl/en/for-rent/properties-tilburg',
            'The Hague': 'https://kamernet.nl/en/for-rent/properties-den-haag',
            'Enschede': 'https://kamernet.nl/en/for-rent/properties-enschede',
            'Hengelo': 'https://kamernet.nl/en/for-rent/properties-hengelo',
            'Beetsterzwaag': 'https://kamernet.nl/en/for-rent/properties-beetsterzwaag',
            'Gorredijk': 'https://kamernet.nl/en/for-rent/properties-gorredijk'
        }

    def set_city(self, city_key_from_map):
        cities = self.supported_cities()
        if city_key_from_map in cities:
            self.url = cities[city_key_from_map]
            self.current_city_name = city_key_from_map
        else:
            raise ValueError(f"Kamernet: City key '{city_key_from_map}' not found in its own supported_cities map.")