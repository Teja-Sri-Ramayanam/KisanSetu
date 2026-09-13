from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_db
from utils.auth import officer_required
import datetime
import uuid

officer_bp = Blueprint('officer', __name__, url_prefix='/officer')

def get_officer_center(officer_id):
    """Retrieve officer's assigned center details."""
    db = get_db()
    officer = db.execute("SELECT assigned_center_id FROM users WHERE id = ?", (officer_id,)).fetchone()
    center_id = officer['assigned_center_id'] if officer and officer['assigned_center_id'] else 1
    center = db.execute("SELECT * FROM procurement_centers WHERE id = ?", (center_id,)).fetchone()
    return center

@officer_bp.route('/dashboard')
@officer_required
def dashboard():
    """Procurement Officer Dashboard."""
    officer_id = session['user_id']
    center = get_officer_center(officer_id)
    center_id = center['id'] if center else 1

    db = get_db()
    today = datetime.date.today().isoformat()

    # Metric counts
    today_bookings = db.execute("""
        SELECT COUNT(*) FROM tokens t
        JOIN slots s ON t.slot_id = s.id
        WHERE t.procurement_center_id = ? AND s.slot_date = ?
    """, (center_id, today)).fetchone()[0]

    waiting_count = db.execute("""
        SELECT COUNT(*) FROM tokens t
        JOIN slots s ON t.slot_id = s.id
        WHERE t.procurement_center_id = ? AND s.slot_date = ? AND t.status IN ('Booked', 'Waiting')
    """, (center_id, today)).fetchone()[0]

    processing_count = db.execute("""
        SELECT COUNT(*) FROM tokens t
        JOIN slots s ON t.slot_id = s.id
        WHERE t.procurement_center_id = ? AND s.slot_date = ? AND t.status = 'Processing'
    """, (center_id, today)).fetchone()[0]

    completed_count = db.execute("""
        SELECT COUNT(*) FROM tokens t
        JOIN slots s ON t.slot_id = s.id
        WHERE t.procurement_center_id = ? AND s.slot_date = ? AND t.status = 'Completed'
    """, (center_id, today)).fetchone()[0]

    # Active queue items
    queue_tokens = db.execute("""
        SELECT t.*, u.full_name AS farmer_name, u.mobile AS farmer_mobile, u.village,
               s.slot_date, s.start_time, s.end_time, p.amount, p.payment_status
        FROM tokens t
        JOIN users u ON t.user_id = u.id
        JOIN slots s ON t.slot_id = s.id
        LEFT JOIN payments p ON p.token_id = t.id
        WHERE t.procurement_center_id = ? AND s.slot_date = ? AND t.status != 'Cancelled'
        ORDER BY CASE 
            WHEN t.status = 'Processing' THEN 1
            WHEN t.status IN ('Booked', 'Waiting') THEN 2
            WHEN t.status = 'Completed' THEN 3
            ELSE 4 END, t.queue_position ASC
    """, (center_id, today)).fetchall()

    return render_template('officer/dashboard.html',
                           center=center,
                           today_bookings=today_bookings,
                           waiting_count=waiting_count,
                           processing_count=processing_count,
                           completed_count=completed_count,
                           queue_tokens=queue_tokens,
                           today=today)

@officer_bp.route('/bookings')
@officer_required
def bookings():
    """View all center bookings."""
    officer_id = session['user_id']
    center = get_officer_center(officer_id)
    center_id = center['id'] if center else 1

    db = get_db()
    selected_date = request.args.get('date', datetime.date.today().isoformat())
    selected_status = request.args.get('status', '').strip()

    query = """
        SELECT t.*, u.full_name AS farmer_name, u.mobile AS farmer_mobile, u.village, u.district,
               s.slot_date, s.start_time, s.end_time, p.amount, p.payment_status
        FROM tokens t
        JOIN users u ON t.user_id = u.id
        JOIN slots s ON t.slot_id = s.id
        LEFT JOIN payments p ON p.token_id = t.id
        WHERE t.procurement_center_id = ?
    """
    params = [center_id]

    if selected_date:
        query += " AND s.slot_date = ?"
        params.append(selected_date)

    if selected_status:
        query += " AND t.status = ?"
        params.append(selected_status)

    query += " ORDER BY s.slot_date DESC, t.queue_position ASC"
    tokens = db.execute(query, params).fetchall()

    return render_template('officer/bookings.html',
                           center=center,
                           tokens=tokens,
                           selected_date=selected_date,
                           selected_status=selected_status)

