-- TCG Dashboard — Fase 3: schema SQLite
-- Traducción literal de fase2-cardmarket-hallazgos-y-schema.md, sección 3.
-- No agregar campos ni índices no listados en ese documento.

CREATE TABLE IF NOT EXISTS games (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE CHECK (code IN ('pokemon', 'one_piece', 'magic')),
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS languages (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cardmarket_categories (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id                 INTEGER NOT NULL REFERENCES games (id),
    cardmarket_id_category  INTEGER NOT NULL UNIQUE,
    category_name           TEXT NOT NULL,
    is_single               INTEGER NOT NULL CHECK (is_single IN (0, 1))
);

CREATE TABLE IF NOT EXISTS expansions (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id                 INTEGER NOT NULL REFERENCES games (id),
    cardmarket_id_expansion INTEGER NOT NULL UNIQUE,
    name                    TEXT,
    set_code                TEXT,
    release_date            TEXT
);

CREATE TABLE IF NOT EXISTS cards (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id                 INTEGER NOT NULL REFERENCES games (id),
    expansion_id            INTEGER NOT NULL REFERENCES expansions (id),
    card_number             TEXT,
    name                    TEXT NOT NULL,
    printing_variant        TEXT NOT NULL CHECK (printing_variant IN ('normal', 'suggested_parallel', 'confirmed_parallel', 'other')),
    variant_label           TEXT,
    cardmarket_id_metacard  INTEGER,
    image_url               TEXT,
    image_source            TEXT CHECK (image_source IS NULL OR image_source IN ('scryfall', 'onepiece_official', 'manual')),
    UNIQUE (expansion_id, card_number, printing_variant)
);

CREATE TABLE IF NOT EXISTS cardmarket_products (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    cardmarket_id_product   INTEGER NOT NULL UNIQUE,
    raw_name                TEXT NOT NULL,
    cardmarket_id_category  INTEGER NOT NULL,
    cardmarket_id_expansion INTEGER NOT NULL,
    cardmarket_id_metacard  INTEGER,
    date_added              TEXT NOT NULL,
    last_seen_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cardmarket_product_mappings (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    cardmarket_product_id   INTEGER NOT NULL UNIQUE REFERENCES cardmarket_products (id),
    card_id                 INTEGER REFERENCES cards (id),
    status                  TEXT NOT NULL CHECK (status IN ('mapped', 'ambiguous', 'unmapped')),
    notes                   TEXT
);

CREATE TABLE IF NOT EXISTS market_price_history (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    cardmarket_product_id   INTEGER NOT NULL REFERENCES cardmarket_products (id),
    observed_at             TEXT NOT NULL,
    low                     REAL,
    avg                     REAL,
    trend                   REAL,
    avg1                    REAL,
    avg7                    REAL,
    avg30                   REAL,
    low_alt                 REAL,
    avg_alt                 REAL,
    trend_alt               REAL,
    avg1_alt                REAL,
    avg7_alt                REAL,
    avg30_alt               REAL,
    imported_at             TEXT NOT NULL,
    UNIQUE (cardmarket_product_id, observed_at)
);

CREATE INDEX IF NOT EXISTS idx_market_price_history_product_observed
    ON market_price_history (cardmarket_product_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS collection_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id             INTEGER REFERENCES cards (id),
    cardmarket_product_id INTEGER REFERENCES cardmarket_products (id),
    language_id         INTEGER NOT NULL REFERENCES languages (id) DEFAULT 1,
    condition           TEXT CHECK (condition IS NULL OR condition IN ('NM', 'EX', 'GD', 'LP', 'PL', 'PO')),
    grading_company      TEXT CHECK (grading_company IS NULL OR grading_company IN ('PSA', 'BGS', 'CGC', 'Other')),
    grade               REAL,
    quantity            INTEGER NOT NULL DEFAULT 1,
    purchase_price      REAL,
    purchase_currency   TEXT,
    purchase_date       TEXT,
    trade_value         REAL,
    status              TEXT NOT NULL CHECK (status IN ('KEEP', 'HOLD', 'TRADE', 'SELL', 'WANT')),
    manual_entry        INTEGER NOT NULL DEFAULT 0 CHECK (manual_entry IN (0, 1)),
    manual_entry_note   TEXT,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS want_list_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id      INTEGER REFERENCES cards (id),
    language_id  INTEGER REFERENCES languages (id),
    condition    TEXT CHECK (condition IS NULL OR condition IN ('NM', 'EX', 'GD', 'LP', 'PL', 'PO')),
    grade_min    REAL,
    target_price REAL,
    max_price    REAL,
    priority     TEXT NOT NULL CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH')),
    notes        TEXT
);
