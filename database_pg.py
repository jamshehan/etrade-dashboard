import os
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
from decimal import Decimal
import psycopg2
from psycopg2 import pool, extras, errors
from dotenv import load_dotenv
from logging_config import get_logger

load_dotenv()

# Initialize logger
logger = get_logger('db')


def serialize_row(row: Dict) -> Dict:
    """Convert PostgreSQL types to JSON-serializable types"""
    result = {}
    for key, value in row.items():
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat() if value else None
        elif isinstance(value, Decimal):
            result[key] = float(value)
        else:
            result[key] = value
    return result


class TransactionDatabase:
    """Manages PostgreSQL database for eTrade transactions"""

    _pool = None

    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL or POSTGRES_URL environment variable required")
        self._init_pool()
        self.init_database()

    def _init_pool(self):
        """Initialize connection pool (singleton for serverless)"""
        if TransactionDatabase._pool is None:
            logger.info("Initializing PostgreSQL connection pool")
            try:
                TransactionDatabase._pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=self.database_url
                )
                logger.info("PostgreSQL connection pool initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                raise

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool with automatic cleanup"""
        conn = None
        try:
            conn = TransactionDatabase._pool.getconn()
            conn.autocommit = False
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                TransactionDatabase._pool.putconn(conn)

    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Create users table for authentication
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        full_name VARCHAR(255),
                        role VARCHAR(20) NOT NULL DEFAULT 'viewer',
                        auth_provider_id VARCHAR(255) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP
                    )
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_users_auth_provider_id ON users(auth_provider_id)
                ''')

                # Create transactions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS transactions (
                        id SERIAL PRIMARY KEY,
                        transaction_date DATE NOT NULL,
                        description TEXT NOT NULL,
                        amount DECIMAL(12, 2) NOT NULL,
                        balance DECIMAL(12, 2),
                        category VARCHAR(100),
                        source VARCHAR(100),
                        notes TEXT,
                        csv_hash VARCHAR(64),
                        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(transaction_date, description, amount)
                    )
                ''')

                # Create indexes for faster queries
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
                        id SERIAL PRIMARY KEY,
                        person_name VARCHAR(255) NOT NULL,
                        keyword VARCHAR(255) NOT NULL,
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

    # ==================== User Management Methods ====================

    def create_user(self, auth_provider_id: str, email: str,
                   full_name: str = None, role: str = 'viewer') -> Dict:
        """Create a new user"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute('''
                    INSERT INTO users (auth_provider_id, email, full_name, role)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, email, full_name, role, created_at
                ''', (auth_provider_id, email, full_name, role))
                user = serialize_row(dict(cursor.fetchone()))
                conn.commit()
                return user

    def get_user_by_auth_id(self, auth_provider_id: str) -> Optional[Dict]:
        """Get user by auth provider ID (e.g., Clerk user ID)"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute('''
                    SELECT id, email, full_name, role, created_at, last_login
                    FROM users
                    WHERE auth_provider_id = %s
                ''', (auth_provider_id,))
                row = cursor.fetchone()
                return serialize_row(dict(row)) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute('''
                    SELECT id, email, full_name, role, auth_provider_id, created_at, last_login
                    FROM users
                    WHERE email = %s
                ''', (email,))
                row = cursor.fetchone()
                return serialize_row(dict(row)) if row else None

    def update_user_role(self, auth_provider_id: str, role: str) -> bool:
        """Update user role (admin/viewer)"""
        if role not in ('admin', 'viewer'):
            raise ValueError("Role must be 'admin' or 'viewer'")

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE users
                    SET role = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE auth_provider_id = %s
                ''', (role, auth_provider_id))
                updated = cursor.rowcount > 0
                conn.commit()
                return updated

    def update_user_last_login(self, auth_provider_id: str) -> bool:
        """Update user's last login timestamp"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE users
                    SET last_login = CURRENT_TIMESTAMP
                    WHERE auth_provider_id = %s
                ''', (auth_provider_id,))
                updated = cursor.rowcount > 0
                conn.commit()
                return updated

    def get_all_users(self) -> List[Dict]:
        """Get all users (admin function)"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute('''
                    SELECT id, email, full_name, role, created_at, last_login
                    FROM users
                    ORDER BY created_at DESC
                ''')
                return [serialize_row(dict(row)) for row in cursor.fetchall()]

    # ==================== Transaction Methods ====================

    def insert_transactions(self, transactions: List[Dict]) -> Tuple[int, int]:
        """
        Insert transactions, skipping duplicates
        Returns: (inserted_count, skipped_count)
        """
        inserted = 0
        skipped = 0

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                for i, txn in enumerate(transactions):
                    savepoint_name = f"txn_insert_{i}"
                    try:
                        # Create savepoint before each insert
                        cursor.execute(f"SAVEPOINT {savepoint_name}")
                        cursor.execute('''
                            INSERT INTO transactions
                            (transaction_date, description, amount, balance, category, source, csv_hash)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ''', (
                            txn.get('transaction_date'),
                            txn.get('description'),
                            txn.get('amount'),
                            txn.get('balance'),
                            txn.get('category'),
                            txn.get('source'),
                            txn.get('csv_hash')
                        ))
                        # Release savepoint on success
                        cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                        inserted += 1
                    except errors.UniqueViolation:
                        # Duplicate transaction - rollback only to savepoint
                        cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                        skipped += 1
                        continue

                conn.commit()

        return inserted, skipped

    def get_all_transactions(self, limit: Optional[int] = None,
                            offset: int = 0) -> List[Dict]:
        """Get all transactions, ordered by date descending"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                if limit:
                    cursor.execute('''
                        SELECT * FROM transactions
                        ORDER BY transaction_date DESC
                        LIMIT %s OFFSET %s
                    ''', (limit, offset))
                else:
                    cursor.execute('''
                        SELECT * FROM transactions
                        ORDER BY transaction_date DESC
                    ''')

                return [serialize_row(dict(row)) for row in cursor.fetchall()]

    def get_transaction_count(self) -> int:
        """Get total number of transactions"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM transactions')
                return cursor.fetchone()[0]

    def search_transactions(self, search_term: str = None,
                           start_date: str = None,
                           end_date: str = None,
                           category: str = None,
                           source: str = None,
                           min_amount: float = None,
                           max_amount: float = None) -> List[Dict]:
        """Search transactions with various filters"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                query = 'SELECT * FROM transactions WHERE 1=1'
                params = []

                if search_term:
                    query += ' AND (description ILIKE %s OR notes ILIKE %s)'
                    params.extend([f'%{search_term}%', f'%{search_term}%'])

                if start_date:
                    query += ' AND transaction_date >= %s'
                    params.append(start_date)

                if end_date:
                    query += ' AND transaction_date <= %s'
                    params.append(end_date)

                if category:
                    query += ' AND category = %s'
                    params.append(category)

                if source:
                    query += ' AND source = %s'
                    params.append(source)

                if min_amount is not None:
                    query += ' AND amount >= %s'
                    params.append(min_amount)

                if max_amount is not None:
                    query += ' AND amount <= %s'
                    params.append(max_amount)

                query += ' ORDER BY transaction_date DESC'

                cursor.execute(query, params)
                return [serialize_row(dict(row)) for row in cursor.fetchall()]

    def get_statistics(self, start_date: str = None, end_date: str = None) -> Dict:
        """Calculate summary statistics"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                where_clause = '1=1'
                params = []

                if start_date:
                    where_clause += ' AND transaction_date >= %s'
                    params.append(start_date)

                if end_date:
                    where_clause += ' AND transaction_date <= %s'
                    params.append(end_date)

                # Overall statistics
                cursor.execute(f'''
                    SELECT
                        COUNT(*) as total_transactions,
                        COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as total_deposits,
                        COALESCE(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 0) as total_withdrawals,
                        COALESCE(SUM(amount), 0) as net_change,
                        COALESCE(AVG(amount), 0) as avg_transaction,
                        MIN(transaction_date) as earliest_date,
                        MAX(transaction_date) as latest_date
                    FROM transactions
                    WHERE {where_clause}
                ''', params)

                stats = serialize_row(dict(cursor.fetchone()))

                # Deposits by source
                cursor.execute(f'''
                    SELECT source, SUM(amount) as total, COUNT(*) as count
                    FROM transactions
                    WHERE amount > 0 AND {where_clause}
                    GROUP BY source
                    ORDER BY total DESC
                ''', params)

                deposits_by_source = [serialize_row(dict(row)) for row in cursor.fetchall()]
                stats['deposits_by_source'] = deposits_by_source

                # Monthly breakdown - PostgreSQL uses TO_CHAR instead of strftime
                cursor.execute(f'''
                    SELECT
                        TO_CHAR(transaction_date, 'YYYY-MM') as month,
                        COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as deposits,
                        COALESCE(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 0) as withdrawals,
                        COALESCE(SUM(amount), 0) as net
                    FROM transactions
                    WHERE {where_clause}
                    GROUP BY TO_CHAR(transaction_date, 'YYYY-MM')
                    ORDER BY month DESC
                ''', params)

                monthly_breakdown = [serialize_row(dict(row)) for row in cursor.fetchall()]
                stats['monthly_breakdown'] = monthly_breakdown

                # Category breakdown
                cursor.execute(f'''
                    SELECT category, SUM(amount) as total, COUNT(*) as count
                    FROM transactions
                    WHERE category IS NOT NULL AND {where_clause}
                    GROUP BY category
                    ORDER BY total
                ''', params)

                by_category = [serialize_row(dict(row)) for row in cursor.fetchall()]
                stats['by_category'] = by_category

                return stats

    def get_recurring_transactions(self, min_occurrences: int = 3) -> List[Dict]:
        """Identify potentially recurring transactions based on description similarity"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute('''
                    SELECT
                        description,
                        COUNT(*) as occurrences,
                        AVG(amount) as avg_amount,
                        MIN(amount) as min_amount,
                        MAX(amount) as max_amount
                    FROM transactions
                    GROUP BY description
                    HAVING COUNT(*) >= %s
                    ORDER BY occurrences DESC
                ''', (min_occurrences,))

                return [serialize_row(dict(row)) for row in cursor.fetchall()]

    def update_transaction(self, transaction_id: int, **kwargs) -> bool:
        """Update transaction fields"""
        valid_fields = ['category', 'source', 'notes', 'description']
        updates = []
        params = []

        for field, value in kwargs.items():
            if field in valid_fields:
                updates.append(f'{field} = %s')
                params.append(value)

        if not updates:
            return False

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                params.append(transaction_id)
                cursor.execute(f'''
                    UPDATE transactions
                    SET {', '.join(updates)}
                    WHERE id = %s
                ''', params)
                updated = cursor.rowcount > 0
                conn.commit()
                return updated

    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT DISTINCT category
                    FROM transactions
                    WHERE category IS NOT NULL
                    ORDER BY category
                ''')
                return [row[0] for row in cursor.fetchall()]

    def get_sources(self) -> List[str]:
        """Get all unique sources"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT DISTINCT source
                    FROM transactions
                    WHERE source IS NOT NULL
                    ORDER BY source
                ''')
                return [row[0] for row in cursor.fetchall()]

    # ==================== Person Mappings Methods ====================

    def get_person_mappings(self) -> List[Dict]:
        """Get all person-keyword mappings ordered by person_name"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute('''
                    SELECT id, person_name, keyword, created_at
                    FROM person_mappings
                    ORDER BY person_name, keyword
                ''')
                return [serialize_row(dict(row)) for row in cursor.fetchall()]

    def add_person_mapping(self, person_name: str, keyword: str) -> bool:
        """
        Add new person-keyword mapping
        Returns True if added successfully
        Raises error if duplicate exists
        """
        if not person_name or not person_name.strip():
            raise ValueError("person_name cannot be empty")
        if not keyword or not keyword.strip():
            raise ValueError("keyword cannot be empty")

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO person_mappings (person_name, keyword)
                    VALUES (%s, %s)
                ''', (person_name.strip(), keyword.strip()))
                conn.commit()
                return True

    def delete_person_mapping(self, mapping_id: int) -> bool:
        """
        Delete mapping by ID
        Returns True if deleted, False if not found
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM person_mappings WHERE id = %s', (mapping_id,))
                deleted = cursor.rowcount > 0
                conn.commit()
                return deleted

    def get_contributions(self, start_date: str = None, end_date: str = None,
                         person_name: str = None) -> List[Dict]:
        """
        Get transactions matched to persons via keywords
        Only returns deposits (amount > 0)
        If multiple keywords match, returns alphabetically first person_name
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                query = '''
                    SELECT DISTINCT ON (t.id)
                        t.id,
                        t.transaction_date,
                        t.description,
                        t.amount,
                        t.balance,
                        pm.person_name
                    FROM transactions t
                    INNER JOIN person_mappings pm ON t.description ILIKE '%%' || pm.keyword || '%%'
                    WHERE t.amount > 0
                '''
                params = []

                if person_name:
                    query += ' AND pm.person_name = %s'
                    params.append(person_name)

                if start_date:
                    query += ' AND t.transaction_date >= %s'
                    params.append(start_date)

                if end_date:
                    query += ' AND t.transaction_date <= %s'
                    params.append(end_date)

                query += '''
                    ORDER BY t.id, pm.person_name
                '''

                cursor.execute(query, params)
                results = [serialize_row(dict(row)) for row in cursor.fetchall()]

                # Sort by date descending (after DISTINCT ON)
                results.sort(key=lambda x: x['transaction_date'], reverse=True)
                return results

    def get_contribution_statistics(self, start_date: str = None,
                                    end_date: str = None) -> Dict:
        """
        Calculate contribution statistics by person
        Returns aggregated stats by person and by month
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                where_clause = '1=1'
                params = []

                if start_date:
                    where_clause += ' AND t.transaction_date >= %s'
                    params.append(start_date)

                if end_date:
                    where_clause += ' AND t.transaction_date <= %s'
                    params.append(end_date)

                # By person totals
                cursor.execute(f'''
                    SELECT
                        pm.person_name,
                        SUM(t.amount) as total,
                        COUNT(DISTINCT t.id) as count
                    FROM transactions t
                    INNER JOIN person_mappings pm ON t.description ILIKE '%%' || pm.keyword || '%%'
                    WHERE t.amount > 0 AND {where_clause}
                    GROUP BY pm.person_name
                    ORDER BY total DESC
                ''', params)

                by_person = [serialize_row(dict(row)) for row in cursor.fetchall()]

                # Monthly by person - PostgreSQL uses TO_CHAR
                cursor.execute(f'''
                    SELECT
                        TO_CHAR(t.transaction_date, 'YYYY-MM') as month,
                        pm.person_name,
                        SUM(t.amount) as total
                    FROM transactions t
                    INNER JOIN person_mappings pm ON t.description ILIKE '%%' || pm.keyword || '%%'
                    WHERE t.amount > 0 AND {where_clause}
                    GROUP BY TO_CHAR(t.transaction_date, 'YYYY-MM'), pm.person_name
                    ORDER BY month DESC, pm.person_name
                ''', params)

                monthly_by_person = [serialize_row(dict(row)) for row in cursor.fetchall()]

                return {
                    'by_person': by_person,
                    'monthly_by_person': monthly_by_person
                }

    # ==================== Cleanup ====================

    @classmethod
    def close_pool(cls):
        """Close all connections in the pool (for graceful shutdown)"""
        if cls._pool:
            cls._pool.closeall()
            cls._pool = None