@officer_bp.route('/queue')
@officer_required
def queue():
    """Live token queue management."""
    officer_id = session['user_id']
    center = get_officer_center(officer_id)
    center_id = center['id'] if center else 1

    db = get_db()
    today = datetime.date.today().isoformat()

    queue_tokens = db.execute("""
        SELECT t.*, u.full_name AS farmer_name, u.mobile AS farmer_mobile, u.village,
               s.slot_date, s.start_time, s.end_time, p.amount, p.payment_status
        FROM tokens t
        JOIN users u ON t.user_id = u.id
        JOIN slots s ON t.slot_id = s.id
        LEFT JOIN payments p ON p.token_id = t.id
        WHERE t.procurement_center_id = ? AND s.slot_date = ?
        ORDER BY CASE 
            WHEN t.status = 'Processing' THEN 1
            WHEN t.status IN ('Booked', 'Waiting') THEN 2
            WHEN t.status = 'Completed' THEN 3
            ELSE 4 END, t.queue_position ASC
    """, (center_id, today)).fetchall()

    return render_template('officer/queue.html',
                           center=center,
                           queue_tokens=queue_tokens,
                           today=today)

@officer_bp.route('/processing/<int:token_id>')
@officer_required
def processing(token_id):
    """Detailed farmer verification and procurement intake form."""
    officer_id = session['user_id']
    center = get_officer_center(officer_id)

    db = get_db()
    token_item = db.execute("""
        SELECT t.*, u.full_name AS farmer_name, u.mobile AS farmer_mobile, u.village, u.district, u.state,
               s.slot_date, s.start_time, s.end_time, p.amount, p.payment_status, p.transaction_reference, p.paid_at
        FROM tokens t
        JOIN users u ON t.user_id = u.id
        JOIN slots s ON t.slot_id = s.id
        LEFT JOIN payments p ON p.token_id = t.id
        WHERE t.id = ? AND t.procurement_center_id = ?
    """, (token_id, center['id'])).fetchone()

    if not token_item:
        flash("Token not found or not assigned to your center.", "danger")
        return redirect(url_for('officer.queue'))

    return render_template('officer/processing.html', center=center, token=token_item)

@officer_bp.route('/token/<int:token_id>/update-status', methods=['POST'])
@officer_required
def update_token_status(token_id):
    """Update token status (Waiting -> Processing -> Completed)."""
    new_status = request.form.get('status', '').strip()
    if new_status not in ['Booked', 'Waiting', 'Processing', 'Completed', 'Cancelled']:
        flash("Invalid status specified.", "danger")
        return redirect(request.referrer or url_for('officer.queue'))

    officer_id = session['user_id']
    center = get_officer_center(officer_id)
    db = get_db()

    token_item = db.execute("SELECT * FROM tokens WHERE id = ? AND procurement_center_id = ?", (token_id, center['id'])).fetchone()
    if not token_item:
        flash("Token not found or unauthorized.", "danger")
        return redirect(url_for('officer.queue'))

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if new_status == 'Completed':
        # Generate demo transaction reference and mark payment completed
        txn_ref = f"TXN-KS-{datetime.datetime.now().strftime('%Y%m%d%H%M')}-{token_id:04d}"
        db.execute("""
            UPDATE tokens 
            SET status = 'Completed', updated_at = ? 
            WHERE id = ?
        """, (now, token_id))

        db.execute("""
            UPDATE payments 
            SET payment_status = 'Payment Done', transaction_reference = ?, paid_at = ? 
            WHERE token_id = ?
        """, (txn_ref, now, token_id))

        db.execute("""
            INSERT INTO notifications (user_id, message, notification_type)
            VALUES (?, ?, 'success')
        """, (token_item['user_id'], f"Procurement completed! Token {token_item['token_number']} processed. Payment Ref: {txn_ref}"))
        flash(f"Token {token_item['token_number']} marked as Completed! Payment marked as Payment Done.", "success")
    else:
        db.execute("""
            UPDATE tokens 
            SET status = ?, updated_at = ? 
            WHERE id = ?
        """, (new_status, now, token_id))

        db.execute("""
            INSERT INTO notifications (user_id, message, notification_type)
            VALUES (?, ?, 'info')
        """, (token_item['user_id'], f"Status for token {token_item['token_number']} updated to {new_status}."))
        flash(f"Token {token_item['token_number']} updated to {new_status}.", "success")

    db.commit()
    return redirect(request.referrer or url_for('officer.queue'))
