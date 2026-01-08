import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# eTrade credentials
ETRADE_USERNAME = os.getenv('ETRADE_USERNAME', '')
ETRADE_PASSWORD = os.getenv('ETRADE_PASSWORD', '')

# Paths
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', BASE_DIR / 'data' / 'downloads'))
DB_PATH = Path(os.getenv('DB_PATH', BASE_DIR / 'data' / 'transactions.db'))

# Create directories if they don't exist
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Flask settings
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# Scraper settings
HEADLESS = os.getenv('HEADLESS', 'True').lower() == 'true'
SCRAPER_TIMEOUT = int(os.getenv('SCRAPER_TIMEOUT', 60000))  # milliseconds
