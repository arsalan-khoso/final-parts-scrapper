import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import os
import logging

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global session variable
_login_session = None

def login(driver, logger):
    """Login to Buy PGW Auto Glass website with session management"""
    global _login_session

    logger.info("Logging in to Buy PGW Auto Glass")
    load_dotenv()
    username = os.getenv('PGW_USER')
    password = os.getenv('PGW_PASS')

    try:
        # Make sure we're at the login page first
        driver.get('https://buypgwautoglass.com')

        # First check if we already have cookies from a previous login
        if _login_session is not None and len(_login_session) > 0:
            logger.info("Using existing session cookies")
            # Make sure we're on the domain before adding cookies
            for cookie in _login_session:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Failed to add cookie: {e}")

            # Try to navigate to a protected page to check if cookies work
            driver.get('https://buypgwautoglass.com/PartSearch/search.asp')
            # If we're not redirected to login page, session is valid
            if "PartSearch" in driver.current_url:
                logger.info("Session cookies still valid")
                return True
            else:
                logger.info("Session cookies expired, logging in again")
                _login_session = None

        # If no session or expired session, perform full login
        wait = WebDriverWait(driver, 10)
        driver.get('https://buypgwautoglass.com')

        # Find and fill login form elements
        try:
            user_input = wait.until(EC.presence_of_element_located((By.ID, 'txtUsername')))
            pass_input = wait.until(EC.presence_of_element_located((By.ID, 'txtPassword')))

            # Clear and fill inputs
            user_input.clear()
            pass_input.clear()

            user_input.send_keys(username)
            pass_input.send_keys(password)

            # Submit form
            login_button = wait.until(EC.element_to_be_clickable((By.ID, 'button1')))
            login_button.click()

            # Wait for login to complete
            wait.until(EC.url_changes('https://buypgwautoglass.com'))
            
            # Handle any "I Agree" prompt that might appear
            try:
                agree_buttons = driver.find_elements(By.XPATH, 
                                "//input[@value='I Agree'] | //button[contains(text(), 'Agree')]")
                if agree_buttons and len(agree_buttons) > 0:
                    agree_buttons[0].click()
                    logger.info("Clicked 'I Agree' button")
            except Exception as e:
                logger.warning(f"Error handling agreement screen: {e}")

            # Save cookies for future use
            _login_session = driver.get_cookies()
            logger.info(f"Login successful - saved {len(_login_session)} cookies")
            return True

        except Exception as e:
            logger.error(f"Login form error: {e}")
            return False

    except Exception as e:
        logger.error(f"Login error: {e}")
        return False

def process_part_detail(driver, part_number):
    """Process a single part detail using direct URL"""
    try:
        logger.info(f"Processing part detail for {part_number}")

        # Create a dynamic URL directly
        direct_url = f"https://importglasscorp.com/glass/{part_number}/"
        logger.info(f"Using direct URL: {direct_url}")

        # Navigate to the part detail page
        driver.get(direct_url)

        # Wait for detail page to load with a short timeout
        detail_wait = WebDriverWait(driver, 5)

        # Try to find table, if not found try alternative URL
        try:
            detail_table = detail_wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        except:
            logger.warning(f"No detail table found at {direct_url}, trying alternate URL format")
            # Try alternative URL format if first one fails
            alt_url = f"https://importglasscorp.com/product/detail/{part_number}/"
            driver.get(alt_url)
            try:
                detail_table = detail_wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            except:
                logger.warning(f"No detail table found at alternate URL {alt_url}")
                return None

        # Check location directly - focus on Opa-Locka
        location_elements = [elem.text for elem in driver.find_elements(By.TAG_NAME, "b")
                             if "Locka" in elem.text or "Warehouse" in elem.text]
        location = location_elements[0] if location_elements else "Unknown"

        # Skip if not in Opa-Locka
        if location != "Unknown" and "Opa-Locka" not in location:
            logger.info(f"Part {part_number} not available in Opa-Locka")
            return None

        # Process detail rows efficiently
        detail_rows = detail_table.find_elements(By.CSS_SELECTOR, "tbody tr")

        for row in detail_rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 5 or part_number not in cells[0].text:
                continue

            # Get price
            price = "Unknown"
            for cell_idx in range(2, min(5, len(cells))):
                bold_elements = cells[cell_idx].find_elements(By.TAG_NAME, "b")
                if bold_elements:
                    potential_price = bold_elements[0].text
                    if "$" in potential_price or any(c.isdigit() for c in potential_price):
                        price = potential_price
                        break

            # Check availability
            availability = "Yes" if any("In Stock" in cell.text for cell in cells) else "No"

            logger.info(f"Found available part: {part_number}, {price}, {location}")

            return [part_number, availability, price, location]

        return None
    except Exception as e:
        logger.error(f"Error processing part detail for {part_number}: {e}")
        return None


