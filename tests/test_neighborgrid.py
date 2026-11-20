"""
NeighborGrid Unit & Integration Test Suite.
Verifies CS50x final project requirements:
1. Commercial content filter blocks currency & selling phrases.
2. Authorization rules: non-owners cannot edit, cancel, or delete other users' posts.
3. Privacy rules: Contact details are strictly hidden until owner accepts a match.
4. Haversine distance formula accuracy.
5. Coordinate privacy jittering logic.
"""

import pytest
import math
from helpers import check_commercial_content, jitter_coordinate, is_safe_url
from app import app, db, haversine_km


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


# ==============================================================================
# 1. COMMERCIAL CONTENT FILTER TESTS
# ==============================================================================
def test_commercial_filter_blocks_currency_and_selling():
    # Should catch Rs, ₹, selling, cash, etc.
    assert check_commercial_content("Water Purifier for Rs 6500", "Good condition")[0] is True
    assert check_commercial_content("Selling bicycle ₹2000", "fixed price")[0] is True
    assert check_commercial_content("Drill machine for sale", "COD available")[0] is True
    assert check_commercial_content("Need drill", "Will pay 500 INR rent per day")[0] is True
    assert check_commercial_content("Ladder", "Pay via UPI / GPay")[0] is True
    assert check_commercial_content("Lawnmower", "Discount available, fixed price 1500/-")[0] is True


def test_commercial_filter_permits_genuine_mutual_aid():
    # Mutual aid language should pass cleanly
    is_comm, term = check_commercial_content(
        "Need a 6-step aluminum ladder for ceiling fan repair",
        "Need an aluminum step ladder for 2 hours this Sunday afternoon. Will return promptly with hot filter coffee!"
    )
    assert is_comm is False
    assert term is None

    is_comm, term = check_commercial_content(
        "Free curry leaf saplings and aloe vera pots",
        "Surplus plant cuttings to give away freely to any balcony gardener in Indiranagar."
    )
    assert is_comm is False
    assert term is None


# ==============================================================================
# 2. HAVERSINE DISTANCE & PRIVACY JITTER TESTS
# ==============================================================================
def test_haversine_distance_calculation():
    # Distance between Indiranagar (12.9784, 77.6408) and Koramangala (12.9352, 77.6245) is ~5.0 - 5.3 km
    dist = haversine_km(12.9784, 77.6408, 12.9352, 77.6245)
    assert dist is not None
    assert 4.5 <= dist <= 5.5

    # Zero distance
    assert haversine_km(12.9784, 77.6408, 12.9784, 77.6408) == 0.0

    # None coordinate handling
    assert haversine_km(None, None, 12.9, 77.6) is None


def test_coordinate_jitter_privacy():
    # Jittering should slightly displace coordinates within ~0.002 degrees (~150m)
    orig_lat = 12.9784
    orig_lng = 77.6408
    j_lat = jitter_coordinate(orig_lat)
    j_lng = jitter_coordinate(orig_lng)

    assert j_lat is not None
    assert abs(j_lat - orig_lat) <= 0.003
    assert abs(j_lng - orig_lng) <= 0.003
    assert jitter_coordinate(None) is None


# ==============================================================================
# 3. OPEN REDIRECT SAFETY
# ==============================================================================
def test_is_safe_url():
    with app.test_request_context("/"):
        assert is_safe_url("/post/1") is True
        assert is_safe_url("/dashboard") is True
        assert is_safe_url("https://malicious-site.com") is False
        assert is_safe_url("//malicious-site.com") is False
        assert is_safe_url("javascript:alert(1)") is False
        assert is_safe_url("") is False
        assert is_safe_url(None) is False


# ==============================================================================
# 4. APP ENDPOINT & AUTHORIZATION INTEGRATION TESTS
# ==============================================================================
def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json["status"] == "healthy"
    assert res.json["service"] == "NeighborGrid"


def test_anonymous_feed_access(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"NeighborGrid" in res.data
    assert b"Mohalla Feed" in res.data


def test_post_detail_privacy_contact_hidden_for_anonymous(client):
    # Fetch an existing open post
    posts = db.execute("SELECT id, user_id FROM posts WHERE status = 'open' AND is_hidden = 0 LIMIT 1")
    assert len(posts) > 0
    post_id = posts[0]["id"]

    res = client.get(f"/post/{post_id}")
    assert res.status_code == 200
    # Contact card should not be displayed
    assert b"Help Connection Confirmed!" not in res.data
    assert b"+91 98450 11223" not in res.data


def test_post_detail_contact_revealed_for_accepted_match(client):
    # Fetch a post with an accepted match
    acc_posts = db.execute(
        """SELECT p.id, p.user_id, m.responder_id 
           FROM posts p 
           JOIN matches m ON m.post_id = p.id 
           WHERE m.status = 'accepted' LIMIT 1"""
    )
    assert len(acc_posts) > 0
    post = acc_posts[0]

    # Logging in as the post owner should reveal the accepted match contact details
    owner = db.execute("SELECT id, username FROM users WHERE id = ?", post["user_id"])[0]
    with client.session_transaction() as sess:
        sess["user_id"] = owner["id"]
        sess["username"] = owner["username"]
        sess["is_admin"] = 0
        sess["csrf_token"] = "testtoken"

    res = client.get(f"/post/{post['id']}")
    assert res.status_code == 200
    assert b"Help Connection Confirmed!" in res.data


def test_unauthorized_user_cannot_edit_post(client):
    # Find a post and a user who does not own it
    post = db.execute("SELECT id, user_id FROM posts WHERE status = 'open' LIMIT 1")[0]
    other_user = db.execute("SELECT id, username FROM users WHERE id != ? LIMIT 1", post["user_id"])[0]

    with client.session_transaction() as sess:
        sess["user_id"] = other_user["id"]
        sess["username"] = other_user["username"]
        sess["is_admin"] = 0
        sess["csrf_token"] = "testtoken"

    res = client.get(f"/post/{post['id']}/edit")
    assert res.status_code == 403


def test_unauthorized_user_cannot_delete_post(client):
    post = db.execute("SELECT id, user_id FROM posts LIMIT 1")[0]
    other_user = db.execute("SELECT id, username FROM users WHERE id != ? AND is_admin = 0 LIMIT 1", post["user_id"])[0]

    with client.session_transaction() as sess:
        sess["user_id"] = other_user["id"]
        sess["username"] = other_user["username"]
        sess["is_admin"] = 0
        sess["csrf_token"] = "testtoken"

    res = client.post(f"/post/{post['id']}/delete", data={"csrf_token": "testtoken"})
    assert res.status_code == 403


def test_commercial_post_creation_is_blocked(client):
    user = db.execute("SELECT id, username FROM users LIMIT 1")[0]
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["username"] = user["username"]
        sess["is_admin"] = 0
        sess["csrf_token"] = "testtoken"

    res = client.post("/post/new", data={
        "csrf_token": "testtoken",
        "title": "Old Washing Machine Selling for Rs 4000",
        "description": "Cash only, urgent sale",
        "post_type": "offer",
        "category_id": "1",
        "urgency": "standard"
    })
    # Must reject with 400 and friendly explanation
    assert res.status_code == 400
    assert b"strictly non-commercial" in res.data
