import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import os
from tqdm import tqdm
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SITE_URL = "https://qubit.autostoresystem.com"
OUTPUT_DIR = "downloaded_js"
CHUNK_PATTERN = re.compile(r'["\']([^"\']+?chunk[^"\']+?\.js)["\']')  # e.g., chunk-abc123.js or vendors~chunk.js

API_PATTERNS = [
    re.compile(r'https?://[^\s\'"]+'),
    re.compile(r'["\']\/api\/[^\s\'"]+'),
    re.compile(r'\.fetch\s*\(|fetch\s*\('),
    re.compile(r'axios\.(get|post|put|delete)\s*\('), 
]

def fetch_html(url, use_selenium=False):
    if not use_selenium:
        return requests.get(url).text
    else:
        # Use Selenium with headless Chrome to load the page with JavaScript execution
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--enable-javascript")
        # Set window size to ensure all content is loaded
        options.add_argument("--window-size=1920,1080")
        
        print(f"Starting headless Chrome for {url}...")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        try:
            print(f"Opening {url} in headless Chrome...")
            driver.get(url)
            
            # Wait for page to be fully loaded
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(("tag name", "body"))
            )
            
            # Wait a bit for React/JS frameworks to render
            time.sleep(3)
            
            # Scroll to trigger lazy-loaded resources
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            print("Page loaded and rendered successfully")
            return driver.page_source
        except Exception as e:
            print(f"Error loading page: {e}")
            return ""
        finally:
            driver.quit()

def extract_script_urls(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    
    # Get scripts with src attributes
    script_urls = [
        urljoin(base_url, tag['src'])
        for tag in soup.find_all("script", src=True)
    ]
    
    # Look for React-specific dynamically loaded scripts
    react_patterns = [
        # Common patterns for React/webpack chunks
        re.compile(r'["\']([^"\']*?(?:chunk|bundle|main|runtime|vendor)[^"\']*?\.js)["\']'),
        # Dynamic imports in modern JS frameworks
        re.compile(r'(import|loadModule|require)\s*\(\s*[\'"]([^"\']+\.js)[\'"]'),
        # Standard JS file references
        re.compile(r'["\']([^"\']+\.js)["\']')
    ]
    
    # Extract script URLs from patterns
    for pattern in react_patterns:
        if pattern.pattern.startswith('(import|loadModule|require)'):
            # For dynamic import pattern
            matches = pattern.findall(html)
            for _, path in matches:
                full_url = urljoin(base_url, path)
                if full_url not in script_urls:
                    script_urls.append(full_url)
        else:
            # For other patterns
            matches = pattern.findall(html)
            for path in matches:
                # Skip data URIs and inline scripts
                if path.startswith('data:') or path.startswith('blob:'):
                    continue
                full_url = urljoin(base_url, path)
                if full_url not in script_urls:
                    script_urls.append(full_url)
    
    return script_urls

def download_script(js_url):
    try:
        response = requests.get(js_url)
        response.raise_for_status()
        parsed_url = urlparse(js_url)
        filename = os.path.basename(parsed_url.path)
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding='utf-8', errors='ignore') as f:
            f.write(response.text)
        return filepath, js_url
    except Exception as e:
        print(f"Failed to download {js_url}: {e}")
        return None, None

def extract_chunk_filenames(js_file_path):
    chunks = set()
    with open(js_file_path, "r", encoding='utf-8', errors='ignore') as f:
        content = f.read()
        matches = CHUNK_PATTERN.findall(content)
        for match in matches:
            chunks.add(match)
    return chunks

def extract_api_calls_from_file(filepath):
    matches = []
    with open(filepath, "r", encoding='utf-8', errors='ignore') as f:
        content = f.read()
        for pattern in API_PATTERNS:
            matches.extend(pattern.findall(content))
    return list(set(matches))

def infer_base_static_url(script_url):
    parsed = urlparse(script_url)
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) >= 2:
        # e.g. /static/js/main.js → /static/js/
        base_path = "/".join(path_parts[:-1]) + "/"
        return f"{parsed.scheme}://{parsed.netloc}/{base_path}"
    return f"{parsed.scheme}://{parsed.netloc}/"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Fetching HTML from {SITE_URL} with headless Chrome...")
    html = fetch_html(SITE_URL, use_selenium=True)

    print("Extracting script URLs...")
    script_urls = extract_script_urls(html, SITE_URL)

    print(f"Downloading {len(script_urls)} JS files...")
    downloaded = []
    base_static_url = ""
    for url in tqdm(script_urls):
        path, js_url = download_script(url)
        if path:
            downloaded.append(path)
            if not base_static_url:
                base_static_url = infer_base_static_url(js_url)

    print("Looking for Webpack-style chunk files...")
    extra_chunk_files = set()
    for js_file in downloaded:
        chunks = extract_chunk_filenames(js_file)
        for chunk in chunks:
            full_url = urljoin(base_static_url, chunk)
            extra_chunk_files.add(full_url)

    print(f"Downloading {len(extra_chunk_files)} additional chunk files...")
    for url in tqdm(extra_chunk_files):
        path, _ = download_script(url)
        if path:
            downloaded.append(path)

    print("Scanning all JS files for API patterns...")
    all_matches = {}
    for filepath in downloaded:
        matches = extract_api_calls_from_file(filepath)
        if matches:
            all_matches[filepath] = matches

    print("\n📊 Discovered API-related references:")
    for file, urls in all_matches.items():
        print(f"\n📄 {file}:")
        for url in urls:
            print(f"  - {url.strip()}")

if __name__ == "__main__":
    main()
