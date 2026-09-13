from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_db
from utils.auth import farmer_required
import datetime
import random

farmer_bp = Blueprint('farmer', __name__, url_prefix='/farmer')

def get_farmer_active_token(user_id):
    """Retrieve the most relevant current or latest token for the farmer."""
    db = get_db()
    # First search for any active token (Booked, Waiting, Processing)
    active_token = db.execute("""
        SELECT t.*, s.slot_date, s.start_time, s.end_time, pc.name AS center_name, pc.location AS center_location,
               pc.contact AS center_contact, p.amount AS payment_amount, p.payment_status, p.transaction_reference, p.paid_at
        FROM tokens t
        JOIN slots s ON t.slot_id = s.id
        JOIN procurement_centers pc ON t.procurement_center_id = pc.id
        LEFT JOIN payments p ON p.token_id = t.id
        WHERE t.user_id = ? AND t.status IN ('Booked', 'Waiting', 'Processing')
        ORDER BY t.created_at DESC LIMIT 1
    """, (user_id,)).fetchone()

    if active_token:
        return active_token

    # Otherwise return the latest completed or recent token
    return db.execute("""
        SELECT t.*, s.slot_date, s.start_time, s.end_time, pc.name AS center_name, pc.location AS center_location,
               pc.contact AS center_contact, p.amount AS payment_amount, p.payment_status, p.transaction_reference, p.paid_at
        FROM tokens t
        JOIN slots s ON t.slot_id = s.id
        JOIN procurement_centers pc ON t.procurement_center_id = pc.id
        LEFT JOIN payments p ON p.token_id = t.id
        WHERE t.user_id = ?
        ORDER BY t.created_at DESC LIMIT 1
    """, (user_id,)).fetchone()

@farmer_bp.route('/dashboard')
@farmer_required
def dashboard():
    """Farmer main dashboard."""
    user_id = session['user_id']
    token = get_farmer_active_token(user_id)

    db = get_db()
    # Recent notifications
    notifications = db.execute("""
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 5
    """, (user_id,)).fetchall()

    # Available slots count today and forward
    today = datetime.date.today().isoformat()
    available_slots_count = db.execute("""
        SELECT COUNT(*) FROM slots 
        WHERE slot_date >= ? AND status = 'Available' AND booked_count < max_capacity
    """, (today,)).fetchone()[0]

    return render_template('farmer/dashboard.html', 
                           token=token, 
                           notifications=notifications,
                           available_slots_count=available_slots_count)

@farmer_bp.route('/schedule')
@farmer_required
def schedule():
    """View and filter available procurement slots."""
    db = get_db()
    center_id = request.args.get('center_id', type=int)
    selected_date = request.args.get('date', '').strip()

    centers = db.execute("SELECT * FROM procurement_centers WHERE status = 'Active' ORDER BY name ASC").fetchall()

    today = datetime.date.today().isoformat()
    query = """
        SELECT s.*, pc.name AS center_name, pc.location AS center_location, pc.district,
               (s.max_capacity - s.booked_count) AS available_capacity
        FROM slots s
        JOIN procurement_centers pc ON s.procurement_center_id = pc.id
        WHERE s.slot_date >= ?
    """
    params = [today]

    if center_id:
        query += " AND s.procurement_center_id = ?"
        params.append(center_id)
    if selected_date:
        query += " AND s.slot_date = ?"
        params.append(selected_date)

    query += " ORDER BY s.slot_date ASC, s.start_time ASC"
    slots = db.execute(query, params).fetchall()

    # Check if user already has an active token to show warning/badge
    active_token = get_farmer_active_token(session['user_id'])
    has_active_token = bool(active_token and active_token['status'] in ['Booked', 'Waiting', 'Processing'])

    return render_template('farmer/schedule.html', 
                           slots=slots, 
                           centers=centers, 
                           selected_center=center_id, 
                           selected_date=selected_date,
                           has_active_token=has_active_token,
                           active_token=active_token)

