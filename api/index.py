"""
Vercel serverless entry point for Flask app.
This file imports the Flask app instance from the main app.py module.
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app

# Vercel will use this as the WSGI application entry point
# The variable must be named 'app' for Vercel to detect it
