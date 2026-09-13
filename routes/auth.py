from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_db
from utils.auth import hash_password, verify_password, login_required
from config import Config

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    """Home landing page accessible to all users."""
    db = get_db()
    # Live stats for the landing page
    total_farmers = db.execute("SELECT COUNT(*) FROM users WHERE role = 'Farmer'").fetchone()[0]
    total_centers = db.execute("SELECT COUNT(*) FROM procurement_centers WHERE status = 'Active'").fetchone()[0]
    total_tokens = db.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
    completed_tokens = db.execute("SELECT COUNT(*) FROM tokens WHERE status = 'Completed'").fetchone()[0]
    
    # Centers list for the preview section
    centers = db.execute("SELECT * FROM procurement_centers ORDER BY name ASC").fetchall()

    return render_template('index.html', 
                           total_farmers=total_farmers, 
                           total_centers=total_centers, 
                           total_tokens=total_tokens, 
                           completed_tokens=completed_tokens,
                           centers=centers)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route supporting Farmer, Procurement Officer, and Admin roles."""
    if session.get('logged_in'):
        role = session.get('role')
        if role == 'Farmer':
            return redirect(url_for('farmer.dashboard'))
        elif role == 'Procurement Officer':
            return redirect(url_for('officer.dashboard'))
        elif role == 'Admin':
            return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        selected_role = request.form.get('role', '').strip()

        if not email or not password or not selected_role:
            flash("Please enter email, password, and select your designated role.", "danger")
            return render_template('login.html', email=email, role=selected_role)

        if selected_role not in ['Farmer', 'Procurement Officer', 'Admin']:
            flash("Invalid role selected.", "danger")
            return render_template('login.html', email=email, role=selected_role)

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if not user:
            flash("No account found with this email address. Please register.", "danger")
            return render_template('login.html', email=email, role=selected_role)

        if not verify_password(user['password_hash'], password):
            flash("Incorrect password. Please try again.", "danger")
            return render_template('login.html', email=email, role=selected_role)

        # Enforce server-side role match
        if user['role'] != selected_role:
            flash("Invalid role selected for this account.", "danger")
            return render_template('login.html', email=email, role=selected_role)

        # Login successful - populate session
        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['role'] = user['role']
        session['email'] = user['email']
        session['assigned_center_id'] = user['assigned_center_id']
        session['logged_in'] = True

        flash(f"Welcome back, {user['full_name']}!", "success")

        if user['role'] == 'Farmer':
            return redirect(url_for('farmer.dashboard'))
        elif user['role'] == 'Procurement Officer':
            return redirect(url_for('officer.dashboard'))
        elif user['role'] == 'Admin':
            return redirect(url_for('admin.dashboard'))

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Dynamic user registration route for Farmer, Officer, and key-protected Admin."""
    db = get_db()
    centers = db.execute("SELECT id, name, district FROM procurement_centers WHERE status = 'Active' ORDER BY name ASC").fetchall()

    if request.method == 'POST':
        role = request.form.get('role', '').strip()
        full_name = request.form.get('full_name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        district = request.form.get('district', '').strip()
        state = request.form.get('state', '').strip()

        village = request.form.get('village', '').strip() if role == 'Farmer' else None
        assigned_center_id = request.form.get('assigned_center_id', '').strip() if role == 'Procurement Officer' else None
        admin_key = request.form.get('admin_key', '').strip() if role == 'Admin' else None

        # Basic validations
        if role not in ['Farmer', 'Procurement Officer', 'Admin']:
            flash("Please select a valid role.", "danger")
            return render_template('register.html', centers=centers)

        if not full_name or not mobile or not email or not password or not district or not state:
            flash("All mandatory fields must be filled.", "danger")
            return render_template('register.html', centers=centers)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html', centers=centers)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('register.html', centers=centers)

        # Role specific checks
        if role == 'Procurement Officer':
            if not assigned_center_id:
                flash("Please select your assigned Procurement Center.", "danger")
                return render_template('register.html', centers=centers)
            try:
                assigned_center_id = int(assigned_center_id)
            except ValueError:
                flash("Invalid Procurement Center selected.", "danger")
                return render_template('register.html', centers=centers)

        if role == 'Admin':
            if admin_key != Config.ADMIN_REGISTRATION_KEY:
                flash("Invalid Admin Registration Key. Public admin registration is restricted.", "danger")
                return render_template('register.html', centers=centers)

        # Check existing email
        existing_user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user:
            flash("An account with this email address already exists. Please log in.", "warning")
            return redirect(url_for('auth.login'))

        # Insert user
        pwd_hash = hash_password(password)
        db.execute("""
            INSERT INTO users (full_name, mobile, email, password_hash, village, district, state, role, assigned_center_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (full_name, mobile, email, pwd_hash, village, district, state, role, assigned_center_id))
        db.commit()

        flash(f"Registration successful as {role}! Please sign in to access your portal.", "success")
        return redirect(url_for('auth.login'))

    return render_template('register.html', centers=centers)

@auth_bp.route('/profile')
@login_required
def profile():
    """View personal profile details."""
    db = get_db()
    user = db.execute("""
        SELECT u.*, pc.name AS assigned_center_name 
        FROM users u 
        LEFT JOIN procurement_centers pc ON u.assigned_center_id = pc.id 
        WHERE u.id = ?
    """, (session['user_id'],)).fetchone()

    # User's recent notifications
    notifications = db.execute("""
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 10
    """, (session['user_id'],)).fetchall()

    return render_template('profile.html', user=user, notifications=notifications)

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Sign out the current user and clear session."""
    user_name = session.get('user_name', 'User')
    session.clear()
    flash(f"Goodbye, {user_name}. You have been securely logged out.", "info")
    return redirect(url_for('auth.index'))
