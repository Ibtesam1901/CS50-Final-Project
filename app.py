import os
import secrets
from functools import wraps
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from db_helper import SQL_PROVIDER
from helpers import apology, login_required, admin_required

# Configure application
app = Flask(__name__)

# Ensure secret key is configured (environment variable with secure fallback)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Connect to database using SQL provider
db = SQL_PROVIDER("sqlite:///neighborgrid.db")

# CSRF helper generator
@app.before_request
def ensure_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)


def verify_csrf():
    token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
    if not token or token != session.get("csrf_token"):
        return False
    return True


@app.route("/")
def index():
    """Display neighborhood feed with urgency prioritization and impact counter"""
    user_id = session.get("user_id")
    current_neighborhood = session.get("neighborhood", "Downtown") if user_id else "Downtown"

    # Count completed mutual aid acts in this neighborhood for the impact counter
    impact_rows = db.execute(
        """SELECT COUNT(*) AS count 
           FROM posts 
           WHERE neighborhood = ? AND status = 'completed'""",
        current_neighborhood
    )
    impact_count = impact_rows[0]["count"] if impact_rows else 0

    # Query active, visible, non-expired posts in current neighborhood
    posts = db.execute(
        """SELECT p.id, p.title, p.description, p.post_type, p.urgency, p.created_at,
                  p.category_id, c.name AS category, u.username
           FROM posts p
           JOIN users u ON u.id = p.user_id
           JOIN categories c ON c.id = p.category_id
           WHERE p.neighborhood = ?
             AND p.status = 'open'
             AND p.is_hidden = 0
             AND (p.expires_at IS NULL OR p.expires_at > CURRENT_TIMESTAMP)
           ORDER BY (p.urgency = 'urgent') DESC, p.created_at DESC""",
        current_neighborhood
    )

    categories = db.execute("SELECT id, name FROM categories ORDER BY name ASC")

    return render_template(
        "index.html",
        posts=posts,
        categories=categories,
        impact_count=impact_count,
        current_neighborhood=current_neighborhood
    )


