import requests
from lxml import html
import re
import json
import os
import random
import shutil
import importlib.util
import sys
import subprocess
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def get_operator_names():
    """
    Uses Selenium to scrape operator names from the Arknights Wiki.
    
    Returns:
        list: List of operator names
    """
    print("Setting up Chrome for web scraping...")
    
    # Ensure Chrome is installed
    try:
        chrome_check = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
        if not chrome_check.stdout:
            print("Chrome not found. You may need to install Chrome in WSL.")
            print("Run: sudo apt update && sudo apt install -y wget unzip fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 libcairo2 libcups2 libcurl3-gnutls libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 xdg-utils && wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && sudo dpkg -i google-chrome-stable_current_amd64.deb && sudo apt-get -f install")
            return []
    except Exception as e:
        print(f"Error checking Chrome installation: {e}")
        return []

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
        
        # URL to scrape
        url = "https://arknights.fandom.com/wiki/Operator/6-star"
        
        print(f"Scraping operator names from {url}...")
        
        # Navigate to the page
        driver.get(url)
        time.sleep(3)  # Wait for page to load
        
        # Find all operator name elements using the XPath
        operator_elements = driver.find_elements(By.XPATH, 
                                                '/html/body/div[4]/div[4]/div[2]/main/div[3]/div/div[1]/div/div/table/tbody/tr/td[2]/a')
        
        # Extract the text (operator names) into a list
        operator_names = [element.text for element in operator_elements if element.text]
        
        print(f"Found {len(operator_names)} operators.")
        
    except Exception as e:
        print(f"Error during web scraping: {e}")
    finally:
        # Close the browser
        if 'driver' in locals():
            driver.quit()
    
    return operator_names

def extract_operator_data(operator_name):
    """
    Extracts text from various sections of an operator's wiki page using XPath.
    
    Args:
        operator_name (str): The name of the operator
        
    Returns:
        dict: Dictionary with section names as keys and their content as values
    """
    # Construct the URL
    url = f"https://arknights.fandom.com/wiki/{operator_name}/File"
    
    # XPaths to extract
    xpaths = {
        "Profile": '//*[@id="Profile"]',
        "Clinical_Analysis": '//*[@id="Clinical_Analysis"]',
        "Archive_File_1": '//*[@id="Archive_File_1"]',
        "Archive_File_2": '//*[@id="Archive_File_2"]',
        "Archive_File_3": '//*[@id="Archive_File_3"]',
        "Archive_File_4": '//*[@id="Archive_File_4"]',
        "Promotion_Record": '//*[@id="Promotion_Record"]'
    }
    
    results = {}
    
    try:
        # Send HTTP request
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the HTML content
        tree = html.fromstring(response.content)
        
        # Extract text for each XPath
        for section_name, xpath in xpaths.items():
            elements = tree.xpath(xpath)
            
            if elements:
                # Extract text from paragraphs inside the table's td element
                paragraphs = elements[0].xpath('.//td//p')
                
                if paragraphs:
                    # Join all paragraphs' text
                    text = ' '.join([p.text_content().strip() for p in paragraphs])
                    
                    # Clean the text
                    text = re.sub(r'\s+', ' ', text).strip()
                    results[section_name] = text
                else:
                    results[section_name] = "No paragraph content found"
            else:
                results[section_name] = "Section not found"
        
        return results
    
    except requests.exceptions.RequestException as e:
        return {"error": f"Error fetching data: {str(e)}"}
    except Exception as e:
        return {"error": f"Error processing data: {str(e)}"}

def save_to_json(operator_name, data, overwrite=True):
    """
    Saves the extracted operator data to a JSON file.
    
    Args:
        operator_name (str): Name of the operator
        data (dict): Dictionary containing extracted data
        overwrite (bool): Whether to overwrite existing files
    
    Returns:
        str: Path to the saved file
    """
    # Create directory path
    dir_path = f"./files/{operator_name}"
    file_path = f"{dir_path}/operator_files.json"
    
    # If overwrite is True and the directory exists, remove it first
    if overwrite and os.path.exists(dir_path):
        shutil.rmtree(dir_path)
        print(f"Removed existing data for {operator_name}")
    
    # Create the directory
    os.makedirs(dir_path, exist_ok=True)
    
    # Save data to JSON file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return file_path

