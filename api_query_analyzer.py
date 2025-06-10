#!/usr/bin/env python3
# React App API Query Parameter Analyzer
# This script focuses on extracting and analyzing query parameters from API endpoints

import os
import re
import json
from urllib.parse import urlparse, unquote, parse_qs
from collections import defaultdict

# Configuration
JS_DIR = "downloaded_js"
EXPORT_FILE = "api_query_results.json"

class APIQueryAnalyzer:
    def __init__(self, js_dir=JS_DIR):
        self.js_dir = js_dir
        self.results = {
            'backend_endpoints': defaultdict(lambda: {
                'files': set(),
                'params': defaultdict(set),
                'template_params': set(),
                'dynamic_patterns': set(),
                'http_methods': set(),  # Store detected HTTP methods for each endpoint
                'request_bodies': [],   # Store detected request body structures
                'responses': []         # Store detected response structures
            })
        }
    
    def analyze_all_files(self):
        """Analyze all JS files in the directory"""
        print(f"Analyzing JS files in {self.js_dir} for API query parameters...")
        for filename in os.listdir(self.js_dir):
            if not filename.endswith(('.js', '.cjs')):
                continue
            
            filepath = os.path.join(self.js_dir, filename)
            self.analyze_file(filepath, filename)
        
        # Convert sets to lists for JSON serialization
        serializable_results = self._prepare_for_serialization()
        return serializable_results
    
    def _prepare_for_serialization(self):
        """Convert sets to lists for JSON serialization"""
        result = {}
        for endpoint, data in self.results['backend_endpoints'].items():
            result[endpoint] = {
                'files': list(data['files']),
                'params': {k: list(v) for k, v in data['params'].items()},
                'template_params': list(data['template_params']),
                'dynamic_patterns': list(data['dynamic_patterns']),
                'http_methods': list(data['http_methods']) if data['http_methods'] else ['GET'],  # Default to GET if no method specified
                'request_bodies': data['request_bodies'],
                'responses': data['responses']
            }
        return {'backend_endpoints': result}
    
    def analyze_file(self, filepath, filename):
        """Analyze a single JS file for API endpoints with query parameters"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Process the file content with different strategies
                self._find_static_query_params(content, filename)
                self._find_template_literal_params(content, filename)
                self._find_search_params_usage(content, filename)
                self._find_axios_fetch_params(content, filename)
                
        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")
    
    def _find_static_query_params(self, content, filename):
        """Find static query parameters in API calls"""
        # Pattern for '/api/something?param=value' style URLs
        pattern = re.compile(r'[\'"`]/api/[^\'"`?]+\?([^\'"`]+)[\'"`]')
        
        matches = pattern.findall(content)
        for query_string in matches:
            # Extract the full URL to get the endpoint
            url_match = re.search(r'[\'"`](/api/[^\'"`?]+)\?[^\'"`]+[\'"`]', content)
            if url_match:
                endpoint = url_match.group(1)
                
                # Add file reference
                self.results['backend_endpoints'][endpoint]['files'].add(filename)
                
                # Parse query parameters
                try:
                    params = self._parse_query_string(query_string)
                    for param, values in params.items():
                        for value in values:
                            self.results['backend_endpoints'][endpoint]['params'][param].add(value)
                except Exception as e:
                    print(f"Error parsing query string '{query_string}': {e}")
    
    def _find_template_literal_params(self, content, filename):
        """Find template literals with dynamic query parameters"""
        # Find all template literals containing /api/ paths - capture the whole template
        template_pattern = re.compile(r'`([^`]*?/api/[^`]*?)`')
        
        # Also look for HTTP methods near template literals
        method_keywords = {
            'get': 'GET',
            'post': 'POST',
            'put': 'PUT',
            'delete': 'DELETE',
            'patch': 'PATCH'
        }
        
        for match in template_pattern.finditer(content):
            template_content = match.group(1)
            context_before = content[max(0, match.start() - 30):match.start()]
            
            # Try to detect HTTP method from context
            http_method = "GET"  # Default method
            for keyword, method in method_keywords.items():
                if keyword in context_before.lower():
                    http_method = method
                    break
            
            # Check if this template has dynamic parts in the endpoint path
            if '${' in template_content and '}' in template_content:
                # Extract the base path pattern up to the first dynamic part
                parts = template_content.split('${', 1)
                base_path = parts[0]
                
                if base_path.startswith('/api/'):
                    # This is a proper API endpoint with dynamic parts
                    # Create normalized endpoint key by replacing dynamic parts with placeholders
                    normalized_endpoint = re.sub(r'\${[^}]+}', '{PARAM}', template_content)
                    
                    # Full template content processing to capture complete expressions
                    template_vars = []
                    # Match ${...} expressions, ensuring we capture the full expression even if complex
                    var_matches = re.finditer(r'\${([^}]+)}', template_content)
                    for var_match in var_matches:
                        var_expr = var_match.group(1)
                        template_vars.append(var_expr)
                    
                    # Add file reference
                    self.results['backend_endpoints'][normalized_endpoint]['files'].add(filename)
                    self.results['backend_endpoints'][normalized_endpoint]['http_methods'].add(http_method)
                    
                    # Add template parameters
                    for var in template_vars:
                        self.results['backend_endpoints'][normalized_endpoint]['template_params'].add(var)
                    
            # Look for standard query parameters in the template
            if '/api/' in template_content and '?' in template_content:
                # Extract the path and query string parts
                path_parts = template_content.split('?', 1)
                endpoint = path_parts[0]
                query_template = path_parts[1] if len(path_parts) > 1 else ''
                
                if not endpoint.startswith('/api/'):
                    continue
                
                # Add file reference
                self.results['backend_endpoints'][endpoint]['files'].add(filename)
                
                if query_template:
                    # Extract template variables ${var} from the query string
                    template_vars = re.findall(r'\${([^}]+)}', query_template)
                    for var in template_vars:
                        self.results['backend_endpoints'][endpoint]['template_params'].add(var)
                    
                    # Try to extract static params if they exist alongside template vars
                    try:
                        # Replace template vars with placeholder for parsing
                        query_with_placeholders = re.sub(r'\${[^}]+}', 'TEMPLATE_VAR', query_template)
                        
                        # Split by & to get param pairs
                        param_pairs = query_with_placeholders.split('&')
                        for pair in param_pairs:
                            if '=' in pair and 'TEMPLATE_VAR' not in pair:
                                # This is a static param
                                key, value = pair.split('=', 1)
                                self.results['backend_endpoints'][endpoint]['params'][key].add(value)
                            elif '=' in pair:
                                # This is a param with a template value
                                key = pair.split('=', 1)[0]
                                self.results['backend_endpoints'][endpoint]['dynamic_patterns'].add(f"{key}=dynamic")
                    except Exception as e:
                        print(f"Error parsing template query string: {e}")
    
    def _find_search_params_usage(self, content, filename):
        """Find URLSearchParams usage for API calls"""
        # Look for patterns like: new URL('/api/endpoint'); url.searchParams.append('key', value)
        url_pattern = re.compile(r'new URL\([\'"](/api/[^\'"]+)[\'"]\)')
        
        for match in url_pattern.finditer(content):
            endpoint = match.group(1)
            # Get the context around this URL creation (next few lines)
            start_pos = match.start()
            end_pos = content.find(';', start_pos + 1)
            if end_pos == -1:
                end_pos = content.find('}', start_pos + 1)
            if end_pos == -1:
                continue
                
            # Look ahead for searchParams usage in the next 10 lines
            next_chunk = content[start_pos:start_pos + 500]  # Look ahead by ~500 chars
            
            # Find searchParams.append() or searchParams.set() calls
            param_pattern = re.compile(r'searchParams\.(append|set)\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*([^)]+)\)')
            param_matches = param_pattern.findall(next_chunk)
            
            if param_matches:
                # Found searchParams usage
                self.results['backend_endpoints'][endpoint]['files'].add(filename)
                
                for method, param_name, param_value in param_matches:
                    # If the value is a string literal, extract it
                    if (param_value.startswith("'") and param_value.endswith("'")) or \
                       (param_value.startswith('"') and param_value.endswith('"')):
                        # Clean up the parameter value
                        cleaned_value = param_value.strip('\'"')
                        self.results['backend_endpoints'][endpoint]['params'][param_name].add(cleaned_value)
                    else:
                        # It's a variable or expression
                        self.results['backend_endpoints'][endpoint]['dynamic_patterns'].add(f"{param_name}=dynamic")
    
    def _find_axios_fetch_params(self, content, filename):
        """Find axios/fetch calls with params objects"""
        # Enhanced pattern for axios that includes options
        axios_pattern = re.compile(r'axios\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]*/api/[^\'"]+)[\'"]')

        # Improved pattern for fetch with template literals or string literals
        fetch_pattern = re.compile(r'fetch\s*\(\s*[\'"`]([^\'"`]*/api/[^\'"]+)[\'"`]')
        
        # Additional pattern for axios instances
        axios_instance_pattern = re.compile(r'([a-zA-Z0-9_]+)\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]*/api/[^\'"]+)[\'"]')
        
        # Find all axios API calls
        for match in axios_pattern.finditer(content):
            http_method = match.group(1).upper()  # Convert to uppercase (GET, POST, etc.)
            endpoint = match.group(2)
            if not endpoint.startswith('/'):
                endpoint = '/' + endpoint
            self._process_api_call_with_params(content, match.start(), endpoint, filename, http_method)
        
        # Find all axios instance API calls (e.g., apiClient.post)
        for match in axios_instance_pattern.finditer(content):
            # Check if this looks like an axios instance
            instance_name = match.group(1)
            instance_check = re.search(r'(?:const|let|var)\s+' + re.escape(instance_name) + r'\s*=\s*axios', content)
            if instance_check:
                http_method = match.group(2).upper()
                endpoint = match.group(3)
                if not endpoint.startswith('/'):
                    endpoint = '/' + endpoint
                self._process_api_call_with_params(content, match.start(), endpoint, filename, http_method)
        
        # Find all fetch API calls with improved method detection
        for match in fetch_pattern.finditer(content):
            endpoint = match.group(1)
            if not endpoint.startswith('/'):
                endpoint = '/' + endpoint
                
            # Look for method in fetch options with a broader context
            start_pos = match.start()
            
            # Define search boundaries for better context capture
            # Look back up to 50 characters to catch the beginning of the statement
            # Look forward up to 300 characters to catch the entire fetch options object
            context_start = max(0, start_pos - 50)
            context_end = min(len(content), start_pos + 300)
            surrounding_context = content[context_start:context_end]
            
            # Try to determine HTTP method from fetch options - case insensitive
            method_match = re.search(r'method\s*:\s*[\'"]([a-zA-Z]+)[\'"]', surrounding_context, re.IGNORECASE)
            
            # If found, normalize the HTTP method to uppercase
            http_method = method_match.group(1).upper() if method_match else "GET"
            
            # Process the API call with the detected method
            self._process_api_call_with_params(content, start_pos, endpoint, filename, http_method)
            
    def _process_api_call_with_params(self, content, start_pos, endpoint, filename, http_method="GET"):
        """Process an API call to extract params object and request body"""
        # Look for the full API call content with improved bracket matching
        call_content = ""
        end_pos = -1
        
        # Find the closing parenthesis with proper nesting support
        open_parens = 1
        pos = start_pos
        max_pos = min(len(content), start_pos + 2000)  # Limit search range
        
        while pos < max_pos:
            if content[pos] == '(':
                open_parens += 1
            elif content[pos] == ')':
                open_parens -= 1
                if open_parens == 0:
                    end_pos = pos
                    break
            pos += 1
            
        if end_pos == -1:
            # Fallback to simpler approach if bracket matching fails
            end_pos = content.find(')', start_pos)
            if end_pos == -1:
                return
        
        call_content = content[start_pos:end_pos]
        
        # Store the file reference and HTTP method
        self.results['backend_endpoints'][endpoint]['files'].add(filename)
        self.results['backend_endpoints'][endpoint]['http_methods'].add(http_method)
        
        # Look for params object pattern
        params_match = re.search(r'params\s*:\s*({[^{}]*(?:{[^{}]*}[^{}]*)*})', call_content)
        if params_match:
            # Extract parameters from the params object
            params_content = params_match.group(1)
            param_pairs = re.findall(r'(\w+)\s*:\s*([^,}]+)', params_content)
            
            for key, value in param_pairs:
                key = key.strip()
                value = value.strip()
                
                if (value.startswith("'") and value.endswith("'")) or \
                   (value.startswith('"') and value.endswith('"')):
                    # It's a string literal
                    cleaned_value = value.strip('\'"')
                    self.results['backend_endpoints'][endpoint]['params'][key].add(cleaned_value)
                else:
                    # It's a variable or expression
                    self.results['backend_endpoints'][endpoint]['dynamic_patterns'].add(f"{key}=dynamic")
        
        # Extract request body information using a more comprehensive approach
        if http_method in ["POST", "PUT", "PATCH"]:
            # Expand context to search for request bodies
            call_line_start = content[:start_pos].rfind('\n')
            if call_line_start == -1:
                call_line_start = 0
            
            # Use a larger context window for better body detection
            broader_context = content[max(0, call_line_start - 100):min(len(content), end_pos + 300)]
            
            # For axios calls, the second argument is often the request body
            if 'axios.' in content[max(0, start_pos - 10):start_pos + 10]:
                # Handle different axios patterns
                # Pattern: axios.post('/api/endpoint', data)
                # The data can be either an object literal or a variable
                axios_data_match = re.search(r'axios\.[a-z]+\s*\(\s*[\'"][^\'"]+[\'"]\s*,\s*({[^{}]*(?:{[^{}]*}[^{}]*)*})', broader_context)
                if axios_data_match:
                    body_content = axios_data_match.group(1)
                    self._extract_body_structure(endpoint, body_content)
                else:
                    # Look for variable reference: axios.post('/api/endpoint', userData)
                    axios_var_match = re.search(r'axios\.[a-z]+\s*\(\s*[\'"][^\'"]+[\'"]\s*,\s*([a-zA-Z0-9_]+)', broader_context)
                    if axios_var_match:
                        body_var = axios_var_match.group(1).strip()
                        variable_context = content[max(0, start_pos - 1000):min(len(content), start_pos + 1000)]
                        self._find_variable_definition(endpoint, body_var, variable_context)
            
            # For fetch calls, look for both method specification and body content
            if 'fetch(' in broader_context:
                # Look for JSON.stringify usage which often indicates a request body
                json_stringify_match = re.search(r'JSON\.stringify\s*\(([^)]+)\)', broader_context)
                if json_stringify_match:
                    body_var = json_stringify_match.group(1).strip()
                    # Handle inline object literals in JSON.stringify
                    if body_var.startswith('{') and body_var.endswith('}'):
                        self._extract_body_structure(endpoint, body_var)
                    else:
                        # Look for the variable definition in a broader context
                        variable_context = content[max(0, start_pos - 1000):min(len(content), start_pos + 1000)]
                        self._find_variable_definition(endpoint, body_var, variable_context)
                
                # Look for body: property with improved pattern for nested objects
                body_match = re.search(r'body\s*:\s*({[^{}]*(?:{[^{}]*}[^{}]*)*})', broader_context)
                if body_match:
                    body_content = body_match.group(1)
                    self._extract_body_structure(endpoint, body_content)
                elif re.search(r'body\s*:\s*([^,}]+)', broader_context):
                    body_match = re.search(r'body\s*:\s*([^,}]+)', broader_context)
                    body_content = body_match.group(1).strip()
                    if not (body_content.startswith('"') or body_content.startswith("'")):
                        # It's likely a variable reference
                        # Look for the variable definition in a broader context
                        variable_context = content[max(0, start_pos - 1000):min(len(content), start_pos + 1000)]
                        self._find_variable_definition(endpoint, body_content, variable_context)
            
            # Look for data: property as part of options object
            data_match = re.search(r'data\s*:\s*({[^{}]*(?:{[^{}]*}[^{}]*)*})', broader_context)
            if data_match:
                body_content = data_match.group(1)
                self._extract_body_structure(endpoint, body_content)
                    
    def _extract_body_structure(self, endpoint, body_content):
        """Extract the structure of a request body"""
        try:
            # Clean up body content by removing whitespace and newlines for consistent parsing
            body_content = body_content.strip()
            
            # Only process if we have a valid object structure
            if not body_content.startswith('{') or not body_content.endswith('}'):
                return
                
            # Extract key-value pairs using a more robust approach
            properties = {}
            
            # Remove the outer braces and split by commas for initial property extraction
            content_inside = body_content[1:-1].strip()
            
            # Handle empty object
            if not content_inside:
                properties["emptyObject"] = {
                    "type": "object", 
                    "example": "{}"
                }
            else:
                # Improved state machine for tokenizing with better handling of nested structures
                tokens = []
                current_token = ""
                in_string = False
                string_delimiter = None  # Keep track of the string delimiter (' or ")
                bracket_depth = 0
                array_depth = 0
                
                for char in content_inside:
                    if (char == '"' or char == "'") and (not in_string or char == string_delimiter):
                        # Handle string start/end
                        if in_string:
                            # Only toggle if this is the same string delimiter we started with
                            if char == string_delimiter:
                                in_string = False
                                string_delimiter = None
                        else:
                            in_string = True
                            string_delimiter = char
                        current_token += char
                    elif char == '{':
                        bracket_depth += 1
                        current_token += char
                    elif char == '}':
                        bracket_depth -= 1
                        current_token += char
                    elif char == '[':
                        array_depth += 1
                        current_token += char
                    elif char == ']':
                        array_depth -= 1
                        current_token += char
                    elif char == ',' and not in_string and bracket_depth == 0 and array_depth == 0:
                        tokens.append(current_token.strip())
                        current_token = ""
                    else:
                        current_token += char
                        
                # Add the last token if not empty
                if current_token.strip():
                    tokens.append(current_token.strip())
                
                # Process each token as a key-value pair with improved type detection
                for token in tokens:
                    if ':' in token:
                        try:
                            key, value = token.split(':', 1)
                            # Clean up the key (remove quotes and whitespace)
                            key = key.strip()
                            if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
                                key = key[1:-1]
                            value = value.strip()
                            
                            # Enhanced type determination logic
                            prop_type = "string"  # Default type
                            prop_example = value
                            
                            if value in ['true', 'false']:
                                prop_type = "boolean"
                                prop_example = value == 'true'
                            elif value.isdigit() or re.match(r'^-?\d+(\.\d+)?$', value):
                                prop_type = "number"
                                try:
                                    prop_example = float(value) if '.' in value else int(value)
                                except:
                                    pass
                            elif value.startswith('[') and value.endswith(']'):
                                prop_type = "array"
                                # Try to determine array items type
                                items_type = "string"
                                array_content = value[1:-1].strip()
                                if array_content:
                                    array_items = self._parse_array_items(array_content)
                                    if array_items:
                                        sample_item = array_items[0] if array_items else ""
                                        if sample_item.isdigit() or re.match(r'^-?\d+(\.\d+)?$', sample_item):
                                            items_type = "number"
                                        elif sample_item in ['true', 'false']:
                                            items_type = "boolean"
                                        elif sample_item.startswith('{') and sample_item.endswith('}'):
                                            items_type = "object"
                                
                                properties[key] = {
                                    "type": prop_type,
                                    "example": prop_example,
                                    "items": {
                                        "type": items_type
                                    }
                                }
                                continue  # Skip the standard property assignment
                            elif value.startswith('{') and value.endswith('}'):
                                prop_type = "object"
                                # Extract nested object properties recursively
                                nested_properties = {}
                                self._extract_nested_object_properties(value, nested_properties)
                                if nested_properties:
                                    properties[key] = {
                                        "type": prop_type,
                                        "example": prop_example,
                                        "properties": nested_properties
                                    }
                                    continue  # Skip the standard property assignment
                            elif value.startswith('"') or value.startswith("'"):
                                value = value.strip('\'"')
                                prop_example = value
                            elif value.startswith('new ') and 'Date' in value:
                                prop_type = "string"
                                prop_example = "2023-01-01T00:00:00Z"  # Example ISO date string
                                
                            properties[key] = {
                                "type": prop_type,
                                "example": prop_example
                            }
                        except Exception as e:
                            print(f"Error processing token '{token}': {e}")
                            # Skip malformed property
                            pass
            
            # If we found any properties, add the body structure
            if properties:
                body_structure = {
                    "contentType": "application/json",
                    "properties": properties
                }
                
                # Check if similar body structure already exists
                exists = False
                for existing_body in self.results['backend_endpoints'][endpoint]['request_bodies']:
                    if self._compare_body_structures(existing_body, body_structure):
                        exists = True
                        break
                        
                if not exists:
                    # Add this to the endpoint's request bodies
                    self.results['backend_endpoints'][endpoint]['request_bodies'].append(body_structure)
                    print(f"Added request body for endpoint: {endpoint}")
        except Exception as e:
            print(f"Error extracting body structure: {e}")
            
    def _find_variable_definition(self, endpoint, var_name, context):
        """Try to find a variable definition in the surrounding context with enhanced detection"""
        # Remove any whitespace or special chars from the variable name
        var_name = var_name.strip().strip('{}():')
        
        # Handle object destructuring and direct property references
        if '.' in var_name:
            parts = var_name.split('.')
            base_var = parts[0]
            prop_path = '.'.join(parts[1:])
            
            # Look for base variable definition with support for different declaration types
            # Define regex pattern for variable definition with an object value
            object_pattern = r'\s*=\s*({[^{}]*(?:{[^{}]*}[^{}]*)*})'
            base_pattern_str = r'(?:const|let|var)\s+' + re.escape(base_var) + object_pattern
            base_pattern = re.compile(base_pattern_str)
            base_match = base_pattern.search(context)
            
            if base_match:
                base_content = base_match.group(1)
                # Now look for the specific property in the object
                prop_parts = prop_path.split('.')
                extracted = self._extract_nested_property(base_content, prop_parts)
                if extracted:
                    self._extract_body_structure(endpoint, extracted)
                    return
                    
            # Look for function argument with destructuring
            func_param_pattern = r'function\s+\w+\s*\(\s*{.*?' + re.escape(base_var) + r'.*?}\s*\)'
            if re.search(func_param_pattern, context):
                # Try to find object being passed to the function
                func_call_pattern = r'\w+\(\s*({[^{}]*(?:{[^{}]*}[^{}]*)*})\s*\)'
                func_calls = re.finditer(func_call_pattern, context)
                for call in func_calls:
                    call_content = call.group(1)
                    self._extract_body_structure(endpoint, call_content)
                    return
        
        # Look for patterns like: const varName = { ... } or let varName = { ... }
        # with improved regex that handles nested objects
        var_def_pattern_str = r'(?:const|let|var)\s+' + re.escape(var_name) + r'\s*=\s*({[^{}]*(?:{[^{}]*}[^{}]*)*})'
        var_def_pattern = re.compile(var_def_pattern_str)
        var_match = var_def_pattern.search(context)
        
        if var_match:
            body_content = var_match.group(1)
            self._extract_body_structure(endpoint, body_content)
            return
            
        # Try to find object assignments
        obj_pattern_str = re.escape(var_name) + r'\s*=\s*({[^{}]*(?:{[^{}]*}[^{}]*)*})'
        obj_pattern = re.compile(obj_pattern_str)
        obj_match = obj_pattern.search(context)
        
        if obj_match:
            body_content = obj_match.group(1)
            self._extract_body_structure(endpoint, body_content)
            return
            
        # Look for the variable in a different context (e.g., function arguments)
        func_arg_pattern = r'function\s+\w+\s*\([^)]*' + re.escape(var_name) + r'[^)]*\)'
        if re.search(func_arg_pattern, context):
            # Try to find calls to this function with object literals
            func_name = re.search(r'function\s+(\w+)', context)
            if func_name:
                func_call_pattern = func_name.group(1) + r'\(\s*({[^{}]*(?:{[^{}]*}[^{}]*)*})'
                func_call_match = re.search(func_call_pattern, context)
                if func_call_match:
                    body_content = func_call_match.group(1)
                    self._extract_body_structure(endpoint, body_content)
                    return
    
    def _compare_body_structures(self, body1, body2):
        """Compare two body structures to check if they are equivalent"""
        try:
            if body1.get('contentType') != body2.get('contentType'):
                return False
                
            props1 = body1.get('properties', {})
            props2 = body2.get('properties', {})
            
            # If one has properties and the other doesn't, they're not equivalent
            if bool(props1) != bool(props2):
                return False
                
            # Check if they have the same property keys
            if set(props1.keys()) != set(props2.keys()):
                return False
                
            # For each property, check if the types are the same
            for key in props1:
                if props1[key].get('type') != props2[key].get('type'):
                    return False
                    
            # If we got here, the structures are equivalent
            return True
        except Exception:
            return False
    
    def _parse_query_string(self, query_string):
        """Parse a query string into a dictionary of parameters"""
        params = defaultdict(list)
        
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                # URL decode the value if needed
                params[key].append(unquote(value))
            else:
                params[param].append(None)
                
        return params
    
    def export_results(self, filepath=EXPORT_FILE):
        """Export the results to a JSON file"""
        serialized = self._prepare_for_serialization()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Use custom encoder to handle sets and other non-serializable types
            json.dump(serialized, f, indent=2)
            
        print(f"Results exported to {filepath}")
    
    def print_results(self):
        """Print the analysis results to the console"""
        serialized = self._prepare_for_serialization()
        backend_endpoints = serialized['backend_endpoints']
        
        if not backend_endpoints:
            print("No API endpoints with query parameters found.")
            return
            
        print("\n📊 API Endpoints with Query Parameters:\n")
        
        for endpoint, data in sorted(backend_endpoints.items()):
            # Display HTTP methods with colored symbols
            methods_str = ", ".join(data['http_methods'])
            method_symbol = "🟢" if all(m == "GET" for m in data['http_methods']) else "🟠"
            
            print(f"🔸 Endpoint: {endpoint} {method_symbol} [{methods_str}]")
            
            # Show parameters
            if data['params']:
                print("  Static Parameters:")
                for param, values in sorted(data['params'].items()):
                    # Convert any None values to strings
                    safe_values = [str(v) if v is not None else '<no value>' for v in values]
                    print(f"    - {param}: {', '.join(safe_values)}")
            
            # Show template parameters
            if data['template_params']:
                print("  Template Parameters:")
                for param in sorted(data['template_params']):
                    print(f"    - ${{{param}}}")
            
            # Show dynamic patterns
            if data['dynamic_patterns']:
                print("  Dynamic Parameter Patterns:")
                for pattern in sorted(data['dynamic_patterns']):
                    print(f"    - {pattern}")
                    
            # Show request bodies if available
            if data.get('request_bodies'):
                print("  Request Body Structure:")
                for i, body in enumerate(data['request_bodies'], 1):
                    print(f"    Body #{i} ({body.get('contentType', 'application/json')}):")
                    for prop_name, prop_info in body.get('properties', {}).items():
                        print(f"      - {prop_name} ({prop_info.get('type', 'string')})")
            
            # Show files
            print("  Found in files:")
            for file in sorted(data['files']):
                print(f"    - {file}")
            
            print("")


    def _extract_nested_property(self, object_content, prop_path):
        """Extract a nested property from an object by following the property path"""
        try:
            # If there are no properties to follow, return the entire object
            if not prop_path:
                return object_content
                
            # Parse the object into a more structured form
            # This is a simplification - in real code a proper JS parser would be needed
            current_object = object_content
            current_prop = prop_path[0]
            
            # Look for the property pattern in the current object
            prop_pattern = r'(?<!\w)' + re.escape(current_prop) + r'\s*:\s*({[^{}]*(?:{[^{}]*}[^{}]*)*}|\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]|[^,}]+)'
            prop_match = re.search(prop_pattern, current_object)
            
            if not prop_match:
                return None
                
            prop_value = prop_match.group(1).strip()
            
            # If this is the last property in the path, return its value
            if len(prop_path) == 1:
                return prop_value
                
            # Otherwise, if it's an object, recursively extract from it
            if prop_value.startswith('{') and prop_value.endswith('}'):
                return self._extract_nested_property(prop_value, prop_path[1:])
                
            # Cannot follow the path further
            return None
        except Exception as e:
            print(f"Error extracting nested property: {e}")
            return None
    
    def _parse_array_items(self, array_content):
        """Parse items from an array string"""
        items = []
        in_string = False
        string_delimiter = None
        bracket_depth = 0
        brace_depth = 0
        current_item = ""
        
        for char in array_content:
            if (char == '"' or char == "'") and (not in_string or char == string_delimiter):
                if in_string:
                    if char == string_delimiter:
                        in_string = False
                        string_delimiter = None
                else:
                    in_string = True
                    string_delimiter = char
                current_item += char
            elif char == '{':
                brace_depth += 1
                current_item += char
            elif char == '}':
                brace_depth -= 1
                current_item += char
            elif char == '[':
                bracket_depth += 1
                current_item += char
            elif char == ']':
                bracket_depth -= 1
                current_item += char
            elif char == ',' and not in_string and bracket_depth == 0 and brace_depth == 0:
                items.append(current_item.strip())
                current_item = ""
            else:
                current_item += char
        
        if current_item.strip():
            items.append(current_item.strip())
            
        return items
    
    def _extract_nested_object_properties(self, object_str, properties):
        """Extract properties from a nested object string"""
        # Remove outer braces
        if object_str.startswith('{') and object_str.endswith('}'):
            object_content = object_str[1:-1].strip()
            
            # Split into key-value pairs using a simplified token extraction
            tokens = []
            current_token = ""
            in_string = False
            string_delimiter = None
            bracket_depth = 0
            brace_depth = 0
            
            for char in object_content:
                if (char == '"' or char == "'") and (not in_string or char == string_delimiter):
                    if in_string:
                        if char == string_delimiter:
                            in_string = False
                            string_delimiter = None
                    else:
                        in_string = True
                        string_delimiter = char
                    current_token += char
                elif char == '{':
                    brace_depth += 1
                    current_token += char
                elif char == '}':
                    brace_depth -= 1
                    current_token += char
                elif char == '[':
                    bracket_depth += 1
                    current_token += char
                elif char == ']':
                    bracket_depth -= 1
                    current_token += char
                elif char == ',' and not in_string and bracket_depth == 0 and brace_depth == 0:
                    tokens.append(current_token.strip())
                    current_token = ""
                else:
                    current_token += char
            
            if current_token.strip():
                tokens.append(current_token.strip())
                
            # Process each token as a key-value pair
            for token in tokens:
                if ':' in token:
                    try:
                        key, value = token.split(':', 1)
                        key = key.strip()
                        if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
                            key = key[1:-1]
                        value = value.strip()
                        
                        # Type determination
                        prop_type = "string"
                        
                        if value in ['true', 'false']:
                            prop_type = "boolean"
                        elif value.isdigit() or re.match(r'^-?\d+(\.\d+)?$', value):
                            prop_type = "number"
                        elif value.startswith('[') and value.endswith(']'):
                            prop_type = "array"
                        elif value.startswith('{') and value.endswith('}'):
                            prop_type = "object"
                        elif value.startswith('"') or value.startswith("'"):
                            value = value.strip('\'"')
                            
                        properties[key] = {
                            "type": prop_type,
                            "example": value
                        }
                    except Exception as e:
                        print(f"Error processing nested property: {e}")
                        # Skip malformed property
                        pass
