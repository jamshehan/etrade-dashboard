"""
Authentication middleware for Clerk JWT verification.
Provides decorators for protecting API endpoints.
"""

import os
import jwt
import requests
from functools import wraps
from flask import request, jsonify, g
from dotenv import load_dotenv
from logging_config import get_logger

load_dotenv()

# Initialize logger
logger = get_logger('auth')

# Clerk configuration
CLERK_JWKS_URL = os.getenv('CLERK_JWKS_URL', '')
CLERK_SECRET_KEY = os.getenv('CLERK_SECRET_KEY', '')

# Cache for JWKS keys
_jwks_cache = None


def get_jwks():
    """Fetch and cache JWKS (JSON Web Key Set) from Clerk"""
    global _jwks_cache

    if _jwks_cache is not None:
        return _jwks_cache

    if not CLERK_JWKS_URL:
        raise ValueError("CLERK_JWKS_URL not configured")

    try:
        logger.debug(f"Fetching JWKS from {CLERK_JWKS_URL}")
        response = requests.get(CLERK_JWKS_URL, timeout=10)
        response.raise_for_status()
        _jwks_cache = response.json()
        logger.debug("JWKS fetched and cached successfully")
        return _jwks_cache
    except requests.RequestException as e:
        logger.error(f"Failed to fetch JWKS: {str(e)}")
        raise ValueError(f"Failed to fetch JWKS: {str(e)}")


def get_public_key(token):
    """Get the public key for verifying the JWT"""
    try:
        # Get the key ID from the token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')

        if not kid:
            raise ValueError("Token missing 'kid' header")

        # Find the matching key in JWKS
        jwks = get_jwks()
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                # Convert JWK to PEM format
                from jwt.algorithms import RSAAlgorithm
                return RSAAlgorithm.from_jwk(key)

        raise ValueError(f"No matching key found for kid: {kid}")

    except Exception as e:
        raise ValueError(f"Failed to get public key: {str(e)}")


def verify_clerk_token(token):
    """
    Verify Clerk JWT token and return user claims.

    Returns dict with:
        - sub: User ID (Clerk user ID)
        - email: User's email (if available)
        - Other Clerk claims
    """
    if not token:
        raise ValueError("No token provided")

    try:
        # Get the public key for verification
        public_key = get_public_key(token)

        # Verify and decode the token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            options={
                'verify_exp': True,
                'verify_aud': False,  # Clerk doesn't always set audience
                'verify_iss': False,  # We'll verify issuer manually if needed
            }
        )

        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token verification failed: expired token")
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token verification failed: {str(e)}")
        raise ValueError(f"Invalid token: {str(e)}")


def get_token_from_request():
    """Extract Bearer token from Authorization header"""
    auth_header = request.headers.get('Authorization', '')

    if not auth_header:
        return None

    parts = auth_header.split()

    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None

    return parts[1]


def require_auth(f):
    """
    Decorator to require valid authentication.
    Sets g.current_user with user claims from the token.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Skip auth in development if no Clerk keys configured
        if not CLERK_JWKS_URL and os.getenv('FLASK_DEBUG', '').lower() == 'true':
            logger.debug("Auth bypassed in dev mode (no Clerk keys configured)")
            g.current_user = {'sub': 'dev-user', 'email': 'dev@localhost', 'role': 'admin'}
            return f(*args, **kwargs)

        token = get_token_from_request()

        if not token:
            logger.warning(f"Missing auth token for {request.method} {request.path}")
            return jsonify({
                'success': False,
                'error': 'Authorization header required'
            }), 401

        try:
            user_claims = verify_clerk_token(token)
            g.current_user = user_claims
            return f(*args, **kwargs)

        except ValueError as e:
            logger.warning(f"Auth failed for {request.method} {request.path}: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 401

    return decorated


def require_admin(f):
    """
    Decorator to require admin role.
    Must be used after @require_auth or will check auth first.
    Checks user role from database.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Skip auth in development if no Clerk keys configured
        if not CLERK_JWKS_URL and os.getenv('FLASK_DEBUG', '').lower() == 'true':
            g.current_user = {'sub': 'dev-user', 'email': 'dev@localhost', 'role': 'admin'}
            return f(*args, **kwargs)

        token = get_token_from_request()

        if not token:
            return jsonify({
                'success': False,
                'error': 'Authorization header required'
            }), 401

        try:
            user_claims = verify_clerk_token(token)
            g.current_user = user_claims
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 401

        # Import here to avoid circular imports
        from app import db

        # Get user from database to check role
        user = db.get_user_by_auth_id(g.current_user.get('sub'))

        if not user:
            logger.warning(f"User not found in database: {g.current_user.get('sub')}")
            return jsonify({
                'success': False,
                'error': 'User not found in database'
            }), 403

        if user.get('role') != 'admin':
            logger.warning(f"Admin access denied for user {g.current_user.get('sub')} (role: {user.get('role')})")
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403

        # Add role to current_user for convenience
        g.current_user['role'] = user['role']
        g.current_user['db_user'] = user

        return f(*args, **kwargs)

    return decorated


def clear_jwks_cache():
    """Clear the JWKS cache (useful for testing or key rotation)"""
    global _jwks_cache
    _jwks_cache = None