@app.route("/api/posts")
def api_posts():
    """JSON feed endpoint with search and filter parameters"""
    current_neighborhood = session.get("neighborhood", "Downtown")
    query = request.args.get("q", "").strip()
    post_type = request.args.get("type", "all")
    category_id = request.args.get("category", "all")

    sql = """
        SELECT p.id, p.title, p.description, p.post_type, p.urgency, p.created_at,
               c.name AS category, u.username
        FROM posts p
        JOIN users u ON u.id = p.user_id
        JOIN categories c ON c.id = p.category_id
        WHERE p.neighborhood = ?
          AND p.status = 'open'
          AND p.is_hidden = 0
          AND (p.expires_at IS NULL OR p.expires_at > CURRENT_TIMESTAMP)
    """
    params = [current_neighborhood]

    if post_type in ["request", "offer"]:
        sql += " AND p.post_type = ?"
        params.append(post_type)

    if category_id and category_id != "all":
        sql += " AND p.category_id = ?"
        params.append(category_id)

    if query:
        sql += " AND (p.title LIKE ? OR p.description LIKE ?)"
        keyword = f"%{query}%"
        params.extend([keyword, keyword])

    sql += " ORDER BY (p.urgency = 'urgent') DESC, p.created_at DESC"

    rows = db.execute(sql, *params)
    return jsonify(rows)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not verify_csrf():
            return apology("Invalid security token", 400)

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        neighborhood = request.form.get("neighborhood", "").strip()
        pincode = request.form.get("pincode", "").strip()
        phone = request.form.get("phone", "").strip()
        bio = request.form.get("bio", "").strip()
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Step 2.3: Validation in order
        if not username or not email or not neighborhood or not password:
            return apology("Must provide username, email, neighborhood, and password", 400)

        if len(password) < 8:
            return apology("Password must be at least 8 characters long", 400)

        if password != confirmation:
            return apology("Passwords do not match", 400)

        # Check existing username or email
        existing = db.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            username, email
        )
        if existing:
            return apology("Username or email already registered", 400)

        # Store hashed password
        pw_hash = generate_password_hash(password)
        user_id = db.execute(
            """INSERT INTO users (username, email, hash, neighborhood, pincode, phone, bio)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            username, email, pw_hash, neighborhood, pincode, phone, bio
        )

        session.clear()
        session["user_id"] = user_id
        session["username"] = username
        session["neighborhood"] = neighborhood
        session["is_admin"] = 0
        session["csrf_token"] = secrets.token_hex(16)

        flash(f"Welcome to NeighborGrid, {username}!", "success")
        return redirect("/")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    if request.method == "POST":
        if not verify_csrf():
            return apology("Invalid security token", 400)

        username = request.form.get("username", "").strip()
        password = request.form.get("password")

        if not username or not password:
            return apology("Must provide username and password", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Step 2.4: Vague error for wrong credentials
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("Invalid username and/or password", 403)

        user = rows[0]
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["neighborhood"] = user["neighborhood"]
        session["is_admin"] = user["is_admin"]
        session["csrf_token"] = secrets.token_hex(16)

        flash(f"Welcome back, {user['username']}!", "success")
        return redirect("/")

    return render_template("login.html")


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


@app.route("/post/new", methods=["GET", "POST"])
@login_required
def new_post():
    """Create a new mutual-aid request or offer"""
    if request.method == "POST":
        if not verify_csrf():
            return apology("Invalid security token", 400)

        post_type = request.form.get("post_type")
        category_id = request.form.get("category_id")
        urgency = request.form.get("urgency", "standard")
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        expires_at = request.form.get("expires_at") or None

        # Validation
        if post_type not in ["request", "offer"]:
            return apology("Invalid post type", 400)

        if not title or len(title) > 120:
            return apology("Title is required and must be under 120 characters", 400)

        if not description:
            return apology("Description is required", 400)

        cat_rows = db.execute("SELECT id FROM categories WHERE id = ?", category_id)
        if not cat_rows:
            return apology("Invalid category selected", 400)

        user_neighborhood = session.get("neighborhood")
        post_id = db.execute(
            """INSERT INTO posts (user_id, post_type, category_id, title, description, urgency, neighborhood, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            session["user_id"], post_type, category_id, title, description, urgency, user_neighborhood, expires_at
        )

        flash("Your post is now live in your neighborhood feed!", "success")
        return redirect(f"/post/{post_id}")

    categories = db.execute("SELECT * FROM categories ORDER BY id ASC")
    return render_template("new_post.html", categories=categories)


@app.route("/post/<int:post_id>")
def post_detail(post_id):
    """View post details, responses, and privacy contact exchange"""
    posts = db.execute(
        """SELECT p.*, c.name AS category, u.username, u.email, u.phone
           FROM posts p
           JOIN users u ON u.id = p.user_id
           JOIN categories c ON c.id = p.category_id
           WHERE p.id = ?""",
        post_id
    )
    if not posts:
        return apology("Post not found", 404)

    post = posts[0]
    user_id = session.get("user_id")
    is_owner = (user_id == post["user_id"])

    # If post is hidden, only admin or author can view
    if post["is_hidden"] and not is_owner and not session.get("is_admin"):
        return apology("This post has been hidden by moderators", 404)

    # Responses for owner
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

    # Check for accepted match to reveal contact details (Phase 4.4)
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

    is_accepted_responder = (accepted_match and user_id == accepted_match["responder_id"])

    return render_template(
        "post_detail.html",
        post=post,
        is_owner=is_owner,
        responses=responses,
        user_match=user_match,
        accepted_match=accepted_match,
        is_accepted_responder=is_accepted_responder
    )


@app.route("/post/<int:post_id>/respond", methods=["POST"])
@login_required
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
    """Accept a response (Phase 4.3)"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    rows = db.execute(
        """SELECT m.id, m.post_id, p.user_id AS owner, p.status
           FROM matches m JOIN posts p ON p.id = m.post_id
           WHERE m.id = ?""",
        match_id
    )
    if not rows or rows[0]["owner"] != session["user_id"] or rows[0]["status"] != "open":
        return apology("Not allowed", 403)

    post_id = rows[0]["post_id"]
    db.execute("UPDATE matches SET status = 'accepted' WHERE id = ?", match_id)
    db.execute("UPDATE matches SET status = 'declined' WHERE post_id = ? AND id != ?", post_id, match_id)
    db.execute("UPDATE posts SET status = 'in_progress' WHERE id = ?", post_id)

    flash("Neighbor response accepted! Contact details are now unlocked below.", "success")
    return redirect(f"/post/{post_id}")


@app.route("/match/<int:match_id>/decline", methods=["POST"])
@login_required
def decline_match(match_id):
    """Decline a response"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    rows = db.execute(
        """SELECT m.id, m.post_id, p.user_id AS owner
           FROM matches m JOIN posts p ON p.id = m.post_id
           WHERE m.id = ?", match_id)
    """, match_id)
    if not rows or rows[0]["owner"] != session["user_id"]:
        return apology("Not allowed", 403)

    post_id = rows[0]["post_id"]
    db.execute("UPDATE matches SET status = 'declined' WHERE id = ?", match_id)
    flash("Response declined.", "info")
    return redirect(f"/post/{post_id}")


