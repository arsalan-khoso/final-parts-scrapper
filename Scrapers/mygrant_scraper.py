import os
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv

def login_mygrant(driver, logger):
    """Login to MyGrant Auto Glass website"""
    logger.info("Checking login status for MyGrant")
    
    # Load environment variables
    load_dotenv()
    username = os.getenv('MYGRANT_USER')
    password = os.getenv('MYGRANT_PASS')
    
    # Check if credentials are available
    if not username or not password:
        logger.error("MyGrant credentials not found in environment variables")
        return False

    try:
        # Go to the login page
        driver.get('https://www.mygrantonline.com/')
        
        # Check if already logged in by looking for sign out link
        try:
            signout_elements = driver.find_elements(By.XPATH, "//a[contains(text(), 'Sign Out') or contains(text(), 'Log Out')]")
            if signout_elements:
                logger.info("Already logged in to MyGrant")
                return True
        except:
            pass
        
        # If not already logged in, perform login
        logger.info("Performing full login to MyGrant")
        wait = WebDriverWait(driver, 10)
        
        # Enter username
        try:
            username_field = wait.until(EC.presence_of_element_located((By.ID, "ctl00_txtLogin")))
            username_field.clear()
            username_field.send_keys(username)
        except Exception as e:
            logger.error(f"Error finding username field: {e}")
            return False
        
        # Enter password
        try:
            password_field = wait.until(EC.presence_of_element_located((By.ID, "ctl00_txtPassword")))
            password_field.clear()
            password_field.send_keys(password)
        except Exception as e:
            logger.error(f"Error finding password field: {e}")
            return False
        
        # Click login button
        try:
            login_button = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_btnLogin")))
            login_button.click()
        except Exception as e:
            logger.error(f"Error clicking login button: {e}")
            return False
        
        # Check if login successful by looking for elements that indicate logged-in status
        try:
            # Wait for a common element that appears after login
            wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Sign Out')] | //a[contains(text(), 'Log Out')] | //a[contains(text(), 'My Account')]")))
            logger.info("Successfully logged in to MyGrant")
            return True
        except TimeoutException:
            # Check for error messages
            error_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'error')] | //span[contains(@class, 'error')]")
            if error_elements:
                for error in error_elements:
                    logger.error(f"Login error message: {error.text}")
            else:
                logger.error("Login failed but no error message found")
            return False
    
    except Exception as e:
        logger.error(f"Failed to login to MyGrant: {e}")
        return False

