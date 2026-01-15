# CLAUDE.MD

This document provides context about the Mortgage Payment Account Dashboard project for Claude Code and future development sessions.

## Project Overview

**Name**: Mortgage Payment Account Dashboard
**Purpose**: Automated web scraping, storage, and visualization of bank account transaction data
**Status**: Production - Deployed and Running
**Production URL**: https://www.hansen.onl
**Created**: January 2026

## Architecture

### Tech Stack
- **Backend**: Python 3.10 with Flask web framework
- **Database**: PostgreSQL (Neon) for production / SQLite for local development
- **Authentication**: Clerk (JWT-based with Google OAuth)
- **Web Scraping**: Playwright (headless Chromium) - local only
- **Data Processing**: Pandas for CSV parsing and data manipulation
- **Frontend**: Vanilla JavaScript, HTML5, CSS3 (no frameworks)
- **Deployment**: Vercel (serverless)

### Core Components

1. **api/index.py** - Vercel serverless entry point
   - Imports Flask app from app.py
   - Handles sys.path configuration for imports

2. **app.py** - Flask web server
   - RESTful API endpoints for transactions, statistics, and projections
   - Authentication endpoints (/api/auth/config, /api/user/me, /api/webhooks/clerk)
   - User management endpoints (/api/users, /api/users/<auth_id>/role)
   - Feature detection endpoint (/api/features)
   - Auto-detects PostgreSQL vs SQLite based on DATABASE_URL env var
   - Environment detection (IS_VERCEL) for serverless compatibility
   - Centralized error handlers with logging

3. **database.py** - SQLite database layer (local development)
   - Transaction CRUD operations
   - Duplicate detection via unique constraint (date, description, amount)
   - Recurring transaction identification
   - Statistics and aggregation queries

4. **database_pg.py** - PostgreSQL database layer (production)
   - Same interface as database.py for seamless switching
   - Connection pooling via psycopg2 SimpleConnectionPool (serverless-optimized)
   - User management methods for authentication
   - Row serialization for JSON compatibility (dates, Decimals)

5. **scraper.py** - Web scraper (local only)
   - Playwright-based headless browser automation
   - Logs into bank, navigates to account, downloads CSV
   - Requires customization of CSS selectors
   - Test mode available for selector identification
   - **Note**: Disabled in production (returns 501)

6. **csv_parser.py** - CSV import logic
   - Flexible column mapping for bank CSV exports
   - Automatic transaction categorization
   - Source identification
   - Balance tracking

7. **projections.py** - Balance forecasting
   - Calculates future account balance based on recurring transactions
   - Supports one-time and recurring deposits/withdrawals
   - Monthly projection calculations

8. **cli.py** - Command-line interface
   - Import, scrape, serve, stats, list, search commands
   - Colored output using colorama
   - Main entry point for local development

9. **config.py** - Configuration management
   - Loads environment variables from .env
   - Auto-detects database type (USE_POSTGRES flag)
   - Auto-detects Vercel environment (IS_VERCEL flag)
   - Skips directory creation in serverless (read-only filesystem)

10. **auth_middleware.py** - Authentication middleware
    - Clerk JWT verification using JWKS
    - `@require_auth` decorator for protected endpoints
    - `@require_admin` decorator for admin-only endpoints
    - Dev mode bypass when FLASK_DEBUG=true and Clerk not configured
    - Security event logging

11. **logging_config.py** - Logging configuration
    - Environment-aware log levels (DEBUG in dev, INFO in prod)
    - Stdout output for Vercel log capture
    - Module-specific child loggers

12. **make_admin.py** - Admin role utility
    - CLI tool to grant admin role to users
    - Works with production PostgreSQL database

### Database Schema

**users** table (PostgreSQL only):
- `id` (SERIAL PRIMARY KEY)
- `email` (VARCHAR(255) UNIQUE)
- `full_name` (VARCHAR(255))
- `role` (VARCHAR(20)) - 'admin' or 'viewer'
- `auth_provider_id` (VARCHAR(255) UNIQUE) - Clerk user ID
- `created_at`, `updated_at`, `last_login` (TIMESTAMP)

**transactions** table:
- `id` (SERIAL/INTEGER PRIMARY KEY)
- `transaction_date` (DATE)
- `description` (TEXT)
- `amount` (DECIMAL(12,2)/REAL)
- `balance` (DECIMAL(12,2)/REAL)
- `category`, `source`, `notes` (TEXT)
- `csv_hash` (TEXT) - For tracking import source
- `imported_at` (TIMESTAMP)
- UNIQUE constraint on (transaction_date, description, amount)

**person_mappings** table:
- `id` (SERIAL/INTEGER PRIMARY KEY)
- `person_name`, `keyword` (TEXT)
- `created_at` (TIMESTAMP)

### Frontend Structure

