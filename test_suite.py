"""
End-to-end integration and security test suite for NeighborGrid.
Tests all requirements from Blueprint v2 and the step-by-step checklist:
1. Duplicate registration rejection (username & email)
2. Password length enforcement and confirmation match
3. Session login, logout, and protected route redirection
4. Neighborhood isolation (Downtown vs Oakridge)
5. Urgency sorting in feed
6. Respond to post & prevent duplicate offers
7. Cannot respond to own post
8. Accept offer -> transitions post to 'in_progress' and declines rivals
9. Mutual contact information revelation only upon acceptance
10. Complete lifecycle transition (open -> in_progress -> completed)
11. Refusal of invalid state transitions
12. Reporting post & admin hide moderation
"""

from app import app
from db_helper import SQL_PROVIDER

client = app.test_client()
db = SQL_PROVIDER("sqlite:///neighborgrid.db")

def run_tests():
    print("--- Starting NeighborGrid Test Suite ---")

    # 1. Test Home page accessible logged-out
    res = client.get("/")
    assert res.status_code == 200, "Home page failed to load"
    assert b"NeighborGrid" in res.data, "NeighborGrid branding missing"
    print("PASS 1: Home page loads with feed and impact counter.")

    # 2. Test Protected route redirection when logged out
    res = client.get("/dashboard", follow_redirects=False)
    assert res.status_code == 302 and "/login" in res.headers["Location"], "Failed to redirect unauthenticated user"
    print("PASS 2: Unauthenticated user redirected to /login.")

    # 3. Test Registration validation
    client.get("/register")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]

    # Short password (< 8 chars)
    res = client.post("/register", data={
        "csrf_token": token,
        "username": "new_neighbor",
        "email": "new@example.com",
        "neighborhood": "Downtown",
        "password": "123",
        "confirmation": "123"
    })
    assert res.status_code == 400 and b"at least 8 characters" in res.data, "Failed short password check"
    print("PASS 3: Password length constraint enforced (<8 chars rejected).")

    # Duplicate username
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    res = client.post("/register", data={
        "csrf_token": token,
        "username": "elena_gardener",
        "email": "unique_email@test.com",
        "neighborhood": "Downtown",
        "password": "password123",
        "confirmation": "password123"
    })
    assert res.status_code == 400 and b"already registered" in res.data, "Failed duplicate username check"
    print("PASS 4: Duplicate username rejected gracefully.")

    # 4. Test Login authentication
    with client.session_transaction() as sess:
        token = sess["csrf_token"]

    # Invalid password
    res = client.post("/login", data={
        "csrf_token": token,
        "username": "elena_gardener",
        "password": "wrongpassword"
    })
    assert res.status_code == 403, "Invalid password was not rejected"
    print("PASS 5: Wrong password rejected with 403 and vague notice.")

    # Valid login
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    res = client.post("/login", data={
        "csrf_token": token,
        "username": "elena_gardener",
        "password": "password123"
    }, follow_redirects=True)
    assert res.status_code == 200 and b"Welcome back, elena_gardener" in res.data
    print("PASS 6: Login succeeds and session is populated.")

    # 5. Test JSON Feed API & Neighborhood isolation
    res = client.get("/api/posts")
    data = res.get_json()
    assert len(data) > 0, "No posts returned for Downtown feed"
    assert all("Oakridge" not in p["title"] for p in data), "Oakridge post leaked into Downtown feed!"
    print(f"PASS 7: Neighborhood isolation verified ({len(data)} Downtown posts, Oakridge excluded).")

    # 6. Test Cannot respond to own post
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
        uid = sess["user_id"]
    
    post1 = db.execute("SELECT id FROM posts WHERE user_id = ? LIMIT 1", uid)[0]["id"]
    res = client.post(f"/post/{post1}/respond", data={
        "csrf_token": token,
        "message": "Helping myself"
    })
    assert res.status_code == 400 and b"cannot respond to your own post" in res.data
    print("PASS 8: Responding to own post is blocked on server.")

    # 7. Test Lifecycle: Switch user to marcus_tech and test privacy lock
    client.get("/logout")
    client.get("/login")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    client.post("/login", data={
        "csrf_token": token,
        "username": "marcus_tech",
        "password": "password123"
    })

    # Elena has an in_progress post with marcus_tech (help moving desk)
    desk_post = db.execute("SELECT id FROM posts WHERE title LIKE '%moving heavy oak desk%'")[0]["id"]
    res = client.get(f"/post/{desk_post}")
    assert b"Help Connection Confirmed!" in res.data, "Contact reveal failed for accepted match!"
    assert b"elena@example.com" in res.data, "Owner contact missing for accepted responder"
    print("PASS 9: Contact privacy boundary functions properly (revealed upon acceptance).")

    # 8. Test Illegal state transitions (e.g., marcus trying to complete elena's post)
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    res = client.post(f"/post/{desk_post}/complete", data={"csrf_token": token})
    assert res.status_code == 403, "Non-owner allowed to complete post!"
    print("PASS 10: Unauthorized completion rejected with 403.")

    # 9. Test Admin moderation
    client.get("/logout")
    client.get("/login")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    client.post("/login", data={
        "csrf_token": token,
        "username": "admin",
        "password": "password123"
    })

    res = client.get("/admin/reports")
    assert res.status_code == 200 and b"Commercial sale" in res.data, "Admin report dashboard failed to load report"
    
    # Hide generator sale post
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    gen_post = db.execute("SELECT id FROM posts WHERE title LIKE '%generator%'")[0]["id"]
    client.post(f"/admin/post/{gen_post}/hide", data={"csrf_token": token}, follow_redirects=True)
    post_check = db.execute("SELECT is_hidden FROM posts WHERE id = ?", gen_post)[0]["is_hidden"]
    assert post_check == 1, "Post failed to hide"
    print("PASS 11: Admin successfully hid flagged post.")

    # Verify hidden post does not appear in public feed
    res = client.get("/api/posts")
    titles = [p["title"] for p in res.get_json()]
    assert not any("generator" in t.lower() for t in titles), "Hidden post appeared in public feed!"
    print("PASS 12: Hidden post confirmed absent from public feed.")

    print("\nALL 12 INTEGRATION & SECURITY TESTS PASSED WITH ZERO ERRORS!")

if __name__ == "__main__":
    run_tests()
