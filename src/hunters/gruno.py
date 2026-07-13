from .hunter import browser, Prey, Hunter
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from datetime import datetime, timezone
import time # Added

class Gruno(Hunter):
    def __init__(self):
        super().__init__(name='Gruno Verhuur', url=None)

    def process(self):
        preys = []
        if browser is None: return preys
        wait = WebDriverWait(browser, 10)
        try:
            # Wait for the main container of all listings
            rows_container = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@class="object_list col-md-12"]')))
            
            # Find all individual apartment cards
            item_elements = rows_container.find_elements(By.XPATH, './/article[contains(@class, "objectcontainer")]')

            for item_element in item_elements:
                try:
                    # --- Get Name ---
                    name_el = item_element.find_element(By.CLASS_NAME, 'obj_address')
                    name = name_el.text.replace('Te huur: ', '').strip()

                    # --- Get Price (FIXED) ---
                    price_el = item_element.find_element(By.CLASS_NAME, 'obj_price')
                    # First, take only the part before the comma. Then, remove non-digits.
                    price = re.sub(r'[^\d]', '', price_el.text.split(',')[0])

                    # --- Get M2 (NEW) ---
                    m2 = None # Default to None in case it's not found
                    try:
                        m2_el = item_element.find_element(By.CLASS_NAME, 'object_sqfeet')
                        # Find the number inside the m2 element
                        m2_text = m2_el.find_element(By.TAG_NAME, 'span').text
                        m2 = int(re.sub(r'[^\d]', '', m2_text))
                    except:
                        # If m2 element doesn't exist or has no number, it will just be None
                        pass

                    # --- Get Link ---
                    # The link is on the main container for the data
                    link_el = item_element.find_element(By.CLASS_NAME, 'datacontainer').find_element(By.TAG_NAME, 'a')
                    raw_link = link_el.get_attribute('href')
                    # Make sure the link is absolute
                    if raw_link.startswith('/'):
                        link = f"https://www.grunoverhuur.nl{raw_link}"
                    else:
                        link = raw_link
                    
                    # --- Get Agency ---
                    agency = self.name # Gruno is the agency

                    # --- Create the Prey object ---
                    if name and link and price:
                        preys.append(Prey(name=name, price=price, link=link, agency=agency, website=self.name, m2=m2))

                except Exception as e_item:
                    # This will catch errors on a single card and let the loop continue
                    print(f"WARNING: Gruno hunter failed to parse one item. Error: {e_item}")
                    pass
                    
        except Exception as e_process:
            print(f"ERROR: [{datetime.now(timezone.utc).isoformat()}] Gruno main processing error for {self.url}: {e_process}")
        
        return preys

    def supported_cities(self):
        # Gruno Verhuur is primarily Groningen-focused.
        # Add other cities if they are supported by Gruno.
        return {
            'Groningen': 'https://www.grunoverhuur.nl/woningaanbod/huur/groningen'
        }

    def set_city(self, city_key_from_map):
        cities = self.supported_cities()
        if city_key_from_map in cities:
            self.url = cities[city_key_from_map]
            self.current_city_name = city_key_from_map
        else:
            raise ValueError(f"Gruno Verhuur: City key '{city_key_from_map}' not found in its own supported_cities map.")