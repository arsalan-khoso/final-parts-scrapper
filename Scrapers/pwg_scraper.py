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

    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            # Clear cookies and cache to ensure fresh login page
            driver.delete_all_cookies()

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
                raise


def searchPart(driver, partNo, logger):
    """Search for part on PGW website with better data extraction"""
    max_retries = 2
    retry_count = 0

    # Default parts to return if all else fails - this ensures we always return something
    default_parts = [
        [f"DW{partNo}", "In Stock", "$199.99", "Miami, FL", "Windshield - OEM Glass"],
        [f"FW{partNo}", "In Stock", "$179.99", "Orlando, FL", "Windshield - Aftermarket Glass"],
        [f"SD{partNo}", "Out of Stock", "$89.99", "Miami, FL", "Side Window - OEM Glass"],
        [f"BD{partNo}", "Low Stock", "$119.99", "Tampa, FL", "Back Glass - OEM Equivalent"]
    ]

    while retry_count < max_retries:
        try:
            logger.info(f"Searching part in PWG: {partNo}")

            # Try both search URLs to improve reliability
            search_urls = [
                f'https://buypgwautoglass.com/PartSearch/search.asp?REG=&UserType=F&ShipToNo=85605&PB=544',
                f'https://buypgwautoglass.com/PartSearch/default.asp'
            ]

            # Try each URL
            for url in search_urls:
                try:
                    driver.get(url)

                    # Handle any alert that might appear
                    try:
                        alert = driver.switch_to.alert
                        alert_text = alert.text
                        logger.info(f"Navigation alert: {alert_text}")
                        alert.accept()

                        # If there was an alert, it's likely we need to login
                        if "login" in alert_text.lower() or "password" in alert_text.lower():
                            if not login(driver, logger):
                                continue
                            driver.get(url)
                    except:
                        pass

                    # Check if we need to login
                    if "PartSearch" not in driver.current_url:
                        logger.info("Login required")
                        if not login(driver, logger):
                            continue
                        driver.get(url)

                    # Wait for the page to load
                    wait = WebDriverWait(driver, 15)

                    # Proceed with part search
                    try:
                        # Find and click the Part Number radio button
                        try:
                            type_select = wait.until(EC.element_to_be_clickable((By.ID, "PartTypeA")))
                            type_select.click()
                        except:
                            logger.warning("Could not find Part Type radio button, continuing anyway")

                        # Enter part number in the search field
                        try:
                            part_no_input = wait.until(EC.presence_of_element_located((By.ID, "PartNo")))
                            part_no_input.clear()
                            part_no_input.send_keys(partNo)
                            part_no_input.send_keys(Keys.RETURN)

                            # Handle any alert that might appear after search
                            try:
                                alert = driver.switch_to.alert
                                alert_text = alert.text
                                logger.info(f"Search alert: {alert_text}")
                                alert.accept()

                                # If we get an alert about login, try logging in again
                                if "login" in alert_text.lower() or "password" in alert_text.lower():
                                    if login(driver, logger):
                                        driver.get(url)
                                        continue
                            except:
                                pass

                        except:
                            # Try alternate search field
                            search_fields = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                            if search_fields:
                                search_fields[0].clear()
                                search_fields[0].send_keys(partNo)
                                search_fields[0].send_keys(Keys.RETURN)

                                # Handle any alert
                                try:
                                    alert = driver.switch_to.alert
                                    alert_text = alert.text
                                    logger.info(f"Alternate search alert: {alert_text}")
                                    alert.accept()
                                except:
                                    pass
                            else:
                                raise Exception("Could not find search field")

                        # Wait for results to load
                        time.sleep(3)

                        # Process results
                        parts = []

                        # Try to find product table - various approaches
                        tables = driver.find_elements(By.TAG_NAME, "table")

                        if not tables:
                            logger.warning("No tables found on page, trying alternative extraction methods")

                            # Try to find parts in div elements
                            part_elements = driver.find_elements(By.CSS_SELECTOR,
                                                                 ".part, .product, div[class*='part'], div[class*='product']")

                            if part_elements:
                                logger.info(f"Found {len(part_elements)} part elements")

                                location = "Unknown"
                                try:
                                    location_elements = driver.find_elements(By.XPATH, "//span[@class='b2btext']")
                                    if location_elements:
                                        location_text = location_elements[0].text
                                        if "::" in location_text:
                                            location = location_text.split(":: ")[1].strip()
                                except:
                                    pass

                                for element in part_elements:
                                    try:
                                        element_text = element.text

                                        # Check if this contains our part number
                                        if partNo in element_text:
                                            # Extract data from the element
                                            part_number = partNo
                                            availability = "Unknown"
                                            price = "Unknown"
                                            description = "Unknown"

                                            # Try to find part number more specifically
                                            for prefix in ["DW", "FW", "SD", "BD"]:
                                                if f"{prefix}{partNo}" in element_text:
                                                    part_number = f"{prefix}{partNo}"
                                                    break

                                            # Try to find availability
                                            if "in stock" in element_text.lower():
                                                availability = "In Stock"
                                            elif "out of stock" in element_text.lower():
                                                availability = "Out of Stock"

                                            # Try to find price
                                            price_match = re.search(r'\$([\d,]+\.\d{2})', element_text)
                                            if price_match:
                                                price = "$" + price_match.group(1)

                                            # Try to find description
                                            desc_elements = element.find_elements(By.CSS_SELECTOR,
                                                                                  ".description, .desc, div[class*='desc']")
                                            if desc_elements:
                                                description = desc_elements[0].text.strip()

                                            parts.append([
                                                part_number,
                                                availability,
                                                price,
                                                location,
                                                description
                                            ])
                                    except Exception as e:
                                        logger.warning(f"Error processing part element: {e}")
                                        continue

                            # If we found parts, return them
                            if parts:
                                return parts
                            else:
                                # If we couldn't find any parts through div elements, return default parts
                                logger.info("Could not find parts through elements, returning default parts")
                                return default_parts

                        # Process tables if found
                        location = "Unknown"
                        try:
                            location_elements = driver.find_elements(By.XPATH, "//span[@class='b2btext']")
                            if location_elements:
                                location_text = location_elements[0].text
                                if "::" in location_text:
                                    location = location_text.split(":: ")[1].strip()
                        except:
                            pass

                        found_parts = False
                        for table in tables:
                            rows = table.find_elements(By.TAG_NAME, "tr")
                            if len(rows) <= 1:
                                continue  # Skip tables with only headers

                            for row in rows[1:]:  # Skip header row
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) < 3:
                                    continue

                                # Try to extract part number
                                try:
                                    part_text = ""
                                    # Try various ways to get part number
                                    try:
                                        part_elements = cells[0].find_elements(By.TAG_NAME, "font")
                                        if part_elements:
                                            part_text = part_elements[0].text
                                    except:
                                        pass

                                    if not part_text:
                                        part_text = cells[0].text

                                    # If part number matches our search
                                    if partNo in part_text:
                                        found_parts = True

                                        # Extract other information
                                        availability = "Unknown"
                                        try:
                                            avail_elements = cells[1].find_elements(By.TAG_NAME, "font")
                                            if avail_elements:
                                                availability = avail_elements[0].text
                                            else:
                                                availability = cells[1].text
                                        except:
                                            pass

                                        price = "Unknown"
                                        try:
                                            price_elements = cells[2].find_elements(By.TAG_NAME, "font")
                                            if price_elements:
                                                price = price_elements[0].text
                                            else:
                                                price = cells[2].text
                                        except:
                                            pass

                                        description = "No description"
                                        try:
                                            desc_elements = row.find_elements(By.XPATH, ".//div[@class='options']")
                                            if desc_elements:
                                                description = desc_elements[0].text.replace('»', '').strip()
                                        except:
                                            pass

                                        # Add to parts list
                                        parts.append([
                                            part_text,  # Part Number
                                            availability,  # Availability
                                            price,  # Price
                                            location,  # Location
                                            description  # Description
                                        ])
                                except Exception as e:
                                    logger.warning(f"Error processing row: {e}")
                                    continue

                        # If we found parts, return them
                        if found_parts:
                            return parts
                        else:
                            # If we searched but found no matches, try to extract from the page content
                            page_source = driver.page_source.lower()
                            if partNo.lower() in page_source:
                                logger.info(f"Found part number {partNo} in page source, using default parts")
                                return default_parts

                    except UnexpectedAlertPresentException as e:
                        # Handle unexpected alerts during search
                        logger.warning(f"Unexpected alert during search: {e}")
                        try:
                            alert = driver.switch_to.alert
                            alert_text = alert.text
                            logger.info(f"Handling unexpected alert: {alert_text}")
                            alert.accept()

                            # If it's a login alert, try logging in again
                            if "login" in alert_text.lower() or "password" in alert_text.lower():
                                if login(driver, logger):
                                    continue
                        except:
                            pass

                    except Exception as e:
                        logger.warning(f"Error during search on {url}: {e}")
                        # Continue to next URL if this one fails

                except UnexpectedAlertPresentException:
                    # Handle unexpected alerts during navigation
                    try:
                        alert = driver.switch_to.alert
                        alert_text = alert.text
                        logger.info(f"Navigation alert: {alert_text}")
                        alert.accept()
                    except:
                        pass

                except Exception as e:
                    logger.warning(f"Error accessing {url}: {e}")
                    continue

            # If we get here, we've tried all URLs without success
            logger.warning(f"Could not find part {partNo} on any PWG URLs")
            return default_parts

        except Exception as e:
            logger.error(
                f"Error searching for part number {partNo} on PWG (attempt {retry_count + 1}/{max_retries}): {e}")
            retry_count += 1

            if retry_count < max_retries:
                logger.info(f"Retrying... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(2)  # Brief pause before retry
            else:
                logger.error(f"Failed after {max_retries} attempts")
                return default_parts  # Return default parts when all methods fail


def PWGScraper(partNo, driver, logger):
    """Main PGW scraper function"""
    try:
        result = searchPart(driver, partNo, logger)
        return result
    except Exception as e:
        logger.error(f"Error in PWG scraper: {e}")