@app.route("/post/<int:post_id>/complete", methods=["POST"])
@login_required
def complete_post(post_id):
    """Mark an in_progress post as completed (poster only)"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    rows = db.execute("SELECT user_id, status FROM posts WHERE id = ?", post_id)
    if not rows or rows[0]["user_id"] != session["user_id"]:
        return apology("Not allowed", 403)

    if rows[0]["status"] != "in_progress":
        return apology("Only in-progress posts can be marked as completed", 400)

    db.execute(
        "UPDATE posts SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        post_id
    )
    flash("Great job! Thank you for completing this neighborly mutual aid.", "success")
    return redirect(f"/post/{post_id}")


@app.route("/post/<int:post_id>/cancel", methods=["POST"])
@login_required
def cancel_post(post_id):
    """Cancel an open or in_progress post (poster only)"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    rows = db.execute("SELECT user_id, status FROM posts WHERE id = ?", post_id)
    if not rows or rows[0]["user_id"] != session["user_id"]:
        return apology("Not allowed", 403)

    if rows[0]["status"] not in ["open", "in_progress"]:
        return apology("Cannot cancel a completed or already cancelled post", 400)

    db.execute("UPDATE posts SET status = 'cancelled' WHERE id = ?", post_id)
    flash("Post has been cancelled.", "info")
    return redirect(f"/post/{post_id}")


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    """Edit title and description while post is still open"""
    rows = db.execute("SELECT * FROM posts WHERE id = ?", post_id)
    if not rows or rows[0]["user_id"] != session["user_id"]:
        return apology("Not allowed", 403)

    post = rows[0]
    if post["status"] != "open":
        return apology("Only open posts can be edited", 400)

    if request.method == "POST":
        if not verify_csrf():
            return apology("Invalid security token", 400)

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category_id = request.form.get("category_id")
        urgency = request.form.get("urgency", "standard")

        if not title or len(title) > 120:
            return apology("Title is required and must be under 120 characters", 400)
        if not description:
            return apology("Description is required", 400)

        db.execute(
            """UPDATE posts SET title = ?, description = ?, category_id = ?, urgency = ?
               WHERE id = ?""",
            title, description, category_id, urgency, post_id
        )
        flash("Post updated successfully.", "success")
        return redirect(f"/post/{post_id}")

    categories = db.execute("SELECT * FROM categories ORDER BY id ASC")
    return render_template("edit_post.html", post=post, categories=categories)


