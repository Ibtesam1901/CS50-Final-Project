-- Schema for NeighborGrid (CS50x Final Project - Indian Locality Edition)

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,
    neighborhood TEXT NOT NULL,
    pincode TEXT,
    phone TEXT,
    bio TEXT,
    latitude REAL,
    longitude REAL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    icon TEXT
);

-- Posts table (Requests and Offers with optional coordinates)
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    post_type TEXT NOT NULL CHECK(post_type IN ('request', 'offer')),
    category_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    urgency TEXT NOT NULL DEFAULT 'standard' CHECK(urgency IN ('standard', 'urgent')),
    neighborhood TEXT NOT NULL,
    location_details TEXT,
    latitude REAL,
    longitude REAL,
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'in_progress', 'completed', 'cancelled')),
    is_hidden INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(category_id) REFERENCES categories(id)
);

-- Index for the neighborhood feed
CREATE INDEX IF NOT EXISTS idx_posts_feed 
ON posts (neighborhood, status, is_hidden, urgency, created_at);

-- Matches table (Responses and Lifecycle)
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    responder_id INTEGER NOT NULL,
    message TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'declined')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(post_id, responder_id),
    FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY(responder_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Reports table (Safety & Moderation)
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    reporter_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(post_id, reporter_id),
    FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY(reporter_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Ratings / Reviews table
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    rater_id INTEGER NOT NULL,
    recipient_id INTEGER NOT NULL,
    score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(post_id, rater_id),
    FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY(rater_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(recipient_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Direct Messages table
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(receiver_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Seed Indian Categories
INSERT OR IGNORE INTO categories (name, description, icon) VALUES
('Tools & Ghar Ka Samaan', 'Borrow or lend drills, ladders, spanners, repair kits.', 'fa-wrench'),
('Tuition & Skill Sharing', 'Coding, maths, music, yoga, spoken English, cooking.', 'fa-graduation-cap'),
('Rides & Local Errands', 'Carpooling to metro/station, sabzi mandi, medicine pickup.', 'fa-motorcycle'),
('Pet Care & Feeding', 'Dog walking, feeding community indies, pet sitting.', 'fa-paw'),
('Household & Shifting Help', 'Help moving furniture, shifting flats, quick plumbing/electrical fixes.', 'fa-hands-helping'),
('Emergency Aid & Blood Request', 'Urgent medical assistance, O+/A+ blood donors, disaster relief.', 'fa-heartbeat'),
('Books & UPSC / Exam Prep', 'Share competitive exam guides, textbooks, novels, board games.', 'fa-book-open'),
('Garden, Plants & Food Sharing', 'Terrace garden cuttings, tulsi/curry leaves, surplus festive sweets/mithai.', 'fa-seedling');
