-- Seed mínimo indispensable: sin esto, los FKs/defaults del schema no resuelven.
-- games: los 3 códigos ya enumerados en el CHECK de games.code.
-- languages: 'en' con id=1, referenciado por el DEFAULT de collection_items.language_id.

INSERT OR IGNORE INTO games (id, code, name) VALUES
    (1, 'pokemon', 'Pokémon'),
    (2, 'one_piece', 'One Piece'),
    (3, 'magic', 'Magic: The Gathering');

INSERT OR IGNORE INTO languages (id, code, name) VALUES
    (1, 'en', 'English');
