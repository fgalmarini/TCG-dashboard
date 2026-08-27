-- TCG Dashboard — schema SQLite
-- Traducción literal de fase2-cardmarket-hallazgos-y-schema.md, sección 3.
-- `cards` is the canonical card/printing catalog. Legacy collection references
-- continue to use cards.id as `collection_items.card_id`.

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
    data_source             TEXT CHECK (data_source IS NULL OR data_source IN ('scryfall', 'cardmarket_heuristic', 'manual')),
    scryfall_raw            TEXT,
    set_code                TEXT,
    normalized_name         TEXT,
    rarity                  TEXT,
    finish                  TEXT CHECK (finish IS NULL OR finish IN ('nonfoil', 'foil', 'etched')),
    treatment               TEXT,
    language_id             INTEGER REFERENCES languages (id),
    scryfall_id             TEXT,
    scryfall_oracle_id      TEXT,
    created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Preserve the old importer identity for legacy rows, while allowing catalog rows
-- to differ by language and real finish.
CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_legacy_identity
    ON cards (expansion_id, card_number, printing_variant)
    WHERE finish IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_catalog_identity
    ON cards (game_id, set_code, card_number, language_id, finish)
    WHERE set_code IS NOT NULL
      AND card_number IS NOT NULL
      AND language_id IS NOT NULL
      AND finish IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_scryfall_finish_identity
    ON cards (scryfall_id, language_id, finish)
    WHERE scryfall_id IS NOT NULL
      AND language_id IS NOT NULL
      AND finish IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_cards_catalog_search
    ON cards (game_id, set_code, normalized_name);

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

CREATE TABLE IF NOT EXISTS card_images (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id         INTEGER NOT NULL REFERENCES cards (id),
    source          TEXT NOT NULL CHECK (source IN ('scryfall', 'cardtrader', 'manual')),
    source_card_id  TEXT,
    source_variant  TEXT,
    source_collector_number TEXT,
    language        TEXT NOT NULL,
    face_index      INTEGER NOT NULL CHECK (face_index >= 0),
    image_url_small TEXT,
    image_url_large TEXT,
    match_quality   TEXT NOT NULL CHECK (match_quality IN ('exact', 'representative', 'manual')),
    status          TEXT NOT NULL CHECK (status IN ('resolved', 'ambiguous', 'missing', 'error')),
    last_checked_at TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (card_id, source, language, face_index)
);

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

CREATE TABLE IF NOT EXISTS wishlist_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id         INTEGER NOT NULL REFERENCES cards (id),
    quantity_wanted INTEGER NOT NULL DEFAULT 1 CHECK (quantity_wanted > 0),
    priority        TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    max_price       REAL,
    currency        TEXT,
    notes           TEXT,
    status          TEXT NOT NULL DEFAULT 'wanted' CHECK (status IN ('wanted', 'acquired', 'removed')),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Legacy want-list fields remain nullable for a lossless additive migration.
    language_id     INTEGER REFERENCES languages (id),
    condition       TEXT CHECK (condition IS NULL OR condition IN ('NM', 'EX', 'GD', 'LP', 'PL', 'PO')),
    grade_min       REAL,
    target_price    REAL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_wishlist_active_card
    ON wishlist_items (card_id)
    WHERE status = 'wanted';

CREATE INDEX IF NOT EXISTS idx_wishlist_status_updated
    ON wishlist_items (status, updated_at DESC, id DESC);
