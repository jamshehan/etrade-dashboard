from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pathlib import Path
import config
from csv_parser import import_csv_to_database
from scraper import ETradeScraper
from projections import calculate_projections
import traceback

# Use PostgreSQL if DATABASE_URL is set, otherwise SQLite
if config.USE_POSTGRES:
    from database_pg import TransactionDatabase
    from psycopg2 import errors as db_errors
    IntegrityError = db_errors.UniqueViolation
else:
    from database import TransactionDatabase
    import sqlite3
    IntegrityError = sqlite3.IntegrityError


app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Initialize database
db = TransactionDatabase()


@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('static', 'index.html')


@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """
    Get all transactions with optional pagination
    Query params: limit, offset
    """
    try:
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', default=0, type=int)

        transactions = db.get_all_transactions(limit=limit, offset=offset)

        return jsonify({
            'success': True,
            'data': transactions,
            'count': len(transactions)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/transactions/search', methods=['GET'])
def search_transactions():
    """
    Search transactions with filters
    Query params: search, start_date, end_date, category, source, min_amount, max_amount
    """
    try:
        search_term = request.args.get('search')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category')
        source = request.args.get('source')
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)

        transactions = db.search_transactions(
            search_term=search_term,
            start_date=start_date,
            end_date=end_date,
            category=category,
            source=source,
            min_amount=min_amount,
            max_amount=max_amount
        )

        return jsonify({
            'success': True,
            'data': transactions,
            'count': len(transactions)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """
    Get summary statistics
    Query params: start_date, end_date
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        stats = db.get_statistics(start_date=start_date, end_date=end_date)

        return jsonify({
            'success': True,
            'data': stats
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/recurring', methods=['GET'])
def get_recurring():
    """
    Get recurring transactions
    Query params: min_occurrences (default: 3)
    """
    try:
        min_occurrences = request.args.get('min_occurrences', default=3, type=int)

        recurring = db.get_recurring_transactions(min_occurrences=min_occurrences)

        return jsonify({
            'success': True,
            'data': recurring
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/projections', methods=['POST'])
def get_projections():
    """
    Calculate future balance projections
    Body: {
        current_balance: number,
        months: number,
        recurring_deposits: [{description, amount, frequency}],
        recurring_withdrawals: [{description, amount, frequency}]
    }
    """
    try:
        data = request.get_json()

        if not data or 'current_balance' not in data:
            return jsonify({
                'success': False,
                'error': 'current_balance is required'
            }), 400

        current_balance = float(data['current_balance'])
        months = int(data.get('months', 12))
        recurring_deposits = data.get('recurring_deposits', [])
        recurring_withdrawals = data.get('recurring_withdrawals', [])

        projections = calculate_projections(
            current_balance=current_balance,
            months=months,
            recurring_deposits=recurring_deposits,
            recurring_withdrawals=recurring_withdrawals
        )

        return jsonify({
            'success': True,
            'data': projections
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/transactions/<int:transaction_id>', methods=['PATCH'])
def update_transaction(transaction_id):
    """
    Update transaction fields
    Body: { category, source, notes, description }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        db.update_transaction(transaction_id, **data)

        return jsonify({
            'success': True,
            'message': 'Transaction updated successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/import/csv', methods=['POST'])
def import_csv():
    """
    Import CSV file from specified path
    Body: { csv_path: string }
    """
    try:
        data = request.get_json()

        if not data or 'csv_path' not in data:
            return jsonify({
                'success': False,
                'error': 'csv_path is required'
            }), 400

        csv_path = Path(data['csv_path'])

        if not csv_path.exists():
            return jsonify({
                'success': False,
                'error': f'CSV file not found: {csv_path}'
            }), 404

        inserted, skipped = import_csv_to_database(csv_path, db)

        return jsonify({
            'success': True,
            'message': f'Import complete: {inserted} new, {skipped} duplicates',
            'inserted': inserted,
            'skipped': skipped
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/scrape', methods=['POST'])
def scrape_transactions():
    """
    Trigger web scraper to download transactions
    Body: { start_date: string, end_date: string } (optional)
    """
    try:
        data = request.get_json() or {}

        start_date = data.get('start_date')
        end_date = data.get('end_date')

        # Run scraper
        scraper = ETradeScraper()
        csv_path = scraper.download_transactions(start_date=start_date, end_date=end_date)

        # Import the downloaded CSV
        inserted, skipped = import_csv_to_database(csv_path, db)

        return jsonify({
            'success': True,
            'message': f'Scrape and import complete: {inserted} new, {skipped} duplicates',
            'csv_path': str(csv_path),
            'inserted': inserted,
            'skipped': skipped
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get list of all unique categories"""
    try:
        transactions = db.get_all_transactions()
        categories = sorted(set(t['category'] for t in transactions if t.get('category')))

        return jsonify({
            'success': True,
            'data': categories
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sources', methods=['GET'])
def get_sources():
    """Get list of all unique sources"""
    try:
        transactions = db.get_all_transactions()
        sources = sorted(set(t['source'] for t in transactions if t.get('source')))

        return jsonify({
            'success': True,
            'data': sources
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Person Mappings and Contributions Endpoints

@app.route('/api/person-mappings', methods=['GET'])
def get_person_mappings():
    """Get all person-keyword mappings"""
    try:
        mappings = db.get_person_mappings()

        return jsonify({
            'success': True,
            'data': mappings
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/person-mappings', methods=['POST'])
def add_person_mapping():
    """Add new person-keyword mapping"""
    try:
        data = request.get_json()

        if not data or 'person_name' not in data or 'keyword' not in data:
            return jsonify({
                'success': False,
                'error': 'person_name and keyword are required'
            }), 400

        # Validate non-empty strings
        if not data['person_name'].strip() or not data['keyword'].strip():
            return jsonify({
                'success': False,
                'error': 'person_name and keyword cannot be empty'
            }), 400

        db.add_person_mapping(data['person_name'], data['keyword'])

        return jsonify({
            'success': True,
            'message': 'Mapping added successfully'
        })

    except IntegrityError:
        return jsonify({
            'success': False,
            'error': 'This mapping already exists'
        }), 409
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/person-mappings/<int:mapping_id>', methods=['DELETE'])
def delete_person_mapping(mapping_id):
    """Delete person-keyword mapping by ID"""
    try:
        deleted = db.delete_person_mapping(mapping_id)

        if not deleted:
            return jsonify({
                'success': False,
                'error': 'Mapping not found'
            }), 404

        return jsonify({
            'success': True,
            'message': 'Mapping deleted successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/contributions', methods=['GET'])
def get_contributions():
    """
    Get contribution transactions with optional filters
    Query params: person_name, start_date, end_date
    """
    try:
        person_name = request.args.get('person_name')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        contributions = db.get_contributions(
            start_date=start_date,
            end_date=end_date,
            person_name=person_name
        )

        return jsonify({
            'success': True,
            'data': contributions,
            'count': len(contributions)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/contributions/statistics', methods=['GET'])
def get_contribution_statistics():
    """
    Get contribution statistics aggregated by person
    Query params: start_date, end_date
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        stats = db.get_contribution_statistics(
            start_date=start_date,
            end_date=end_date
        )

        return jsonify({
            'success': True,
            'data': stats
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print(f"Starting eTrade Dashboard on http://localhost:{config.FLASK_PORT}")
    if config.USE_POSTGRES:
        print(f"Database: PostgreSQL (via DATABASE_URL)")
    else:
        print(f"Database: SQLite ({config.DB_PATH})")
    print(f"Download directory: {config.DOWNLOAD_DIR}")
    app.run(debug=config.FLASK_DEBUG, port=config.FLASK_PORT, host='0.0.0.0')
