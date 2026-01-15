from flask import Flask, jsonify, request, send_from_directory, g
from flask_cors import CORS
from pathlib import Path
import config
from projections import calculate_projections
from auth_middleware import require_auth, require_admin
from logging_config import get_logger
import traceback
import hmac
import hashlib
import os

# Detect Vercel serverless environment
IS_VERCEL = os.getenv('VERCEL', '').lower() == '1'

# Initialize logger
logger = get_logger('api')
logger.info(f"Environment: {'Vercel (serverless)' if IS_VERCEL else 'Local'}")

# Conditional imports for serverless compatibility
if IS_VERCEL:
    # These features require local filesystem/browser - not available in serverless
    ETradeScraper = None
    import_csv_to_database = None
    logger.info("Serverless mode: scraper and filesystem imports disabled")
else:
    from csv_parser import import_csv_to_database
    from scraper import ETradeScraper

# Use PostgreSQL if DATABASE_URL is set, otherwise SQLite
if config.USE_POSTGRES:
    from database_pg import TransactionDatabase
    from psycopg2 import errors as db_errors
    IntegrityError = db_errors.UniqueViolation
else:
    from database import TransactionDatabase
    import sqlite3
    IntegrityError = sqlite3.IntegrityError


app = Flask(__name__, static_folder='public', static_url_path='')
app.config['SECRET_KEY'] = config.FLASK_SECRET_KEY
CORS(app)

# Initialize database
db = TransactionDatabase()


# =============================================================================
# Centralized Error Handlers
# =============================================================================

def error_response(message: str, status_code: int, details: dict = None):
    """Create standardized error response."""
    response = {
        'success': False,
        'error': message
    }
    if config.FLASK_DEBUG and details:
        response['details'] = details
    return jsonify(response), status_code


@app.errorhandler(400)
def bad_request_error(error):
    logger.warning(f"Bad request: {error}")
    return error_response('Bad request', 400)


@app.errorhandler(401)
def unauthorized_error(error):
    logger.warning("Unauthorized access attempt")
    return error_response('Authentication required', 401)


@app.errorhandler(403)
def forbidden_error(error):
    logger.warning("Forbidden access attempt")
    return error_response('Access denied', 403)


@app.errorhandler(404)
def not_found_error(error):
    logger.info(f"Resource not found: {request.path}")
    return error_response('Resource not found', 404)


@app.errorhandler(500)
def internal_server_error(error):
    logger.error(f"Internal server error: {error}", exc_info=True)
    return error_response('Internal server error', 500)


@app.errorhandler(Exception)
def handle_exception(error):
    """Catch-all handler for unhandled exceptions."""
    logger.error(f"Unhandled exception: {type(error).__name__}: {error}", exc_info=config.FLASK_DEBUG)

    if config.FLASK_DEBUG:
        return error_response(str(error), 500, {'type': type(error).__name__})
    else:
        return error_response('An unexpected error occurred', 500)


# =============================================================================
# Routes
# =============================================================================

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('public', 'index.html')


@app.route('/api/transactions', methods=['GET'])
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_admin
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
@require_admin
def import_csv():
    """
    Import CSV file from specified path
    Body: { csv_path: string }
    NOTE: Only available in local environment (requires filesystem access)
    """
    if IS_VERCEL:
        logger.warning("CSV import attempt in production environment")
        return jsonify({
            'success': False,
            'error': 'CSV import from filesystem not available in production.',
            'suggestion': 'Use web scraper in local environment or implement file upload feature',
            'code': 'FEATURE_UNAVAILABLE_PRODUCTION'
        }), 501

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
@require_admin
def scrape_transactions():
    """
    Trigger web scraper to download transactions
    Body: { start_date: string, end_date: string } (optional)
    NOTE: Only available in local environment (requires Playwright)
    """
    if IS_VERCEL:
        logger.warning("Scrape attempt in production environment")
        return jsonify({
            'success': False,
            'error': 'Scraping not available in production. Use this feature in local environment.',
            'reason': 'Requires Playwright browser binaries and filesystem access',
            'code': 'FEATURE_UNAVAILABLE_PRODUCTION'
        }), 501

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
@require_auth
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
@require_auth
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
@require_auth
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
@require_admin
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
@require_admin
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
@require_auth
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
@require_auth
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


@app.route('/api/features', methods=['GET'])
@require_auth
def get_features():
    """
    Get available features based on environment.
    Frontend uses this to show/hide unavailable features.
    """
    return jsonify({
        'success': True,
        'data': {
            'environment': 'production' if IS_VERCEL else 'local',
            'scraping_enabled': not IS_VERCEL,
            'csv_import_enabled': not IS_VERCEL,
            'database_type': 'postgresql' if config.USE_POSTGRES else 'sqlite'
        }
    })


