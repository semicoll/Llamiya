from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import subprocess
import json
import re
import sys
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

# Global constants
PAGE_LOAD_TIMEOUT = 20
DEFAULT_WAIT_TIME = 5
MAX_RETRY_ATTEMPTS = 3
OPERATOR_DIR = "operator"

def setup_driver_options():
    """Configure and return optimized Chrome options"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.page_load_strategy = 'eager'  # Don't wait for all resources
    
    prefs = {
        "profile.managed_default_content_settings.images": 2,  # Don't load images
        "disk-cache-size": 52428800,  # 50MB cache
        "profile.default_content_setting_values.notifications": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    return chrome_options

def create_driver():
    """Create and return a new WebDriver instance with optimized settings"""
    try:
        chrome_options = setup_driver_options()
        driver_path = ChromeDriverManager().install()
        print(f"Driver installed at: {driver_path}")
        os.chmod(driver_path, 0o755)
        
        driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        driver.set_script_timeout(PAGE_LOAD_TIMEOUT)
        
        return driver
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        return None

def is_driver_alive(driver):
    """Check if the WebDriver is still responsive with improved error handling"""
    try:
        _ = driver.current_url
        return True
    except:
        return False

@lru_cache(maxsize=32)
def get_operator_url(operator_name):
    """Generate and cache operator URLs"""
    base_url = "https://arknights.fandom.com/wiki/"
    return f"{base_url}{operator_name.replace(' ', '_')}"

def safe_find_element(driver, by, selector, parent=None, wait_time=DEFAULT_WAIT_TIME, optional=False):
    """Safely find an element with retries and proper error handling"""
    element = None
    retry_count = 0
    errors = []
    
    while retry_count < MAX_RETRY_ATTEMPTS and not element:
        try:
            if parent:
                element = parent.find_element(by, selector)
            else:
                if wait_time > 0:
                    element = WebDriverWait(driver, wait_time).until(
                        EC.presence_of_element_located((by, selector))
                    )
                else:
                    element = driver.find_element(by, selector)
            return element
        except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
            retry_count += 1
            errors.append(str(e))
            if retry_count >= MAX_RETRY_ATTEMPTS:
                if not optional:
                    print(f"Failed to find element {selector} after {MAX_RETRY_ATTEMPTS} attempts: {errors}")
                return None
            time.sleep(0.5)
    
    return None

def safe_find_elements(driver, by, selector, parent=None, wait_time=DEFAULT_WAIT_TIME):
    """Safely find elements with retries and proper error handling"""
    elements = []
    retry_count = 0
    
    while retry_count < MAX_RETRY_ATTEMPTS and not elements:
        try:
            if parent:
                elements = parent.find_elements(by, selector)
            else:
                if wait_time > 0:
                    WebDriverWait(driver, wait_time).until(
                        EC.presence_of_element_located((by, selector))
                    )
                elements = driver.find_elements(by, selector)
            return elements
        except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
            retry_count += 1
            if retry_count >= MAX_RETRY_ATTEMPTS:
                print(f"Failed to find elements {selector} after {MAX_RETRY_ATTEMPTS} attempts: {e}")
                return []
            time.sleep(0.5)
    
    return elements

def load_operator_page(driver, operator_name):
    """Load the operator page with optimized error handling and retries"""
    url = get_operator_url(operator_name)
    retry_count = 0
    
    while retry_count < MAX_RETRY_ATTEMPTS:
        try:
            driver.get(url)
            WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="mw-content-text"]/div[1]/aside'))
            )
            return True
        except Exception as e:
            retry_count += 1
            if retry_count >= MAX_RETRY_ATTEMPTS:
                print(f"Failed to load page for {operator_name} after {MAX_RETRY_ATTEMPTS} attempts: {e}")
                return False
            time.sleep(1)
    
    return False

def extract_operator_info_with_selenium(driver, operator_name, reload_page=True):
    """Extract comprehensive operator information from the sidebar with performance optimizations"""
    info_data = {}
    try:
        print(f"Extracting basic info for {operator_name}...")
        
        if reload_page:
            if not load_operator_page(driver, operator_name):
                return info_data
        
        # Get the sidebar element using optimized selector
        sidebar = safe_find_element(driver, By.XPATH, '//*[@id="mw-content-text"]/div[1]/aside')
        if not sidebar:
            return info_data
        
        # Get operator title/name from the sidebar
        title_element = safe_find_element(driver, By.XPATH, 
                                         './/h2[contains(@class, "pi-title")]', 
                                         parent=sidebar, optional=True)
        if title_element:
            info_data["title"] = title_element.text.strip()
        
        # Extract images more efficiently
        extract_images(driver, sidebar, info_data)
        
        # Extract direct fields and section data in a single pass
        extract_sidebar_data(driver, sidebar, info_data)
        
        # Extract related characters
        extract_related_characters(driver, sidebar, info_data, operator_name)
        
        # Organize voice actors (if not already processed)
        organize_voice_actors(info_data)
        
        # Save the data
        save_operator_data(operator_name, {"info": info_data})
        
        print(f"Comprehensive info for {operator_name} saved successfully")
    
    except Exception as e:
        print(f"Error extracting operator info: {e}")
    
    return info_data

def extract_images(driver, sidebar, info_data):
    """Extract images more efficiently"""
    images = {}
    try:
        image_tabs = safe_find_elements(driver, By.XPATH, './/ul[@class="wds-tabs"]/li', parent=sidebar)
        image_contents = safe_find_elements(driver, By.XPATH, './/div[@class="wds-tab__content"]', parent=sidebar)
        
        for i in range(min(len(image_tabs), len(image_contents))):
            try:
                tab_name = image_tabs[i].text.strip()
                if not tab_name:
                    continue
                
                img_element = safe_find_element(driver, By.XPATH, './/img', 
                                            parent=image_contents[i], optional=True)
                if img_element:
                    img_url = img_element.get_attribute('src')
                    images[tab_name] = img_url
            except Exception:
                pass
    except Exception as e:
        print(f"Error extracting images: {e}")
    
    if images:
        info_data["images"] = images

def extract_sidebar_data(driver, sidebar, info_data):
    """Extract all sidebar data in a more efficient manner"""
    # Process direct data items first
    direct_data_items = safe_find_elements(driver, By.XPATH, 
                                         './div[contains(@class, "pi-item pi-data")]', 
                                         parent=sidebar)
    
    for item in direct_data_items:
        try:
            label_elem = safe_find_element(driver, By.XPATH, './/h3', parent=item, optional=True)
            value_elem = safe_find_element(driver, By.XPATH, './/div[@class="pi-data-value"]', 
                                        parent=item, optional=True)
            
            if label_elem and value_elem:
                label = label_elem.text.strip()
                value = value_elem.text.strip()
                
                # Check for list values
                if "<li>" in value_elem.get_attribute("innerHTML"):
                    list_items = safe_find_elements(driver, By.XPATH, './/li', parent=value_elem)
                    if list_items:
                        value = [item.text.strip() for item in list_items]
                
                # Convert label to a standardized key
                key = label.lower().replace(' ', '_').replace('.', '').replace('/', '_')
                info_data[key] = value
        except Exception:
            pass
    
    # Process sections in a single pass
    sections = safe_find_elements(driver, By.XPATH, 
                               './/section[contains(@class, "pi-item pi-group")]', 
                               parent=sidebar)
    
    for section in sections:
        try:
            section_header = safe_find_element(driver, By.XPATH, './/h2', parent=section, optional=True)
            if not section_header:
                continue
                
            section_name = section_header.text.strip()
            section_key = section_name.lower().replace(' ', '_')
            
            # Skip related characters section (processed separately)
            if "related characters" in section_name.lower():
                continue
            
            # Extract section data
            section_data = {}
            data_items = safe_find_elements(driver, By.XPATH, 
                                         './/div[contains(@class, "pi-item pi-data")]', 
                                         parent=section)
            
            for item in data_items:
                try:
                    label_elem = safe_find_element(driver, By.XPATH, './/h3', parent=item, optional=True)
                    value_elem = safe_find_element(driver, By.XPATH, './/div[@class="pi-data-value"]', 
                                                parent=item, optional=True)
                    
                    if label_elem and value_elem:
                        label = label_elem.text.strip()
                        value = value_elem.text.strip()
                        
                        # Check for list values
                        if "<li>" in value_elem.get_attribute("innerHTML"):
                            list_items = safe_find_elements(driver, By.XPATH, './/li', parent=value_elem)
                            if list_items:
                                value = [item.text.strip() for item in list_items]
                        
                        section_data[label.lower().replace(' ', '_')] = value
                except Exception:
                    pass
            
            if section_data:
                info_data[section_key] = section_data
        except Exception:
            pass

def extract_related_characters(driver, sidebar, info_data, operator_name):
    """Extract related characters efficiently"""
    try:
        related_sections = safe_find_elements(driver, By.XPATH, 
                                          './/section[.//caption[contains(text(), "Related Characters")]]', 
                                          parent=sidebar)
        
        if related_sections:
            related_chars = []
            char_links = safe_find_elements(driver, By.XPATH, './/a[contains(@href, "/wiki/")]', 
                                         parent=related_sections[0])
            
            for link in char_links:
                try:
                    href = link.get_attribute("href")
                    if href and "/wiki/" in href:
                        char_name = href.split("/wiki/")[-1].replace("_", " ")
                        char_display = link.text.strip()
                        
                        # Use display name if available, otherwise use URL-derived name
                        if char_display and char_name != operator_name and char_display not in related_chars:
                            related_chars.append(char_display)
                        elif char_name and char_name != operator_name and char_name not in related_chars:
                            related_chars.append(char_name)
                except Exception:
                    pass
            
            if related_chars:
                info_data["related_characters"] = related_chars
    except Exception:
        pass

def organize_voice_actors(info_data):
    """Organize voice actors into a single structure"""
    voice_actors = {}
    voice_keys = ["va_jp", "va_cn", "va_en", "va_kr"]
    
    for key in voice_keys:
        if key in info_data:
            voice_actors[key.replace("va_", "")] = info_data.pop(key)
    
    # Check if we already have character_voices section
    if "character_voices" not in info_data and voice_actors:
        info_data["character_voices"] = voice_actors

def save_operator_data(operator_name, data_to_add):
    """Save operator data with optimized file handling"""
    os.makedirs(OPERATOR_DIR, exist_ok=True)
    file_path = os.path.join(OPERATOR_DIR, f"{operator_name}.json")
    
    try:
        # Load existing data if available
        operator_data = {}
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as json_file:
                operator_data = json.load(json_file)
        
        # Merge new data
        for key, value in data_to_add.items():
            operator_data[key] = value
        
        # Save data
        with open(file_path, "w", encoding="utf-8") as json_file:
            json.dump(operator_data, json_file, ensure_ascii=False, indent=4)
        
        return True
    except Exception as e:
        print(f"Error saving data for {operator_name}: {e}")
        return False

def operator_info(driver, operator_name):
    """Initialize operator data - simplified to reduce redundancy"""
    try:
        if not load_operator_page(driver, operator_name):
            return False
        
        operator_data = {"info": {}}
        save_operator_data(operator_name, operator_data)
        
        print(f"Basic operator data for {operator_name} initialized")
        return True
    except Exception as e:
        print(f"Error initializing data for {operator_name}: {e}")
        return False

def extract_and_write_stats_with_selenium(driver, operator_name, reload_page=True):
    """Extract stats with optimized performance"""
    stats_data = {}
    try:
        print(f"Extracting stats for {operator_name}...")

        if reload_page:
            if not load_operator_page(driver, operator_name):
                return stats_data
        
        # Use more precise selector and retry mechanism
        stats_table = safe_find_element(driver, By.XPATH, '//*[@id="mw-content-text"]/div[1]/table[5]')
        if not stats_table:
            return stats_data
            
        rows = safe_find_elements(driver, By.XPATH, ".//tr", parent=stats_table)
        elite_levels = ["Base", "Max", "Elite 1", "Elite 2", "Trust"]

        for row in rows[1:]:  # Skip header row
            try:
                attribute_name = safe_find_element(driver, By.XPATH, ".//th", parent=row, optional=True)
                if not attribute_name:
                    continue
                    
                stat_cells = safe_find_elements(driver, By.XPATH, ".//td", parent=row)
                stats = [cell.text.strip() for cell in stat_cells]
                
                stats_data[attribute_name.text.strip()] = {
                    level: stats[i] if i < len(stats) else "" 
                    for i, level in enumerate(elite_levels)
                }
            except Exception:
                pass

        if stats_data:
            save_operator_data(operator_name, {"stats": stats_data})
            print(f"Stats data for {operator_name} saved successfully")

    except Exception as e:
        print(f"Error extracting stats: {e}")

    return stats_data

def extract_potential_with_selenium(driver, operator_name, reload_page=True):
    """Extract potential data with optimized performance"""
    potential_data = {"Pot 1": "Base form"}
    
    try:
        print(f"Extracting potential data for {operator_name}...")

        if reload_page:
            if not load_operator_page(driver, operator_name):
                return potential_data
        
        potential_table = safe_find_element(driver, By.XPATH, '//*[@id="mw-content-text"]/div[1]/table[6]')
        if not potential_table:
            return potential_data
            
        rows = safe_find_elements(driver, By.XPATH, ".//tr", parent=potential_table)
        
        pot_counter = 1
        for row in rows[1:]:  # Skip header row
            try:
                row_text = row.text
                # Skip "OR" rows
                if "OR" in row_text and "Potential" not in row_text:
                    continue

                potential_effect = safe_find_element(driver, By.XPATH, ".//td[2]", parent=row, optional=True)
                if potential_effect:
                    potential_key = f"Pot {pot_counter}"
                    potential_data[potential_key] = potential_effect.text.strip()
                    pot_counter += 1
            except Exception:
                pass

        if len(potential_data) > 1:  # If we added any potential data beyond base form
            save_operator_data(operator_name, {"potential": potential_data})
            print(f"Potential data for {operator_name} saved successfully")

    except Exception as e:
        print(f"Error extracting potential data: {e}")

    return potential_data

def extract_promotion_with_selenium(driver, operator_name, reload_page=True):
    """Extract promotion data with optimized performance"""
    promotion_data = {}
    
    try:
        print(f"Extracting promotion data for {operator_name}...")

        if reload_page:
            if not load_operator_page(driver, operator_name):
                return promotion_data
        
        promotion_rows = {
            "Elite 1": {
                "button": '//*[@id="mw-content-text"]/div[1]/table[7]/tbody/tr[2]/td/div/button/span',
                "content": '//*[@id="mw-content-text"]/div[1]/table[7]/tbody/tr[2]/td/div/div[@class="mw-collapsible-content"]'
            },
            "Elite 2": {
                "button": '//*[@id="mw-content-text"]/div[1]/table[7]/tbody/tr[3]/td/div/button/span',
                "content": '//*[@id="mw-content-text"]/div[1]/table[7]/tbody/tr[3]/td/div/div[@class="mw-collapsible-content"]'
            }
        }

        for level, xpaths in promotion_rows.items():
            try:
                toggle_button = safe_find_element(driver, By.XPATH, xpaths["button"], optional=True)
                if toggle_button:
                    driver.execute_script("arguments[0].click();", toggle_button)
                    # Short wait for content to expand
                    time.sleep(0.5)

                content_div = safe_find_element(driver, By.XPATH, xpaths["content"], optional=True)
                if not content_div:
                    continue
                    
                details = content_div.text.strip().replace("\\n", "\n")
                material_images = safe_find_elements(driver, By.XPATH, ".//img", parent=content_div)
                
                # Process materials more efficiently
                materials = extract_promotion_materials(content_div, material_images, details)
                
                promotion_data[level] = {
                    "details": details,
                    "materials": materials
                }
            except Exception as e:
                print(f"Error processing promotion level {level}: {e}")

        if promotion_data:
            save_operator_data(operator_name, {"promotion": promotion_data})
            print(f"Promotion data for {operator_name} saved successfully")

    except Exception as e:
        print(f"Error extracting promotion data: {e}")

    return promotion_data

def extract_promotion_materials(content_div, material_images, details):
    """Extract promotion materials more efficiently"""
    text_items = details.split()
    quantities = [item.strip() for item in text_items 
                 if item.strip().isdigit() or 
                 (len(item.strip()) > 1 and item.strip()[:-1].isdigit() and item.strip()[-1] == 'K')]
    
    # Separate LMD quantities
    lmd_quantity = next((q for q in quantities if q.endswith('K')), None)
    other_quantities = [q for q in quantities if q != lmd_quantity] if lmd_quantity else quantities
    
    # Process image names
    valid_images = []
    for img in material_images:
        img_name = (
            img.get_attribute("alt") or 
            img.get_attribute("data-image-name") or
            img.get_attribute("src").split("/")[-1]
        )
        
        if not img_name or "icon" in img_name.lower():
            continue
        
        if img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
            img_name = img_name.rsplit('.', 1)[0]
            
        valid_images.append(img_name)
    
    # Match materials and quantities
    materials = []
    if valid_images and lmd_quantity:
        materials.append({"name": valid_images[0], "quantity": lmd_quantity})
        
        for i, img_name in enumerate(valid_images[1:]):
            quantity = other_quantities[i] if i < len(other_quantities) else "1"
            materials.append({"name": img_name, "quantity": quantity})
    else:
        for i, img_name in enumerate(valid_images):
            quantity = quantities[i] if i < len(quantities) else "1"
            materials.append({"name": img_name, "quantity": quantity})
            
    return materials

def extract_skills_with_selenium(driver, operator_name, reload_page=True):
    """Extract skills with optimized performance"""
    skills_data = []
    
    try:
        print(f"Extracting skills for {operator_name}...")

        if reload_page:
            if not load_operator_page(driver, operator_name):
                return skills_data
        
        main_content = safe_find_element(driver, By.XPATH, '//*[@id="mw-content-text"]/div[1]')
        if not main_content:
            return skills_data
            
        skill_divs = safe_find_elements(driver, By.XPATH, './div[contains(@class, "mw-collapsible")]', parent=main_content)
        
        for skill_div in skill_divs:
            try:
                # Extract skill name
                skill_name_elem = safe_find_element(driver, By.XPATH, 
                                                 './/b[@style="font-size:14px;"]', 
                                                 parent=skill_div, optional=True)
                if not skill_name_elem or not skill_name_elem.text.strip():
                    continue
                    
                skill_name = skill_name_elem.text.strip()
                print(f"Processing skill: {skill_name}")
                
                # Extract skill image
                skill_image = ""
                img_elem = safe_find_element(driver, By.XPATH, './/img', parent=skill_div, optional=True)
                if img_elem:
                    skill_image = img_elem.get_attribute('src')
                
                # Extract skill types
                types = extract_skill_types(driver, skill_div)
                
                # Expand skill details if needed
                expand_skill_details(driver, skill_div)
                
                # Extract skill levels
                levels = extract_skill_levels(driver, skill_div)
                
                if levels:
                    skill_data = {
                        "name": skill_name,
                        "image": skill_image,
                        "types": types,
                        "levels": levels
                    }
                    skills_data.append(skill_data)
                    print(f"Added skill {skill_name} with {len(levels)} levels")
            
            except Exception as e:
                print(f"Error processing skill div: {e}")
        
        if skills_data:
            save_operator_data(operator_name, {"skills": skills_data})
            print(f"Saved {len(skills_data)} skills for {operator_name}")
        else:
            print(f"No skills were found for {operator_name}")
    
    except Exception as e:
        print(f"Error in skill extraction: {e}")
    
    return skills_data

def extract_skill_types(driver, skill_div):
    """Extract skill types more efficiently"""
    types = []
    try:
        type_container = safe_find_element(driver, By.XPATH, 
                                        './table/tbody/tr/td[2]/div', 
                                        parent=skill_div, optional=True)
        if type_container:
            type_divs = safe_find_elements(driver, By.XPATH, './div', parent=type_container)
            
            for type_div in type_divs:
                type_text = type_div.text.strip()
                if type_text:
                    types.append(type_text)
    except Exception:
        pass
    
    return types

def expand_skill_details(driver, skill_div):
    """Expand skill details if they're collapsed"""
    try:
        toggle_button = safe_find_element(driver, By.XPATH, 
                                       './button/span', 
                                       parent=skill_div, optional=True)
        if toggle_button and "Show effects" in toggle_button.text:
            driver.execute_script("arguments[0].click();", toggle_button)
            time.sleep(0.5)  # Short delay for content to appear
    except Exception:
        pass

