#!/usr/bin/env python3
"""
Command-line interface for Mortgage Payment Account Dashboard
"""

import argparse
import sys
from pathlib import Path
from csv_parser import import_csv_to_database
from scraper import ETradeScraper
import config

# Use PostgreSQL if DATABASE_URL is set, otherwise SQLite
if config.USE_POSTGRES:
    from database_pg import TransactionDatabase
else:
    from database import TransactionDatabase


def cmd_import(args):
    """Import a CSV file"""
    csv_path = Path(args.csv_file)

    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        return 1

    print(f"Importing {csv_path}...")

    try:
        db = TransactionDatabase()
        inserted, skipped = import_csv_to_database(csv_path, db)
        print(f"\nSuccess!")
        print(f"  - {inserted} new transactions imported")
        print(f"  - {skipped} duplicates skipped")
        return 0
    except Exception as e:
        print(f"\nError during import: {e}")
        return 1


def cmd_scrape(args):
    """Scrape eTrade and import transactions"""
    print("Starting eTrade scraper...")

    try:
        scraper = ETradeScraper()
        csv_path = scraper.download_transactions(
            start_date=args.start_date,
            end_date=args.end_date
        )

        print(f"\nDownload successful: {csv_path}")
        print("Importing to database...")

        db = TransactionDatabase()
        inserted, skipped = import_csv_to_database(csv_path, db)

        print(f"\nSuccess!")
        print(f"  - {inserted} new transactions imported")
        print(f"  - {skipped} duplicates skipped")
        return 0

    except Exception as e:
        print(f"\nError during scraping: {e}")
        return 1


def cmd_stats(args):
    """Display database statistics"""
    try:
        db = TransactionDatabase()
        stats = db.get_statistics()

        print("\n=== Transaction Statistics ===\n")
        print(f"Total Transactions: {stats['total_transactions']}")
        print(f"Total Deposits:     ${stats['total_deposits']:,.2f}")
        print(f"Total Withdrawals:  ${stats['total_withdrawals']:,.2f}")
        print(f"Net Change:         ${stats['net_change']:,.2f}")
        print(f"Average:            ${stats['avg_transaction']:,.2f}")
        print(f"Date Range:         {stats['earliest_date']} to {stats['latest_date']}")

        if stats['deposits_by_source']:
            print("\n=== Top Deposit Sources ===\n")
            for source in stats['deposits_by_source'][:5]:
                print(f"  {source['source']}: ${source['total']:,.2f} ({source['count']} txns)")

        if stats['monthly_breakdown']:
            print("\n=== Recent Monthly Breakdown ===\n")
            for month in stats['monthly_breakdown'][:6]:
                print(f"  {month['month']}: Deposits ${month['deposits']:,.2f}, "
                      f"Withdrawals ${month['withdrawals']:,.2f}, "
                      f"Net ${month['net']:,.2f}")

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        return 1


def cmd_serve(args):
    """Start the web server"""
    print(f"Starting eTrade Dashboard on http://localhost:{config.FLASK_PORT}")
    if config.USE_POSTGRES:
        print(f"Database: PostgreSQL (via DATABASE_URL)")
    else:
        print(f"Database: SQLite ({config.DB_PATH})")
    print(f"Download directory: {config.DOWNLOAD_DIR}")
    print("\nPress Ctrl+C to stop\n")

    try:
        from app import app
        app.run(
            debug=config.FLASK_DEBUG,
            port=config.FLASK_PORT,
            host='0.0.0.0'
        )
        return 0
    except KeyboardInterrupt:
        print("\nShutting down...")
        return 0
    except Exception as e:
        print(f"\nError: {e}")
        return 1


def cmd_test_scraper(args):
    """Test scraper selector identification"""
    print("Starting scraper test mode...")
    print("This will help you identify the correct selectors for eTrade\n")

    try:
        scraper = ETradeScraper()
        scraper.test_selectors()
        return 0
    except Exception as e:
        print(f"\nError: {e}")
        return 1


def cmd_list(args):
    """List recent transactions"""
    try:
        db = TransactionDatabase()
        transactions = db.get_all_transactions(limit=args.limit)

        if not transactions:
            print("No transactions found in database")
            return 0

        print(f"\n=== Recent {len(transactions)} Transactions ===\n")
        print(f"{'Date':<12} {'Amount':<12} {'Balance':<12} {'Description':<50}")
        print("-" * 86)

        for txn in transactions:
            amount_str = f"${txn['amount']:,.2f}"
            balance_str = f"${txn['balance']:,.2f}" if txn['balance'] else "-"
            desc = txn['description'][:47] + "..." if len(txn['description']) > 50 else txn['description']
            print(f"{txn['transaction_date']:<12} {amount_str:<12} {balance_str:<12} {desc:<50}")

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        return 1


def cmd_search(args):
    """Search transactions"""
    try:
        db = TransactionDatabase()
        transactions = db.search_transactions(
            search_term=args.query,
            start_date=args.start_date,
            end_date=args.end_date
        )

        if not transactions:
            print("No transactions found matching your search")
            return 0

        print(f"\n=== Found {len(transactions)} Transactions ===\n")
        print(f"{'Date':<12} {'Amount':<12} {'Description':<50}")
        print("-" * 74)

        for txn in transactions:
            amount_str = f"${txn['amount']:,.2f}"
            desc = txn['description'][:47] + "..." if len(txn['description']) > 50 else txn['description']
            print(f"{txn['transaction_date']:<12} {amount_str:<12} {desc:<50}")

        # Summary
        total = sum(t['amount'] for t in transactions)
        print(f"\n{'Total:':<12} ${total:,.2f}")

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Mortgage Payment Account Dashboard CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Import command
    import_parser = subparsers.add_parser('import', help='Import a CSV file')
    import_parser.add_argument('csv_file', help='Path to CSV file')
    import_parser.set_defaults(func=cmd_import)

    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape eTrade and import transactions')
    scrape_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    scrape_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    scrape_parser.set_defaults(func=cmd_scrape)

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Display database statistics')
    stats_parser.set_defaults(func=cmd_stats)

    # Serve command
    serve_parser = subparsers.add_parser('serve', help='Start the web server')
    serve_parser.set_defaults(func=cmd_serve)

    # Test scraper command
    test_parser = subparsers.add_parser('test-scraper', help='Test scraper selector identification')
    test_parser.set_defaults(func=cmd_test_scraper)

    # List command
    list_parser = subparsers.add_parser('list', help='List recent transactions')
    list_parser.add_argument('-n', '--limit', type=int, default=20, help='Number of transactions to show')
    list_parser.set_defaults(func=cmd_list)

    # Search command
    search_parser = subparsers.add_parser('search', help='Search transactions')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    search_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    search_parser.set_defaults(func=cmd_search)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