def process_operator(operator_name, overwrite=True, display_preview=True):
    """
    Process a single operator: extract data and save to JSON.
    
    Args:
        operator_name (str): Name of the operator
        overwrite (bool): Whether to overwrite existing data
        display_preview (bool): Whether to display a preview of the data
        
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\nProcessing operator: {operator_name}")
    data = extract_operator_data(operator_name)
    
    if "error" in data:
        print(f"Error: {data['error']}")
        return False
    
    # Save data to JSON file
    file_path = save_to_json(operator_name, data, overwrite)
    print(f"Data saved to: {file_path}")
    
    # Display preview if requested
    if display_preview:
        for section, content in data.items():
            print(f"\n{section.replace('_', ' ')}:")
            print("-" * len(section) + "---")
            print(content[:200] + ("..." if len(content) > 200 else ""))
    
    return True

if __name__ == "__main__":
    print("Arknights Operator Data Extractor")
    print("=================================")
    print("1. Extract data for a specific operator")
    print("2. Extract data for all operators")
    print("3. Extract data for a random operator (for testing)")
    print("4. Scrape operator names from the wiki")
    print("5. Exit")
    
    choice = input("\nEnter your choice (1-5): ")
    
    if choice == "1":
        operator = input("Enter operator name (e.g., 'Aak'): ")
        overwrite = input("Overwrite existing data? (y/n): ").lower() == 'y'
        
        success = process_operator(operator, overwrite)
        
        if success:
            print("\nWould you like to see the full content of a specific section?")
            section_choice = input("Enter section name (or 'all' for all sections, 'exit' to quit): ")
            
            data = extract_operator_data(operator)
            while section_choice.lower() not in ['exit', 'quit', 'q']:
                if section_choice.lower() == 'all':
                    for section, content in data.items():
                        print(f"\n{section.replace('_', ' ')}:")
                        print("-" * len(section) + "---")
                        print(content)
                        print()
                elif section_choice in data:
                    print(f"\n{section_choice.replace('_', ' ')}:")
                    print("-" * len(section_choice) + "---")
                    print(data[section_choice])
                else:
                    print(f"Section '{section_choice}' not found.")
                    
                section_choice = input("\nEnter another section name (or 'all' for all sections, 'exit' to quit): ")
    
    elif choice == "2":
        # Get operators list - either from scraping or file input
        use_scraping = input("Scrape operator names from the wiki? (y/n): ").lower() == 'y'
        
        if use_scraping:
            operators = get_operator_names()
            if not operators:
                print("Failed to scrape operator names. Please provide a file with operator names.")
                operators_file = input("Enter path to operators list file (one operator per line): ")
                with open(operators_file, 'r') as f:
                    operators = [line.strip() for line in f if line.strip()]
        else:
            operators_file = input("Enter path to operators list file (one operator per line): ")
            with open(operators_file, 'r') as f:
                operators = [line.strip() for line in f if line.strip()]
            
        print(f"Found {len(operators)} operators in the list.")
        overwrite = input("Overwrite existing data? (y/n): ").lower() == 'y'
        
        successful = 0
        for i, operator in enumerate(operators, 1):
            print(f"\n[{i}/{len(operators)}] Processing {operator}...")
            if process_operator(operator, overwrite, display_preview=False):
                successful += 1
        
        print(f"\nProcessed {successful} out of {len(operators)} operators successfully.")
    
    elif choice == "3":
        # Try to get operators from scraping for more diverse testing
        try:
            test_operators = get_operator_names()
            if not test_operators:
                # Fallback list
                test_operators = ["Aak", "Exusiai", "SilverAsh", "Eyjafjalla", "Blaze", "Chen", "Bagpipe"]
            else:
                test_operators = test_operators[:20]  # Use first 20 operators
                print("Using scraped operators for random selection.")
        except Exception:
            # Fallback list
            test_operators = ["Aak", "Exusiai", "SilverAsh", "Eyjafjalla", "Blaze", "Chen", "Bagpipe"]
        
        operator = random.choice(test_operators)
        print(f"Randomly selected operator: {operator}")
        
        overwrite = input("Overwrite existing data? (y/n): ").lower() == 'y'
        process_operator(operator, overwrite)
    
    elif choice == "4":
        print("Scraping operator names from the wiki...")
        operator_names = get_operator_names()
        
        if operator_names:
            print("\nOperator Names:")
            for i, name in enumerate(operator_names, 1):
                print(f"{i}. {name}")
            print(f"\nTotal operators found: {len(operator_names)}")
            
            # Ask if user wants to save the list
            save_list = input("Save this list to a file? (y/n): ").lower() == 'y'
            if save_list:
                file_path = input("Enter file path to save (default: ./operator_names.txt): ") or "./operator_names.txt"
                with open(file_path, 'w', encoding='utf-8') as f:
                    for name in operator_names:
                        f.write(f"{name}\n")
                print(f"Operator names saved to {file_path}")
        else:
            print("Failed to scrape operator names.")
    
    elif choice == "5":
        print("Exiting...")
    
    else:
        print("Invalid choice. Exiting...")