def extract_skill_levels(driver, skill_div):
    """Extract skill level details more efficiently"""
    levels = []
    try:
        tbody = safe_find_element(driver, By.XPATH, './div/table/tbody', parent=skill_div, optional=True)
        if not tbody:
            return levels
            
        level_rows = safe_find_elements(driver, By.XPATH, './tr[position() > 1]', parent=tbody)
        
        for row_index, row in enumerate(level_rows):
            try:
                # Determine level based on row index
                if row_index < 7:
                    level = str(row_index + 1)
                else:
                    level = f"M{row_index - 6}"
                
                # Extract data from row cells
                cells = safe_find_elements(driver, By.XPATH, './td', parent=row)
                if len(cells) < 4:
                    continue
                    
                level_data = {
                    "level": level,
                    "effect": cells[0].text.strip(),
                    "initial_sp": cells[1].text.strip(),
                    "sp_cost": cells[2].text.strip(),
                    "duration": cells[3].text.strip()
                }
                levels.append(level_data)
            except Exception as e:
                print(f"Error extracting row {row_index+1}: {e}")
    except Exception as e:
        print(f"Error finding or processing tbody: {e}")
    
    return levels

def extract_skill_upgrade_costs(driver, operator_name, reload_page=True):
    """Extract skill upgrade costs with optimized performance"""
    upgrade_costs = {}
    mastery_costs = {
        "Skill1": {"masteries": {"M1": [], "M2": [], "M3": []}},
        "Skill2": {"masteries": {"M1": [], "M2": [], "M3": []}},
        "Skill3": {"masteries": {"M1": [], "M2": [], "M3": []}}
    }
    
    try:
        print(f"Extracting skill upgrade costs for {operator_name}...")

        if reload_page:
            if not load_operator_page(driver, operator_name):
                return {"regular": upgrade_costs, "mastery": mastery_costs}
        
        # Find skills upgrade section
        skill_upgrades_section = safe_find_element(driver, By.XPATH, 
                                                '//*[@id="mw-content-text"]/div[1]/div[contains(., "Skill upgrades")]',
                                                optional=True)
        if not skill_upgrades_section:
            return {"regular": upgrade_costs, "mastery": mastery_costs}
        
        # Expand the section if needed
        expand_skill_upgrades_section(driver, skill_upgrades_section)
        
        # Find the upgrade table
        upgrade_table = safe_find_element(driver, By.XPATH, 
                                       './/table[contains(@class, "mrfz-wtable")]', 
                                       parent=skill_upgrades_section, optional=True)
        if not upgrade_table:
            return {"regular": upgrade_costs, "mastery": mastery_costs}
        
        # Extract regular skill upgrades
        extract_regular_skill_upgrades(driver, upgrade_table, upgrade_costs)
        
        # Extract mastery upgrades
        extract_mastery_upgrades(driver, upgrade_table, mastery_costs)
        
        if upgrade_costs or any(skill["masteries"] for skill in mastery_costs.values()):
            # Clean mastery costs to remove empty skills
            clean_mastery_costs = {}
            for skill_key, skill_data in mastery_costs.items():
                if any(skill_data["masteries"].values()):
                    clean_mastery_costs[skill_key] = skill_data
            
            save_operator_data(operator_name, {
                "skill_upgrade_costs": upgrade_costs,
                "mastery_costs": clean_mastery_costs
            })
            print(f"Saved skill upgrade costs for {operator_name}")
    
    except Exception as e:
        print(f"Error in skill upgrade costs extraction: {e}")
    
    return {"regular": upgrade_costs, "mastery": mastery_costs}

