# CLAUDE.MD

This document provides context about the eTrade Transaction Dashboard project for Claude Code and future development sessions.

## Project Overview

**Name**: eTrade Transaction Dashboard
**Purpose**: Automated web scraping, storage, and visualization of eTrade checking account transaction data
**Status**: Active Development
**Created**: January 2026

## Architecture

### Tech Stack
- **Backend**: Python 3.x with Flask web framework
- **Database**: SQLite for transaction storage
- **Web Scraping**: Playwright (headless Chromium)
- **Data Processing**: Pandas for CSV parsing and data manipulation
- **Frontend**: Vanilla JavaScript, HTML5, CSS3 (no frameworks)

### Core Components

1. **app.py** - Flask web server
   - RESTful API endpoints for transactions, statistics, and projections
   - Serves static frontend files
   - Handles CORS and error responses

2. **scraper.py** - eTrade web scraper
   - Playwright-based headless browser automation
   - Logs into eTrade, navigates to checking account, downloads CSV
   - Requires customization of CSS selectors per user's eTrade layout
   - Test mode available for selector identification

3. **database.py** - SQLite database layer
   - Transaction CRUD operations
   - Duplicate detection via CSV hash
   - Recurring transaction identification
   - Statistics and aggregation queries

4. **csv_parser.py** - CSV import logic
   - Flexible column mapping for eTrade CSV exports
   - Automatic transaction categorization (Income, Transfer, Purchase, etc.)
   - Source identification (PayPal, Venmo, Direct Deposit, etc.)
   - Balance tracking

5. **projections.py** - Balance forecasting
   - Calculates future account balance based on recurring transactions
   - Supports one-time and recurring deposits/withdrawals
   - Monthly projection calculations

6. **cli.py** - Command-line interface
   - Import, scrape, serve, stats, list, search commands
   - Colored output using colorama
   - Main entry point for automation and testing

7. **config.py** - Configuration management
   - Loads environment variables from .env
   - Defines data directories and paths

### Database Schema

**transactions** table:
- `id` (INTEGER PRIMARY KEY)
- `transaction_date` (TEXT)
- `description` (TEXT)
- `amount` (REAL)
- `balance` (REAL)
- `category` (TEXT) - Auto-categorized: Income, Transfer, Purchase, Fee, etc.
- `source` (TEXT) - PayPal, Venmo, Direct Deposit, etc.
- `notes` (TEXT)
- `csv_hash` (TEXT) - For duplicate detection
- `imported_at` (TIMESTAMP)

### Frontend Structure

