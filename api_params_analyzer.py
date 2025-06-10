#!/usr/bin/env python3
# React App API Parameter Analyzer
# This script analyzes JS files to find API endpoints and their parameters

import os
import re
from urllib.parse import urlparse, unquote

# Configuration
JS_DIR = "downloaded_js"

def extract_api_endpoints_with_params():
    """Extract API endpoints with query parameters from JavaScript files"""
    api_endpoints = []
    
    # Patterns to find
    # 1. Direct API endpoints with query params in URL strings
    direct_pattern = re.compile(r'["\']\/api\/[^"\'?]+(?:\?[^"\']+)["\']')
    
    # 2. API calls with parameter objects - like fetch('/api/something', { params: {...} })
    url_pattern = re.compile(r'["\']\/api\/[^\'"]+["\']')
    param_pattern = re.compile(r'params\s*:\s*{([^}]+)}')
    
    # 3. URL + searchParams construction - like new URL('/api/something'); url.searchParams.append(...)
    search_params_pattern = re.compile(r'searchParams\.(?:append|set)\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*([^)]+)\)')
    
    # 4. Template literals with parameters - like `/api/something/${param}`
    template_pattern = re.compile(r'`/api/[^`]+`')
    
    # Process each JavaScript file
    for filename in os.listdir(JS_DIR):
        if not filename.endswith('.js') and not filename.endswith('.cjs'):
            continue
            
        filepath = os.path.join(JS_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # 1. Find direct API endpoints with query parameters
                direct_matches = direct_pattern.findall(content)
                for match in direct_matches:
                    api_endpoints.append({
                        'file': filename,
                        'endpoint': match,
                        'type': 'direct'
                    })
                
                # 2. Find URL and nearby param objects
                # This is more complex and requires context analysis
                # Look for URL patterns and then check if there's a params object nearby
                url_matches = url_pattern.findall(content)
                param_matches = param_pattern.findall(content)
                
                # For demonstration, we'll just pair them if both exist
                if url_matches and param_matches:
                    for url in url_matches:
                        for param in param_matches:
                            # Simplified pairing - in reality would need more context
                            api_endpoints.append({
                                'file': filename,
                                'endpoint': url,
                                'params': param.strip(),
                                'type': 'params_object'
                            })
                
                # 3. Find URL with searchParams operations
                url_contexts = re.finditer(r'(new URL\([\'"](?:/api/[^\'"]+)[\'"]\)[^;]+)', content)
                for context_match in url_contexts:
                    context = context_match.group(1)
                    base_url_match = re.search(r'new URL\([\'"](/api/[^\'"]+)[\'"]\)', context)
                    if base_url_match:
                        base_url = base_url_match.group(1)
                        search_params = search_params_pattern.findall(context)
                        if search_params:
                            api_endpoints.append({
                                'file': filename,
                                'endpoint': base_url,
                                'search_params': search_params,
                                'type': 'search_params'
                            })
                
                # 4. Find template literal API calls
                template_matches = template_pattern.findall(content)
                for match in template_matches:
                    if '/api/' in match:
                        api_endpoints.append({
                            'file': filename,
                            'endpoint': match,
                            'type': 'template'
                        })
                
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    return api_endpoints

def parse_query_params(api_url):
    """Parse query parameters from an API URL"""
    # Remove quotes if present
    if api_url.startswith('"') and api_url.endswith('"'):
        api_url = api_url[1:-1]
    elif api_url.startswith("'") and api_url.endswith("'"):
        api_url = api_url[1:-1]
    
    # Split URL and query string
    base_url, query_string = api_url.split('?', 1)
    
    # Parse parameters
    params = {}
    for param in query_string.split('&'):
        if '=' in param:
            key, value = param.split('=', 1)
            # URL decode the value if needed
            params[key] = unquote(value)
        else:
            params[param] = None
            
    return base_url, params

def main():
    # Get all API endpoints with parameters
    api_endpoints = extract_api_endpoints_with_params()
    
    # Parse and organize by endpoint
    endpoint_map = {}
    
    for item in api_endpoints:
        try:
            endpoint, params = parse_query_params(item['endpoint'])
            
            if endpoint not in endpoint_map:
                endpoint_map[endpoint] = {
                    'files': set(),
                    'params': {}
                }
            
            endpoint_map[endpoint]['files'].add(item['file'])
            
            # Add parameters
            for key, value in params.items():
                if key not in endpoint_map[endpoint]['params']:
                    endpoint_map[endpoint]['params'][key] = set()
                
                if value:
                    endpoint_map[endpoint]['params'][key].add(value)
        except Exception as e:
            print(f"Error parsing {item['endpoint']}: {e}")
    
    # Print results
    if endpoint_map:
        print("\n📊 API Endpoints with Query Parameters:\n")
        
        for endpoint, data in sorted(endpoint_map.items()):
            print(f"🔸 {endpoint}")
            
            # Show parameters
            if data['params']:
                print("  Parameters:")
                for param, values in data['params'].items():
                    print(f"    - {param}: {', '.join(sorted(values)) if values and None not in values else '<no value>'}")
            
            # Show files
            print(f"  Found in files:")
            for file in sorted(data['files']):
                print(f"    - {file}")
            
            print("")
    else:
        print("No API endpoints with query parameters found.")

if __name__ == "__main__":
    main()
