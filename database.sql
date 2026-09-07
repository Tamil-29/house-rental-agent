-- =======================================================
-- Database: house_rental_db
-- Project: House Rental Agent
-- Description: MySQL Database Schema and Seed Data
-- =======================================================

CREATE DATABASE IF NOT EXISTS house_rental_db;
USE house_rental_db;

-- Drop tables if they already exist (in reverse order of dependencies)
DROP TABLE IF EXISTS rental_requests;
DROP TABLE IF EXISTS houses;
DROP TABLE IF EXISTS users;

-- -------------------------------------------------------
-- 1. Table: users
-- -------------------------------------------------------
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'owner', 'tenant') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 2. Table: houses
-- -------------------------------------------------------
CREATE TABLE houses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    owner_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    location VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    rent DECIMAL(10, 2) NOT NULL,
    deposit DECIMAL(10, 2) NOT NULL,
    bedrooms INT NOT NULL,
    bathrooms INT NOT NULL,
    furnishing ENUM('Furnished', 'Semi-Furnished', 'Unfurnished') NOT NULL DEFAULT 'Furnished',
    description TEXT,
    image VARCHAR(255) DEFAULT 'default_house.jpg',
    status ENUM('Available', 'Rented') NOT NULL DEFAULT 'Available',
    approved TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_house_owner FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- 3. Table: rental_requests
-- -------------------------------------------------------
CREATE TABLE rental_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    house_id INT NOT NULL,
    tenant_id INT NOT NULL,
    status ENUM('Pending', 'Accepted', 'Rejected') NOT NULL DEFAULT 'Pending',
    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_request_house FOREIGN KEY (house_id) REFERENCES houses(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_tenant FOREIGN KEY (tenant_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -------------------------------------------------------
-- Sample Seed Data
-- 1. Administrator : admin@example.com   | Password: admin123
-- 2. House Owner   : owner@example.com   | Password: owner123
-- 3. Tenant        : tenant@example.com  | Password: tenant123
-- -------------------------------------------------------

INSERT INTO users (id, name, email, phone, password, role) VALUES
(1, 'System Administrator', 'admin@example.com', '9876543210', 'scrypt:32768:8:1$7ndxiGTBsTjP4zk7$2ad6ffc7cfd86480e544d140233d4c093e2f210c5deb9e1084bc745df92443ea6ad7322fb1b13dd9f70af5086f27846d59fd580e184cdeae4102b5d737d10266', 'admin'),
(2, 'Rajesh Kumar', 'owner@example.com', '9123456780', 'scrypt:32768:8:1$9qBxXu3vl3IDHN9z$5f7fc19f4abd273293743fa5debb3a4ca31df982b7ffa60d2a177d1ba28b244f2e2cd7ed262f85ae4db08c903eaa816c1101101eb09963bf8bc170c62151a207', 'owner'),
(3, 'Ananya Sharma', 'tenant@example.com', '9988776655', 'scrypt:32768:8:1$1DaCBLkzR0d0njKv$444006c84bdebb673a3719a0a4f96d87e916149b8cd6989ed36c2e2fb653815de01a518e81aec53b95a420915cfd78beebf41c9fd9c27e56b45c206c2425201f', 'tenant');

-- Sample houses listed by Rajesh Kumar (owner_id = 2)
INSERT INTO houses (id, owner_id, title, location, address, rent, deposit, bedrooms, bathrooms, furnishing, description, image, status, approved) VALUES
(1, 2, 'Luxury 2BHK Apartment near Metro', 'Indiranagar, Bangalore', 'Flat 302, Green Valley Apartments, 12th Main, Indiranagar', 28000.00, 60000.00, 2, 2, 'Furnished', 'Spacious 2 BHK with modern modular kitchen, wooden flooring in master bedroom, 24/7 security, power backup, and dedicated covered car parking.', 'house1.jpg', 'Available', 1),
(2, 2, 'Cozy 1BHK Flat for Students & Bachelors', 'Koramangala, Bangalore', 'House #45, 5th Block, near Sony World Signal, Koramangala', 14500.00, 30000.00, 1, 1, 'Semi-Furnished', 'Bright and ventilated 1 BHK flat with wardrobe, geyser, kitchen cabinets, and balcony. Located near popular colleges, tech parks, and eateries.', 'house2.jpg', 'Available', 1),
(3, 2, 'Spacious 3BHK Independent Villa', 'Whitefield, Bangalore', 'Villa 12, Palm Meadows Enclave, ECC Road, Whitefield', 45000.00, 100000.00, 3, 3, 'Furnished', 'Beautiful 3 BHK duplex villa featuring private garden, modular kitchen, large hall, clubhouse access, and swimming pool within gated community.', 'house3.jpg', 'Available', 1);

-- Sample pending rental request by Ananya Sharma (tenant_id = 3) for house 1
INSERT INTO rental_requests (id, house_id, tenant_id, status, request_date) VALUES
(1, 1, 3, 'Pending', NOW());
