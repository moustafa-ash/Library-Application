-- Moustafa's six books. Run once after AUTHOR seeds with IDs 1, 2, and 3.
-- Coordinate these IDs with Ibrahim; no AUTHOR records are supplied here.
USE library;

INSERT INTO BOOK (title, price, author_id, cover_filename) VALUES
    ('Library sample 1', 120.00, 1, NULL),
    ('Library sample 2', 95.50, 1, NULL),
    ('Library sample 3', 150.00, 2, NULL),
    ('Library sample 4', 80.00, 2, NULL),
    ('Library sample 5', 110.75, 3, NULL),
    ('Library sample 6', 135.00, 3, NULL);
