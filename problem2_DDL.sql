-- Moustafa's BOOK definition. Ibrahim supplies AUTHOR before this statement.
-- Prerequisite: AUTHOR.author_id is a signed INT primary key, using InnoDB.
-- No database/table reset: coordinate edits before executing this shared file.
CREATE DATABASE IF NOT EXISTS library CHARACTER SET utf8mb4;
USE library;

CREATE TABLE BOOK (
    book_id INT NOT NULL AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    author_id INT NOT NULL,
    cover_filename VARCHAR(36) NULL,
    PRIMARY KEY (book_id),
    CONSTRAINT chk_book_price CHECK (price >= 0),
    CONSTRAINT fk_book_author FOREIGN KEY (author_id)
        REFERENCES AUTHOR (author_id) ON DELETE CASCADE
) ENGINE=InnoDB;
