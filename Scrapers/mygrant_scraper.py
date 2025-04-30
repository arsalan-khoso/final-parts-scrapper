from bs4 import BeautifulSoup
import os
import time
from dotenv import load_dotenv
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Global cookies storage
_mygrant_cookies = None


def login(driver, logger):
    """Login to MyGrant website with cookies persistence"""
    global _mygrant_cookies

    logger.info("Checking login status for MyGrant")

    # Try using existing cookies if available
    if _mygrant_cookies is not None and len(_mygrant_cookies) > 0:
        logger.info("Attempting to use saved cookies")
        driver.get('https://www.mygrantglass.com')

        # Add saved cookies
        for cookie in _mygrant_cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(f"Failed to add cookie: {e}")

        # Navigate to a protected page to verify login
        driver.get('https://www.mygrantglass.com/pages/search.aspx')

        # Check if we're still on the search page and not redirected to login
        if 'login.aspx' not in driver.current_url:
            logger.info("Login successful using cookies")
            return True
        else:
            logger.info("Cookies expired, performing full login")

    # Perform full login if no cookies or they've expired
    logger.info("Performing full login to MyGrant")
    load_dotenv()
    username = os.getenv('MYGRANT_USER')
    password = os.getenv('MYGRANT_PASS')

    try:
        driver.get('https://www.mygrantglass.com/pages/login.aspx')
        wait = WebDriverWait(driver, 10)

        # Wait until username field is visible and enter username
        username_field = wait.until(EC.visibility_of_element_located((By.ID, "clogin_TxtUsername")))
        username_field.clear()
        username_field.send_keys(username)

        # Wait until password field is visible and enter password
        password_field = wait.until(EC.visibility_of_element_located((By.ID, "clogin_TxtPassword")))
        password_field.clear()
        password_field.send_keys(password)

        # Wait until login button is clickable and click it
        login_button = wait.until(EC.element_to_be_clickable((By.ID, "clogin_ButtonLogin")))
        login_button.click()

        # Wait for redirect after login
        wait.until(EC.url_changes('https://www.mygrantglass.com/pages/login.aspx'))

        # Save cookies for future use
        _mygrant_cookies = driver.get_cookies()
        logger.info(f"Login successful - saved {len(_mygrant_cookies)} cookies")
        return True

    except Exception as e:
        logger.error(f"Login error: {e}")
        return False


def MyGrantScraper(partNo, driver, logger):
    """Optimized scraper for MyGrant using list comprehensions and improved error handling"""
    try:
        # Ensure login first
        if not login(driver, logger):
            logger.error("Failed to login to MyGrant")
            return []

        # URL for part search
        url = f'https://www.mygrantglass.com/pages/search.aspx?q={partNo}&sc=r&do=Search'
        logger.info(f"Searching for part in MyGrant: {partNo}")
        driver.get(url)

        # Wait for page to load with 10-second timeout
        wait = WebDriverWait(driver, 10)

        # Wait for either results div or "no results" message
        wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[@id='cpsr_DivParts'] | //div[contains(text(), 'No results')]")))

        # Check for "no results" message
        if driver.find_elements(By.XPATH, "//div[contains(text(), 'No results')]"):
            logger.info(f"No results found for part {partNo}")
            return []

        # Find locations (h3 elements) - skip the first one as it's the header
        locations = driver.find_elements(By.XPATH, "//div[@id='cpsr_DivParts']/h3")
        if not locations or len(locations) <= 1:
            logger.info(f"No location headers found for part {partNo}")
            return []

        # Skip the first h3 as it's usually just the page title
        locations = locations[1:]

        # Process all locations and extract parts using list comprehension
        parts = []

        for location_elem in locations:
            try:
                location = location_elem.text.strip()
                logger.info(f"Processing location: {location}")

                # Find all table rows for this location
                xpath_query = f"//h3[contains(text(), '{location}')]/following-sibling::table[@class='partlist'][1]//tr[position() > 1]"
                rows = driver.find_elements(By.XPATH, xpath_query)

                # Process each row in this location's table
                location_parts = []

                for row in rows:
                    try:
                        # Extract cells using XPath
                        cells = row.find_elements(By.XPATH, "./td")

                        # Only process rows with enough cells
                        if len(cells) >= 4:
                            availability_text = cells[1].text.strip()
                            part_number = cells[2].text.strip()
                            price = cells[3].text.strip()

                            # Convert availability to Yes/No format
                            availability = "Yes" if "yes" in availability_text.lower() else "No"

                            # Add part to location parts
                            location_parts.append([part_number, availability, price, location])

                    except Exception as e:
                        logger.warning(f"Error processing row: {e}")
                        continue

                # Add all parts from this location
                parts.extend(location_parts)
                logger.info(f"Found {len(location_parts)} parts at {location}")

            except Exception as e:
                logger.warning(f"Error processing location {location}: {e}")
                continue

        if not parts:
            logger.info(f"No parts found for {partNo}")
        else:
            logger.info(f"Found {len(parts)} parts for {partNo}")

        return parts

    except Exception as e:
        logger.error(f"Error in MyGrant scraper: {e}")
        return []


# For testing purposes
if __name__ == "__main__":
    import logging
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    # Setup Chrome with optimized options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")  # Disable images for faster loading

    # Initialize the driver directly
    driver = webdriver.Chrome(options=chrome_options)

    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    try:
        # Test multiple part numbers to demonstrate cookie reuse
        part_numbers = ["2000", "3000", "4000"]

        for part_no in part_numbers:
            print(f"\nSearching for part {part_no}...")
            results = MyGrantScraper(part_no, driver, logger)

            if results:
                print(f"Found {len(results)} results for {part_no}:")
                for part in results:
                    print(f"Part: {part[0]}, Availability: {part[1]}, Price: {part[2]}, Location: {part[3]}")
            else:
                print(f"No results found for {part_no}")
    finally:
        driver.quit()