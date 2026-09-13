import os
import datetime
from flask import Flask, render_template, request, session, jsonify
from config import Config
from database import init_app, init_db, get_db
from routes.auth import auth_bp
from routes.farmer import farmer_bp
from routes.officer import officer_bp
from routes.admin import admin_bp
from routes.api import api_bp
from utils.auth import is_api_request, api_response

def create_app(test_config=None):
    """Application factory for Kisan Setu."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # Initialize Database
    init_app(app)
    with app.app_context():
        init_db()

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(farmer_bp)
    app.register_blueprint(officer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Global Context Processor
    @app.context_processor
    def inject_globals():
        unread_notifications_count = 0
        if session.get('logged_in') and session.get('user_id'):
            try:
                db = get_db()
                unread = db.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0", (session['user_id'],)).fetchone()
                if unread:
                    unread_notifications_count = unread[0]
            except Exception:
                pass

        return {
            'now': datetime.datetime.now(),
            'current_year': datetime.datetime.now().year,
            'current_user_name': session.get('user_name'),
            'current_role': session.get('role'),
            'is_logged_in': session.get('logged_in', False),
            'unread_notifications_count': unread_notifications_count
        }

    # Custom Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if is_api_request():
            return api_response(False, "Resource not found.", status_code=404)
        return render_template('404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        if is_api_request():
            return api_response(False, "Forbidden access.", status_code=403)
        return render_template('404.html', message="Access Forbidden: You do not have permission to view this page."), 403

    @app.errorhandler(500)
    def internal_error(error):
        if is_api_request():
            return api_response(False, "Internal server error occurred.", status_code=500)
        return render_template('500.html'), 500

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"[*] Starting Kisan Setu Web Application on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