def expand_skill_upgrades_section(driver, section):
    """Expand skill upgrades section if collapsed"""
    try:
        toggle_button = safe_find_element(driver, By.XPATH, 
                                       './/button/span', 
                                       parent=section, optional=True)
        if toggle_button and "Show" in toggle_button.text:
            driver.execute_script("arguments[0].click();", toggle_button)
            time.sleep(0.5)
    except Exception:
        pass

def extract_regular_skill_upgrades(driver, upgrade_table, upgrade_costs):
    """Extract regular skill upgrade costs more efficiently"""
    for level in range(2, 8):
        try:
            # More flexible XPath to handle different page structures
            level_xpath = f'.//tr[.//th[contains(., "Level {level}") or .//div[@title="Level {level}"] or .//img[contains(@data-image-name, "Rank_{level}")]]]'
            level_row = safe_find_element(driver, By.XPATH, level_xpath, parent=upgrade_table, optional=True)
            
            if not level_row:
                continue
                
            materials_cell = safe_find_element(driver, By.XPATH, './td', parent=level_row, optional=True)
            if not materials_cell:
                continue
                
            materials = extract_materials_from_cell(driver, materials_cell)
            if materials:
                upgrade_costs[str(level)] = materials
        except Exception as e:
            print(f"Error processing level {level}: {e}")

