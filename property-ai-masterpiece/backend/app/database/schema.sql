-- Property AI Masterpiece v2.0 — SQLite Schema

CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    email        TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    user_type    TEXT CHECK (user_type IN ('buyer','seller','admin','both')) DEFAULT 'buyer',
    name         TEXT NOT NULL,
    phone        TEXT,
    avatar_url   TEXT,
    is_verified  INTEGER DEFAULT 0,
    is_active    INTEGER DEFAULT 1,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS listings (
    id                    TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    seller_id             TEXT REFERENCES users(id) ON DELETE CASCADE,
    title                 TEXT NOT NULL,
    description           TEXT,
    address               TEXT,
    city                  TEXT,
    state                 TEXT,
    zip_code              TEXT,
    country               TEXT DEFAULT 'USA',
    price                 REAL NOT NULL DEFAULT 0,
    property_type         TEXT CHECK (property_type IN ('house','apartment','condo','townhouse','land','commercial')) DEFAULT 'house',
    bedrooms              INTEGER,
    bathrooms             REAL,
    square_feet           INTEGER,
    year_built            INTEGER,
    status                TEXT CHECK (status IN ('draft','published','pending','sold','archived')) DEFAULT 'draft',
    featured              INTEGER DEFAULT 0,
    overall_quality_score REAL,
    authenticity_verified INTEGER DEFAULT 0,
    accessibility_score   REAL,
    predicted_price       REAL,
    created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
    published_at          DATETIME
);

CREATE TABLE IF NOT EXISTS images (
    id                TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    listing_id        TEXT REFERENCES listings(id) ON DELETE CASCADE,
    image_path        TEXT NOT NULL,
    original_filename TEXT,
    upload_order      INTEGER DEFAULT 0,
    is_primary        INTEGER DEFAULT 0,
    is_staged         INTEGER DEFAULT 0,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS image_analysis (
    id                    TEXT PRIMARY KEY,
    image_id              TEXT UNIQUE REFERENCES images(id) ON DELETE CASCADE,
    room_type             TEXT,
    style_category        TEXT,
    spaciousness_score    REAL,
    clutter_score         REAL,
    lighting_quality_score REAL,
    trust_score           REAL,
    is_ai_generated       INTEGER DEFAULT 0,
    ai_probability        REAL,
    accessibility_score   REAL,
    overall_quality_score REAL,
    recommendations       TEXT,
    analyzed_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS favorites (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    buyer_id        TEXT REFERENCES users(id) ON DELETE CASCADE,
    listing_id      TEXT REFERENCES listings(id) ON DELETE CASCADE,
    collection_name TEXT DEFAULT 'Default',
    notes           TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(buyer_id, listing_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id           TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    listing_id   TEXT REFERENCES listings(id) ON DELETE CASCADE,
    sender_id    TEXT REFERENCES users(id) ON DELETE CASCADE,
    recipient_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    subject      TEXT,
    message      TEXT NOT NULL,
    status       TEXT DEFAULT 'sent',
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at      DATETIME
);

CREATE TABLE IF NOT EXISTS notifications (
    id         TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id    TEXT REFERENCES users(id) ON DELETE CASCADE,
    type       TEXT,
    title      TEXT NOT NULL,
    content    TEXT,
    is_read    INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS listing_analytics (
    id         TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    listing_id TEXT REFERENCES listings(id) ON DELETE CASCADE,
    date       DATE NOT NULL,
    views      INTEGER DEFAULT 0,
    saves      INTEGER DEFAULT 0,
    contacts   INTEGER DEFAULT 0,
    UNIQUE(listing_id, date)
);

CREATE TABLE IF NOT EXISTS viewing_history (
    id         TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id    TEXT REFERENCES users(id) ON DELETE CASCADE,
    listing_id TEXT REFERENCES listings(id) ON DELETE CASCADE,
    viewed_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS smart_alerts (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id         TEXT REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT,
    search_criteria TEXT,
    frequency       TEXT DEFAULT 'daily',
    is_active       INTEGER DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Investment Analysis Cache
CREATE TABLE IF NOT EXISTS investment_analysis (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    listing_id      TEXT UNIQUE REFERENCES listings(id) ON DELETE CASCADE,
    roi_percent     REAL,
    rental_yield    REAL,
    cap_rate        REAL,
    market_position TEXT,
    analysis_data   TEXT,
    calculated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Neighborhood Scores Cache
CREATE TABLE IF NOT EXISTS neighborhood_scores (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    listing_id      TEXT UNIQUE REFERENCES listings(id) ON DELETE CASCADE,
    overall_score   REAL,
    walkability     REAL,
    transit         REAL,
    safety          REAL,
    amenities       REAL,
    score_data      TEXT,
    calculated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User Property Comparisons
CREATE TABLE IF NOT EXISTS user_comparisons (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id     TEXT REFERENCES users(id) ON DELETE CASCADE,
    listing_ids TEXT NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Search History
CREATE TABLE IF NOT EXISTS search_history (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id     TEXT REFERENCES users(id) ON DELETE CASCADE,
    query       TEXT,
    filters     TEXT,
    result_count INTEGER DEFAULT 0,
    searched_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_listings_seller   ON listings(seller_id);
CREATE INDEX IF NOT EXISTS idx_listings_status   ON listings(status);
CREATE INDEX IF NOT EXISTS idx_listings_price    ON listings(price);
CREATE INDEX IF NOT EXISTS idx_images_listing    ON images(listing_id);
CREATE INDEX IF NOT EXISTS idx_favorites_buyer   ON favorites(buyer_id);
CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_history_user      ON viewing_history(user_id, viewed_at);

-- Triggers
CREATE TRIGGER IF NOT EXISTS update_listings_ts AFTER UPDATE ON listings
BEGIN UPDATE listings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS update_users_ts AFTER UPDATE ON users
BEGIN UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id; END;
