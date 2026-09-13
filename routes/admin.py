from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_db
from utils.auth import admin_required
import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin Dashboard with system-wide KPI metrics."""
    db = get_db()
    today = datetime.date.today().isoformat()

    total_farmers = db.execute("SELECT COUNT(*) FROM users WHERE role = 'Farmer'").fetchone()[0]
    total_officers = db.execute("SELECT COUNT(*) FROM users WHERE role = 'Procurement Officer'").fetchone()[0]
    total_centers = db.execute("SELECT COUNT(*) FROM procurement_centers").fetchone()[0]
    today_slots = db.execute("SELECT COUNT(*) FROM slots WHERE slot_date = ?", (today,)).fetchone()[0]

    waiting_tokens = db.execute("SELECT COUNT(*) FROM tokens WHERE status IN ('Booked', 'Waiting')").fetchone()[0]
    processing_tokens = db.execute("SELECT COUNT(*) FROM tokens WHERE status = 'Processing'").fetchone()[0]
    completed_tokens = db.execute("SELECT COUNT(*) FROM tokens WHERE status = 'Completed'").fetchone()[0]
    payments_done = db.execute("SELECT COUNT(*) FROM payments WHERE payment_status = 'Payment Done'").fetchone()[0]
    total_disbursed = db.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payment_status = 'Payment Done'").fetchone()[0]

    # Recent activity
    recent_tokens = db.execute("""
        SELECT t.*, u.full_name AS farmer_name, pc.name AS center_name, p.payment_status, p.amount
        FROM tokens t
        JOIN users u ON t.user_id = u.id
        JOIN procurement_centers pc ON t.procurement_center_id = pc.id
        LEFT JOIN payments p ON p.token_id = t.id
        ORDER BY t.created_at DESC LIMIT 8
    """).fetchall()

    return render_template('admin/dashboard.html',
                           total_farmers=total_farmers,
                           total_officers=total_officers,
                           total_centers=total_centers,
                           today_slots=today_slots,
                           waiting_tokens=waiting_tokens,
                           processing_tokens=processing_tokens,
                           completed_tokens=completed_tokens,
                           payments_done=payments_done,
                           total_disbursed=total_disbursed,
                           recent_tokens=recent_tokens)

@admin_bp.route('/farmers')
@admin_required
def farmers():
    """Directory of registered farmers."""
    db = get_db()
    farmers_list = db.execute("""
        SELECT u.*, 
               (SELECT COUNT(*) FROM tokens WHERE user_id = u.id) AS total_tokens,
               (SELECT COUNT(*) FROM tokens WHERE user_id = u.id AND status = 'Completed') AS completed_tokens
        FROM users u
        WHERE u.role = 'Farmer'
        ORDER BY u.created_at DESC
    """).fetchall()

    return render_template('admin/farmers.html', farmers=farmers_list)

@admin_bp.route('/officers')
@admin_required
def officers():
    """Directory of procurement officers."""
    db = get_db()
    officers_list = db.execute("""
        SELECT u.*, pc.name AS center_name
        FROM users u
        LEFT JOIN procurement_centers pc ON u.assigned_center_id = pc.id
        WHERE u.role = 'Procurement Officer'
        ORDER BY u.created_at DESC
    """).fetchall()

    centers = db.execute("SELECT id, name FROM procurement_centers WHERE status = 'Active' ORDER BY name ASC").fetchall()
    return render_template('admin/officers.html', officers=officers_list, centers=centers)

@admin_bp.route('/centers', methods=['GET', 'POST'])
@admin_required
def centers():
    """Manage procurement centers."""
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        location = request.form.get('location', '').strip()
        district = request.form.get('district', '').strip()
        state = request.form.get('state', '').strip()
        contact = request.form.get('contact', '').strip()
        opening_time = request.form.get('opening_time', '08:00 AM').strip()
        closing_time = request.form.get('closing_time', '05:00 PM').strip()
        status = request.form.get('status', 'Active').strip()

        try:
            lat = float(request.form.get('latitude', 16.8142))
            lng = float(request.form.get('longitude', 81.5268))
        except (ValueError, TypeError):
            lat, lng = 16.8142, 81.5268

        if not name or not location or not district or not state or not contact:
            flash("All mandatory fields must be filled.", "danger")
        else:
            db.execute("""
                INSERT INTO procurement_centers (name, location, district, state, latitude, longitude, contact, opening_time, closing_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, location, district, state, lat, lng, contact, opening_time, closing_time, status))
            db.commit()
            flash(f"Procurement Center '{name}' added successfully!", "success")
        return redirect(url_for('admin.centers'))

    centers_list = db.execute("""
        SELECT pc.*, 
               (SELECT COUNT(*) FROM slots WHERE procurement_center_id = pc.id) AS total_slots,
               (SELECT COUNT(*) FROM tokens WHERE procurement_center_id = pc.id) AS total_tokens
        FROM procurement_centers pc
        ORDER BY pc.name ASC
    """).fetchall()

    return render_template('admin/centers.html', centers=centers_list)