def extract_mastery_upgrades(driver, upgrade_table, mastery_costs):
    """Extract mastery upgrade costs more efficiently"""
    # Find mastery rows
    mastery_xpath = './/tr[.//th[contains(., "Mastery") or .//div[contains(@title, "Mastery")] or ' + \
                  './/img[contains(@data-image-name, "Rank_8") or ' + \
                  'contains(@data-image-name, "Rank_9") or ' + \
                  'contains(@data-image-name, "Rank_10")]]]'
    mastery_rows = safe_find_elements(driver, By.XPATH, mastery_xpath, parent=upgrade_table)
    
    if not mastery_rows:
        return
        
    # Extract all materials
    all_mastery_materials = []
    for row in mastery_rows:
        materials_cell = safe_find_element(driver, By.XPATH, './td', parent=row, optional=True)
        if materials_cell:
            materials = extract_materials_from_cell(driver, materials_cell)
            all_mastery_materials.extend(materials)
    
    # Distribute materials to skills and masteries
    materials_per_mastery = len(all_mastery_materials) // 9  # 3 skills x 3 masteries
    if materials_per_mastery > 0:
        material_index = 0
        skills = ["Skill1", "Skill2", "Skill3"]
        mastery_levels = ["M1", "M2", "M3"]
        
        for skill in skills:
            for mastery in mastery_levels:
                end_index = min(material_index + materials_per_mastery, len(all_mastery_materials))
                materials_for_this_mastery = all_mastery_materials[material_index:end_index]
                mastery_costs[skill]["masteries"][mastery] = materials_for_this_mastery
                material_index = end_index

