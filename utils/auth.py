from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

def hash_password(password: str) -> str:
    """Securely hash a password using werkzeug."""
    return generate_password_hash(password)

def verify_password(password_hash: str, password: str) -> bool:
    """Verify a plain password against the stored hash."""
    return check_password_hash(password_hash, password)

def is_api_request() -> bool:
    """Check if the current request is an API request or expects JSON."""
    return (
        request.path.startswith('/api/') or 
        request.is_json or 
        'application/json' in request.headers.get('Accept', '')
    )

def api_response(success: bool, message: str, data=None, status_code: int = 200):
    """Return a consistent JSON response format."""
    payload = {
        "success": success,
        "message": message,
        "data": data if data is not None else {}
    }
    return jsonify(payload), status_code

def login_required(view_func):
    """Ensure the user is logged into an active session."""
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get('logged_in') or not session.get('user_id'):
            if is_api_request():
                return api_response(False, "Authentication required. Please log in.", status_code=401)
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.path))
        return view_func(*args, **kwargs)
    return wrapped_view

def role_required(allowed_roles):
    """Ensure the logged-in user belongs to one of the permitted roles."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if not session.get('logged_in') or not session.get('user_id'):
                if is_api_request():
                    return api_response(False, "Authentication required.", status_code=401)
                flash("Please log in to continue.", "warning")
                return redirect(url_for('auth.login', next=request.path))
            
            user_role = session.get('role')
            if user_role not in allowed_roles:
                if is_api_request():
                    return api_response(False, "Unauthorized access. Role forbidden.", status_code=403)
                flash("You do not have permission to access that resource.", "danger")
                # Redirect user to their own dashboard
                if user_role == 'Farmer':
                    return redirect(url_for('farmer.dashboard'))
                elif user_role == 'Procurement Officer':
                    return redirect(url_for('officer.dashboard'))
                elif user_role == 'Admin':
                    return redirect(url_for('admin.dashboard'))
                return redirect(url_for('auth.login'))
            return view_func(*args, **kwargs)
        return wrapped_view
    return decorator

def farmer_required(view_func):
    """Convenience decorator for Farmer only routes."""
    return role_required(['Farmer'])(view_func)

def officer_required(view_func):
    """Convenience decorator for Procurement Officer only routes."""
    return role_required(['Procurement Officer'])(view_func)

def admin_required(view_func):
    """Convenience decorator for Admin only routes."""
    return role_required(['Admin'])(view_func)

def officer_or_admin_required(view_func):
    """Convenience decorator for either Officer or Admin routes."""
    return role_required(['Procurement Officer', 'Admin'])(view_func)

def get_current_user():
    """Fetch current user record from database based on session."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
