import pandas as pd
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict


class ETradeCSVParser:
    """Parse eTrade transaction CSV files"""

    def __init__(self):
        # Define expected column mappings (may need adjustment based on actual CSV format)
        self.column_mapping = {
            'Date': 'transaction_date',
            'Transaction Date': 'transaction_date',
            'TransactionDate': 'transaction_date',
            'Description': 'description',
            'Amount': 'amount',
            'Balance': 'balance',
            'TransactionType': 'transaction_type',
            'Categories': 'original_category',
        }

    def parse_csv(self, csv_path: Path) -> List[Dict]:
        """
        Parse eTrade CSV file and return list of transaction dictionaries

        Args:
            csv_path: Path to the CSV file

        Returns:
            List of transaction dictionaries ready for database insertion
        """
        try:
            # Find the header row (eTrade CSVs have leading metadata)
            header_row = self._find_header_row(csv_path)

            # Read CSV file starting from header row
            df = pd.read_csv(csv_path, skiprows=header_row)

            # Remove any blank rows
            df = df.dropna(how='all')

            # Generate hash of CSV for duplicate detection
            csv_hash = self._generate_csv_hash(csv_path)

            # Rename columns based on mapping
            df = self._rename_columns(df)

            # Clean and process data
            transactions = self._process_dataframe(df, csv_hash)

            return transactions

        except Exception as e:
            raise Exception(f"Error parsing CSV file {csv_path}: {str(e)}")

    def _find_header_row(self, csv_path: Path) -> int:
        """
        Find the row number where the header starts
        Looks for common header keywords like Date, Amount, Description
        """
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            for i, line in enumerate(f):
                line_lower = line.lower()
                # Check if this line contains header keywords
                if any(keyword in line_lower for keyword in
                       ['transactiondate', 'transaction date', 'date', 'amount', 'description']):
                    return i
        return 0  # Default to first row if no header found

    def _rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename columns based on mapping"""
        # Find matching columns (case-insensitive)
        rename_dict = {}
        for col in df.columns:
            for key, value in self.column_mapping.items():
                if col.strip().lower() == key.strip().lower():
                    rename_dict[col] = value
                    break

        df = df.rename(columns=rename_dict)
        return df

    def _process_dataframe(self, df: pd.DataFrame, csv_hash: str) -> List[Dict]:
        """Process dataframe and convert to list of dictionaries"""
        transactions = []

        # Required columns
        if 'transaction_date' not in df.columns:
            raise ValueError("CSV must contain a date column (Date or Transaction Date)")
        if 'description' not in df.columns:
            raise ValueError("CSV must contain a Description column")
        if 'amount' not in df.columns:
            raise ValueError("CSV must contain an Amount column")

        for _, row in df.iterrows():
            try:
                # Parse date
                txn_date = self._parse_date(row['transaction_date'])

                # Parse amount
                amount = self._parse_amount(row['amount'])

                # Parse balance (optional)
                balance = None
                if 'balance' in row and pd.notna(row['balance']):
                    balance = self._parse_amount(row['balance'])

                # Extract description
                description = str(row['description']).strip()

                # Attempt to categorize and extract source
                category = self._categorize_transaction(description, amount)
                source = self._extract_source(description, amount)

                transaction = {
                    'transaction_date': txn_date,
                    'description': description,
                    'amount': amount,
                    'balance': balance,
                    'category': category,
                    'source': source,
                    'csv_hash': csv_hash
                }

                transactions.append(transaction)

            except Exception as e:
                print(f"Warning: Skipping row due to error: {str(e)}")
                continue

        return transactions

    def _parse_date(self, date_value) -> str:
        """Parse date value to YYYY-MM-DD format"""
        if pd.isna(date_value):
            raise ValueError("Date value is missing")

        # Try various date formats
        date_formats = [
            '%m/%d/%Y',
            '%Y-%m-%d',
            '%m-%d-%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%m/%d/%y',
            '%d-%m-%Y'
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(str(date_value).strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # If none of the formats work, try pandas parsing
        try:
            dt = pd.to_datetime(date_value)
            return dt.strftime('%Y-%m-%d')
        except:
            raise ValueError(f"Unable to parse date: {date_value}")

    def _parse_amount(self, amount_value) -> float:
        """Parse amount value, handling various formats"""
        if pd.isna(amount_value):
            return 0.0

        # Convert to string and clean
        amount_str = str(amount_value).strip()

        # Remove currency symbols and commas
        amount_str = amount_str.replace('$', '').replace(',', '').replace(' ', '')

        # Handle parentheses notation for negative numbers
        if amount_str.startswith('(') and amount_str.endswith(')'):
            amount_str = '-' + amount_str[1:-1]

        try:
            return float(amount_str)
        except ValueError:
            raise ValueError(f"Unable to parse amount: {amount_value}")

    def _categorize_transaction(self, description: str, amount: float) -> str:
        """Basic categorization based on description keywords"""
        description_lower = description.lower()

        if amount > 0:
            # Deposits
            if any(keyword in description_lower for keyword in ['direct dep', 'deposit', 'payroll', 'salary']):
                return 'Income'
            elif any(keyword in description_lower for keyword in ['transfer', 'xfer']):
                return 'Transfer In'
            elif any(keyword in description_lower for keyword in ['interest', 'dividend']):
                return 'Interest/Dividend'
            else:
                return 'Other Income'
        else:
            # Withdrawals
            if any(keyword in description_lower for keyword in ['atm', 'withdrawal']):
                return 'ATM/Cash'
            elif any(keyword in description_lower for keyword in ['grocery', 'supermarket', 'food']):
                return 'Groceries'
            elif any(keyword in description_lower for keyword in ['gas', 'fuel', 'shell', 'exxon', 'chevron']):
                return 'Gas/Fuel'
            elif any(keyword in description_lower for keyword in ['restaurant', 'cafe', 'coffee']):
                return 'Dining'
            elif any(keyword in description_lower for keyword in ['utility', 'electric', 'gas', 'water']):
                return 'Utilities'
            elif any(keyword in description_lower for keyword in ['transfer', 'xfer']):
                return 'Transfer Out'
            elif any(keyword in description_lower for keyword in ['check', 'cheque']):
                return 'Check'
            elif any(keyword in description_lower for keyword in ['fee', 'charge']):
                return 'Fees'
            else:
                return 'Other Expense'

    def _extract_source(self, description: str, amount: float) -> str:
        """Extract source/payee from description"""
        # For deposits, try to identify the source
        if amount > 0:
            description_lower = description.lower()
            if 'direct dep' in description_lower or 'payroll' in description_lower:
                # Try to extract company name
                parts = description.split()
                if len(parts) > 2:
                    return ' '.join(parts[2:4])  # Heuristic
                return 'Payroll'
            elif 'transfer' in description_lower:
                return 'Transfer'
            elif 'interest' in description_lower:
                return 'Interest'
            else:
                return 'Other'
        else:
            # For withdrawals, the merchant/payee is the source
            # Clean up the description to extract merchant name
            return description.split('-')[0].strip()[:50]  # First part, max 50 chars

    def _generate_csv_hash(self, csv_path: Path) -> str:
        """Generate hash of CSV file for duplicate detection"""
        with open(csv_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()


def import_csv_to_database(csv_path: Path, database):
    """
    Import CSV file to database

    Args:
        csv_path: Path to CSV file
        database: TransactionDatabase instance

    Returns:
        Tuple of (inserted_count, skipped_count)
    """
    parser = ETradeCSVParser()
    transactions = parser.parse_csv(csv_path)

    if not transactions:
        print(f"No transactions found in {csv_path}")
        return 0, 0

    inserted, skipped = database.insert_transactions(transactions)
    print(f"Import complete: {inserted} new transactions, {skipped} duplicates skipped")

    return inserted, skipped