def extract_materials_from_cell(driver, cell):
    """Extract materials from a table cell more efficiently"""
    materials = []
    material_divs = safe_find_elements(driver, By.XPATH, 
                                    './/div[contains(@style, "display:inline-block; margin:3px")]', 
                                    parent=cell)
    
    for div in material_divs:
        try:
            material_img = safe_find_element(driver, By.XPATH, './/img', parent=div, optional=True)
            if not material_img:
                continue
                
            material_name = material_img.get_attribute("alt")
            
            quantity_div = safe_find_element(driver, By.XPATH, 
                                          './/div[contains(@style, "position:absolute; right:0px; bottom:0px")]/div', 
                                          parent=div, optional=True)
            quantity = quantity_div.text.strip() if quantity_div else "1"
            
            materials.append({
                "name": material_name,
                "quantity": quantity
            })
        except Exception:
            pass
    
    return materials

def extract_talents_with_selenium(driver, operator_name, reload_page=True):
    """Extract talents with optimized performance"""
    talents_data = []
    
    try:
        print(f"Extracting talents for {operator_name}...")

        if reload_page:
            if not load_operator_page(driver, operator_name):
                return talents_data
        
        talent_divs = safe_find_elements(driver, By.XPATH, 
                                      '//*[@id="mw-content-text"]/div[1]/div[contains(@class, "otherskill")]')
        
        for talent_index, div in enumerate(talent_divs):
            try:
                # Get talent name
                talent_name = ""
                talent_header = safe_find_element(driver, By.XPATH, './/th', parent=div, optional=True)
                if talent_header:
                    talent_name = talent_header.text.strip()
                
                if not talent_name:
                    talent_name = f"Talent {talent_index + 1}"
                    
                print(f"Processing talent: {talent_name}")
                
                # Get inner div with talent data
                inner_div = safe_find_element(driver, By.XPATH, 
                                           './/div[contains(@class, "otherskill-inner")]', 
                                           parent=div, optional=True)
                if not inner_div:
                    continue
                    
                elite_levels = []
                potential_levels = []
                
                # Process rows more efficiently
                rows = safe_find_elements(driver, By.XPATH, './/tr', parent=inner_div)
                for row in rows:
                    process_talent_row(driver, row, elite_levels, potential_levels)
                
                if elite_levels or potential_levels:
                    talent_data = {
                        "name": talent_name,
                        "elite_levels": elite_levels,
                    }
                    
                    if potential_levels:
                        talent_data["potential_upgrades"] = potential_levels
                    
                    talents_data.append(talent_data)
                    print(f"Added talent {talent_name} with {len(elite_levels)} elite levels and {len(potential_levels)} potential upgrades")
            
            except Exception as e:
                print(f"Error processing talent div #{talent_index}: {e}")
        
        if talents_data:
            save_operator_data(operator_name, {"talents": talents_data})
            print(f"Saved {len(talents_data)} talents for {operator_name}")
        else:
            print(f"No talents were found for {operator_name}")
    
    except Exception as e:
        print(f"Error in talent extraction: {e}")
    
    return talents_data

