-- WARNING: Running this script deletes and recreates the company database.
DROP DATABASE IF EXISTS company;

CREATE DATABASE company CHARACTER SET utf8mb4;

USE company;

CREATE TABLE DEPARTMENT (
    Dnumber INT NOT NULL,
    Dname VARCHAR(50) NOT NULL,
    mgr_ssn CHAR(9) NOT NULL,
    mgr_start_date DATE NOT NULL,
    PRIMARY KEY (Dnumber)
);

CREATE TABLE EMPLOYEE (
    ssn CHAR(9) NOT NULL,
    fname VARCHAR(50) NOT NULL,
    lname VARCHAR(50) NOT NULL,
    bdate DATE NOT NULL,
    address VARCHAR(100) NOT NULL,
    gender CHAR(1) NOT NULL,
    salary DECIMAL(10, 2) NOT NULL,
    -- Temporarily nullable so the first employees can be inserted before departments.
    Dno INT NULL,
    PRIMARY KEY (ssn),
    CONSTRAINT fk_employee_department FOREIGN KEY (Dno) REFERENCES DEPARTMENT (Dnumber) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Add the circular reference only after both tables exist.
ALTER TABLE DEPARTMENT
ADD CONSTRAINT fk_department_manager FOREIGN KEY (mgr_ssn) REFERENCES EMPLOYEE (ssn) ON DELETE RESTRICT ON UPDATE RESTRICT;

CREATE TABLE PROJECT (
    Pnumber INT NOT NULL,
    Pname VARCHAR(50) NOT NULL,
    Plocation VARCHAR(50) NOT NULL,
    Dno INT NOT NULL,
    PRIMARY KEY (Pnumber),
    CONSTRAINT fk_project_department FOREIGN KEY (Dno) REFERENCES DEPARTMENT (Dnumber) ON DELETE RESTRICT ON UPDATE RESTRICT
);