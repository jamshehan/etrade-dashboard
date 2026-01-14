# CLAUDE.MD

This document provides context about the eTrade Transaction Dashboard project for Claude Code and future development sessions.

## Project Overview

**Name**: eTrade Transaction Dashboard
**Purpose**: Automated web scraping, storage, and visualization of eTrade checking account transaction data
**Status**: Active Development - Preparing for Production Deployment
**Created**: January 2026

## Architecture

### Tech Stack
- **Backend**: Python 3.x with Flask web framework
- **Database**: PostgreSQL (production) / SQLite (local development)
- **Web Scraping**: Playwright (headless Chromium) - local only
- **Data Processing**: Pandas for CSV parsing and data manipulation
- **Frontend**: Vanilla JavaScript, HTML5, CSS3 (no frameworks)
- **Deployment Target**: Vercel (serverless)

### Core Components

1. **app.py** - Flask web server
   - RESTful API endpoints for transactions, statistics, and projections
   - Authentication endpoints (/api/auth/config, /api/user/me, /api/webhooks/clerk)
   - User management endpoints (/api/users, /api/users/<auth_id>/role)
   - Auto-detects PostgreSQL vs SQLite based on DATABASE_URL env var
   - Serves static frontend files
   - Handles CORS and error responses

2. **database.py** - SQLite database layer (local development)
   - Transaction CRUD operations
   - Duplicate detection via CSV hash
   - Recurring transaction identification
   - Statistics and aggregation queries

3. **database_pg.py** - PostgreSQL database layer (production)
   - Same interface as database.py for seamless switching
   - Connection pooling via psycopg2 SimpleConnectionPool (serverless-optimized)
   - User management methods for authentication (create_user, get_user_by_auth_id, update_user_role)
   - Users table for role-based access control

4. **scraper.py** - eTrade web scraper
   - Playwright-based headless browser automation
   - Logs into eTrade, navigates to checking account, downloads CSV
   - Requires customization of CSS selectors per user's eTrade layout
   - Test mode available for selector identification
   - **Note**: Runs locally only (Playwright incompatible with Vercel serverless)

5. **csv_parser.py** - CSV import logic
   - Flexible column mapping for eTrade CSV exports
   - Automatic transaction categorization (Income, Transfer, Purchase, etc.)
   - Source identification (PayPal, Venmo, Direct Deposit, etc.)
   - Balance tracking

6. **projections.py** - Balance forecasting
   - Calculates future account balance based on recurring transactions
   - Supports one-time and recurring deposits/withdrawals
   - Monthly projection calculations

7. **cli.py** - Command-line interface
   - Import, scrape, serve, stats, list, search commands
   - Colored output using colorama
   - Main entry point for automation and testing

8. **config.py** - Configuration management
   - Loads environment variables from .env
   - Auto-detects database type (USE_POSTGRES flag)
   - Defines data directories and paths
   - Clerk authentication configuration

9. **auth_middleware.py** - Authentication middleware
   - Clerk JWT verification using JWKS
   - `@require_auth` decorator for protected endpoints
   - `@require_admin` decorator for admin-only endpoints
   - Dev mode bypass when FLASK_DEBUG=true and Clerk not configured
   - Token extraction from Authorization Bearer header

10. **migration_export.py** - SQLite to JSON export script
    - Exports transactions and person_mappings to JSON
    - Used for migrating local data to production PostgreSQL

11. **migration_import.py** - JSON to PostgreSQL import script
    - Imports JSON data to PostgreSQL
    - Validates data before import (--dry-run mode)
    - Handles duplicates gracefully

### Database Schema

**users** table (PostgreSQL only):
- `id` (SERIAL PRIMARY KEY)
- `email` (VARCHAR(255) UNIQUE)
- `full_name` (VARCHAR(255))
- `role` (VARCHAR(20)) - 'admin' or 'viewer'
- `auth_provider_id` (VARCHAR(255) UNIQUE) - Clerk user ID
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- `last_login` (TIMESTAMP)

**transactions** table:
- `id` (SERIAL/INTEGER PRIMARY KEY)
- `transaction_date` (DATE)
- `description` (TEXT)
- `amount` (DECIMAL(12,2)/REAL)
- `balance` (DECIMAL(12,2)/REAL)
- `category` (VARCHAR(100)/TEXT) - Auto-categorized: Income, Transfer, Purchase, Fee, etc.
- `source` (VARCHAR(100)/TEXT) - PayPal, Venmo, Direct Deposit, etc.
- `notes` (TEXT)
- `csv_hash` (VARCHAR(64)/TEXT) - For duplicate detection
- `imported_at` (TIMESTAMP)

