from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import subprocess
import json
import re

def extract_range_with_selenium(driver, operator_name):
    range_data = {}
    try:
        base_url = "https://arknights.fandom.com/wiki/"
        url = f"{base_url}{operator_name.replace(' ', '_')}"
        driver.get(url)
        driver.implicitly_wait(5)

        range_table_xpath = '//*[@id="mw-content-text"]/div[1]/table[4]'
        range_table = driver.find_element(By.XPATH, range_table_xpath)

        levels = ["Base", "Elite 1", "Elite 2"]
        for i, level in enumerate(levels):
            try:
                column_xpath = f'{range_table_xpath}/tbody/tr[2]/td[{i + 1}]'
                column = driver.find_element(By.XPATH, column_xpath)
                grid_cells = column.find_elements(By.XPATH, ".//span[@style]")

                range_representation = []
                row = []
                for idx, cell in enumerate(grid_cells):
                    symbol = '○' if 'background: #27A6F3' in cell.get_attribute("style") else '□'
                    row.append(symbol)

                    if (idx + 1) % 5 == 0:
                        range_representation.append(row)
                        row = []

                if row:
                    range_representation.append(row)

                range_data[level] = range_representation

            except Exception as e:
                print(f"Error extracting range for {level}: {e}")
                range_data[level] = "N/A"

    except Exception as e:
        print(f"Error extracting range with Selenium: {e}")

    return range_data

def operator_info(driver, operator_name):
    base_url = "https://arknights.fandom.com/wiki/"
    url = f"{base_url}{operator_name.replace(' ', '_')}"

    try:
        driver.get(url)

        operator_data = {}
        operator_data["range"] = extract_range_with_selenium(driver, operator_name)

        output_dir = "operator"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{operator_name}.json")
        with open(output_path, "w", encoding="utf-8") as json_file:
            json.dump(operator_data, json_file, ensure_ascii=False, indent=4)

        print(f"Operator data for {operator_name} saved to {output_path}")

    except Exception as e:
        print(f"Error scraping data for {operator_name}: {e}")

def extract_and_write_stats_with_selenium(driver, operator_name):
    stats_data = {}
    try:
        print(f"Extracting stats for {operator_name}...")

        base_url = "https://arknights.fandom.com/wiki/"
        url = f"{base_url}{operator_name.replace(' ', '_')}"
        driver.get(url)
        driver.implicitly_wait(5)

        stats_table_xpath = '//*[@id="mw-content-text"]/div[1]/table[5]'
        stats_table = driver.find_element(By.XPATH, stats_table_xpath)
        rows = stats_table.find_elements(By.XPATH, ".//tr")
        elite_levels = ["Base", "Max", "Elite 1", "Elite 2", "Trust"]

        for row in rows[1:]:
            try:
                attribute_name = row.find_element(By.XPATH, ".//th").text.strip()
                stats = [cell.text.strip() for cell in row.find_elements(By.XPATH, ".//td")]
                stats_data[attribute_name] = {level: stats[i] if i < len(stats) else "" for i, level in enumerate(elite_levels)}
            except Exception as e:
                print(f"Error processing row: {e}")

        output_dir = "operator"
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"{operator_name}.json")

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as json_file:
                operator_data = json.load(json_file)
        else:
            operator_data = {}

        operator_data["stats"] = stats_data

        with open(file_path, "w", encoding="utf-8") as json_file:
            json.dump(operator_data, json_file, ensure_ascii=False, indent=4)

        print(f"Stats data for {operator_name} saved to {file_path}")

    except Exception as e:
        print(f"Error extracting stats with Selenium: {e}")

    return stats_data

