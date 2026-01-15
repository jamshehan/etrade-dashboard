# Mortgage Payment Account Dashboard

A Python-based web application for automatically scraping, storing, and visualizing bank account transaction data. Originally built for eTrade checking accounts, now deployed in production.

**Live Site**: [www.hansen.onl](https://www.hansen.onl)

## Features

- **Automated Data Collection**: Headless browser scraping of transaction data (local only)
- **CSV Import**: Parse and import bank CSV exports
- **Transaction Management**: Search, filter, and view all transactions
- **Statistics Dashboard**:
  - Total deposits/withdrawals
  - Deposits by source
  - Monthly breakdowns
  - Category analysis
- **Contributions Tracking**: Map transactions to people by keywords
- **Balance Projections**: Project future account balance based on recurring transactions
- **Role-Based Access**: Admin and viewer roles with Clerk authentication

## Tech Stack

- **Backend**: Python 3.10, Flask
- **Database**: PostgreSQL (Neon) for production, SQLite for local dev
- **Authentication**: Clerk (JWT-based)
- **Web Scraping**: Playwright (local development only)
- **Data Processing**: Pandas
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Deployment**: Vercel (serverless)

## Production Deployment

The app is deployed on Vercel with:
- Serverless Python functions via `@vercel/python`
- Static files served via Vercel CDN from `public/`
- PostgreSQL database on Neon
- Clerk authentication with Google OAuth

### Environment Variables (Vercel)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `FLASK_SECRET_KEY` | Secure random string |
| `CLERK_PUBLISHABLE_KEY` | Clerk public key |
| `CLERK_SECRET_KEY` | Clerk secret key |
| `CLERK_JWKS_URL` | Clerk JWKS endpoint |

## Local Development Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers (for scraping)

```bash
python -m playwright install chromium
```

### 3. Configure Environment

Create a `.env` file:

```bash
# Database (leave empty for SQLite, set for PostgreSQL)
DATABASE_URL=

# Flask
FLASK_DEBUG=True
FLASK_SECRET_KEY=dev-secret-key

# Scraper credentials (optional)
ETRADE_USERNAME=your_username
ETRADE_PASSWORD=your_password

# Clerk (optional for local dev - auth bypassed in debug mode)
CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
CLERK_JWKS_URL=
```

### 4. Start the Application

```bash
python cli.py serve
```

The dashboard will be available at: `http://localhost:5000`

## Project Structure

```
etrade-dashboard/
├── api/
│   └── index.py           # Vercel serverless entry point
├── public/                # Static files (served by Vercel CDN)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── app.py                 # Flask web application
├── auth_middleware.py     # Clerk JWT authentication
├── config.py              # Configuration management
├── database.py            # SQLite database (local dev)
├── database_pg.py         # PostgreSQL database (production)
├── csv_parser.py          # CSV parsing logic
├── projections.py         # Balance projection calculations
├── scraper.py             # Web scraper (local only)
├── cli.py                 # Command-line interface
├── logging_config.py      # Logging configuration
├── make_admin.py          # Admin role utility
├── vercel.json            # Vercel deployment config
├── runtime.txt            # Python version for Vercel
└── requirements.txt       # Python dependencies
```

## Usage

### Command Line Interface

```bash
# Import a CSV file
python cli.py import path/to/transactions.csv

# Run the scraper (local only)
python cli.py scrape

# Start the web server
python cli.py serve

# View statistics
python cli.py stats
```

### Web Interface

- **Transactions Tab**: Browse, search, and filter transactions
- **Statistics Tab**: View analytics with custom date ranges
- **Contributions Tab**: Track contributions by person with keyword mapping
- **Projections Tab**: Calculate future balance projections

### User Roles

- **Admin**: Full access including CSV import, scraping, user management
- **Viewer**: Read-only access to all data

## Serverless Limitations

The following features are only available in local development:
- Web scraping (requires Playwright browser)
- CSV import from filesystem paths

In production, these endpoints return `501 Not Implemented`.

## Security

- JWT-based authentication via Clerk
- Role-based access control
- Protected API endpoints
- Environment variables for secrets
- CORS enabled

## License

This project is for personal use.
