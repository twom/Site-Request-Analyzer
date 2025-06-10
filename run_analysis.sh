#!/bin/bash
# React JS API Analyzer Runner
# This script helps run the different analyzers sequentially

SITE_URL="https://qubit.autostoresystem.com"  # Default URL
DOWNLOAD_DIR="downloaded_js"
OUTPUT_DIR="analysis_results"
ANALYZE_ONLY=false
VERBOSE=false

# Display script usage
show_help() {
    echo "React JS API Analyzer - Usage"
    echo "=============================="
    echo "Options:"
    echo "  -h, --help             Show this help message"
    echo "  -u, --url [URL]        Specify the target website URL"
    echo "  -a, --analyze-only     Skip downloading and use existing JS files"
    echo "  -v, --verbose          Show more detailed output"
    echo ""
    echo "Examples:"
    echo "  ./run_analysis.sh -u https://example.com"
    echo "  ./run_analysis.sh --analyze-only"
}

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -h|--help) show_help; exit 0 ;;
        -u|--url) SITE_URL="$2"; shift ;;
        -a|--analyze-only) ANALYZE_ONLY=true ;;
        -v|--verbose) VERBOSE=true ;;
        *) echo "Unknown parameter: $1"; show_help; exit 1 ;;
    esac
    shift
done

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

echo "====================================="
echo "React JS API Analyzer"
echo "====================================="
echo "Target URL: $SITE_URL"
echo "Output directory: $OUTPUT_DIR"
echo "Analyze only mode: $ANALYZE_ONLY"
echo "====================================="

# Function to run a script and save its output
run_script() {
    local script=$1
    local output_file="$OUTPUT_DIR/$(basename $script .py)_output.txt"
    
    echo -e "\n🚀 Running $script..."
    if [ "$VERBOSE" = true ]; then
        python3 "$script" | tee "$output_file"
    else
        python3 "$script" > "$output_file"
        echo "Output saved to $output_file"
    fi
}

# Step 1: Download JS files (unless analyze-only mode is active)
if [ "$ANALYZE_ONLY" = false ]; then
    echo -e "\n📥 Downloading JavaScript files using js_analyzer.py..."
    
    # Temporarily modify the SITE_URL in js_analyzer.py
    sed -i.bak "s|SITE_URL = \".*\"|SITE_URL = \"$SITE_URL\"|" js_analyzer.py
    
    run_script "js_analyzer.py"
    
    # Restore the original js_analyzer.py
    mv js_analyzer.py.bak js_analyzer.py
else
    echo -e "\n📂 Using existing JavaScript files in $DOWNLOAD_DIR"
    # Check if the download directory exists
    if [ ! -d "$DOWNLOAD_DIR" ]; then
        echo "❌ Error: $DOWNLOAD_DIR directory not found. Run without --analyze-only first."
        exit 1
    fi
    
    # Check if there are JS files in the directory
    JS_FILE_COUNT=$(find "$DOWNLOAD_DIR" -name "*.js" | wc -l)
    if [ "$JS_FILE_COUNT" -eq 0 ]; then
        echo "❌ Error: No JavaScript files found in $DOWNLOAD_DIR."
        exit 1
    fi
    
    echo "✅ Found $JS_FILE_COUNT JavaScript files to analyze."
fi

# Step 2: Run the refactored analyzer to categorize by domain
echo -e "\n🔍 Running domain categorization analysis..."
run_script "js_analyzer_refactored.py"

# Step 3: Run parameter extraction analysis
echo -e "\n🧩 Extracting API parameters..."
run_script "api_params_analyzer.py"

# Step 4: Run enhanced query parameter analysis
echo -e "\n🔬 Performing detailed API query parameter analysis..."
run_script "api_query_analyzer.py"

# Copy the JSON results to the output directory
cp api_query_results.json "$OUTPUT_DIR/"

# Generate HTML report
echo -e "\n🌐 Generating HTML report..."
python3 generate_html_report.py

echo -e "\n✅ Analysis complete! Results saved to the $OUTPUT_DIR directory."
echo "📊 Summary files:"
ls -la "$OUTPUT_DIR"

echo -e "\n💡 To view the HTML report, open: $OUTPUT_DIR/api_report.html"

# Ask if user wants to open the HTML report
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "\n🌐 Would you like to open the HTML report now? (y/n)"
    read -p "> " open_report
    if [[ "$open_report" == "y" || "$open_report" == "Y" ]]; then
        open "$OUTPUT_DIR/api_report.html"
        echo "Report opened in your default browser."
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "\n🌐 Would you like to open the HTML report now? (y/n)"
    read -p "> " open_report
    if [[ "$open_report" == "y" || "$open_report" == "Y" ]]; then
        xdg-open "$OUTPUT_DIR/api_report.html"
        echo "Report opened in your default browser."
    fi
fi
