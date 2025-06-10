# Site Request Analyzer

A collection of Python scripts for analyzing JavaScript files in web applications to extract and document API endpoints, request bodies, and their query parameters.

## Features

- Uses headless Chrome to render web applications completely
- Extracts all script URLs and downloads JavaScript files
- Discovers webpack chunk files and other dynamically loaded JavaScript
- Categorizes API calls by domain (backend vs external)
- Extracts query parameters from API endpoints
- Identifies template literals with dynamic parameters
- Detects HTTP methods (GET, POST, PUT, DELETE, PATCH) for API calls
- Handles different patterns of API calls (fetch, axios, URLSearchParams)
- Extracts request bodies from API calls
- Analyzes request body structure including nested objects and arrays
- Generates OpenAPI specification based on discovered endpoints
- Creates interactive HTML reports for easy exploration of API endpoints

## Requirements

- Python 3.7+
- Chrome browser installed

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic API Extraction

1. Edit the `SITE_URL` variable in the script to point to your target React application
2. Run the script:

```bash
python js_analyzer.py
```

### Enhanced API Query Parameter Analysis

To extract and analyze query parameters from API endpoints:

```bash
python api_query_analyzer.py
```

This will:
1. Analyze all downloaded JS files
2. Extract query parameters from API endpoints
3. Detect request bodies and their structure
4. Identify HTTP methods used for each endpoint

### Generate OpenAPI Specification

To generate an OpenAPI specification document from the extracted API data:

```bash
python generate_openapi_spec.py
```

### Generate HTML Report

To create an interactive HTML report for exploring the API endpoints:

```bash
python generate_html_report.py
```

### Complete Analysis Suite

To run all analysis steps in sequence:

```bash
./run_analysis.sh
```

Or use the main script for an interactive menu:

```bash
./run.sh
```
3. Identify template literals with dynamic parameters
4. Export results to a JSON file for further processing

### Generate HTML Report

To generate a beautifully formatted HTML report of the API endpoints:

```bash
python generate_html_report.py
```

This will create an interactive HTML report in the `results` directory with:
- Searchable interface for endpoints and parameters
- Statistical overview of API endpoints
- Filterable view by parameter types
- Expandable/collapsible endpoint details

### Run Complete Analysis Suite

To run the entire analysis pipeline (download JS, analyze endpoints, extract parameters, generate HTML report):

```bash
./run_analysis.sh
```

Options:
- `-u, --url [URL]`: Specify the target website URL
- `-a, --analyze-only`: Skip downloading and use existing JS files
- `-v, --verbose`: Show more detailed output

## Scripts in this Repository

### 1. js_analyzer.py

Basic analyzer that extracts JavaScript files and scans them for API endpoints.

### 2. js_analyzer_refactored.py 

Improved version with domain categorization.

### 3. api_params_analyzer.py

Specialized script for extracting query parameters from API endpoints.

### 4. api_query_analyzer.py

Enhanced analyzer that specifically focuses on query parameters in `/api/` endpoints, with support for:
- Detection of HTTP methods (GET, POST, PUT, DELETE, PATCH)
- Static parameters in URL strings
- Template literals with dynamic parameters
- Search params objects
- Axios/fetch config objects with params

### 5. generate_html_report.py

Generates a beautifully formatted, interactive HTML report from the JSON results:
- Modern responsive design
- Search functionality
- Filter by parameter types
- Expand/collapse endpoint details
- Statistics overview

## Output

The scripts output discovered API endpoints organized by:
- JavaScript file where they were found
- Endpoint path with query parameters
- Parameters and their values (static or dynamic)
- Template variables used in dynamic endpoints
