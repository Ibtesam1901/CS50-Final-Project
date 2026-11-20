# NeighborGrid · Mohalla Feed (CS50x Final Project)

#### Hyperlocal, Non-Monetary Mutual-Aid Web Platform for Indian Neighborhoods
**Live Production URL:** [https://neighbor-grid.onrender.com/](https://neighbor-grid.onrender.com/)  
**Video Demo:** [https://youtu.be/CS50x-NeighborGrid-Demo](https://youtu.be/CS50x-NeighborGrid-Demo) *(Update with your recording)*

---

## 1. Project Overview & Motivation

In today's urban Indian neighborhoods, apartment complexes, and colonies (*mohallas*), people live in close physical proximity yet often remain socially isolated. When a resident needs a 6-foot ladder for two hours, an impact drill for curtain rods, an urgent O-negative blood donor, or a carpool ride to the metro station, commercial services charge fees, require deposits, or spam feeds with buying/selling advertisements.

**NeighborGrid** is a production-grade, hyperlocal mutual-aid web platform designed to restore community solidarity. It operates on a strict **non-commercial, neighbor-to-neighbor policy**: no buying, selling, renting, or cash exchanges are allowed. Everything shared is through grassroots goodwill.

The platform is designed with an authentic Indian localization (*Mohalla Feed*, *Ghar Ka Samaan*, Bengaluru localities such as Indiranagar, Koramangala, HSR Layout, Jayanagar, and Whitefield), strict privacy protections, real-time geolocation with walking distance calculations, private in-app coordination messaging, star ratings, and community moderation.

---

## 2. Key Features

### A. Non-Commercial Enforcement (Rule #1)
- **Server-Side Commercial Content Filter:** Uses regex and keyword matching on both post creation and post editing.
- Blocks currency symbols (`Rs`, `Rs.`, `₹`, `INR`), selling terms (`selling`, `for sale`, `fixed price`, `COD`, `cash`, `rent per day`, `charge`, `buy`, `discount`), and digital payment terms (`UPI`, `GPay`, `PhonePe`, `Paytm`).
- Any attempt to monetize aid is blocked before hitting the database with a helpful message: *"NeighborGrid is strictly non-commercial. Buying, selling, pricing, or payment language is not permitted."*
- Posts can also be reported by community members for administrator review.

### B. Geolocation, Proximity Engine & Privacy Jitter
- **Live HTML5 Geolocation:** Detects user coordinates upon confirmation.
- **Fail-Safe Locality Selector:** Includes an 8-second timeout fallback with a manual Bengaluru locality dropdown (Indiranagar, Koramangala, HSR Layout, Jayanagar, Whitefield) stored in browser `localStorage`.
- **Haversine Distance Engine:** Computes real-time walking and driving distance in kilometers (`haversine_km`) between the viewer and each post pin.
- **Radius & Proximity Sorting:** The feed supports live radius filtering (within 500m, 1km, 2km, 5km, or any radius) and sorting by *Nearest*, *Urgent First*, or *Newest*.
- **Coordinate Privacy Jitter (~100m):** Exact house coordinates are jittered to 3 decimal places (~100m resolution) before public rendering on maps to protect home privacy.

### C. Post Detail & Actionable Next Steps
- **Prominent Action CTA:** Clearly displays *"I can help / Offer to lend"* for requests, and *"Request this / Ask to borrow"* for offers.
- **Guest Experience:** Unauthenticated visitors see a prominent *"Log in to respond"* button with safe redirect validation (`/login?next=/post/<id>`).
- **Interactive Leaflet Map:** Displays the post's approximate neighborhood location with OpenStreetMap tiles.
- **Poster Reputation Badge:** Displays the poster's completed community acts, average star rating, and review count.
- **WhatsApp Share:** One-click button generates a pre-formatted message with post title and link.
- **Owner Controls:** Post creator can edit, cancel, or permanently delete posts, accept/decline responses, and mark tasks completed.

### D. Privacy-Preserving Mutual Aid Lifecycle
1. **Open:** Post is live on the neighborhood feed and map.
2. **Respond:** Neighbors submit an offer or request with a polite note.
3. **Acceptance & Contact Unlock:** When the post owner accepts an offer:
   - The post transitions to `in_progress`.
   - Contact details (phone number, WhatsApp, email) are **strictly unlocked on the backend** only for the two participating neighbors.
   - An in-app private coordination chat thread is unlocked.
4. **Task Completion & Ratings:** The owner marks the task as completed. Both neighbors can submit a 1-to-5 star rating and written review.
5. **14-Day Expiration & Repost:** Unfilled open posts older than 14 days are marked as expired and can be renewed with a single click (*"Repost"*) on the dashboard.

### E. Security & Data Protection
- **Password Hashing:** Passwords hashed using Werkzeug (`scrypt`).
- **Session & Cookie Security:** `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`, dynamic `SESSION_COOKIE_SECURE` in production.
- **CSRF Defense:** Cryptographic CSRF tokens on all state-altering forms.
- **Open-Redirect Shield:** Safe URL validation prevents open-redirect exploits on login/redirects.
- **Rate Limiting:** Integrated with `Flask-Limiter` to protect auth endpoints and prevent spam.
- **Parameterized SQL:** Every query utilizes parameterized placeholders (`?`) to prevent SQL injection.
- **Custom Error Pages:** Dedicated styled 404 and 500 error templates matching the application design.

---

## 3. Tech Stack

- **Backend:** Python 3.11+, Flask, Gunicorn WSGI
- **Database:** SQLite with `cs50` / `sqlite3` abstraction layer (`db_helper.py`)
- **Frontend:** HTML5, CSS3, JavaScript (ES6+), Bootstrap 5, Font Awesome 6
- **Mapping & GIS:** Leaflet.js, OpenStreetMap tiles, Nominatim reverse geocoding API
- **Testing:** `pytest` unit and integration test suite

---

## 4. Architecture & File Structure

```
CS50-Final-Project/
│
├── app.py                   # Central Flask controller, routes, proximity logic, API endpoints
├── db_helper.py             # CS50 SQL wrapper with fallback to sqlite3 and connection pooling
├── helpers.py               # View decorators, commercial content regex, coordinate jitter, safe redirect
├── init_db.py               # Database initialization and idempotent schema migration engine
├── schema.sql               # SQLite DDL schema with relational tables, foreign keys, and indexes
├── seed.py                  # Realistic Bengaluru demo data across 5 localities with chat & ratings
├── requirements.txt         # Pinned Python package dependencies
├── Procfile                 # Cloud deployment process file for Render / Gunicorn
├── .env.example             # Example environment variable template (SECRET_KEY, PORT, etc.)
│
├── static/
│   ├── css/styles.css       # Custom design system with Indian color accents, badge styles, steppers
│   └── js/main.js           # Client-side debounced search, category, radius, and sorting engine
│
├── templates/
│   ├── layout.html          # Base template, navbar, notifications badge, emergency banner, geo modal
│   ├── index.html           # Mohalla feed, "How it works" banner, radius/sort controls, live map view
│   ├── post_detail.html     # Post detail view, action CTA, embedded map, WhatsApp share, chat, reviews
│   ├── dashboard.html       # User dashboard: My posts, incoming responses, sent offers, repost button
│   ├── new_post.html        # Post creation with live coordinates and client-side character validation
│   ├── edit_post.html       # Post editing form with commercial filter enforcement
│   ├── profile.html         # Resident profile with reputation badges, star ratings, and history
│   ├── admin_reports.html   # Moderator dashboard: Dismiss report, hide/restore, remove post, ban user
│   ├── guidelines.html      # Community mutual aid guidelines & emergency service disclaimers
│   ├── login.html           # Login page with safe ?next= redirection
│   ├── register.html        # User registration with locality and coordinate capture
│   ├── 404.html             # Styled 404 Not Found error page
│   └── 500.html             # Styled 500 Internal Server Error page
│
└── tests/
    └── test_neighborgrid.py # Pytest test suite (commercial filter, auth, privacy, Haversine, CSRF)
```

---

## 5. Local Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/Ibtesam1901/CS50-Final-Project.git
cd CS50-Final-Project
```

### 2. Create a virtual environment & install requirements
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Initialize & Seed Database
```bash
python seed.py
```
*Creates `neighborgrid.db` and populates realistic Bengaluru demo accounts (`admin`, `aarav_patel`, `priya_sharma`, `rohan_verma`, etc.) with password `password123`.*

### 4. Run the Test Suite
```bash
pytest -v
```
*All 13 integration and security tests will execute and pass.*

### 5. Start Local Development Server
```bash
python -m flask run
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## 6. Cloud Deployment Notes (Render & Ephemeral Storage)

NeighborGrid is deployed to Render at [https://neighbor-grid.onrender.com/](https://neighbor-grid.onrender.com/).

### Important Note on SQLite in Cloud Free Tiers
- **Ephemeral Filesystem:** On Render's free tier, the web container filesystem is ephemeral. Whenever the service spins down due to inactivity or restarts upon a new git deployment, the SQLite database (`neighborgrid.db`) resets to its seeded state.
- **Production Recommendation:** For continuous persistence in production, mount a **Render Persistent Disk** to the `/data` directory and configure `DATABASE_PATH=/data/neighborgrid.db`, or migrate `db_helper.py` to PostgreSQL using Render's Managed Postgres.

---

## 7. Video Demo Walkthrough Outline (CS50x Submission)

When recording your 3-minute CS50x final project demo video:
1. **Introduction (0:00 - 0:30):** State your name, project title (*NeighborGrid*), your city/country, and explain the core problem (hyperlocal mutual aid without buying/selling or commercial middlemen).
2. **Geolocation & Map View (0:30 - 1:00):** Show the landing page, allow location or select a Bengaluru locality, switch to the *Live Map View*, and demonstrate the user beacon and nearby request/offer pins.
3. **Commercial Filter Enforcement (1:00 - 1:30):** Try creating a post with commercial language (e.g. *"Selling drill for Rs 500"* or *"₹1000 cash"*). Show the server blocking it with the friendly non-commercial guideline alert.
4. **The Mutual-Aid Lifecycle (1:30 - 2:30):**
   - Open a neighbor's request (e.g. Aarav's ladder).
   - Log in and submit an offer to help.
   - Switch to Aarav's account, accept the offer on the Dashboard.
   - Show how contact details and the private in-app coordination chat unlock.
   - Complete the task and leave a 5-star rating and review.
5. **Admin Moderation & Wrap-up (2:30 - 3:00):** Log in as `admin`, show the Moderation Dashboard reviewing community reports, and conclude with the `/health` endpoint.

---

## 8. Academic Honesty & Credits

Developed by **Syed Hassan Ibtesam** for Harvard University's **CS50x: Introduction to Computer Science**.
- Maps powered by [Leaflet.js](https://leafletjs.com/) and [OpenStreetMap](https://www.openstreetmap.org/).
- Reverse geocoding via OpenStreetMap Nominatim.
- Icons by [Font Awesome](https://fontawesome.com/).
