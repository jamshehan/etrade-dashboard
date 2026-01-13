# eTrade Transaction Dashboard

A Python-based web application for automatically scraping, storing, and visualizing eTrade checking account transaction data.

## Features

- **Automated Data Collection**: Headless browser scraping of eTrade transaction data
- **CSV Import**: Parse and import eTrade CSV exports
- **Transaction Management**: Search, filter, and view all transactions
- **Statistics Dashboard**:
  - Total deposits/withdrawals
  - Deposits by source
  - Monthly breakdowns
  - Category analysis
- **Balance Projections**: Project future account balance based on recurring transactions
- **Recurring Transaction Detection**: Automatically identify recurring deposits and withdrawals

## Tech Stack

- **Backend**: Python, Flask
- **Database**: PostgreSQL (production) / SQLite (local development)
- **Web Scraping**: Playwright (local only)
- **Data Processing**: Pandas
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Deployment**: Vercel (planned)

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
python -m playwright install chromium
```

### 3. Configure Environment

Copy the example environment file and configure your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your eTrade credentials:

```
ETRADE_USERNAME=your_username
ETRADE_PASSWORD=your_password
```

### 4. Customize the Scraper

The web scraper needs to be customized for your eTrade account. The selectors in `scraper.py` are templates and need to be updated.

#### Option A: Use Test Mode to Find Selectors

```bash
python scraper.py test
```

This will open a browser and guide you through identifying the correct CSS selectors for:
- Username input field
- Password input field
- Login button
- Download button

#### Option B: Manual Customization

1. Open eTrade in your browser
2. Right-click on elements and "Inspect"
3. Find the CSS selectors or element IDs
4. Update the selectors in `scraper.py` in these methods:
   - `_login()`: Login form selectors
   - `_navigate_to_checking()`: Navigation selectors
   - `_download_csv()`: Download button selectors

### 5. Test CSV Import

Before running the scraper, test with a manually downloaded CSV:

1. Log into eTrade manually
2. Download a transaction CSV
3. Run the import:

```bash
python cli.py import path/to/your/file.csv
```

### 6. Start the Application

```bash
python app.py
```

The dashboard will be available at: `http://localhost:5000`

## Project Structure

```
etrade-dashboard/
├── app.py                 # Flask web application
├── scraper.py             # eTrade web scraper (local only)
├── database.py            # SQLite database management (local dev)
├── database_pg.py         # PostgreSQL database management (production)
├── csv_parser.py          # CSV parsing logic
├── projections.py         # Balance projection calculations
├── config.py              # Configuration management
├── cli.py                 # Command-line interface
├── migration_export.py    # Export SQLite data to JSON
├── migration_import.py    # Import JSON data to PostgreSQL
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create from .env.example)
├── data/                  # Data storage
│   ├── downloads/         # Downloaded CSV files
│   └── transactions.db    # SQLite database (local dev)
└── static/                # Frontend files
    ├── index.html
    ├── style.css
    └── app.js
```

## Usage

### Command Line Interface

The CLI tool provides convenient commands for managing the dashboard:

```bash
# Import a CSV file
python cli.py import path/to/transactions.csv

# Run the scraper
python cli.py scrape

# Start the web application
python cli.py serve

# View statistics
python cli.py stats
```

### Web Interface

#### Overview Tab
- View total transactions, deposits, withdrawals
- See deposits by source
- Monthly transaction breakdown
- Recurring transaction detection

#### Transactions Tab
- Browse all transactions
- Search by description
- Filter by date range, category, source
- Pagination for large datasets

#### Statistics Tab
- Detailed analytics with custom date ranges
- Deposits by source breakdown
- Monthly summaries
- Category-wise spending

#### Projections Tab
- Set current balance
- Add recurring deposits and withdrawals
- Calculate projected balance for future months
- View monthly projections table

## CSV Format

The parser expects eTrade CSV files with these columns:
- **Date** or **Transaction Date**: Transaction date
- **Description**: Transaction description
- **Amount**: Transaction amount (positive for deposits, negative for withdrawals)
- **Balance**: Account balance after transaction (optional)

The parser is flexible and will attempt to map column names automatically.

## Customization

### Adding Categories

The system automatically categorizes transactions based on keywords in `csv_parser.py`. To customize:

1. Open `csv_parser.py`
2. Edit the `_categorize_transaction()` method
3. Add your own keywords and categories

### Database Schema

The SQLite database stores transactions with these fields:
- transaction_date
- description
- amount
- balance
- category
- source
- notes
- csv_hash (for duplicate detection)
- imported_at

You can extend the schema in `database.py` if needed.

## Troubleshooting

### Scraper Issues

If the scraper fails:

1. Check your credentials in `.env`
2. Run in non-headless mode by setting `HEADLESS=False` in `.env`
3. Use test mode: `python scraper.py test`
4. Check the error screenshots in `data/downloads/`
5. Update selectors in `scraper.py` if eTrade changed their website

### CSV Import Issues

If CSV import fails:

1. Check the CSV format - ensure it has Date, Description, and Amount columns
2. Try manually editing the column mapping in `csv_parser.py`
3. Check for encoding issues (use UTF-8)

### Database Issues

To reset the database:

```bash
rm data/transactions.db
python app.py  # Will recreate the database
```

## Security Notes

- Never commit your `.env` file or share your credentials
- The `.gitignore` is configured to exclude sensitive files
- Store your database securely
- Consider using environment-specific credentials

## Future Enhancements

Potential features to add:
- Export functionality (Excel, PDF reports)
- Email notifications for low balance
- Budget tracking and alerts
- Multi-account support
- Advanced data visualizations (charts)
- Mobile-responsive improvements
- Transaction editing and tagging

## License

This project is for personal use. Ensure compliance with eTrade's terms of service when scraping their website.