def extract_potential_with_selenium(driver, operator_name):
    potential_data = {}
    try:
        print(f"Extracting potential data for {operator_name}...")

        base_url = "https://arknights.fandom.com/wiki/"
        url = f"{base_url}{operator_name.replace(' ', '_')}"
        driver.get(url)
        driver.implicitly_wait(5)

        potential_table_xpath = '//*[@id="mw-content-text"]/div[1]/table[6]'
        potential_table = driver.find_element(By.XPATH, potential_table_xpath)
        rows = potential_table.find_elements(By.XPATH, ".//tr")

        potential_data["Pot 1"] = "Base form"
        
        pot_counter = 1
        for row in rows[1:]:
            try:
                if "OR" in row.text and "Potential" not in row.text:
                    continue

                potential_effect = row.find_element(By.XPATH, ".//td[2]").text.strip()
                potential_key = f"Pot {pot_counter}"
                potential_data[potential_key] = potential_effect
                
                pot_counter += 1
            except Exception as e:
                print(f"Error processing potential row: {e}")

        output_dir = "operator"
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"{operator_name}.json")

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as json_file:
                operator_data = json.load(json_file)
        else:
            operator_data = {}

        operator_data["potential"] = potential_data
        with open(file_path, "w", encoding="utf-8") as json_file:
            json.dump(operator_data, json_file, ensure_ascii=False, indent=4)

        print(f"Potential data for {operator_name} saved to {file_path}")

    except Exception as e:
        print(f"Error extracting potential with Selenium: {e}")

    return potential_data

def extract_promotion_with_selenium(driver, operator_name):
    promotion_data = {}
    try:
        print(f"Extracting promotion data for {operator_name}...")

        base_url = "https://arknights.fandom.com/wiki/"
        url = f"{base_url}{operator_name.replace(' ', '_')}"
        driver.get(url)
        driver.implicitly_wait(5)

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
                toggle_button = driver.find_element(By.XPATH, xpaths["button"])
                driver.execute_script("arguments[0].click();", toggle_button)
                time.sleep(1)

                content_div = driver.find_element(By.XPATH, xpaths["content"])
                details = content_div.text.strip()
                details = details.replace("\\n", "\n")
                
                material_images = content_div.find_elements(By.XPATH, ".//img")
                text_items = details.split()
                quantities = []
                
                for item in text_items:
                    item = item.strip()
                    if item.isdigit() or (item[:-1].isdigit() and item[-1] == 'K'):
                        quantities.append(item)
                
                lmd_quantity = None
                other_quantities = []
                
                for quantity in quantities:
                    if quantity.endswith('K') and lmd_quantity is None:
                        lmd_quantity = quantity
                    else:
                        other_quantities.append(quantity)
                
                materials = []
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
                
                if valid_images and lmd_quantity:
                    materials.append({"name": valid_images[0], "quantity": lmd_quantity})
                    
                    for i, img_name in enumerate(valid_images[1:]):
                        if i < len(other_quantities):
                            materials.append({"name": img_name, "quantity": other_quantities[i]})
                        else:
                            materials.append({"name": img_name, "quantity": "1"})
                else:
                    for i, img_name in enumerate(valid_images):
                        if i < len(quantities):
                            materials.append({"name": img_name, "quantity": quantities[i]})
                        else:
                            materials.append({"name": img_name, "quantity": "1"})

                promotion_data[level] = {
                    "details": details,
                    "materials": materials
                }
            except Exception as e:
                print(f"Error processing promotion level {level}: {e}")

        output_dir = "operator"
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"{operator_name}.json")

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as json_file:
                operator_data = json.load(json_file)
        else:
            operator_data = {}

        operator_data["promotion"] = promotion_data
        with open(file_path, "w", encoding="utf-8") as json_file:
            json.dump(operator_data, json_file, ensure_ascii=False, indent=4)

        print(f"Promotion data for {operator_name} saved to {file_path}")

    except Exception as e:
        print(f"Error extracting promotion with Selenium: {e}")

    return promotion_data

