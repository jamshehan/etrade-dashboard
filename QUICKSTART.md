# Quick Start Guide

Get your eTrade Transaction Dashboard up and running in minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Step 2: Configure Credentials

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and add your eTrade credentials:

```
ETRADE_USERNAME=your_username
ETRADE_PASSWORD=your_password
```

## Step 3: Test with Manual CSV Import

Before setting up the scraper, test with a manually downloaded CSV:

1. Log into eTrade
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

## Step 5: Configure the Scraper (Optional)

To enable automatic scraping, you need to customize the web scraper with the correct CSS selectors for eTrade:

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
4. The selectors currently in the file are examples and will need to be customized

### Testing the Scraper

Once configured, test it:

```bash
python cli.py scrape
```

This will:
1. Open a headless browser
2. Log into eTrade
3. Download the transaction CSV
4. Import it to the database

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

# Scrape eTrade
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

1. Explore the Overview tab to see your transaction summary
2. Use the Transactions tab to search and filter
3. Check the Statistics tab for detailed analytics
4. Try the Projections tab to forecast your future balance

## Need Help?

- Check the full README.md for detailed documentation
- Review the code comments in each Python file
- Check error messages in the console for hints
