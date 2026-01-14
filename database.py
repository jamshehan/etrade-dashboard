import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import config


class TransactionDatabase:
    """Manages SQLite database for eTrade transactions"""

    def __init__(self, db_path: Path = config.DB_PATH):
        self.db_path = db_path
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        """Create a database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date DATE NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                balance REAL,
                category TEXT,
                source TEXT,
                notes TEXT,
                csv_hash TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(transaction_date, description, amount)
            )
        ''')

        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_transaction_date
            ON transactions(transaction_date DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_category
            ON transactions(category)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_source
            ON transactions(source)
        ''')

        # Create person_mappings table for contribution tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS person_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_name TEXT NOT NULL,
                keyword TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(person_name, keyword)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_person_name
            ON person_mappings(person_name)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_keyword
            ON person_mappings(keyword)
        ''')

        conn.commit()
        conn.close()

    def insert_transactions(self, transactions: List[Dict]) -> Tuple[int, int]:
        """
        Insert transactions, skipping duplicates
        Returns: (inserted_count, skipped_count)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        inserted = 0
        skipped = 0

        for txn in transactions:
            try:
                cursor.execute('''
                    INSERT INTO transactions
                    (transaction_date, description, amount, balance, category, source, csv_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    txn.get('transaction_date'),
                    txn.get('description'),
                    txn.get('amount'),
                    txn.get('balance'),
                    txn.get('category'),
                    txn.get('source'),
                    txn.get('csv_hash')
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                # Duplicate transaction
                skipped += 1

        conn.commit()
        conn.close()

        return inserted, skipped

    def get_all_transactions(self, limit: Optional[int] = None,
                            offset: int = 0) -> List[Dict]:
        """Get all transactions, ordered by date descending"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM transactions ORDER BY transaction_date DESC'
        if limit:
            query += f' LIMIT {limit} OFFSET {offset}'

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def search_transactions(self, search_term: str = None,
                           start_date: str = None,
                           end_date: str = None,
                           category: str = None,
                           source: str = None,
                           min_amount: float = None,
                           max_amount: float = None) -> List[Dict]:
        """Search transactions with various filters"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM transactions WHERE 1=1'
        params = []

        if search_term:
            query += ' AND (description LIKE ? OR notes LIKE ?)'
            params.extend([f'%{search_term}%', f'%{search_term}%'])

        if start_date:
            query += ' AND transaction_date >= ?'
            params.append(start_date)

        if end_date:
            query += ' AND transaction_date <= ?'
            params.append(end_date)

        if category:
            query += ' AND category = ?'
            params.append(category)

        if source:
            query += ' AND source = ?'
            params.append(source)

        if min_amount is not None:
            query += ' AND amount >= ?'
            params.append(min_amount)

        if max_amount is not None:
            query += ' AND amount <= ?'
            params.append(max_amount)

        query += ' ORDER BY transaction_date DESC'

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_statistics(self, start_date: str = None, end_date: str = None) -> Dict:
        """Calculate summary statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        where_clause = '1=1'
        params = []

        if start_date:
            where_clause += ' AND transaction_date >= ?'
            params.append(start_date)

        if end_date:
            where_clause += ' AND transaction_date <= ?'
            params.append(end_date)

        # Overall statistics
        cursor.execute(f'''
            SELECT
                COUNT(*) as total_transactions,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_deposits,
                SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as total_withdrawals,
                SUM(amount) as net_change,
                AVG(amount) as avg_transaction,
                MIN(transaction_date) as earliest_date,
                MAX(transaction_date) as latest_date
            FROM transactions
            WHERE {where_clause}
        ''', params)

        stats = dict(cursor.fetchone())

        # Deposits by source
        cursor.execute(f'''
            SELECT source, SUM(amount) as total, COUNT(*) as count
            FROM transactions
            WHERE amount > 0 AND {where_clause}
            GROUP BY source
            ORDER BY total DESC
        ''', params)

        stats['deposits_by_source'] = [dict(row) for row in cursor.fetchall()]

        # Monthly breakdown
        cursor.execute(f'''
            SELECT
                strftime('%Y-%m', transaction_date) as month,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as deposits,
                SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as withdrawals,
                SUM(amount) as net
            FROM transactions
            WHERE {where_clause}
            GROUP BY month
            ORDER BY month DESC
        ''', params)

        stats['monthly_breakdown'] = [dict(row) for row in cursor.fetchall()]

        # Category breakdown (if categories are populated)
        cursor.execute(f'''
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM transactions
            WHERE category IS NOT NULL AND {where_clause}
            GROUP BY category
            ORDER BY total
        ''', params)

        stats['by_category'] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return stats

    def get_recurring_transactions(self, min_occurrences: int = 3) -> List[Dict]:
        """Identify potentially recurring transactions based on description similarity"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                description,
                COUNT(*) as occurrences,
                AVG(amount) as avg_amount,
                MIN(amount) as min_amount,
                MAX(amount) as max_amount
            FROM transactions
            GROUP BY description
            HAVING COUNT(*) >= ?
            ORDER BY occurrences DESC
        ''', (min_occurrences,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_transaction(self, transaction_id: int, **kwargs):
        """Update transaction fields"""
        conn = self.get_connection()
        cursor = conn.cursor()

        valid_fields = ['category', 'source', 'notes', 'description']
        updates = []
        params = []

        for field, value in kwargs.items():
            if field in valid_fields:
                updates.append(f'{field} = ?')
                params.append(value)

        if updates:
            params.append(transaction_id)
            cursor.execute(f'''
                UPDATE transactions
                SET {', '.join(updates)}
                WHERE id = ?
            ''', params)
            conn.commit()

        conn.close()

    # Person Mappings Methods for Contribution Tracking

    def get_person_mappings(self) -> List[Dict]:
        """Get all person-keyword mappings ordered by person_name"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, person_name, keyword, created_at
            FROM person_mappings
            ORDER BY person_name, keyword
        ''')

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def add_person_mapping(self, person_name: str, keyword: str) -> bool:
        """
        Add new person-keyword mapping
        Returns True if added successfully
        Raises sqlite3.IntegrityError if duplicate exists
        """
        if not person_name or not person_name.strip():
            raise ValueError("person_name cannot be empty")
        if not keyword or not keyword.strip():
            raise ValueError("keyword cannot be empty")

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO person_mappings (person_name, keyword)
            VALUES (?, ?)
        ''', (person_name.strip(), keyword.strip()))

        conn.commit()
        conn.close()

        return True

    def delete_person_mapping(self, mapping_id: int) -> bool:
        """
        Delete mapping by ID
        Returns True if deleted, False if not found
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM person_mappings WHERE id = ?', (mapping_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def get_contributions(self, start_date: str = None, end_date: str = None,
                         person_name: str = None) -> List[Dict]:
        """
        Get transactions matched to persons via keywords
        Only returns deposits (amount > 0)
        If multiple keywords match, returns alphabetically first person_name
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
            SELECT DISTINCT
                t.id,
                t.transaction_date,
                t.description,
                t.amount,
                t.balance,
                MIN(pm.person_name) as person_name
            FROM transactions t
            INNER JOIN person_mappings pm ON t.description LIKE '%' || pm.keyword || '%'
            WHERE t.amount > 0
        '''
        params = []

        if person_name:
            query += ' AND pm.person_name = ?'
            params.append(person_name)

        if start_date:
            query += ' AND t.transaction_date >= ?'
            params.append(start_date)

        if end_date:
            query += ' AND t.transaction_date <= ?'
            params.append(end_date)

        query += '''
            GROUP BY t.id
            ORDER BY t.transaction_date DESC
        '''

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_contribution_statistics(self, start_date: str = None,
                                    end_date: str = None) -> Dict:
        """
        Calculate contribution statistics by person
        Returns aggregated stats by person and by month
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        where_clause = '1=1'
        params = []

        if start_date:
            where_clause += ' AND t.transaction_date >= ?'
            params.append(start_date)

        if end_date:
            where_clause += ' AND t.transaction_date <= ?'
            params.append(end_date)

        # By person totals
        cursor.execute(f'''
            SELECT
                pm.person_name,
                SUM(t.amount) as total,
                COUNT(DISTINCT t.id) as count
            FROM transactions t
            INNER JOIN person_mappings pm ON t.description LIKE '%' || pm.keyword || '%'
            WHERE t.amount > 0 AND {where_clause}
            GROUP BY pm.person_name
            ORDER BY total DESC
        ''', params)

        by_person = [dict(row) for row in cursor.fetchall()]

        # Monthly by person
        cursor.execute(f'''
            SELECT
                strftime('%Y-%m', t.transaction_date) as month,
                pm.person_name,
                SUM(t.amount) as total
            FROM transactions t
            INNER JOIN person_mappings pm ON t.description LIKE '%' || pm.keyword || '%'
            WHERE t.amount > 0 AND {where_clause}
            GROUP BY month, pm.person_name
            ORDER BY month DESC, pm.person_name
        ''', params)

        monthly_by_person = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            'by_person': by_person,
            'monthly_by_person': monthly_by_person
        }
