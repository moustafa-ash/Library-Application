-- One-time additive migration for an existing library database.
-- Run once if AUTHOR already exists and does not yet have country.
-- Existing rows are preserved and receive "Unknown"; edit their countries in the app.
USE library;
ALTER TABLE AUTHOR
    ADD COLUMN country VARCHAR(100) NOT NULL DEFAULT 'Unknown';
ALTER TABLE AUTHOR
    ALTER COLUMN country DROP DEFAULT;
