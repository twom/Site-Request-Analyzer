#!/usr/bin/env python3
# React App JS Assets Analyzer
# This script analyzes a React application to extract JavaScript files and scan them for API endpoints

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import os
from tqdm import tqdm
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration
SITE_URL = "https://qubit.autostoresystem.com"
OUTPUT_DIR = "downloaded_js"
CHUNK_PATTERN = re.compile(r'["\']([^"\']+?chunk[^"\']+?\.js)["\']')  # e.g., chunk-abc123.js or vendors~chunk.js

# API pattern constants
API_PREFIX_DOUBLE_QUOTE = '"/api'
API_PREFIX_SINGLE_QUOTE = "'/api"
FETCH_PATTERN = 'fetch('
FETCH_METHOD_PATTERN = '.fetch('

API_PATTERNS = [
    re.compile(r'https?://[^\s\'"]+'),
    re.compile(r'["\']\/api\/[^\s\'"]+'),
    re.compile(r'\.fetch\s*\(|fetch\s*\('),
    re.compile(r'axios\.(get|post|put|delete)\s*\('), 
]

def setup_chrome_options():
    """Configure Chrome options for headless browsing"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--enable-javascript")
    options.add_argument("--window-size=1920,1080")
    return options

def fetch_html_simple(url):
    """Fetch HTML content using requests library"""
    return requests.get(url).text

def fetch_html_selenium(url):
    """Fetch HTML content using Selenium with headless Chrome"""
    options = setup_chrome_options()
    print(f"Starting headless Chrome for {url}...")
    
    # Use the updated ChromeDriverManager implementation
    from selenium.webdriver.chrome.service import Service as ChromeService
    driver = webdriver.Chrome(options=options)
    try:
        print(f"Opening {url} in headless Chrome...")
        driver.get(url)
        
        # Wait for page to be fully loaded
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(("tag name", "body"))
        )
        
        # Wait for React/JS frameworks to render
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

def fetch_html(url, use_selenium=False):
    """Fetch HTML content using either requests or Selenium"""
    if not use_selenium:
        return fetch_html_simple(url)
    else:
        return fetch_html_selenium(url)

def extract_basic_script_urls(soup, base_url):
    """Extract script URLs from script tags with src attributes"""
    return [
        urljoin(base_url, tag['src'])
        for tag in soup.find_all("script", src=True)
    ]

def extract_dynamic_script_urls(html, base_url, existing_urls):
    """Extract dynamically loaded script URLs using regex patterns"""
    script_urls = list(existing_urls)
    
    # Common patterns for React/webpack chunks
    chunk_pattern = re.compile(r'["\']([^"\']*?(?:chunk|bundle|main|runtime|vendor)[^"\']*?\.js)["\']')
    matches = chunk_pattern.findall(html)
    for path in matches:
        if path.startswith('data:') or path.startswith('blob:'):
            continue
        full_url = urljoin(base_url, path)
        if full_url not in script_urls:
            script_urls.append(full_url)
    
    # Dynamic imports in modern JS frameworks
    dynamic_pattern = re.compile(r'(import|loadModule|require)\s*\(\s*[\'"]([^"\']+\.js)[\'"]')
    dynamic_matches = dynamic_pattern.findall(html)
    for _, path in dynamic_matches:
        full_url = urljoin(base_url, path)
        if full_url not in script_urls:
            script_urls.append(full_url)
    
    # Standard JS file references
    std_pattern = re.compile(r'["\']([^"\']+\.js)["\']')
    std_matches = std_pattern.findall(html)
    for path in std_matches:
        if path.startswith('data:') or path.startswith('blob:'):
            continue
        full_url = urljoin(base_url, path)
        if full_url not in script_urls:
            script_urls.append(full_url)
            
    return script_urls

def extract_script_urls(html, base_url):
    """Extract all script URLs from HTML content"""
    soup = BeautifulSoup(html, "html.parser")
    basic_urls = extract_basic_script_urls(soup, base_url)
    all_urls = extract_dynamic_script_urls(html, base_url, basic_urls)
    return all_urls

def download_script(js_url):
    """Download a JavaScript file and save it to the output directory"""
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
    """Extract chunk filenames from a JavaScript file"""
    chunks = set()
    try:
        with open(js_file_path, "r", encoding='utf-8', errors='ignore') as f:
            content = f.read()
            matches = CHUNK_PATTERN.findall(content)
            for match in matches:
                chunks.add(match)
    except Exception as e:
        print(f"Error reading {js_file_path}: {e}")
    return chunks

def process_chunk_files(downloaded_files, base_static_url):
    """Process JS files to find and download chunk files"""
    extra_chunk_files = set()
    
    # Find chunk references
    for js_file in downloaded_files:
        chunks = extract_chunk_filenames(js_file)
        for chunk in chunks:
            full_url = urljoin(base_static_url, chunk)
            extra_chunk_files.add(full_url)
    
    # Download chunk files
    new_files = []
    print(f"Downloading {len(extra_chunk_files)} additional chunk files...")
    for url in tqdm(extra_chunk_files):
        path, _ = download_script(url)
        if path:
            new_files.append(path)
            
    return new_files

def extract_api_calls_from_file(filepath):
    """Extract API calls from a JavaScript file"""
    matches = []
    try:
        with open(filepath, "r", encoding='utf-8', errors='ignore') as f:
            content = f.read()
            for pattern in API_PATTERNS:
                matches.extend(pattern.findall(content))
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
    return list(set(matches))

def infer_base_static_url(script_url):
    """Infer the base URL for static assets from a script URL"""
    parsed = urlparse(script_url)
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) >= 2:
        # e.g. /static/js/main.js → /static/js/
        base_path = "/".join(path_parts[:-1]) + "/"
        return f"{parsed.scheme}://{parsed.netloc}/{base_path}"
    return f"{parsed.scheme}://{parsed.netloc}/"

def analyze_js_files(downloaded_files):
    """Analyze JavaScript files for API patterns"""
    all_matches = {}
    print("Scanning all JS files for API patterns...")
    for filepath in downloaded_files:
        matches = extract_api_calls_from_file(filepath)
        if matches:
            all_matches[filepath] = matches
    return all_matches

def extract_params_from_api_url(url):
    """Extract endpoint and parameters from API URL"""
    # Remove quotes if present
    if url.startswith('"') and url.endswith('"'):
        url = url[1:-1]
    elif url.startswith("'") and url.endswith("'"):
        url = url[1:-1]
    
    # Handle query parameters
    params = {}
    if '?' in url:
        base_url, query_string = url.split('?', 1)
        try:
            # Try to parse parameters from the query string
            param_parts = query_string.split('&')
            for part in param_parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    params[key] = value
                else:
                    params[part] = None  # Parameter without value
        except Exception:
            # If parsing fails, just keep the whole query string
            params['raw_query'] = query_string
        return base_url, params
    
    return url, params

def categorize_by_domain(all_matches):
    """Categorize API calls by domain"""
    domain_map = {}
    backend_calls = {}
    
    for file, urls in all_matches.items():
        for url in urls:
            url = url.strip()
            
            # Determine if this is a backend call or has a domain
            if url.startswith('http://') or url.startswith('https://'):
                # Extract domain from URL
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                
                if domain not in domain_map:
                    domain_map[domain] = {}
                
                if file not in domain_map[domain]:
                    domain_map[domain][file] = []
                
                domain_map[domain][file].append(url)
            elif (url.startswith('"/api') or url.startswith("'/api") or 
                  url.startswith('.fetch') or url == 'fetch('):
                # Backend call
                if file not in backend_calls:
                    backend_calls[file] = []
                
                # For API calls, extract query parameters if present
                if url.startswith('"/api') or url.startswith("'/api"):
                    endpoint, params = extract_params_from_api_url(url)
                    # Store both the original URL and the extracted parameters
                    backend_calls[file].append({
                        'url': url,
                        'endpoint': endpoint,
                        'params': params
                    })
                else:
                    backend_calls[file].append({
                        'url': url,
                        'endpoint': url,
                        'params': {}
                    })
    
    return domain_map, backend_calls

def print_results(all_matches):
    """Print the results of the analysis"""
    domain_map, backend_calls = categorize_by_domain(all_matches)
    
    print("\n📊 Discovered API-related references:")
    
    # Print backend calls first
    print("\n🔹 Backend API Calls:")
    if backend_calls:
        for file, endpoints in backend_calls.items():
            print(f"\n  📄 {os.path.basename(file)}:")
            for endpoint_data in endpoints:
                url = endpoint_data['url']
                params = endpoint_data['params']
                
                # Special formatting for API endpoints
                if url.startswith('"/api') or url.startswith("'/api"):
                    print(f"    - Endpoint: {endpoint_data['endpoint']}")
                    # Print parameters if any exist
                    if params:
                        print(f"      Parameters:")
                        for param_name, param_value in params.items():
                            print(f"        - {param_name}: {param_value}")
                else:
                    print(f"    - {url}")
    else:
        print("  No backend API calls found.")
    
    # Print external domain calls
    print("\n🔹 External API Calls by Domain:")
    if domain_map:
        for domain, files in sorted(domain_map.items()):
            print(f"\n  🌐 Domain: {domain}")
            for file, urls in files.items():
                print(f"    📄 {os.path.basename(file)}:")
                for url in urls:
                    print(f"      - {url}")
    else:
        print("  No external API calls found.")

def main():
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Fetch HTML using Selenium
    print(f"Fetching HTML from {SITE_URL} with headless Chrome...")
    html = fetch_html(SITE_URL, use_selenium=True)
    
    # Extract script URLs
    print("Extracting script URLs...")
    script_urls = extract_script_urls(html, SITE_URL)
    
    # Download script files
    print(f"Downloading {len(script_urls)} JS files...")
    downloaded = []
    base_static_url = ""
    
    for url in tqdm(script_urls):
        path, js_url = download_script(url)
        if path:
            downloaded.append(path)
            if not base_static_url and js_url:
                base_static_url = infer_base_static_url(js_url)
    
    # Process chunk files
    print("Looking for Webpack-style chunk files...")
    chunk_files = process_chunk_files(downloaded, base_static_url)
    downloaded.extend(chunk_files)
    
    # Analyze JS files
    all_matches = analyze_js_files(downloaded)
    
    # Print results
    print_results(all_matches)

if __name__ == "__main__":
    main()