**public/** directory (served by Vercel CDN):
- `index.html` - Single-page app with auth screens and tab-based navigation
- `style.css` - Responsive styling, auth screens, user menu
- `app.js` - Clerk SDK integration, auth state management, feature detection

**Auth Flow**:
1. **Loading Screen** - Shows while checking auth state
2. **Sign-In Screen** - Clerk sign-in with Google OAuth
3. **Main App** - Dashboard with user menu showing email, role, sign-out

**Role-Based UI**:
- Admin users see: Import CSV, Scrape Account buttons, delete buttons
- Viewer users see: Read-only access to all data
- Feature detection hides unavailable features in production

**Tabs**:
1. **Transactions** - Searchable, filterable transaction list with pagination
2. **Statistics** - Total deposits/withdrawals, deposits by source, monthly breakdown
3. **Contributions** - Person-to-keyword mapping for tracking contributions
4. **Projections** - Balance forecasting tool

## Vercel Deployment

### Configuration Files

**vercel.json**:
```json
{
  "version": 2,
  "builds": [
    { "src": "api/index.py", "use": "@vercel/python" },
    { "src": "public/**", "use": "@vercel/static" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "/api/index.py" },
    { "src": "/(.*\\.(js|css|ico|png|jpg|jpeg|svg|woff|woff2))", "dest": "/public/$1" },
    { "src": "/(.*)", "dest": "/public/index.html" }
  ]
}
```

**runtime.txt**: `python-3.10`

### Serverless Limitations
- Scraper disabled (requires Playwright browser binaries)
- CSV import from filesystem disabled (read-only filesystem)
- These endpoints return 501 Not Implemented with clear messages
- Feature detection API allows frontend to hide unavailable UI

### Environment Variables (Vercel Dashboard)
- `DATABASE_URL` - Neon PostgreSQL connection string
- `FLASK_SECRET_KEY` - Secure random string
- `CLERK_PUBLISHABLE_KEY` - pk_live_...
- `CLERK_SECRET_KEY` - sk_live_...
- `CLERK_JWKS_URL` - https://clerk.hansen.onl/.well-known/jwks.json
- `VERCEL` - Auto-set to "1" by platform

## Key Design Decisions

### 1. Dual Database Support
- SQLite for local development (zero setup)
- PostgreSQL for production (Neon serverless)
- `config.USE_POSTGRES` flag auto-detects based on DATABASE_URL
- Same TransactionDatabase interface for both backends

### 2. Serverless Compatibility
- Environment detection via `IS_VERCEL` flag
- Conditional imports to avoid loading Playwright in production
- Graceful degradation with 501 responses for unavailable features
- Read-only filesystem handling in config.py

### 3. Authentication & Security
- Clerk production instance with custom domain
- Google OAuth with custom credentials
- JWT verification via JWKS
- Role-based access control (admin/viewer)
- Webhook for user sync

### 4. Static File Serving
- Production: Vercel CDN serves from public/
- Local: Flask serves from public/ directory
- Explicit routes in vercel.json for proper handling

## Configuration

### Environment Variables (.env for local)

```bash
# Database (leave empty for SQLite)
DATABASE_URL=

# Flask
FLASK_PORT=5000
FLASK_DEBUG=True
FLASK_SECRET_KEY=dev-secret-key

# Clerk (optional for local - auth bypassed in debug mode)
CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
CLERK_JWKS_URL=

# Scraper (local only)
ETRADE_USERNAME=your_username
ETRADE_PASSWORD=your_password
HEADLESS=True
SCRAPER_TIMEOUT=60000
```

## Common Development Tasks

### Local Development
```bash
# Start server (SQLite, auth bypassed)
python cli.py serve

# Import CSV
python cli.py import path/to/transactions.csv

# View statistics
python cli.py stats
```

### Database Changes
- Modify BOTH `database.py` AND `database_pg.py`
- Update the `init_database()` method in each
- Test with both SQLite and PostgreSQL

### Adding API Endpoints
1. Add route in `app.py`
2. Add database method in both database modules
3. Update `public/app.js` to call endpoint
4. Consider auth requirements (@require_auth, @require_admin)

### Granting Admin Access
```bash
# Set production DATABASE_URL
set DATABASE_URL=your_neon_connection_string
python make_admin.py
```

Or via Neon SQL Editor:
```sql
UPDATE users SET role = 'admin' WHERE email = 'user@example.com';
```

## Notes for Claude Code

### When Working on This Project
1. Database changes must be made in BOTH database.py and database_pg.py
2. Frontend files are in `public/` (not `static/`)
3. Test locally before deploying to Vercel
4. Check Vercel logs for serverless errors
5. Security: Never log or expose credentials

### Codebase Patterns
- Error handling: Centralized Flask error handlers with logging
- API responses: Consistent JSON format `{"success": true/false, "data/error": ...}`
- Dates: ISO format (YYYY-MM-DD) throughout
- PostgreSQL: Use serialize_row() for JSON compatibility
- Environment: Check IS_VERCEL for serverless-specific behavior

### Deployment
```bash
# Commit and push changes
git add . && git commit -m "message" && git push

# Vercel auto-deploys from GitHub
# Or manually: vercel --prod
```

## Project Status

### Completed
- [x] Phase 1: PostgreSQL migration (database_pg.py, migration scripts)
- [x] Phase 2: Clerk authentication (auth_middleware.py, frontend integration)
- [x] Phase 3: Vercel deployment (vercel.json, api/index.py, serverless compatibility)
- [x] Phase 4: Production testing and webhook setup

### Production Infrastructure
- **Hosting**: Vercel (serverless)
- **Database**: Neon PostgreSQL
- **Authentication**: Clerk (production instance)
- **Domain**: www.hansen.onl
- **OAuth**: Google (custom credentials)

---

Last Updated: 2026-01-14
