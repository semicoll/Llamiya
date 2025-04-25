import re
import json
from bs4 import BeautifulSoup
from html import unescape
import requests
import os
import random

def parse_dialogue_table(html_content):
    """
    Parse operator dialogue from HTML table and convert to structured JSON format.
    
    Args:
        html_content (str): HTML content containing the dialogue table
        
    Returns:
        dict: Structured dialogue data
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    rows = soup.select('tbody tr')
    
    dialogue_data = {}
    
    for row in rows:
        # Get row ID (from id attribute or th text)
        row_id = row.get('id', '')
        if not row_id:
            header = row.select_one('th')
            if header:
                row_id = header.get_text(strip=True)
        
        # Skip rows without ID
        if not row_id:
            continue
            
        # Normalize ID to a key format
        key = row_id.replace('#', '').replace(' ', '_').lower()
        
        # Extract dialogue text from the second cell
        text_cell = row.select_one('th + td')
        if not text_cell:
            continue
            
        # Clean up the text, removing HTML tags but preserving important links
        text = text_cell.get_text(strip=True)
        
        # Extract links for reference
        links = []
        for link in text_cell.select('a'):
            link_text = link.get_text(strip=True)
            link_href = link.get('href', '')
            if link_href and link_text:
                links.append({
                    'text': link_text,
                    'href': link_href
                })
        
        # Get audio information
        audio_cell = row.select_one('th + td + td')
        audio_info = {}
        
        if audio_cell:
            # Extract language codes and audio files
            for lang_div in audio_cell.select('div'):
                lang_code = lang_div.select_one('b')
                if lang_code:
                    lang = lang_code.get_text(strip=True)
                    audio_file = None
                    file_link = lang_div.select_one('a')
                    if file_link:
                        audio_file = file_link.get('href', '').split('wpDestFile=')[-1]
                    audio_info[lang] = audio_file
        
        # Add to dialogue data
        dialogue_data[key] = {
            'id': row_id,
            'text': text,
            'links': links,
            'audio': audio_info
        }
    
    return dialogue_data

def format_dialogue_json(dialogue_data, operator_code):
    """
    Format dialogue data into standard JSON structure for an operator.
    
    Args:
        dialogue_data (dict): Parsed dialogue data
        operator_code (str): Operator code/name
        
    Returns:
        dict: Formatted dialogue JSON
    """
    result = {
        "operator": operator_code,
        "dialogue": dialogue_data
    }
    
    return result

def extract_dialogue_from_wiki_html(html_content, operator_code):
    """
    Main function to extract dialogue from wiki HTML and return JSON.
    
    Args:
        html_content (str): HTML content from the wiki page
        operator_code (str): Operator code/name
        
    Returns:
        str: JSON string of dialogue data
    """
    dialogue_data = parse_dialogue_table(html_content)
    formatted_json = format_dialogue_json(dialogue_data, operator_code)
    return json.dumps(formatted_json, indent=2, ensure_ascii=False)

def scrape_six_star_operators(wiki_url="https://arknights.fandom.com/wiki/Operator/6-star"):
    """
    Scrape the names of 6-star operators from the Arknights wiki's dedicated 6-star page.
    
    Args:
        wiki_url (str): URL of the Arknights wiki 6-star operator page
        
    Returns:
        list: List of 6-star operator names
    """
    try:
        response = requests.get(wiki_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        six_star_operators = []
        
        # Use the specific XPath selector to find operator names
        # XPath: //*[@id="mw-content-text"]/div[1]/div/div/table/tbody/tr[1]/td[2]/a
        # Converting XPath to CSS selector format
        op_links = soup.select('#mw-content-text > div:nth-child(1) > div > div > table > tbody > tr > td:nth-child(2) > a')
        
        if op_links:
            for link in op_links:
                operator_name = link.get_text(strip=True)
                if operator_name:
                    six_star_operators.append(operator_name)
        
        # Fallback: If the specific selector didn't work, we'll use the previous methods
        if not six_star_operators:
            # Method 1: Check for gallery items (common format for operator listings)
            gallery_items = soup.select('.gallery-item') or soup.select('.article-table td a')
            
            if gallery_items:
                for item in gallery_items:
                    # Extract operator name from link
                    name_link = item.select_one('a') or item
                    if name_link and name_link.has_attr('title'):
                        operator_name = name_link['title'].strip()
                        if operator_name and not operator_name.startswith("File:"):
                            six_star_operators.append(operator_name)
            
            # Method 2: Fallback to checking tables if gallery approach didn't work
            if not six_star_operators:
                operator_tables = soup.select('table.wikitable, table.article-table')
                
                for table in operator_tables:
                    for row in table.select('tr'):
                        # Skip header rows
                        if row.select_one('th') and not row.select('td'):
                            continue
                        
                        # Look for operator name in the cell with a link
                        for cell in row.select('td'):
                            name_link = cell.select_one('a')
                            if name_link and name_link.has_attr('title'):
                                operator_name = name_link['title'].strip()
                                if operator_name and not operator_name.startswith("File:"):
                                    six_star_operators.append(operator_name)
        
        # Remove duplicates while preserving order
        seen = set()
        six_star_operators = [op for op in six_star_operators if not (op in seen or seen.add(op))]
        
        return six_star_operators
    except Exception as e:
        print(f"Error scraping 6-star operators: {e}")
        return []

def get_operator_dialogue(operator_name, wiki_base_url="https://arknights.fandom.com/wiki"):
    """
    Get dialogue data for a specific operator from the wiki.
    
    Args:
        operator_name (str): Name of the operator
        wiki_base_url (str): Base URL of the Arknights wiki
        
    Returns:
        dict: Dialogue data for the operator
    """
    try:
        # Format the operator name for the URL
        operator_url = f"{wiki_base_url}/{operator_name.replace(' ', '_')}/Dialogue"
        
        response = requests.get(operator_url)
        response.raise_for_status()
        
        # Extract dialogue table from the HTML
        dialogue_data = parse_dialogue_table(response.content)
        return format_dialogue_json(dialogue_data, operator_name)
    except Exception as e:
        print(f"Error getting dialogue for {operator_name}: {e}")
        return {"operator": operator_name, "dialogue": {}, "error": str(e)}

def bulk_scrape_operator_dialogues(rarity="6-star"):
    """
    Scrape dialogue for all operators of a specific rarity.
    
    Args:
        rarity (str): Rarity to scrape, defaults to "6-star"
        
    Returns:
        dict: Dictionary with operator names as keys and their dialogue data as values
    """
    operators = scrape_six_star_operators() if rarity == "6-star" else []
    
    if not operators:
        return {"error": f"No {rarity} operators found"}
    
    result = {}
    for op_name in operators:
        print(f"Scraping dialogue for {op_name}...")
        result[op_name] = get_operator_dialogue(op_name)
    
    return result

def process_operator(operator_name, overwrite=False, display_preview=True):
    """
    Process dialogue data for a specific operator and save it to a file.
    
    Args:
        operator_name (str): Name of the operator
        overwrite (bool): Whether to overwrite existing data
        display_preview (bool): Whether to display a preview of the data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        output_file = f"{operator_name.lower().replace(' ', '_')}_dialogue.json"
        
        # Check if file already exists
        if not overwrite and os.path.exists(output_file):
            print(f"File {output_file} already exists. Skipping...")
            return True
            
        print(f"Fetching dialogue data for {operator_name}...")
        dialogue_data = get_operator_dialogue(operator_name)
        
        if not dialogue_data.get('dialogue'):
            print(f"No dialogue data found for {operator_name}.")
            return False
            
        # Save data to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dialogue_data, f, indent=2, ensure_ascii=False)
            
        print(f"Dialogue data saved to {output_file}")
        
        # Display preview if requested
        if display_preview:
            print("\nPreview of dialogue data:")
            dialogue = dialogue_data.get('dialogue', {})
            keys = list(dialogue.keys())
            
            # Show the first 3 dialogue entries as a preview
            for i, key in enumerate(keys[:3]):
                print(f"\n{dialogue[key]['id']}:")
                print(f"  {dialogue[key]['text'][:100]}..." if len(dialogue[key]['text']) > 100 else f"  {dialogue[key]['text']}")
                
            if len(keys) > 3:
                print(f"\n... and {len(keys) - 3} more dialogue entries.")
                
        return True
    except Exception as e:
        print(f"Error processing {operator_name}: {e}")
        return False

def extract_operator_data(operator_name):
    """
    Extract dialogue data for a specific operator.
    
    Args:
        operator_name (str): Name of the operator
        
    Returns:
        dict: Dialogue data organized by sections
    """
    try:
        dialogue_data = get_operator_dialogue(operator_name)
        return dialogue_data.get('dialogue', {})
    except Exception as e:
        print(f"Error extracting data for {operator_name}: {e}")
        return {}

def get_operator_names(rarity=None):
    """
    Get a list of operator names from the wiki.
    
    Args:
        rarity (str, optional): Rarity filter (e.g., "6-star")
        
    Returns:
        list: List of operator names
    """
    if rarity == "6-star" or rarity is None:
        return scrape_six_star_operators()
    # In the future, we could add support for other rarities
    return []

# Add to the main block to support command-line scraping
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