def extract_skills_with_selenium(driver, operator_name):
    skills_data = []
    
    try:
        print(f"Extracting skills for {operator_name}...")

        base_url = "https://arknights.fandom.com/wiki/"
        url = f"{base_url}{operator_name.replace(' ', '_')}"
        driver.get(url)
        driver.implicitly_wait(5)
        
        main_content = driver.find_element(By.XPATH, '//*[@id="mw-content-text"]/div[1]')
        skill_divs = main_content.find_elements(By.XPATH, './div[contains(@class, "mw-collapsible")]')
        
        for skill_index, div in enumerate(skill_divs, 2):
            try:
                try:
                    skill_name_elem = div.find_element(By.XPATH, './/b[@style="font-size:14px;"]')
                    skill_name = skill_name_elem.text.strip()
                    if not skill_name:
                        continue
                    print(f"Processing skill: {skill_name}")
                except:
                    continue
                
                try:
                    skill_image = div.find_element(By.XPATH, './/img').get_attribute('src')
                except:
                    skill_image = ""
                
                types = []
                try:
                    type_container = div.find_element(By.XPATH, './table/tbody/tr/td[2]/div')
                    type_divs = type_container.find_elements(By.XPATH, './div')
                    
                    for type_div in type_divs:
                        type_text = type_div.text.strip()
                        if type_text:
                            types.append(type_text)
                except Exception as e:
                    print(f"Error extracting skill types: {e}")
                
                try:
                    toggle_button = div.find_element(By.XPATH, './button/span')
                    toggle_text = toggle_button.text.strip()
                    
                    if "Show effects" in toggle_text:
                        driver.execute_script("arguments[0].click();", toggle_button)
                        time.sleep(1)
                except Exception:
                    pass
                
                levels = []
                
                try:
                    tbody = div.find_element(By.XPATH, './div/table/tbody')
                    level_rows = tbody.find_elements(By.XPATH, './tr[position() > 1]')
                    
                    for row_index, row in enumerate(level_rows):
                        try:
                            if row_index < 7:
                                level = str(row_index + 1)
                            else:
                                level = f"M{row_index - 6}"
                                
                            effect = row.find_element(By.XPATH, './td[1]').text.strip()
                            initial_sp = row.find_element(By.XPATH, './td[2]').text.strip()
                            sp_cost = row.find_element(By.XPATH, './td[3]').text.strip()
                            duration = row.find_element(By.XPATH, './td[4]').text.strip()
                            
                            level_data = {
                                "level": level,
                                "effect": effect,
                                "initial_sp": initial_sp,
                                "sp_cost": sp_cost,
                                "duration": duration
                            }
                            levels.append(level_data)
                        except Exception as e:
                            print(f"Error extracting row {row_index+1}: {e}")
                except Exception as e:
                    print(f"Error finding or processing tbody: {e}")
                
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
                print(f"Error processing skill div #{skill_index}: {e}")
        
        if skills_data:
            output_dir = "operator"
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, f"{operator_name}.json")
            
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as json_file:
                    operator_data = json.load(json_file)
            else:
                operator_data = {}
            
            operator_data["skills"] = skills_data
            
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(operator_data, json_file, ensure_ascii=False, indent=4)
            
            print(f"Saved {len(skills_data)} skills for {operator_name}")
        else:
            print(f"No skills were found for {operator_name}")
    
    except Exception as e:
        print(f"Error in skill extraction: {e}")
    
    return skills_data

