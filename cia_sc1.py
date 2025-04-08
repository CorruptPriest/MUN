import requests
from bs4 import BeautifulSoup
import csv
import time
import re

# List of all CIA World Factbook countries.
COUNTRIES = [
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda",
    "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan",
    "Bahamas, The", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia",
    "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi",
    "Cabo Verde", "Cambodia", "Cameroon", "Canada", "Central African Republic", "Chad", "Chile", "China",
    "Colombia", "Comoros", "Congo, Democratic Republic of the", "Congo, Republic of the", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic",
    "Denmark", "Djibouti", "Dominica", "Dominican Republic",
    "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia",
    "Fiji", "Finland", "France",
    "Gabon", "Gambia, The", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana",
    "Haiti", "Holy See (Vatican City)", "Honduras", "Hungary",
    "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy",
    "Jamaica", "Japan", "Jordan",
    "Kazakhstan", "Kenya", "Kiribati", "Korea, North", "Korea, South", "Kosovo", "Kuwait", "Kyrgyzstan",
    "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg",
    "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius", "Mexico", 
    "Micronesia, Federated States of", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar",
    "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Macedonia", "Norway",
    "Oman",
    "Pakistan", "Palau", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal",
    "Qatar",
    "Romania", "Russia", "Rwanda",
    "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe", 
    "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", 
    "Somalia", "South Africa", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria",
    "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", 
    "Turkmenistan", "Tuvalu",
    "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan",
    "Vanuatu", "Vatican City", "Venezuela", "Vietnam",
    "Yemen",
    "Zambia", "Zimbabwe"
]

# Mapping for country names that require special URL slugs.
EXCEPTIONS = {
    "Antigua and Barbuda": "antigua-and-barbuda",
    "Bahamas, The": "bahamas",
    "Gambia, The": "gambia",
    "Holy See (Vatican City)": "vatican-city",
    "Korea, North": "north-korea",
    "Korea, South": "south-korea",
    "Congo, Democratic Republic of the": "congo-democratic-republic-of-the",
    "Congo, Republic of the": "congo",
    "Micronesia, Federated States of": "micronesia",
    "North Macedonia": "north-macedonia",
    "Sao Tome and Principe": "sao-tome-and-principe",
    "Saint Kitts and Nevis": "saint-kitts-and-nevis",
    "Saint Lucia": "saint-lucia",
    "Saint Vincent and the Grenadines": "saint-vincent-and-the-grenadines",
    "Vatican City": "vatican-city"  # sometimes listed as Vatican City
}

BASE_URL = "https://www.cia.gov/the-world-factbook/countries/"

# Extra phrases to clean from the text.
REMOVE_PHRASES = ["competitive ranking", "position"]

def slugify(country_name):
    """
    Convert a country name into a URL-friendly slug.
    """
    if country_name in EXCEPTIONS:
        return EXCEPTIONS[country_name]
    slug = country_name.lower()
    slug = re.sub(r"[,'\(\)]", "", slug)  # remove punctuation
    slug = slug.replace(" ", "-")
    return slug

def clean_text(text):
    """
    Clean the provided text by removing repeating mentions of specific phrases.
    This function removes duplicate occurrences of phrases such as 'competitive ranking'
    and 'position' while retaining the underlying data.
    """
    # Normalize whitespace.
    text = re.sub(r'\s+', ' ', text)
    # List of phrases to deduplicate (case insensitive)
    remove_phrases = ["competitive ranking", "position"]
    for phrase in remove_phrases:
        # Replace multiple consecutive occurrences with a single occurrence
        pattern = re.compile(r'(?i)(?:\b' + re.escape(phrase) + r'\b[\s,;:-]*){2,}')
        text = pattern.sub(phrase + " ", text)
    return text.strip()

def extract_sections(soup):
    """
    Extracts sections from the Factbook page by scanning both h2 and h3 headings.
    Returns a dictionary mapping each unique header to its concatenated text content.
    """
    sections_data = {}
    
    # Get all headings h2 and h3 which typically denote sections/subsections.
    headings = soup.find_all(['h2', 'h3'])
    
    for heading in headings:
        header_text = heading.get_text(strip=True)
        # Only consider headers that are not empty and of a certain minimal length
        if len(header_text) < 3:
            continue
        # Initialize or append to the content for this header.
        content_parts = []
        sibling = heading.find_next_sibling()
        while sibling and sibling.name not in ['h2', 'h3']:
            if sibling.name not in ['script', 'style']:
                part_text = sibling.get_text(" ", strip=True)
                if part_text:
                    content_parts.append(part_text)
            sibling = sibling.find_next_sibling()
        full_section_text = clean_text(" ".join(content_parts))
        if full_section_text:
            # Avoid overwriting if header already exists (append instead).
            if header_text in sections_data:
                sections_data[header_text] += "\n" + full_section_text
            else:
                sections_data[header_text] = full_section_text
    return sections_data

def fetch_country_data(url):
    """
    Fetches the page content from the given URL and extracts the full text
    plus structured section data.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CorporateDataAgent/1.0)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            full_text = clean_text(soup.get_text(separator=" ", strip=True))
            sections = extract_sections(soup)
            return full_text, sections
        else:
            return f"HTTP Error: {response.status_code}", {}
    except Exception as e:
        return f"Error: {e}", {}

def main():
    output_file = "cia_world_factbook_data.csv"
    scraped_data = []  # List to store data for each country.
    all_section_headers = set()  # To collect all unique section headers across pages.

    # First pass: scrape each country's page.
    for country in COUNTRIES:
        slug = EXCEPTIONS.get(country, slugify(country))
        url = f"{BASE_URL}{slug}/"
        print(f"[INFO] Processing {country}: {url}")
        full_text, sections = fetch_country_data(url)
        # Update the union of section headers.
        all_section_headers.update(sections.keys())
        scraped_data.append({
            "Country": country,
            "URL": url,
            "Full_Text": full_text,
            "Sections": sections
        })
        time.sleep(1)  # Respectful delay.

    # Sort section headers for consistent CSV column order.
    sorted_sections = sorted(all_section_headers)

    # Define CSV fieldnames.
    fieldnames = ["Country", "URL", "Full_Text"] + sorted_sections

    # Second pass: write CSV with all columns.
    with open(output_file, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        
        for entry in scraped_data:
            row = {
                "Country": entry["Country"],
                "URL": entry["URL"],
                "Full_Text": entry["Full_Text"]
            }
            # Insert section data for each header column.
            for header in sorted_sections:
                row[header] = entry["Sections"].get(header, "")
            writer.writerow(row)

    print(f"[SUCCESS] CSV generation complete. File created: {output_file}")

if __name__ == "__main__":
    main()
