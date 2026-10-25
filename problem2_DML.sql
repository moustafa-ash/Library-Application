-- Run once on a new library database. Check for existing rows first.
USE library;

INSERT INTO AUTHOR (author_id, name, country, photo_filename) VALUES
    (1, 'Naguib Mahfouz', 'Egypt', NULL),
    (2, 'Taha Hussein', 'Egypt', NULL),
    (3, 'Ahdaf Soueif', 'Egypt', NULL);

INSERT INTO BOOK (title, price, author_id, cover_filename) VALUES
    ('Library sample 1', 120.00, 1, NULL),
    ('Library sample 2', 95.50, 1, NULL),
    ('Library sample 3', 150.00, 2, NULL),
    ('Library sample 4', 80.00, 2, NULL),
    ('Library sample 5', 110.75, 3, NULL),
    ('Library sample 6', 135.00, 3, NULL);
