import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import re
from pathlib import Path

def scrape_operator_overview(operator_name):
    """
    Scrapes the overview page for a specific operator from arknights.fandom.com
    
    Args:
        operator_name (str): The name of the operator to scrape
        
    Returns:
        dict: JSON-serializable dictionary containing the operator's overview data
    """
    url = f"https://arknights.fandom.com/wiki/{operator_name}/Overview"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching page: {e}")
        if response.status_code == 404:
            print(f"Operator '{operator_name}' not found. Check the spelling and try again.")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract the overview text (paragraphs before the Gameplay section)
    overview_text = ""
    gameplay_heading = soup.find('span', {'id': 'Gameplay'})
    
    if gameplay_heading:
        # Get all paragraphs before the Gameplay section
        current = gameplay_heading.parent.previous_sibling
        while current:
            if current.name == 'p':
                overview_text = current.get_text().strip() + "\n" + overview_text
            current = current.previous_sibling
    
    # Extract the gameplay description
    gameplay_text = ""
    if gameplay_heading:
        current = gameplay_heading.parent.next_sibling
        while current and (not current.name or current.name != 'h2'):
            if current.name == 'p' or current.name == 'ul':
                gameplay_text += current.get_text().strip() + "\n"
            current = current.next_sibling
    
    # Extract pros and cons
    pros = []
    cons = []
    
    procon_table = soup.find('table', style=lambda s: s and 'table-layout:fixed' in s)
    if procon_table:
        pro_cell = procon_table.find('td', style=lambda s: s and 'background:rgba(0,128,0' in s)
        con_cell = procon_table.find('td', style=lambda s: s and 'background:rgba(128,0,0' in s)
        
        if pro_cell:
            pro_items = pro_cell.find_all('li')
            pros = [item.get_text().strip() for item in pro_items]
        
        if con_cell:
            con_items = con_cell.find_all('li')
            cons = [item.get_text().strip() for item in con_items]
    
    # Get the operator's page title to confirm correct name
    page_title = soup.find('h1', {'class': 'page-header__title'})
    if page_title:
        title_text = page_title.get_text().strip()
        # Extract the operator name from "X's overview"
        actual_name = re.sub(r"'s overview$", "", title_text, flags=re.IGNORECASE)
    else:
        actual_name = operator_name
    
    # Create the result object
    result = {
        "name": actual_name,
        "overview": overview_text.strip(),
        "gameplay": gameplay_text.strip(),
        "pros": pros,
        "cons": cons,
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
    # Create the directory if it doesn't exist
    output_dir = Path("/home/semicolon/Projects/Llamiya/files/operator")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "overview.json"
    
    # Load existing data if the file exists
    if output_file.exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            try:
                all_operators = json.load(f)
            except json.JSONDecodeError:
                all_operators = {}
    else:
        all_operators = {}
    
    # Add or update the operator data
    all_operators[operator_name.lower()] = data
    
    # Save the updated data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_operators, f, indent=2, ensure_ascii=False)
    
    print(f"Data for {operator_name} saved to {output_file}")

def get_operator_list():
    """
    Gets a list of operators from the Arknights fandom wiki
    
    Returns:
        list: A list of operator names
    """
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
        str: The chosen operator name
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
        print("q - Quit")
        
        choice = input("\nEnter a number to select an operator, or an option: ").strip().lower()
        
        if choice == 'q':
            sys.exit(0)
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
        elif choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(operators):
                return operators[idx - 1]
            else:
                print("Invalid selection. Please try again.")
        else:
            print("Invalid choice. Please try again.")

def main():
    if len(sys.argv) < 2:
        print("No operator name provided as argument.")
        operator_name = choose_operator()
    else:
        operator_name = sys.argv[1]
    
    print(f"Scraping overview for {operator_name}...")
    
    operator_data = scrape_operator_overview(operator_name)
    
    if operator_data:
        save_to_json(operator_data, operator_name)
    else:
        print(f"Failed to scrape data for {operator_name}")

if __name__ == "__main__":
    main()
