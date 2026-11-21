# NeighborGrid · Mohalla Feed (CS50x Final Project)

#### Hyperlocal, Non-Monetary Mutual-Aid Web Platform for Indian Neighborhoods
**Live Production URL:** [https://neighbor-grid.onrender.com/](https://neighbor-grid.onrender.com/)  
**Video Demo:** [https://youtu.be/CS50x-NeighborGrid-Demo](https://youtu.be/CS50x-NeighborGrid-Demo) *(Update with your recording)*

---

## 1. Project Overview & Motivation

In urban Indian neighborhoods, apartment societies, and residential colonies (*mohallas*), residents live close physically yet often remain socially isolated. When a neighbor needs a step ladder, a power drill, an urgent blood donor, or a carpool ride to the metro station, commercial marketplaces impose transaction fees, encourage buying/selling spam, and compromise privacy.

**NeighborGrid** is a production-grade, hyperlocal mutual-aid web platform designed to foster community solidarity. It operates on a strict **non-commercial, neighbor-to-neighbor policy**: no buying, selling, renting, or cash exchanges are permitted. Everything shared is through grassroots goodwill.

The platform is localized for Indian neighborhoods (*Mohalla Feed*, *Ghar Ka Samaan*, Bengaluru localities such as Indiranagar, Koramangala, HSR Layout, Jayanagar, and Whitefield), featuring live short polling updates, strict contact privacy, real-time walking distance calculations, private in-app coordination chat, star ratings, and community moderation.

---

## 2. Key Features

### A. Non-Commercial Enforcement (Rule #1)
- **Server-Side Commercial Content Filter:** Multi-language regex engine checks post creation and editing.
- Blocks currency symbols (`Rs`, `Rs.`, `R s`, `₹`, `INR`, `/-`), English commercial words (`selling`, `for sale`, `fixed price`, `COD`, `cash`, `rent per day`, `charge`, `buy`, `discount`), digital payment apps (`UPI`, `GPay`, `PhonePe`, `Paytm`), and Hindi/Hinglish commercial words (`bechna`, `bechni`, `kimat`, `keemat`, `daam`, `rupaye`, `rupees`, `paise`, `bikau`).
- Any attempt to monetize mutual aid is rejected before database insertion with a friendly guideline notice.
- Community members can report suspicious posts via a dedicated modal for administrator review.

### B. Live Updates Architecture (No WebSockets / Free-Tier Optimized)
To eliminate manual page refreshes on Render's free tier (where WebSockets/SocketIO are fragile with Gunicorn sync workers):
- **Lightweight Short Polling:**
  - **Feed Updates (`GET /api/posts/updates`):** Polls every 10 seconds while the browser tab is active. Detects new posts, status changes, and deletions without disrupting active scrolling via a non-intrusive sticky alert pill (*"X new posts · Tap to view"*).
  - **In-App Direct Chat (`GET /api/threads/<id>/messages`):** Polls every 3 seconds while a thread is open and visible (15s in background). Renders incoming messages, shows a subtle `· Seen` marker via `read_at`, and preserves scroll position.
  - **Client-Side Idempotency:** Prevents duplicate chat messages on double-click or network retry using a client-generated UUID key.
  - **Notification Summary (`GET /api/notifications/summary`):** Polls every 18 seconds, dynamically updating the navbar badge, browser tab title prefix (e.g. `(2) NeighborGrid`), and non-intrusive toast alerts.
- **Page Visibility API Integration:** Automatically pauses or throttles polling when the user switches tabs, resuming with an immediate fetch upon return.
- **Worker Configuration:** Configured Gunicorn with 3 sync workers and 2 threads (`gunicorn --workers 3 --threads 2 --bind 0.0.0.0:$PORT app:app`) to ensure polling requests never block standard page loads.

### C. Privacy Shielding & Public Meeting Points (B2)
- **Landmark Privacy Guard:** Public meeting points (cross streets/landmarks) are required instead of residential addresses. The backend checks for private patterns (e.g. `Flat 402`, `House No. 12`, `Door No. 5B`, `#42`, `Apartment`) and blocks accidental home address submissions.
- **Coordinate Privacy Jitter (~100m):** Coordinates are jittered by ~100m before public map rendering so exact house locations are never exposed.
- **Two-Tier Contact Concealment:** Phone numbers, WhatsApp, and emails are **never** rendered publicly. Direct contact details are strictly unlocked on the server only after the post owner clicks **Accept** on a neighbor's response.

### D. Real-Time Proximity Engine & Locality Standards
- **Haversine Distance Engine:** Calculates exact walking and driving distance in kilometers (`haversine_km`) between the viewer and each post pin.
- **Radius & Proximity Sorting:** The feed supports live radius filtering (within 500m, 1km, 2km, 5km, or any radius) and sorting by *Nearest*, *Urgent First*, or *Newest*.
- **Standardized Localities (B3):** Standardized dropdown of Bengaluru localities (Indiranagar, Koramangala, HSR Layout, Jayanagar, Whitefield, etc.). Placeholder labels such as "Your Current Location" are prohibited and automatically sanitized.

### E. Social Previews & Friendly Timestamps (B4, B7)
- **Live Relative Time Updates:** Timestamps render as `"just now"`, `"5 min ago"`, `"Yesterday"`, or `"3 days ago"`, updating live on the client every 60 seconds without refetching. Hovering displays the full exact timestamp in a tooltip.
- **Rich Social Previews (Open Graph & Twitter Cards):** Styled 1200x630 branded banner (`/static/og-image.png`), `twitter:card = summary_large_image`, `og:url`, and post-specific titles/descriptions.
- **Recently Completed Strip (B5):** Showcases recent community mutual aid completions to visitors without requiring login.

---

## 3. Tech Stack

- **Backend:** Python 3.11+, Flask, Gunicorn WSGI
- **Database:** SQLite with `cs50` / `sqlite3` abstraction layer (`db_helper.py`)
- **Frontend:** HTML5, CSS3, JavaScript (ES6+), Bootstrap 5, Font Awesome 6
- **Mapping & GIS:** Leaflet.js, OpenStreetMap tiles, Nominatim reverse geocoding API
- **Testing:** `pytest` unit and integration test suite (18/18 passing)

---

## 4. Architecture & File Structure

```
CS50-Final-Project/
│
├── app.py                   # Central controller, polling endpoints, proximity logic, API routes
├── db_helper.py             # CS50 SQL wrapper with fallback to sqlite3 and connection pooling
├── helpers.py               # View decorators, Hinglish commercial filter, address regex, coordinate jitter
├── init_db.py               # Database initialization and idempotent schema migration engine
├── schema.sql               # SQLite DDL schema with relational tables, foreign keys, and indexes
├── seed.py                  # Realistic Bengaluru demo data across 5 localities with chat & ratings
├── requirements.txt         # Pinned Python package dependencies
├── Procfile                 # Cloud deployment process file for Render (3 workers, 2 threads)
├── .env.example             # Example environment variable template (SECRET_KEY, PORT, etc.)
│
├── static/
│   ├── css/styles.css       # Custom design system with Indian color accents, badge styles, steppers
│   ├── js/main.js           # Live polling engine, sticky pill, relative time, search, radius, sort
│   └── og-image.png         # 1200x630 branded social media preview card
│
├── templates/
│   ├── layout.html          # Base template, navbar badge, social meta tags, emergency banner, geo modal
│   ├── index.html           # Mohalla feed, sticky new posts pill, recently completed strip, live map
│   ├── post_detail.html     # Post view, action CTA, live 3s chat polling, seen marker, WhatsApp share
│   ├── dashboard.html       # User dashboard: My posts, incoming responses, sent offers, repost button
│   ├── new_post.html        # Post creation with landmark privacy warning and required locality dropdown
│   ├── edit_post.html       # Post editing form with commercial filter and landmark privacy checks
│   ├── profile.html         # Resident profile with reputation badges, star ratings, and history
│   ├── admin_reports.html   # Moderator dashboard: Dismiss report, hide/restore, remove post, ban user
│   ├── guidelines.html      # Community mutual aid guidelines & emergency service disclaimers
│   ├── login.html           # Login page with safe ?next= redirection
│   ├── register.html        # User registration with locality and coordinate capture
│   ├── 404.html             # Styled 404 Not Found error page
│   └── 500.html             # Styled 500 Internal Server Error page
│
└── tests/
    └── test_neighborgrid.py # 18-test Pytest suite (live polling, chat security, idempotency, filters)
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
*All 18 integration, live polling, and security tests will execute and pass.*

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

## 7. Two-Browser Verification Checklist

To test live updates and mutual-aid flow across two separate users:
1. **Window A (Google Chrome)**: Log in as `aarav_patel` (`password123`).
2. **Window B (Firefox or Incognito)**: Log in as `priya_sharma` (`password123`).
3. **Live Feed Test**:
   - In Window A, submit a new post (`/post/new`): *"Need a torque wrench for bicycle repair"*.
   - In Window B, keep the home feed (`/`) open without manually refreshing.
   - Within 10 seconds, the sticky alert pill appears at the top: *"1 new post · Tap to view"*. Click it to prepend the new post without losing scroll position.
4. **Live In-App Chat Test**:
   - In Window B, view Aarav's post and submit an offer: *"I have one in my toolkit, happy to lend!"*.
   - In Window A, open `/dashboard`, click **Accept** on Priya's offer.
   - Both users open the post page.
   - Send messages back and forth in the in-app chat box.
   - Messages appear automatically within 3 seconds on the other screen, the `· Seen` status updates live, and auto-scrolling triggers smoothly without page reloads.

---

## 8. Academic Honesty & Credits

Developed by **Syed Hassan Ibtesam** for Harvard University's **CS50x: Introduction to Computer Science**.
- Maps powered by [Leaflet.js](https://leafletjs.com/) and [OpenStreetMap](https://www.openstreetmap.org/).
- Reverse geocoding via OpenStreetMap Nominatim.
- Icons by [Font Awesome](https://fontawesome.com/).
