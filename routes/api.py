from flask import Blueprint, request, session, jsonify
from database import get_db
from utils.auth import (
    hash_password, verify_password, api_response, 
    login_required, farmer_required, officer_required, admin_required
)
from config import Config
import datetime
import random
import uuid

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Helper to convert sqlite3.Row or list of Rows to dict
def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    # Remove sensitive fields
    d.pop('password_hash', None)
    return d

def rows_to_list(rows):
    return [row_to_dict(r) for r in rows]

# ==================================================
# AUTHENTICATION APIS
# ==================================================

@api_bp.route('/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    role = data.get('role', '').strip()
    full_name = data.get('full_name', '').strip()
    mobile = data.get('mobile', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()
    district = data.get('district', '').strip()
    state = data.get('state', '').strip()
    village = data.get('village', '').strip() if role == 'Farmer' else None
    assigned_center_id = data.get('assigned_center_id') if role == 'Procurement Officer' else None
    admin_key = data.get('admin_key', '').strip() if role == 'Admin' else None

    if role not in ['Farmer', 'Procurement Officer', 'Admin']:
        return api_response(False, "Invalid role selected.", status_code=400)

    if not full_name or not mobile or not email or not password or not district or not state:
        return api_response(False, "All required fields must be provided.", status_code=400)

    if password != confirm_password:
        return api_response(False, "Passwords do not match.", status_code=400)

    if len(password) < 6:
        return api_response(False, "Password must be at least 6 characters long.", status_code=400)

    if role == 'Procurement Officer' and not assigned_center_id:
        return api_response(False, "Procurement Officer must have an assigned center.", status_code=400)

    if role == 'Admin' and admin_key != Config.ADMIN_REGISTRATION_KEY:
        return api_response(False, "Invalid Admin registration key.", status_code=403)

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return api_response(False, "An account with this email already exists.", status_code=409)

    pwd_hash = hash_password(password)
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO users (full_name, mobile, email, password_hash, village, district, state, role, assigned_center_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (full_name, mobile, email, pwd_hash, village, district, state, role, assigned_center_id))
    db.commit()
    user_id = cursor.lastrowid

    return api_response(True, f"Registration successful as {role}.", {"user_id": user_id, "email": email, "role": role}, status_code=201)

@api_bp.route('/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    selected_role = data.get('role', '').strip()

    if not email or not password or not selected_role:
        return api_response(False, "Email, password, and role are required.", status_code=400)

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user:
        return api_response(False, "No account found with this email address.", status_code=404)

    if not verify_password(user['password_hash'], password):
        return api_response(False, "Incorrect password.", status_code=401)

    if user['role'] != selected_role:
        return api_response(False, "Invalid role selected for this account.", status_code=403)

    session.clear()
    session['user_id'] = user['id']
    session['user_name'] = user['full_name']
    session['role'] = user['role']
    session['email'] = user['email']
    session['assigned_center_id'] = user['assigned_center_id']
    session['logged_in'] = True

    return api_response(True, "Login successful.", {
        "user_id": user['id'],
        "full_name": user['full_name'],
        "role": user['role'],
        "email": user['email']
    }, status_code=200)

@api_bp.route('/logout', methods=['POST'])
def api_logout():
    session.clear()
    return api_response(True, "Successfully logged out.", status_code=200)

@api_bp.route('/profile', methods=['GET'])
@login_required
def api_profile():
    db = get_db()
    user = db.execute("""
        SELECT u.*, pc.name AS center_name
        FROM users u
        LEFT JOIN procurement_centers pc ON u.assigned_center_id = pc.id
        WHERE u.id = ?
    """, (session['user_id'],)).fetchone()
    return api_response(True, "User profile retrieved.", row_to_dict(user))

# ==================================================
# FARMER APIS
# ==================================================

@api_bp.route('/farmer/dashboard', methods=['GET'])
@farmer_required
def api_farmer_dashboard():
    user_id = session['user_id']
    db = get_db()

    token = db.execute("""
        SELECT t.*, s.slot_date, s.start_time, s.end_time, pc.name AS center_name,
               p.amount AS payment_amount, p.payment_status, p.transaction_reference
        FROM tokens t
        JOIN slots s ON t.slot_id = s.id
        JOIN procurement_centers pc ON t.procurement_center_id = pc.id
        LEFT JOIN payments p ON p.token_id = t.id
        WHERE t.user_id = ?
        ORDER BY t.created_at DESC LIMIT 1
    """, (user_id,)).fetchone()

    notifications = db.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 5", (user_id,)).fetchall()

    return api_response(True, "Farmer dashboard data retrieved.", {
        "token": row_to_dict(token),
        "notifications": rows_to_list(notifications)
    })

@api_bp.route('/slots', methods=['GET'])
def api_slots():
    db = get_db()
    center_id = request.args.get('center_id', type=int)
    slot_date = request.args.get('date', '').strip()
    today = datetime.date.today().isoformat()

    query = """
        SELECT s.*, pc.name AS center_name, pc.district,
               (s.max_capacity - s.booked_count) AS available_capacity
        FROM slots s
        JOIN procurement_centers pc ON s.procurement_center_id = pc.id
        WHERE s.slot_date >= ?
    """
    params = [today]

    if center_id:
        query += " AND s.procurement_center_id = ?"
        params.append(center_id)
    if slot_date:
        query += " AND s.slot_date = ?"
        params.append(slot_date)

    query += " ORDER BY s.slot_date ASC, s.start_time ASC"
    slots = db.execute(query, params).fetchall()
    return api_response(True, "Slots retrieved successfully.", rows_to_list(slots))

@api_bp.route('/procurement-centers', methods=['GET'])
def api_procurement_centers():
    db = get_db()
    today = datetime.date.today().isoformat()
    centers = db.execute("""
        SELECT pc.*,
               (SELECT COUNT(*) FROM slots WHERE procurement_center_id = pc.id AND slot_date >= ? AND status = 'Available') AS available_slots
        FROM procurement_centers pc
        ORDER BY pc.name ASC
    """, (today,)).fetchall()
    return api_response(True, "Procurement centers retrieved.", rows_to_list(centers))

@api_bp.route('/slots/<int:slot_id>/book', methods=['POST'])
@farmer_required
def api_book_slot(slot_id):
    user_id = session['user_id']
    data = request.get_json() or {}
    crop_type = data.get('crop_type', 'Paddy / Rice')
    try:
        est_quantity = float(data.get('estimated_quantity_quintals', 50.0))
    except (ValueError, TypeError):
        est_quantity = 50.0

    db = get_db()

    # Check active tokens
    existing = db.execute("""
        SELECT id, token_number FROM tokens 
        WHERE user_id = ? AND status IN ('Booked', 'Waiting', 'Processing')
    """, (user_id,)).fetchone()
    if existing:
        return api_response(False, f"You already hold active token {existing['token_number']}.", status_code=409)

    try:
        slot = db.execute("SELECT * FROM slots WHERE id = ?", (slot_id,)).fetchone()
        if not slot:
            return api_response(False, "Slot not found.", status_code=404)

        if slot['status'] != 'Available' or slot['booked_count'] >= slot['max_capacity']:
            return api_response(False, "Slot is fully booked.", status_code=409)

        queue_count = db.execute("SELECT COUNT(*) FROM tokens WHERE slot_id = ? AND status != 'Cancelled'", (slot_id,)).fetchone()[0]
        queue_pos = queue_count + 1

        rand_suffix = random.randint(1000, 9999)
        token_number = f"KS-{slot['procurement_center_id']}{slot_id % 100:02d}-{rand_suffix}"

        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO tokens (token_number, user_id, slot_id, procurement_center_id, crop_type, estimated_quantity_quintals, queue_position, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Waiting')
        """, (token_number, user_id, slot_id, slot['procurement_center_id'], crop_type, est_quantity, queue_pos))
        new_token_id = cursor.lastrowid

        new_booked = slot['booked_count'] + 1
        new_status = 'Full' if new_booked >= slot['max_capacity'] else 'Available'
        db.execute("UPDATE slots SET booked_count = ?, status = ? WHERE id = ?", (new_booked, new_status, slot_id))

        amount = round(est_quantity * 2300.0, 2)
        db.execute("""
            INSERT INTO payments (token_id, user_id, amount, payment_status)
            VALUES (?, ?, ?, 'Pending')
        """, (new_token_id, user_id, amount))

        db.execute("""
            INSERT INTO notifications (user_id, message, notification_type)
            VALUES (?, ?, 'success')
        """, (user_id, f"Digital Token {token_number} generated successfully."))

        db.commit()

        return api_response(True, "Slot booked successfully!", {
            "token_id": new_token_id,
            "token_number": token_number,
            "queue_position": queue_pos,
            "status": "Waiting"
        }, status_code=201)

    except Exception as e:
        db.rollback()
        return api_response(False, f"Booking failed: {str(e)}", status_code=500)

@api_bp.route('/my-token', methods=['GET'])
@farmer_required
def api_my_token():
    user_id = session['user_id']
    db = get_db()
    token = db.execute("""
        SELECT t.*, s.slot_date, s.start_time, s.end_time, pc.name AS center_name, pc.location AS center_location,
               u.full_name AS farmer_name, p.amount, p.payment_status, p.transaction_reference
        FROM tokens t
        JOIN users u ON t.user_id = u.id
        JOIN slots s ON t.slot_id = s.id
        JOIN procurement_centers pc ON t.procurement_center_id = pc.id
        LEFT JOIN payments p ON p.token_id = t.id
        WHERE t.user_id = ?
        ORDER BY t.created_at DESC LIMIT 1
    """, (user_id,)).fetchone()

    if not token:
        return api_response(False, "No token found for current user.", status_code=404)

    return api_response(True, "Token retrieved.", row_to_dict(token))

@api_bp.route('/queue/<int:token_id>', methods=['GET'])
@login_required
def api_queue_details(token_id):
    db = get_db()
    token = db.execute("""
        SELECT t.*, pc.name AS center_name
        FROM tokens t
        JOIN procurement_centers pc ON t.procurement_center_id = pc.id
        WHERE t.id = ?
    """, (token_id,)).fetchone()

    if not token:
        return api_response(False, "Token not found.", status_code=404)

    # People ahead
    people_ahead = db.execute("""
        SELECT COUNT(*) FROM tokens
        WHERE slot_id = ? AND queue_position < ? AND status IN ('Booked', 'Waiting')
    """, (token['slot_id'], token['queue_position'])).fetchone()[0]

    est_minutes = 5 * people_ahead

    proc = db.execute("""
        SELECT token_number FROM tokens
        WHERE procurement_center_id = ? AND status = 'Processing'
        ORDER BY queue_position ASC LIMIT 1
    """, (token['procurement_center_id'],)).fetchone()

    return api_response(True, "Queue details retrieved.", {
        "token_number": token['token_number'],
        "queue_position": token['queue_position'],
        "people_ahead": people_ahead,
        "estimated_waiting_minutes": est_minutes,
        "current_processing_token": proc['token_number'] if proc else None,
        "status": token['status']
    })

@api_bp.route('/status/<int:token_id>', methods=['GET'])
@login_required
def api_status_details(token_id):
    db = get_db()
    token = db.execute("""
        SELECT t.*, p.payment_status, p.transaction_reference, p.paid_at
        FROM tokens t
        LEFT JOIN payments p ON p.token_id = t.id
        WHERE t.id = ?
    """, (token_id,)).fetchone()

    if not token:
        return api_response(False, "Token not found.", status_code=404)

    return api_response(True, "Status retrieved.", row_to_dict(token))

@api_bp.route('/payments/<int:token_id>', methods=['GET'])
@login_required
def api_payment_details(token_id):
    db = get_db()
    payment = db.execute("""
        SELECT p.*, t.token_number, t.status AS token_status
        FROM payments p
        JOIN tokens t ON p.token_id = t.id
        WHERE p.token_id = ?
    """, (token_id,)).fetchone()

    if not payment:
        return api_response(False, "Payment record not found.", status_code=404)

    return api_response(True, "Payment details retrieved.", row_to_dict(payment))

# ==================================================
# PROCUREMENT OFFICER APIS
# ==================================================

@api_bp.route('/officer/dashboard', methods=['GET'])
@officer_required
def api_officer_dashboard():
    officer_id = session['user_id']
    db = get_db()
    officer = db.execute("SELECT assigned_center_id FROM users WHERE id = ?", (officer_id,)).fetchone()
    center_id = officer['assigned_center_id'] if officer and officer['assigned_center_id'] else 1
    today = datetime.date.today().isoformat()

    stats = {
        "center_id": center_id,
        "today_bookings": db.execute("SELECT COUNT(*) FROM tokens t JOIN slots s ON t.slot_id = s.id WHERE t.procurement_center_id = ? AND s.slot_date = ?", (center_id, today)).fetchone()[0],
        "waiting": db.execute("SELECT COUNT(*) FROM tokens t JOIN slots s ON t.slot_id = s.id WHERE t.procurement_center_id = ? AND s.slot_date = ? AND t.status IN ('Booked', 'Waiting')", (center_id, today)).fetchone()[0],
        "processing": db.execute("SELECT COUNT(*) FROM tokens t JOIN slots s ON t.slot_id = s.id WHERE t.procurement_center_id = ? AND s.slot_date = ? AND t.status = 'Processing'", (center_id, today)).fetchone()[0],
        "completed": db.execute("SELECT COUNT(*) FROM tokens t JOIN slots s ON t.slot_id = s.id WHERE t.procurement_center_id = ? AND s.slot_date = ? AND t.status = 'Completed'", (center_id, today)).fetchone()[0]
    }
    return api_response(True, "Officer dashboard metrics retrieved.", stats)

@api_bp.route('/officer/bookings', methods=['GET'])
@officer_required
def api_officer_bookings():
    officer_id = session['user_id']
    db = get_db()
    officer = db.execute("SELECT assigned_center_id FROM users WHERE id = ?", (officer_id,)).fetchone()
    center_id = officer['assigned_center_id'] if officer and officer['assigned_center_id'] else 1
    today = datetime.date.today().isoformat()

    bookings = db.execute("""
        SELECT t.*, u.full_name AS farmer_name, u.mobile AS farmer_mobile, u.village,
               s.slot_date, s.start_time, s.end_time, p.amount, p.payment_status
        FROM tokens t
        JOIN users u ON t.user_id = u.id
        JOIN slots s ON t.slot_id = s.id
        LEFT JOIN payments p ON p.token_id = t.id
        WHERE t.procurement_center_id = ? AND s.slot_date = ?
        ORDER BY t.queue_position ASC
    """, (center_id, today)).fetchall()

    return api_response(True, "Officer bookings retrieved.", rows_to_list(bookings))

@api_bp.route('/officer/queue', methods=['GET'])
@officer_required
def api_officer_queue():
    officer_id = session['user_id']
    db = get_db()
    officer = db.execute("SELECT assigned_center_id FROM users WHERE id = ?", (officer_id,)).fetchone()
    center_id = officer['assigned_center_id'] if officer and officer['assigned_center_id'] else 1
    today = datetime.date.today().isoformat()

    queue_items = db.execute("""
        SELECT t.*, u.full_name AS farmer_name, u.mobile AS farmer_mobile,
               s.slot_date, s.start_time, s.end_time
        FROM tokens t
        JOIN users u ON t.user_id = u.id
        JOIN slots s ON t.slot_id = s.id
        WHERE t.procurement_center_id = ? AND s.slot_date = ?
        ORDER BY t.queue_position ASC
    """, (center_id, today)).fetchall()

    return api_response(True, "Queue retrieved.", rows_to_list(queue_items))

@api_bp.route('/officer/farmer/<int:user_id>', methods=['GET'])
@officer_required
def api_officer_farmer(user_id):
    db = get_db()
    farmer = db.execute("SELECT id, full_name, mobile, email, village, district, state, created_at FROM users WHERE id = ? AND role = 'Farmer'", (user_id,)).fetchone()
    if not farmer:
        return api_response(False, "Farmer not found.", status_code=404)
    return api_response(True, "Farmer details retrieved.", row_to_dict(farmer))

@api_bp.route('/officer/tokens/<int:token_id>/status', methods=['PUT'])
@officer_required
def api_officer_update_status(token_id):
    data = request.get_json() or {}
    new_status = data.get('status', '').strip()
    if new_status not in ['Booked', 'Waiting', 'Processing', 'Completed', 'Cancelled']:
        return api_response(False, "Invalid status.", status_code=400)

    db = get_db()
    token = db.execute("SELECT * FROM tokens WHERE id = ?", (token_id,)).fetchone()
    if not token:
        return api_response(False, "Token not found.", status_code=404)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute("UPDATE tokens SET status = ?, updated_at = ? WHERE id = ?", (new_status, now, token_id))
    
    if new_status == 'Completed':
        txn_ref = f"TXN-KS-{datetime.datetime.now().strftime('%Y%m%d%H%M')}-{token_id:04d}"
        db.execute("""
            UPDATE payments 
            SET payment_status = 'Payment Done', transaction_reference = ?, paid_at = ? 
            WHERE token_id = ?
        """, (txn_ref, now, token_id))

    db.commit()
    return api_response(True, f"Token status updated to {new_status}.", {"token_id": token_id, "status": new_status})

@api_bp.route('/officer/tokens/<int:token_id>/complete', methods=['POST'])
@officer_required
def api_officer_complete_procurement(token_id):
    db = get_db()
    token = db.execute("SELECT * FROM tokens WHERE id = ?", (token_id,)).fetchone()
    if not token:
        return api_response(False, "Token not found.", status_code=404)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txn_ref = f"TXN-KS-{datetime.datetime.now().strftime('%Y%m%d%H%M')}-{token_id:04d}"

    db.execute("UPDATE tokens SET status = 'Completed', updated_at = ? WHERE id = ?", (now, token_id))
    db.execute("""
        UPDATE payments 
        SET payment_status = 'Payment Done', transaction_reference = ?, paid_at = ? 
        WHERE token_id = ?
    """, (txn_ref, now, token_id))

    db.execute("""
        INSERT INTO notifications (user_id, message, notification_type)
        VALUES (?, ?, 'success')
    """, (token['user_id'], f"Procurement verified and completed. Payment Reference: {txn_ref}"))

    db.commit()
    return api_response(True, "Procurement marked as Completed.", {
        "token_id": token_id,
        "status": "Completed",
        "payment_status": "Payment Done",
        "transaction_reference": txn_ref
    })

# ==================================================
# ADMIN APIS
# ==================================================

@api_bp.route('/admin/dashboard', methods=['GET'])
@admin_required
def api_admin_dashboard():
    db = get_db()
    today = datetime.date.today().isoformat()
    metrics = {
        "total_farmers": db.execute("SELECT COUNT(*) FROM users WHERE role = 'Farmer'").fetchone()[0],
        "total_officers": db.execute("SELECT COUNT(*) FROM users WHERE role = 'Procurement Officer'").fetchone()[0],
        "total_centers": db.execute("SELECT COUNT(*) FROM procurement_centers").fetchone()[0],
        "today_slots": db.execute("SELECT COUNT(*) FROM slots WHERE slot_date = ?", (today,)).fetchone()[0],
        "waiting_tokens": db.execute("SELECT COUNT(*) FROM tokens WHERE status IN ('Booked', 'Waiting')").fetchone()[0],
        "processing_tokens": db.execute("SELECT COUNT(*) FROM tokens WHERE status = 'Processing'").fetchone()[0],
        "completed_tokens": db.execute("SELECT COUNT(*) FROM tokens WHERE status = 'Completed'").fetchone()[0],
        "payments_done": db.execute("SELECT COUNT(*) FROM payments WHERE payment_status = 'Payment Done'").fetchone()[0],
        "total_disbursed": db.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payment_status = 'Payment Done'").fetchone()[0]
    }
    return api_response(True, "Admin dashboard metrics retrieved.", metrics)

@api_bp.route('/admin/farmers', methods=['GET'])
@admin_required
def api_admin_farmers():
    db = get_db()
    farmers = db.execute("SELECT id, full_name, mobile, email, village, district, state, created_at FROM users WHERE role = 'Farmer' ORDER BY created_at DESC").fetchall()
    return api_response(True, "Farmers retrieved.", rows_to_list(farmers))

@api_bp.route('/admin/officers', methods=['GET'])
@admin_required
def api_admin_officers():
    db = get_db()
    officers = db.execute("""
        SELECT u.id, u.full_name, u.mobile, u.email, u.district, u.state, u.assigned_center_id, pc.name AS center_name
        FROM users u
        LEFT JOIN procurement_centers pc ON u.assigned_center_id = pc.id
        WHERE u.role = 'Procurement Officer'
        ORDER BY u.created_at DESC
    """).fetchall()
    return api_response(True, "Officers retrieved.", rows_to_list(officers))

@api_bp.route('/admin/centers', methods=['GET', 'POST'])
@admin_required
def api_admin_centers():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        location = data.get('location', '').strip()
        district = data.get('district', '').strip()
        state = data.get('state', '').strip()
        contact = data.get('contact', '').strip()
        opening = data.get('opening_time', '08:00 AM')
        closing = data.get('closing_time', '05:00 PM')
        status = data.get('status', 'Active')
        lat = data.get('latitude', 16.8142)
        lng = data.get('longitude', 81.5268)

        if not name or not location or not district or not state or not contact:
            return api_response(False, "Missing required center fields.", status_code=400)

        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO procurement_centers (name, location, district, state, latitude, longitude, contact, opening_time, closing_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, location, district, state, lat, lng, contact, opening, closing, status))
        db.commit()
        return api_response(True, "Procurement center created.", {"id": cursor.lastrowid, "name": name}, status_code=201)

    centers = db.execute("SELECT * FROM procurement_centers ORDER BY name ASC").fetchall()
    return api_response(True, "Procurement centers retrieved.", rows_to_list(centers))

@api_bp.route('/admin/centers/<int:center_id>', methods=['PUT'])
@admin_required
def api_admin_update_center(center_id):
    data = request.get_json() or {}
    db = get_db()
    center = db.execute("SELECT * FROM procurement_centers WHERE id = ?", (center_id,)).fetchone()
    if not center:
        return api_response(False, "Center not found.", status_code=404)

    name = data.get('name', center['name'])
    location = data.get('location', center['location'])
    district = data.get('district', center['district'])
    state = data.get('state', center['state'])
    contact = data.get('contact', center['contact'])
    opening = data.get('opening_time', center['opening_time'])
    closing = data.get('closing_time', center['closing_time'])
    status = data.get('status', center['status'])

    db.execute("""
        UPDATE procurement_centers 
        SET name = ?, location = ?, district = ?, state = ?, contact = ?, opening_time = ?, closing_time = ?, status = ?
        WHERE id = ?
    """, (name, location, district, state, contact, opening, closing, status, center_id))
    db.commit()
    return api_response(True, "Center updated successfully.", {"id": center_id, "name": name})

@api_bp.route('/admin/slots', methods=['GET', 'POST'])
@admin_required
def api_admin_slots():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json() or {}
        center_id = data.get('procurement_center_id')
        slot_date = data.get('slot_date', '').strip()
        start_time = data.get('start_time', '').strip()
        end_time = data.get('end_time', '').strip()
        max_capacity = data.get('max_capacity', 20)

        if not center_id or not slot_date or not start_time or not end_time:
            return api_response(False, "Missing slot parameters.", status_code=400)

        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO slots (procurement_center_id, slot_date, start_time, end_time, max_capacity, booked_count, status)
            VALUES (?, ?, ?, ?, ?, 0, 'Available')
        """, (center_id, slot_date, start_time, end_time, max_capacity))
        db.commit()
        return api_response(True, "Slot created successfully.", {"id": cursor.lastrowid}, status_code=201)

    slots = db.execute("""
        SELECT s.*, pc.name AS center_name 
        FROM slots s 
        JOIN procurement_centers pc ON s.procurement_center_id = pc.id 
        ORDER BY s.slot_date DESC LIMIT 100
    """).fetchall()
    return api_response(True, "Slots retrieved.", rows_to_list(slots))

@api_bp.route('/admin/tokens', methods=['GET'])
@admin_required
def api_admin_tokens():
    db = get_db()
    tokens = db.execute("""
        SELECT t.*, u.full_name AS farmer_name, pc.name AS center_name, p.amount, p.payment_status
        FROM tokens t
        JOIN users u ON t.user_id = u.id
        JOIN procurement_centers pc ON t.procurement_center_id = pc.id
        LEFT JOIN payments p ON p.token_id = t.id
        ORDER BY t.created_at DESC LIMIT 100
    """).fetchall()
    return api_response(True, "Tokens retrieved.", rows_to_list(tokens))

@api_bp.route('/admin/tokens/<int:token_id>/status', methods=['PUT'])
@admin_required
def api_admin_update_token_status(token_id):
    data = request.get_json() or {}
    new_status = data.get('status', '').strip()
    if new_status not in ['Booked', 'Waiting', 'Processing', 'Completed', 'Cancelled']:
        return api_response(False, "Invalid status.", status_code=400)

    db = get_db()
    token = db.execute("SELECT * FROM tokens WHERE id = ?", (token_id,)).fetchone()
    if not token:
        return api_response(False, "Token not found.", status_code=404)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute("UPDATE tokens SET status = ?, updated_at = ? WHERE id = ?", (new_status, now, token_id))

    if new_status == 'Completed':
        txn_ref = f"TXN-KS-{datetime.datetime.now().strftime('%Y%m%d%H%M')}-{token_id:04d}"
        db.execute("""
            UPDATE payments 
            SET payment_status = 'Payment Done', transaction_reference = ?, paid_at = ? 
            WHERE token_id = ?
        """, (txn_ref, now, token_id))

    db.commit()
    return api_response(True, f"Token status updated to {new_status}.", {"token_id": token_id, "status": new_status})

@api_bp.route('/admin/reports', methods=['GET'])
@admin_required
def api_admin_reports():
    db = get_db()
    center_stats = db.execute("""
        SELECT pc.name, pc.district,
               COUNT(t.id) AS total_tokens,
               SUM(CASE WHEN t.status = 'Completed' THEN 1 ELSE 0 END) AS completed_tokens,
               COALESCE(SUM(CASE WHEN p.payment_status = 'Payment Done' THEN p.amount ELSE 0 END), 0) AS total_disbursed
        FROM procurement_centers pc
        LEFT JOIN tokens t ON t.procurement_center_id = pc.id
        LEFT JOIN payments p ON p.token_id = t.id
        GROUP BY pc.id
    """).fetchall()

    return api_response(True, "Reports generated.", rows_to_list(center_stats))