def extract_skill_upgrade_costs(driver, operator_name):    
    upgrade_costs = {}
    mastery_costs = {
        "Skill1": {"masteries": {"M1": [], "M2": [], "M3": []}},
        "Skill2": {"masteries": {"M1": [], "M2": [], "M3": []}},
        "Skill3": {"masteries": {"M1": [], "M2": [], "M3": []}}
    }
    
    try:
        print(f"Extracting skill upgrade costs for {operator_name}...")

        base_url = "https://arknights.fandom.com/wiki/"
        url = f"{base_url}{operator_name.replace(' ', '_')}"
        driver.get(url)
        driver.implicitly_wait(5)
        
        try:
            skill_upgrades_section = driver.find_element(By.XPATH, '//*[@id="mw-content-text"]/div[1]/div[contains(., "Skill upgrades")]')
            
            try:
                toggle_button = skill_upgrades_section.find_element(By.XPATH, './/button/span')
                if "Show" in toggle_button.text:
                    driver.execute_script("arguments[0].click();", toggle_button)
                    time.sleep(1)
            except:
                pass
            
            upgrade_table = skill_upgrades_section.find_element(By.XPATH, './/table[contains(@class, "mrfz-wtable")]')
            
            for level in range(2, 8):
                try:
                    level_xpath = f'.//tr[th//div[@title="Level {level}"] or th//img[contains(@data-image-name, "Rank_{level}")]]'
                    level_row = upgrade_table.find_element(By.XPATH, level_xpath)
                    
                    materials_cell = level_row.find_element(By.XPATH, './td')
                    materials = []
                    
                    material_divs = materials_cell.find_elements(By.XPATH, './/div[contains(@style, "display:inline-block; margin:3px")]')
                    
                    for div in material_divs:
                        try:
                            material_img = div.find_element(By.XPATH, './/img')
                            material_name = material_img.get_attribute("alt")
                            
                            quantity_div = div.find_element(By.XPATH, './/div[contains(@style, "position:absolute; right:0px; bottom:0px")]/div')
                            quantity = quantity_div.text.strip()
                            
                            materials.append({
                                "name": material_name,
                                "quantity": quantity
                            })
                        except Exception as e:
                            print(f"Error extracting material for level {level}: {e}")
                    
                    upgrade_costs[str(level)] = materials
                    
                except Exception as e:
                    print(f"Error processing level {level}: {e}")
            
            mastery_rows = upgrade_table.find_elements(By.XPATH, 
                './/tr[th//div[contains(@title, "Mastery")] or ' +
                'th//img[contains(@data-image-name, "Rank_8") or ' +
                'contains(@data-image-name, "Rank_9") or ' +
                'contains(@data-image-name, "Rank_10")]]')
            
            if mastery_rows:
                all_mastery_materials = []
                
                for row in mastery_rows:
                    try:
                        materials_cell = row.find_element(By.XPATH, './td')
                        material_divs = materials_cell.find_elements(By.XPATH, './/div[contains(@style, "display:inline-block; margin:3px")]')
                        
                        for div in material_divs:
                            try:
                                material_img = div.find_element(By.XPATH, './/img')
                                material_name = material_img.get_attribute("alt")
                                
                                quantity_div = div.find_element(By.XPATH, './/div[contains(@style, "position:absolute; right:0px; bottom:0px")]/div')
                                quantity = quantity_div.text.strip()
                                
                                all_mastery_materials.append({
                                    "name": material_name,
                                    "quantity": quantity
                                })
                            except Exception:
                                pass
                    except Exception:
                        pass
                
                materials_per_mastery = len(all_mastery_materials) // 9
                material_index = 0
                skills = ["Skill1", "Skill2", "Skill3"]
                mastery_levels = ["M1", "M2", "M3"]
                
                for skill in skills:
                    for mastery in mastery_levels:
                        end_index = min(material_index + materials_per_mastery, len(all_mastery_materials))
                        materials_for_this_mastery = all_mastery_materials[material_index:end_index]
                        mastery_costs[skill]["masteries"][mastery] = materials_for_this_mastery
                        material_index = end_index
            
            if upgrade_costs or any(skill["masteries"] for skill in mastery_costs.values()):
                output_dir = "operator"
                os.makedirs(output_dir, exist_ok=True)
                file_path = os.path.join(output_dir, f"{operator_name}.json")
                
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as json_file:
                        operator_data = json.load(json_file)
                else:
                    operator_data = {}
                
                operator_data["skill_upgrade_costs"] = upgrade_costs
                
                clean_mastery_costs = {}
                for skill_key, skill_data in mastery_costs.items():
                    if any(skill_data["masteries"].values()):
                        clean_mastery_costs[skill_key] = skill_data
                
                operator_data["mastery_costs"] = clean_mastery_costs
                
                with open(file_path, "w", encoding="utf-8") as json_file:
                    json.dump(operator_data, json_file, ensure_ascii=False, indent=4)
                
                print(f"Saved skill upgrade costs for {operator_name}")
                
        except Exception as e:
            print(f"Error finding or processing skill upgrades section: {e}")
    
    except Exception as e:
        print(f"Error in skill upgrade costs extraction: {e}")
    
    return {"regular": upgrade_costs, "mastery": mastery_costs}

