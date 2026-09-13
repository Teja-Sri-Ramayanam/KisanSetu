import unittest
import json
import os
import tempfile
from app import create_app
from database import init_db, get_db
from config import Config

class KisanSetuTestSuite(unittest.TestCase):
    def setUp(self):
        # Setup temporary database for test suite
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app({
            'TESTING': True,
            'DATABASE': self.db_path,
            'SECRET_KEY': 'test-secret-key',
            'WTF_CSRF_ENABLED': False
        })
        self.client = self.app.test_client()

        with self.app.app_context():
            init_db()
            # Seed minimal required entities for tests
            db = get_db()
            # Insert test centers
            db.execute("""
                INSERT INTO procurement_centers (id, name, location, district, state, contact, opening_time, closing_time, status)
                VALUES (1, 'Tadepalligudem Center', 'Market Yard', 'West Godavari', 'Andhra Pradesh', '08818-223344', '08:00 AM', '05:00 PM', 'Active'),
                       (2, 'Tanuku Center', 'Velpur Road', 'West Godavari', 'Andhra Pradesh', '08819-224455', '08:00 AM', '05:00 PM', 'Active')
            """)
            # Insert test slot
            db.execute("""
                INSERT INTO slots (id, procurement_center_id, slot_date, start_time, end_time, max_capacity, booked_count, status)
                VALUES (1, 1, '2026-09-15', '09:00 AM', '11:00 AM', 2, 0, 'Available')
            """)
            db.commit()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_01_homepage_renders(self):
        """Home page should render with HTTP 200, branding, and HOME link."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'KISAN SETU', res.data)
        self.assertIn(b'Skip the long queue', res.data)
        self.assertIn(b'HOME', res.data)

    def test_02_registration_and_role_mismatch(self):
        """Register farmer, test login validation, and role mismatch rejection."""
        # 1. Register Farmer
        reg_data = {
            "role": "Farmer",
            "full_name": "Satyanarayana",
            "mobile": "9848012345",
            "email": "satya@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "village": "Pentapadu",
            "district": "West Godavari",
            "state": "Andhra Pradesh"
        }
        res = self.client.post('/api/register', json=reg_data)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data['success'])

        # 2. Try to login with wrong role (Select Officer for a Farmer account)
        login_wrong_role = {
            "email": "satya@example.com",
            "password": "password123",
            "role": "Procurement Officer"
        }
        res = self.client.post('/api/login', json=login_wrong_role)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Invalid role selected", res.get_json()['message'])

        # 3. Try to login with wrong password
        login_wrong_pwd = {
            "email": "satya@example.com",
            "password": "wrongpassword",
            "role": "Farmer"
        }
        res = self.client.post('/api/login', json=login_wrong_pwd)
        self.assertEqual(res.status_code, 401)

        # 4. Correct login
        login_correct = {
            "email": "satya@example.com",
            "password": "password123",
            "role": "Farmer"
        }
        res = self.client.post('/api/login', json=login_correct)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

    def test_03_role_guards(self):
        """Farmer cannot access Officer or Admin dashboards."""
        # Register and login as Farmer
        self.client.post('/api/register', json={
            "role": "Farmer",
            "full_name": "Farmer Ramu",
            "mobile": "9848011111",
            "email": "ramu@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "district": "West Godavari",
            "state": "Andhra Pradesh"
        })
        self.client.post('/api/login', json={
            "email": "ramu@example.com",
            "password": "password123",
            "role": "Farmer"
        })

        # Farmer tries to access officer dashboard via API -> 403
        res = self.client.get('/api/officer/dashboard')
        self.assertEqual(res.status_code, 403)

        # Farmer tries to access admin dashboard via API -> 403
        res = self.client.get('/api/admin/dashboard')
        self.assertEqual(res.status_code, 403)

        # Farmer tries to access officer web page -> redirect to farmer dashboard
        res = self.client.get('/officer/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/farmer/dashboard', res.headers['Location'])

    def test_04_full_demo_workflow(self):
        """
        Complete end-to-end demo flow:
        Farmer registers -> logs in -> books slot -> gets token & queue ->
        Officer logs in -> changes Waiting to Processing ->
        Admin logs in -> marks Completed -> auto Payment Done with txn ref ->
        Farmer verifies status & payment.
        """
        # Step A: Register Farmer
        self.client.post('/api/register', json={
            "role": "Farmer",
            "full_name": "Babu Rao",
            "mobile": "9848099999",
            "email": "baburao@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "district": "West Godavari",
            "state": "Andhra Pradesh"
        })
        # Login as Farmer
        self.client.post('/api/login', json={
            "email": "baburao@example.com",
            "password": "password123",
            "role": "Farmer"
        })

        # Step B: Book slot #1
        book_res = self.client.post('/api/slots/1/book', json={
            "crop_type": "Paddy (Grade A)",
            "estimated_quantity_quintals": 50.0
        })
        self.assertEqual(book_res.status_code, 201)
        token_data = book_res.get_json()['data']
        token_id = token_data['token_id']
        token_number = token_data['token_number']
        self.assertEqual(token_data['queue_position'], 1)
        self.assertEqual(token_data['status'], 'Waiting')

        # Step C: Farmer checks Queue API
        q_res = self.client.get(f'/api/queue/{token_id}')
        self.assertEqual(q_res.status_code, 200)
        q_data = q_res.get_json()['data']
        self.assertEqual(q_data['people_ahead'], 0)
        self.assertEqual(q_data['estimated_waiting_minutes'], 0) # 5 * 0 = 0
        self.assertEqual(q_data['status'], 'Waiting')

        # Step D: Farmer logs out
        self.client.post('/api/logout')

        # Step E: Register and Login as Procurement Officer
        self.client.post('/api/register', json={
            "role": "Procurement Officer",
            "full_name": "Officer Satish",
            "mobile": "9440112299",
            "email": "satish.officer@kisansetu.com",
            "password": "officerpass123",
            "confirm_password": "officerpass123",
            "assigned_center_id": 1,
            "district": "West Godavari",
            "state": "Andhra Pradesh"
        })
        self.client.post('/api/login', json={
            "email": "satish.officer@kisansetu.com",
            "password": "officerpass123",
            "role": "Procurement Officer"
        })

        # Step F: Officer advances token to 'Processing'
        officer_up_res = self.client.put(f'/api/officer/tokens/{token_id}/status', json={"status": "Processing"})
        self.assertEqual(officer_up_res.status_code, 200)

        # Logout Officer
        self.client.post('/api/logout')

        # Step G: Login as Farmer to verify 'Processing' status
        self.client.post('/api/login', json={
            "email": "baburao@example.com",
            "password": "password123",
            "role": "Farmer"
        })
        tok_res = self.client.get('/api/my-token')
        self.assertEqual(tok_res.get_json()['data']['status'], 'Processing')
        self.client.post('/api/logout')

        # Step H: Register and Login as Admin using key
        self.client.post('/api/register', json={
            "role": "Admin",
            "full_name": "Admin Chief",
            "mobile": "9876543210",
            "email": "adminchief@kisansetu.com",
            "password": "adminpass123",
            "confirm_password": "adminpass123",
            "admin_key": Config.ADMIN_REGISTRATION_KEY,
            "district": "West Godavari",
            "state": "Andhra Pradesh"
        })
        self.client.post('/api/login', json={
            "email": "adminchief@kisansetu.com",
            "password": "adminpass123",
            "role": "Admin"
        })

        # Step I: Admin marks token as 'Completed'
        admin_up_res = self.client.put(f'/api/admin/tokens/{token_id}/status', json={"status": "Completed"})
        self.assertEqual(admin_up_res.status_code, 200)

        # Step J: Verify that payment status is automatically updated to 'Payment Done'
        pay_res = self.client.get(f'/api/payments/{token_id}')
        self.assertEqual(pay_res.status_code, 200)
        pay_data = pay_res.get_json()['data']
        self.assertEqual(pay_data['payment_status'], 'Payment Done')
        self.assertTrue(pay_data['transaction_reference'].startswith('TXN-KS-'))
        self.assertIsNotNone(pay_data['paid_at'])

        self.client.post('/api/logout')

        # Step K: Login again as Farmer and verify finalized state
        self.client.post('/api/login', json={
            "email": "baburao@example.com",
            "password": "password123",
            "role": "Farmer"
        })
        status_page = self.client.get('/farmer/status')
        self.assertEqual(status_page.status_code, 200)
        self.assertIn(b'Procurement Completed', status_page.data)

        pay_page = self.client.get('/farmer/payment')
        self.assertEqual(pay_page.status_code, 200)
        self.assertIn(b'Payment Done', pay_page.data)

if __name__ == '__main__':
    unittest.main()
