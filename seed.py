"""
Seed script for NeighborGrid - Indian Locality Edition.
Populates realistic Bengaluru neighborhoods:
Indiranagar, Koramangala, HSR Layout, Jayanagar, Whitefield
with genuine local mutual-aid requests, offers, live geo-coordinates, in-app Hindi/English chat, and reviews.
Commercial spam post is pre-flagged and hidden from public feed.
"""

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from init_db import init_db
from db_helper import SQL_PROVIDER

# Ensure database tables and columns exist before opening connection
init_db()

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

    cat_rows = db.execute("SELECT id, name FROM categories")
    cat_map = {c["name"]: c["id"] for c in cat_rows}

    # 1. Insert Indian Neighborhood Residents across Bengaluru
    print("Creating Bengaluru neighborhood users...")
    users_data = [
        # (username, email, hash, neighborhood, pincode, phone, bio, lat, lng, is_admin)
        ("admin", "admin@neighborgrid.in", demo_pw_hash, "Indiranagar, Bengaluru", "560038", "+91 98765 43210", 
         "NeighborGrid Community Lead & Moderator. Ensuring safe, non-commercial mutual aid.", 12.9784, 77.6408, 1),

        ("aarav_patel", "aarav@neighborgrid.in", demo_pw_hash, "Indiranagar, Bengaluru", "560038", "+91 98450 11223", 
         "Tech lead by day, urban balcony gardener on weekends. Happy to share plant cuttings and tools!", 12.9719, 77.6412, 0),

        ("priya_sharma", "priya@neighborgrid.in", demo_pw_hash, "Indiranagar, Bengaluru", "560038", "+91 99801 33445", 
         "Chartered Accountant and pet parent. Happy to lend study materials or DIY toolkit.", 12.9756, 77.6380, 0),

        ("rohan_verma", "rohan@neighborgrid.in", demo_pw_hash, "Indiranagar, Bengaluru", "560038", "+91 98203 55667", 
         "Freelance UI designer. Commute daily toward MG Road metro station on two-wheeler.", 12.9790, 77.6440, 0),

        ("ananya_iyer", "ananya@neighborgrid.in", demo_pw_hash, "Koramangala, Bengaluru", "560034", "+91 97412 88990", 
         "Koramangala resident passionate about stray animal welfare and community libraries.", 12.9352, 77.6245, 0),

        ("karthik_nair", "karthik@neighborgrid.in", demo_pw_hash, "HSR Layout, Bengaluru", "560102", "+91 98440 22334",
         "Cycling enthusiast in Sector 2, HSR Layout. Have bicycle repair stand and pump.", 12.9116, 77.6474, 0),

        ("deepa_kulkarni", "deepa@neighborgrid.in", demo_pw_hash, "Jayanagar, Bengaluru", "560041", "+91 99002 44556",
         "Retired school educator in Jayanagar 4th Block. Love reading and baking.", 12.9299, 77.5833, 0),

        ("vikram_sen", "vikram@neighborgrid.in", demo_pw_hash, "Whitefield, Bengaluru", "560066", "+91 98860 66778",
         "Software architect in Inner Circle, Whitefield. Has heavy duty jumper cables & tire inflator.", 12.9698, 77.7500, 0),
    ]

    user_ids = {}
    for u in users_data:
        uid = db.execute(
            """INSERT INTO users (username, email, hash, neighborhood, pincode, phone, bio, latitude, longitude, is_admin)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            *u
        )
        user_ids[u[0]] = uid
    print("Created users:", list(user_ids.keys()))

    now = datetime.utcnow()

    # 2. Insert Realistic Indian Hyperlocal Posts with Coordinates across Bengaluru
    print("Seeding Indian locality mutual-aid posts...")
    posts_data = [
        # 1. Aarav request for ladder (Indiranagar)
        (user_ids["aarav_patel"], "request", cat_map["Tools & Ghar Ka Samaan"], 
         "Need a 6-step aluminum ladder for ceiling fan repair", 
         "Need an aluminum step ladder for 2 hours this Sunday afternoon to fix balcony ceiling lights and clean fan blades. Will return promptly!", 
         "standard", "Indiranagar, Bengaluru", "100ft Road, Near Toit Brewpub", 12.9792, 77.6405, "open", 0, 0,
         (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")),
        
        # 2. Priya offering drill & toolkit (Indiranagar)
        (user_ids["priya_sharma"], "offer", cat_map["Tools & Ghar Ka Samaan"], 
         "Bosch impact drill set & screwdriver kit available to borrow", 
         "Have a complete Bosch 500W electric drill with concrete and wood bits. Neighbors in Indiranagar 12th Main are welcome to borrow anytime for photo frames or curtain rods.", 
         "standard", "Indiranagar, Bengaluru", "12th Main Road, Near Corner House", 12.9715, 77.6375, "open", 0, 0,
         (now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")),

        # 3. Rohan urgent request for keys (Indiranagar)
        (user_ids["rohan_verma"], "request", cat_map["Emergency Aid & Blood Request"], 
         "Urgent: Lost two-wheeler Activa key near Defence Colony park", 
         "Dropped Honda Activa key with a black leather keychain around 7:30 AM while jogging in Defence Colony Playground. If spotted by any morning walker, please reach out!", 
         "urgent", "Indiranagar, Bengaluru", "Defence Colony Children Park", 12.9765, 77.6432, "open", 0, 0,
         (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")),

        # 4. Aarav offering curry leaves and plants (Indiranagar)
        (user_ids["aarav_patel"], "offer", cat_map["Garden, Plants & Food Sharing"], 
         "Free organic curry leaf (Kadi Patta) saplings & aloe vera pots", 
         "My terrace garden has surplus healthy curry leaf saplings, fresh tulsi, and aloe vera starters. Happy to give to fellow green thumbs in the colony!", 
         "standard", "Indiranagar, Bengaluru", "Near CMH Road Metro Station", 12.9785, 77.6445, "open", 0, 0,
         (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")),

        # 5. Priya request for help shifting sofa (Indiranagar) - In Progress
        (user_ids["priya_sharma"], "request", cat_map["Household & Shifting Help"], 
         "Need a hand shifting a 3-seater sofa down 1st floor staircase", 
         "Looking for a helpful neighbor to assist for 10-15 minutes this Saturday morning to carry a light sofa down one flight of stairs. Hot filter coffee on me!", 
         "standard", "Indiranagar, Bengaluru", "Double Road, Indiranagar Stage 2", 12.9735, 77.6395, "in_progress", 0, 0,
         (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")),

        # 6. Rohan completed carpool/metro ride with Aarav (Indiranagar) - Completed
        (user_ids["rohan_verma"], "offer", cat_map["Rides & Local Errands"], 
         "Daily morning scooter carpool to Baiyappanahalli / MG Road Metro", 
         "Commuting toward MG Road daily at 8:45 AM via CMH Road. Happy to offer pillion ride to save auto fares and cut traffic.", 
         "standard", "Indiranagar, Bengaluru", "CMH Road & 100ft Junction", 12.9780, 77.6420, "completed", 0, 0,
         (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")),

        # 7. Priya offering UPSC / CA prep books (Indiranagar)
        (user_ids["priya_sharma"], "offer", cat_map["Books & UPSC / Exam Prep"], 
         "Laxmikanth Indian Polity & CA Financial Management textbooks", 
         "Have latest edition Indian Polity, Ramesh Singh Indian Economy, and CA Inter revision manuals in mint condition. Free to borrow for exam aspirants.", 
         "standard", "Indiranagar, Bengaluru", "Indiranagar Club Area", 12.9705, 77.6410, "open", 0, 0,
         (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")),

        # 8. Commercial spam (Flagged & Hidden to showcase moderation)
        (user_ids["ananya_iyer"], "request", cat_map["Tools & Ghar Ka Samaan"], 
         "[FLAGGED] Commercial Water Purifier RO Selling for Rs 6500 Cash", 
         "Aquaguard RO water filter for immediate sale, cash on delivery only. Fixed price.", 
         "standard", "Indiranagar, Bengaluru", "Old Airport Road", 12.9600, 77.6480, "open", 1, 1,
         (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")),

        # 9. Koramangala pet care offer
        (user_ids["ananya_iyer"], "offer", cat_map["Pet Care & Feeding"], 
         "Evening dog walking & indie puppy feeding in Koramangala 4th Block", 
         "Available every weekday evening to walk dogs or feed community puppies near Sony World Signal.", 
         "standard", "Koramangala, Bengaluru", "Koramangala 4th Block", 12.9350, 77.6240, "open", 0, 0,
         (now - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")),

        # 10. HSR Layout bike pump offer
        (user_ids["karthik_nair"], "offer", cat_map["Tools & Ghar Ka Samaan"], 
         "Bicycle floor pump with pressure gauge & puncture kit available", 
         "High pressure Giyo floor pump (Presta & Schrader) and patch kit available in Sector 2. Cyclists welcome to drop in anytime.", 
         "standard", "HSR Layout, Bengaluru", "Sector 2, 27th Main", 12.9116, 77.6474, "open", 0, 0,
         (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")),

        # 11. Jayanagar blood donor request (Urgent)
        (user_ids["deepa_kulkarni"], "request", cat_map["Emergency Aid & Blood Request"], 
         "Urgent: O-ve Blood Donor needed for senior citizen surgery at Jayanagar General", 
         "Looking for an O-negative volunteer blood donor for a planned hip surgery tomorrow morning at Jayanagar General Hospital.", 
         "urgent", "Jayanagar, Bengaluru", "4th Block Jayanagar, near Complex", 12.9299, 77.5833, "open", 0, 0,
         (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")),

        # 12. Whitefield car battery jumpstart offer
        (user_ids["vikram_sen"], "offer", cat_map["Tools & Ghar Ka Samaan"], 
         "Heavy-duty car jumper cables & 12V portable tire inflator", 
         "Keep jumper cables and a digital air pump in my car boot. If your vehicle battery is drained near Inner Circle, feel free to ping.", 
         "standard", "Whitefield, Bengaluru", "Inner Circle Whitefield", 12.9698, 77.7500, "open", 0, 0,
         (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")),

        # 13. Expired post demo (>14 days) to demonstrate Repost feature
        (user_ids["aarav_patel"], "request", cat_map["Books & UPSC / Exam Prep"], 
         "Borrowing NCERT Physics & Chemistry Class 11 textbooks", 
         "Looking to borrow NCERT standard 11 textbooks for my nephew for two weeks.", 
         "standard", "Indiranagar, Bengaluru", "6th Main Indiranagar", 12.9730, 77.6415, "open", 0, 0,
         (now - timedelta(days=16)).strftime("%Y-%m-%d %H:%M:%S")),
    ]

    post_ids = []
    for p in posts_data:
        pid = db.execute(
            """INSERT INTO posts (user_id, post_type, category_id, title, description, urgency, neighborhood, location_details, latitude, longitude, status, is_hidden, is_flagged, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            *p
        )
        post_ids.append(pid)

    # 3. Create Seed Matches
    print("Seeding responses & lifecycle matches...")
    # Response on Priya's sofa shift (post_ids[4]) -> Accepted by Rohan
    db.execute(
        """INSERT INTO matches (post_id, responder_id, message, status)
           VALUES (?, ?, ?, 'accepted')""",
        post_ids[4], user_ids["rohan_verma"], "Hi Priya! I live just down 12th Main, can drop by on Saturday at 11:00 AM to help shift the sofa."
    )

    # Response on Rohan's metro ride (post_ids[5]) -> Accepted by Aarav and Completed
    db.execute(
        """INSERT INTO matches (post_id, responder_id, message, status)
           VALUES (?, ?, ?, 'accepted')""",
        post_ids[5], user_ids["aarav_patel"], "That would be awesome Rohan! My office is right near Trinity circle. Would love to join."
    )
    db.execute("UPDATE posts SET completed_at = CURRENT_TIMESTAMP WHERE id = ?", post_ids[5])

    # Pending response on Aarav's ladder request (post_ids[0])
    db.execute(
        """INSERT INTO matches (post_id, responder_id, message, status)
           VALUES (?, ?, ?, 'pending')""",
        post_ids[0], user_ids["priya_sharma"], "Hi Aarav, my dad has a sturdy 6-foot aluminum ladder at home. You can collect it Sunday 2 PM."
    )

    # 4. Seed Chat Messages between Priya & Rohan (Bilingual Indian touch)
    print("Seeding in-app direct messaging thread...")
    db.execute(
        """INSERT INTO messages (post_id, sender_id, receiver_id, content)
           VALUES (?, ?, ?, ?)""",
        post_ids[4], user_ids["priya_sharma"], user_ids["rohan_verma"], 
        "Namaste Rohan! Thanks a lot for offering. Does 11:30 AM work for you on Saturday?"
    )
    db.execute(
        """INSERT INTO messages (post_id, sender_id, receiver_id, content)
           VALUES (?, ?, ?, ?)""",
        post_ids[4], user_ids["rohan_verma"], user_ids["priya_sharma"], 
        "Haanji bilkul, 11:30 AM is perfect! I will be there on time. Don't worry, 10 min ka kaam hai."
    )

    # 5. Seed Reviews & Ratings
    print("Seeding neighbor reviews & ratings...")
    db.execute(
        """INSERT INTO ratings (post_id, rater_id, recipient_id, score, feedback)
           VALUES (?, ?, ?, 5, 'Rohan is a fantastic neighbor! Very punctual on the ride, safe driver, and refused to take any fuel contribution. Pure mutual aid!')""",
        post_ids[5], user_ids["aarav_patel"], user_ids["rohan_verma"]
    )
    db.execute(
        """INSERT INTO ratings (post_id, rater_id, recipient_id, score, feedback)
           VALUES (?, ?, ?, 5, 'Aarav was ready right on time at CMH signal. Great conversation about tech on the way. Bahut badhiya neighbor!')""",
        post_ids[5], user_ids["rohan_verma"], user_ids["aarav_patel"]
    )

    # 6. Seed Moderation Report on Commercial Post
    print("Seeding moderation report...")
    db.execute(
        """INSERT INTO reports (post_id, reporter_id, reason)
           VALUES (?, ?, ?)""",
        post_ids[7], user_ids["aarav_patel"], "Commercial water filter sale for Rs 6500 cash. Violates Rule #1: No buying/selling or business promotions."
    )

    print("Seed complete! Database populated with multi-locality Bengaluru neighborhoods, coordinates, bilingual chat, ratings, and flagged post.")

if __name__ == "__main__":
    seed()