def IGCScraper(partNo, driver, logger):
    """Optimized scraper for Import Glass Corp website using direct URLs"""
    logger.info(f"Searching part in IGC: {partNo}")

    try:
        # Check login status first before navigation
        if not login(driver):
            logger.error("Failed to login")
            return None

        # Navigate to search page with existing session
        driver.get('https://importglasscorp.com/product/search/')

        # Wait for search form to load
        wait = WebDriverWait(driver, 10)
        search_input = wait.until(EC.presence_of_element_located((By.NAME, 'search')))
        search_input.clear()
        search_input.send_keys(partNo)

        # Submit the search form
        driver.execute_script("arguments[0].closest('form').submit();", search_input)

        logger.info("Search submitted, waiting for results...")

        # Wait for results to load
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".contentTitle")))
        time.sleep(1)  # Short wait for results to fully load

        # Find all tables at once
        tables = driver.find_elements(By.CSS_SELECTOR, ".blue-table")
        if not tables:
            logger.warning(f"No tables found for part {partNo}")
            return None

        # Extract part numbers from search results
        part_numbers = []
        for table in tables:
            try:
                # Process rows
                rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")

                # Extract part numbers that match our search
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 3:
                        continue

                    part_cell = cells[0]
                    try:
                        part_links = part_cell.find_elements(By.TAG_NAME, "a")
                        if part_links:
                            part_number = part_links[0].text.strip()
                            # Case-insensitive match
                            if partNo.lower() in part_number.lower():
                                part_numbers.append(part_number)
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Error processing table: {e}")
                continue

        logger.info(f"Found {len(part_numbers)} matching part numbers")

        if not part_numbers:
            return None

        # Process parts sequentially using direct URLs
        final_results = []

        for part_number in part_numbers:
            result = process_part_detail(driver, part_number)
            if result:
                final_results.append(result)

        logger.info(f"Final results count: {len(final_results)}")
        return final_results

    except Exception as e:
        logger.error(f"Error searching for part number {partNo} on IGC: {e}")
        return None


# Example usage
if __name__ == "__main__":
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    # Setup Chrome with optimized options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Single line for headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")  # Disable images for faster loading

    # Initialize the driver directly
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # First login separately to troubleshoot any login issues
        login_successful = login(driver)
        if not login_successful:
            print("Initial login failed. Check credentials and site availability.")
            driver.quit()
            exit(1)

        print("Login successful! Now searching for parts...")

        # Now run multiple searches reusing the same session
        part_numbers = ["2000"]
        all_results = {}

        for part_no in part_numbers:
            print(f"Searching for part {part_no}...")
            results = IGCScraper(part_no, driver, logger)
            all_results[part_no] = results

            # Print results for this part
            if results:
                print(f"Found {len(results)} results for part {part_no}:")
                for part in results:
                    print(f"Part: {part[0]}, Available: {part[1]}, Price: {part[2]}, Location: {part[3]}")
            else:
                print(f"No results found for part {part_no}.")
    finally:
        # Always close the driver
        driver.quit()