def process_talent_row(driver, row, elite_levels, potential_levels):
    """Process a talent table row more efficiently"""
    try:
        level_cell = safe_find_element(driver, By.XPATH, './/td[1]', parent=row, optional=True)
        description_cell = safe_find_element(driver, By.XPATH, './/td[2]', parent=row, optional=True)
        
        if not level_cell or not description_cell:
            return
            
        description = description_cell.text.strip()
        if not description:
            return
            
        # Check if this is a potential upgrade
        is_potential = False
        potential_text = ""
        
        row_text = row.text.lower()
        if "potential" in row_text:
            is_potential = True
            potential_matches = re.findall(r"potential\s+(\d+)", row_text)
            potential_text = f"Potential {potential_matches[0]}" if potential_matches else "Potential Upgrade"
        
        # Check images for potential indicators
        if not is_potential:
            img_elements = safe_find_elements(driver, By.XPATH, './/img', parent=level_cell)
            for img in img_elements:
                img_src = img.get_attribute("src") or ""
                img_alt = img.get_attribute("alt") or ""
                img_title = img.get_attribute("title") or ""
                
                if ("potential" in img_src.lower() or 
                    "potential" in img_alt.lower() or 
                    "potential" in img_title.lower()):
                    is_potential = True
                    potential_text = img_title or img_alt or "Potential Upgrade"
                    break
        
        # Add to appropriate list
        if is_potential:
            potential_levels.append({
                "level": potential_text,
                "description": description
            })
        else:
            level_img = safe_find_element(driver, By.XPATH, './/img', parent=level_cell, optional=True)
            level_title = "Base"
            if level_img:
                level_title = level_img.get_attribute("title") or level_img.get_attribute("alt") or "Base"
                
            elite_levels.append({
                "level": level_title,
                "description": description
            })
    except Exception:
        pass

