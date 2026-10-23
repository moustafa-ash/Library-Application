USE company;

START TRANSACTION;

INSERT INTO
    EMPLOYEE (
        ssn,
        fname,
        lname,
        bdate,
        address,
        gender,
        salary,
        Dno
    )
VALUES (
        '100000001',
        'Moustafa',
        'Mohamed',
        '2005-04-26',
        'Alexandria',
        'M',
        38000.00,
        NULL
    ),
    (
        '100000002',
        'Ibrahim',
        'Hossam',
        '2005-01-22',
        'Alexandria',
        'M',
        20000.00,
        NULL
    ),
    (
        '100000003',
        'Omar',
        'Nassret',
        '1988-11-05',
        'Giza',
        'M',
        22000.00,
        NULL
    );

INSERT INTO
    DEPARTMENT (
        Dnumber,
        Dname,
        mgr_ssn,
        mgr_start_date
    )
VALUES (
        1,
        'Engineering',
        '100000001',
        '2024-01-01'
    ),
    (
        2,
        'Finance',
        '100000002',
        '2024-02-01'
    ),
    (
        3,
        'Operations',
        '100000003',
        '2024-03-01'
    );

UPDATE EMPLOYEE SET Dno = 1 WHERE ssn = '100000001';

UPDATE EMPLOYEE SET Dno = 2 WHERE ssn = '100000002';

UPDATE EMPLOYEE SET Dno = 3 WHERE ssn = '100000003';

INSERT INTO
    PROJECT (
        Pnumber,
        Pname,
        Plocation,
        Dno
    )
VALUES (
        101,
        'Library Website',
        'Alexandria',
        1
    ),
    (
        102,
        'Budget Review',
        'Cairo',
        2
    ),
    (
        103,
        'Inventory Setup',
        'Giza',
        3
    );

COMMIT;