# NeighborGrid: Hyperlocal Mutual Aid & Community Sharing (India Locality Edition)

#### Video Demo: <YOUR YOUTUBE URL>

#### Description:

### 1. What It Is and Why

In Indian metropolitan and suburban neighborhoods—whether across housing societies, colonies, or vibrant mohallas—neighbors live in close physical proximity, yet often lack any non-commercial, authentic medium to assist one another. From borrowing an aluminum ladder for ceiling fan cleaning, sharing a Bosch drill kit, carpooling on a two-wheeler to the nearest metro station, seeking urgent blood donors, sharing balcony garden cuttings (tulsi, curry leaves), to mentoring for competitive exams (UPSC, CA), commercial apps frequently fill feeds with paid ads, delivery fees, and spam while compromising user privacy.

**NeighborGrid (Bharat Locality Edition)** is a grassroots, hyperlocal mutual-aid and equipment-sharing web platform built for **CS50x (CS50's Introduction to Computer Science)**. It operates strictly on community solidarity—no buying, selling, or financial transactions. Crucially, the platform includes automatic live browser geolocation: upon logging in, users are prompted for location permissions, centering an interactive Leaflet.js mohalla map directly on their physical surroundings with walking-distance requests and offers. A two-tier privacy boundary keeps phone numbers and WhatsApp details concealed until the post creator explicitly reviews and accepts an offer.

---

### 2. Core Features & User Journey

1. **User Registration & Locality Scoping:**
   Residents register with their username, email, PIN code, and specific locality (e.g., *Indiranagar, Bengaluru* or *Hauz Khas, Delhi*).

2. **Automated Geolocation Prompt on Login:**
   Immediately following login, if the user hasn't set their coordinates, a modal prompts for live location access. Confirming access saves the latitude and longitude, immediately centering the live OpenStreetMap on their exact surroundings and recalculating walking-distance aid pins.

3. **Localized Indian Community Categories:**
   Requests and offers are structured into eight culturally tailored categories:
   - *Tools & Ghar Ka Samaan* (Drills, ladders, toolsets)
   - *Tuition & Skill Sharing* (Coding, music, yoga, spoken English)
   - *Rides & Local Errands* (Metro carpooling, sabzi mandi, chemist pickup)
   - *Pet Care & Feeding* (Dog walking, feeding community indies)
   - *Household & Shifting Help* (Furniture lifting, flat shifting assistance)
   - *Emergency Aid & Blood Request* (Urgent non-monetary aid, blood donation)
   - *Books & UPSC / Exam Prep* (Exam manuals, textbooks, novels)
   - *Garden, Plants & Food Sharing* (Terrace garden saplings, kadi patta, festive sweets)

4. **Interactive Leaflet.js Mohalla Map:**
   The homepage features a live toggle between **Cards Grid** and **Live Map**. Green pins indicate nearby offers; red pins represent requests, with pulsing indicators for urgent items. Clicking any pin displays a preview card with distance, category, and a one-click connection link.

5. **Structured Cooperation Lifecycle:**
   - **Offer Help:** Neighbors browse their local feed or map and send structured notes.
   - **Acceptance & Rival Declining:** The creator clicks *Accept*, which shifts the post to `in_progress` and auto-declines competing offers.
   - **Privacy Boundary Breach & In-App Chat:** Acceptance unlocks private phone/WhatsApp numbers and enables an integrated in-app direct chat thread on the post itself for real-time coordination.
   - **Completion & Star Reputation:** When finished, the creator marks the post `completed`. Both participants can exchange 1-to-5 star ratings and written reviews, building a community trust score.

6. **Safety, Guidelines & Admin Moderation:**
   Clear guidelines emphasize non-commercial aid, safe public meeting points, and emergency notices citing **112 / 100 / 108**. Resident welfare moderators have a dedicated `/admin/reports` portal to review and hide spam or commercial listings.

---

### 3. File-by-File Explanation

- **`app.py`:**
  The Flask backend managing authentication, session handling, CSRF security, geolocation updates (`/api/user/location`), JSON map feed endpoints (`/api/posts`), mutual-aid lifecycle transitions, direct messaging (`/post/<id>/messages`), ratings (`/post/<id>/rate`), and admin moderation.

- **`db_helper.py`:**
  Dual-mode database wrapper ensuring seamless compatibility with CS50's `cs50.SQL` and Python's native `sqlite3` module with dictionary row factories and `PRAGMA foreign_keys = ON;`.

- **`helpers.py`:**
  Provides `@login_required`, `@admin_required`, and `apology(message, code)`.

- **`schema.sql`:**
  Database definitions for `users`, `categories`, `posts` (with geo-coordinates and location landmarks), `matches`, `reports`, `ratings`, and `messages`.

- **`seed.py`:**
  Seeds authentic Indian neighborhood accounts in Bengaluru (*Indiranagar* and *Koramangala*), featuring realistic requests (fan repair ladders, metro scooter carpooling, UPSC books, terrace garden cuttings), active chat threads, reviews, and sample reports.

- **`test_suite.py`:**
  Automated testing script covering 15 distinct functional and security checks (password validation, geolocation updates, neighborhood isolation, contact shielding, in-app messaging, star ratings, and admin moderation).

- **`static/css/styles.css`:**
  Warm Indian color palette (deep forest green, saffron orange, marigold yellow), card elevations, pulsing urgency badges, and lifecycle stepper bars.

- **`templates/layout.html`:**
  Navigation, user dropdown, flash toasts, emergency service notices, and the automated geolocation modal prompt.

- **`templates/index.html`:**
  Mohalla feed, impact counter, filter controls, and interactive Leaflet.js live map.

- **`templates/post_detail.html`:**
  Full post view with lifecycle steppers, unlocked contact details, in-app chat box, rating forms, and report modal.

- **`templates/dashboard.html` & `templates/profile.html`:**
  User activity tracking, star rating reputation displays, and community reviews.

---

### 4. How to Run the Application

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize and seed the database:**
   ```bash
   python seed.py
   ```

3. **Run the test suite:**
   ```bash
   python test_suite.py
   ```

4. **Start the Flask server:**
   ```bash
   flask run
   ```
   Open `http://127.0.0.1:5000` in your browser. Log in with:
   - **Username:** `aarav_patel` (or `priya_sharma`, `rohan_verma`, `admin`)
   - **Password:** `password123`
