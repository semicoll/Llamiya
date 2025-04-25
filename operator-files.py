import requests
from lxml import html
import re
import json
import os
import random
import shutil
import importlib.util
import sys

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
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ")
    
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
        # Try to import operator_names from scrapper.py
        try:
            # Check if scrapper.py exists
            scrapper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scrapper.py")
            if os.path.exists(scrapper_path):
                # Load the scrapper module
                spec = importlib.util.spec_from_file_location("scrapper", scrapper_path)
                scrapper = importlib.util.module_from_spec(spec)
                sys.modules["scrapper"] = scrapper
                spec.loader.exec_module(scrapper)
                
                # Check if operator_names is available
                if hasattr(scrapper, "operator_names") and scrapper.operator_names:
                    print(f"Found {len(scrapper.operator_names)} operators from the scrapper module.")
                    use_scrapper_list = input("Use this list? (y/n): ").lower() == 'y'
                    
                    if use_scrapper_list:
                        operators = scrapper.operator_names
                    else:
                        # Fall back to file input
                        operators_file = input("Enter path to operators list file (one operator per line): ")
                        with open(operators_file, 'r') as f:
                            operators = [line.strip() for line in f if line.strip()]
                else:
                    print("No operator names found in the scrapper module.")
                    operators_file = input("Enter path to operators list file (one operator per line): ")
                    with open(operators_file, 'r') as f:
                        operators = [line.strip() for line in f if line.strip()]
            else:
                # Fall back to file input
                print("Scrapper module not found.")
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
            
        except FileNotFoundError as e:
            print(f"Error: File not found - {e}")
        except Exception as e:
            print(f"Error processing operators list: {str(e)}")
    
    elif choice == "3":
        # Try to import operator_names from scrapper for more diverse testing
        try:
            scrapper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scrapper.py")
            if os.path.exists(scrapper_path):
                spec = importlib.util.spec_from_file_location("scrapper", scrapper_path)
                scrapper = importlib.util.module_from_spec(spec)
                sys.modules["scrapper"] = scrapper
                spec.loader.exec_module(scrapper)
                
                if hasattr(scrapper, "operator_names") and scrapper.operator_names:
                    test_operators = scrapper.operator_names[:20]  # Use first 20 operators
                    print("Using operators from scrapper module for random selection.")
                else:
                    # Fallback list
                    test_operators = ["Aak", "Exusiai", "SilverAsh", "Eyjafjalla", "Blaze", "Chen", "Bagpipe"]
            else:
                # Fallback list
                test_operators = ["Aak", "Exusiai", "SilverAsh", "Eyjafjalla", "Blaze", "Chen", "Bagpipe"]
        except Exception:
            # Fallback list
            test_operators = ["Aak", "Exusiai", "SilverAsh", "Eyjafjalla", "Blaze", "Chen", "Bagpipe"]
        
        operator = random.choice(test_operators)
        print(f"Randomly selected operator: {operator}")
        
        overwrite = input("Overwrite existing data? (y/n): ").lower() == 'y'
        process_operator(operator, overwrite)
    
    elif choice == "4":
        print("Exiting...")
    
    else:
        print("Invalid choice. Exiting...")
