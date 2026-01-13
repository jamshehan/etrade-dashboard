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

# Database configuration
# For production: Set DATABASE_URL or POSTGRES_URL environment variable
# For local development: Uses SQLite at DB_PATH
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
USE_POSTGRES = DATABASE_URL is not None

# Paths (for SQLite local development)
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', BASE_DIR / 'data' / 'downloads'))
DB_PATH = Path(os.getenv('DB_PATH', BASE_DIR / 'data' / 'transactions.db'))

# Create directories if they don't exist
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Flask settings
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Scraper settings
HEADLESS = os.getenv('HEADLESS', 'True').lower() == 'true'
SCRAPER_TIMEOUT = int(os.getenv('SCRAPER_TIMEOUT', 60000))  # milliseconds

# Clerk authentication settings (for production)
CLERK_PUBLISHABLE_KEY = os.getenv('CLERK_PUBLISHABLE_KEY', '')
CLERK_SECRET_KEY = os.getenv('CLERK_SECRET_KEY', '')
CLERK_JWKS_URL = os.getenv('CLERK_JWKS_URL', '')