@app.route("/dashboard")
@login_required
def dashboard():
    """User dashboard (Phase 5.1): My Posts, Responses Sent, Incoming Responses"""
    user_id = session["user_id"]

    my_posts = db.execute(
        """SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC""",
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

    return render_template(
        "dashboard.html",
        my_posts=my_posts,
        incoming_responses=incoming_responses,
        sent_responses=sent_responses
    )


@app.route("/profile/<username>")
def profile(username):
    """Public profile with neighbors-helped counter (Phase 5.2)"""
    users = db.execute("SELECT id, username, neighborhood, pincode, bio, is_admin, created_at FROM users WHERE username = ?", username)
    if not users:
        return apology("User not found", 404)

    profile_user = users[0]

    # Count completed posts where user was either the creator or the accepted responder
    helped_rows = db.execute(
        """SELECT COUNT(DISTINCT p.id) AS count
           FROM posts p
           LEFT JOIN matches m ON m.post_id = p.id AND m.status = 'accepted'
           WHERE p.status = 'completed' AND (p.user_id = ? OR m.responder_id = ?)""",
        profile_user["id"], profile_user["id"]
    )
    helped_count = helped_rows[0]["count"] if helped_rows else 0

    active_posts = db.execute(
        """SELECT p.*, c.name AS category
           FROM posts p
           JOIN categories c ON c.id = p.category_id
           WHERE p.user_id = ? AND p.status = 'open' AND p.is_hidden = 0
           ORDER BY p.created_at DESC""",
        profile_user["id"]
    )

    return render_template(
        "profile.html",
        profile_user=profile_user,
        helped_count=helped_count,
        active_posts=active_posts
    )


@app.route("/post/<int:post_id>/report", methods=["POST"])
@login_required
def report_post(post_id):
    """Report a post for moderation review (Phase 7.1)"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    reason = request.form.get("reason", "").strip()
    if not reason:
        return apology("A reason is required to report a post", 400)

    try:
        db.execute(
            """INSERT INTO reports (post_id, reporter_id, reason)
               VALUES (?, ?, ?)""",
            post_id, session["user_id"], reason
        )
        flash("Thank you for reporting. Our moderation team has been alerted.", "info")
    except Exception:
        flash("You have already reported this post.", "warning")

    return redirect(f"/post/{post_id}")


@app.route("/admin/reports")
@admin_required
def admin_reports():
    """Admin moderation review page (Phase 7.2)"""
    reports = db.execute(
        """SELECT r.id AS report_id, r.reason, r.created_at,
                  p.id AS post_id, p.title AS post_title, p.neighborhood, p.is_hidden,
                  u_author.username AS author_username,
                  u_reporter.username AS reporter_username
           FROM reports r
           JOIN posts p ON p.id = r.post_id
           JOIN users u_author ON u_author.id = p.user_id
           JOIN users u_reporter ON u_reporter.id = r.reporter_id
           ORDER BY r.created_at DESC"""
    )
    return render_template("admin_reports.html", reports=reports)


@app.route("/admin/post/<int:post_id>/hide", methods=["POST"])
@admin_required
def admin_hide_post(post_id):
    """Admin hide a post"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    db.execute("UPDATE posts SET is_hidden = 1 WHERE id = ?", post_id)
    flash(f"Post #{post_id} has been hidden from all neighborhood feeds.", "success")
    return redirect("/admin/reports")


@app.route("/admin/post/<int:post_id>/unhide", methods=["POST"])
@admin_required
def admin_unhide_post(post_id):
    """Admin unhide a post"""
    if not verify_csrf():
        return apology("Invalid security token", 400)

    db.execute("UPDATE posts SET is_hidden = 0 WHERE id = ?", post_id)
    flash(f"Post #{post_id} has been restored to visible status.", "success")
    return redirect("/admin/reports")


if __name__ == "__main__":
    app.run(debug=True)
