"""
Seed script for NeighborGrid demo data.
Inserts realistic test users across two neighborhoods ('Downtown' and 'Oakridge'),
and authentic mutual-aid requests/offers in various lifecycle states.
"""

from werkzeug.security import generate_password_hash
from db_helper import SQL_PROVIDER

db = SQL_PROVIDER("sqlite:///neighborgrid.db")

def seed():
    # Clear existing demo data
    print("Clearing prior test data...")
    db.execute("DELETE FROM reports")
    db.execute("DELETE FROM matches")
    db.execute("DELETE FROM posts")
    db.execute("DELETE FROM users")

    # Hash for standard demo password: 'password123'
    demo_pw_hash = generate_password_hash("password123")

    # 1. Insert Demo Users (including 1 Admin)
    print("Creating demo users...")
    users_data = [
        ("admin", "admin@neighborgrid.org", demo_pw_hash, "Downtown", "10001", "555-0100", "NeighborGrid Community Moderator.", 1),
        ("elena_gardener", "elena@example.com", demo_pw_hash, "Downtown", "10001", "555-0101", "Avid urban gardener and DIY enthusiast. Always happy to lend garden tools!", 0),
        ("marcus_tech", "marcus@example.com", demo_pw_hash, "Downtown", "10002", "555-0102", "Software engineer and woodworking hobbyist. Have circular saw and cordless drills.", 0),
        ("sarah_baker", "sarah@example.com", demo_pw_hash, "Downtown", "10001", "555-0103", "Bakes fresh sourdough weekly. Passionate about community sharing.", 0),
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

    # 2. Insert Posts across categories and lifecycles
    print("Seeding posts...")
    posts_data = [
        # Downtown Posts
        (user_ids["elena_gardener"], "request", 1, "Need an extension ladder for roof gutter clearing", 
         "Looking to borrow a 12ft or 16ft extension ladder this weekend to clear out autumn leaves from gutters. Will return within 48 hours in pristine condition!", 
         "standard", "Downtown", "open", 0),
        
        (user_ids["marcus_tech"], "offer", 1, "Lending Dewalt cordless drill kit and bit set", 
         "Available to borrow: Dewalt 20V drill with two charged batteries, wall mount anchors, and complete screw/bit set. Feel free to request for your home projects.", 
         "standard", "Downtown", "open", 0),

        (user_ids["sarah_baker"], "request", 6, "Urgent: Lost house keys near Elm Street park", 
         "Accidentally dropped a silver keychain with blue lanyard near the community park playground while walking this morning. If anyone spots them, please connect!", 
         "urgent", "Downtown", "open", 0),

        (user_ids["sarah_baker"], "offer", 2, "Free sourdough bread starter & beginner baking tutorial", 
         "Happy to gift mature active sourdough starter cultures along with step-by-step baking tips to any neighbor interested in artisan bread making.", 
         "standard", "Downtown", "open", 0),

        (user_ids["elena_gardener"], "request", 5, "Help moving heavy oak desk down two flights of stairs", 
         "Looking for a strong neighbor to help lift a solid wood desk downstairs on Tuesday evening. Takes about 15 minutes, fresh baked cookies provided!", 
         "standard", "Downtown", "in_progress", 0),

        (user_ids["marcus_tech"], "request", 3, "Ride to airport terminal early Thursday morning", 
         "Flight departs 7:00 AM Thursday. Looking for a neighbor carpooling toward the metro airport around 5:15 AM.", 
         "standard", "Downtown", "completed", 0),

        # Flagged / Reported post for testing moderation
        (user_ids["david_oak"], "request", 1, "Selling commercial generator for $400 cash only", 
         "Brand new generator, retail price $700, selling fast for cash. Not looking to lend.", 
         "standard", "Downtown", "open", 0),

        # Oakridge Post (Proves neighborhood isolation)
        (user_ids["david_oak"], "offer", 4, "Available for weekend dog walking in Oakridge", 
         "Experienced with large and small breeds. Available to walk dogs on Saturday mornings around Oakridge Park.", 
         "standard", "Oakridge", "open", 0)
    ]

    post_ids = []
    for p in posts_data:
        pid = db.execute(
            """INSERT INTO posts (user_id, post_type, category_id, title, description, urgency, neighborhood, status, is_hidden)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            *p
        )
        post_ids.append(pid)

    # 3. Create Seed Responses (Matches)
    print("Seeding responses & lifecycle matches...")
    # Response on Elena's desk move (post_ids[4]) -> Accepted (in_progress)
    db.execute(
        """INSERT INTO matches (post_id, responder_id, message, status)
           VALUES (?, ?, ?, 'accepted')""",
        post_ids[4], user_ids["marcus_tech"], "I can help on Tuesday at 6pm! I have lifting straps."
    )

    # Response on Marcus's airport ride (post_ids[5]) -> Accepted & Completed
    db.execute(
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

    # 4. Create a Report on the commercial sales post (post_ids[6])
    print("Seeding moderation report...")
    db.execute(
        """INSERT INTO reports (post_id, reporter_id, reason)
           VALUES (?, ?, ?)""",
        post_ids[6], user_ids["elena_gardener"], "Violates rule #1: Commercial sale offering item for cash instead of mutual aid."
    )

    print("Seed complete! Database successfully populated with realistic demo environment.")

if __name__ == "__main__":
    seed()