@admin_bp.route('/centers/<int:center_id>/edit', methods=['POST'])
@admin_required
def edit_center(center_id):
    """Edit existing procurement center."""
    db = get_db()
    name = request.form.get('name', '').strip()
    location = request.form.get('location', '').strip()
    district = request.form.get('district', '').strip()
    state = request.form.get('state', '').strip()
    contact = request.form.get('contact', '').strip()
    opening_time = request.form.get('opening_time', '08:00 AM').strip()
    closing_time = request.form.get('closing_time', '05:00 PM').strip()
    status = request.form.get('status', 'Active').strip()

    try:
        lat = float(request.form.get('latitude', 16.8142))
        lng = float(request.form.get('longitude', 81.5268))
    except (ValueError, TypeError):
        lat, lng = 16.8142, 81.5268

    db.execute("""
        UPDATE procurement_centers
        SET name = ?, location = ?, district = ?, state = ?, latitude = ?, longitude = ?, contact = ?, opening_time = ?, closing_time = ?, status = ?
        WHERE id = ?
    """, (name, location, district, state, lat, lng, contact, opening_time, closing_time, status, center_id))
    db.commit()
    flash("Procurement Center updated successfully.", "success")
    return redirect(url_for('admin.centers'))

@admin_bp.route('/slots', methods=['GET', 'POST'])
@admin_required
def slots():
    """Manage time slots for centers."""
    db = get_db()
    if request.method == 'POST':
        center_id = request.form.get('procurement_center_id', type=int)
        slot_date = request.form.get('slot_date', '').strip()
        start_time = request.form.get('start_time', '').strip()
        end_time = request.form.get('end_time', '').strip()
        max_capacity = request.form.get('max_capacity', type=int) or 20

        if not center_id or not slot_date or not start_time or not end_time:
            flash("Please specify center, date, start time, and end time.", "danger")
        else:
            # Check duplicate slot
            dup = db.execute("""
                SELECT id FROM slots WHERE procurement_center_id = ? AND slot_date = ? AND start_time = ?
            """, (center_id, slot_date, start_time)).fetchone()
            if dup:
                flash("A slot for this center, date, and start time already exists.", "warning")
            else:
                db.execute("""
                    INSERT INTO slots (procurement_center_id, slot_date, start_time, end_time, max_capacity, booked_count, status)
                    VALUES (?, ?, ?, ?, ?, 0, 'Available')
                """, (center_id, slot_date, start_time, end_time, max_capacity))
                db.commit()
                flash("Slot created successfully!", "success")
        return redirect(url_for('admin.slots'))

    centers = db.execute("SELECT id, name FROM procurement_centers WHERE status = 'Active' ORDER BY name ASC").fetchall()
    
    selected_center = request.args.get('center_id', type=int)
    selected_date = request.args.get('date', '').strip()

    query = """
        SELECT s.*, pc.name AS center_name, (s.max_capacity - s.booked_count) AS available_capacity
        FROM slots s
        JOIN procurement_centers pc ON s.procurement_center_id = pc.id
        WHERE 1=1
    """
    params = []
    if selected_center:
        query += " AND s.procurement_center_id = ?"
        params.append(selected_center)
    if selected_date:
        query += " AND s.slot_date = ?"
        params.append(selected_date)

    query += " ORDER BY s.slot_date DESC, s.start_time ASC LIMIT 100"
    slots_list = db.execute(query, params).fetchall()

    return render_template('admin/slots.html', slots=slots_list, centers=centers, selected_center=selected_center, selected_date=selected_date)

