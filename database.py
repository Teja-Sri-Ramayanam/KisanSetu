import sqlite3
from flask import g, current_app
from config import Config

def get_db():
    """Get database connection for current request context or standalone."""
    if 'db' not in g:
        db_path = current_app.config['DATABASE'] if current_app else Config.DATABASE
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def get_standalone_db(db_path=None):
    """Get standalone database connection outside Flask application context."""
    if db_path is None:
        try:
            if current_app:
                db_path = current_app.config['DATABASE']
            else:
                db_path = Config.DATABASE
        except RuntimeError:
            db_path = Config.DATABASE

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def close_db(e=None):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(db_path=None):
    """Create all tables and indexes if they do not exist."""
    conn = get_standalone_db(db_path)
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS procurement_centers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            district TEXT NOT NULL,
            state TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            contact TEXT NOT NULL,
            opening_time TEXT NOT NULL DEFAULT '08:00 AM',
            closing_time TEXT NOT NULL DEFAULT '05:00 PM',
            status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Inactive')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            village TEXT,
            district TEXT NOT NULL,
            state TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Farmer', 'Procurement Officer', 'Admin')),
            assigned_center_id INTEGER REFERENCES procurement_centers(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            procurement_center_id INTEGER NOT NULL REFERENCES procurement_centers(id) ON DELETE CASCADE,
            slot_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            max_capacity INTEGER NOT NULL DEFAULT 20,
            booked_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Available' CHECK(status IN ('Available', 'Full', 'Cancelled')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_number TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            slot_id INTEGER NOT NULL REFERENCES slots(id) ON DELETE CASCADE,
            procurement_center_id INTEGER NOT NULL REFERENCES procurement_centers(id) ON DELETE CASCADE,
            crop_type TEXT DEFAULT 'Paddy / Rice',
            estimated_quantity_quintals REAL DEFAULT 50.0,
            queue_position INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Booked' CHECK(status IN ('Booked', 'Waiting', 'Processing', 'Completed', 'Cancelled')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, slot_id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id INTEGER NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            amount REAL NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'Pending' CHECK(payment_status IN ('Pending', 'Payment Done')),
            transaction_reference TEXT,
            paid_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            notification_type TEXT NOT NULL DEFAULT 'info',
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Performance Indexes
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_slots_center_date ON slots(procurement_center_id, slot_date);
        CREATE INDEX IF NOT EXISTS idx_tokens_user ON tokens(user_id);
        CREATE INDEX IF NOT EXISTS idx_tokens_center_status ON tokens(procurement_center_id, status);
        CREATE INDEX IF NOT EXISTS idx_payments_token ON payments(token_id);
        CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
        """)
    conn.close()

def init_app(app):
    """Register database functions with Flask app."""
    app.teardown_appcontext(close_db)