def extract_talents_with_selenium(driver, operator_name):
    talents_data = []
    
    try:
        print(f"Extracting talents for {operator_name}...")

        base_url = "https://arknights.fandom.com/wiki/"
        url = f"{base_url}{operator_name.replace(' ', '_')}"
        driver.get(url)
        driver.implicitly_wait(5)
        
        talent_divs = driver.find_elements(By.XPATH, '//*[@id="mw-content-text"]/div[1]/div[contains(@class, "otherskill")]')
        
        for talent_index, div in enumerate(talent_divs):
            try:
                try:
                    talent_name = div.find_element(By.XPATH, './/th').text.strip()
                    print(f"Processing talent: {talent_name}")
                except:
                    talent_name = f"Talent {talent_index + 1}"
                
                inner_div = div.find_element(By.XPATH, './/div[contains(@class, "otherskill-inner")]')
                elite_levels = []
                potential_levels = []
                rows = inner_div.find_elements(By.XPATH, './/tr')
                
                for row_index, row in enumerate(rows):
                    try:
                        level_cell = row.find_element(By.XPATH, './/td[1]')
                        description_cell = row.find_element(By.XPATH, './/td[2]')
                        description = description_cell.text.strip()
                        
                        is_potential = False
                        potential_text = ""
                        
                        row_text = row.text.lower()
                        if "potential" in row_text:
                            is_potential = True
                            potential_matches = re.findall(r"potential\s+(\d+)", row_text.lower())
                            potential_text = f"Potential {potential_matches[0]}" if potential_matches else "Potential Upgrade"
                        
                        try:
                            img_elements = level_cell.find_elements(By.XPATH, './/img')
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
                        except:
                            pass
                        
                        if is_potential:
                            potential_levels.append({
                                "level": potential_text,
                                "description": description
                            })
                        else:
                            try:
                                level_img = level_cell.find_element(By.XPATH, './/img')
                                level_title = level_img.get_attribute("title") or level_img.get_attribute("alt") or "Base"
                                
                                elite_levels.append({
                                    "level": level_title,
                                    "description": description
                                })
                            except:
                                pass
                        
                    except Exception as e:
                        print(f"Error processing talent level row {row_index}: {e}")
                
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
            output_dir = "operator"
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, f"{operator_name}.json")
            
            if os.path.exists(file_path):
                with open(file_file, "r", encoding="utf-8") as json_file:
                    operator_data = json.load(json_file)
            else:
                operator_data = {}
            
            operator_data["talents"] = talents_data
            
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(operator_data, json_file, ensure_ascii=False, indent=4)
            
            print(f"Saved {len(talents_data)} talents for {operator_name}")
        else:
            print(f"No talents were found for {operator_name}")
    
    except Exception as e:
        print(f"Error in talent extraction: {e}")
    
    return talents_data

# Main execution code
if __name__ == "__main__":
    try:
        chrome_check = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
        if not chrome_check.stdout:
            print("Chrome not found. Installing Chrome dependencies for WSL...")
            %pip install --upgrade pip webdriver-manager selenium
            print("You may need to install Chrome in WSL with: sudo apt update && sudo apt install -y wget unzip fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 libcairo2 libcups2 libcurl3-gnutls libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 xdg-utils && wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && sudo dpkg -i google-chrome-stable_current_amd64.deb && sudo apt-get -f install")
    except Exception as e:
        print(f"Error checking Chrome installation: {e}")

    os.environ['WDM_LOG_LEVEL'] = '0'
    os.environ['WDM_PROGRESS_BAR'] = '0'

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    try:
        chrome_version_cmd = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
        chrome_version = chrome_version_cmd.stdout.strip()
        print(f"Detected Chrome version: {chrome_version}")
    except:
        print("Could not detect Chrome version. Make sure Chrome is installed.")

    # Initialize the central WebDriver
    driver = None
    try:
        driver_path = ChromeDriverManager().install()
        print(f"Driver installed at: {driver_path}")
        
        os.chmod(driver_path, 0o755)
        
        driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
        
        # Scrape the list of 6-star operators
        url = "https://arknights.fandom.com/wiki/Operator/6-star"
        driver.get(url)
        time.sleep(3)
        
        operator_elements = driver.find_elements(By.XPATH, '/html/body/div[4]/div[4]/div[2]/main/div[3]/div/div[1]/div/div/table/tbody/tr/td[2]/a')
        
        operator_names = [element.text for element in operator_elements if element.text]
        
        print("6-Star Operators:")
        for name in operator_names:
            print(name)
            
        print(f"\nTotal 6-star operators found: {len(operator_names)}")
        
        # Example of processing one operator with the central driver
        if operator_names:
            test_operator = operator_names[0]
            print(f"\nProcessing example operator: {test_operator}")
            
            # Extract data using the central driver
            operator_info(driver, test_operator)
            extract_and_write_stats_with_selenium(driver, test_operator)
            extract_potential_with_selenium(driver, test_operator)
            extract_promotion_with_selenium(driver, test_operator)
            extract_skills_with_selenium(driver, test_operator)
            extract_skill_upgrade_costs(driver, test_operator)
            extract_talents_with_selenium(driver, test_operator)
            
            print(f"Completed processing {test_operator}")
        
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        print("If you're using WSL, you may need to install Chrome in the WSL environment")
    finally:
        if driver:
            driver.quit()

