import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import re
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import subprocess

def scrape_operator_trivia(operator_name):
    """
    Scrapes the trivia page for a specific operator from arknights.fandom.com
    
    Args:
        operator_name (str): The name of the operator to scrape
        
    Returns:
        dict: JSON-serializable dictionary containing the operator's trivia data
    """
    url = f"https://arknights.fandom.com/wiki/{operator_name}/Trivia"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching page: {e}")
        if response.status_code == 404:
            print(f"Trivia for operator '{operator_name}' not found. Check the spelling and try again.")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract trivia items (usually in bullet points/list items)
    trivia_items = []
    
    # Find the main content area and the top-level unordered list
    content_div = soup.find('div', {'class': 'mw-parser-output'})
    
    if content_div:
        # Try to find the main trivia list using XPath-like selector
        main_ul = content_div.select_one('#mw-content-text > div.mw-parser-output > ul')
        
        if main_ul:
            # Process each top-level list item
            for li in main_ul.find_all('li', recursive=False):
                trivia_text = ""
                
                # Get the main text of this list item (excluding nested lists)
                for content in li.contents:
                    if content.name != 'ul':  # Skip nested lists for now
                        if content.name == 'sup':  # Handle citation references
                            continue  # Skip citation numbers
                        elif content.string:
                            trivia_text += content.string
                        else:
                            trivia_text += content.get_text()
                
                # Clean the text
                trivia_text = trivia_text.strip()
                
                # Handle nested lists
                nested_items = []
                nested_ul = li.find('ul')
                if nested_ul:
                    for nested_li in nested_ul.find_all('li', recursive=True):
                        # Remove citations from nested items
                        for citation in nested_li.find_all('sup', {'class': 'reference'}):
                            citation.decompose()
                        
                        nested_text = nested_li.get_text().strip()
                        if nested_text:
                            nested_items.append(nested_text)
                
                # Add the main item
                if trivia_text:
                    # Remove citation references from text
                    trivia_text = re.sub(r'\[\d+\]', '', trivia_text)
                    item_dict = {"text": trivia_text}
                    
                    # Add nested items if present
                    if nested_items:
                        item_dict["sub_items"] = nested_items
                    
                    trivia_items.append(item_dict)
        
        # If no list was found, try paragraphs as a fallback
        if not trivia_items:
            paragraphs = content_div.find_all('p')
            for p in paragraphs:
                # Remove citations
                for citation in p.find_all('sup', {'class': 'reference'}):
                    citation.decompose()
                
                trivia_text = p.get_text().strip()
                if trivia_text and not trivia_text.startswith("This is"):  # Filter out common intro text
                    trivia_items.append({"text": trivia_text})
    
    # Get the operator's page title to confirm correct name
    page_title = soup.find('h1', {'class': 'page-header__title'})
    if page_title:
        title_text = page_title.get_text().strip()
        # Extract the operator name from "X's trivia"
        actual_name = re.sub(r"'s trivia$", "", title_text, flags=re.IGNORECASE)
    else:
        actual_name = operator_name
    
    # Create the result object
    result = {
        "name": actual_name,
        "trivia_items": trivia_items,
        "url": url
    }
    
    return result

