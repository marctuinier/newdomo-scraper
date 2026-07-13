# src/hunters/funda.py
from .hunter import browser, Prey, Hunter
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import re
from datetime import datetime, timezone
import time
import random

class Funda(Hunter):
    def __init__(self):
        super().__init__(name='Funda', url=None)

    def process(self):
        preys = []
        if browser is None: return preys
        wait = WebDriverWait(browser, 30)  # Increased timeout

        try:
            # --- 1. Human-like page load with scrolling ---
            print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Funda: Waiting for page to load...")
            time.sleep(random.uniform(2, 4))  # Random delay

            # Scroll to simulate human behavior
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight / 4);")
            time.sleep(random.uniform(1, 2))

            browser.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(random.uniform(1, 2))

            browser.execute_script("window.scrollTo(0, 0);")  # Back to top
            time.sleep(random.uniform(0.5, 1))

            # --- 2. Handle Cookie Banner ---
            try:
                cookie_btn = WebDriverWait(browser, 10).until(
                    EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
                )
                cookie_btn.click()
                print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Funda: Clicked cookie banner")
                time.sleep(random.uniform(1, 3))
            except:
                print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Funda: No cookie banner found")
                pass

            # --- 3. Look for bot detection page ---
            try:
                # Check if we're on the bot detection page
                bot_elements = browser.find_elements(By.XPATH, "//*[contains(text(), 'verifiëren dat onze bezoekers echte mensen zijn')]")
                if bot_elements:
                    print(f"WARNING: [{datetime.now(timezone.utc).isoformat()}] Funda: Detected bot verification page. Waiting...")
                    # Wait and try to continue, but likely will fail
                    time.sleep(10)
            except:
                pass

            # --- 4. More human-like scrolling and interaction ---
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
            time.sleep(random.uniform(1, 2))

            # --- 5. Find Listings ---
            print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Funda: Looking for listings...")

            # Scroll a bit more to ensure content loads
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(random.uniform(1, 2))

            # Wait up to 10s for at least one listing; if none (e.g. no results for this city), return [] without crashing
            try:
                wait_short = WebDriverWait(browser, 10)
                wait_short.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="listingDetailsAddress"]')))
            except TimeoutException:
                print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Funda: No listings found for {getattr(self, 'current_city_name', 'this city')} (timeout).")
                return preys

            address_links = browser.find_elements(By.CSS_SELECTOR, '[data-testid="listingDetailsAddress"]')
            print(f"INFO: [{datetime.now(timezone.utc).isoformat()}] Funda: Found {len(address_links)} potential listing elements")

            for link_el in address_links:
                try:
                    # 1. Extract Link & Name
                    link = link_el.get_attribute('href')
                    name = link_el.text.replace('\n', ', ').strip()
                    
                    # Skip "koophuur" (buy/rent) listings - we only want "huur" (rent-only)
                    if link and '/koophuur/' in link:
                        continue

                    # 2. Navigate to Container (Price/Specs/Agency are siblings/parents)
                    info_container = link_el.find_element(By.XPATH, "./../..")

                    # 3. Extract Price (must be the *rent*, not the house number!)
                    # Page: search results list — /zoeken/huur?selected_area=[...]
                    # Based on CSV analysis: the clean rent price is in an element with:
                    # - CSS class "truncate" 
                    # - Contains "€" and "/maand"
                    # This gives us "€ X.XXX /maand" without the purchase price
                    price = "0"
                    try:
                        price_el = None
                        # First try: look for element with class "truncate" containing "€" and "/maand"
                        # This is the clean rent price element (Element Index 4 in CSV)
                        for el in info_container.find_elements(By.CSS_SELECTOR, '.truncate'):
                            t = el.text.strip()
                            if "€" in t and "/maand" in t:
                                price_el = el
                                break
                        
                        # Fallback: try data-testid selectors
                        if not price_el:
                            for sel in (
                                '[data-testid="listingPrice"]',
                                '[data-testid="listingDetailsPrice"]',
                                '[data-testid="price"]',
                            ):
                                try:
                                    cand = info_container.find_element(By.CSS_SELECTOR, sel)
                                    if cand and ("€" in cand.text and "/maand" in cand.text):
                                        price_el = cand
                                        break
                                except Exception:
                                    continue
                        
                        # Last resort: any element with "€" and "/maand" (but prefer truncate)
                        if not price_el:
                            for el in info_container.find_elements(By.XPATH, ".//*[contains(text(), '€') and contains(text(), '/maand')]"):
                                t = el.text.strip()
                                if "/maand" in t:  # Must have /maand to be rent price
                                    price_el = el
                                    break
                        
                        if price_el:
                            price_text = price_el.text.strip()
                            # Extract just the part before "/maand" to get clean price
                            if "/maand" in price_text:
                                price_text = price_text.split("/maand")[0].strip()
                            clean_text = price_text.replace('.', '').replace(',', '')
                            raw = re.sub(r'[^\d]', '', clean_text)
                            p = int(raw) if raw else 0
                            if 50 <= p <= 50_000:
                                price = str(p)
                    except Exception:
                        pass

                    # 4. Extract M2
                    m2 = None
                    try:
                        specs = info_container.find_elements(By.TAG_NAME, 'li')
                        for spec in specs:
                            text = spec.text
                            if 'm²' in text:
                                m2 = int(re.sub(r'[^\d]', '', text))
                                break
                    except:
                        pass

                    # 5. Extract Agency
                    agency = "Funda Broker"
                    try:
                        all_links = info_container.find_elements(By.TAG_NAME, 'a')
                        if len(all_links) > 1:
                            agency = all_links[-1].text.strip()
                    except:
                        pass

                    # 6. Actual city from listing URL (so we store/show real city, not search region)
                    # Funda URLs: .../huur/{city_slug}/... e.g. .../huur/leeuwarden/... or .../huur/beetsterzwaag/...
                    actual_city = self.current_city_name  # fallback to search city
                    if link and "/huur/" in link:
                        parts = link.rstrip("/").split("/")
                        try:
                            i = parts.index("huur")
                            if i + 1 < len(parts):
                                slug = parts[i + 1].lower()
                                actual_city = self._slug_to_city(slug)
                        except (ValueError, IndexError):
                            pass

                    if name and link and price and int(price) > 0:
                        p = Prey(name=name, price=price, link=link, agency=agency, website=self.name, m2=m2)
                        p.city_scraped_for = actual_city
                        preys.append(p)

                except Exception:
                    continue

        except Exception as e_process:
            print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Funda processing error for {self.url}: {e_process}")
        
        return preys

    @staticmethod
    def _slug_to_city(slug):
        """Map Funda URL slug to display city name."""
        if not slug:
            return None
        slug = slug.lower()
        mapping = {
            "den-haag": "The Hague",
            "beetsterzwaag": "Beetsterzwaag",
            "gorredijk": "Gorredijk",
            "leeuwarden": "Leeuwarden",
            "amsterdam": "Amsterdam",
            "groningen": "Groningen",
            "rotterdam": "Rotterdam",
            "utrecht": "Utrecht",
            "eindhoven": "Eindhoven",
            "tilburg": "Tilburg",
            "enschede": "Enschede",
            "hengelo": "Hengelo",
            "maastricht": "Maastricht",
            "leiden": "Leiden",
            "delft": "Delft",
        }
        return mapping.get(slug, slug.replace("-", " ").title())

    def supported_cities(self):
        base_url = "https://www.funda.nl/zoeken/huur?selected_area=[\"{city_lower}\"]"
        
        cities = [
            'Amsterdam', 'Groningen', 'Maastricht', 'Rotterdam', 'Leiden',
            'Delft', 'Utrecht', 'Eindhoven', 'Tilburg', 'Enschede', 'Hengelo', 'The Hague',
            'Beetsterzwaag', 'Gorredijk' # Added new cities
        ]
        
        mapping = {}
        for city in cities:
            if city == 'The Hague':
                search_term = "den-haag"
            else:
                search_term = city.lower()
            
            mapping[city] = base_url.replace("{city_lower}", search_term)
            
        return mapping

    def set_city(self, city_key_from_map):
        cities = self.supported_cities()
        if city_key_from_map in cities:
            self.url = cities[city_key_from_map]
            self.current_city_name = city_key_from_map
        else:
            raise ValueError(f"Funda: City key '{city_key_from_map}' not found.")

