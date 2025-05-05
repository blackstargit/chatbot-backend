# !pip install requests beautifulsoup4 lxml tqdm

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from tqdm import tqdm

# --------- Helper Functions ----------
def get_sitemap_urls(sitemap_url):
    res = requests.get(sitemap_url)
    soup = BeautifulSoup(res.content, 'xml')
    return [loc.text for loc in soup.find_all('loc')]

def clean_text(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for script in soup(['script', 'style', 'noscript']):
        script.decompose()
    return soup.get_text(separator='\n', strip=True)

def get_filename_from_url(folder, url):
    parsed = urlparse(url)
    path = parsed.path.strip('/').replace('/', '_') or 'index'
    return os.path.join(folder, f"{path}.txt")

def save_text_to_file(filename, text):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(text)

def create_combined_file(folder):
    combined_path = os.path.join(folder, "combined.txt")
    with open(combined_path, 'w', encoding='utf-8') as outfile:
        for filename in sorted(os.listdir(folder)):
            if filename.endswith(".txt") and filename != "combined.txt":
                file_path = os.path.join(folder, filename)
                with open(file_path, 'r', encoding='utf-8') as infile:
                    outfile.write(f"\n\n--- {filename} ---\n\n")
                    outfile.write(infile.read())

    print(f"\n📚 Combined all text into: {combined_path}")

# --------- Main Scraper -------------
def scrape_site_from_sitemap(base_url: str):
    parsed_url = urlparse(base_url)
    domain_folder = f'db/{parsed_url.netloc.replace(":", "_")}'

    os.makedirs(domain_folder, exist_ok=True)

    sitemap_url = f"{base_url.rstrip('/')}/sitemap.xml"
    try:
        urls = get_sitemap_urls(sitemap_url)
    except:
        print("⚠️ Unable to fetch sitemap.")
        return

    total_urls = len(urls)
    already_scraped = 0
    newly_scraped = 0
    failed = 0

    print(f"📦 Found {total_urls} URLs in sitemap.")

    for url in tqdm(urls, desc="Scraping pages"):
        file_path = get_filename_from_url(domain_folder, url)

        if os.path.exists(file_path):
            already_scraped += 1
            continue 

        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                text = clean_text(response.text)
                save_text_to_file(file_path, text)
                newly_scraped += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
            failed += 1

    # --------- Show Stats -------------
    print("\n✅ Scraping Complete:")
    print(f"🔢 Total URLs in Sitemap: {total_urls}")
    print(f"📁 Already Scraped:        {already_scraped}")
    print(f"🆕 Newly Scraped:          {newly_scraped}")
    print(f"⚠️ Failed to Scrape:       {failed}")

    # --------- Combine into one file -------------
    create_combined_file(domain_folder)

    return domain_folder

