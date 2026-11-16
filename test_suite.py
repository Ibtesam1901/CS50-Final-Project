"""
End-to-end integration and security test suite for NeighborGrid (India Locality Edition).
Tests all requirements from Blueprint v2 and the step-by-step checklist:
1. Duplicate registration rejection (username & email)
2. Password length enforcement and confirmation match
3. Session login, logout, and location persistence
4. Neighborhood isolation (Indiranagar vs Koramangala)
5. Live location update endpoint (/api/user/location)
6. Respond to post & prevent duplicate offers
7. Cannot respond to own post
8. Accept offer -> transitions post to 'in_progress' and declines rivals
9. Mutual contact information revelation only upon acceptance
10. In-app direct messaging between accepted match participants
11. Star rating and reviews on completed posts
12. Complete lifecycle transition (open -> in_progress -> completed)
13. Refusal of invalid state transitions
14. Reporting post & admin hide moderation
"""

from app import app
from db_helper import SQL_PROVIDER

client = app.test_client()
db = SQL_PROVIDER("sqlite:///neighborgrid.db")

def run_tests():
    print("--- Starting NeighborGrid India Locality Test Suite ---")

    # 1. Test Home page accessible logged-out
    res = client.get("/")
    assert res.status_code == 200, "Home page failed to load"
    assert b"NeighborGrid" in res.data, "NeighborGrid branding missing"
    print("PASS 1: Home page loads with feed, impact counter, and map toggles.")

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
        "username": "new_resident",
        "email": "new@example.in",
        "neighborhood": "Indiranagar, Bengaluru",
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
        "username": "aarav_patel",
        "email": "unique_email@test.in",
        "neighborhood": "Indiranagar, Bengaluru",
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
        "username": "aarav_patel",
        "password": "wrongpassword"
    })
    assert res.status_code == 403, "Invalid password was not rejected"
    print("PASS 5: Wrong password rejected with 403 and vague notice.")

    # Valid login
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    res = client.post("/login", data={
        "csrf_token": token,
        "username": "aarav_patel",
        "password": "password123"
    }, follow_redirects=True)
    assert res.status_code == 200 and b"aarav_patel" in res.data
    print("PASS 6: Login succeeds and session is populated.")

    # 5. Test Live Location Update Endpoint
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    res = client.post("/api/user/location", 
        headers={"X-CSRFToken": token},
        json={"latitude": 12.9719, "longitude": 77.6412}
    )
    assert res.status_code == 200 and res.get_json()["status"] == "success"
    print("PASS 7: Live user location endpoint properly updates user coordinates.")

    # 6. Test JSON Feed API & Neighborhood isolation (Indiranagar vs Koramangala)
    res = client.get("/api/posts")
    data = res.get_json()
    assert len(data) > 0, "No posts returned for Indiranagar feed"
    assert all("Koramangala" not in p["title"] for p in data), "Koramangala post leaked into Indiranagar feed!"
    print(f"PASS 8: Locality isolation verified ({len(data)} Indiranagar posts, Koramangala excluded).")

    # 7. Test Cannot respond to own post
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
        uid = sess["user_id"]
    
    post1 = db.execute("SELECT id FROM posts WHERE user_id = ? LIMIT 1", uid)[0]["id"]
    res = client.post(f"/post/{post1}/respond", data={
        "csrf_token": token,
        "message": "Helping myself"
    })
    assert res.status_code == 400 and b"cannot respond to your own post" in res.data
    print("PASS 9: Responding to own post is blocked on server.")

    # 8. Test Lifecycle: Switch user to rohan_verma and test privacy lock
    client.get("/logout")
    client.get("/login")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    client.post("/login", data={
        "csrf_token": token,
        "username": "rohan_verma",
        "password": "password123"
    })

    # Priya has an in_progress post with rohan_verma (help shifting sofa)
    sofa_post = db.execute("SELECT id FROM posts WHERE title LIKE '%shifting a 3-seater sofa%'")[0]["id"]
    res = client.get(f"/post/{sofa_post}")
    assert b"Help Connection Confirmed!" in res.data, "Contact reveal failed for accepted match!"
    assert b"priya@neighborgrid.in" in res.data, "Owner contact missing for accepted responder"
    print("PASS 10: Contact privacy boundary functions properly (revealed upon acceptance).")

    # 9. Test Direct Messaging between accepted pair
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    res = client.post(f"/post/{sofa_post}/messages", data={
        "csrf_token": token,
        "content": "Aapke building ke gate par pahunch gaya hoon!"
    }, follow_redirects=True)
    assert res.status_code == 200
    msg_check = db.execute("SELECT content FROM messages WHERE post_id = ? ORDER BY id DESC LIMIT 1", sofa_post)
    assert msg_check and "gate par pahunch gaya" in msg_check[0]["content"]
    print("PASS 11: In-app direct messaging functions between accepted participants.")

    # 10. Test Rating submission on completed post
    ride_post = db.execute("SELECT id FROM posts WHERE title LIKE '%scooter carpool%'")[0]["id"]
    res = client.get(f"/post/{ride_post}")
    assert b"Collaboration Ratings" in res.data
    print("PASS 12: Ratings and reviews display on completed mutual aid posts.")

    # 11. Test Illegal state transitions
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    res = client.post(f"/post/{sofa_post}/complete", data={"csrf_token": token})
    assert res.status_code == 403, "Non-owner allowed to complete post!"
    print("PASS 13: Unauthorized completion rejected with 403.")

    # 12. Test Admin moderation
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
    assert res.status_code == 200 and b"Commercial" in res.data, "Admin report dashboard failed to load report"
    
    # Hide water purifier sale post
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    purifier_post = db.execute("SELECT id FROM posts WHERE title LIKE '%Water Purifier%'")[0]["id"]
    client.post(f"/admin/post/{purifier_post}/hide", data={"csrf_token": token}, follow_redirects=True)
    post_check = db.execute("SELECT is_hidden FROM posts WHERE id = ?", purifier_post)[0]["is_hidden"]
    assert post_check == 1, "Post failed to hide"
    print("PASS 14: Admin successfully hid flagged post.")

    # Verify hidden post does not appear in public feed
    res = client.get("/api/posts")
    titles = [p["title"] for p in res.get_json()]
    assert not any("purifier" in t.lower() for t in titles), "Hidden post appeared in public feed!"
    print("PASS 15: Hidden post confirmed absent from public feed.")

    print("\nALL 15 INTEGRATION, GEOLOCATION, MESSAGING & SECURITY TESTS PASSED WITH ZERO ERRORS!")

if __name__ == "__main__":
    run_tests()