def cleanup_operator_files(operator_name=None):
    """Remove existing operator JSON files with improved error handling"""
    try:
        if not os.path.exists(OPERATOR_DIR):
            os.makedirs(OPERATOR_DIR, exist_ok=True)
            print(f"Created fresh operator directory at {OPERATOR_DIR}")
            return True
            
        if operator_name:
            file_path = os.path.join(OPERATOR_DIR, f"{operator_name}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Removed existing data file for {operator_name}")
        else:
            file_count = 0
            for filename in os.listdir(OPERATOR_DIR):
                if filename.endswith(".json"):
                    file_path = os.path.join(OPERATOR_DIR, filename)
                    os.remove(file_path)
                    file_count += 1
            if file_count > 0:
                print(f"Cleaned up {file_count} operator files from {OPERATOR_DIR} directory")
            else:
                print(f"No operator files found to clean up in {OPERATOR_DIR} directory")
        return True
    except Exception as e:
        print(f"Error cleaning up operator files: {e}")
        return False

def process_operator(driver, operator_name, clean_before_run=True):
    """Process a single operator with all extraction functions - optimized version"""
    print(f"\nProcessing operator: {operator_name}")
    
    # Clean up existing files if requested
    if clean_before_run:
        cleanup_operator_files(operator_name)
    
    # Check if driver is alive, recreate if needed
    if not is_driver_alive(driver):
        print("WebDriver connection lost. Recreating...")
        try:
            driver.quit()  # Try to clean up
        except:
            pass
        driver = create_driver()
        if not driver:
            print("Failed to recreate WebDriver. Aborting operator processing.")
            return driver, False
    
    try:
        # Load the page once for all extractions
        if not load_operator_page(driver, operator_name):
            print(f"Failed to load page for {operator_name}. Aborting.")
            return driver, False
            
        # Initialize operator data
        operator_info(driver, operator_name)
        
        # Extract all data with reload_page=False to avoid redundant page loads
        extract_operator_info_with_selenium(driver, operator_name, reload_page=False)
        extract_and_write_stats_with_selenium(driver, operator_name, reload_page=False)
        extract_potential_with_selenium(driver, operator_name, reload_page=False)
        extract_promotion_with_selenium(driver, operator_name, reload_page=False)
        extract_skills_with_selenium(driver, operator_name, reload_page=False)
        extract_skill_upgrade_costs(driver, operator_name, reload_page=False)
        extract_talents_with_selenium(driver, operator_name, reload_page=False)
        
        print(f"Completed processing {operator_name}")
        return driver, True
    except Exception as e:
        print(f"Error processing {operator_name}: {e}")
        
        # Check if driver is still alive
        if not is_driver_alive(driver):
            print("WebDriver connection lost during processing. Recreating for next operation.")
            try:
                driver.quit()
            except:
                pass
            driver = create_driver()
        
        return driver, False

def get_all_operators(driver):
    """Get all 6-star operators with optimized loading"""
    operator_names = []
    try:
        url = "https://arknights.fandom.com/wiki/Operator/6-star"
        retry_count = 0
        
        while retry_count < MAX_RETRY_ATTEMPTS:
            try:
                driver.get(url)
                # Wait for operators table to load
                WebDriverWait(driver, DEFAULT_WAIT_TIME).until(
                    EC.presence_of_element_located((By.XPATH, '//table[contains(@class, "mrfz-wtable")]'))
                )
                
                # Extract operator names
                operator_elements = safe_find_elements(driver, By.XPATH, 
                                                   '/html/body/div[4]/div[4]/div[2]/main/div[3]/div/div[1]/div/div/table/tbody/tr/td[2]/a')
                
                operator_names = [element.text for element in operator_elements if element.text]
                if operator_names:
                    break
                    
                retry_count += 1
                time.sleep(1)
            except Exception as e:
                print(f"Error loading operators list (attempt {retry_count+1}): {e}")
                retry_count += 1
                time.sleep(1)
        
        print(f"Found {len(operator_names)} 6-star operators")
        
    except Exception as e:
        print(f"Error getting operator list: {e}")
    
    return operator_names

