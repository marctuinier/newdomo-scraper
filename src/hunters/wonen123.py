from .hunter import browser, Prey, Hunter
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from datetime import datetime, timezone
import time

class Wonen123(Hunter):
    def __init__(self):
        super().__init__(name='123Wonen', url=None)

    def process(self):
        preys = []
        if browser is None: return preys
        wait = WebDriverWait(browser, 10)
        try:
            # Wait for the main container of all listings
            items_wrap = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'pandlist')))
            # Find all individual apartment cards
            item_elements = items_wrap.find_elements(By.CSS_SELECTOR, '.pandlist-container')

            for item_element in item_elements:
                try:
                    # Get Name (street name)
                    name_el = item_element.find_element(By.CLASS_NAME, 'pand-address')
                    name = name_el.text.strip()
                    
                    # Get Price
                    price_el = item_element.find_element(By.CLASS_NAME, 'pand-price')
                    price_text = price_el.text.strip()
                    # Take only the part before the comma, then remove non-digits.
                    price = re.sub(r'[^\d]', '', price_text.split(',')[0])
                    
                    # Get Link
                    link_el = item_element.find_element(By.CLASS_NAME, 'textlink-design')
                    link = link_el.get_attribute('href')
                    
                    agency = self.name

                    # Get M2 (NEW FEATURE - from search page)
                    m2 = None
                    try:
                        # Find the "Living area" label, then get the text of its sibling span
                        m2_element = item_element.find_element(By.XPATH, ".//span[contains(text(), 'Living area')]/following-sibling::span")
                        m2_text = m2_element.text
                        # Remove all non-digits (like " m²") and convert to integer
                        m2 = int(re.sub(r'[^\d]', '', m2_text))
                    except:
                        pass # m2 will remain None if not found

                    if name and link and price:
                        # Add m2 to the Prey object creation
                        preys.append(Prey(name=name, price=price, link=link, agency=agency, website=self.name, m2=m2))
                
                except Exception as e_item:
                    # print(f"DEBUG: [{datetime.now(timezone.utc).isoformat()}] 123Wonen item parsing error: {e_item}")
                    pass
        
        except Exception as e_process:
            print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] 123Wonen main processing error for {self.url}: {e_process}")
        
        return preys

    def supported_cities(self):
        base_url_template = "https://www.expatrentalsholland.com/offer/in/{city_slug}"
        city_slugs_for_expat = {
            'Amsterdam': 'amsterdam', 
            'Groningen': 'groningen', 
            'Maastricht': 'maastricht',
            'Rotterdam': 'rotterdam', 
            'Leiden': 'leiden', 
            'Delft': 'delft',
            'Utrecht': 'utrecht', 
            'Eindhoven': 'eindhoven', 
            'Tilburg': 'tilburg',
            'The Hague': 'den+haag',
            'Enschede': 'enschede',
            'Hengelo': 'hengelo',
            'Beetsterzwaag': 'beetsterzwaag',
            'Gorredijk': 'gorredijk'
        }
        city_map = {}
        for city_name, slug in city_slugs_for_expat.items():
             city_map[city_name] = base_url_template.replace("{city_slug}", slug)
        return city_map

    def set_city(self, city_key_from_map):
        cities = self.supported_cities()
        if city_key_from_map in cities:
            self.url = cities[city_key_from_map]
            self.current_city_name = city_key_from_map
        else:
            raise ValueError(f"123Wonen: City key '{city_key_from_map}' not found in its own supported_cities map.")