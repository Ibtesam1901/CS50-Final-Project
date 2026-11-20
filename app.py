import os
import math
import secrets
from functools import wraps
from flask import Flask, flash, redirect, render_template, request, session, jsonify, abort
from werkzeug.security import check_password_hash, generate_password_hash
from init_db import init_db
from db_helper import SQL_PROVIDER
from helpers import apology, login_required, admin_required, check_commercial_content, is_safe_url, jitter_coordinate

# Initialize rate limiting gracefully
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    HAS_LIMITER = True
except ImportError:
    HAS_LIMITER = False

# Ensure database and schema migrations are applied on start
init_db()

# Configure application
app = Flask(__name__)

# Production-grade secret key configuration
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# Cookie security settings (HttpOnly, SameSite, Secure if production)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if os.environ.get("FLASK_ENV") == "production" or os.environ.get("RENDER"):
    app.config["SESSION_COOKIE_SECURE"] = True

# Rate limiting setup
if HAS_LIMITER:
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["300 per hour", "60 per minute"],
        storage_uri="memory://"
    )
else:
    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    limiter = DummyLimiter()

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Connect to database (configurable path)
db_url = os.environ.get("DATABASE_PATH", "neighborgrid.db")
if not db_url.startswith("sqlite:///"):
    db_url = f"sqlite:///{db_url}"
db = SQL_PROVIDER(db_url)

# Haversine distance formula (in Kilometers) for real-time proximity sorting
def haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    R = 6371.0 # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# CSRF helper generator
@app.before_request
def ensure_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)


def verify_csrf():
    token = (
        request.form.get("csrf_token") 
        or request.headers.get("X-CSRFToken") 
        or (request.is_json and request.get_json(silent=True) and request.get_json(silent=True).get("csrf_token"))
    )
    if not token or token != session.get("csrf_token"):
        return False
    return True

# Context processor for global unread notifications count
@app.context_processor
def inject_notifications():
    user_id = session.get("user_id")
    if not user_id:
        return {"unread_notifications_count": 0}
    try:
        # Pending incoming responses to user's posts
        inc = db.execute(
            """SELECT COUNT(m.id) AS count 
               FROM matches m 
               JOIN posts p ON p.id = m.post_id 
               WHERE p.user_id = ? AND m.status = 'pending'""",
            user_id
        )
        # Unread in-app messages received
        msgs = db.execute(
            """SELECT COUNT(id) AS count 
               FROM messages 
               WHERE receiver_id = ? AND is_read = 0""",
            user_id
        )
        total = (inc[0]["count"] if inc else 0) + (msgs[0]["count"] if msgs else 0)
        return {"unread_notifications_count": total}
    except Exception:
        return {"unread_notifications_count": 0}


# ==============================================================================
# HEALTHCHECK ENDPOINT (FOR UPTIME MONITORS / RENDER KEEP-ALIVE)
# ==============================================================================
@app.route("/health")
def health():
    """Lightweight 200 OK endpoint for Render uptime pingers to prevent sleep"""
    return jsonify({"status": "healthy", "service": "NeighborGrid", "uptime": "active"}), 200


# ==============================================================================
# FEED & CORE PAGES
# ==============================================================================
@app.route("/")
def index():
    """Production Real-Time Location-Driven Feed & Map with Auto-Expiry Filter"""
    user_id = session.get("user_id")

    # Real-time coordinates from session or database
    user_lat = session.get("user_lat")
    user_lng = session.get("user_lng")
    user_loc_name = session.get("user_loc_name") or session.get("neighborhood")

    # If logged in without coordinates in session, check user record in db
    if user_id and (user_lat is None or user_lng is None):
        user_rows = db.execute("SELECT latitude, longitude, neighborhood FROM users WHERE id = ?", user_id)
        if user_rows and user_rows[0].get("latitude") and user_rows[0].get("longitude"):
            user_lat = user_rows[0]["latitude"]
            user_lng = user_rows[0]["longitude"]
            session["user_lat"] = user_lat
            session["user_lng"] = user_lng
            session["has_location"] = True
            if not user_loc_name:
                user_loc_name = user_rows[0].get("neighborhood")

    # Query active, visible, non-expired posts (Open posts older than 14 days auto-expire from feed)
    raw_posts = db.execute(
        """SELECT p.id, p.title, p.description, p.post_type, p.urgency, p.created_at,
                  p.category_id, p.location_details, p.latitude, p.longitude, p.neighborhood,
                  c.name AS category, c.icon AS category_icon, u.username
           FROM posts p
           JOIN users u ON u.id = p.user_id
           JOIN categories c ON c.id = p.category_id
           WHERE p.status = 'open'
             AND p.is_hidden = 0
             AND p.is_flagged = 0
             AND (p.expires_at IS NULL OR p.expires_at > CURRENT_TIMESTAMP)
             AND (p.created_at >= datetime('now', '-14 days'))
           ORDER BY (p.urgency = 'urgent') DESC, p.created_at DESC"""
    )

    # Calculate real-time distance and jitter coordinates for privacy
    posts = []
    for p in raw_posts:
        p_dict = dict(p)
        # Jitter coordinates slightly (~100m) so exact home coordinates aren't publicly exposed
        p_dict["latitude"] = jitter_coordinate(p_dict.get("latitude"))
        p_dict["longitude"] = jitter_coordinate(p_dict.get("longitude"))

        if user_lat is not None and user_lng is not None and p_dict.get("latitude") and p_dict.get("longitude"):
            dist = haversine_km(user_lat, user_lng, p_dict["latitude"], p_dict["longitude"])
            p_dict["distance_km"] = dist
        else:
            p_dict["distance_km"] = None
        posts.append(p_dict)

    # Sort by urgency first, then nearest distance if user has coordinates
    if user_lat is not None and user_lng is not None:
        posts.sort(key=lambda x: (
            0 if x.get("urgency") == "urgent" else 1,
            x["distance_km"] if x["distance_km"] is not None else 999999
        ))

    # Total completed acts of community mutual aid in the network
    impact_rows = db.execute("SELECT COUNT(*) AS count FROM posts WHERE status = 'completed'")
    impact_count = impact_rows[0]["count"] if impact_rows else 0

    categories = db.execute("SELECT id, name, icon FROM categories ORDER BY name ASC")

    return render_template(
        "index.html",
        posts=posts,
        categories=categories,
        impact_count=impact_count,
        user_loc_name=user_loc_name,
        user_lat=user_lat,
        user_lng=user_lng,
        has_real_coords=bool(user_lat and user_lng)
    )


