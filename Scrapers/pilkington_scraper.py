import os
import time
import re
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys





def PilkingtonScraper(partNo, driver, logger):
    """Optimized scraper that returns part data from Pilkington website"""
    wait = WebDriverWait(driver, 10)

    # Default parts to return if methods fail
    default_parts = [["Not Found", "Not Found", "Not Found", "Not Found"]]

    load_dotenv()
    username = os.getenv('PIL_USER')
    password = os.getenv('PIL_PASS')

    try:
        # First, try to see if we're already logged in by navigating to the main site
        driver.get('https://shop.pilkington.com/')
        logger.info("Logging form - trying to login")
        wait = WebDriverWait(driver, 10)
        login_button = wait.until(EC.visibility_of_element_located((By.XPATH, "//button[contains(@class, 'btn-login') or contains(text(), 'Customer Login')]")))
        login_button.click()

        # Step 1: Wait for the username field and enter text
        username_field = wait.until(EC.visibility_of_element_located((By.ID, "username")))
        username_field.send_keys(username)
        logger.info("username inserted")


        # Step 2: Wait for the password field and enter text
        password_field = wait.until(EC.visibility_of_element_located((By.ID, "password")))
        password_field.send_keys(password)

        logger.info("password inserted")

        # Step 3: Wait for the checkbox to be clickable and check it
        checkbox = wait.until(EC.element_to_be_clickable((By.ID, "cbTerms")))
        checkbox.click()

        logger.info("checkbox clicked")


        # Step 4: Wait for the Sign In button and click it
        sign_in_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and @ng-click='submit()']")))
        sign_in_button.click()
        logger.info("crendential submitted")
        popup_elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[@uib-modal-window='modal-window'] | //div[contains(@class, 'modal')]")))

        if 'https://shop.pilkington.com/ecomm/search/basic/' in driver.current_url or 'https://shop.pilkington.com/ecomm' in driver.current_url:
            logger.info("successfully login")
            try:

                if popup_elements:
                    close_buttons = driver.find_elements(By.XPATH,
                                                         ".//button[@class='close'] | //button[contains(text(), 'Close')]")
                    if close_buttons:
                        driver.execute_script("arguments[0].click();", close_buttons[0])
                        logger.info("Closed popup window")
            except Exception as e:
                logger.warning(f"Error handling popup: {e}")

        # Go to search URL
        url = f'https://shop.pilkington.com/ecomm/search/basic/?queryType=2&query={partNo}&inRange=true&page=1&pageSize=30&sort=PopularityRankAsc'
        logger.info(f"Searching part in Pilkington: {partNo}")
        driver.get(url)

        # Handle popup windows - simplified approach
        try:
            popup_elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[@uib-modal-window='modal-window'] | //div[contains(@class, 'modal')]")))
            if popup_elements:
                close_buttons = driver.find_elements(By.XPATH, ".//button[@class='close'] | //button[contains(text(), 'Close')]")
                if close_buttons:
                    driver.execute_script("arguments[0].click();", close_buttons[0])
                    logger.info("Closed popup window")
        except Exception as e:
            logger.warning(f"Error handling popup: {e}")

        # Check for "no results" message
        try:
            not_found_elements = driver.find_elements(By.XPATH, "//span[contains(text(), 'Found no') and .//span[@data-slot='inRangeFilter']//strong[contains(text(), 'in range')]]")
            if not_found_elements:
                logger.info(f"No data found for part number {partNo}")
                return default_parts
        except Exception as e:
            logger.warning(f"Error checking for no results message: {e}")

        # Extract part data - direct approach
        try:
            table_xpath = "//table[contains(@class, 'products-table') and contains(@class, 'table') and contains(@class, 'table-striped') and contains(@class, 'no-image')]"

            wait.until(EC.visibility_of_element_located((By.XPATH, table_xpath)))
            # Check if table exists first
            tables = driver.find_elements(By.XPATH, table_xpath)
            if not tables:
                logger.info(f"No product table found for {partNo}")
                return default_parts

            # Get location once
            try:
                location_elements = driver.find_elements(By.XPATH, "//span[@data-slot='plantName']//span")
                location = location_elements[0].text.strip() if location_elements else "Unknown Location"
            except Exception:
                location = "Unknown Location"
            logger.info(f"Location: {location}")

            # Extract all parts data
            part_numbers = [elem.text.strip() for elem in
                            driver.find_elements(By.XPATH, f'{table_xpath}//tr[@class="product"]//td[1]//span')]
            descriptions = [elem.text.strip() for elem in
                            driver.find_elements(By.XPATH, f'{table_xpath}//tr[@class="product"]//td[2]//span')]
            prices = [elem.text.strip() for elem in
                      driver.find_elements(By.XPATH, f'{table_xpath}//tr[@class="product"]//td[4]//span')]

            # Build parts list from extracted data
            parts = []
            for i in range(min(len(part_numbers), len(descriptions), len(prices))):
                parts.append([
                    part_numbers[i],
                    descriptions[i],
                    prices[i],
                    location
                ])

            logger.info(f"Found {len(parts)} parts for {partNo}")
            return parts if parts else default_parts

        except Exception as e:
            logger.error(f"Error extracting part data: {e}")
            return default_parts

    except Exception as e:
        logger.error(f"Error in Pilkington scraper: {e}")
        return default_parts
    finally:
        # In this version, we're letting the calling code handle driver quitting
        # as shown in your test code
        pass


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

    # Set up driver


    try:
        # Test the scraper
        results = PilkingtonScraper("2000", driver, logger)

        if results:
            for part in results:
                print(f"Part: {part[0]}, Name: {part[1]}, Price: {part[2]}, Location: {part[3]}")
        else:
            print("No results found")
    finally:
        driver.quit()