#!/usr/bin/env python3
# OpenAPI Specification Generator for React API Analyzer
# This script generates an OpenAPI specification from the API analysis results

import os
import json
import re
from collections import defaultdict

# Configuration
INPUT_FILE = "api_query_results.json"
OUTPUT_DIR = "results"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "api_openapi_spec.json")

class OpenAPIGenerator:
    def __init__(self, api_data_file=INPUT_FILE):
        self.api_data_file = api_data_file
        self.api_data = None
        self.spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Extracted API Specification",
                "description": "API specification generated from JavaScript analysis",
                "version": "1.0.0"
            },
            "servers": [
                {
                    "url": "/",
                    "description": "Local server"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    }
                }
            }
        }
    
    def load_api_data(self):
        """Load API data from JSON file"""
        try:
            with open(self.api_data_file, 'r', encoding='utf-8') as f:
                self.api_data = json.load(f)
                return True
        except Exception as e:
            print(f"Error loading API data: {e}")
            return False
    
    def generate_spec(self):
        """Generate OpenAPI specification from API data"""
        if not self.api_data:
            if not self.load_api_data():
                return False
        
        backend_endpoints = self.api_data.get('backend_endpoints', {})
        
        # Process each endpoint
        for endpoint, data in backend_endpoints.items():
            # Skip incomplete endpoints
            if '{PARAM}' in endpoint and not self._has_template_params(data):
                continue
                
            path_params = []
            
            # Normalize the path for OpenAPI (replace {PARAM} with {param})
            normalized_path = self._normalize_path(endpoint, path_params)
            
            # Add path entry if it doesn't exist
            if normalized_path not in self.spec['paths']:
                self.spec['paths'][normalized_path] = {}
            
            # Process each HTTP method for this endpoint
            for method in data.get('http_methods', ["GET"]):
                method = method.lower()  # OpenAPI uses lowercase HTTP methods
                
                # Skip if method already defined (prefer the first definition)
                if method in self.spec['paths'][normalized_path]:
                    continue
                
                # Create operation object
                operation = {
                    "summary": f"{method.upper()} {endpoint}",
                    "description": f"Endpoint extracted from JavaScript analysis",
                    "operationId": self._generate_operation_id(method, normalized_path),
                    "tags": [self._extract_tag(normalized_path)],
                    "responses": {
                        "200": {
                            "description": "Successful response"
                        },
                        "400": {
                            "description": "Bad request"
                        },
                        "401": {
                            "description": "Unauthorized"
                        }
                    }
                }
                
                # Add parameters (path params, query params)
                parameters = []
                
                # Add path parameters
                for param in path_params:
                    parameters.append({
                        "name": param,
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string"
                        }
                    })
                
                # Add query parameters
                for param_name in data.get('params', {}):
                    param_values = data['params'][param_name]
                    param_type = "string"  # Default type
                    
                    # Try to determine parameter type from values
                    if param_values and param_values[0]:
                        value = param_values[0]
                        try:
                            if value.lower() in ['true', 'false']:
                                param_type = "boolean"
                            elif value.isdigit():
                                param_type = "integer"
                            elif re.match(r'^-?\d+(\.\d+)?$', value):
                                param_type = "number"
                        except:
                            pass
                    
                    parameters.append({
                        "name": param_name,
                        "in": "query",
                        "required": False,
                        "schema": {
                            "type": param_type
                        }
                    })
                
                # Add dynamic parameters
                for pattern in data.get('dynamic_patterns', []):
                    if '=' in pattern:
                        param_name = pattern.split('=')[0]
                        parameters.append({
                            "name": param_name,
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string"
                            },
                            "description": "Dynamic parameter (value determined at runtime)"
                        })
                
                if parameters:
                    operation['parameters'] = parameters
                
                # Add request body for POST/PUT/PATCH methods
                if method in ['post', 'put', 'patch'] and data.get('request_bodies'):
                    best_body = self._select_best_request_body(data['request_bodies'])
                    if best_body:
                        schema_name = self._create_schema_name(method, normalized_path)
                        self._add_schema(schema_name, best_body)
                        
                        operation['requestBody'] = {
                            "description": "Request body",
                            "required": True,
                            "content": {
                                best_body.get("contentType", "application/json"): {
                                    "schema": {
                                        "$ref": f"#/components/schemas/{schema_name}"
                                    }
                                }
                            }
                        }
                
                # Add the operation to the path
                self.spec['paths'][normalized_path][method] = operation
        
        # Remove empty components
        if not self.spec['components']['schemas']:
            del self.spec['components']['schemas']
        
        return True
    
    def _normalize_path(self, endpoint, path_params):
        """Normalize path for OpenAPI and extract path parameters"""
        # Replace template literals like ${var} with {var}
        path = re.sub(r'\${([^}]+)}', r'{\1}', endpoint)
        
        # Replace {PARAM} placeholders with sequentially numbered parameters
        param_count = 1
        while '{PARAM}' in path:
            path = path.replace('{PARAM}', f'{{param{param_count}}}', 1)
            path_params.append(f"param{param_count}")
            param_count += 1
        
        # Extract other parameter names from the path
        for param in re.findall(r'{([^}]+)}', path):
            if param not in path_params:
                path_params.append(param)
        
        return path
    
    def _has_template_params(self, data):
        """Check if endpoint has template parameters defined"""
        return len(data.get('template_params', [])) > 0
    
    def _generate_operation_id(self, method, path):
        """Generate a unique operation ID"""
        # Remove leading and trailing slashes
        clean_path = path.strip('/')
        
        # Replace slashes and variables with camelCase
        parts = re.split(r'[/{}-]', clean_path)
        parts = [part for part in parts if part and not part.startswith('{')]
        
        operation_id = method + ''.join(part.title() for part in parts)
        return operation_id
    
    def _extract_tag(self, path):
        """Extract tag from path"""
        parts = path.strip('/').split('/')
        if parts:
            return parts[0]
        return "api"
    
    def _select_best_request_body(self, bodies):
        """Select the best request body from multiple options"""
        if not bodies:
            return None
            
        # For now, just take the one with the most properties
        return max(bodies, key=lambda b: len(b.get('properties', {}))) if bodies else None
    
    def _create_schema_name(self, method, path):
        """Create a schema name for request/response bodies"""
        # Extract meaningful parts from the path
        parts = re.split(r'[/{}-]', path.strip('/'))
        parts = [part for part in parts if part and not part.startswith('{')]
        
        # Join parts with camelCase
        name = ''.join(part.title() for part in parts) + method.title() + "Body"
        return name
    
    def _add_schema(self, name, body_structure):
        """Add schema to components/schemas"""
        if 'schemas' not in self.spec['components']:
            self.spec['components']['schemas'] = {}
            
        properties = {}
        for prop_name, prop_info in body_structure.get('properties', {}).items():
            properties[prop_name] = {
                "type": prop_info.get('type', 'string')
            }
            
            if 'example' in prop_info:
                properties[prop_name]['example'] = prop_info['example']
        
        self.spec['components']['schemas'][name] = {
            "type": "object",
            "properties": properties
        }
    
    def save_spec(self, output_file=OUTPUT_FILE):
        """Save OpenAPI specification to a file"""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.spec, f, indent=2)
            
        print(f"OpenAPI specification saved to {output_file}")
        
        # Also save to analysis_results directory
        analysis_output_file = os.path.join("analysis_results", os.path.basename(output_file))
        os.makedirs(os.path.dirname(analysis_output_file), exist_ok=True)
        
        with open(analysis_output_file, 'w', encoding='utf-8') as f:
            json.dump(self.spec, f, indent=2)
            
        print(f"OpenAPI specification also saved to {analysis_output_file}")
        return output_file, analysis_output_file

def main():
    generator = OpenAPIGenerator()
    if generator.generate_spec():
        generator.save_spec()
    else:
        print("Failed to generate OpenAPI specification")

if __name__ == "__main__":
    main()
