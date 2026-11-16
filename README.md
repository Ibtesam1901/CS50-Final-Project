# NeighborGrid: Hyperlocal Mutual Aid & Community Sharing

#### Video Demo: <YOUR YOUTUBE URL>

#### Description:

### 1. What It Is and Why

Modern urban and suburban life is often marked by physical proximity paired with social fragmentation. Neighbors frequently live only meters apart, yet lack any reliable, non-commercial channel to lend a step ladder, share an extra drill, offer carpooling rides, assist with moving heavy furniture, or offer friendly tutoring and pet care. Commercial platforms often monetize neighbor interactions, fill feeds with algorithmic noise or marketplace fees, and compromise personal privacy by exposing direct phone numbers and addresses publicly to the whole web.

**NeighborGrid** is a grassroots, hyperlocal mutual-aid and equipment-sharing web platform built for **CS50x (CS50's Introduction to Computer Science)**. It provides a community bulletin where verified local residents can publish structured assistance requests and offers. NeighborGrid operates on pure mutual aid—financial transactions, commercial advertisements, and monetary demands are strictly prohibited. Crucially, the platform incorporates a privacy-first lifecycle: a user's direct contact details (phone numbers, emails) are completely concealed until the creator of a post explicitly reviews and accepts a neighbor's offer to assist.

---

### 2. Core Features & User Journey

NeighborGrid guides neighbors through a safe, transparent, and structured cooperation lifecycle:

1. **User Registration & Neighborhood Pinning:**
   Neighbors register with a unique username, email, password (hashed using Werkzeug security standards), bio, and their specific residential neighborhood or locality. All feed discovery is strictly scoped to the user's registered neighborhood, preventing irrelevant posts from distant cities.

2. **Categorized Mutual-Aid Posts with Interactive Maps:**
   Neighbors can publish requests or offers across eight community categories: *Tools & Equipment*, *Skills & Teaching*, *Rides & Errands*, *Pet Care*, *Household Help*, *Emergency Aid*, *Books & Media*, and *Garden & Food Sharing*. Each post features an urgency flag (`standard` vs `urgent`), an optional automatic expiration date, cross-street landmarks, and optional map coordinates with automatic browser geolocation.

3. **Urgency-Prioritized Activity Feed & Interactive Leaflet.js Map:**
   The homepage dynamically presents active, non-expired posts in the user's neighborhood. Urgent items are styled with high-visibility badges and prioritized at the top of the feed. An automated neighborhood **Impact Counter** showcases the real-time total of completed acts of neighborly aid. A built-in view switcher allows neighbors to toggle between a card grid and an interactive OpenStreetMap view powered by Leaflet.js.

4. **Structured Cooperation Lifecycle (The Heart of NeighborGrid):**
   - **Offer Help:** Neighbors browse their local feed and send structured responses with personalized notes.
   - **Review & Match:** The post owner reviews incoming offers on the post detail page or their centralized Dashboard.
   - **Acceptance & Automatic Rival Declining:** When the owner clicks *Accept*, the post transitions from `open` to `in_progress`. Any competing pending offers on that specific post are automatically declined to prevent double-booking.
   - **Privacy Boundary Breach (Contact Reveal):** Only upon acceptance are private contact channels (email, phone number) unlocked and revealed between the matched neighbors.
   - **In-App Direct Messaging Thread:** An integrated private chat box unlocks immediately between the post owner and the accepted helper, allowing real-time coordination without leaving the application.
   - **Completion & Reputation Ratings:** Once the aid is complete, the owner marks the post `completed`. Both participants can then submit a 1-to-5 star rating and written review, updating public neighbor reputation scores.

5. **Live Search & Dynamic Filter:**
   A debounced JavaScript client filter enables residents to instantly search requests by keywords or landmarks, toggle between Requests and Offers, and filter by category without page refreshes.

6. **Safety, Guidelines & Admin Moderation:**
   NeighborGrid features comprehensive safety guidelines, explicit disclaimers clarifying that the application is not an emergency dispatch service (911/112), and an integrated reporting mechanism. System administrators have access to a dedicated moderation dashboard (`/admin/reports`) where reported posts can be audited and hidden from public feeds with one click.

---

### 3. File-by-File Explanation

- **`app.py`:**
  The central Flask controller handling all routing, authentication, authorization checks, session handling, CSRF token validation, and database operations. It implements the entire lifecycle: registration, login/logout, feed queries, post creation/editing, neighbor response submission, match acceptance/declining, in-app direct messaging, star rating submission, task completion, cancelation, profile display, reporting, and admin moderation.

- **`db_helper.py`:**
  A robust database interface provider. It seamlessly supports CS50's `cs50.SQL` library (`sqlite:///neighborgrid.db`) while including a self-contained fallback using Python's native `sqlite3` module with dictionary cursor row-factories and foreign key enforcement (`PRAGMA foreign_keys = ON;`). This ensures zero dependency hurdles across local Windows setups, Linux environments, and CS50 Codespaces.

- **`helpers.py`:**
  Contains core view decorators and utility functions:
  - `login_required`: Restricts protected routes to authenticated users, redirecting guests to the login screen.
  - `admin_required`: Restricts moderation routes (`/admin/reports`, hiding/unhiding posts) exclusively to users possessing `is_admin = 1`.
  - `apology`: Renders custom error and notification templates with standard HTTP status codes (400, 403, 404).

- **`schema.sql`:**
  Contains the relational database architecture:
  - `users`: Stores user credentials, hashed passwords, neighborhoods, optional phone numbers, bios, and administrator flags.
  - `categories`: Standardizes aid categories with descriptive icons.
  - `posts`: Maintains mutual aid requests and offers, location details, latitude, longitude, urgency states, neighborhood indexing, expiration dates, and statuses (`open`, `in_progress`, `completed`, `cancelled`).
  - `matches`: Tracks responses, messages, unique constraints per (post, responder), and match states (`pending`, `accepted`, `declined`).
  - `reports`: Stores safety complaints submitted by residents.
  - `ratings`: Stores 1-5 star ratings and reviews between mutual-aid partners upon task completion.
  - `messages`: Stores in-app direct messaging chat entries between the post creator and the accepted helper.
  - `idx_posts_feed`: Composite database index accelerating neighborhood feed querying.

- **`seed.py`:**
  A database utility that seeds realistic test accounts across two distinct neighborhoods (`Downtown` and `Oakridge`), populating realistic posts across every category, map coordinates, active direct chats, completed reviews, and sample moderation reports.

- **`test_suite.py`:**
  An automated end-to-end integration and security test suite testing 14 distinct system requirements: password validations, duplicate constraints, session isolation, neighborhood boundary isolation, self-response barriers, contact privacy unveiling, in-app messaging, post ratings, illegal state transition prevention, and admin moderation hiding.

- **`static/css/styles.css`:**
  Custom styling augmenting Bootstrap 5. Provides custom color palettes (deep blues, gold accents), responsive card grids, hover elevations, urgent alert pulsing animations, lifecycle stepper progress bars, and clean status badges.

- **`static/js/main.js`:**
  Client-side interactivity script powering real-time debounced search and category/type filtering over the feed without page reloads.

- **`templates/layout.html`:**
  The primary Jinja2 template establishing the global navigation bar, user session badge, dynamic flash message toasts, CSRF-protected logout triggers, and the emergency service disclaimer footer.

- **`templates/index.html`:**
  The neighborhood feed view containing the hero banner, real-time community impact counter, filter toolbars, Leaflet.js interactive map view, and post grid cards.

- **`templates/post_detail.html`:**
  The detailed view of an individual post. Conditionally displays post owner controls, lifecycle stepper, offer response submission forms, pending neighbor responses, unlocked contact details, in-app direct chat thread, star reviews, and the moderation report modal.

- **`templates/dashboard.html`:**
  A user command center dividing activity into: *Incoming Responses to My Posts* (with direct Accept/Decline controls), *My Active Posts*, *Offers/Responses I Sent*, and *Received Community Reviews*.

- **`templates/profile.html`:**
  Public neighborhood user profile displaying member join date, neighborhood, bio, star rating average, community reviews, active posts, and the community impact score ("Acts of Aid Completed").

- **`templates/new_post.html` & `templates/edit_post.html`:**
  Accessible forms with live character counters, post type selectors, category dropdowns, urgency flags, location/coordinates input with browser geolocation detection, and dynamic emergency advisories.

- **`templates/admin_reports.html`:**
  Administrative moderation queue listing flagged items, reporter rationales, and controls to hide or unhide offending posts.

- **`templates/guidelines.html`:**
  Clear community standards and safety protocols outlining non-commercial rules, public meeting safety, and emergency services boundaries.

- **`templates/login.html` & `templates/register.html`:**
  User authentication templates with client validation, security reminders, and CSRF token binding.

- **`requirements.txt`:**
  Package dependency file listing required Python packages (`Flask`, `cs50`, `Werkzeug`).

---

### 4. Key Design Decisions

1. **Integrated In-App Messaging vs External Apps:**
   Rather than forcing neighbors immediately to third-party SMS or messaging apps, an in-app private coordination chat unlocks on the post itself once a match is accepted.
2. **Post-Completion Ratings and Reputation:**
   Trust is essential in mutual aid. Allowing participants to leave 1-to-5 star ratings and reviews gives neighbors confidence when lending equipment or offering assistance.
3. **Optional Approximate Map Geolocation:**
   Neighbors can specify landmarks and optional coordinates (or auto-detect via browser geolocation) without exposing private apartment numbers, rendering helpful spatial pins on the Leaflet.js map.
4. **Respond-Then-Accept Lifecycle:**
   Unlike instant-claim gig boards, mutual aid requires comfort and mutual consent. Neighbors offer assistance; post owners review notes and choose whom to coordinate with.
5. **Two-Tier Contact Information Concealment:**
   Phone numbers and personal emails are never visible publicly on posts. They remain strictly concealed until an offer is accepted by the post creator.

---

### 5. How to Run the Application

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize and seed the database:**
   ```bash
   python seed.py
   ```

3. **Execute the automated test suite:**
   ```bash
   python test_suite.py
   ```

4. **Start the Flask server:**
   ```bash
   flask run
   ```
   Open your browser to `http://127.0.0.1:5000` to interact with NeighborGrid.
