# NeighborGrid: Hyperlocal Mutual Aid & Community Sharing (Production Edition)

#### Video Demo: <YOUR YOUTUBE URL>

#### Description:

### 1. Project Overview & Motivation

In today's urban neighborhoods, residential colonies, and housing societies, residents live in close physical proximity yet often remain socially disconnected. Neighbors frequently lack a trusted, non-commercial channel to lend tools, assist with household tasks, carpool to transit hubs, locate urgent blood donors, or share books and skills. Mainstream commercial apps often monetize basic neighbor interactions, clutter feeds with advertisements, impose delivery fees, and compromise privacy by exposing personal contact information publicly.

**NeighborGrid** is a production-ready, hyperlocal mutual-aid and equipment-sharing web platform developed as the final project for **CS50x (CS50's Introduction to Computer Science)**. Built with Flask, SQLite, HTML5, CSS3, and JavaScript, NeighborGrid operates on pure community solidarity: buying, selling, commercial promotions, and monetary exchanges are prohibited.

The platform features:
- **Live HTML5 Geolocation & Reverse Geocoding:** Automatically prompts for location permissions upon login, centers an interactive OpenStreetMap (via Leaflet.js) on the user's exact coordinates, and reverse-geocodes coordinates into human-readable neighborhood/locality names via OpenStreetMap Nominatim.
- **Real-Time Mathematical Proximity Engine:** Uses the **Haversine formula** to calculate exact walking and driving distances in kilometers between the user and every community post, dynamically sorting feeds by proximity.
- **Two-Tier Privacy Protection:** Phone and WhatsApp numbers remain hidden until a post creator reviews and accepts a neighbor's offer.
- **Integrated In-App Messaging:** An encrypted direct chat thread unlocks directly on the post between matched neighbors for real-time coordination.
- **Post-Completion Ratings & Reputation:** A 1-to-5 star rating and written review system to establish trust across the community.

---

### 2. Detailed Feature Breakdown & User Journey

#### A. User Authentication & Geolocation Onboarding
- **Secure Registration:** Users sign up with a unique username, email, password (hashed using Werkzeug's `generate_password_hash` with scrypt), contact number, bio, and PIN code.
- **Automated Location Modal:** Upon logging in, if GPS coordinates are not yet set, an onboarding modal prompts the user for location access.
- **Reverse Geocoding:** Coordinates captured via the browser's `navigator.geolocation` API are sent to `/api/user/location`, where server-side reverse geocoding translates latitude and longitude into an authentic locality label (e.g., *Indiranagar, Bengaluru* or *South Extension, New Delhi*).
- **Proximity Pinning:** Users can click **"Pin My Exact GPS Location"** at any time in the hero header to refresh their coordinates.

#### B. Culturally Tailored Mutual-Aid Categories
Posts are classified into eight community categories:
1. **Tools & Ghar Ka Samaan:** Drills, ladders, toolsets, pressure washers, and repair gear.
2. **Tuition & Skill Sharing:** Coding, mathematics, yoga, music, spoken English, and cooking.
3. **Rides & Local Errands:** Carpooling to metro/train stations, grocery/sabzi mandi runs, and medicine pickups.
4. **Pet Care & Feeding:** Dog walking, pet sitting, and caring for community animals.
5. **Household & Shifting Help:** Furniture lifting, flat shifting assistance, and quick repairs.
6. **Emergency Aid & Blood Request:** Urgent non-monetary assistance, blood donor matching, and emergency neighborhood support.
7. **Books & UPSC / Exam Prep:** Competitive exam manuals, NCERT textbooks, reference literature, and board games.
8. **Garden, Plants & Food Sharing:** Balcony and terrace garden saplings, kadi patta cuttings, tulsi starters, and festive home-cooked food.

#### C. Live Interactive Map & Distance-Sorted Feed
- **View Switcher:** A toggle allows switching between a responsive **Card Grid** and an interactive **Leaflet.js Map**.
- **User Live Beacon:** A glowing blue pulse marker (*"Aapki Location (You Are Here)"*) marks the user's exact physical position.
- **Visual Pins:** Nearby requests are rendered as red markers; offers are rendered as green markers, with pulsing badges for urgent items.
- **Distance Badges:** Every card and popup displays real-time calculated walking distances (e.g., `🚶 0.35 km away`).
- **Map Controls:** One-click controls include **"Center on Me"** and **"Show All Nearby Pins"** (which automatically fits the map viewport around all neighboring aid requests).

#### D. The Cooperation Lifecycle & Privacy Safeguards
1. **Browse & Filter:** Neighbors search the feed with real-time debounced keyword search, category filters, and request/offer toggles.
2. **Offer Help:** Neighbors send structured responses with personal notes (`/post/<id>/respond`). Duplicate submissions are prevented by a database-level `UNIQUE(post_id, responder_id)` constraint.
3. **Review & Accept:** The post owner reviews incoming responses on their Dashboard or Post Detail page. Clicking **Accept** (`/match/<id>/accept`) transitions the post to `in_progress` and automatically marks all competing pending offers as `declined`.
4. **Privacy Barrier Release:** Unlocks private phone numbers and emails only between the two accepted participants.
5. **In-App Direct Chat:** An embedded direct messaging thread (`/post/<id>/messages`) opens on the post, allowing real-time coordination without leaving the application.
6. **Task Completion:** The owner marks the task `completed` (`/post/<id>/complete`), recording the completion timestamp and updating community impact counters.
7. **Star Ratings & Reviews:** Both participants can leave a 1-to-5 star rating and written review (`/post/<id>/rate`), which updates each user's public profile reputation score.

#### E. Safety, Guidelines & Moderation
- **Emergency Services Notice:** Clear disclaimers across all templates emphasize that NeighborGrid is not an emergency response service and provide official emergency dispatch numbers (**112 / 100 / 108**).
- **Post Reporting:** Neighbors can report suspicious, commercial, or unsafe posts with a detailed reason (`/post/<id>/report`).
- **Moderator Dashboard:** Protected by `@admin_required`, the moderation portal (`/admin/reports`) allows community administrators to audit reported items and hide offending posts from the public feed with a single click.

---

### 3. Architecture & File-by-File Technical Guide

- **`app.py`:**
  The central application controller. Contains all Flask routing, session management, CSRF validation, Haversine distance calculations (`haversine_km`), JSON map feed endpoints (`/api/posts`), geolocation updates (`/api/user/location`), authentication routes (`/register`, `/login`, `/logout`), post lifecycle transitions, direct messaging, star ratings, and moderation controls.

- **`db_helper.py`:**
  Database interface provider. Works seamlessly with CS50's `cs50.SQL` library (`sqlite:///neighborgrid.db`) while providing an automatic fallback to Python's built-in `sqlite3` module. Features dictionary row factories, connection pooling, and automatic execution of `PRAGMA foreign_keys = ON;`.

- **`helpers.py`:**
  Contains view decorators and presentation helpers:
  - `login_required`: Restricts protected views to authenticated sessions, redirecting guests to `/login`.
  - `admin_required`: Restricts administrative routes to users with `is_admin = 1`.
  - `apology`: Renders structured error pages with HTTP status codes (400, 403, 404).

- **`schema.sql`:**
  Defines the relational SQLite database schema:
  - `users`: Credentials, password hashes, locality, coordinates, phone numbers, bio, and admin status.
  - `categories`: Standardized categories with Font Awesome icons.
  - `posts`: Requests and offers, location details, coordinates, urgency, status (`open`, `in_progress`, `completed`, `cancelled`), and expiration timestamps.
  - `matches`: Responses, notes, status (`pending`, `accepted`, `declined`), and unique responder constraints.
  - `reports`: Community complaints linked to reported posts and reporting users.
  - `ratings`: 1-to-5 star scores, written reviews, post links, and participant IDs.
  - `messages`: Private in-app chat entries between matched participants.
  - `idx_posts_feed`: Composite index optimizing query performance on neighborhood feeds.

- **`seed.py`:**
  Production database seeder. Populates test accounts across localities (*Indiranagar* and *Koramangala* in Bengaluru), realistic mutual-aid posts with precise GPS coordinates, active in-app chat messages, completed star reviews, and a flagged commercial listing for moderation testing.

- **`test_suite.py`:**
  Automated integration and security test suite testing 15 distinct functional requirements, including password length constraints, duplicate checks, session isolation, live location updating, neighborhood boundaries, self-response barriers, contact detail concealment, in-app messaging, post ratings, unauthorized state transitions, and admin moderation.

- **`static/css/styles.css`:**
  Custom styling augmenting Bootstrap 5. Implements an Indian-inspired color palette (deep forest green `#064e3b`, saffron orange `#f97316`, marigold yellow `#eab308`), responsive card grids, hover elevation transitions, pulsing emergency alerts, and a 3-step lifecycle progress stepper (`Open` $\to$ `In Progress` $\to$ `Completed`).

- **`static/js/main.js`:**
  Powers client-side debounced search and live category/type filtering over the DOM without full page reloads.

- **`templates/layout.html`:**
  Base Jinja2 template establishing the sticky navigation bar, flash message alerts, emergency disclaimers, and the automated geolocation onboarding modal.

- **`templates/index.html`:**
  The main feed template. Contains the hero section, community impact counter, filter toolbars, Leaflet.js interactive map view, and post grid cards.

- **`templates/post_detail.html`:**
  Individual post page with lifecycle stepper, response submission forms, accepted contact cards, in-app chat box, review/rating forms, and the moderation report modal.

- **`templates/dashboard.html`:**
  User activity hub organized into three tabs: *Responses to My Posts* (with Accept/Decline actions), *My Active Posts*, and *Offers/Responses I Sent*.

- **`templates/profile.html`:**
  Public resident profile displaying join date, locality, bio, average star rating score, community reviews, and active posts.

- **`templates/new_post.html` & `templates/edit_post.html`:**
  Post creation and editing forms with live character counters, category selectors, urgency toggles, landmark inputs, and browser GPS coordinate detection.

- **`templates/admin_reports.html`:**
  Moderation dashboard displaying flagged posts, reporter comments, and one-click hide/unhide controls.

- **`templates/guidelines.html`:**
  Community rules detailing non-commercial policies, privacy protection, public meeting safety, and emergency service contact information.

- **`templates/login.html` & `templates/register.html`:**
  Authentication templates with CSRF token protection and client-side validation.

- **`Procfile` & `requirements.txt`:**
  Cloud deployment configuration files specifying Gunicorn WSGI server execution (`web: gunicorn app:app`) and pinned Python dependencies (`Flask`, `cs50`, `Werkzeug`, `gunicorn`).

---

### 4. Key Design Decisions

1. **Haversine Distance vs. External Distance Matrix APIs:**
   Rather than relying on paid third-party API keys (such as Google Maps Distance Matrix) that require external network calls and can cause rate-limiting issues, distances are calculated server-side using the Haversine trigonometric formula. This ensures sub-millisecond query performance and complete self-containment.

2. **OpenStreetMap & Leaflet.js vs. Proprietary Mapping Services:**
   Leaflet.js paired with OpenStreetMap tiles and the Nominatim reverse-geocoding API provides a lightweight, open-source mapping stack that requires zero API keys, operates cleanly across all modern browsers, and respects user privacy.

3. **Respond-Then-Accept Lifecycle vs. Instant Claiming:**
   In mutual aid, mutual consent and comfort are critical. Instead of allowing items or favors to be instantly claimed, responders submit offers with personalized notes, giving the post creator full agency to choose whom to coordinate with.

4. **Two-Tier Contact Concealment:**
   Phone numbers and personal emails are never visible publicly on posts. They remain strictly concealed until an offer is accepted by the post creator, preventing unsolicited messages and spam.

5. **In-App Direct Chat on the Post:**
   Rather than forcing users to switch to third-party SMS or messaging platforms immediately, an embedded in-app chat thread unlocks directly on the post detail page once a match is accepted.

6. **SQLite with Strict Foreign Key Enforcement:**
   SQLite provides a lightweight, single-file relational database that requires no standalone database server setup. `db_helper.py` explicitly executes `PRAGMA foreign_keys = ON;` on every connection to guarantee relational integrity and cascade deletions.

---

### 5. Local Setup & Testing Instructions

#### Prerequisites
- Python 3.10 or newer
- Git

#### Installation Steps
1. **Clone the repository:**
   ```bash
   git clone https://github.com/Ibtesam1901/CS50-Final-Project.git
   cd CS50-Final-Project
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize and seed the database:**
   ```bash
   python seed.py
   ```
   *This seeds demo accounts with the password `password123`:*
   - `aarav_patel` (Resident in Indiranagar)
   - `priya_sharma` (Resident in Indiranagar)
   - `rohan_verma` (Resident in Indiranagar)
   - `admin` (Resident Welfare Moderator)

4. **Run the automated test suite:**
   ```bash
   python test_suite.py
   ```
   *All 15 integration and security tests should pass with zero errors.*

5. **Start the local development server:**
   ```bash
   python -m flask run
   ```
   Open your browser to `http://127.0.0.1:5000`.

---

### 6. Production Deployment Guide

NeighborGrid includes production WSGI support (`gunicorn`) and a `Procfile` ready for cloud deployment:

#### Deploying on Render (Free Tier)
1. Push your repository to GitHub.
2. Sign in to [Render](https://render.com/) and create a **New Web Service**.
3. Connect your `CS50-Final-Project` repository.
4. Set the build and start commands:
   - **Build Command:** `pip install -r requirements.txt && python seed.py`
   - **Start Command:** `gunicorn app:app`
5. Click **Create Web Service**. Render will provision an HTTPS URL with SSL certificates enabled.

---

### 7. Academic Honesty & AI Disclosure

This project was built with the assistance of Anthropic / Google AI tools for code scaffolding, reviewing mathematical distance formulas, and designing edge-case constraint tests. All application logic, database schema constraints, security validations, and architectural decisions were reviewed, tested, and understood by the author in full accordance with CS50's academic honesty policy.