def MyGrantScraper(partNo, driver, logger):
    """Scrape part information from MyGrant website"""
    logger.info(f"Searching part in MyGrant: {partNo}")
    
    # Default part data if nothing is found
    default_parts = [["Not Found", "Not Found", "Not Found", "Not Found"]]
    
    try:
        # First make sure we're logged in
        login_successful = login_mygrant(driver, logger)
        if not login_successful:
            logger.error("Failed to login to MyGrant")
            return default_parts
        
        # Navigate to search page
        driver.get('https://www.mygrantonline.com/')
        
        # Find and use the search box
        wait = WebDriverWait(driver, 10)
        try:
            # Look for search box - try different possible IDs or XPaths
            search_box_selectors = [
                "//input[contains(@id, 'txtSearch')]",
                "//input[contains(@id, 'search')]",
                "//input[contains(@placeholder, 'Search')]"
            ]
            
            search_box = None
            for selector in search_box_selectors:
                try:
                    search_box = driver.find_element(By.XPATH, selector)
                    if search_box:
                        break
                except:
                    continue
            
            if not search_box:
                logger.error("Could not find search box")
                return default_parts
            
            # Clear and enter part number
            search_box.clear()
            search_box.send_keys(partNo)
            search_box.send_keys(Keys.RETURN)
            
            # Wait for results page to load
            time.sleep(3)
            
            # Check for no results message
            no_results_elements = driver.find_elements(By.XPATH, "//div[contains(text(), 'No results')] | //p[contains(text(), 'No results')]")
            if no_results_elements:
                logger.info(f"No results found for part {partNo}")
                return default_parts
            
            # Extract results
            parts = []
            
            # Try to find the results table
            try:
                # Look for results in multiple possible table formats
                table_selectors = [
                    "//table[contains(@class, 'results')]",
                    "//table[contains(@class, 'grid')]",
                    "//div[contains(@class, 'results')]//table",
                    "//div[contains(@class, 'product-list')]"
                ]
                
                # First try to find the table
                result_table = None
                for selector in table_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            result_table = elements[0]
                            break
                    except:
                        continue
                
                if not result_table:
                    logger.warning("Could not find results table, trying alternative approach")
                    # Alternative approach: look for product elements directly
                    product_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'product')] | //tr[contains(@class, 'item')]")
                    
                    for product in product_elements:
                        try:
                            # Extract part number
                            part_number_element = product.find_element(By.XPATH, ".//span[contains(@class, 'part-number')] | .//span[contains(@class, 'partno')] | .//td[1]")
                            part_number = part_number_element.text.strip()
                            
                            # Extract description/name
                            description_element = product.find_element(By.XPATH, ".//span[contains(@class, 'description')] | .//span[contains(@class, 'name')] | .//td[2]")
                            description = description_element.text.strip()
                            
                            # Extract price (may not be available)
                            price = "Price not available"
                            try:
                                price_element = product.find_element(By.XPATH, ".//span[contains(@class, 'price')] | .//td[contains(@class, 'price')]")
                                price = price_element.text.strip()
                            except:
                                pass
                            
                            # Extract location/availability (may not be available)
                            location = "Location not available"
                            try:
                                location_element = product.find_element(By.XPATH, ".//span[contains(@class, 'location')] | .//span[contains(@class, 'warehouse')]")
                                location = location_element.text.strip()
                            except:
                                pass
                            
                            # Only add if the part number matches our search
                            if partNo.lower() in part_number.lower():
                                parts.append([part_number, description, price, location])
                                logger.info(f"Found matching part: {part_number}")
                        except Exception as e:
                            logger.warning(f"Error extracting product details: {e}")
                            continue
                else:
                    # Process the table rows
                    rows = result_table.find_elements(By.TAG_NAME, "tr")
                    logger.info(f"Found {len(rows)} rows in results table")
                    
                    # Skip header row if present
                    start_index = 1 if len(rows) > 1 else 0
                    
                    for i in range(start_index, len(rows)):
                        try:
                            cells = rows[i].find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 3:  # Ensure we have enough cells
                                part_number = cells[0].text.strip()
                                description = cells[1].text.strip() if len(cells) > 1 else "No description"
                                price = cells[2].text.strip() if len(cells) > 2 else "Price not available"
                                location = cells[3].text.strip() if len(cells) > 3 else "Location not available"
                                
                                # Only add if the part number matches our search
                                if partNo.lower() in part_number.lower():
                                    parts.append([part_number, description, price, location])
                                    logger.info(f"Found matching part in table: {part_number}")
                        except Exception as e:
                            logger.warning(f"Error processing table row: {e}")
                            continue
            
            except Exception as e:
                logger.error(f"Error extracting results: {e}")
                return default_parts
            
            # Return parts or default if none found
            if parts:
                logger.info(f"Found {len(parts)} parts matching {partNo}")
                return parts
            else:
                logger.warning(f"No parts found for {partNo}")
                return default_parts
                
        except Exception as e:
            logger.error(f"Error searching for part: {e}")
            return default_parts
            
    except Exception as e:
        logger.error(f"Error in MyGrant scraper: {e}")
        return default_parts

# For testing purposes
if __name__ == "__main__":
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
        # Test the scraper
        results = MyGrantScraper("2000", driver, logger)

        if results and results[0][0] != "Not Found":
            for part in results:
                print(f"Part: {part[0]}, Description: {part[1]}, Price: {part[2]}, Location: {part[3]}")
        else:
            print("No results found")
    finally:
        driver.quit()