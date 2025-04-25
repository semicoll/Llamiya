import re
import json
from bs4 import BeautifulSoup
from html import unescape
import requests

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

# Add to the main block to support command-line scraping
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scrape-six-stars":
            # Scrape all 6-star operators
            operators = scrape_six_star_operators()
            print(f"Found {len(operators)} 6-star operators:")
            for op in operators:
                print(f"- {op}")
        elif sys.argv[1] == "--get-dialogue" and len(sys.argv) > 2:
            # Get dialogue for a specific operator
            operator_name = sys.argv[2]
            dialogue = get_operator_dialogue(operator_name)
            print(json.dumps(dialogue, indent=2, ensure_ascii=False))
        elif sys.argv[1] == "--bulk-scrape":
            # Bulk scrape all 6-star operator dialogues
            result = bulk_scrape_operator_dialogues()
            output_file = "six_star_dialogues.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"Saved dialogues to {output_file}")
        else:
            # Original functionality
            html_content = sys.argv[1]
            operator_code = sys.argv[2] if len(sys.argv) > 2 else "unknown"
            print(extract_dialogue_from_wiki_html(html_content, operator_code))
    else:
        print("Usage options:")
        print("1. python dialogue.py <html_content> <operator_code>")
        print("2. python dialogue.py --scrape-six-stars")
        print("3. python dialogue.py --get-dialogue <operator_name>")
        print("4. python dialogue.py --bulk-scrape")