def process_all_operators(driver, operator_names, clean_before_run=True):
    """Process all operators with better error handling and recovery"""
    if clean_before_run:
        cleanup_operator_files()  # Clean all files before batch processing
    
    successful = 0
    failed = 0
    
    for index, operator_name in enumerate(operator_names):
        print(f"\nProcessing operator {index+1}/{len(operator_names)}: {operator_name}")
        
        try:
            # Process operator
            driver, success = process_operator(driver, operator_name, clean_before_run=False)
            
            if success:
                successful += 1
            else:
                failed += 1
                
            # If driver is None, we need to create a new one
            if not driver:
                print("Creating new WebDriver for next operator...")
                driver = create_driver()
                if not driver:
                    print("Failed to create WebDriver. Exiting batch processing.")
                    break
                    
            # Pause between operators to avoid rate limiting
            time.sleep(1)
                
        except Exception as e:
            print(f"Critical error processing {operator_name}: {e}")
            failed += 1
            
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
            print("Attempting to recreate WebDriver before continuing...")
            driver = create_driver()
            if not driver:
                print("Failed to recreate WebDriver. Exiting batch processing.")
                break
    
    print(f"\nCompleted processing {len(operator_names)} operators.")
    print(f"Successful: {successful}, Failed: {failed}")
    
    return driver

# Main execution code
if __name__ == "__main__":
    try:
        # Check Chrome installation
        chrome_check = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
        if not chrome_check.stdout:
            print("Chrome not found. Installing Chrome dependencies for WSL...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "webdriver-manager", "selenium"])
            print("You may need to install Chrome in WSL. See instructions in output.")
        else:
            print("Chrome found.")
    except Exception as e:
        print(f"Error checking Chrome installation: {e}")

    # Suppress WebDriver Manager logs
    os.environ['WDM_LOG_LEVEL'] = '0'
    os.environ['WDM_PROGRESS_BAR'] = '0'

    # Initialize the central WebDriver
    driver = None
    try:
        # Create the initial WebDriver
        driver = create_driver()
        if not driver:
            print("Failed to create WebDriver. Exiting.")
            sys.exit(1)
        
        # Show Chrome version
        try:
            chrome_version_cmd = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
            chrome_version = chrome_version_cmd.stdout.strip()
            print(f"Detected Chrome version: {chrome_version}")
        except:
            print("Could not detect Chrome version. Make sure Chrome is installed.")
        
        # Get all operators
        operator_names = get_all_operators(driver)
        
        if not operator_names:
            print("No operators found. Exiting.")
            sys.exit(1)
            
        print("\n6-Star Operators:")
        for name in operator_names:
            print(name)
            
        print(f"\nTotal 6-star operators found: {len(operator_names)}")
        
        # Give the user choices for processing
        print("\nChoose an option:")
        print("1. Process a specific operator (by name)")
        print("2. Process all operators")
        print("3. Process only the first operator (for testing)")
        print("4. Clean all operator files and exit")
        
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == '1':
            # Process specific operator
            specific_name = input("Enter the operator name: ").strip()
            clean_option = input("Remove existing data before processing? (y/n, default: y): ").strip().lower()
            clean_before_run = clean_option != 'n'
            
            if specific_name in operator_names:
                driver, _ = process_operator(driver, specific_name, clean_before_run)
            else:
                print(f"Operator '{specific_name}' not found in the list of 6-star operators.")
                similar_names = [name for name in operator_names if specific_name.lower() in name.lower()]
                if similar_names:
                    print("Did you mean one of these?")
                    for name in similar_names:
                        print(f"- {name}")
                    confirmation = input(f"Process {similar_names[0]}? (y/n): ").strip().lower()
                    if confirmation == 'y':
                        driver, _ = process_operator(driver, similar_names[0], clean_before_run)
        
        elif choice == '2':
            # Process all operators
            clean_option = input("Remove all existing data before processing? (y/n, default: y): ").strip().lower()
            clean_before_run = clean_option != 'n'
            
            driver = process_all_operators(driver, operator_names, clean_before_run)
        
        elif choice == '3':
            # Process only the first operator (for testing)
            test_operator = operator_names[0]
            clean_option = input("Remove existing data before processing? (y/n, default: y): ").strip().lower()
            clean_before_run = clean_option != 'n'
            driver, _ = process_operator(driver, test_operator, clean_before_run)
        
        elif choice == '4':
            # Just clean all files and exit
            cleanup_operator_files()
            print("All operator files have been removed. Exiting...")
    
    except Exception as e:
        print(f"Error in main execution: {e}")
    
    finally:
        if driver:
            try:
                driver.quit()
                print("WebDriver closed successfully.")
            except:
                print("Error while closing WebDriver")