def save_to_json(data, operator_name):
    """
    Save the operator data to a JSON file
    
    Args:
        data (dict): The operator data to save
        operator_name (str): The name of the operator
    """
    # Create the directory for this operator if it doesn't exist
    output_dir = Path(f"./files/{operator_name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "Trivia.json"
    
    # Save the data to the file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Trivia data for {operator_name} saved to {output_file}")

def get_operator_list():
    """
    Gets a list of operators from the Arknights fandom wiki using Selenium
    
    Returns:
        list: A list of operator names
    """
    print("Setting up Chrome for web scraping...")
    
    # Ensure Chrome is installed
    try:
        chrome_check = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
        if not chrome_check.stdout:
            print("Chrome not found. You may need to install Chrome in WSL.")
            print("Run: sudo apt update && sudo apt install -y wget unzip fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 libcairo2 libcups2 libcurl3-gnutls libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 xdg-utils && wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && sudo dpkg -i google-chrome-stable_current_amd64.deb && sudo apt-get -f install")
            # Fall back to the original method
            return get_operator_list_fallback()
    except Exception as e:
        print(f"Error checking Chrome installation: {e}")
        return get_operator_list_fallback()

    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Suppress webdriver-manager logs
    os.environ['WDM_LOG_LEVEL'] = '0'
    os.environ['WDM_PROGRESS_BAR'] = '0'

    operator_names = []
    
    try:
        # Initialize the WebDriver
        driver_path = ChromeDriverManager().install()
        print(f"Driver installed at: {driver_path}")
        
        # Make sure the driver is executable
        os.chmod(driver_path, 0o755)
        
        driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
        
        # Scrape 6-star operators
        url = "https://arknights.fandom.com/wiki/Operator/6-star"
        print(f"Scraping 6-star operator names from {url}...")
        
        driver.get(url)
        time.sleep(3)  # Wait for page to load
        
        operator_elements = driver.find_elements(By.XPATH, 
                                                '/html/body/div[4]/div[4]/div[2]/main/div[3]/div/div[1]/div/div/table/tbody/tr/td[2]/a')
        
        # Extract names and add to the list
        six_star_operators = [element.text for element in operator_elements if element.text]
        operator_names.extend(six_star_operators)
        
        # Also scrape 5-star operators
        # url = "https://arknights.fandom.com/wiki/Operator/5-star"
        # print(f"Scraping 5-star operator names from {url}...")
        
        # driver.get(url)
        # time.sleep(3)
        
        # operator_elements = driver.find_elements(By.XPATH, 
        #                                         '/html/body/div[4]/div[4]/div[2]/main/div[3]/div/div[1]/div/div/table/tbody/tr/td[2]/a')
        
        # five_star_operators = [element.text for element in operator_elements if element.text]
        # operator_names.extend(five_star_operators)
        
        print(f"Found {len(operator_names)} operators in total.")
        
    except Exception as e:
        print(f"Error during web scraping: {e}")
        print("Falling back to alternative method...")
        return get_operator_list_fallback()
    finally:
        # Close the browser
        if 'driver' in locals():
            driver.quit()
    
    return sorted(operator_names)

def get_operator_list_fallback():
    """
    Fallback method to get operator list using BeautifulSoup when Selenium is not available
    
    Returns:
        list: A list of operator names
    """
    print("Using fallback method to get operator list...")
    url = "https://arknights.fandom.com/wiki/Operator_List"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching operator list: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    operator_links = []
    
    # Find the operator links in the tables
    tables = soup.find_all('table', {'class': 'wikitable'})
    for table in tables:
        links = table.find_all('a')
        for link in links:
            if link.get('title') and not link.get('title').startswith('Category:'):
                operator_name = link.get('title')
                if operator_name not in operator_links and not operator_name.endswith('/Gallery'):
                    operator_links.append(operator_name)
    
    return sorted(operator_links)

def choose_operator():
    """
    Let the user choose an operator from a list
    
    Returns:
        str: The chosen operator name or special command
    """
    print("Fetching operator list...")
    operators = get_operator_list()
    
    if not operators:
        print("Could not retrieve operator list. Please enter operator name manually.")
        return input("Enter operator name: ")
    
    # Display operators in a paginated format
    page_size = 10
    total_pages = (len(operators) + page_size - 1) // page_size
    current_page = 1
    
    while True:
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, len(operators))
        
        print(f"\nOperators (Page {current_page}/{total_pages}):")
        for i, op in enumerate(operators[start_idx:end_idx], start=start_idx + 1):
            print(f"{i}. {op}")
        
        print("\nOptions:")
        if current_page > 1:
            print("p - Previous page")
        if current_page < total_pages:
            print("n - Next page")
        print("s - Search for an operator")
        print("a - All operators")
        print("r - Random operator")
        print("q - Quit")
        
        choice = input("\nEnter a number to select an operator, or an option: ").strip().lower()
        
        if choice == 'q':
            sys.exit(0)
        elif choice == 'a':
            return "ALL_OPERATORS"
        elif choice == 'r':
            import random
            random_op = random.choice(operators)
            print(f"Randomly selected: {random_op}")
            return random_op
        elif choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(operators):
                return operators[idx - 1]
            else:
                print("Invalid selection. Please try again.")
        elif choice == 'p' and current_page > 1:
            current_page -= 1
        elif choice == 'n' and current_page < total_pages:
            current_page += 1
        elif choice == 's':
            search_term = input("Enter search term: ").strip().lower()
            matches = [op for op in operators if search_term in op.lower()]
            
            if not matches:
                print("No operators found matching your search term.")
                continue
            
            print("\nMatching operators:")
            for i, op in enumerate(matches, start=1):
                print(f"{i}. {op}")
            
            search_choice = input("\nEnter a number to select an operator, or any other key to return: ")
            if search_choice.isdigit() and 1 <= int(search_choice) <= len(matches):
                return matches[int(search_choice) - 1]
        else:
            print("Invalid choice. Please try again.")

def process_all_operators():
    """
    Process all operators: extract trivia data and save to JSON
    
    Returns:
        int: Number of successfully processed operators
    """
    operators = get_operator_list()
    
    if not operators:
        print("Failed to get operator list.")
        return 0
    
    print(f"Found {len(operators)} operators. Beginning to process...")
    
    successful = 0
    failed = []
    
    for i, operator_name in enumerate(operators, 1):
        print(f"\n[{i}/{len(operators)}] Processing {operator_name}...")
        
        operator_data = scrape_operator_trivia(operator_name)
        
        if operator_data:
            save_to_json(operator_data, operator_name)
            successful += 1
        else:
            print(f"Failed to process {operator_name}")
            failed.append(operator_name)
    
    print(f"\nProcessed {successful} out of {len(operators)} operators successfully.")
    
    if failed:
        print(f"Failed operators ({len(failed)}):")
        for op in failed:
            print(f"- {op}")
    
    return successful

def main():
    print("Arknights Operator Trivia Extractor")
    print("====================================")
    
    if len(sys.argv) < 2:
        print("No operator name provided as argument.")
        operator_choice = choose_operator()
        
        if operator_choice == "ALL_OPERATORS":
            process_all_operators()
            return
        else:
            operator_name = operator_choice
    else:
        operator_name = sys.argv[1]
        if operator_name.lower() == "all":
            process_all_operators()
            return
    
    print(f"Scraping trivia for {operator_name}...")
    
    operator_data = scrape_operator_trivia(operator_name)
    
    if operator_data:
        save_to_json(operator_data, operator_name)
    else:
        print(f"Failed to scrape trivia data for {operator_name}")

if __name__ == "__main__":
    main()