@admin_bp.route('/queue')
@admin_required
def queue():
    """Global queue and token lifecycle management."""
    db = get_db()
    selected_center = request.args.get('center_id', type=int)
    selected_status = request.args.get('status', '').strip()

    query = """
        SELECT t.*, u.full_name AS farmer_name, u.mobile AS farmer_mobile,
               pc.name AS center_name, s.slot_date, s.start_time, s.end_time,
               p.amount, p.payment_status, p.transaction_reference
        FROM tokens t
        JOIN users u ON t.user_id = u.id
        JOIN procurement_centers pc ON t.procurement_center_id = pc.id
        JOIN slots s ON t.slot_id = s.id
        LEFT JOIN payments p ON p.token_id = t.id
        WHERE 1=1
    """
    params = []
    if selected_center:
        query += " AND t.procurement_center_id = ?"
        params.append(selected_center)
    if selected_status:
        query += " AND t.status = ?"
        params.append(selected_status)

    query += " ORDER BY t.created_at DESC LIMIT 100"
    tokens_list = db.execute(query, params).fetchall()
    centers = db.execute("SELECT id, name FROM procurement_centers ORDER BY name ASC").fetchall()

    return render_template('admin/queue.html', tokens=tokens_list, centers=centers, selected_center=selected_center, selected_status=selected_status)

@admin_bp.route('/token/<int:token_id>/update-status', methods=['POST'])
@admin_required
def update_token_status(token_id):
    """Admin token status update."""
    new_status = request.form.get('status', '').strip()
    if new_status not in ['Booked', 'Waiting', 'Processing', 'Completed', 'Cancelled']:
        flash("Invalid status specified.", "danger")
        return redirect(request.referrer or url_for('admin.queue'))

    db = get_db()
    token_item = db.execute("SELECT * FROM tokens WHERE id = ?", (token_id,)).fetchone()
    if not token_item:
        flash("Token not found.", "danger")
        return redirect(url_for('admin.queue'))

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if new_status == 'Completed':
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
        """, (token_item['user_id'], f"Token {token_item['token_number']} marked Completed by Admin. Payment Reference: {txn_ref}"))
        flash(f"Token {token_item['token_number']} marked Completed. Payment updated to Payment Done.", "success")
    else:
        db.execute("UPDATE tokens SET status = ?, updated_at = ? WHERE id = ?", (new_status, now, token_id))
        flash(f"Token {token_item['token_number']} status changed to {new_status}.", "success")

    db.commit()
    return redirect(request.referrer or url_for('admin.queue'))

@admin_bp.route('/reports')
@admin_required
def reports():
    """Procurement and DBT payment reports."""
    db = get_db()

    # Center-wise procurement breakdown
    center_stats = db.execute("""
        SELECT pc.name, pc.district,
               COUNT(t.id) AS total_tokens,
               SUM(CASE WHEN t.status = 'Completed' THEN 1 ELSE 0 END) AS completed_tokens,
               SUM(CASE WHEN t.status IN ('Booked', 'Waiting') THEN 1 ELSE 0 END) AS pending_tokens,
               COALESCE(SUM(CASE WHEN p.payment_status = 'Payment Done' THEN p.amount ELSE 0 END), 0) AS total_disbursed,
               COALESCE(SUM(t.estimated_quantity_quintals), 0) AS total_quintals
        FROM procurement_centers pc
        LEFT JOIN tokens t ON t.procurement_center_id = pc.id
        LEFT JOIN payments p ON p.token_id = t.id
        GROUP BY pc.id
        ORDER BY total_tokens DESC
    """).fetchall()

    # Status distribution
    status_distribution = db.execute("""
        SELECT status, COUNT(*) AS count 
        FROM tokens 
        GROUP BY status
    """).fetchall()

    # Payment summary
    payment_summary = db.execute("""
        SELECT payment_status, COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total_amount
        FROM payments
        GROUP BY payment_status
    """).fetchall()

    return render_template('admin/reports.html',
                           center_stats=center_stats,
                           status_distribution=status_distribution,
                           payment_summary=payment_summary)
