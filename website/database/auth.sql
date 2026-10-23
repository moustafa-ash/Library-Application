-- Optional setup for a new local MySQL instance; existing Lab 2 users are kept.
CREATE DATABASE IF NOT EXISTS registration
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE registration;

CREATE TABLE IF NOT EXISTS users (
    user_id INT NOT NULL AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    registration_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE (email)
) ENGINE=InnoDB;
