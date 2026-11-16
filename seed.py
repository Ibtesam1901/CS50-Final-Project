"""
Seed script for NeighborGrid demo data.
Populates realistic test accounts across 'Downtown' and 'Oakridge',
including coordinates, ratings/reviews, and direct messages.
"""

from werkzeug.security import generate_password_hash
from db_helper import SQL_PROVIDER

db = SQL_PROVIDER("sqlite:///neighborgrid.db")

def seed():
    print("Clearing prior test data...")
    db.execute("DELETE FROM messages")
    db.execute("DELETE FROM ratings")
    db.execute("DELETE FROM reports")
    db.execute("DELETE FROM matches")
    db.execute("DELETE FROM posts")
    db.execute("DELETE FROM users")

    demo_pw_hash = generate_password_hash("password123")

    # Fetch Category mapping by name
    cat_rows = db.execute("SELECT id, name FROM categories")
    cat_map = {c["name"]: c["id"] for c in cat_rows}

    # 1. Insert Demo Users (including 1 Admin)
    print("Creating demo users...")
    users_data = [
        ("admin", "admin@neighborgrid.org", demo_pw_hash, "Downtown", "10001", "555-0100", "NeighborGrid Community Moderator.", 1),
        ("elena_gardener", "elena@example.com", demo_pw_hash, "Downtown", "10001", "555-0101", "Avid urban gardener and DIY enthusiast. Always happy to lend garden tools and seeds!", 0),
        ("marcus_tech", "marcus@example.com", demo_pw_hash, "Downtown", "10002", "555-0102", "Software engineer and woodworking hobbyist. Have circular saw, drill kit, and bike tools.", 0),
        ("sarah_baker", "sarah@example.com", demo_pw_hash, "Downtown", "10001", "555-0103", "Bakes fresh sourdough weekly. Passionate about community mutual aid.", 0),
        ("david_oak", "david@example.com", demo_pw_hash, "Oakridge", "94102", "555-0104", "Oakridge neighborhood resident, cycling enthusiast.", 0)
    ]

    user_ids = {}
    for u in users_data:
        uid = db.execute(
            """INSERT INTO users (username, email, hash, neighborhood, pincode, phone, bio, is_admin)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            *u
        )
        user_ids[u[0]] = uid
    print("Created users:", list(user_ids.keys()))

    # 2. Insert Posts with Map Coordinates & Categories
    print("Seeding posts with geo-coordinates...")
    posts_data = [
        # Downtown Posts
        (user_ids["elena_gardener"], "request", cat_map["Tools & Equipment"], "Need an extension ladder for roof gutter clearing", 
         "Looking to borrow a 12ft or 16ft extension ladder this weekend to clear out autumn leaves from gutters. Will return within 48 hours in pristine condition!", 
         "standard", "Downtown", "5th Ave & Pine St", 40.7138, -74.0040, "open", 0),
        
        (user_ids["marcus_tech"], "offer", cat_map["Tools & Equipment"], "Lending Dewalt cordless drill kit and bit set", 
         "Available to borrow: Dewalt 20V drill with two charged batteries, wall mount anchors, and complete screw/bit set. Feel free to request for your home projects.", 
         "standard", "Downtown", "Oak St Library vicinity", 40.7160, -74.0080, "open", 0),

        (user_ids["sarah_baker"], "request", cat_map["Emergency Aid"], "Urgent: Lost house keys near Elm Street park", 
         "Accidentally dropped a silver keychain with blue lanyard near the community park playground while walking this morning. If anyone spots them, please connect!", 
         "urgent", "Downtown", "Elm Street Community Park", 40.7115, -74.0020, "open", 0),

        (user_ids["sarah_baker"], "offer", cat_map["Garden & Food Sharing"], "Free sourdough bread starter & heirloom tomato seeds", 
         "Happy to gift mature active sourdough starter cultures along with heirloom tomato seed packets to any neighbor interested in gardening or baking.", 
         "standard", "Downtown", "Maple & 3rd St", 40.7145, -74.0095, "open", 0),

        (user_ids["elena_gardener"], "request", cat_map["Household Help"], "Help moving heavy oak desk down two flights of stairs", 
         "Looking for a strong neighbor to help lift a solid wood desk downstairs on Tuesday evening. Takes about 15 minutes, fresh baked cookies provided!", 
         "standard", "Downtown", "Center St Apartments", 40.7125, -74.0055, "in_progress", 0),

        (user_ids["marcus_tech"], "request", cat_map["Rides & Errands"], "Ride to airport terminal early Thursday morning", 
         "Flight departs 7:00 AM Thursday. Looking for a neighbor carpooling toward the metro airport around 5:15 AM.", 
         "standard", "Downtown", "Grand Plaza Metro", 40.7180, -74.0010, "completed", 0),

        # Commercial violation post (for moderation testing)
        (user_ids["david_oak"], "request", cat_map["Tools & Equipment"], "Selling commercial generator for $400 cash only", 
         "Brand new generator, retail price $700, selling fast for cash. Not looking to lend.", 
         "standard", "Downtown", "Broad Street", 40.7100, -74.0070, "open", 0),

        # Oakridge Post (Proves neighborhood isolation)
        (user_ids["david_oak"], "offer", cat_map["Pet Care"], "Available for weekend dog walking in Oakridge", 
         "Experienced with large and small breeds. Available to walk dogs on Saturday mornings around Oakridge Park.", 
         "standard", "Oakridge", "Oakridge Meadow", 37.7749, -122.4194, "open", 0)
    ]

    post_ids = []
    for p in posts_data:
        pid = db.execute(
            """INSERT INTO posts (user_id, post_type, category_id, title, description, urgency, neighborhood, location_details, latitude, longitude, status, is_hidden)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            *p
        )
        post_ids.append(pid)

    # 3. Create Seed Responses (Matches)
    print("Seeding responses & lifecycle matches...")
    # Response on Elena's desk move (post_ids[4]) -> Accepted (in_progress)
    match_desk_id = db.execute(
        """INSERT INTO matches (post_id, responder_id, message, status)
           VALUES (?, ?, ?, 'accepted')""",
        post_ids[4], user_ids["marcus_tech"], "I can help on Tuesday at 6pm! I have lifting straps."
    )

    # Response on Marcus's airport ride (post_ids[5]) -> Accepted & Completed
    match_ride_id = db.execute(
        """INSERT INTO matches (post_id, responder_id, message, status)
           VALUES (?, ?, ?, 'accepted')""",
        post_ids[5], user_ids["sarah_baker"], "I head that direction every Thursday morning for work. Happy to give you a lift!"
    )
    db.execute("UPDATE posts SET completed_at = CURRENT_TIMESTAMP WHERE id = ?", post_ids[5])

    # Pending response on Elena's ladder request (post_ids[0])
    db.execute(
        """INSERT INTO matches (post_id, responder_id, message, status)
           VALUES (?, ?, ?, 'pending')""",
        post_ids[0], user_ids["marcus_tech"], "I have a 16ft aluminum ladder you can pick up on Friday afternoon."
    )

    # 4. Seed Direct Messages for accepted match (Elena & Marcus on desk move)
    print("Seeding in-app direct messaging thread...")
    db.execute(
        """INSERT INTO messages (post_id, sender_id, receiver_id, content)
           VALUES (?, ?, ?, ?)""",
        post_ids[4], user_ids["elena_gardener"], user_ids["marcus_tech"], 
        "Hi Marcus, thank you so much for offering! Does 6:15 PM work best for you?"
    )
    db.execute(
        """INSERT INTO messages (post_id, sender_id, receiver_id, content)
           VALUES (?, ?, ?, ?)""",
        post_ids[4], user_ids["marcus_tech"], user_ids["elena_gardener"], 
        "6:15 PM is perfect! I will bring heavy-duty work gloves and shoulder straps."
    )

    # 5. Seed Reviews / Star Ratings for the completed airport ride
    print("Seeding neighbor reviews & ratings...")
    db.execute(
        """INSERT INTO ratings (post_id, rater_id, recipient_id, score, feedback)
           VALUES (?, ?, ?, 5, 'Sarah was incredible! Punctual, friendly, and saved me a huge cab fare. Wonderful neighbor!')""",
        post_ids[5], user_ids["marcus_tech"], user_ids["sarah_baker"]
    )
    db.execute(
        """INSERT INTO ratings (post_id, rater_id, recipient_id, score, feedback)
           VALUES (?, ?, ?, 5, 'Marcus was ready right on time and great company on the drive. Delighted to help!')""",
        post_ids[5], user_ids["sarah_baker"], user_ids["marcus_tech"]
    )

    # 6. Create Moderation Report on generator sale
    print("Seeding moderation report...")
    db.execute(
        """INSERT INTO reports (post_id, reporter_id, reason)
           VALUES (?, ?, ?)""",
        post_ids[6], user_ids["elena_gardener"], "Violates rule #1: Commercial sale offering item for cash instead of mutual aid."
    )

    print("Seed complete! Database populated with maps, reviews, chat messages, and full lifecycle.")

if __name__ == "__main__":
    seed()
