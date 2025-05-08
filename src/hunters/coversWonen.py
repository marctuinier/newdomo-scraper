from hunters.hunter import *
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import re

# Utrecht hunter
class CoversWonen(Hunter):
    def __init__(self):
        name = 'Covers Wonen'
        url = 'https://coverswonen.nl/en/properties/rent'
        super().__init__(name, url)

    def process(self):
        # Get list or rows
        wait = WebDriverWait(browser, 10)
        listing = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'grid-main-area')))
        items = listing.find_elements(By.CLASS_NAME, 'parallax-item')

        # Process items
        preys = []
        for item in items:
            try:
                anchor_tag = item.find_element(By.XPATH, ".//h3/a")
                name = anchor_tag.get_attribute('innerHTML').strip()
                link = anchor_tag.get_attribute('href')

                # Get price
                price_element = item.find_element(By.XPATH, ".//p[starts-with(text(), '€') and contains(text(), 'per month')]")
                price_text_full = price_element.get_attribute('innerHTML').strip()
                price = re.search(r'€\s*([\d\.,]+)\s*per month', price_text_full, re.IGNORECASE).group(1).replace(".", "")

                agency = self.name
                preys.append(Prey(name, price, link, agency, self.name))
            except:
                 # Ignore incomplete items
                continue
        return preys
