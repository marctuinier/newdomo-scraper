from .hunter import browser, Prey, Hunter 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from datetime import datetime, timezone
import time # Added for potential sleeps

class Pararius(Hunter):
    def __init__(self):
        super().__init__(name='Pararius', url=None)

    def process(self):
        preys = []
        if browser is None: return preys
        wait = WebDriverWait(browser, 15)
        try:
            # Handle cookie consent if it appears
            try:
                cookie_button = WebDriverWait(browser, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accepteren')]"))
                )
                if cookie_button and cookie_button.is_displayed():
                    cookie_button.click()
                    time.sleep(0.5)
            except:
                pass

            # Wait for the main list container
            item_list_container = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'search-list')))
            # Find all individual listing items
            listing_items = item_list_container.find_elements(By.XPATH, "./li[contains(@class, 'search-list__item--listing')]")
            
            for item_element in listing_items:
                try:
                    # Get Name and Link
                    title_anchor = item_element.find_element(By.CLASS_NAME, 'listing-search-item__link--title')
                    name = title_anchor.text.strip()
                    link = title_anchor.get_attribute('href')
                    
                    # Get Price
                    price_text_element = item_element.find_element(By.CLASS_NAME, 'listing-search-item__price')
                    price_text = price_text_element.text.strip()
                    price = re.sub(r'[^\d]', '', price_text) 
                    
                    # Get Agency
                    agency_name = "Pararius Listing" 
                    try:
                        agency_element = item_element.find_element(By.CLASS_NAME, 'listing-search-item__info')
                        # The agency name is within an <a> tag inside the info element
                        agency_name = agency_element.find_element(By.CLASS_NAME, 'listing-search-item__link').text.strip()
                    except: 
                        pass

                    # Get M2 (NEW FEATURE)
                    m2 = None
                    try:
                        # Find the specific feature for surface area
                        m2_element = item_element.find_element(By.CLASS_NAME, 'illustrated-features__item--surface-area')
                        m2_text = m2_element.text
                        # Remove all non-digits (like " m²") and convert to integer
                        m2 = int(re.sub(r'[^\d]', '', m2_text))
                    except:
                        # If m2 element isn't found or text isn't a number, m2 remains None
                        pass
                        
                    if name and link and price:
                        p = Prey(name=name, price=price, link=link, agency=agency_name, website=self.name, m2=m2)
                        p.city_scraped_for = self._city_from_listing_url(link) or self.current_city_name
                        preys.append(p)
                
                except Exception as e_item:
                    # print(f"DEBUG: [{datetime.now(timezone.utc).isoformat()}] Pararius item parsing error for URL {self.url}: {e_item}")
                    pass
        except Exception as e_process:
            print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Pararius main processing error for {self.url}: {e_process}")
        return preys

    _SLUG_TO_CITY = {"den-haag": "The Hague"}

    @classmethod
    def _city_from_listing_url(cls, link):
        """Actual city from Pararius listing URL: .../apartment-for-rent/{city}/... (or house/room/studio-for-rent)."""
        if not link:
            return None
        parts = link.rstrip("/").split("/")
        for key in ("apartment-for-rent", "house-for-rent", "room-for-rent", "studio-for-rent"):
            try:
                i = parts.index(key)
                if i + 1 < len(parts):
                    slug = parts[i + 1].lower()
                    return cls._SLUG_TO_CITY.get(slug) or slug.replace("-", " ").title()
            except ValueError:
                continue
        return None

    def supported_cities(self): # Use exact names matching CITIES_TO_SCRAPE from main.py
        return {
            'Amsterdam': 'https://www.pararius.com/apartments/amsterdam',
            'Groningen': 'https://www.pararius.com/apartments/groningen',
            'Maastricht': 'https://www.pararius.com/apartments/maastricht',
            'Rotterdam': 'https://www.pararius.com/apartments/rotterdam',
            'Leiden': 'https://www.pararius.com/apartments/leiden',
            'Delft': 'https://www.pararius.com/apartments/delft',
            'Utrecht': 'https://www.pararius.com/apartments/utrecht',
            'Eindhoven': 'https://www.pararius.com/apartments/eindhoven',
            'Tilburg': 'https://www.pararius.com/apartments/tilburg',
            'The Hague': 'https://www.pararius.com/apartments/den-haag',
            'Enschede': 'https://www.pararius.com/apartments/enschede',
            'Hengelo': 'https://www.pararius.com/apartments/hengelo',
            'Beetsterzwaag': 'https://www.pararius.com/apartments/beetsterzwaag',
            'Gorredijk': 'https://www.pararius.com/apartments/gorredijk'
        }

    def set_city(self, city_key_from_map): # city_key_from_map is a key from its own supported_cities()
        cities = self.supported_cities()
        if city_key_from_map in cities:
            self.url = cities[city_key_from_map]
            self.current_city_name = city_key_from_map # Store the canonical name
        else:
            # This error should ideally not be hit if main.py filters correctly
            raise ValueError(f"Pararius: City key '{city_key_from_map}' not found in its own supported_cities map.")