**person_mappings** table:
- `id` (SERIAL/INTEGER PRIMARY KEY)
- `person_name` (VARCHAR(255)/TEXT)
- `keyword` (VARCHAR(255)/TEXT)
- `created_at` (TIMESTAMP)

### Frontend Structure

**static/** directory:
- `index.html` - Single-page app with auth screens and tab-based navigation
- `style.css` - Responsive styling, auth screens, user menu, admin-only elements
- `app.js` - Clerk SDK integration, auth state management, API calls with JWT

**Auth Flow**:
1. **Loading Screen** - Shows while checking auth state
2. **Sign-In Screen** - Clerk sign-in component for unauthenticated users
3. **Main App** - Dashboard with user menu showing email, role, sign-out button

**Role-Based UI**:
- Admin users see: Import CSV, Scrape eTrade buttons, delete buttons on mappings
- Viewer users see: Read-only access to all data
- Elements with `.admin-only` class hidden for non-admin users

**Tabs**:
1. **Transactions** - Searchable, filterable transaction list with pagination
2. **Statistics** - Total deposits/withdrawals, deposits by source, monthly breakdown
3. **Contributions** - Person-to-keyword mapping for tracking contributions
4. **Projections** - Balance forecasting tool with recurring transaction management

## Key Design Decisions

### 1. Dual Database Support
- SQLite for local development (zero setup, file-based)
- PostgreSQL for production (Vercel Postgres / Neon)
- `config.USE_POSTGRES` flag auto-detects based on DATABASE_URL
- Same TransactionDatabase interface for both backends

### 2. Web Scraping Approach
- Chose Playwright over Selenium for better headless performance
- Selector customization required per user due to eTrade's dynamic UI
- Test mode implemented to help users find correct selectors
- Screenshots saved on error for debugging
- **Production Note**: Scraper runs locally, not on Vercel (Playwright requires browser binaries)

### 3. Data Storage
- CSV hash prevents duplicate imports
- All dates stored in ISO format (YYYY-MM-DD) for consistency
- Recurring transactions detected by pattern matching descriptions
- Connection pooling in PostgreSQL for serverless environments

### 4. Categorization Logic
- Keyword-based categorization in csv_parser.py
- Categories: Income, Transfer, Purchase, Fee, Check, ATM
- Source detection for common payment platforms
- Easily extensible by modifying `_categorize_transaction()` method

### 5. Frontend Architecture
- No JavaScript framework to keep dependencies minimal
- Single-page app with tab navigation
- Vanilla JS fetch API for backend communication
- Responsive tables with pagination

### 6. Authentication & Security
- **Clerk Integration**: JWT-based authentication with JWKS verification
- **Role-Based Access Control**: Admin and viewer roles
- **Protected Endpoints**: All API endpoints require valid JWT (except /api/auth/config)
- **Admin-Only Actions**: CSV import, scraping, user management, mapping deletion
- **Dev Mode Bypass**: Auth skipped when FLASK_DEBUG=true and Clerk not configured
- Credentials stored in .env file (gitignored)
- Database stored locally in data/ directory (SQLite) or cloud (PostgreSQL)

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

4. **PostgreSQL Migration** (Phase 1 - Production Prep)
   - Created database_pg.py with connection pooling
   - Added users table for authentication support
   - Created migration scripts (migration_export.py, migration_import.py)
   - Updated app.py to auto-detect database type
   - Updated config.py with PostgreSQL and Clerk settings
   - Added psycopg2, pyjwt, cryptography dependencies

5. **Clerk Authentication** (Phase 2 - Production Prep)
   - Created auth_middleware.py with JWT verification and decorators
   - Added @require_auth to all API endpoints
   - Added @require_admin for sensitive operations (import, scrape, user mgmt)
   - New endpoints: /api/auth/config, /api/user/me, /api/webhooks/clerk, /api/users
   - Frontend Clerk SDK integration with dynamic loading
   - Auth screens (loading, sign-in) and user menu in header
   - Role-based UI hiding admin-only elements for viewers
   - CSS styles for auth screens and user menu

### Planned Features (Production Deployment)
- **Phase 3**: Vercel deployment configuration
- **Phase 4**: Production testing and webhook setup

## Configuration

### Environment Variables (.env)

```bash
# eTrade credentials (for local scraper)
ETRADE_USERNAME=your_username
ETRADE_PASSWORD=your_password

# Database configuration
# Leave empty for SQLite (local dev), set for PostgreSQL (production)
DATABASE_URL=postgresql://user:password@host:port/database

# Flask settings
FLASK_PORT=5000
FLASK_DEBUG=False
FLASK_SECRET_KEY=generate-a-secure-random-key

# Clerk authentication (for production)
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_JWKS_URL=https://your-app.clerk.accounts.dev/.well-known/jwks.json

# Scraper settings
HEADLESS=True
SCRAPER_TIMEOUT=60000
```

### Data Directory Structure
```
data/
├── downloads/              # Downloaded CSV files from scraper
│   └── *.csv
├── transactions.db         # SQLite database (local dev)
└── migration_export.json   # Export file for PostgreSQL migration
```

## Common Development Tasks

### Switching Between SQLite and PostgreSQL
- **SQLite (local)**: Remove or comment out DATABASE_URL in .env
- **PostgreSQL**: Set DATABASE_URL in .env to your connection string
- App auto-detects and uses appropriate database module

### Migrating Data to PostgreSQL
```bash
# 1. Export from SQLite
python migration_export.py

# 2. Set DATABASE_URL in .env

# 3. Validate (dry run)
python migration_import.py --dry-run

# 4. Import to PostgreSQL
python migration_import.py
```

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
2. Add database method in both `database.py` AND `database_pg.py`
3. Update frontend in `static/app.js` to call endpoint

### Database Schema Changes
- For SQLite: Modify `database.py` `init_database()` method
- For PostgreSQL: Modify `database_pg.py` `init_database()` method
- Run migration scripts if data exists

## Testing Workflow

1. **CSV Import Test**: `python cli.py import sample_transactions.csv`
2. **Web Interface Test**: `python cli.py serve` → http://localhost:5000
3. **Scraper Test**: `python scraper.py test` (interactive mode)
4. **Full Scraper Test**: `python cli.py scrape`
5. **CLI Stats Test**: `python cli.py stats`
6. **PostgreSQL Connection Test**:
   ```python
   python -c "from database_pg import TransactionDatabase; db = TransactionDatabase(); print(db.get_statistics())"
   ```

## Dependencies

Key Python packages (requirements.txt):
```
# Web framework
flask==3.0.0
flask-cors==4.0.0

# Database
psycopg2-binary==2.9.9

# Authentication (JWT verification)
pyjwt==2.8.0
cryptography==41.0.7
requests==2.31.0

# Data processing
pandas==2.2.0
python-dateutil==2.8.2

# Environment management
python-dotenv==1.0.0

# Web scraping (local development only)
playwright==1.41.0
```

## Git Repository

- **Branch**: master
- **Remote**: Origin on GitHub (jamshehan/etrade-dashboard)
- **Recent PRs**: #1 (happy-ptolemy branch merged)

## Notes for Claude Code

### When Working on This Project
1. Always test scraper changes in non-headless mode first
2. Database changes must be made in BOTH database.py and database_pg.py
3. Frontend changes should maintain vanilla JS (no framework dependencies)
4. CSV parser changes should be backward compatible with existing data
5. Security: Never log or expose credentials, always use .env
6. Test with both SQLite and PostgreSQL when modifying database code

### Codebase Patterns
- Error handling: Log errors and return meaningful messages
- Database: Use context managers for connections (especially PostgreSQL)
- API responses: Consistent JSON format `{"success": true/false, "data/error": ...}`
- Dates: ISO format (YYYY-MM-DD) throughout
- CLI: Use colorama for output (green=success, red=error, yellow=warning)
- PostgreSQL: Convert Decimal types to float for JSON serialization

### Testing Considerations
- Test with both empty and populated databases
- Verify duplicate detection works (CSV hash)
- Test with various CSV formats from eTrade
- Check date handling across timezones
- Verify projections calculations manually
- Test PostgreSQL connection pooling under load

## Current Status

### Completed
- [x] Phase 1: PostgreSQL migration
  - database_pg.py with connection pooling
  - Migration scripts
  - Dual database support in app.py

- [x] Phase 2: Clerk authentication
  - auth_middleware.py with JWT verification
  - Protected API endpoints with @require_auth
  - Admin-only endpoints with @require_admin
  - Frontend Clerk SDK integration
  - Auth screens and role-based UI

### In Progress
- [ ] Phase 3: Vercel deployment configuration
- [ ] Phase 4: Production testing and webhook setup

---

Last Updated: 2026-01-13
