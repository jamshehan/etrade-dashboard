"""
Vercel serverless entry point for Flask app.
This file imports the Flask app instance from the main app.py module.
"""
from app import app

# Vercel will use this as the WSGI application entry point
