#!/bin/zsh

# Setup script for React JS Analyzer
# This will install dependencies and run the analyzer

# Colors for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== React JS Analyzer Setup ===${NC}"

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python 3 is not installed. Please install Python 3 first.${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -r requirements.txt

# Ask user which script to run
echo -e "${GREEN}Which script would you like to run?${NC}"
echo "1) react_js_scraper.py (Original script)"
echo "2) js_analyzer.py (Improved script)"
echo "3) api_params_analyzer.py (API parameter extraction)"
echo "4) api_query_analyzer.py (Enhanced query parameter analyzer)"
echo "5) run_analysis.sh (Full analysis suite)"
echo -n "Enter your choice (1-5): "
read choice

if [ "$choice" = "1" ]; then
    echo -e "${GREEN}Running react_js_scraper.py...${NC}"
    python3 react_js_scraper.py
elif [ "$choice" = "2" ]; then
    echo -e "${GREEN}Running js_analyzer.py...${NC}"
    python3 js_analyzer.py
elif [ "$choice" = "3" ]; then
    echo -e "${GREEN}Running api_params_analyzer.py...${NC}"
    python3 api_params_analyzer.py
elif [ "$choice" = "4" ]; then
    echo -e "${GREEN}Running api_query_analyzer.py...${NC}"
    python3 api_query_analyzer.py
elif [ "$choice" = "5" ]; then
    echo -e "${GREEN}Running full analysis suite...${NC}"
    ./run_analysis.sh
else
    echo -e "${YELLOW}Invalid choice. Exiting.${NC}"
    exit 1
fi

# Deactivate virtual environment
deactivate