@farmer_bp.route('/book-slot/<int:slot_id>', methods=['POST'])
@farmer_required
def book_slot(slot_id):
    """Book a slot directly via form submission."""
    user_id = session['user_id']
    crop_type = request.form.get('crop_type', 'Paddy / Rice').strip()
    try:
        est_quantity = float(request.form.get('estimated_quantity_quintals', 50.0))
    except ValueError:
        est_quantity = 50.0

    db = get_db()

    # Check if user already has active booking
    existing = db.execute("""
        SELECT id, token_number FROM tokens 
        WHERE user_id = ? AND status IN ('Booked', 'Waiting', 'Processing')
    """, (user_id,)).fetchone()
    if existing:
        flash(f"You already have an active digital token ({existing['token_number']}). Only one active token is permitted at a time.", "warning")
        return redirect(url_for('farmer.token'))

    # Begin transaction
    try:
        # Lock and check slot
        slot = db.execute("SELECT * FROM slots WHERE id = ?", (slot_id,)).fetchone()
        if not slot:
            flash("Selected slot not found.", "danger")
            return redirect(url_for('farmer.schedule'))

        if slot['status'] != 'Available' or slot['booked_count'] >= slot['max_capacity']:
            flash("Sorry, this slot is completely full. Please choose another slot.", "danger")
            return redirect(url_for('farmer.schedule'))

        # Calculate queue position for this center and slot date
        queue_count = db.execute("""
            SELECT COUNT(*) FROM tokens 
            WHERE slot_id = ? AND status != 'Cancelled'
        """, (slot_id,)).fetchone()[0]
        queue_pos = queue_count + 1

        # Generate unique token number
        rand_suffix = random.randint(1000, 9999)
        token_number = f"KS-{slot['procurement_center_id']}{slot_id % 100:02d}-{rand_suffix}"

        # Insert token
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO tokens (token_number, user_id, slot_id, procurement_center_id, crop_type, estimated_quantity_quintals, queue_position, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Waiting')
        """, (token_number, user_id, slot_id, slot['procurement_center_id'], crop_type, est_quantity, queue_pos))
        new_token_id = cursor.lastrowid

        # Update slot booked count and status
        new_booked = slot['booked_count'] + 1
        new_status = 'Full' if new_booked >= slot['max_capacity'] else 'Available'
        db.execute("UPDATE slots SET booked_count = ?, status = ? WHERE id = ?", (new_booked, new_status, slot_id))

        # Standard MSP calculation (e.g., MSP for paddy ~ ₹2300 per quintal)
        msp_rate = 2300.0
        amount = round(est_quantity * msp_rate, 2)

        # Create pending payment record
        db.execute("""
            INSERT INTO payments (token_id, user_id, amount, payment_status)
            VALUES (?, ?, ?, 'Pending')
        """, (new_token_id, user_id, amount))

        # Create notification
        db.execute("""
            INSERT INTO notifications (user_id, message, notification_type)
            VALUES (?, ?, 'success')
        """, (user_id, f"Digital Token {token_number} confirmed for slot on {slot['slot_date']}."))

        db.commit()
        flash(f"Slot booked successfully! Your Digital Token number is {token_number}.", "success")
        return redirect(url_for('farmer.token'))

    except Exception as e:
        db.rollback()
        flash(f"Booking error: {str(e)}", "danger")
        return redirect(url_for('farmer.schedule'))

@farmer_bp.route('/token')
@farmer_required
def token():
    """Display official printable digital token."""
    user_id = session['user_id']
    token_record = get_farmer_active_token(user_id)
    return render_template('farmer/token.html', token=token_record)

@farmer_bp.route('/queue')
@farmer_required
def queue():
    """Live queue tracking page."""
    user_id = session['user_id']
    token_record = get_farmer_active_token(user_id)

    people_ahead = 0
    estimated_waiting_minutes = 0
    current_processing_token = None

    if token_record and token_record['status'] in ['Booked', 'Waiting', 'Processing']:
        db = get_db()
        # Find people ahead in the same center and slot
        ahead_count = db.execute("""
            SELECT COUNT(*) FROM tokens
            WHERE slot_id = ? AND queue_position < ? AND status IN ('Booked', 'Waiting')
        """, (token_record['slot_id'], token_record['queue_position'])).fetchone()[0]
        
        people_ahead = ahead_count
        # Rule: 5 minutes * number of people ahead
        estimated_waiting_minutes = 5 * people_ahead

        # Find current processing token in this center
        proc = db.execute("""
            SELECT token_number, queue_position FROM tokens
            WHERE procurement_center_id = ? AND status = 'Processing'
            ORDER BY queue_position ASC LIMIT 1
        """, (token_record['procurement_center_id'],)).fetchone()
        if proc:
            current_processing_token = proc['token_number']

    return render_template('farmer/queue.html', 
                           token=token_record, 
                           people_ahead=people_ahead, 
                           estimated_waiting_minutes=estimated_waiting_minutes,
                           current_processing_token=current_processing_token)

@farmer_bp.route('/procurement-centers')
@farmer_required
def procurement_centers():
    """View all procurement centers, contact info, and Google Maps directions."""
    db = get_db()
    today = datetime.date.today().isoformat()
    centers = db.execute("""
        SELECT pc.*, 
               (SELECT COUNT(*) FROM slots WHERE procurement_center_id = pc.id AND slot_date >= ? AND status = 'Available') AS available_slots
        FROM procurement_centers pc
        ORDER BY pc.name ASC
    """, (today,)).fetchall()

    return render_template('farmer/centers.html', centers=centers)

@farmer_bp.route('/status')
@farmer_required
def status():
    """Step-by-step progress tracking for the farmer."""
    user_id = session['user_id']
    token_record = get_farmer_active_token(user_id)
    return render_template('farmer/status.html', token=token_record)

@farmer_bp.route('/payment')
@farmer_required
def payment():
    """Farmer payment receipt view."""
    user_id = session['user_id']
    token_record = get_farmer_active_token(user_id)
    
    db = get_db()
    payment_records = db.execute("""
        SELECT p.*, t.token_number, s.slot_date, pc.name AS center_name
        FROM payments p
        JOIN tokens t ON p.token_id = t.id
        JOIN slots s ON t.slot_id = s.id
        JOIN procurement_centers pc ON t.procurement_center_id = pc.id
        WHERE p.user_id = ?
        ORDER BY p.id DESC
    """, (user_id,)).fetchall()

    return render_template('farmer/payment.html', token=token_record, payments=payment_records)