@app.route("/api/user/location", methods=["POST"])
def update_user_location():
    """Production endpoint: Update user's live detected latitude, longitude, and reverse-geocoded locality"""
    if not verify_csrf():
        return jsonify({"error": "Invalid CSRF token"}), 400

    data = request.get_json() or {}
    try:
        lat = float(data.get("latitude"))
        lng = float(data.get("longitude"))
        # Range validation
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            return jsonify({"error": "Coordinates out of bounds"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid GPS coordinates"}), 400

    locality_name = data.get("locality_name") or data.get("city") or "Your Current Location"

    session["user_lat"] = lat
    session["user_lng"] = lng
    session["user_loc_name"] = locality_name
    session["has_location"] = True

    # If user is logged in, persist to database
    if session.get("user_id"):
        db.execute(
            """UPDATE users 
               SET latitude = ?, longitude = ?, neighborhood = COALESCE(?, neighborhood) 
               WHERE id = ?""",
            lat, lng, locality_name if locality_name != "Your Current Location" else None, session["user_id"]
        )

    return jsonify({
        "status": "success", 
        "latitude": lat, 
        "longitude": lng, 
        "locality": locality_name
    })


@app.route("/api/posts")
def api_posts():
    """
    Production GeoJSON-style endpoint: returns posts sorted by real-time distance,
    radius filtering, and multi-parameter query filtering with coordinate privacy jitter.
    """
    query = request.args.get("q", "").strip()
    post_type = request.args.get("type", "all")
    category_id = request.args.get("category", "all")
    radius_km = request.args.get("radius", type=float)
    sort_by = request.args.get("sort", "nearest") # nearest, newest, urgent

    # Caller's coordinates
    caller_lat = request.args.get("lat", type=float) or session.get("user_lat")
    caller_lng = request.args.get("lng", type=float) or session.get("user_lng")
    neighborhood = request.args.get("neighborhood")

    sql = """
        SELECT p.id, p.title, p.description, p.post_type, p.urgency, p.created_at,
               p.category_id, p.location_details, p.latitude, p.longitude, p.neighborhood,
               c.name AS category, c.icon AS category_icon, u.username
        FROM posts p
        JOIN users u ON u.id = p.user_id
        JOIN categories c ON c.id = p.category_id
        WHERE p.status = 'open'
          AND p.is_hidden = 0
          AND p.is_flagged = 0
          AND (p.expires_at IS NULL OR p.expires_at > CURRENT_TIMESTAMP)
          AND (p.created_at >= datetime('now', '-14 days'))
    """
    params = []

    if neighborhood:
        sql += " AND p.neighborhood = ?"
        params.append(neighborhood)

    if post_type in ["request", "offer"]:
        sql += " AND p.post_type = ?"
        params.append(post_type)

    if category_id and category_id != "all":
        sql += " AND p.category_id = ?"
        params.append(category_id)

    if query:
        sql += " AND (p.title LIKE ? OR p.description LIKE ? OR p.location_details LIKE ? OR p.neighborhood LIKE ?)"
        keyword = f"%{query}%"
        params.extend([keyword, keyword, keyword, keyword])

    raw_rows = db.execute(sql, *params)
    results = []

    for r in raw_rows:
        row_dict = dict(r)
        # Apply coordinate privacy jitter
        row_dict["latitude"] = jitter_coordinate(row_dict.get("latitude"))
        row_dict["longitude"] = jitter_coordinate(row_dict.get("longitude"))

        if caller_lat is not None and caller_lng is not None and row_dict.get("latitude") and row_dict.get("longitude"):
            dist = haversine_km(caller_lat, caller_lng, row_dict["latitude"], row_dict["longitude"])
            row_dict["distance_km"] = dist
        else:
            row_dict["distance_km"] = None

        # Filter by radius if requested and distance known
        if radius_km and row_dict["distance_km"] is not None:
            if row_dict["distance_km"] > radius_km:
                continue

        results.append(row_dict)

    # Sorting
    if sort_by == "newest":
        results.sort(key=lambda x: x["created_at"], reverse=True)
    elif sort_by == "urgent":
        results.sort(key=lambda x: (0 if x.get("urgency") == "urgent" else 1, x["created_at"]), reverse=False)
    else: # nearest default
        if caller_lat is not None and caller_lng is not None:
            results.sort(key=lambda x: (
                0 if x.get("urgency") == "urgent" else 1,
                x["distance_km"] if x["distance_km"] is not None else 999999
            ))

    return jsonify(results)


# ==============================================================================
# AUTHENTICATION
# ==============================================================================
@app.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def register():
    """Register user with input validation and password hashing"""
    if request.method == "POST":
        if not verify_csrf():
            return apology("Invalid security token", 400)

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        neighborhood = request.form.get("neighborhood", "").strip()
        pincode = request.form.get("pincode", "").strip()
        phone = request.form.get("phone", "").strip()
        bio = request.form.get("bio", "").strip()
        lat_raw = request.form.get("latitude", "").strip()
        lng_raw = request.form.get("longitude", "").strip()
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not email or not neighborhood or not password:
            return apology("Must provide username, email, neighborhood, and password", 400)

        if len(username) > 30 or len(email) > 80:
            return apology("Username or email exceeds maximum length limit", 400)

        if len(password) < 8:
            return apology("Password must be at least 8 characters long", 400)

        if password != confirmation:
            return apology("Passwords do not match", 400)

        existing = db.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            username, email
        )
        if existing:
            return apology("Username or email already registered", 400)

        latitude = None
        longitude = None
        try:
            if lat_raw and lng_raw:
                latitude = float(lat_raw)
                longitude = float(lng_raw)
                if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
                    latitude, longitude = None, None
        except ValueError:
            pass

        # Hash with werkzeug.security (scrypt)
        pw_hash = generate_password_hash(password)
        user_id = db.execute(
            """INSERT INTO users (username, email, hash, neighborhood, pincode, phone, bio, latitude, longitude)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            username, email, pw_hash, neighborhood, pincode, phone, bio, latitude, longitude
        )

        session.clear()
        session["user_id"] = user_id
        session["username"] = username
        session["neighborhood"] = neighborhood
        session["user_loc_name"] = neighborhood
        session["user_lat"] = latitude
        session["user_lng"] = longitude
        session["has_location"] = bool(latitude and longitude)
        session["is_admin"] = 0
        session["csrf_token"] = secrets.token_hex(16)

        flash(f"Swagat hai! Welcome to NeighborGrid, {username}!", "success")
        return redirect("/")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("15 per minute")
def login():
    """Log user in with safe redirect to next URL"""
    next_url = request.args.get("next") or request.form.get("next")
    if not is_safe_url(next_url):
        next_url = "/"

    if request.method == "POST":
        if not verify_csrf():
            return apology("Invalid security token", 400)

        username = request.form.get("username", "").strip()
        password = request.form.get("password")

        if not username or not password:
            return apology("Must provide username and password", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("Invalid username and/or password", 403)

        user = rows[0]
        if user.get("is_banned"):
            return apology("Your account has been suspended for community guidelines violations.", 403)

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["neighborhood"] = user["neighborhood"]
        session["user_loc_name"] = user["neighborhood"]
        session["is_admin"] = user["is_admin"]
        session["csrf_token"] = secrets.token_hex(16)

        if user.get("latitude") and user.get("longitude"):
            session["user_lat"] = user["latitude"]
            session["user_lng"] = user["longitude"]
            session["has_location"] = True
        else:
            session["has_location"] = False

        flash(f"Welcome back, {user['username']}! Namaste.", "success")
        return redirect(next_url)

    return render_template("login.html", next=next_url)


@app.route("/logout", methods=["POST", "GET"])
def logout():
    """Log user out"""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect("/")


@app.route("/guidelines")
def guidelines():
    """Community Guidelines and safety principles"""
    return render_template("guidelines.html")


# ==============================================================================
# POSTS & MUTUAL-AID LIFECYCLE
# ==============================================================================
@app.route("/post/new", methods=["GET", "POST"])
@login_required
@limiter.limit("20 per minute")
def new_post():
    """Create a new mutual-aid request or offer with commercial content enforcement"""
    if request.method == "POST":
        if not verify_csrf():
            return apology("Invalid security token", 400)

        post_type = request.form.get("post_type")
        category_id = request.form.get("category_id")
        urgency = request.form.get("urgency", "standard")
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location_details = request.form.get("location_details", "").strip()
        lat_raw = request.form.get("latitude", "").strip()
        lng_raw = request.form.get("longitude", "").strip()
        expires_at = request.form.get("expires_at") or None

        if post_type not in ["request", "offer"]:
            return apology("Invalid post type", 400)

        if not title or len(title) > 120:
            return apology("Title is required and must be under 120 characters", 400)

        if not description or len(description) > 2000:
            return apology("Description is required and must be under 2000 characters", 400)

        # ----------------------------------------------------------------------
        # ENFORCE NO BUYING / SELLING (COMMERCIAL CONTENT FILTER)
        # ----------------------------------------------------------------------
        is_comm, match_term = check_commercial_content(title, description, location_details)
        if is_comm:
            return apology(
                f"NeighborGrid is strictly non-commercial. Buying, selling, pricing, or payment language ('{match_term}') is not permitted. Please remove any prices or commercial terms.",
                400
            )

        cat_rows = db.execute("SELECT id FROM categories WHERE id = ?", category_id)
        if not cat_rows:
            return apology("Invalid category selected", 400)

        latitude = None
        longitude = None
        try:
            if lat_raw and lng_raw:
                latitude = float(lat_raw)
                longitude = float(lng_raw)
                if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
                    latitude, longitude = None, None
        except ValueError:
            pass

        # Fallback to user's saved location coordinates if not manually entered
        if latitude is None and session.get("user_lat"):
            latitude = session.get("user_lat")
            longitude = session.get("user_lng")

        user_neighborhood = session.get("user_loc_name") or session.get("neighborhood", "Local Area")
        post_id = db.execute(
            """INSERT INTO posts (user_id, post_type, category_id, title, description, urgency, neighborhood, location_details, latitude, longitude, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            session["user_id"], post_type, category_id, title, description, urgency, user_neighborhood, location_details, latitude, longitude, expires_at
        )

        flash("Your post is now live on the mohalla map!", "success")
        return redirect(f"/post/{post_id}")

    categories = db.execute("SELECT * FROM categories ORDER BY id ASC")
    return render_template("new_post.html", categories=categories)


@app.route("/post/<int:post_id>")
def post_detail(post_id):
    """
    View post details, small embedded map, poster's reputation badge,
    direct messages thread, ratings, and contextual CTA.
    """
    posts = db.execute(
        """SELECT p.*, c.name AS category, c.icon AS category_icon, u.username, u.email, u.phone, u.created_at AS user_joined
           FROM posts p
           JOIN users u ON u.id = p.user_id
           JOIN categories c ON c.id = p.category_id
           WHERE p.id = ?""",
        post_id
    )
    if not posts:
        return render_template("404.html"), 404

    post = posts[0]
    user_id = session.get("user_id")
    is_owner = (user_id == post["user_id"])

    # If hidden or flagged, only admin or author can view
    if (post["is_hidden"] or post.get("is_flagged")) and not is_owner and not session.get("is_admin"):
        return apology("This post has been removed or flagged for review by community moderators", 404)

    # Calculate distance from viewer
    distance_km = None
    if session.get("user_lat") and session.get("user_lng") and post.get("latitude") and post.get("longitude"):
        distance_km = haversine_km(session["user_lat"], session["user_lng"], post["latitude"], post["longitude"])

    # Jitter coordinates for public display
    post_display_lat = jitter_coordinate(post.get("latitude"))
    post_display_lng = jitter_coordinate(post.get("longitude"))

    # Fetch poster's reputation stats (completed acts + average rating)
    poster_stats = db.execute(
        """SELECT 
               (SELECT COUNT(DISTINCT p2.id) FROM posts p2 
                LEFT JOIN matches m2 ON m2.post_id = p2.id AND m2.status = 'accepted'
                WHERE p2.status = 'completed' AND (p2.user_id = ? OR m2.responder_id = ?)) AS completed_count,
               (SELECT AVG(r.score) FROM ratings r WHERE r.recipient_id = ?) AS avg_rating,
               (SELECT COUNT(r.id) FROM ratings r WHERE r.recipient_id = ?) AS rating_count
        """,
        post["user_id"], post["user_id"], post["user_id"], post["user_id"]
    )
    poster_completed_count = poster_stats[0]["completed_count"] if poster_stats else 0
    poster_avg_rating = round(poster_stats[0]["avg_rating"], 1) if (poster_stats and poster_stats[0]["avg_rating"]) else None
    poster_rating_count = poster_stats[0]["rating_count"] if poster_stats else 0

    # Owner view of responses
    responses = []
    if is_owner:
        responses = db.execute(
            """SELECT m.*, u.username, u.email, u.phone
               FROM matches m
               JOIN users u ON u.id = m.responder_id
               WHERE m.post_id = ?
               ORDER BY m.created_at DESC""",
            post_id
        )

    # Check if current visitor has responded
    user_match = None
    if user_id and not is_owner:
        match_rows = db.execute(
            "SELECT * FROM matches WHERE post_id = ? AND responder_id = ?",
            post_id, user_id
        )
        if match_rows:
            user_match = match_rows[0]

    # Check for accepted match to reveal contact details and in-app chat
    # STRICT SERVER-SIDE ENFORCEMENT: Contact details are ONLY selected if match is accepted!
    accepted_match = None
    acc_rows = db.execute(
        """SELECT m.*, u.username AS responder_username, u.email AS responder_email, u.phone AS responder_phone
           FROM matches m
           JOIN users u ON u.id = m.responder_id
           WHERE m.post_id = ? AND m.status = 'accepted'""",
        post_id
    )
    if acc_rows:
        accepted_match = acc_rows[0]

    is_accepted_responder = bool(accepted_match and user_id == accepted_match["responder_id"])
    can_chat = bool(is_owner or is_accepted_responder) and bool(accepted_match)

    # Fetch in-app messages if accepted match exists
    messages = []
    if can_chat:
        messages = db.execute(
            """SELECT msg.*, u.username AS sender_username
               FROM messages msg
               JOIN users u ON u.id = msg.sender_id
               WHERE msg.post_id = ?
               ORDER BY msg.created_at ASC""",
            post_id
        )
        # Mark messages to current user as read
        if user_id:
            db.execute("UPDATE messages SET is_read = 1 WHERE post_id = ? AND receiver_id = ?", post_id, user_id)

    # Fetch ratings / reviews if completed
    ratings = []
    user_has_rated = False
    if post["status"] == "completed":
        ratings = db.execute(
            """SELECT r.*, u_rater.username AS rater_username, u_rec.username AS recipient_username
               FROM ratings r
               JOIN users u_rater ON u_rater.id = r.rater_id
               JOIN users u_rec ON u_rec.id = r.recipient_id
               WHERE r.post_id = ?
               ORDER BY r.created_at DESC""",
            post_id
        )
        if user_id:
            rated_rows = db.execute("SELECT id FROM ratings WHERE post_id = ? AND rater_id = ?", post_id, user_id)
            user_has_rated = bool(rated_rows)

    return render_template(
        "post_detail.html",
        post=post,
        is_owner=is_owner,
        distance_km=distance_km,
        post_display_lat=post_display_lat,
        post_display_lng=post_display_lng,
        poster_completed_count=poster_completed_count,
        poster_avg_rating=poster_avg_rating,
        poster_rating_count=poster_rating_count,
        responses=responses,
        user_match=user_match,
        accepted_match=accepted_match,
        is_accepted_responder=is_accepted_responder,
        can_chat=can_chat,
        messages=messages,
        ratings=ratings,
        user_has_rated=user_has_rated
    )


@app.route("/post/<int:post_id>/messages", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def send_message(post_id):
    """Send in-app direct message between post owner and accepted helper"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    post_rows = db.execute("SELECT * FROM posts WHERE id = ?", post_id)
    if not post_rows:
        return apology("Post not found", 404)
    post = post_rows[0]

    acc_rows = db.execute(
        "SELECT * FROM matches WHERE post_id = ? AND status = 'accepted'",
        post_id
    )
    if not acc_rows:
        return apology("Chat is only enabled once a match is accepted", 403)

    accepted_match = acc_rows[0]
    user_id = session["user_id"]

    if user_id == post["user_id"]:
        receiver_id = accepted_match["responder_id"]
    elif user_id == accepted_match["responder_id"]:
        receiver_id = post["user_id"]
    else:
        return apology("You are not part of this accepted mutual-aid match", 403)

    content = request.form.get("content", "").strip()
    if not content or len(content) > 1000:
        return apology("Message must be between 1 and 1000 characters", 400)

    db.execute(
        """INSERT INTO messages (post_id, sender_id, receiver_id, content)
           VALUES (?, ?, ?, ?)""",
        post_id, user_id, receiver_id, content
    )

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"status": "ok", "sender": session["username"], "content": content})

    flash("Message sent to your neighbor!", "success")
    return redirect(f"/post/{post_id}#chatSection")


@app.route("/post/<int:post_id>/rate", methods=["POST"])
@login_required
def rate_match(post_id):
    """Leave a star rating and review after post completion"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    post_rows = db.execute("SELECT * FROM posts WHERE id = ?", post_id)
    if not post_rows or post_rows[0]["status"] != "completed":
        return apology("You can only rate completed collaborations", 400)
    post = post_rows[0]

    acc_rows = db.execute("SELECT * FROM matches WHERE post_id = ? AND status = 'accepted'", post_id)
    if not acc_rows:
        return apology("No accepted match found to review", 400)

    accepted_match = acc_rows[0]
    user_id = session["user_id"]

    if user_id == post["user_id"]:
        recipient_id = accepted_match["responder_id"]
    elif user_id == accepted_match["responder_id"]:
        recipient_id = post["user_id"]
    else:
        return apology("Only participants in this match can submit a review", 403)

    try:
        score = int(request.form.get("score", 5))
        if score < 1 or score > 5:
            return apology("Score must be between 1 and 5", 400)
    except ValueError:
        return apology("Invalid rating score", 400)

    feedback = request.form.get("feedback", "").strip()

    try:
        db.execute(
            """INSERT INTO ratings (post_id, rater_id, recipient_id, score, feedback)
               VALUES (?, ?, ?, ?, ?)""",
            post_id, user_id, recipient_id, score, feedback
        )
        flash("Dhanyavaad! Your review and star rating has been published.", "success")
    except Exception:
        flash("You have already submitted a rating for this collaboration.", "info")

    return redirect(f"/post/{post_id}")


@app.route("/post/<int:post_id>/respond", methods=["POST"])
@login_required
@limiter.limit("15 per minute")
def respond_post(post_id):
    """Respond to a neighbor's post"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    post_rows = db.execute("SELECT user_id, status FROM posts WHERE id = ?", post_id)
    if not post_rows:
        return apology("Post not found", 404)

    post = post_rows[0]
    if post["status"] != "open":
        return apology("This post is no longer accepting responses", 400)

    if post["user_id"] == session["user_id"]:
        return apology("You cannot respond to your own post", 400)

    message = request.form.get("message", "").strip()
    if len(message) > 500:
        return apology("Message exceeds 500 characters limit", 400)

    try:
        db.execute(
            """INSERT INTO matches (post_id, responder_id, message)
               VALUES (?, ?, ?)""",
            post_id, session["user_id"], message
        )
    except Exception:
        flash("You have already submitted an offer on this post.", "info")
        return redirect(f"/post/{post_id}")

    flash("Your offer has been sent to the neighbor!", "success")
    return redirect(f"/post/{post_id}")


@app.route("/match/<int:match_id>/accept", methods=["POST"])
@login_required
def accept_match(match_id):
    """Accept a response and unlock direct messaging and contact info (Owner only)"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    rows = db.execute(
        """SELECT m.id, m.post_id, p.user_id AS owner, p.status
           FROM matches m JOIN posts p ON p.id = m.post_id
           WHERE m.id = ?""",
        match_id
    )
    if not rows or rows[0]["owner"] != session["user_id"] or rows[0]["status"] != "open":
        return apology("Unauthorized action on this post", 403)

    post_id = rows[0]["post_id"]
    db.execute("UPDATE matches SET status = 'accepted' WHERE id = ?", match_id)
    db.execute("UPDATE matches SET status = 'declined' WHERE post_id = ? AND id != ?", post_id, match_id)
    db.execute("UPDATE posts SET status = 'in_progress' WHERE id = ?", post_id)

    flash("Neighbor response accepted! Contact details and direct chat are now unlocked below.", "success")
    return redirect(f"/post/{post_id}")


@app.route("/match/<int:match_id>/decline", methods=["POST"])
@login_required
def decline_match(match_id):
    """Decline a response (Owner only)"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    rows = db.execute(
        """SELECT m.id, m.post_id, p.user_id AS owner
           FROM matches m JOIN posts p ON p.id = m.post_id
           WHERE m.id = ?""", match_id
    )
    if not rows or rows[0]["owner"] != session["user_id"]:
        return apology("Unauthorized action", 403)

    post_id = rows[0]["post_id"]
    db.execute("UPDATE matches SET status = 'declined' WHERE id = ?", match_id)
    flash("Response declined.", "info")
    return redirect(f"/post/{post_id}")


@app.route("/post/<int:post_id>/complete", methods=["POST"])
@login_required
def complete_post(post_id):
    """Mark an in_progress post as completed (Owner only)"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    rows = db.execute("SELECT user_id, status FROM posts WHERE id = ?", post_id)
    if not rows or rows[0]["user_id"] != session["user_id"]:
        return apology("Unauthorized action: only post creator can mark as completed", 403)

    if rows[0]["status"] != "in_progress":
        return apology("Only in-progress posts can be marked as completed", 400)

    db.execute(
        "UPDATE posts SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        post_id
    )
    flash("Bahut badhiya! Mutual aid completed. Please leave a rating and review below.", "success")
    return redirect(f"/post/{post_id}")


@app.route("/post/<int:post_id>/cancel", methods=["POST"])
@login_required
def cancel_post(post_id):
    """Cancel an open or in_progress post (Owner only)"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    rows = db.execute("SELECT user_id, status FROM posts WHERE id = ?", post_id)
    if not rows or rows[0]["user_id"] != session["user_id"]:
        return apology("Unauthorized action: only post creator can cancel", 403)

    if rows[0]["status"] not in ["open", "in_progress"]:
        return apology("Cannot cancel a completed or already cancelled post", 400)

    db.execute("UPDATE posts SET status = 'cancelled' WHERE id = ?", post_id)
    flash("Post has been cancelled.", "info")
    return redirect(f"/post/{post_id}")


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    """Delete a post permanently (Owner or Admin only)"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    rows = db.execute("SELECT user_id FROM posts WHERE id = ?", post_id)
    if not rows:
        return apology("Post not found", 404)

    if rows[0]["user_id"] != session["user_id"] and not session.get("is_admin"):
        return apology("Unauthorized action", 403)

    db.execute("DELETE FROM posts WHERE id = ?", post_id)
    flash("Post has been permanently removed.", "info")
    return redirect("/dashboard")


@app.route("/post/<int:post_id>/repost", methods=["POST"])
@login_required
def repost_post(post_id):
    """Renew/repost an open post that had auto-expired (Owner only)"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    rows = db.execute("SELECT * FROM posts WHERE id = ?", post_id)
    if not rows or rows[0]["user_id"] != session["user_id"]:
        return apology("Unauthorized action", 403)

    db.execute("UPDATE posts SET created_at = CURRENT_TIMESTAMP WHERE id = ?", post_id)
    flash("Post has been renewed and brought back to the top of the mohalla feed!", "success")
    return redirect(f"/post/{post_id}")


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    """Edit title, description, category, and location while post is still open (Owner only)"""
    rows = db.execute("SELECT * FROM posts WHERE id = ?", post_id)
    if not rows or rows[0]["user_id"] != session["user_id"]:
        return apology("Unauthorized action: you can only edit your own posts", 403)

    post = rows[0]
    if post["status"] != "open":
        return apology("Only open posts can be edited", 400)

    if request.method == "POST":
        if not verify_csrf():
            return apology("Invalid security token", 400)

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location_details = request.form.get("location_details", "").strip()
        lat_raw = request.form.get("latitude", "").strip()
        lng_raw = request.form.get("longitude", "").strip()
        category_id = request.form.get("category_id")
        urgency = request.form.get("urgency", "standard")

        if not title or len(title) > 120:
            return apology("Title is required and must be under 120 characters", 400)
        if not description or len(description) > 2000:
            return apology("Description is required and must be under 2000 characters", 400)

        # ----------------------------------------------------------------------
        # ENFORCE NO BUYING / SELLING (COMMERCIAL CONTENT FILTER ON EDIT)
        # ----------------------------------------------------------------------
        is_comm, match_term = check_commercial_content(title, description, location_details)
        if is_comm:
            return apology(
                f"NeighborGrid is strictly non-commercial. Buying, selling, pricing, or payment language ('{match_term}') is not permitted. Please remove any prices or commercial terms.",
                400
            )

        latitude = None
        longitude = None
        try:
            if lat_raw and lng_raw:
                latitude = float(lat_raw)
                longitude = float(lng_raw)
                if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
                    latitude, longitude = None, None
        except ValueError:
            pass

        db.execute(
            """UPDATE posts 
               SET title = ?, description = ?, category_id = ?, urgency = ?, location_details = ?, latitude = ?, longitude = ?
               WHERE id = ?""",
            title, description, category_id, urgency, location_details, latitude, longitude, post_id
        )
        flash("Post updated successfully.", "success")
        return redirect(f"/post/{post_id}")

    categories = db.execute("SELECT * FROM categories ORDER BY id ASC")
    return render_template("edit_post.html", post=post, categories=categories)


@app.route("/dashboard")
@login_required
def dashboard():
    """User dashboard: My Posts, Offers I Made, Responses to My Posts, Completed, Repost options"""
    user_id = session["user_id"]

    my_posts = db.execute(
        """SELECT p.*, c.name AS category,
                  CASE WHEN p.status = 'open' AND (p.created_at < datetime('now', '-14 days')) THEN 1 ELSE 0 END AS is_expired
           FROM posts p
           JOIN categories c ON c.id = p.category_id
           WHERE p.user_id = ? 
           ORDER BY p.created_at DESC""",
        user_id
    )

    incoming_responses = db.execute(
        """SELECT m.id, m.post_id, m.message, m.status, m.created_at,
                  p.title AS post_title, p.status AS post_status, p.post_type,
                  u.username AS responder_username
           FROM matches m
           JOIN posts p ON p.id = m.post_id
           JOIN users u ON u.id = m.responder_id
           WHERE p.user_id = ?
           ORDER BY m.created_at DESC""",
        user_id
    )

    sent_responses = db.execute(
        """SELECT m.id, m.post_id, m.status, m.created_at,
                  p.title AS post_title, u.username AS owner_username
           FROM matches m
           JOIN posts p ON p.id = m.post_id
           JOIN users u ON u.id = p.user_id
           WHERE m.responder_id = ?
           ORDER BY m.created_at DESC""",
        user_id
    )

    received_ratings = db.execute(
        """SELECT r.*, u.username AS rater_username, p.title AS post_title
           FROM ratings r
           JOIN users u ON u.id = r.rater_id
           JOIN posts p ON p.id = r.post_id
           WHERE r.recipient_id = ?
           ORDER BY r.created_at DESC""",
        user_id
    )

    return render_template(
        "dashboard.html",
        my_posts=my_posts,
        incoming_responses=incoming_responses,
        sent_responses=sent_responses,
        received_ratings=received_ratings
    )


@app.route("/profile/<username>")
def profile(username):
    """
    Public profile with neighbors-helped counter and average star ratings.
    PRIVACY AUDIT: Strictly excludes phone, email, and exact coordinates.
    """
    users = db.execute(
        "SELECT id, username, neighborhood, bio, is_admin, created_at FROM users WHERE username = ?",
        username
    )
    if not users:
        return render_template("404.html"), 404

    profile_user = users[0]

    helped_rows = db.execute(
        """SELECT COUNT(DISTINCT p.id) AS count
           FROM posts p
           LEFT JOIN matches m ON m.post_id = p.id AND m.status = 'accepted'
           WHERE p.status = 'completed' AND (p.user_id = ? OR m.responder_id = ?)""",
        profile_user["id"], profile_user["id"]
    )
    helped_count = helped_rows[0]["count"] if helped_rows else 0

    rating_stats = db.execute(
        """SELECT AVG(score) AS avg_score, COUNT(id) AS review_count
           FROM ratings
           WHERE recipient_id = ?""",
        profile_user["id"]
    )
    avg_score = round(rating_stats[0]["avg_score"], 1) if (rating_stats and rating_stats[0]["avg_score"]) else None
    review_count = rating_stats[0]["review_count"] if rating_stats else 0

    reviews = db.execute(
        """SELECT r.*, u.username AS rater_username, p.title AS post_title
           FROM ratings r
           JOIN users u ON u.id = r.rater_id
           JOIN posts p ON p.id = r.post_id
           WHERE r.recipient_id = ?
           ORDER BY r.created_at DESC""",
        profile_user["id"]
    )

    active_posts = db.execute(
        """SELECT p.*, c.name AS category, c.icon AS category_icon
           FROM posts p
           JOIN categories c ON c.id = p.category_id
           WHERE p.user_id = ? AND p.status = 'open' AND p.is_hidden = 0 AND p.is_flagged = 0
           ORDER BY p.created_at DESC""",
        profile_user["id"]
    )

    return render_template(
        "profile.html",
        profile_user=profile_user,
        helped_count=helped_count,
        avg_score=avg_score,
        review_count=review_count,
        reviews=reviews,
        active_posts=active_posts
    )


# ==============================================================================
# MODERATION & REPORTS
# ==============================================================================
@app.route("/post/<int:post_id>/report", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def report_post(post_id):
    """Report a post for moderation review"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    reason = request.form.get("reason", "").strip()
    if not reason or len(reason) > 500:
        return apology("A valid reason under 500 characters is required to report a post", 400)

    try:
        db.execute(
            """INSERT INTO reports (post_id, reporter_id, reason)
               VALUES (?, ?, ?)""",
            post_id, session["user_id"], reason
        )
        # Mark post as flagged for moderator review
        db.execute("UPDATE posts SET is_flagged = 1 WHERE id = ?", post_id)
        flash("Thank you for reporting. Our Resident Welfare moderation team has been alerted.", "info")
    except Exception:
        flash("You have already reported this post.", "warning")

    return redirect(f"/post/{post_id}")


@app.route("/admin/reports")
@admin_required
def admin_reports():
    """Admin moderation review page with dismiss, remove, and ban actions"""
    reports = db.execute(
        """SELECT r.id AS report_id, r.reason, r.created_at,
                  p.id AS post_id, p.title AS post_title, p.neighborhood, p.is_hidden, p.is_flagged,
                  u_author.id AS author_id, u_author.username AS author_username, u_author.is_banned AS author_is_banned,
                  u_reporter.username AS reporter_username
           FROM reports r
           JOIN posts p ON p.id = r.post_id
           JOIN users u_author ON u_author.id = p.user_id
           JOIN users u_reporter ON u_reporter.id = r.reporter_id
           ORDER BY r.created_at DESC"""
    )
    return render_template("admin_reports.html", reports=reports)


@app.route("/admin/report/<int:report_id>/dismiss", methods=["POST"])
@admin_required
def admin_dismiss_report(report_id):
    """Dismiss a report and restore post if flagged"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    report_rows = db.execute("SELECT post_id FROM reports WHERE id = ?", report_id)
    if report_rows:
        post_id = report_rows[0]["post_id"]
        db.execute("UPDATE posts SET is_flagged = 0 WHERE id = ?", post_id)
        db.execute("DELETE FROM reports WHERE id = ?", report_id)
        flash("Report dismissed. Post has been cleared.", "success")
    return redirect("/admin/reports")


@app.route("/admin/post/<int:post_id>/hide", methods=["POST"])
@admin_required
def admin_hide_post(post_id):
    """Admin hide a post from feeds"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    db.execute("UPDATE posts SET is_hidden = 1 WHERE id = ?", post_id)
    flash(f"Post #{post_id} has been hidden from all mohalla feeds.", "success")
    return redirect("/admin/reports")


@app.route("/admin/post/<int:post_id>/unhide", methods=["POST"])
@admin_required
def admin_unhide_post(post_id):
    """Admin unhide a post"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    db.execute("UPDATE posts SET is_hidden = 0, is_flagged = 0 WHERE id = ?", post_id)
    flash(f"Post #{post_id} has been restored to visible status.", "success")
    return redirect("/admin/reports")


@app.route("/admin/post/<int:post_id>/delete", methods=["POST"])
@admin_required
def admin_delete_post(post_id):
    """Admin delete a post permanently"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    db.execute("DELETE FROM posts WHERE id = ?", post_id)
    flash(f"Post #{post_id} permanently removed.", "success")
    return redirect("/admin/reports")


@app.route("/admin/user/<int:user_id>/ban", methods=["POST"])
@admin_required
def admin_ban_user(user_id):
    """Admin ban a user for guideline violations"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    db.execute("UPDATE users SET is_banned = 1 WHERE id = ?", user_id)
    db.execute("UPDATE posts SET is_hidden = 1 WHERE user_id = ?", user_id)
    flash(f"User #{user_id} has been suspended and their posts hidden.", "warning")
    return redirect("/admin/reports")


# ==============================================================================
# CUSTOM ERROR HANDLERS (404, 500)
# ==============================================================================
@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
