# KISAN SETU (किसान सेतु)
### Smart Procurement Slot & Digital Token Management System for Farmers

[![Python](https://img.shields.io/badge/Python-3.10%2B-2e7d32.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-4caf50.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-1b5e20.svg)](https://www.sqlite.org/)
[![Bootstrap](https://img.shields.io/badge/UI-Bootstrap%205-0d6efd.svg)](https://getbootstrap.com/)
[![License](https://img.shields.io/badge/License-MIT-f59e0b.svg)](LICENSE)

---

## 1. Project Introduction
**KISAN SETU** is a full-stack digital web portal engineered for agricultural produce procurement mandis and government centers. Built specifically for Indian farmers and procurement agencies, Kisan Setu bridges the gap between rural farmers and government minimum support price (MSP) procurement operations by transforming chaotic physical queueing into an organized, transparent digital slot reservation and token dispensation system.

---

## 2. Problem Statement
In traditional agricultural procurement centers (mandis):
- **Excessive Physical Waiting:** Farmers queue with loaded tractor trolleys for 8 to 16 hours under harsh weather conditions.
- **Traffic Congestion & Spoilage:** Unscheduled mandi traffic jams cause grain loss, grain moisture degradation, and localized chaos.
- **Opacity & Middlemen:** Lack of scheduled time slots allows informal queue jumping and exploitation of smallholder farmers.
- **Payment Uncertainty:** Unclear tracking between physical produce weighment and Direct Benefit Transfer (DBT) disbursals.

---

## 3. The Kisan Setu Solution
**"Book your slot. Get your digital token. Skip the long queue."**

Kisan Setu solves mandi congestion through a 4-pillar digital workflow:
1. **Capacity-Controlled Time Slots:** Centers publish slots with strict capacity caps, preventing overbooking via atomic database transactions.
2. **QR-Ready Digital Tokens:** Farmers receive an official digital pass (`KS-XXXXX`) containing their exact queue number, center location, and scheduled window.
3. **Live Queue Tracking:** Real-time queue monitor with transparent estimated waiting time (`5 minutes × number of people ahead`).
4. **End-to-End DBT Transparency:** When procurement officers inspect and complete grain intake, payment records transition directly to `Payment Done` with unique audit references.

---

## 4. Key Features
- **Three User Roles:** Farmer, Procurement Officer, and Administrator with server-enforced role authentication.
- **Visible HOME Button:** Every single page and dashboard contains a persistent, prominent Home button redirecting to `/`.
- **Dynamic Role-Based Registration:** Real-time form toggling for Village, Assigned Mandi, and Security Key.
- **Printable Digital Tokens:** High-contrast `@media print` layout styled as an official government e-Pass.
- **Live Queue Calculator:** Dynamic calculation of farmers ahead and estimated waiting times.
- **Google Maps Integration:** Direct GPS directions link to procurement depots without requiring third-party API keys.
- **6-Step Progress Pipeline:** Visual step wizard tracking produce from booking to bank transfer.
- **Mandi Officer Intake Desk:** Grain moisture, quality grading (FAQ/Grade A), and weighbridge recording.
- **Central Admin Command:** CRUD operations for centers and slots, queue overrides, and procurement analytics.

---

## 5. Technology Stack
- **Frontend:** HTML5, CSS3 (Custom Agriculture Theme), Vanilla JavaScript, Bootstrap 5.3.3, Bootstrap Icons 1.11.3.
- **Backend:** Python 3.10+, Flask 3.1, Werkzeug password security, Flask Session authentication.
- **Database:** SQLite3 with foreign key enforcement (`PRAGMA foreign_keys = ON`) and indexing.
- **Architecture:** Modular Flask Blueprints (`auth`, `farmer`, `officer`, `admin`, `api`).

---

## 6. Folder Structure
```text
KisanSetu/
│
├── app.py                     # Flask application factory and entry point
├── config.py                  # App configuration and environment fallbacks
├── database.py                # SQLite connection helpers and table schemas
├── seed.py                    # Database seeder for demo accounts, centers & slots
├── test_app.py                # Automated integration and workflow test suite
├── requirements.txt           # Python package dependencies
├── README.md                  # Detailed documentation and beginner guide
├── .gitignore                 # Git ignore rules
├── kisan_setu.db              # SQLite database (auto-generated)
│
├── routes/
│   ├── __init__.py
│   ├── auth.py                # Landing, Login, Registration, Profile, Logout
│   ├── farmer.py              # Farmer views (Schedule, Token, Queue, Status, Payment)
│   ├── officer.py             # Officer views (Dashboard, Bookings, Queue, Processing)
│   ├── admin.py               # Admin views (Centers, Slots, Queue, Reports)
│   └── api.py                 # REST API endpoints (JSON responses)
│
├── utils/
│   ├── __init__.py
│   └── auth.py                # Password hashing, role decorators, session guards
│
├── static/
│   ├── css/
│   │   └── style.css          # Agriculture design palette, print CSS, steppers
│   ├── js/
│   │   ├── main.js            # Toast notifications and modal utilities
│   │   ├── auth.js            # Dynamic role toggler and form validation
│   │   ├── farmer.js          # Slot modal, fetch API booking, live queue poller
│   │   ├── officer.js         # Status updater and quick transition actions
│   │   └── admin.js           # Center/Slot modal handlers and queue controls
│   └── images/
│       ├── logo.svg           # Scalable agriculture brand emblem
│       └── logo.png           # Raster brand logo
│
└── templates/
    ├── base.html              # Core layout, role-based navbar, universal Home button
    ├── index.html             # Landing page with hero, problem/solution & stats
    ├── login.html             # Role-selection login card
    ├── register.html          # Dynamic multi-role registration form
    ├── profile.html           # User profile and notifications
    ├── 404.html               # Themed Not Found error page
    ├── 500.html               # Themed Server Error page
    │
    ├── farmer/
    │   ├── dashboard.html     # Farmer control center & quick actions
    │   ├── schedule.html      # Filterable slots with real-time capacity
    │   ├── token.html         # Digital Token pass with print styling
    │   ├── queue.html         # Live queue position and 5-min/person estimate
    │   ├── centers.html       # Center directories with Google Maps directions
    │   ├── status.html        # 6-step progress pipeline tracker
    │   └── payment.html       # Direct Benefit Transfer (DBT) receipt
    │
    ├── officer/
    │   ├── dashboard.html     # Today's queue counters and quick actions
    │   ├── bookings.html      # Center bookings filterable by date and status
    │   ├── queue.html         # Real-time queue board (Waiting -> Processing -> Done)
    │   └── processing.html    # Quality check, weighment & intake form
    │
    └── admin/
        ├── dashboard.html     # Central KPI dashboard & recent activities
        ├── farmers.html       # Farmers directory
        ├── officers.html      # Procurement officers directory
        ├── centers.html       # Centers CRUD management
        ├── slots.html         # Slot generation and capacity manager
        ├── queue.html         # System-wide queue override panel
        └── reports.html       # Procurement volume and payment disbursal metrics
```

---

## 7. Python Installation
Ensure Python 3.10 or higher is installed on your system.
Verify from your terminal or Command Prompt:
```bash
python --version
```

---

## 8. Virtual Environment Setup
Open a terminal in the `KisanSetu` project folder:

**Windows (Command Prompt / PowerShell):**
```powershell
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 9. Dependency Installation
Install Flask and Werkzeug using `pip`:
```bash
pip install -r requirements.txt
```

---

## 10. Database Initialization
The database `kisan_setu.db` will be initialized automatically when running `app.py`. To explicitly create tables and performance indexes, run:
```bash
python -c "from database import init_db; init_db()"
```

---

## 11. Seed Data Setup
Run the idempotent database seeder to generate demo centers, slots, and demo accounts:
```bash
python seed.py
```
This populates:
- 3 Procurement Centers (Tadepalligudem, Tanuku, Bhimavaram).
- Demo Farmer, Officer, and Admin accounts.
- Daily time slots for today and the upcoming week.
- Sample queue items.

---

## 12. How to Run Flask
Start the web application:
```bash
python app.py
```

---

## 13. Browser URL
Open your web browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 14. Demo Credentials
| Role | Email | Password | Assigned Location / Note |
| :--- | :--- | :--- | :--- |
| **Farmer** | `farmer@example.com` | `farmer123` | Pentapadu, West Godavari |
| **Procurement Officer** | `officer@kisansetu.com` | `officer123` | Tadepalligudem Procurement Center |
| **Procurement Officer (Tanuku)** | `officer.tanuku@kisansetu.com` | `officer123` | Tanuku Procurement Center |
| **Administrator** | `admin@kisansetu.com` | `admin123` | Master Command (Key: `KISAN_ADMIN_2026`) |

---

## 15. Farmer Demo Flow
1. Navigate to `http://127.0.0.1:5000/`.
2. Click **Register** &rarr; Select **Farmer**. Fill in details and click **Complete Registration**.
3. Sign in at `/login` as **Farmer** (`farmer@example.com` / `farmer123`).
4. On the **Farmer Dashboard**, click **Select Slot** or **View Schedule**.
5. Choose a convenient time slot and click **Select Slot**.
6. Review the confirmation modal (Center, Date, Time, Estimated Load) and click **Confirm & Generate Token**.
7. View your newly generated **Digital Token** (`KS-XXXXX`). Click **Print Token** to see the clean printable pass.
8. Click **Track Queue** to view your position, people ahead, and the estimated waiting time (`5 minutes × people ahead`).
9. Click **Status** to follow the visual step-by-step progress pipeline.

---

## 16. Procurement Officer Demo Flow
1. Click **Logout**, then sign in as **Procurement Officer** (`officer@kisansetu.com` / `officer123`).
2. The **Officer Dashboard** displays today's metrics (Waiting, Processing, Completed) for the assigned center.
3. Click **Today's Queue** (`/officer/queue`).
4. Find the newly queued farmer token.
5. Click **Start Processing** to move the token from `Waiting` &rarr; `Processing`.
6. Click the inspection eye icon to open `/officer/processing/<token_id>`. Verify moisture and quality grade.
7. Click **Complete Procurement & Issue Payment**.
8. The token status becomes `Completed`, and payment automatically transitions to `Payment Done` with an audit transaction reference (`TXN-KS-...`).

---

## 17. Admin Demo Flow
1. Sign in as **Admin** (`admin@kisansetu.com` / `admin123`).
2. Review system-wide metrics on `/admin/dashboard` (Farmers, Officers, Mandis, Slots, Disbursed Funds).
3. Access `/admin/centers` to add or edit procurement center details.
4. Access `/admin/slots` to generate intake slots for any center.
5. Access `/admin/queue` to monitor or override any token across all mandis.
6. Access `/admin/reports` to inspect procurement summaries, volume, and DBT payment logs.

---

## 18. REST API Reference
All REST API endpoints accept and return JSON with the consistent structure:
```json
{
    "success": true,
    "message": "Operation completed successfully",
    "data": {}
}
```

### Authentication APIs
- `POST /api/register` &ndash; Register user with dynamic role validation.
- `POST /api/login` &ndash; Sign in with server-side role validation.
- `POST /api/logout` &ndash; Terminate active Flask session.
- `GET /api/profile` &ndash; Fetch current authenticated user profile.

### Farmer APIs
- `GET /api/farmer/dashboard` &ndash; Farmer overview and active token snapshot.
- `GET /api/slots` &ndash; Query available slots filtered by `center_id` or `date`.
- `GET /api/procurement-centers` &ndash; List all active procurement depots.
- `POST /api/slots/<slot_id>/book` &ndash; Atomic slot booking and token generation.
- `GET /api/my-token` &ndash; Fetch active farmer digital token.
- `GET /api/queue/<token_id>` &ndash; Real-time queue details, people ahead, and waiting estimate.
- `GET /api/status/<token_id>` &ndash; Detailed 6-step progress state.
- `GET /api/payments/<token_id>` &ndash; Direct Benefit Transfer receipt information.

### Procurement Officer APIs
- `GET /api/officer/dashboard` &ndash; Today's depot metrics.
- `GET /api/officer/bookings` &ndash; All bookings for the officer's assigned mandi.
- `GET /api/officer/queue` &ndash; Today's queue stream.
- `GET /api/officer/farmer/<user_id>` &ndash; Farmer KYC details.
- `PUT /api/officer/tokens/<token_id>/status` &ndash; Update token status (`Processing` / `Waiting`).
- `POST /api/officer/tokens/<token_id>/complete` &ndash; Finalize procurement and trigger `Payment Done`.

### Admin APIs
- `GET /api/admin/dashboard` &ndash; Central platform metrics.
- `GET /api/admin/farmers` &ndash; Registered farmers list.
- `GET /api/admin/officers` &ndash; Mandi officers list.
- `GET /api/admin/centers` &ndash; List procurement centers.
- `POST /api/admin/centers` &ndash; Create new procurement center.
- `PUT /api/admin/centers/<center_id>` &ndash; Edit existing center.
- `GET /api/admin/slots` &ndash; List slots across mandis.
- `POST /api/admin/slots` &ndash; Allocate new procurement slot.
- `GET /api/admin/tokens` &ndash; Global token directory.
- `PUT /api/admin/tokens/<token_id>/status` &ndash; Status override.
- `GET /api/admin/reports` &ndash; Financial and procurement analytics.

---

## 19. Common Errors and Fixes
1. **`Invalid role selected for this account.`**
   - *Fix:* Ensure the role card selected on the login page matches the role assigned to that email. A Farmer cannot log in as an Officer or Admin.
2. **`Only one active token is permitted at a time.`**
   - *Fix:* Farmers can have one active booking in progress. Once the procurement is marked `Completed` by an Officer or Admin, a new slot can be booked.
3. **`Slot is fully booked.`**
   - *Fix:* The slot has reached its maximum capacity. Select another available time window.
4. **`Invalid Admin Registration Key.`**
   - *Fix:* Use the demo admin key: `KISAN_ADMIN_2026`.
5. **Database Locked / Concurrent Access in Tests:**
   - *Fix:* Kisan Setu uses short-lived atomic connections and `PRAGMA foreign_keys = ON;`. Close open database viewers if locked during writes.

---

## 20. Future Improvements
- **Automated SMS & WhatsApp Alerts:** Send token confirmations and queue updates directly via SMS gateway (Twilio / NIC SMS).
- **Weighbridge IoT Integration:** Direct automated weight readings from physical weighbridge scales into the intake portal.
- **Multilingual Support:** Localization into Telugu, Hindi, Tamil, and other regional languages.
- **Offline PWA Support:** Service worker caching for low-connectivity rural mandi areas.
- **Direct Aadhaar / NPCI Integration:** Live bank account verification via DBT Bharat gateway.
