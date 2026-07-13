# src/hunters/huurwoningen.py

from .hunter import browser, Prey, Hunter
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from datetime import datetime, timezone

class Huurwoningen(Hunter):
    def __init__(self):
        # Initialize with the name of the new site
        super().__init__(name='Huurwoningen', url=None)

    def process(self):
        preys = []
        if browser is None: return preys
        wait = WebDriverWait(browser, 15)
        try:
            # Wait for the main list of apartments to be visible
            list_container = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'search-list')))
            
            # Get all individual listing items
            listing_items = list_container.find_elements(By.CSS_SELECTOR, "li.search-list__item--listing")

            for item in listing_items:
                try:
                    # --- Get Name and Link ---
                    # Both are in the same main link element
                    title_anchor = item.find_element(By.CLASS_NAME, 'listing-search-item__link--title')
                    name = title_anchor.text.strip()
                    link = title_anchor.get_attribute('href')

                    # --- Get Price ---
                    # Located in its own dedicated element
                    price_element = item.find_element(By.CLASS_NAME, 'listing-search-item__price')
                    price_text = price_element.text.strip()
                    # Some cards show two amounts ("Bare rental price €1,145 pcm\n
                    # Total rental price €1,345 per month"); take the first (bare rent)
                    price_match = re.search(r'€\s*([\d.,]+)', price_text)
                    price = re.sub(r'[^\d]', '', price_match.group(1)) if price_match else ''

                    # --- Get M2 (Surface Area) ---
                    # This is one of the "illustrated features"
                    m2 = None
                    try:
                        m2_element = item.find_element(By.CLASS_NAME, 'illustrated-features__item--surface-area')
                        m2_text = m2_element.text
                        m2 = int(re.sub(r'[^\d]', '', m2_text)) # Removes " m²"
                    except:
                        pass # m2 will remain None if not found

                    # --- Get Agency ---
                    # Also in its own element
                    agency = "Unknown Agency" # Default value
                    try:
                        agency_element = item.find_element(By.CLASS_NAME, 'listing-search-item__link')
                        agency = agency_element.text.strip()
                    except:
                        pass

                    # --- City: from URL slug (canonical /huren/{city}/) or card address, never search city for cross-region results ---
                    city = self._city_from_listing_url(link)
                    if not city:
                        city = self._city_from_listing_card(item)
                    if not city:
                        city = self.current_city_name  # last resort
                    # --- Create the Prey object with all the data ---
                    if name and link and price:
                        p = Prey(name=name, price=price, link=link, agency=agency, website=self.name, m2=m2)
                        p.city_scraped_for = city
                        preys.append(p)

                except Exception as e_item:
                    # If one card fails, print a warning and continue with the rest
                    print(f"WARNING: [{datetime.now(timezone.utc).isoformat()}] Huurwoningen hunter failed to parse one item. Error: {e_item}")
                    continue

        except Exception as e_process:
            print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Huurwoningen main processing error for {self.url}: {e_process}")
        
        return preys

    _SLUG_TO_CITY = {"den-haag": "The Hague", "oudega-smallingerland": "Oudega Smallingerland"}

    @classmethod
    def _city_from_listing_url(cls, link):
        """Actual city from Huurwoningen listing URL: .../huren/{city}/... (canonical listing path)."""
        if not link:
            return None
        # Regex fallback: /huren/{slug}/ in path
        m = re.search(r"/huren/([a-zA-Z0-9\-]+)/", link)
        if m:
            slug = m.group(1).lower()
            return cls._SLUG_TO_CITY.get(slug) or slug.replace("-", " ").title()
        parts = link.rstrip("/").split("/")
        try:
            i = parts.index("huren")
            if i + 1 < len(parts):
                slug = parts[i + 1].lower()
                return cls._SLUG_TO_CITY.get(slug) or slug.replace("-", " ").title()
        except ValueError:
            pass
        return None

    @classmethod
    def _city_from_listing_card(cls, item):
        """Fallback: extract city from address line (e.g. '8939 EJ Leeuwarden (Zuiderburen)')."""
        try:
            text = None
            for cls_name in ("listing-search-item__address", "listing-search-item__location", "listing-search-item__subtitle"):
                try:
                    el = item.find_element(By.CLASS_NAME, cls_name)
                    text = el.text.strip()
                    break
                except Exception:
                    continue
            if not text:
                text = item.text
            if text:
                # Match Dutch postal (4 digits, 2 letters) followed by city before (Area)
                m = re.search(r"\d{4}\s*[A-Z]{2}\s+(.+?)\s*\(", text)
                if m:
                    return m.group(1).strip()
        except Exception:
            pass
        return None

    def supported_cities(self):
        # We generate the URLs based on the pattern "https://www.huurwoningen.com/en/in/{city-slug}/"
        city_slugs = {
            'Amsterdam': 'amsterdam',
            'Groningen': 'groningen',
            'Maastricht': 'maastricht',
            'Rotterdam': 'rotterdam',
            'Leiden': 'leiden',
            'Delft': 'delft',
            'Utrecht': 'utrecht',
            'Eindhoven': 'eindhoven',
            'Tilburg': 'tilburg',
            'The Hague': 'den-haag',
            'Enschede': 'enschede',
            'Hengelo': 'hengelo',
            'Beetsterzwaag': 'beetsterzwaag',
            'Gorredijk': 'gorredijk'
        }
        
        base_url = "https://www.huurwoningen.com/en/in/{}/"
        return {city: base_url.format(slug) for city, slug in city_slugs.items()}

    def set_city(self, city_key_from_map):
        cities = self.supported_cities()
        if city_key_from_map in cities:
            self.url = cities[city_key_from_map]
            self.current_city_name = city_key_from_map
        else:
            raise ValueError(f"Huurwoningen: City key '{city_key_from_map}' not found in its own supported_cities map.")