# Quick Start Guide

Get your Mortgage Payment Account Dashboard up and running locally in minutes!

> **Production Site**: The app is deployed at [www.hansen.onl](https://www.hansen.onl)

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Step 2: Configure Environment

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:

```
# Leave DATABASE_URL empty to use SQLite locally
DATABASE_URL=

# Flask settings
FLASK_DEBUG=True
FLASK_SECRET_KEY=dev-secret-key

# Optional: Bank credentials for scraper
ETRADE_USERNAME=your_username
ETRADE_PASSWORD=your_password
```

## Step 3: Test with Manual CSV Import

Before setting up the scraper, test with a manually downloaded CSV:

1. Log into your bank
2. Download a transaction CSV
3. Import it:

```bash
python cli.py import "C:\path\to\your\transactions.csv"
```

## Step 4: Start the Dashboard

```bash
python cli.py serve
```

Open your browser to: `http://localhost:5000`

> **Note**: In debug mode without Clerk configured, authentication is bypassed and you get admin access automatically.

## Step 5: Configure the Scraper (Optional)

To enable automatic scraping, customize the web scraper with the correct CSS selectors:

### Option A: Interactive Test Mode

```bash
python scraper.py test
```

This will:
1. Open a browser window
2. Guide you through finding the correct selectors
3. Show you what values to update in `scraper.py`

### Option B: Manual Configuration

1. Open `scraper.py`
2. Find the `_login()`, `_navigate_to_checking()`, and `_download_csv()` methods
3. Update the CSS selectors marked with `TODO` comments

### Testing the Scraper

Once configured, test it:

```bash
python cli.py scrape
```

## Common Commands

```bash
# View statistics
python cli.py stats

# List recent transactions
python cli.py list -n 20

# Search transactions
python cli.py search "grocery"

# Import a CSV
python cli.py import path/to/file.csv

# Scrape account (local only)
python cli.py scrape

# Start web server
python cli.py serve
```

## Troubleshooting

### "Module not found" error
Make sure you installed dependencies: `pip install -r requirements.txt`

### Playwright browser error
Install browsers: `python -m playwright install chromium`

### Scraper fails
1. Set `HEADLESS=False` in `.env` to see what's happening
2. Run test mode: `python scraper.py test`
3. Update selectors in `scraper.py`

### CSV import fails
Check that your CSV has columns: Date, Description, Amount

## Next Steps

1. Explore the Transactions tab to see your transaction list
2. Use the Statistics tab for analytics
3. Set up Contributions to track payments by person
4. Try the Projections tab to forecast your future balance

## Need Help?

- Check the full README.md for detailed documentation
- Review CLAUDE.MD for development context
- Check error messages in the console for hints
