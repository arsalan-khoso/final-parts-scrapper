import os
import time
import re
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.common.exceptions import UnexpectedAlertPresentException


def login(driver, logger):
    """Login to Buy PGW Auto Glass website with improved alert handling"""
    logger.info("Logging in to Buy PGW Auto Glass")
    load_dotenv()
    username = os.getenv('PGW_USER')
    password = os.getenv('PGW_PASS')
    
    # Check if credentials are available
    if not username or not password:
        logger.error("PGW credentials not found in environment variables")
        return False

    max_attempts = 1
    for attempt in range(max_attempts):
        try:
            # Go to the login page directly
            driver.get('https://buypgwautoglass.com/')

            # Handle any alert that might be present
            try:
                alert = driver.switch_to.alert
                alert_text = alert.text
                logger.info(f"Alert present: {alert_text}")
                alert.accept()
            except:
                pass

            # Wait for page to load
            wait = WebDriverWait(driver, 20)

            # Check if we're already logged in
            if "PartSearch" in driver.current_url:
                logger.info("Already logged in")
                return True

            # Wait for the username field - this is the most reliable indicator
            try:
                user_input = wait.until(EC.presence_of_element_located((By.ID, 'txtUsername')))
                pass_input = wait.until(EC.presence_of_element_located((By.ID, 'txtPassword')))

                # Clear and fill fields
                user_input.clear()
                pass_input.clear()
                user_input.send_keys(username)
                pass_input.send_keys(password)

                # Find and click login button
                login_button = wait.until(EC.element_to_be_clickable((By.ID, 'button1')))
                login_button.click()

                # Handle any alert that might appear after login
                try:
                    alert = driver.switch_to.alert
                    alert_text = alert.text
                    logger.info(f"Login alert: {alert_text}")
                    alert.accept()
                except:
                    pass

                # Handle the agreement screen if it appears
                try:
                    time.sleep(2)  # Brief pause to let the page update

                    # Look for the I Agree button or any button with "agree" text
                    agree_buttons = driver.find_elements(By.XPATH,
                                                         "//input[@value='I Agree'] | //button[contains(text(), 'Agree')]")
                    if agree_buttons:
                        agree_buttons[0].click()
                        logger.info("Clicked 'I Agree' button")
                    else:
                        logger.info("No agreement screen found")
                except Exception as e:
                    logger.warning(f"Error handling agreement screen: {e}")

                # Wait for successful login
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".header, .menu")))
                    logger.info("Login successful")
                    return True
                except TimeoutException:
                    # Check if we're on the part search page anyway
                    if "PartSearch" in driver.current_url:
                        logger.info("Login successful (detected from URL)")
                        return True
                    else:
                        raise TimeoutException("Login verification failed")

            except TimeoutException:
                # Try alternative login approach if standard elements not found
                logger.warning("Standard login elements not found, trying alternative approach")

                # Try looking for any login form
                inputs = driver.find_elements(By.TAG_NAME, 'input')
                if len(inputs) >= 2:
                    # Look for username and password fields
                    for i in range(len(inputs) - 1):
                        if inputs[i].get_attribute('type') == 'text' and inputs[i + 1].get_attribute(
                                'type') == 'password':
                            inputs[i].clear()
                            inputs[i].send_keys(username)
                            inputs[i + 1].clear()
                            inputs[i + 1].send_keys(password)

                            # Find a button to click
                            buttons = driver.find_elements(By.TAG_NAME, 'button')
                            if buttons:
                                buttons[0].click()

                                # Handle any alert
                                try:
                                    alert = driver.switch_to.alert
                                    alert_text = alert.text
                                    logger.info(f"Alternative login alert: {alert_text}")
                                    alert.accept()
                                except:
                                    pass

                                # Wait for page change
                                time.sleep(5)

                                # Check if login succeeded
                                if "PartSearch" in driver.current_url:
                                    logger.info("Login successful via alternative method")
                                    return True

                if attempt < max_attempts - 1:
                    logger.warning(f"Login attempt {attempt + 1} failed, retrying...")
                    time.sleep(2)
                else:
                    raise Exception("Could not find login elements after multiple attempts")

        except Exception as e:
            if attempt < max_attempts - 1:
                logger.warning(f"Login attempt {attempt + 1} failed with error: {e}, retrying...")
                time.sleep(2)
            else:
                logger.error(f"Login error: {e}")
                return False  # Return False instead of raising exception to handle it gracefully


