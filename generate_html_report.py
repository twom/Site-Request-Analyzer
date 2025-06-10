#!/usr/bin/env python3
# HTML Report Generator for API Query Results
# This script converts the API query results to a nice HTML report

import os
import json
import shutil
from datetime import datetime

# Configuration
INPUT_FILE = "api_query_results.json"
OUTPUT_DIR = "results"
ANALYSIS_DIR = "analysis_results"  # Alternative output directory
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "api_report.html")

# HTML templates
HTML_HEADER = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>React API Endpoints Analysis</title>
    <style>
        :root {
            --primary-color: #3498db;
            --secondary-color: #2c3e50;
            --success-color: #2ecc71;
            --warning-color: #f1c40f;
            --danger-color: #e74c3c;
            --light-color: #f8f9fa;
            --dark-color: #343a40;
            --border-color: #dee2e6;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        
        header {
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
        }
        
        h1 {
            margin: 0;
            font-size: 28px;
        }
        
        h2 {
            color: var(--secondary-color);
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 10px;
            margin-top: 40px;
        }
        
        .stats {
            display: flex;
            justify-content: space-between;
            margin: 20px 0;
            flex-wrap: wrap;
            gap: 15px;
        }
        
        .stat-card {
            flex: 1;
            background-color: white;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            min-width: 200px;
            text-align: center;
        }
        
        .stat-card h3 {
            margin: 0;
            font-size: 16px;
            color: var(--dark-color);
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: var(--primary-color);
            margin: 10px 0;
        }
        
        .endpoint-card {
            background-color: white;
            border-radius: 5px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }
        
        .endpoint-header {
            padding: 15px;
            background-color: #f8f9fa;
            border-bottom: 1px solid var(--border-color);
            border-radius: 5px 5px 0 0;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
        }
        
        .endpoint-header:hover {
            background-color: #e9ecef;
        }
        
        .endpoint-name {
            font-weight: bold;
            color: var(--primary-color);
            font-family: monospace;
            font-size: 16px;
        }
        
        .endpoint-content {
            padding: 20px;
        }
        
        .params-section {
            margin-top: 15px;
        }
        
        .params-title {
            font-weight: bold;
            margin-bottom: 10px;
            color: var(--secondary-color);
        }
        
        .param-list {
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 10px 15px;
            margin-bottom: 15px;
        }
        
        .param-item {
            margin: 5px 0;
            font-family: monospace;
        }
        
        .param-name {
            font-weight: bold;
            color: #e83e8c;
        }
        
        .param-value {
            color: #28a745;
        }
        
        .template-param {
            color: #fd7e14;
        }
        
        .files-section {
            margin-top: 15px;
        }
        
        .file-list {
            padding-left: 20px;
        }
        
        .search-container {
            margin-bottom: 20px;
        }
        
        #searchInput {
            width: 100%;
            padding: 10px;
            font-size: 16px;
            border: 2px solid var(--primary-color);
            border-radius: 5px;
        }
        
        .controls {
            margin: 20px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        button {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-right: 10px;
            transition: background-color 0.2s;
        }
        
        button:hover {
            background-color: #2980b9;
        }
        
        footer {
            margin-top: 40px;
            text-align: center;
            color: #6c757d;
            font-size: 14px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
        }
        
        .collapsible {
            display: none;
        }
        
        .expand-all:after {
            content: ' [+]';
        }
        
        /* Badge styling */
        .badge {
            display: inline-block;
            padding: 3px 8px;
            font-size: 12px;
            font-weight: bold;
            border-radius: 10px;
            margin-left: 10px;
        }
        
        .badge-static {
            background-color: #e0f7fa;
            color: #0097a7;
        }
        
        .badge-template {
            background-color: #fff3e0;
            color: #e65100;
        }
        
        .badge-dynamic {
            background-color: #e8f5e9;
            color: #2e7d32;
        }
        
        /* HTTP Method badges */
        .method-badge {
            display: inline-block;
            padding: 3px 8px;
            font-size: 12px;
            font-weight: bold;
            border-radius: 10px;
            margin-left: 5px;
        }
        
        .method-get {
            background-color: #e3f2fd;
            color: #1565c0;
        }
        
        .method-post {
            background-color: #e8f5e9;
            color: #2e7d32;
        }
        
        .method-put {
            background-color: #fff8e1;
            color: #ff8f00;
        }
        
        .method-delete {
            background-color: #ffebee;
            color: #c62828;
        }
        
        .method-patch {
            background-color: #e0f2f1;
            color: #00695c;
        }
        
        /* Request body styles */
        .body-title {
            font-weight: bold;
            margin: 10px 0 5px;
            color: var(--secondary-color);
        }
        
        .param-type {
            color: #6c757d;
            font-style: italic;
        }
        
        .no-results {
            background-color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            margin-top: 20px;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <header>
        <h1>React API Endpoints Analysis</h1>
        <p>Analysis of API endpoints and query parameters found in JavaScript files.</p>
        <p class="generation-date">Generated on: ${GENERATION_DATE}</p>
    </header>

    <div class="search-container">
        <input type="text" id="searchInput" placeholder="Search for endpoints, parameters, or files...">
    </div>

    <div class="controls">
        <div>
            <button id="expandAll" class="expand-all">Expand All</button>
            <button id="collapseAll">Collapse All</button>
        </div>
        <div>
            <label for="filterDropdown">Filter by: </label>
            <select id="filterDropdown">
                <option value="all">All Endpoints</option>
                <option value="static">Static Parameters</option>
                <option value="template">Template Parameters</option>
                <option value="dynamic">Dynamic Parameters</option>
            </select>
        </div>
    </div>

    <div class="stats">
        <div class="stat-card">
            <h3>Total Endpoints</h3>
            <div class="stat-value" id="totalEndpoints">0</div>
        </div>
        <div class="stat-card">
            <h3>Static Parameters</h3>
            <div class="stat-value" id="staticParamsCount">0</div>
        </div>
        <div class="stat-card">
            <h3>Template Parameters</h3>
            <div class="stat-value" id="templateParamsCount">0</div>
        </div>
        <div class="stat-card">
            <h3>Unique Files</h3>
            <div class="stat-value" id="filesCount">0</div>
        </div>
    </div>

    <h2>API Endpoints</h2>
    <div id="endpoints-container">
        <!-- Endpoint cards will be inserted here -->
    </div>
"""

HTML_FOOTER = """
    <footer>
        <p>Generated by React JS API Analyzer</p>
    </footer>

    <script>
        // Search functionality
        document.getElementById('searchInput').addEventListener('input', filterEndpoints);
        document.getElementById('filterDropdown').addEventListener('change', filterEndpoints);
        
        function filterEndpoints() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const filterType = document.getElementById('filterDropdown').value;
            const endpointCards = document.querySelectorAll('.endpoint-card');
            let visibleCount = 0;
            
            endpointCards.forEach(card => {
                const endpointText = card.textContent.toLowerCase();
                const hasStaticParams = card.querySelector('.static-params') !== null;
                const hasTemplateParams = card.querySelector('.template-params') !== null;
                const hasDynamicPatterns = card.querySelector('.dynamic-patterns') !== null;
                
                let shouldShow = endpointText.includes(searchTerm);
                
                // Apply filter type
                if (shouldShow && filterType !== 'all') {
                    if (filterType === 'static' && !hasStaticParams) shouldShow = false;
                    if (filterType === 'template' && !hasTemplateParams) shouldShow = false;
                    if (filterType === 'dynamic' && !hasDynamicPatterns) shouldShow = false;
                }
                
                card.style.display = shouldShow ? 'block' : 'none';
                if (shouldShow) visibleCount++;
            });
            
            // Show no results message if needed
            const noResultsEl = document.getElementById('no-results');
            if (visibleCount === 0) {
                if (!noResultsEl) {
                    const message = document.createElement('div');
                    message.id = 'no-results';
                    message.className = 'no-results';
                    message.textContent = 'No endpoints match your search criteria.';
                    document.getElementById('endpoints-container').appendChild(message);
                }
            } else if (noResultsEl) {
                noResultsEl.remove();
            }
        }
        
        // Expand/collapse functionality
        document.querySelectorAll('.endpoint-header').forEach(header => {
            header.addEventListener('click', function() {
                const content = this.nextElementSibling;
                content.style.display = content.style.display === 'block' ? 'none' : 'block';
            });
        });
        
        document.getElementById('expandAll').addEventListener('click', function() {
            const contents = document.querySelectorAll('.endpoint-content');
            const isExpanding = this.classList.contains('expand-all');
            
            contents.forEach(content => {
                const card = content.closest('.endpoint-card');
                if (card.style.display !== 'none') {  // Only affect visible cards
                    content.style.display = isExpanding ? 'block' : 'none';
                }
            });
            
            if (isExpanding) {
                this.textContent = 'Collapse All';
                this.classList.remove('expand-all');
            } else {
                this.textContent = 'Expand All';
                this.classList.add('expand-all');
            }
        });
        
        document.getElementById('collapseAll').addEventListener('click', function() {
            document.querySelectorAll('.endpoint-content').forEach(content => {
                content.style.display = 'none';
            });
            const expandAllBtn = document.getElementById('expandAll');
            expandAllBtn.textContent = 'Expand All';
            expandAllBtn.classList.add('expand-all');
        });
    </script>
</body>
</html>
"""

ENDPOINT_TEMPLATE = """
<div class="endpoint-card">
    <div class="endpoint-header">
        <span class="endpoint-name">${ENDPOINT_PATH}</span>
        <span>
            ${HTTP_METHODS}
            ${BADGES}
        </span>
    </div>
    <div class="endpoint-content collapsible">
        ${STATIC_PARAMS}
        ${TEMPLATE_PARAMS}
        ${DYNAMIC_PATTERNS}
        ${REQUEST_BODIES}
        <div class="files-section">
            <div class="params-title">Found in files:</div>
            <div class="file-list">
                ${FILES}
            </div>
        </div>
    </div>
</div>
"""

def generate_html_report():
    """Generate an HTML report from the JSON results"""
    print("Generating HTML report...")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load API results from JSON
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading API results: {e}")
        return False

    # Prepare data for HTML generation
    endpoints_data = data.get('backend_endpoints', {})
    
    # Count statistics
    endpoint_count = len(endpoints_data)
    
    static_params_count = 0
    template_params_count = 0
    all_files = set()
    
    # Generate HTML for each endpoint
    endpoints_html = ""
    
    for endpoint_path, endpoint_info in sorted(endpoints_data.items()):
        # Collect stats
        static_params_count += sum(len(values) for values in endpoint_info.get('params', {}).values())
        template_params_count += len(endpoint_info.get('template_params', []))
        all_files.update(endpoint_info.get('files', []))
        
        # Prepare badges
        badges = []
        if endpoint_info.get('params'):
            badges.append('<span class="badge badge-static">Static Params</span>')
        if endpoint_info.get('template_params'):
            badges.append('<span class="badge badge-template">Template Vars</span>')
        if endpoint_info.get('dynamic_patterns'):
            badges.append('<span class="badge badge-dynamic">Dynamic</span>')
        
        badges_html = "\n".join(badges) if badges else ""
        
        # Generate static params section
        static_params_html = ""
        if endpoint_info.get('params'):
            params_items = []
            for param_name, param_values in sorted(endpoint_info['params'].items()):
                formatted_values = []
                for value in param_values:
                    if value is None:
                        formatted_values.append("<i>null</i>")
                    elif "${" in str(value):
                        # Highlight template literals in param values
                        formatted_values.append(f'<span class="template-param">{value}</span>')
                    else:
                        formatted_values.append(str(value))
                
                value_str = ", ".join(formatted_values)
                params_items.append(f'<div class="param-item"><span class="param-name">{param_name}</span>: {value_str}</div>')
            
            static_params_html = f"""
            <div class="params-section static-params">
                <div class="params-title">Static Parameters:</div>
                <div class="param-list">
                    {"".join(params_items)}
                </div>
            </div>
            """
        
        # Generate template params section
        template_params_html = ""
        if endpoint_info.get('template_params'):
            template_items = []
            for param in sorted(endpoint_info['template_params']):
                template_items.append(f'<div class="param-item"><span class="template-param">${{{param}}}</span></div>')
            
            template_params_html = f"""
            <div class="params-section template-params">
                <div class="params-title">Template Variables:</div>
                <div class="param-list">
                    {"".join(template_items)}
                </div>
            </div>
            """
        
        # Generate dynamic patterns section
        dynamic_patterns_html = ""
        if endpoint_info.get('dynamic_patterns'):
            dynamic_items = []
            for pattern in sorted(endpoint_info['dynamic_patterns']):
                dynamic_items.append(f'<div class="param-item">{pattern}</div>')
            
            dynamic_patterns_html = f"""
            <div class="params-section dynamic-patterns">
                <div class="params-title">Dynamic Patterns:</div>
                <div class="param-list">
                    {"".join(dynamic_items)}
                </div>
            </div>
            """
            
        # Generate request bodies section
        request_bodies_html = ""
        if endpoint_info.get('request_bodies'):
            bodies_html = []
            for i, body in enumerate(endpoint_info['request_bodies'], 1):
                properties_html = []
                for prop_name, prop_info in body.get('properties', {}).items():
                    prop_type = prop_info.get('type', 'string')
                    prop_example = prop_info.get('example', '')
                    properties_html.append(f'<div class="param-item"><span class="param-name">{prop_name}</span>: <span class="param-type">({prop_type})</span> {prop_example}</div>')
                
                bodies_html.append(f"""
                <div class="param-list">
                    <div class="body-title">Body #{i} ({body.get('contentType', 'application/json')}):</div>
                    {"".join(properties_html)}
                </div>
                """)
            
            request_bodies_html = f"""
            <div class="params-section request-bodies">
                <div class="params-title">Request Body Structure:</div>
                {"".join(bodies_html)}
            </div>
            """
        
        # Generate files list
        files_html = []
        for file in sorted(endpoint_info.get('files', [])):
            files_html.append(f'<div>{file}</div>')
        
        # Generate HTTP method badges
        http_methods_html = ""
        if 'http_methods' in endpoint_info:
            method_badges = []
            for method in sorted(endpoint_info['http_methods']):
                method_lower = method.lower()
                method_badges.append(f'<span class="method-badge method-{method_lower}">{method}</span>')
            http_methods_html = "".join(method_badges)
        
        # Create the endpoint card
        endpoint_html = ENDPOINT_TEMPLATE.replace('${ENDPOINT_PATH}', endpoint_path) \
                                         .replace('${BADGES}', badges_html) \
                                         .replace('${HTTP_METHODS}', http_methods_html) \
                                         .replace('${STATIC_PARAMS}', static_params_html) \
                                         .replace('${TEMPLATE_PARAMS}', template_params_html) \
                                         .replace('${DYNAMIC_PATTERNS}', dynamic_patterns_html) \
                                         .replace('${REQUEST_BODIES}', request_bodies_html) \
                                         .replace('${FILES}', "\n".join(files_html))
        
        endpoints_html += endpoint_html
    
    # Generate the complete HTML report
    generation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html_content = HTML_HEADER.replace('${GENERATION_DATE}', generation_date)
    html_content += endpoints_html
    html_content += HTML_FOOTER
    
    # Write the HTML report to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Copy the JSON data to results folder
    output_json = os.path.join(OUTPUT_DIR, os.path.basename(INPUT_FILE))
    shutil.copy(INPUT_FILE, output_json)
    
    # Update JavaScript stats
    html_content = html_content.replace('"totalEndpoints">0<', f'"totalEndpoints">{endpoint_count}<')
    html_content = html_content.replace('"staticParamsCount">0<', f'"staticParamsCount">{static_params_count}<')
    html_content = html_content.replace('"templateParamsCount">0<', f'"templateParamsCount">{template_params_count}<')
    html_content = html_content.replace('"filesCount">0<', f'"filesCount">{len(all_files)}<')
    
    # Write the updated HTML report to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML report generated at {OUTPUT_FILE}")
    return True

def main():
    # Create results directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    
    # Generate HTML report
    if generate_html_report():
        print(f"✅ Report successfully generated in {OUTPUT_DIR} directory")
        print(f"   - HTML Report: {os.path.basename(OUTPUT_FILE)}")
        print(f"   - JSON Data: {os.path.basename(INPUT_FILE)}")
        
        # Also copy the report to analysis_results directory for consistency
        analysis_output_file = os.path.join(ANALYSIS_DIR, os.path.basename(OUTPUT_FILE))
        shutil.copy(OUTPUT_FILE, analysis_output_file)
        print(f"✅ Report also copied to {ANALYSIS_DIR} directory")
    else:
        print("❌ Failed to generate HTML report")

if __name__ == "__main__":
    main()