**static/** directory:
- `index.html` - Single-page app with tab-based navigation
- `style.css` - Responsive styling, dark header, table formatting
- `app.js` - JavaScript for API calls, DOM manipulation, tab switching

**Tabs**:
1. **Statistics** - Total deposits/withdrawals, deposits by source, monthly breakdown
2. **Transactions** - Searchable, filterable transaction list with pagination
3. **Projections** - Balance forecasting tool with recurring transaction management

## Key Design Decisions

### 1. Web Scraping Approach
- Chose Playwright over Selenium for better headless performance
- Selector customization required per user due to eTrade's dynamic UI
- Test mode implemented to help users find correct selectors
- Screenshots saved on error for debugging

### 2. Data Storage
- SQLite chosen for simplicity (no server setup required)
- CSV hash prevents duplicate imports
- All dates stored as TEXT in ISO format for easy parsing
- Recurring transactions detected by pattern matching descriptions

### 3. Categorization Logic
- Keyword-based categorization in csv_parser.py
- Categories: Income, Transfer, Purchase, Fee, Check, ATM
- Source detection for common payment platforms
- Easily extensible by modifying `_categorize_transaction()` method

### 4. Frontend Architecture
- No JavaScript framework to keep dependencies minimal
- Single-page app with tab navigation
- Vanilla JS fetch API for backend communication
- Responsive tables with pagination

### 5. Security
- Credentials stored in .env file (gitignored)
- No authentication on web interface (assumes local/trusted use)
- Database stored locally in data/ directory

## Development History

### Initial Implementation
- Basic Flask app with transaction import from CSV
- SQLite database with transaction schema
- Simple web interface with transaction listing

### Key Features Added
1. **Web Scraper** (commit b12bb8f)
   - Playwright integration for automated eTrade login and CSV download
   - Customizable selector system
   - Test mode for selector identification

2. **Projections Feature** (commit 5639ab7)
   - Balance forecasting based on recurring transactions
   - Automated population from database data
   - Monthly projection calculations

3. **Bug Fixes**
   - Date parsing timezone issue fixed (commit 167d815)
   - Contributions tab reorganized and simplified

### Known Issues & Limitations
1. Scraper requires manual selector customization per user
2. No multi-account support (single checking account only)
3. No transaction editing through web UI
4. No data export functionality (Excel, PDF)
5. Web interface has no authentication (local use only)

## Configuration

### Environment Variables (.env)
```
ETRADE_USERNAME=your_username
ETRADE_PASSWORD=your_password
HEADLESS=True  # Set to False for debugging scraper
```

### Data Directory Structure
```
data/
├── downloads/        # Downloaded CSV files from scraper
│   └── *.csv
└── transactions.db   # SQLite database
```

## Common Development Tasks

### Adding New Categories
Edit `csv_parser.py`, modify `_categorize_transaction()` method:
```python
if 'KEYWORD' in desc:
    return 'CATEGORY', 'SOURCE'
```

### Updating Scraper Selectors
Edit `scraper.py`, update CSS selectors in:
- `_login()` - Login form elements
- `_navigate_to_checking()` - Navigation elements
- `_download_csv()` - Download button

### Adding New API Endpoints
1. Add route in `app.py`
2. Add database method in `database.py` if needed
3. Update frontend in `static/app.js` to call endpoint

### Database Migrations
Currently manual - modify schema in `database.py` `_create_tables()` method.
Existing databases will need manual migration or recreation.

## Testing Workflow

1. **CSV Import Test**: `python cli.py import sample_transactions.csv`
2. **Web Interface Test**: `python cli.py serve` → http://localhost:5000
3. **Scraper Test**: `python scraper.py test` (interactive mode)
4. **Full Scraper Test**: `python cli.py scrape`
5. **CLI Stats Test**: `python cli.py stats`

## Future Enhancement Ideas

### High Priority
- Transaction editing through web UI
- Data export (Excel, PDF, CSV)
- Better error handling in scraper
- Mobile-responsive improvements

### Medium Priority
- Budget tracking and alerts
- Email notifications for low balance
- Advanced visualizations (charts/graphs)
- Multi-account support

### Low Priority
- Transaction tagging system
- Spending insights and analytics
- Scheduled automatic scraping (cron job)
- Cloud deployment option

## Dependencies

Key Python packages (requirements.txt):
- `flask` - Web framework
- `playwright` - Browser automation
- `pandas` - Data processing
- `python-dotenv` - Environment management
- `colorama` - CLI colored output

## Git Repository

- **Branch**: master
- **Remote**: Origin on GitHub (jamshehan/etrade-dashboard)
- **Recent PRs**: #1 (happy-ptolemy branch merged)

## Notes for Claude Code

### When Working on This Project
1. Always test scraper changes in non-headless mode first
2. Database changes require careful consideration of existing data
3. Frontend changes should maintain vanilla JS (no framework dependencies)
4. CSV parser changes should be backward compatible with existing data
5. Security: Never log or expose credentials, always use .env

### Codebase Patterns
- Error handling: Log errors and return meaningful messages
- Database: Use context managers for connections
- API responses: Consistent JSON format `{"status": "success/error", "data/message": ...}`
- Dates: ISO format (YYYY-MM-DD) throughout
- CLI: Use colorama for output (green=success, red=error, yellow=warning)

### Testing Considerations
- Test with both empty and populated databases
- Verify duplicate detection works (CSV hash)
- Test with various CSV formats from eTrade
- Check date handling across timezones
- Verify projections calculations manually

## Contact & Support

This is a personal project for tracking eTrade checking account transactions. The scraper requires customization per user's eTrade account layout.

---

Last Updated: 2026-01-13
