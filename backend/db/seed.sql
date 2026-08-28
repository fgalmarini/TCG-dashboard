-- Seed mínimo indispensable: sin esto, los FKs/defaults del schema no resuelven.
-- games: los 3 códigos ya enumerados en el CHECK de games.code.
-- languages: 'en' con id=1, referenciado por el DEFAULT de collection_items.language_id.

INSERT OR IGNORE INTO games (id, code, name, catalog_is_active) VALUES
    (1, 'pokemon', 'Pokémon', 0),
    (2, 'one_piece', 'One Piece', 1),
    (3, 'magic', 'Magic: The Gathering', 1);

INSERT OR IGNORE INTO languages (id, code, name) VALUES
    (1, 'en', 'English');

-- Existing production databases already use other numeric IDs (for example Qya at
-- id=2), so Japanese must be keyed by its stable code rather than a fixed integer.
INSERT OR IGNORE INTO languages (code, name) VALUES
    ('jp', 'Japanese');
