#!/usr/bin/env python3
"""
Export data from SQLite database to JSON for migration to PostgreSQL.
Run this locally before deploying to production.

Usage:
    python migration_export.py [--db-path PATH] [--output PATH]
"""

import sqlite3
import json
import argparse
from datetime import datetime
from pathlib import Path


def export_sqlite_to_json(db_path: Path, output_path: Path):
    """Export all data from SQLite database to JSON file"""

    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    export_data = {
        'exported_at': datetime.now().isoformat(),
        'source_db': str(db_path),
        'tables': {}
    }

    # Export transactions
    print("Exporting transactions...")
    cursor.execute('''
        SELECT
            transaction_date,
            description,
            amount,
            balance,
            category,
            source,
            notes,
            csv_hash,
            imported_at
        FROM transactions
        ORDER BY transaction_date DESC
    ''')

    transactions = []
    for row in cursor.fetchall():
        transactions.append({
            'transaction_date': row['transaction_date'],
            'description': row['description'],
            'amount': row['amount'],
            'balance': row['balance'],
            'category': row['category'],
            'source': row['source'],
            'notes': row['notes'],
            'csv_hash': row['csv_hash'],
            'imported_at': row['imported_at']
        })

    export_data['tables']['transactions'] = {
        'count': len(transactions),
        'data': transactions
    }
    print(f"  Found {len(transactions)} transactions")

    # Export person_mappings
    print("Exporting person_mappings...")
    cursor.execute('''
        SELECT
            person_name,
            keyword,
            created_at
        FROM person_mappings
        ORDER BY person_name, keyword
    ''')

    mappings = []
    for row in cursor.fetchall():
        mappings.append({
            'person_name': row['person_name'],
            'keyword': row['keyword'],
            'created_at': row['created_at']
        })

    export_data['tables']['person_mappings'] = {
        'count': len(mappings),
        'data': mappings
    }
    print(f"  Found {len(mappings)} person mappings")

    conn.close()

    # Write to JSON file
    print(f"\nWriting to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, default=str)

    # Calculate file size
    file_size = output_path.stat().st_size
    if file_size > 1024 * 1024:
        size_str = f"{file_size / (1024 * 1024):.2f} MB"
    elif file_size > 1024:
        size_str = f"{file_size / 1024:.2f} KB"
    else:
        size_str = f"{file_size} bytes"

    print(f"\nExport complete!")
    print(f"  File size: {size_str}")
    print(f"  Transactions: {len(transactions)}")
    print(f"  Person mappings: {len(mappings)}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Export SQLite database to JSON for PostgreSQL migration'
    )
    parser.add_argument(
        '--db-path',
        type=Path,
        default=Path('data/transactions.db'),
        help='Path to SQLite database (default: data/transactions.db)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('data/migration_export.json'),
        help='Output JSON file path (default: data/migration_export.json)'
    )

    args = parser.parse_args()

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    success = export_sqlite_to_json(args.db_path, args.output)

    if success:
        print(f"\nNext steps:")
        print(f"  1. Set DATABASE_URL environment variable to your PostgreSQL connection string")
        print(f"  2. Run: python migration_import.py --input {args.output}")

    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