# Authentication Endpoints

@app.route('/api/auth/config', methods=['GET'])
def get_auth_config():
    """
    Get public authentication configuration for frontend.
    Returns Clerk publishable key if configured.
    """
    return jsonify({
        'success': True,
        'data': {
            'clerk_publishable_key': config.CLERK_PUBLISHABLE_KEY or None,
            'auth_enabled': bool(config.CLERK_PUBLISHABLE_KEY)
        }
    })


@app.route('/api/user/me', methods=['GET'])
@require_auth
def get_current_user():
    """
    Get current authenticated user's info including role.
    """
    try:
        user_id = g.current_user.get('sub')

        # Get user from database
        user = db.get_user_by_auth_id(user_id)

        if not user:
            # User authenticated but not in database yet
            # This can happen if webhook hasn't fired yet
            return jsonify({
                'success': True,
                'data': {
                    'auth_id': user_id,
                    'email': g.current_user.get('email'),
                    'role': 'viewer',  # Default role
                    'in_database': False
                }
            })

        # Update last login
        db.update_user_last_login(user_id)

        return jsonify({
            'success': True,
            'data': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user['full_name'],
                'role': user['role'],
                'created_at': str(user['created_at']) if user.get('created_at') else None,
                'last_login': str(user['last_login']) if user.get('last_login') else None,
                'in_database': True
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/webhooks/clerk', methods=['POST'])
def clerk_webhook():
    """
    Handle Clerk webhook events for user lifecycle management.
    Creates user in database when they sign up via Clerk.
    """
    try:
        # Get the webhook payload
        payload = request.get_json()

        if not payload:
            return jsonify({'success': False, 'error': 'No payload'}), 400

        event_type = payload.get('type')
        data = payload.get('data', {})

        if event_type == 'user.created':
            # Extract user info from Clerk webhook
            auth_id = data.get('id')
            email_addresses = data.get('email_addresses', [])
            email = email_addresses[0].get('email_address') if email_addresses else None
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip() or None

            if not auth_id or not email:
                return jsonify({
                    'success': False,
                    'error': 'Missing required user data'
                }), 400

            # Check if user already exists
            existing_user = db.get_user_by_auth_id(auth_id)
            if existing_user:
                return jsonify({
                    'success': True,
                    'message': 'User already exists'
                })

            # Create user with viewer role by default
            user = db.create_user(
                auth_provider_id=auth_id,
                email=email,
                full_name=full_name,
                role='viewer'
            )

            logger.info(f"Created new user: {email} (role: viewer)")

            return jsonify({
                'success': True,
                'message': 'User created',
                'user_id': user['id']
            })

        elif event_type == 'user.updated':
            # Update user info if needed
            auth_id = data.get('id')
            if auth_id:
                # Could update email/name here if needed
                pass

            return jsonify({'success': True, 'message': 'User update noted'})

        elif event_type == 'user.deleted':
            # Could handle user deletion here
            # For now, we'll keep the user record for audit purposes
            return jsonify({'success': True, 'message': 'User deletion noted'})

        else:
            # Unknown event type, just acknowledge
            return jsonify({'success': True, 'message': f'Event {event_type} received'})

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/users', methods=['GET'])
@require_admin
def get_all_users():
    """
    Get all users (admin only).
    Used for user management.
    """
    try:
        users = db.get_all_users()

        return jsonify({
            'success': True,
            'data': users,
            'count': len(users)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/users/<auth_id>/role', methods=['PATCH'])
@require_admin
def update_user_role(auth_id):
    """
    Update user role (admin only).
    Body: { role: 'admin' | 'viewer' }
    """
    try:
        data = request.get_json()

        if not data or 'role' not in data:
            return jsonify({
                'success': False,
                'error': 'role is required'
            }), 400

        role = data['role']
        if role not in ('admin', 'viewer'):
            return jsonify({
                'success': False,
                'error': "role must be 'admin' or 'viewer'"
            }), 400

        updated = db.update_user_role(auth_id, role)

        if not updated:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        return jsonify({
            'success': True,
            'message': f'User role updated to {role}'
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
    print(f"Auth: {'Clerk enabled' if config.CLERK_PUBLISHABLE_KEY else 'Disabled (dev mode)'}")
    app.run(debug=config.FLASK_DEBUG, port=config.FLASK_PORT, host='0.0.0.0')