def searchPart(driver, partNo, logger):
    """Search for part on PGW website using optimized XPath selectors"""
    # Default part data if nothing is found
    default_parts = [[f"Not Found", "Not Found", "Not Found", "Not Found", "Not Found"]]
    
    try:
        # First ensure we're logged in
        if "PartSearch" not in driver.current_url:
            logger.info("Not on search page, attempting to login first")
            if not login(driver, logger):
                logger.error("Login failed, cannot proceed with search")
                return default_parts
                
        logger.info(f"Searching for part: {partNo}")
            
        # Navigate to search page
        search_url = 'https://buypgwautoglass.com/PartSearch/search.asp?REG=&UserType=F&ShipToNo=85605&PB=544'
        driver.get(search_url)
        
        # Handle any alerts
        try:
            alert = driver.switch_to.alert
            alert.accept()
        except:
            pass
            
        # Perform search using XPath
        wait = WebDriverWait(driver, 5)
        
        # Click part type radio button
        try:
            type_select = wait.until(EC.element_to_be_clickable((By.ID, "PartTypeA")))
            type_select.click()
        except:
            logger.warning("Part Type radio button not found")
            
        # Enter part number
        try:
            part_input = wait.until(EC.presence_of_element_located((By.ID, "PartNo")))
            part_input.clear()
            part_input.send_keys(partNo)
            part_input.send_keys(Keys.RETURN)
        except Exception as e:
            logger.error(f"Could not enter part number: {e}")
            return default_parts
            
        # Wait for results
        time.sleep(2)
        
        # Get location information
        location = "Unknown"
        try:
            location_element = driver.find_element(By.XPATH, "//span[@class='b2btext']")
            if location_element:
                location = location_element.text.replace("Branch::", "").strip()
                print(f"Found location: {location}")
        except:
            pass
        
        # Click all "Check" buttons first to maximize available data
        try:
            check_buttons = driver.find_elements(By.CSS_SELECTOR, "button.button.check")
            print(f"Found {len(check_buttons)} check buttons")
            for button in check_buttons:
                button.click()
                time.sleep(0.2)  # Small delay to avoid UI issues
        except:
            pass
            
        # Extract part data using XPath
        parts = []
        
        # First look for colored rows which contain part data
        part_rows = driver.find_elements(By.XPATH, "//tr[contains(@bgcolor, '#ffffff') or contains(@bgcolor, '#C3F4F4')]")
        print(f"Found {len(part_rows)} potential part rows")
        
        for row in part_rows:
            try:
                # Get part number from 3rd column
                part_number = "Unknown"
                try:
                    part_el = row.find_element(By.XPATH, ".//td[3]//font")
                    part_number = part_el.text.strip()
                    print(f"Found part: {part_number}")
                except:
                    pass
                
                # Only process if this part is relevant to our search
                if partNo in part_number:
                    # Get availability from 2nd column
                    availability = "Unknown"
                    try:
                        avail_el = row.find_element(By.XPATH, ".//td[2]")
                        availability = avail_el.text.strip()
                        print(f"Availability: {availability}")
                    except:
                        pass
                    
                    # Get description from options div
                    description = "No description"
                    try:
                        options_el = row.find_element(By.XPATH, ".//div[@class='options']")
                        if options_el:
                            description = options_el.text.replace('»', '').replace('\n', ' - ').strip()
                            print(f"Description: {description}")
                    except:
                        pass
                    
                    # Add to our parts list
                    parts.append([
                        part_number,
                        availability,
                        "See website for pricing",  # Price not directly shown in the HTML
                        location,
                        description
                    ])
                    print(f"Added part to results list: {part_number}")
            except Exception as e:
                logger.warning(f"Error processing row: {e}")
                continue
                
        # Return parts or default if none found
        if parts:
            logger.info(f"Found {len(parts)} parts matching {partNo}")
            return parts
        else:
            logger.warning(f"No parts found for {partNo}")
            return default_parts
            
    except Exception as e:
        logger.error(f"Error in searchPart: {e}")
        return default_parts

def PWGScraper(partNo, driver, logger):
    """Main PGW scraper function"""
    try:
        result = searchPart(driver, partNo, logger)
        return result
    except Exception as e:
        logger.error(f"Error in PWG scraper: {e}")
        return [[f"Not Found", "Not Found", "Not Found", "Not Found", "Not Found"]]  # Return default parts in case of error


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
        # Test the scraper
        results = PWGScraper("2000", driver, logger)

        if results and results[0][0] != "Not Found":
            for part in results:
                print(f"Part: {part[0]}, Availability: {part[1]}, Price: {part[2]}, Location: {part[3]}, Description: {part[4]}")
        else:
            print("No results found")
    finally:
        driver.quit()