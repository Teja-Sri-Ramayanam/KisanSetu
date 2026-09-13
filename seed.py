import sqlite3
import datetime
from database import get_standalone_db, init_db
from utils.auth import hash_password

def seed_database():
    """Seed demo accounts, procurement centers, slots, and sample tokens."""
    init_db()
    conn = get_standalone_db()
    cursor = conn.cursor()

    print("[*] Initializing and seeding Kisan Setu database...")

    # 1. Procurement Centers
    centers = [
        (1, "Tadepalligudem Procurement Center", "Agricultural Market Yard, Near Railway Gate, Tadepalligudem", "West Godavari", "Andhra Pradesh", 16.8142, 81.5268, "08818-223344", "08:00 AM", "05:00 PM", "Active"),
        (2, "Tanuku Procurement Center", "Agricultural Market Committee, Velpur Road, Tanuku", "West Godavari", "Andhra Pradesh", 16.7565, 81.6811, "08819-224455", "08:00 AM", "05:00 PM", "Active"),
        (3, "Bhimavaram Procurement Center", "Civil Supplies Godown, Somaram Road, Bhimavaram", "West Godavari", "Andhra Pradesh", 16.5449, 81.5212, "08816-225566", "08:00 AM", "05:00 PM", "Active")
    ]

    for c in centers:
        cursor.execute("""
            INSERT INTO procurement_centers (id, name, location, district, state, latitude, longitude, contact, opening_time, closing_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                location=excluded.location,
                district=excluded.district,
                state=excluded.state,
                contact=excluded.contact
        """, c)
    print("  [OK] Procurement Centers seeded (Tadepalligudem, Tanuku, Bhimavaram).")

    # 2. Users
    users = [
        # Admin
        ("Super Admin", "9876543210", "admin@kisansetu.com", hash_password("admin123"), "Collectorate Complex", "West Godavari", "Andhra Pradesh", "Admin", None),
        # Officer (Assigned to Center 1 - Tadepalligudem)
        ("Srinivasa Rao", "9440112233", "officer@kisansetu.com", hash_password("officer123"), "Tadepalligudem Urban", "West Godavari", "Andhra Pradesh", "Procurement Officer", 1),
        # Sample Officer 2 (Tanuku)
        ("Murali Krishna", "9440114455", "officer.tanuku@kisansetu.com", hash_password("officer123"), "Tanuku Urban", "West Godavari", "Andhra Pradesh", "Procurement Officer", 2),
        # Demo Farmer
        ("Ramesh Babu", "9848022338", "farmer@example.com", hash_password("farmer123"), "Pentapadu", "West Godavari", "Andhra Pradesh", "Farmer", None),
        # Extra Farmers for sample queue
        ("Venkatesh Naidu", "9848011223", "venkatesh@example.com", hash_password("farmer123"), "Prathipadu", "West Godavari", "Andhra Pradesh", "Farmer", None),
        ("Appa Rao", "9848033445", "apparao@example.com", hash_password("farmer123"), "Maruteru", "West Godavari", "Andhra Pradesh", "Farmer", None),
        ("Kishore Varma", "9848055667", "kishore@example.com", hash_password("farmer123"), "Undi", "West Godavari", "Andhra Pradesh", "Farmer", None)
    ]

    for u in users:
        cursor.execute("""
            INSERT INTO users (full_name, mobile, email, password_hash, village, district, state, role, assigned_center_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                full_name=excluded.full_name,
                password_hash=excluded.password_hash,
                role=excluded.role,
                assigned_center_id=excluded.assigned_center_id
        """, u)
    print("  [OK] Demo Accounts seeded (Admin, Officers, Farmers).")

    # 3. Slots for Today and Next 5 Days
    today = datetime.date.today()
    slot_times = [
        ("08:30 AM", "10:30 AM", 25),
        ("10:30 AM", "12:30 PM", 25),
        ("01:30 PM", "03:30 PM", 25),
        ("03:30 PM", "05:00 PM", 20)
    ]

    for day_offset in range(6):
        s_date = (today + datetime.timedelta(days=day_offset)).isoformat()
        for center_id in [1, 2, 3]:
            for st, et, cap in slot_times:
                cursor.execute("""
                    SELECT id FROM slots 
                    WHERE procurement_center_id = ? AND slot_date = ? AND start_time = ?
                """, (center_id, s_date, st))
                existing = cursor.fetchone()
                if not existing:
                    cursor.execute("""
                        INSERT INTO slots (procurement_center_id, slot_date, start_time, end_time, max_capacity, booked_count, status)
                        VALUES (?, ?, ?, ?, ?, 0, 'Available')
                    """, (center_id, s_date, st, et, cap))

    print("  [OK] Slots generated for all centers for the upcoming week.")

    # 4. Create sample tokens for other farmers to make queue realistic
    # Let's find today's morning slot at Tadepalligudem (Center 1)
    today_str = today.isoformat()
    cursor.execute("""
        SELECT id FROM slots 
        WHERE procurement_center_id = 1 AND slot_date = ? 
        ORDER BY start_time ASC LIMIT 1
    """, (today_str,))
    today_slot = cursor.fetchone()

    if today_slot:
        slot_id = today_slot[0]
        # Get extra farmers
        cursor.execute("SELECT id, full_name FROM users WHERE email IN ('venkatesh@example.com', 'apparao@example.com') ORDER BY id ASC")
        extra_farmers = cursor.fetchall()
        
        sample_tokens = [
            ("KS-10001", extra_farmers[0][0], slot_id, 1, "Paddy (Grade A)", 45.0, 1, "Processing", 45000.0, "Pending", None, None),
            ("KS-10002", extra_farmers[1][0], slot_id, 1, "Paddy (Common)", 60.0, 2, "Waiting", 60000.0, "Pending", None, None)
        ]

        for tok_num, uid, s_id, c_id, crop, qty, q_pos, status, amt, pay_stat, txn, paid_date in sample_tokens:
            cursor.execute("SELECT id FROM tokens WHERE token_number = ?", (tok_num,))
            tok_exists = cursor.fetchone()
            if not tok_exists:
                cursor.execute("""
                    INSERT INTO tokens (token_number, user_id, slot_id, procurement_center_id, crop_type, estimated_quantity_quintals, queue_position, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (tok_num, uid, s_id, c_id, crop, qty, q_pos, status))
                new_tok_id = cursor.lastrowid

                # Update booked count on slot
                cursor.execute("UPDATE slots SET booked_count = booked_count + 1 WHERE id = ?", (s_id,))

                # Insert payment
                cursor.execute("""
                    INSERT INTO payments (token_id, user_id, amount, payment_status, transaction_reference, paid_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (new_tok_id, uid, amt, pay_stat, txn, paid_date))

                # Insert notification
                cursor.execute("""
                    INSERT INTO notifications (user_id, message, notification_type)
                    VALUES (?, ?, 'info')
                """, (uid, f"Digital Token {tok_num} confirmed for {today_str}."))

        print("  [OK] Sample active tokens created in queue (Positions 1 & 2).")

    conn.commit()
    conn.close()
    print("[OK] Kisan Setu database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
