#!/usr/bin/env python3
"""
Import data from JSON export file to PostgreSQL database.
Run this after setting up your PostgreSQL database.

Usage:
    1. Set DATABASE_URL or POSTGRES_URL environment variable
    2. python migration_import.py [--input PATH] [--dry-run]
"""

import json
import argparse
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def import_json_to_postgres(input_path: Path, dry_run: bool = False):
    """Import data from JSON file to PostgreSQL database"""

    # Check for database URL (not required for dry-run)
    database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
    if not database_url and not dry_run:
        print("Error: DATABASE_URL or POSTGRES_URL environment variable required")
        print("Set it in your .env file or export it:")
        print("  export DATABASE_URL='postgresql://user:pass@host:port/dbname'")
        return False

    if not input_path.exists():
        print(f"Error: Input file not found at {input_path}")
        print("Run migration_export.py first to create the export file.")
        return False

    # Load JSON data
    print(f"Loading data from {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        export_data = json.load(f)

    print(f"  Export date: {export_data.get('exported_at', 'unknown')}")
    print(f"  Source: {export_data.get('source_db', 'unknown')}")

    transactions = export_data['tables']['transactions']['data']
    mappings = export_data['tables']['person_mappings']['data']

    print(f"  Transactions to import: {len(transactions)}")
    print(f"  Person mappings to import: {len(mappings)}")

    if dry_run:
        print("\n[DRY RUN] No changes will be made to the database.")
        print("\nData validation:")

        # Validate transactions
        invalid_txns = 0
        for i, txn in enumerate(transactions):
            if not txn.get('transaction_date') or not txn.get('description'):
                print(f"  Warning: Transaction {i} missing required fields")
                invalid_txns += 1

        if invalid_txns:
            print(f"  Found {invalid_txns} transactions with missing fields")
        else:
            print("  All transactions have required fields")

        # Validate mappings
        invalid_mappings = 0
        for i, m in enumerate(mappings):
            if not m.get('person_name') or not m.get('keyword'):
                print(f"  Warning: Mapping {i} missing required fields")
                invalid_mappings += 1

        if invalid_mappings:
            print(f"  Found {invalid_mappings} mappings with missing fields")
        else:
            print("  All person mappings have required fields")

        print("\nTo perform the actual import, run without --dry-run")
        return True

    # Import dependencies
    try:
        import psycopg2
        from psycopg2 import extras, errors
    except ImportError:
        print("Error: psycopg2 not installed. Run:")
        print("  pip install psycopg2-binary")
        return False

    # Connect to PostgreSQL
    print(f"\nConnecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cursor = conn.cursor()
        print("  Connected successfully")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False

    # Check if tables exist (init_database should have created them)
    print("\nVerifying database schema...")
    cursor.execute('''
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name IN ('transactions', 'person_mappings', 'users')
    ''')
    existing_tables = [row[0] for row in cursor.fetchall()]

    if 'transactions' not in existing_tables or 'person_mappings' not in existing_tables:
        print("  Tables not found. Creating schema...")
        # Import database_pg to create tables
        try:
            from database_pg import TransactionDatabase
            db = TransactionDatabase(database_url)
            print("  Schema created successfully")
        except Exception as e:
            print(f"  Error creating schema: {e}")
            conn.close()
            return False
    else:
        print(f"  Found tables: {', '.join(existing_tables)}")

    # Check for existing data
    cursor.execute('SELECT COUNT(*) FROM transactions')
    existing_txn_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM person_mappings')
    existing_mapping_count = cursor.fetchone()[0]

    if existing_txn_count > 0 or existing_mapping_count > 0:
        print(f"\nWarning: Database already contains data!")
        print(f"  Existing transactions: {existing_txn_count}")
        print(f"  Existing person mappings: {existing_mapping_count}")
        response = input("Continue and skip duplicates? (y/N): ")
        if response.lower() != 'y':
            print("Import cancelled.")
            conn.close()
            return False

    # Import transactions
    print(f"\nImporting {len(transactions)} transactions...")
    inserted_txns = 0
    skipped_txns = 0

    for txn in transactions:
        try:
            cursor.execute('''
                INSERT INTO transactions
                (transaction_date, description, amount, balance, category, source, notes, csv_hash, imported_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                txn.get('transaction_date'),
                txn.get('description'),
                txn.get('amount'),
                txn.get('balance'),
                txn.get('category'),
                txn.get('source'),
                txn.get('notes'),
                txn.get('csv_hash'),
                txn.get('imported_at') or datetime.now().isoformat()
            ))
            inserted_txns += 1
        except errors.UniqueViolation:
            conn.rollback()
            skipped_txns += 1

    conn.commit()
    print(f"  Inserted: {inserted_txns}")
    print(f"  Skipped (duplicates): {skipped_txns}")

    # Import person mappings
    print(f"\nImporting {len(mappings)} person mappings...")
    inserted_mappings = 0
    skipped_mappings = 0

    for m in mappings:
        try:
            cursor.execute('''
                INSERT INTO person_mappings (person_name, keyword, created_at)
                VALUES (%s, %s, %s)
            ''', (
                m.get('person_name'),
                m.get('keyword'),
                m.get('created_at') or datetime.now().isoformat()
            ))
            inserted_mappings += 1
        except errors.UniqueViolation:
            conn.rollback()
            skipped_mappings += 1

    conn.commit()
    print(f"  Inserted: {inserted_mappings}")
    print(f"  Skipped (duplicates): {skipped_mappings}")

    # Verify import
    print("\nVerifying import...")
    cursor.execute('SELECT COUNT(*) FROM transactions')
    final_txn_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM person_mappings')
    final_mapping_count = cursor.fetchone()[0]

    print(f"  Final transaction count: {final_txn_count}")
    print(f"  Final person mapping count: {final_mapping_count}")

    conn.close()

    print("\nImport complete!")
    print("\nNext steps:")
    print("  1. Test the application with PostgreSQL: python app.py")
    print("  2. Set up Clerk authentication")
    print("  3. Deploy to Vercel")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Import JSON data to PostgreSQL database'
    )
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('data/migration_export.json'),
        help='Input JSON file path (default: data/migration_export.json)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate data without importing'
    )

    args = parser.parse_args()

    success = import_json_to_postgres(args.input, args.dry_run)

    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
